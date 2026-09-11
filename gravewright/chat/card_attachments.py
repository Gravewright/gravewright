"""Card-message media with the same membership, audience and scene checks as chat."""
import uuid
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET
from gravewright.campaigns.models import Membership
from .context import readable
from .models import CardAttachment


def capture(message, cards):
    files=[]
    metadata=[]
    try:
        for card in cards:
            row=CardAttachment(message=message)
            for face,source in [('front',card.front if card.revealed else None),('back',card.deck.back)]:
                if not source:continue
                target=getattr(row,face)
                with source.open('rb') as stream:
                    target.save(uuid.uuid4().hex+'.webp',stream,save=False)
                files.append(target)
            row.save()
            root=f'/game/chat/{message.pk}/cards/{row.pk}'
            metadata.append({'id':str(card.pk),'name':card.name if card.revealed else 'Card',
                             'face_state':'face_up' if card.revealed else 'face_down',
                             'frontUrl':root+'/front' if row.front else None,
                             'backUrl':root+'/back' if row.back else None})
        message.metadata['cards']=metadata
        message.save(update_fields=['metadata'])
    except Exception:
        for file in files:file.delete(save=False)
        raise


@require_GET
def media(request,message_id,attachment_id,face):
    if not request.user.is_authenticated or face not in ('front','back'):raise Http404
    row=CardAttachment.objects.select_related('message').filter(pk=attachment_id,message_id=message_id).first()
    if row is None or row.message.deleted:raise Http404
    message=row.message
    if not Membership.objects.filter(campaign_id=message.campaign_id,user=request.user).exists():raise Http404
    if message.visibility!='public' and not message.recipients.filter(user=request.user).exists():raise Http404
    if not readable(message.campaign_id,request.user.pk,message.scene_id):raise Http404
    file=getattr(row,face)
    if not file:raise Http404
    try:response=FileResponse(file.open('rb'),content_type='image/webp')
    except FileNotFoundError:raise Http404 from None
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff'
    return response


@receiver(post_delete,sender=CardAttachment)
def cleanup(sender,instance,**kwargs):
    for file in (instance.front,instance.back):
        if file:
            storage,name=file.storage,file.name
            transaction.on_commit(lambda s=storage,n=name:s.delete(n))
