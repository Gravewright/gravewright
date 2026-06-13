# Criando um Sistema

> [!WARNING]
> **System API v1 está em Alpha.**
>
> Sistemas são a superfície de extensão mais sensível do Gravewright porque definem schema, fichas, regras, rolagens, pacotes, mapeamentos de token, labels e comportamento de combate.
>
> Releases Alpha podem alterar campos ou comportamento. Teste sistemas customizados em one-shots e ambientes de teste antes de confiar campanhas longas a eles.

Um **sistema** é um pacote declarativo que ensina o Gravewright a entender um jogo específico: quais tipos de atores existem, quais tipos de itens existem, qual formato de dados cada entidade usa, como as fichas renderizam, quais rolagens existem, como a iniciativa funciona, quais labels devem aparecer e qual conteúdo inicial pode ser importado.

Sistemas não são plugins arbitrários de backend.

O servidor lê e valida arquivos declarativos. JavaScript de sistema, quando usado, roda no navegador e deve usar apenas APIs públicas documentadas.

## Quando Criar um Sistema

Crie um sistema quando você precisa definir as regras estruturais de um jogo:

* tipos de ator como `character`, `monster`, `npc` ou `vehicle`;
* tipos de item como `weapon`, `armor`, `spell` ou `feat`;
* fichas declarativas de ator e item;
* dados derivados, fórmulas, rolagens e ações;
* mapeamentos entre dados de ficha e tokens;
* configuração de combate, iniciativa e recursos;
* vocabulário de ruleset e labels de UI;
* arquivos de locale;
* pacotes de conteúdo que pertencem ao sistema.

Não crie um sistema para pequenas melhorias visuais, automação opcional ou comportamento que deve ser ligado e desligado por campanha. Use um **módulo** para isso.

## Modelo Mental

Um sistema tem quatro camadas principais:

1. **Manifest**: identidade, compatibilidade, capabilities e mapa de arquivos do pacote.
2. **Dados**: JSON Schemas que validam dados de atores e itens.
3. **UI declarativa**: layouts `.sheet.gw.json` que descrevem fichas.
4. **Regras**: arquivos `.gw.json` para ações, fórmulas, dados derivados, combate, validação e mapeamentos.

Opcionalmente, um sistema também pode incluir:

* CSS para visual customizado;
* JavaScript client-side para pontos documentados de extensão;
* labels;
* locales;
* pacotes de conteúdo.

## Layout Recomendado do Pacote

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
    en.json
    pt-BR.json
  assets/
    meu-sistema.css
    meu-sistema.js
```

Para um sistema mínimo, você precisa apenas de:

```text
data/systems/meu-sistema/
  manifest.json
  schemas/
    character.schema.json
  layouts/
    character.sheet.gw.json
