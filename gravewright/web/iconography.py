from functools import lru_cache
from pathlib import Path
from markupsafe import Markup, escape


def rpg_icon(name):
    """Template-owned RPG symbols; general interface controls keep their icons."""
    from gravewright.web.assets import static
    paths = {'scenes': 'comigo/Map.svg', 'actors': 'comigo/Human.svg',
             'journals': 'comigo/Book_Open.svg', 'items': 'comigo/Backpack.svg',
             'combat': 'game-icons/lorc/crossed-swords.svg'}
    path = static('gravewright_web/vendor/rpg-icons/' + paths[name])
    return Markup('<span class="rpg-icon" aria-hidden="true" style="--rpg-icon:url(\'{}\')"></span>').format(escape(path))


@lru_cache(maxsize=128)
def icon(name, weight='regular', css='', scope=''):
    # Only template-owned names are accepted; no filesystem paths from requests.
    if not name.isalpha() or weight not in {'regular', 'bold', 'duotone'}:
        raise ValueError('Unknown icon')
    if scope not in {'', 'data-v-gwcondition', 'data-v-gwaudio', 'data-v-gwdice', 'data-v-gwpreset', 'data-v-gwtoolbar', 'data-v-gwentry'}:
        raise ValueError('Unknown scope')
    svg = (Path(__file__).with_name('icons') / f'{name}-{weight}.svg').read_text()
    return Markup(svg.replace('<svg ', f'<svg {scope} aria-hidden="true" class="{escape(css)}" ', 1))
