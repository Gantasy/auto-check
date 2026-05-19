from pathlib import Path

CODECHECK_TEST_ORIGIN = "https://codecheck.cn-north-4.example.invalid"
REQUEST_TEST_PROJECT_ID = "11111111111111111111111111111111"
REQUEST_TEST_TASK_ID = "22222222222222222222222222222222"
REQUEST_TEST_MERGE_KEY = "33333333333333333333333333333333"
REQUEST_TEST_MERGE_ID = "621"
REQUEST_TEST_JOB_ID = "56fca83bf2e243aab404513bfd382611"
REQUEST_TEST_TASK_WITH_PREFIX_ID = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
REQUEST_TEST_PROJECT_URL = (
    f"{CODECHECK_TEST_ORIGIN}/codechecknew/project/{REQUEST_TEST_PROJECT_ID}"
    f"/codecheck/task/{REQUEST_TEST_TASK_ID}"
)
REQUEST_TEST_DEFECT_URL = (
    f"{REQUEST_TEST_PROJECT_URL}/defect/{REQUEST_TEST_MERGE_KEY}"
    f"?mergeId={REQUEST_TEST_MERGE_ID}&jobId={REQUEST_TEST_JOB_ID}&defectIndex=1"
)
REQUEST_TEST_TASK_URL = (
    f"{REQUEST_TEST_PROJECT_URL}/defects?jobId={REQUEST_TEST_JOB_ID}"
    f"&mergeId={REQUEST_TEST_MERGE_ID}&delayStatus=undefined&approver=undefined"
)
REQUEST_TEST_PREFIXED_DEFECT_URL = (
    f"{CODECHECK_TEST_ORIGIN}/codechecknew/project/{REQUEST_TEST_PROJECT_ID}/codecheck/task/green/"
    f"{REQUEST_TEST_TASK_WITH_PREFIX_ID}/defect/{REQUEST_TEST_MERGE_KEY}"
    f"?mergeId={REQUEST_TEST_MERGE_ID}&jobId={REQUEST_TEST_JOB_ID}&defectIndex=1"
)
REQUEST_TEST_PREFIXED_CANONICAL_DEFECT_URL = (
    f"{CODECHECK_TEST_ORIGIN}/codechecknew/project/{REQUEST_TEST_PROJECT_ID}/codecheck/task/"
    f"{REQUEST_TEST_TASK_WITH_PREFIX_ID}/defect/{REQUEST_TEST_MERGE_KEY}"
    f"?mergeId={REQUEST_TEST_MERGE_ID}&jobId={REQUEST_TEST_JOB_ID}&defectIndex=1"
)
REQUEST_TEST_PREFIXED_CANONICAL_TASK_URL = (
    f"{CODECHECK_TEST_ORIGIN}/codechecknew/project/{REQUEST_TEST_PROJECT_ID}/codecheck/task/"
    f"{REQUEST_TEST_TASK_WITH_PREFIX_ID}/defects?jobId={REQUEST_TEST_JOB_ID}"
    f"&mergeId={REQUEST_TEST_MERGE_ID}&delayStatus=undefined&approver=undefined"
)


def test_close_stops_started_playwright_instead_of_manager() -> None:
    from codecheck_shield.automation import BrowserSettings, PlaywrightAutomation

    class FakeContext:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeManager:
        pass

    class FakePlaywright:
        def __init__(self) -> None:
            self.stopped = False

        def stop(self) -> None:
            self.stopped = True

    automation = PlaywrightAutomation(
        BrowserSettings(
            browser_channel="chrome",
            user_data_dir=Path("/tmp/profile"),
            profile_directory=None,
            headless=True,
            slow_mo_ms=0,
            screenshot_dir=Path("/tmp/screenshots"),
        )
    )
    context = FakeContext()
    playwright = FakePlaywright()
    automation._context = context
    automation._playwright_manager = FakeManager()
    automation._playwright = playwright

    automation.close()

    assert context.closed is True
    assert playwright.stopped is True


