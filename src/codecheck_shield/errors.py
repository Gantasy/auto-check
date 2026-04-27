from __future__ import annotations


class AutomationFailure(RuntimeError):
    def __init__(self, status: str, message: str, screenshot_path: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.screenshot_path = screenshot_path
