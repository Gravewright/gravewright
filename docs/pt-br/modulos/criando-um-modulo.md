# Criando um Módulo

> [!WARNING]
> **Module API v1 ainda está em Alpha.**
> Módulos rodam JavaScript no navegador da mesa e podem afetar experiência de usuários em campanha. Não use módulos experimentais em campanhas longas sem testar em one-shots.

Um **módulo** é uma extensão opcional do Gravewright. Ele pode adicionar CSS, JavaScript client-side, hooks, configurações, conteúdo e integrações leves sem alterar o core e sem definir um sistema de jogo completo.

Módulos são instalados globalmente, mas habilitados por campanha. Isso significa que instalar um módulo não faz ele afetar todas as mesas automaticamente: o GM decide quais módulos carregam em cada campanha.

## Quando criar um módulo

Crie um módulo quando você quer:

- adicionar comportamento opcional à mesa;
- adicionar overlay visual, tema, botões, toasts ou painéis;
- escutar hooks como `game:ready` ou `scene:loaded`;
- adicionar configurações por usuário ou campanha;
- distribuir content packs opcionais;
- melhorar a experiência de um sistema sem mudar o sistema base;
- experimentar uma feature antes de propor inclusão no core.

Não crie um módulo para definir tipos de ator, schemas fundamentais, ficha base ou regras estruturais do jogo. Para isso, crie um **sistema**.

## Modelo mental

Um módulo tem três partes:

1. **Manifest**: declara identidade, assets, capabilities, settings, dependências e compatibilidade.
2. **Assets**: CSS/JS carregados em entrypoints como `game` e `inside`.
3. **Runtime client-side**: código que registra o módulo em `window.Gravewright.modules.register(...)` e usa a API pública escopada.

O backend valida e serve arquivos declarados. Ele não executa código de módulo no servidor.

## Estrutura recomendada

```text
data/modules/meu-modulo/
  manifest.json
  README.md

  assets/
    meu-modulo.css
    meu-modulo.js

  locales/
    pt-BR.json
    en.json

  content/
    items.extras.gwpack.json
```

Estrutura mínima:

```text
data/modules/meu-modulo/
  manifest.json
  assets/meu-modulo.js
```

## Manifest mínimo

```json
{
  "schemaVersion": 1,
  "type": "module",
  "id": "meu-modulo",
  "name": "Meu Módulo",
  "version": "0.1.0",
  "apiVersion": "1",
  "description": "Módulo de exemplo para Gravewright.",
  "authors": [
    { "name": "Seu Nome" }
  ],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": [
    "assets.scripts",
    "hooks.client",
    "assets.ui"
  ],
  "display": {
    "color": "#7c5cff"
  },
  "module": {
    "id": "meu-modulo",
    "entrypoints": {
      "game": {
        "scripts": ["assets/meu-modulo.js"]
      }
    }
  }
}
```

### Regras importantes

- Use `schemaVersion`, não `manifestVersion`.
- `type` deve ser `"module"`.
- `apiVersion` deve ser `"1"`.
- `id` e `module.id` devem ser iguais.
- IDs usam kebab-case minúsculo: `meu-modulo`.
- Assets precisam ser declarados em `module.entrypoints`.
- O backend só serve arquivos declarados e validados.
- Paths absolutos, URLs, `..`, barra dupla e arquivos fora do pacote são rejeitados.

## Entrypoints

Entrypoints dizem onde os assets do módulo carregam.

```json
{
  "module": {
    "entrypoints": {
      "game": {
        "styles": ["assets/game.css"],
        "scripts": ["assets/game.js"]
      },
      "inside": {
        "styles": ["assets/inside.css"],
        "scripts": ["assets/inside.js"]
      }
    }
  }
}
```

Entrypoints atualmente aceitos:

| Entrypoint | Uso |
|---|---|
| `game` | mesa/campanha ativa |
| `inside` | telas internas de gestão, quando suportado |

Limites atuais:

| Limite | Valor |
|---|---:|
| CSS por entrypoint | 16 |
| JS por entrypoint | 16 |
| paths de asset declarados | 64 |
| tamanho máximo de asset servido | 2 MB |
| tamanho máximo de path | 240 caracteres |
| extensões de CSS | `.css` |
| extensões de JS | `.js`, `.mjs` |

