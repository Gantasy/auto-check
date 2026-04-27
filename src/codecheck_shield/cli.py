from __future__ import annotations

import argparse
import ntpath
import os
import platform
from pathlib import Path

from codecheck_shield.automation import build_automation
from codecheck_shield.results import write_results_csv
from codecheck_shield.runner import BatchRunner
from codecheck_shield.spreadsheet import load_tasks


def default_user_data_dir(
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch ignore CodeCheck issues from a spreadsheet")
    parser.add_argument("input_file", help="Path to the CSV or XLSX task file")
    parser.add_argument("--output", help="Path to the output CSV file")
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
    if not args.user_data_dir:
        args.user_data_dir = default_user_data_dir(args.browser_channel)
    input_path = Path(args.input_file)
    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}.results.csv")

    tasks = load_tasks(input_path)
    automation = build_automation(args)
    results = BatchRunner(automation).run(tasks)
    write_results_csv(results, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
