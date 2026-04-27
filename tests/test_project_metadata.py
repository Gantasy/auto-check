from __future__ import annotations

import tomllib
from pathlib import Path


def test_build_system_declares_wheel_dependency() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "wheel" in data["build-system"]["requires"]


def test_project_supports_python_310_or_newer() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["requires-python"] == ">=3.10"


def test_readme_mentions_python_310_or_newer() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Python 3.10+" in readme


def test_automation_extra_includes_desktop_dependencies() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    automation_deps = data["project"]["optional-dependencies"]["automation"]
    assert any(dep.startswith("pyautogui") for dep in automation_deps)
    assert any(dep.startswith("pyperclip") for dep in automation_deps)


def test_readme_mentions_windows_desktop_mode_and_calibration() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "windows-desktop" in readme
    assert "--calibrate-desktop" in readme
