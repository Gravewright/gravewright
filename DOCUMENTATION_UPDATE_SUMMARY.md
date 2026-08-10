# Documentation Update Summary

This bundle is corrected for **Gravewright v3.0.1-alpha**.

## Included

- Full project documentation tree under `docs/`.
- Root project docs:
  - `README.md`
  - `CHANGELOG.md`
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `CODE_OF_CONDUCT.md`
  - `NOTICE`
- Release notes:
  - `RELEASE_v3.0.1-alpha.md`
- GitHub org/profile README:
  - `ORG_PROFILE_README.md`
  - `.github/profile/README.md`
- English and Brazilian Portuguese Alpha docs updated for `v3.0.1-alpha`.
- Public status language uses the explicit `v3.0.1-alpha` release name.

## Changed in this release

- `docs/features/dice-tray.md` (new) — notation, open-ended `!`, naming a roll
  with `#`, and the browser-local tray history.
- `docs/features/dynamic-lighting.md` — layer visibility split (effects, walls,
  lighting) and the streamer composition sandbox.
- `docs/pt-br/efeitos-visuais.md` — the same two sections in Portuguese.
- `docs/api/http.md` — per-user preference routes (`layout`, `vision`, `ping`),
  the `view_scene` query parameter, and the chat deletion authorization rule.
- `docs/README.md`, `docs/pt-br/README.md` — index entries and release pointer.

## Version language

Use:

```text
Gravewright v3.0.1-alpha
```

Avoid old generic pre-release labels. Use the explicit release name instead.

## Recommended validation

```bash
grave doctor
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```
