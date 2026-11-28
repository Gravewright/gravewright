"""Read installed package and legacy native collections; never execute package code."""
import json
import logging
import uuid
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from django.conf import settings
from gravewright.table.domain import MapError, manage, title, document, number
from .models import ContentAccess

logger = logging.getLogger(__name__)

# By default, players observe item and spell reference
# packs until the GM hides them. Actor, journal, scene and card packs can hold
# adventure spoilers, so they stay hidden until the GM shares them.
PLAYER_VISIBLE_PACKS = {'item_pack', 'spell_pack'}


def native_defaults(pack_type):
    """Role levels used when the GM has not configured a native pack."""
    return {'player': 'read'} if pack_type in PLAYER_VISIBLE_PACKS else {}


def native_level(who, collection, pack):
    """A role's configured ContentAccess level, or the pack's default."""
    row = ContentAccess.objects.filter(campaign_id=who.campaign_id, collection=collection, pack=str(pack.get('id')), role=who.role).first()
    return row.level if row else native_defaults(pack.get('type')).get(who.role, 'none')


KINDS = {'actor_pack':'actor', 'item_pack':'item', 'spell_pack':'item',
         'journal_pack':'journal', 'scene_pack':'scene', 'card_pack':'deck', 'deck_pack':'deck'}

# Cache only validated, immutable content. Selection, revocation, trust, file
# integrity and read grants are deliberately checked again by every request.
_COLLECTION_CACHE_LIMIT = 8
_COLLECTION_CACHE_BYTES = 16 * 1024 * 1024
_collection_cache = OrderedDict()
_collection_cache_lock = RLock()


def _cached_collection(key):
    with _collection_cache_lock:
        cached = _collection_cache.get(key)
        if cached is not None:
            _collection_cache.move_to_end(key)
        return cached


def _cache_collection(key, value, size):
    with _collection_cache_lock:
        _collection_cache[key] = (value, size)
        _collection_cache.move_to_end(key)
        while (len(_collection_cache) > _COLLECTION_CACHE_LIMIT
               or sum(entry[1] for entry in _collection_cache.values()) > _COLLECTION_CACHE_BYTES):
            _collection_cache.popitem(last=False)


def _pack_id(base, collection, pack):
    seed = ('module/' + collection['_module_id'] + '/' + collection['_module_path'] + '/' + str(pack.get('id'))
            if '_module_id' in collection else base.name + '/' + str(pack.get('id')))
    return 'native:' + str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def collection_key(base, collection):
    return collection.get('_module_key', base.name)


def _types(definition):
    return (frozenset(row['id'] for row in definition.get('actorTypes', [])),
            frozenset(row['id'] for row in definition.get('itemTypes', [])))


def _release(package):
    """Whether an installed row still describes one coherent, compatible release."""
    from gravewright.modules.packages import compatible
    manifest = package.manifest
    return (isinstance(package.record, dict) and isinstance(manifest, dict)
            and manifest.get('id') == package.module_id and manifest.get('version') == package.version
            and compatible(manifest.get('sdk', {}).get('requires')))


def _system(campaign, selected, packages, versions=None):
    """``(system_id, actor_types, item_types, package)`` of the table's active system.

    An installed system counts only through its exact, selected, non-revoked
    release, and ``versions`` constrains that release. A built-in system has no
    package release (``package`` is None), so it never satisfies a version range.
    """
    from gravewright.campaigns.systems import bundled, resolve_system_id
    from gravewright.modules.packages import release, satisfies
    system_id = resolve_system_id(campaign.system)
    provider = bundled(system_id)
    if provider is not None:
        return None if versions is not None else (system_id, *_types(provider['descriptor']), None)
    package = packages.get((system_id, selected.get(system_id)))
    if package is None or not _release(package) or not isinstance(package.manifest.get('system'), dict):
        return None
    current = release(package.version)
    if versions is not None and (current is None or not satisfies(current, versions)):
        return None
    return (system_id, *_types(package.manifest['system']), package)


