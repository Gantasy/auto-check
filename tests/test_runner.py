def test_runner_executes_ignore_flow_in_order() -> None:
    from codecheck_shield.models import TaskInput
    from codecheck_shield.runner import BatchRunner

    calls: list[tuple[str, str]] = []

    class FakeAutomation:
        def shield_issue(self, url: str, reason: str) -> None:
            calls.append((url, reason))

    task = TaskInput(
        row_number=2,
        url="https://example.test/1",
        reason="评审可屏蔽",
        raw={"详情链接": "https://example.test/1"},
    )

    runner = BatchRunner(automation=FakeAutomation(), clock=lambda: "2026-04-25T18:00:00+08:00")

    results = runner.run([task])

    assert calls == [("https://example.test/1", "评审可屏蔽")]
    assert results[0].status == "success"


def test_runner_records_failure_and_continues() -> None:
    from codecheck_shield.models import TaskInput
    from codecheck_shield.runner import BatchRunner

    class FakeAutomation:
        def shield_issue(self, url: str, reason: str) -> None:
            if url.endswith("/1"):
                raise RuntimeError("missing status button")

    tasks = [
        TaskInput(row_number=2, url="https://example.test/1", reason="评审可屏蔽", raw={"详情链接": "https://example.test/1"}),
        TaskInput(row_number=3, url="https://example.test/2", reason="评审可屏蔽", raw={"详情链接": "https://example.test/2"}),
    ]

    runner = BatchRunner(automation=FakeAutomation(), clock=lambda: "2026-04-25T18:00:00+08:00")

    results = runner.run(tasks)

    assert [result.status for result in results] == ["failed", "success"]
    assert "missing status button" in results[0].message


def test_runner_uses_failure_screenshot_and_closes_automation() -> None:
    from codecheck_shield.errors import AutomationFailure
    from codecheck_shield.models import TaskInput
    from codecheck_shield.runner import BatchRunner

    closed: list[bool] = []

    class FakeAutomation:
        def shield_issue(self, url: str, reason: str) -> None:
            raise AutomationFailure("failed_confirm", "dialog confirm failed", "artifacts/failed.png")

        def close(self) -> None:
            closed.append(True)

    task = TaskInput(
        row_number=2,
        url="https://example.test/1",
        reason="评审可屏蔽",
        raw={"详情链接": "https://example.test/1"},
    )

    runner = BatchRunner(automation=FakeAutomation(), clock=lambda: "2026-04-25T18:00:00+08:00")

    results = runner.run([task])

    assert results[0].status == "failed_confirm"
    assert results[0].screenshot_path == "artifacts/failed.png"
    assert closed == [True]


def test_runner_emits_start_success_and_failure_logs() -> None:
    from codecheck_shield.errors import AutomationFailure
    from codecheck_shield.models import TaskInput
    from codecheck_shield.runner import BatchRunner

    messages: list[str] = []

    class FakeAutomation:
        def shield_issue(self, url: str, reason: str) -> None:
            if url.endswith("/2"):
                raise AutomationFailure("failed_request", "backend rejected")

    tasks = [
        TaskInput(row_number=2, url="https://example.test/1", reason="评审可屏蔽", raw={"详情链接": "https://example.test/1"}),
        TaskInput(row_number=3, url="https://example.test/2", reason="评审可屏蔽", raw={"详情链接": "https://example.test/2"}),
    ]

    runner = BatchRunner(
        automation=FakeAutomation(),
        clock=lambda: "2026-04-25T18:00:00+08:00",
        logger=messages.append,
    )

    runner.run(tasks)

    assert messages == [
        "START index=1/2 row=2 url=https://example.test/1",
        "SUCCESS index=1/2 row=2 status=success",
        "START index=2/2 row=3 url=https://example.test/2",
        "FAILED index=2/2 row=3 status=failed_request message=backend rejected",
    ]


def test_runner_sleeps_between_requests_tasks_and_streams_results() -> None:
    from codecheck_shield.models import TaskInput
    from codecheck_shield.runner import BatchRunner

    seen_results: list[tuple[int, str]] = []
    sleep_calls: list[float] = []

    class FakeRequestsAutomation:
        request_delay_seconds = 0.5

        def shield_issue(self, url: str, reason: str) -> None:
            return None

    tasks = [
        TaskInput(row_number=2, url="https://example.test/1", reason="评审可屏蔽", raw={"详情链接": "https://example.test/1"}),
        TaskInput(row_number=3, url="https://example.test/2", reason="评审可屏蔽", raw={"详情链接": "https://example.test/2"}),
    ]

    runner = BatchRunner(
        automation=FakeRequestsAutomation(),
        clock=lambda: "2026-04-25T18:00:00+08:00",
        on_result=lambda result: seen_results.append((result.task.row_number, result.status)),
        sleeper=sleep_calls.append,
    )

    results = runner.run(tasks)

    assert [result.status for result in results] == ["success", "success"]
    assert seen_results == [(2, "success"), (3, "success")]
    assert sleep_calls == [0.5, 0.5]
