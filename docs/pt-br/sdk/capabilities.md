# Capabilities

Um pacote declara as capabilities que precisa no `manifest.json`. O Gravewright valida as capabilities declaradas contra uma allow-list e rejeita capabilities proibidas. A SDK do navegador aplica gates aos métodos em runtime.

Se um pacote chama um método com gate sem declarar a capability exigida, o método lança um erro acionável:

```text
Package "x" attempted to use sdk.chat.send but does not declare capability "chat.cards".
```

## Allowed capabilities

<!-- BEGIN GENERATED: allowed-capabilities -->
| Capability | Finalidade |
|---|---|
| `actors.data.write` | Altera dados validados de fichas de ator que o usuário atual pode editar. |
| `actors.read` | Lê snapshots de atores visíveis. |
| `actors.register` | Registra comportamento/dados de tipos de ator via metadados do pacote. |
| `actors.write` | Cria, atualiza e exclui atores por comandos semânticos. |
| `assets.audio` | Fornece assets de áudio. |
| `assets.icons` | Fornece assets de ícone. |
| `assets.images` | Fornece assets de imagem. |
| `assets.library` | Lê a biblioteca de assets da campanha: lista os arquivos enviados (imagens e PDFs) que o membro pode ver. |
| `assets.maps` | Fornece assets de mapa. |
| `assets.pack` | Fornece asset packs. |
| `assets.scripts` | Carrega JavaScript confiável do pacote. |
| `assets.styles` | Carrega CSS do pacote. |
| `assets.ui` | Usa métodos de UI como toasts e modais. |
| `assets.video` | Fornece assets de vídeo. |
| `bus.provide` | Provê um método no bus de interop da SDK que outros pacotes podem requisitar. |
| `bus.publish` | Publica eventos no bus de interop da SDK. |
| `bus.request` | Solicita um valor a um provider do bus de interop da SDK. |
| `bus.subscribe` | Assina eventos do bus de interop da SDK. |
| `cards.manage` | Embaralha, reinicia, compra, revela, descarta e joga cartas por serviços autoritativos. |
| `cards.read` | Lê decks, pilhas, cartas e posicionamentos filtrados por permissão. |
| `chat.cards` | Envia cards/mensagens de chat via `sdk.chat`. |
| `chat.read` | Lê mensagens de chat visíveis ao usuário atual. |
| `combat.config` | Declara como a iniciativa é rolada e quais recursos o combate lê. |
| `combat.manage` | Gerencia o estado autoritativo de combate. |
| `combat.read` | Lê o snapshot autoritativo de combate. |
| `combat.runtime` | Usa métodos de runtime `sdk.combat.*` e registro de painel. |
| `commands.register` | Registra comandos de cliente. |
| `content.index` | Pesquisa um índice de conteúdo da campanha filtrado por permissão. |
| `content.packs` | Fornece e lê content packs. |
| `content.references` | Resolve e abre referências universais de conteúdo filtradas por permissão. |
| `dice.roll` | Pede rolagens autoritativas no servidor via `sdk.dice`. |
| `events.subscribe` | Assina eventos semânticos do jogo filtrados por permissão. |
| `handouts.present` | Apresenta conteúdo autorizado sem conceder acesso persistente. |
| `items.data.write` | Altera dados validados de fichas de item que o usuário atual pode editar. |
| `items.read` | Lê snapshots de itens visíveis. |
| `items.register` | Registra comportamento/dados de tipos de item via metadados do pacote. |
| `items.write` | Cria, atualiza e exclui itens por comandos semânticos. |
| `journals.read` | Lê journals e handouts visíveis ao usuário atual. |
| `journals.write` | Cria, atualiza e exclui journals validados. |
| `locales` | Fornece locales e usa `sdk.i18n.t`. |
| `pdf.annotations.read` | Lê anotações de documentos PDF visíveis. |
| `pdf.annotations.write` | Cria, atualiza e exclui anotações validadas em documentos PDF visíveis. |
| `pdf.read` | Lê documentos PDF visíveis ao usuário atual e seus metadados. |
| `pdf.viewer` | Abre e navega documentos PDF no visualizador do host. |
| `permissions.inspect` | Consulta decisões de permissão efetivas do usuário atual. |
| `rolls.intent` | Pede intents declarativas de rolagem/action no servidor. |
| `rules.actions` | Executa grafos declarativos limitados de forma autoritativa. |
| `rules.declarative` | Fornece documentos de regras declarativos. |
| `rules.extends` | Estende o comportamento das regras. |
| `scene.effects.read` | Lê efeitos semânticos de cena. |
| `scene.effects.write` | Gerencia efeitos semânticos de cena. |
| `scene.fog.read` | Lê o estado lógico do fog sem expor o renderer. |
| `scene.fog.write` | Gerencia fog por operações autoritativas limitadas. |
| `scene.geometry.read` | Lê paredes, portas e luzes lógicas. |
| `scene.geometry.write` | Gerencia paredes, portas e luzes lógicas. |
| `scene.images.read` | Lê colocações de imagens filtradas por permissão. |
| `scene.images.write` | Coloca, atualiza e remove imagens de cena autorizadas. |
| `scene.overlays` | Fornece overlays de cena. |
| `scene.read` | Lê snapshots de cenas visíveis. |
| `scene.tools` | Usa métodos de cena/ferramenta como `sdk.scene.*` e `sdk.tools.*`. |
| `settings` | Define e usa settings do pacote. |
| `sheets.components` | Fornece componentes de ficha. |
| `sheets.controller` | Anexa um script controller a uma ficha HTML. |
| `sheets.declarative` | Fornece layouts de ficha declarativos. |
| `sheets.html` | Fornece fichas de ator/item em modo HTML. |
| `sheets.richText` | Renderiza rich text sanitizado em uma ficha HTML. |
| `sheets.runtime` | Usa métodos de runtime `sdk.sheets.*`. |
| `storage.sqlite` | Usa storage SQLite gerenciado pelo Gravewright, escopado ao pacote. |
| `tokens.extends` | Usa métodos de extensão de token como `sdk.tokens.centerOn`. |
| `tokens.manage` | Cria, atualiza e exclui tokens de forma autoritativa. |
| `tokens.mappings` | Fornece mapeamentos de token. |
| `tokens.move` | Move tokens controlados de forma autoritativa. |
| `tokens.read` | Lê snapshots de tokens visíveis. |
| `ui.applications` | Renderiza aplicações do pacote incrementalmente por partes nomeadas. |
| `ui.slots` | Monta UI do pacote em slots documentados do host. |
<!-- END GENERATED -->

