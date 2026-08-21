from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_windows_build_bundles_the_pdf_ruleset():
    spec = (ROOT / "grave.spec").read_text(encoding="utf-8")
    package = "data/packages/rulesets/gravewright-pdf-system"
    destination = "bundled-packages/rulesets/gravewright-pdf-system"
    assert package in spec
    assert destination in spec


def test_core_installs_bundled_packages_without_overwriting_user_copy():
    launcher = (ROOT / "app/cli/bundled_packages.py").read_text(encoding="utf-8")
    assert "def install_bundled_packages(" in launcher
    assert 'data_root / "packages" / kind' in launcher
    assert "if target.exists():" in launcher
    assert "shutil.copytree(source, target)" in launcher
    cli = (ROOT / "app/cli/__init__.py").read_text(encoding="utf-8")
    assert "install_bundled_packages()" in cli
