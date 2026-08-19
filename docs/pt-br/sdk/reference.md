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

## `sdk.assets`

Requer `assets.library`.

### `sdk.assets.list(options)`

Lista a biblioteca de assets da campanha. O servidor já filtra pelo papel do
membro, então um pacote nunca enxerga mais do que o usuário atual pode ver.

Cada item traz `kind`: `"image"` ou `"pdf"`: para o pacote não precisar
reinterpretar `content_type`. Filtre com `options.kind`; `options.campaignId` usa a
campanha ativa por padrão.

```js
const fichas = await sdk.assets.list({ kind: "pdf" });
// [{ id, filename, src, kind: "pdf", byte_size, ... }]
```

`src` é a URL para buscar os bytes. Imagem é servida inline; o resto vai como
anexo, então renderize um PDF por um renderizador em canvas em vez de embutir a
URL direto.

### `sdk.assets.ingest(file)` / `sdk.assets.cancelImport(assetId)`

Requer `assets.import`. `ingest` aceita um `File` realmente selecionado pelo
usuário; o core valida e cria um asset da campanha. Não aceita path do servidor
nem retorna path de storage ou digest. O pipeline síncrono e limitado da SDK 1
retorna `ready`; cancelar uma importação concluída não remove o asset.

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

Os handlers são chamados durante a renderização: `beforeRender`, `afterRender` e
`combatantMeta` (cujo retorno é anexado à linha de meta do combatente). O slot
`combatantActions` retorna nós colocados ao lado do menu do combatente.

```js
sdk.combat.register({
  handlers: {
    combatantMeta({ combatant }) {
      return combatant.defeated ? "caído" : "";
    },
  },
  slots: {
    combatantActions({ combatant, isGm }) {
      if (!isGm) return [];
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Concentração";
      button.dataset.combatantId = combatant.id;
      return button;
    },
  },
});
```

Cada payload traz o combatente como o painel o vê: `id`, `actor_id`, `token_id`,
`name`, `initiative` (`null` enquanto não rolado), `hidden`, `defeated`,
`position`, `is_current`, `is_next`, `has_acted`, `can_move_up`, `can_move_down`
e `bar` (a barra principal do token do combatente, ou `null`). `initiative` é
texto, não número: leia `state.config.input` para saber
que formato o sistema ativo coloca ali.

### `sdk.combat.registerPanel(panel)`

Substitui o painel de combate padrão. O objeto precisa expor `renderPanel(panel,
state)`, que passa a ser dono de tudo dentro do corpo do painel.

```js
sdk.combat.registerPanel({
  renderPanel(panel, state) {
    const target = panel.querySelector("[data-combat-state]");
    target.textContent = `Rodada ${state.round}: ${state.current_name}`;
  },
});
```

Substituir o painel significa reimplementar a edição de iniciativa e os
controles de turno, então prefira handlers e slots quando eles bastarem.

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

## Runtime semântico da SDK 1

Estes métodos SDK 1 aplicam gates de capability do pacote e permissão do usuário atual e retornam snapshots públicos congelados. Leituras são limitadas a 100 registros; escritas permanecem autoritativas no servidor.

- `sdk.events.on`, `sdk.events.once`, `sdk.events.available`; `sdk.permissions.can`.
  Mutations de annotations PDF emitem o evento agregado e filtrado por visibility
  `pdf.annotations.changed` para re-read autorizado.
