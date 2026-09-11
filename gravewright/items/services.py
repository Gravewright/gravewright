"""Item permissions, directory projections and mutations inside table.domain.

The native PDF system currently supplies no item types. Extension-facing callers
must use public_state/public_command, which recheck membership and record retries."""

from copy import deepcopy
from gravewright.table.domain import title, color, manage, identifier, version, document, permissions, MapError
from .models import Item, Folder


def types(system_id):
    # The original native PDF system declares no item document types.
    return []


def access(row, who, edit=False):
    level = row.permissions.get(str(who.user_id),'none')
    return who.role == 'gm' or level == 'owner' or (not edit and level == 'read')


def get(value, who, edit=False):
    row = Item.objects.filter(pk=identifier(value),campaign_id=who.campaign_id).first()
    if row is None or not access(row,who,edit):
        raise MapError('Item not found.', 'not_found')
    return row


def project(row, who):
    return dict(id=str(row.pk),name=row.name,type=row.type,systemId=row.system_id,folderId=str(row.folder_id) if row.folder_id else None,
                data=deepcopy(row.data),version=row.version,canEdit=access(row,who,True),
                permissions=row.permissions if who.role=='gm' else {})


def state(who, scene_id=None):
    rows=[project(row,who) for row in Item.objects.filter(campaign_id=who.campaign_id).order_by('name') if access(row,who)]
    used={row['folderId'] for row in rows}
    folders=list(Folder.objects.filter(campaign_id=who.campaign_id))
    # Include ancestors of visible items, without leaking unrelated private folders.
    for _ in folders:
        for f in folders:
            if str(f.pk) in used and f.parent_id:used.add(str(f.parent_id))
    return dict(types=types(who.campaign.system),items=rows,folders=[dict(id=str(f.pk),name=f.name,parentId=str(f.parent_id) if f.parent_id else None,color=f.color) for f in folders if who.role=='gm' or str(f.pk) in used],isGM=who.role=='gm')


def folder(value,who):
    if not value:return None
    row=Folder.objects.filter(pk=identifier(value),campaign_id=who.campaign_id).first()
    if row is None:raise MapError('Folder not found.')
    return row


def command(who,action,p):
    if action.startswith('folder-'):
        manage(who)
        if action=='folder-create':
            row=Folder.objects.create(campaign_id=who.campaign_id,name=title(p.get('name')),parent=folder(p.get('parentId'),who),color=color(p.get('color','#c9a44c')))
        else:
            row=folder(p.get('id'),who)
            if row is None:raise MapError('Folder not found.')
            if action=='folder-delete':row.delete();return {}
            if action!='folder-update':raise MapError('Unknown folder command.')
            parent=folder(p.get('parentId'),who);cursor=parent
            while cursor:
                if cursor.pk==row.pk:raise MapError('Folders cannot contain themselves.')
                cursor=cursor.parent
            row.name=title(p.get('name',row.name));row.parent=parent;row.color=color(p.get('color',row.color));row.save()
        return {'id':str(row.pk)}
    if action=='create':
        manage(who)
        if p.get('type') not in {t['id'] for t in types(who.campaign.system)}:
            raise MapError('Enable a system that provides item types to create items.')
        row=Item.objects.create(campaign_id=who.campaign_id,name=title(p.get('name')),type=title(p.get('type','item'),80),system_id=who.campaign.system,
            data=document(p.get('data',{})),permissions=permissions(p.get('permissions',{}),who),folder=folder(p.get('folderId'),who))
    else:
        row=get(p.get('id'),who,True);version(row,p)
        if action=='delete':manage(who);row.delete();return {}
        if action=='duplicate':
            manage(who);row.pk=None;row.name=title(p.get('name',row.name+' copy'));row.version=1
        elif action=='permissions':manage(who);row.permissions=permissions(p.get('permissions'),who);row.version+=1
        elif action=='update':
            row.name=title(p.get('name',row.name));row.data=document(p.get('data',row.data));row.version+=1
            if 'folderId' in p:manage(who);row.folder=folder(p['folderId'],who)
        else:raise MapError('Unknown item command.')
        row.save()
    return {'id':str(row.pk),'item':project(row,who)}


def public_state(campaign_id, user_id, scene_id=None):
    """Authorized extension entry point; raw membership-based helpers stay internal."""
    from gravewright.table.domain import state as read
    return read(campaign_id,user_id,'items',scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    """Use the shared transaction, permission and idempotency boundary."""
    from gravewright.table.domain import command as execute
    return execute(campaign_id,user_id,'items',action,data,request_id)
