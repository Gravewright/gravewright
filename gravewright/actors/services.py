"""Actor directory, resource ownership and revision-checked PDF sheets."""

from copy import deepcopy

from django.db import transaction

from gravewright.campaigns.catalog import get_ruleset
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.services import identifier, member
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError, color, manage, title
from gravewright.pdf_system.schema import normalize

from .models import Actor, Asset, Folder


def types(system_id, *, campaign_id=None):
    ruleset = get_ruleset(system_id, campaign_id=campaign_id)
    return deepcopy(ruleset.get("actorTypes", [])) if ruleset else []


def actor_type(system_id, value=None, *, campaign_id=None):
    available = types(system_id, campaign_id=campaign_id)
    if value is None and available:
        value = available[0]["id"]
    if not isinstance(value, str) or value not in {t["id"] for t in available}:
        raise MapError("Choose an actor type provided by this campaign's system.")
    return value


def access(actor, who, edit=False):
    level = actor.permissions.get(str(who.user_id), "none")
    return who.role == "gm" or level == "owner" or (not edit and level == "read")


def get(value, who, edit=False):
    row = Actor.objects.filter(
        pk=identifier(value), campaign_id=who.campaign_id
    ).first()
    if row is None or not access(row, who, edit):
        raise MapError("Character not found or access denied.", "not_found")
    return row


def revision(row, expected, field="version"):
    if str(getattr(row, field)) != str(expected):
        raise MapError("This sheet was changed in another window.", "conflict")


def image_url(row, kind):
    asset = max(
        (a for a in row.assets.all() if a.kind == kind),
        key=lambda a: a.created_at,
        default=None,
    )
    return f"/game/actors/asset/{asset.pk}" if asset else None


def project(row, who):
    """Serialize actor metadata for one member; this does not include sheet data."""
    return dict(
        id=str(row.pk),
        containerId=str(row.campaign_id),
        name=row.name,
        actorType=row.type,
        systemId=who.campaign.system or "gravewright-pdf-system",
        folderId=str(row.folder_id) if row.folder_id else None,
        canEdit=access(row, who, True),
        version=row.version,
        sheetVersion=row.sheet_version,
        portraitUrl=image_url(row, "portrait"),
        tokenUrl=image_url(row, "token"),
        **({"permissions": row.permissions} if who.role == "gm" else {}),
    )


def state(campaign, user):
    who = member(campaign, user)
    visible = [
        a
        for a in Actor.objects.filter(campaign_id=campaign)
        .prefetch_related("assets")
        .order_by("name")
        if access(a, who)
    ]
    all_folders = {f.pk: f for f in Folder.objects.filter(campaign_id=campaign)}
    allowed = set(all_folders) if who.role == "gm" else set()
    for actor in visible:
        cursor = actor.folder_id
        while cursor in all_folders and cursor not in allowed:
            allowed.add(cursor)
            cursor = all_folders[cursor].parent_id
    return {
        "actorTypes": types(who.campaign.system, campaign_id=who.campaign_id),
        "actors": [project(a, who) for a in visible],
        "folders": [
            dict(
                id=str(f.pk),
                name=f.name,
                label=f.name,
                color=f.color,
                parentId=str(f.parent_id) if f.parent_id else None,
            )
            for f in all_folders.values()
            if f.pk in allowed
        ],
        "templates": [
            {"id": str(a.pk), "name": a.name}
            for a in Asset.objects.filter(campaign_id=campaign, kind="pdf")
        ],
        "is_gm": who.role == "gm",
        "players": [
            {"id": str(m.user_id), "name": m.user.name}
            for m in Membership.objects.select_related("user").filter(
                campaign_id=campaign, role="player"
            )
        ],
    }


def folder(value, who):
    if not value:
        return None
    found = Folder.objects.filter(
        pk=identifier(value), campaign_id=who.campaign_id
    ).first()
    if not found:
        raise MapError("Folder not found.")
    return found


def sheet(campaign, user, actor_id, token_id=None):
    """Read an authorized actor sheet or an unlinked token's independent snapshot."""
    who = member(campaign, user)
    if token_id:
        from gravewright.tokens.services import control
        from gravewright.tokens.services import get as get_token

        t = get_token(token_id, who)
        if identifier(actor_id) != t.actor_id:
            raise MapError("Token does not belong to this actor.", "not_found")
        if not (control(t, who) or access(t.actor, who)):
            raise MapError("Sheet not available.", "forbidden")
        row = t.actor
        data = row.data if t.linked else t.snapshot
        view = project(row, who)
        view.update(
            canEdit=control(t, who),
            sheetVersion=row.sheet_version if t.linked else t.sheet_version,
            name=data.get("token", {}).get("name", row.name)
            if not t.linked
            else row.name,
            tokenId=str(t.pk) if not t.linked else None,
        )
    else:
        row = get(actor_id, who)
        data = row.data
        view = project(row, who)
    view["data"] = deepcopy(data)
    return view


