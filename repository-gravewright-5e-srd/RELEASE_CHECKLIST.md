# Release Checklist

Use this checklist before publishing a package release.

## Package metadata

```text
[ ] manifest.json version updated
[ ] CHANGELOG.md updated
[ ] compatibility minimum/verified checked
[ ] package id unchanged unless intentionally breaking
[ ] display name avoids official/endorsed wording
```

## Legal/content

```text
[ ] NOTICE.md reviewed
[ ] CONTENT_POLICY.md reviewed
[ ] no official PDFs included
[ ] no official artwork included
[ ] no copied proprietary compendium data included
[ ] SRD-derived content is attributed
```

## Validation

From a Gravewright checkout:

```bash
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli package update dnd5e --json
uv run python -m app.cli doctor --strict --json
```

Expected doctor result:

```json
{
  "ok": true,
  "error_count": 0
}
```

Warnings may be environment-specific, such as a development `SESSION_SECRET`.

## Release artifact

Recommended release ZIP layout:

```text
dnd5e/
  manifest.json
  assets/
  content/
  layouts/
  locales/
  mappings/
  rules/
  schemas/
  README.md
  INSTALL.md
  NOTICE.md
  LICENSE.md
```

## Tag

```bash
git tag v0.3.0
git push origin v0.3.0
```
