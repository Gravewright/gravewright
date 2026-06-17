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
| `actors.register` | Registra comportamento/dados de tipos de ator via metadados do pacote. |
| `assets.audio` | Fornece assets de áudio. |
| `assets.icons` | Fornece assets de ícone. |
| `assets.images` | Fornece assets de imagem. |
| `assets.maps` | Fornece assets de mapa. |
| `assets.pack` | Fornece asset packs. |
| `assets.scripts` | Carrega JavaScript confiável do pacote. |
| `assets.styles` | Carrega CSS do pacote. |
| `assets.ui` | Usa métodos de UI como toasts e modais. |
| `assets.video` | Fornece assets de video. |
| `bus.provide` | Prove um metodo no bus de interop da SDK que outros pacotes podem requisitar. |
| `bus.publish` | Publica eventos no bus de interop da SDK. |
| `bus.request` | Solicita um valor a um provider do bus de interop da SDK. |
| `bus.subscribe` | Assina eventos do bus de interop da SDK. |
| `chat.cards` | Envia cards/mensagens de chat via `sdk.chat`. |
| `combat.config` | Fornece configuração de combate. |
| `combat.runtime` | Usa métodos de runtime `sdk.combat.*` e registro de painel. |
| `commands.register` | Registra comandos de cliente. |
| `content.packs` | Fornece e lê content packs. |
| `dice.roll` | Participa do comportamento de rolagem de dados. |
| `items.register` | Registra comportamento/dados de tipos de item via metadados do pacote. |
| `locales` | Fornece locales e usa `sdk.i18n.t`. |
| `rolls.intent` | Envia ou mapeia intenções de rolagem. |
| `rules.declarative` | Fornece documentos de regras declarativos. |
| `rules.extends` | Estende o comportamento das regras. |
| `scene.overlays` | Fornece overlays de cena. |
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
| `tokens.mappings` | Fornece mapeamentos de token. |
<!-- END GENERATED -->

> Gerado a partir de `KNOWN_CAPABILITIES` em `app/engine/sdk/package_manifest_validator.py` e `docs/pt-br/sdk/_data/capability-descriptions.json`. Não edite à mão — rode `uv run python scripts/generate_sdk_reference.py`.

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
| `sdk.bus.provide` | `bus.provide` |
| `sdk.bus.publish` | `bus.publish` |
| `sdk.bus.request` | `bus.request` |
| `sdk.bus.subscribe` | `bus.subscribe` |
| `sdk.chat.send` | `chat.cards` |
| `sdk.combat.dispatch` | `combat.runtime` |
| `sdk.combat.register` | `combat.runtime` |
| `sdk.combat.registerPanel` | `combat.runtime` |
| `sdk.combat.renderSlot` | `combat.runtime` |
| `sdk.commands.register` | `commands.register` |
| `sdk.content.pack` | `content.packs` |
| `sdk.content.packs` | `content.packs` |
| `sdk.i18n.t` | `locales` |
| `sdk.scene.activeCameraForScene` | `scene.tools` |
| `sdk.scene.activeCanvas` | `scene.tools` |
| `sdk.settings.all` | `settings` |
| `sdk.settings.definitions` | `settings` |
| `sdk.settings.get` | `settings` |
| `sdk.settings.set` | `settings` |
| `sdk.sheets.helpers` | `sheets.runtime` |
| `sdk.sheets.register` | `sheets.runtime` |
| `sdk.sheets.registerController` | `sheets.controller` |
| `sdk.storage.sqlite.execute` | `storage.sqlite` |
| `sdk.storage.sqlite.query` | `storage.sqlite` |
| `sdk.storage.sqlite.status` | `storage.sqlite` |
| `sdk.tokens.centerOn` | `tokens.extends` |
| `sdk.tools.activeTool` | `scene.tools` |
| `sdk.ui.closeModal` | `assets.ui` |
| `sdk.ui.openModal` | `assets.ui` |
| `sdk.ui.toast` | `assets.ui` |
<!-- END GENERATED -->

> Gerado a partir de `CAPABILITY_REQUIREMENTS` em `static/js/sdk/sdk-capabilities.js`. Não edite à mão — rode `uv run python scripts/generate_sdk_reference.py`.

## Review guidance

Solicite o menor conjunto de capabilities possível.

- Não declare `assets.scripts` a menos que o pacote realmente precise de código confiável no navegador.
- Não declare `assets.ui` para themes que são só CSS.
- Não declare `settings` a menos que o pacote defina ou leia settings.
- Prefira dados declarativos de pacote a scripting de runtime quando possível.
