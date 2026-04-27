from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AutomationFailure(RuntimeError):
    def __init__(self, status: str, message: str, screenshot_path: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.screenshot_path = screenshot_path


@dataclass(slots=True)
class BrowserSettings:
    browser_channel: str
    user_data_dir: Path
    profile_directory: str | None
    headless: bool
    slow_mo_ms: int
    screenshot_dir: Path


class PlaywrightAutomation:
    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._playwright_manager: Any | None = None
        self._context: Any | None = None

    def shield_issue(self, url: str, reason: str) -> None:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run `pip install -e .[automation]` and `playwright install chromium`."
            ) from exc

        try:
            if self._context is None:
                self._playwright_manager = sync_playwright()
                playwright = self._playwright_manager.start()
                browser_type = playwright.chromium
                launch_args = []
                if self._settings.profile_directory:
                    launch_args.append(f"--profile-directory={self._settings.profile_directory}")
                self._context = browser_type.launch_persistent_context(
                    user_data_dir=str(self._settings.user_data_dir),
                    channel=self._settings.browser_channel,
                    headless=self._settings.headless,
                    slow_mo=self._settings.slow_mo_ms,
                    args=launch_args,
                )
            page = self._context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.get_by_role("button", name="修改问题状态").click()
                self._click_visible_text(page, "忽略问题")
                dialog = page.locator("[role='dialog']").last
                dialog.wait_for(state="visible")
                self._fill_comment(dialog, reason)
                dialog.get_by_role("button", name="确定").click()
                page.get_by_text("修改问题状态").wait_for(state="visible")
            finally:
                page.close()
        except PlaywrightTimeoutError as exc:
            raise self._automation_failure("failed_timeout", str(exc), locals().get("page")) from exc
        except AutomationFailure:
            raise
        except Exception as exc:
            raise self._automation_failure("failed_automation", str(exc), locals().get("page")) from exc

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._playwright_manager is not None:
            self._playwright_manager.stop()
            self._playwright_manager = None

    def _automation_failure(self, status: str, message: str, page: Any | None) -> AutomationFailure:
        screenshot_path = ""
        if page is not None:
            self._settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_file = self._settings.screenshot_dir / "last_failure.png"
            page.screenshot(path=str(screenshot_file), full_page=True)
            screenshot_path = str(screenshot_file)
        return AutomationFailure(status, message, screenshot_path)

    def _click_visible_text(self, page, text: str) -> None:
        candidates = [
            page.get_by_role("menuitem", name=text),
            page.get_by_role("option", name=text),
            page.get_by_text(text, exact=True),
        ]
        for locator in candidates:
            if locator.count():
                locator.first.click()
                return
        raise AutomationFailure("failed_select_ignore", f"Could not find clickable text: {text}")

    def _fill_comment(self, dialog, reason: str) -> None:
        candidates = [
            dialog.locator("textarea"),
            dialog.get_by_label("评论"),
            dialog.get_by_label("备注"),
            dialog.get_by_label("处理意见"),
            dialog.get_by_placeholder("评论"),
            dialog.get_by_placeholder("备注"),
        ]
        for locator in candidates:
            if locator.count():
                locator.first.fill(reason)
                return
        textboxes = dialog.get_by_role("textbox")
        if textboxes.count():
            textboxes.last.fill(reason)
            return
        raise AutomationFailure("failed_fill_comment", "Could not find comment input in dialog")


def build_automation(args) -> PlaywrightAutomation:
    settings = BrowserSettings(
        browser_channel=args.browser_channel,
        user_data_dir=Path(os.path.expandvars(args.user_data_dir)).expanduser(),
        profile_directory=args.profile_directory,
        headless=args.headless,
        slow_mo_ms=args.slow_mo_ms,
        screenshot_dir=Path(os.path.expandvars(args.screenshot_dir)).expanduser(),
    )
    return PlaywrightAutomation(settings)
