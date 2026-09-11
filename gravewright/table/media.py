"""Authenticated module uploads; assets never become public static files."""
import io
import uuid
import re
from django.db import transaction
from django.core.files.base import ContentFile
from django.http import FileResponse, JsonResponse, Http404, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST, require_GET
from PIL import Image, UnidentifiedImageError
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import member, JournalError
from gravewright.maps.services import manage, MapError, title
from gravewright.audio.models import Track
from gravewright.cards.models import Card, Deck, CardAsset


def announce(campaign):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    for module in ('audio','cards'):
        async_to_sync(get_channel_layer().group_send)(f'table.{campaign.hex}',{'type':'room.resources','module':module})


@require_POST
def upload(request,campaign_id,kind):
    if not request.user.is_authenticated:return JsonResponse({'error':'Authentication required.'},status=403)
    file=None
    try:
        who=member(campaign_id,request.user.pk);manage(who)
        incoming=request.FILES.get('file')
        if not incoming or incoming.size>128*1024*1024:raise MapError('Choose a file up to 128 MiB.')
        name=title(request.POST.get('name') or incoming.name[:120])
        if kind=='audio':
            from gravewright.audio.metadata import inspect
            content_type,extension,duration=inspect(incoming)
            row=Track(campaign_id=campaign_id,name=name,content_type=content_type,duration=duration,loop=request.POST.get('purpose')!='effect',kind='effect' if request.POST.get('purpose')=='effect' else 'ambience')
            row.file.save(uuid.uuid4().hex+extension,incoming,save=False);file=row.file
        elif kind in ('card-front','deck-back','card-asset'):
            if incoming.size>10*1024*1024:raise MapError('Choose a card image up to 10 MiB.')
            try:
                with Image.open(incoming) as image:
                    if image.format not in ('PNG','JPEG','WEBP') or image.width*image.height>16_000_000:raise ValueError()
                    output=io.BytesIO();image.convert('RGBA').save(output,format='WEBP');raw=output.getvalue()
            except (ValueError,OSError,Image.DecompressionBombError):raise MapError('Choose a valid card image.') from None
            from gravewright.journals.services import identifier
            if kind=='card-asset':
                purpose=request.POST.get('purpose','card_front')
                if purpose not in ('card_front','card_back'):raise MapError('Invalid card asset.')
                row=CardAsset(campaign_id=campaign_id,uploader=request.user,purpose=purpose);field='file'
            elif kind=='card-front':
                row=Card.objects.filter(pk=identifier(request.POST.get('id')),deck__campaign_id=campaign_id).first();field='front'
            else:row=Deck.objects.filter(pk=identifier(request.POST.get('id')),campaign_id=campaign_id).first();field='back'
            if not row:raise MapError('Card or deck not found.')
            old=getattr(row,field).name
            file=getattr(row,field);file.save(uuid.uuid4().hex+'.webp',ContentFile(raw),save=False)
        else:raise MapError('Unknown upload type.')
        with transaction.atomic():
            Campaign.objects.select_for_update().get(pk=campaign_id)
            manage(member(campaign_id,request.user.pk))
            if kind not in ('audio','card-asset'):
                exists=type(row).objects.filter(pk=row.pk).exists()
                if not exists:raise MapError('Resource was removed during upload.')
                row.version+=1;row.save(update_fields=[field,'version'])
                if old:transaction.on_commit(lambda s=file.storage,n=old:s.delete(n))
            else:
                if kind=='audio' and request.POST.get('folder_id'):
                    from gravewright.maps.models import AssetFolder
                    from gravewright.journals.services import identifier
                    folder=AssetFolder.objects.filter(pk=identifier(request.POST['folder_id']),campaign_id=campaign_id).first()
                    if not folder:raise MapError('Folder not found.')
                    row.folder=folder
                row.save()
            transaction.on_commit(lambda:announce(campaign_id))
        return JsonResponse({'id':str(row.pk),'asset_id':str(row.pk)})
    except (MapError,JournalError) as error:
        if file and file.name:file.storage.delete(file.name)
        return JsonResponse({'error':str(error)},status=400)
    except Exception:
        if file and file.name:file.storage.delete(file.name)
        raise


@require_GET
def audio_file(request,track_id):
    if not request.user.is_authenticated:raise Http404
    row=Track.objects.filter(pk=track_id).first()
    try:
        if not row:raise Http404
        member(row.campaign_id,request.user.pk)
        size=row.file.size
        requested=request.headers.get('Range')
        if requested:
            match=re.fullmatch(r'bytes=([0-9]{0,20})-([0-9]{0,20})',requested)
            if not match or not any(match.groups()):
                response=HttpResponse(status=416);response['Content-Range']=f'bytes */{size}';return response
            left,right=match.groups()
            start=int(left) if left else max(0,size-int(right))
            end=min(size-1,int(right)) if left and right else size-1
            if start>end or start>=size:
                response=HttpResponse(status=416);response['Content-Range']=f'bytes */{size}';return response
            def chunks():
                with row.file.open('rb') as source:
                    source.seek(start);remaining=end-start+1
                    while remaining:
                        data=source.read(min(65536,remaining))
                        if not data:break
                        remaining-=len(data);yield data
            response=StreamingHttpResponse(chunks(),status=206,content_type=row.content_type)
            response['Content-Range']=f'bytes {start}-{end}/{size}';response['Content-Length']=str(end-start+1)
        else:response=FileResponse(row.file.open('rb'),content_type=row.content_type)
        response['Accept-Ranges']='bytes';response['X-Content-Type-Options']='nosniff'
        response['Cache-Control']='private, no-store';return response
    except (JournalError,FileNotFoundError):raise Http404 from None


@require_GET
def card_file(request,kind,object_id,face):
    if not request.user.is_authenticated:raise Http404
    try:
        if kind=='deck' and face=='back':
            row=Deck.objects.get(pk=object_id);member(row.campaign_id,request.user.pk);file=row.back
        elif kind=='card' and face=='front':
            row=Card.objects.select_related('deck').get(pk=object_id);who=member(row.deck.campaign_id,request.user.pk)
            if not (who.role=='gm' or row.zone=='hand' and row.owner_id==who.user_id or row.zone=='scene' and row.revealed):raise Http404
            if row.zone=='scene':
                from gravewright.maps.services import scene
                scene(row.scene_id,who)
            file=row.front
        else:raise Http404
        if not file:raise Http404
        response=FileResponse(file.open('rb'),content_type='image/webp');response['Cache-Control']='private, no-store';return response
    except (Card.DoesNotExist,Deck.DoesNotExist,JournalError,MapError,FileNotFoundError):raise Http404 from None
