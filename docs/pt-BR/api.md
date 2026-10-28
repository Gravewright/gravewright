# Referência da API pública

[Índice da documentação](../README.pt-BR.md) · [English](../en/api.md) · [Guia de módulos](modules.md)

O Gravewright possui três interfaces relacionadas. Elas usam as mesmas verificações nativas de permissão, mas têm marcadores de versão, assinaturas e formatos de resposta diferentes:

| Interface | Entrada | Marcador atual | Uso previsto |
| --- | --- | --- | --- |
| Python | `from api import actors, ...` | `api.API_VERSION == "1.0"` | Integrações confiáveis no servidor com Django inicializado |
| API de domínio no navegador | `window.gravewright` ou `api` do contexto do módulo | `api.version == "1.2.0"` | Frontend nativo e extensões de navegador |
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
| `maps` | `update`, `move`, `delete`, `activate`, `navigate`, `updateObjects`, `createFolder`, `updateFolder`, `deleteFolder`, `exportUniversalVtt` |
| `journals` | `resources`, `resolve`, `create`, `update`, `delete`, `move`, `setAccess`, `present`, `createFolder`, `updateFolder`, `moveFolder`, `deleteFolder`, `setStatus`, `setObjective`, `assignCharacters`, `createBoardQuest`, `addQuest`, `removeQuest`, `pinQuest`, `reorderQuests`, `roll`, `reset`, `setPrerequisites`, `restoreRevision`, `restoreDeleted`, `purgeDeleted` |
| `items` | `create`, `update`, `delete`, `duplicate`, `setPermissions`, `createFolder`, `updateFolder`, `deleteFolder` |
| `combat` | `add`, `remove`, `configure`, `setInitiative`, `rollInitiative`, `toggle`, `moveUp`, `moveDown`, `setTurn`, `nextRound`, `previousRound`, `start`, `stop`, `nextTurn`, `previousTurn` |
| `clocks` | `create`, `update`, `advance`, `reset`, `delete` |
| `clues` | `create`, `update`, `advance`, `reset`, `reveal`, `hide`, `delete` |
| `mindmaps` | `read`, `resources`, `resolve`, `create`, `update`, `node`, `delete` |
| `cards` | `define`, `instantiate`, `create`, `draw`, `shuffle`, `reset`, `deleteDeck`, `discard`, `return`, `give`, `place`, `take`, `flip`, `move` |
| `audio` | `updateTrack`, `deleteTrack`, `createPlaylist`, `updatePlaylist`, `deletePlaylist`, `createSpatialSound`, `updateSpatialSound`, `deleteSpatialSound`, `play`, `pause`, `stop`, `seek`, `setVolume`, `startScore`, `pauseScore`, `resumeScore`, `stopScore`, `nextScore`, `previousScore` |
| `compendiums` | `create`, `configure`, `read`, `delete`, `add`, `remove`, `import`, `setPermissions` |
| `mapBuilder` | `read`, `save`, `generate`, `update`, `sync`, `adopt` |
| `blueprints` | `save`, `templates`, `readTemplate`, `saveTemplate`, `deleteTemplate`, `test`, `testDraft`, `control` |
| `library` | `createFolder`, `updateFolder`, `deleteFolder`, `move`, `delete` |
| `ownership` | `read`, `update`; `state`/`read` exigem `{kind, id}` |
| `system` | `call(operation, data, options)`; `state` descreve as operações do sistema da campanha |

Formas adicionais:

| Método | Comportamento |
| --- | --- |
| `actors/tokens/maps/journals/items/clocks/clues/mindmaps.list(payload, options)` | Retorna a coleção da resposta autorizada de `state` |
| `actors/tokens/maps/journals/items/clocks/clues/mindmaps.get(id, payload, options)` | Procura na coleção projetada ou gera `not_found` |
| `actors.update(id, changes, options)` | Atalho que lê a versão atual se `changes.version` não foi fornecido |
| `actors.sheet(id, payload, options)` | Lê ficha, inclusive com contexto de token no payload |
| `maps.layers(payload, options)` | Lê camadas autorizadas da cena |
| `chat.history(payload, options)` | Lê mensagens visíveis |
| `chat.send(payload, options)` | Envia `{text, sceneId?}` pelo processamento nativo |
| `chat.remove(id, options)` / `chat.clear(options)` | Exclui uma/todas as mensagens conforme regras nativas de moderação |
| `compendiums.read({packId, id}, options)` | Lê uma entrada com o acesso atual da mesa; conserva o documento/envelope do compêndio |
| `compendiums.read({packId, ids}, options)` | Lê de 1 a 100 IDs únicos e retorna `{entries: [...]}` na ordem pedida; não retorna resultados parciais se alguma entrada faltar |
| `dice.roll(expression, payload, options)` | Rola e publica; suporta `repeat`, `label`, `visibility` e cena |
| `table.search(query, options)` | Busca documentos com acesso mínimo de leitura. As opções aceitam `kind` (`actor`, `item`, `journal`, `quest`, `quest_board`, `scene`, `compendium`) e `recent` (até 12 referências `{id, type}` com consulta vazia). Os resultados incluem `snippet` autorizado, `kind` e `actions`; as referências recentes são revalidadas a cada consulta. |
| `table.lobby(options)` / `table.updateLobby(payload, options)` | Lê/altera a sala de espera nativa |

`combat.stop` encerra o encontro e limpa os participantes, a iniciativa e o histórico de turnos e rodadas. Os atores e tokens da cena são preservados; adicione participantes novamente antes de iniciar outro encontro.

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

`options.signal` cancela operações pendentes. Um contexto descartado resulta em `stale_context`; cancelamento explícito resulta em `cancelled` nas operações com escopo do módulo. Trate `error.code`, não textos traduzidos. Falhas autorizadas dos serviços nativos também podem fornecer uma mensagem em `error.message`; exiba-a como texto pelo Translator. Adaptadores HTTP globais também podem expor erros de transporte/autenticação dos endpoints.

### Descoberta de capacidades e domínios adicionais

