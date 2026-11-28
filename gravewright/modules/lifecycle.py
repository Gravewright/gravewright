"""Replace or remove installed releases while preserving module storage."""
import shutil
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from gravewright.campaigns.models import Campaign
from gravewright.campaigns.systems import default_system_id
from .models import ContextLease, ModuleSet, Package
from .packages import ModuleFailure, package_type, release


def usage(engine, row):
    from config.marketplace_apps import selections
    global_use = row.global_enabled or ('django' in row.manifest and
        selections(engine.directory).get(row.module_id, {}).get('version') == row.version)
    last_system = ('system' in row.manifest and not Package.objects.filter(
        module_id=row.module_id, revoked=False).exclude(pk=row.pk).exists())
    selections = {item.campaign_id: item.modules for item in ModuleSet.objects.all()}
    return [{'id': str(campaign.pk), 'name': campaign.name}
            for campaign in Campaign.objects.order_by('name', 'pk')
            if global_use or selections.get(campaign.pk, {}).get(row.module_id) == row.version
            or (last_system and campaign.system == row.module_id)]


def check_replacement(module_id, version, kind):
    """Reject a release that cannot become the only installed release of its package.

    An installation keeps one release per package ID: installing another
    version replaces the installed one, as an update does. An older version
    never replaces a newer usable one, and a package ID keeps its type.
    """
    for row in Package.objects.filter(module_id=module_id).exclude(version=version):
        if package_type(row.manifest) != kind:
            raise ModuleFailure('package_type_changed', f'This ID is installed as a {package_type(row.manifest)} package.')
        if not row.revoked and release(row.version) > release(version):
            raise ModuleFailure('newer_installed', f'Version {row.version} is installed. Remove it before installing {version}.')


def supersede(engine, replacement, active):
    """Replace every other release of ``replacement``'s package with it.

    Caller holds an atomic transaction. Tables move to the replacement and
    module storage is kept, exactly as for an update. A revoked release stays
    recorded so its bytes cannot be installed again. ``active(engine, row)``
    tells whether a Django release runs on this server; switching it requires
    a supervised restart, which this returns as an activation result.
    """
    result = {'replaced': []}
    rows = (Package.objects.select_for_update().filter(module_id=replacement.module_id)
            .exclude(pk=replacement.pk).order_by('pk'))
    for row in rows:
        if (package_type(row.manifest) != package_type(replacement.manifest)
                or bool(row.locale_catalogs) != bool(replacement.locale_catalogs)):
            raise ModuleFailure('package_type_changed')
        if row.revoked:
            continue
        if release(row.version) > release(replacement.version):
            raise ModuleFailure('newer_installed')
        if active(engine, row):
            from .server_apps import queue_activation
            result.update(queue_activation(replacement, True))
        else:
            replace_release(engine, row, replacement)
        result['replaced'].append(row.version)
    return result


def broadcast(engine, table_id):
    async_to_sync(get_channel_layer().group_send)(
        f'table.{table_id.hex}', {'type': 'room.modules', 'state': engine.state(table_id)}
    )


def replace_release(engine, row, replacement=None):
    """Caller holds an atomic transaction; old files are quarantined until commit."""
    root = engine.directory.resolve()
    targets = [root / 'packages' / row.module_id / row.version / row.digest]
    if not Package.objects.filter(digest=row.digest).exclude(pk=row.pk).exists():
        targets.append(root / 'archives' / (row.digest + '.zip'))
    for path in targets:
        if (not path.resolve().is_relative_to(root) or path.resolve() == root
                or any(part.is_symlink() for part in (path, *path.parents) if part != root)):
            raise ModuleFailure('permission_denied')

    moved = []
    try:
        for path in targets:
            if path.exists():
                quarantine = path.with_name('.removed-' + uuid.uuid4().hex)
                path.rename(quarantine)
                moved.append((path, quarantine))
        # Match configure's campaign lock order before changing table selections.
        for campaign in Campaign.objects.select_for_update().order_by('pk'):
            transaction.on_commit(lambda table_id=campaign.pk: broadcast(engine, table_id), robust=True)
            reset_system = (replacement is None and 'system' in row.manifest
                            and campaign.system == row.module_id
                            and not Package.objects.filter(module_id=row.module_id, revoked=False)
                            .exclude(pk=row.pk).exists())
            if reset_system:
                campaign.system = default_system_id()
                campaign.save(update_fields=['system'])
            selected = ModuleSet.objects.select_for_update().filter(campaign=campaign).first()
            if not selected:
                if not reset_system:
                    continue
                selected = ModuleSet.objects.create(campaign=campaign)
            if selected.modules.get(row.module_id) != row.version and not reset_system:
                continue
            if replacement:
                selected.modules[row.module_id] = replacement.version
            else:
                selected.modules.pop(row.module_id, None)
                selected.replacements = {key: value for key, value in selected.replacements.items()
                                         if value != row.module_id}
            selected.revision = uuid.uuid4().hex
            selected.save()
            ContextLease.objects.filter(campaign=campaign, module_id=row.module_id).update(closed=True)
        if replacement and row.global_enabled:
            replacement.global_enabled = True
            replacement.save(update_fields=['global_enabled'])
        row.delete()
    except BaseException:
        for path, quarantine in reversed(moved):
            quarantine.rename(path)
        raise

    def clean():
        for _, path in moved:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
    transaction.on_commit(clean, robust=True)
