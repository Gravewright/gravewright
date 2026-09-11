"""Compendium snapshots own their files independently of the source document."""
from .models import EntryAsset
from gravewright.maps.services import MapError


def identifiers(value):
    if isinstance(value, dict):
        return {key for child in value.values() for key in identifiers(child)}
    if isinstance(value, list):
        return {key for child in value for key in identifiers(child)}
    return {value} if isinstance(value, str) else set()


def capture(entry, resource, kind):
    if kind == 'actor':
        from gravewright.actors.models import Asset
        from django.db.models import Q
        refs = identifiers(resource.data)
        assets = Asset.objects.filter(campaign_id=resource.campaign_id).filter(
            Q(actor=resource) | Q(pk__in=[a.pk for a in Asset.objects.filter(campaign_id=resource.campaign_id) if str(a.pk) in refs]))
    elif kind == 'journal':
        from gravewright.journals.models import Asset
        assets = Asset.objects.filter(journal=resource)
    else:
        return
    saved = []
    total = 0
    try:
        for source in assets:
            if not source.file:
                continue
            total += source.file.size
            if total > 256*1024*1024:
                raise MapError('Compendium document assets exceed 256 MiB.')
            asset = EntryAsset(entry=entry,source_id=source.pk,kind=source.kind if kind=='actor' else source.content_type,name=source.name)
            with source.file.open('rb') as file:
                asset.file.save(source.file.name.rsplit('/',1)[-1],file,save=False)
            saved.append(asset.file)
            asset.save()
    except Exception:
        for file in saved:
            file.delete(save=False)
        raise


def restore(entry, document):
    if entry.kind == 'actor':
        from gravewright.actors.models import Asset
        relation = {'actor':document,'campaign_id':document.campaign_id}
    elif entry.kind == 'journal':
        from gravewright.journals.models import Asset
        relation = {'journal':document}
    else:
        return
    mapping = {}
    saved = []
    try:
        for source in entry.assets.all():
            asset = Asset(**relation,**({'kind':source.kind} if entry.kind=='actor' else {'content_type':source.kind}),name=source.name)
            with source.file.open('rb') as file:
                asset.file.save(source.file.name.rsplit('/',1)[-1],file,save=False)
            saved.append(asset.file)
            asset.save()
            mapping[str(source.source_id)] = str(asset.pk)
        from gravewright.administration.archives import rewrite
        document.data = rewrite(document.data,mapping,{})
        document.save(update_fields=['data'])
    except Exception:
        for file in saved:
            file.delete(save=False)
        raise
