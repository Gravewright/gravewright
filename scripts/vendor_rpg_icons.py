"""Import the official Game-icons transparent SVG and CoMiGo SVG archives.

Usage: python scripts/vendor_rpg_icons.py game-icons.zip comigo.zip
Only SVG assets are bundled; raster duplicates and previews are omitted.
"""
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'gravewright/web/static/gravewright_web/vendor/rpg-icons'
LIMIT = 40_000_000


def main(game_archive, comigo_archive):
    files, catalog, packs = {}, [], []
    for pack, source, prefix, archive in [
        ('game-icons', 'https://game-icons.net/', 'icons/ffffff/transparent/1x1/', game_archive),
        ('comigo', 'https://comigo.itch.io/fantasy-icons-ink', 'SVG_Black/', comigo_archive),
    ]:
        archive = Path(archive)
        count = size = 0
        with zipfile.ZipFile(archive) as zipped:
            if pack == 'game-icons':
                files['GAME-ICONS-NOTICE.txt'] = zipped.read('icons/license.txt')
            for item in zipped.infolist():
                if not item.filename.startswith(prefix) or not item.filename.endswith('.svg'):
                    continue
                relative = PurePosixPath(item.filename.removeprefix(prefix))
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Invalid archive path')
                raw = zipped.read(item)
                svg = ET.fromstring(raw)
                if svg.tag != '{http://www.w3.org/2000/svg}svg':
                    raise ValueError('Expected SVG')
                for el in svg.iter():
                    if el.tag.split('}')[-1] in {'script', 'foreignObject'}:
                        raise ValueError('Active SVG content')
                    if any(key.lower().startswith('on') for key in el.attrib):
                        raise ValueError('SVG event handler')
                path = f'{pack}/{relative.as_posix()}'
                files[path] = raw
                author = relative.parts[0] if pack == 'game-icons' else 'Cosmo Myzrail Gorynych'
                license_id = 'CC0-1.0' if pack == 'comigo' or author in {'viscious-speed', 'zeromancer'} else 'CC-BY-3.0'
                catalog.append({'id': f'{pack}/{relative.with_suffix("").as_posix()}', 'path': path,
                                'author': author, 'license': license_id,
                                'sha256': hashlib.sha256(raw).hexdigest()})
                count += 1
                size += len(raw)
        packs.append({'id': pack, 'source': source, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'count': count, 'svg_bytes': size, 'modifications': 'None; original SVG files preserved.'})
    files['catalog.json'] = (json.dumps({'packs': packs, 'icons': sorted(catalog, key=lambda v: v['id'])}, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    authors = sorted({entry['author'] for entry in catalog if entry['id'].startswith('game-icons/')})
    credits = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gravewright — RPG icon credits</title><style>body{font:16px/1.6 system-ui;max-width:760px;margin:48px auto;padding:0 20px;background:#14181d;color:#e5dfd1}a{color:#d6b578}h1,h2{line-height:1.3}</style>
<h1>RPG icon credits</h1><p>These assets retain their own licenses, independently of Gravewright's code license. Original SVG files are bundled without modification; the interface applies color and size at display time.</p>
<h2>Game-icons.net</h2><p>Icons made by the following authors. Available on <a href="https://game-icons.net/">Game-icons.net</a>.</p><p>''' + html.escape(', '.join(authors)) + '''</p>
<p><a href="GAME-ICONS-NOTICE.txt">Original author names and links</a> · <a href="https://game-icons.net/about.html#authors">Authors</a> · <a href="https://creativecommons.org/licenses/by/3.0/">CC BY 3.0</a>. Viscious Speed and Zeromancer icons are CC0 as recorded in the original notice.</p>
<h2>CoMiGo Hand-drawn Fantasy Icon Pack</h2><p>By Cosmo Myzrail Gorynych. <a href="https://comigo.itch.io/fantasy-icons-ink">Original pack</a> · <a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0 1.0</a>.</p>
<p><a href="CC-BY-3.0.txt">CC BY 3.0 legal code</a> · <a href="CC0-1.0.txt">CC0 legal code</a> · <a href="catalog.json">Asset catalog and provenance</a></p></html>'''
    files['CREDITS.html'] = credits.encode()
    # Include the already downloaded verbatim legal texts in the budget.
    legal_size = sum(p.stat().st_size for p in DEST.glob('CC*.txt')) if DEST.exists() else 0
    total = sum(map(len, files.values())) + legal_size
    if total > LIMIT:
        raise ValueError(f'Icon library exceeds {LIMIT} bytes: {total}')
    for path, raw in files.items():
        target = DEST / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    print(json.dumps({'packs': packs, 'total_bytes': total}, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