`api.capabilities()` retorna uma cópia independente do contrato local do
navegador, incluindo métodos, leituras, transportes binários e operações
demoradas. A seção `global` lista os adaptadores exclusivos da página para
contas, campanhas e administração; não os concede a uma montagem de módulo.
Não faz requisições nem concede permissões. Em Python,
`api.capabilities()` retorna `{pythonVersion, browser}` sem acessar o banco.
As operações do sistema atual são descobertas por `await api.system.state()`.

Os novos domínios mantêm campanha, verificações de mestre, UUIDs de operações e
revisões esperadas dos serviços nativos. Os payloads públicos usam estes nomes:

| Operação | Payload |
| --- | --- |
| `mapBuilder.state` / `read` | `{}` / `{projectId}` |
| `mapBuilder.save` | `{projectId, expectedVersion, document, folderId?}`; na criação, use UUID novo e `expectedVersion: 0` |
| `mapBuilder.generate` | `{projectId, expectedVersion}`; cria uma cena privada |
| `mapBuilder.update` / `sync` | `{projectId, expectedVersion, expectedSceneVersion}` |
| `mapBuilder.adopt` | `{sceneId, expectedSceneVersion}` |
| `blueprints.state` | `{sceneId}`; rede de automações autorizada |
| `blueprints.save` | `{sceneId, elementId, expectedVersion, expectedProjectVersion, blueprint}` |
| `blueprints.templates` / `readTemplate` | `{}` / `{templateId}` |
| `blueprints.saveTemplate` / `deleteTemplate` | `{templateId, expectedVersion, name, description, definition}` / `{templateId, expectedVersion}` |
| `blueprints.test` | `{sceneId, elementId, expectedVersion, event, tokenId?, blueprint?}` |
| `blueprints.testDraft` | `{document, elementId, event, actorId?, projectId?}`; um projeto vinculado autorizado fornece o escopo da cena original para vínculos de relógios, pistas e mapas mentais no ensaio temporário |
| `blueprints.control` | `{sceneId, elementId, expectedVersion, action, value?}` |
| `maps.exportUniversalVtt` | `{sceneId}`; JSON nativo de intercâmbio |
| `maps.navigate` | `{mapId}`; `mapId: null` explícito volta a seguir a transmissão em contexto sem cena fixa |
| `maps.activate` | `{mapId, playerIds?}`; exclusivo do mestre. Omita `playerIds` para ativar para todos e remover destinos individuais. Um array não vazio de IDs de usuários jogadores da campanha, sem duplicatas, muda somente esses destinos. O estado de mapas do mestre inclui `players: [{id, name, color, sceneId}]`; os demais papéis não recebem essa lista. |
| `library.createFolder` | `{name}`; retorna `{ok, id}` |
| `library.updateFolder` / `deleteFolder` | `{folderId, name}` / `{folderId}` |
| `library.move` / `delete` | `{assetId, folderId}` / `{assetId}`; aliases nativos snake_case continuam aceitos |
| `ownership.read` / `state` | `{kind, id}`; revisão, níveis, permissões e membros para o mestre |
| `ownership.update` | `{kind, id, version, permissions, reset?}`; mantém as regras nativas de lote/páginas |

Os tipos de ownership são `actors`, `items`, `journals`, `scenes`, `cards`,
`compendiums`, `tokens`, `pages` e os grupos `actor-folders`, `item-folders`,
`journal-folders`, `scene-folders`. A página usa ID `journalUUID:sectionId`;
revisões de pastas em lote são strings opacas. Nenhum método novo substitui
silenciosamente uma revisão fornecida. Atualizações do Builder também conferem
a cena gerada com a cena autoritativa da montagem. Ensaios mantêm o rollback nativo.

Renderização e criação de tiles ocorrem fora de uma transação global do
transporte; cada serviço mantém seus próprios limites de commit e limpeza.
Geração, atualização de cenas, exportação UVTT e ensaios começam sem prazo
artificial no cliente. `options.timeoutMs` define um prazo; `null` o desativa.
As coleções do Builder usam as invalidações existentes de mapas. Relógios e
pistas possuem os eventos de coleção descritos abaixo.

### Relógios de progresso

O domínio `clocks` fornece os mesmos registros persistentes na mesa e no gestor
de campanha. `state({sceneId})` retorna os relógios da campanha e daquela cena
autorizada, filtrados pela participação atual. O adaptador nativo da página usa
a rota GET de estado dos recursos para espectadores visualizarem relógios públicos.

Criar aceita `{name, description?, segments?, value?, color?, visibility?, playersCanEdit?,
pinned?, scopeSceneId?}`. Os padrões são 4 segmentos, valor 0, `#c9a44c`, `gm`,
false, false e escopo da campanha. Segmentos são inteiros de 2 a 24; o progresso
vai de 0 ao total de segmentos; cada campanha comporta até 128 relógios. Atualizar
aceita os campos de configuração e o `id` e a `version` existentes.
`advance({id, version, delta})` aceita delta inteiro de -24 a 24 e limita o
progresso ao intervalo válido. Reiniciar e excluir aceitam `{id, version}`.
Somente mestres configuram, reiniciam ou excluem; jogadores avançam apenas
relógios públicos com `playersCanEdit: true`. Espectadores continuam somente
com leitura. Os relógios retornados expõem `canEdit`, `canConfigure` e o escopo
salvo em `sceneId`.

`description` é texto autoral opcional com padrão `""` e exige string de até
4.000 caracteres. Somente configurações do mestre o alteram. Atualizações que
omitem o campo o preservam; leitores só o recebem quando podem ver o relógio.
O campo é adicional, sem novo método de navegador ou versão do SDK.

`scopeSceneId: null` salva o escopo da campanha; um UUID de cena salva o escopo
da cena. O `sceneId`/`mapId` da requisição é o contexto de visualização e nunca
move o relógio. Uma API vinculada a cena rejeita outro `scopeSceneId` não nulo.
Alterações de relógios existentes exigem a versão salva; conflitos exigem revisar
o estado atualizado. O evento `clocks.changed` usa o envelope de estado de
recursos descrito abaixo. Consulte [o guia de relógios](clocks.md) para
visibilidade, fixação e sincronização.

### Descoberta de pistas

