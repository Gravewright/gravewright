from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.build_windows_release import assemble


def test_release_zip_places_minimal_launcher_at_root(tmp_path):
    launcher = tmp_path / "built" / "Gravewright.exe"
    launcher.parent.mkdir()
    launcher.write_bytes(b"launcher")
    archive = assemble(
        launcher=launcher,
        staging=tmp_path / "staging",
        archive=tmp_path / "Gravewright-Windows-x64.zip",
    )
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
    assert "Gravewright.exe" in names
    assert "pyproject.toml" in names and "uv.lock" in names
    assert ".env.development.example" in names
    assert "install-windows.bat" in names and "README.md" in names
    assert "app/cli/__init__.py" in names
    assert "scripts/setup_local_env.py" in names
    assert "data/packages/rulesets/gravewright-pdf-system/manifest.json" in names
    assert not any(name.startswith(("storage/", ".venv/")) for name in names)


def test_fallback_bat_delegates_to_executable_and_does_not_pipe_remote_code():
    root = Path(__file__).resolve().parents[2]
    fallback = (root / "install-windows.bat").read_text(encoding="utf-8").lower()
    assert "gravewright.exe" in fallback
    assert "irm" not in fallback and "iex" not in fallback
