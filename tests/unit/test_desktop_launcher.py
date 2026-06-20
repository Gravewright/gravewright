from __future__ import annotations

import os

import desktop


def test_desktop_environment_always_allows_local_websocket(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "_writable_base_dir", lambda: tmp_path)
    monkeypatch.setattr(desktop, "_load_user_env", lambda: None)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_HOSTS", "example.test")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("WS_ALLOWED_ORIGINS", "https://example.test")

    desktop._configure_environment("127.0.0.1", 43123)

    assert os.environ["APP_ENV"] == "development"
    assert os.environ["ALLOWED_HOSTS"] == "*"
    assert os.environ["SESSION_COOKIE_SECURE"] == "false"
    assert os.environ["WS_ALLOWED_ORIGINS"].split(",") == [
        "http://127.0.0.1:43123",
        "http://localhost:43123",
        "https://example.test",
    ]


def test_desktop_environment_deduplicates_local_websocket_origins(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "_writable_base_dir", lambda: tmp_path)
    monkeypatch.setattr(desktop, "_load_user_env", lambda: None)
    monkeypatch.setenv(
        "WS_ALLOWED_ORIGINS",
        "http://127.0.0.1:43123,http://localhost:43123",
    )

    desktop._configure_environment("127.0.0.1", 43123)

    assert os.environ["WS_ALLOWED_ORIGINS"].split(",") == [
        "http://127.0.0.1:43123",
        "http://localhost:43123",
    ]
