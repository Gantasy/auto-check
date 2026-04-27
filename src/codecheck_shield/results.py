from __future__ import annotations

import csv
from pathlib import Path

from codecheck_shield.models import TaskResult

RESULT_COLUMNS = ["run_status", "run_message", "processed_at", "used_reason", "screenshot_path"]


def write_results_csv(results: list[TaskResult], output_path: Path | str) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = _fieldnames(results)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
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
            writer.writerow(row)
    return destination


def _fieldnames(results: list[TaskResult]) -> list[str]:
    seen: list[str] = []
    for result in results:
        for key in result.task.raw:
            if key not in seen:
                seen.append(key)
    return seen + [column for column in RESULT_COLUMNS if column not in seen]
