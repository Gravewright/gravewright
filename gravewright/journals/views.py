from io import BytesIO
from pathlib import Path
import uuid
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from . import services
from .models import Asset


@require_POST
def upload(request):
    if not request.user.is_authenticated:return JsonResponse({'error':'Authentication required.'},status=403)
    try:
        campaign=services.identifier(request.POST.get('campaign_id'))
        who=services.member(campaign,request.user.pk)
        journal=services.get(request.POST.get('journal_id'),who,edit=True)
        file=request.FILES.get('file')
        if not file or file.size>max(settings.JOURNAL_IMAGE_MAX_BYTES,settings.JOURNAL_PDF_MAX_BYTES):raise services.JournalError('Choose an image or PDF within the configured upload limit.')
        raw=file.read()
        limit=settings.JOURNAL_PDF_MAX_BYTES if raw.startswith(b'%PDF-') else settings.JOURNAL_IMAGE_MAX_BYTES
        if len(raw)>limit:raise services.JournalError('Attachment exceeds the configured upload limit.')
        if raw.startswith(b'%PDF-'):
            content_type,extension='application/pdf','.pdf'
        else:
            try:
                with Image.open(BytesIO(raw)) as image:
                    if image.format not in {'PNG','JPEG','WEBP'} or image.width*image.height>40_000_000:raise ValueError()
                    image.load()
                    output=BytesIO();image.convert('RGBA').save(output,format='PNG');raw=output.getvalue()
                content_type,extension='image/png','.png'
            except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError):
                raise services.JournalError('Choose a PNG, JPEG, WebP image or PDF.') from None
        # Recheck after decoding; an upload cannot extend access revoked meanwhile.
        who=services.member(campaign,request.user.pk);services.get(journal.pk,who,edit=True)
        asset=Asset(journal=journal,uploader=request.user,name=Path(file.name).name[:240],content_type=content_type)
        asset.file.save(uuid.uuid4().hex+extension,ContentFile(raw),save=False)
        try:asset.save()
        except Exception:
            asset.file.delete(save=False);raise
        return JsonResponse({'asset_id':str(asset.pk),'src':f'/game/journal/asset/{asset.pk}'})
    except services.JournalError as error:
        return JsonResponse({'error':str(error)},status=400)


@require_GET
def asset(request,asset_id):
    if not request.user.is_authenticated:raise Http404
    try:
        item=Asset.objects.select_related('journal').get(pk=asset_id)
        who=services.member(item.journal.campaign_id,request.user.pk)
        journal=services.get(item.journal_id,who)
        visible=set(services.asset_ids(services.projection(journal,who)))
        pending=str(item.pk) not in set(services.asset_ids(journal.data))
        if str(item.pk) not in visible and not (pending and item.uploader_id==request.user.pk and services.permissions(journal,who)[1]):raise Http404
        response=FileResponse(item.file.open('rb'),content_type=item.content_type)
        response['Cache-Control']='private, no-store'
        response['Content-Disposition']='inline'
        response['X-Content-Type-Options']='nosniff'
        return response
    except (Asset.DoesNotExist,services.JournalError,FileNotFoundError):raise Http404 from None


@require_GET
def state(request,campaign_id):
    if not request.user.is_authenticated:return JsonResponse({'error':'Authentication required.'},status=403)
    try:return JsonResponse(services.state(campaign_id,request.user.pk))
    except services.JournalError:raise Http404 from None


@require_GET
def presentation(request, campaign_id, ticket):
    if not request.user.is_authenticated: raise Http404
    from .presentations import resolve
    try:
        _, view = resolve(ticket, request.user.pk, campaign_id)
        response = JsonResponse(view)
        response['Cache-Control'] = 'private, no-store'
        return response
    except services.JournalError: raise Http404 from None


@require_GET
def presentation_asset(request, ticket, asset_id):
    if not request.user.is_authenticated: raise Http404
    from .presentations import resolve
    try:
        journal, view = resolve(ticket, request.user.pk)
        if str(asset_id) not in set(services.asset_ids(view)): raise Http404
        item = Asset.objects.get(pk=asset_id, journal=journal)
        response = FileResponse(item.file.open('rb'), content_type=item.content_type)
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except (services.JournalError, Asset.DoesNotExist, FileNotFoundError): raise Http404 from None