O domínio `clues` compartilha as descobertas persistentes entre a mesa e o gestor
de campanha. `state({sceneId})` retorna as pistas da campanha e daquela cena
autorizada. Jogadores e espectadores recebem somente pistas com
`visibility: "players"` e `value === segments`; pistas não descobertas não têm
registro, título, conteúdo, ID ou marcador público. `gmNotes` fica ausente de
todas as projeções públicas, inclusive após a descoberta. Toda alteração direta
exige a autoridade atual de mestre.

Criar aceita `{name, content?, gmNotes?, segments?, value?, color?, visibility?,
pinned?, scopeSceneId?}`. Os padrões são conteúdo e notas vazios, 4 etapas,
valor 0, `#c9a44c`, `players`, false e escopo da campanha. Nomes têm até 120
caracteres; conteúdo e notas do mestre têm até 4000 cada. Etapas são inteiros
de 1 a 24; o valor vai de 0 ao total. Uma etapa permite descoberta imediata.
Cada campanha comporta até 128 pistas, independentemente dos relógios.

Atualizar aceita esses campos e `{id, version}`. `advance({id, version, delta})`
aceita inteiro de -24 a 24 e limita o progresso. `reset({id, version})` zera o
progresso e preserva a visibilidade; `hide({id, version})` restringe a mestres
e preserva o progresso; `reveal({id, version})` completa a descoberta e permite
visibilidade aos jogadores. Excluir aceita `{id, version}`. Versões e UUIDs de
tentativa seguem os recibos nativos; um antigo mestre não pode reutilizar um
recibo privado após perder a autoridade.

`scopeSceneId` controla o escopo salvo; `sceneId`/`mapId` fornece o contexto de
visualização, como nos relógios. Leituras nativas usam a rota GET compatível com
espectadores. Assinaturas de `clues.changed` releem o estado projetado no envelope
de recursos abaixo. O nó `clueControl` do MapBuilder delega somente o efeito
configurado e não concede alterações diretas aos jogadores. Ensaios desfazem
suas alterações e notificações. Veja [pistas](clues.md) para uso e ações do nó.

### Mapas mentais colaborativos e vínculos tipados

O domínio `mindmaps` lê grafos compartilhados pelas permissões atuais de cada
pessoa. Não usa a cena atual implicitamente: `state({})` lista todos os mapas
acessíveis; `state({sceneId})` seleciona mapas de campanha e daquela cena.
Módulos vinculados explicitamente a uma cena mantêm esse contexto autoritativo.

| Método | Payload e resultado |
| --- | --- |
| `state` / `read` | `{sceneId?}` / `{id, sceneId?}`; envelope da coleção / um mapa projetado |
| `resources` | `{query?, kinds?, limit?, sceneId?}`; `{kinds:[{id,label}], resources:[...], truncated}` |
| `resolve` | `{reference}`; exibição autorizada atual de um recurso ou `null` para destinos ausentes/negados |
| `create` | `{name, visibility?, editorIds?, scopeSceneId?, document?}`; exclusivo do mestre, padrão privado e escopo de campanha |
| `update` | `{id, version, name?, document?, visibility?, editorIds?, scopeSceneId?}` |
| `node` | `{id, version, nodeId, patch}`; altera os campos informados de um tópico |
| `delete` | `{id, version}`; exclusivo do mestre |

`visibility` é `gm` ou `players`. `editorIds` contém UUIDs de jogadores atuais da
campanha; selecionados leem/editam mesmo mapas privados. Todos os mestres editam,
e a visibilidade pública concede somente leitura aos demais. Jogadores alteram
`name`, `document` e campos dos tópicos; escopo/acesso continuam exclusivos dos
mestres. Streamers não escrevem. Escritas retornam `{id, version, mindmap}`
(excluir retorna `{id}`), usam recibo separado e exigem a versão salva para mapas
existentes. Conflitos exigem revisão do estado atual sem trocar silenciosamente
a versão esperada do rascunho. `mindmaps.changed` usa o envelope de recursos.

O documento é `{nodes, edges}`. Tópicos têm UUID `id`, `parentId` opcional,
`label`, `notes`, `color` hexadecimal, `x`, `y`, `collapsed`, `completed` e `links`.
Vínculos de pais formam uma floresta sem ciclos. Arestas adicionais são
`{id, from, to, label?}` entre tópicos existentes. Patches aceitam esses campos
dos tópicos, exceto `id`. Os limites são 64 mapas por campanha, 500 tópicos/1.000
arestas por mapa, 16 vínculos por tópico/2.048 no total e 1 MiB por documento.
Títulos têm 240 caracteres, notas 8.000 e coordenadas ficam entre ±100.000.

Referências canônicas são exatamente `{kind, id, pageId?}`. O
[registro de recursos](../../gravewright/table/resource_links.py) define 37 tipos,
incluindo IDs numéricos nativos, entradas de compêndios instalados
(`packId/entryId`), páginas (`id: journalId` com `pageId`) e desenhos
(`sceneId/drawingId`). Descubra os tipos por `resources`, sem inferi-los pelos
rótulos. A busca aceita até 120 caracteres; `limit` tem padrão 80 e intervalo
1–200. Rótulos vêm das projeções nativas atuais. Nomes autorais ficam literais;
`labelKey`/`descriptionKey` opcionais identificam textos gerados para o Translator.

Vínculos ausentes e negados são projetados igualmente como `{unavailable:true,
key}`, sem tipo/ID/nome/URL ocultos. Devolva o marcador opaco intacto ao editar
outros conteúdos ou omita-o para remover o vínculo. Ele não autoriza criar uma
referência oculta. Abrir novamente revalida as permissões; nomear o destino ou
compartilhar um mapa não concede acesso ao recurso. Veja [Mapas mentais](mindmaps.md)
para tipos, colaboração, nós do MapBuilder e remapeamento tipado dos arquivos.

### Vínculos de recursos nos diários

`api.journals.resources({query?, kinds?, limit?, sceneId?}, options)` busca no
mesmo catálogo tipado de campanha dos mapas mentais.
`api.journals.resolve({reference}, options)` devolve `{resource: row | null}` após
verificar o acesso atual ao destino. Ambos são métodos de leitura disponíveis
a jogadores e streamers autorizados. Leituras sem cena vinculada não herdam a
cena transmitida; uma cena explicitamente vinculada continua sendo a autoridade.

