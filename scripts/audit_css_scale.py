"""Audit or migrate first-party CSS dimensions to the shared Fibonacci scale.

Run without arguments to check; use --fix to replace exact pixel lengths and
add missing Fibonacci composites. Breakpoints, strings, URLs, vendor CSS and
the scale's own definitions remain untouched. Physical geometry is preserved.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / 'gravewright/web/static/gravewright_web/css/tokens.css'
FIB = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
LEX = re.compile(r'''(?P<skip>/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|url\((?:\\.|[^)])*\)|@(?:media|container|supports)\b[^{]*)|(?P<px>(?<![\w.-])-?(?:\d*\.)?\d+px\b)''', re.S | re.I)


def token(value, defined, additions):
    number = abs(int(value))
    if number in FIB:
        name = f'--fib-{FIB.index(number) + 1}'
    else:
        # Reuse existing exact step/size aliases before creating a composite.
        names = [f'--step-{number}', f'--size-{number}']
        name = next((name for name in names if name in defined), names[number > 55])
        if name not in defined:
            remainder, terms = number, []
            for index, step in reversed(list(enumerate(FIB, 1))):
                if remainder >= step:
                    terms.append(f'var(--fib-{index})')
                    remainder -= step
            if remainder:
                raise ValueError(f'Dimension outside the scale: {number}')
            additions[name] = 'calc(' + ' + '.join(terms) + ')'
            defined.add(name)
    ref = f'var({name})'
    return f'calc(-1 * {ref})' if value < 0 else ref


def main(fix=False):
    source = TOKENS.read_text(encoding='utf-8')
    defined = set(re.findall(r'(--[\w-]+)\s*:', source))
    additions, changed, edits, refs = {}, [], [], set()
    for path in sorted((ROOT / 'gravewright').rglob('*.css')):
        if 'vendor' in path.parts or path == TOKENS:
            continue
        css = path.read_text(encoding='utf-8')
        refs.update(re.findall(r'var\((--(?:step|size|fib)-[\w-]+)', css))
        count = 0

        def replace(match):
            nonlocal count
            if match['skip']:
                return match[0]
            value = float(match['px'][:-2])
            # Subpixel drawn strokes are an explicit design-system exception.
            if not value.is_integer():
                return match[0]
            count += 1
            return '0' if value == 0 else token(value, defined, additions)

        migrated = LEX.sub(replace, css)
        if count:
            changed.append((path, count))
            if fix:
                edits.append((path, migrated))
    missing = sorted(refs - defined)
    if missing:
        print('Undefined scale tokens: ' + ', '.join(missing))
        return 1
    if fix and additions:
        block = '\n    /* Exact geometry expressed as Fibonacci sums (CSS scale audit). */\n'
        block += ''.join(f'    {name}: {value};\n' for name, value in sorted(additions.items(), key=lambda v: int(v[0].rsplit('-', 1)[1])))
        source = source.replace('    /* ===== Spacing', block + '\n    /* ===== Spacing', 1)
        TOKENS.write_text(source, encoding='utf-8', newline='\n')
    for path, migrated in edits:
        path.write_text(migrated, encoding='utf-8', newline='\n')
    for path, count in changed:
        print(f'{path.relative_to(ROOT).as_posix()}: {count}')
    print(f'{"Migrated" if fix else "Remaining"}: {sum(count for _, count in changed)} pixel lengths in {len(changed)} stylesheets.')
    return 0 if fix or not changed else 1


if __name__ == '__main__':
    raise SystemExit(main('--fix' in sys.argv))