```

Um sistema útil normalmente também terá:

* `rules/actions.gw.json`;
* `rules/combat.gw.json`;
* arquivos de locale;
* pelo menos um arquivo CSS;
* JavaScript opcional de sistema para pontos documentados de extensão de ficha ou combate.

## Manifest Mínimo

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
    {
      "name": "Seu Nome"
    }
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

Regras importantes:

* `manifestVersion` deve ser `1`;
* `type` deve ser `"system"`;
* `apiVersion` deve ser `"1"`;
* o `id` de topo e `system.id` devem ser iguais;
* IDs usam kebab-case em minúsculas, como `meu-sistema`;
* `system.storage.model` deve ser `"scoped-json-v1"`;
* paths de pacote devem ser relativos à raiz do pacote;
* URLs, paths absolutos, `..` e arquivos fora do pacote são rejeitados;
* declare apenas capabilities que correspondem a arquivos ou APIs que você realmente usa.

## Capabilities

Capabilities descrevem o que o sistema fornece.

| Capability           | Use quando o sistema...               |
| -------------------- | ------------------------------------- |
| `actors.register`    | declara tipos de ator                 |
| `items.register`     | declara tipos de item                 |
| `sheets.declarative` | fornece layouts declarativos de ficha |
| `rules.declarative`  | fornece arquivos de regras            |
| `content.packs`      | fornece pacotes de conteúdo           |
| `tokens.mappings`    | mapeia dados de ator/item para tokens |
| `dice.roll`          | declara ações de rolagem              |
| `chat.cards`         | customiza cards de chat               |
| `roll.toast`         | customiza toasts de rolagem           |
| `locales`            | fornece arquivos de locale            |
| `assets.ui`          | contribui comportamento de UI         |
| `assets.styles`      | contribui CSS                         |
| `assets.scripts`     | contribui JavaScript                  |
| `combat.config`      | fornece configuração de combate       |
| `combat.hooks`       | registra hooks de combate no cliente  |
| `rolls.intent`       | usa intents semânticas de rolagem     |

Capabilities não são apenas decoração.

Elas documentam o pacote para usuários e mantenedores, e permitem que o backend/runtime rejeite comportamento sem suporte.

## Criando o Primeiro Schema de Ator

Crie `schemas/character.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Personagem do Meu Sistema",
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "attributes": {
      "type": "object",
      "properties": {
        "strength": {
          "type": "integer",
          "default": 10
        },
        "dexterity": {
          "type": "integer",
          "default": 10
        },
        "strengthMod": {
          "type": "integer",
          "default": 0
        },
        "dexterityMod": {
          "type": "integer",
          "default": 0
        }
      }
    },
    "combat": {
      "type": "object",
      "properties": {
        "hp": {
          "type": "integer",
          "default": 10
        },
        "maxHp": {
          "type": "integer",
          "default": 10
        },
        "initiative": {
          "type": "integer",
          "default": 0
        }
      }
    }
  }
}
```

Gravewright armazena metadados centrais do ator separadamente dos dados de ficha do sistema.

Em layouts e regras, normalmente você referencia dados do sistema através de paths como:

```text
sheet.attributes.strength
sheet.combat.hp
sheet.combat.maxHp
```

Boa prática: mantenha schemas estáveis e previsíveis.

Durante Alpha, mudanças de schema podem tornar mesas antigas difíceis de recuperar.

## Criando a Primeira Ficha

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

Nós úteis de layout:

| Tipo              | Uso                                         |
| ----------------- | ------------------------------------------- |
| `tabs`            | container com abas                          |
| `section`         | bloco visual com título                     |
| `row`             | linha flexível                              |
| `grid`            | grid; aceita `columns`                      |
| `column`          | coluna                                      |
| `divider`         | separador visual                            |
| `spacer`          | espaço visual                               |
| `abilityCard`     | habilidade com valor, modificador e rolagem |
| `rollableStat`    | linha de stat clicável                      |
| `combatStat`      | estatística de combate                      |
| `resourceBar`     | barra de recurso valor/máximo               |
| `imageField`      | imagem readonly                             |
| `readonlyField`   | valor readonly                              |
| `text`            | texto simples                               |
| `badge`           | label/badge curto                           |
| `itemList`        | lista/tabela de itens vinculados            |
| `rollButton`      | botão de rolagem                            |
| `actionButton`    | botão de ação                               |
| `incrementButton` | botão de incremento                         |
| `decrementButton` | botão de decremento                         |

Nem todo campo está totalmente travado em JSON Schema ainda.

Alpha permite propriedades adicionais para que o renderer possa evoluir. Documente qualquer nó ou variant customizado de que seu sistema dependa.

## Criando Ações e Rolagens

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

Valores de intent em v1:

| Intent       | Significado                |
| ------------ | -------------------------- |
| `check`      | teste genérico             |
| `save`       | salvaguarda/resistência    |
| `attack`     | ataque                     |
| `damage`     | dano                       |
| `initiative` | iniciativa                 |
| `skill`      | perícia                    |
| `tool`       | ferramenta                 |
| `custom`     | caso específico do sistema |

Use `intent` para semântica, não aparência.

Aparência deve ser controlada por `chatCard`, `rollToast`, CSS e mapeamentos.

## Configurando Combate

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
    {
      "id": "action",
      "label": "Ação"
    },
    {
      "id": "bonus",
      "label": "Ação Bônus"
    },
    {
      "id": "reaction",
      "label": "Reação"
    }
  ]
}
```

