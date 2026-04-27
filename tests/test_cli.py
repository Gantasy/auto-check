from pathlib import Path


def test_default_user_data_dir_uses_windows_chrome_profile() -> None:
    import codecheck_shield.cli as cli

    path = cli.default_user_data_dir(
        browser_channel="chrome",
        system="Windows",
        env={"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"},
    )

    assert str(path) == r"C:\Users\tester\AppData\Local\Google\Chrome\User Data"


def test_cli_writes_output_path(tmp_path: Path, monkeypatch) -> None:
    import codecheck_shield.cli as cli
    from codecheck_shield.models import TaskInput, TaskResult

    input_path = tmp_path / "issues.csv"
    input_path.write_text("详情链接\nhttps://example.test/1\n", encoding="utf-8")
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        cli,
        "load_tasks",
        lambda path: [TaskInput(row_number=2, url="https://example.test/1", reason="评审可屏蔽", raw={"详情链接": "https://example.test/1"})],
    )
    monkeypatch.setattr(
        cli,
        "build_automation",
        lambda args: captured.update(
            {
                "user_data_dir": args.user_data_dir,
                "profile_directory": args.profile_directory,
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
    monkeypatch.setattr(cli, "os", type("OS", (), {"environ": {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"}})())

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
    assert captured["user_data_dir"] == r"C:\Users\tester\AppData\Local\Google\Chrome\User Data"
    assert captured["profile_directory"] == "Profile 2"
