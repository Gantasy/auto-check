import os
from pathlib import Path

CODECHECK_TEST_ORIGIN = "https://codecheck.cn-north-4.example.invalid"


def test_setup_subcommand_writes_requests_config_from_curl_file(tmp_path: Path) -> None:
    import json

    import codecheck_shield.cli as cli

    config_path = tmp_path / "codecheck-shield.config.json"
    curl_path = tmp_path / "request.curl"
    curl_path.write_text(
        (
            f'curl "{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect/issue-status?_=1777280163578" '
            '-H "AgencyId: agency-1" '
            '-H "cftk: token-1" '
            '-b "SID=abc; SessionID=xyz" '
            '--data-raw "{\\"platform\\":\\"clouddragon\\",\\"operator\\":\\"Gitee\\"}"'
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "setup",
            "--from-curl-file",
            str(curl_path),
            "--config",
            str(config_path),
        ]
    )

    assert exit_code == 0
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["mode"] == "requests"
    assert saved["requests"]["cookie"] == "SID=abc; SessionID=xyz"
    assert saved["requests"]["agency_id"] == "agency-1"
    assert saved["requests"]["cftk"] == "token-1"


def test_run_subcommand_uses_saved_requests_config(tmp_path: Path, monkeypatch) -> None:
    import json

    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    config_path = tmp_path / "codecheck-shield.config.json"
    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "requests",
                "default_reason": "人工确认可屏蔽",
                "requests": {
                    "cookie": "SID=abc",
                    "agency_id": "agency-1",
                    "cftk": "token-1",
                    "operator": "Gitee",
                    "platform": "clouddragon",
                },
                "windows_desktop": {
                    "calibration_file": "./desktop-calibration.json",
                    "page_load_seconds": 3.0,
                    "action_delay_seconds": 0.5,
                },
                "output": {"default_suffix": ".results.csv"},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, str | None] = {}

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(
        cli,
        "build_automation",
        lambda args: captured.update(
            {
                "browser_mode": args.browser_mode,
                "request_cookie": args.request_cookie,
                "agency_id": args.agency_id,
                "cftk": args.cftk,
                "default_reason": args.default_reason,
            }
        )
        or object(),
    )
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.success(
                            task=tasks[0],
                            processed_at="2026-04-27T14:00:00+08:00",
                            screenshot_path="",
                        )
                    ]
                )
            },
        )(),
    )

    exit_code = cli.main(
        [
            "run",
            str(input_path),
            "--config",
            str(config_path),
            "--output",
            str(tmp_path / "out.csv"),
        ]
    )

    assert exit_code == 0
    assert captured["browser_mode"] == "requests"
    assert captured["request_cookie"] == "SID=abc"
    assert captured["agency_id"] == "agency-1"
    assert captured["cftk"] == "token-1"
    assert captured["default_reason"] == "人工确认可屏蔽"


def test_run_subcommand_uses_default_config_file_from_cwd(tmp_path: Path, monkeypatch) -> None:
    import json

    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    config_path = tmp_path / "codecheck-shield.config.json"
    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "requests",
                "default_reason": "人工确认可屏蔽",
                "requests": {
                    "cookie": "SID=abc",
                    "agency_id": "agency-1",
                    "cftk": "token-1",
                    "operator": "Gitee",
                    "platform": "clouddragon",
                },
                "windows_desktop": {
                    "calibration_file": "./desktop-calibration.json",
                    "page_load_seconds": 3.0,
                    "action_delay_seconds": 0.5,
                },
                "output": {"default_suffix": ".results.csv"},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, str | None] = {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(
        cli,
        "build_automation",
        lambda args: captured.update(
            {
                "browser_mode": args.browser_mode,
                "request_cookie": args.request_cookie,
                "agency_id": args.agency_id,
                "cftk": args.cftk,
            }
        )
        or object(),
    )
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.success(
                            task=tasks[0],
                            processed_at="2026-04-27T14:00:00+08:00",
                            screenshot_path="",
                        )
                    ]
                )
            },
        )(),
    )

    exit_code = cli.main(
        [
            "run",
            str(input_path),
            "--output",
            str(tmp_path / "out.csv"),
        ]
    )

    assert exit_code == 0
    assert captured["browser_mode"] == "requests"
    assert captured["request_cookie"] == "SID=abc"
    assert captured["agency_id"] == "agency-1"
    assert captured["cftk"] == "token-1"


