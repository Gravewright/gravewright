from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.sheets.sheet_action_service import ActionResult, SheetActionService
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.chat_message_repository import ChatMessageRepository


@dataclass(frozen=True)
class RerollResult:
    success: bool
    roll: ActionResult | None = None
    version: int | None = None
    error_key: str | None = None


def _critical_failure(metadata: dict) -> bool:
    rendered = metadata.get("rendered") if isinstance(metadata, dict) else {}
    card = rendered.get("chatCard") if isinstance(rendered, dict) else {}
    outcome = card.get("outcome") if isinstance(card, dict) else {}
    return bool(
        isinstance(card, dict)
        and (
            card.get("tone") == "critical-failure"
            or (isinstance(outcome, dict) and outcome.get("criticalFailure"))
        )
    )


class RollRerollService:
    """Authoritative, one-shot Savage Worlds trait rerolls paid with one Benny."""

    def __init__(self) -> None:
        self.messages = ChatMessageRepository()
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.actions = SheetActionService()
        self.rules = SystemRulesService()

    def reroll(self, *, campaign_id: str, message_id: str, user_id: str) -> RerollResult:
        message = self.messages.get_for_campaign(campaign_id=campaign_id, message_id=message_id)
        metadata = message.get("metadata") if isinstance(message, dict) else {}
        if not message or message.get("kind") != "roll" or metadata.get("systemId") != "savage-worlds":
            return RerollResult(False, error_key="game.rolls.reroll.invalid")
        if _critical_failure(metadata):
            return RerollResult(False, error_key="game.rolls.reroll.critical_failure")
        actor_id = str(metadata.get("actorId") or "")
        action_id = str(metadata.get("actionId") or "")
        action = self.rules.get_action("savage-worlds", action_id)
        if isinstance(action, dict) and isinstance(action.get("selfResolution"), dict):
            return RerollResult(False, error_key="game.rolls.reroll.self_resolving_action")
        actor = self.actors.get(actor_id)
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        authored = message.get("author_user_id") == user_id or (campaign and campaign.get("member_role") == "gm")
        if not actor or not campaign or not authored or actor.get("campaign_id") != campaign_id or not can_edit_actor(actor=actor, campaign=dict(campaign), user_id=user_id):
            return RerollResult(False, error_key="game.rolls.reroll.not_allowed")
        receipt_id = f"reroll:{message_id}"
        with self.storage.lock_entity(kind="actor", system_id=actor["system_id"], campaign_id=campaign_id, entity_id=actor_id):
            envelope = self.storage.read_actor(system_id=actor["system_id"], campaign_id=campaign_id, actor_id=actor_id) or {"version": 1, "data": {}}
            receipts = envelope.get("_core_action_receipts") if isinstance(envelope.get("_core_action_receipts"), list) else []
            if any(entry.get("identity") == receipt_id for entry in receipts if isinstance(entry, dict)):
                return RerollResult(False, error_key="game.rolls.reroll.already_used")
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
            bennies = data.get("bennies") if isinstance(data.get("bennies"), dict) else {}
            current = int(bennies.get("value") or 0)
            if current < 1:
                return RerollResult(False, error_key="game.rolls.reroll.no_bennies")
            roll = self.actions.execute(actor_id=actor_id, action_id=action_id, user_id=user_id, item=metadata.get("item") if isinstance(metadata.get("item"), dict) else None, roll_options=metadata.get("rollInput") if isinstance(metadata.get("rollInput"), dict) else None)
            if not roll.success:
                return RerollResult(False, error_key=roll.error_key)
            bennies["value"] = current - 1
            data["bennies"] = bennies
            version = int(envelope.get("version", 1)) + 1
            receipts = [*receipts[-127:], {"identity": receipt_id, "payloadHash": sha256(message_id.encode()).hexdigest(), "version": version, "expiresAt": 4_102_444_800}]
            self.storage.write_actor(system_id=actor["system_id"], campaign_id=campaign_id, actor_id=actor_id, version=version, data=data, action_receipts=receipts)
        from dataclasses import replace
        original = int(message.get("total") or 0)
        rolled_total = int(roll.total or 0)
        original_pool = metadata.get("pool") if isinstance(metadata.get("pool"), dict) else None
        rolled_pool = roll.metadata.get("pool") if isinstance(roll.metadata.get("pool"), dict) else None
        keep_original = original > rolled_total
        if original_pool is not None and rolled_pool is not None:
            original_score = (
                int(original_pool.get("hits") or 0),
                int(original_pool.get("raises") or 0),
                original,
            )
            rolled_score = (
                int(rolled_pool.get("hits") or 0),
                int(rolled_pool.get("raises") or 0),
                rolled_total,
            )
            keep_original = original_score > rolled_score
        if keep_original:
            roll = replace(
                roll,
                total=original,
                groups=message.get("groups") if isinstance(message.get("groups"), list) else roll.groups,
                modifier=int(message.get("modifier") or 0),
                expression=str(message.get("expression") or roll.expression or ""),
                metadata={**roll.metadata, **({"pool": original_pool} if original_pool else {})},
            )
        kept = int(roll.total or 0)
        enriched = dict(roll.metadata or {}) | {
            "rerollOf": message_id,
            "reroll": {"original": original, "rolled": rolled_total, "kept": kept, "cost": 1},
        }
        return RerollResult(True, replace(roll, metadata=enriched, label=f"{roll.label} — Rerrolagem"), version=version)
