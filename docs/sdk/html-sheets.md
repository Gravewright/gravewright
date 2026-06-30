# HTML Sheets

> **Status: stable.** `sheets.html`, `sheets.controller`, and
> `sheets.richText` are part of the SDK 1 contract.

> **Authoritative rolls.** HTML sheets can request server-side rolls with
> `data-roll` or `sdk.dice.roll`. Use Sheet IR actions or `sdk.rolls.intent`
> when the roll also needs targets, damage application, initiative, or other
> declarative action effects. See [`rolls.md`](rolls.md).

HTML sheets let a ruleset provide custom actor or item markup while keeping data
storage, permissions, asset loading, and package identity under Gravewright's
control. An HTML sheet replaces the declarative Sheet IR for that type.

This guide follows the current loader, browser runtime, actor/item renderers, and
validation rules. It covers template-only sheets first, then controllers and
advanced behavior.

## Start Here: The Mental Model

An HTML sheet is not a standalone web page. It is one part of an installed and
active Gravewright package. Gravewright owns the window, loads your files, gives
the template actor/item data, and decides whether a write is allowed.

```text
manifest.json
    │ declares the type and all allowed files
    ▼
Gravewright opens an actor or item
    │ reads the matching type id, for example "character"
    ▼
sheets/character.html
    │ is inserted inside the Gravewright sheet modal
    ▼
data-text / data-bind / data-rich-text
    │ read or update the sheet data
    ▼
Gravewright persistence and permission checks
```

JavaScript is optional. Add a controller only when plain bindings are not
enough, for example when a button must show a toast or coordinate UI state.

### Terms used in this guide

| Term | Plain-language meaning |
|---|---|
| Package | The complete extension directory containing the manifest and files. |
| Ruleset | The package that defines a campaign's game system. |
| Manifest | `manifest.json`, the inventory and permission declaration for the package. |
| Actor | A game entity such as a character, creature, or NPC. |
| Item | A game entity such as a weapon, spell, or piece of equipment. |
| Actor/item type | A stable id such as `character` or `weapon` that selects a schema and sheet. |
| Schema | JSON Schema describing the fields allowed in the type's data. |
| Template | The `.html` file Gravewright inserts into the sheet modal. |
| Binding | A `data-*` attribute that connects an HTML element to sheet data. |
| Controller | Optional JavaScript handling lifecycle hooks and `data-action` buttons. |
| Capability | A manifest permission describing what the package is allowed to use. |
| Entrypoint | A list of package CSS/JS files loaded into the game page. |

### What you need before starting

You need a ruleset directory under `data/packages/rulesets/`, a valid
`manifest.json`, and a campaign where that ruleset can be activated. Start from
a scaffold when creating a new package:

```bash
grave ruleset new my-ruleset --name "My Ruleset" --sheets
```

The scaffold may initially contain a declarative Sheet IR file. This guide
replaces that type's `sheet` value with an HTML descriptor object.

## 1. Package Layout

A typical ruleset uses this structure:

```text
data/packages/rulesets/my-ruleset/
├── manifest.json
├── schemas/
│   └── actors/character.schema.json
├── sheets/
│   └── character.html
├── scripts/
│   └── character-sheet.js
└── styles/
    └── character-sheet.css
```

Every path is package-relative. Paths that escape the package, such as
`../character.html`, are rejected.

### What each file does

| File | Required? | Responsibility |
|---|---|---|
| `manifest.json` | Yes | Declares package identity, capabilities, type ids, and every file Gravewright may load. |
| `schemas/actors/character.schema.json` | Yes when referenced | Defines the shape and defaults of character data. It is data, not visual layout. |
| `sheets/character.html` | Yes | Defines semantic markup, labels, inputs, and buttons. It must not contain scripts. |
| `styles/character-sheet.css` | Optional | Styles the markup. It must also be listed in `entrypoints.game.styles` to load. |
| `scripts/character-sheet.js` | Optional | Registers the package and controller. It must also be listed in `entrypoints.game.scripts`. |

Create missing directories with:

```bash
mkdir -p data/packages/rulesets/my-ruleset/{schemas/actors,sheets,scripts,styles}
```

### A small character schema

