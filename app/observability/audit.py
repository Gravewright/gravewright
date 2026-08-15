"""Structured audit events for security-relevant operations.

Thin wrapper over ``emit_diagnostic`` that records *what happened to what*, by
whom, and the result: with internal IDs only. Redaction and request-id
correlation are inherited from ``emit_diagnostic``, so a code/token/cookie passed
here by mistake is still masked (maintenance plan, Etapa 10).

Examples of auditable actions: ``schema.mismatch``, ``login.blocked``,
``membership.created``, ``membership.removed``, ``permission.changed``,
``package.activated``.
"""

from __future__ import annotations

from typing import Any

from app.observability.diagnostics import emit_diagnostic


def emit_audit(
    action: str,
    *,
    actor_id: str | None = None,
    result: str = "ok",
    level: str = "info",
    **fields: Any,
) -> None:
    """Record one audit event as ``audit.<action>`` with actor/result/context."""
    emit_diagnostic(
        f"audit.{action}",
        level=level,
        actor_id=actor_id,
        result=result,
        **fields,
    )
