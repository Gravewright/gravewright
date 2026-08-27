from __future__ import annotations

import asyncio

from app.middleware.versioned_asset_cache import VersionedAssetCacheMiddleware


def response_headers(path: str, query: bytes = b"", status: int = 200) -> dict[bytes, bytes]:
    messages: list[dict] = []

    async def downstream(_scope, _receive, send):
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [(b"cache-control", b"no-cache")],
        })
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        messages.append(message)

    middleware = VersionedAssetCacheMiddleware(downstream)
    asyncio.run(middleware({
        "type": "http", "method": "GET", "path": path, "query_string": query,
    }, receive, send))
    return dict(messages[0]["headers"])


def test_versioned_static_asset_is_immutable() -> None:
    headers = response_headers("/static/js/game.js", b"v=abc123")

    assert headers[b"cache-control"] == b"public, max-age=31536000, immutable"


def test_unversioned_static_asset_keeps_revalidation_policy() -> None:
    assert response_headers("/static/js/game.js")[b"cache-control"] == b"no-cache"


def test_versioned_sdk_asset_is_immutable_but_html_is_not() -> None:
    sdk = response_headers("/sdk/packages/example/asset/main.js", b"v=42")
    html = response_headers("/game", b"v=42")

    assert sdk[b"cache-control"] == b"public, max-age=31536000, immutable"
    assert html[b"cache-control"] == b"no-cache"


def test_error_response_is_never_made_immutable() -> None:
    assert response_headers("/static/missing.js", b"v=42", status=404)[b"cache-control"] == b"no-cache"
