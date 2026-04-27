from __future__ import annotations

import json
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from codecheck_shield.errors import AutomationFailure


Point = tuple[int, int]


@dataclass(slots=True)
class DesktopCalibration:
    status_button: Point
    ignore_option: Point
    comment_field: Point
    confirm_button: Point


@dataclass(slots=True)
class DesktopSettings:
    calibration: DesktopCalibration
    screenshot_dir: Path
    page_load_seconds: float
    action_delay_seconds: float


def load_desktop_calibration(path: Path | str) -> DesktopCalibration:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return DesktopCalibration(
        status_button=_point(data["status_button"]),
        ignore_option=_point(data["ignore_option"]),
        comment_field=_point(data["comment_field"]),
        confirm_button=_point(data["confirm_button"]),
    )


def save_desktop_calibration(calibration: DesktopCalibration, path: Path | str) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "status_button": _point_dict(calibration.status_button),
                "ignore_option": _point_dict(calibration.ignore_option),
                "comment_field": _point_dict(calibration.comment_field),
                "confirm_button": _point_dict(calibration.confirm_button),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination


def run_desktop_calibration(
    destination: Path | str,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
    position_provider: Callable[[], Point] | None = None,
) -> int:
    provider = position_provider or _pyautogui_position
    output_func("Desktop calibration started. Move the mouse to each target and press Enter.")
    calibration = DesktopCalibration(
        status_button=_capture_point("修改问题状态 按钮", input_func, output_func, provider),
        ignore_option=_capture_point("忽略问题 选项", input_func, output_func, provider),
        comment_field=_capture_point("评论输入框", input_func, output_func, provider),
        confirm_button=_capture_point("确定 按钮", input_func, output_func, provider),
    )
    saved = save_desktop_calibration(calibration, destination)
    output_func(f"Calibration saved to {saved}")
    return 0


class PyAutoGuiBackend:
    def __init__(self) -> None:
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Desktop automation dependencies are not installed. Run `pip install -e .[automation]`."
            ) from exc
        self._pyautogui = pyautogui

    def click(self, x: int, y: int) -> None:
        self._pyautogui.click(x=x, y=y)

    def hotkey(self, *keys: str) -> None:
        self._pyautogui.hotkey(*keys)

    def screenshot(self, path: str) -> None:
        self._pyautogui.screenshot(path)

    def position(self) -> Point:
        pos = self._pyautogui.position()
        return int(pos.x), int(pos.y)


class BrowserLauncher:
    def open_new_tab(self, url: str) -> None:
        if not webbrowser.open_new_tab(url):
            raise RuntimeError(f"Could not open browser tab for {url}")


class Clipboard:
    def __init__(self) -> None:
        try:
            import pyperclip
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Desktop automation dependencies are not installed. Run `pip install -e .[automation]`."
            ) from exc
        self._pyperclip = pyperclip

    def copy(self, text: str) -> None:
        self._pyperclip.copy(text)


class WindowsDesktopAutomation:
    def __init__(
        self,
        settings: DesktopSettings,
        backend: object | None = None,
        browser: object | None = None,
        clipboard: object | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._settings = settings
        self._backend = backend or PyAutoGuiBackend()
        self._browser = browser or BrowserLauncher()
        self._clipboard = clipboard or Clipboard()
        self._sleep = sleeper or time.sleep

    def shield_issue(self, url: str, reason: str) -> None:
        try:
            getattr(self._browser, "open_new_tab")(url)
            self._sleep(self._settings.page_load_seconds)
            self._click(self._settings.calibration.status_button)
            self._sleep(self._settings.action_delay_seconds)
            self._click(self._settings.calibration.ignore_option)
            self._sleep(self._settings.action_delay_seconds)
            self._click(self._settings.calibration.comment_field)
            self._sleep(self._settings.action_delay_seconds)
            getattr(self._clipboard, "copy")(reason)
            getattr(self._backend, "hotkey")("ctrl", "a")
            getattr(self._backend, "hotkey")("ctrl", "v")
            self._sleep(self._settings.action_delay_seconds)
            self._click(self._settings.calibration.confirm_button)
            self._sleep(self._settings.action_delay_seconds)
            getattr(self._backend, "hotkey")("ctrl", "w")
            self._sleep(self._settings.action_delay_seconds)
        except AutomationFailure:
            raise
        except Exception as exc:
            raise self._automation_failure("failed_desktop_step", str(exc)) from exc

    def close(self) -> None:
        return None

    def _click(self, point: Point) -> None:
        getattr(self._backend, "click")(point[0], point[1])

    def _automation_failure(self, status: str, message: str) -> AutomationFailure:
        screenshot_path = ""
        try:
            self._settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            screenshot_file = self._settings.screenshot_dir / f"desktop-failure-{timestamp}.png"
            getattr(self._backend, "screenshot")(str(screenshot_file))
            screenshot_path = str(screenshot_file)
        except Exception:
            screenshot_path = ""
        return AutomationFailure(status, message, screenshot_path)


def _capture_point(
    label: str,
    input_func: Callable[[str], str],
    output_func: Callable[[str], None],
    position_provider: Callable[[], Point],
) -> Point:
    input_func(f"Move the mouse to {label}, then press Enter...")
    point = position_provider()
    output_func(f"{label}: x={point[0]}, y={point[1]}")
    return point


def _pyautogui_position() -> Point:
    backend = PyAutoGuiBackend()
    return backend.position()


def _point(raw: dict[str, int]) -> Point:
    return int(raw["x"]), int(raw["y"])


def _point_dict(point: Point) -> dict[str, int]:
    return {"x": point[0], "y": point[1]}
