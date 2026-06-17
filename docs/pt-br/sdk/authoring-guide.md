# Guia de autoria de pacotes

Comece por [`declarative-model.md`](declarative-model.md), [`author-complete-checklist.md`](author-complete-checklist.md) e [`power-map.md`](power-map.md) antes de usar este workflow. Essas páginas explicam o modelo de pacote, a superfície completa do autor e como escolher entre dados de manifesto e chamadas de runtime da SDK.

Este guia percorre o workflow recomendado para autores de pacote SDK.

## 1. Escolha o kind do pacote

| Objetivo | Kind |
|---|---|
| Construir uma implementação de regras base de RPG | `ruleset` |
| Adicionar comportamento opcional a uma campanha | `addon` |
| Compartilhar código/assets entre pacotes | `library` |
| Mudar a apresentação visual | `theme` |
| Distribuir conteúdo de jogo importável | `content` |
| Distribuir mídia reutilizável | `assets` |

## 2. Faça o scaffold com a CLI

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"
```

Os pacotes gerados devem ficar em:

```text
data/packages/{kind_plural}/{id}/
```

## 3. Edite o `manifest.json`

Decisões obrigatórias:

- `kind` do pacote;
- `id` estável;
- `name` legível;
- `version` do pacote;
- faixa de compatibilidade;
- conjunto mínimo de capabilities;
- modo de ativação;
- entrypoints;
- dados de `provides`;
- settings, dependencies, conflicts e metadados de distribuição quando necessário.

## 4. Mantenha as capabilities mínimas

Comece sem capabilities, depois adicione apenas o que o pacote usa.

Exemplos:

- theme só com CSS: `assets.styles`
- addon com JS de navegador e toasts: `assets.scripts`, `assets.ui`
- addon com settings: `settings`
- barramento de eventos de pacote: `bus.publish`, `bus.subscribe`
- fichas de ruleset: `sheets.declarative`, `sheets.runtime`
- runtime de combate: `combat.runtime`
- pacote de content pack: `content.packs`

## 5. Adicione dados declarativos de pacote

Prefira dados declarativos a código de runtime.

Rulesets comumente declaram:

```text
schemas/
layouts/
rules/
mappings/
content/
locales/
assets/
```

Adicione cada path de arquivo referenciado ao manifesto via `entrypoints` ou `provides`.

## 6. Adicione runtime de navegador só quando necessário

Pacotes com `assets.scripts` podem registrar comportamento de navegador:

```js
window.GravewrightSDK.register({
  id: "my-package",
  ready(sdk, { context }) {
    console.log(context);
  },
});
```

Código de runtime de navegador deve tratar o servidor como autoritativo. Use métodos da SDK para expressar intenções e integrar com superfícies de UI documentadas.

## 7. Valide localmente

```bash
grave package validate data/packages/my-package
grave package validate data/packages/my-package --json
grave package doctor my-package
```

Corrija todos os erros de validação antes de instalar ou publicar.

## 8. Instale e ative

```bash
grave package install my-package --yes --enable
```

Para pacotes com escopo de campanha:

```bash
grave campaign package activate <campaign_id> my-package
```

Rulesets são exclusive. Addons, themes, content e assets são kinds de pacote com ativação múltipla. Libraries são dependências passivas.

## 9. Teste na mesa

Rode o Gravewright:

```bash
grave run --open
```

Teste:

- o manifesto carrega;
- o pacote aparece nas listas de pacotes;
- as capabilities são apropriadas;
- os styles e scripts do entrypoint carregam;
- `window.GravewrightSDK.register` tem sucesso;
- o comportamento do pacote funciona após `ready`;
- as settings persistem no escopo pretendido;
- os content packs carregam;
- as chaves de locale resolvem;
- ativação/desativação se comportam corretamente;
- os diagnósticos do pacote estão limpos.

## 10. Documente o comportamento do pacote

Cada pacote deve incluir um README cobrindo:

- propósito;
- kind do pacote;
- versões suportadas do Gravewright;
- capabilities solicitadas e por quê;
- passos de install/enable/activate;
- settings;
- content packs/assets;
- eventos emitidos e consumidos;
- limitações conhecidas;
- licença e direitos de conteúdo.

## 11. Publique com segurança

Antes de publicar:

```bash
grave package validate data/packages/my-package
grave package doctor my-package
grave backup -o before-package-release.zip --include-assets --include-packages --verify
grave lock -o grave.lock.json
```

Checklist de release recomendado:

- versão incrementada;
- `compatibility.verified` atualizado após testes;
- README atualizado;
- changelog atualizado;
- nenhuma API privada/proibida usada;
- nenhuma capability desnecessária declarada;
- metadados de distribuição (zip/git/diretório) corretos;
- licença/direitos de conteúdo claros.
