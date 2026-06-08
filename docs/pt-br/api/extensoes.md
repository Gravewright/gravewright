# APIs de Extensão

Gravewright expõe APIs públicas de navegador para sistemas e módulos. Essas APIs são materiais MIT para facilitar criação de integrações, sistemas, módulos, exemplos e SDKs. A implementação interna continua Apache-2.0.

> [!WARNING]
> **Alpha.** Use apenas APIs documentadas aqui. Objetos internos, stores, funções globais não documentadas e estrutura DOM do core podem mudar sem aviso entre versões Alpha.

## Superfícies principais

| Superfície | Usada por | Finalidade |
|---|---|---|
| `window.Gravewright.modules` | módulos | registrar runtime, consultar módulos, obter API escopada |
| `api.*` | módulos | hooks, UI, settings, chat, cena, tokens e contexto |
| `window.GravewrightSheets` | sistemas | registrar comportamento complementar de fichas |
| `window.GravewrightCombat` | sistemas | registrar hooks/slots leves do tracker de combate |

## Regra de autoridade

O backend é autoritativo para estado de jogo. Código de módulo/sistema no navegador pode melhorar UI, enviar intenções e reagir a eventos, mas não deve assumir que estado local é verdade final.

Use APIs públicas para:

- mostrar UI;
- registrar hooks;
- ler contexto;
- enviar intenções;
- salvar settings por endpoint oficial;
- acionar interações documentadas.

Evite:

- mutar objetos retornados por `api.game.*`;
- depender de DOM interno do core;
- chamar endpoints privados sem documentação;
- guardar estado crítico só em `localStorage`;
- sobrescrever globals do Gravewright.

## Module Runtime API

Um módulo registra seu runtime assim:

```js
(function () {
  window.Gravewright.modules.register({
    id: "meu-modulo",

    init(api, payload) {
      // registre hooks e prepare estado local
    },

    ready(api, payload) {
      // rode depois do game:ready para este módulo
    }
  });
})();
```

O `id` deve bater com o `id` do manifest.

### `payload`

O payload passado para `init` e `ready` contém:

```js
{
  module,   // manifesto normalizado do módulo
  api,      // API escopada do módulo
  context   // contexto atual da mesa
}
```

## Namespaces do `api`

### `api.version`

```js
console.log(api.version); // "1"
```

### `api.capabilities`

```js
api.capabilities.has("settings");
api.capabilities.require("assets.ui", "minha-ui");
api.capabilities.requirement("settings.get");
api.capabilities.list();
```

Use para verificar em runtime se o manifest declarou o necessário.

### `api.game`

```js
const context = api.game.context();
const campaign = api.game.campaign();
const scene = api.game.scene();
const user = api.game.user();
```

Os retornos são clones congelados. Eles são leitura, não fonte de mutação.

### `api.hooks`

Requer capability `hooks.client`.

```js
const off = api.hooks.on("game:ready", ({ context }) => {
  console.log("Mesa pronta", context);
});

api.hooks.once("scene:loaded", ({ scene }) => {
  console.log("Primeira cena carregada", scene);
});

off();
```

Hooks oficiais:

```text
module:init
module:ready
module:failed
game:ready
campaign:loaded
scene:loaded
```

Consulte programaticamente:

```js
api.hooks.official();
```

### `api.ui`

Requer capability `assets.ui`.

```js
api.ui.toast("Mensagem do módulo", { duration: 4000 });
api.ui.openModal("modal-id");
api.ui.closeModal("modal-id");
```

### `api.settings`

Requer capability `settings`.

```js
const definitions = api.settings.definitions();
const all = api.settings.all();
const value = api.settings.get("ui.enabled", true);
await api.settings.set("ui.enabled", false);
```

`set` usa o endpoint oficial:

```text
POST /modules/settings
```

### `api.chat`

Requer capability `chat.cards`.

```js
api.chat.send({
  type: "module-message",
  text: "Olá do módulo"
});
```

### `api.scene`

Requer capability `assets.ui`.

```js
const canvas = api.scene.activeCanvas();
const camera = api.scene.activeCameraForScene(sceneId);
```

### `api.tokens`

Requer capability `tokens.extends`.

```js
api.tokens.centerOn(tokenId);
```

### `api.tools`

Requer capability `assets.ui`.

```js
const tool = api.tools.activeTool();
```

## System Sheet API

Sistemas podem registrar comportamento complementar para fichas:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("meu-sistema", {
    renderSection(node, variant, renderContext, helpers) {
      if (variant !== "special") return null;
      const section = helpers.el("section", "my-special-section");
      section.appendChild(helpers.el("h3", null, node.label || "Especial"));
      return section;
    },

    renderHeaderIdentity(main, bundle, helpers) {
      main.appendChild(helpers.el("div", "my-subtitle", bundle.actor?.type || ""));
    },

    autoFitWidth(actorType) {
      return actorType === "character" ? 820 : null;
    }
  });
})();
```

Hooks conhecidos:

| Hook | Retorno | Uso |
|---|---|---|
| `renderSection(node, variant, renderContext, helpers)` | `Node` ou `null` | renderizar uma seção customizada |
| `renderHeaderIdentity(main, bundle, helpers)` | `void` | complementar cabeçalho da ficha |
| `autoFitWidth(actorType)` | número ou `null` | sugerir largura automática da modal |

Helpers úteis:

```text
helpers.el
helpers.phIcon
helpers.getPath
helpers.formatMod
helpers.cssIdent
helpers.nonEmptyParts
helpers.normalizeInteraction
helpers.bindInteraction
helpers.headerInput
helpers.headerSelect
helpers.headerIdentityCell
helpers.closeFloatingSheetMenus
helpers.postJSON
helpers.refresh
helpers.getContext
```

Use essa API com moderação. Prefira layout declarativo sempre que possível.

## System Combat API

Sistemas podem registrar hooks e slots de combate:

```js
(function () {
  const Combat = window.GravewrightCombat;
  if (!Combat || typeof Combat.registerSystem !== "function") return;

  Combat.registerSystem("meu-sistema", {
    hooks: {
      participantMeta(payload) {
        return payload.participant?.actor_type || "";
      }
    },
    slots: {
      participantBadge(payload) {
        const badge = document.createElement("span");
        badge.className = "my-combat-badge";
        badge.textContent = payload.participant?.actor_type || "";
        return badge;
      }
    }
  });
})();
```

A API de combate é intencionalmente pequena. Sistemas não substituem o renderer completo do tracker.

## Compatibilidade

Todo sistema/módulo deve declarar:

```json
{
  "apiVersion": "1",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  }
}
```

Durante Alpha, atualize `verified` sempre que testar contra uma nova versão do Gravewright.