The schema and template should describe the same data. If the template binds
`system.strength`, define `strength` in the schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "title": "Character",
  "properties": {
    "strength": {
      "type": "integer",
      "default": 10
    },
    "biography": {
      "type": "string",
      "default": ""
    },
    "biographyHtml": {
      "type": "string",
      "default": ""
    }
  },
  "additionalProperties": false
}
```

## 2. Minimal Template-Only Sheet

A controller is optional. A template-only sheet supports display and automatic
field persistence through `data-text`, `data-bind`, and `data-rich-text`.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "ruleset",
  "id": "my-ruleset",
  "name": "My Ruleset",
  "version": "0.1.0",
  "compatibility": {
    "minimum": "1",
    "verified": "1"
  },
  "capabilities": ["actors.register", "sheets.html", "sheets.richText", "assets.styles"],
  "activation": {
    "scope": "campaign",
    "mode": "exclusive"
  },
  "entrypoints": {
    "game": {
      "styles": ["styles/character-sheet.css"]
    }
  },
  "provides": {
    "storage": {
      "model": "scoped-json-v1"
    },
    "actorTypes": [
      {
        "id": "character",
        "label": "Character",
        "schema": "schemas/actors/character.schema.json",
        "sheet": {
          "mode": "html",
          "template": "sheets/character.html",
          "style": "styles/character-sheet.css"
        }
      }
    ]
  },
  "settings": [],
  "dependencies": [],
  "conflicts": []
}
```

### Manifest field by field

| Field | Why it exists |
|---|---|
| `$schema` | Lets editors validate and autocomplete the manifest. |
| `schemaVersion` | Selects the manifest format. SDK 1 uses `1`. |
| `sdkVersion` | Selects the SDK API line used by the package. |
| `kind` | `ruleset` means this package defines the campaign's base system. |
| `id` | Permanent machine id. It must match the package directory and controller registration. |
| `name` | Human-readable package name. |
| `version` | Package/asset version. Increment it when shipping changes. |
| `compatibility` | States which SDK versions the package targets. |
| `capabilities` | Declares package features and gates scoped SDK methods. |
| `activation` | A ruleset is campaign-scoped and exclusive. |
| `entrypoints.game.styles` | Loads CSS into the game page. |
| `provides.storage` | Selects the ruleset's managed data model. |
| `provides.actorTypes` | Declares every actor type owned by the ruleset. |
| `actorTypes[].id` | The exact type stored on actors and used to find the controller. |
| `actorTypes[].schema` | The data contract for that actor type. |
| `actorTypes[].sheet` | Selects HTML mode and its template/controller/style files. |

The empty `settings`, `dependencies`, and `conflicts` arrays mean that this
minimal package declares none of those features yet.

Important loading rules:

- `sheet.template` declares and loads the HTML template.
- `sheet.style` declares the related file but does **not** inject it into the
  page. Add the CSS to `entrypoints.game.styles` and declare `assets.styles`.
- `sheet.controller` declares a controller path but does **not** execute it.
  Add the script to `entrypoints.game.scripts` and declare `assets.scripts`.
- The package must be installed, enabled, and active in the campaign.

### Make the minimal package available

Run these commands after creating the manifest, schema, HTML, and CSS:

```bash
grave package validate data/packages/rulesets/my-ruleset --json
grave package install my-ruleset --yes --enable
grave campaign package activate <campaign_id> my-ruleset
grave doctor
```

Replace `<campaign_id>` with the actual campaign id. Reload the game page after
activation. When editing an already installed package, use
`grave package update my-ruleset` instead of installing it again.

## 3. Template Bindings

```html
<form class="character-sheet">
  <input aria-label="Name" data-bind="actor.name">
  <span data-text="actor.type"></span>

  <label>
    Strength
    <input type="number" data-bind="system.strength">
  </label>

  <label>
    Biography
    <textarea data-bind="system.biography"></textarea>
  </label>

  <div data-rich-text="system.biographyHtml"></div>
</form>
```

Read the example from top to bottom:

1. The `<form>` is only a semantic/container element; Gravewright handles
   persistence, so no `action` URL is needed.
2. `data-bind="actor.name"` fills the input with the actor's core name and saves
   edits back to that name.
