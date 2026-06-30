# Gravewright SDK

A Gravewright SDK é o único modelo suportado para extensões do Gravewright.

Toda extensão instalável é um **pacote**. Um pacote é um diretório em `data/packages/{kind_plural}/{id}/` que contém um `manifest.json` e os arquivos declarados por esse manifesto. O comportamento do pacote é definido por um contrato único de SDK v1.

> [!WARNING]
> Gravewright e software Alpha, mas a superficie de autoria de pacotes da SDK 1 esta congelada. Pacotes novos devem declarar `compatibility: { "minimum": "1", "verified": "1" }` e podem adicionar `"maximum": "1.x"` quando quiserem que um engine SDK 2 futuro marque o pacote como incompativel.

## Tipos de pacote suportados

| Kind | Finalidade | Modo de ativação |
|---|---|---|
| `ruleset` | Regras-base de uma campanha. Define tipos de actor/item, sheets, regras, mappings, conteúdo e comportamento de combate. | `exclusive` |
| `addon` | Extensão opcional de campanha. Adiciona UI, plugins, settings, scene tools, chat cards, conteúdo ou comportamento de runtime. | `multiple` |
| `library` | Dependência passiva compartilhada por outros pacotes. | `passive` |
| `theme` | Pacote visual/de UI, principalmente CSS e assets de interface. | `multiple` |
| `content` | Pacote somente de conteúdo importável. | `multiple` |
| `assets` | Biblioteca reutilizável de imagens, mapas, ícones, áudio, retratos e assets semelhantes. | `multiple` |

Uma campanha tem exatamente um `ruleset` ativo e qualquer número de pacotes `addon`, `theme`, `content` e `assets` ativos. Pacotes `library` são carregados somente como dependências.

## Arquivos canônicos da SDK

- `manifest.json` — metadados, capabilities, ativação, entrypoints, settings, dependências, conflitos e dados em `provides`.
- `schemas/gravewright-package-v1.schema.json` — JSON Schema público dos manifestos SDK v1.
- `static/js/sdk/sdk-capabilities.js` — allow-list de capabilities no navegador e gates método → capability.
- `static/js/sdk/gravewright-sdk.js` — runtime do navegador e entrypoint público `window.GravewrightSDK`.
- `app/engine/sdk/` — carregamento, validação, instalação, ativação, dependências, conteúdo, assets, settings, locales e diagnóstico no servidor.

## Comece por aqui

Para criar um pacote, leia primeiro:

1. [`declarative-model.md`](declarative-model.md) — explica o modelo declarativo-first e quando adicionar JavaScript de runtime.
2. [`author-complete-checklist.md`](author-complete-checklist.md) — lista tudo que um autor precisa para usar toda a superfície da SDK.
3. [`power-map.md`](power-map.md) — mapeia objetivo do autor → campo do manifesto → capability → API de runtime → documentação.

O modelo pretendido da SDK não é “escrever um plugin e descobrir globals”. É:

```text
manifest + arquivos declarados + capabilities declaradas + runtime escopado opcional
```

Autores devem preferir dados declarativos em `manifest.json` para rulesets, addons, conteúdo, assets, settings, locales, sheets, mappings e rules. JavaScript de runtime deve ser usado apenas para comportamento que realmente precisa de eventos client-side, UI, comandos, chat, mutação de settings, plugins de runtime de sheets/combate ou outros métodos escopados documentados.

## Entrypoint público do navegador

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Registre plugins, sheets, comportamento de combate, comandos ou estado local.
  },
  ready(sdk, payload) {
    // Chamado depois que o runtime do jogo estiver pronto.
  },
});
```

O `id` deve corresponder ao `id` de um manifesto ativo e a chamada deve vir de um script declarado por esse pacote. O runtime rejeita ids ausentes, pacotes inativos, registros duplicados e tentativas de registro vindas de script pertencente a outro pacote.

## O `sdk` escopado

Cada pacote recebe um objeto SDK congelado e escopado ao pacote. O acesso a métodos é controlado pelas capabilities declaradas no manifesto.

Namespaces:

```text
sdk.version
sdk.package
sdk.kind
sdk.capabilities
sdk.context
sdk.game
sdk.bus
sdk.commands
sdk.ui
sdk.chat
sdk.settings
sdk.sheets
sdk.combat
sdk.tokens
sdk.scene
sdk.tools
sdk.content
sdk.i18n
```

Atalhos:

```js
sdk.toast("Olá");
sdk.setting("enabled");        // get
sdk.setting("enabled", true);  // set
```

## Workflow de autoria

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"

grave package validate data/packages/rulesets/my-rpg
grave package install my-rpg --yes --enable
grave package doctor my-rpg
```

## Mapa da documentação

- [`tutorial-addon.md`](tutorial-addon.md) — fim a fim: do zero a um addon funcionando.
- [`tutorial-ruleset.md`](tutorial-ruleset.md) — fim a fim: do zero a um ruleset mínimo funcionando.
- [`declarative-model.md`](declarative-model.md) — modelo declarativo-first, exemplos e regras de decisão.
- [`author-complete-checklist.md`](author-complete-checklist.md) — checklist de 100% da SDK, do scaffold ao release.
- [`power-map.md`](power-map.md) — objetivo do autor → manifesto → capability → API de runtime.
- [`manifest.md`](manifest.md) — contrato completo do manifesto.
- [`kinds.md`](kinds.md) — kinds de pacote e regras específicas.
- [`capabilities.md`](capabilities.md) — capabilities permitidas, proibidas e gates por método.
- [`runtime.md`](runtime.md) — ciclo de vida do runtime e `window.GravewrightSDK`.
- [`html-sheets.md`](html-sheets.md) — guia completo de fichas HTML de ator/item, do template ao controller.
- [`reference.md`](reference.md) — referência completa dos namespaces do `sdk` escopado.
- [`rolls.md`](rolls.md) - rolagens autoritativas, intents de rolagem e sintaxe de dados.
- [`authoring-guide.md`](authoring-guide.md) — workflow de autoria, scaffold e publicação.
- [`settings.md`](settings.md) — settings no manifesto e API de runtime.
- [`content-and-assets.md`](content-and-assets.md) — content packs, asset packs e paths seguros.
- [`messaging.md`](messaging.md) — eventos entre pacotes.
- [`cli.md`](cli.md) — CLI `grave` para SDK e operação.
- [`validation.md`](validation.md) — regras de validação e erros comuns.
- [`security.md`](security.md) — modelo de segurança e fronteiras privadas.
- [`examples.md`](examples.md) — exemplos mínimos de ruleset e addon.
- [`troubleshooting.md`](troubleshooting.md) — playbook de diagnóstico.

## O que não é SDK pública

Não são APIs públicas de pacote:

- execução de backend a partir de pacotes;
- acesso direto/não gerenciado ao banco de dados; use `storage.sqlite` quando precisar da via SQL gerenciada e escopada;
- acesso cru ao sistema de arquivos;
- acesso cru à rede;
- override de permissões;
- globals de navegador não documentados;
- internals do renderer;
- stores privadas;
- shapes privados de eventos WebSocket;
- estrutura DOM não documentada como ponto de extensão.