Use `combat.config` na lista de capabilities ao declarar esse arquivo.

Texto de UI de combate deve vir de configuração de combate, labels ou arquivos de locale pertencentes ao sistema quando o texto padrão da engine não for adequado para o sistema.

## Mapeando Tokens

Se seu sistema usa tokens com PV, nomes, retratos ou estados derivados, declare um mapeamento:

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

Referencie no manifest:

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

## Adicionando Assets

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

CSS é o caminho preferido para customização visual.

JavaScript deve ser reservado para comportamento documentado que fichas e regras declarativas ainda não conseguem expressar.

## Fornecendo Labels de UI do Sistema

Sistemas podem fornecer labels de UI para renderização de fichas através do seu asset de navegador.

Registre labels em `assets/meu-sistema.js`:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("meu-sistema", {
    labels: {
      actorName: "Nome",
      levelPrefix: "Nível",
      equipped: "Equipado",
      spellCirclePrefix: "Círculo",
      prepared: "Preparado",
      active: "Ativo",
      inactive: "Inativo",
      qtyPrefix: "Qtd.",
      portrait: "Retrato",
      token: "Token",
      uploadPortrait: "Enviar retrato",
      uploadToken: "Enviar token",
      cancel: "Cancelar",
      roll: "Rolar",
      rollDialogTitle: "Rolagem",
      healed: "curou",
      tookDamage: "sofreu",
      reducedFrom: "reduzido de"
    }
  });
})();
```

Use labels para vocabulário de ruleset e texto específico de idioma que a engine não consegue saber com segurança.

A engine fornece fallbacks em inglês, mas sistemas públicos devem definir suas próprias labels ao distribuir uma experiência em outro idioma ou específica de um ruleset.

## Adicionando Hooks de Ficha

Exemplo de JavaScript de sistema:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("meu-sistema", {
    renderSection(node, variant, renderContext, helpers) {
      if (variant !== "special") return null;

      const section = helpers.el("section", "meu-sistema-especial");
      section.appendChild(helpers.el("h3", null, node.label || "Especial"));
      return section;
    },

    renderHeaderIdentity(main, bundle, helpers) {
      const actor = bundle.actor || {};
      main.appendChild(helpers.el("div", "meu-sistema-subtitulo", actor.type || ""));
    },

    autoFitWidth(actorType) {
      if (actorType === "character") return 820;
      return null;
    }
  });
})();
```

APIs de navegador disponíveis para sistemas:

* `window.GravewrightSheets.registerSystem(systemId, hooks)`;
* `window.GravewrightSheets.helpers`;
* `window.GravewrightSheets.getLabels(systemId)`;
* `window.GravewrightCombat.registerSystem(systemId, plugin)`.

Evite variáveis internas, stores privados, estrutura DOM não documentada, comportamento de fallback e internals de renderer.

## Adicionando Hooks e Slots de Combate

Sistemas podem registrar hooks e slots leves de combate:

```js
(function () {
  const Combat = window.GravewrightCombat;
  if (!Combat || typeof Combat.registerSystem !== "function") return;

  Combat.registerSystem("meu-sistema", {
    hooks: {
      participantMeta({ participant }) {
        return participant?.actor_type || "";
      }
    },

    slots: {
      participantActions({ participant }) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "meu-sistema-acao-combate";
        button.textContent = participant?.actor_type || "Ação";
        return button;
      }
    }
  });
})();
```

Prefira configuração de combate, CSS, labels, hooks e slots em vez de substituir o renderer inteiro de combate.

Substituição completa do renderer de combate não faz parte da API pública estável durante Alpha.

## Localização

No manifest:

