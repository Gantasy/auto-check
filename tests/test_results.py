from pathlib import Path


def test_write_results_appends_execution_columns(tmp_path: Path) -> None:
    from codecheck_shield.models import TaskInput, TaskResult
    from codecheck_shield.results import write_results_csv

    input_row = TaskInput(
        row_number=2,
        url="https://example.test/1",
        reason="评审可屏蔽",
        raw={"详情链接": "https://example.test/1", "负责人": "alice"},
    )
    result = TaskResult.success(
        task=input_row,
        processed_at="2026-04-25T18:00:00+08:00",
        screenshot_path="",
    )

    output_path = write_results_csv([result], tmp_path / "results.csv")
    content = output_path.read_text(encoding="utf-8")

    assert "run_status" in content
    assert "processed_at" in content
    assert "success" in content
    assert "alice" in content


def test_results_writer_appends_rows_incrementally(tmp_path: Path) -> None:
    from codecheck_shield.models import TaskInput, TaskResult
    from codecheck_shield.results import ResultsCsvWriter

    first_task = TaskInput(
        row_number=2,
        url="https://example.test/1",
        reason="评审可屏蔽",
        raw={"详情链接": "https://example.test/1", "负责人": "alice"},
    )
    second_task = TaskInput(
        row_number=3,
        url="https://example.test/2",
        reason="人工确认可屏蔽",
        raw={"详情链接": "https://example.test/2", "负责人": "bob"},
    )

    writer = ResultsCsvWriter(tmp_path / "results.csv", [first_task, second_task])
    try:
        writer.write_result(
            TaskResult.success(
                task=first_task,
                processed_at="2026-04-25T18:00:00+08:00",
                screenshot_path="",
            )
        )
        first_snapshot = writer.path.read_text(encoding="utf-8")
        assert "https://example.test/1" in first_snapshot
        assert "https://example.test/2" not in first_snapshot

        writer.write_result(
            TaskResult.failure(
                task=second_task,
                message="backend rejected",
                processed_at="2026-04-25T18:01:00+08:00",
            )
        )
    finally:
        writer.close()

    content = writer.path.read_text(encoding="utf-8")
    assert content.count("run_status") == 1
    assert "https://example.test/1" in content
    assert "https://example.test/2" in content
    assert "backend rejected" in content
