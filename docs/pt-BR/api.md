# Referência da API pública

[Índice da documentação](../README.pt-BR.md) · [English](../en/api.md) · [Guia de módulos](modules.md)

O Gravewright possui três interfaces relacionadas. Elas usam as mesmas verificações nativas de permissão, mas têm marcadores de versão, assinaturas e formatos de resposta diferentes:

| Interface | Entrada | Marcador atual | Uso previsto |
| --- | --- | --- | --- |
| Python | `from api import actors, ...` | `api.API_VERSION == "1.0"` | Integrações confiáveis no servidor com Django inicializado |
| API de domínio no navegador | `window.gravewright` ou `api` do contexto do módulo | `api.version == "1.1.0"` | Frontend nativo e extensões de navegador |
| Operações originais de módulos | `host.call(name, payload, options)` do bloco montado | SDK `1.0.0` | Módulos de navegador instalados e ativos |

A fachada Python reexporta funções selecionadas dos serviços; não descobre plugins nem registra apps Django. As APIs do navegador fazem requisições autenticadas a esses serviços. O registro original do SDK é menor e possui schemas JSON explícitos. Não reutilize payloads entre `api.actors.update(...)` e `host.call("actor.update", ...)` sem conferir seus contratos. O projeto não distribui atualmente SDK npm, especificação OpenAPI nem verificador automático de compatibilidade entre versões. Os marcadores descrevem este checkout, sem garantir estabilidade de detalhes internos não documentados. Consulte o [licenciamento](../../LICENSING.pt-BR.md).

## API de domínio no navegador

O template base carrega [`frontend-api.js`](../../gravewright/modules/static/gravewright_modules/frontend-api.js). Após o carregamento, use a API vinculada à mesa na página de jogo ou selecione uma mesa explicitamente:

```javascript
const table = gravewright.forTable("<uuid-da-campanha>");
const actors = await table.actors.list();
const result = await table.dice.roll("1d20+3", { label: "Teste" });
```

Substitua o UUID por uma campanha da qual o usuário autenticado participe. Rolagens publicam uma mensagem de chat; `dice.roll` não é uma calculadora somente de leitura. Um módulo deve usar sua `api` fornecida para manter as requisições vinculadas à ativação e montagem.

`forTable(tableId, {sceneId})` fixa a cena. Um `sceneId`/`mapId` conflitante em payload posterior gera `stale_context`. Na página de jogo, a API sem cena fixa pode usar o mapa selecionado; integrações que precisam de identidade estável devem fixá-la. Adaptadores globais de conta/campanha/administração/módulos funcionam sem mesa selecionada; operações da mesa exigem contexto.

### Métodos e payloads

O mapeamento de métodos para comandos está em [`contracts/frontend.json`](../../gravewright/modules/contracts/frontend.json); [`domain-api.js`](../../gravewright/modules/static/gravewright_modules/domain-api.js) acrescenta atalhos. Validação e projeção de permissões pertencem aos serviços nativos. O contrato é um registro de métodos, não um schema completo de payloads. Exemplos estão nos [testes de API frontend](../../gravewright/table/tests/test_frontend_api.py), [testes dos domínios](../../gravewright/table/tests/test_modules.py) e testes de cada app.

Todo domínio abaixo possui `state(payload = {}, options)` e os métodos listados, normalmente com assinatura `(payload = {}, options)`:

| Domínio | Métodos de comando |
| --- | --- |
| `actors` | `create`, `update`, `delete`, `setPermissions`, `saveSheet`, `createFolder`, `updateFolder`, `deleteFolder`, `deleteAsset` |
| `tokens` | `place`, `move`, `remove`, `duplicate`, `setHidden`, `setVision`, `configure`, `addCondition`, `removeCondition` |
| `maps` | `update`, `move`, `delete`, `activate`, `updateObjects`, `createFolder`, `updateFolder`, `deleteFolder` |
| `journals` | `create`, `update`, `delete`, `move`, `setAccess`, `present`, `createFolder`, `updateFolder`, `moveFolder`, `deleteFolder`, `setStatus`, `addQuest`, `removeQuest`, `pinQuest`, `reorderQuests`, `roll`, `reset` |
| `items` | `create`, `update`, `delete`, `duplicate`, `setPermissions`, `createFolder`, `updateFolder`, `deleteFolder` |
| `combat` | `add`, `remove`, `configure`, `setInitiative`, `rollInitiative`, `toggle`, `moveUp`, `moveDown`, `setTurn`, `nextRound`, `previousRound`, `start`, `stop`, `nextTurn`, `previousTurn` |
| `cards` | `define`, `instantiate`, `create`, `draw`, `shuffle`, `reset`, `deleteDeck`, `discard`, `return`, `give`, `place`, `take`, `flip`, `move` |
| `audio` | `updateTrack`, `deleteTrack`, `createPlaylist`, `updatePlaylist`, `deletePlaylist`, `createSpatialSound`, `updateSpatialSound`, `deleteSpatialSound`, `play`, `pause`, `stop`, `seek`, `setVolume`, `startScore`, `pauseScore`, `resumeScore`, `stopScore`, `nextScore`, `previousScore` |
| `compendiums` | `create`, `configure`, `read`, `delete`, `add`, `remove`, `import`, `setPermissions` |

