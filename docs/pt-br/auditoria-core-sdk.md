# Auditoria de cobertura entre core e SDK 1

Data da auditoria: 14 de agosto de 2026. Este documento compara os serviços de
domínio do core com a SDK pública do navegador. Nem todo serviço interno deve
virar API: administração, persistência, transporte, renderização e instalação de
pacotes continuam pertencendo ao core por projeto.

Status da implementação: as prioridades 0–2 foram concluídas em 14 de agosto de
2026. Mutação opcional de assets, exclusão de chat, operações em lote de
luzes/efeitos e a automação de GM da Prioridade 3 continuam adiadas por decisão.

## Cobertura atual

O registry, as tabelas geradas, o runtime do navegador, a ponte de comandos do
servidor e os testes de contrato concordam com a superfície exposta atualmente.

| Domínio | Cobertura pública atual | Avaliação |
|---|---|---|
| Atores | Leitura/listagem, CRUD e patch validado dos dados | Boa |
| Itens | Leitura/listagem, CRUD central e patch validado dos dados | Boa |
| Tokens | Leitura/listagem, CRUD e movimento | Boa; HP e condições existem indiretamente nas ações de regra |
| Cenas | Leitura/listagem/ativa, geometria, efeitos, fog e imagens | Boa para ferramentas de gameplay |
| Combate | Estado, ciclo, turnos/rodadas, flags, rolagem e iniciativas | Boa |
| Chat e dados | Envio/leitura, dados autoritativos e intents de rolagem | Boa |
| Regras | Validação e execução de grafo semântico limitado | Boa |
| Cartas | Estado, embaralhar, resetar, comprar, revelar, descartar e jogar | Boa |
| PDFs | Leitura, navegação e CRUD completo de annotations | Boa |
| Assets | Listagem filtrada por permissão | Parcial |
| Conteúdo | Content packs e importação para campanha | Boa para conteúdo declarativo |
| UI e fichas | Slots, modais, toast, fichas HTML, controllers e helpers | Boa |
| Runtime de pacote | Settings, SQLite escopado, eventos, bus e localização | Boa |
| Journals e handouts | CRUD em runtime e apresentação transitória | Boa |
| Fog e imagens de cena | Fog limitado e colocações autorizadas | Boa |

## Adições implementadas

### Prioridade 0 — completar cartas

O core implementa revelar, descartar, jogar na cena, atualizar a colocação e
descartar a colocação com checagens de permissão. A SDK agora expõe essas
operações em `cards.manage`:

```js
sdk.cards.reveal(cardIds)
sdk.cards.discard(cardIds)
sdk.cards.play(cardId, { sceneId, x, y, rotation, scale, faceUp })
sdk.cards.updatePlacement(placementId, patch)
sdk.cards.discardPlacement(placementId)
```

Criação de definição, instanciação e exclusão de baralho só devem ser públicas
se jogos de cartas gerados em runtime forem um objetivo explícito. Caso
contrário, definições continuam como conteúdo declarativo e configuração do GM.

### Prioridade 1 — assimetrias de gameplay fechadas

- `sdk.items.patchData(itemId, patch)` é simétrico à escrita de atores.
- Combate expõe rolagem de iniciativa, avanço de rodada e flags seguras.
- Journals oferecem leitura/listagem e CRUD validado; a apresentação de handout
  é transitória e respeita a configuração da aplicação.
- Annotations de PDF oferecem update/delete além de list/create, com validação
  de região, página, autoria e visibilidade no servidor.
- HP e condições de token são ações semânticas suportadas. Criar
  atalhos diretos apenas se pacotes precisarem deles fora dos grafos de ação.

### Prioridade 2 — ferramentas de cena entregues

- Estado do fog, enable/disable, reset e pintura limitada.
- Colocação, atualização e remoção de imagens de cena usando assets autorizados.
- Operações avançadas de parede: split, movimento de nós e edição em lote limitada.
- Operações em lote opcionais para luzes e efeitos.
- Upload/criação/movimento/exclusão de assets, se houver fluxo orientado por pacote.
- Exclusão de mensagem pelo autor ou GM; limpeza em lote deve continuar administrativa.

### Prioridade 3 — automação opcional do GM

Criação, edição, ativação e agrupamento de cenas, upload de mapas e retile são
úteis para addons administrativos, mas aumentam riscos de storage e negação de
serviço. Se forem expostos, precisam de capability exclusiva de GM, limites de
tamanho, progresso e eventos de auditoria.

## Deve permanecer privado

- autenticação, sessões, membros, bans e convites;
- mudança de ownership e override de permissões;
- backup, restore, snapshots, imports e auditoria administrativa;
- instalação, enable, remoção e ativação de pacotes;
- banco, filesystem, rede, rotas HTTP e WebSocket brutos;
- renderer, tiles/chunks, prefetch preditivo e caches;
- repositories e mutações em lote sem limite.

Pacotes devem enviar intenções validadas. O servidor continua responsável por
membership, papel, visibilidade, ownership, capabilities, limites e versões.

## Estado da validação

A superfície entregue das prioridades 0–2 possui testes de contrato do registry
e bridge, testes HTTP de autorização, testes contra mutação entre campanhas e a
suíte de domínio do core. A automação opcional de GM permanece adiada para uma
análise própria de ameaças e limites de recursos.

Cada adição deve atualizar, na mesma mudança, o registry canônico, tabelas
geradas, runtime JS, ponte do servidor, DTOs, referências EN/PT-BR, fixtures,
testes de permissão e testes end-to-end de pacote.