O texto mantém `gw-journal-doc-v1`, versão 1. A referência é um átomo inline:

```json
{"type":"gwResourceLink","attrs":{"reference":{"kind":"journal-page","id":"<journalUUID>","pageId":"page_main"}}}
```

O vínculo salvo contém apenas `kind`, `id` e `pageId` opcional. A projeção de
cada destinatário acrescenta metadados atuais e uma `key` opaca; destinos sem
acesso tornam-se `{unavailable:true,key}`, sem identidade ou título. Devolva o
marcador intacto para preservá-lo numa edição autorizada. Ele está vinculado ao
diário de origem e não cria uma conexão privada nova. Cada diário aceita até
512 referências; os limites normais de tamanho e profundidade também se aplicam.
O salvamento usa a versão e o UUID de operação existentes do diário.

As leituras nativas usam `GET /api/containers/{campaign}/journals/resources` com
parâmetros `query`, `kinds` (array JSON), `limit` e `sceneId` opcional, e
`GET /api/containers/{campaign}/journals/resolve?reference=<JSON>`. As respostas
são privadas e não ficam em cache. Pacotes Python usam
`api.journals.resources(campaign_id, user_id, *, query='', kinds=None, limit=80,
scene_id=None)` e `api.journals.resolve(campaign_id, user_id, reference)`.
A busca não muda a presença ou navegação na mesa. Veja
[Diários e referências](journals.md) para edição, acesso e cópias portáteis.

### Capítulos e páginas dos diários

Atualizações usam o comando existente do diário, a versão esperada e o UUID de
operação. O payload `data` pode incluir capítulos independentes, inclusive vazios:

```json
{
  "chapters": [
    {"id":"chapter_main", "name":"Chapter one", "parentId":null, "sortOrder":10},
    {"id":"chapter_child", "name":"A subchapter", "parentId":"chapter_main", "sortOrder":10}
  ],
  "sections": [
    {"id":"page_main", "title":"A page", "kind":"text", "chapterId":"chapter_child"},
    {"id":"page_loose", "title":"An ungrouped page", "kind":"text", "chapterId":null}
  ]
}
```

Cada página pertence a nenhum ou a um capítulo. Cada capítulo tem nenhum ou um
pai e pode conter de zero a várias páginas e subcapítulos. Os IDs são locais ao
diário; copiar uma campanha os preserva sem tratá-los como UUIDs de recursos.
IDs de capítulos são únicos, com 1–40 letras ASCII, números, sublinhados ou
hífens; nomes têm 1–80 caracteres. O servidor permite até 128 capítulos, oito
níveis e as 64 páginas existentes. Pais ausentes, ciclos e vínculos de página
para capítulos inexistentes são rejeitados antes de salvar. `sortOrder` ordena
capítulos dentro de cada pai.

A projeção autorizada expõe `chapters` junto com `sections`. Páginas privadas
continuam filtradas, assim como os ramos compostos apenas de páginas sem acesso.
Ancestrais de páginas legíveis e ramos realmente vazios permanecem visíveis.
Apresentações de uma página incluem apenas seu caminho de capítulos. Atualizações
preservam as páginas ocultas protegidas pelo servidor e a estrutura necessária
para esses vínculos.

Nomes legados de `sections[].category` recebem IDs estáveis na normalização;
`category` permanece como espelho do nome para compatibilidade. Um
`chapterId: null` explícito remove o vínculo da página. Atualizações antigas que
omitem `chapters` mantêm os capítulos existentes, inclusive vazios. O histórico
e os arquivos portáteis da campanha preservam a árvore.

### Operações dos sistemas e PDF System

O host encaminha `api.system.call(name, data, options)` somente ao provedor do
sistema atual da campanha. Nome ou payload não selecionam outro sistema.
Pacotes confiáveis de servidor registram callbacks no `AppConfig.ready()` com
`api.systems.register_api(system_id, operations)`. Cada entrada declara
`{effect: "read" | "write", handler, description?}`, sem consultar o banco no
registro. O handler recebe `(campaign_id, user_id, payload, request_id, scene_id)`
e controla validação dos recursos, transações, revisões, recibos e notificações.
O host verifica participação atual, limita o JSON, impede trocar a cena montada
e rejeita escritas de streamers antes de chamar o handler.

O provedor PDF integrado expõe estes nomes pela API genérica:

| Operação | Dados e comportamento |
| --- | --- |
| `pdf.read` | `{actorId, tokenId?}`; ficha nativa autorizada com `source` atual |
| `pdf.configure` | `{actorId, tokenId?, source, version, sheetVersion, changes}`; configuração parcial exclusiva do mestre |
| `pdf.exportMapping` | `{actorId, tokenId?, source?}`; pacote portátil sem PDF ou valores, exclusivo do mestre |
| `pdf.applyMapping` | `{actorId, tokenId?, source, version, sheetVersion, bundle}`; aplicação em ator ou token independente pelo mestre |
| `pdf.diagnostics` | `{actorId, tokenId?, source?, document?}`; diagnóstico de metadados/cálculos sem gravação |
| `preparation.diagnostics` | `{}`; problemas de fichas salvas para o painel de preparação, exclusivos do mestre, sem ler bytes do PDF |
| `pdf.roll` | `{actorId, tokenId?, field, source?, visibility?, sceneId?}`; ação salva autorizada com dados/chat e recibos nativos |
| `pdf.templates.list` / `read` / `export` | `{}` / `{id}` / `{id}`; biblioteca da campanha para o mestre |
| `pdf.templates.create` / `update` | `{name, bundle}` / `{id, revision, name, bundle}` |
| `pdf.templates.delete` / `import` | `{id, revision}` / `{name, bundle}`; importação aceita JSON original ou objeto existente |
| `pdf.templates.apply` | `{id, revision, targets:[{actorId, version, sheetVersion, source}]}`; lote atômico de até 100 atores |

`changes` aceita `manualFields`, `fieldActions`, `fieldBindings`,
`calculatedFields` sem origem, `bindings` das barras e metadados esperados em
`document`. Seções omitidas e valores atuais são preservados. A validação de
cálculos e ciclos continua nativa. Snapshots mantêm nome, permissões e valores
da própria cópia. Importações conservam o limite de 1 MB por arquivo e rejeitam
chaves duplicadas/números não finitos quando recebem o texto original.

