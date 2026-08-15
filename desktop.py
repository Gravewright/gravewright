"""Native PySide6 launcher for Gravewright.

The launcher is intentionally small: it operates the existing ``grave`` CLI,
owns the local Uvicorn process, and opens the table in the user's browser.  It
does not embed a browser engine.
"""

from __future__ import annotations

import contextlib
import io
import logging
import os
import shutil
import socket
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Callable


APP_TITLE = "Gravewright Launcher"


def writable_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent / "GravewrightData"
    else:
        base = Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base


# Private compatibility names are kept because the packaged-launcher contract and
# its tests patch these seams to avoid touching the real user data directory.
_writable_base_dir = writable_base_dir


def load_user_env() -> None:
    if not getattr(sys, "frozen", False):
        return
    env_path = Path(sys.executable).resolve().parent / ".env"
    if env_path.is_file():
        from app.helpers.env import _apply_file

        _apply_file(env_path)


_load_user_env = load_user_env


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _configure_environment(host: str, port: int) -> None:
    _load_user_env()
    base = _writable_base_dir()
    storage = base / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("GRAVEWRIGHT_DATA_DIR", str(base / "data"))
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{(storage / 'gravewright.sqlite3').resolve()}")
    os.environ["APP_ENV"] = "development"
    os.environ["ALLOWED_HOSTS"] = "*"
    os.environ["SESSION_COOKIE_SECURE"] = "false"
    origins = [f"http://{host}:{port}", f"http://localhost:{port}"]
    origins.extend(x.strip() for x in os.environ.get("WS_ALLOWED_ORIGINS", "").split(",") if x.strip())
    os.environ["WS_ALLOWED_ORIGINS"] = ",".join(dict.fromkeys(origins))


def configure_environment(port: int) -> None:
    _configure_environment("127.0.0.1", port)


def install_bundled_packages() -> None:
    if not getattr(sys, "frozen", False):
        return
    bundle_root = Path(getattr(sys, "_MEIPASS", "")) / "bundled-packages"
    data_root = Path(os.environ["GRAVEWRIGHT_DATA_DIR"])
    for kind in ("rulesets", "addons", "libraries", "themes", "content", "assets"):
        source_kind = bundle_root / kind
        if not source_kind.is_dir():
            continue
        for source in source_kind.iterdir():
            if source.is_dir():
                target = data_root / "packages" / kind / source.name
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(source, target)


def _install_bundled_packages() -> None:
    install_bundled_packages()


class SignalWriter(io.TextIOBase):
    def __init__(self, emit: Callable[[str], None]) -> None:
        self._emit = emit

    def write(self, text: str) -> int:
        if text:
            self._emit(text)
        return len(text)

    def flush(self) -> None:
        return None


