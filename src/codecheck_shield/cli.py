from __future__ import annotations

import argparse
import ntpath
import os
import platform
import sys
from pathlib import Path
from typing import TextIO

from codecheck_shield.automation import build_automation
from codecheck_shield.config import (
    DEFAULT_ACTION_DELAY_SECONDS,
    DEFAULT_CONFIG_FILE_NAME,
    DEFAULT_DESKTOP_CALIBRATION_FILE,
    DEFAULT_OUTPUT_SUFFIX,
    DEFAULT_PAGE_LOAD_SECONDS,
    AppConfig,
    RequestAuthConfig,
    WindowsDesktopConfig,
    default_config,
    load_config,
    save_config,
)
from codecheck_shield.curl_import import parse_curl_text
from codecheck_shield.desktop import run_desktop_calibration
from codecheck_shield.models import DEFAULT_REASON
from codecheck_shield.results import ResultsCsvWriter, write_retry_tasks_csv
from codecheck_shield.runner import BatchRunner
from codecheck_shield.spreadsheet import load_tasks


def primary_browser_user_data_dir(
    browser_channel: str,
    system: str | None = None,
    env: dict[str, str] | None = None,
) -> str:
    current_system = (system or platform.system()).lower()
    current_env = env or dict(os.environ)
    channel = browser_channel.lower()

    if current_system == "windows":
        local_app_data = current_env.get("LOCALAPPDATA")
        if not local_app_data:
            raise ValueError("LOCALAPPDATA is required to resolve the Windows browser profile path")
        roots = {
            "chrome": ntpath.join(local_app_data, "Google", "Chrome", "User Data"),
            "msedge": ntpath.join(local_app_data, "Microsoft", "Edge", "User Data"),
        }
        return roots.get(channel, roots["chrome"])

    home = Path.home()
    roots = {
        "chrome": str(home / ".config" / "google-chrome"),
        "msedge": str(home / ".config" / "microsoft-edge"),
    }
    return roots.get(channel, roots["chrome"])


def default_user_data_dir(
    browser_channel: str,
    system: str | None = None,
    env: dict[str, str] | None = None,
) -> str:
    current_system = (system or platform.system()).lower()
    current_env = env or dict(os.environ)

    if current_system == "windows":
        local_app_data = current_env.get("LOCALAPPDATA")
        if not local_app_data:
            raise ValueError("LOCALAPPDATA is required to resolve the Windows browser profile path")
        return ntpath.join(local_app_data, "codecheck-shield", "chrome-profile")

    return str(Path.home() / ".config" / "codecheck-shield" / "chrome-profile")


