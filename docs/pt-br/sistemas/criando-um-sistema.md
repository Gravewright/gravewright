# Criando um Sistema

> [!WARNING]
> **System API v1 ainda está em Alpha.**
> Sistemas são o ponto mais sensível do Gravewright porque definem schema, fichas, regras, rolagens, packs e mapeamentos de token. Entre versões Alpha, campos e comportamento podem mudar. Use sistemas personalizados em one-shots e ambientes de teste antes de confiar uma campanha longa a eles.

Um **sistema** é um pacote declarativo que ensina o Gravewright a entender um jogo específico: quais tipos de atores existem, quais tipos de itens existem, qual é o schema de dados de cada entidade, como as fichas são renderizadas, quais rolagens existem, como a iniciativa funciona e quais conteúdos iniciais podem ser importados.

Sistemas não são plugins arbitrários de backend. O servidor lê e valida arquivos declarativos. JavaScript de sistema, quando usado, roda no navegador e deve usar apenas APIs públicas documentadas.

## Quando criar um sistema

Crie um sistema quando você precisa definir as regras estruturais de um jogo:

- tipos de ator, como `character`, `monster`, `npc`, `vehicle`;
- tipos de item, como `weapon`, `armor`, `spell`, `feat`;
- fichas declarativas para atores e itens;
- dados derivados, fórmulas, rolagens e ações;
- mapeamentos entre dados da ficha e tokens;
- configuração de combate, iniciativa e recursos;
- packs de conteúdo que pertencem ao sistema.

Não crie um sistema para pequenas melhorias visuais, automações opcionais ou comportamento que pode ser ligado/desligado por campanha. Para isso, crie um **módulo**.

## Modelo mental

Um sistema tem quatro camadas:

1. **Manifest**: identidade, compatibilidade, capabilities e lista de arquivos do pacote.
2. **Dados**: JSON Schemas para validar o formato de atores e itens.
3. **UI declarativa**: layouts `.sheet.gw.json` que descrevem a ficha.
4. **Regras**: arquivos `.gw.json` para ações, fórmulas, derivados, combate, validação e mapeamentos.

Opcionalmente, o sistema pode ter:

- CSS para visual próprio;
- JavaScript client-side para pequenos pontos de extensão;
- locales;
- content packs.

## Estrutura recomendada

```text
data/systems/meu-sistema/
  manifest.json
  README.md

  schemas/
    character.schema.json
    monster.schema.json
    item.schema.json

  layouts/
    character.sheet.gw.json
    monster.sheet.gw.json
    items/
      weapon.sheet.gw.json
      spell.sheet.gw.json

  rules/
    actions.gw.json
    combat.gw.json
    derived.gw.json
    formulas.gw.json
    validation.gw.json
    conditions.gw.json

  mappings/
    token.gw.json
    chat-cards.gw.json
    roll-toast.gw.json

  content/
    actors.monsters.gwpack.json
    items.weapons.gwpack.json
    spells.gwpack.json

  locales/
    pt-BR.json
    en.json

  assets/
    meu-sistema.css
    meu-sistema.js
```

Para um sistema mínimo, você precisa apenas de:

```text
data/systems/meu-sistema/
  manifest.json
  schemas/character.schema.json
  layouts/character.sheet.gw.json
```

Mas um sistema útil normalmente também tem `rules/actions.gw.json`, `rules/combat.gw.json` e pelo menos um arquivo CSS.

## Primeiro manifest

Crie `manifest.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-manifest-v1.json",
  "manifestVersion": 1,
  "type": "system",
  "id": "meu-sistema",
  "name": "Meu Sistema",
  "description": "Sistema de exemplo para Gravewright.",
  "version": "0.1.0",
  "apiVersion": "1",
  "authors": [
    { "name": "Seu Nome" }
  ],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "display": {
    "color": "#7c5cff"
  },
  "capabilities": [
    "actors.register",
    "sheets.declarative",
    "rules.declarative",
    "dice.roll"
  ],
  "system": {
    "id": "meu-sistema",
    "storage": {
      "model": "scoped-json-v1"
    },
    "actorTypes": [
      {
        "id": "character",
        "label": "Personagem",
        "schema": "schemas/character.schema.json",
        "sheet": "layouts/character.sheet.gw.json"
      }
    ],
    "itemTypes": [],
    "rules": {
      "actions": "rules/actions.gw.json"
    }
  },
  "dependencies": [],
  "conflicts": []
}
```

