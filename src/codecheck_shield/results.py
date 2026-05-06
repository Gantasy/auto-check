from __future__ import annotations

import csv
from pathlib import Path

from codecheck_shield.models import TaskInput, TaskResult

RESULT_COLUMNS = ["run_status", "run_message", "processed_at", "used_reason", "screenshot_path"]


class ResultsCsvWriter:
    def __init__(self, output_path: Path | str, tasks: list[TaskInput]) -> None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.path = destination
        self._fieldnames = _fieldnames_from_tasks(tasks)
        self._handle = destination.open("w", encoding="utf-8-sig", newline="")
        self._writer = csv.DictWriter(self._handle, fieldnames=self._fieldnames)
        self._writer.writeheader()
        self._handle.flush()

    def write_result(self, result: TaskResult) -> None:
        row = dict(result.task.raw)
        row.update(
            {
                "run_status": result.status,
                "run_message": result.message,
                "processed_at": result.processed_at,
                "used_reason": result.task.reason,
                "screenshot_path": result.screenshot_path,
            }
        )
        self._writer.writerow(row)
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


def write_results_csv(results: list[TaskResult], output_path: Path | str) -> Path:
    writer = ResultsCsvWriter(output_path, [result.task for result in results])
    try:
        for result in results:
            writer.write_result(result)
    finally:
        writer.close()
    return writer.path


def write_retry_tasks_csv(tasks: list[TaskInput], output_path: Path | str) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _raw_fieldnames_from_tasks(tasks)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks:
            writer.writerow(dict(task.raw))
    return destination


def _fieldnames(results: list[TaskResult]) -> list[str]:
    return _fieldnames_from_tasks([result.task for result in results])


def _fieldnames_from_tasks(tasks: list[TaskInput]) -> list[str]:
    seen = _raw_fieldnames_from_tasks(tasks)
    return seen + [column for column in RESULT_COLUMNS if column not in seen]


def _raw_fieldnames_from_tasks(tasks: list[TaskInput]) -> list[str]:
    seen: list[str] = []
    for task in tasks:
        for key in task.raw:
            if key not in seen:
                seen.append(key)
    return seen
