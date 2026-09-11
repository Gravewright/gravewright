"""SDK DTO adapters; permissions and movement stay in the native Python services."""

import base64
import json
import uuid

from django.db import transaction
from django.http import FileResponse

from gravewright.actors import services as actors
from gravewright.actors.models import Actor, Asset
from gravewright.actors.views import publish
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import JournalError, member
from gravewright.maps.services import MapError, title
from gravewright.tokens import services as tokens

from .packages import ModuleFailure


def revision(*parts):
    return base64.urlsafe_b64encode(
        json.dumps(parts, separators=(",", ":"), default=str).encode()
    ).decode()


def invoke(request, table_id, scene_id, name, payload, upload=None):
    Campaign.objects.select_for_update().get(pk=table_id)
    who = member(table_id, request.user.pk)

    def changed():
        transaction.on_commit(lambda: publish(table_id))

    def dto(row):
        return {
            "id": str(row.pk),
            "tableId": str(table_id),
            "name": row.name,
            "type": "character",
            "systemId": who.campaign.system or "gravewright-pdf-system",
            "revision": revision("actor", row.pk, row.version),
            "canEdit": actors.access(row, who, True),
            "data": row.data,
            "portraitUrl": actors.image_url(row, "portrait"),
            "tokenUrl": actors.image_url(row, "token"),
        }

    def expected(value):
        if value != payload.get("expectedRevision"):
            raise ModuleFailure("conflict")

    try:
        if name == "actor.list":
            rows = [
                row
                for row in Actor.objects.filter(campaign_id=table_id)
                .prefetch_related("assets")
                .order_by("id")
                if actors.access(row, who)
            ]
            if payload.get("cursor"):
                rows = [row for row in rows if str(row.pk) > payload["cursor"]]
            limit = payload.get("limit", 50)
            return {
                "items": [dto(row) for row in rows[:limit]],
                "nextCursor": str(rows[limit - 1].pk) if len(rows) > limit else None,
            }
        if name == "actor.create":
            if payload.get("type", "character") != "character":
                raise ModuleFailure("invalid_data")
            result = actors.command(
                table_id, request.user.pk, name, payload, uuid.uuid4()
            )
            changed()
            return dto(actors.get(result["id"], who))
        if name in ("actor.read", "actor.update", "actor.delete"):
            row = actors.get(payload["id"], who, name != "actor.read")
            if name != "actor.read":
                expected(revision("actor", row.pk, row.version))
                if name == "actor.delete":
                    row.delete()
                    changed()
                    return None
                if payload["changes"]:
                    row.name = title(payload["changes"].get("name", row.name))
                    row.version += 1
                    row.save()
                    changed()
            return dto(row)
        if name.startswith(("actor.data.", "token.data.")):
            token = (
                tokens.get(payload["id"], who) if name.startswith("token.") else None
            )
            if token and token.scene_id != scene_id:
                raise ModuleFailure("not_found")
            row = token.actor if token else actors.get(payload["id"], who)
            view = actors.sheet(
                table_id, request.user.pk, row.pk, token.pk if token else None
            )
            source = token if token and not token.linked else row
            kind = "token-data" if source is token else "actor-data"
            if name.endswith("update"):
                expected(revision(kind, source.pk, source.sheet_version))
                actors.save_sheet(
                    who,
                    {
                        "actorId": str(row.pk),
                        "tokenId": str(token.pk) if token else None,
                        "name": row.name,
                        "version": row.version,
                        "sheetVersion": source.sheet_version,
                        "data": payload["data"],
                    },
                )
                source.refresh_from_db()
                view = actors.sheet(
                    table_id, request.user.pk, row.pk, token.pk if token else None
                )
                changed()
            return {
                "id": payload["id"],
                "revision": revision(kind, source.pk, source.sheet_version),
                "data": view["data"],
            }
        if name in ("token.read", "token.move"):
            token = tokens.get(payload["id"], who)
            if token.scene_id != scene_id:
                raise ModuleFailure("not_found")
            cell, ox, oy, _, _ = tokens.geometry(token.scene)
            size = tokens.data(token)["token"]["size"]
            if name == "token.move":
                expected(revision("token", token.pk, token.version))
                tokens.command(
                    table_id,
                    request.user.pk,
                    "move",
                    {
                        "mapId": str(scene_id),
                        "id": str(token.pk),
                        "version": token.version,
                        "gridX": (payload["position"]["x"] - ox) / cell - size / 2,
                        "gridY": (payload["position"]["y"] - oy) / cell - size / 2,
                    },
                    uuid.uuid4(),
                )
                token.refresh_from_db()
                changed()
            return {
                "id": str(token.pk),
                "sceneId": str(scene_id),
                "actorId": str(token.actor_id),
                "revision": revision("token", token.pk, token.version),
                "canControl": tokens.control(token, who),
                "position": {
                    "x": ox + (token.grid_x + size / 2) * cell,
                    "y": oy + (token.grid_y + size / 2) * cell,
                },
            }
        if name == "asset.list":
            return {
                "items": [
                    {
                        "id": str(a.pk),
                        "name": a.name,
                        "contentType": "application/pdf",
                        "createdAt": a.created_at.isoformat(),
                    }
                    for a in Asset.objects.filter(
                        campaign_id=table_id, kind="pdf"
                    ).order_by("created_at")
                ]
            }
        if name == "asset.download":
            row = Asset.objects.filter(
                pk=payload["id"], campaign_id=table_id, kind="pdf"
            ).first()
            if not row:
                raise ModuleFailure("not_found")
            return FileResponse(
                row.file.open("rb"),
                as_attachment=True,
                filename=row.name,
                content_type="application/pdf",
            )
        if name in ("asset.upload", "actor.image.upload"):
            if upload is None:
                raise ModuleFailure("invalid_data")
            # Reuse the native upload validator, with the actual request/user/CSRF context.
            from gravewright.actors.views import upload as upload_asset

            request.POST = request.POST.copy()
            request.POST["kind"] = "pdf" if name == "asset.upload" else payload["kind"]
            if name == "actor.image.upload":
                request.POST["actorId"] = payload["id"]
                row = actors.get(payload["id"], who, True)
            response = upload_asset(request, table_id)
            if response.status_code != 200:
                raise ModuleFailure("invalid_data")
            result = json.loads(response.content)
            if name == "actor.image.upload":
                row.version += 1
                row.save()
                return {"url": result["url"]}
            asset = Asset.objects.get(pk=result["id"])
            return {
                "id": str(asset.pk),
                "name": asset.name,
                "contentType": "application/pdf",
                "createdAt": asset.created_at.isoformat(),
            }
        raise ModuleFailure("unavailable")
    except (MapError, JournalError) as error:
        raise ModuleFailure(
            {"forbidden": "permission_denied",
                "blocked": "permission_denied",
                "not_a_member": "permission_denied", "invalid_input": "invalid_data"}.get(
                error.code, error.code
            )
        ) from None
