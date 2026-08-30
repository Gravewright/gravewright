# Contributing

Contributions are welcome if they keep the package safe, maintainable, and
compatible with Gravewright SDK 1.

## Before contributing

Read:

- `README.md`
- `NOTICE.md`
- `CONTENT_POLICY.md`
- `COMPATIBILITY.md`

## Contribution rules

Contributions must not add proprietary or unclear content.

Allowed contribution types:

- schema improvements;
- sheet/layout improvements;
- original automation logic;
- original examples;
- tests and validation tooling;
- documentation improvements;
- properly attributed SRD-compatible material.

Do not submit:

- copied book text outside permitted SRD material;
- official artwork;
- official trade dress;
- copied proprietary compendium data;
- setting/adventure content you do not own or have permission to use.

## Validation

From a Gravewright checkout with this package installed at
`data/packages/rulesets/dnd5e`:

```bash
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli doctor --strict --json
```

## Pull request checklist

Before opening a PR:

```text
[ ] Package validates in Gravewright.
[ ] New content follows CONTENT_POLICY.md.
[ ] NOTICE.md is updated if attribution changed.
[ ] CHANGELOG.md is updated for user-visible changes.
[ ] No official/proprietary content was copied into the repository.
```
