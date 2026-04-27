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