def _selected_packages(selected):
    from gravewright.modules.models import Package
    rows = Package.objects.filter(module_id__in=list(selected), revoked=False)
    return {(row.module_id, row.version): row for row in rows if selected.get(row.module_id) == row.version}


def system_types(campaign, modules, versions=None):
    """The active system and types a compendium module would use with ``modules``."""
    if not isinstance(modules, dict):
        return None
    return _system(campaign, modules, _selected_packages(modules), versions)


# A broken release is reported once per reason rather than on every directory read.
_reported = set()


def _report(package, reason):
    key = (package.module_id, package.version, package.digest, reason)
    if key in _reported:
        return
    if len(_reported) >= 256:
        _reported.clear()
    _reported.add(key)
    logger.warning('Compendiums from %s %s are unavailable: %s', package.module_id, package.version, reason)


def _sources(campaign, selected):
    """Packages whose collections a table reads, with each one's document provider.

    The table's system package comes first, then each selected compendium
    module, which uses the active system's actual types or, without a
    required system, supplies only journal packs.
    """
    from gravewright.modules.packages import compendium_module
    from .content import requirement
    packages = _selected_packages(selected)
    system = _system(campaign, selected, packages)
    if system is not None and system[3] is not None and 'content' in system[3].manifest:
        yield system[3], system[0], system[1], system[2]
    for _, package in sorted(packages.items()):
        if not compendium_module(package.manifest) or not _release(package):
            continue
        required = requirement(package.manifest)
        if required is None:
            yield package, None, frozenset(), frozenset()
            continue
        provider = _system(campaign, selected, packages, required[1])
        if provider is None or provider[0] != required[0]:
            _report(package, 'the table does not use the required system ' + required[0]
                    + (' ' + required[1] if required[1] else ''))
            continue
        yield package, required[0], provider[1], provider[2]


