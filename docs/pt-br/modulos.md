# Module API v1

Módulos são extensões opcionais do Gravewright. Eles podem adicionar assets de UI, hooks client-side, configurações, content packs e integrações leves sem alterar o core e sem substituir o sistema de jogo ativo.

> [!WARNING]
> **API em Alpha.** A Module API v1 existe para permitir experimentação pública, mas ainda pode ter breaking changes entre versões Alpha.

## Comece aqui

- [Criando um módulo](modulos/criando-um-modulo.md)
- [APIs de extensão](api/extensoes.md)
- [HTTP API](api/http.md)
- [Realtime API](api/realtime.md)

## Resumo rápido

Um módulo é instalado em:

```text
<GRAVEWRIGHT_DATA_DIR>/modules/<module-id>/manifest.json
```

E tem dois níveis de ativação:

1. **Instalação/habilitação global**: o owner disponibiliza o pacote.
2. **Habilitação por campanha**: cada GM decide quais módulos carregam naquela campanha.

Isso evita que um módulo afete todas as mesas só por ter sido instalado.

## Manifest mínimo

```json
{
  "schemaVersion": 1,
  "type": "module",
  "id": "sample-module",
  "name": "Sample Module",
  "version": "0.1.0",
  "apiVersion": "1",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": ["assets.scripts", "hooks.client", "assets.ui"],
  "module": {
    "id": "sample-module",
    "entrypoints": {
      "game": {
        "scripts": ["assets/sample-module.js"]
      }
    }
  }
}
```

## Runtime mínimo

```js
(function () {
  window.Gravewright.modules.register({
    id: "sample-module",
    init(api) {
      api.hooks.on("game:ready", () => {
        api.ui.toast("Sample Module carregado");
      });
    }
  });
})();
```

## Capabilities aceitas

```text
assets.ui
assets.styles
assets.scripts
chat.cards
content.packs
hooks.client
locales
settings
sheets.extends
rules.extends
tokens.extends
```

Capabilities proibidas:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

## APIs disponíveis no navegador

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

APIs privilegiadas exigem capabilities declaradas no manifest. Use sempre o `api` escopado recebido em `init(api)` ou `ready(api)`, não a API root global.

## Rotas de gestão

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

Gestão por campanha exige acesso de GM.

## Licença

A especificação, exemplos e documentação da Module API são materiais MIT. A implementação do loader, validador, storage e runtime de módulos é Apache-2.0.
