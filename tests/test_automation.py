from pathlib import Path


def test_close_stops_started_playwright_instead_of_manager() -> None:
    from codecheck_shield.automation import BrowserSettings, PlaywrightAutomation

    class FakeContext:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeManager:
        pass

    class FakePlaywright:
        def __init__(self) -> None:
            self.stopped = False

        def stop(self) -> None:
            self.stopped = True

    automation = PlaywrightAutomation(
        BrowserSettings(
            browser_channel="chrome",
            user_data_dir=Path("/tmp/profile"),
            profile_directory=None,
            headless=True,
            slow_mo_ms=0,
            screenshot_dir=Path("/tmp/screenshots"),
        )
    )
    context = FakeContext()
    playwright = FakePlaywright()
    automation._context = context
    automation._playwright_manager = FakeManager()
    automation._playwright = playwright

    automation.close()

    assert context.closed is True
    assert playwright.stopped is True


def test_build_automation_returns_cdp_mode_when_requested() -> None:
    from types import SimpleNamespace

    from codecheck_shield.automation import CdpAttachAutomation, build_automation

    automation = build_automation(
        SimpleNamespace(
            browser_mode="attach-cdp",
            cdp_url="http://127.0.0.1:9333",
            browser_channel="chrome",
            user_data_dir=None,
            profile_directory=None,
            headless=False,
            slow_mo_ms=0,
            screenshot_dir="./artifacts/screenshots",
        )
    )

    assert isinstance(automation, CdpAttachAutomation)
