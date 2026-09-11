from django.conf import settings
"""Campaign-bound journal commands and role-filtered projections."""
from copy import deepcopy
import json
import re
import uuid
from django.db import transaction
from . import types
from gravewright.campaigns.models import Membership, Campaign
from .models import Journal, Folder, Access, Asset, Receipt
from . import documents, data as shapes


class JournalError(Exception):
    def __init__(self, message, code='invalid_input'):
        self.code = code
        super().__init__(message)


def identifier(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise JournalError('Invalid document identifier.') from None


def member(campaign_id, user_id):
    """Resolve current active membership, including streamer link validity."""
    found = Membership.objects.select_related('user').filter(campaign_id=campaign_id, user_id=user_id, user__is_active=True).first()
    if found is None:
        raise JournalError('You no longer have access to this table.', 'not_a_member')
    if found.role == 'streamer':
        from gravewright.campaigns.streamer import active
        if not active(user_id,campaign_id):raise JournalError('Stream expired.', 'not_a_member')
    return found


def writable(who):
    if who.role == 'streamer':raise JournalError('Streamers have read-only access.', 'forbidden')


def permissions(journal, who):
    levels = {row.user_id: row.level for row in journal.access.all()}
    gm = who.role == 'gm'
    own = levels.get(who.user_id) == 'owner'
    return gm or own or journal.visibility in {'shared','handout'} or levels.get(who.user_id) == 'read', gm or own


def get(journal_id, who, edit=False):
    journal = Journal.objects.prefetch_related('access').filter(pk=identifier(journal_id), campaign_id=who.campaign_id).first()
    if journal is None or not (permissions(journal, who)[int(edit)] or (not edit and types.via_board(journal, who))):
        raise JournalError('Document not found or access denied.', 'not_found')
    return journal


def text(value, limit, label):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise JournalError(f'{label} must contain 1 to {limit} characters.')
    return value.strip()


def folder(value, who, write=False):
    if not value:
        return None
    found = Folder.objects.filter(pk=identifier(value), campaign_id=who.campaign_id).first()
    if not found or (write and who.role != 'gm' and found.creator_id != who.user_id):
        raise JournalError('Folder not found or access denied.')
    return found


def asset_ids(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'assetId','asset_id'} and child:
                yield str(child)
            elif isinstance(child,(dict,list)):
                yield from asset_ids(child)
    elif isinstance(value,list):
        for child in value:
            yield from asset_ids(child)


def clean_data(raw, journal, who):
    """Normalize document data while preserving hidden content and asset ownership."""
    if not isinstance(raw, dict) or len(json.dumps(raw)) > 512_000:
        raise JournalError('The document is too large.')
    if not isinstance(raw.get('sections', []), list):
        raise JournalError('Invalid document pages.')
    if who.role != 'gm':
        available = set(asset_ids(projection(journal,who)))
        linked = set(asset_ids(journal.data))
        available |= {str(pk) for pk in Asset.objects.filter(journal=journal,uploader_id=who.user_id).values_list('pk',flat=True)} - linked
        if not set(asset_ids(raw)) <= available:
            raise JournalError('A file is not available to this editor.')
    try:
        clean = shapes.normalize_data_for(journal.type,raw)
    except (TypeError,ValueError,AttributeError):
        raise JournalError('Invalid document content.') from None
    if journal.type == 'diary':
        sections=clean['sections']
        if len(raw.get('sections',[])) > 64 or len({s['id'] for s in sections}) != len(sections):
            raise JournalError('Use up to 64 pages with unique identifiers.')
        # Page files, unlike links, always use authorized local journal assets.
        for section in sections:
            aid=section['assetId']
            section['src']=f'/game/journal/asset/{aid}' if aid else ''
        if who.role != 'gm':
            existing=shapes.normalize_diary_data(journal.data)
            clean['gm']=existing['gm']
            clean['content']=preserve_secrets(clean['content'],existing['content'])
            old={s['id']:s for s in existing['sections']}
            for section in sections:
                if section['id'] in old and old[section['id']]['audience']=='gm':
                    raise JournalError('Page not found or access denied.')
                section['audience']='public'
                section['content']=preserve_secrets(section['content'],old.get(section['id'],{}).get('content',{}))
            clean['sections']=sorted(sections+[s for s in existing['sections'] if s['audience']=='gm'], key=lambda s:s['sortOrder'])
            if len(clean['sections'])>64:
                raise JournalError('This journal already has 64 pages.')
    clean = types.clean_type(raw, clean, journal, who)
    requested=set(asset_ids(clean))
    allowed={str(pk) for pk in Asset.objects.filter(journal=journal).values_list('pk',flat=True)}
    if not requested <= allowed:
        raise JournalError('A file does not belong to this document.')
    return clean


def preserve_secrets(submitted, stored):
    # A player cannot create GM blocks or erase nested GM blocks they never saw.
    public=documents.filter_doc_for_role(submitted,is_gm=False)
    secrets=[]
    def walk(nodes):
        for node in nodes:
            if node.get('attrs',{}).get('visibility')=='gm':
                secrets.append(deepcopy(node))
            elif isinstance(node.get('content'),list):
                walk(node['content'])
    walk(documents.validate_document(stored)['doc']['content'])
    public['doc']['content'].extend(secrets)
    return public


def projection(journal, who):
    """Build recipient-visible content and omit GM-only fields, pages and blocks."""
    gm=who.role=='gm'
    clean=shapes.normalize_data_for(journal.type,journal.data)
    view={'id':str(journal.pk),'type':journal.type,'title':journal.title,
          'folder_id':str(journal.folder_id) if journal.folder_id else None,
          'visibility':journal.visibility,'version':journal.version,'can_edit':permissions(journal,who)[1]}
    if gm:
        view['permissions']={str(a.user_id):a.level for a in journal.access.all()}
    if journal.type=='diary':
        view['content_doc']=documents.filter_doc_for_role(clean['content'],is_gm=gm)
        view['cover_image']=clean['cover']
        view['sections']=[{**s,'content':documents.filter_doc_for_role(s['content'],is_gm=gm)} for s in clean['sections'] if gm or s['audience']=='public']
        view['editable_sections']=deepcopy(view['sections'])
        if gm: view['diary']={'gm':clean['gm']}
    view.update(types.project(journal, who, clean))
    view['listed'] = permissions(journal, who)[0]
    return view


def state(campaign_id,user_id):
    who=member(campaign_id,user_id)
    journals=[projection(j,who) for j in Journal.objects.filter(campaign_id=campaign_id).prefetch_related('access') if permissions(j,who)[0] or types.via_board(j,who)]
    folders=list(Folder.objects.filter(campaign_id=campaign_id))
    if who.role!='gm':
        visible={j['folder_id'] for j in journals}|{str(f.pk) for f in folders if f.creator_id==user_id}
        while True:
            parents={str(f.parent_id) for f in folders if str(f.pk) in visible and f.parent_id}
            if parents<=visible:break
            visible|=parents
        folders=[f for f in folders if str(f.pk) in visible]
    result={'is_gm':who.role=='gm','journals':journals,'handouts_enabled':True,'targeted_handouts_enabled':settings.TARGETED_HANDOUTS_ENABLED,
            'folders':[{'id':str(f.pk),'name':f.name,'color':f.color,'parent_id':str(f.parent_id) if f.parent_id else None} for f in folders],
            'members':[{'id':str(m.user_id),'name':m.user.name,'role':m.role} for m in Membership.objects.filter(campaign_id=campaign_id).select_related('user')] if who.role=='gm' else []}
    return result


def command(campaign_id,user_id,action,payload,request_id):
    """Authorize and serialize a journal command, then publish only after commit."""
    rid=identifier(request_id)
    if not isinstance(action,str): raise JournalError('Invalid command.')
    if not isinstance(payload,dict): raise JournalError('Invalid command.')
    with transaction.atomic():
        # One campaign lock serializes tree moves, grants and document saves.
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who=member(campaign_id,user_id)
        writable(who)
        receipt=Receipt.objects.filter(campaign_id=campaign_id,user_id=user_id,request_id=rid).first()
        if receipt:
            if receipt.result.get('message_id') and who.role != 'gm':
                raise JournalError('Only the GM can retrieve a table roll.')
            return receipt.result
        result=apply(who,action,payload)
        Receipt.objects.create(campaign_id=campaign_id,user_id=user_id,request_id=rid,result=result)
        from gravewright.realtime.dispatch import changed
        changed(campaign_id,user_id,'journals',action,rid,result)
    return result


def apply(who,action,p):
    gm=who.role=='gm'
    if action == 'present':
        from .presentations import present
        return present(who, p)
    if action=='create':
        kind = p.get('journal_type', 'diary')
        if not isinstance(kind, str) or kind not in shapes.JOURNAL_TYPES: raise JournalError('Invalid document type.')
        j=Journal.objects.create(campaign_id=who.campaign_id,creator_id=who.user_id,
            title=text(p.get('title'),120,'Title'),folder=folder(p.get('folder_id'),who,True),type=kind,data=shapes.empty_data_for(kind))
        if kind == 'quest':
            j.data['status'] = 'available'; j.save(update_fields=['data'])
        Access.objects.create(journal=j,user_id=who.user_id,level='owner')
        return {'journal_id':str(j.pk),'version':j.version}
    if action.startswith('folder-'):
        if action=='folder-create':
            f=Folder.objects.create(campaign_id=who.campaign_id,creator_id=who.user_id,parent=folder(p.get('parent_id'),who,True),name=text(p.get('name'),80,'Folder name'),color=color(p.get('color','#c09a5a')))
        else:
            f=folder(p.get('folder_id'),who,True)
            if f is None:raise JournalError('Folder not found.')
            if action=='folder-update':f.name=text(p.get('name'),80,'Folder name');f.color=color(p.get('color'))
            elif action=='folder-move':
                target=folder(p.get('target_parent_id'),who,True)
                ancestor=target
                while ancestor:
                    if ancestor.pk==f.pk:raise JournalError('A folder cannot contain itself.')
                    ancestor=ancestor.parent
                f.parent=target
            elif action=='folder-delete':
                Folder.objects.filter(parent=f).update(parent=f.parent)
                Journal.objects.filter(folder=f).update(folder=f.parent)
                f.delete();return {}
            else:raise JournalError('Unknown folder command.')
            f.save()
        return {'folder_id':str(f.pk)}
    j=get(p.get('journal_id'),who,edit=True)
    result = {}
    if action=='update':
        if type(p.get('version')) is not int or p['version']!=j.version:
            raise JournalError('This journal changed in another window. Review your draft, then try saving to replace that version.', 'conflict')
        j.title=text(p.get('title'),120,'Title')
        if gm:
            visibility=p.get('visibility',j.visibility)
            if visibility not in {'private','shared','handout'}:raise JournalError('Invalid visibility.')
            j.visibility=visibility
        j.data=clean_data(p.get('data'),j,who)
    elif action=='move':
        if not gm:raise JournalError('Only the GM can move documents.')
        j.folder=folder(p.get('target_folder_id'),who,True)
    elif action=='access':
        if not gm:raise JournalError('Only the GM can change access.')
        target=member(who.campaign_id,identifier(p.get('target_user_id')))
        level=p.get('access_level')
        if level not in {'none','read','owner'}:raise JournalError('Invalid access level.')
        Access.objects.update_or_create(journal=j,user_id=target.user_id,defaults={'level':level})
    elif action=='delete':
        if not gm:raise JournalError('Only the GM can delete documents.')
        j.delete();return {}
    else:
        result = types.apply(j, who, action, p)
    j.version+=1;j.save()
    return {'journal_id':str(j.pk),'version':j.version, **result}


def color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):
        raise JournalError('Invalid folder color.')
    return value
