"""Select one native document and the dependencies needed to import it."""
from django.apps import apps
import re
from .assets import identifiers

CHILDREN = {
    'gravewright_maps.scene': {'gravewright_maps.tile','gravewright_maps.scenestate','gravewright_maps.sceneobject','gravewright_tokens.token'},
    'gravewright_actors.actor': {'gravewright_actors.asset'},
    'gravewright_journals.journal': {'gravewright_journals.asset','gravewright_journals.boardentry'},
    'gravewright_cards.deck': {'gravewright_cards.card'},
}


def select(rows, root):
    by_key = {(r['model'],str(r['pk'])):r for r in rows}
    by_id = {str(r['pk']):key for key,r in by_key.items() if not apps.get_model(r['model'])._meta.pk.is_relation}
    selected = set()
    pending = [root]
    while pending:
        key = pending.pop()
        if key in selected or key not in by_key:
            continue
        selected.add(key)
        row = by_key[key]
        model = apps.get_model(row['model'])
        for field in model._meta.fields:
            if not field.is_relation or field.related_model._meta.label_lower in {'gravewright_accounts.user','gravewright_campaigns.campaign'}:
                continue
            value = row['pk'] if field.primary_key else row['fields'].get(field.name)
            if value is not None:
                pending.append((field.related_model._meta.label_lower,str(value)))
        references=identifiers(row['fields'])
        references|={match for value in list(references) for match in re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',value)}
        for value in references:
            if value in by_id and not by_id[value][0].startswith('gravewright_compendiums.'):
                pending.append(by_id[value])
        for child_key, child in by_key.items():
            if child['model'] not in CHILDREN.get(row['model'],set()):
                continue
            child_model = apps.get_model(child['model'])
            for field in child_model._meta.fields:
                if field.is_relation and field.related_model is model:
                    value = child['pk'] if field.primary_key else child['fields'].get(field.name)
                    # Quest links are owned by their board, not by each referenced quest.
                    if child['model']=='gravewright_journals.boardentry' and field.name!='board':
                        continue
                    if str(value)==key[1]:pending.append(child_key)
    return [row for key,row in by_key.items() if key in selected]