3. `data-text="actor.type"` displays the type safely as plain text.
4. `data-bind="system.strength"` connects the number input to the `strength`
   property defined by the schema.
5. The `<textarea>` edits an ordinary string.
6. `data-rich-text` displays trusted-looking formatted output only after the
   runtime sanitizer processes it.

For an actor whose stored data is:

```json
{
  "strength": 14,
  "biography": "A wandering knight",
  "biographyHtml": "<strong>A wandering knight</strong>"
}
```

`system.strength` resolves to `14`. Do not add an extra `sheet` or `data` segment
to the binding; the renderer already exposes stored sheet data under `system`.

### Available roots

| Sheet | Core identity | Sheet data | Permission flag |
|---|---|---|---|
| Actor | `actor.id`, `actor.name`, `actor.type` | `system.*` | `canEdit` |
| Item | `item.id`, `item.name`, `item.type` | `system.*` | `canEdit` |

The actor/item object also contains the sheet data for compatibility, but new
templates should use `system.*` for data and `actor.*`/`item.*` for identity.

### Binding behavior

- `data-text="path"` reads a value and assigns it through `textContent`.
- `data-rich-text="path"` renders sanitized HTML and requires
  `sheets.richText`.
- `data-bind="path"` initializes an element's `value`, listens to `input`,
  updates local context, and requests persistence through the normal actor/item
  patch path.
- `data-roll="formula"` requests a server-authoritative roll on click and
  requires `dice.roll`. Use `data-roll-label` to set the chat label.
- `type="number"` is converted with `Number(value)`. Other controls currently
  produce strings.
- `actor.name`, `item.name`, and `core.name` update the core name. `system.x`
  updates sheet data at `x`.
- Bindings use dot-separated object paths. Array indexing and wildcard paths
  are not a documented contract.

Checkboxes do not currently receive special boolean coercion in HTML mode. Use
a controller or a supported string/number representation when a true boolean is
required.

`canEdit` is context, not a client-side permission override. The server remains
authoritative and may reject writes. A controller may disable controls when
`ctx.data.canEdit` is false, but it must never treat the DOM state as security.

## 4. Adding CSS

```css
.character-sheet {
  display: grid;
  gap: 1rem;
  padding: 1rem;
}

.character-sheet input {
  width: 100%;
}
```

Scope selectors under a package-specific root class. Entrypoint styles are
loaded for the whole game page, not only inside one sheet modal.

After changing static assets, increment the package `version`, run
`grave package update`, and reload the page so versioned asset URLs change.

## 5. Adding a Controller

Add the required capabilities and entrypoint:

```json
{
  "capabilities": [
    "actors.register",
    "sheets.html",
    "sheets.controller",
    "assets.scripts",
    "assets.styles",
    "assets.ui"
  ],
  "entrypoints": {
    "game": {
      "scripts": ["scripts/character-sheet.js"],
      "styles": ["styles/character-sheet.css"]
    }
  }
}
```

Declare it on the type:

```json
"sheet": {
  "mode": "html",
  "template": "sheets/character.html",
  "controller": "scripts/character-sheet.js",
  "style": "styles/character-sheet.css"
}
```

Register from the declared package script:

```js
window.GravewrightSDK.register({
  id: "my-ruleset",

  setup(sdk) {
    sdk.sheets.registerController("character", {
      setup(ctx) {},
      mount(ctx) {},
      update(ctx) {},
      unmount(ctx) {},

      async onAction(action, ctx) {
        if (action.name === "show-summary") {
          sdk.ui.toast(`${ctx.actor.name}: ${ctx.data.system.strength}`);
        }
      },
    });
  },
});
```

This script does four separate things:

1. `GravewrightSDK.register` identifies which active package owns the code.
2. `setup(sdk)` receives the capability-gated SDK for that package.
3. `registerController("character", ...)` connects behavior to the actor type.
4. `onAction` compares `action.name` with the HTML button's `data-action` value.

The `sdk` object is intentionally scoped. If the controller calls
`sdk.ui.toast`, the manifest must include the capability mapped to that method
(`assets.ui`). A missing capability raises a runtime error instead of silently
granting access.

Both identifiers are exact contracts:

