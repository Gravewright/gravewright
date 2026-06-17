# Modelo declarativo de pacotes

Pacotes Gravewright são **declarative-first**: o manifesto e os arquivos apontados por ele são a superfície primária da API. JavaScript de runtime é opcional e deve ser adicionado somente quando o pacote precisa de comportamento que não pode ser representado como dados.

A regra de autoria é:

```text
Declare tudo que o engine consegue carregar, validar, indexar, ativar, localizar e proteger.
Escreva script apenas para comportamento que realmente precisa de código client-side em runtime.
```

Esta página é o ponto de partida para autores. Ela explica o modelo antes dos campos individuais do manifesto e dos métodos do `sdk`.

## Modelo mental

Um pacote não é um plugin solto. É um contrato:

```text
data/packages/{kind_plural}/{id}/
├─ manifest.json          # contrato do pacote
├─ assets/                # scripts, styles, imagens, áudio, mapas, ícones
├─ schemas/               # schemas de actor/item ou outros schemas do pacote
├─ sheets/                # layouts/templates declarativos de sheets
├─ rules/                 # documentos declarativos de regras
├─ mappings/              # mappings de token, sheet, roll ou conteúdo
├─ content/               # packs importáveis
├─ locales/               # arquivos de tradução
└─ README.md              # notas para autores/usuários
```

O engine lê `manifest.json`, valida o schema, resolve dependências e conflitos, checa capabilities, carrega assets declarados, indexa conteúdo declarado, expõe settings declaradas e só então entrega aos scripts do pacote um SDK de navegador escopado.

```text
manifest.json
  -> valida contra o schema SDK v1
  -> declara kind e modo de ativação
  -> declara capabilities
  -> declara dados fornecidos pelo pacote
  -> declara scripts/styles de entrypoint
  -> declara settings, dependências, conflitos e distribuição
  -> entra no registro server-side de pacotes
  -> expõe um manifesto client-side seguro
  -> runtime opcional recebe um objeto sdk com acesso filtrado por capability
```

## O que “declarativo” significa

Dados declarativos são dados que o engine entende sem executar código do pacote.

Use dados declarativos para:

| Necessidade do autor | Preferir declarar em | Capability típica |
|---|---|---|
| Identidade e compatibilidade | campos top-level do manifesto | nenhuma |
| Kind e ativação | `kind`, `activation` | nenhuma |
| Permissões do pacote | `capabilities` | capability específica |
| CSS e JS | `entrypoints.game.styles`, `entrypoints.game.scripts` | `assets.styles`, `assets.scripts` |
| Settings de usuário/campanha | `settings` | `settings` |
| Tipos de actor | `provides.actorTypes` ou definições equivalentes | `actors.register` |
| Tipos de item | `provides.itemTypes` ou definições equivalentes | `items.register` |
| Layouts de sheet | `provides.sheets`, `sheets/` | `sheets.declarative` |
| Componentes de sheet | `provides.sheetComponents`, `sheets/components/` | `sheets.components` |
| Documentos de regras | `provides.rules`, `rules/` | `rules.declarative` |
| Configuração de combate | `provides.combat` | `combat.config` |
| Mappings de token | `provides.mappings`, `mappings/` | `tokens.mappings` |
| Rolls/intents | `provides.rolls`, `provides.mappings` | `rolls.intent`, `dice.roll` |
| Content packs importáveis | `provides.contentPacks`, `content/` | `content.packs` |
| Locales | `provides.locales`, `locales/` | `locales` |
| Bibliotecas de assets | `provides.assets`, `assets/` | `assets.pack`, `assets.images`, `assets.audio`, `assets.maps`, `assets.icons` |
| Dependências/conflitos | `dependencies`, `conflicts` | nenhuma |
| Metadados de distribuição | `distribution` | nenhuma |

A forma exata de cada objeto fica em [`manifest.md`](manifest.md), [`content-and-assets.md`](content-and-assets.md) e no JSON Schema da SDK v1.

## JavaScript de runtime é camada de extensão, não base

Um pacote com script declara um arquivo de navegador:

```json
{
  "capabilities": ["assets.scripts", "assets.ui"],
  "entrypoints": {
    "game": {
      "scripts": ["assets/main.js"]
    }
  }
}
```

