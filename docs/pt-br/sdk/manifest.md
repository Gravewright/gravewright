# Manifesto `manifest.json`

`manifest.json` é o contrato principal de um pacote Gravewright. Ele informa ao engine quem é o pacote, com quais versões é compatível, que tipo de pacote é, como deve ser ativado, quais permissões precisa, quais arquivos devem ser carregados e quais recursos ele fornece.

## Estrutura geral

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "my-package",
  "name": "My Package",
  "version": "0.1.0",
  "description": "Package description.",
  "authors": ["Author Name"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1",
    "verified": "1",
    "maximum": "1.x"
  },
  "capabilities": [],
  "activation": {
    "scope": "campaign",
    "mode": "multiple"
  },
  "entrypoints": {
    "game": {}
  },
  "settings": [],
  "dependencies": [],
  "conflicts": [],
  "provides": {}
}
```

## Campos de identidade

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `$schema` | recomendado | URL ou path do JSON Schema SDK v1. |
| `schemaVersion` | sim | Versão do schema do manifesto. |
| `sdkVersion` | sim | Versão major da SDK usada pelo pacote. |
| `kind` | sim | `ruleset`, `addon`, `library`, `theme`, `content` ou `assets`. |
| `id` | sim | Identificador estável do pacote. Deve ser único. |
| `name` | sim | Nome exibido ao usuário. |
| `version` | sim | Versão do pacote. Use versionamento semântico. |
| `description` | recomendado | Explica o que o pacote faz. |
| `authors` | recomendado | Autores/mantenedores. |
| `license` | recomendado | Licença do pacote. |

## Compatibilidade

```json
"compatibility": {
  "minimum": "1",
  "verified": "1",
  "maximum": "1.x"
}
```

- `minimum`: menor versão da linha de API da SDK suportada.
- `verified`: versão testada pelo autor.
- `maximum`: maior faixa esperada. Use com cuidado quando houver risco de breaking changes.

A compatibilidade é avaliada contra a **linha de versão da API da SDK** (a mesma
nomeada por `sdkVersion`, congelada em `1` pela Alpha 2.0.0), não a versão de
marketing do core — então um bump de release do core não torna pacotes da SDK 1
incompatíveis retroativamente.

## Ativação

```json
"activation": {
  "scope": "campaign",
  "mode": "multiple"
}
```

- `scope` define onde o pacote pode ser ativado.
- `mode` define se ele é exclusivo, múltiplo ou passivo.

Regras usuais:

| Kind | `activation.mode` esperado |
|---|---|
| `ruleset` | `exclusive` |
| `addon` | `multiple` |
| `library` | `passive` |
| `theme` | `multiple` |
| `content` | `multiple` |
| `assets` | `multiple` |

## Capabilities

`capabilities` declara o que o pacote tem permissão para fornecer ou executar.

```json
"capabilities": [
  "assets.scripts",
  "settings"
]
```

Declare somente o necessário. O runtime filtra métodos do `sdk` por capability, e a validação pode falhar se o pacote usar entrypoints ou `provides` incompatíveis com as capabilities declaradas.

## Entrypoints

`entrypoints` lista arquivos que o cliente deve carregar.

```json
"entrypoints": {
  "game": {
    "styles": ["assets/main.css"],
    "scripts": ["assets/main.js"]
  }
}
```

- `styles` exige `assets.styles`.
- `scripts` exige `assets.scripts`.
- Paths devem ser relativos ao pacote.
- Scripts devem chamar `window.GravewrightSDK.register(...)` se precisam de runtime.

## Settings

```json
"settings": [
  {
    "key": "compactMode",
    "type": "boolean",
    "scope": "campaign",
    "default": true,
    "label": "Compact mode",
    "description": "Use a denser UI layout."
  }
]
```

Boas práticas:

- use `key` estável;
- escolha `scope` correto;
- forneça `default` seguro;
- documente efeitos colaterais;
- evite renomear settings sem migração.

## Dependências e conflitos

```json
"dependencies": [
  { "id": "core-library", "version": ">=1.0.0", "optional": false }
],
"conflicts": [
  { "id": "other-addon", "reason": "Both replace the same sheet behavior." }
]
```

Use `dependencies` apenas quando a ausência for um erro. Se um pacote apenas melhora o comportamento quando outro está presente, prefira escuta opcional de eventos via `sdk.bus.subscribe(...)` e degrade graciosamente. Use `conflicts` quando dois pacotes ativos produziriam comportamento inválido, ambíguo ou inseguro.

## `provides`

`provides` é a seção declarativa mais importante. Ela lista o que o pacote entrega para o engine.

Campos comuns:

```json
"provides": {
  "storage": { "model": "scoped-json-v1" },
  "actorTypes": [],
  "itemTypes": [],
  "rules": {
    "formulas": "rules/formulas.gw.json"
  },
  "mappings": {
    "tokens": "mappings/tokens.gw.json"
  },
  "contentPacks": [],
  "assets": {},
  "locales": {},
  "areaMarkers": []
}
```

Esses são os campos de `provides` consumidos hoje pela engine. Fichas são
referenciadas em `provides.actorTypes[].sheet` e `provides.itemTypes[].sheet`;
não existe um `provides.sheets` de topo ativo. Chaves como `sheets`,
`sheetComponents`, `rolls`, `combat` e `sceneOverlays` são reservadas/planejadas
e geram warning de validação enquanto não tiverem consumo canônico. Para
rolagens, declare fórmulas/actions em `provides.rules` e chame via Sheet IR,
`sdk.dice.roll` ou `sdk.rolls.intent`.

#### `rules/combat.gw.json`

O core é dono do rastreador de combate — a rodada, a ordem de turnos, o painel —
mas não do que a iniciativa *é*. Ele guarda o valor como texto e nunca o
interpreta. O ruleset decide como o valor chega lá e se ele implica uma ordem.

```json
{
  "version": 2,
  "initiative": {
    "label": "Iniciativa",
    "input": "roll",
    "sort": "desc",
    "formula": "1d20 + @sheet.combat.initiative",
    "actionId": "roll.initiative",
    "tieBreaker": "@sheet.abilities.dex.score",
    "icon": "ph-dice-five",
    "accent": "#b88a44"
  },
  "resources": {
    "hp": { "label": "PV", "path": "sheet.hp.value", "maxPath": "sheet.hp.max", "min": 0 }
  }
}
```

`initiative.input` é o único campo que muda o comportamento do painel:

| `input` | O que o mestre vê | Como a ordem é decidida |
| --- | --- | --- |
| `roll` | Botões de rolagem, mais um campo numérico para sobrescrever | Pelo valor, usando `sort` |
| `number` | Só um campo numérico | Pelo valor, usando `sort` |
| `text` | Um campo de texto livre | Na mão: o mestre move as linhas para cima e para baixo |

Use `text` sempre que a ordem de turnos não for um número que a engine pudesse
comparar — cartas compradas, fases nomeadas, "quem emboscou age primeiro", ou
uma ficha que a mesa lê no papel. O core não inventa ranking para uma string.

| Campo | Significado |
| --- | --- |
| `initiative.label` | Como o valor se chama. Uma chave de locale é resolvida pelo catálogo do pacote. |
| `initiative.input` | `roll`, `number` ou `text`. Padrão: `roll` quando há `formula`, `number` caso contrário. |
| `initiative.sort` | `desc` (padrão) ou `asc`. Ignorado quando `input` é `text`. |
| `initiative.formula` | Avaliada contra a ficha do ator. Sem ela, a engine usa a fórmula do `actionId`. |
| `initiative.actionId` | A action declarativa que um botão de ficha usa; o resultado é adotado pelo rastreador. Padrão: `roll.initiative`. |
| `initiative.tieBreaker` | Um caminho de ficha que desempata sem aparecer no valor exibido. |
| `initiative.icon` | Ícone Phosphor dos botões de rolagem. |
| `initiative.accent` | Uma cor hex para o painel. |
| `resources` | Recursos nomeados; `hp` (ou `health`) é a barra desenhada sob cada combatente. |

A engine não tem dado próprio: um sistema que declara `input: "roll"` sem
`formula` e sem um `actionId` rolável simplesmente não tem o que rolar, e os
botões de rolagem dizem isso. Todo o resto do painel é comportamento do core ou
a capability `combat.runtime`.

Nem todo kind deve usar todos os campos. Por exemplo, `content` normalmente declara `contentPacks`, enquanto `assets` declara `assets`.

Rulesets devem declarar `provides.storage` (modelo de storage) e ao menos um tipo em `provides.actorTypes`. Os tipos de content pack permitidos são `actor_pack`, `item_pack`, `spell_pack`, `journal_pack`, `table_pack` e `condition_pack`.

Arquivos de locale são dicionários JSON. A tradução em runtime fica disponível via `sdk.i18n.t(key, fallback)` quando o pacote declara a capability `locales`.

## Paths seguros

Todos os paths no manifesto devem:

- ser relativos ao diretório do pacote;
- não conter `..`;
- não apontar para arquivos fora do pacote;
- usar separador `/`;
- apontar para arquivos existentes;
- ser compatíveis com a capability declarada.

## Manifesto declarativo antes de código

Antes de criar `assets/main.js`, confira se a funcionalidade pode ser expressa com `provides`, `settings`, `entrypoints.game.styles`, `dependencies` ou `conflicts`. O manifesto é o contrato; o runtime é uma camada opcional.