def _package_collections(manager, package, provider, actor_types, item_types, pack_id):
    from gravewright.modules.packages import ModuleFailure, safe_path
    from .content import MAX_COLLECTION_BYTES, validate_collection
    paths = package.manifest.get('content', {}).get('compendiums', [])
    if not isinstance(paths, list) or not 1 <= len(paths) <= 16:
        return
    try:
        base = manager.directory / 'packages' / str(safe_path(package.module_id)) / str(safe_path(package.version)) / str(safe_path(package.digest))
        for relative in paths:
            key = (str(base.resolve()), package.digest, package.record.get('sha256'), relative,
                   provider, tuple(sorted(actor_types)), tuple(sorted(item_types)))
            cached = _cached_collection(key)
            if pack_id is not None and cached is not None and pack_id not in cached[0]['_pack_ids']:
                continue
            path = base / str(safe_path(relative))
            if (path.suffix != '.json' or not path.resolve().is_relative_to(base.resolve())
                    or not path.is_file() or path.stat().st_size > MAX_COLLECTION_BYTES):
                _report(package, 'invalid compendium path or size: ' + relative)
                continue
            raw = manager.verify_installed(package, str(safe_path(relative)))
            if cached is None:
                value = json.loads(raw)
                validate_collection(value, provider, actor_types, item_types)
                value['_module_key'] = 'module:' + str(uuid.uuid5(uuid.NAMESPACE_URL, package.module_id + '/' + relative))
                value['_module_id'] = package.module_id
                value['_module_path'] = relative
                value['_pack_ids'] = {_pack_id(base, value, pack) for pack in value['packs']}
                _cache_collection(key, value, len(raw))
            else:
                value = cached[0]
            yield base, value
    except (ModuleFailure, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        # Unavailable or changed approved content never falls back to another
        # release, directory or an arbitrary path provided by a browser client.
        # Other packages remain available.
        _report(package, getattr(error, 'message', None) or str(error) or type(error).__name__)
        return


def module_collections(who, pack_id=None):
    """Expose exact, approved package collections only in tables where they are active.

    Assets are checked against their approved archive on every read. Stable IDs
    exclude the release digest so an update retains existing read grants.
    """
    from gravewright.modules.models import ModuleSet
    from gravewright.modules.packages import host
    selected = ModuleSet.objects.filter(campaign_id=who.campaign_id).values_list('modules', flat=True).first() or {}
    if not isinstance(selected, dict) or not selected:
        return
    manager = None
    for package, provider, actor_types, item_types in _sources(who.campaign, selected):
        manager = manager or host()
        yield from _package_collections(manager, package, provider, actor_types, item_types, pack_id)


def native_collections(who):
    root = Path(getattr(settings, 'GRAVEWRIGHT_CONTENT_ROOT', settings.BASE_DIR / 'data' / 'vtt' / 'compendiums')).resolve()
    for index in sorted(root.glob('*/index.json')):
        if not index.resolve().is_relative_to(root) or index.stat().st_size > 8 * 1024 * 1024:
            continue
        try:
            collection = json.loads(index.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(collection,dict) or not isinstance(collection.get('campaigns'),list) or str(who.campaign_id) not in collection['campaigns'] or not isinstance(collection.get('packs'),list):
            continue
        collection.pop('_module_key', None)
        collection.pop('_module_id', None)
        collection.pop('_module_path', None)
        collection.pop('_pack_ids', None)
        yield index.parent, collection


def available(who, pack_id=None):
    from itertools import chain
    for base, collection in chain(native_collections(who), module_collections(who, pack_id)):
        for pack in collection.get('packs',[]):
            if not isinstance(pack,dict) or pack.get('type') not in KINDS or not isinstance(pack.get('entries'),list):
                continue
            rid = _pack_id(base, collection, pack)
            if pack_id is not None and rid != pack_id:
                continue
            # New role defaults preserve legacy grants until explicitly configured.
            if who.role != 'gm':
                from gravewright.table.ownership import policy
                explicit = policy(who, 'compendiums', rid)
                level = explicit.get(who.role, explicit.get('default', 'none')) if explicit is not None else native_level(who, collection_key(base, collection), pack)
                allowed = level in {'read', 'owner'}
                if not allowed:
                    continue
            yield rid,base,collection,pack


def _folder(collection):
    """Installed collections were validated on install; legacy roots were not."""
    from .content import folder_path
    try:
        return folder_path(collection)
    except ValueError:
        return []


def folder_id(path):
    """Opaque, URL-safe key for one directory folder, shared by every collection on that path."""
    return 'native-folder:' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'compendium-folder/' + json.dumps(path, ensure_ascii=False)))


def folder_packs(who, key):
    """The folder path for ``key`` and the available packs beneath it, subfolders included."""
    path, rows = None, []
    for record in available(who):
        folder = _folder(record[2])
        for size in range(1, len(folder) + 1):
            if folder_id(folder[:size]) == key:
                path = folder[:size]
                rows.append(record)
                break
    return path, rows


def summaries(who):
    rows=[]
    for rid,base,collection,pack in available(who):
        label=str(pack.get('label',pack.get('name',pack.get('id'))))
        row=dict(id=rid,name=f"{collection.get('name',base.name)} / {label}",
                 shared=who.role!='gm',locked=True,version=1,systemId=who.campaign.system,
                 entries=[dict(id=str(e.get('id')),name=str(e.get('name',e.get('title','Imported'))),kind=KINDS[pack['type']],type=str(e.get('type','')),version=1)
                          for e in pack.get('entries',[]) if isinstance(e,dict)])
        folder=_folder(collection)
        if folder:
            # The folder path names the collection, so the directory shows the label alone.
            # folderIds address each enclosing folder for GM permissions.
            row.update(folder=folder,folderIds=[folder_id(folder[:size]) for size in range(1,len(folder)+1)],label=label)
        rows.append(row)
    return rows


