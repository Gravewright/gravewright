# HTML Sheets

> **Status: stable.** `sheets.html`, `sheets.controller` e `sheets.richText`
> fazem parte do contrato LTS da SDK 1.

HTML sheets permitem que um pacote forneca templates HTML para actor/item
sheets, com controller registrado via `sdk.sheets.registerController`.

## Manifest

```json
{
  "capabilities": ["sheets.html", "sheets.controller"],
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

`template` deve apontar para um arquivo `.html` seguro dentro do pacote. HTML
inline no manifest, `<script>` inline e handlers como `onclick` sao rejeitados.
`controller` exige `sheets.controller`; rich text com `data-rich-text` exige
`sheets.richText`. Cada arquivo declarado deve existir no disco: o loader reporta
`sdk.sheets.html.template_missing`, `sdk.sheets.html.controller_missing` e
`sdk.sheets.html.style_missing` para arquivos ausentes, e as variantes
`*_unsafe_path` para caminhos que escapam do diretório do pacote.
HTML sheets devem usar `sdk.bus` para interop entre pacotes e
`sdk.storage.sqlite` para estado persistente gerenciado.

## Template

```html
<section class="character-sheet">
  <h1 data-text="name"></h1>
  <input data-bind="system.hp.value" type="number" />
  <button data-action="rollAttack">Attack</button>
  <div data-rich-text="system.biography"></div>
</section>
```

- `data-text` escreve com `textContent`.
- `data-bind` sincroniza inputs e chama `ctx.onChange`.
- `data-action` chama `controller.onAction`.
- `data-rich-text` passa pelo sanitizer do runtime.

## Controller

```ts
sdk.sheets.registerController("character", {
  mount(ctx) {
    // chamado apos a montagem inicial
  },
  update(ctx) {
    // chamado quando os dados mudam
  },
  unmount(ctx) {
    // limpar listeners externos aqui
  },
  onAction(action, ctx) {
    // action.name, action.event, action.element
  },
});
```

Controllers sao registrados por tipo de sheet e o runtime chama mount, update e
unmount conforme a sheet entra, muda ou sai da tela.
