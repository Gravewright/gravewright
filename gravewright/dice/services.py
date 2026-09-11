"""Idempotent dice submission, private audiences and committed chat delivery.

A durable claim is recorded before evaluation. Completion rechecks authorization
and persists the result; retries retrieve that result instead of drawing again."""

from datetime import timedelta
from django import forms
from django.db import transaction
from django.utils import timezone

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Membership
from gravewright.chat.models import Message, Recipient
from gravewright.chat.services import public_message, consume_limit
from gravewright.realtime.services import authorize
from .models import Submission
from gravewright.chat.context import scene_for, readable
from .engine import RollError


class RollForm(forms.Form):
    expression = forms.CharField(max_length=512)
    label = forms.CharField(max_length=48, required=False)
    visibility = forms.ChoiceField(choices=[('public', 'Public'), ('gm', 'GM')])
    repeat = forms.IntegerField(min_value=1, max_value=12)
    requestId = forms.UUIDField()


def validate(payload):
    values = {'label': '', 'visibility': 'public', 'repeat': 1, **payload}
    if any(not isinstance(values.get(key), str) for key in ['expression', 'label', 'visibility', 'requestId']) or type(values['repeat']) is not int:
        raise RollError('Invalid roll request.')
    form = RollForm(values)
    if not form.is_valid():
        raise RollError(' '.join(str(e) for errors in form.errors.values() for e in errors))
    return {**form.cleaned_data, 'mapId': payload.get('mapId'), 'block_id': payload.get('block_id')}


def envelope(message):
    audience = list(message.recipients.values_list('user_id', flat=True)) if message.visibility == 'gm' else None
    return public_message(message), [str(pk) for pk in audience] if audience is not None else None


def claim(member_id, data):
    """Reserve a request before random evaluation, or return its completed message."""
    with transaction.atomic():
        member = Membership.objects.select_for_update().filter(pk=member_id).first()
        if member is None or member.role=='streamer':
            raise AuthError('not_a_member')
        previous = Message.objects.filter(campaign_id=member.campaign_id, author_id=member.user_id,
                                           request_id=data['requestId']).first()
        if previous:
            if not readable(member.campaign_id, member.user_id, previous.scene_id): raise AuthError('invalid_scene')
            if previous.roll is None:
                raise RollError('This request ID was already used for a chat message.')
            return None, envelope(previous)
        reservation = Submission.objects.filter(campaign_id=member.campaign_id, author_id=member.user_id,
                                                  request_id=data['requestId']).first()
        if reservation:
            if reservation.error:
                raise RollError(reservation.error)
            if reservation.expires_at <= timezone.now():
                raise RollError('The roll was interrupted. Submit a new roll.')
            raise AuthError('roll_in_progress')
        resolved = scene_for(member, data.get('mapId'), data.get('block_id'))
        data['resolved_scene_id'] = str(resolved.pk) if resolved else None
        consume_limit(member)
        reservation = Submission.objects.create(campaign_id=member.campaign_id, author_id=member.user_id,
            request_id=data['requestId'], expires_at=timezone.now()+timedelta(seconds=15))
        return reservation.pk, None


def fail(reservation_id, error):
    Submission.objects.filter(pk=reservation_id).update(error=str(error)[:512])


def complete(reservation_id, data, result, session_key, campaign_id, user_id):
    """Reauthorize and commit a reserved result with its fixed recipient audience."""
    with transaction.atomic():
        member = authorize(session_key, campaign_id, user_id) if session_key is not None else Membership.objects.select_related('user').filter(campaign_id=campaign_id,user_id=user_id,user__is_active=True).first()
        if member is None or member.role=='streamer':
            raise AuthError('not_a_member')
        # Membership deletion and other submissions serialize against this lock.
        Membership.objects.select_for_update().get(pk=member.pk)
        claim = Submission.objects.select_for_update().get(pk=reservation_id)
        if claim.error or claim.expires_at <= timezone.now():
            raise RollError('The roll was interrupted. Submit a new roll.')
        roll = {'expression': data['expression'], 'label': data['label'],
                'secret': data['visibility'] == 'gm', 'result': result[0] if isinstance(result, list) else result}
        if isinstance(result, list):
            roll['batch'] = [{'label': f'Value {i+1}', 'result': value} for i, value in enumerate(result)]
        scene = scene_for(member, data['resolved_scene_id']) if data.get('resolved_scene_id') else None
        message = Message.objects.create(campaign_id=campaign_id, author_id=user_id, scene=scene,
            author_name=member.user.name, text=data['label'], request_id=data['requestId'],
            visibility=data['visibility'], roll=roll)
        if roll['secret']:
            audience = set(Membership.objects.filter(campaign_id=campaign_id, role='gm').values_list('user_id', flat=True))
            audience.add(user_id)
            Recipient.objects.bulk_create([Recipient(message=message, user_id=pk) for pk in audience])
        from gravewright.realtime.dispatch import message as publish, changed
        publish(campaign_id,message.pk)
        changed(campaign_id,user_id,'dice','roll',data['requestId'])
    return envelope(message)


def roll(campaign_id, user_id, expression, request_id, *, repeat=1, label='', visibility='public', map_id=None):
    """Persist a roll from the native grammar without requiring an HTTP session."""
    data=validate(dict(expression=expression,requestId=str(request_id),repeat=repeat,label=label,visibility=visibility,mapId=map_id))
    member=Membership.objects.filter(campaign_id=campaign_id,user_id=user_id,user__is_active=True).first()
    if member is None or member.role=='streamer':raise AuthError('not_a_member',403)
    reservation,previous=claim(member.pk,data)
    if previous:return previous[0]
    try:
        from .engine import evaluate
        result=evaluate(expression,repeat)
        return complete(reservation,data,result,None,campaign_id,user_id)[0]
    except (AuthError,RollError) as error:
        fail(reservation,error)
        raise
