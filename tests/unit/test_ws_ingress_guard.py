from __future__ import annotations

import json

from app.realtime.ingress_guard import MAX_MESSAGE_BYTES
from app.realtime.ingress_guard import WebSocketIngressGuard
from app.realtime.ingress_guard import is_origin_allowed


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _command(name: str, command_id: str = "cmd-1") -> str:
    return json.dumps({"type": "command", "id": command_id, "command": name, "payload": {}})


def test_oversized_message_closes_with_1009() -> None:
    guard = WebSocketIngressGuard()
    raw = "x" * (MAX_MESSAGE_BYTES + 1)

    decision = guard.inspect(raw)

    assert decision.should_close is True
    assert decision.close_code == 1009


def test_invalid_json_is_rejected_without_closing() -> None:
    guard = WebSocketIngressGuard()

    decision = guard.inspect("{not json")

    assert decision.should_close is False
    assert decision.error is not None
    assert decision.error["code"] == "invalid_payload"


def test_non_object_message_is_rejected() -> None:
    guard = WebSocketIngressGuard()

    decision = guard.inspect(json.dumps([1, 2, 3]))

    assert decision.error is not None
    assert decision.message is None


def test_valid_message_passes_through() -> None:
    guard = WebSocketIngressGuard()

    decision = guard.inspect(_command("token.move"))

    assert decision.error is None
    assert decision.close_code is None
    assert decision.message is not None
    assert decision.message["command"] == "token.move"


def test_per_command_rate_limit_trips_then_recovers() -> None:
    clock = _Clock()
    guard = WebSocketIngressGuard(clock=clock)

                                                                             
    limited = False
    for _ in range(200):
        decision = guard.inspect(_command("viewport.update"))
        if decision.error is not None and decision.error["code"] == "rate_limited":
            limited = True
            break
    assert limited is True

                                                                   
    clock.advance(10.0)
    decision = guard.inspect(_command("viewport.update"))
    assert decision.message is not None


def test_expensive_commands_have_tight_budget() -> None:
    clock = _Clock()
    guard = WebSocketIngressGuard(clock=clock)

    accepted = 0
    for _ in range(50):
        decision = guard.inspect(_command("viewport.subscribe"))
        if decision.message is not None:
            accepted += 1
        else:
            break

                                                                          
    assert accepted <= 8


def test_origin_allowlist() -> None:
                                                                   
    assert is_origin_allowed(None, ()) is True
    assert is_origin_allowed("https://evil.test", ()) is True

    allowed = ("https://table.example",)
    assert is_origin_allowed("https://table.example", allowed) is True
    assert is_origin_allowed("https://table.example/", allowed) is True
    assert is_origin_allowed("https://evil.test", allowed) is False
    assert is_origin_allowed(None, allowed) is False


def test_origin_allowlist_accepts_tunnel_wildcards() -> None:
    allowed = ("https://*.trycloudflare.com", "https://*.ngrok-free.app")

    assert is_origin_allowed("https://random-name.trycloudflare.com", allowed) is True
    assert is_origin_allowed("https://demo.ngrok-free.app/", allowed) is True
    assert is_origin_allowed("https://trycloudflare.com", allowed) is False
    assert is_origin_allowed("http://random-name.trycloudflare.com", allowed) is False
