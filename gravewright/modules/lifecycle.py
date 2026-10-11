"""Replace or remove installed releases while preserving module storage."""
import shutil
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from gravewright.campaigns.models import Campaign
from .models import ContextLease, ModuleSet, Package
from .packages import ModuleFailure


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
                campaign.system = 'gravewright-pdf-system'
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
