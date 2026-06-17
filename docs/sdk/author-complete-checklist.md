# 100% SDK author checklist

This checklist defines what "complete SDK documentation" should let an author do.

Use it as an acceptance test for a package and for the documentation itself. If an author cannot complete an item from the docs alone, the docs are incomplete.

## 1. Choose the package kind

| Goal | Kind | Required activation pattern | Start with |
|---|---|---|---|
| Create a game system/ruleset | `ruleset` | `scope: "campaign"`, `mode: "exclusive"` | actor/item types, sheets, rules, combat, content |
| Add optional behavior | `addon` | `scope: "campaign"`, `mode: "multiple"` | settings, scripts, plugins, UI, content |
| Share dependency code/data | `library` | `mode: "passive"` | dependencies and provided shared assets/data |
| Change visual presentation | `theme` | `mode: "multiple"` | styles, UI assets, settings |
| Ship importable data | `content` | `mode: "multiple"` | content packs |
| Ship media | `assets` | `mode: "multiple"` | asset pack metadata and media paths |

## 2. Author the manifest contract

Every package author must be able to define:

- `$schema`
- `schemaVersion`
- `sdkVersion`
- `kind`
- `id`
- `name`
- `version`
- `description`
- `authors`
- `license`
- `homepage`
- `repository`
- `compatibility.minimum`
- `compatibility.verified`
- `compatibility.maximum`
- `capabilities`
- `activation.scope`
- `activation.mode`
- `entrypoints.game.styles`
- `entrypoints.game.scripts`
- `settings`
- `provides`
- `dependencies`
- `conflicts`
- `distribution`
- `display`

See [`manifest.md`](manifest.md) and [`declarative-model.md`](declarative-model.md).

## 3. Declare capabilities intentionally

The author must know why every capability is present.

| Capability family | Author can use it to | Main docs |
|---|---|---|
| `actors.*` | define actor types and actor behavior contracts | [`declarative-model.md`](declarative-model.md), [`manifest.md`](manifest.md) |
| `items.*` | define item types and item behavior contracts | [`declarative-model.md`](declarative-model.md), [`manifest.md`](manifest.md) |
| `sheets.*` | declare sheets or add sheet runtime plugins | [`runtime.md`](runtime.md), [`reference.md`](reference.md) |
| `rules.*` | provide rules documents or extend rules | [`declarative-model.md`](declarative-model.md) |
| `dice.*`, `rolls.*` | support roll behavior and roll intents | [`reference.md`](reference.md) |
| `combat.*` | configure combat or register combat runtime plugins/panels | [`reference.md`](reference.md) |
| `tokens.*` | map token data or use token helpers | [`reference.md`](reference.md) |
| `scene.*` | read scene/tool state or add scene tooling | [`reference.md`](reference.md) |
| `chat.*` | send chat cards/intents | [`reference.md`](reference.md) |
| `content.*` | provide and read importable content packs | [`content-and-assets.md`](content-and-assets.md), [`reference.md`](reference.md) |
| `settings` | declare/read/write package settings | [`settings.md`](settings.md), [`reference.md`](reference.md) |
| `locales` | provide translations and translate labels | [`reference.md`](reference.md) |
| `assets.*` | load styles/scripts/UI assets/media packs | [`content-and-assets.md`](content-and-assets.md) |
| `bus.*` | publish/subscribe/provide/request package messages | [`messaging.md`](messaging.md), [`reference.md`](reference.md) |
| `commands.register` | register user/browser commands | [`reference.md`](reference.md) |

## 4. Build a ruleset with full SDK coverage

A complete ruleset author should be able to do all of this:

### Data model

- Define actor types.
- Define item types.
- Attach schemas to actor/item types.
- Define defaults and derived fields where supported.
- Map actors/items to sheets.
- Map actors to token defaults.

### User experience

- Provide declarative sheets.
- Provide sheet components where needed.
- Provide localized labels for sheets, settings, content, and rules.
- Provide CSS for the ruleset UI.
- Define settings for optional rules.

### Game rules

- Provide declarative rules documents.
- Declare roll mappings or roll intents.
- Configure combat defaults.
- Declare content packs with starter data.
- Provide assets used by the ruleset.

### Runtime behavior

Only where declarative data is insufficient, a ruleset author should know how to:

- register sheet runtime plugins with `sdk.sheets.register`;
- register combat runtime behavior with `sdk.combat.register`;
- register a combat panel with `sdk.combat.registerPanel`;
- publish/subscribe to namespaced events with `sdk.bus`;
- send chat cards or intents with `sdk.chat.send`;
- read settings with `sdk.settings.get`;
- write settings with `sdk.settings.set`;
- translate labels with `sdk.i18n.t`;
- inspect current campaign/scene/user state with `sdk.game.*`;
- use token/scene/tool helpers through the documented SDK only.

## 5. Build an addon with full SDK coverage

A complete addon author should be able to build these addon types:

