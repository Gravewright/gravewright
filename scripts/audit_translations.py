"""Check catalog parity, parameters and explicit native UI translation calls."""
import argparse
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = re.compile(r'\{(?:[A-Za-z_][A-Za-z0-9_.]*|\d+)\}')
CALLS = re.compile(r'''\b(?:gwText|modalText|text|label|t)\s*\(\s*((?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'))''')


def audit(catalog_root):
    catalogs = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in catalog_root.glob('*.json')}
    source = catalogs.get('en', {})
    errors = []
    if not source:
        return ['Missing English catalog'], {}
    for locale, messages in catalogs.items():
        if set(messages) != set(source):
            errors.append(f'{locale}: different source keys')
        for key, value in messages.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(f'{locale}: empty/non-string value: {key}')
            elif sorted(PARAMETERS.findall(key)) != sorted(PARAMETERS.findall(value)):
                errors.append(f'{locale}: altered placeholders: {key}')
    missing = {}
    for path in (ROOT / 'gravewright').rglob('*.js'):
        if any(p in path.parts for p in ('vendor', 'node_modules')) or path.name.endswith('.test.js'):
            continue
        for match in CALLS.finditer(path.read_text(encoding='utf-8')):
            try:
                key = ast.literal_eval(match[1])
                # Widget expressions are nested inside serialized JSON strings.
                key = re.sub(r'\\(?:x([0-9A-Fa-f]{2})|u([0-9A-Fa-f]{4}))', lambda m: chr(int(m[1] or m[2], 16)), key)
            except (ValueError, SyntaxError):
                continue
            if key not in source and key.strip() not in source and re.search(r'[A-Za-z]', key) and (key[:1].isupper() or ' ' in key) and not any(c in key for c in '<>'):
                missing.setdefault(key, set()).add(path.relative_to(ROOT).as_posix())
    return errors, {key: sorted(paths) for key, paths in sorted(missing.items())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogs', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    errors, missing = audit(args.catalogs)
    report = {'errors': errors, 'untranslated_calls': missing}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors or missing))
