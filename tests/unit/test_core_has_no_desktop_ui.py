from __future__ import annotations

import ast
from pathlib import Path

from app.cli import build_parser


ROOT = Path(__file__).resolve().parents[2]


def test_core_runtime_has_no_pyside_imports():
    for path in [*ROOT.glob("*.py"), *(ROOT / "app").rglob("*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        names += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert not any(name == "PySide6" or name.startswith("PySide6.") for name in names), path


def test_standard_dependencies_do_not_include_qt():
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "pyside6" not in project
    assert '"qt' not in project


def test_core_build_uses_cli_entrypoint_and_excludes_desktop_ui():
    spec = (ROOT / "grave.spec").read_text(encoding="utf-8")
    assert "grave_launcher.py" in spec
    assert "desktop.py" not in spec
    assert "PySide6" not in spec


def test_cli_still_builds_without_desktop_dependency():
    args = build_parser().parse_args(["doctor", "--skip-db"])
    assert args.command == "doctor"
