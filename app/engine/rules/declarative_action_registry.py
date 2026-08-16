"""Validated public registry for bounded, declarative package actions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from app.engine.sdk import package_registry
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_paths import safe_join

ACTION_ID = re.compile(r"^[a-z][a-z0-9._-]{0,95}$")
IDEMPOTENCY = {"IDEMPOTENT", "REQUIRES_IDEMPOTENCY_KEY", "NOT_DURABLE"}
OPERATIONS = {"actor.data.patch": "actors.data.write"}
MAX_ACTIONS = 128
MAX_STEPS = 16
MAX_SCHEMA_BYTES = 16_384


class ActionContractError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RegisteredAction:
    package_id: str
    action_id: str
    version: int
    inputs: dict
    required_capabilities: tuple[str, ...]
    operations: tuple[dict, ...]
    idempotency: str
    limits: dict
    semantics: tuple[str, ...] = ()

    @property
    def reference(self) -> str:
        return f"{self.package_id}:{self.action_id}@{self.version}"

    @property
    def durability(self) -> str:
        # Derived by core from the operation topology; packages cannot assert it.
        return "supported" if len(self.operations) == 1 and self.operations[0].get("op") == "actor.data.patch" else "unsupported"

    def public(self) -> dict:
        return {
            "id": self.action_id,
            "packageId": self.package_id,
            "version": self.version,
            "reference": self.reference,
            "inputs": self.inputs,
            "requiredCapabilities": list(self.required_capabilities),
            "idempotency": self.idempotency,
            "durability": self.durability,
            "limits": self.limits,
            "semantics": list(self.semantics),
        }


def _validate_definition(package_id: str, raw: object, capabilities: set[str]) -> RegisteredAction:
    if not isinstance(raw, dict):
        raise ActionContractError("sdk.rules.actions.definition_invalid")
    action_id = raw.get("id")
    version = raw.get("version")
    inputs = raw.get("inputs", {"type": "object", "properties": {}})
    operations = raw.get("operations")
    idempotency = raw.get("idempotency")
    if not isinstance(action_id, str) or not ACTION_ID.fullmatch(action_id):
        raise ActionContractError("sdk.rules.actions.id_invalid")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ActionContractError("sdk.rules.actions.version_invalid")
    if not isinstance(inputs, dict) or len(json.dumps(inputs, separators=(",", ":"))) > MAX_SCHEMA_BYTES:
        raise ActionContractError("sdk.rules.actions.inputs_invalid")
    if inputs.get("type") != "object" or not isinstance(inputs.get("properties", {}), dict):
        raise ActionContractError("sdk.rules.actions.inputs_invalid")
    if idempotency not in IDEMPOTENCY:
        raise ActionContractError("sdk.rules.actions.idempotency_required")
    if not isinstance(operations, list) or not operations or len(operations) > MAX_STEPS:
        raise ActionContractError("sdk.rules.actions.operations_invalid")
    required: set[str] = set()
    clean: list[dict] = []
    for operation in operations:
        if not isinstance(operation, dict) or operation.get("op") not in OPERATIONS:
            raise ActionContractError("sdk.rules.actions.operation_unsupported")
        capability = OPERATIONS[str(operation["op"])]
        if capability not in capabilities:
            raise ActionContractError("sdk.rules.actions.capability_unknown")
        if operation["op"] == "actor.data.patch" and not isinstance(operation.get("patch"), dict):
            raise ActionContractError("sdk.rules.actions.operation_invalid")
        required.add(capability)
        clean.append(operation)
    semantics = raw.get("semantics", [])
    if not isinstance(semantics, list) or len(semantics) > 16 or any(not isinstance(value, str) or not ACTION_ID.fullmatch(value) for value in semantics):
        raise ActionContractError("sdk.rules.actions.semantics_invalid")
    return RegisteredAction(package_id, action_id, version, inputs, tuple(sorted(required)), tuple(clean), str(idempotency), {"maxSteps": MAX_STEPS}, tuple(dict.fromkeys(semantics)))


class DeclarativeActionRegistry:
    def _raw(self, package_id: str) -> tuple[list, set[str]]:
        loaded = package_registry.load_by_package_id(package_id)
        manifest = PackageInstallService().get_active_manifest(package_id)
        if loaded is None or manifest is None:
            raise ActionContractError("sdk.runtime.package_disabled")
        relative = manifest.rules.get("actionRegistry", "")
        path = safe_join(loaded.package_dir, relative) if relative else None
        if path is None or not path.is_file():
            return [], set(manifest.capabilities)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ActionContractError("sdk.rules.actions.registry_invalid") from exc
        definitions = document.get("actions") if isinstance(document, dict) else None
        if not isinstance(definitions, list) or len(definitions) > MAX_ACTIONS:
            raise ActionContractError("sdk.rules.actions.registry_invalid")
        return definitions, set(manifest.capabilities)

    def list(self, package_id: str) -> list[RegisteredAction]:
        raw, capabilities = self._raw(package_id)
        valid: list[RegisteredAction] = []
        identities: set[tuple[str, int]] = set()
        for definition in raw:
            try:
                action = _validate_definition(package_id, definition, capabilities)
            except ActionContractError:
                continue
            identity = (action.action_id, action.version)
            if identity not in identities:
                identities.add(identity)
                valid.append(action)
        return valid

    def get(self, package_id: str, action_id: str, version: int | None = None) -> RegisteredAction:
        candidates = [a for a in self.list(package_id) if a.action_id == action_id]
        if not candidates:
            raise ActionContractError("sdk.rules.actions.not_found")
        if version is not None:
            match = next((a for a in candidates if a.version == version), None)
            if match is None:
                raise ActionContractError("sdk.rules.actions.version_unsupported")
            return match
        return max(candidates, key=lambda action: action.version)

    def resolve_active_ruleset(self, campaign_id: str, semantic: str) -> RegisteredAction:
        from app.engine.sdk.package_activation_service import PackageActivationService
        record = PackageActivationService().get_active_ruleset(campaign_id)
        if not record:
            raise ActionContractError("sdk.rules.actions.semantic_not_found")
        matches = [entry for entry in self.list(str(record["package_id"])) if semantic in entry.semantics]
        if not matches:
            raise ActionContractError("sdk.rules.actions.semantic_not_found")
        return max(matches, key=lambda entry: entry.version)


def validate_registry_file(package_id: str, raw: object, capabilities: set[str]) -> list[str]:
    definitions = raw.get("actions") if isinstance(raw, dict) else None
    if not isinstance(definitions, list) or len(definitions) > MAX_ACTIONS:
        return ["sdk.rules.actions.registry_invalid"]
    errors: list[str] = []
    seen: set[tuple[str, int]] = set()
    for definition in definitions:
        try:
            action = _validate_definition(package_id, definition, capabilities)
            identity = (action.action_id, action.version)
            if identity in seen:
                errors.append("sdk.rules.actions.identity_duplicate")
            seen.add(identity)
        except ActionContractError as exc:
            errors.append(exc.code)
    return list(dict.fromkeys(errors))
