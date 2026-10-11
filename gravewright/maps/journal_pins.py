"""Persistent journal locations, projected through document and page ownership."""
from .models import SceneObject
from .services import MapError, manage
from .objects import number, boolean, get_object, entry
from gravewright.journals import services as journals


def target(data, who):
    journal = journals.get(data.get('journalId'), who)
    view = journals.projection(journal, who)
    page_id = data.get('pageId') or ''
    if not isinstance(page_id, str) or len(page_id) > 120:
        raise MapError('Invalid journal page.')
    page = next((p for p in view.get('sections', []) if p['id'] == page_id), None)
    if page_id and page is None:
        raise MapError('Page not found or access denied.', 'not_found')
    return journal, page


def visible(rows, who):
    result, views = [], {}
    for pin in rows:
        if who.role != 'gm' and not pin.get('public'):
            continue
        journal_id = pin.get('journalId')
        if journal_id not in views:
            try:
                journal = journals.get(journal_id, who)
                views[journal_id] = journals.projection(journal, who)
            except journals.JournalError:
                views[journal_id] = None
        view = views[journal_id]
        if view is None:
            continue
        page_id = pin.get('pageId')
        page = next((p for p in view.get('sections', []) if p['id'] == page_id), None)
        if page_id and page is None:
            continue
        result.append({**pin, 'label': page['title'] if page else view['title']})
    return result


def apply(scene, who, env, action, data):
    manage(who)
    if action not in {'create', 'update', 'delete'}:
        raise MapError('Unknown journal marker command.')
    obj = None if action == 'create' else get_object(scene, data.get('id'), 'journalPins')
    if obj and data.get('version') != obj.version:
        raise MapError('This marker changed. Reopen it and try again.', 'conflict')
    if action == 'delete':
        obj.delete()
        result = {}
    else:
        if not obj and scene.elements.count() >= 5000:
            raise MapError('Scene object limit reached.')
        merged = {**(obj.data if obj else {}), **data}
        journal, page = target(merged, who)
        clean = {'journalId': str(journal.pk), 'pageId': page['id'] if page else '',
                 'x': number(merged.get('x')), 'y': number(merged.get('y')),
                 'public': boolean(merged.get('public', False))}
        if obj:
            obj.data = clean
            obj.version += 1
            obj.save()
        else:
            obj = SceneObject.objects.create(scene=scene, kind='journalPins', data=clean)
        result = {'journalPin': entry(obj)}
    env.version += 1
    env.save()
    return result