```javascript
const capabilities = await api.system.state();
const sheet = await api.system.call('pdf.read', { actorId });
const bundle = await api.system.call('pdf.exportMapping', { actorId, source: sheet.source });
const template = await api.system.call('pdf.templates.create', {
  name: 'Mapeamento reutilizável', bundle,
}, { requestId: crypto.randomUUID() });
```

Inspeção com PDF.js, renderização achatada, seleção e histórico permanecem no
navegador. O diagnóstico do servidor usa vínculos/cálculos salvos e um descritor
opcional observado pelo cliente; não afirma interpretar bytes do PDF.
Veja o fluxo de mapeamento, cálculo e exportação no [guia do PDF System](pdf-system.md).

### Métodos binários dos domínios

Métodos binários recebem `File`/`Blob` real em `payload.file`, usam multipart com
CSRF e conservam a identidade da ativação/montagem do módulo. Downloads retornam
`{blob, name, contentType, size}`. Arquivos não são codificados no corpo JSON.

| Método | Payload adicional |
| --- | --- |
| `maps.upload` | `{name, settings?, activate?}` |
| `maps.importUniversalVtt` | `{name, folderId?, builderEditable?}`; use `options.requestId` ao repetir a importação |
| `library.upload` | `{purpose?, folderId?}`; uploader nativo de imagens/áudio/PDF |
| `library.download` | `{id, kind?: "image" | "audio" | "pdf"}` |
| `actors.uploadAsset` / `downloadAsset` | `{folderId?}` / `{id}`; provedor de arquivos do sistema e download autorizado |
| `actors.uploadImage` | `{id, kind: "portrait" | "token"}` |
| `audio.upload` | `{name?, purpose?, folderId?}` |
| `cards.uploadAsset` | `{purpose: "card_front" | "card_back"}` |
| `journals.uploadAsset` / `downloadAsset` | `{journalId}` / `{id}` |

Valem os limites nativos de formato, tamanho e complexidade. Uploads criam
arquivos e não têm recibos de repetição, exceto UVTT. Guarde os IDs retornados
antes de iniciar outra importação. `onProgress` informa bytes concluídos e
`signal` cancela trabalho; descartar o contexto impede callbacks posteriores.
Transferências começam sem prazo artificial, com `timeoutMs` opcional. IDs de
outra campanha são rejeitados mesmo quando o usuário participa das duas.
Os handlers continuam verificando propriedade e visibilidade das páginas;
a URL ou o adaptador não concedem acesso por si mesmos.

### Adaptadores de conta, campanha, proprietário e módulos

Disponíveis no objeto global `gravewright`, não na API restrita a domínios do módulo:

| Adaptador | Métodos |
| --- | --- |
| `accounts` | `status`, `session`, `login(payload)`, `register(payload)`, `setup(payload)`, `logout`, `update(payload)`, `home(kind)`, `privacy` |
| `campaigns` | `list`, `management(id)`, `create(payload)`, `update(id, payload)`, `join(code)`, `remove(id, code)`, `invite(id, payload)`, `removalCode(id, payload)`, `invitationStatus(id)`, `revokeInvitation(id)`, `banMember(id, payload)`, `onboarding(id)`, `configureOnboarding(id, payload)`, `claimCharacter(id)`, `streamerLink(id)`, `revokeStreamer(id)`, `rulesets`, `preparation(id)`, `prepare(id, action, payload, requestId)`, `references(id, type, documentId)`, `viewAs(id, userId)`, `journalHistory(id, journalId)`, `journalRevision(id, revisionId)`, `journalTrash(id)` |
| `administration` | `status`, `diagnostics`, `settings`, `updateSettings(section, payload)`, `snapshots(id)`, `createSnapshot(id, payload)`, `snapshotAction(id, snapshotId, action, payload)`, `previewSnapshot(id, snapshotId)`, `restoreSnapshot(id, snapshotId, payload)`, `deleteSnapshot(id, snapshotId, payload)`, `clonePreview(id, payload)`, `clone(id, payload)`, `exportCampaign(id)`, `importCampaign(file, payload)` |
| `administration.updates` | `check`, `notification`, `channel(payload)`, `apply(payload)` |
| `modules` | `list`, `catalog`, `catalogLatest`, `status`, `install(payload)`, `state(tableId)`, `configure(tableId, payload)`, `activation(payload)`, `update(payload)`, `removalPreview(payload)`, `remove(payload)`, `defaultMarketplace`, `configureDefaultMarketplace`, `acknowledge(tableId, payload)`, `localInstallationInfo`, `installLocal(file, payload)` |

Todo método aceita um argumento final `options` opcional com `signal` e `timeoutMs`; transferências de arquivos também aceitam `onProgress`. As assinaturas e os nomes nativos dos campos estão documentados em [`global-api.js`](../../gravewright/modules/static/gravewright_modules/global-api.js). Ações de snapshots preservam `{confirm}` fornecido pelo chamador, e a remoção de pacotes preserva `confirmedTables`; os adaptadores não preenchem aprovações automaticamente. A exportação retorna `{blob, name, contentType, size}`. A importação de campanha recebe um ZIP como `File`/`Blob` e `{title}` opcional; a instalação local de pacote recebe um ZIP e `{kind: "module" | "system"}`. Não existe endpoint nativo de download de snapshot. Criar a referência da API não executa ações administrativas.

`campaigns.management(id, options)` lê o resumo da campanha exclusivo do mestre sem carregar a mesa nem entrar em sua presença. A [área de gerenciamento](campaign-management.md) usa os mesmos serviços nativos de documentos e verifica o vínculo atual de mestre daquela campanha.

