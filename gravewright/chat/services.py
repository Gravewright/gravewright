"""Campaign chat history, whispers, emotes and moderation with shared flood limits.

Persisted message identities also protect dice/chat retries. Recipient and scene
checks belong to the service and delivery paths, not to the browser renderer."""

from datetime import timedelta

from django import forms
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Membership
from .models import Message, SendWindow, Recipient
from .context import scene_for, readable

HISTORY_LIMIT = 100


class MessageForm(forms.Form):
    text = forms.CharField(max_length=2000, strip=True)
    request_id = forms.UUIDField()


def public_message(message):
    """Serialize stored content; callers must still enforce scene and audience access."""
    if message.deleted:
        return {'id': str(message.pk), 'tableId': str(message.campaign_id), 'deleted': True, 'audience': []}
    targets = (
        list(
            message.recipients.exclude(user_id=message.author_id).values_list(
                "user__name", flat=True
            )
        )
        if message.visibility == "whisper"
        else []
    )
    return {
        "target_names": targets,
        "id": str(message.pk),
        "tableId": str(message.campaign_id),
        "from": {
            "id": str(message.author_id) if message.author_id else None,
            "name": message.author_name,
        },
        "sceneId": str(message.scene_id) if message.scene_id else None,
        "blockId": str(message.scene.block_id) if message.scene_id else None,
        "visibility": message.visibility,
        "audience": [
            str(pk) for pk in message.recipients.values_list("user_id", flat=True)
        ]
        if message.visibility != "public"
        else None,
        "roll": message.roll,
        "metadata": message.metadata,
        "text": message.text,
        "at": int(message.created_at.timestamp() * 1000),
        "html": render_to_string(
            "gravewright_chat/message.html",
            {"message": message, "target_names": targets},
            using="jinja2",
        ),
    }


def history(campaign_id, user_id, map_id=None):
    """Read the last visible messages for the selected/broadcast scene and table."""
    who = Membership.objects.filter(campaign_id=campaign_id, user_id=user_id,user__is_active=True).first()
    if not who:
        raise AuthError("not_a_member")
    if who.role=='streamer':
        from gravewright.campaigns.streamer import active
        if not active(user_id,campaign_id):raise AuthError('not_a_member',403)
    scene = scene_for(who, map_id)
    rows = list(
        Message.objects.select_related("scene")
        .filter(campaign_id=campaign_id, deleted=False)
        .filter(Q(scene=scene) | Q(scene__isnull=True))
        .filter(Q(visibility="public") | Q(recipients__user_id=user_id))
        .distinct()
        .order_by("-id")[:HISTORY_LIMIT]
    )
    return [public_message(row) for row in reversed(rows)]