### Regras importantes do manifest

- `manifestVersion` deve ser `1`.
- `type` deve ser `"system"`.
- `apiVersion` deve ser `"1"`.
- `id` deve usar kebab-case minúsculo: `meu-sistema`, não `MeuSistema`.
- `system.id` deve ser igual ao `id` do topo.
- `system.storage.model` deve ser `"scoped-json-v1"`.
- Todo path deve ser relativo ao pacote.
- Paths absolutos, URLs, `..` e barras duplas são rejeitados.

## Capabilities

Declare apenas o que o sistema realmente usa.

| Capability | Use quando o sistema... |
|---|---|
| `actors.register` | declara `actorTypes` |
| `items.register` | declara `itemTypes` |
| `sheets.declarative` | fornece layouts de ficha |
| `rules.declarative` | fornece arquivos em `system.rules` |
| `content.packs` | fornece packs em `system.contentPacks` |
| `tokens.mappings` | fornece mapeamentos de token |
| `dice.roll` | declara ações de rolagem |
| `chat.cards` | customiza cards de chat |
| `roll.toast` | customiza toasts de rolagem |
| `locales` | fornece `system.locales` |
| `assets.ui` | altera UI via assets |
| `assets.styles` | fornece CSS |
| `assets.scripts` | fornece JavaScript |
| `combat.config` | fornece config de combate |
| `combat.hooks` | registra hooks client-side de combate |
| `rolls.intent` | usa intents semânticos de rolagem |

Na Alpha, trate capabilities como contrato de segurança e compatibilidade. Não declare capabilities “por via das dúvidas”.

## Criando o schema de ator

