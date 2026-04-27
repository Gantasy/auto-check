from __future__ import annotations

import argparse
import ntpath
import os
import platform
from pathlib import Path

from codecheck_shield.automation import build_automation
from codecheck_shield.desktop import run_desktop_calibration
from codecheck_shield.models import DEFAULT_REASON
from codecheck_shield.results import write_results_csv
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
    parser.add_argument("--output", help="Path to the output CSV file")
    parser.add_argument("--default-reason", default=DEFAULT_REASON, help="Fallback reason used when a row does not provide 屏蔽理由")
    parser.add_argument("--calibrate-desktop", action="store_true", help="Interactively record desktop click points and save them to a calibration file")
    parser.add_argument("--browser-mode", choices=["isolated-profile", "attach-cdp", "windows-desktop"], default="isolated-profile", help="Launch an isolated automation profile, attach to an already running Chrome via CDP, or drive the current desktop browser")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP endpoint used when --browser-mode=attach-cdp")
    parser.add_argument("--desktop-calibration-file", default="./desktop-calibration.json", help="Desktop calibration JSON used when --browser-mode=windows-desktop")
    parser.add_argument("--page-load-seconds", type=float, default=3.0, help="Delay after opening each URL in windows-desktop mode")
    parser.add_argument("--action-delay-seconds", type=float, default=0.5, help="Delay between desktop automation actions")
    parser.add_argument("--user-data-dir", help="Persistent browser profile directory")
    parser.add_argument("--profile-directory", help="Chrome profile directory inside the user data dir, such as 'Default' or 'Profile 2'")
    parser.add_argument("--browser-channel", default="chrome", help="Playwright browser channel")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--slow-mo-ms", type=int, default=150, help="Delay between Playwright actions in milliseconds")
    parser.add_argument("--screenshot-dir", default="./artifacts/screenshots", help="Directory for failure screenshots")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}.results.csv")

    tasks = load_tasks(input_path, default_reason=args.default_reason)
    if not tasks:
        print(f"No tasks found in {input_path}")
        return 1

    automation = build_automation(args)
    results = BatchRunner(automation).run(tasks)
    write_results_csv(results, output_path)
    failures = [result for result in results if result.status != "success"]
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


if __name__ == "__main__":
    raise SystemExit(main())