Formas adicionais:

| Método | Comportamento |
| --- | --- |
| `actors/tokens/maps/journals/items.list(payload, options)` | Retorna a coleção da resposta autorizada de `state` |
| `actors/tokens/maps/journals/items.get(id, payload, options)` | Procura na coleção projetada ou gera `not_found` |
| `actors.update(id, changes, options)` | Atalho que lê a versão atual se `changes.version` não foi fornecido |
| `actors.sheet(id, payload, options)` | Lê ficha, inclusive com contexto de token no payload |
| `maps.layers(payload, options)` | Lê camadas autorizadas da cena |
| `chat.history(payload, options)` | Lê mensagens visíveis |
| `chat.send(payload, options)` | Envia `{text, sceneId?}` pelo processamento nativo |
| `chat.remove(id, options)` / `chat.clear(options)` | Exclui uma/todas as mensagens conforme regras nativas de moderação |
| `dice.roll(expression, payload, options)` | Rola e publica; suporta `repeat`, `label`, `visibility` e cena |
| `table.search(query, options)` | Busca recursos visíveis ao usuário |
| `table.lobby(options)` / `table.updateLobby(payload, options)` | Lê/altera a sala de espera nativa |

Os seis atalhos de transição de combate (`nextTurn`, `previousTurn`, `nextRound`, `previousRound`, `start`, `stop`) também buscam a versão atual quando omitida. Fornecer versões explicitamente permite detectar alterações concorrentes:

```javascript
const current = await table.actors.get("<uuid-do-ator>");
const requestId = crypto.randomUUID();
await table.actors.update(current.id, {
  name: "Ator renomeado",
  version: current.version
}, { requestId });
```

Mutações geram um UUID `requestId` quando ele não é fornecido. Comandos que usam recibos nativos deduplicam tentativas com o mesmo ID; reutilize-o apenas ao repetir o mesmo comando lógico. Uma nova alteração exige novo ID. `version`/`expectedVersion` desatualizada ainda pode gerar `conflict`. Não presuma idempotência em todos os endpoints: alterações da sala de espera e moderação do chat possuem outras assinaturas de serviço.

`options.signal` cancela operações pendentes. Um contexto descartado resulta em `stale_context`; cancelamento explícito resulta em `cancelled` nas operações com escopo do módulo. Trate `error.code`, não textos traduzidos. Adaptadores HTTP globais também podem expor erros de transporte/autenticação dos endpoints.

### Adaptadores de conta, campanha, proprietário e módulos

Disponíveis no objeto global `gravewright`, não na API restrita a domínios do módulo:

| Adaptador | Métodos |
| --- | --- |
| `accounts` | `status`, `session`, `login`, `register`, `setup`, `logout`, `update` |
| `campaigns` | `list`, `create`, `update(id, payload)`, `join(code)`, `remove(id, code)`, `invite(id, payload)`, `rulesets` |
| `administration` | `status`, `diagnostics`, `settings`, `updateSettings(section, payload)` |
| `modules` | `list`, `catalog`, `status`, `install(payload)`, `state(tableId)`, `configure(tableId, payload)` |

Permissões de proprietário e gerenciamento da campanha continuam verificadas no servidor. Os métodos usam cookies de sessão e obtêm token CSRF antes de escrever. Não há autenticação por chave de API nessa interface. Views e testes dos apps definem os payloads; não coloque credenciais no código de módulos.

### Eventos de domínio

Use `api.events.on(name, handler)`, que retorna uma função para cancelar a assinatura. Assinaturas são removidas junto com o ciclo de vida da API. Nomes suportados:

```text
actors.changed       tokens.changed       maps.changed
maps.layersChanged   journals.changed     items.changed
combat.changed       cards.changed        audio.changed
compendiums.changed  chat.changed         chat.message
table.presence       table.lobbyChanged
```

