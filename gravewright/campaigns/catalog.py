"""Available campaign systems from the host and installed module manifests.

Choosing a system identifies its documents and activates its installed browser
package when the campaign form is saved.
"""
from copy import deepcopy
import re

from gravewright.modules.models import ModuleSet, Package
from gravewright.modules.packages import compatible


NATIVE_SYSTEM_ID = 'gravewright-pdf-system'
NATIVE_RULESET = {
    'systemId': NATIVE_SYSTEM_ID,
    'title': 'Gravewright PDF System',
    'actorTypes': [{'id': 'character', 'label': 'Character'}],
}


def activate_selected_system(campaign, previous_system=None):
    """Select system code alongside document types, retaining unrelated modules."""
    from gravewright.modules.packages import host
    current = ModuleSet.objects.filter(campaign=campaign).first()
    modules = dict(current.modules) if current else {}
    replacements = dict(current.replacements) if current else {}
    if previous_system and previous_system != campaign.system:
        modules.pop(previous_system, None)
        replacements = {key: value for key, value in replacements.items() if value != previous_system}
    if campaign.system and campaign.system != NATIVE_SYSTEM_ID and campaign.system not in modules:
        descriptor = get_ruleset(campaign.system)
        if descriptor is None:
            return
        modules[campaign.system] = descriptor['version']
    if modules != (current.modules if current else {}) or replacements != (current.replacements if current else {}):
        host().configure(campaign.pk, modules, replacements, current.revision if current else '0')


def _descriptor(package):
    """Project an eligible installed release into the campaign system contract."""
    manifest = package.manifest
    system = manifest.get('system')
    if not isinstance(system, dict) or not compatible(manifest.get('sdk', {}).get('requires')):
        return None
    if package.module_id == NATIVE_SYSTEM_ID or manifest.get('id') != package.module_id:
        return None
    if manifest.get('version') != package.version or not re.fullmatch(
            r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', package.version):
        return None
    return {
        'systemId': manifest['id'],
        'title': manifest['name'],
        'version': manifest['version'],
        'actorTypes': system['actorTypes'],
        'itemTypes': system.get('itemTypes', []),
    }


def list_rulesets():
    """Read currently eligible releases, keeping the newest version of each ID.

    The native identity is reserved. No marketplace configuration or remote
    request is needed to discover packages that were already installed.
    """
    latest = {}
    for package in Package.objects.filter(revoked=False).only('module_id', 'version', 'manifest'):
        descriptor = _descriptor(package)
        if descriptor is None:
            continue
        # Releases use stable semver; integer tuples avoid treating 1.9 as newer than 1.10.
        version = tuple(map(int, package.version.split('.')))
        if package.module_id in latest and latest[package.module_id][0] >= version:
            continue
        latest[package.module_id] = (version, descriptor)
    installed = sorted((row for _, row in latest.values()), key=lambda row: (row['title'].casefold(), row['systemId']))
    return [deepcopy(NATIVE_RULESET), *installed]


def get_ruleset(system_id='', *, campaign_id=None):
    """Resolve table types from its active release, otherwise the newest installed.

    An unavailable selected release never silently falls back to another version.
    """
    if not system_id or system_id == NATIVE_SYSTEM_ID:
        return deepcopy(NATIVE_RULESET)
    if campaign_id is not None:
        modules = ModuleSet.objects.filter(campaign_id=campaign_id).values_list('modules', flat=True).first() or {}
        if system_id in modules:
            package = Package.objects.filter(
                module_id=system_id, version=modules[system_id], revoked=False,
            ).only('module_id', 'version', 'manifest').first()
            return _descriptor(package) if package else None
    return next((row for row in list_rulesets() if row['systemId'] == system_id), None)
