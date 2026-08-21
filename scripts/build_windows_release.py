"""Build the minimal launcher and assemble the source-based Windows x64 ZIP."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
LAUNCHER = DIST / "windows-launcher" / "Gravewright.exe"
STAGING = DIST / "Gravewright-Windows-x64"
ARCHIVE = DIST / "Gravewright-Windows-x64.zip"
DIRECTORIES = ("app", "migrations", "schemas", "scripts", "static", "templates")
FILES = (
    ".env.development.example", ".python-version", "alembic.ini", "icon.png", "LICENSE", "LICENSE-API.md",
    "install-windows.bat", "main.py", "marketplace.toml", "NOTICE", "pyproject.toml", "README.md", "SECURITY.md",
    "THIRD_PARTY_NOTICES.md", "uv.lock",
)


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in {"__pycache__", ".pytest_cache", ".ruff_cache"} or name.endswith((".pyc", ".pyo"))}


def build_launcher(*, runner=subprocess.run) -> None:
    command = [
        "uv", "run", "--group", "dev", "pyinstaller", "--noconfirm", "--clean",
        "--distpath", str(DIST / "windows-launcher"),
        "--workpath", str(ROOT / "build" / "windows-launcher"),
        str(ROOT / "packaging" / "windows-launcher.spec"),
    ]
    result = runner(command, cwd=str(ROOT), check=False)
    if result.returncode != 0 or not LAUNCHER.is_file():
        raise RuntimeError(f"Windows launcher build failed with exit code {result.returncode}")


def assemble(*, launcher: Path = LAUNCHER, staging: Path = STAGING, archive: Path = ARCHIVE) -> Path:
    if not launcher.is_file():
        raise FileNotFoundError(f"Launcher is missing: {launcher}")
    staging = staging.resolve()
    archive = archive.resolve()
    if staging == ROOT.resolve() or staging == staging.parent or len(staging.parts) < 3:
        raise ValueError(f"Unsafe release staging path: {staging}")
    if archive == ROOT.resolve() or archive == archive.parent or len(archive.parts) < 3:
        raise ValueError(f"Unsafe release archive path: {archive}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copy2(launcher, staging / "Gravewright.exe")
    for relative in DIRECTORIES:
        shutil.copytree(ROOT / relative, staging / relative, ignore=_ignore)
    pdf_source = ROOT / "data" / "packages" / "rulesets" / "gravewright-pdf-system"
    shutil.copytree(pdf_source, staging / "data" / "packages" / "rulesets" / pdf_source.name, ignore=_ignore)
    for relative in FILES:
        shutil.copy2(ROOT / relative, staging / relative)
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(staging).as_posix())
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-launcher-build", action="store_true")
    args = parser.parse_args(argv)
    if not args.skip_launcher_build:
        build_launcher()
    result = assemble()
    print(f"Windows release: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