## Capabilities

Capabilities declaram o que o módulo pretende usar. APIs privilegiadas exigem capabilities específicas.

| Capability | Permite |
|---|---|
| `assets.ui` | interações de UI, canvas/cena e helpers visuais |
| `assets.styles` | carregar CSS |
| `assets.scripts` | carregar JS |
| `chat.cards` | enviar mensagens/cards para o chat via API pública |
| `content.packs` | distribuir packs de conteúdo |
| `hooks.client` | registrar hooks client-side |
| `locales` | fornecer arquivos de tradução |
| `settings` | declarar e alterar settings do módulo |
| `sheets.extends` | extensão de ficha, reservado/experimental |
| `rules.extends` | extensão de regras, reservado/experimental |
| `tokens.extends` | interagir com tokens via API pública |

Capabilities proibidas são rejeitadas:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

Declare só o que você usa. Isso facilita auditoria e reduz a superfície de risco.

## Runtime básico

Crie `assets/meu-modulo.js`:

```js
(function () {
  window.Gravewright.modules.register({
    id: "meu-modulo",

    init(api, payload) {
      // Chamado durante a inicialização do runtime de módulos.
      // Use para registrar hooks e preparar estado local.
      api.hooks.on("game:ready", ({ context }) => {
        api.ui.toast(`Meu Módulo carregado em ${context.campaign?.name || "campanha"}`);
      });
    },

    ready(api, payload) {
      // Chamado depois de game:ready para este módulo.
      const user = api.game.user();
      console.debug("Meu Módulo pronto", { user });
    }
  });
})();
```

O `id` registrado no JS deve ser igual ao `id` do manifest. Se não bater, o runtime não consegue associar o código carregado ao manifesto validado.

## API pública do módulo

O runtime recebe um objeto `api` escopado ao módulo:

```js
init(api, payload) {}
ready(api, payload) {}
```

Namespaces disponíveis:

```text
api.version
api.capabilities
api.hooks
api.game
api.chat
api.scene
api.settings
api.tokens
api.tools
api.ui
```

### `api.capabilities`

```js
api.capabilities.has("settings");
api.capabilities.require("settings", "minha-feature");
api.capabilities.requirement("settings.get");
api.capabilities.list();
```

Use para falhar cedo quando uma capability necessária não foi declarada.

### `api.game`

```js
const context = api.game.context();
const campaign = api.game.campaign();
const scene = api.game.scene();
const user = api.game.user();
```

Esses métodos retornam cópias congeladas dos dados de contexto. Não tente mutar o retorno. O backend continua sendo autoritativo.

### `api.hooks`

Exige capability `hooks.client`.

```js
const off = api.hooks.on("scene:loaded", ({ scene }) => {
  console.log("Cena carregada", scene);
});

api.hooks.once("game:ready", ({ context }) => {
  console.log("Pronto", context);
});

off();
```

Hooks oficiais atuais:

```text
module:init
module:ready
module:failed
game:ready
campaign:loaded
scene:loaded
```

Você pode consultar:

```js
api.hooks.official();
```

### `api.ui`

Exige capability `assets.ui`.

```js
api.ui.toast("Olá da extensão", { duration: 4000 });
api.ui.openModal("my-modal-id");
api.ui.closeModal("my-modal-id");
```

Use UI APIs para interação leve. Não manipule DOM interno do core salvo quando a documentação permitir.

### `api.tools`

Exige capability `assets.ui`.

```js
const activeTool = api.tools.activeTool();
```

### `api.scene`

Exige capability `assets.ui`.

```js
const canvas = api.scene.activeCanvas();
const camera = api.scene.activeCameraForScene(sceneId);
```

Use com cuidado: canvas e câmera são APIs de UI, não fonte autoritativa de estado.

### `api.tokens`

Exige capability `tokens.extends`.

```js
api.tokens.centerOn(tokenId);
```

### `api.chat`

Exige capability `chat.cards`.

```js
api.chat.send({
  type: "module-message",
  text: "Mensagem enviada pelo módulo"
});
```

A API dispara um evento client-side `vtt:chat-send`. O core decide como transformar isso em mensagem real.

