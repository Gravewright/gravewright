# Power map da SDK

Esta página mapeia objetivos do autor para o manifesto do pacote, capabilities, métodos de runtime da SDK e docs detalhados.

Use-a quando você sabe o que quer construir mas ainda não sabe qual superfície da SDK usar.

## Mapa central

| Objetivo do autor | Superfície do manifesto | Capability | Runtime SDK | Docs detalhados |
|---|---|---|---|---|
| Criar um ruleset de jogo | `kind: "ruleset"`, `activation.mode: "exclusive"`, `provides` | varia | opcional | [`declarative-model.md`](declarative-model.md), [`kinds.md`](kinds.md) |
| Criar um addon | `kind: "addon"`, `activation.mode: "multiple"` | varia | opcional | [`kinds.md`](kinds.md), [`author-complete-checklist.md`](author-complete-checklist.md) |
| Criar uma dependência library | `kind: "library"`, `activation.mode: "passive"` | varia | normalmente nenhum | [`kinds.md`](kinds.md) |
| Criar um theme | `kind: "theme"`, entrypoint de styles | `assets.styles`, talvez `assets.ui`, `settings` | opcional | [`content-and-assets.md`](content-and-assets.md), [`settings.md`](settings.md) |
| Criar conteúdo importável | `kind: "content"`, `provides.contentPacks` | `content.packs` | `sdk.content.*` opcional | [`content-and-assets.md`](content-and-assets.md) |
| Criar biblioteca de mídia/assets | `kind: "assets"`, `provides.assets` | `assets.pack`, `assets.*` específicos de mídia | normalmente nenhum | [`content-and-assets.md`](content-and-assets.md) |

## Power map de manifesto/dados

| Recurso | Declare aqui | Arquivos típicos | Capability |
|---|---|---|---|
| Tipos de ator | `provides.actorTypes` | `schemas/*.schema.json`, `sheets/*.sheet.json` | `actors.register` |
| Tipos de item | `provides.itemTypes` | `schemas/*.schema.json`, `sheets/*.sheet.json` | `items.register` |
| Fichas declarativas | `provides.actorTypes[].sheet`, `provides.itemTypes[].sheet` | `sheets/*.json` | `sheets.declarative` |
| Componentes de ficha | layouts declarativos que usam `sheets/components/` | `sheets/components/*.json` | `sheets.components` |
| Documentos de regras | `provides.rules` | `rules/*.json` | `rules.declarative` |
| Extensões de regra | `provides.rules`, comportamento de runtime | `rules/*.json`, `assets/*.js` | `rules.extends`, `assets.scripts` |
| Metadados de dados/rolagem | actions/fórmulas em `provides.rules`, `provides.mappings` | `rules/*.json`, `mappings/*.json` | `dice.roll`, `rolls.intent` |
| Defaults de combate | documentos em `provides.rules` | `rules/combat.json` | `combat.config` |
| Mappings de token | `provides.mappings` | `mappings/token-*.json` | `tokens.mappings` |
| Overlays de cena | runtime e entrypoints declarados | `assets/*.js`, `assets/*.css` | `scene.overlays`, `assets.scripts` |
| Content packs | `provides.contentPacks` | `content/*.json` | `content.packs` |
| Locales | `provides.locales` | `locales/en.json`, `locales/pt-BR.json` | `locales` |
| Settings | `settings` | só manifesto | `settings` |
| Styles | `entrypoints.game.styles` | `assets/*.css` | `assets.styles` |
| Scripts | `entrypoints.game.scripts` | `assets/*.js` | `assets.scripts` |
| Assets de UI | `provides.assets` ou paths do pacote | `assets/icons`, `assets/images` | `assets.ui`, capabilities específicas de mídia |
| Dependencies | `dependencies` | só manifesto | nenhuma |
| Conflicts | `conflicts` | só manifesto | nenhuma |
| Distribution | `distribution` | só manifesto | nenhuma |

## Power map de runtime da SDK

