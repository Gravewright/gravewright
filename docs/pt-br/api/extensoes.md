# APIs de Extensão no Navegador

Gravewright expõe APIs públicas de navegador para sistemas e módulos.

Os materiais de API são licenciados sob MIT. A implementação permanece Apache-2.0.

> [!WARNING]
> **Alpha.**
>
> Use apenas APIs documentadas. Globals internos, stores privados, internals de renderer, comportamento de fallback e estrutura DOM do core podem mudar entre releases Alpha.

## Superfícies Principais

| Superfície                   | Usada por | Finalidade                                                                               |
| ---------------------------- | --------- | ---------------------------------------------------------------------------------------- |
| `window.Gravewright.modules` | Módulos   | Registrar runtimes de módulo, inspecionar módulos e obter APIs escopadas                 |
| `api.*` escopado             | Módulos   | Hooks, UI, settings, chat, cena, tokens e APIs de contexto                               |
| `window.GravewrightSheets`   | Sistemas  | Labels de ficha, pequenas extensões de comportamento de ficha e hooks de cabeçalho/seção |
| `window.GravewrightCombat`   | Sistemas  | Hooks e slots leves do tracker de combate                                                |

O backend é autoritativo para o estado de jogo.

APIs de navegador podem melhorar UI, reagir a eventos e enviar intenções. Elas não devem tratar estado local como verdade final.

## Module Runtime API

```js
(function () {
  window.Gravewright.modules.register({
    id: "meu-modulo",

    init(api, payload) {
      // Chamado quando o runtime do módulo é inicializado.
    },

    ready(api, payload) {
      // Chamado quando o runtime do módulo está pronto.
    }
  });
})();
```

O id do runtime deve bater com o id do manifest.

`payload` contém:

```js
{
  module,  // manifest normalizado do módulo
  api,     // API escopada do módulo
  context  // contexto atual da mesa
}
```

## API Escopada de Módulo

Namespaces:

```text
api.version
api.capabilities
api.hooks
api.game
api.chat
api.scene
api.settings
api.tokens
api.tools
api.ui
```

### `api.capabilities`

```js
api.capabilities.has("settings");
api.capabilities.require("assets.ui", "minha-feature");
api.capabilities.requirement("settings.get");
api.capabilities.list();
```

### `api.game`

```js
const context = api.game.context();
const campaign = api.game.campaign();
const scene = api.game.scene();
const user = api.game.user();
```

Os valores retornados são clones ou snapshots congelados.

### `api.hooks`

Requer `hooks.client`.

```js
const off = api.hooks.on("game:ready", ({ context }) => {
  // Reage quando a mesa está pronta.
});

api.hooks.once("scene:loaded", ({ scene }) => {
  // Reage uma única vez.
});

off();
```

Hooks oficiais:

* `module:init`
* `module:ready`
* `module:failed`
* `game:ready`
* `campaign:loaded`
* `scene:loaded`

### `api.ui`

Requer `assets.ui`.

```js
api.ui.toast("Olá do módulo", { duration: 4000 });
api.ui.openModal("modal-id");
api.ui.closeModal("modal-id");
```

### `api.settings`

Requer `settings`.

```js
const value = api.settings.get("ui.enabled", true);
await api.settings.set("ui.enabled", false);
```

### `api.chat`

Requer `chat.cards`.

```js
api.chat.send({
  type: "module-message",
  text: "Olá"
});
```

### `api.scene`, `api.tokens` e `api.tools`

```js
const canvas = api.scene.activeCanvas(); // assets.ui
const camera = api.scene.activeCameraForScene(sceneId); // assets.ui

api.tokens.centerOn(tokenId); // tokens.extends

const tool = api.tools.activeTool(); // assets.ui
```

## System Sheet API

