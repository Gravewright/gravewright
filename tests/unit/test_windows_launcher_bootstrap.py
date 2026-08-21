from __future__ import annotations

import hashlib
import io
import subprocess
import zipfile
from pathlib import Path

import pytest

from scripts import windows_launcher as launcher


def project(tmp_path: Path) -> Path:
    root = tmp_path / "Gravewright Release With Spaces"
    root.mkdir()
    for name in ("app", "scripts"):
        (root / name).mkdir()
    for name in ("pyproject.toml", "uv.lock"):
        (root / name).write_text("marker", encoding="utf-8")
    return root


def fake_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"exe")
    return path.resolve()


def completed(command, code=0):
    return subprocess.CompletedProcess(command, code)


def test_project_root_is_executable_directory_and_supports_spaces(tmp_path):
    root = project(tmp_path)
    assert launcher.discover_project_root(root) == root.resolve()


def test_project_root_reports_incomplete_zip(tmp_path):
    with pytest.raises(launcher.LauncherError, match="Missing"):
        launcher.discover_project_root(tmp_path)


def test_uv_detection_prefers_path(tmp_path, monkeypatch):
    uv = fake_executable(tmp_path / "path" / "uv.exe")
    monkeypatch.setattr(launcher.shutil, "which", lambda *_args, **_kwargs: str(uv))
    assert launcher.find_uv(environ={"PATH": str(uv.parent)}) == uv


def test_uv_detection_uses_user_install_directory(tmp_path, monkeypatch):
    uv = fake_executable(tmp_path / ".local" / "bin" / "uv.exe")
    monkeypatch.setattr(launcher.shutil, "which", lambda *_args, **_kwargs: None)
    assert launcher.find_uv(environ={"USERPROFILE": str(tmp_path), "PATH": ""}) == uv


def test_uv_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher.shutil, "which", lambda *_args, **_kwargs: None)
    assert launcher.find_uv(environ={"USERPROFILE": str(tmp_path), "PATH": ""}) is None


def uv_archive() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("uv.exe", b"uv")
        archive.writestr("uvx.exe", b"uvx")
    return output.getvalue()


def test_verified_uv_bootstrap_installs_only_expected_binaries(tmp_path, monkeypatch):
    data = uv_archive()
    monkeypatch.setattr(launcher, "UV_ARCHIVE_SHA256", hashlib.sha256(data).hexdigest())
    def download(_url, destination, *, timeout):
        assert timeout == 60.0
        destination.write_bytes(data)
    uv = launcher.bootstrap_uv(environ={"USERPROFILE": str(tmp_path)}, downloader=download)
    assert uv.read_bytes() == b"uv"
    assert (uv.parent / "uvx.exe").read_bytes() == b"uvx"
    assert sorted(path.name for path in uv.parent.iterdir()) == ["uv.exe", "uvx.exe"]


def test_uv_bootstrap_rejects_checksum_mismatch(tmp_path):
    def download(_url, destination, *, timeout):
        destination.write_bytes(uv_archive())
    with pytest.raises(launcher.LauncherError, match="SHA-256"):
        launcher.bootstrap_uv(environ={"USERPROFILE": str(tmp_path)}, downloader=download)


def test_uv_bootstrap_failure_is_operational_error(tmp_path):
    def fail(*_args, **_kwargs):
        raise TimeoutError("offline")
    with pytest.raises(launcher.LauncherError, match="Could not download uv"):
        launcher.bootstrap_uv(environ={"USERPROFILE": str(tmp_path)}, downloader=fail)


@pytest.mark.parametrize("failed_index, step", [(1, "Dependency synchronization"), (2, "Local configuration")])
def test_orchestration_reports_sync_and_setup_failures(tmp_path, monkeypatch, failed_index, step):
    root, uv = project(tmp_path), fake_executable(tmp_path / "uv.exe")
    monkeypatch.setattr(launcher, "find_uv", lambda **_kwargs: uv)
    calls = []
    def runner(command, **_kwargs):
        calls.append(command)
        return completed(command, 7 if len(calls) - 1 == failed_index else 0)
    with pytest.raises(launcher.LauncherError) as error:
        launcher.orchestrate(root=root, runner=runner, environ={})
    assert error.value.step == step and error.value.exit_code == 7


def test_doctor_is_invoked_but_its_exit_does_not_override_startup_policy(tmp_path, monkeypatch):
    root, uv = project(tmp_path), fake_executable(tmp_path / "uv.exe")
    monkeypatch.setattr(launcher, "find_uv", lambda **_kwargs: uv)
    calls = []
    def runner(command, **_kwargs):
        calls.append(command)
        code = 3 if command[-1] == "doctor" else 0
        return completed(command, code)
    monkeypatch.setattr(launcher, "run_server", lambda *_args, **_kwargs: 0)
    assert launcher.orchestrate(root=root, runner=runner, environ={}) == 0
    assert [str(uv), "run", "python", "-m", "app.cli", "doctor"] in calls


def test_server_startup_uses_public_cli_and_propagates_ctrl_c(tmp_path, monkeypatch):
    root, uv = project(tmp_path), fake_executable(tmp_path / "uv.exe")
    class Process:
        returncode = 0
        signals = []
        def wait(self, timeout=None):
            if timeout is None and not self.signals:
                raise KeyboardInterrupt
            return 0
        def poll(self): return None
        def send_signal(self, value): self.signals.append(value)
        def terminate(self): raise AssertionError("graceful shutdown should succeed")
    process, captured = Process(), {}
    def popen(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return process
    assert launcher.run_server(uv, root=root, popen=popen) == 0
    assert captured["command"] == [
        str(uv), "run", "python", "-m", "app.cli", "run", "--open", "--port", "8000",
    ]
    assert process.signals


def test_nonzero_server_exit_is_reported(tmp_path, monkeypatch):
    root, uv = project(tmp_path), fake_executable(tmp_path / "uv.exe")
    monkeypatch.setattr(launcher, "find_uv", lambda **_kwargs: uv)
    monkeypatch.setattr(launcher, "run_server", lambda *_args, **_kwargs: 9)
    with pytest.raises(launcher.LauncherError) as error:
        launcher.orchestrate(root=root, runner=lambda command, **_kwargs: completed(command), environ={})
    assert error.value.step == "Gravewright startup" and error.value.exit_code == 9


def test_launcher_source_and_spec_are_minimal_and_have_no_gui_dependency():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts/windows_launcher.py").read_text(encoding="utf-8")
    spec = (root / "packaging/windows-launcher.spec").read_text(encoding="utf-8")
    assert "PySide6" not in source
    assert "shell=True" not in source
    assert 'name="Gravewright"' in spec
    assert "console=True" in spec
    assert all(value not in spec for value in ("collect_all", "app/", "static", "templates"))
