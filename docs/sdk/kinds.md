# Package kinds

SDK v1 has six package kinds. The kind controls activation, validation, expected `provides` fields, and the package author's design intent.

## Summary

| Kind | Purpose | Required activation mode | Typical author |
|---|---|---|---|
| `ruleset` | Base game system for a campaign. | `exclusive` | Game system author |
| `addon` | Optional campaign extension. | `multiple` | Addon author |
| `library` | Passive shared dependency. | `passive` | Shared utility author |
| `theme` | Visual/UI package. | `multiple` | Theme author |
| `content` | Importable content package. | `multiple` | Content pack author |
| `assets` | Reusable media package. | `multiple` | Asset pack author |

## `ruleset`

A `ruleset` defines the campaign's base game model. A campaign has exactly one active ruleset.

Required:

- `kind: "ruleset"`
- `activation.mode: "exclusive"`
- `provides.storage.model`
- at least one `provides.actorTypes` entry

Common `provides` fields:

- `storage`
- `actorTypes`
- `itemTypes`
- `rules`
- `mappings`
- `contentPacks`
- `locales`
- `assets`
- `areaMarkers`

Typical capabilities:

```text
actors.register
items.register
sheets.declarative
sheets.runtime
rules.declarative
rules.extends
dice.roll
rolls.intent
combat.config
combat.runtime
tokens.mappings
tokens.extends
content.packs
locales
assets.styles
assets.scripts
assets.ui
chat.cards
```

Use a ruleset when the campaign cannot function without the package.

## `addon`

An `addon` is an optional campaign extension. Addons can add browser runtime behavior, UI, settings, chat cards, scene tools, token tools, content packs, and package-to-package integrations.

Required:

- `kind: "addon"`
- `activation.mode: "multiple"`

Typical capabilities:

```text
assets.scripts
assets.styles
assets.ui
settings
chat.cards
tokens.extends
scene.tools
sheets.runtime
combat.runtime
content.packs
commands.register
locales
```

Use an addon when a GM should be able to enable, disable, activate, or deactivate the behavior per campaign.

## `library`

A `library` is a passive package loaded as a dependency. It should not be activated directly as campaign functionality.

Required:

- `kind: "library"`
- `activation.mode: "passive"`

Typical capabilities:

```text
assets.scripts
assets.styles
locales
```

A metadata-only library can declare no runtime capabilities.

Use a library when multiple packages need shared assets, utilities, or metadata and absence should block dependent packages.

## `theme`

A `theme` provides visual/UI presentation assets, typically CSS.

Required:

- `kind: "theme"`
- `activation.mode: "multiple"`

Typical capabilities:

```text
assets.styles
assets.ui
settings
locales
```

A theme should avoid game-state assumptions. Prefer CSS, icons, and optional settings.

## `content`

A `content` package ships content packs without defining the campaign's ruleset or runtime behavior.

Required:

- `kind: "content"`
- `activation.mode: "multiple"`

Typical capabilities:

```text
content.packs
locales
```

Content packages should not define actor types, item types, storage models, or combat configuration. They are intended for importable or campaign-activated content.

## `assets`

An `assets` package ships reusable media.

Required:

- `kind: "assets"`
- `activation.mode: "multiple"`
- `provides.assets` entries with `id`, `label`, and safe package-relative `path`

Typical capabilities:

```text
assets.pack
assets.images
assets.audio
assets.maps
assets.icons
locales
```

An `assets` package must not declare:

- `provides.storage`
- `provides.actorTypes`
- `provides.itemTypes`
- `provides.rules`
- combat configuration

## Decision guide

| Question | Package kind |
|---|---|
| Is this the base rules model for a campaign? | `ruleset` |
| Can the campaign work without it? | Usually `addon`, `theme`, `content`, or `assets` |
| Does it only exist because other packages depend on it? | `library` |
| Is it only CSS/UI styling? | `theme` |
| Is it only importable data/content? | `content` |
| Is it reusable media? | `assets` |
