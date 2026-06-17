# Checklist 100% do autor de SDK

Este checklist define o que uma "documentação de SDK completa" deve permitir um autor fazer.

Use-o como teste de aceitação para um pacote e para a própria documentação. Se um autor não consegue completar um item apenas com os docs, os docs estão incompletos.

## 1. Escolha o kind do pacote

| Objetivo | Kind | Padrão de ativação exigido | Comece com |
|---|---|---|---|
| Criar um sistema/ruleset de jogo | `ruleset` | `scope: "campaign"`, `mode: "exclusive"` | tipos de actor/item, sheets, rules, combate, conteúdo |
| Adicionar comportamento opcional | `addon` | `scope: "campaign"`, `mode: "multiple"` | settings, scripts, plugins, UI, conteúdo |
| Compartilhar código/dados de dependência | `library` | `mode: "passive"` | dependências e assets/dados compartilhados fornecidos |
| Mudar a apresentação visual | `theme` | `mode: "multiple"` | styles, assets de UI, settings |
| Distribuir dados importáveis | `content` | `mode: "multiple"` | content packs |
| Distribuir mídia | `assets` | `mode: "multiple"` | metadados de asset pack e paths de mídia |

## 2. Escreva o contrato do manifesto

Todo autor de pacote deve conseguir definir:

- `$schema`
- `schemaVersion`
- `sdkVersion`
- `kind`
- `id`
- `name`
- `version`
- `description`
- `authors`
- `license`
- `homepage`
- `repository`
- `compatibility.minimum`
- `compatibility.verified`
- `compatibility.maximum`
- `capabilities`
- `activation.scope`
- `activation.mode`
- `entrypoints.game.styles`
- `entrypoints.game.scripts`
- `settings`
- `provides`
- `dependencies`
- `conflicts`
- `distribution`
- `display`

Veja [`manifest.md`](manifest.md) e [`declarative-model.md`](declarative-model.md).

## 3. Declare capabilities intencionalmente

O autor deve saber por que cada capability está presente.

| Família de capability | O autor pode usar para | Docs principais |
|---|---|---|
| `actors.*` | definir tipos de actor e contratos de comportamento de actor | [`declarative-model.md`](declarative-model.md), [`manifest.md`](manifest.md) |
| `items.*` | definir tipos de item e contratos de comportamento de item | [`declarative-model.md`](declarative-model.md), [`manifest.md`](manifest.md) |
| `sheets.*` | declarar sheets ou adicionar plugins de runtime de sheet | [`runtime.md`](runtime.md), [`reference.md`](reference.md) |
| `rules.*` | fornecer documentos de regras ou estender regras | [`declarative-model.md`](declarative-model.md) |
| `dice.*`, `rolls.*` | suportar comportamento e intents de rolagem | [`reference.md`](reference.md) |
| `combat.*` | configurar combate ou registrar plugins/painéis de combate | [`reference.md`](reference.md) |
| `tokens.*` | mapear dados de token ou usar helpers de token | [`reference.md`](reference.md) |
| `scene.*` | ler estado de cena/ferramenta ou adicionar ferramentas de cena | [`reference.md`](reference.md) |
| `chat.*` | enviar chat cards/intents | [`reference.md`](reference.md) |
| `content.*` | fornecer e ler content packs importáveis | [`content-and-assets.md`](content-and-assets.md), [`reference.md`](reference.md) |
| `settings` | declarar/ler/gravar settings do pacote | [`settings.md`](settings.md), [`reference.md`](reference.md) |
| `locales` | fornecer traduções e traduzir labels | [`reference.md`](reference.md) |
| `assets.*` | carregar styles/scripts/assets de UI/packs de mídia | [`content-and-assets.md`](content-and-assets.md) |
| `bus.*` | publicar/assinar/prover/requisitar mensagens de pacote | [`messaging.md`](messaging.md), [`reference.md`](reference.md) |
| `commands.register` | registrar comandos de usuário/navegador | [`reference.md`](reference.md) |

## 4. Construa um ruleset com cobertura completa da SDK

Um autor de ruleset completo deve conseguir fazer tudo isto:

### Modelo de dados

