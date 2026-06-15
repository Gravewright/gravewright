# Package Kinds

| Kind | Purpose | `activation.mode` |
|---|---|---|
| `ruleset` | Campaign base ruleset. The only base package type. | `exclusive` |
| `addon` | Optional campaign extension. | `multiple` |
| `library` | Passive dependency shared by packages. | `passive` |
| `content` | Importable content package. | `multiple` |
| `theme` | Visual/UI package, mostly CSS/UI. | `multiple` |
| `assets` | Reusable media library: images, maps, icons, audio. | `multiple` |

A campaign has exactly **one** active `ruleset` and any number of active `addon`, `theme`, `assets`, and `content` packages. `library` packages are passive and are loaded only as dependencies.

## `ruleset`

Required: `activation.mode = exclusive`, `provides.storage`, `provides.actorTypes`.

Typical capabilities: `actors.register`, `items.register`, `sheets.declarative`, `rules.declarative`, `dice.roll`, `combat.config`, `tokens.mappings`, `content.packs`, `locales`, `assets.styles`, `assets.scripts`.

## `addon`

Required: `activation.mode = multiple`.

Typical capabilities: `assets.scripts`, `assets.styles`, `assets.ui`, `hooks.client`, `settings`, `chat.cards`, `tokens.extends`, `scene.tools`, `sheets.hooks`, `combat.hooks`, `content.packs`.

## `library`

Required: `activation.mode = passive`.

Typical capabilities: `assets.scripts`, `assets.styles`, `locales`, or none when used only as a passive dependency metadata package.

## `theme`

Required: `activation.mode = multiple`.

Typical capabilities: `assets.styles`, `assets.ui`, `settings`, `locales`.

## `content`

Required: `activation.mode = multiple`.

Typical capabilities: `content.packs`, `locales`.

Content packages provide importable or campaign-activated content packs without defining actor/item types or runtime rules.

## `assets`

Required: `activation.mode = multiple`.

Provides reusable media via `provides.assets` (`images`, `maps`, `icons`, `audio`). Each entry needs `id`, `label`, and package-relative `path`.

An `assets` package must **not** declare `actorTypes`, `itemTypes`, `rules`, or combat config.