- `sdk.actors.get`, `sdk.actors.list`, `sdk.actors.data`, `sdk.actors.create`, `sdk.actors.update`, `sdk.actors.delete`.
- `sdk.items.get`, `sdk.items.list`, `sdk.items.create`, `sdk.items.update`, `sdk.items.delete`.
- `sdk.tokens.get`, `sdk.tokens.list`, `sdk.tokens.move`, `sdk.tokens.create`, `sdk.tokens.update`, `sdk.tokens.delete`; targets privados usam `sdk.tokens.targets.list`, `sdk.tokens.targets.set` e `sdk.tokens.targets.clear`.
- `sdk.scene.get`, `sdk.scene.list`, `sdk.scene.active`.
- `sdk.scene.geometry.walls`, `sdk.scene.geometry.lights`, `sdk.scene.geometry.createWall`, `sdk.scene.geometry.updateWall`, `sdk.scene.geometry.deleteWall`, `sdk.scene.geometry.createLight`, `sdk.scene.geometry.updateLight`, `sdk.scene.geometry.deleteLight`, `sdk.scene.geometry.setDoorState`.
- `sdk.scene.effects.list`, `sdk.scene.effects.create`, `sdk.scene.effects.update`, `sdk.scene.effects.delete`.
- `sdk.ui.slots.available`, `sdk.ui.slots.register`; `sdk.chat.list`, `sdk.chat.get`.
- `sdk.combat.current`, `sdk.combat.combatants`, `sdk.combat.start`, `sdk.combat.end`, `sdk.combat.advance`, `sdk.combat.setTurn`, `sdk.combat.add`, `sdk.combat.remove`.
- `sdk.rules.actions.list`, `sdk.rules.actions.get`, `sdk.rules.actions.resolve`, `sdk.rules.actions.execute`, `sdk.rules.actions.executeReference`.
- `sdk.automation.schedule`, `sdk.automation.get`, `sdk.automation.list`, `sdk.automation.cancel` aceitam somente registered actions durable-safe; `sdk.automation.audit` retorna transições limitadas, pertencentes ao pacote e sem payload.
- `sdk.pdf.get`, `sdk.pdf.metadata`; `sdk.pdf.viewer.open`, `sdk.pdf.viewer.goToPage`, `sdk.pdf.viewer.search`, `sdk.pdf.viewer.currentPage`.
- `sdk.pdf.annotations.list`, `sdk.pdf.annotations.create`; presentation usa `sdk.pdf.presentation.start`, `sdk.pdf.presentation.current`, `sdk.pdf.presentation.update` e `sdk.pdf.presentation.end`. Veja [API de PDF](pdf.md).
- `sdk.cards.state`, `sdk.cards.definitions.list`, `sdk.cards.definitions.get`,
  `sdk.cards.definitions.instantiate`, `sdk.cards.shuffle`, `sdk.cards.reset`, `sdk.cards.draw`,
  `sdk.cards.reveal`, `sdk.cards.discard`, `sdk.cards.play`,
  `sdk.cards.updatePlacement`, `sdk.cards.discardPlacement`.

Journals em runtime usam `sdk.journals.get`, `sdk.journals.list`,
`sdk.journals.create`, `sdk.journals.update` e `sdk.journals.delete`.
A apresentação transitória autorizada usa `sdk.handouts.present`.

As ferramentas de cena incluem `sdk.scene.fog.state`, `sdk.scene.fog.enable`,
`sdk.scene.fog.disable`, `sdk.scene.fog.reset`, `sdk.scene.fog.paint`,
`sdk.scene.images.list`, `sdk.scene.images.place`, `sdk.scene.images.update`,
`sdk.scene.images.delete`, `sdk.scene.geometry.splitWall`,
`sdk.scene.geometry.moveWallNode`, `sdk.scene.geometry.moveWalls` e
`sdk.scene.geometry.deleteWalls`.

Ferramentas espaciais usam `sdk.tools.register` para registrar uma tool de
package com descarte automático e DTO estável de pointer em world-space.
Consultas puras de distância usam `sdk.scene.measurements.measure`. Measurements compartilhadas com TTL usam `sdk.scene.measurements.share`, `sdk.scene.measurements.listShared` e `sdk.scene.measurements.cancel`. Templates
compartilhados persistentes usam `sdk.scene.templates.list`,
`sdk.scene.templates.get`, `sdk.scene.templates.create`,
`sdk.scene.templates.update` e `sdk.scene.templates.delete`. Controles de
partículas descobrem schemas públicos com `sdk.scene.effects.presets`.

Shaders semânticos usam `sdk.scene.shaders.presets`,
`sdk.scene.shaders.getPreset`, `sdk.scene.shaders.list`,
`sdk.scene.shaders.apply`, `sdk.scene.shaders.update`,
`sdk.scene.shaders.enable` e `sdk.scene.shaders.remove`. Esses métodos expõem
somente metadata estável, parâmetros tipados e instances versionadas; GLSL e o
lifecycle do renderer permanecem privados.

Bibliotecas trusted usam `sdk.scene.shaders.customLibrary.registerProvider`,
`sdk.scene.shaders.customLibrary.openEditor` e
`sdk.scene.shaders.customLibrary.preview`, `sdk.scene.shaders.customLibrary.clearPreview` e
`sdk.scene.shaders.customLibrary.use`. Elas conectam storage e UI do pacote ao
editor e placement controlados pelo core sem expor compilação, renderer ou
aplicação raw automática.

UI orientada por permissão diferencia negação de ação desconhecida com
`sdk.permissions.check`; `sdk.permissions.can` continua como atalho booleano.
Integrações opcionais descobrem apenas metadados públicos de packages ativos
com `sdk.packages.get` e `sdk.packages.has`.

