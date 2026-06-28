# Documentation Update Summary

This bundle is corrected for **Gravewright v2.1.0-alpha**.

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
  - `RELEASE_v2.1.0-alpha.md`
- GitHub org/profile README:
  - `ORG_PROFILE_README.md`
  - `.github/profile/README.md`
- English and Brazilian Portuguese Alpha docs updated for `v2.1.0-alpha`.
- Public status language uses the explicit `v2.1.0-alpha` release name.

## Version language

Use:

```text
Gravewright v2.1.0-alpha
```

Avoid old generic pre-release labels. Use the explicit release name instead.

## Recommended validation

```bash
grave doctor
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```