def say(membership_id, text, request_id, map_id=None):
    """Persist chat once, interpreting supported slash commands and recipient scope."""
    if not isinstance(text, str) or not isinstance(request_id, str):
        raise AuthError("invalid_input")
    form = MessageForm({"text": text, "request_id": request_id})
    if not form.is_valid():
        raise AuthError("invalid_message")
    with transaction.atomic():
        member = (
            Membership.objects.select_for_update()
            .select_related("user")
            .filter(pk=membership_id, user__is_active=True)
            .first()
        )
        if member is not None and member.role=='streamer':raise AuthError('read_only',403)
        if member is None:
            raise AuthError("not_a_member", 403)
        previous = Message.objects.filter(
            campaign=member.campaign_id,
            author=member.user_id,
            request_id=form.cleaned_data["request_id"],
        ).first()
        if previous:
            if not readable(member.campaign_id, member.user_id, previous.scene_id):
                raise AuthError("invalid_scene")
            return public_message(previous), False
        from gravewright.dice.models import Submission

        if Submission.objects.filter(
            campaign_id=member.campaign_id,
            author_id=member.user_id,
            request_id=form.cleaned_data["request_id"],
        ).exists():
            raise AuthError("invalid_input")
        scene = scene_for(member, map_id)
        content = form.cleaned_data["text"]
        recipients = None
        metadata = {}
        if content.lower().startswith('/gm '):
            content = content[4:].strip()
            recipients = set(Membership.objects.filter(campaign_id=member.campaign_id, role='gm', user__is_active=True).values_list('user_id', flat=True)) | {member.user_id}
        elif content.lower().startswith('/me '):
            content = content[4:].strip()
            metadata = {'emote': True}
        elif content.startswith('/') and not content.lower().startswith(('/w ', '/whisper ')):
            raise AuthError('invalid_chat_command')
        if not content:
            raise AuthError('invalid_message')
        if form.cleaned_data["text"].lower().startswith(("/w ", "/whisper ")):
            arg = content.split(" ", 1)[1].strip()
            members = list(
                Membership.objects.filter(
                    campaign_id=member.campaign_id, user__is_active=True
                ).select_related("user")
            )
            matches = [
                m
                for m in members
                if arg.casefold().startswith(m.user.name.strip().casefold() + " ")
            ]
            if not matches:
                raise AuthError("invalid_whisper_target")
            target = max(
                matches, key=lambda m: len(m.user.name.strip())
            ).user.name.strip()
            content = arg[len(target) :].strip()
            if not content:
                raise AuthError("invalid_message")
            recipients = {
                m.user_id
                for m in matches
                if m.user.name.strip().casefold() == target.casefold()
            } | {member.user_id}
        consume_limit(member)
        message = Message.objects.create(
            campaign_id=member.campaign_id,
            author=member.user,
            author_name=member.user.name,
            text=content,
            metadata=metadata,
            scene=scene,
            visibility="whisper" if recipients else "public",
            request_id=form.cleaned_data["request_id"],
        )
        if recipients:
            Recipient.objects.bulk_create(
                [Recipient(message=message, user_id=pk) for pk in recipients]
            )
        from gravewright.realtime.dispatch import message as publish, changed
        publish(member.campaign_id,message.pk)
        changed(member.campaign_id,member.user_id,'chat','send',message.request_id)
    return public_message(message), True


def consume_limit(member):
    """Call while holding the membership lock in a transaction."""
    now = timezone.now()
    window, _ = SendWindow.objects.select_for_update().get_or_create(
        membership=member, defaults={"expires_at": now + timedelta(seconds=10)}
    )
    if window.expires_at <= now:
        window.count, window.expires_at = 0, now + timedelta(seconds=10)
    if window.count >= 20:
        raise AuthError("too_many_messages", 429)
    window.count += 1
    window.save()


def send(campaign_id, user_id, text, request_id, map_id=None):
    """Send as a live campaign member; authorization never comes from an extension role."""
    member = Membership.objects.filter(campaign_id=campaign_id,user_id=user_id,user__is_active=True).first()
    if member is None:raise AuthError('not_a_member',403)
    return say(member.pk,text,str(request_id),map_id)[0]


def remove(campaign_id, user_id, message_id=None):
    """GM moderation, campaign-wide when no message is specified.

    Keep submission identities so retries cannot recreate removed messages.
    """
    with transaction.atomic():
        member = Membership.objects.select_for_update().filter(
            campaign_id=campaign_id, user_id=user_id, user__is_active=True).first()
        if member is None or member.role != 'gm':
            raise AuthError('gm_required', 403)
        rows = Message.objects.filter(campaign_id=campaign_id, deleted=False)
        if message_id is not None:
            if not str(message_id).isdigit():
                raise AuthError('invalid_input')
            rows = rows.filter(pk=message_id)
        # Remove content and attachments, preserving only the retry receipt.
        from .models import CardAttachment
        CardAttachment.objects.filter(message__in=rows).delete()
        count = rows.update(deleted=True, text='', roll=None, metadata={})
        from gravewright.realtime.dispatch import send as publish
        transaction.on_commit(lambda: publish(campaign_id, {'type':'room.chat_refresh'}), robust=True)
        return {'removed': count}
