from __future__ import annotations

import os
import subprocess
import sys
from importlib import import_module
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.actions.auth.submit_forgot_password import ForgotPasswordForm
from app.helpers.request import get_client_ip


def _import_config_with_env(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "production",
            "APP_DEBUG": "false",
            "SESSION_SECRET": "strong-secret-for-production-tests",
            "SESSION_COOKIE_SECURE": "true",
            "PUBLIC_BASE_URL": "https://gravewright.test",
            "ALLOWED_HOSTS": "gravewright.test",
            "DATABASE_URL": "postgresql+psycopg://user:pass@localhost/gravewright",
        }
    )
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_production_requires_public_base_url() -> None:
    result = _import_config_with_env({"PUBLIC_BASE_URL": ""})

    assert result.returncode != 0
    assert "PUBLIC_BASE_URL must be set in production" in result.stderr


def test_production_requires_allowed_hosts() -> None:
    result = _import_config_with_env({"ALLOWED_HOSTS": ""})

    assert result.returncode != 0
    assert "ALLOWED_HOSTS must be set in production" in result.stderr


def test_production_refuses_multiple_workers() -> None:
    result = _import_config_with_env({"WEB_WORKERS": "4"})

    assert result.returncode != 0
    assert "WEB_WORKERS must be 1 in production" in result.stderr


def test_production_accepts_single_worker() -> None:
    result = _import_config_with_env({"WEB_WORKERS": "1"})

    assert result.returncode == 0


def test_production_refuses_mysql_backend() -> None:
    result = _import_config_with_env(
        {"DATABASE_URL": "mysql+pymysql://user:pass@localhost/gravewright"}
    )

    assert result.returncode != 0
    assert "MySQL/MariaDB is not a supported production backend" in result.stderr


def test_get_client_ip_ignores_forwarded_headers_from_untrusted_peer() -> None:
    request = SimpleNamespace(
        headers={"x-forwarded-for": "203.0.113.9", "x-real-ip": "203.0.113.10"},
        client=SimpleNamespace(host="198.51.100.5"),
    )

    assert get_client_ip(request) == "198.51.100.5"


def test_get_client_ip_uses_forwarded_headers_from_trusted_proxy(monkeypatch) -> None:
    import app.helpers.request as request_helpers

    monkeypatch.setattr(
        request_helpers,
        "config",
        replace(request_helpers.config, trusted_proxies=("127.0.0.1",)),
    )
    request = SimpleNamespace(
        headers={"x-forwarded-for": "203.0.113.9, 127.0.0.1"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    assert get_client_ip(request) == "203.0.113.9"


@pytest.mark.asyncio
async def test_forgot_password_uses_public_base_url(monkeypatch) -> None:
    forgot_action = import_module("app.actions.auth.submit_forgot_password")

    sent: dict[str, str] = {}

    class FakeAuthService:
        async def forgot_password(
            self,
            *,
            email: str,
            client_ip: str,
            reset_base_url: str,
        ) -> None:
            sent["email"] = email
            sent["client_ip"] = client_ip
            sent["reset_base_url"] = reset_base_url

    monkeypatch.setattr(
        forgot_action,
        "config",
        replace(forgot_action.config, public_base_url="https://configured.example"),
    )
    request = SimpleNamespace(
        base_url="http://spoofed-host.test/",
        headers={},
        client=SimpleNamespace(host="198.51.100.5"),
    )

    await forgot_action.submit_forgot_password.fn(
        request=request,
        cookies={},
        current_user=None,
        auth_service=FakeAuthService(),
        data=ForgotPasswordForm(email="alice@example.test"),
    )

    assert sent == {
        "email": "alice@example.test",
        "client_ip": "198.51.100.5",
        "reset_base_url": "https://configured.example",
    }


def test_production_requires_https_public_base_url() -> None:
    result = _import_config_with_env({"PUBLIC_BASE_URL": "http://gravewright.test"})

    assert result.returncode != 0
    assert "PUBLIC_BASE_URL must use https:// in production" in result.stderr


def test_production_requires_public_base_url_host_in_allowed_hosts() -> None:
    result = _import_config_with_env(
        {
            "PUBLIC_BASE_URL": "https://evil.example",
            "ALLOWED_HOSTS": "gravewright.test",
        }
    )

    assert result.returncode != 0
    assert "PUBLIC_BASE_URL host must be present in ALLOWED_HOSTS" in result.stderr


def test_production_allows_public_base_url_through_configured_tunnel_wildcard() -> None:
    result = _import_config_with_env(
        {
            "PUBLIC_BASE_URL": "https://generated-name.trycloudflare.com",
            "ALLOWED_HOSTS": "gravewright.test",
            "TUNNEL_ALLOWED_HOSTS": "*.trycloudflare.com",
        }
    )

    assert result.returncode == 0


def test_production_rejects_short_session_secret() -> None:
    result = _import_config_with_env({"SESSION_SECRET": "too-short"})

    assert result.returncode != 0
    assert "SESSION_SECRET must be at least 32 characters" in result.stderr


def test_production_rejects_database_echo() -> None:
    result = _import_config_with_env({"DATABASE_ECHO": "true"})

    assert result.returncode != 0
    assert "DATABASE_ECHO must be false in production" in result.stderr


def test_config_rejects_non_positive_limits() -> None:
    result = _import_config_with_env({"WS_MAX_MESSAGE_BYTES": "0"})

    assert result.returncode != 0
    assert "WS_MAX_MESSAGE_BYTES must be greater than zero" in result.stderr
