"""Bounded, GM-only reusable object bundles, scoped to their campaign assets."""
from django.db import transaction
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier
from . import builder_services as builder, services
from .models import BuilderObjectPreset


def clean_bundle(raw, who):
    document = builder.clean_document(raw, who)
    count = sum(len(document.get(kind, [])) for kind in ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders", "regions"))
    if not 1 <= count <= 100:
        raise services.MapError("Object library limit exceeded.")
    return document


def catalog(campaign, user):
    who = builder.authority(campaign, user)
    return {"presets": [{"id": str(row.pk), "name": row.name}
                        for row in BuilderObjectPreset.objects.filter(campaign_id=who.campaign_id)]}


def detail(campaign, user, preset_id):
    who = builder.authority(campaign, user)
    row = BuilderObjectPreset.objects.filter(campaign_id=campaign, pk=preset_id).first()
    if not row:
        raise services.MapError("Object preset not found.", "not_found")
    return {"id": str(row.pk), "name": row.name, "document": clean_bundle(row.document, who)}


@transaction.atomic
def save(campaign, user, payload):
    who = builder.authority(campaign, user)
    Campaign.objects.select_for_update().get(pk=campaign)
    who = builder.authority(campaign, user)
    if not isinstance(payload, dict) or set(payload) != {"request_id", "name", "document"}:
        raise services.MapError("Invalid object preset.")
    request_id = identifier(payload["request_id"])
    digest = builder.fingerprint("builder-object-preset", campaign, payload)
    previous = builder.replay(campaign, user, request_id, digest)
    if previous is not None:
        return previous
    document = clean_bundle(payload["document"], who)
    if BuilderObjectPreset.objects.filter(campaign_id=campaign).count() >= 128:
        raise services.MapError("Object library limit exceeded.")
    row = BuilderObjectPreset.objects.create(campaign_id=campaign, name=services.title(payload["name"]), document=document)
    result = {"id": str(row.pk), "operation": "builder-object-preset"}
    builder.record(campaign, user, request_id, digest, result)
    return result


@transaction.atomic
def remove(campaign, user, preset_id):
    builder.authority(campaign, user)
    BuilderObjectPreset.objects.filter(campaign_id=campaign, pk=preset_id).delete()
    return {"removed": str(preset_id)}
