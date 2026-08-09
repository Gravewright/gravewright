from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_windows_build_bundles_the_pdf_ruleset():
    spec = (ROOT / "Gravewright.spec").read_text(encoding="utf-8")
    package = "data/packages/rulesets/gravewright-pdf-system"
    destination = "bundled-packages/rulesets/gravewright-pdf-system"
    assert package in spec
    assert destination in spec


def test_desktop_installs_bundled_packages_without_overwriting_user_copy():
    launcher = (ROOT / "desktop.py").read_text(encoding="utf-8")
    assert "def _install_bundled_packages()" in launcher
    assert 'data_root / "packages" / kind' in launcher
    assert "if not target.exists():" in launcher
    assert "shutil.copytree(source, target)" in launcher
    assert "_install_bundled_packages()" in launcher.split("def main()", 1)[1]
