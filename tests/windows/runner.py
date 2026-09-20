"""Exercise the actual Windows BAT, private tools and local server.

Run ``python tests/windows/runner.py`` on Windows. A temporary source copy,
profile and campaign directory keep developer files untouched. The first BAT
process sees a restricted PATH; the next reuses the installed tools offline.
The harness then runs the frontend unit tests and the real browser Runner E2E.

``--source-check`` checks for obsolete launcher implementations on any OS.
``--skip-browser`` omits Playwright installation and the browser E2E.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = "Gravewright Runner.bat"
PROFILE_NAME = "Private profile ç"


def check_sources():
    batch = (ROOT / LAUNCHER).read_text(encoding="utf-8-sig").lower()
    for obsolete in ("powershell", "pwsh", ".ps1"):
        if obsolete in batch:
            raise AssertionError(f"The native BAT still references {obsolete}.")
    for obsolete in ("scripts/windows/bootstrap.ps1", "scripts/windows/tools.ps1",
                     "tests/windows/tooling.ps1"):
        if (ROOT / obsolete).exists():
            raise AssertionError(f"Obsolete launcher implementation remains: {obsolete}")
    print("Native BAT source checks passed.", flush=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def registry_paths():
    """Read the persisted PATH values; the Runner must never modify them."""
    import winreg

    values = []
    for hive, key in ((winreg.HKEY_CURRENT_USER, r"Environment"),
                      (winreg.HKEY_LOCAL_MACHINE,
                       r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
        with winreg.OpenKey(hive, key) as handle:
            try:
                values.append(winreg.QueryValueEx(handle, "Path"))
            except FileNotFoundError:
                values.append(None)
    return values


def run_command(command, *, cwd, env, log, label, timeout=600, expected=0, executable=None):
    print(label, flush=True)
    process = subprocess.Popen(
        command, executable=executable, cwd=cwd, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # Only this test's process tree is terminated; uv/node may own children.
        subprocess.run(
            [str(Path(env["SYSTEMROOT"]) / "System32/taskkill.exe"),
             "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        output, _ = process.communicate(timeout=15)
        log.write_text(output, encoding="utf-8")
        raise
    log.write_text(output, encoding="utf-8")
    if (expected == 0 and process.returncode != 0) or (expected != 0 and process.returncode == 0):
        raise AssertionError(f"{label} Exit code {process.returncode}; inspect {log}\n{output[-16000:]}")
    return output


def run_batch(project, arguments, *, env, log, label, cwd, expected=0, timeout=600):
    """Call CMD directly and keep paths containing %, ! and & as data.

    CMD expands these test variables once. Substituted percent signs are not
    recursively expanded, and delayed expansion is disabled for literal '!'.
    The BAT is the actual entry point, with no alternate installer involved.
    """
    child = dict(env)
    parts = []
    for index, value in enumerate((str(project / LAUNCHER), *arguments)):
        if any(character in str(value) for character in '\r\n"'):
            raise ValueError("Test batch arguments may not contain quotes or newlines.")
        name = f"GRAVEWRIGHT_TEST_ARGUMENT_{index}"
        child[name] = str(value)
        parts.append(f'"%{name}%"')
    comspec = str(Path(env["SYSTEMROOT"]) / "System32/cmd.exe")
    command = f'"{comspec}" /d /s /v:off /c "' + " ".join(parts) + '"'
    return run_command(command, executable=comspec, cwd=cwd, env=child,
                       log=log, label=label, expected=expected, timeout=timeout)


def single_match(directory, pattern):
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise AssertionError(f"Expected one {pattern} under {directory}; found {len(matches)}")
    return matches[0]


@contextmanager
def exclusive_file(path):
    """Hold the real Windows file sharing lock used by CMD redirection."""
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                   ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handle = kernel.CreateFileW(str(path), 0xC0000000, 0, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())


def check_shortcut(project, output):
    """Read the actual shell link back through COM, without another shell."""
    import ctypes

    source = ROOT / "scripts/windows/create_shortcut.py"
    spec = importlib.util.spec_from_file_location("runner_shortcut", source)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    report = {"shortcut": str(project / "Gravewright Runner.lnk")}
    with helper.shell_link() as link, helper.interface(link, helper.IID_PERSIST_FILE) as persist:
        helper.checked(helper.method(persist, 5, ctypes.c_wchar_p, ctypes.c_uint32)(
            persist, str(project / "Gravewright Runner.lnk"), 0), "Load shortcut")
        buffer = ctypes.create_unicode_buffer(32768)
        helper.checked(helper.method(link, 3, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p,
                                     ctypes.c_uint32)(link, buffer, len(buffer), None, 0), "Read target")
        report["target"] = buffer.value
        helper.checked(helper.method(link, 3, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p,
                                     ctypes.c_uint32)(link, buffer, len(buffer), None, 4), "Read raw target")
        report["target_raw"] = buffer.value  # SLGP_RAWPATH; retain alongside the resolved target.
        icon_index = ctypes.c_int()
        helper.checked(helper.method(link, 16, ctypes.c_wchar_p, ctypes.c_int,
                                     ctypes.POINTER(ctypes.c_int))(
            link, buffer, len(buffer), ctypes.byref(icon_index)), "Read icon")
        report["icon"] = buffer.value
        report["icon_index"] = icon_index.value
        helper.checked(helper.method(link, 8, ctypes.c_wchar_p, ctypes.c_int)(
            link, buffer, len(buffer)), "Read working directory")
        report["working_directory"] = buffer.value

    expected = {"target": project / LAUNCHER,
                "icon": project / "scripts/windows/gravewright.ico",
                "working_directory": project}
    report["expected"] = {name: str(path) for name, path in expected.items()}
    report["same_file"] = {}
    failures = []
    for name, path in expected.items():
        try:
            # TEMP may contain RUNNER~1 while the Shell returns runneradmin.
            # Require actual file identity, not merely similar path strings.
            matches = bool(report[name]) and Path(report[name]).samefile(path)
        except OSError as error:
            matches = False
            report.setdefault("errors", {})[name] = str(error)
        report["same_file"][name] = matches
        if not matches:
            failures.append(f"{name}: received {report[name]!r}; expected {str(path)!r}")
    if report["icon_index"] != 0:
        failures.append(f"icon index: received {report['icon_index']}; expected 0")
    destination = output / "shortcut-diagnostics.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        raise AssertionError(f"Runner shortcut validation failed; inspect {destination}\n" + "\n".join(failures))
    print("Shortcut target, project icon and working directory identify the expected files.", flush=True)


def diagnose_failure(work, output):
    """Retain tool startup evidence before deleting the temporary test profile."""
    runtime = work / PROFILE_NAME / "Gravewright/runner"
    system = Path(os.environ["SYSTEMROOT"]) / "System32"
    report = {"runtime_exists": runtime.exists(), "executables": []}

    def probe(arguments):
        try:
            result = subprocess.run(arguments, stdin=subprocess.DEVNULL, capture_output=True,
                                    cwd=work, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            return {"error": str(error)}
        return {"exit_code": result.returncode, "stdout_bytes": repr(result.stdout),
                "stderr_bytes": repr(result.stderr)}

    for directory, pattern in (("uv", "*/uv.exe"), ("node", "*/node.exe")):
        for executable in (runtime / directory).glob(pattern):
            item = {"path": str(executable.relative_to(runtime)),
                    "size": executable.stat().st_size, "sha256": digest(executable)}
            item["version"] = probe([str(executable), "--version"])
            item["certutil"] = probe([str(system / "certutil.exe"), "-hashfile", str(executable), "SHA256"])
            report["executables"].append(item)
    destination = output / "tool-diagnostics.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Additional native tool diagnostics: {destination}", flush=True)


def exercise(work, output, *, skip_browser):
    project = work / "Gravewright & (test) ! 100% ç"
    data = work / "Campaign data & ã"
    profile = work / PROFILE_NAME
    shutil.copytree(
        ROOT, project,
        ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__",
                                     "test-results", ".env", "data", "media", "staticfiles"),
    )
    source_env = project / ".env"
    source_env.write_text("DJANGO_SECRET_KEY=source-env-must-stay-untouched", encoding="utf-8")
    sentinel = project / ".venv/developer-data.txt"
    sentinel.parent.mkdir()
    sentinel.write_text("existing developer environment", encoding="utf-8")
    protected = [source_env, sentinel, project / "uv.lock",
                 project / "gravewright/maps/frontend/package-lock.json"]
    original = {path: digest(path) for path in protected}
    persisted_paths = registry_paths()
    process_path = os.environ.get("PATH", "")
    env = dict(os.environ, LOCALAPPDATA=str(profile))
    # uv/Node/npm disappear from PATH; registered/shared Python may still be
    # found and reused by uv. This never changes the parent or registry PATH.
    env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
    port = str(free_port())
    arguments = ["--check", "--no-browser", "--no-pause", "--data-dir", str(data), "--port", port]
    run_batch(project, arguments, cwd=work, env=env, log=output / "first-bootstrap.log",
              label="Running the real BAT with uv and Node/npm absent from PATH...")
    runtime = profile / "Gravewright/runner"
    uv = single_match(runtime / "uv", "*/uv.exe")
    node = single_match(runtime / "node", "*/node.exe")
    python = single_match(runtime / "environments", "*/Scripts/python.exe")
    check_shortcut(project, output)
    for expected in (data / ".env", data / "gravewright.sqlite3"):
        if not expected.is_file():
            raise AssertionError(f"First bootstrap did not create {expected.name} in the requested data directory.")
    user_configuration = digest(data / ".env")
    installed_lock = project / "gravewright/maps/frontend/node_modules/.package-lock.json"
    bundle = project / "gravewright/table/static/gravewright_table/media-workspace.js"
    timestamps = {path: path.stat().st_mtime_ns for path in (installed_lock, bundle, uv, node)}

    database_time = (data / "gravewright.sqlite3").stat().st_mtime_ns
    with exclusive_file(runtime / "prepare.lock"):
        locked = run_batch(project, arguments, cwd=work, env=env, log=output / "preparation-lock.log",
                           label="Rejecting a concurrent preparation before installing or migrating...",
                           expected=1, timeout=30)
    if "[1/7] Checking uv" in locked:
        raise AssertionError("The competing launcher entered preparation while its lock was held.")
    if (data / "gravewright.sqlite3").stat().st_mtime_ns != database_time:
        raise AssertionError("The competing launcher changed the database while preparation was locked.")

    # Make the same tools available as preinstalled applications on PATH.
    env["PATH"] = os.pathsep.join((str(uv.parent), str(node.parent), process_path))
    env["UV_OFFLINE"] = "1"
    env["npm_config_offline"] = "true"
    repeated = run_batch(project, arguments, cwd=work, env=env, log=output / "repeat-bootstrap.log",
                         label="Reusing installed tools, packages and frontend assets offline...")
    for message in ("Frontend dependencies are already current.", "Frontend assets are already current."):
        if message not in repeated:
            raise AssertionError(f"The unchanged bootstrap did not report: {message}")
    for path, timestamp in timestamps.items():
        if path.stat().st_mtime_ns != timestamp:
            raise AssertionError(f"The unchanged bootstrap rewrote {path.name}.")
    if digest(data / ".env") != user_configuration:
        raise AssertionError("The repeated bootstrap changed the user configuration.")
    if {path: digest(path) for path in protected} != original:
        raise AssertionError("The BAT changed a source lockfile, .env or developer environment.")
    if registry_paths() != persisted_paths or os.environ.get("PATH", "") != process_path:
        raise AssertionError("The BAT changed the user, machine or parent process PATH.")

    run_batch(project, ["--port", "70000", "--no-pause"], cwd=work, env=env,
              log=output / "invalid-port.log", label="Rejecting an invalid port without pausing...", expected=1)
    run_command([str(python), "-X", "utf8", "-m", "unittest", "config.test_frontend_preparation"],
                cwd=project, env=env, log=output / "frontend-tests.log",
                label="Running frontend preparation and repair regression tests...")
    if skip_browser:
        return

    env.pop("UV_OFFLINE", None)
    env.pop("npm_config_offline", None)
    env["UV_PROJECT_ENVIRONMENT"] = str(work / "Browser test environment")
    env["UV_PYTHON_INSTALL_DIR"] = str(runtime / "python")
    env["UV_CACHE_DIR"] = str(runtime / "cache")
    env["UV_PYTHON_INSTALL_BIN"] = "0"
    env["UV_PYTHON_INSTALL_REGISTRY"] = "0"
    run_command([str(uv), "--no-config", "sync", "--project", str(project), "--locked", "--python", str(python)],
                cwd=project, env=env, log=output / "browser-dependencies.log",
                label="Preparing isolated browser test dependencies...")
    browser_python = Path(env["UV_PROJECT_ENVIRONMENT"]) / "Scripts/python.exe"
    run_command([str(browser_python), "-m", "playwright", "install", "chromium"],
                cwd=project, env=env, log=output / "browser-install.log", label="Installing test Chromium...")
    try:
        run_command([str(browser_python), "-X", "utf8", str(project / "tests/e2e/runner.py")],
                    cwd=project, env=env, log=output / "browser-e2e.log",
                    label="Testing the real server, chat, persistence and shutdown in Chromium...", timeout=300)
    finally:
        server_logs = project / "test-results/runner"
        if server_logs.exists():
            shutil.copytree(server_logs, output / "server", dirs_exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-check", action="store_true")
    parser.add_argument("--skip-browser", action="store_true")
    arguments = parser.parse_args()
    check_sources()
    if arguments.source_check:
        return
    if os.name != "nt":
        parser.error("Native BAT tests require Windows; --source-check is available on this OS.")
    output = ROOT / "test-results/windows-runner"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gravewright-bat-") as temporary:
        try:
            exercise(Path(temporary), output, skip_browser=arguments.skip_browser)
        except Exception:
            try:
                diagnose_failure(Path(temporary), output)
            except Exception as diagnostic_error:
                (output / "diagnostic-error.txt").write_text(str(diagnostic_error), encoding="utf-8")
            raise
    print(f"Native Windows Runner checks passed. Logs: {output}", flush=True)


if __name__ == "__main__":
    main()