Annotations suportam `sdk.pdf.annotations.update` e
`sdk.pdf.annotations.delete`, além de list/create.
- `sdk.actors.patchData`; `sdk.actors.items.slots`, `sdk.actors.items.listCopies`, `sdk.actors.items.insertCopy`, `sdk.actors.items.removeCopy`; `sdk.combat.setInitiative`, `sdk.combat.moveCombatant`, `sdk.combat.setInitiativeOrder`.

Updates aceitam `expectedVersion` onde documentado; divergência retorna `STALE_VERSION`. Actions registradas contêm no máximo 16 operações semânticas allow-listed; callers não enviam grafos. Nenhum acesso bruto a banco, transporte, renderer, filesystem ou DOM do core é exposto.

Dados de ficha de item são atualizados com `sdk.items.patchData`. O gerenciamento
de combate também fornece `sdk.combat.advanceRound`, `sdk.combat.setFlags` e
`sdk.combat.rollInitiative`.

## Referências universais de conteúdo

Pacotes com `content.references` criam uma URI canônica com `sdk.content.ref`,
resolvem com `sdk.content.resolve`, obtêm o valor público autorizado com
`sdk.content.get` e consultam acesso com `sdk.content.can`. `sdk.content.open`
solicita ao host a abertura do alvo e `sdk.content.link` cria um link portável.
A resolução ocorre no servidor e não atravessa a campanha ativa.
`sdk.content.search` pesquisa o índice autorizado da campanha por texto e tipo.
Retorna `{ entries, nextCursor }`; passe `nextCursor` como `options.cursor` para
continuar. O cursor é opaco, os resultados continuam filtrados por permissão e
cada página é limitada a 100 entradas.

`sdk.actors.data(actorId)` retorna `{ actor_id, version, data }` depois das
mesmas verificações de visibilidade da ficha. Atores ocultos e inexistentes
retornam `NOT_FOUND`. Alterações da ficha emitem `actor.data.updated`.

Os eventos públicos incluem `journal.created`, `journal.updated`,
`journal.deleted`, `cards.state.changed`, `scene.fog.changed` e
`scene.images.changed`. A audiência de journals respeita sua visibilidade,
inclusive na exclusão.

## Aplicações parciais e configurações por escopo

Pacotes com `ui.applications` usam `sdk.ui.applications.register`,
`sdk.ui.applications.render` e `sdk.ui.applications.close`. A renderização pode
nomear apenas as partes alteradas e preservar DOM, foco e scroll não afetados.

As configurações expõem `sdk.settings.scope` e `sdk.settings.onChange`. Os
escopos são `client`, `user`, `campaign` e `package`; `global` permanece como
alias legado de `package`.

## Zonas de cena e interações direcionadas

Regiões semânticas usam `sdk.scene.zones.list`, `sdk.scene.zones.get`, `sdk.scene.zones.members`, `sdk.scene.zones.create`, `sdk.scene.zones.update` e `sdk.scene.zones.delete`. Decisões direcionadas usam `sdk.interactions.request`, `sdk.interactions.get`, `sdk.interactions.list`, `sdk.interactions.respond` e `sdk.interactions.cancel`.

## Scene world objects e semantic presentations

Packages registram tipos limitados com `sdk.scene.objectTypes.register`. Instances autoritativas usam `sdk.scene.objects.list`, `sdk.scene.objects.get`, `sdk.scene.objects.hitTest`, `sdk.scene.objects.create`, `sdk.scene.objects.update`, `sdk.scene.objects.delete` e `sdk.scene.objects.interact`. Projeções temporárias core-owned usam `sdk.ui.presentations.show`, `sdk.ui.presentations.get`, `sdk.ui.presentations.list`, `sdk.ui.presentations.wait`, `sdk.ui.presentations.update` e `sdk.ui.presentations.close`.

## Ponteiro, áudio, navegação e input

Use `sdk.ui.dragDrop.registerSource`, `sdk.ui.dragDrop.registerTarget`, `sdk.ui.dragDrop.sources`, `sdk.ui.dragDrop.targets`, `sdk.ui.dragDrop.drop`, `sdk.audio.play`, `sdk.audio.get`, `sdk.audio.list`, `sdk.audio.update`, `sdk.audio.stop`, `sdk.navigation.scene.go`, `sdk.navigation.scene.getState`, `sdk.input.commands.register`, `sdk.input.commands.list`, `sdk.input.commands.execute`, `sdk.input.bindings.get`, `sdk.input.bindings.set` e `sdk.input.gestures.register`.

## Composição durável