### `api.settings`

Exige capability `settings`.

```js
const definitions = api.settings.definitions();
const all = api.settings.all();
const color = api.settings.get("dice.color", "#7c5cff");
await api.settings.set("dice.color", "#ff006e");
```

`settings.set` envia para:

```text
POST /modules/settings
```

O payload inclui `module_id`, `key`, `value` e `campaign_id`.

## Declarando settings

No manifest:

```json
{
  "capabilities": ["settings"],
  "module": {
    "id": "meu-modulo",
    "settings": [
      {
        "key": "ui.enabled",
        "scope": "campaign",
        "type": "boolean",
        "default": true,
        "label": "Habilitar UI extra"
      },
      {
        "key": "dice.color",
        "scope": "user",
        "type": "string",
        "default": "#7c5cff",
        "label": "Cor do dado",
        "maxLength": 32
      },
      {
        "key": "automation.mode",
        "scope": "campaign",
        "type": "enum",
        "default": "assistive",
        "label": "Modo de automação",
        "choices": [
          { "value": "off", "label": "Desligado" },
          { "value": "assistive", "label": "Assistivo" },
          { "value": "strict", "label": "Estrito" }
        ]
      }
    ]
  }
}
```

Scopes aceitos:

| Scope | Significado |
|---|---|
| `global` | valor global da instalação |
| `campaign` | valor por campanha |
| `user` | valor por usuário |

Tipos aceitos:

| Tipo | Valor esperado |
|---|---|
| `boolean` | `true`/`false` |
| `string` | texto |
| `number` | número |
| `integer` | inteiro |
| `enum` | uma das opções declaradas |

Regras de chave:

- começa com letra minúscula;
- usa letras minúsculas, números e `_`;
- pode usar pontos para namespaces: `dice.color`, `ui.enabled`;
- tamanho máximo: 96 caracteres.

## Dependências, conflitos e load order

```json
{
  "dependencies": ["base-rules"],
  "conflicts": [
    { "id": "alternate-rules" }
  ],
  "loadOrder": 10
}
```

Regras:

- dependências precisam estar instaladas, habilitadas globalmente e habilitadas na campanha;
- um módulo não pode ser habilitado se conflitar com outro módulo já habilitado;
- conflitos são checados nos dois sentidos;
- você não pode desabilitar um módulo se outro módulo habilitado depende dele;
- `loadOrder` deve estar entre `-10000` e `10000`;
- dependências carregam antes de dependentes;
- depois disso, módulos carregam por `loadOrder`, nome e id.

Use dependências para contratos reais, não para ordenar cosmética. Para só carregar antes/depois, prefira `loadOrder`.

## Content packs em módulos

Módulos podem distribuir conteúdo opcional:

```json
{
  "capabilities": ["content.packs"],
  "module": {
    "contentPacks": [
      {
        "id": "extra-weapons",
        "type": "item_pack",
        "label": "Armas Extras",
        "path": "content/items.extra-weapons.gwpack.json"
      }
    ]
  }
}
```

Tipos aceitos em módulos:

- `actor_pack`;
- `item_pack`;
- `spell_pack`;
- `journal_pack`.

O conteúdo precisa fazer sentido para o sistema ativo da campanha.

## Compatibilidade com sistemas

Use `module.systems` quando o módulo só funciona com sistemas específicos:

```json
{
  "module": {
    "systems": {
      "dnd5e": {
        "minimum": "0.3.0",
        "verified": "0.3.0"
      }
    }
  }
}
```

Na Alpha, trate compatibilidade de sistema como documentação operacional: deixe claro em quais sistemas você testou.

## Locales

```json
{
  "capabilities": ["locales"],
  "module": {
    "locales": {
      "pt-BR": "locales/pt-BR.json",
      "en": "locales/en.json"
    }
  }
}
```

## Exemplo completo: módulo de toast ao abrir cena

`manifest.json`:

