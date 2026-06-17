# Examples

Real, validated Gravewright SDK packages used by the documentation.

Every package under `packages/` passes `grave package validate` and is checked in CI
(see `.github/workflows/ci.yml`). The SDK docs reference these packages as their
single source of truth for example manifests and runtime code:

- [`packages/hello-toast`](packages/hello-toast) — minimal addon that shows a toast.
- [`packages/toggle-example`](packages/toggle-example) — addon with a user setting.
- [`packages/my-rpg`](packages/my-rpg) — minimal ruleset (actor/item types, a rule, locales).
- [`packages/dark-fantasy-assets`](packages/dark-fantasy-assets) — asset pack (images, maps, icons).

Validate them all:

```bash
grave package validate examples/packages
```

See the end-to-end tutorials in [`docs/sdk/tutorial-addon.md`](../docs/sdk/tutorial-addon.md)
and [`docs/sdk/tutorial-ruleset.md`](../docs/sdk/tutorial-ruleset.md).
