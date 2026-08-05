from __future__ import annotations

import pytest

from app.middleware.request_id import RequestIdMiddleware
from app.observability.request_context import get_request_id, set_request_id


async def _call(*, inbound: bytes | None = None, app=None):
    seen = []

    async def default_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-request-id", b"from-handler")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    headers = [] if inbound is None else [(b"x-request-id", inbound)]

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        seen.append(message)

    await RequestIdMiddleware(app or default_app)(
        {"type": "http", "headers": headers}, receive, send
    )
    return seen[0]["headers"]


@pytest.mark.asyncio
async def test_response_has_exactly_one_generated_request_id():
    headers = await _call()
    values = [value for name, value in headers if name.lower() == b"x-request-id"]
    assert len(values) == 1
    assert values[0] != b"from-handler"


@pytest.mark.asyncio
async def test_valid_request_id_is_preserved():
    headers = await _call(inbound=b"client-id_123")
    assert (b"x-request-id", b"client-id_123") in headers


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [b"", b"contains spaces", b"x" * 65, b"bad\r\nheader"])
async def test_invalid_request_id_is_replaced(value):
    headers = await _call(inbound=value)
    request_id = next(value for name, value in headers if name == b"x-request-id")
    assert request_id != value


@pytest.mark.asyncio
async def test_previous_context_is_restored():
    token = set_request_id("outer")
    try:
        await _call(inbound=b"inner")
        assert get_request_id() == "outer"
    finally:
        from app.observability.request_context import reset_request_id

        reset_request_id(token)