```json
{
  "schemaVersion": 1,
  "type": "module",
  "id": "scene-welcome",
  "name": "Scene Welcome",
  "version": "0.1.0",
  "apiVersion": "1",
  "description": "Mostra um toast quando uma cena é carregada.",
  "authors": [{ "name": "Seu Nome" }],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": [
    "assets.scripts",
    "assets.ui",
    "hooks.client",
    "settings"
  ],
  "display": {
    "color": "#22c55e"
  },
  "module": {
    "id": "scene-welcome",
    "entrypoints": {
      "game": {
        "scripts": ["assets/scene-welcome.js"]
      }
    },
    "settings": [
      {
        "key": "toast.enabled",
        "scope": "user",
        "type": "boolean",
        "default": true,
        "label": "Mostrar toast ao carregar cena"
      }
    ]
  }
}
```

`assets/scene-welcome.js`:

```js
(function () {
  window.Gravewright.modules.register({
    id: "scene-welcome",

    init(api) {
      api.hooks.on("scene:loaded", ({ scene }) => {
        if (!api.settings.get("toast.enabled", true)) return;
        api.ui.toast(`Cena carregada: ${scene?.name || "sem nome"}`);
      });
    }
  });
})();
```

## Empacotamento ZIP

Layouts aceitos:

```text
scene-welcome.zip
  manifest.json
  assets/scene-welcome.js
```

ou:

```text
scene-welcome.zip
  scene-welcome/
    manifest.json
    assets/scene-welcome.js
```

O upload instala em staging antes de mover para `data/modules/<module-id>/`. O zip é tratado como input não confiável.

Não inclua:

- `.env`;
- banco SQLite;
- `storage/`;
- `node_modules/`;
- `__pycache__/`;
- `.pyc`;
- logs;
- dados de campanhas reais;
- assets sem licença.

## Instalando e habilitando

Fluxo operacional:

1. Instale o módulo pela tela Inside Modules ou endpoint de upload.
2. Habilite globalmente.
3. Entre na campanha.
4. Habilite o módulo para aquela campanha.
5. Recarregue a mesa.
6. Verifique console, status e comportamento.

Rotas de gestão existentes:

```text
POST /modules/upload
POST /modules/install
POST /modules/enable
POST /modules/disable
POST /modules/remove
POST /campaigns/modules/enable
POST /campaigns/modules/disable
POST /modules/settings
```

## Checklist de validação

Antes de distribuir:

```bash
python3 -m json.tool data/modules/meu-modulo/manifest.json > /dev/null
uv run pytest tests/unit/test_module_manifest.py tests/unit/test_module_install_service.py tests/unit/test_module_client_api.py
```

Verifique:

- `id` e `module.id` batem;
- paths existem;
- extensions são `.css`, `.js` ou `.mjs`;
- capabilities correspondem ao que a API usa;
- settings têm `key`, `scope`, `type`, `default` coerente;
- dependências e conflitos usam ids válidos;
- módulo instala por zip;
- módulo habilita globalmente;
- módulo habilita em campanha;
- `window.Gravewright.modules.list()` mostra o módulo;
- console não tem erro de capability;
- desabilitar o módulo remove o comportamento esperado.

## Erros comuns

| Erro | Causa provável | Correção |
|---|---|---|
| `requires a scoped module api` | uso da API root em vez do `api` passado para `init/ready` | use sempre o `api` escopado |
| capability ausente | manifest não declara a capability exigida | adicione a capability correta |
| módulo não registra | `id` no JS diferente do manifest | iguale os ids |
| script não carrega | path não declarado ou extensão inválida | declare em `entrypoints.game.scripts` |
| CSS não aplica | `assets.styles` ausente ou path errado | declare capability e path |
| setting não salva | scope/tipo/key inválidos ou CSRF/contexto ausente | revise manifest e campanha ativa |
| dependência bloqueia habilitação | dependência não habilitada na campanha | habilite dependências primeiro |
| conflito bloqueia habilitação | módulo conflita com outro ativo | desabilite o conflitante ou remova conflito |

## Boas práticas

- Prefira hooks e APIs públicas a manipulação direta de DOM.
- Não persista estado crítico só no navegador.
- Não envie dados sensíveis para logs.
- Não assuma que um sistema específico está ativo sem checar contexto.
- Use settings para comportamento configurável.
- Falhe silenciosamente quando uma API opcional não existir.
- Documente quais sistemas foram testados.
- Mantenha módulos pequenos: um módulo deve fazer uma coisa clara.