def test_build_automation_returns_requests_mode_when_requested() -> None:
    from types import SimpleNamespace

    from codecheck_shield.automation import RequestsAutomation, build_automation

    automation = build_automation(
        SimpleNamespace(
            browser_mode="requests",
            request_cookie="SID=abc; SessionID=xyz",
            request_cookie_file=None,
            agency_id="agency-1",
            cftk="token-1",
            request_operator="Gitee",
            request_platform="clouddragon",
            browser_channel="chrome",
            user_data_dir=None,
            profile_directory=None,
            headless=False,
            slow_mo_ms=0,
            cdp_url="http://127.0.0.1:9333",
            screenshot_dir="./artifacts/screenshots",
            desktop_calibration_file="./desktop-calibration.json",
            page_load_seconds=0.0,
            action_delay_seconds=0.0,
        )
    )

    assert isinstance(automation, RequestsAutomation)


def test_build_automation_returns_cdp_mode_when_requested() -> None:
    from types import SimpleNamespace

    from codecheck_shield.automation import CdpAttachAutomation, build_automation

    automation = build_automation(
        SimpleNamespace(
            browser_mode="attach-cdp",
            cdp_url="http://127.0.0.1:9333",
            browser_channel="chrome",
            user_data_dir=None,
            profile_directory=None,
            headless=False,
            slow_mo_ms=0,
            screenshot_dir="./artifacts/screenshots",
        )
    )

    assert isinstance(automation, CdpAttachAutomation)


def test_requests_automation_builds_expected_request() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation

    captured: dict[str, object] = {"requests": []}

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return b'{"status":"success","result":"\xe4\xbf\xae\xe6\x94\xb9\xe6\x88\x90\xe5\x8a\x9f"}'

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps({"defectVo": {"comment": "评审可屏蔽"}}, ensure_ascii=False).encode("utf-8")

    def fake_sender(request):
        captured["requests"].append(
            {
                "method": request.get_method(),
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": request.data.decode("utf-8") if request.data else "",
            }
        )
        if request.get_method() == "POST":
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=lambda: 1777280163578,
    )

    automation.shield_issue(
        REQUEST_TEST_DEFECT_URL,
        "评审可屏蔽",
    )

    post_request = captured["requests"][0]
    get_request = captured["requests"][1]
    assert post_request["url"] == f"{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect/issue-status?_=1777280163578"
    assert post_request["headers"]["Agencyid"] == "agency-1"
    assert post_request["headers"]["Cookie"] == "SID=abc; SessionID=xyz"
    assert post_request["headers"]["Cftk"] == "token-1"
    payload = json.loads(post_request["body"])
    assert payload == {
        "taskId": REQUEST_TEST_TASK_ID,
        "mergeId": REQUEST_TEST_MERGE_ID,
        "jobId": REQUEST_TEST_JOB_ID,
        "status": 5,
        "comment": "评审可屏蔽",
        "mergeKey": REQUEST_TEST_MERGE_KEY,
        "espaceUrl": REQUEST_TEST_TASK_URL,
        "platform": "clouddragon",
        "operator": "Gitee",
    }
    assert get_request["url"] == (
        f"{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect?defect_index=1&task_id={REQUEST_TEST_TASK_ID}"
        f"&merge_id={REQUEST_TEST_MERGE_ID}&job_id={REQUEST_TEST_JOB_ID}"
        f"&merge_key={REQUEST_TEST_MERGE_KEY}&_=1777280163578"
    )


def test_requests_automation_fails_when_backend_json_is_not_success() -> None:
    from codecheck_shield.automation import RequestSettings, RequestsAutomation
    from codecheck_shield.errors import AutomationFailure

    class FakeResponse:
        status = 200

        def read(self) -> bytes:
            return b'{"status":"error","result":"\xe6\x93\x8d\xe4\xbd\x9c\xe5\xa4\xb1\xe8\xb4\xa5","message":"permission denied"}'

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=lambda request: FakeResponse(),
        time_ms=lambda: 1777280163578,
    )

    try:
        automation.shield_issue(
            REQUEST_TEST_DEFECT_URL,
            "评审可屏蔽",
        )
    except AutomationFailure as exc:
        assert exc.status == "failed_request"
        assert "permission denied" in exc.message
    else:
        raise AssertionError("Expected AutomationFailure for non-success backend response")


