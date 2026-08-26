# Gravewright SDK

Start with the [SDK 1 quick start](quick-start.md). The final generated contract
is available as [JSON](_data/gravewright-sdk-1.json),
[TypeScript declarations](gravewright-sdk-1.d.ts), an exact
[method reference](method-reference.md), and [DTO schemas](dto-reference.md).

The Gravewright SDK is the only supported extension model for Gravewright.

Every installable extension is a package. A package is a directory under `data/packages/{kind_plural}/{id}/` containing a `manifest.json` plus the files declared by that manifest. Package behavior is defined through a single SDK v1 contract.

> [!WARNING]
> Gravewright is Beta software. SDK 1 RC 1 is the frozen public compatibility
> candidate. Packages declare `sdkVersion: "1"` and should use
> `compatibility: { "minimum": "1", "verified": "1" }`; RC status is release
> metadata and does not change those fields.

## Supported package kinds

| Kind | Purpose | Activation mode |
|---|---|---|
| `ruleset` | Campaign base game rules. Defines actor/item types, sheets, rules, mappings, content, and combat behavior. | `exclusive` |
| `addon` | Optional campaign extension. Adds UI, plugins, settings, scene tools, chat cards, content, or runtime behavior. | `multiple` |
| `library` | Passive dependency shared by other packages. | `passive` |
| `theme` | Visual/UI package, mostly CSS and UI assets. | `multiple` |
| `content` | Importable content-only package. | `multiple` |
| `assets` | Reusable media library for images, maps, icons, audio, portraits, and similar assets. | `multiple` |

A campaign has exactly one active `ruleset` and any number of active `addon`, `theme`, `content`, and `assets` packages. `library` packages are loaded only as dependencies.

## Canonical SDK files

- `manifest.json`: package metadata, capabilities, activation, entrypoints, settings, dependencies, conflicts, and `provides` data.
- `schemas/gravewright-package-v1.schema.json`: public JSON Schema for SDK v1 manifests.
- `static/js/sdk/sdk-capabilities.js`: browser capability allow-list and method-to-capability gates.
- `static/js/sdk/gravewright-sdk.js`: browser runtime and `window.GravewrightSDK` public entry point.
- `app/engine/sdk/`: server-side package loading, validation, install, activation, dependencies, content, assets, settings, locales, and diagnostics.

## Start here for package authors

If you are creating a package, read these three pages first:

1. [`declarative-model.md`](declarative-model.md): explains the declarative-first package model and when to add runtime JavaScript.
2. [`author-complete-checklist.md`](author-complete-checklist.md): defines what an author needs to build and use the full SDK surface.
3. [`power-map.md`](power-map.md): maps author goals to manifest fields, capabilities, runtime APIs, and docs.

The intended SDK model is not “write a plugin and discover globals”. It is:

```text
manifest + declared files + declared capabilities + optional scoped runtime
```

Authors should prefer declarative `manifest.json` data for rulesets, addons, content, assets, settings, locales, sheets, mappings, and rules. Runtime JavaScript should be used only for behavior that needs client-side events, UI, commands, chat, settings mutation, sheet/combat runtime plugins, or other documented scoped SDK methods.

## Public browser entry point

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Register plugins, sheets, combat behavior, commands, or local state.
  },
  ready(sdk, payload) {
    // Called after the game runtime is ready.
  },
});
```

The `id` must match the active package manifest id and must be called from that package's declared script. The runtime rejects missing ids, inactive packages, duplicate registrations, and registration attempts from a script owned by another package.

## The scoped `sdk`

Each package receives a frozen, package-scoped SDK object. Method access is gated by the capabilities declared in the package manifest.

Namespaces:

```text
sdk.version
sdk.package
sdk.kind
sdk.capabilities
sdk.context
sdk.game
sdk.bus
sdk.commands
sdk.ui
sdk.chat
sdk.settings
sdk.sheets
sdk.combat
sdk.tokens
sdk.scene
sdk.tools
sdk.content
sdk.i18n
```

Convenience shortcuts:

```js
sdk.toast("Hello");
sdk.setting("enabled");        // get
sdk.setting("enabled", true);  // set
```

## Authoring workflow

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"

grave package validate data/packages/rulesets/my-rpg
grave package install my-rpg --yes --enable
grave package doctor my-rpg
```

## Documentation map

### Concepts

