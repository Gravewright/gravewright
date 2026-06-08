from __future__ import annotations

from litestar.testing import TestClient


def test_chrome_devtools_probe_is_silenced():
    from main import app

    with TestClient(app=app) as client:
        response = client.get("/.well-known/appspecific/com.chrome.devtools.json")

    assert response.status_code == 204
    assert response.content == b""