def build_ui(port: int):
    from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
    from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSpacerItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class Bridge(QObject):
        output = Signal(str)
        command_done = Signal(str, int)
        server_ready = Signal(str)
        server_stopped = Signal(int)
        server_failed = Signal(str)

    class CommandWorker(QThread):
        def __init__(self, bridge: Bridge, label: str, arguments: list[str]) -> None:
            super().__init__()
            self.bridge = bridge
            self.label = label
            self.arguments = arguments

        def run(self) -> None:
            writer = SignalWriter(self.bridge.output.emit)
            code = 1
            try:
                from app.cli import main as grave_main

                with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                    code = int(grave_main(self.arguments))
            except BaseException:  # CLI failures must be visible in the launcher log.
                writer.write(traceback.format_exc())
            self.bridge.command_done.emit(self.label, code)

    class ServerWorker(QThread):
        def __init__(self, bridge: Bridge) -> None:
            super().__init__()
            self.bridge = bridge
            self.server = None

        def stop(self) -> None:
            if self.server is not None:
                self.server.should_exit = True

        def run(self) -> None:
            writer = SignalWriter(self.bridge.output.emit)
            class EmitHandler(logging.Handler):
                def emit(handler_self, record: logging.LogRecord) -> None:
                    try:
                        writer.write(handler_self.format(record) + "\n")
                    except Exception:
                        pass

            handler = EmitHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            captured_loggers = [logging.getLogger(name) for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "alembic")]
            for logger in captured_loggers:
                logger.addHandler(handler)
            try:
                from app.cli.doctor import render_check_lines
                from app.cli.run import prepare

                checks, abort = prepare(no_install=True, no_migrate=False, strict_doctor=False)
                for line in render_check_lines(checks, verbose=True):
                    writer.write(f"{line}\n")
                if abort is not None:
                    self.bridge.server_failed.emit(f"Pre-flight checks failed (exit {abort}).")
                    return

                import uvicorn
                from main import app

                self.server = uvicorn.Server(
                    uvicorn.Config(
                        app,
                        host="127.0.0.1",
                        port=port,
                        log_level="info",
                        log_config=None,
                        ws="websockets-sansio",
                    )
                )
                self.server.install_signal_handlers = lambda: None

                def announce_ready() -> None:
                    deadline = time.time() + 30
                    while time.time() < deadline and not self.server.started:
                        time.sleep(0.1)
                    if self.server.started:
                        self.bridge.server_ready.emit(f"http://127.0.0.1:{port}/")

                threading.Thread(target=announce_ready, daemon=True).start()
                self.server.run()
                code = 0
                self.bridge.server_stopped.emit(code)
            except BaseException:
                detail = traceback.format_exc()
                writer.write(detail)
                self.bridge.server_failed.emit(detail.splitlines()[-1] if detail else "Server failed.")
            finally:
                for logger in captured_loggers:
                    logger.removeHandler(handler)

    class PackagesDialog(QDialog):
        def __init__(self, launcher: "Launcher") -> None:
            super().__init__(launcher)
            self.launcher = launcher
            self.setWindowTitle("Packages")
            self.resize(720, 460)
            layout = QVBoxLayout(self)
            form = QFormLayout()
            self.operation = QComboBox()
            self.operation.addItems(["list", "install", "enable", "disable", "update", "doctor", "remove"])
            self.package_id = QLineEdit()
            self.package_id.setPlaceholderText("Package ID (not required for list)")
            form.addRow("Operation", self.operation)
            form.addRow("Package", self.package_id)
            layout.addLayout(form)
            run = QPushButton("Run package command")
            run.clicked.connect(self.run_command)
            layout.addWidget(run)
            self.output = QTextEdit()
            self.output.setReadOnly(True)
            self.output.setFont(QFont("Cascadia Mono", 9))
            layout.addWidget(self.output, 1)
            close = QPushButton("Close")
            close.clicked.connect(self.accept)
            layout.addWidget(close)
            self.refresh()

        def refresh(self) -> None:
            self.output.setPlainText("See the main launcher log for command output.\n")
            self.launcher.run_cli("Packages", ["package", "list"])

        @Slot()
        def run_command(self) -> None:
            operation = self.operation.currentText()
            package_id = self.package_id.text().strip()
            if operation != "list" and not package_id:
                QMessageBox.warning(self, APP_TITLE, "Enter a package ID.")
                return
            args = ["package", operation]
            if package_id:
                args.append(package_id)
            if operation == "install":
                args.extend(["--yes", "--enable"])
            if operation == "remove":
                args.append("--yes")
            self.launcher.run_cli("Packages", args)

    class Launcher(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.bridge = Bridge()
            self.server_worker: ServerWorker | None = None
            self.command_worker: CommandWorker | None = None
            self.server_url = f"http://127.0.0.1:{port}/"
            self.setWindowTitle(APP_TITLE)
            self.resize(820, 580)
            self.setMinimumSize(680, 480)
            self._build()
            self.bridge.output.connect(self.append_log)
            self.bridge.command_done.connect(self.command_finished)
            self.bridge.server_ready.connect(self.server_started)
            self.bridge.server_stopped.connect(self.server_finished)
            self.bridge.server_failed.connect(self.server_error)
            self.append_log(f"Data folder: {writable_base_dir()}\n")

        def _build(self) -> None:
            root = QWidget()
            self.setCentralWidget(root)
            layout = QVBoxLayout(root)
            title = QLabel("Gravewright Launcher")
            title.setObjectName("title")
            subtitle = QLabel("Run and maintain your local Gravewright table.")
            subtitle.setObjectName("subtitle")
            layout.addWidget(title)
            layout.addWidget(subtitle)
            row = QHBoxLayout()
            actions = [
                ("Start Gravewright", self.toggle_server),
                ("Doctor", lambda: self.run_cli("Doctor", ["doctor", "--verbose"])),
                ("Backup", self.backup),
                ("Restore", self.restore),
                ("Packages", self.packages),
                ("Open data folder", self.open_data),
                ("Logs", self.toggle_logs),
            ]
            self.buttons: list[QPushButton] = []
            for label, callback in actions:
                button = QPushButton(label)
                button.clicked.connect(callback)
                row.addWidget(button)
                self.buttons.append(button)
            layout.addLayout(row)
            status_row = QHBoxLayout()
            self.status = QLabel("Server stopped")
            self.status.setObjectName("status")
            self.open_browser_button = QPushButton("Open in browser")
            self.open_browser_button.setEnabled(False)
            self.open_browser_button.clicked.connect(self.open_browser)
            status_row.addWidget(self.status)
            status_row.addItem(QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            status_row.addWidget(self.open_browser_button)
            layout.addLayout(status_row)
            self.logs = QTextEdit()
            self.logs.setReadOnly(True)
            self.logs.setFont(QFont("Cascadia Mono", 9))
            layout.addWidget(self.logs, 1)
            self.setStyleSheet("""
                QMainWindow, QWidget { background: #111417; color: #e8e9ea; }
                QLabel#title { font-size: 26px; font-weight: 700; color: #e2b85b; }
                QLabel#subtitle { color: #9da5ad; margin-bottom: 12px; }
                QLabel#status { font-weight: 600; padding: 10px 0; }
                QPushButton { background: #252a30; border: 1px solid #454c54; border-radius: 5px; padding: 9px 12px; }
                QPushButton:hover { border-color: #e2b85b; color: #e2b85b; }
                QPushButton:disabled { color: #666; border-color: #333; }
                QTextEdit, QLineEdit, QComboBox { background: #0b0d0f; border: 1px solid #363c43; border-radius: 4px; padding: 6px; }
            """)

        @Slot(str)
        def append_log(self, text: str) -> None:
            cursor = self.logs.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(text)
            self.logs.setTextCursor(cursor)
            self.logs.ensureCursorVisible()

        def run_cli(self, label: str, args: list[str]) -> None:
            if self.command_worker and self.command_worker.isRunning():
                QMessageBox.information(self, APP_TITLE, "Another maintenance command is still running.")
                return
            self.append_log(f"\n$ grave {' '.join(args)}\n")
            self.command_worker = CommandWorker(self.bridge, label, args)
            self.command_worker.start()

        @Slot(str, int)
        def command_finished(self, label: str, code: int) -> None:
            self.append_log(f"[{label} finished with exit code {code}]\n")
            if code != 0:
                QMessageBox.warning(self, APP_TITLE, f"{label} finished with exit code {code}. See Logs.")

        @Slot()
        def toggle_server(self) -> None:
            if self.server_worker and self.server_worker.isRunning():
                self.status.setText("Stopping server…")
                self.server_worker.stop()
                return
            self.status.setText("Preparing server…")
            self.buttons[0].setText("Stop Gravewright")
            self.server_worker = ServerWorker(self.bridge)
            self.server_worker.start()

        @Slot(str)
        def server_started(self, url: str) -> None:
            self.server_url = url
            self.status.setText(f"Running at {url}")
            self.open_browser_button.setEnabled(True)
            self.append_log(f"Server ready: {url}\n")
            if os.environ.get("GRAVEWRIGHT_NO_BROWSER", "").strip().lower() not in {"1", "true", "yes"}:
                self.open_browser()

        @Slot(int)
        def server_finished(self, code: int) -> None:
            self.status.setText("Server stopped")
            self.buttons[0].setText("Start Gravewright")
            self.open_browser_button.setEnabled(False)
            self.append_log(f"Server stopped (exit {code}).\n")

        @Slot(str)
        def server_error(self, detail: str) -> None:
            self.server_finished(1)
            QMessageBox.critical(self, APP_TITLE, f"Could not start Gravewright.\n\n{detail}")

        @Slot()
        def open_browser(self) -> None:
            QDesktopServices.openUrl(QUrl(self.server_url))

        @Slot()
        def backup(self) -> None:
            default = str(writable_base_dir() / f"gravewright-backup-{time.strftime('%Y%m%d-%H%M%S')}.zip")
            path, _ = QFileDialog.getSaveFileName(self, "Create Gravewright backup", default, "ZIP archives (*.zip)")
            if path:
                self.run_cli("Backup", ["backup", "-o", path, "--include-assets", "--include-packages", "--verify"])

        @Slot()
        def restore(self) -> None:
            if self.server_worker and self.server_worker.isRunning():
                QMessageBox.warning(self, APP_TITLE, "Stop Gravewright before restoring a backup.")
                return
            path, _ = QFileDialog.getOpenFileName(self, "Restore Gravewright backup", str(writable_base_dir()), "ZIP archives (*.zip)")
            if not path:
                return
            answer = QMessageBox.question(self, APP_TITLE, "Restore this backup and replace matching assets and packages?")
            if answer == QMessageBox.StandardButton.Yes:
                self.run_cli("Restore", ["restore", path, "--yes", "--replace-assets", "--replace-packages"])

        @Slot()
        def packages(self) -> None:
            PackagesDialog(self).exec()

        @Slot()
        def open_data(self) -> None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(writable_base_dir())))

        @Slot()
        def toggle_logs(self) -> None:
            self.logs.setVisible(not self.logs.isVisible())

        def closeEvent(self, event: QCloseEvent) -> None:
            if self.server_worker and self.server_worker.isRunning():
                self.server_worker.stop()
                self.server_worker.wait(5000)
            event.accept()

    return QApplication, Launcher


def main() -> int:
    configured_port = os.environ.get("GRAVEWRIGHT_PORT", "").strip()
    port = int(configured_port) if configured_port else free_port()
    configure_environment(port)
    _install_bundled_packages()
    QApplication, Launcher = build_ui(port)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("Gravewright")
    window = Launcher()
    window.show()
    if os.environ.get("GRAVEWRIGHT_AUTOSTART", "").strip().lower() in {"1", "true", "yes"}:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, window.toggle_server)
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