def read_ids(payload):
    """Validate an explicit, bounded batch without changing single-entry reads."""
    from .content import IDENTIFIER
    ids = payload.get('ids')
    if ('id' in payload or not isinstance(ids, list) or not 1 <= len(ids) <= 100
            or any(not isinstance(value, str) or not IDENTIFIER.fullmatch(value) for value in ids)
            or len(set(ids)) != len(ids)):
        raise MapError('Invalid compendium entry IDs.', 'invalid_data')
    return ids


def prepare_import(who, payload):
    """Validate native deck artwork before reserving the campaign writer."""
    manage(who)
    requested = payload.get('packId')
    record = next((row for row in available(who, requested) if row[0] == requested), None)
    if record is None:
        raise MapError('Compendium not found.', 'not_found')
    _, base, collection, pack = record
    entry = next((row for row in pack.get('entries', [])
                  if isinstance(row, dict) and str(row.get('id')) == str(payload.get('id'))), None)
    if entry is None:
        raise MapError('Entry not found.', 'not_found')
    from copy import deepcopy
    prepared = {'native': (str(base), pack['type'], deepcopy(entry))}
    if KINDS[pack['type']] == 'deck':
        data = document(entry.get('data', {}))
        data.pop('importFolder', None)
        prepared['cards'] = prepare_deck(base, data or entry)
    return prepared


def command(who, action, payload, *, prepared=None):
    requested_pack = payload.get('packId')
    record=next((record for record in available(who, requested_pack) if record[0] == requested_pack),None)
    if record is None:
        raise MapError('Compendium not found.','not_found')
    _,base,collection,pack=record
    if action=='permissions':
        manage(who)
        level=payload.get('level')
        if level not in ('none','read','owner'):raise MapError('Invalid permissions.')
        ContentAccess.objects.update_or_create(campaign_id=who.campaign_id,collection=collection_key(base,collection),pack=str(pack.get('id')),role='player',defaults={'level':level})
        from gravewright.table.models import DocumentAccess
        explicit=DocumentAccess.objects.filter(campaign_id=who.campaign_id,kind='compendiums',resource_id=payload['packId']).first()
        if explicit:
            explicit.grants['player']='read' if level in {'read','owner'} else 'none'
            explicit.version+=1;explicit.save(update_fields=['grants','version'])
            who._ownership_cache={}
        return {}
    if action == 'read' and 'ids' in payload:
        ids = read_ids(payload)
        indexed = {str(entry.get('id')): entry for entry in pack.get('entries', []) if isinstance(entry, dict)}
        if any(value not in indexed for value in ids):
            raise MapError('Entry not found.', 'not_found')
        return {'entries': [document(indexed[value]) for value in ids]}
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
    if prepared is not None and prepared.get('native') != (str(base), pack['type'], entry):
        raise MapError('This resource changed. Refresh before editing.', 'conflict')
    kind=KINDS[pack['type']]
    name=title(entry.get('name',entry.get('title','Imported')))
    data=document(entry.get('data',{}))
    import_folder=data.pop('importFolder',None)
    if kind=='actor':
        from gravewright.actors.models import Actor
        from gravewright.actors.services import command as actor_command
        created=actor_command(who.campaign_id,who.user_id,'actor.create',{'name':name,'type':entry.get('type'),'data':data},uuid.uuid4())
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
        return import_deck(who,base,name,data or entry, prepared=prepared.get('cards') if prepared else None)
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


def prepare_deck(base, data):
    """Return bounded, verified artwork bytes without writing any database rows."""
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
    return prepared


def import_deck(who,base,name,data, *, prepared=None):
    from django.core.files.base import ContentFile
    from gravewright.cards.models import CardAsset
    from gravewright.cards.services import command as cards
    prepared = prepare_deck(base, data) if prepared is None else prepared
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