- `GravewrightSDK.register({ id })` must equal the package manifest `id`.
- `registerController(sheetType, ...)` must equal the actor/item type `id`, such
  as `character`. Registering `personagem` for a `character` sheet will not bind.

The package must declare every capability required by the SDK methods it calls.

## 6. Controller Context and Lifecycle

The controller receives:

```js
{
  packageId,
  sheetType,
  root,
  data,
  actor,     // actor sheets only
  item,      // item sheets only
  onChange
}
```

For a character named Aria with strength 14, the useful part of the context is
conceptually:

```js
{
  packageId: "my-ruleset",
  sheetType: "character",
  root: HTMLElement,
  actor: { id: "...", name: "Aria", type: "character" },
  data: {
    actor: { id: "...", name: "Aria", type: "character" },
    system: { strength: 14 },
    canEdit: true
  }
}
```

`root` is the element containing this one open sheet. Query inside it with
`ctx.root.querySelector(...)` instead of searching the entire document. This
keeps multiple simultaneously open sheets independent.

- `setup(ctx)` runs once for that registered controller in the page runtime.
- `mount(ctx)` runs after the template is inserted into the DOM.
- `update(ctx)` runs after a built-in `data-bind` input updates local data, and
  when the HTML runtime is explicitly updated.
- `unmount(ctx)` runs before built-in listeners are removed.
- `onAction(action, ctx)` handles elements with `data-action`.

Choose hooks by responsibility:

| Hook | Good uses | Avoid |
|---|---|---|
| `setup` | One-time controller configuration that does not belong to one modal. | Reading elements that have not been mounted yet. |
| `mount` | Initializing widgets or observers inside `ctx.root`. | Attaching global listeners without remembering how to remove them. |
| `update` | Refreshing calculated visual state after a bound value changes. | Replacing all `root.innerHTML`; that destroys runtime bindings. |
| `onAction` | Handling an explicit user click from `data-action`. | Comparing the whole action object to a string. Use `action.name`. |
| `unmount` | Disconnecting observers, timers, and external listeners. | Persisting last-minute state that should already have been saved. |

Listeners attached directly under the template are discarded when the sheet is
re-rendered. Listeners attached to `document`, `window`, timers, observers, or
other external objects must be removed in `unmount`.

## 7. Buttons and Actions

```html
<button type="button" data-action="show-summary">Show summary</button>
```

The controller receives:

```js
{
  name: "show-summary",
  event: MouseEvent,
  element: HTMLButtonElement
}
```

`data-action` only calls `controller.onAction`. It does **not** automatically
execute an entry from `rules/actions.gw.json`, and it is a no-op when no matching
controller is registered.

Use documented scoped SDK methods inside the handler, for example `sdk.ui`,
`sdk.settings`, `sdk.bus`, or `sdk.chat`, with their matching capabilities.
Do not call private renderer globals or depend on undocumented DOM internals.

Use `sdk.dice.roll` inside a controller for dynamic formulas. Use
`sdk.rolls.intent` or Sheet IR actions when the interaction should execute an
entry from `rules/actions.gw.json`, apply damage, target an actor/token, or
record initiative. Do not present a private core route as package API.

## 8. Rich Text and Security

Rich text requires `sheets.richText`:

```html
<article data-rich-text="system.biographyHtml"></article>
```

The sanitizer removes dangerous elements such as `script`, `iframe`, `object`,
and `embed`, event-handler attributes, and `javascript:` attribute values.

Templates themselves must not contain:

```html
<script src="..."></script>
<button onclick="roll()">Roll</button>
```

Inline scripts and inline event handlers fail package validation. Put behavior
in a declared controller. Only manifest-declared assets are served; undeclared
HTML files and traversal paths are rejected.

## 9. Actor, Item, and Token Sheets

HTML mode works for entries in both `provides.actorTypes` and
`provides.itemTypes`. Use `actor.*` for actor identity and `item.*` for item
identity. Both use `system.*` for package data.

Actor HTML sheets opened from unlinked tokens persist through the token sheet
data path; linked tokens persist through their actor. This routing is performed
by the core renderer, so templates should continue to bind `system.*` rather
than selecting an endpoint themselves.

An HTML descriptor suppresses the declarative layout for that type. A type uses
one mode at a time: an HTML descriptor object or a Sheet IR path string.

