from __future__ import annotations

"""Event-loop non-blocking guard (Maintenance Plan - Etapa 3).

The chosen concurrency pattern is: purely-synchronous HTTP handlers are declared
``def ... sync_to_thread=True`` and mixed handlers wrap their synchronous unit in
``await run_blocking(...)``. Both route the blocking DB work through anyio's
worker-thread offload, so a slow database call cannot serialize independent
requests on the event loop.

These tests prove the mechanism keeps the loop responsive (deterministically,
via a heartbeat counter rather than sleeps) and that an exception inside an
offloaded transaction propagates and rolls back. A source-level guard asserts the
priority handlers actually use the pattern, so a regression to a blocking
``async def`` is caught.

Note: Litestar's TestClient drives the app through a blocking anyio portal that
serializes ASGI calls, so it cannot exercise true event-loop concurrency; we test
the offload mechanism the handlers use (``run_blocking`` / ``sync_to_thread``,
both anyio ``to_thread``) directly.
"""

import asyncio
import threading
from pathlib import Path

import pytest

from app.helpers.async_blocking import run_blocking

ACTIONS_ROOT = Path(__file__).resolve().parents[2] / "app" / "actions"


@pytest.mark.asyncio
async def test_run_blocking_keeps_event_loop_responsive():
    """While a blocking call is in flight, the loop still runs other coroutines."""
    entered = threading.Event()
    release = threading.Event()
    ticks = 0

    def slow_blocking_call() -> str:
        # Stands in for a slow synchronous DB transaction.
        entered.set()
        assert release.wait(timeout=5.0), "heartbeat never released the blocker"
        return "done"

    async def heartbeat() -> None:
        nonlocal ticks
        while not release.is_set():
            ticks += 1
            await asyncio.sleep(0.005)

    async def scenario() -> None:
        nonlocal ticks
        blocking_task = asyncio.ensure_future(run_blocking(slow_blocking_call))
        heartbeat_task = asyncio.ensure_future(heartbeat())

        # Wait until the blocking call is actually executing in its worker thread.
        while not entered.is_set():
            await asyncio.sleep(0.005)

        # The loop kept advancing the heartbeat while the blocking call was
        # stuck in its thread — i.e. an independent route would still respond.
        ticks_before = ticks
        await asyncio.sleep(0.05)
        assert ticks > ticks_before, "event loop was blocked by the offloaded call"

        release.set()
        assert await blocking_task == "done"
        await heartbeat_task

    await asyncio.wait_for(scenario(), timeout=10.0)


@pytest.mark.asyncio
async def test_run_blocking_runs_off_the_loop_thread():
    loop_thread = threading.get_ident()

    def where_am_i() -> int:
        return threading.get_ident()

    worker_thread = await run_blocking(where_am_i)
    assert worker_thread != loop_thread


def _insert_user_then_fail() -> None:
    import time
    import uuid

    from app.persistence.database import engine_begin

    with engine_begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO users (id, name, email, password_hash, system_role, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'user', ?, ?)",
            (
                uuid.uuid4().hex,
                "Rollback",
                "rollback@test.com",
                "x",
                int(time.time()),
                int(time.time()),
            ),
        )
        raise RuntimeError("boom inside offloaded transaction")


@pytest.mark.asyncio
async def test_exception_inside_offloaded_transaction_rolls_back(db):
    from app.persistence.database import engine_connect

    with pytest.raises(RuntimeError, match="boom"):
        await run_blocking(_insert_user_then_fail)

    # The failed transaction must not have persisted the row.
    with engine_connect() as conn:
        count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM users WHERE email = 'rollback@test.com'"
        ).scalar()
    assert count == 0


# Files converted to the offload pattern in this stage.
_PURE_SYNC_HANDLERS = [
    "inside/create_campaign.py",
    "inside/update_campaign.py",
    "inside/delete_campaign.py",
    "inside/request_delete_campaign.py",
    "inside/decline_campaign_invitation.py",
    "inside/list_campaign_invitations.py",
    "inside/show_inside.py",
    "game/invite_to_campaign.py",
    "auth/submit_login.py",
    "auth/submit_register.py",
    "auth/submit_reset_password.py",
    "auth/logout.py",
]
_MIXED_HANDLERS = [
    "game/ban_member.py",
    "inside/accept_campaign_invitation.py",
]


@pytest.mark.parametrize("rel", _PURE_SYNC_HANDLERS)
def test_pure_sync_handlers_offload_via_sync_to_thread(rel):
    source = (ACTIONS_ROOT / rel).read_text(encoding="utf-8")
    assert "sync_to_thread=True" in source, f"{rel} must declare sync_to_thread=True"
    # The route function itself must be synchronous (offloaded by the framework),
    # not a blocking ``async def``.
    assert "\nasync def " not in source, f"{rel} handler should be a plain def"


@pytest.mark.parametrize("rel", _MIXED_HANDLERS)
def test_mixed_handlers_offload_sync_unit_with_run_blocking(rel):
    source = (ACTIONS_ROOT / rel).read_text(encoding="utf-8")
    assert "run_blocking(" in source, f"{rel} must offload its sync unit via run_blocking"