def is_primary_browser_user_data_dir(
    user_data_dir: str,
    browser_channel: str,
    system: str | None = None,
    env: dict[str, str] | None = None,
) -> bool:
    primary_dir = primary_browser_user_data_dir(browser_channel, system=system, env=env)
    normalized_input = ntpath.normcase(os.path.normpath(os.path.expandvars(user_data_dir)))
    normalized_primary = ntpath.normcase(os.path.normpath(os.path.expandvars(primary_dir)))
    return normalized_input == normalized_primary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch ignore CodeCheck issues from a spreadsheet")
    parser.add_argument("input_file", nargs="?", help="Path to the CSV or XLSX task file")
    parser.add_argument("--config", help="Path to a local JSON config file")
    parser.add_argument("--output", help="Path to the output CSV file")
    parser.add_argument("--default-reason", help="Fallback reason used when a row does not provide 屏蔽理由")
    parser.add_argument("--calibrate-desktop", action="store_true", help="Interactively record desktop click points and save them to a calibration file")
    parser.add_argument("--browser-mode", choices=["requests", "isolated-profile", "attach-cdp", "windows-desktop"], help="Send direct HTTP requests, launch an isolated automation profile, attach to an already running Chrome via CDP, or drive the current desktop browser")
    parser.add_argument("--request-cookie", help="Raw Cookie header value used in requests mode")
    parser.add_argument("--request-cookie-file", help="Path to a text file containing the raw Cookie header value for requests mode")
    parser.add_argument("--agency-id", help="AgencyId header used in requests mode")
    parser.add_argument("--cftk", help="cftk header used in requests mode")
    parser.add_argument("--request-operator", help="operator field used in requests mode")
    parser.add_argument("--request-platform", help="platform field used in requests mode")
    parser.add_argument("--cdp-url", help="CDP endpoint used when --browser-mode=attach-cdp")
    parser.add_argument("--desktop-calibration-file", help="Desktop calibration JSON used when --browser-mode=windows-desktop")
    parser.add_argument("--page-load-seconds", type=float, help="Delay after opening each URL in windows-desktop mode")
    parser.add_argument("--action-delay-seconds", type=float, help="Delay between desktop automation actions")
    parser.add_argument("--user-data-dir", help="Persistent browser profile directory")
    parser.add_argument("--profile-directory", help="Chrome profile directory inside the user data dir, such as 'Default' or 'Profile 2'")
    parser.add_argument("--browser-channel", help="Playwright browser channel")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--slow-mo-ms", type=int, help="Delay between Playwright actions in milliseconds")
    parser.add_argument("--screenshot-dir", help="Directory for failure screenshots")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "setup":
        return setup_main(argv[1:])
    if argv and argv[0] == "run":
        return run_main(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    return execute_args(args, parser)


def setup_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save a local config for later batch runs")
    parser.add_argument("--from-curl-file", required=True, help="Path to a text file containing a captured cURL request")
    parser.add_argument("--config", default=str(default_config_path()), help="Path to the local JSON config file")
    parser.add_argument("--default-reason", default=DEFAULT_REASON, help="Fallback reason used when a row does not provide 屏蔽理由")
    parser.add_argument("--desktop-calibration-file", default=DEFAULT_DESKTOP_CALIBRATION_FILE, help="Default desktop calibration JSON path")
    parser.add_argument("--page-load-seconds", type=float, default=DEFAULT_PAGE_LOAD_SECONDS, help="Default delay after opening each URL in windows-desktop mode")
    parser.add_argument("--action-delay-seconds", type=float, default=DEFAULT_ACTION_DELAY_SECONDS, help="Default delay between desktop automation actions")
    parser.add_argument("--output-suffix", default=DEFAULT_OUTPUT_SUFFIX, help="Default suffix used when --output is omitted")
    args = parser.parse_args(argv)

    curl_text = Path(args.from_curl_file).read_text(encoding="utf-8")
    imported = parse_curl_text(curl_text)
    config_path = Path(args.config)
    config = load_config(config_path) if config_path.exists() else default_config()
    config.mode = "requests"
    config.default_reason = args.default_reason
    config.requests = RequestAuthConfig(
        cookie=imported.cookie,
        agency_id=imported.agency_id,
        cftk=imported.cftk,
        operator=imported.operator,
        platform=imported.platform,
    )
    config.windows_desktop = WindowsDesktopConfig(
        calibration_file=args.desktop_calibration_file,
        page_load_seconds=args.page_load_seconds,
        action_delay_seconds=args.action_delay_seconds,
    )
    if config.output is None:
        config.output = default_config().output
    config.output.default_suffix = args.output_suffix
    save_config(config_path, config)
    print(config_path)
    return 0


def run_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.input_file:
        parser.error("input_file is required")
    return execute_args(args, parser)


def execute_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    config_path = resolve_config_path(args.config)
    config = load_config(config_path) if config_path else None
    apply_config(args, config)
    apply_runtime_defaults(args)
    if args.calibrate_desktop:
        return run_desktop_calibration(Path(args.desktop_calibration_file))
    if not args.input_file:
        parser.error("input_file is required unless --calibrate-desktop is set")
    if args.browser_mode == "isolated-profile":
        if not args.user_data_dir:
            args.user_data_dir = default_user_data_dir(args.browser_channel)
        if is_primary_browser_user_data_dir(args.user_data_dir, args.browser_channel):
            print("The primary Chrome/Edge user data directory is not supported by Playwright persistent contexts.")
            print(f"Use a dedicated automation profile directory instead, for example: {default_user_data_dir(args.browser_channel)}")
            return 1
    else:
        args.user_data_dir = None
    input_path = Path(args.input_file)
    default_suffix = config.output.default_suffix if config and config.output else DEFAULT_OUTPUT_SUFFIX
    output_path = Path(args.output) if args.output else default_output_path(input_path, default_suffix)

    tasks, skipped = load_task_batch(input_path, args.default_reason)
    if not tasks:
        print(f"No tasks found in {input_path}")
        return 1

    automation = build_automation(args)
    log_path = default_log_path(output_path)
    results_writer = ResultsCsvWriter(output_path, tasks)
    try:
        with log_path.open("a", encoding="utf-8") as log_handle:
            logger = build_logger(log_handle)
            for message in skipped:
                logger(message)
            results = create_batch_runner(automation, logger=logger, on_result=results_writer.write_result).run(tasks)
    finally:
        results_writer.close()
    failures = [result for result in results if result.status != "success"]
    retry429_tasks = [result.task for result in results if _is_retryable_429(result)]
    if retry429_tasks:
        write_retry_tasks_csv(retry429_tasks, retry429_path(output_path))
    if failures:
        print(f"Completed with failures: {len(failures)}/{len(results)}")
        first_failure = failures[0]
        print(
            "First failure:"
            f" url={first_failure.task.url}"
            f" status={first_failure.status}"
            f" message={first_failure.message}"
        )
        print(output_path)
        return 1

    print(output_path)
    return 0


def default_config_path() -> Path:
    return Path.cwd() / DEFAULT_CONFIG_FILE_NAME


def default_output_path(input_path: Path, default_suffix: str = DEFAULT_OUTPUT_SUFFIX) -> Path:
    return Path.cwd() / "output" / f"{input_path.stem}{default_suffix}"


def default_log_path(output_path: Path) -> Path:
    return output_path.with_suffix(".log")


def retry429_path(output_path: Path) -> Path:
    if output_path.name.endswith(".results.csv"):
        return output_path.with_name(output_path.name[: -len(".results.csv")] + ".retry429.csv")
    return output_path.with_name(f"{output_path.stem}.retry429.csv")


def build_logger(handle: TextIO):
    def log(message: str) -> None:
        print(message)
        handle.write(f"{message}\n")
        handle.flush()

    return log


def create_batch_runner(automation: object, logger, on_result=None):
    try:
        return BatchRunner(automation, logger=logger, on_result=on_result)
    except TypeError:
        return BatchRunner(automation)


def _is_retryable_429(result) -> bool:
    return "HTTP 429" in result.message


def load_task_batch(input_path: Path, default_reason: str) -> tuple[list, list[str]]:
    try:
        loaded = load_tasks(input_path, default_reason=default_reason, include_skipped=True)
    except TypeError:
        return load_tasks(input_path, default_reason=default_reason), []
    if isinstance(loaded, tuple) and len(loaded) == 2:
        return loaded
    return loaded, []


def resolve_config_path(config_arg: str | None) -> Path | None:
    if config_arg:
        return Path(config_arg)
    candidate = default_config_path()
    if candidate.exists():
        return candidate
    return None


def apply_config(args: argparse.Namespace, config: AppConfig | None) -> None:
    if config is None:
        return
    if args.browser_mode is None:
        args.browser_mode = config.mode
    if args.default_reason is None:
        args.default_reason = config.default_reason

    request_config = config.requests
    if request_config is not None:
        if args.request_cookie is None and args.request_cookie_file is None and request_config.cookie:
            args.request_cookie = request_config.cookie
        if args.agency_id is None and request_config.agency_id:
            args.agency_id = request_config.agency_id
        if args.cftk is None and request_config.cftk:
            args.cftk = request_config.cftk
        if args.request_operator is None and request_config.operator:
            args.request_operator = request_config.operator
        if args.request_platform is None and request_config.platform:
            args.request_platform = request_config.platform

    desktop_config = config.windows_desktop
    if desktop_config is not None:
        if args.desktop_calibration_file is None:
            args.desktop_calibration_file = desktop_config.calibration_file
        if args.page_load_seconds is None:
            args.page_load_seconds = desktop_config.page_load_seconds
        if args.action_delay_seconds is None:
            args.action_delay_seconds = desktop_config.action_delay_seconds


def apply_runtime_defaults(args: argparse.Namespace) -> None:
    if args.browser_mode is None:
        args.browser_mode = "requests"
    if args.default_reason is None:
        args.default_reason = DEFAULT_REASON
    if args.request_operator is None:
        args.request_operator = "Gitee"
    if args.request_platform is None:
        args.request_platform = "clouddragon"
    if args.cdp_url is None:
        args.cdp_url = "http://127.0.0.1:9222"
    if args.desktop_calibration_file is None:
        args.desktop_calibration_file = DEFAULT_DESKTOP_CALIBRATION_FILE
    if args.page_load_seconds is None:
        args.page_load_seconds = DEFAULT_PAGE_LOAD_SECONDS
    if args.action_delay_seconds is None:
        args.action_delay_seconds = DEFAULT_ACTION_DELAY_SECONDS
    if args.browser_channel is None:
        args.browser_channel = "chrome"
    if args.slow_mo_ms is None:
        args.slow_mo_ms = 150
    if args.screenshot_dir is None:
        args.screenshot_dir = "./artifacts/screenshots"


if __name__ == "__main__":
    raise SystemExit(main())
