# Package authoring guide

Start with [`declarative-model.md`](declarative-model.md), [`author-complete-checklist.md`](author-complete-checklist.md), and [`power-map.md`](power-map.md) before using this workflow. Those pages explain the package model, the full author surface, and how to choose between manifest data and runtime SDK calls.

This guide walks through the recommended SDK package author workflow.

## 1. Choose package kind

| Goal | Kind |
|---|---|
| Build a base RPG rules implementation | `ruleset` |
| Add optional behavior to a campaign | `addon` |
| Share code/assets between packages | `library` |
| Change visual presentation | `theme` |
| Ship importable game content | `content` |
| Ship reusable media | `assets` |

## 2. Scaffold with the CLI

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"
```

Generated packages should be placed under:

```text
data/packages/{kind_plural}/{id}/
```

## 3. Edit `manifest.json`

Required decisions:

- package `kind`;
- stable `id`;
- human-readable `name`;
- package `version`;
- compatibility range;
- minimal capability set;
- activation mode;
- entrypoints;
- `provides` data;
- settings, dependencies, conflicts, and distribution metadata when needed.

## 4. Keep capabilities minimal

Start with no capabilities, then add only what the package uses.

Examples:

- CSS-only theme: `assets.styles`
- addon with browser JS and toasts: `assets.scripts`, `assets.ui`
- addon with settings: `settings`
- package event bus: `bus.publish`, `bus.subscribe`
- ruleset sheets: `sheets.declarative`, `sheets.runtime`
- combat runtime: `combat.runtime`
- content pack package: `content.packs`

## 5. Add declarative package data

Prefer declarative data over runtime code.

Rulesets commonly declare:

```text
schemas/
layouts/
rules/
mappings/
content/
locales/
assets/
```

Add every referenced file path to the manifest through `entrypoints` or `provides`.

## 6. Add browser runtime only when needed

Packages with `assets.scripts` can register browser behavior:

```js
window.GravewrightSDK.register({
  id: "my-package",
  ready(sdk, { context }) {
    console.log(context);
  },
});
```

Browser runtime code must treat the server as authoritative. Use SDK methods to express intentions and integrate with documented UI surfaces.

## 7. Validate locally

```bash
grave package validate data/packages/my-package
grave package validate data/packages/my-package --json
grave package doctor my-package
```

Fix all validation errors before installing or publishing.

## 8. Install and activate

```bash
grave package install my-package --yes --enable
```

For campaign-scoped packages:

```bash
grave campaign package activate <campaign_id> my-package
```

Rulesets are exclusive. Addons, themes, content, and assets packages are multiple-activation package kinds. Libraries are passive dependencies.

## 9. Test in the table

Run Gravewright:

```bash
grave run --open
```

Test:

- manifest loads;
- package appears in package lists;
- capabilities are appropriate;
- entrypoint styles and scripts load;
- `window.GravewrightSDK.register` succeeds;
- package behavior works after `ready`;
- settings persist at intended scope;
- content packs load;
- locale keys resolve;
- activation/deactivation behaves correctly;
- package diagnostics are clean.

## 10. Document package behavior

Each package should include a README covering:

- purpose;
- package kind;
- supported Gravewright versions;
- capabilities requested and why;
- install/enable/activate steps;
- settings;
- content packs/assets;
- events emitted and consumed;
- known limitations;
- license and content rights.

## 11. Publish safely

Before publishing:

```bash
grave package validate data/packages/my-package
grave package doctor my-package
grave backup -o before-package-release.zip --include-assets --include-packages --verify
grave lock -o grave.lock.json
```

Recommended release checklist:

- version bumped;
- `compatibility.verified` updated after testing;
- README updated;
- changelog updated;
- no forbidden/private APIs used;
- no unnecessary capabilities declared;
- package zip/git/directory distribution metadata correct;
- license/content rights clear.