def test_parse_defect_url_supports_task_status_segment() -> None:
    from codecheck_shield.automation import _parse_defect_url

    parsed = _parse_defect_url(REQUEST_TEST_PREFIXED_DEFECT_URL)

    assert parsed["origin"] == CODECHECK_TEST_ORIGIN
    assert parsed["project_id"] == REQUEST_TEST_PROJECT_ID
    assert parsed["task_id"] == REQUEST_TEST_TASK_WITH_PREFIX_ID
    assert parsed["merge_id"] == REQUEST_TEST_MERGE_ID
    assert parsed["job_id"] == REQUEST_TEST_JOB_ID
    assert parsed["merge_key"] == REQUEST_TEST_MERGE_KEY
    assert parsed["defect_index"] == "1"
    assert parsed["region"] == "cn-north-4"
    assert parsed["task_path_prefix"] == "green"
    assert parsed["canonical_defect_url"] == REQUEST_TEST_PREFIXED_CANONICAL_DEFECT_URL
    assert parsed["canonical_task_url"] == REQUEST_TEST_PREFIXED_CANONICAL_TASK_URL


def test_requests_automation_uses_task_status_segment_in_espace_url() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation

    captured: dict[str, object] = {}

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return b'{"status":"success","result":"\xe4\xbf\xae\xe6\x94\xb9\xe6\x88\x90\xe5\x8a\x9f"}'

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return b'{"defectVo":{"comment":"\xe8\xaf\x84\xe5\xae\xa1\xe5\x8f\xaf\xe5\xb1\x8f\xe8\x94\xbd"}}'

    def fake_sender(request):
        if request.get_method() == "POST":
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data.decode("utf-8")
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=lambda: 1777280163578,
    )

    automation.shield_issue(
        REQUEST_TEST_PREFIXED_DEFECT_URL,
        "评审可屏蔽",
    )

    payload = json.loads(captured["body"])
    assert payload["taskId"] == REQUEST_TEST_TASK_WITH_PREFIX_ID
    assert payload["espaceUrl"] == REQUEST_TEST_PREFIXED_CANONICAL_TASK_URL
    assert captured["headers"]["Referer"] == REQUEST_TEST_PREFIXED_CANONICAL_DEFECT_URL


def test_requests_automation_verifies_with_follow_up_get_when_post_body_empty() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation

    requests_seen: list[tuple[str, str, dict[str, str]]] = []

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return b""

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "merge_key": REQUEST_TEST_MERGE_KEY,
                    "defectVo": {"comment": "评审可屏蔽"},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_sender(request):
        method = request.get_method()
        requests_seen.append((method, request.full_url, dict(request.header_items())))
        if method == "POST":
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=iter([1777424973773, 1777424973999]).__next__,
    )

    automation.shield_issue(
        REQUEST_TEST_PREFIXED_DEFECT_URL,
        "评审可屏蔽",
    )

    assert [item[0] for item in requests_seen] == ["POST", "GET"]
    assert requests_seen[1][1] == (
        f"{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect?defect_index=1&task_id={REQUEST_TEST_TASK_WITH_PREFIX_ID}"
        f"&merge_id={REQUEST_TEST_MERGE_ID}&job_id={REQUEST_TEST_JOB_ID}"
        f"&merge_key={REQUEST_TEST_MERGE_KEY}&_=1777424973999"
    )
    assert requests_seen[1][2]["Referer"] == REQUEST_TEST_PREFIXED_CANONICAL_DEFECT_URL


