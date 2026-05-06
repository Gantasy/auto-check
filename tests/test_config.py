from pathlib import Path


def test_save_and_load_app_config_roundtrip(tmp_path: Path) -> None:
    from codecheck_shield.config import AppConfig, OutputConfig, RequestAuthConfig, WindowsDesktopConfig, load_config, save_config

    path = tmp_path / "codecheck-shield.config.json"
    config = AppConfig(
        version=1,
        mode="requests",
        default_reason="人工确认可屏蔽",
        requests=RequestAuthConfig(
            cookie="SID=abc",
            agency_id="agency-1",
            cftk="token-1",
            operator="Gitee",
            platform="clouddragon",
        ),
        windows_desktop=WindowsDesktopConfig(
            calibration_file="./desktop-calibration.json",
            page_load_seconds=4.0,
            action_delay_seconds=0.8,
        ),
        output=OutputConfig(default_suffix=".results.csv"),
    )

    save_config(path, config)
    loaded = load_config(path)

    assert loaded == config