def save_sheet(who, data):
    """Validate revisions and PDF references before updating actor or token sheet data."""
    token = None
    if data.get("tokenId"):
        from gravewright.tokens.services import control
        from gravewright.tokens.services import get as get_token

        token = get_token(data["tokenId"], who)
        if not control(token, who):
            raise MapError("Sheet is read only.", "forbidden")
        row = token.actor
        if token.linked:
            token = None
    else:
        row = get(data.get("actorId"), who, True)
    target = token or row
    revision(target, data.get("sheetVersion"), "sheet_version")
    old = token.snapshot if token else row.data
    clean = normalize(data.get("data"), old, who.role == "gm")
    asset = clean["pdf"]["asset"]
    if (
        asset
        and not Asset.objects.filter(
            pk=identifier(asset), campaign_id=who.campaign_id, kind="pdf"
        ).exists()
    ):
        raise MapError("PDF not found.")
    if token:
        token.snapshot = clean
        token.sheet_version += 1
        token.version += 1
        token.save()
    else:
        revision(row, data.get("version"))
        row.name = title(data.get("name"))
        row.data = clean
        row.version += 1
        row.sheet_version += 1
        row.save()
        from django.db.models import F

        row.tokens.filter(linked=True).update(version=F("version") + 1)
    return {"sheetVersion": target.sheet_version, "version": row.version}


@transaction.atomic
def command(campaign, user, action, data, request_id):
    """Run one actor mutation under the campaign lock, replaying known request IDs."""
    Campaign.objects.select_for_update().get(pk=campaign)
    who = member(campaign, user)
    from gravewright.journals.services import writable
    writable(who)
    if not isinstance(data, dict):
        raise MapError("Invalid actor command.")
    request_id = identifier(request_id)
    receipt = Receipt.objects.filter(
        campaign_id=campaign, user_id=user, request_id=request_id
    ).first()
    if receipt:
        return receipt.result
    result = {}
    if action == "sheet.save":
        result = save_sheet(who, data)
    else:
        manage(who)
        if action == "actor.create":
            clean = normalize(data.get("data", {}))
            aid = clean["pdf"]["asset"]
            if (
                aid
                and not Asset.objects.filter(
                    pk=identifier(aid), campaign_id=campaign, kind="pdf"
                ).exists()
            ):
                raise MapError("PDF not found.")
            row = Actor.objects.create(
                campaign_id=campaign,
                name=title(data.get("name")),
                type=actor_type(
                    who.campaign.system,
                    data.get("type", data.get("actorType")),
                    campaign_id=who.campaign_id,
                ),
                folder=folder(data.get("folderId"), who),
                data=clean,
            )
            result = {"id": str(row.pk)}
        elif action in {"actor.update", "actor.delete", "actor.permissions"}:
            row = get(data.get("id"), who, True)
            if action == "actor.delete":
                row.delete()
            elif action == "actor.permissions":
                levels = data.get("permissions")
                members = {
                    str(m)
                    for m in Membership.objects.filter(
                        campaign_id=campaign, user__is_active=True
                    ).values_list("user_id", flat=True)
                }
                if (
                    not isinstance(levels, dict)
                    or not set(levels) <= members
                    or any(v not in ("none", "read", "owner") for v in levels.values())
                ):
                    raise MapError("Invalid resource permissions.")
                row.permissions = levels
                row.version += 1
                row.save()
            else:
                revision(row, data.get("version"))
                if "name" in data:
                    row.name = title(data["name"])
                if "folderId" in data:
                    row.folder = folder(data["folderId"], who)
                row.version += 1
                row.save()
        elif action.startswith("folder."):
            row = (
                folder(data.get("id"), who)
                if action != "folder.create"
                else Folder(campaign_id=campaign)
            )
            if row is None:
                raise MapError("Folder not found.")
            if action == "folder.delete":

                def remove(f):
                    for child in Folder.objects.filter(parent=f):
                        remove(child)
                    if data.get("recursive"):
                        Actor.objects.filter(folder=f).delete()
                    f.delete()

                remove(row)
            else:
                if "parentId" in data:
                    parent = folder(data["parentId"], who)
                    cursor = parent
                    depth = 0
                    while cursor:
                        if cursor.pk == row.pk or depth >= 2:
                            raise MapError("Invalid folder nesting.")
                        depth += 1
                        cursor = cursor.parent
                    if parent and Folder.objects.filter(parent=row).exists():
                        raise MapError("Move child folders first.")
                    row.parent = parent
                row.name = title(data.get("name", row.name))
                row.color = color(data.get("color", row.color))
                row.save()
        elif action == "asset.delete":
            asset = Asset.objects.filter(
                pk=identifier(data.get("id")), campaign_id=campaign, kind="pdf"
            ).first()
            if not asset:
                raise MapError("PDF not found.")
            from gravewright.tokens.models import Token

            for a in Actor.objects.filter(campaign_id=campaign):
                if a.data.get("pdf", {}).get("asset") == str(asset.pk):
                    a.data["pdf"].update(asset="", template="generic")
                    a.sheet_version += 1
                    a.save()
            for t in Token.objects.filter(scene__campaign_id=campaign, linked=False):
                if t.snapshot.get("pdf", {}).get("asset") == str(asset.pk):
                    t.snapshot["pdf"].update(asset="", template="generic")
                    t.sheet_version += 1
                    t.save()
            asset.delete()
        else:
            raise MapError("Unknown actor command.")
    Receipt.objects.create(
        campaign_id=campaign, user_id=user, request_id=request_id, result=result
    )
    from gravewright.realtime.dispatch import changed
    changed(campaign,user,'actors',action,request_id,result)
    return result
