# Referência da SDK do navegador

Esta página documenta o objeto `sdk` escopado passado aos runtimes de pacote por `window.GravewrightSDK.register(...)`.

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {},
  ready(sdk, payload) {},
});
```

## `sdk.version`

```js
sdk.version // "1"
```

A string de versão do runtime da SDK.

## `sdk.package`

```js
sdk.package.id
sdk.package.kind
sdk.package.version
```

Identidade congelada do pacote para o runtime escopado atual.

## `sdk.kind`

```js
sdk.kind // "ruleset", "addon", "library", "theme", "content" ou "assets"
```

Atalho para o kind do pacote.

## `sdk.capabilities`

### `sdk.capabilities.has(capability)`

Retorna `true` quando o pacote atual declarou `capability`.

```js
if (sdk.capabilities.has("settings")) {
  const enabled = sdk.settings.get("enabled", true);
}
```

### `sdk.capabilities.require(capability, apiName = "sdk")`

Lança erro se o pacote não declarou `capability`.

```js
sdk.capabilities.require("storage.sqlite", "my-feature");
```

### `sdk.capabilities.list()`

Retorna a lista de capabilities declaradas pelo pacote.

```js
console.log(sdk.capabilities.list());
```

## `sdk.context()`

Retorna um snapshot congelado do contexto de jogo atual.

```js
const context = sdk.context();
```

Prefira helpers específicos de namespace sob `sdk.game` quando possível.

## `sdk.game`

### `sdk.game.context()`

Retorna um snapshot congelado do contexto de jogo.

### `sdk.game.campaign()`

Retorna o snapshot da campanha atual ou `null`.

### `sdk.game.scene()`

Retorna o snapshot da cena atual ou `null`.

### `sdk.game.user()`

Retorna o snapshot do usuário atual ou `null`.

### `sdk.game.ready()`

Retorna `true` depois que o runtime de jogo está pronto.

## `sdk.commands`

Requer `commands.register`.

### `sdk.commands.register(name, handler)`

Registra um comando de navegador despachando um evento `vtt:command-register`.

```js
sdk.commands.register("my-package.open-panel", async () => {
  sdk.ui.openModal("my-panel");
});
```

Nomes de comando devem ser namespaced por pacote.

## `sdk.ui`

Requer `assets.ui`.

### `sdk.ui.toast(message, options)`

Mostra um toast de UI através da superfície de toast do core.

```js
sdk.ui.toast("Saved", { duration: 3000 });
```

### `sdk.ui.openModal(modalId)`

Abre um modal do core por id.

### `sdk.ui.closeModal(modalOrId)`

Fecha um modal do core por id ou referência de modal.

## `sdk.chat`

Requer `chat.cards`.

### `sdk.chat.send(message)`

Submete uma requisição de mensagem/card de chat de propriedade do pacote através da ponte de eventos do navegador.

```js
sdk.chat.send({
  type: "package-card",
  title: "Roll Result",
  total: 17,
});
```

O servidor e o runtime do core permanecem autoritativos. Trate isto como uma intenção, não como uma escrita direta de persistência.

## `sdk.dice`

Requer `dice.roll`.

### `sdk.dice.roll({ formula, label = "", actorId = "" })`

Pede uma rolagem autoritativa de ator via `POST /game/actor/roll`. A resposta
inclui total, grupos de dados, metadados renderizados do chat e os campos de
apresentacao retornados pelo engine.

```js
await sdk.dice.roll({
  actorId: ctx.actor.id,
  label: "Attack",
  formula: "2d20kh1 + @sheet.attackBonus",
});
```

## `sdk.rolls`

Requer `rolls.intent`.

### `sdk.rolls.intent({ actorId, actionId, inputs = {}, rollOptions = {}, target = {} })`

Pede uma action declarativa autoritativa via `POST /game/actor/action`. Use para
actions de Sheet IR, targets, dano aplicado, iniciativa e outros efeitos
declarados em `rules/actions.gw.json`.

```js
await sdk.rolls.intent({
  actorId: ctx.actor.id,
  actionId: "attack.primary",
  inputs: {},
  rollOptions: { visibility: "public" },
  target: { actorId: targetActorId, tokenId: targetTokenId },
});
```

Veja [`rolls.md`](rolls.md) para sintaxe de formulas e padroes de sistema.

## `sdk.settings`

Requer `settings`.

### `sdk.settings.definitions()`

Retorna as definições de settings declaradas no manifesto do cliente.

### `sdk.settings.all()`

Retorna os valores de settings atuais visíveis ao pacote.

### `sdk.settings.get(key, fallback = undefined)`

Lê o valor de uma setting.

```js
const enabled = sdk.settings.get("enabled", true);
```

### `sdk.settings.set(key, value, options = {})`

Persiste o valor de uma setting através do endpoint de settings da SDK.

```js
await sdk.settings.set("enabled", false);
await sdk.settings.set("enabled", true, { campaignId: "campaign-id" });
```

Quando `options.campaignId` é omitido, o id da campanha ativa é usado quando disponível.

## `sdk.sheets`

Requer `sheets.runtime`.

### `sdk.sheets.helpers()`

Retorna funções helper públicas de ficha expostas pelo runtime de ficha do core.

### `sdk.sheets.register(plugin)`

Registra comportamento de ficha para o pacote.

```js
sdk.sheets.register({
  labels: {
    actorName: "Name",
    roll: "Roll",
  },
  renderSection(node, variant, renderContext, helpers) {
    if (variant !== "special") return null;
    const section = helpers.el("section", "my-special-section");
    section.appendChild(helpers.el("h3", null, node.label || "Special"));
    return section;
  },
  renderHeaderIdentity(main, bundle, helpers) {
    main.appendChild(helpers.el("div", "my-subtitle", bundle.actor?.type || ""));
  },
  autoFitWidth(actorType) {
    return actorType === "character" ? 820 : null;
  },
});
```

### `sdk.sheets.registerController(sheetType, controller)`

Registra um controller de ficha HTML para uma ficha declarada com
`sheet.mode = "html"`.

```js
sdk.sheets.registerController("character", {
  setup(ctx) {},
  mount(ctx) {},
  update(ctx) {},
  unmount(ctx) {},
  async onAction(action, ctx) {},
});
```

Controllers tratam eventos `data-action` e devem limpar listeners externos no
`unmount`.

## `sdk.combat`

Requer `combat.runtime`.

### `sdk.combat.register(plugin)`

Registra handlers e slots de combate leves em runtime.

```js
sdk.combat.register({
  handlers: {
    participantMeta({ participant }) {
      return participant?.actor_type || "";
    },
  },
  slots: {
    participantActions({ participant }) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = participant?.actor_type || "Action";
      return button;
    },
  },
});
```

### `sdk.combat.registerPanel(panel)`

Registra um objeto de substituição/extensão de painel de combate.

```js
sdk.combat.registerPanel({
  renderHud(context) {},
  renderPanel(context) {},
});
```

Substituir o painel é poderoso; prefira handlers e slots leves quando possível.

### `sdk.combat.dispatch(name, payload)`

Despacha um evento de runtime de combate para o handler registrado do pacote atual.

### `sdk.combat.renderSlot(name, payload)`

Renderiza um slot de combate e retorna um array de nós ou valores renderizados.

## `sdk.tokens`

Requer `tokens.extends`.

### `sdk.tokens.centerOn(tokenId)`

Centraliza o mapa ativo em um token.

```js
sdk.tokens.centerOn(tokenId);
```

## `sdk.scene`

Requer `scene.tools`.

### `sdk.scene.activeCanvas()`

Retorna o objeto de canvas ativo quando disponível, senão `null`.

### `sdk.scene.activeCameraForScene(sceneId)`

Retorna os dados de câmera de uma cena quando disponível, senão `null`.

## `sdk.tools`

Requer `scene.tools`.

### `sdk.tools.activeTool()`

Retorna o id da ferramenta/mapa ativa, com padrão `"select"` quando indisponível.

## `sdk.content`

Requer `content.packs`.

### `sdk.content.packs()`

Carrega os resumos de content packs do pacote atual.

```js
const packs = await sdk.content.packs();
```

### `sdk.content.pack(packId)`

Carrega um content pack específico.

```js
const spells = await sdk.content.pack("my-rpg-spells");
```

## `sdk.storage.sqlite`

Requer `storage.sqlite`.

### `sdk.storage.sqlite.query(scope, name, params = {})`

Executa uma query de leitura declarada via endpoint de storage gerenciado.

```js
const rows = await sdk.storage.sqlite.query("campaign", "getState", {
  key: "panel-state",
});
```

### `sdk.storage.sqlite.execute(scope, name, params = {})`

Executa uma query de escrita declarada via endpoint de storage gerenciado.

```js
await sdk.storage.sqlite.execute("campaign", "saveState", {
  key: "panel-state",
  value_json: JSON.stringify(state),
});
```

### `sdk.storage.sqlite.status(scope)`

Retorna o status do storage gerenciado para o pacote e escopo.

```js
const status = await sdk.storage.sqlite.status("campaign");
```

O pacote nunca recebe path nem envia SQL; o backend resolve pacote, campanha,
capability, escopo, nome da query e parametros declarados.

## `sdk.bus`

Requer a capability `bus.*` correspondente a cada metodo.

### `sdk.bus.publish(eventName, payload)`

Publica um evento pertencente ao pacote. Nomes de eventos devem usar o namespace
do pacote.

```js
await sdk.bus.publish("my-package.panel.opened", { panelId: "main" });
```

### `sdk.bus.subscribe(eventName, handler)`

Assina eventos do bus e retorna uma funcao de unsubscribe.

```js
const off = sdk.bus.subscribe("other-ruleset.actor.rested", (payload) => {
  console.log(payload);
});
```

### `sdk.bus.provide(methodName, handler)`

Registra um provider RPC do pacote para `methodName`.

```js
const off = sdk.bus.provide("my-package.state.get", async (payload) => {
  return { key: payload.key, value: "open" };
});
```

### `sdk.bus.request(methodName, payload, options)`

Chama um provider do bus e resolve para `{ ok: true, value }` ou
`{ ok: false, error }`.

```js
const result = await sdk.bus.request("my-package.state.get", {
  key: "panel-state",
});
```

## `sdk.i18n`

Requer `locales`.

### `sdk.i18n.t(key, fallback)`

Procura uma chave de locale no catálogo de locales do pacote. Retorna `fallback` quando fornecido, senão retorna `key`.

```js
const label = sdk.i18n.t("my-rpg.action.attack", "Attack");
```

## Shortcuts

| Atalho | Equivalente |
|---|---|
| `sdk.toast(message, options)` | `sdk.ui.toast(message, options)` |
| `sdk.setting(key)` | `sdk.settings.get(key)` |
| `sdk.setting(key, value)` | `sdk.settings.set(key, value)` |