Um schema define o formato dos dados salvos em `sheet`. Exemplo mínimo:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Meu Sistema Character",
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "attributes": {
      "type": "object",
      "properties": {
        "strength": { "type": "integer", "default": 10 },
        "dexterity": { "type": "integer", "default": 10 }
      }
    },
    "combat": {
      "type": "object",
      "properties": {
        "hp": { "type": "integer", "default": 10 },
        "maxHp": { "type": "integer", "default": 10 },
        "initiative": { "type": "integer", "default": 0 }
      }
    }
  }
}
```

O layout acessa esses dados usando paths como:

```text
sheet.attributes.strength
sheet.combat.hp
sheet.combat.maxHp
```

Boa prática: mantenha o schema estável e previsível. Em Alpha, mudanças de schema podem tornar mesas antigas difíceis de recuperar.

## Criando a primeira ficha

Crie `layouts/character.sheet.gw.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-layout-v1.json",
  "kind": "actorSheet",
  "system": "meu-sistema",
  "actorType": "character",
  "id": "meu-sistema-character",
  "title": {
    "bind": "core.name"
  },
  "body": {
    "type": "tabs",
    "tabs": [
      {
        "type": "tab",
        "id": "main",
        "label": "Principal",
        "icon": "user",
        "children": [
          {
            "type": "section",
            "label": "Atributos",
            "children": [
              {
                "type": "grid",
                "columns": 2,
                "children": [
                  {
                    "type": "abilityCard",
                    "label": "Força",
                    "abbr": "FOR",
                    "scorePath": "sheet.attributes.strength",
                    "modPath": "sheet.attributes.strengthMod",
                    "rollAction": "roll.strength"
                  },
                  {
                    "type": "abilityCard",
                    "label": "Destreza",
                    "abbr": "DES",
                    "scorePath": "sheet.attributes.dexterity",
                    "modPath": "sheet.attributes.dexterityMod",
                    "rollAction": "roll.dexterity"
                  }
                ]
              }
            ]
          },
          {
            "type": "section",
            "label": "Combate",
            "children": [
              {
                "type": "resourceBar",
                "valuePath": "sheet.combat.hp",
                "maxPath": "sheet.combat.maxHp"
              },
              {
                "type": "combatStat",
                "label": "Iniciativa",
                "abbr": "INI",
                "valuePath": "sheet.combat.initiative",
                "signed": true,
                "rollAction": "roll.initiative"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Nós de layout mais úteis

| Tipo | Uso |
|---|---|
| `tabs` | contêiner com abas |
| `section` | bloco visual com título |
| `row` | linha flexível |
| `grid` | grade; aceita `columns` |
| `column` | coluna |
| `divider` | separador |
| `spacer` | espaço visual |
| `abilityCard` | atributo com score, modificador e rolagem |
| `rollableStat` | linha clicável para rolagem |
| `combatStat` | estatística de combate |
| `resourceBar` | barra baseada em valor/máximo |
| `imageField` | imagem readonly |
| `readonlyField` | valor readonly |
| `text` | texto simples |
| `badge` | etiqueta curta |
| `itemList` | lista/tabela de itens vinculados |
| `rollButton` | botão de rolagem |
| `actionButton` | botão de ação |
| `incrementButton` | botão de incremento |
| `decrementButton` | botão de decremento |

Nem todo campo é formalizado no JSON Schema ainda; a Alpha aceita propriedades adicionais para permitir evolução do renderer. Documente no README do seu sistema qualquer nó customizado que você usar.

## Criando ações e rolagens

Crie `rules/actions.gw.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-actions-v1.json",
  "actions": {
    "roll.strength": {
      "type": "roll",
      "label": "Teste de Força",
      "intent": "check",
      "formula": "1d20 + @sheet.attributes.strengthMod",
      "visibility": "public",
      "chatCard": "check"
    },
    "roll.dexterity": {
      "type": "roll",
      "label": "Teste de Destreza",
      "intent": "check",
      "formula": "1d20 + @sheet.attributes.dexterityMod",
      "visibility": "public",
      "chatCard": "check"
    },
    "roll.initiative": {
      "type": "roll",
      "label": "Iniciativa",
      "intent": "initiative",
      "formula": "1d20 + @sheet.combat.initiative",
      "visibility": "public",
      "chatCard": "initiative"
    }
  }
}
```

Intents v1:

| Intent | Significado |
|---|---|
| `check` | teste genérico |
| `save` | salvaguarda/resistência |
| `attack` | ataque |
| `damage` | dano |
| `initiative` | iniciativa |
| `skill` | perícia |
| `tool` | ferramenta |
| `custom` | caso específico do sistema |

Use `intent` para semântica, não para aparência. Aparência deve ser controlada por `chatCard`, `rollToast`, CSS e mapeamentos.

## Configurando combate

Crie `rules/combat.gw.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-combat-v1.json",
  "version": 1,
  "defaultMode": "encounter",
  "turnOrder": {
    "strategy": "formula_sort",
    "label": "Iniciativa",
    "formula": "@sheet.combat.initiative",
    "sort": "desc",
    "tieBreakers": ["name"]
  },
  "resources": {
    "hp": {
      "label": "PV",
      "path": "sheet.combat.hp",
      "maxPath": "sheet.combat.maxHp",
      "min": 0
    }
  },
  "activityTypes": [
    { "id": "action", "label": "Ação" },
    { "id": "bonus", "label": "Ação bônus" },
    { "id": "reaction", "label": "Reação" }
  ]
}
```

Use `combat.config` na lista de capabilities quando declarar esse arquivo.

## Mapeando tokens

Se seu sistema usa tokens com HP, nome, retrato ou estados derivados, declare um mapping:

```json
{
  "version": 1,
  "token": {
    "name": "core.name",
    "hp": "sheet.combat.hp",
    "maxHp": "sheet.combat.maxHp",
    "initiative": "sheet.combat.initiative"
  }
}
```

E referencie no manifest:

```json
{
  "system": {
    "mappings": {
      "tokens": "mappings/token.gw.json"
    }
  }
}
```

Use a capability `tokens.mappings`.

## Adicionando assets

No manifest:

```json
{
  "capabilities": ["assets.ui", "assets.styles", "assets.scripts"],
  "system": {
    "assets": {
      "styles": ["assets/meu-sistema.css"],
      "scripts": ["assets/meu-sistema.js"]
    }
  }
}
```

CSS é o caminho preferido para customização visual. JavaScript deve ser usado apenas para comportamento que a ficha declarativa ainda não consegue expressar.

Exemplo de JS de sistema:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("meu-sistema", {
    renderSection(node, variant, renderContext, helpers) {
      if (variant !== "special") return null;

      const section = helpers.el("section", "meu-sistema-special");
      section.appendChild(helpers.el("h3", null, node.label || "Especial"));
      return section;
    },

    renderHeaderIdentity(main, bundle, helpers) {
      const actor = bundle.actor || {};
      main.appendChild(helpers.el("div", "meu-sistema-subtitle", actor.type || ""));
    },

    autoFitWidth(actorType) {
      if (actorType === "character") return 820;
      return null;
    }
  });
})();
```

APIs disponíveis para sistemas no navegador:

- `window.GravewrightSheets.registerSystem(systemId, hooks)`;
- `window.GravewrightSheets.helpers`;
- `window.GravewrightCombat.registerSystem(systemId, plugin)`.

Evite acessar variáveis internas, stores privados ou estrutura DOM não documentada.

## Adicionando content packs

No manifest:

```json
{
  "capabilities": ["content.packs"],
  "system": {
    "contentPacks": [
      {
        "id": "starter-weapons",
        "type": "item_pack",
        "label": "Armas Iniciais",
        "path": "content/items.weapons.gwpack.json"
      }
    ]
  }
}
```

Tipos aceitos:

- `actor_pack`;
- `item_pack`;
- `spell_pack`;
- `journal_pack`;
- `table_pack`;
- `condition_pack`.

Um pack deve usar o mesmo modelo de dados que os schemas do sistema esperam.

## Localização

No manifest:

```json
{
  "capabilities": ["locales"],
  "system": {
    "locales": {
      "pt-BR": "locales/pt-BR.json",
      "en": "locales/en.json"
    }
  }
}
```

Exemplo `locales/pt-BR.json`:

```json
{
  "MEU_SISTEMA.Character": "Personagem",
  "MEU_SISTEMA.Strength": "Força",
  "MEU_SISTEMA.Initiative": "Iniciativa"
}
```

Prefira `labelKey` em layouts quando o texto precisa ser traduzido.

## Checklist de validação

Antes de distribuir:

```bash
python3 -m json.tool data/systems/meu-sistema/manifest.json > /dev/null
python3 -m json.tool data/systems/meu-sistema/layouts/character.sheet.gw.json > /dev/null
python3 -m json.tool data/systems/meu-sistema/rules/actions.gw.json > /dev/null
uv run pytest tests/unit/test_system_manifest.py tests/unit/test_system_install_service.py
```

Verifique também:

- `id` e `system.id` são iguais;
- todos os paths existem;
- não há path absoluto, URL ou `..`;
- todas as capabilities necessárias foram declaradas;
- nenhum arquivo runtime, banco, cache ou dado privado entrou no pacote;
- o sistema instala pela aba Sistemas;
- uma campanha nova consegue selecionar o sistema;
- atores e itens novos abrem a ficha sem erro;
- rolagens aparecem no chat;
- combate funciona com a iniciativa esperada.

## Erros comuns

| Erro | Causa provável | Correção |
|---|---|---|
| Manifest inválido | `manifestVersion`, `type`, `apiVersion` ou `compatibility` incorretos | Compare com o manifest mínimo |
| Path rejeitado | path absoluto, URL, `..` ou arquivo inexistente | Use paths relativos ao pacote |
| Asset não carrega | capability `assets.styles` ou `assets.scripts` ausente | Declare a capability correta |
| Ficha abre vazia | `actorType` não bate com o tipo registrado | Confira `actorTypes` e layout |
| Botão não rola | `rollAction` não existe em `rules/actions.gw.json` | Crie a action ou corrija o id |
| Token não mostra recurso | mapping ausente ou path errado | Revise `mappings/token.gw.json` |
| Sistema quebra mesa antiga | mudança de schema sem migração | Em Alpha, avise breaking changes claramente |

## Distribuição

Para distribuir um sistema:

```text
meu-sistema.zip
  manifest.json
  schemas/
  layouts/
  rules/
  mappings/
  content/
  locales/
  assets/
  README.md
```

Não inclua:

- `.env`;
- banco SQLite;
- `storage/`;
- `__pycache__/`;
- `.pyc`;
- logs;
- assets privados de campanhas reais;
- conteúdo protegido por copyright sem permissão.

## Diferença entre sistema e módulo

| Precisa de... | Use sistema | Use módulo |
|---|---:|---:|
| Definir tipos de ator/item | Sim | Não |
| Definir ficha e schema | Sim | Não |
| Definir rolagens base | Sim | Às vezes, como extensão |
| Adicionar CSS opcional | Às vezes | Sim |
| Adicionar automação por campanha | Não | Sim |
| Adicionar settings de usuário/campanha | Não | Sim |
| Ser ligado/desligado por GM em cada campanha | Não | Sim |

Regra prática: se a mesa não faz sentido sem aquilo, é sistema. Se é uma melhoria opcional, é módulo.
