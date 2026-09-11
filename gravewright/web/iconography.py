from functools import lru_cache
from pathlib import Path
from markupsafe import Markup, escape


@lru_cache(maxsize=128)
def icon(name, weight='regular', css='', scope=''):
    # Only template-owned names are accepted; no filesystem paths from requests.
    if not name.isalpha() or weight not in {'regular', 'bold', 'duotone'}:
        raise ValueError('Unknown icon')
    if scope not in {'', 'data-v-gwcondition', 'data-v-gwaudio', 'data-v-gwdice', 'data-v-gwpreset', 'data-v-gwtoolbar', 'data-v-gwentry'}:
        raise ValueError('Unknown scope')
    svg = (Path(__file__).with_name('icons') / f'{name}-{weight}.svg').read_text()
    return Markup(svg.replace('<svg ', f'<svg {scope} aria-hidden="true" class="{escape(css)}" ', 1))
