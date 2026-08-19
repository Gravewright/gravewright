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
| `actors.items.read` | Descobre slots e snapshots locais de Item declarados pelo ruleset. |
| `actors.items.write` | Insere e remove snapshots locais de Item por slots declarados. |
| `actors.read` | Lê snapshots de atores visíveis. |
| `actors.register` | Registra comportamento/dados de tipos de ator via metadados do pacote. |
| `actors.write` | Cria, atualiza e exclui atores por comandos semânticos. |
| `assets.audio` | Fornece assets de áudio. |
| `assets.icons` | Fornece assets de ícone. |
| `assets.images` | Fornece assets de imagem. |
| `assets.import` | Ingere um arquivo selecionado pelo usuário como asset validado da campanha, sem acesso ao filesystem. |
| `assets.library` | Lê a biblioteca de assets da campanha: lista os arquivos enviados (imagens e PDFs) que o membro pode ver. |
| `assets.maps` | Fornece assets de mapa. |
| `assets.pack` | Fornece asset packs. |
| `assets.scripts` | Carrega JavaScript confiável do pacote. |
| `assets.styles` | Carrega CSS do pacote. |
| `assets.ui` | Usa métodos de UI como toasts e modais. |
| `assets.video` | Fornece assets de vídeo. |
| `audio.playback` | Controla playbacks semânticos pertencentes ao core de primeira classe. |
| `automation.schedule` | Agenda registered actions durable-safe sob autoridade revalidada na execução. |
| `bus.provide` | Provê um método no bus de interop da SDK que outros pacotes podem requisitar. |
| `bus.publish` | Publica eventos no bus de interop da SDK. |
| `bus.request` | Solicita um valor a um provider do bus de interop da SDK. |
| `bus.subscribe` | Assina eventos do bus de interop da SDK. |
| `campaign.members.read` | Ler o quadro de membros da campanha (id, papel e nome de exibicao) para orquestracao e selecao de participantes. |
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
| `gameplay.flows.manage` | Registra, inicia e avança gameplay flows limitados. |
| `gameplay.flows.participate` | Envia escolhas tipadas como participante autorizado do flow. |
| `gameplay.flows.read` | Lê estado autoritativo de gameplay flows filtrado por audience. |
| `handouts.present` | Apresenta conteúdo autorizado sem conceder acesso persistente. |
| `input.commands` | Registra commands e gestures semânticos com bindings de usuário sem conflitos. |
| `interactions.request` | Solicita e cancela decisões limitadas pertencentes ao servidor para recipients explícitos. |
| `interactions.respond` | Descobre e responde interações direcionadas como o usuário autenticado. |
| `items.data.write` | Altera dados validados de fichas de item que o usuário atual pode editar. |
| `items.read` | Lê snapshots de itens visíveis. |
| `items.register` | Registra comportamento/dados de tipos de item via metadados do pacote. |
| `items.write` | Cria, atualiza e exclui itens por comandos semânticos. |
| `journals.read` | Lê journals e handouts visíveis ao usuário atual. |
| `journals.write` | Cria, atualiza e exclui journals validados. |
| `locales` | Fornece locales e usa `sdk.i18n.t`. |
| `navigation.scene` | Muda o contexto persistido da Scene vista por usuários autorizados sem mover tokens. |
| `packages.inspect` | Descobre metadados públicos e contratos de interoperabilidade de packages ativos na campanha atual. |
| `pdf.annotations.read` | Lê anotações de documentos PDF visíveis. |
| `pdf.annotations.write` | Cria, atualiza e exclui anotações validadas em documentos PDF visíveis. |
| `pdf.presentation` | Coordena apresentação PDF versionada sem conceder acesso ao documento. |
| `pdf.read` | Lê documentos PDF visíveis ao usuário atual e seus metadados. |
| `pdf.viewer` | Abre e navega documentos PDF no visualizador do host. |
| `permissions.inspect` | Consulta decisões de permissão efetivas do usuário atual. |
| `rolls.intent` | Pede intents declarativas de rolagem/action no servidor. |
| `rules.actions` | Descobre e executa ações semânticas versionadas declaradas por pacotes. |
| `rules.declarative` | Fornece documentos de regras declarativos. |
| `rules.extends` | Estende o comportamento das regras. |
| `scene.effects.read` | Lê efeitos semânticos de cena. |
| `scene.effects.write` | Gerencia efeitos semânticos de cena. |
| `scene.fog.read` | Lê o estado lógico do fog sem expor o renderer. |
| `scene.fog.write` | Gerencia fog por operações autoritativas limitadas. |
| `scene.geometry.read` | Lê walls, doors, canais semânticos e lights filtrados por audiência sem expor o renderer. |
| `scene.geometry.write` | Gerencia walls, doors, canais semânticos fechados, apresentação de discovery e lights. |
| `scene.images.read` | Lê colocações de imagens filtradas por permissão. |
| `scene.images.write` | Coloca, atualiza e remove imagens de cena autorizadas. |
| `scene.measurements.shared` | Compartilha measurements com TTL e audience explícita. |
| `scene.objectTypes.register` | Registra tipos declarativos limitados de world object para o pacote ativo. |
| `scene.objects.interact` | Envia intents semânticos autorizados para world objects visíveis. |
| `scene.objects.read` | Lê e executa hit-test core-owned em world objects filtrados por audience. |
| `scene.objects.write` | Cria, atualiza, move e remove world objects autoritativos da cena. |
| `scene.overlays` | Fornece overlays de cena. |
| `scene.read` | Lê snapshots de cenas visíveis. |
| `scene.shaders.customLibrary` | Integra uma biblioteca de custom shaders do pacote ao editor e placement trusted do core. |
| `scene.shaders.read` | Descobre presets semânticos de shader e lê instâncias sem expor o renderer. |
| `scene.shaders.write` | Aplica e gerencia presets semânticos validados sem authority de GLSL raw. |
| `scene.spatialSounds.read` | Lê configurações autorizadas de Spatial Sounds nativos e persistentes de uma Cena. |
| `scene.spatialSounds.write` | Cria, atualiza e exclui Spatial Sounds nativos e persistentes com autoridade de Cena e CAS. |
| `scene.templates.read` | Lê templates persistentes de gameplay em world-space filtrados por permissão. |
| `scene.templates.write` | Cria, atualiza e remove templates persistentes de gameplay com geometria limitada. |
| `scene.tools` | Usa métodos de cena/ferramenta como `sdk.scene.*` e `sdk.tools.*`. |
| `scene.zones.read` | Lê zonas semânticas visíveis e membership observável de tokens. |
| `scene.zones.write` | Cria, atualiza e remove zonas semânticas versionadas pertencentes à campanha. |
| `settings` | Define e usa settings do pacote. |
| `sheets.components` | Fornece componentes de ficha. |
| `sheets.controller` | Anexa um script controller a uma ficha HTML. |
| `sheets.declarative` | Fornece layouts de ficha declarativos. |
| `sheets.html` | Fornece fichas de ator/item em modo HTML. |
| `sheets.richText` | Renderiza rich text sanitizado em uma ficha HTML. |
| `sheets.runtime` | Usa métodos de runtime `sdk.sheets.*`. |
| `sounds.read` | Lê recursos reutilizáveis de Sound nativo na campanha ativa. |
| `sounds.write` | Cria, atualiza e exclui com segurança recursos reutilizáveis de Sound nativo a partir de Assets de áudio autorizados. |
| `storage.sqlite` | Usa storage SQLite gerenciado pelo Gravewright, escopado ao pacote. |
| `timelines.control` | Cancela cues futuros de uma timeline semântica autorizada. |
| `timelines.read` | Lê timelines semânticas autorizadas temporizadas pelo core. |
| `timelines.start` | Registra e inicia timelines semânticas limitadas. |
| `tokens.extends` | Usa métodos de extensão de token como `sdk.tokens.centerOn`. |
| `tokens.manage` | Cria, atualiza e exclui tokens de forma autoritativa. |
| `tokens.mappings` | Fornece mapeamentos de token. |
| `tokens.move` | Move tokens controlados de forma autoritativa. |
| `tokens.read` | Lê snapshots de tokens visíveis. |
| `tokens.targets` | Gerencia o conjunto privado de targets do usuário atual por cena. |
| `tokens.transfer` | Transfere atomicamente identidades estáveis de tokens entre Scenes autorizadas. |
| `ui.applications` | Renderiza aplicações do pacote incrementalmente por partes nomeadas. |
| `ui.dragDrop` | Registra sources tipados e destinations concretas revalidadas por autoridade. |
| `ui.presentations` | Mostra presentations efêmeras limitadas e renderizadas pelo core para audiences autorizadas. |
| `ui.slots` | Monta UI do pacote em slots documentados do host. |
| `workflows.control` | Cancela workflows autorizados sem rollback implícito. |
| `workflows.read` | Lê instâncias autorizadas de workflows duráveis. |
| `workflows.start` | Registra definições limitadas e inicia workflows duráveis pertencentes ao core. |
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
| `sdk.actors.data` | `actors.read` |
| `sdk.actors.delete` | `actors.write` |
| `sdk.actors.get` | `actors.read` |
| `sdk.actors.items.insertCopy` | `actors.items.write` |
| `sdk.actors.items.listCopies` | `actors.items.read` |
| `sdk.actors.items.removeCopy` | `actors.items.write` |
| `sdk.actors.items.slots` | `actors.items.read` |
| `sdk.actors.list` | `actors.read` |
| `sdk.actors.patchData` | `actors.data.write` |
| `sdk.actors.update` | `actors.write` |
| `sdk.assets.cancelImport` | `assets.import` |
| `sdk.assets.ingest` | `assets.import` |
| `sdk.assets.list` | `assets.library` |
| `sdk.audio.get` | `audio.playback` |
| `sdk.audio.list` | `audio.playback` |
| `sdk.audio.play` | `audio.playback` |
| `sdk.audio.stop` | `audio.playback` |
| `sdk.audio.update` | `audio.playback` |
| `sdk.automation.audit` | `automation.schedule` |
| `sdk.automation.cancel` | `automation.schedule` |
| `sdk.automation.get` | `automation.schedule` |
| `sdk.automation.list` | `automation.schedule` |
| `sdk.automation.schedule` | `automation.schedule` |
| `sdk.bus.provide` | `bus.provide` |
| `sdk.bus.publish` | `bus.publish` |
| `sdk.bus.request` | `bus.request` |
| `sdk.bus.subscribe` | `bus.subscribe` |
| `sdk.campaign.members` | `campaign.members.read` |
| `sdk.cards.definitions.get` | `cards.read` |
| `sdk.cards.definitions.instantiate` | `cards.manage` |
| `sdk.cards.definitions.list` | `cards.read` |
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
| `sdk.gameplay.flows.advance` | `gameplay.flows.manage` |
| `sdk.gameplay.flows.get` | `gameplay.flows.read` |
| `sdk.gameplay.flows.list` | `gameplay.flows.read` |
| `sdk.gameplay.flows.register` | `gameplay.flows.manage` |
| `sdk.gameplay.flows.start` | `gameplay.flows.manage` |
| `sdk.gameplay.flows.submit` | `gameplay.flows.participate` |
| `sdk.handouts.present` | `handouts.present` |
| `sdk.i18n.t` | `locales` |
| `sdk.input.bindings.get` | `input.commands` |
| `sdk.input.bindings.set` | `input.commands` |
| `sdk.input.commands.execute` | `input.commands` |
| `sdk.input.commands.list` | `input.commands` |
| `sdk.input.commands.register` | `input.commands` |
| `sdk.input.gestures.register` | `input.commands` |
| `sdk.interactions.cancel` | `interactions.request` |
| `sdk.interactions.get` | `interactions.respond` |
| `sdk.interactions.list` | `interactions.respond` |
| `sdk.interactions.request` | `interactions.request` |
| `sdk.interactions.respond` | `interactions.respond` |
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
| `sdk.navigation.scene.getState` | `navigation.scene` |
| `sdk.navigation.scene.go` | `navigation.scene` |
| `sdk.packages.get` | `packages.inspect` |
| `sdk.packages.has` | `packages.inspect` |
| `sdk.pdf.annotations.create` | `pdf.annotations.write` |
| `sdk.pdf.annotations.delete` | `pdf.annotations.write` |
| `sdk.pdf.annotations.list` | `pdf.annotations.read` |
| `sdk.pdf.annotations.update` | `pdf.annotations.write` |
| `sdk.pdf.get` | `pdf.read` |
| `sdk.pdf.metadata` | `pdf.read` |
| `sdk.pdf.presentation.current` | `pdf.presentation` |
| `sdk.pdf.presentation.end` | `pdf.presentation` |
| `sdk.pdf.presentation.start` | `pdf.presentation` |
| `sdk.pdf.presentation.update` | `pdf.presentation` |
| `sdk.pdf.viewer.currentPage` | `pdf.viewer` |
| `sdk.pdf.viewer.goToPage` | `pdf.viewer` |
| `sdk.pdf.viewer.open` | `pdf.viewer` |
| `sdk.pdf.viewer.search` | `pdf.viewer` |
| `sdk.permissions.can` | `permissions.inspect` |
| `sdk.permissions.check` | `permissions.inspect` |
| `sdk.rolls.intent` | `rolls.intent` |
| `sdk.rules.actions.execute` | `rules.actions` |
| `sdk.rules.actions.executeReference` | `rules.actions` |
| `sdk.rules.actions.get` | `rules.actions` |
| `sdk.rules.actions.list` | `rules.actions` |
| `sdk.rules.actions.resolve` | `rules.actions` |
| `sdk.scene.active` | `scene.read` |
| `sdk.scene.activeCameraForScene` | `scene.tools` |
| `sdk.scene.activeCanvas` | `scene.tools` |
| `sdk.scene.effects.create` | `scene.effects.write` |
| `sdk.scene.effects.delete` | `scene.effects.write` |
| `sdk.scene.effects.list` | `scene.effects.read` |
| `sdk.scene.effects.presets` | `scene.effects.read` |
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
| `sdk.scene.measurements.cancel` | `scene.measurements.shared` |
| `sdk.scene.measurements.listShared` | `scene.measurements.shared` |
| `sdk.scene.measurements.measure` | `scene.tools` |
| `sdk.scene.measurements.share` | `scene.measurements.shared` |
| `sdk.scene.objectTypes.register` | `scene.objectTypes.register` |
| `sdk.scene.objects.create` | `scene.objects.write` |
| `sdk.scene.objects.delete` | `scene.objects.write` |
| `sdk.scene.objects.get` | `scene.objects.read` |
| `sdk.scene.objects.hitTest` | `scene.objects.read` |
| `sdk.scene.objects.interact` | `scene.objects.interact` |
| `sdk.scene.objects.list` | `scene.objects.read` |
| `sdk.scene.objects.update` | `scene.objects.write` |
| `sdk.scene.shaders.apply` | `scene.shaders.write` |
| `sdk.scene.shaders.customLibrary.clearPreview` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.openEditor` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.preview` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.registerProvider` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.use` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.enable` | `scene.shaders.write` |
| `sdk.scene.shaders.getPreset` | `scene.shaders.read` |
| `sdk.scene.shaders.list` | `scene.shaders.read` |
| `sdk.scene.shaders.presets` | `scene.shaders.read` |
| `sdk.scene.shaders.remove` | `scene.shaders.write` |
| `sdk.scene.shaders.update` | `scene.shaders.write` |
| `sdk.scene.spatialSounds.create` | `scene.spatialSounds.write` |
| `sdk.scene.spatialSounds.delete` | `scene.spatialSounds.write` |
| `sdk.scene.spatialSounds.get` | `scene.spatialSounds.read` |
| `sdk.scene.spatialSounds.list` | `scene.spatialSounds.read` |
| `sdk.scene.spatialSounds.update` | `scene.spatialSounds.write` |
| `sdk.scene.templates.create` | `scene.templates.write` |
| `sdk.scene.templates.delete` | `scene.templates.write` |
| `sdk.scene.templates.get` | `scene.templates.read` |
| `sdk.scene.templates.list` | `scene.templates.read` |
| `sdk.scene.templates.update` | `scene.templates.write` |
| `sdk.scene.zones.create` | `scene.zones.write` |
| `sdk.scene.zones.delete` | `scene.zones.write` |
| `sdk.scene.zones.get` | `scene.zones.read` |
| `sdk.scene.zones.list` | `scene.zones.read` |
| `sdk.scene.zones.members` | `scene.zones.read` |
| `sdk.scene.zones.update` | `scene.zones.write` |
| `sdk.settings.all` | `settings` |
| `sdk.settings.definitions` | `settings` |
| `sdk.settings.get` | `settings` |
| `sdk.settings.onChange` | `settings` |
| `sdk.settings.scope` | `settings` |
| `sdk.settings.set` | `settings` |
| `sdk.sheets.helpers` | `sheets.runtime` |
| `sdk.sheets.register` | `sheets.runtime` |
| `sdk.sheets.registerController` | `sheets.controller` |
| `sdk.sounds.create` | `sounds.write` |
| `sdk.sounds.delete` | `sounds.write` |
| `sdk.sounds.get` | `sounds.read` |
| `sdk.sounds.list` | `sounds.read` |
| `sdk.sounds.update` | `sounds.write` |
| `sdk.storage.sqlite.execute` | `storage.sqlite` |
| `sdk.storage.sqlite.query` | `storage.sqlite` |
| `sdk.storage.sqlite.status` | `storage.sqlite` |
| `sdk.timelines.cancel` | `timelines.control` |
| `sdk.timelines.get` | `timelines.read` |
| `sdk.timelines.list` | `timelines.read` |
| `sdk.timelines.register` | `timelines.start` |
| `sdk.timelines.start` | `timelines.start` |
| `sdk.tokens.centerOn` | `tokens.extends` |
| `sdk.tokens.create` | `tokens.manage` |
| `sdk.tokens.delete` | `tokens.manage` |
| `sdk.tokens.get` | `tokens.read` |
| `sdk.tokens.list` | `tokens.read` |
| `sdk.tokens.move` | `tokens.move` |
| `sdk.tokens.targets.clear` | `tokens.targets` |
| `sdk.tokens.targets.list` | `tokens.targets` |
| `sdk.tokens.targets.set` | `tokens.targets` |
| `sdk.tokens.transfer` | `tokens.transfer` |
| `sdk.tokens.transferMany` | `tokens.transfer` |
| `sdk.tokens.update` | `tokens.manage` |
| `sdk.tools.activeTool` | `scene.tools` |
| `sdk.tools.register` | `scene.tools` |
| `sdk.ui.applications.close` | `ui.applications` |
| `sdk.ui.applications.register` | `ui.applications` |
| `sdk.ui.applications.render` | `ui.applications` |
| `sdk.ui.closeModal` | `assets.ui` |
| `sdk.ui.dragDrop.drop` | `ui.dragDrop` |
| `sdk.ui.dragDrop.registerSource` | `ui.dragDrop` |
| `sdk.ui.dragDrop.registerTarget` | `ui.dragDrop` |
| `sdk.ui.dragDrop.sources` | `ui.dragDrop` |
| `sdk.ui.dragDrop.targets` | `ui.dragDrop` |
| `sdk.ui.openModal` | `assets.ui` |
| `sdk.ui.presentations.close` | `ui.presentations` |
| `sdk.ui.presentations.get` | `ui.presentations` |
| `sdk.ui.presentations.list` | `ui.presentations` |
| `sdk.ui.presentations.show` | `ui.presentations` |
| `sdk.ui.presentations.update` | `ui.presentations` |
| `sdk.ui.presentations.wait` | `ui.presentations` |
| `sdk.ui.slots.available` | `ui.slots` |
| `sdk.ui.slots.register` | `ui.slots` |
| `sdk.ui.toast` | `assets.ui` |
| `sdk.workflows.cancel` | `workflows.control` |
| `sdk.workflows.get` | `workflows.read` |
| `sdk.workflows.list` | `workflows.read` |
| `sdk.workflows.register` | `workflows.start` |
| `sdk.workflows.start` | `workflows.start` |
<!-- END GENERATED -->

> Gerado a partir de `CAPABILITY_REQUIREMENTS` em `static/js/sdk/sdk-capabilities.js`. Não edite à mão: rode `uv run python scripts/generate_sdk_reference.py`.

## Review guidance

Solicite o menor conjunto de capabilities possível.

- Não declare `assets.scripts` a menos que o pacote realmente precise de código confiável no navegador.
- Não declare `assets.ui` para themes que são só CSS.
- Não declare `settings` a menos que o pacote defina ou leia settings.
- Prefira dados declarativos de pacote a scripting de runtime quando possível.
