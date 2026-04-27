from pathlib import Path


def test_load_desktop_calibration_reads_required_points(tmp_path: Path) -> None:
    from codecheck_shield.desktop import load_desktop_calibration

    config = tmp_path / "desktop-calibration.json"
    config.write_text(
        (
            "{"
            '"status_button": {"x": 100, "y": 200},'
            '"ignore_option": {"x": 120, "y": 240},'
            '"comment_field": {"x": 300, "y": 500},'
            '"confirm_button": {"x": 640, "y": 720}'
            "}"
        ),
        encoding="utf-8",
    )

    calibration = load_desktop_calibration(config)

    assert calibration.status_button == (100, 200)
    assert calibration.ignore_option == (120, 240)
    assert calibration.comment_field == (300, 500)
    assert calibration.confirm_button == (640, 720)


def test_windows_desktop_automation_runs_click_sequence(tmp_path: Path) -> None:
    from codecheck_shield.desktop import DesktopCalibration, DesktopSettings, WindowsDesktopAutomation

    calls: list[tuple[str, object]] = []

    class FakeBackend:
        def click(self, x: int, y: int) -> None:
            calls.append(("click", (x, y)))

        def hotkey(self, *keys: str) -> None:
            calls.append(("hotkey", keys))

        def screenshot(self, path: str) -> None:
            calls.append(("screenshot", path))

    class FakeBrowser:
        def open_new_tab(self, url: str) -> None:
            calls.append(("open", url))

    class FakeClipboard:
        def copy(self, text: str) -> None:
            calls.append(("copy", text))

    automation = WindowsDesktopAutomation(
        settings=DesktopSettings(
            calibration=DesktopCalibration(
                status_button=(10, 20),
                ignore_option=(30, 40),
                comment_field=(50, 60),
                confirm_button=(70, 80),
            ),
            screenshot_dir=tmp_path / "shots",
            page_load_seconds=0.0,
            action_delay_seconds=0.0,
        ),
        backend=FakeBackend(),
        browser=FakeBrowser(),
        clipboard=FakeClipboard(),
        sleeper=lambda seconds: calls.append(("sleep", seconds)),
    )

    automation.shield_issue("https://example.test/1", "评审可屏蔽")

    assert calls == [
        ("open", "https://example.test/1"),
        ("sleep", 0.0),
        ("click", (10, 20)),
        ("sleep", 0.0),
        ("click", (30, 40)),
        ("sleep", 0.0),
        ("click", (50, 60)),
        ("sleep", 0.0),
        ("copy", "评审可屏蔽"),
        ("hotkey", ("ctrl", "a")),
        ("hotkey", ("ctrl", "v")),
        ("sleep", 0.0),
        ("click", (70, 80)),
        ("sleep", 0.0),
    ]


def test_windows_desktop_automation_saves_failure_screenshot(tmp_path: Path) -> None:
    from codecheck_shield.errors import AutomationFailure
    from codecheck_shield.desktop import DesktopCalibration, DesktopSettings, WindowsDesktopAutomation

    screenshots: list[str] = []

    class FakeBackend:
        def click(self, x: int, y: int) -> None:
            raise RuntimeError("button not found")

        def hotkey(self, *keys: str) -> None:
            raise AssertionError("should not reach hotkey")

        def screenshot(self, path: str) -> None:
            screenshots.append(path)

    class FakeBrowser:
        def open_new_tab(self, url: str) -> None:
            return None

    class FakeClipboard:
        def copy(self, text: str) -> None:
            return None

    automation = WindowsDesktopAutomation(
        settings=DesktopSettings(
            calibration=DesktopCalibration(
                status_button=(10, 20),
                ignore_option=(30, 40),
                comment_field=(50, 60),
                confirm_button=(70, 80),
            ),
            screenshot_dir=tmp_path / "shots",
            page_load_seconds=0.0,
            action_delay_seconds=0.0,
        ),
        backend=FakeBackend(),
        browser=FakeBrowser(),
        clipboard=FakeClipboard(),
        sleeper=lambda seconds: None,
    )

    try:
        automation.shield_issue("https://example.test/1", "评审可屏蔽")
    except AutomationFailure as exc:
        assert exc.status == "failed_desktop_step"
        assert "button not found" in exc.message
        assert exc.screenshot_path.endswith(".png")
    else:
        raise AssertionError("expected AutomationFailure")

    assert len(screenshots) == 1