def test_default_user_data_dir_uses_windows_chrome_profile() -> None:
    import codecheck_shield.cli as cli

    path = cli.default_user_data_dir(
        browser_channel="chrome",
        system="Windows",
        env={"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"},
    )

    assert str(path) == r"C:\Users\tester\AppData\Local\codecheck-shield\chrome-profile"


def test_cli_writes_output_path(tmp_path: Path, monkeypatch) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(
        cli,
        "build_automation",
        lambda args: captured.update(
            {
                "user_data_dir": args.user_data_dir,
                "profile_directory": args.profile_directory,
                "browser_mode": args.browser_mode,
                "cdp_url": args.cdp_url,
                "request_cookie": args.request_cookie,
                "agency_id": args.agency_id,
                "cftk": args.cftk,
            }
        )
        or object(),
    )
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.success(
                            task=tasks[0],
                            processed_at="2026-04-25T18:00:00+08:00",
                            screenshot_path="",
                        )
                    ]
                )
            },
        )(),
    )
    monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli.os, "environ", {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"})

    exit_code = cli.main(
        [
            str(input_path),
            "--output",
            str(tmp_path / "out.csv"),
            "--request-cookie",
            "SID=abc",
            "--agency-id",
            "agency-1",
            "--cftk",
            "token-1",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "out.csv").exists()
    assert captured["user_data_dir"] is None
    assert captured["profile_directory"] is None
    assert captured["browser_mode"] == "requests"
    assert captured["cdp_url"] == "http://127.0.0.1:9222"
    assert captured["request_cookie"] == "SID=abc"
    assert captured["agency_id"] == "agency-1"
    assert captured["cftk"] == "token-1"


def test_cli_returns_1_when_no_tasks_found(tmp_path: Path, monkeypatch, capsys) -> None:
    import codecheck_shield.cli as cli

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\n", encoding="utf-8")

    monkeypatch.setattr(cli, "load_tasks", lambda path, default_reason: [])

    exit_code = cli.main([str(input_path), "--output", str(tmp_path / "out.csv")])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "No tasks found" in output
    assert not (tmp_path / "out.csv").exists()


def test_cli_writes_realtime_log_file(tmp_path: Path, monkeypatch, capsys) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput

    input_path = tmp_path / "issues.csv"
    output_path = tmp_path / "out.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(cli, "build_automation", lambda args: type("Automation", (), {"shield_issue": staticmethod(lambda url, reason: None)})())

    exit_code = cli.main(
        [
            str(input_path),
            "--output",
            str(output_path),
            "--request-cookie",
            "SID=abc",
            "--agency-id",
            "agency-1",
            "--cftk",
            "token-1",
        ]
    )

    output = capsys.readouterr().out
    log_path = output_path.with_suffix(".log")

    assert exit_code == 0
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "START index=1/1 row=2 url=https://example.test/1" in log_text
    assert "SUCCESS index=1/1 row=2 status=success" in log_text
    assert "START index=1/1 row=2 url=https://example.test/1" in output


def test_cli_logs_skipped_rows_to_terminal_and_log_file(tmp_path: Path, monkeypatch, capsys) -> None:
    import codecheck_shield.cli as cli

    input_path = tmp_path / "issues.csv"
    output_path = tmp_path / "out.csv"
    input_path.write_text(
        (
            "详情链接,处理方式（待屏蔽/修改）,屏蔽描述\n"
            "https://example.test/1,待屏蔽,已经是const\n"
            "https://example.test/2,修改,应当修复\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "build_automation", lambda args: type("Automation", (), {"shield_issue": staticmethod(lambda url, reason: None)})())

    exit_code = cli.main(
        [
            str(input_path),
            "--output",
            str(output_path),
            "--request-cookie",
            "SID=abc",
            "--agency-id",
            "agency-1",
            "--cftk",
            "token-1",
        ]
    )

    output = capsys.readouterr().out
    log_path = output_path.with_suffix(".log")
    log_text = log_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert "SKIP row=3 reason=处理方式（待屏蔽/修改）=修改" in output
    assert "SKIP row=3 reason=处理方式（待屏蔽/修改）=修改" in log_text


def test_cli_returns_1_and_prints_failure_summary(tmp_path: Path, monkeypatch, capsys) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(cli, "build_automation", lambda args: object())
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.failure(
                            task=tasks[0],
                            message="Playwright is not installed",
                            processed_at="2026-04-27T10:00:00+08:00",
                        )
                    ]
                )
            },
        )(),
    )

    exit_code = cli.main([str(input_path), "--output", str(tmp_path / "out.csv")])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Completed with failures: 1/1" in output
    assert "https://example.test/1" in output
    assert "Playwright is not installed" in output
    assert str(tmp_path / "out.csv") in output


