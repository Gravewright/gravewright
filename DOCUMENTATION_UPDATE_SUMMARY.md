# Documentation Update Summary

This documentation set is aligned with **Gravewright v1.0.0-beta.1**.

## Performance documentation refresh — 2026-08-13

- Added canonical English and Brazilian Portuguese performance pages.
- Added explicit workload boundaries so synthetic dragon ceilings are not
  presented as realistic campaign token recommendations.
- Recorded the RTX 4060, driver, ANGLE/D3D11 backend, headed viewport, warm-up,
  measurement window, and validity rules used by current results.
- Linked the raw Gravewright realistic-scene and dragon benchmark reports.
- Replaced the superseded ~5,150 synthetic knee claim with the GPU-confirmed
  presentation and callback ranges.
- Converted the main documentation indexes from plain paths to navigable links.

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
  - `RELEASE_v1.0.0-beta.1.md`
- GitHub org/profile README:
  - `ORG_PROFILE_README.md`
  - `.github/profile/README.md`
- English and Brazilian Portuguese Beta status documents.
- Public status language uses the explicit `v1.0.0-beta.1` release name.
- SDK 1 PDF, annotations, capabilities, runtime, security, and power-map documentation.
- GM-guided prefetch, adaptive raster, campaign transfer, and renderer benchmark release coverage.

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
Gravewright v1.0.0-beta.1
```

Use the explicit release name and keep historical version labels only in release history.

## Recommended validation

```bash
grave doctor
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```
