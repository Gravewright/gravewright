from __future__ import annotations

import threading

import pytest

from app.helpers.async_blocking import run_blocking


@pytest.mark.asyncio
async def test_run_blocking_returns_value_from_worker_thread():
    main_thread = threading.get_ident()

    def work(value: int, *, scale: int) -> tuple[int, bool]:
        return value * scale, threading.get_ident() != main_thread

    result, used_worker = await run_blocking(work, 7, scale=6)

    assert result == 42
    assert used_worker
