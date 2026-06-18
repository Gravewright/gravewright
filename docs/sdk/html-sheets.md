# HTML Sheets

HTML sheets are a stable SDK 1 sheet mode for packages that need custom UI while
staying inside Gravewright's package, capability, and security boundaries.

## Manifest

```json
{
  "capabilities": ["sheets.html", "sheets.controller", "sheets.richText"],
  "provides": {
    "actorTypes": [
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