| Objetivo de runtime | Método(s) da SDK | Capability exigida | Notas |
|---|---|---|---|
| Checar identidade do pacote | `sdk.package`, `sdk.kind`, `sdk.version` | nenhuma | Sempre disponível na SDK escopada. |
| Checar capabilities | `sdk.capabilities.has`, `sdk.capabilities.require`, `sdk.capabilities.list` | nenhuma | Use para comportamento opcional. |
| Ler contexto | `sdk.context()`, `sdk.game.context()` | nenhuma | Retorna snapshots congelados. |
| Ler campanha | `sdk.game.campaign()` | nenhuma | Snapshot, não um modelo mutável cru. |
| Ler cena | `sdk.game.scene()` | nenhuma | Snapshot do contexto da cena ativa. |
| Ler usuário | `sdk.game.user()` | nenhuma | Snapshot do contexto do usuário ativo. |
| Checar readiness | `sdk.game.ready()` | nenhuma | True depois que o runtime de jogo está pronto. |
| Assinar eventos | `sdk.bus.subscribe` | `bus.subscribe` | Declare em `interop.listens`; nomes com escopo de pacote. |
| Publicar evento | `sdk.bus.publish` | `bus.publish` | Declare em `interop.emits`; payloads devem incluir `version`. |
| Registrar comando | `sdk.commands.register` | `commands.register` | Nomes de comando devem ter escopo de pacote. |
| Mostrar toast | `sdk.ui.toast`, `sdk.toast` | `assets.ui` | Helper de UI. |
| Abrir/fechar modal | `sdk.ui.openModal`, `sdk.ui.closeModal` | `assets.ui` | Apenas ids de modal documentados/do core. |
| Enviar chat card/intent | `sdk.chat.send` | `chat.cards` | Trate como intent; o core permanece autoritativo. |
| Rolar uma fÃ³rmula | `sdk.dice.roll` | `dice.roll` | Rolagem autoritativa no servidor com card de chat. |
| Executar intent de rolagem/action | `sdk.rolls.intent` | `rolls.intent` | Action de Sheet IR autoritativa, targets, dano e iniciativa. |
| Listar settings | `sdk.settings.definitions`, `sdk.settings.all` | `settings` | Valores visíveis ao pacote atual. |
| Ler setting | `sdk.settings.get`, `sdk.setting(key)` | `settings` | Use valores de fallback. |
| Gravar setting | `sdk.settings.set`, `sdk.setting(key, value)` | `settings` | Persiste pelo endpoint de settings da SDK. |
| Usar helpers de ficha | `sdk.sheets.helpers` | `sheets.runtime` | Acesso a helpers de runtime. |
| Registrar comportamento de ficha | `sdk.sheets.register` | `sheets.runtime` | Use após declarar a capability de ficha. |
| Registrar comportamento de combate | `sdk.combat.register` | `combat.runtime` | Integração de combate em runtime. |
| Registrar painel de combate | `sdk.combat.registerPanel` | `combat.runtime` | O objeto de painel deve ser estável e documentado pelo pacote. |
| Despachar evento de combate | `sdk.combat.dispatch` | `combat.runtime` | Ponte de runtime de combate de propriedade do pacote. |
| Renderizar slot de combate | `sdk.combat.renderSlot` | `combat.runtime` | Retorna resultados de slot renderizados ou array vazio. |
| Centralizar em token | `sdk.tokens.centerOn` | `tokens.extends` | Apenas helper de cliente. |
| Ler canvas ativo | `sdk.scene.activeCanvas` | `scene.tools` | Apenas helper de cliente. |
| Ler câmera da cena | `sdk.scene.activeCameraForScene` | `scene.tools` | Apenas helper de cliente. |
| Ler ferramenta ativa | `sdk.tools.activeTool` | `scene.tools` | Apenas helper de cliente. |
| Listar content packs | `sdk.content.packs` | `content.packs` | Async. |
| Ler um content pack | `sdk.content.pack` | `content.packs` | Async. |
| Traduzir texto | `sdk.i18n.t` | `locales` | Usa fallback quando ausente. |

## Receitas de construção

### Quero construir um ruleset completo

Use:

- `kind: "ruleset"`
- `activation.mode: "exclusive"`
- `provides.actorTypes`
- `provides.itemTypes`
- `provides.actorTypes[].sheet` / `provides.itemTypes[].sheet`
- `provides.rules`
- `provides.mappings`
- `provides.contentPacks`
- `provides.locales`
- `settings`
- `entrypoints.game.styles` opcional
- `entrypoints.game.scripts` opcional

Capabilities geralmente incluem:

```json
[
  "actors.register",
  "items.register",
  "sheets.declarative",
  "rules.declarative",
  "combat.config",
  "tokens.mappings",
  "content.packs",
  "settings",
  "locales",
  "assets.styles"
]
```

Adicione capabilities de runtime apenas se usar métodos de runtime:

```json
[
  "assets.scripts",
  "sheets.runtime",
  "combat.runtime",
  "dice.roll",
  "rolls.intent",
  "chat.cards",
  "assets.ui"
]
```

### Quero construir um addon com script

Use:

- `kind: "addon"`
- `activation.mode: "multiple"`
- `entrypoints.game.scripts`
- `assets.scripts`
- as capabilities exatas de método de [`capabilities.md`](capabilities.md)

Exemplo de conjunto de capabilities:

```json
[
  "assets.scripts",
  "assets.ui",
  "settings",
  "chat.cards",
  "commands.register"
]
```

### Quero construir um theme só com CSS

Use:

- `kind: "theme"`
- `entrypoints.game.styles`
- `assets.styles`
- `settings` opcional

Não use `assets.scripts` a menos que o theme tenha comportamento de navegador.

### Quero construir conteúdo importável

Use:

- `kind: "content"`
- `provides.contentPacks`
- `content.packs`
- dependência opcional do ruleset esperado pelo pack

Não use JavaScript de runtime para conteúdo importável a menos que o pacote de conteúdo também adicione comportamento de UI.

### Quero construir uma biblioteca de mídia

Use:

- `kind: "assets"`
- `provides.assets`
- `assets.pack`
- capabilities específicas de mídia como `assets.images`, `assets.audio`, `assets.maps`, `assets.icons`

## O que ler em seguida

1. [`declarative-model.md`](declarative-model.md) — entenda o modelo de pacote.
2. [`author-complete-checklist.md`](author-complete-checklist.md) — garanta que os autores usem toda a SDK.
3. [`manifest.md`](manifest.md) — escreva o contrato.
4. [`capabilities.md`](capabilities.md) — solicite as permissões certas.
5. [`runtime.md`](runtime.md) e [`reference.md`](reference.md) — adicione comportamento de navegador.
6. [`validation.md`](validation.md) — valide e depure.
