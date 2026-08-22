from __future__ import annotations

import re

from litestar.testing import TestClient

from main import app


def test_safe_request_replaces_csrf_cookie_from_another_installation() -> None:
    with TestClient(app=app) as client:
        client.cookies.set(
            "csrftoken",
            "stale-token-from-another-installation",
            domain="testserver.local",
            path="/",
        )

        response = client.get("/login")

        assert response.status_code == 200
        token_match = re.search(
            r'name="_csrf_token"[^>]*value="([^"]+)"', response.text
        )
        assert token_match is not None
        replacement = client.cookies.get("csrftoken")
        assert replacement != "stale-token-from-another-installation"
        assert replacement == token_match.group(1)

        post_response = client.post(
            "/login",
            data={
                "email": "missing-user@example.invalid",
                "password": "invalid",
                "_csrf_token": replacement,
            },
        )
        assert post_response.status_code != 403