Workflows limitados usam `sdk.workflows.register`, `sdk.workflows.start`,
`sdk.workflows.get`, `sdk.workflows.list` e `sdk.workflows.cancel`. Turnos e fases
autoritativos usam `sdk.gameplay.flows.register`, `sdk.gameplay.flows.start`,
`sdk.gameplay.flows.get`, `sdk.gameplay.flows.list`,
`sdk.gameplay.flows.advance` e `sdk.gameplay.flows.submit`. Tokens mantêm a
identidade entre Scenes com `sdk.tokens.transfer` ou com a operação atômica
`sdk.tokens.transferMany`; navegação continua separada. Timelines semânticas
usam `sdk.timelines.register`, `sdk.timelines.start`, `sdk.timelines.get`,
`sdk.timelines.list` e `sdk.timelines.cancel`.

Um passo `INTERACTION` pode declarar um `resultKey` opcional. Quando a interação
termina, o core grava o *valor* da resposta do único destinatário — nunca o objeto da
interação — em `context[resultKey]`, que o passo `BRANCH` já existente consome sem
mudança. A chave deve ser um identificador local do workflow e não pode ocupar os
slots do runtime `input`, `lastResult` ou `interaction`. Como um branch escalar não
representa divergência, `resultKey` só é válido em requisições com exatamente um
destinatário. Cancelamento, expiração e falha do provider deixam a chave ausente em
vez de inventar uma resposta, então uma definição que precisa tratar recusa faz o
branch sobre a chave ausente. O valor vem sempre do estado autoritativo do servidor;
o pacote não pode fornecê-lo nem sobrescrevê-lo.

## Quadro de membros e controle de Token

`sdk.campaign.members()` retorna o quadro de membros da campanha como
`{ userId, role, name }`, a mesma associação que a mesa nativa já mostra a quem
chama. Não traz metadados de conta, é restrito à campanha ativa e só responde a quem
já é membro. É um quadro de membros, não um feed de presença: associação não é status
online.

`TokenDTO.controllers` informa os usuários que podem controlar aquele Token, derivado
da mesma autoridade que decide se um movimento é permitido, então um Token com vários
donos lista todos em vez de reduzir a um. A projeção é filtrada: quem chama vê
controladores apenas dos Tokens que ele próprio poderia controlar, o que impede que um
tabuleiro compartilhado vire um canal lateral de enumeração. Conhecer o id de um
controlador não concede nada — toda operação continua derivando o principal da sessão
autenticada.

Juntos, permitem reagir a `zone.entered`: ler o Token, pegar os controladores
autorizados e endereçar uma Interação Dirigida a um participante real.

## Sons nativos e Sons espaciais

Conteúdo sonoro semântico reutilizável é um recurso de campanha de primeira
classe, distinto da reprodução em runtime. A biblioteca de Sons usa
`sdk.sounds.list`, `sdk.sounds.get`, `sdk.sounds.create`, `sdk.sounds.update` e
`sdk.sounds.delete`; a criação referencia um Asset canônico `audio` autorizado
(`{ kind: "library-asset", id }`) ou um recurso de áudio distribuído pelo pacote
(`{ kind: "package-asset", id }`), que o servidor canoniza pelo mesmo pipeline
seguro de ingestão antes de o Som existir. Excluir um Som ainda referenciado por
Playlist, Soundscape ou Som espacial falha pela política nativa de dependência,
em vez de deixar uma referência quebrada.

Emissores persistentes de Scene usam `sdk.scene.spatialSounds.list`,
`sdk.scene.spatialSounds.get`, `sdk.scene.spatialSounds.create`,
`sdk.scene.spatialSounds.update` e `sdk.scene.spatialSounds.delete`. O emissor
referencia o Som por `soundId`; URLs de Asset e caminhos de arquivo nunca são
aceitos como identidade do emissor. Com `constrainedByWalls`, a geometria de
Paredes e Portas atenua o emissor como projeção, então abrir ou fechar uma Porta
muda o que os ouvintes escutam sem reiniciar a reprodução.

A fronteira é deliberada: `sdk.sounds.*` cuida do conteúdo persistente
reutilizável, `sdk.audio.*` cuida da reprodução e do controle em runtime, e
`sdk.scene.spatialSounds.*` cuida dos emissores espaciais persistentes da Scene.

## Shortcuts

| Atalho | Equivalente |
|---|---|
| `sdk.toast(message, options)` | `sdk.ui.toast(message, options)` |
| `sdk.setting(key)` | `sdk.settings.get(key)` |
| `sdk.setting(key, value)` | `sdk.settings.set(key, value)` |