- Definir tipos de actor.
- Definir tipos de item.
- Anexar schemas aos tipos de actor/item.
- Definir defaults e campos derivados onde suportado.
- Mapear actors/items para sheets.
- Mapear actors para defaults de token.

### Experiência do usuário

- Fornecer sheets declarativas.
- Fornecer componentes de sheet quando necessário.
- Fornecer labels localizados para sheets, settings, conteúdo e regras.
- Fornecer CSS para a UI do ruleset.
- Definir settings para regras opcionais.

### Regras de jogo

- Fornecer documentos de regras declarativos.
- Declarar mappings ou intents de rolagem.
- Configurar defaults de combate.
- Declarar content packs com dados iniciais.
- Fornecer assets usados pelo ruleset.

### Comportamento de runtime

Apenas onde os dados declarativos forem insuficientes, um autor de ruleset deve saber como:

- registrar plugins de runtime de sheet com `sdk.sheets.register`;
- registrar comportamento de combate em runtime com `sdk.combat.register`;
- registrar um painel de combate com `sdk.combat.registerPanel`;
- publicar/assinar eventos com namespace usando `sdk.bus`;
- enviar chat cards ou intents com `sdk.chat.send`;
- ler settings com `sdk.settings.get`;
- gravar settings com `sdk.settings.set`;
- traduzir labels com `sdk.i18n.t`;
- inspecionar o estado atual de campanha/cena/usuário com `sdk.game.*`;
- usar helpers de token/cena/ferramenta apenas pela SDK documentada.

## 5. Construa um addon com cobertura completa da SDK

Um autor de addon completo deve conseguir construir estes tipos de addon:

| Tipo de addon | Recursos de manifesto | APIs de runtime |
|---|---|---|
| Addon de estilo | `entrypoints.game.styles`, `assets.styles` | nenhuma |
| Addon de settings | `settings`, capability `settings` | `sdk.settings.*` se com script |
| Addon de UI | `assets.scripts`, `assets.ui` | `sdk.ui.*` |
| Addon de chat | `chat.cards` | `sdk.chat.send` |
| Addon de automação | `bus.*`, dependências de evento | `sdk.bus.*` |
| Addon de comando | `commands.register` | `sdk.commands.register` |
| Addon de conteúdo | `provides.contentPacks`, `content.packs` | `sdk.content.*` se com script |
| Addon de cena/ferramenta | `scene.tools`, assets opcionais | `sdk.scene.*`, `sdk.tools.*` |
| Addon de token | `tokens.extends` | `sdk.tokens.centerOn` |
| Addon de combate | `combat.runtime` | `sdk.combat.*` |

## 6. Construa pacotes de conteúdo e de assets

Um autor de conteúdo deve conseguir:

- declarar um ou mais content packs;
- apontar cada pack para paths seguros relativos ao pacote;
- definir id, label, type e path do pack;
- validar a existência dos arquivos de conteúdo;
- depender de um ruleset se o conteúdo espera tipos específicos de actor/item;
- localizar labels de conteúdo quando apropriado.

Um autor de assets deve conseguir:

- declarar assets de imagem, mapa, ícone, áudio ou mistos;
- escolher formatos seguros;
- evitar suposições de filesystem cru;
- documentar licença e atribuição;
- referenciar assets de pacotes de content/ruleset/addon por paths declarados ou dependências.

## 7. Use o ciclo de vida do runtime corretamente

