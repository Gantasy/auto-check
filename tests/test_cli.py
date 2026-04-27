import os
from pathlib import Path


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
            "--profile-directory",
            "Profile 2",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "out.csv").exists()
    assert captured["user_data_dir"] == r"C:\Users\tester\AppData\Local\codecheck-shield\chrome-profile"
    assert captured["profile_directory"] == "Profile 2"
    assert captured["browser_mode"] == "isolated-profile"
    assert captured["cdp_url"] == "http://127.0.0.1:9222"


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