## 10. Complete Validation Workflow

```bash
grave package validate data/packages/rulesets/my-ruleset --json
grave package update my-ruleset --json
grave package doctor my-ruleset
grave doctor
```

After installation, activate the ruleset in the campaign and reload `/game`.
The controller script is only emitted for active packages.

Common errors:

| Error | Cause |
|---|---|
| `sdk.sheets.html.invalid_mode` | Sheet descriptor object whose `mode` is not `html`. |
| `sdk.sheets.html.capability_missing` | HTML descriptor without `sheets.html`. |
| `sdk.sheets.html.template_missing` | Missing/empty template declaration or file. |
| `sdk.sheets.html.template_unsafe_path` | Unsafe path or non-HTML template. |
| `sdk.sheets.html.controller_missing` | Missing file or missing `sheets.controller`. |
| `sdk.sheets.html.controller_unsafe_path` | Unsafe controller path. |
| `sdk.sheets.html.style_missing` | Declared style file does not exist. |
| `sdk.sheets.html.style_unsafe_path` | Unsafe style path. |
| `sdk.sheets.html.inline_html_forbidden` | Inline HTML was placed in the manifest. |
| `sdk.sheets.html.inline_script_forbidden` | Template contains a `<script>` tag. |
| `sdk.sheets.html.inline_handler_forbidden` | Template contains `onclick` or similar. |
| `sdk.sheets.html.rich_text_capability_missing` | `data-rich-text` lacks its capability. |
| `sdk.sheets.html.roll_capability_missing` | `data-roll` lacks `dice.roll`. |

## 11. Troubleshooting Checklist

If the template does not appear:

1. Confirm `sheet.mode` is `html` and the type id matches the created actor/item.
2. Validate the package and update its installed snapshot.
3. Confirm the package is enabled and active in the current campaign.
4. Confirm the template path is declared and exists.

If bindings do not save:

1. Use `actor.name`/`item.name` for names and `system.*` for package data.
2. Check `ctx.data.canEdit` and server permissions.
3. Inspect the browser network response for the patch request.
4. Ensure the schema and validation rules accept the value.

If a button does nothing:

1. Confirm the controller is in `entrypoints.game.scripts`.
2. Confirm `assets.scripts` and `sheets.controller` are declared.
3. Confirm the package id and `sheetType` match exactly.
4. Use `action.name`, not `action === "name"`.
5. Confirm the handler only calls SDK methods allowed by declared capabilities.
6. Increment the package version, update it, and reload the page.

### Using browser developer tools

Open the browser developer tools (usually `F12`) and use:

- **Console:** look for `GravewrightSDK.register refused`, capability errors,
  duplicate controller errors, or exceptions inside `onAction`.
- **Network:** filter for the package id. The template, CSS, and JS should return
  HTTP 200 from `/sdk/packages/<id>/asset/...`.
- **Network after editing a field:** inspect the actor/item patch request. HTTP
  200 means the server accepted it; HTTP 400/403 usually means invalid data or
  insufficient permission.
- **Elements:** confirm the template exists under the sheet root and that the
  expected `data-bind`/`data-action` attribute is present.

Useful symptoms:

| Symptom | Most likely cause |
|---|---|
| Plain “No sheet layout” message | Type id mismatch, inactive package, or missing HTML descriptor. |
| HTML appears without styling | CSS is declared as `sheet.style` but missing from the game entrypoint. |
| HTML and CSS appear, button is inert | Controller script was not loaded or `sheetType` does not match. |
| Input changes visually but resets later | Server rejected persistence, schema/path is wrong, or user cannot edit. |
| Old code still runs | Package version/snapshot or browser page has not been refreshed. |

## 12. Release Checklist

- Keep HTML, CSS, schemas, and controllers inside the package.
- Declare every referenced path and capability.
- Scope CSS under a package-specific root class.
- Use `data-text` for plain text and `data-rich-text` only when needed.
- Keep rules and authoritative game logic declarative/server-side where the SDK
  provides a public path.
- Remove external listeners in `unmount`.
- Test actor and item permissions, linked and unlinked tokens, and multiple open
  sheets.
- Validate, update, run doctor, bump the package version, and test after a full
  page reload.
