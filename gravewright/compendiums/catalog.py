"""Read native data/compendiums collections; never execute package code."""
import json
import uuid
from pathlib import Path
from django.conf import settings
from gravewright.table.domain import MapError, manage, title, document, number
from .models import ContentAccess

KINDS = {'actor_pack':'actor', 'item_pack':'item', 'spell_pack':'item',
         'journal_pack':'journal', 'scene_pack':'scene', 'card_pack':'deck', 'deck_pack':'deck'}


def available(who):
    root = Path(getattr(settings, 'GRAVEWRIGHT_CONTENT_ROOT', settings.BASE_DIR / 'data' / 'vtt' / 'compendiums')).resolve()
    for index in sorted(root.glob('*/index.json')):
        if not index.resolve().is_relative_to(root) or index.stat().st_size > 8 * 1024 * 1024:
            continue
        try:
            collection = json.loads(index.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(collection,dict) or not isinstance(collection.get('campaigns'),list) or str(who.campaign_id) not in collection['campaigns'] or not isinstance(collection.get('packs'),list):
            continue
        for pack in collection.get('packs',[]):
            if not isinstance(pack,dict) or pack.get('type') not in KINDS or not isinstance(pack.get('entries'),list):
                continue
            # Native collections are private unless the host explicitly grants reading.
            if who.role != 'gm' and not ContentAccess.objects.filter(campaign_id=who.campaign_id,collection=index.parent.name,pack=str(pack.get('id')),role=who.role,level__in=['read','owner']).exists():
                continue
            rid='native:'+str(uuid.uuid5(uuid.NAMESPACE_URL, index.parent.name+'/'+str(pack.get('id'))))
            yield rid,index.parent,collection,pack


def summaries(who):
    return [dict(id=rid,name=f"{collection.get('name',base.name)} / {pack.get('label',pack.get('name',pack.get('id')))}",
                 shared=who.role!='gm',locked=True,version=1,systemId=who.campaign.system,
                 entries=[dict(id=str(e.get('id')),name=str(e.get('name',e.get('title','Imported'))),kind=KINDS[pack['type']],version=1)
                          for e in pack.get('entries',[]) if isinstance(e,dict)])
            for rid,base,collection,pack in available(who)]


def command(who, action, payload):
    record=next((r for r in available(who) if r[0]==payload.get('packId')),None)
    if record is None:
        raise MapError('Compendium not found.','not_found')
    _,base,collection,pack=record
    if action=='permissions':
        manage(who)
        level=payload.get('level')
        if level not in ('none','read','owner'):raise MapError('Invalid permissions.')
        ContentAccess.objects.update_or_create(campaign_id=who.campaign_id,collection=base.name,pack=str(pack.get('id')),role='player',defaults={'level':level})
        return {}
    entry=next((e for e in pack.get('entries',[]) if isinstance(e,dict) and str(e.get('id'))==str(payload.get('id'))),None)
    if entry is None:
        raise MapError('Entry not found.','not_found')
    if action=='read':
        return document(entry)
    manage(who)
    if action!='import':
        raise MapError('Native compendiums are read only.')
    system=entry.get('systemId',entry.get('system_id',who.campaign.system))
    if system!=who.campaign.system:
        raise MapError('This compendium requires a different system.')
    kind=KINDS[pack['type']]
    name=title(entry.get('name',entry.get('title','Imported')))
    data=document(entry.get('data',{}))
    import_folder=data.pop('importFolder',None)
    if kind=='actor':
        from gravewright.actors.models import Actor
        from gravewright.actors.services import command as actor_command
        if entry.get('type','character')!='character':raise MapError('Unknown actor type.')
        created=actor_command(who.campaign_id,who.user_id,'actor.create',{'name':name,'data':data},uuid.uuid4())
        result=Actor.objects.get(pk=created['id'])
    elif kind=='item':
        from gravewright.items.services import command as create_item
        return {**create_item(who,'create',{'name':name,'type':entry.get('type'),'data':data}),'kind':'item'}
    elif kind=='journal':
        from gravewright.journals import services, data as shapes
        from gravewright.journals.models import Journal
        journal_type=entry.get('type','diary')
        if journal_type not in shapes.JOURNAL_TYPES:journal_type='diary'
        result_id=services.apply(who,'create',{'title':name,'journal_type':journal_type})['journal_id']
        result=Journal.objects.get(pk=result_id)
        if data:result.data=services.clean_data(data,result,who)
        content=entry.get('content_markdown',entry.get('content'))
        if content and journal_type=='diary' and not result.data.get('sections'):
            result.data=services.clean_data({'sections':[{'id':str(uuid.uuid4()),'title':name,'kind':'text','content':{'format':'gw-journal-doc-v1','version':1,'doc':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':str(content)}]}]}}}]},result,who)
        result.save()
    elif kind=='scene':
        from gravewright.maps.models import Scene
        width=number(data.get('width',2048),1,500000);height=number(data.get('height',2048),1,500000)
        if type(width) is not int or type(height) is not int:raise MapError('Invalid scene dimensions.')
        result=Scene.objects.create(campaign_id=who.campaign_id,name=name,width=width,height=height)
    else:
        return import_deck(who,base,name,data or entry)
    if kind in ('actor','journal'):
        if kind=='actor':
            from gravewright.actors.models import Folder
        else:
            from gravewright.journals.models import Folder
        parent=None
        labels=[collection.get('name',base.name),pack.get('label',pack.get('name',pack.get('id')))]
        if import_folder:labels.append(import_folder)
        for label in labels:
            parent,_=Folder.objects.get_or_create(campaign_id=who.campaign_id,parent=parent,name=title(str(label))[:60])
        result.folder=parent;result.save(update_fields=['folder'])
    return {'id':str(result.pk),'kind':kind}


def import_deck(who,base,name,data):
    from django.core.files.base import ContentFile
    from gravewright.cards.models import CardAsset
    from gravewright.cards.services import command as cards
    from PIL import Image
    import io
    rows=data.get('cards',[])
    if not isinstance(rows,list) or not 1<=len(rows)<=500:raise MapError('Invalid deck.')
    prepared=[]
    for row in rows:
        if not isinstance(row,dict):raise MapError('Invalid card.')
        relative=row.get('artwork',row.get('front',''))
        if not isinstance(relative,str):raise MapError('Invalid artwork.')
        path=(base/relative).resolve()
        if not path.is_relative_to(base.resolve()) or not path.is_file() or path.suffix.lower()!='.webp' or path.stat().st_size>10*1024*1024:
            raise MapError('Invalid card artwork.')
        raw=path.read_bytes()
        try:
            with Image.open(io.BytesIO(raw)) as image:image.verify()
        except (OSError,ValueError):raise MapError('Invalid card artwork.') from None
        quantity=row.get('quantity',1)
        if type(quantity) is not int or not 1<=quantity<=500 or len(prepared)+quantity>500:raise MapError('Invalid card quantity.')
        prepared.extend([(title(row.get('name',row.get('label','Card'))),raw)]*quantity)
    files=[]
    try:
        entries=[]
        for card_name,raw in prepared:
            asset=CardAsset(campaign_id=who.campaign_id,uploader_id=who.user_id,purpose='front')
            asset.file.save(uuid.uuid4().hex+'.webp',ContentFile(raw));files.append(asset.file)
            entries.append({'name':card_name,'front_asset_id':str(asset.pk)})
        definition=cards(who,'define',{'name':name,'cards':entries})
        return {**cards(who,'instantiate',{'deck_definition_id':definition['deck']['id']}),'kind':'deck'}
    except Exception:
        for file in files:file.delete(save=False)
        raise
