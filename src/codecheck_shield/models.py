from __future__ import annotations

from dataclasses import dataclass


DEFAULT_REASON = "评审可屏蔽"


@dataclass(slots=True)
class TaskInput:
    row_number: int
    url: str
    reason: str
    raw: dict[str, str]


@dataclass(slots=True)
class TaskResult:
    task: TaskInput
    status: str
    message: str
    processed_at: str
    screenshot_path: str

    @classmethod
    def success(cls, task: TaskInput, processed_at: str, screenshot_path: str) -> "TaskResult":
        return cls(
            task=task,
            status="success",
            message="",
            processed_at=processed_at,
            screenshot_path=screenshot_path,
        )

    @classmethod
    def failure(
        cls,
        task: TaskInput,
        message: str,
        processed_at: str,
        screenshot_path: str = "",
    ) -> "TaskResult":
        return cls(
            task=task,
            status="failed",
            message=message,
            processed_at=processed_at,
            screenshot_path=screenshot_path,
        )
