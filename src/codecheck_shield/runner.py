from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import time

from codecheck_shield.errors import AutomationFailure
from codecheck_shield.models import TaskInput, TaskResult


class BatchRunner:
    def __init__(
        self,
        automation: object,
        clock: Callable[[], str] | None = None,
        logger: Callable[[str], None] | None = None,
        on_result: Callable[[TaskResult], None] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._automation = automation
        self._clock = clock or (lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
        self._logger = logger
        self._on_result = on_result
        self._sleep = sleeper or time.sleep

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
                    result = TaskResult(
                        task=task,
                        status=exc.status,
                        message=exc.message,
                        processed_at=processed_at,
                        screenshot_path=exc.screenshot_path,
                    )
                    results.append(result)
                    self._emit_result(result)
                    self._sleep_after_task()
                    continue
                except Exception as exc:
                    self._log(f"FAILED index={index}/{total} row={task.row_number} status=failed message={exc}")
                    result = TaskResult.failure(task, str(exc), processed_at)
                    results.append(result)
                    self._emit_result(result)
                    self._sleep_after_task()
                    continue
                self._log(f"SUCCESS index={index}/{total} row={task.row_number} status=success")
                result = TaskResult.success(task, processed_at, screenshot_path="")
                results.append(result)
                self._emit_result(result)
                self._sleep_after_task()
        finally:
            close = getattr(self._automation, "close", None)
            if callable(close):
                close()
        return results

    def _log(self, message: str) -> None:
        if self._logger is not None:
            self._logger(message)

    def _emit_result(self, result: TaskResult) -> None:
        if self._on_result is not None:
            self._on_result(result)

    def _sleep_after_task(self) -> None:
        delay = getattr(self._automation, "request_delay_seconds", 0.0)
        if delay and delay > 0:
            self._sleep(delay)
