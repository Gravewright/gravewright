"""Bounded document fingerprints and display-page geometry for mapping diagnostics."""
from copy import deepcopy
from math import isfinite

from gravewright.maps.services import MapError
from .field_actions import _source


def normalize_source_metadata(pdf, previous=None, *, gm=True):
    old = (previous or {}).get('pdf', {}).get('sourceMetadata')
    if 'sourceMetadata' not in pdf:
        if old is not None:
            pdf['sourceMetadata'] = deepcopy(old)
        return
    records = pdf['sourceMetadata']
    if not isinstance(records, list) or len(records) > 64:
        raise MapError('Invalid PDF document metadata.')
    seen = set()
    clean = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {'source', 'pageCount', 'pages', 'fingerprint'}:
            raise MapError('Invalid PDF document metadata.')
        source = _source(record['source'])
        if source in seen or type(record['pageCount']) is not int or not 1 <= record['pageCount'] <= 100000:
            raise MapError('Invalid PDF document metadata.')
        seen.add(source)
        if not isinstance(record['fingerprint'], str) or len(record['fingerprint']) > 128:
            raise MapError('Invalid PDF document metadata.')
        pages = record['pages']
        if not isinstance(pages, list) or len(pages) > 1024:
            raise MapError('Invalid PDF document metadata.')
        page_ids = set()
        for page in pages:
            if not isinstance(page, dict) or set(page) != {'page', 'width', 'height', 'rotation'}:
                raise MapError('Invalid PDF document metadata.')
            if type(page['page']) is not int or not 1 <= page['page'] <= record['pageCount'] or page['page'] in page_ids:
                raise MapError('Invalid PDF document metadata.')
            page_ids.add(page['page'])
            if type(page['rotation']) is not int or page['rotation'] not in {0, 90, 180, 270}:
                raise MapError('Invalid PDF document metadata.')
            if any(type(page[key]) not in (int, float) or not isfinite(page[key]) or not 0 < page[key] <= 32768 for key in ('width', 'height')):
                raise MapError('Invalid PDF document metadata.')
        clean.append({**deepcopy(record), 'source': source})
    if not gm and clean != (old or []):
        raise MapError('Only the GM can update PDF document metadata.', 'forbidden')
    pdf['sourceMetadata'] = clean