def test_cli_rejects_primary_windows_chrome_user_data_dir(tmp_path: Path, monkeypatch, capsys) -> None:
    import codecheck_shield.cli as cli

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli.os, "environ", {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"})

    exit_code = cli.main(
        [
            str(input_path),
            "--browser-mode",
            "isolated-profile",
            "--user-data-dir",
            r"C:\Users\tester\AppData\Local\Google\Chrome\User Data",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "not supported by Playwright" in output
    assert "codecheck-shield\\chrome-profile" in output


def test_cli_attach_cdp_mode_skips_user_data_dir_checks(tmp_path: Path, monkeypatch) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    captured: dict[str, str | None] = {}

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(
        cli,
        "build_automation",
        lambda args: captured.update(
            {
                "browser_mode": args.browser_mode,
                "cdp_url": args.cdp_url,
                "user_data_dir": args.user_data_dir,
            }
        )
        or object(),
    )
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.success(
                            task=tasks[0],
                            processed_at="2026-04-27T12:00:00+08:00",
                            screenshot_path="",
                        )
                    ]
                )
            },
        )(),
    )
    monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cli.os, "environ", {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"})

    exit_code = cli.main(
        [
            str(input_path),
            "--output",
            str(tmp_path / "out.csv"),
            "--browser-mode",
            "attach-cdp",
            "--cdp-url",
            "http://127.0.0.1:9333",
        ]
    )

    assert exit_code == 0
    assert captured["browser_mode"] == "attach-cdp"
    assert captured["cdp_url"] == "http://127.0.0.1:9333"
    assert captured["user_data_dir"] is None


def test_cli_windows_desktop_mode_passes_calibration_file(tmp_path: Path, monkeypatch) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    input_path = tmp_path / "issues.csv"
    calibration_path = tmp_path / "desktop-calibration.json"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    captured: dict[str, str | None] = {}

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(
        cli,
        "build_automation",
        lambda args: captured.update(
            {
                "browser_mode": args.browser_mode,
                "desktop_calibration_file": args.desktop_calibration_file,
            }
        )
        or object(),
    )
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.success(
                            task=tasks[0],
                            processed_at="2026-04-27T12:30:00+08:00",
                            screenshot_path="",
                        )
                    ]
                )
            },
        )(),
    )

    exit_code = cli.main(
        [
            str(input_path),
            "--output",
            str(tmp_path / "out.csv"),
            "--browser-mode",
            "windows-desktop",
            "--desktop-calibration-file",
            str(calibration_path),
        ]
    )

    assert exit_code == 0
    assert captured["browser_mode"] == "windows-desktop"
    assert captured["desktop_calibration_file"] == str(calibration_path)


def test_cli_passes_default_reason_to_load_tasks(tmp_path: Path, monkeypatch) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    captured: dict[str, str | None] = {}

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path, default_reason: captured.update(
            {
                "input_path": str(path),
                "default_reason": default_reason,
            }
        )
        or [TaskInput(row_number=2, url="https://example.test/1", reason=default_reason, raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(cli, "build_automation", lambda args: object())
    monkeypatch.setattr(
        cli,
        "BatchRunner",
        lambda automation: type(
            "Runner",
            (),
            {
                "run": staticmethod(
                    lambda tasks: [
                        TaskResult.success(
                            task=tasks[0],
                            processed_at="2026-04-27T13:00:00+08:00",
                            screenshot_path="",
                        )
                    ]
                )
            },
        )(),
    )

    exit_code = cli.main(
        [
            str(input_path),
            "--output",
            str(tmp_path / "out.csv"),
            "--default-reason",
            "人工确认可屏蔽",
        ]
    )

    assert exit_code == 0
    assert captured["input_path"] == str(input_path)
    assert captured["default_reason"] == "人工确认可屏蔽"


def test_cli_calibrate_writes_desktop_config_without_input_file(tmp_path: Path, monkeypatch) -> None:
    import codecheck_shield.cli as cli

    calibration_path = tmp_path / "desktop-calibration.json"
    captured: dict[str, str | None] = {}

    def fake_run_desktop_calibration(destination):
        captured["destination"] = str(destination)
        return 0

    monkeypatch.setattr(
        cli,
        "run_desktop_calibration",
        fake_run_desktop_calibration,
    )

    exit_code = cli.main(
        [
            "--calibrate-desktop",
            "--desktop-calibration-file",
            str(calibration_path),
        ]
    )

    assert exit_code == 0
    assert captured["destination"] == str(calibration_path)
