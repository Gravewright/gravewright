"""Execution boundary for registered actions; never accepts an action graph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from app.engine.rules.declarative_action_registry import ActionContractError, DeclarativeActionRegistry
from app.engine.sdk.runtime_authority import SdkRuntimeAuthority
from app.engine.sheets.sheet_data_service import SheetDataService


@dataclass(frozen=True)
class DeclarativeActionResult:
    success: bool
    value: dict | None = None
    error_key: str | None = None


def _validate_inputs(schema: dict, value: object) -> dict:
    if not isinstance(value, dict):
        raise ActionContractError("sdk.rules.actions.input_invalid")
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(required, list) or any(key not in value for key in required):
        raise ActionContractError("sdk.rules.actions.input_invalid")
    if schema.get("additionalProperties") is False and any(key not in properties for key in value):
        raise ActionContractError("sdk.rules.actions.input_invalid")
    kinds = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}
    for key, item in value.items():
        expected = properties.get(key, {}).get("type") if isinstance(properties.get(key), dict) else None
        if expected in kinds and (not isinstance(item, kinds[expected]) or expected in {"integer", "number"} and isinstance(item, bool)):
            raise ActionContractError("sdk.rules.actions.input_invalid")
    return value


def _resolve(value: Any, inputs: dict) -> Any:
    if isinstance(value, str) and value.startswith("$input."):
        cursor: Any = inputs
        for segment in value[7:].split("."):
            cursor = cursor.get(segment) if isinstance(cursor, dict) else None
        return cursor
    if isinstance(value, dict):
        return {key: _resolve(item, inputs) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, inputs) for item in value]
    return value

def _resolve_patch(patch: dict, inputs: dict) -> dict:
    resolved: dict = {}
    for key, value in patch.items():
        def replace(match):
            dynamic = inputs.get(match.group(1))
            if not isinstance(dynamic, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", dynamic):
                raise ActionContractError("sdk.rules.actions.input_invalid")
            return dynamic
        resolved[re.sub(r"\$input\.([A-Za-z0-9_-]+)", replace, str(key))] = _resolve(value, inputs)
    return resolved


class DeclarativeActionService:
    def execute(self, *, campaign_id: str, user_id: str, package_id: str, action_id: str, version: int | None, inputs: object, idempotency_key: str | None = None, fault=None) -> DeclarativeActionResult:
        try:
            action = DeclarativeActionRegistry().get(package_id, action_id, version)
            typed = _validate_inputs(action.inputs, inputs)
        except ActionContractError as exc:
            return DeclarativeActionResult(False, error_key=exc.code)
        if action.idempotency == "REQUIRES_IDEMPOTENCY_KEY":
            if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 191:
                return DeclarativeActionResult(False, error_key="sdk.rules.actions.idempotency_key_required")
            if action.durability != "supported":
                return DeclarativeActionResult(False, error_key="sdk.rules.actions.not_durable")
        if action.idempotency == "NOT_DURABLE" and idempotency_key:
            return DeclarativeActionResult(False, error_key="sdk.rules.actions.not_durable")
        changed: list[dict] = []
        execution_id = str(uuid4())
        for operation in action.operations:
            capability = action.required_capabilities[0]
            authority = SdkRuntimeAuthority().authorize(campaign_id=campaign_id, user_id=user_id, package_id=package_id, capability=capability)
            if not authority.allowed:
                return DeclarativeActionResult(False, error_key=authority.error_key)
            if operation["op"] == "actor.data.patch":
                actor_id = _resolve(operation.get("actorId"), typed)
                try:
                    patch = _resolve_patch(operation["patch"], typed)
                except ActionContractError as exc:
                    return DeclarativeActionResult(False, error_key=exc.code)
                if action.idempotency == "REQUIRES_IDEMPOTENCY_KEY":
                    canonical = json.dumps({"inputs": typed}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    identity = f"{package_id}:{action.action_id}@{action.version}:{idempotency_key.strip()}"
                    result = SheetDataService().patch_data_idempotent(actor_id=str(actor_id or ""), user_id=user_id, patch=patch, receipt_identity=identity, payload_hash=payload_hash, execution_id=execution_id, fault=fault)
                else:
                    result = SheetDataService().patch_data(actor_id=str(actor_id or ""), user_id=user_id, patch=patch)
                if not result.success or result.campaign_id != campaign_id:
                    return DeclarativeActionResult(False, error_key=result.error_key or "sdk.runtime.not_found")
                if result.receipt:
                    execution_id = str(result.receipt["executionId"])
                changed.append({"type": "actor", "id": result.actor_id, "version": result.version})
        return DeclarativeActionResult(True, {"action": action.action_id, "version": action.version, "reference": action.reference, "executionId": execution_id, "result": {"ok": True}, "changedResources": changed})