def test_requests_automation_includes_merge_and_job_ids_when_verifying() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation

    requests_seen: list[tuple[str, str, str]] = []

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return b""

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps({"defectVo": {"comment": "评审可屏蔽"}}, ensure_ascii=False).encode("utf-8")

    def fake_sender(request):
        requests_seen.append(
            (
                request.get_method(),
                request.full_url,
                request.data.decode("utf-8") if request.data else "",
            )
        )
        if request.get_method() == "POST":
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=iter([1777424973773, 1777424973999]).__next__,
    )

    automation.shield_issue(REQUEST_TEST_DEFECT_URL, "评审可屏蔽")

    post_payload = json.loads(requests_seen[0][2])
    assert post_payload["mergeId"] == REQUEST_TEST_MERGE_ID
    assert post_payload["jobId"] == REQUEST_TEST_JOB_ID
    assert requests_seen[1][1] == (
        f"{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect?defect_index=1&task_id={REQUEST_TEST_TASK_ID}"
        f"&merge_id={REQUEST_TEST_MERGE_ID}&job_id={REQUEST_TEST_JOB_ID}"
        f"&merge_key={REQUEST_TEST_MERGE_KEY}&_=1777424973999"
    )


def test_requests_automation_classifies_already_shielded_when_verify_shows_status_5() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation
    from codecheck_shield.errors import AutomationFailure

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "result": None,
                    "status": "error",
                    "error": {
                        "code": "CC.00070324.400",
                        "message": "告警状态修改失败",
                        "reason": "全部执行失败:\n【1 条告警状态修改不合法，本次不刷新】",
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8")

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "result": {
                        "defectStatus": "5",
                        "comment": "已有屏蔽理由",
                    },
                    "status": "success",
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_sender(request):
        if request.get_method() == "POST":
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=lambda: 1777280163578,
    )

    try:
        automation.shield_issue(REQUEST_TEST_DEFECT_URL, "评审可屏蔽")
    except AutomationFailure as exc:
        assert exc.status == "already_shielded"
        assert "already shielded" in exc.message
    else:
        raise AssertionError("Expected already_shielded classification")


def test_requests_automation_classifies_unreachable_page_when_defect_missing() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation
    from codecheck_shield.errors import AutomationFailure

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "result": None,
                    "status": "error",
                    "error": {
                        "code": "CC.00070324.400",
                        "message": "告警状态修改失败",
                        "reason": "全部执行失败:\n【1 条告警不能在数据库中找到】",
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8")

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "result": None,
                    "status": "error",
                    "error": {
                        "code": "CC.00070322.400",
                        "message": "告警信息查询异常",
                        "reason": "please ensure the last check contains this defect!",
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_sender(request):
        if request.get_method() == "POST":
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=lambda: 1777280163578,
    )

    try:
        automation.shield_issue(REQUEST_TEST_DEFECT_URL, "评审可屏蔽")
    except AutomationFailure as exc:
        assert exc.status == "unreachable_page"
        assert "not found" in exc.message
    else:
        raise AssertionError("Expected unreachable_page classification")


def test_requests_automation_does_not_treat_defect_content_not_found_as_unreachable_page() -> None:
    import json

    from codecheck_shield.automation import RequestSettings, RequestsAutomation
    from codecheck_shield.errors import AutomationFailure

    class FakePostResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "result": None,
                    "status": "error",
                    "error": {
                        "code": "CC.00070324.400",
                        "message": "告警状态修改失败",
                        "reason": "全部执行失败:\n【1 条告警状态修改不合法，本次不刷新】",
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8")

    class FakeGetResponse:
        status = 200

        def read(self) -> bytes:
            return json.dumps(
                {
                    "result": {
                        "defectStatus": "5",
                        "occursInfo": [
                            {
                                "occurDescription": "'register/op_impl_registry.h' file not found",
                            }
                        ],
                    },
                    "status": "success",
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_sender(request):
        if request.get_method() == "POST":
            return FakePostResponse()
        return FakeGetResponse()

    automation = RequestsAutomation(
        RequestSettings(
            cookie="SID=abc; SessionID=xyz",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
            screenshot_dir=Path("/tmp/screenshots"),
        ),
        sender=fake_sender,
        time_ms=lambda: 1777280163578,
    )

    try:
        automation.shield_issue(REQUEST_TEST_DEFECT_URL, "评审可屏蔽")
    except AutomationFailure as exc:
        assert exc.status == "already_shielded"
    else:
        raise AssertionError("Expected already_shielded classification")
