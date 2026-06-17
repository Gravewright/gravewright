<<<<<<< HEAD
# HTML Sheets

HTML sheets are a stable SDK 1 sheet mode for packages that need custom UI while
staying inside Gravewright's package, capability, and security boundaries.

## Manifest

```json
{
  "capabilities": ["sheets.html", "sheets.controller", "sheets.richText"],
  "provides": {
    "actorTypes": [
=======
# HTML Sheets — Preparation (Phase 13)

> **Planned, not yet implemented.** HTML sheets must come *after* the stable
> base (frontend lifecycle, managed storage, interop). This document reserves the
> contract so it can land later without breaking SDK v1. The capabilities
> `sheets.html`, `sheets.controller`, and `sheets.richText` exist in the
> canonical registry as **experimental, declaration-only** placeholders.

## Sheet modes

HTML sheets are a separate sheet *mode*, not a loose extension of the declarative
model:

```text
declarative   (current)
html          (planned)
component     (future)
```

## Proposed manifest

```json
{
  "provides": {
    "actors": [
>>>>>>> origin/main
      {
        "id": "character",
        "label": "Character",
        "schema": "schemas/character.schema.json",
        "sheet": {
          "mode": "html",
          "template": "sheets/character.html",
          "controller": "scripts/character-sheet.js",
          "style": "styles/character-sheet.css"
        }
      }
    ]
<<<<<<< HEAD
  }
}
```

Inline HTML in the manifest is forbidden. Templates, controllers, and styles
must be package-local safe paths, and each declared file must exist on disk: the
loader reports `sdk.sheets.html.template_missing`,
`sdk.sheets.html.controller_missing`, and `sdk.sheets.html.style_missing` for
missing files, and the `*_unsafe_path` variants for paths that escape the
package directory.

## Template Rules

Forbidden in templates:

```html
<script></script>
<button onclick="roll()">Roll</button>
```

Supported bindings:

```html
<h1 data-text="actor.name"></h1>
<input data-bind="system.attributes.strength.value" type="number">
<button data-action="roll-strength">Roll</button>
<div data-rich-text="system.biography"></div>
```

`data-text` uses `textContent`. `data-rich-text` is sanitized and requires the
`sheets.richText` capability.

## Controller

```js
GravewrightSDK.register({
  id: "my-ruleset",
  setup(sdk) {
    sdk.sheets.registerController("character", {
      setup(ctx) {},
      mount(ctx) {},
      update(ctx) {},
      unmount(ctx) {},
      async onAction(action, ctx) {},
    });
  },
});
```

`setup` runs once per controller registration. `mount` runs when a sheet enters
the DOM. `update` runs when bound data changes. `unmount` runs before listeners
are removed. `onAction` handles `data-action`.

HTML sheet controllers communicate with other packages through `sdk.bus` and use
managed storage through `sdk.storage.sqlite` when their package declares the
matching capabilities.
=======
  },
  "capabilities": ["sheets.html", "sheets.controller"]
}
```

## Reserved rules (to enforce when implemented)

1. No inline HTML in the manifest — `template` must be a declared, path-safe file.
2. `controller` and `style` must be declared, path-safe files.
3. Actor/item/campaign data is escaped by default (`textContent`); rich text
   requires the explicit `sheets.richText` capability and a sanitizer.
4. Inline scripts and inline event handlers are forbidden (or an explicit unsafe
   mode).
5. HTML sheets communicate via `sdk.bus.*`, not loose public DOM events, and may
   use managed storage only via `sdk.storage.sqlite.*` with the capability.
6. HTML of a package is trusted installed code, not safe user content.

## Why now

Reserving the capabilities and the `sheet.mode: "html"` shape now means a future
HTML-sheets release is additive: packages declaring these capabilities are
already validated against the registry, and the security rules above are agreed
before any rendering code exists.
>>>>>>> origin/main
