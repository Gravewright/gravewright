"""Capability-gated semantic runtime API for SDK 1 packages."""

from __future__ import annotations

from typing import Any
import json

from litestar import Request, get, post
from litestar.params import FromPath, FromQuery
from litestar.response import Response

from app.business.permissions.permission_service import PermissionService
from app.engine.actors.actor_service import ActorService
from app.engine.combat.combat_service import CombatService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.business.handouts import HandoutService, dispatch_handout_presentation
from app.config import config
from app.persistence.repositories.journal_repository import JournalRepository
from app.engine.scenes.scene_service import SceneService
from app.engine.scenes.scene_light_service import SceneLightService
from app.engine.scenes.scene_particle_service import PARTICLE_PRESETS, SceneParticleService
from app.engine.scenes.scene_shader_service import SceneShaderService
from app.engine.scenes.scene_wall_service import SceneWallService
from app.engine.scenes.fog_service import FogService
from app.engine.scenes.scene_image_service import SceneImageService
from app.engine.scenes.scene_template_service import SceneTemplateService
from app.domain.fog import FogInitialState
from app.realtime.fog_command_handler import _parse_op
from app.engine.sdk.runtime_authority import SdkRuntimeAuthority
from app.engine.sdk.runtime_permissions import SdkRuntimePermissionInspector
from app.engine.sdk.package_asset_service import PackageAssetService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.runtime_dto import actor_snapshot, chat_snapshot, item_snapshot, light_snapshot, particle_snapshot, scene_snapshot, shader_metadata_snapshot, wall_snapshot
from app.engine.sdk.pdf_service import SdkPdfService
from app.engine.sdk.ephemeral_domain_service import TokenTargetService, SharedMeasurementService, PdfPresentationService
from app.engine.sdk.content_reference_service import ContentReferenceService
from app.engine.decks.card_service import CardService
from app.engine.decks.cards import CardFaceState, DrawDestination, DrawMode
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.item_sheet_data_service import ItemSheetDataService
from app.engine.sheets.actor_item_copy_service import ActorItemCopyService
from app.engine.rules.declarative_action_registry import DeclarativeActionRegistry, ActionContractError
from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.engine.rules.automation_service import AutomationService
from app.engine.assets.asset_ingestion_service import AssetIngestionService
from app.engine.chat.chat_service import ChatService
from app.engine.tokens.token_service import TokenService
from app.engine.tokens.token_hp_service import TokenHpService
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.chat_message_repository import ChatMessageRepository
from app.persistence.rows import Row
from app.realtime.transport import RealtimeTransport
from app.realtime.events import TransportEvent
from app.engine.actors.actor_permissions import can_view_actor
from app.engine.items.item_permissions import can_view_item
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.helpers.auth import require_user
from app.helpers.async_blocking import run_blocking


_RESOURCE_CAPABILITIES = {
    "actors": "actors.read",
    "actors.data": "actors.read",
    "items": "items.read",
    "tokens": "tokens.read",
    "scenes": "scene.read",
    "combat": "combat.read",
    "permissions": "permissions.inspect",
    "packages": "packages.inspect",
    "geometry": "scene.geometry.read",
    "effects": "scene.effects.read",
    "effects.presets": "scene.effects.read",
    "shader.presets": "scene.shaders.read",
    "shader.preset": "scene.shaders.read",
    "shader.instances": "scene.shaders.read",
    "fog": "scene.fog.read",
    "scene.images": "scene.images.read",
    "scene.templates": "scene.templates.read",
    "chat": "chat.read",
    "journals": "journals.read",
    "pdf": "pdf.read",
    "pdf.viewer": "pdf.viewer",
    "pdf.annotations": "pdf.annotations.read",
    "cards": "cards.read",
    "card.definitions": "cards.read",
    "content.references": "content.references",
    "content.index": "content.index",
    "rules.actions": "rules.actions",
    "actor.item.slots": "actors.items.read",
    "actor.item.copies": "actors.items.read",
    "token.targets": "tokens.targets",
    "shared.measurements": "scene.measurements.shared",
    "pdf.presentation": "pdf.presentation",
    "automation.jobs": "automation.schedule",
    "automation.audit": "automation.schedule",
}


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _card_asset_urls(payload: dict[str, Any]) -> dict[str, Any]:
    for card in payload.get("cards", []) if isinstance(payload.get("cards"), list) else []:
        if not isinstance(card, dict):
            continue
        asset_id = card.get("front_asset_id")
        card["front_asset_url"] = f"/game/journal/asset/{asset_id}" if asset_id else None
    return payload


def _error(error_key: str, status_code: int) -> Response[dict[str, Any]]:
    codes = {
        400: "VALIDATION_FAILED", 403: "PERMISSION_DENIED", 404: "NOT_FOUND", 409: "STALE_VERSION"
    }
    code = codes.get(status_code, "UNSUPPORTED")
    if error_key in {"UNSUPPORTED_MEDIA_TYPE", "RATE_LIMITED", "VALIDATION_FAILED", "PERMISSION_DENIED", "NOT_FOUND"}:
        code = error_key
    elif "package_inactive" in error_key or "package_disabled" in error_key:
        code = "PACKAGE_INACTIVE"
    elif "capability_required" in error_key:
        code = "CAPABILITY_REQUIRED"
    elif "idempotency_conflict" in error_key:
        code = "IDEMPOTENCY_CONFLICT"
    elif "not_durable" in error_key:
        code = "NOT_DURABLE"
    elif "rate_limited" in error_key or ".quota" in error_key:
        code = "RATE_LIMITED"
    return Response(
        {"error": {"code": code, "message": error_key}, "error_key": error_key},
        status_code=status_code,
    )


async def _body(request: Request) -> dict[str, Any]:
    try:
        value = await request.json()
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _service_error(error_key: str | None) -> Response[dict[str, Any]]:
    key = error_key or "sdk.runtime.validation_failed"
    lowered=key.lower()
    if "stale" in lowered or "version_conflict" in lowered:
        return _error(key, 409)
    if "denied" in lowered or "required" in lowered or "not_allowed" in lowered:
        return _error(key, 403)
    if "not_found" in lowered:
        return _error(key, 404)
    return _error(key, 400)


def _resource_in_campaign(row: dict[str, Any] | None, campaign_id: str) -> bool:
    """Bind an ID-addressed SDK mutation to its authorized campaign."""
    return bool(row and row.get("campaign_id") == campaign_id)


async def _emit_resource_event(*, kind: str, event: TransportEvent, campaign_id: str, resource_id: str, version: int | None = None) -> None:
    row = ActorRepository().get(resource_id) if kind == "actor" else ItemRepository().get(resource_id)
    check = can_view_actor if kind == "actor" else can_view_item
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    audience = [member["user_id"] for member in members if row and check(**{kind: row, "campaign": {"member_role": member["role"]}, "user_id": member["user_id"]})]
    payload = {"room_id": campaign_id, f"{kind}_id": resource_id}
    if version is not None: payload["version"] = version
    await RealtimeTransport().to_players(player_ids=audience, event=event, payload=payload)


async def _emit_journal_event(*, event: TransportEvent, campaign_id: str, row: dict[str, Any], version: int | None = None) -> None:
    service = JournalService()
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    audience = []
    for member in members:
        campaign = CampaignRepository().get_for_user(campaign_id=campaign_id, user_id=member["user_id"])
        if campaign and service.can_view_journal(journal=row, campaign=dict(campaign), user_id=member["user_id"]):
            audience.append(member["user_id"])
    payload = {"room_id": campaign_id, "journal_id": row["id"]}
    if version is not None:
        payload["version"] = version
    await RealtimeTransport().to_players(player_ids=audience, event=event, payload=payload)


async def _emit_template_event(*, event: TransportEvent, campaign_id: str, payload: dict[str, Any], audience: str) -> None:
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    player_ids = [
        member["user_id"] for member in members
        if audience != "gm" or member.get("role") == "gm"
    ]
    await RealtimeTransport().to_players(player_ids=player_ids, event=event, payload=payload)


