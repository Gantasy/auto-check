from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from codecheck_shield.errors import AutomationFailure
from codecheck_shield.models import TaskInput, TaskResult


class BatchRunner:
    def __init__(self, automation: object, clock: Callable[[], str] | None = None) -> None:
        self._automation = automation
        self._clock = clock or (lambda: datetime.now().astimezone().isoformat(timespec="seconds"))

    def run(self, tasks: list[TaskInput]) -> list[TaskResult]:
        results: list[TaskResult] = []
        try:
            for task in tasks:
                processed_at = self._clock()
                try:
                    getattr(self._automation, "shield_issue")(task.url, task.reason)
                except AutomationFailure as exc:
                    results.append(
                        TaskResult(
                            task=task,
                            status=exc.status,
                            message=exc.message,
                            processed_at=processed_at,
                            screenshot_path=exc.screenshot_path,
                        )
                    )
                    continue
                except Exception as exc:
                    results.append(TaskResult.failure(task, str(exc), processed_at))
                    continue
                results.append(TaskResult.success(task, processed_at, screenshot_path=""))
        finally:
            close = getattr(self._automation, "close", None)
            if callable(close):
                close()
        return results
