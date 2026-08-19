"""Durable workflows: bounded, server-owned multi-step processes.

A workflow is data, not a script. Every executable step is selected from a
closed enum, and all suspension state — a pending decision, a scheduled
wake-up, the step it will resume at — is persisted by core, so a workflow
survives reload, package reload and server restart unchanged.
"""

from __future__ import annotations

import time
from typing import Any

from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.engine.sdk.directed_interaction_service import DirectedInteractionService
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
from app.persistence.repositories.semantic_registration_repository import SemanticRegistrationRepository

from app.engine.sdk.semantic_authority import (
    ACTION_REFERENCE, IDENTIFIER, TERMINAL_STATUSES, SemanticResult,
    is_gm, is_json_safe,
)

class DurableWorkflowService:
    DOMAIN = "workflow"
    REGISTRY = "workflow-definition"
    TYPES = {"ACTION", "INTERACTION", "WAIT_UNTIL", "BRANCH", "SET", "COMPLETE", "FAIL"}
    MAX_STEPS = 128
    MAX_DURATION = 7 * 86_400
    # Canonical context slots the runtime owns; a definition may never claim them.
    RESERVED_CONTEXT_KEYS = {"input", "lastResult", "interaction"}

    def __init__(self):
        self.definitions = SemanticRegistrationRepository()
        self.instances = SemanticInstanceRepository()

    @classmethod
    def _result_key(cls, key: object, request: object) -> str:
        """Validate a scalar interaction projection target.

        The projection is only meaningful when the interaction resolves to exactly
        one authoritative response, so a multi-recipient request is rejected here
        rather than silently picking a winner.
        """
        if not isinstance(key, str) or not IDENTIFIER.fullmatch(key) or key in cls.RESERVED_CONTEXT_KEYS:
            raise ValueError
        recipients = request.get("recipients") if isinstance(request, dict) else None
        if not isinstance(recipients, list) or len(recipients) != 1:
            raise ValueError
        return key

    def register(self, *, campaign_id: str, package_id: str, definition: dict) -> SemanticResult:
        try:
            normalized = self._definition(package_id, definition)
            row = self.definitions.put(campaign_id, package_id, self.REGISTRY, normalized["id"], normalized)
            return SemanticResult(True, {"packageId": package_id, **row["definition"]})
        except (TypeError, ValueError):
            return SemanticResult(False, error_key="sdk.workflows.invalid_definition")

    def start(self, *, campaign_id: str, user_id: str, package_id: str, values: dict) -> SemanticResult:
        try:
            if not isinstance(values, dict) or set(values) - {"definitionId", "input", "sceneId", "idempotencyKey", "origin"}:
                raise ValueError
            definition_id = str(values.get("definitionId") or "")
            row = self.definitions.get(campaign_id, package_id, self.REGISTRY, definition_id)
            if not row:
                return SemanticResult(False, error_key="sdk.workflows.definition_not_found")
            definition = row["definition"]
            inputs = values.get("input", {})
            if not isinstance(inputs, dict) or not is_json_safe(inputs):
                raise ValueError
            key = str(values.get("idempotencyKey") or "")
            if not key or len(key) > 191:
                raise ValueError
            prior = self.instances.by_idempotency(campaign_id, package_id, self.DOMAIN, key)
            if prior:
                return SemanticResult(True, self._public(prior))
            scene_id = values.get("sceneId")
            if scene_id:
                scene = SceneRepository().get_by_id(str(scene_id))
                if not scene or scene["campaign_id"] != campaign_id:
                    return SemanticResult(False, error_key="sdk.workflows.resource_not_found")
            now = int(time.time())
            origin = values.get("origin", {})
            if not isinstance(origin, dict) or not is_json_safe(origin):
                raise ValueError
            instance = self.instances.create({
                "campaign_id": campaign_id, "package_id": package_id, "domain": self.DOMAIN,
                "definition_id": definition_id, "schema_version": definition["schemaVersion"],
                "owner_user_id": user_id, "scene_id": scene_id, "status": "RUNNING",
                "waiting_on": None, "wake_at": None, "idempotency_key": key,
                "payload": {"currentStep": 0, "context": {"input": inputs}, "receipts": {},
                            "startedAt": now, "maxDuration": definition["maxDuration"],
                            "origin": origin, "definitionSnapshot": definition},
            })
            return self._drive(instance)
        except (TypeError, ValueError):
            return SemanticResult(False, error_key="sdk.workflows.invalid_input")

    def get(self, *, campaign_id: str, user_id: str, package_id: str, instance_id: str) -> SemanticResult:
        row = self.instances.get(instance_id)
        if not self._visible(row, campaign_id, user_id, package_id):
            return SemanticResult(False, error_key="sdk.workflows.not_found")
        return SemanticResult(True, self._public(row))

    def list(self, *, campaign_id: str, user_id: str, package_id: str) -> SemanticResult:
        return SemanticResult(True, [self._public(row) for row in self.instances.list(campaign_id, self.DOMAIN, package_id)
                                  if self._visible(row, campaign_id, user_id, package_id)])

    def cancel(self, *, campaign_id: str, user_id: str, package_id: str, instance_id: str, expected_version: int | None) -> SemanticResult:
        row = self.instances.get(instance_id)
        if not self._visible(row, campaign_id, user_id, package_id) or user_id != row["owner_user_id"] and not is_gm(campaign_id, user_id):
            return SemanticResult(False, error_key="sdk.workflows.not_found")
        if row["status"] in TERMINAL_STATUSES:
            return SemanticResult(True, self._public(row))
        if row["status"] == "WAITING_INTERACTION" and row["waiting_on"]:
            DirectedInteractionService().cancel(campaign_id=campaign_id, interaction_id=row["waiting_on"], user_id=user_id)
        changed = self.instances.patch(instance_id, expected_version, status="CANCELLED", waiting_on=None, wake_at=None,
                                       payload={**row["payload"], "completionReason": "cancelled"})
        return SemanticResult(bool(changed), self._public(changed) if changed else None,
                           None if changed else "sdk.workflows.stale_version")

    def resume_interaction(self, *, campaign_id: str, interaction_id: str) -> list[dict]:
        resumed = []
        for row in self.instances.list(campaign_id, self.DOMAIN):
            if row["status"] != "WAITING_INTERACTION" or row["waiting_on"] != interaction_id:
                continue
            interaction = DirectedInteractionService().get(campaign_id=campaign_id, interaction_id=interaction_id, user_id=row["owner_user_id"])
            if not interaction.success or interaction.value["status"] == "open":
                continue
            payload = dict(row["payload"])
            index = int(payload["currentStep"])
            context = {**payload["context"], "lastResult": interaction.value, "interaction": interaction.value}
            projected = self._projection(payload, index, interaction.value)
            if projected is not None:
                context[projected[0]] = projected[1]
            payload["context"] = context
            payload["receipts"] = {**payload["receipts"], str(index): {"interactionId": interaction_id}}
            payload["currentStep"] = index + 1
            changed = self.instances.patch(row["id"], row["version"], status="RUNNING", waiting_on=None, payload=payload)
            if changed:
                result = self._drive(changed)
                if result.success:
                    resumed.append(result.value)
        return resumed

    @staticmethod
    def _projection(payload: dict, index: int, interaction: dict) -> tuple[str, Any] | None:
        """Derive `resultKey` from canonical state only.

        Nothing is projected unless the interaction reached `completed` with the
        single declared recipient's answer recorded, so cancel, expiry and
        provider failure leave the key unset instead of inventing an answer.
        """
        definition = payload.get("definitionSnapshot") or {}
        steps = definition.get("steps") or []
        step = steps[index] if 0 <= index < len(steps) else {}
        key = step.get("resultKey") if isinstance(step, dict) else None
        if not key or interaction.get("status") != "completed":
            return None
        recipients = step.get("request", {}).get("recipients") or []
        responses = interaction.get("responses") or {}
        answer = responses.get(recipients[0]) if len(recipients) == 1 else None
        if not isinstance(answer, dict) or "value" not in answer:
            return None
        return str(key), answer["value"]

    def recover_campaign(self, campaign_id: str, now: int | None = None) -> list[dict]:
        now = int(now or time.time())
        output = []
        for row in self.instances.list(campaign_id, self.DOMAIN):
            if row["status"] == "WAITING_TIME" and int(row["wake_at"] or 0) <= now:
                payload = dict(row["payload"]); payload["currentStep"] += 1
                next_row = self.instances.patch(row["id"], row["version"], status="RUNNING", wake_at=None, payload=payload)
                if next_row:
                    result = self._drive(next_row)
                    if result.success: output.append(result.value)
            elif row["status"] == "WAITING_INTERACTION" and row["waiting_on"]:
                output.extend(self.resume_interaction(campaign_id=campaign_id, interaction_id=row["waiting_on"]))
            elif row["status"] == "RUNNING":
                result = self._drive(row)
                if result.success: output.append(result.value)
        return output

    def _drive(self, row: dict) -> SemanticResult:
        interaction_event=None;action_events=[]
        definition_row = self.definitions.get(row["campaign_id"], row["package_id"], self.REGISTRY, row["definition_id"])
        if not definition_row or definition_row["definition"]["schemaVersion"] != row["schema_version"]:
            failed = self.instances.patch(row["id"], row["version"], status="FAILED",
                                          payload={**row["payload"], "completionReason": "provider-unavailable"})
            return SemanticResult(True, self._public(failed))
        definition = row["payload"].get("definitionSnapshot") or definition_row["definition"]
        while row["status"] == "RUNNING":
            payload = dict(row["payload"]); index = int(payload["currentStep"])
            if int(time.time()) > payload["startedAt"] + definition["maxDuration"]:
                row = self.instances.patch(row["id"], row["version"], status="FAILED",
                                           payload={**payload, "completionReason": "max-duration"})
                break
            if index >= len(definition["steps"]):
                row = self.instances.patch(row["id"], row["version"], status="COMPLETED",
                                           payload={**payload, "completionReason": "complete"})
                break
            step = definition["steps"][index]; receipt_key = str(index)
            if receipt_key in payload["receipts"]:
                payload["currentStep"] += 1
                row = self.instances.patch(row["id"], row["version"], payload=payload)
                continue
            kind = step["type"]
            if kind == "ACTION":
                match = ACTION_REFERENCE.fullmatch(step["action"])
                result = DeclarativeActionService().execute(
                    campaign_id=row["campaign_id"], user_id=row["owner_user_id"], package_id=match.group(1),
                    action_id=match.group(2), version=int(match.group(3)), inputs=step.get("input", {}),
                    idempotency_key=f"workflow:{row['id']}:{index}",
                )
                if not result.success:
                    row = self.instances.patch(row["id"], row["version"], status="FAILED",
                                               payload={**payload, "completionReason": result.error_key})
                    break
                payload["receipts"] = {**payload["receipts"], receipt_key: result.value}
                action_events.append(result.value)
                payload["context"] = {**payload["context"], "lastResult": result.value}
                payload["currentStep"] += 1
                row = self.instances.patch(row["id"], row["version"], payload=payload)
            elif kind == "INTERACTION":
                request = DirectedInteractionService().request(campaign_id=row["campaign_id"], user_id=row["owner_user_id"],
                    package_id=row["package_id"], values=step["request"])
                if not request.success:
                    row = self.instances.patch(row["id"], row["version"], status="FAILED",
                                               payload={**payload, "completionReason": request.error_key})
                    break
                row = self.instances.patch(row["id"], row["version"], status="WAITING_INTERACTION",
                                           waiting_on=request.value["id"], payload=payload)
                interaction_event=request.value
            elif kind == "WAIT_UNTIL":
                wake_at = int(step.get("at") or int(time.time()) + int(step.get("delaySeconds", 0)))
                row = self.instances.patch(row["id"], row["version"], status="WAITING_TIME", wake_at=wake_at, payload=payload)
            elif kind == "SET":
                payload["context"] = {**payload["context"], step["key"]: step.get("value")}
                payload["receipts"] = {**payload["receipts"], receipt_key: {"ok": True}}
                payload["currentStep"] += 1
                row = self.instances.patch(row["id"], row["version"], payload=payload)
            elif kind == "BRANCH":
                actual = payload["context"].get(step["key"])
                payload["currentStep"] = step["then"] if actual == step.get("equals") else step["else"]
                payload["receipts"] = {**payload["receipts"], receipt_key: {"matched": actual == step.get("equals")}}
                row = self.instances.patch(row["id"], row["version"], payload=payload)
            else:
                status = "COMPLETED" if kind == "COMPLETE" else "FAILED"
                row = self.instances.patch(row["id"], row["version"], status=status,
                                           payload={**payload, "output": step.get("output"), "completionReason": step.get("reason", kind.lower())})
        public=self._public(row)
        if interaction_event:public["_interactionEvent"]=interaction_event
        if action_events:public["_actionEvents"]=action_events
        return SemanticResult(True, public)

    def _definition(self, package_id: str, value: dict) -> dict:
        if not isinstance(value, dict) or set(value) - {"id", "schemaVersion", "steps", "maxDuration", "maxSteps"}:
            raise ValueError
        ident = str(value.get("id") or ""); version = value.get("schemaVersion"); steps = value.get("steps")
        if not IDENTIFIER.fullmatch(ident) or version != 1 or not isinstance(steps, list) or not 1 <= len(steps) <= self.MAX_STEPS:
            raise ValueError
        normalized = []
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or step.get("type") not in self.TYPES:
                raise ValueError
            kind = step["type"]
            allowed = {
                "ACTION": {"type", "action", "input"},
                "INTERACTION": {"type", "request", "resultKey"},
                "WAIT_UNTIL": {"type", "at", "delaySeconds"},
                "SET": {"type", "key", "value"},
                "BRANCH": {"type", "key", "equals", "then", "else"},
                "COMPLETE": {"type", "output", "reason"},
                "FAIL": {"type", "output", "reason"},
            }[kind]
            if set(step) - allowed:
                raise ValueError
            if kind == "ACTION":
                match = ACTION_REFERENCE.fullmatch(str(step.get("action") or ""))
                if not match or match.group(1) != package_id or not isinstance(step.get("input", {}), dict): raise ValueError
            elif kind == "INTERACTION":
                if not isinstance(step.get("request"), dict): raise ValueError
                if "resultKey" in step: self._result_key(step["resultKey"], step["request"])
            elif kind == "WAIT_UNTIL" and not (isinstance(step.get("at"), int) or isinstance(step.get("delaySeconds"), int)): raise ValueError
            elif kind == "SET" and (not IDENTIFIER.fullmatch(str(step.get("key") or "")) or not is_json_safe(step.get("value"))): raise ValueError
            elif kind == "BRANCH" and (not IDENTIFIER.fullmatch(str(step.get("key") or "")) or not all(isinstance(step.get(k), int) and index < step[k] < len(steps) for k in ("then", "else"))): raise ValueError
            normalized.append(dict(step))
        duration = int(value.get("maxDuration", 86_400)); max_steps = int(value.get("maxSteps", len(steps)))
        if not 1 <= duration <= self.MAX_DURATION or not len(steps) <= max_steps <= self.MAX_STEPS: raise ValueError
        return {"id": ident, "schemaVersion": 1, "steps": normalized, "maxDuration": duration, "maxSteps": max_steps}

    @staticmethod
    def _visible(row, campaign_id, user_id, package_id):
        return bool(row and row["campaign_id"] == campaign_id and row["package_id"] == package_id and
                    (row["owner_user_id"] == user_id or is_gm(campaign_id, user_id)))

    @staticmethod
    def _public(row):
        p = row["payload"]
        return {"id": row["id"], "definitionId": row["definition_id"], "providerPackageId": row["package_id"],
                "campaignId": row["campaign_id"], "sceneId": row["scene_id"], "status": row["status"],
                "currentStep": p.get("currentStep"), "context": p.get("context", {}), "origin": p.get("origin", {}),
                "createdBy": row["owner_user_id"], "startedAt": p.get("startedAt"), "wakeAt": row["wake_at"],
                "waitingOn": row["waiting_on"], "completionReason": p.get("completionReason"), "version": row["version"]}
