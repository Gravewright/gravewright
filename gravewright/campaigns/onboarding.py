"""Persist initial GM progress and the player's atomic first-visit claim."""
from django.db import transaction
from django.utils import timezone
from gravewright.accounts.services import AuthError
from .models import AccessCode, Campaign, Membership, Onboarding
from .services import get_campaign


def state(user, campaign_id):
    campaign=get_campaign(user,campaign_id,manage=True)
    from gravewright.actors.models import Actor
    from gravewright.maps.models import Scene
    from django.db.models import Q, F
    steps=dict(campaign=True,system=bool(campaign.system),
        character=Actor.objects.filter(campaign=campaign).exists(),
        scene=Scene.objects.filter(campaign=campaign).exists(),
        code=AccessCode.objects.filter(campaign=campaign,kind='invite',revoked_at__isnull=True,
            expires_at__gt=timezone.now()).filter(Q(max_uses=None)|Q(use_count__lt=F('max_uses'))).exists())
    preference=Onboarding.objects.filter(membership__campaign=campaign,membership__user=user).first()
    completed=sum(steps.values())
    return dict(campaign_id=str(campaign.pk),steps=steps,completed=completed,total=5,
                finished=completed==5,dismissed=preference.dismissed if preference else False)


@transaction.atomic
def preference(user,campaign_id,dismissed):
    get_campaign(user,campaign_id,manage=True)
    if type(dismissed) is not bool:raise AuthError('invalid_input')
    Campaign.objects.select_for_update().get(pk=campaign_id)
    who=Membership.objects.get(campaign_id=campaign_id,user=user)
    Onboarding.objects.update_or_create(membership=who,defaults={'dismissed':dismissed})
    return state(user,campaign_id)


@transaction.atomic
def claim(user,campaign_id):
    get_campaign(user,campaign_id)
    Campaign.objects.select_for_update().get(pk=campaign_id)
    who=Membership.objects.get(campaign_id=campaign_id,user=user)
    if who.role!='player':raise AuthError('player_required',403)
    row,_=Onboarding.objects.get_or_create(membership=who)
    # Conditional write also makes the claim safe across concurrent sessions.
    show=Onboarding.objects.filter(pk=row.pk,player_shown_at=None).update(player_shown_at=timezone.now())==1
    return {'show':show}
