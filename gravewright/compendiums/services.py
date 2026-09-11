"""Content pack visibility, editing and import into the current campaign.

Portable entry bundles use the same archive validator and dependency graph as
campaign transfer. Public wrappers retain the shared table command boundary."""

from copy import deepcopy
from gravewright.table.domain import manage,identifier,version,title,boolean,document,MapError
from .models import Pack,Entry


def pack(value,who,edit=False):
    row=Pack.objects.filter(pk=identifier(value),campaign_id=who.campaign_id).first()
    if not row or (who.role!='gm' and (edit or not row.shared)):raise MapError('Compendium not found.', 'not_found')
    if edit and row.locked:raise MapError('Unlock the compendium before editing.')
    return row


def state(who,scene_id=None):
    from .catalog import summaries
    rows=Pack.objects.filter(campaign_id=who.campaign_id).prefetch_related('entries').order_by('name')
    return {'packs':[dict(id=str(p.pk),name=p.name,shared=p.shared,locked=p.locked,version=p.version,systemId=p.system_id,
        entries=[dict(id=str(e.pk),name=e.name,kind=e.kind,version=e.version) for e in p.entries.all()]) for p in rows if who.role=='gm' or p.shared]+summaries(who),'isGM':who.role=='gm'}


def command(who,action,p):
    if isinstance(p.get('packId'),str) and p['packId'].startswith('native:'):
        from .catalog import command as native_command
        return native_command(who,action,p)
    if action=='create':
        manage(who);row=Pack.objects.create(campaign_id=who.campaign_id,name=title(p.get('name')),system_id=who.campaign.system)
        return {'id':str(row.pk)}
    row=pack(p.get('packId'),who)
    if action=='configure':
        manage(who);version(row,p);row.name=title(p.get('name',row.name));row.shared=boolean(p.get('shared',row.shared));row.locked=boolean(p.get('locked',row.locked));row.version+=1;row.save();return {}
    if action=='read':
        entry=row.entries.filter(pk=identifier(p.get('id'))).first()
        if not entry:raise MapError('Entry not found.')
        return dict(id=str(entry.pk),name=entry.name,kind=entry.kind,data=deepcopy(entry.data),version=entry.version)
    manage(who)
    if row.locked and action!='import':raise MapError('Unlock the compendium before editing.')
    if action=='delete':version(row,p);row.delete();return {}
    if action=='add':
        kind=p.get('kind')
        if kind=='actor':
            from gravewright.actors.services import get
            resource=get(p.get('resourceId'),who);data={'name':resource.name,'data':deepcopy(resource.data)}
        elif kind=='item':
            from gravewright.items.services import get
            resource=get(p.get('resourceId'),who);data={'name':resource.name,'type':resource.type,'data':deepcopy(resource.data)}
        elif kind=='journal':
            from gravewright.journals.services import get
            resource=get(p.get('resourceId'),who);data={'title':resource.title,'type':resource.type,'data':deepcopy(resource.data)}
        elif kind=='scene':
            from gravewright.maps.services import scene
            resource=scene(p.get('resourceId'),who)
            data={'name':resource.name}
        elif kind=='deck':
            from gravewright.cards.models import Deck
            resource=Deck.objects.filter(pk=identifier(p.get('resourceId')),campaign_id=who.campaign_id).first()
            if not resource:raise MapError('Deck not found.')
            data={'name':resource.name}
        else:raise MapError('Unsupported compendium entry.')
        entry=Entry.objects.create(pack=row,name=title(p.get('name',data.get('name',data.get('title')))),kind=kind,data=data)
        from gravewright.administration.archives import export_campaign
        from django.core.files.base import ContentFile
        model=resource._meta.label_lower
        raw=export_campaign(who.campaign,resource=(model,str(resource.pk)))
        try:
            entry.bundle.save(f'{entry.pk}.zip',ContentFile(raw),save=False)
            entry.save()
        except Exception:
            if entry.bundle:entry.bundle.delete(save=False)
            raise
        row.version+=1;row.save();return {'id':str(entry.pk)}
    entry=row.entries.filter(pk=identifier(p.get('id'))).first()
    if not entry:raise MapError('Entry not found.')
    if action=='remove':version(entry,p);entry.delete();row.version+=1;row.save();return {}
    if action=='import':
        if row.system_id and row.system_id!=who.campaign.system:raise MapError('This compendium requires a different system.')
        if entry.bundle:
            from gravewright.administration.archives import import_campaign,MAX_ARCHIVE
            with entry.bundle.open('rb') as file:raw=file.read(MAX_ARCHIVE+1)
            result=import_campaign(raw,who.user,target=who.campaign,merge=True)
            return {'id':str(result.imported_resource),'kind':entry.kind}
        data=deepcopy(entry.data)
        if entry.kind=='actor':
            from gravewright.actors.models import Actor
            created=Actor.objects.create(campaign_id=who.campaign_id,name=title(data['name']),data=data['data'])
        elif entry.kind=='item':
            from gravewright.items.models import Item
            created=Item.objects.create(campaign_id=who.campaign_id,name=title(data['name']),type=data['type'],system_id=who.campaign.system,data=data['data'])
        else:
            from gravewright.journals.models import Journal
            created=Journal.objects.create(campaign_id=who.campaign_id,title=data['title'],type=data['type'],data=data['data'],creator_id=who.user_id)
        from .assets import restore
        restore(entry,created)
        return {'id':str(created.pk),'kind':entry.kind}
    raise MapError('Unknown compendium action.')


def public_state(campaign_id, user_id, scene_id=None):
    """Authorized extension entry point; raw membership-based helpers stay internal."""
    from gravewright.table.domain import state as read
    return read(campaign_id,user_id,'compendiums',scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    """Use the shared transaction, permission and idempotency boundary."""
    from gravewright.table.domain import command as execute
    return execute(campaign_id,user_id,'compendiums',action,data,request_id)