```json
{
  "capabilities": ["locales"],
  "system": {
    "locales": {
      "en": "locales/en.json",
      "pt-BR": "locales/pt-BR.json"
    }
  }
}
```

Exemplo de `locales/pt-BR.json`:

```json
{
  "MEU_SISTEMA.Personagem": "Personagem",
  "MEU_SISTEMA.Forca": "Força",
  "MEU_SISTEMA.Iniciativa": "Iniciativa"
}
```

Prefira `labelKey` em layouts, manifests, regras e pacotes de conteúdo quando o texto precisa ser traduzido.

## Adicionando Pacotes de Conteúdo

No manifest:

```json
{
  "capabilities": ["content.packs"],
  "system": {
    "contentPacks": [
      {
        "id": "armas-iniciais",
        "type": "item_pack",
        "label": "Armas Iniciais",
        "path": "content/items.weapons.gwpack.json"
      }
    ]
  }
}
```

Tipos aceitos de pack:

* `actor_pack`;
* `item_pack`;
* `spell_pack`;
* `journal_pack`;
* `table_pack`;
* `condition_pack`.

Um pack deve usar o mesmo modelo de dados esperado pelos schemas do sistema.

## Checklist de Validação

Antes de distribuir:

```bash
python3 -m json.tool data/systems/meu-sistema/manifest.json > /dev/null
python3 -m json.tool data/systems/meu-sistema/layouts/character.sheet.gw.json > /dev/null
python3 -m json.tool data/systems/meu-sistema/rules/actions.gw.json > /dev/null
uv run pytest tests/unit/test_system_manifest.py tests/unit/test_system_install_service.py
```

Verifique também:

* `id` e `system.id` são iguais;
* todo path declarado existe;
* não há paths absolutos, URLs ou segmentos `..`;
* todas as capabilities necessárias foram declaradas;
* nenhum runtime file, banco de dados, cache ou dado privado entrou no pacote;
* o sistema instala pela tela de Sistemas;
* uma campanha nova consegue selecionar o sistema;
* atores e itens novos abrem suas fichas sem erro;
* labels renderizam corretamente;
* rolagens aparecem no chat;
* combate funciona com a lógica de iniciativa esperada.

## Erros Comuns

| Erro                           | Causa provável                                                                  | Correção                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Manifest inválido              | `manifestVersion`, `type`, `apiVersion` ou campos de `compatibility` incorretos | Compare com o manifest mínimo                                                      |
| Path rejeitado                 | Path absoluto, URL, `..` ou arquivo ausente                                     | Use paths relativos ao pacote                                                      |
| Asset não carrega              | Capability `assets.styles` ou `assets.scripts` ausente                          | Declare a capability correta                                                       |
| Ficha abre vazia               | `actorType` não bate com o tipo de ator registrado                              | Confira `actorTypes` e metadados do layout                                         |
| Botão de rolagem não faz nada  | `rollAction` não existe em `rules/actions.gw.json`                              | Crie a ação ou corrija o id                                                        |
| Token não mostra recurso       | Mapeamento ausente ou path errado                                               | Revise `mappings/token.gw.json`                                                    |
| Labels não aparecem            | Script do sistema não carregou ou labels não foram registradas                  | Confira `assets.scripts`, capabilities e `window.GravewrightSheets.registerSystem` |
| Sistema quebra uma mesa antiga | Schema mudou sem migração                                                       | Durante Alpha, marque breaking changes claramente                                  |

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

* `.env`;
* bancos SQLite;
* `storage/`;
* `__pycache__/`;
* `.pyc`;
* logs;
* dados reais de campanha;
* assets sem licença.

## README para um Sistema Público

Um pacote de sistema deve incluir um `README.md` com:

* versão suportada do Gravewright;
* notas de jogo/licença;
* tipos de ator e item;
* recursos de ficha;
* rolagens e comportamento de combate suportados;
* labels/locales incluídos;
* pacotes de conteúdo incluídos;
* limitações conhecidas de Alpha;
* avisos de migração para mudanças quebráveis de schema.