Sistemas podem registrar pequenos comportamentos de ficha no navegador através de `window.GravewrightSheets`.

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("meu-sistema", {
    labels: {
      actorName: "Nome",
      roll: "Rolar",
      equipped: "Equipado",
      prepared: "Preparado"
    },

    renderSection(node, variant, renderContext, helpers) {
      if (variant !== "special") return null;

      const section = helpers.el("section", "minha-secao-especial");
      section.appendChild(helpers.el("h3", null, node.label || "Especial"));
      return section;
    },

    renderHeaderIdentity(main, bundle, helpers) {
      main.appendChild(helpers.el("div", "meu-subtitulo", bundle.actor?.type || ""));
    },

    autoFitWidth(actorType) {
      return actorType === "character" ? 820 : null;
    }
  });
})();
```

### Labels de ficha

Sistemas podem fornecer labels de ficha através de `labels`.

A engine fornece labels de fallback em inglês. Labels de sistema são mescladas com os fallbacks. Chaves ausentes caem para inglês.

Chaves conhecidas de label de ficha:

| Chave               | Finalidade                                    |
| ------------------- | --------------------------------------------- |
| `actorName`         | Placeholder do nome do ator                   |
| `levelPrefix`       | Prefixo usado antes de um valor de nível      |
| `equipped`          | Badge de item equipado                        |
| `spellCirclePrefix` | Prefixo usado antes de círculo/nível de magia |
| `prepared`          | Badge de magia preparada                      |
| `active`            | Label de efeito/status ativo                  |
| `inactive`          | Label de efeito/status inativo                |
| `qtyPrefix`         | Prefixo de quantidade                         |
| `portrait`          | Placeholder de retrato                        |
| `token`             | Placeholder de token                          |
| `uploadPortrait`    | Título de upload de retrato                   |
| `uploadToken`       | Título de upload de token                     |
| `cancel`            | Label do botão de cancelar                    |
| `roll`              | Label genérico de rolagem                     |
| `rollDialogTitle`   | Título do diálogo de rolagem                  |
| `healed`            | Texto de toast de cura                        |
| `tookDamage`        | Texto de toast de dano recebido               |
| `reducedFrom`       | Texto de toast de redução de dano             |

Exemplo:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("meu-sistema", {
    labels: {
      actorName: "Nome",
      levelPrefix: "Nível",
      equipped: "Equipado",
      spellCirclePrefix: "Círculo",
      prepared: "Preparado",
      active: "Ativo",
      inactive: "Inativo",
      qtyPrefix: "Qtd.",
      portrait: "Retrato",
      token: "Token",
      uploadPortrait: "Enviar retrato",
      uploadToken: "Enviar token",
      cancel: "Cancelar",
      roll: "Rolar",
      rollDialogTitle: "Rolagem",
      healed: "curou",
      tookDamage: "sofreu",
      reducedFrom: "reduzido de"
    }
  });
})();
```

### Hooks de ficha

Hooks conhecidos de ficha:

| Hook                                                   | Retorno            | Finalidade                                         |
| ------------------------------------------------------ | ------------------ | -------------------------------------------------- |
| `renderSection(node, variant, renderContext, helpers)` | `Node` ou `null`   | Renderiza uma seção customizada de ficha           |
| `renderHeaderIdentity(main, bundle, helpers)`          | `void`             | Estende a área de identidade do cabeçalho da ficha |
| `autoFitWidth(actorType)`                              | `number` ou `null` | Sugere largura de modal para um tipo de ator       |

### Limite dos helpers de ficha

O objeto `helpers` passado para hooks de ficha é a superfície suportada de helpers.

Sistemas não devem depender de variáveis não documentadas do renderer, stores privados, estrutura DOM ou classes CSS internas, exceto quando forem explicitamente documentadas como pontos públicos de extensão.

## System Combat API

Sistemas podem registrar hooks e slots leves de combate através de `window.GravewrightCombat`.

```js
(function () {
  const Combat = window.GravewrightCombat;
  if (!Combat || typeof Combat.registerSystem !== "function") return;

  Combat.registerSystem("meu-sistema", {
    hooks: {
      participantMeta({ participant }) {
        return participant?.actor_type || "";
      }
    },

    slots: {
      participantActions({ participant }) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "minha-acao-combate";
        button.textContent = participant?.actor_type || "Ação";
        return button;
      }
    }
  });
})();
```

Hooks conhecidos de combate:

| Hook              | Retorno                       | Finalidade                                                |
| ----------------- | ----------------------------- | --------------------------------------------------------- |
| `beforeRender`    | `void`                        | Chamado antes do tracker de combate renderizar            |
| `afterRender`     | `void`                        | Chamado depois do tracker de combate renderizar           |
| `participantMeta` | `string`, `string[]` ou falsy | Adiciona metadados específicos do sistema ao participante |

Slots conhecidos de combate:

| Slot                 | Retorno                   | Finalidade                                                                |
| -------------------- | ------------------------- | ------------------------------------------------------------------------- |
| `participantActions` | `Node`, `Node[]` ou falsy | Adiciona controles específicos do sistema à área de ações do participante |

A API de combate é intencionalmente pequena.

Sistemas devem preferir configuração de combate, labels, hooks, slots e CSS em vez de substituir o renderer inteiro do tracker de combate.

Substituir `window.GravewrightCombatPanel` não faz parte da API pública estável durante Alpha.

## Detalhes Privados de Implementação

Os itens abaixo são privados, exceto quando documentados em outro lugar:

* globals de renderer;
* estrutura DOM;
* stores privados;
* ordenação interna de eventos;
* classes CSS que não foram documentadas como hooks de extensão;
* labels de fallback;
* substituição completa do renderer de ficha;
* substituição completa do renderer de combate.

Use APIs documentadas, configuração declarativa, labels, locales, hooks, slots e assets.