- [`authority-model.md`](authority-model.md): how intent, capability, principal and projection fit together.
- [`semantic-runtime-boundaries.md`](semantic-runtime-boundaries.md): where each runtime domain stops, and why.
- [`campaign-and-tokens.md`](campaign-and-tokens.md): the campaign roster and token control projection.
- [`terminology.md`](terminology.md): canonical product terms and their translations.

### Scene and content

- [`scene-zones.md`](scene-zones.md): authoritative regions and membership.
- [`scene-world-objects.md`](scene-world-objects.md): package-owned semantic objects.
- [`geometry-semantics.md`](geometry-semantics.md): walls, doors, and what geometry means.
- [`content-and-assets.md`](content-and-assets.md): content packs, asset packs, and safe paths.
- [`pdf.md`](pdf.md): PDF documents, viewer, and annotations.

### Gameplay

- [`declarative-actions.md`](declarative-actions.md): registered actions and their bounded operations.
- [`input-commands.md`](input-commands.md): semantic commands, bindings, and typing rules.
- [`directed-interactions.md`](directed-interactions.md): asking a user to decide.
- [`durable-workflows.md`](durable-workflows.md): multi-step processes that wait and resume.
- [`gameplay-flow.md`](gameplay-flow.md): phases, participants, and secret commitment.
- [`semantic-timelines.md`](semantic-timelines.md): scheduled composition of semantic effects.
- [`token-transfer.md`](token-transfer.md): moving tokens between scenes.

### Audio and presentation

- [`native-sounds.md`](native-sounds.md): audio assets, sounds, and playback.
- [`spatial-sounds.md`](spatial-sounds.md): persistent scene emitters and acoustics.
- [`semantic-presentations.md`](semantic-presentations.md): temporary core-owned projections.
- [`shader-presets.md`](shader-presets.md): shader presets and instances.
- [`custom-shader-libraries.md`](custom-shader-libraries.md): package-provided shader libraries.

### Release

- [`rc1-compatibility-policy.md`](rc1-compatibility-policy.md): what is public, and what may change.
- [`rc1-certification.md`](rc1-certification.md): the certified RC 1 contract and known observations.
- [`stability-policy.md`](stability-policy.md): capability status levels.

### Reference


### Guides

- [`porting-modules.md`](porting-modules.md): end-to-end guidance for adapting modules from other platforms to Gravewright.
- [`tutorial-addon.md`](tutorial-addon.md): end-to-end: from zero to a working addon.
- [`tutorial-ruleset.md`](tutorial-ruleset.md): end-to-end: from zero to a minimal working ruleset.
- [`declarative-model.md`](declarative-model.md): declarative-first package model, examples, and author decision rules.
- [`author-complete-checklist.md`](author-complete-checklist.md): 100% SDK author checklist from scaffold to release.
- [`power-map.md`](power-map.md): author goal → manifest field → capability → runtime API map.
- [`manifest.md`](manifest.md): complete manifest contract.
- [`kinds.md`](kinds.md): package kinds and kind-specific rules.
- [`capabilities.md`](capabilities.md): allowed, forbidden, and method-gated capabilities.
- [`runtime.md`](runtime.md): browser runtime lifecycle and `window.GravewrightSDK`.
- [`html-sheets.md`](html-sheets.md): complete HTML actor/item sheet guide, from templates to controllers.
- [`reference.md`](reference.md): complete scoped SDK namespace reference.
- [`rolls.md`](rolls.md) - authoritative formula rolls, roll intents, and dice syntax.
- [`authoring-guide.md`](authoring-guide.md): package author workflow from scaffold to publish.
- [`settings.md`](settings.md): manifest settings and runtime settings API.
- [`content-and-assets.md`](content-and-assets.md): content packs, asset packs, and safe paths.
- [`messaging.md`](messaging.md): package-to-package events.
- [`cli.md`](cli.md): `grave` SDK and operator CLI.
- [`validation.md`](validation.md): manifest validation rules and common error keys.
- [`security.md`](security.md): security model and private API boundaries.
- [`examples.md`](examples.md): minimal ruleset and addon examples.
- [`troubleshooting.md`](troubleshooting.md): diagnosis playbook.

## What is not public SDK

The following are intentionally not public package APIs:

- backend code execution from packages;
- raw database access;
- raw filesystem access;
- raw network access;
- permission override;
- undocumented browser globals;
- direct renderer internals;
- private stores;
- private WebSocket event shapes;
- DOM structure not explicitly documented as an extension point.
