from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from codecheck_shield.errors import AutomationFailure
from codecheck_shield.models import TaskInput, TaskResult


class BatchRunner:
    def __init__(
        self,
        automation: object,
        clock: Callable[[], str] | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self._automation = automation
        self._clock = clock or (lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
        self._logger = logger

    def run(self, tasks: list[TaskInput]) -> list[TaskResult]:
        results: list[TaskResult] = []
        total = len(tasks)
        try:
            for index, task in enumerate(tasks, start=1):
                processed_at = self._clock()
                self._log(f"START index={index}/{total} row={task.row_number} url={task.url}")
                try:
                    getattr(self._automation, "shield_issue")(task.url, task.reason)
                except AutomationFailure as exc:
                    self._log(
                        f"FAILED index={index}/{total} row={task.row_number} status={exc.status} message={exc.message}"
                    )
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
                    self._log(f"FAILED index={index}/{total} row={task.row_number} status=failed message={exc}")
                    results.append(TaskResult.failure(task, str(exc), processed_at))
                    continue
                self._log(f"SUCCESS index={index}/{total} row={task.row_number} status=success")
                results.append(TaskResult.success(task, processed_at, screenshot_path=""))
        finally:
            close = getattr(self._automation, "close", None)
            if callable(close):
                close()
        return results

    def _log(self, message: str) -> None:
        if self._logger is not None:
            self._logger(message)
