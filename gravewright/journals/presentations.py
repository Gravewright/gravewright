"""Recipient-bound, short-lived read access without permanent journal grants."""

from types import SimpleNamespace

from django.conf import settings
from django.core import signing

from . import services
from .models import Journal

TTL = 90
SALT = "gravewright.journal.presentation.v1"


def present(who, payload):
    if who.role != "gm":
        raise services.JournalError("Only the GM can present a journal.", "forbidden")
    journal = services.get(payload.get("journal_id"), who)
    target = payload.get("target", "")
    if target and not settings.TARGETED_HANDOUTS_ENABLED:
        raise services.JournalError("Targeted handouts are disabled.", "forbidden")
    if target:
        target = str(
            services.member(who.campaign_id, services.identifier(target)).user_id
        )
    return {
        "presentation": {
            "journal_id": str(journal.pk),
            "campaign_id": str(who.campaign_id),
            "issuer": str(who.user_id),
            "target": target,
        }
    }


def ticket(event, user_id):
    return signing.dumps({**event, "user_id": str(user_id)}, salt=SALT)


def resolve(value, user_id, campaign_id=None):
    try:
        data = signing.loads(value, salt=SALT, max_age=TTL)
        if data["user_id"] != str(user_id) or (
            campaign_id and data["campaign_id"] != str(campaign_id)
        ):
            raise ValueError()
        who = services.member(data["campaign_id"], user_id)
        if services.member(who.campaign_id, data["issuer"]).role != "gm":
            raise ValueError()
        journal = Journal.objects.prefetch_related("access").get(
            pk=data["journal_id"], campaign_id=who.campaign_id
        )
        # Presentations always project player content, including when the recipient is a GM.
        view = services.projection(
            journal,
            SimpleNamespace(
                role="player", user_id=who.user_id, campaign_id=who.campaign_id
            ),
        )
        view.update(can_edit=False, listed=False, presentation_ticket=value)
        view.pop("permissions", None)

        def rewrite(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    item[key] = rewrite(child)
            elif isinstance(item, list):
                return [rewrite(child) for child in item]
            elif isinstance(item, str) and item.startswith("/game/journal/asset/"):
                return f"/game/handouts/presentation/{value}/asset/{item.rsplit('/', 1)[-1]}"
            return item

        return journal, rewrite(view)
    except signing.BadSignature, Journal.DoesNotExist, KeyError, ValueError, TypeError:
        raise services.JournalError(
            "The presentation expired or is unavailable.", "not_found"
        ) from None