| Addon type | Manifest features | Runtime APIs |
|---|---|---|
| Style addon | `entrypoints.game.styles`, `assets.styles` | none |
| Settings addon | `settings`, `settings` capability | `sdk.settings.*` if scripted |
| UI addon | `assets.scripts`, `assets.ui` | `sdk.ui.*` |
| Chat addon | `chat.cards` | `sdk.chat.send` |
| Automation addon | `bus.*`, event dependencies | `sdk.bus.*` |
| Command addon | `commands.register` | `sdk.commands.register` |
| Content addon | `provides.contentPacks`, `content.packs` | `sdk.content.*` if scripted |
| Scene/tool addon | `scene.tools`, optional assets | `sdk.scene.*`, `sdk.tools.*` |
| Token addon | `tokens.extends` | `sdk.tokens.centerOn` |
| Combat addon | `combat.runtime` | `sdk.combat.*` |

## 6. Build content and asset packages

A content author must be able to:

- declare one or more content packs;
- point each pack to safe package-relative paths;
- define pack id, label, type, and path;
- validate content file existence;
- depend on a ruleset if the content expects specific actor/item types;
- localize content labels where appropriate.

An asset author must be able to:

- declare image, map, icon, audio, or mixed assets;
- choose safe formats;
- avoid raw filesystem assumptions;
- document license and attribution;
- reference assets from content/ruleset/addon packages through declared paths or dependencies.

## 7. Use the runtime lifecycle correctly

Every scripted package author must understand:

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Register listeners, commands, sheet plugins, combat plugins, and local state.
  },
  ready(sdk, payload) {
    // Use functionality that depends on the DOM/game runtime being ready.
  }
});
```

Rules:

- The `id` must match `manifest.json`.
- The script must be declared in `entrypoints.game.scripts`.
- The package must declare `assets.scripts`.
- The package must declare each capability required by the SDK methods it calls.
- Registration should happen once.
- Code should be resilient if optional dependencies are absent.

## 8. Use every scoped SDK namespace appropriately

| Namespace | Author use |
|---|---|
| `sdk.version` | check SDK runtime version |
| `sdk.package` | read current package identity |
| `sdk.kind` | branch behavior by package kind if necessary |
| `sdk.capabilities` | test/require capability before optional behavior |
| `sdk.context()` | read frozen context snapshot |
| `sdk.game` | read campaign, scene, user, readiness |
| `sdk.bus` | publish/subscribe/provide/request package messages |
| `sdk.commands` | register commands |
| `sdk.ui` | show toasts and open/close documented modals |
| `sdk.chat` | send chat cards/intents |
| `sdk.settings` | read/write declared settings |
| `sdk.sheets` | use sheet helpers and register sheet plugins |
| `sdk.combat` | register combat behavior, panels, handlers, slots |
| `sdk.tokens` | use token helpers |
| `sdk.scene` | read scene/canvas/camera state |
| `sdk.tools` | read active tool state |
| `sdk.content` | list/read content packs |
| `sdk.i18n` | translate package strings |

See [`reference.md`](reference.md).

## 9. Integrate with other packages safely

Authors must be able to:

- declare hard dependencies in `dependencies`;
- declare incompatible packages in `conflicts`;
- use optional integration through namespaced events;
- include a `version` field in event payloads;
- keep event names package-scoped, for example `package:my-addon:ready`;
- check `sdk.capabilities.has(...)` before optional runtime paths;
- gracefully no-op when an optional dependency is not present.

See [`messaging.md`](messaging.md).

## 10. Validate and debug

Authors must be able to run:

```bash
grave package validate data/packages/my-package
grave package doctor my-package
grave package install my-package --yes --enable
```

A package is ready only after:

- manifest validation passes;
- every declared file exists;
- capabilities are valid;
- forbidden capabilities are absent;
- dependency/conflict behavior is intentional;
- package can be installed and activated from a clean checkout;
- runtime registration appears in debug mode when applicable;
- settings persist and reload;
- content/assets can be discovered by the SDK;
- UI behavior fails safely when optional core surfaces are unavailable.

## 11. Security and boundary checklist

Authors must understand that SDK v1 does not expose:

- backend package execution;
- raw database access;
- raw filesystem access;
- raw network access;
- permission override;
- private stores;
- private renderer internals;
- undocumented browser globals.

Scripted packages run trusted browser code for table users. Request `assets.scripts` only when necessary.

## 12. Release checklist

Before publishing a package, verify:

- `manifest.json` is valid.
- `README.md` explains install, activation, capabilities, settings, and compatibility.
- `CHANGELOG.md` documents changes.
- License and asset attribution are included.
- Compatibility range is honest.
- No development-only paths are present.
- The package has been installed from its packaged distribution form.
- All examples in the docs still work.

## 13. Documentation completeness test

The SDK docs should answer these author questions without external help:

- What package kind should I choose?
- Which files should my package contain?
- Which manifest fields are required?
- Which `provides` fields should I use?
- Which capabilities do I need?
- Which runtime SDK methods exist?
- Which capability gates each method?
- How do I declare settings?
- How do I read/write settings?
- How do I provide content?
- How do I provide assets?
- How do I register sheet/combat behavior?
- How do I send chat cards?
- How do I communicate with another package?
- How do I validate, install, activate, and debug?
- Which APIs are private or forbidden?
