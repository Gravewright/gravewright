"""Minimal Windows bootstrapper for the source-based Gravewright distribution.

This module intentionally uses only the Python standard library. PyInstaller
freezes it into ``Gravewright.exe``; Gravewright itself remains managed by uv.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


UV_VERSION = "0.9.11"
UV_ARCHIVE_URL = (
    f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/"
    "uv-x86_64-pc-windows-msvc.zip"
)
UV_ARCHIVE_SHA256 = "45a3ff2a68c246ed9fd2d9df032496c1beebe480357f356ac25d2cb144884c30"
UV_ARCHIVE_MAX_BYTES = 64 * 1024 * 1024
PROJECT_MARKERS = ("pyproject.toml", "uv.lock", "app", "scripts")


class LauncherError(RuntimeError):
    def __init__(self, step: str, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.step, self.exit_code = step, exit_code


@dataclass(frozen=True)
class StepResult:
    returncode: int


Runner = Callable[..., subprocess.CompletedProcess]


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def discover_project_root(base: Path | None = None) -> Path:
    root = (base or executable_dir()).resolve()
    missing = [marker for marker in PROJECT_MARKERS if not (root / marker).exists()]
    if missing:
        raise LauncherError(
            "Project discovery",
            f"Gravewright.exe must be inside the extracted Gravewright folder. Missing: {', '.join(missing)}",
        )
    return root


def _candidate_uv_paths(*, environ: dict[str, str] | None = None) -> list[Path]:
    env = environ or os.environ
    candidates: list[Path] = []
    found = shutil.which("uv", path=env.get("PATH"))
    if found:
        candidates.append(Path(found))
    if env.get("UV_INSTALL_DIR"):
        candidates.append(Path(env["UV_INSTALL_DIR"]) / "uv.exe")
    if env.get("USERPROFILE"):
        home = Path(env["USERPROFILE"])
        candidates.extend((home / ".local" / "bin" / "uv.exe", home / ".cargo" / "bin" / "uv.exe"))
    if env.get("LOCALAPPDATA"):
        candidates.append(Path(env["LOCALAPPDATA"]) / "uv" / "bin" / "uv.exe")
    return candidates


def find_uv(*, environ: dict[str, str] | None = None) -> Path | None:
    for candidate in _candidate_uv_paths(environ=environ):
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _download(url: str, destination: Path, *, timeout: float = 60.0) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Gravewright-Windows-Launcher/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as output:
        declared = int(response.headers.get("Content-Length") or 0)
        if declared > UV_ARCHIVE_MAX_BYTES:
            raise LauncherError("Runtime bootstrap", "Official uv archive exceeds the size limit.")
        total = 0
        while chunk := response.read(64 * 1024):
            total += len(chunk)
            if total > UV_ARCHIVE_MAX_BYTES:
                raise LauncherError("Runtime bootstrap", "Official uv archive exceeds the size limit.")
            output.write(chunk)


def bootstrap_uv(
    *, environ: dict[str, str] | None = None,
    downloader: Callable[..., None] = _download,
) -> Path:
    env = environ or os.environ
    user_profile = env.get("USERPROFILE")
    if not user_profile:
        raise LauncherError("Runtime bootstrap", "USERPROFILE is unavailable; uv cannot be installed per-user.")
    install_dir = Path(user_profile).resolve() / ".local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gravewright-uv-") as temporary:
        archive = Path(temporary) / "uv.zip"
        try:
            downloader(UV_ARCHIVE_URL, archive, timeout=60.0)
        except LauncherError:
            raise
        except Exception as exc:
            raise LauncherError("Runtime bootstrap", f"Could not download uv: {exc}") from None
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if not hmac.compare_digest(actual, UV_ARCHIVE_SHA256):
            raise LauncherError("Runtime bootstrap", "Downloaded uv archive failed SHA-256 verification.")
        try:
            with zipfile.ZipFile(archive) as package:
                members = {Path(info.filename).name.lower(): info for info in package.infolist() if not info.is_dir()}
                for name in ("uv.exe", "uvx.exe"):
                    info = members.get(name)
                    if info is None or info.file_size > UV_ARCHIVE_MAX_BYTES:
                        raise LauncherError("Runtime bootstrap", f"Official uv archive is missing {name}.")
                    staged = Path(temporary) / name
                    with package.open(info) as source, staged.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    os.replace(staged, install_dir / name)
        except (OSError, zipfile.BadZipFile) as exc:
            raise LauncherError("Runtime bootstrap", f"Could not install verified uv archive: {exc}") from None
    uv = install_dir / "uv.exe"
    if not uv.is_file():
        raise LauncherError("Runtime bootstrap", "uv was not installed successfully.")
    return uv


def run_step(step: str, command: Sequence[str], *, root: Path, runner: Runner = subprocess.run) -> StepResult:
    try:
        result = runner(list(command), cwd=str(root), check=False)
    except OSError as exc:
        raise LauncherError(step, f"Could not start command: {exc}") from None
    if result.returncode != 0:
        raise LauncherError(step, "Command returned a non-zero exit code.", result.returncode)
    return StepResult(result.returncode)


def run_doctor(uv: Path, *, root: Path, runner: Runner = subprocess.run) -> int:
    """Show Doctor verbatim; startup remains authoritative about fatal checks."""
    try:
        result = runner([str(uv), "run", "python", "-m", "app.cli", "doctor"], cwd=str(root), check=False)
    except OSError as exc:
        raise LauncherError("Installation health", f"Could not start Doctor: {exc}") from None
    return int(result.returncode)


def _stop_process(process: subprocess.Popen, *, timeout: float = 15.0) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
        process.wait(timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def run_server(
    uv: Path, *, root: Path, popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    smoke_seconds: float = 0, port: int = 8000,
) -> int:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        process = popen(
            [str(uv), "run", "python", "-m", "app.cli", "run", "--open", "--port", str(port)],
            cwd=str(root),
            creationflags=flags,
        )
    except OSError as exc:
        raise LauncherError("Gravewright startup", f"Could not start Gravewright: {exc}") from None
    smoke_stop = threading.Event()
    def stop_smoke() -> None:
        smoke_stop.set()
        _stop_process(process)
    if smoke_seconds > 0:
        timer = threading.Timer(smoke_seconds, stop_smoke)
        timer.daemon = True
        timer.start()
    try:
        returncode = int(process.wait())
        return 0 if smoke_stop.is_set() else returncode
    except KeyboardInterrupt:
        _stop_process(process)
        return 0


def print_header() -> None:
    print("=" * 59)
    print("  Gravewright")
    print("=" * 59)
    print()


def pause() -> None:
    if sys.stdin and sys.stdin.isatty():
        try:
            input("Press Enter to close.")
        except (EOFError, KeyboardInterrupt):
            pass


def orchestrate(
    *, root: Path | None = None, runner: Runner = subprocess.run,
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    environ: dict[str, str] | None = None,
) -> int:
    project_root = root or discover_project_root()
    env = environ or os.environ
    print_header()
    uv = find_uv(environ=env)
    if uv is None:
        print(f"[1/5] Runtime\n      Installing verified uv {UV_VERSION} per-user...")
        uv = bootstrap_uv(environ=env)
    version = runner([str(uv), "--version"], cwd=str(project_root), check=False)
    if version.returncode != 0:
        raise LauncherError("Runtime detection", "uv was found but could not run.", version.returncode)
    print(f"[1/5] Runtime\n      {uv}")
    print("[2/5] Dependencies\n      Synchronizing locked environment...")
    run_step("Dependency synchronization", [str(uv), "sync", "--frozen"], root=project_root, runner=runner)
    print("      Ready")
    print("[3/5] Local configuration\n      Preparing...")
    run_step(
        "Local configuration",
        [str(uv), "run", "python", "scripts/setup_local_env.py"],
        root=project_root,
        runner=runner,
    )
    print("      Ready")
    print("[4/5] Installation health\n      Running grave doctor...")
    doctor_code = run_doctor(uv, root=project_root, runner=runner)
    if doctor_code:
        print(f"      Doctor reported exit code {doctor_code}; startup will enforce fatal checks.")
    try:
        port = int(env.get("GRAVEWRIGHT_LAUNCHER_PORT", "8000") or 8000)
    except ValueError:
        raise LauncherError("Gravewright startup", "GRAVEWRIGHT_LAUNCHER_PORT must be an integer.") from None
    if not 1 <= port <= 65535:
        raise LauncherError("Gravewright startup", f"Invalid TCP port: {port}")
    print(f"[5/5] Gravewright\n      Starting at http://127.0.0.1:{port}")
    print("\nKeep this window open while you play.\nPress Ctrl+C to stop.\n")
    smoke_seconds = float(env.get("GRAVEWRIGHT_LAUNCHER_SMOKE_SECONDS", "0") or 0)
    server_code = run_server(uv, root=project_root, popen=popen, smoke_seconds=smoke_seconds, port=port)
    if server_code != 0:
        raise LauncherError("Gravewright startup", "Gravewright stopped with an error.", server_code)
    print("\nGravewright has stopped. You can close this window.")
    return 0


def main() -> int:
    # Child Python processes must render Doctor's Unicode status symbols even
    # when the launcher is opened from a legacy Windows console code page.
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        code = orchestrate()
    except LauncherError as exc:
        print("\n[ERROR] Gravewright setup did not finish.\n", file=sys.stderr)
        print(f"Step:\n{exc.step}\n", file=sys.stderr)
        print(f"Exit code:\n{exc.exit_code}\n", file=sys.stderr)
        print(f"{exc}\n", file=sys.stderr)
        print("Copy the output above when asking for help.\n", file=sys.stderr)
        pause()
        return exc.exit_code or 1
    pause()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