As [ferramentas de preparação](campaign-management.md#ferramentas-de-preparação) usam outros métodos exclusivos do mestre. `preparation(id)` lê planos de sessão, eventos da cronologia, o painel de quem chama, pendências e o diagnóstico de fichas do sistema. `prepare(id, action, payload, requestId)` executa um comando: `session-create`, `session-update`, `session-finish`, `session-reopen`, `session-delete`, `event-create`, `event-update`, `event-delete` ou `board-update`. Repetir o mesmo comando reutiliza seu UUID de requisição. Alterações e exclusões enviam a `revision` atual do registro; uma revisão desatualizada é recusada com HTTP 409. `references(id, type, documentId)` lista os vínculos e usos de um personagem, item, diário ou cena. `viewAs(id, userId)` devolve as projeções nativas de diários, atores, itens e cenas que um jogador recebe. `journalHistory(id, journalId)`, `journalRevision(id, revisionId)` e `journalTrash(id)` leem versões de diários, uma comparação linha a linha com a versão atual e os diários excluídos. Requisições de preparação recusadas informam o motivo no campo JSON `error`.

Payloads de preparação usam estes campos nativos. Criar retorna `{id, revision}`;
alterar o painel retorna `{revision}`. Campos omitidos em atualizações preservam
seus valores atuais.

| Ação | Payload |
| --- | --- |
| `session-create` / `session-update` | `{title, scheduledFor?, steps?, checklist?, notes?}`; atualizar também exige `{id, revision}` |
| `session-finish` | `{id, revision, summary, pending?}`; pendências usam itens de checklist |
| `session-reopen` / `session-delete` | `{id, revision}` |
| `event-create` / `event-update` | `{title, worldDate?, position?, date?, upcoming?, description?, links?}`; atualizar também exige `{id, revision}` |
| `event-delete` | `{id, revision}` |
| `board-update` | `{revision, pins?, widgets?}`; altera somente o painel de quem chama |

Uma etapa usa `{id, kind, refId, label, done}`; `kind` pode ser `actor`, `item`,
`journal`, `scene`, `encounter`, `track`, `playlist` ou `note` (notas usam
`refId: null`). Um item de checklist usa `{id, text, done}`. Vínculos de eventos e
itens fixados usam `{type, id}` para os mesmos tipos, exceto `note`. Datas usam
`YYYY-MM-DD` ou `null`; datas do mundo continuam texto. IDs dos painéis são
`pins`, `session`, `pending`, `diagnostics`, `events`, na ordem desejada e sem
repetições. O serviço valida campanha e [limites da preparação](campaign-management.md).

Escritas no histórico usam a API `journals` vinculada à mesa e UUIDs de operação:

| Método | Payload |
| --- | --- |
| `setPrerequisites` | `{journal_id, version, prerequisites: [questId, ...]}`; exclusivo do mestre, missões da mesma campanha, rejeita ciclos |
| `restoreRevision` | `{journal_id, revision_id, version}`; `version` deve ser o `current.version` devolvido pela comparação exibida |
| `restoreDeleted` / `purgeDeleted` | `{revision_id}`; ID da entrada excluída, em vez do antigo UUID do diário |

Restaurações revalidam acesso padrão, pré-requisitos e anexos físicos. Uma falha
preserva o diário/lixeira atual. Após um conflito, obtenha outra comparação antes
de restaurar; substituir a versão esperada sem revisão descartaria edições de
outro mestre. Leituras e escritas de histórico/lixeira verificam novamente o
vínculo atual de mestre, inclusive ao repetir recibos.

Permissões de proprietário e gerenciamento da campanha continuam verificadas no servidor. Os métodos usam cookies de sessão e obtêm token CSRF antes de escrever. Não há autenticação por chave de API nessa interface. Views e testes dos apps definem os payloads; não coloque credenciais no código de módulos.

O cabeçalho da biblioteca usa `POST /api/admin/updates/notification`, exclusivo do proprietário, com JSON vazio e o token CSRF normal. A resposta compacta inclui `status`, `available`, versões instalada/disponível e seus rótulos, `channel`, `checkedAt` e a URL interna de Atualizações. Ela reaproveita o cache de consulta por 24 horas; consultas simultâneas com cache expirado recebem `checking` enquanto uma requisição atualiza os metadados. A rota não inicia instalação nem expõe artefatos da release ou erros internos.

`GET /api/marketplace?latest=1`, exclusivo do proprietário, retorna uma release compatível e não revogada por ID de pacote, escolhendo a maior versão numérica `X.Y.Z` após validar o catálogo assinado completo e aplicar suas revogações. Sistemas e Módulos usam essa seleção na instalação. Sem `latest=1`, a rota continua retornando todas as releases compatíveis e não revogadas; a instalação por versão exata continua disponível.

`GET /api/admin/status` inclui `updates.installedRelease` com `version`, `name` completo, `notes`, `url` canônica do GitHub e `source` (`bundled`, `published` ou `metadata`). Respostas de verificação explícita incluem a mesma apresentação. As notas locais estão disponíveis sem consulta ou acesso à rede e não são gravadas no cache de atualização. As notas têm limite de 128 KiB em UTF-8; a versão numérica e as regras de comparação são independentes do nome exibido.

### Eventos de domínio

Use `api.events.on(name, handler)`, que retorna uma função para cancelar a assinatura. Assinaturas são removidas junto com o ciclo de vida da API. Nomes suportados:

```text
actors.changed       tokens.changed       maps.changed
maps.layersChanged   journals.changed     items.changed
combat.changed       cards.changed        audio.changed
compendiums.changed  chat.changed         chat.message
table.presence       table.lobbyChanged   clocks.changed   clues.changed
mindmaps.changed
```

Assinaturas de mudanças em coleções fazem leitura HTTP autorizada inicialmente, após invalidações correspondentes do socket e na reconexão. Invalidações concorrentes são agrupadas; não representam todas as mutações intermediárias. Callbacks de ator/token/mapa/documento recebem o estado projetado e a identidade da mesa/cena; callbacks de item/combate/cartas/áudio/compêndio/relógio/pista/mapa mental recebem `{module, state, tableId, sceneId?}`. `chat.changed`, `chat.message`, presença e sala de espera encaminham payloads do socket sem ler automaticamente o estado inicial. Consulte esse estado separadamente quando necessário.

Assinaturas usam o socket da página atual. Uma API criada com `forTable` em `/inside`, ou apontando para outra mesa, faz requisições HTTP, mas não cria socket para essa mesa. Não presuma atualizações contínuas. Callbacks devem ser síncronos; inicie tarefas assíncronas explicitamente com tratamento de erro. O `events` antigo do bloco usa outros nomes e possui ressalvas descritas no [guia de módulos](modules.md#arquivos-persistência-e-eventos).

## Operações originais validadas por schema

Use `host.call` do bloco montado ou do contexto de ciclo de vida/personalização. Schemas de entrada/saída/eventos/contexto estão relacionados em [`contracts/registry.json`](../../gravewright/modules/contracts/registry.json); semântica de ciclo de vida e armazenamento, em [`contracts/api.json`](../../gravewright/modules/contracts/api.json).

| Operação | Escopo | Finalidade |
| --- | --- | --- |
| `actor.list`, `actor.read` | Mesa | Ler resumos/documentos de atores visíveis |
| `actor.create`, `actor.update`, `actor.delete` | Mesa | Criar, alterar campos fornecidos ou excluir logicamente com revisão |
| `actor.data.read`, `actor.data.update` | Mesa | Ler/substituir todos os dados do sistema |
| `token.read`, `token.move` | Cena | Ler token ou mover seu centro em pixels da cena |
| `token.data.read`, `token.data.update` | Cena | Ler/substituir dados do ator vinculado ou snapshot do token |
| `asset.list`, `asset.upload`, `asset.download` | Mesa | Listar/enviar/baixar modelos PDF do sistema atual |
| `actor.image.upload` | Mesa | Enviar retrato/imagem do ator com validação nativa |
| `card.asset.upload` | Mesa | Enviar imagem reutilizável de frente/verso de carta; apenas mestre |
| `locale.apply` | Local | Aplicar catálogo de idioma durante a montagem |

```javascript
const actor = await host.call("actor.read", { id: actorId });
const data = await host.call("actor.data.read", { id: actorId });
// Consulte os campos de revisão e substituição do schema antes de escrever.
```

Operações de cena exigem uma cena montada; um ID arbitrário no payload não cria essa autorização. `actor.data.update` e `token.data.update` substituem objetos completos, inclusive arrays/objetos internos; `null` é valor, não instrução de exclusão. `actor.update` altera apenas campos fornecidos. Confira cada campo de revisão: revisões do SDK não equivalem às versões de entidade da API de domínio.

Uploads recebem `File`/`Blob` real em `payload.file`, usam multipart autenticado e derivam metadados no servidor. Envio de modelo PDF é exclusivo do mestre e limitado a 10 MiB. Downloads retornam `{blob, name, contentType, size}`. `options.onProgress` informa conclusão nesse transporte SDK por fetch, não progresso contínuo. `options.signal` é suportado; cancelamento não desfaz mutação confirmada.

`card.asset.upload` é uma adição ao SDK 1.0 disponível no Gravewright 0.2.3 ou posterior. Recebe `purpose: "card_front" | "card_back"` e `File`/`Blob`, valida PNG/JPEG/WebP de até 10 MiB e 16 megapixels pelo uploader nativo de cartas e retorna `{assetId}`. O arquivo pertence ao mestre autenticado e à mesa atual. Reutilize o ID em `api.cards.define` como `front_asset_id` ou `default_back_asset_id`; as instâncias do baralho referenciam a mesma imagem armazenada. Cada upload cria um novo arquivo e não possui recibo de repetição: guarde os IDs retornados antes de iniciar outra importação. Não exige migração de banco nem alteração da versão principal do SDK.

```javascript
const { assetId } = await context.host.call("card.asset.upload", {
  file: new File([await context.assets.bytes("cards/front.png")], "front.png", { type: "image/png" }),
  purpose: "card_front",
});
const definition = await context.api.cards.define({
  name: "Meu baralho", cards: [{ name: "Um", front_asset_id: assetId }],
});
await context.api.cards.instantiate({ deck_definition_id: definition.deck.id });
```

| Erro público do módulo | Significado |
| --- | --- |
| `not_found` | Recurso ausente ou indisponível nesse contexto |
| `permission_denied` | Usuário sem permissão para a ação |
| `invalid_data` | Falha de validação de payload/schema/caminho/valor |
| `conflict` | Conflito de revisão de entidade, armazenamento, ativação ou registro |
| `unavailable` | Operação desconhecida, SDK incompatível ou falha do serviço (HTTP 503), incluindo um provedor obrigatório do sistema que não está habilitado |
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
| `api` | `API_VERSION == "1.0"`, `capabilities()`; o marcador Python é independente da API de navegador `1.2.0` e do SDK `1.0.0`. [Implementação do catálogo](../../api/__init__.py) |
| `api.campaigns` | `management(campaign_id, user_id)`; [resumo da campanha exclusivo do mestre](../../gravewright/campaigns/management.py) e [guia de gerenciamento](campaign-management.md) |
| `api.actors` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `sheet(campaign_id, user_id, actor_id, token_id=None)` |
| `api.tokens` | `state(campaign_id, user_id, map_id)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.maps` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `layer_state(campaign_id, user_id, scene_id)` |
| `api.map_builder` | Catálogo de projetos editáveis, revisões, geração, atualização de cenas e adoção; [exports públicos](../../api/map_builder.py), [assinaturas dos projetos](../../gravewright/maps/builder_services.py), [assinatura de adoção](../../gravewright/maps/builder_import.py) |
| `api.map_blueprints` | Templates de campanha, redes de cenas, controles e ensaios; [exports públicos e referências às assinaturas dos serviços](../../api/map_blueprints.py) |
| `api.universal_vtt` | Importação/exportação nativa de mapas; [exports públicos](../../api/universal_vtt.py) e [assinaturas](../../gravewright/maps/universal_vtt.py) |
| `api.pdf_system` | Fichas, configuração de mapeamento, diagnósticos, rolagens salvas e templates; [exports públicos](../../api/pdf_system.py) e [assinaturas](../../gravewright/pdf_system/public.py) |
| `api.systems` | `capabilities(campaign_id, user_id)`, `call(campaign_id, user_id, operation, payload, request_id=None, *, scene_id=None)`, `register_api(system_id, operations)`; [contrato de provedores](../../gravewright/campaigns/system_api.py) |
| `api.library` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, payload, request_id)`; [serviço nativo da biblioteca](../../gravewright/maps/library_services.py) |
| `api.ownership` | `state(campaign_id, user_id, kind, resource_id)`, `command(campaign_id, user_id, kind, resource_id, payload, request_id)`; [serviço do mestre para documentos, pastas e páginas](../../gravewright/table/permission_services.py) |
| `api.journals` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `resources(campaign_id, user_id, **search)`, `resolve(campaign_id, user_id, reference)` |
| `api.clocks` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)`; ações `create`, `update`, `advance`, `reset`, `delete` |
| `api.clues` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)`; ações `create`, `update`, `advance`, `reset`, `reveal`, `hide`, `delete` |
| `api.mindmaps` | `state(campaign_id, user_id, scene_id=None)`, `read(campaign_id, user_id, mindmap_id, scene_id=None)`, `resources(campaign_id, user_id, *, query='', kinds=None, limit=80, scene_id=None)`, `resolve(campaign_id, user_id, reference)`, `command(campaign_id, user_id, action, data, request_id)`; ações `create`, `update`, `node`, `delete` |
| `api.items`, `api.combat`, `api.cards`, `api.audio`, `api.compendiums` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.combat.register_provider` | Registro de callbacks pelo sistema em `AppConfig.ready()`; veja [provedores de combate](modules.md#provedores-de-combate-do-sistema) |
| `api.resources` | `state(campaign_id, user_id, name, scene_id=None, preview_token_id=None)`, `command(campaign_id, user_id, name, action, data, request_id)` |
| `api.chat` | `history(campaign_id, user_id, map_id=None)`, `send(campaign_id, user_id, text, request_id, map_id=None)`, `remove(campaign_id, user_id, message_id=None)` |
| `api.dice` | `evaluate(expression, repeat=1, *, random_source=None)`, `roll(campaign_id, user_id, expression, request_id, *, repeat=1, label="", visibility="public", map_id=None)` |
| `api.table` | `search(campaign_id, user_id, query)`, `lobby(campaign_id, user_id)`, `update_lobby(campaign_id, user_id, payload)` |
| `api.events` | `Change`, `resource_changed` |
| `api.errors` | `AuthError`, `JournalError`, `MapError`, `RollError` |

Use argumentos posicionais como no exemplo quando nomes de parâmetros diferirem. `resources` seleciona `items`, `combat`, `cards`, `audio`, `compendiums`, `clocks`, `clues` ou `mindmaps` pelo nome. `dice.evaluate` calcula localmente; `dice.roll` salva/publica uma rolagem. Exceções Python preservam tipos/códigos dos serviços originais, sem a normalização de sete códigos do navegador.

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

O endpoint de domínio do host é `POST /api/tables/<table_id>/api`; módulos instalados usam `POST /api/tables/<table_id>/modules/<module_id>/api`. Recebem `{domain, method, payload, requestId?}` e retornam `{value}`. Módulos também enviam `mountId`, `moduleSetRevision` e `sceneId` opcional; a ponte abre o lease antes. Métodos binários usam o sufixo `/files` correspondente, com metadados JSON no campo multipart `metadata` e o arquivo em `file`; downloads retornam bytes. O SDK antigo usa o mesmo prefixo do módulo com `/call` e envelope `{name, payload, ...context}`. As URLs descrevem a implementação para mantenedores; módulos devem usar as APIs fornecidas.

Depois de alterar o registro de métodos:

```sh
uv run --locked python scripts/generate_frontend_api.py
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.table.tests.test_public_api gravewright.modules
node --test tests/modules/*.test.mjs
```

`frontend-contract.js` é gerado a partir de `frontend.json`; altere o registro fonte primeiro. Preserve consistência de autorização, payloads e pós-commit entre frontend nativo, módulos e Python. Ao adicionar operação no SDK original, atualize schemas, registro, constantes de operações, dispatcher e testes em conjunto; não existe gerador genérico para todos esses arquivos.

## Tradu??es de m?dulos (Translator)

Os m?dulos recebem `context.i18n` e `context.api.i18n`. Registre os cat?logos em
`start(context)` e use a API fornecida ? superf?cie para traduzir seus controles:

```javascript
export default {
  start({ i18n }) {
    i18n.register({
      en: { 'sheet.title': 'Character sheet', 'sheet.greeting': 'Welcome, {name}' },
      'pt-BR': { 'sheet.title': 'Ficha de personagem', 'sheet.greeting': 'Boas-vindas, {name}' },
      es: { 'sheet.title': 'Ficha de personaje', 'sheet.greeting': 'Bienvenido, {name}' },
    });
  },
  register({ register }) {
    register('actor.directory', async ({ root, api }) => {
      root.setAttribute('translate', 'no');
      root.textContent = api.i18n.t('sheet.greeting', { name: 'Arin' });
    });
  },
};
```

Tamb?m ? poss?vel carregar os cat?logos com
`await context.assets.json('locales/messages.json')`. `locale` segue o idioma da
interface escolhido pelo usu?rio. A busca usa o idioma exato, o idioma base, o
ingl?s e, por ?ltimo, a pr?pria chave. `t(chave, par?metros)` substitui par?metros
nomeados ou num?ricos como texto simples; use `textContent` ao exibir o resultado.
`has(chave)` verifica a cobertura; `number(valor, op??es)` usa `Intl.NumberFormat`;
`onChange(callback)` acompanha eventos de idioma e registro/remoção de catálogos
do mesmo namespace, devolvendo uma função para cancelar a assinatura. A troca de
idioma recarrega a página preservando a URL da mesa.

Os cat?logos s?o isolados pelo ID do m?dulo e compartilhados entre seus contextos
na p?gina. `register` devolve uma fun??o de remo??o; o descarte do contexto que fez
o registro tamb?m remove o cat?logo. Tradu??es parciais s?o aceitas, com um texto
em ingl?s para cada chave e os mesmos par?metros em todos os idiomas. Registre
durante a ativa??o para que as superf?cies reutilizem o cat?logo. N?o ? necess?ria
permiss?o HTTP nem servi?o externo de tradu??o. Sem Translator/pacotes de idioma,
a interface usa ingl?s. O adaptador nativo `gravewright.i18n` consulta o cat?logo
da interface; m?dulos instalados devem usar o contexto recebido.