> Gerado a partir de `KNOWN_CAPABILITIES` em `app/engine/sdk/package_manifest_validator.py` e `docs/pt-br/sdk/_data/capability-descriptions.json`. Não edite à mão: rode `uv run python scripts/generate_sdk_reference.py`.

## Forbidden capabilities

Estas são sempre rejeitadas:

<!-- BEGIN GENERATED: forbidden-capabilities -->
```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```
<!-- END GENERATED -->

Não há execução de plugin de backend no SDK v1. Pacotes são declarativos mais código de runtime do navegador. O servidor permanece autoritativo para estado de jogo, permissões, persistência e validação.

## Runtime method gates

<!-- BEGIN GENERATED: method-gates -->
| Método do SDK | Capability exigida |
|---|---|
| `sdk.actors.create` | `actors.write` |
| `sdk.actors.delete` | `actors.write` |
| `sdk.actors.get` | `actors.read` |
| `sdk.actors.list` | `actors.read` |
| `sdk.actors.patchData` | `actors.data.write` |
| `sdk.actors.update` | `actors.write` |
| `sdk.assets.list` | `assets.library` |
| `sdk.bus.provide` | `bus.provide` |
| `sdk.bus.publish` | `bus.publish` |
| `sdk.bus.request` | `bus.request` |
| `sdk.bus.subscribe` | `bus.subscribe` |
| `sdk.cards.discard` | `cards.manage` |
| `sdk.cards.discardPlacement` | `cards.manage` |
| `sdk.cards.draw` | `cards.manage` |
| `sdk.cards.play` | `cards.manage` |
| `sdk.cards.reset` | `cards.manage` |
| `sdk.cards.reveal` | `cards.manage` |
| `sdk.cards.shuffle` | `cards.manage` |
| `sdk.cards.state` | `cards.read` |
| `sdk.cards.updatePlacement` | `cards.manage` |
| `sdk.chat.get` | `chat.read` |
| `sdk.chat.list` | `chat.read` |
| `sdk.chat.send` | `chat.cards` |
| `sdk.combat.add` | `combat.manage` |
| `sdk.combat.advance` | `combat.manage` |
| `sdk.combat.advanceRound` | `combat.manage` |
| `sdk.combat.combatants` | `combat.read` |
| `sdk.combat.current` | `combat.read` |
| `sdk.combat.dispatch` | `combat.runtime` |
| `sdk.combat.end` | `combat.manage` |
| `sdk.combat.moveCombatant` | `combat.manage` |
| `sdk.combat.register` | `combat.runtime` |
| `sdk.combat.registerPanel` | `combat.runtime` |
| `sdk.combat.remove` | `combat.manage` |
| `sdk.combat.renderSlot` | `combat.runtime` |
| `sdk.combat.rollInitiative` | `combat.manage` |
| `sdk.combat.setFlags` | `combat.manage` |
| `sdk.combat.setInitiative` | `combat.manage` |
| `sdk.combat.setInitiativeOrder` | `combat.manage` |
| `sdk.combat.setTurn` | `combat.manage` |
| `sdk.combat.start` | `combat.manage` |
| `sdk.commands.register` | `commands.register` |
| `sdk.content.can` | `content.references` |
| `sdk.content.get` | `content.references` |
| `sdk.content.link` | `content.references` |
| `sdk.content.open` | `content.references` |
| `sdk.content.pack` | `content.packs` |
| `sdk.content.packs` | `content.packs` |
| `sdk.content.ref` | `content.references` |
| `sdk.content.resolve` | `content.references` |
| `sdk.content.search` | `content.index` |
| `sdk.dice.roll` | `dice.roll` |
| `sdk.events.available` | `events.subscribe` |
| `sdk.events.on` | `events.subscribe` |
| `sdk.events.once` | `events.subscribe` |
| `sdk.handouts.present` | `handouts.present` |
| `sdk.i18n.t` | `locales` |
| `sdk.items.create` | `items.write` |
| `sdk.items.delete` | `items.write` |
| `sdk.items.get` | `items.read` |
| `sdk.items.list` | `items.read` |
| `sdk.items.patchData` | `items.data.write` |
| `sdk.items.update` | `items.write` |
| `sdk.journals.create` | `journals.write` |
| `sdk.journals.delete` | `journals.write` |
| `sdk.journals.get` | `journals.read` |
| `sdk.journals.list` | `journals.read` |
| `sdk.journals.update` | `journals.write` |
| `sdk.pdf.annotations.create` | `pdf.annotations.write` |
| `sdk.pdf.annotations.delete` | `pdf.annotations.write` |
| `sdk.pdf.annotations.list` | `pdf.annotations.read` |
| `sdk.pdf.annotations.update` | `pdf.annotations.write` |
| `sdk.pdf.get` | `pdf.read` |
| `sdk.pdf.metadata` | `pdf.read` |
| `sdk.pdf.viewer.currentPage` | `pdf.viewer` |
| `sdk.pdf.viewer.goToPage` | `pdf.viewer` |
| `sdk.pdf.viewer.open` | `pdf.viewer` |
| `sdk.pdf.viewer.search` | `pdf.viewer` |
| `sdk.permissions.can` | `permissions.inspect` |
| `sdk.rolls.intent` | `rolls.intent` |
| `sdk.rules.actions.execute` | `rules.actions` |
| `sdk.rules.actions.validate` | `rules.actions` |
| `sdk.scene.active` | `scene.read` |
| `sdk.scene.activeCameraForScene` | `scene.tools` |
| `sdk.scene.activeCanvas` | `scene.tools` |
| `sdk.scene.effects.create` | `scene.effects.write` |
| `sdk.scene.effects.delete` | `scene.effects.write` |
| `sdk.scene.effects.list` | `scene.effects.read` |
| `sdk.scene.effects.update` | `scene.effects.write` |
| `sdk.scene.fog.disable` | `scene.fog.write` |
| `sdk.scene.fog.enable` | `scene.fog.write` |
| `sdk.scene.fog.paint` | `scene.fog.write` |
| `sdk.scene.fog.reset` | `scene.fog.write` |
| `sdk.scene.fog.state` | `scene.fog.read` |
| `sdk.scene.geometry.createLight` | `scene.geometry.write` |
| `sdk.scene.geometry.createWall` | `scene.geometry.write` |
| `sdk.scene.geometry.deleteLight` | `scene.geometry.write` |
| `sdk.scene.geometry.deleteWall` | `scene.geometry.write` |
| `sdk.scene.geometry.deleteWalls` | `scene.geometry.write` |
| `sdk.scene.geometry.lights` | `scene.geometry.read` |
| `sdk.scene.geometry.moveWallNode` | `scene.geometry.write` |
| `sdk.scene.geometry.moveWalls` | `scene.geometry.write` |
| `sdk.scene.geometry.setDoorState` | `scene.geometry.write` |
| `sdk.scene.geometry.splitWall` | `scene.geometry.write` |
| `sdk.scene.geometry.updateLight` | `scene.geometry.write` |
| `sdk.scene.geometry.updateWall` | `scene.geometry.write` |
| `sdk.scene.geometry.walls` | `scene.geometry.read` |
| `sdk.scene.get` | `scene.read` |
| `sdk.scene.images.delete` | `scene.images.write` |
| `sdk.scene.images.list` | `scene.images.read` |
| `sdk.scene.images.place` | `scene.images.write` |
| `sdk.scene.images.update` | `scene.images.write` |
| `sdk.scene.list` | `scene.read` |
| `sdk.settings.all` | `settings` |
| `sdk.settings.definitions` | `settings` |
| `sdk.settings.get` | `settings` |
| `sdk.settings.onChange` | `settings` |
| `sdk.settings.scope` | `settings` |
| `sdk.settings.set` | `settings` |
| `sdk.sheets.helpers` | `sheets.runtime` |
| `sdk.sheets.register` | `sheets.runtime` |
| `sdk.sheets.registerController` | `sheets.controller` |
| `sdk.storage.sqlite.execute` | `storage.sqlite` |
| `sdk.storage.sqlite.query` | `storage.sqlite` |
| `sdk.storage.sqlite.status` | `storage.sqlite` |
| `sdk.tokens.centerOn` | `tokens.extends` |
| `sdk.tokens.create` | `tokens.manage` |
| `sdk.tokens.delete` | `tokens.manage` |
| `sdk.tokens.get` | `tokens.read` |
| `sdk.tokens.list` | `tokens.read` |
| `sdk.tokens.move` | `tokens.move` |
| `sdk.tokens.update` | `tokens.manage` |
| `sdk.tools.activeTool` | `scene.tools` |
| `sdk.ui.applications.close` | `ui.applications` |
| `sdk.ui.applications.register` | `ui.applications` |
| `sdk.ui.applications.render` | `ui.applications` |
| `sdk.ui.closeModal` | `assets.ui` |
| `sdk.ui.openModal` | `assets.ui` |
| `sdk.ui.slots.available` | `ui.slots` |
| `sdk.ui.slots.register` | `ui.slots` |
| `sdk.ui.toast` | `assets.ui` |
<!-- END GENERATED -->

> Gerado a partir de `CAPABILITY_REQUIREMENTS` em `static/js/sdk/sdk-capabilities.js`. Não edite à mão: rode `uv run python scripts/generate_sdk_reference.py`.

## Review guidance

Solicite o menor conjunto de capabilities possível.

- Não declare `assets.scripts` a menos que o pacote realmente precise de código confiável no navegador.
- Não declare `assets.ui` para themes que são só CSS.
- Não declare `settings` a menos que o pacote defina ou leia settings.
- Prefira dados declarativos de pacote a scripting de runtime quando possível.
