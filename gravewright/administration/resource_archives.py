"""Remap canonical campaign references in their resource-specific namespaces."""

from copy import deepcopy
from uuid import uuid4

from django.apps import apps

from gravewright.table.resource_links import RESOURCE_KINDS, validate_reference


def remap_reference(reference, model_ids, inert, identifiers, *, snapshot):
    ref = deepcopy(validate_reference(reference))

    def binding(label, value, *, integer=False):
        key = (label, str(value))
        if model_ids.get(key) is not None:
            return str(model_ids[key])
        if key not in inert:
            if snapshot:
                inert[key] = str(value)
            elif integer:
                candidate = 2**63 - 1
                reserved = set(inert.values()) | {str(pk) for (model, _), pk in model_ids.items() if model == label}
                model = apps.get_model(label)
                while str(candidate) in reserved or model.objects.filter(pk=candidate).exists():
                    candidate -= 1
                inert[key] = str(candidate)
            else:
                inert[key] = str(uuid4())
        return str(inert[key])

    spec = RESOURCE_KINDS[ref['kind']]
    codec, label, value = spec['identifier'], spec['model'], ref['id']
    if codec == 'pack' and value.startswith('native:'):
        return ref
    if codec == 'pack-entry':
        pack, entry = value.split('/', 1)
        if pack.startswith('native:'):
            return ref
        ref['id'] = binding(spec['parentModel'], pack) + '/' + binding(label, entry)
    elif codec == 'scene-fragment':
        scene, drawing = value.split('/', 1)
        ref['id'] = binding('gravewright_maps.scene', scene) + '/' + identifiers.get(drawing, drawing)
    else:
        ref['id'] = binding(label, value, integer=codec == 'integer')
    # A page identifier is local to its journal, even when it resembles a UUID.
    return ref
