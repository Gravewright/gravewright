"""Content pack visibility, editing and import into the current campaign.

Portable entry bundles use the same archive validator and dependency graph as
campaign transfer. Public wrappers retain the shared table command boundary."""

from copy import deepcopy
from uuid import UUID
from django.db.models import F, Prefetch
from gravewright.table.domain import manage,identifier,version,title,boolean,document,MapError
from .models import Pack,Entry


def pack(value,who,edit=False):
    from gravewright.table.ownership import resource_allows
    row=Pack.objects.filter(pk=identifier(value),campaign_id=who.campaign_id).first()
    if not row or (who.role!='gm' and (edit or not resource_allows(who,'compendiums',row,default='read' if row.shared else 'none'))):raise MapError('Compendium not found.', 'not_found')
    if edit and row.locked:raise MapError('Unlock the compendium before editing.')
    return row


def state(who,scene_id=None):
    from .catalog import summaries
    from gravewright.table.ownership import resource_allows
    # The directory needs only metadata. Keep document bodies and portable
    # archives out of this query, including for packs the member cannot read.
    entries=Entry.objects.only('id','pack_id','name','kind','version').annotate(entry_type=F('data__type'))
    rows=Pack.objects.filter(campaign_id=who.campaign_id).prefetch_related(Prefetch('entries',queryset=entries)).order_by('name')
    return {'packs':[dict(id=str(p.pk),name=p.name,shared=p.shared,locked=p.locked,version=p.version,systemId=p.system_id,
        entries=[dict(id=str(e.pk),name=e.name,kind=e.kind,type=e.entry_type if isinstance(e.entry_type,str) else '',version=e.version) for e in p.entries.all()]) for p in rows if resource_allows(who,'compendiums',p,default='read' if p.shared else 'none')]+summaries(who),'isGM':who.role=='gm'}


def prepare_import(who, payload):
    """Read and validate immutable file snapshots before entering a write transaction."""
    manage(who)
    if isinstance(payload.get('packId'), str) and payload['packId'].startswith('native:'):
        from .catalog import prepare_import as prepare_native
        return prepare_native(who, payload)
    row = pack(payload.get('packId'), who)
    entry = row.entries.filter(pk=identifier(payload.get('id'))).first()
    if not entry:
        raise MapError('Entry not found.')
    if row.system_id and row.system_id != who.campaign.system:
        raise MapError('This compendium requires a different system.')
    prepared = {'entry': (entry.pk, entry.version, entry.bundle.name, entry.kind, deepcopy(entry.data))}
    if entry.bundle:
        from gravewright.administration.archives import read_archive, MAX_ARCHIVE
        with entry.bundle.open('rb') as file:
            prepared['archive'] = read_archive(file.read(MAX_ARCHIVE + 1))
    return prepared


def command(who,action,p, *, prepared=None):
    if isinstance(p.get('packId'),str) and p['packId'].startswith('native:'):
        from .catalog import command as native_command
        return native_command(who,action,p,prepared=prepared)
    if action=='create':
        manage(who);row=Pack.objects.create(campaign_id=who.campaign_id,name=title(p.get('name')),system_id=who.campaign.system)
        return {'id':str(row.pk)}
    row=pack(p.get('packId'),who)
    if action=='configure':
        manage(who);version(row,p);row.name=title(p.get('name',row.name));row.shared=boolean(p.get('shared',row.shared));row.locked=boolean(p.get('locked',row.locked));row.version+=1;row.save();return {}
    if action=='read':
        if 'ids' in p:
            from .catalog import read_ids
            ids=read_ids(p)
            try:normalized=[UUID(value) for value in ids]
            except (ValueError,TypeError,AttributeError):raise MapError('Invalid compendium entry IDs.', 'invalid_data') from None
            if len(set(normalized)) != len(normalized):raise MapError('Invalid compendium entry IDs.', 'invalid_data')
            entries={str(entry.pk):entry for entry in row.entries.filter(pk__in=normalized)}
            if len(entries) != len(ids):raise MapError('Entry not found.', 'not_found')
            return {'entries':[dict(id=str(entry.pk),name=entry.name,kind=entry.kind,data=deepcopy(entry.data),version=entry.version)
                               for value in normalized for entry in [entries[str(value)]]]}
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
            resource=get(p.get('resourceId'),who);data={'name':resource.name,'type':resource.type,'data':deepcopy(resource.data)}
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
        if prepared is not None and prepared.get('entry') != (entry.pk, entry.version, entry.bundle.name, entry.kind, entry.data):
            raise MapError('This resource changed. Refresh before editing.', 'conflict')
        if entry.bundle:
            from gravewright.administration.archives import _import_validated_campaign
            # Internal direct callers retain validation; public commands always
            # prepare first and compare the live entry while holding the lock.
            prepared = prepared if prepared is not None else prepare_import(who, p)
            result=_import_validated_campaign(*prepared['archive'],who.user,target=who.campaign,merge=True)
            return {'id':str(result.imported_resource),'kind':entry.kind}
        data=deepcopy(entry.data)
        if entry.kind=='actor':
            from gravewright.actors.models import Actor
            from gravewright.actors.services import actor_type
            # Existing snapshots retain explicit document types even when a
            # provider is unavailable; only missing legacy types need a default.
            actor_kind=data.get('type')
            actor_kind=actor_type(who.campaign.system,campaign_id=who.campaign_id) if actor_kind is None else title(actor_kind,80)
            created=Actor.objects.create(campaign_id=who.campaign_id,name=title(data['name']),
                type=actor_kind,data=data['data'])
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
