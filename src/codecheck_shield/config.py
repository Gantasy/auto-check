from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from codecheck_shield.models import DEFAULT_REASON


DEFAULT_CONFIG_FILE_NAME = "codecheck-shield.config.json"
DEFAULT_OUTPUT_SUFFIX = ".results.csv"
DEFAULT_DESKTOP_CALIBRATION_FILE = "./desktop-calibration.json"
DEFAULT_PAGE_LOAD_SECONDS = 3.0
DEFAULT_ACTION_DELAY_SECONDS = 0.5
DEFAULT_REQUEST_OPERATOR = "Gitee"
DEFAULT_REQUEST_PLATFORM = "clouddragon"


@dataclass(slots=True)
class RequestAuthConfig:
    cookie: str = ""
    agency_id: str = ""
    cftk: str = ""
    operator: str = DEFAULT_REQUEST_OPERATOR
    platform: str = DEFAULT_REQUEST_PLATFORM


@dataclass(slots=True)
class WindowsDesktopConfig:
    calibration_file: str = DEFAULT_DESKTOP_CALIBRATION_FILE
    page_load_seconds: float = DEFAULT_PAGE_LOAD_SECONDS
    action_delay_seconds: float = DEFAULT_ACTION_DELAY_SECONDS


@dataclass(slots=True)
class OutputConfig:
    default_suffix: str = DEFAULT_OUTPUT_SUFFIX


@dataclass(slots=True)
class AppConfig:
    version: int = 1
    mode: str = "requests"
    default_reason: str = DEFAULT_REASON
    requests: RequestAuthConfig | None = None
    windows_desktop: WindowsDesktopConfig | None = None
    output: OutputConfig | None = None


def default_config() -> AppConfig:
    return AppConfig(
        requests=RequestAuthConfig(),
        windows_desktop=WindowsDesktopConfig(),
        output=OutputConfig(),
    )


def load_config(path: str | Path) -> AppConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return AppConfig(
        version=raw.get("version", 1),
        mode=raw.get("mode", "requests"),
        default_reason=raw.get("default_reason", DEFAULT_REASON),
        requests=RequestAuthConfig(**raw.get("requests", {})),
        windows_desktop=WindowsDesktopConfig(**raw.get("windows_desktop", {})),
        output=OutputConfig(**raw.get("output", {})),
    )


def save_config(path: str | Path, config: AppConfig) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