Assinaturas de mudanças em coleções fazem leitura HTTP autorizada inicialmente, após invalidações correspondentes do socket e na reconexão. Invalidações concorrentes são agrupadas; não representam todas as mutações intermediárias. Callbacks de ator/token/mapa/documento recebem o estado projetado e a identidade da mesa/cena; callbacks de item/combate/cartas/áudio/compêndio recebem `{module, state, tableId, sceneId?}`. `chat.changed`, `chat.message`, presença e sala de espera encaminham payloads do socket sem ler automaticamente o estado inicial. Consulte esse estado separadamente quando necessário.

Assinaturas usam o socket da página atual. Uma API criada com `forTable` em `/inside`, ou apontando para outra mesa, faz requisições HTTP, mas não cria socket para essa mesa. Não presuma atualizações contínuas. Callbacks devem ser síncronos; inicie tarefas assíncronas explicitamente com tratamento de erro. O `events` antigo do bloco usa outros nomes e possui ressalvas descritas no [guia de módulos](modules.md#arquivos-persistência-e-eventos).

## Operações originais validadas por schema

Use `host.call` do bloco montado. Schemas de entrada/saída/eventos/contexto estão relacionados em [`contracts/registry.json`](../../gravewright/modules/contracts/registry.json); semântica de ciclo de vida e armazenamento, em [`contracts/api.json`](../../gravewright/modules/contracts/api.json).

| Operação | Escopo | Finalidade |
| --- | --- | --- |
| `actor.list`, `actor.read` | Mesa | Ler resumos/documentos de atores visíveis |
| `actor.create`, `actor.update`, `actor.delete` | Mesa | Criar, alterar campos fornecidos ou excluir logicamente com revisão |
| `actor.data.read`, `actor.data.update` | Mesa | Ler/substituir todos os dados do sistema |
| `token.read`, `token.move` | Cena | Ler token ou mover seu centro em pixels da cena |
| `token.data.read`, `token.data.update` | Cena | Ler/substituir dados do ator vinculado ou snapshot do token |
| `asset.list`, `asset.upload`, `asset.download` | Mesa | Listar/enviar/baixar modelos PDF do sistema atual |
| `actor.image.upload` | Mesa | Enviar retrato/imagem do ator com validação nativa |
| `locale.apply` | Local | Aplicar catálogo de idioma durante a montagem |

```javascript
const actor = await host.call("actor.read", { id: actorId });
const data = await host.call("actor.data.read", { id: actorId });
// Consulte os campos de revisão e substituição do schema antes de escrever.
```

Operações de cena exigem uma cena montada; um ID arbitrário no payload não cria essa autorização. `actor.data.update` e `token.data.update` substituem objetos completos, inclusive arrays/objetos internos; `null` é valor, não instrução de exclusão. `actor.update` altera apenas campos fornecidos. Confira cada campo de revisão: revisões do SDK não equivalem às versões de entidade da API de domínio.

Uploads recebem `File`/`Blob` real em `payload.file`, usam multipart autenticado e derivam metadados no servidor. Envio de modelo PDF é exclusivo do mestre e limitado a 10 MiB. Downloads retornam `{blob, name, contentType, size}`. `options.onProgress` informa conclusão nesse transporte SDK por fetch, não progresso contínuo. `options.signal` é suportado; cancelamento não desfaz mutação confirmada.

| Erro público do módulo | Significado |
| --- | --- |
| `not_found` | Recurso ausente ou indisponível nesse contexto |
| `permission_denied` | Usuário sem permissão para a ação |
| `invalid_data` | Falha de validação de payload/schema/caminho/valor |
| `conflict` | Conflito de revisão de entidade, armazenamento, ativação ou registro |
| `unavailable` | Operação desconhecida, SDK incompatível ou falha do serviço |
| `cancelled` | Cancelamento de operação pelo chamador |
| `stale_context` | Montagem/cena/revisão deixou de ser válida |

## Interface Python

Inicialize Django antes de importar fachadas de domínio. `manage.py shell`, views e inicialização de apps já fazem isso. Em scripts independentes, defina `DJANGO_SETTINGS_MODULE=config.settings` e chame `django.setup()` primeiro. Não consulte o banco durante imports ou `AppConfig.ready()`.

`Context(campaign_id, user_id)` normaliza UUIDs e é imutável; construí-lo não autoriza ações. `Context.from_request(request, campaign_id)` verifica autenticação e participação. Serviços continuam verificando permissões atuais. Use a identidade autenticada, não um ID de usuário fornecido pelo cliente.

```python
from uuid import uuid4
from api import Context, actors

# Dentro de uma view Django autenticada; campaign_id vem da rota.
context = Context.from_request(request, campaign_id)
visible = actors.state(context.campaign_id, context.user_id)
created = actors.command(
    context.campaign_id,
    context.user_id,
    "actor.create",
    {"name": "Ator de exemplo"},
    uuid4(),
)
```

Imports e assinaturas públicas; `campaign_id`/`user_id` representam identificadores mesmo onde a implementação usa nomes de parâmetros mais curtos:

| Import | Assinaturas |
| --- | --- |
| `api.actors` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `sheet(campaign_id, user_id, actor_id, token_id=None)` |
| `api.tokens` | `state(campaign_id, user_id, map_id)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.maps` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `layer_state(campaign_id, user_id, scene_id)` |
| `api.journals` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.items`, `api.combat`, `api.cards`, `api.audio`, `api.compendiums` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.resources` | `state(campaign_id, user_id, name, scene_id=None, preview_token_id=None)`, `command(campaign_id, user_id, name, action, data, request_id)` |
| `api.chat` | `history(campaign_id, user_id, map_id=None)`, `send(campaign_id, user_id, text, request_id, map_id=None)`, `remove(campaign_id, user_id, message_id=None)` |
| `api.dice` | `evaluate(expression, repeat=1, *, random_source=None)`, `roll(campaign_id, user_id, expression, request_id, *, repeat=1, label="", visibility="public", map_id=None)` |
| `api.table` | `search(campaign_id, user_id, query)`, `lobby(campaign_id, user_id)`, `update_lobby(campaign_id, user_id, payload)` |
| `api.events` | `Change`, `resource_changed` |
| `api.errors` | `AuthError`, `JournalError`, `MapError`, `RollError` |

Use argumentos posicionais como no exemplo quando nomes de parâmetros diferirem. `resources` seleciona `items`, `combat`, `cards`, `audio` ou `compendiums` pelo nome. `dice.evaluate` calcula localmente; `dice.roll` salva/publica uma rolagem. Exceções Python preservam tipos/códigos dos serviços originais, sem a normalização de sete códigos do navegador.

### Transações e hooks do servidor

Wrappers públicos preservam transações, permissões, versões, recibos de deduplicação onde implementados e notificações após commit. Reverter uma transação externa descarta a escrita e suas notificações pendentes. Escritas ORM diretas não equivalem a essa API de mutação.

Conecte hooks confiáveis ao sinal Django:

```python
from api.events import resource_changed

def observe_change(sender, change, **kwargs):
    # sender é o nome do recurso; change contém IDs, não um snapshot.
    print(change.resource, change.action, change.request_id)

resource_changed.connect(
    observe_change,
    dispatch_uid="example.observe-change",
    weak=False,
)
```

Registre receivers uma vez em `AppConfig.ready()` de seu app explicitamente instalado. `Change` contém `campaign_id`, `user_id`, `resource`, `action` e `request_id`. O sinal ocorre após commit por `send_robust`; falhas de receivers são registradas e não revertem comandos confirmados. Ele executa no processo servidor, sem fila durável nem log reproduzível. Mantenha handlers curtos e não envie IDs/dados privados a públicos de navegador sem filtragem. Chat e dados possuem notificações próprias com controle de audiência; não há garantia de `resource_changed` para toda escrita.

## Transporte e manutenção

O endpoint de domínio do host é `POST /api/tables/<table_id>/api`; módulos instalados usam `POST /api/tables/<table_id>/modules/<module_id>/api`. Recebem `{domain, method, payload, requestId?}` e retornam `{value}`. Módulos também enviam `mountId`, `moduleSetRevision` e `sceneId` opcional; a ponte abre o lease antes. O SDK antigo usa o mesmo prefixo do módulo com `/call` e envelope `{name, payload, ...context}`. As URLs descrevem a implementação para mantenedores; módulos devem usar as APIs fornecidas.

Depois de alterar o registro de métodos:

```sh
uv run --locked python scripts/generate_frontend_api.py
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.table.tests.test_public_api gravewright.modules
node --test tests/modules/*.test.mjs
```

`frontend-contract.js` é gerado a partir de `frontend.json`; altere o registro fonte primeiro. Preserve consistência de autorização, payloads e pós-commit entre frontend nativo, módulos e Python. Ao adicionar operação no SDK original, atualize schemas, registro, constantes de operações, dispatcher e testes em conjunto; não existe gerador genérico para todos esses arquivos.