async def _emit_pdf_annotations_changed(*, campaign_id: str, document_id: str) -> None:
    """Notify only members who can currently re-read the PDF document."""
    service = SdkPdfService()
    audience = [
        member["user_id"]
        for member in CampaignRepository().list_members(campaign_id=campaign_id)
        if service.document(
            campaign_id=campaign_id,
            document_id=document_id,
            user_id=member["user_id"],
        ).success
    ]
    await RealtimeTransport().to_players(
        player_ids=audience,
        event=TransportEvent.PDF_ANNOTATIONS_CHANGED,
        payload={"room_id": campaign_id, "document_id": document_id, "schema_version": 1},
    )


@get(
    "/sdk/runtime/read/{resource_name:str}",
    guards=[require_user],
    sync_to_thread=True,
)
def sdk_runtime_read(
    resource_name: FromPath[str],
    campaign_id: FromQuery[str],
    package_id: FromQuery[str],
    current_user: Row,
    entity_id: FromQuery[str | None] = None,
    scene_id: FromQuery[str | None] = None,
    action: FromQuery[str | None] = None,
    entity_type: FromQuery[str | None] = None,
    folder_id: FromQuery[str | None] = None,
    cursor: FromQuery[str | None] = None,
    limit: FromQuery[int] = 100,
    document_id: FromQuery[str | None] = None,
    reference: FromQuery[str | None] = None,
    q: FromQuery[str | None] = None,
    kinds: FromQuery[str | None] = None,
    slot: FromQuery[str | None] = None,
    version: FromQuery[int | None] = None,
) -> Response[dict[str, Any]]:
    capability = _RESOURCE_CAPABILITIES.get(resource_name)
    if capability is None:
        return _error("sdk.runtime.resource_unknown", 404)

    authority = SdkRuntimeAuthority().authorize(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        package_id=package_id,
        capability=capability,
    )
    if not authority.allowed:
        return _error(authority.error_key or "sdk.runtime.denied", 403)

    user_id = current_user["id"]
    if resource_name == "card.definitions":
        from app.engine.decks.declarative_card_registry import CardDefinitionError, DeclarativeCardRegistry
        try:
            registry = DeclarativeCardRegistry()
            if entity_id:
                return Response({"definition": registry.get(package_id, entity_id, version).public()})
            return Response({"definitions": [entry.public() for entry in registry.list(package_id)]})
        except CardDefinitionError as exc:
            return _error(exc.code, 404 if exc.code.endswith(("not_found", "disabled")) else 400)
    if resource_name == "content.references":
        if not reference:
            return _error("sdk.content.reference_required", 400)
        try:
            resolved = ContentReferenceService().resolve(
                reference, campaign_id=campaign_id, user_id=user_id
            )
        except (ValueError, PermissionError):
            return _error("sdk.content.reference_invalid", 400)
        return Response(resolved) if resolved else _error("sdk.runtime.not_found", 404)
    if resource_name == "token.targets":
        result = TokenTargetService().list(campaign_id=campaign_id, scene_id=str(scene_id or ""), user_id=user_id)
        return Response({"ids": result.value}) if result.success else _service_error(result.error_key)
    if resource_name == "shared.measurements":
        result = SharedMeasurementService().list(campaign_id=campaign_id, scene_id=str(scene_id or ""), user_id=user_id)
        return Response({"measurements": result.value}) if result.success else _service_error(result.error_key)
    if resource_name == "pdf.presentation":
        result = PdfPresentationService().current(campaign_id=campaign_id, document_id=str(document_id or ""), user_id=user_id)
        return Response({"presentation": result.value}) if result.success else _service_error(result.error_key)
    if resource_name == "automation.jobs":
        service=AutomationService(); result=service.get(campaign_id=campaign_id,package_id=package_id,job_id=str(entity_id)) if entity_id else service.list(campaign_id=campaign_id,package_id=package_id)
        return Response({"job":result.value} if entity_id else {"jobs":result.value}) if result.success else _service_error(result.error_key)
    if resource_name == "automation.audit":
        result=AutomationService().list_audit(campaign_id=campaign_id,package_id=package_id,user_id=user_id)
        return Response({"events":result.value}) if result.success else _service_error(result.error_key)
    if resource_name == "packages":
        target_id = str(entity_id or "")
        active = target_id in PackageAssetService().active_package_ids(campaign_id)
        manifest = PackageInstallService().get_active_manifest(target_id) if active else None
        if manifest is None:
            return Response({"package": None})
        interop = manifest.raw.get("interop") if isinstance(manifest.raw.get("interop"), dict) else {}
        public_interop = {
            section: sorted(str(name) for name in entries)
            for section in ("emits", "listens", "provides", "requires")
            if isinstance((entries := interop.get(section)), dict)
        }
        return Response({"package": {
            "id": manifest.id, "kind": manifest.kind, "version": manifest.version,
            "active": True, "interop": public_interop,
        }})
    if resource_name == "content.index":
        requested = {part.strip().lower() for part in str(kinds or "").split(",") if part.strip()}
        try:
            page = ContentReferenceService().search(
                campaign_id=campaign_id, user_id=user_id, query=str(q or ""),
                kinds=requested or None, limit=limit, cursor=cursor,
            )
        except ValueError:
            return _error("sdk.content.cursor_invalid", 400)
        return Response(page)
    if resource_name in {"pdf", "pdf.viewer", "pdf.annotations"}:
        if not document_id:
            return _error("sdk.pdf.document_required", 400)
        service = SdkPdfService()
        if resource_name in {"pdf", "pdf.viewer"}:
            result = service.document(campaign_id=campaign_id, document_id=document_id, user_id=user_id)
            if not result.success:
                return _service_error(result.error_key)
            return Response({"document": result.value})
        result = service.list_annotations(campaign_id=campaign_id, document_id=document_id, user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        return Response({"annotations": result.value})

    if resource_name == "cards":
        result = CardService().get_state(campaign_id=campaign_id, user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        return Response(_card_asset_urls(_plain(result.payload)))

    if resource_name == "actors":
        service = ActorService()
        if entity_id:
            actor = service.get_actor(actor_id=entity_id, user_id=user_id)
            return Response({"actor": actor_snapshot(actor)}) if actor else _error("sdk.runtime.not_found", 404)
        actors = [actor_snapshot(actor) for actor in service.list_for_campaign(campaign_id=campaign_id, user_id=user_id)]
        if entity_type: actors = [actor for actor in actors if actor.get("type") == entity_type]
        if folder_id is not None: actors = [actor for actor in actors if (actor.get("folder_id") or "") == folder_id]
        if cursor: actors = actors[next((index + 1 for index, actor in enumerate(actors) if actor.get("id") == cursor), 0):]
        bounded = actors[:max(1, min(int(limit), 100))]
        return Response({"actors": bounded, "next_cursor": bounded[-1]["id"] if len(actors) > len(bounded) else None})

    if resource_name == "actors.data":
        if not entity_id:
            return _error("sdk.runtime.actor_required", 400)
        result = SheetDataService().get_data(actor_id=entity_id, user_id=user_id)
        # A hidden actor and a missing actor are intentionally indistinguishable.
        if not result.success:
            return _error("sdk.runtime.not_found", 404)
        return Response({"actor_id": result.actor_id, "version": result.version, "data": _plain(result.data or {})})

    if resource_name == "items":
        service = ItemService()
        if entity_id:
            item = service.get_item(item_id=entity_id, user_id=user_id)
            return Response({"item": item_snapshot(item)}) if item else _error("sdk.runtime.not_found", 404)
        items = [item_snapshot(item) for item in service.list_for_campaign(campaign_id=campaign_id, user_id=user_id)]
        if entity_type: items = [item for item in items if item.get("type") == entity_type]
        if folder_id is not None: items = [item for item in items if (item.get("folder_id") or "") == folder_id]
        if cursor: items = items[next((index + 1 for index, item in enumerate(items) if item.get("id") == cursor), 0):]
        bounded = items[:max(1, min(int(limit), 100))]
        return Response({"items": bounded, "next_cursor": bounded[-1]["id"] if len(items) > len(bounded) else None})

    if resource_name == "journals":
        service = JournalService()
        campaign = CampaignRepository().get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return _error("sdk.runtime.permission_denied", 403)
        rows = JournalRepository().list_active_for_campaign(campaign_id=campaign_id)
        visible = [row for row in rows if service.can_view_journal(journal=row, campaign=dict(campaign), user_id=user_id)]
        if entity_type:
            visible = [row for row in visible if row.get("type") == entity_type]
        if folder_id is not None:
            visible = [row for row in visible if (row.get("folder_id") or "") == folder_id]
        def present(row):
            return {"id": row["id"], "title": row["title"], "type": row["type"], "folder_id": row.get("folder_id"), "visibility": row.get("visibility"), "version": row.get("version"), "view": service.build_view(journal=row, campaign=dict(campaign), user_id=user_id)}
        if entity_id:
            row = next((row for row in visible if row.get("id") == entity_id), None)
            return Response({"journal": _plain(present(row))}) if row else _error("sdk.runtime.not_found", 404)
        bounded = visible[:max(1, min(int(limit), 100))]
        return Response({"journals": [_plain(present(row)) for row in bounded]})

    if resource_name == "tokens":
        if not scene_id:
            return _error("sdk.runtime.scene_required", 400)
        result = TokenService().get_snapshot(
            campaign_id=campaign_id, scene_id=scene_id, user_id=user_id
        )
        if not result.success:
            return _error(result.error_key or "sdk.runtime.denied", 403)
        tokens = result.tokens or []
        if entity_id:
            token = next((token for token in tokens if token.get("id") == entity_id), None)
            return Response({"token": _plain(token)}) if token else _error("sdk.runtime.not_found", 404)
        return Response({"scene_id": scene_id, "tokens": _plain(tokens[:max(1, min(int(limit), 500))])})

    if resource_name == "scenes":
        result = SceneService().list_scenes_for_campaign(campaign_id=campaign_id, user_id=user_id)
        if not result.success:
            return _error(result.error_key or "sdk.runtime.denied", 403)
        scenes = [scene_snapshot(dict(scene)) for scene in (result.scenes or [])][:100]
        if entity_id:
            scene = next((scene for scene in scenes if scene.get("id") == entity_id), None)
            return Response({"scene": scene}) if scene else _error("sdk.runtime.not_found", 404)
        active = SceneRepository().get_active_scene(campaign_id)
        return Response({"scenes": scenes, "active_scene_id": active.get("id") if active else None})

    if resource_name == "combat":
        result = CombatService().get_state(campaign_id=campaign_id, user_id=user_id)
        if not result.success:
            return _error(result.error_key or "sdk.runtime.denied", 403)
        return Response(_plain(result.state_payload()))

    if resource_name == "rules.actions":
        registry = DeclarativeActionRegistry()
        try:
            if action:
                return Response({"action": registry.resolve_active_ruleset(campaign_id, str(action)).public()})
            if entity_id:
                return Response({"action": registry.get(package_id, str(entity_id)).public()})
            return Response({"actions": [entry.public() for entry in registry.list(package_id)]})
        except ActionContractError as exc:
            return _error(exc.code, 404 if "not_found" in exc.code else 400)

    if resource_name in {"actor.item.slots", "actor.item.copies"}:
        service = ActorItemCopyService()
        result = service.slots(actor_id=str(entity_id or ""), user_id=user_id) if resource_name.endswith("slots") else service.list(actor_id=str(entity_id or ""), user_id=user_id, slot_id=str(slot or ""))
        if not result.success: return _error(result.error_key or "sdk.runtime.not_found", 404 if "not_found" in str(result.error_key) else 400)
        return Response(result.value or {})

    if resource_name == "geometry":
        if not scene_id:
            return _error("sdk.runtime.scene_required", 400)
        walls = SceneWallService().state(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        lights = SceneLightService().state(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not walls.success or not lights.success:
            return _error(walls.error_key or lights.error_key or "sdk.runtime.denied", 403)
        return Response({"walls": [wall_snapshot(row) for row in walls.payload.get("walls", [])][:500], "lights": [light_snapshot(row) for row in lights.payload.get("lights", [])][:500]})

    if resource_name == "effects.presets":
        return Response({"presets": _plain(PARTICLE_PRESETS), "schema_version": 1})

    if resource_name in {"shader.presets", "shader.preset", "shader.instances"}:
        service = SceneShaderService()
        if resource_name == "shader.presets":
            result = service.presets()
        elif resource_name == "shader.preset":
            result = service.preset(str(entity_id or ""))
        else:
            if not scene_id:
                return _error("sdk.runtime.scene_required", 400)
            result = service.semantic_state(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        return Response(_plain(result.payload))

    if resource_name == "effects":
        if not scene_id:
            return _error("sdk.runtime.scene_required", 400)
        particles = SceneParticleService().state(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        shaders = SceneShaderService().state(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not particles.success or not shaders.success:
            return _error(particles.error_key or shaders.error_key or "sdk.runtime.denied", 403)
        return Response({"particles": [particle_snapshot(row) for row in particles.payload.get("emitters", particles.payload.get("particles", []))][:500], "shaders": [shader_metadata_snapshot(row) for row in shaders.payload.get("shaders", [])][:500]})

    if resource_name == "fog":
        if not scene_id:
            return _error("sdk.runtime.scene_required", 400)
        scene = SceneRepository().get_by_id(scene_id)
        if not scene or scene.get("campaign_id") != campaign_id or CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=user_id) is None:
            return _error("sdk.runtime.not_found", 404)
        result = FogService().get_state(scene_id)
        if not result.success:
            return _service_error(result.error_key)
        return Response({"scene_id": result.scene_id, "enabled": result.enabled, "baseline": result.baseline, "ops": result.ops or [], "version": result.version})

    if resource_name == "scene.images":
        result = SceneImageService().get_state(campaign_id=campaign_id, user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        placements = result.payload.get("placements", [])
        if scene_id:
            placements = [row for row in placements if row.get("scene_id") == scene_id]
        return Response({"placements": _plain(placements[:500])})

    if resource_name == "scene.templates":
        if not scene_id:
            return _error("sdk.runtime.scene_required", 400)
        result = SceneTemplateService().list(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        templates = result.payload.get("templates", [])
        if entity_id:
            template = next((item for item in templates if item.get("id") == entity_id), None)
            return Response({"template": template}) if template else _error("sdk.runtime.not_found", 404)
        return Response(_plain(result.payload))

    if resource_name == "chat":
        if not PermissionService().can(user_id=user_id, campaign_id=campaign_id, permission="chat.view"):
            return _error("sdk.runtime.permission_denied", 403)
        repo = ChatMessageRepository()
        role = CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=user_id)
        visible = lambda message: role == "gm" or message.get("visibility") not in {"gm", "gm_only", "private", "self"}
        if entity_id:
            message = repo.get_for_campaign(campaign_id=campaign_id, message_id=entity_id)
            return Response({"message": chat_snapshot(message)}) if message and visible(message) else _error("sdk.runtime.not_found", 404)
        messages = [chat_snapshot(message) for message in repo.list_for_campaign(campaign_id=campaign_id, limit=100) if visible(message)]
        return Response({"messages": messages})

    permission_key = str(action or "")
    supported, allowed = SdkRuntimePermissionInspector().can(
        action=permission_key, campaign_id=campaign_id, user_id=user_id, resource_id=str(entity_id or "")
    )
    reason = "ALLOWED" if allowed else ("DENIED" if supported else "UNKNOWN_ACTION")
    return Response({"action": permission_key, "supported": supported, "allowed": allowed, "reason": reason})


@post("/sdk/runtime/command/{command_name:str}", guards=[require_user])
async def sdk_runtime_command(
    command_name: FromPath[str], request: Request, current_user: Row
) -> Response[dict[str, Any]]:
    data = await _body(request)
    campaign_id = str(data.get("campaign_id") or "")
    package_id = str(data.get("package_id") or "")
    capability = {
        "actors.create": "actors.write", "actors.update": "actors.write", "actors.delete": "actors.write",
        "items.create": "items.write", "items.update": "items.write", "items.delete": "items.write", "items.patchData": "items.data.write",
        "journals.create": "journals.write", "journals.update": "journals.write", "journals.delete": "journals.write", "handouts.present": "handouts.present",
        "tokens.create": "tokens.manage", "tokens.update": "tokens.manage", "tokens.delete": "tokens.manage",
        "tokens.move": "tokens.move", "geometry.createWall": "scene.geometry.write",
        "geometry.updateWall": "scene.geometry.write", "geometry.deleteWall": "scene.geometry.write", "geometry.setDoorState": "scene.geometry.write",
        "geometry.splitWall": "scene.geometry.write", "geometry.moveWallNode": "scene.geometry.write", "geometry.moveWalls": "scene.geometry.write", "geometry.deleteWalls": "scene.geometry.write",
        "geometry.createLight": "scene.geometry.write", "geometry.updateLight": "scene.geometry.write",
        "geometry.deleteLight": "scene.geometry.write", "effects.create": "scene.effects.write",
        "effects.update": "scene.effects.write", "effects.delete": "scene.effects.write",
        "fog.enable": "scene.fog.write", "fog.disable": "scene.fog.write", "fog.reset": "scene.fog.write", "fog.paint": "scene.fog.write",
        "templates.create": "scene.templates.write", "templates.update": "scene.templates.write", "templates.delete": "scene.templates.write",
        "sceneImages.place": "scene.images.write", "sceneImages.update": "scene.images.write", "sceneImages.delete": "scene.images.write",
        "combat.start": "combat.manage", "combat.end": "combat.manage", "combat.advance": "combat.manage", "combat.advanceRound": "combat.manage",
        "combat.setTurn": "combat.manage", "combat.add": "combat.manage", "combat.remove": "combat.manage", "combat.setFlags": "combat.manage", "combat.rollInitiative": "combat.manage",
        "rules.action.execute": "rules.actions",
        "actorItems.insertCopy": "actors.items.write", "actorItems.removeCopy": "actors.items.write",
        "pdf.annotations.create": "pdf.annotations.write", "pdf.annotations.update": "pdf.annotations.write", "pdf.annotations.delete": "pdf.annotations.write",
        "shaders.apply": "scene.shaders.write", "shaders.update": "scene.shaders.write", "shaders.remove": "scene.shaders.write",
        "cards.shuffle": "cards.manage", "cards.reset": "cards.manage", "cards.draw": "cards.manage",
        "cards.reveal": "cards.manage", "cards.discard": "cards.manage", "cards.play": "cards.manage",
        "cards.updatePlacement": "cards.manage", "cards.discardPlacement": "cards.manage",
        "cards.instantiateDefinition": "cards.manage",
        "actors.patchData": "actors.data.write", "combat.setInitiative": "combat.manage", "combat.moveCombatant": "combat.manage", "combat.setInitiativeOrder": "combat.manage",
        "tokenTargets.set": "tokens.targets", "tokenTargets.clear": "tokens.targets",
        "measurements.share": "scene.measurements.shared", "measurements.cancel": "scene.measurements.shared",
        "pdf.presentation.start": "pdf.presentation", "pdf.presentation.update": "pdf.presentation", "pdf.presentation.end": "pdf.presentation",
        "automation.schedule": "automation.schedule", "automation.cancel": "automation.schedule",
        "assets.ingest": "assets.import", "assets.cancelImport": "assets.import",
    }.get(command_name)
    if capability is None:
        return _error("sdk.runtime.command_unknown", 404)
    authority = SdkRuntimeAuthority().authorize(
        campaign_id=campaign_id, user_id=current_user["id"], package_id=package_id, capability=capability
    )
    if not authority.allowed:
        return _error(authority.error_key or "sdk.runtime.denied", 403)

    user_id = current_user["id"]
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    if command_name in {"assets.ingest", "assets.cancelImport"}:
        service=AssetIngestionService()
        result=(service.ingest(campaign_id=campaign_id,user_id=user_id,package_id=package_id,source=payload.get("source")) if command_name=="assets.ingest" else service.cancel(campaign_id=campaign_id,user_id=user_id,package_id=package_id,asset_id=str(payload.get("assetId") or "")))
        if not result.success:return _service_error(result.error_key)
        return Response(_plain(result.payload))
    if command_name in {"automation.schedule","automation.cancel"}:
        service=AutomationService()
        if command_name.endswith("schedule"):
            result=service.schedule(campaign_id=campaign_id,user_id=user_id,package_id=package_id,action_id=str(payload.get("actionId") or ""),version=_int(payload.get("version")),inputs=payload.get("input",{}),run_at_utc=_int(payload.get("runAtUtc")),idempotency_key=str(payload.get("idempotencyKey") or ""),origin_execution_id=payload.get("originExecutionId"),origin_job_id=payload.get("originJobId"),causal_depth=_int(payload.get("causalDepth")))
        else: result=service.cancel(campaign_id=campaign_id,package_id=package_id,job_id=str(payload.get("jobId") or ""))
        if result.success: await RealtimeTransport().to_players(player_ids=[user_id],event=TransportEvent.AUTOMATION_JOB_CHANGED,payload={"room_id":campaign_id,"job_id":result.value.get("id"),"schema_version":1})
        return Response({"job":result.value}) if result.success else _service_error(result.error_key)
    if command_name in {"tokenTargets.set", "tokenTargets.clear"}:
        service = TokenTargetService(); scene = str(payload.get("sceneId") or "")
        result = service.set(campaign_id=campaign_id, scene_id=scene, user_id=user_id, ids=payload.get("ids")) if command_name.endswith("set") else service.clear(campaign_id=campaign_id, scope_id=scene, owner_user_id=user_id)
        if result.success: await RealtimeTransport().to_players(player_ids=[user_id],event=TransportEvent.TOKEN_TARGETS_CHANGED,payload={"room_id":campaign_id,"scene_id":scene,"schema_version":1})
        return Response({"ids": result.value}) if result.success else _service_error(result.error_key)
    if command_name in {"measurements.share", "measurements.cancel"}:
        service = SharedMeasurementService(); scene = str(payload.get("sceneId") or "")
        result = service.create(campaign_id=campaign_id, scene_id=scene, user_id=user_id, geometry=payload.get("geometry"), audience=str(payload.get("audience") or "campaign"), ttl_seconds=_int(payload.get("ttlSeconds"),30)) if command_name.endswith("share") else service.cancel(campaign_id=campaign_id, scene_id=scene, user_id=user_id, measurement_id=str(payload.get("measurementId") or ""))
        if result.success:
            members=CampaignRepository().list_members(campaign_id=campaign_id); audience=[m["user_id"] for m in members if result.value.get("audience")=="campaign" or result.value.get("audience")=="gm" and m.get("role") in {"gm","assistant_gm"} or m["user_id"]==result.value.get("creator")]
            await RealtimeTransport().to_players(player_ids=audience,event=TransportEvent.SCENE_MEASUREMENTS_CHANGED,payload={"room_id":campaign_id,"scene_id":scene,"schema_version":1})
        return Response({"measurement": result.value}) if result.success else _service_error(result.error_key)
    if command_name.startswith("pdf.presentation."):
        service=PdfPresentationService(); document=str(payload.get("documentId") or "")
        if command_name.endswith("start"): result=service.start(campaign_id=campaign_id,document_id=document,user_id=user_id,audience=payload.get("audience"),page=payload.get("page"),ttl_seconds=_int(payload.get("ttlSeconds"),300))
        elif command_name.endswith("update"): result=service.update(campaign_id=campaign_id,document_id=document,user_id=user_id,page=payload.get("page"),expected_version=payload.get("expectedVersion"))
        else: result=service.end(campaign_id=campaign_id,document_id=document,user_id=user_id)
        if result.success:
            audience=list(dict.fromkeys(([user_id]+result.value.get("audience",[])) if isinstance(result.value,dict) else [user_id])); await RealtimeTransport().to_players(player_ids=audience,event=TransportEvent.PDF_PRESENTATION_CHANGED,payload={"room_id":campaign_id,"document_id":document,"schema_version":1})
        return Response({"presentation":result.value}) if result.success else _service_error(result.error_key)
    if command_name == "rules.action.execute":
        provider_package_id = str(payload.get("providerPackageId") or package_id)
        result = DeclarativeActionService().execute(
            campaign_id=campaign_id, user_id=user_id, package_id=provider_package_id,
            action_id=str(payload.get("actionId") or ""),
            version=_int(payload.get("version")) if payload.get("version") is not None else None,
            inputs=payload.get("input", {}),
            idempotency_key=str(payload.get("idempotencyKey")) if payload.get("idempotencyKey") is not None else None,
        )
        if not result.success:
            status = 404 if "not_found" in str(result.error_key) else (409 if "conflict" in str(result.error_key) else 400)
            return _error(result.error_key or "sdk.rules.actions.failed", status)
        await RealtimeTransport().to_room(
            room_id=campaign_id, event=TransportEvent.RULES_ACTION_COMPLETED,
            payload={"room_id": campaign_id, "package_id": provider_package_id, "action_id": result.value["action"], "version": result.value["version"], "execution_id": result.value["executionId"]},
        )
        return Response(result.value or {})
    if command_name in {"actorItems.insertCopy", "actorItems.removeCopy"}:
        service = ActorItemCopyService()
        if command_name == "actorItems.insertCopy":
            result = service.insert(campaign_id=campaign_id, actor_id=str(payload.get("actorId") or ""), source_item_id=str(payload.get("sourceItemId") or ""), slot_id=str(payload.get("slot") or ""), user_id=user_id)
        else:
            result = service.remove(actor_id=str(payload.get("actorId") or ""), local_id=str(payload.get("localInstanceId") or ""), slot_id=str(payload.get("slot") or ""), user_id=user_id)
        if not result.success: return _error(result.error_key or "sdk.runtime.not_found", 404 if "not_found" in str(result.error_key) else 400)
        value = result.value or {}
        await RealtimeTransport().to_room(room_id=campaign_id, event=TransportEvent.SHEET_DATA_UPDATED, payload={"room_id": campaign_id, "actor_id": value.get("actorId"), "version": value.get("version", 0), "updated_by": user_id, "changed_paths": []})
        return Response(value)
    if command_name == "actors.patchData":
        actor_id = str(payload.get("actorId") or "")
        if not _resource_in_campaign(ActorRepository().get(actor_id), campaign_id):
            return _error("sdk.runtime.not_found", 404)
        result = SheetDataService().patch_data(actor_id=actor_id, user_id=user_id, patch=payload.get("patch") if isinstance(payload.get("patch"), dict) else {})
        if not result.success:
            return _service_error(result.error_key)
        await RealtimeTransport().to_room(room_id=result.campaign_id or campaign_id, event=TransportEvent.SHEET_DATA_UPDATED, payload={"room_id": result.campaign_id or campaign_id, "system_id": result.system_id or "", "actor_id": result.actor_id, "version": result.version or 0, "updated_by": user_id, "changed_paths": result.changed_paths or []})
        return Response({"actor_id": result.actor_id, "version": result.version, "changed_paths": result.changed_paths or []})

    if command_name == "items.patchData":
        item_id = str(payload.get("itemId") or "")
        if not _resource_in_campaign(ItemRepository().get(item_id), campaign_id):
            return _error("sdk.runtime.not_found", 404)
        result = ItemSheetDataService().patch_data(item_id=item_id, user_id=user_id, patch=payload.get("patch") if isinstance(payload.get("patch"), dict) else {})
        if not result.success:
            return _service_error(result.error_key)
        await RealtimeTransport().to_room(room_id=result.campaign_id or campaign_id, event=TransportEvent.ITEM_UPDATED, payload={"room_id": result.campaign_id or campaign_id, "system_id": result.system_id or "", "item_id": result.item_id, "version": result.version or 0, "updated_by": user_id, "changed_paths": result.changed_paths or []})
        return Response({"item_id": result.item_id, "version": result.version, "changed_paths": result.changed_paths or []})

    if command_name.startswith("journals."):
        service = JournalService()
        if command_name == "journals.create":
            result = service.create_journal(campaign_id=campaign_id, user_id=user_id, journal_type=str(payload.get("type") or "diary"), title=str(payload.get("title") or ""), folder_id=str(payload.get("folderId") or ""), visibility=str(payload.get("visibility") or "private"), content_markdown=str(payload.get("contentMarkdown") or ""), data=payload.get("data") if isinstance(payload.get("data"), dict) else {}, owner_user_ids=payload.get("ownerUserIds") if isinstance(payload.get("ownerUserIds"), list) else None)
            event = TransportEvent.JOURNAL_CREATED
            event_row = None
        elif command_name == "journals.update":
            journal_id = str(payload.get("journalId") or "")
            current = JournalRepository().get_by_id(journal_id)
            if not _resource_in_campaign(current, campaign_id):
                return _error("sdk.runtime.not_found", 404)
            try:
                current_data = json.loads(current.get("data_json") or "{}")
            except (TypeError, ValueError):
                current_data = {}
            result = service.update_journal(journal_id=journal_id, user_id=user_id, title=str(payload["title"]) if "title" in payload else str(current.get("title") or ""), folder_id=str(payload["folderId"]) if "folderId" in payload else str(current.get("folder_id") or ""), visibility=str(payload["visibility"]) if "visibility" in payload else str(current.get("visibility") or "private"), content_markdown=str(payload["contentMarkdown"]) if "contentMarkdown" in payload else str(current.get("content_markdown") or ""), data=payload["data"] if isinstance(payload.get("data"), dict) else current_data, owner_user_ids=payload.get("ownerUserIds") if isinstance(payload.get("ownerUserIds"), list) else None)
            event = TransportEvent.JOURNAL_UPDATED
            event_row = None
        else:
            journal_id = str(payload.get("journalId") or "")
            if not _resource_in_campaign(JournalRepository().get_by_id(journal_id), campaign_id):
                return _error("sdk.runtime.not_found", 404)
            result = service.delete_journal(journal_id=journal_id, requester_user_id=user_id)
            event = TransportEvent.JOURNAL_DELETED
            event_row = current
        if not result.success:
            return _service_error(result.error_key)
        response = {"journal_id": result.journal_id, "version": result.version}
        if event_row is None:
            event_row = JournalRepository().get_by_id(result.journal_id)
        if event_row:
            await _emit_journal_event(event=event, campaign_id=result.campaign_id or campaign_id, row=dict(event_row), version=result.version)
        return Response(response, status_code=201 if command_name == "journals.create" else 200)

    if command_name == "handouts.present":
        if not config.targeted_handouts_enabled:
            return _error("handout.errors.disabled", 404)
        result = await run_blocking(HandoutService().prepare_presentation, campaign_id=campaign_id, user_id=user_id, resource_type=str(payload.get("resourceType") or ""), resource_id=str(payload.get("resourceId") or ""), subject_type=str(payload.get("subjectType") or "all"), subject_id=str(payload.get("subjectId") or ""))
        if not result.success:
            return _service_error(result.error_key)
        await dispatch_handout_presentation(result.grant)
        return Response({"presented": True})

    if command_name.startswith("fog."):
        service = FogService()
        scene_id = str(payload.get("sceneId") or "")
        if not _resource_in_campaign(SceneRepository().get_by_id(scene_id), campaign_id):
            return _error("sdk.runtime.not_found", 404)
        try:
            initial = FogInitialState(str(payload.get("initial") or payload.get("to") or FogInitialState.HIDE_ALL.value))
        except ValueError:
            return _error("sdk.runtime.invalid_payload", 400)
        if command_name == "fog.enable":
            result = service.enable(scene_id=scene_id, user_id=user_id, initial=initial)
        elif command_name == "fog.disable":
            result = service.disable(scene_id=scene_id, user_id=user_id)
        elif command_name == "fog.reset":
            result = service.reset(scene_id=scene_id, user_id=user_id, to=initial)
        else:
            raw_ops = payload.get("ops") if isinstance(payload.get("ops"), list) else []
            if not raw_ops or len(raw_ops) > 100:
                return _error("sdk.runtime.invalid_payload", 400)
            ops = [_parse_op(raw) for raw in raw_ops]
            if any(op is None for op in ops):
                return _error("sdk.runtime.invalid_payload", 400)
            expected = payload.get("expectedVersion")
            result = service.paint(scene_id=scene_id, user_id=user_id, ops=ops, expected_version=_int(expected) if expected is not None else None)
        if not result.success:
            return _service_error(result.error_key)
        response = {"scene_id": result.scene_id, "enabled": result.enabled, "baseline": result.baseline, "ops": result.ops or [], "new_ops": result.new_ops or [], "version": result.version}
        await RealtimeTransport().to_room(room_id=result.campaign_id or campaign_id, event=TransportEvent.FOG_UPDATED, payload=response)
        return Response(response)

    if command_name.startswith("sceneImages."):
        service = SceneImageService()
        if command_name == "sceneImages.place":
            result = service.place_asset(campaign_id=campaign_id, user_id=user_id, scene_id=str(payload.get("sceneId") or ""), asset_id=str(payload.get("assetId") or ""), x=_float(payload.get("x")), y=_float(payload.get("y")), rotation=_float(payload.get("rotation")), scale=_float(payload.get("scale")) if payload.get("scale") is not None else None, layer=str(payload.get("layer") or "game"))
        elif command_name == "sceneImages.update":
            patch = payload.get("patch") if isinstance(payload.get("patch"), dict) else {}
            expected = payload.get("expectedVersion")
            result = service.update_placement(campaign_id=campaign_id, user_id=user_id, placement_id=str(payload.get("placementId") or ""), x=_float(patch.get("x")) if patch.get("x") is not None else None, y=_float(patch.get("y")) if patch.get("y") is not None else None, rotation=_float(patch.get("rotation")) if patch.get("rotation") is not None else None, scale=_float(patch.get("scale")) if patch.get("scale") is not None else None, z_index=_int(patch.get("zIndex")) if patch.get("zIndex") is not None else None, layer=str(patch.get("layer")) if patch.get("layer") is not None else None, asset_id=str(patch.get("assetId")) if patch.get("assetId") is not None else None, expected_version=_int(expected) if expected is not None else None)
        else:
            result = service.delete_placement(campaign_id=campaign_id, user_id=user_id, placement_id=str(payload.get("placementId") or ""))
        if not result.success:
            return _service_error(result.error_key)
        placement = result.payload.get("placement") if isinstance(result.payload.get("placement"), dict) else {}
        event_scene_id = str(placement.get("scene_id") or result.payload.get("scene_id") or payload.get("sceneId") or "")
        await RealtimeTransport().to_room(room_id=campaign_id, event=TransportEvent.SCENE_IMAGES_UPDATED, payload={"room_id": campaign_id, "scene_id": event_scene_id, "updated_by": user_id})
        return Response(_plain(result.payload), status_code=201 if command_name == "sceneImages.place" else 200)

    if command_name.startswith("templates."):
        service = SceneTemplateService()
        values = payload.get("values") if isinstance(payload.get("values"), dict) else {}
        if command_name == "templates.create":
            result = service.create(campaign_id=campaign_id, scene_id=str(payload.get("sceneId") or ""), user_id=user_id, values=values)
            event = TransportEvent.BOARD_AREA_MARKER_UPSERTED
        elif command_name == "templates.update":
            expected = payload.get("expectedVersion")
            result = service.update(campaign_id=campaign_id, template_id=str(payload.get("templateId") or ""), user_id=user_id, values=values, expected_version=_int(expected) if expected is not None else None)
            event = TransportEvent.BOARD_AREA_MARKER_UPSERTED
        else:
            expected = payload.get("expectedVersion")
            result = service.delete(campaign_id=campaign_id, template_id=str(payload.get("templateId") or ""), user_id=user_id, expected_version=_int(expected) if expected is not None else None)
            event = TransportEvent.BOARD_AREA_MARKER_DELETED
        if not result.success:
            return _service_error(result.error_key)
        template = result.payload.get("template") if isinstance(result.payload.get("template"), dict) else None
        audience = str((template or result.payload).get("audience") or "campaign")
        scene_value = str((template or {}).get("sceneId") or result.payload.get("scene_id") or "")
        event_payload = {"room_id": campaign_id, "scene_id": scene_value, "template_id": str((template or {}).get("id") or result.payload.get("template_id") or ""), "version": int((template or result.payload).get("version") or 0)}
        await _emit_template_event(event=event, campaign_id=campaign_id, payload=event_payload, audience=audience)
        return Response(_plain(result.payload), status_code=201 if command_name == "templates.create" else 200)

    if command_name in {"combat.setInitiative", "combat.moveCombatant", "combat.setInitiativeOrder", "combat.advanceRound", "combat.setFlags", "combat.rollInitiative"}:
        service = CombatService()
        if command_name == "combat.setInitiative":
            raw = payload.get("value")
            result = service.set_initiative(campaign_id=campaign_id, user_id=user_id, combatant_id=str(payload.get("combatantId") or ""), value=None if raw is None else str(raw))
        elif command_name == "combat.moveCombatant":
            result = service.move_combatant(campaign_id=campaign_id, user_id=user_id, combatant_id=str(payload.get("combatantId") or ""), delta=-1 if _int(payload.get("delta"), 1) < 0 else 1)
        elif command_name == "combat.setInitiativeOrder":
            entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
            result = service.set_manual_initiative_order(campaign_id=campaign_id, user_id=user_id, entries=entries)
        elif command_name == "combat.advanceRound":
            result = service.advance_round(campaign_id=campaign_id, user_id=user_id, delta=_int(payload.get("delta"), 1))
        elif command_name == "combat.setFlags":
            result = service.set_flags(campaign_id=campaign_id, user_id=user_id, combatant_id=str(payload.get("combatantId") or ""), hidden=payload.get("hidden") if isinstance(payload.get("hidden"), bool) else None, defeated=payload.get("defeated") if isinstance(payload.get("defeated"), bool) else None)
        else:
            result = service.roll_initiative(campaign_id=campaign_id, user_id=user_id, scope=str(payload.get("scope") or "all"), combatant_id=str(payload.get("combatantId") or ""))
        if not result.success:
            return _service_error(result.error_key)
        state_payload = _plain(result.state_payload())
        await RealtimeTransport().to_room(room_id=campaign_id, event=TransportEvent.COMBAT_UPDATED, payload=state_payload)
        return Response(state_payload)

    if command_name.startswith("cards."):
        service = CardService()
        deck_id = str(payload.get("deckId") or "")
        if command_name == "cards.instantiateDefinition":
            from app.engine.decks.declarative_card_registry import CardDefinitionError, DeclarativeCardRegistry
            try:
                definition = DeclarativeCardRegistry().get(package_id, str(payload.get("definitionId") or ""), _int(payload.get("version")) if payload.get("version") is not None else None)
            except CardDefinitionError as exc:
                return _error(exc.code, 404 if exc.code.endswith("not_found") else 400)
            artwork = payload.get("artwork") if isinstance(payload.get("artwork"), dict) else {}
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            result = service.instantiate_declared_deck(campaign_id=campaign_id, user_id=user_id, package_id=package_id, definition=definition, artwork=artwork, metadata=metadata, name=str(payload.get("name") or "") or None)
        elif command_name == "cards.shuffle":
            result = service.shuffle(campaign_id=campaign_id, user_id=user_id, deck_instance_id=deck_id)
        elif command_name == "cards.reset":
            result = service.reset(campaign_id=campaign_id, user_id=user_id, deck_instance_id=deck_id, shuffle=bool(payload.get("shuffle", True)))
        elif command_name == "cards.draw":
            try: destination = DrawDestination(str(payload.get("destination") or DrawDestination.HAND.value))
            except ValueError: destination = DrawDestination.HAND
            try: mode = DrawMode(str(payload.get("mode") or DrawMode.TOP.value))
            except ValueError: mode = DrawMode.TOP
            result = service.draw(campaign_id=campaign_id, user_id=user_id, deck_instance_id=deck_id, count=max(1, min(_int(payload.get("count"), 1), 100)), destination=destination, mode=mode, target_pile_id=payload.get("targetPileId") if isinstance(payload.get("targetPileId"), str) else None, reveal=bool(payload.get("reveal")))
        elif command_name in {"cards.reveal", "cards.discard"}:
            card_ids = [str(value) for value in payload.get("cardIds", []) if str(value)] if isinstance(payload.get("cardIds"), list) else []
            result = service.reveal(campaign_id=campaign_id, user_id=user_id, card_ids=card_ids) if command_name == "cards.reveal" else service.discard(campaign_id=campaign_id, user_id=user_id, card_ids=card_ids)
        elif command_name == "cards.play":
            result = service.play_to_scene(campaign_id=campaign_id, user_id=user_id, card_id=str(payload.get("cardId") or ""), scene_id=str(payload.get("sceneId") or ""), x=float(payload.get("x") or 0), y=float(payload.get("y") or 0), rotation=float(payload.get("rotation") or 0), scale=float(payload.get("scale") or 1), reveal=bool(payload.get("reveal", True)))
        elif command_name == "cards.updatePlacement":
            patch = payload.get("patch") if isinstance(payload.get("patch"), dict) else {}
            face_state = None
            if patch.get("faceState") in {CardFaceState.FACE_UP.value, CardFaceState.FACE_DOWN.value}:
                face_state = CardFaceState(str(patch["faceState"]))
            result = service.update_scene_placement(campaign_id=campaign_id, user_id=user_id, placement_id=str(payload.get("placementId") or ""), x=float(patch["x"]) if patch.get("x") is not None else None, y=float(patch["y"]) if patch.get("y") is not None else None, rotation=float(patch["rotation"]) if patch.get("rotation") is not None else None, scale=float(patch["scale"]) if patch.get("scale") is not None else None, z_index=_int(patch.get("zIndex")) if patch.get("zIndex") is not None else None, face_state=face_state)
        else:
            result = service.discard_scene_placement(campaign_id=campaign_id, user_id=user_id, placement_id=str(payload.get("placementId") or ""))
        if not result.success:
            return _service_error(result.error_key)
        if command_name == "cards.draw" and destination == DrawDestination.CHAT:
            cards = result.payload.get("cards") if isinstance(result.payload.get("cards"), list) else []
            count_label = len(cards) or max(1, min(_int(payload.get("count"), 1), 100))
            content = f"{current_user.get('name') or 'Player'} revealed {count_label} card" + ("s" if count_label != 1 else "")
            await ChatService().send_card_message(campaign_id=campaign_id, sender_user_id=user_id, sender_name=str(current_user.get("name") or "Player"), content=content, cards=cards, card_event=result.payload.get("event") if isinstance(result.payload.get("event"), dict) else {}, transport=RealtimeTransport())
        await RealtimeTransport().to_room(room_id=campaign_id, event=TransportEvent.CARDS_STATE_UPDATED, payload={"room_id": campaign_id, "updated_by": user_id})
        return Response(_card_asset_urls(_plain(result.payload)))
    if command_name == "pdf.annotations.create":
        result = SdkPdfService().create_annotation(
            campaign_id=campaign_id, document_id=str(payload.get("documentId") or ""),
            user_id=user_id, page=payload.get("page"), region=payload.get("region"), text=payload.get("text"),
        )
        if not result.success:
            return _service_error(result.error_key)
        await _emit_pdf_annotations_changed(campaign_id=campaign_id, document_id=str(payload.get("documentId") or ""))
        return Response({"annotation": result.value}, status_code=201)
    if command_name == "pdf.annotations.update":
        result = SdkPdfService().update_annotation(campaign_id=campaign_id, document_id=str(payload.get("documentId") or ""), annotation_id=str(payload.get("annotationId") or ""), user_id=user_id, page=payload.get("page"), region=payload.get("region"), text=payload.get("text"))
        if not result.success:
            return _service_error(result.error_key)
        await _emit_pdf_annotations_changed(campaign_id=campaign_id, document_id=str(payload.get("documentId") or ""))
        return Response({"annotation": result.value})
    if command_name == "pdf.annotations.delete":
        result = SdkPdfService().delete_annotation(campaign_id=campaign_id, document_id=str(payload.get("documentId") or ""), annotation_id=str(payload.get("annotationId") or ""), user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        await _emit_pdf_annotations_changed(campaign_id=campaign_id, document_id=str(payload.get("documentId") or ""))
        return Response(result.value)

    if command_name.startswith("actors."):
        service = ActorService()
        if command_name != "actors.create" and not _resource_in_campaign(ActorRepository().get(str(payload.get("id") or "")), campaign_id):
            return _error("sdk.runtime.not_found", 404)
        if command_name == "actors.create":
            result = service.create_actor(campaign_id=campaign_id, user_id=user_id, system_id=str(payload.get("systemId") or ""), actor_type=str(payload.get("type") or ""), name=str(payload.get("name") or ""), folder_id=str(payload.get("folderId") or ""))
        elif command_name == "actors.update":
            result = service.update_core(actor_id=str(payload.get("id") or ""), user_id=user_id, name=str(payload.get("name") or ""), folder_id=str(payload.get("folderId") or ""), portrait_asset_id=str(payload.get("portraitAssetId") or ""), token_asset_id=str(payload.get("tokenAssetId") or ""), expected_version=_int(payload.get("expectedVersion"), -1) if payload.get("expectedVersion") is not None else None)
        else:
            result = service.delete_actor(actor_id=str(payload.get("id") or ""), user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        actor_event = {"actors.create": TransportEvent.ACTOR_CREATED, "actors.update": TransportEvent.ACTOR_UPDATED, "actors.delete": TransportEvent.ACTOR_DELETED}[command_name]
        await _emit_resource_event(kind="actor", event=actor_event, campaign_id=campaign_id, resource_id=str(result.actor_id or ""), version=result.version)
        return Response({"actor_id": result.actor_id, "version": result.version})

    if command_name.startswith("items."):
        service = ItemService()
        if command_name != "items.create" and not _resource_in_campaign(ItemRepository().get(str(payload.get("id") or "")), campaign_id):
            return _error("sdk.runtime.not_found", 404)
        if command_name == "items.create":
            result = service.create_item(campaign_id=campaign_id, user_id=user_id, system_id=str(payload.get("systemId") or ""), item_type=str(payload.get("type") or ""), name=str(payload.get("name") or ""), folder_id=str(payload.get("folderId") or ""))
        elif command_name == "items.update":
            result = service.update_core(item_id=str(payload.get("id") or ""), user_id=user_id, name=str(payload.get("name") or ""), folder_id=str(payload.get("folderId") or ""), portrait_asset_id=str(payload.get("portraitAssetId") or ""), expected_version=_int(payload.get("expectedVersion"), -1) if payload.get("expectedVersion") is not None else None)
        else:
            result = service.delete_item(item_id=str(payload.get("id") or ""), user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        item_event = {"items.create": TransportEvent.ITEM_CREATED, "items.update": TransportEvent.ITEM_UPDATED, "items.delete": TransportEvent.ITEM_DELETED}[command_name]
        await _emit_resource_event(kind="item", event=item_event, campaign_id=campaign_id, resource_id=str(result.item_id or ""), version=result.version)
        return Response({"item_id": result.item_id, "version": result.version})

    if command_name.startswith("tokens."):
        service = TokenService()
        transport = RealtimeTransport()
        common = {"campaign_id": campaign_id, "scene_id": str(payload.get("sceneId") or ""), "user_id": user_id, "transport": transport}
        if command_name == "tokens.create":
            result = await service.create_many_from_actors(**common, actor_ids=[str(payload.get("actorId") or "")], origin_x=_int(payload.get("x")), origin_y=_int(payload.get("y")), elevation=_float(payload.get("elevation")))
        elif command_name == "tokens.move":
            result = await service.move(**common, token_id=str(payload.get("id") or ""), grid_x=_int(payload.get("x")), grid_y=_int(payload.get("y")), expected_version=_int(payload.get("expectedVersion"), -1) if payload.get("expectedVersion") is not None else None)
        elif command_name == "tokens.update":
            result = await service.update_override(**common, token_id=str(payload.get("id") or ""), overrides=payload.get("patch") if isinstance(payload.get("patch"), dict) else {}, expected_version=_int(payload.get("expectedVersion"), -1) if payload.get("expectedVersion") is not None else None)
        else:
            result = await service.remove_from_scene(**common, token_id=str(payload.get("id") or ""))
        if not result.success:
            return _service_error(result.error_key)
        return Response({"token": _plain(result.token), "tokens": _plain(result.tokens or [])})

    if command_name.startswith("geometry."):
        if "Wall" in command_name or "Door" in command_name:
            service = SceneWallService()
            if command_name == "geometry.createWall":
                result = service.create(campaign_id=campaign_id, scene_id=str(payload.get("sceneId") or ""), user_id=user_id, kind=str(payload.get("kind") or "wall"), x1=_float(payload.get("x1")), y1=_float(payload.get("y1")), x2=_float(payload.get("x2")), y2=_float(payload.get("y2")), behavior=payload.get("behavior") if isinstance(payload.get("behavior"), dict) else None, presentation=str(payload.get("presentation") or "normal"), vertical=payload.get("vertical"))
            elif command_name == "geometry.updateWall":
                result = service.update(campaign_id=campaign_id, wall_id=str(payload.get("id") or ""), user_id=user_id, **(payload.get("values") if isinstance(payload.get("values"), dict) else {}))
            elif command_name == "geometry.setDoorState":
                result = service.set_door_state(campaign_id=campaign_id, wall_id=str(payload.get("id") or ""), user_id=user_id, door_state=str(payload.get("state") or ""))
            elif command_name == "geometry.splitWall":
                result = service.split(campaign_id=campaign_id, wall_id=str(payload.get("id") or ""), user_id=user_id, x=_float(payload.get("x")), y=_float(payload.get("y")))
            elif command_name == "geometry.moveWallNode":
                source = payload.get("from") if isinstance(payload.get("from"), dict) else {}
                target = payload.get("to") if isinstance(payload.get("to"), dict) else {}
                result = service.move_node(campaign_id=campaign_id, scene_id=str(payload.get("sceneId") or ""), user_id=user_id, from_x=_float(source.get("x")), from_y=_float(source.get("y")), to_x=_float(target.get("x")), to_y=_float(target.get("y")))
            elif command_name == "geometry.moveWalls":
                wall_ids = [str(value) for value in payload.get("wallIds", [])[:100]] if isinstance(payload.get("wallIds"), list) else []
                result = service.move_many(campaign_id=campaign_id, scene_id=str(payload.get("sceneId") or ""), wall_ids=wall_ids, user_id=user_id, dx=_float(payload.get("dx")), dy=_float(payload.get("dy")))
            elif command_name == "geometry.deleteWalls":
                wall_ids = [str(value) for value in payload.get("wallIds", [])[:100]] if isinstance(payload.get("wallIds"), list) else []
                result = service.delete_many(campaign_id=campaign_id, wall_ids=wall_ids, user_id=user_id)
            else:
                result = service.delete(campaign_id=campaign_id, wall_id=str(payload.get("id") or ""), user_id=user_id)
        else:
            service = SceneLightService()
            values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
            if command_name == "geometry.createLight":
                result = service.create(campaign_id=campaign_id, scene_id=str(payload.get("sceneId") or ""), user_id=user_id, **{k: v for k, v in values.items() if k not in {"sceneId", "id"}})
            elif command_name == "geometry.updateLight":
                result = service.update(campaign_id=campaign_id, light_id=str(payload.get("id") or ""), user_id=user_id, **{k: v for k, v in values.items() if k not in {"sceneId", "id"}})
            else:
                result = service.delete(campaign_id=campaign_id, light_id=str(payload.get("id") or ""), user_id=user_id)
        if not result.success:
            return _service_error(result.error_key)
        public = _plain(result.payload)
        if public.get("wall"): public["wall"] = wall_snapshot(public["wall"])
        if public.get("light"): public["light"] = light_snapshot(public["light"])
        event_scene_id = str((public.get("wall") or {}).get("scene_id") or public.get("scene_id") or payload.get("sceneId") or "")
        event = TransportEvent.SCENE_WALLS_UPDATED if ("Wall" in command_name or "Door" in command_name) else TransportEvent.SCENE_LIGHTS_UPDATED
        await RealtimeTransport().to_room(room_id=campaign_id, event=event, payload={"room_id": campaign_id, "scene_id": event_scene_id, "updated_by": user_id})
        return Response(public)

    if command_name.startswith("effects."):
        kind = str(payload.get("kind") or "particle")
        if kind != "particle":
            return _error("sdk.runtime.effect_kind_unsupported", 400)
        service = SceneParticleService()
        values = payload.get("values") if isinstance(payload.get("values"), dict) else {}
        if command_name == "effects.create":
            result = service.create(campaign_id=campaign_id, scene_id=str(payload.get("sceneId") or ""), user_id=user_id, **values)
        elif command_name == "effects.update":
            identity = {"emitter_id": str(payload.get("id") or "")}
            result = service.update(campaign_id=campaign_id, user_id=user_id, **identity, **values)
        else:
            identity = {"emitter_id": str(payload.get("id") or "")}
            result = service.delete(campaign_id=campaign_id, user_id=user_id, **identity)
        if not result.success:
            return _service_error(result.error_key)
        public = _plain(result.payload)
        if public.get("emitter"): public["emitter"] = particle_snapshot(public["emitter"])
        return Response(public)

    if command_name.startswith("shaders."):
        service = SceneShaderService()
        if command_name == "shaders.apply":
            result = service.apply_preset(
                campaign_id=campaign_id,
                scene_id=str(payload.get("sceneId") or ""),
                user_id=user_id,
                preset_id=str(payload.get("presetId") or ""),
                schema_version=_int(payload.get("schemaVersion"), 1),
                parameters=payload.get("parameters"),
            )
        elif command_name == "shaders.update":
            expected = payload.get("expectedVersion")
            result = service.update_preset(
                campaign_id=campaign_id,
                shader_id=str(payload.get("id") or ""),
                user_id=user_id,
                parameters=payload.get("parameters"),
                expected_version=_int(expected) if expected is not None else None,
            )
        else:
            result = service.remove_preset(
                campaign_id=campaign_id,
                shader_id=str(payload.get("id") or ""),
                user_id=user_id,
            )
        if not result.success:
            return _service_error(result.error_key)
        instance = result.payload.get("instance") if isinstance(result.payload.get("instance"), dict) else {}
        event_scene_id = str(instance.get("sceneId") or result.payload.get("scene_id") or payload.get("sceneId") or "")
        await RealtimeTransport().to_room(
            room_id=campaign_id,
            event=TransportEvent.SCENE_SHADER_PRESETS_UPDATED,
            payload={"room_id": campaign_id, "scene_id": event_scene_id, "schema_version": 1},
        )
        return Response(_plain(result.payload), status_code=201 if command_name == "shaders.apply" else 200)

    if command_name.startswith("combat."):
        service = CombatService()
        if command_name == "combat.start": result = service.start(campaign_id=campaign_id, user_id=user_id, scene_id=payload.get("sceneId"))
        elif command_name == "combat.end": result = service.end(campaign_id=campaign_id, user_id=user_id)
        elif command_name == "combat.advance": result = service.advance_turn(campaign_id=campaign_id, user_id=user_id, delta=_int(payload.get("delta"), 1))
        elif command_name == "combat.setTurn": result = service.set_turn(campaign_id=campaign_id, user_id=user_id, combatant_id=str(payload.get("combatantId") or ""))
        elif command_name == "combat.add": result = service.add_combatants(campaign_id=campaign_id, user_id=user_id, actor_ids=[str(v) for v in payload.get("actorIds", [])][:64], token_ids=[str(v) for v in payload.get("tokenIds", [])][:64])
        else: result = service.remove_combatant(campaign_id=campaign_id, user_id=user_id, combatant_id=str(payload.get("combatantId") or ""))
        if not result.success:
            return _service_error(result.error_key)
        return Response(_plain(result.state_payload()))

    return _error("sdk.runtime.command_unknown", 404)