E registra seu runtime:

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk) {
    // Configure o estado antes do runtime do jogo ficar pronto.
  },
  ready(sdk) {
    // DOM e runtime do jogo estão prontos aqui.
    sdk.ui.toast("Meu pacote está pronto");
  }
});
```

Use runtime JavaScript para:

- responder a eventos client-side;
- registrar comandos;
- enviar chat cards ou chat intents;
- adicionar comportamento de UI por métodos documentados;
- ler/escrever settings do pacote;
- registrar plugins de runtime de sheet/combate quando dados declarativos não bastarem;
- centralizar em tokens ou ler estado atual de cena/ferramenta;
- compor integrações entre pacotes por eventos versionados.

Não use runtime JavaScript para:

- executar backend;
- escrever diretamente no banco;
- acessar filesystem bruto;
- fazer chamadas de rede não mediadas;
- sobrescrever permissões;
- depender de globals privados;
- depender de estrutura DOM não documentada;
- substituir dados declarativos que o engine já suporta.

## Tabela de decisão: declarativo vs runtime

| Pergunta | Use dados declarativos | Use SDK de runtime |
|---|---:|---:|
| O engine consegue carregar e validar antes da mesa abrir? | sim | não |
| Define conteúdo durável do pacote? | sim | não |
| Precisa de capability, mas não de interação client-side? | sim | não |
| Precisa de eventos, UI ou comandos no navegador? | não | sim |
| Depende de cena/usuário/mesa atual? | talvez | sim |
| Precisa persistir preferências? | declare `settings` | chame `sdk.settings.*` |
| Precisa enviar chat a partir de click handler? | declare capability | chame `sdk.chat.send` |
| Precisa de sheet customizada? | declare sheet | script só para comportamento dinâmico |
| Precisa de configuração de combate? | declare config | script para plugins/painel |
| Precisa reutilizar arte/mapas/ícones/áudio? | declare asset pack | runtime só se houver UI |

## Addon declarativo mínimo

Este addon contribui CSS e settings. Ele não executa JavaScript.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "clean-ui",
  "name": "Clean UI",
  "version": "0.1.0",
  "description": "Small visual improvements for the table UI.",
  "authors": ["Example Author"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": ["assets.styles", "settings"],
  "activation": {
    "scope": "campaign",
    "mode": "multiple"
  },
  "entrypoints": {
    "game": {
      "styles": ["assets/clean-ui.css"]
    }
  },
  "settings": [
    {
      "key": "compactMode",
      "type": "boolean",
      "scope": "campaign",
      "default": true,
      "label": "Compact mode"
    }
  ],
  "provides": {}
}
```

## Content package declarativo mínimo

Um pacote `content` deve ser importável sem executar scripts.

```json
{
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "content",
  "id": "starter-encounters",
  "name": "Starter Encounters",
  "version": "0.1.0",
  "compatibility": { "minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1" },
  "capabilities": ["content.packs"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": {} },
  "provides": {
    "contentPacks": [
      {
        "id": "encounters",
        "label": "Starter Encounters",
        "path": "content/encounters.json",
        "type": "encounter"
      }
    ]
  }
}
```

## Asset package declarativo mínimo

Um pacote `assets` contribui mídia reutilizável para campanhas e outros pacotes.

```json
{
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "assets",
  "id": "dark-forest-assets",
  "name": "Dark Forest Assets",
  "version": "0.1.0",
  "compatibility": { "minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1" },
  "capabilities": ["assets.pack", "assets.images", "assets.maps", "assets.icons"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": {} },
  "provides": {
    "assets": [
      { "id": "forest-map", "type": "map", "path": "assets/maps/forest.webp", "label": "Dark Forest Map" },
      { "id": "wolf-icon", "type": "icon", "path": "assets/icons/wolf.svg", "label": "Wolf Icon" }
    ]
  }
}
```

## Ruleset declarativo mínimo

Um `ruleset` é o sistema-base da campanha. Ele deve declarar a estrutura do jogo primeiro e adicionar runtime apenas quando necessário.

```json
{
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "ruleset",
  "id": "my-rpg",
  "name": "My RPG",
  "version": "0.1.0",
  "compatibility": { "minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x" },
  "capabilities": [
    "actors.register",
    "items.register",
    "sheets.declarative",
    "rules.declarative",
    "tokens.mappings",
    "content.packs"
  ],
  "activation": { "scope": "campaign", "mode": "exclusive" },
  "entrypoints": { "game": {} },
  "provides": {
    "actorTypes": [{ "id": "character", "label": "Character", "schema": "schemas/character.json" }],
    "itemTypes": [{ "id": "weapon", "label": "Weapon", "schema": "schemas/weapon.json" }],
    "sheets": [{ "id": "character-sheet", "type": "actor", "for": "character", "path": "sheets/character.json" }],
    "rules": [{ "id": "core-rules", "path": "rules/core.json" }]
  }
}
```

## Regras práticas para autores

1. Comece sempre pelo `manifest.json`.
2. Declare `kind`, `activation`, `compatibility` e `capabilities` antes de escrever qualquer script.
3. Para cada arquivo no pacote, garanta que existe uma declaração correspondente ou que ele é asset interno de algo declarado.
4. Para cada método de runtime usado, confirme a capability exigida em [`reference.md`](reference.md) e [`capabilities.md`](capabilities.md).
5. Rode `grave package validate` e `grave package doctor` antes de distribuir.
6. Documente para o usuário quais settings, conteúdos e integrações o pacote fornece.