Todo autor de pacote com script deve entender:

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Registra listeners, comandos, sheet plugins, combat plugins e estado local.
  },
  ready(sdk, payload) {
    // Usa funcionalidade que depende do DOM/runtime de jogo estar pronto.
  }
});
```

Regras:

- O `id` deve corresponder ao `manifest.json`.
- O script deve ser declarado em `entrypoints.game.scripts`.
- O pacote deve declarar `assets.scripts`.
- O pacote deve declarar cada capability exigida pelos métodos da SDK que chama.
- O registro deve acontecer uma vez.
- O código deve ser resiliente se dependências opcionais estiverem ausentes.

## 8. Use cada namespace da SDK escopada apropriadamente

| Namespace | Uso pelo autor |
|---|---|
| `sdk.version` | checar a versão do runtime da SDK |
| `sdk.package` | ler a identidade do pacote atual |
| `sdk.kind` | ramificar comportamento por kind de pacote se necessário |
| `sdk.capabilities` | testar/exigir capability antes de comportamento opcional |
| `sdk.context()` | ler snapshot congelado de contexto |
| `sdk.game` | ler campanha, cena, usuário, readiness |
| `sdk.bus` | publicar/assinar/prover/requisitar mensagens de pacote |
| `sdk.commands` | registrar comandos |
| `sdk.ui` | mostrar toasts e abrir/fechar modais documentados |
| `sdk.chat` | enviar chat cards/intents |
| `sdk.settings` | ler/gravar settings declaradas |
| `sdk.sheets` | usar helpers de sheet e registrar sheet plugins |
| `sdk.combat` | registrar comportamento de combate, painéis, handlers, slots |
| `sdk.tokens` | usar helpers de token |
| `sdk.scene` | ler estado de cena/canvas/câmera |
| `sdk.tools` | ler estado da ferramenta ativa |
| `sdk.content` | listar/ler content packs |
| `sdk.i18n` | traduzir strings do pacote |

Veja [`reference.md`](reference.md).

## 9. Integre com outros pacotes com segurança

Autores devem conseguir:

- declarar dependências rígidas em `dependencies`;
- declarar pacotes incompatíveis em `conflicts`;
- usar integração opcional por eventos com namespace;
- incluir um campo `version` nos payloads de evento;
- manter nomes de evento com escopo de pacote, por exemplo `package:my-addon:ready`;
- checar `sdk.capabilities.has(...)` antes de caminhos opcionais de runtime;
- fazer no-op gracioso quando uma dependência opcional não está presente.

Veja [`messaging.md`](messaging.md).

## 10. Valide e depure

Autores devem conseguir rodar:

```bash
grave package validate data/packages/my-package
grave package doctor my-package
grave package install my-package --yes --enable
```

Um pacote só está pronto depois que:

- a validação do manifesto passa;
- todo arquivo declarado existe;
- as capabilities são válidas;
- capabilities proibidas estão ausentes;
- o comportamento de dependência/conflito é intencional;
- o pacote pode ser instalado e ativado a partir de um checkout limpo;
- o registro de runtime aparece em modo debug quando aplicável;
- as settings persistem e recarregam;
- conteúdo/assets podem ser descobertos pela SDK;
- o comportamento de UI falha com segurança quando superfícies opcionais do core estão indisponíveis.

## 11. Checklist de segurança e fronteiras

Autores devem entender que o SDK v1 não expõe:

- execução de pacote no backend;
- acesso cru ao banco de dados;
- acesso cru ao filesystem;
- acesso cru à rede;
- override de permissões;
- stores privadas;
- internals privados do renderer;
- globals de navegador não documentados.

Pacotes com script rodam código de navegador confiável para os usuários da mesa. Solicite `assets.scripts` apenas quando necessário.

## 12. Checklist de release

Antes de publicar um pacote, verifique:

- `manifest.json` é válido.
- `README.md` explica install, ativação, capabilities, settings e compatibilidade.
- `CHANGELOG.md` documenta as mudanças.
- Licença e atribuição de assets estão incluídas.
- A faixa de compatibilidade é honesta.
- Não há paths apenas de desenvolvimento.
- O pacote foi instalado a partir de sua forma de distribuição empacotada.
- Todos os exemplos nos docs ainda funcionam.

## 13. Teste de completude da documentação

Os docs da SDK devem responder a estas perguntas do autor sem ajuda externa:

- Que kind de pacote devo escolher?
- Quais arquivos meu pacote deve conter?
- Quais campos de manifesto são obrigatórios?
- Quais campos de `provides` devo usar?
- Quais capabilities preciso?
- Quais métodos de runtime da SDK existem?
- Qual capability faz o gate de cada método?
- Como declaro settings?
- Como leio/gravo settings?
- Como forneço conteúdo?
- Como forneço assets?
- Como registro comportamento de sheet/combate?
- Como envio chat cards?
- Como me comunico com outro pacote?
- Como valido, instalo, ativo e depuro?
- Quais APIs são privadas ou proibidas?
