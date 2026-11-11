# Direção do tempo real

[Documentação](../README.pt-BR.md) · [English](../en/realtime-direction.md) · [Arquitetura](architecture.md)

## Objetivo e situação atual

Este documento registra a direção aprovada para o transporte de tempo real da mesa:
como os comandos por WebSocket, as invalidações após o commit e as projeções por
destinatário devem evoluir para reduzir latência e contenção no banco. O responsável
pelo projeto aprovou a direção em 2026-11-09, incluindo a mudança de autorização do
transporte da etapa 6.

Todas as etapas foram entregues em 2026-11-09; a [Arquitetura](architecture.md)
descreve o comportamento resultante e os [Testes](testing.md) listam os testes de
regressão. Dois itens condicionais não foram construídos porque as condições não se
cumpriram: validar o movimento fora da transação (etapa 3) e um cache de projeção
compartilhado (etapa 5). As medições abaixo descrevem o transporte antes destas etapas.

## Comportamento atual e custos medidos

As medições abaixo foram feitas em 2026-11-09 com uma campanha sintética num banco de
teste isolado. São amostras únicas do processamento dos manipuladores, não latência
de ponta a ponta, percentis nem limites de capacidade.

- Uma mudança confirmada em itens, combate, cartas, áudio ou compêndios agenda nove
  eventos internos (dez na importação de um compêndio de cena): cinco atualizações de
  recursos, mais camadas, atores, tokens e diários. Os manipuladores de camadas e de
  tokens também atualizam o áudio.
- Para um GM inscrito nos cinco módulos de recursos e nos diretórios de atores e
  diários, mover um token custa 32 comandos SQL e 6 frames por cliente, e uma mudança
  de áudio custa 108 comandos e 24 frames.
- Cada movimento de token reenvia as camadas completas do mapa. Com 102 imagens sem
  alteração, um movimento entregou 12.705 bytes em vez de 2.115.
- Cada socket processa comandos, entregas, amostras de cursor, arrasto e viewport e
  pongs numa única sequência. A fila de entrada não tem limite, e o limite de taxa é
  avaliado quando a mensagem é processada, não quando ela chega.
- O SQLite com `transaction_mode='IMMEDIATE'` serializa toda transação de escrita, e
  uma leitura de compêndio também abre `BEGIN IMMEDIATE`. Uma transação de escrita de
  um segundo atrasou uma escrita sem relação em cerca de 1,03 s, tanto no modo de
  journal DELETE quanto no WAL.
- Um timeout de lock (`OperationalError`) num manipulador de comando fecha o socket.
  O navegador reenvia mensagens de chat e rolagens pendentes a cada ping, o que soma
  trabalho duplicado justamente quando o servidor está lento.
- Todo frame recebido relê a sessão e o vínculo com a campanha (duas consultas). Todo
  pong de presença grava o lease e executa uma limpeza global dos leases expirados.
- As camadas do Channels descartam em silêncio uma mensagem de grupo quando a fila do
  canal está cheia (capacidade padrão de 100), então um consumidor lento pode perder
  uma invalidação.

## Invariantes

Todas as etapas preservam estas regras:

- O servidor filtra cada entrega por destinatário. Nenhum envelope, delta ou cache
  pode entregar a um destinatário um dado que a projeção completa dele não conteria.
- Um UUID de requisição identifica um comando lógico. Retentativas (`busy`, prazo e
  reconexão) o reutilizam; uma operação nova recebe um UUID novo.
- As notificações são agendadas após o commit, e os clientes sempre conseguem
  ressincronizar.
- Os comandos de escrita mantêm autorização, recibos e revisões dentro dos serviços
  responsáveis.
- A superfície de eventos do SDK (`createEvents` em
  `gravewright/modules/static/gravewright_modules/domain-api.js`) continua entregando
  os mesmos payloads. Qualquer mudança visível ao SDK passa por
  `gravewright/modules/contracts/frontend.json` e `scripts/generate_frontend_api.py`.
- O núcleo não contém nomes de sistemas de RPG. Pacotes só estendem as dependências
  de atualização por contratos genéricos.
- As retentativas automáticas são silenciosas. Qualquer texto novo na interface usa o
  mecanismo oficial de tradução (`en`, `pt-BR`, `es`).

## Etapas

As etapas seguem a ordem da tabela. A etapa 5 depende da etapa 4, e a etapa 7 usa a
tarefa de presença criada na etapa 2.

| Etapa | Mudança | Situação |
| --- | --- | --- |
| 0 | Medições de base e instrumentação | Entregue |
| 1 | Contenção do banco recuperável | Entregue |
| 2 | Faixas separadas por conexão | Entregue |
| 3 | Transações de escrita curtas | Entregue; a pré-validação condicional do movimento não foi necessária |
| 4 | Um envelope por commit | Entregue |
| 5 | Envio só do que mudou | Entregue; o cache condicional de projeção compartilhado não foi construído |
| 6 | Autorização do transporte em cache | Entregue (condição de início cumprida: a autorização era 25–50% das consultas nos caminhos de cursor, arrasto e pong) |
| 7 | Presença sem escrita a cada pong | Entregue |

### Etapa 0: base e instrumentação

- Um teste de orçamento versionado conta comandos SQL, frames e bytes por cenário,
  partindo dos valores acima. Uma saída opcional de benchmark registra medianas e
  percentis 95, no padrão de `GRAVEWRIGHT_EVENT_BENCHMARK_OUTPUT`.
- Avisos de manipulador lento informam espera na fila, tempo do manipulador,
  quantidade e tempo de SQL, frames e bytes, e erros de lock geram um aviso
  `database busy`. Uma nova configuração, `GRAVEWRIGHT_REALTIME_SLOW_MS`, controla o
  limite (padrão 500; `0` desativa). Os logs nunca incluem payloads nem conteúdo dos
  usuários. O Runner executa o Daphne no próprio processo, então esses avisos chegam
  a `data/logs/runner.log`.

Aceite: os orçamentos reproduzem os valores medidos, e as medições de base no
navegador ficam salvas antes de qualquer mudança de comportamento.

### Etapa 1: contenção do banco recuperável

- O navegador reenvia mensagens de chat e rolagens pendentes só depois de reconectar.
  Uma resposta `roll_in_progress` agenda uma única retentativa com espera crescente
  (1, 2, 4 e 8 segundos).
- Erros de lock do SQLite viram um erro recuperável `busy`, com o mesmo ID de
  requisição, e o navegador tenta de novo em silêncio com esse ID. Os demais erros de
  banco continuam falhando de forma visível.
- Quando a conclusão de uma rolagem encontra um lock, o servidor libera a reserva para
  que a retentativa a reivindique de novo. O resultado não confirmado nunca sai do
  servidor.
- Cada comando tem prazo de 45 segundos, acima do timeout de 30 segundos do SQLite. Ao
  expirar, o navegador trata o socket como falho e reconecta, o que reenvia os
  comandos pendentes com os IDs originais.
- Um erro de lock num manipulador de entrega não fecha o socket. A projeção afetada é
  enviada de novo na próxima manutenção do heartbeat.

Aceite: pings não geram reenvios duplicados, uma retentativa após `busy` é aplicada
uma única vez (um recibo), e erros que não são de lock se comportam como antes.

### Etapa 2: faixas separadas por conexão

- Amostras efêmeras (cursor, viewport e parada do viewport, e arrasto por stream) usam
  posições "o último valor vence", processadas numa thread separada por socket. As
  mensagens de fim e cancelamento de arrasto nunca são descartadas.
- A renovação do lease após um pong roda fora da faixa de comandos.
- Os comandos mantêm a ordem numa fila limitada (256 mensagens). O limite de taxa usa
  a hora de chegada, e as verificações de streamer e de mesa valem para todas as
  faixas.

Aceite: pongs, cursores e arrastos avançam enquanto um comando está bloqueado, os
comandos continuam ordenados, e o estouro da fila ou uma rajada excessiva fecha o
socket com 4429.

### Etapa 3: transações de escrita curtas

- Leituras, começando pelas leituras de compêndio, rodam sem `BEGIN IMMEDIATE` e
  mantêm as verificações de permissão atuais.
- Importações de compêndio validam os arquivos antes de a transação de escrita
  começar.
- Comandos de token procuram um recibo existente antes de pegar o lock de escrita e
  montam a projeção do ack depois do commit. As automações de região continuam dentro
  da transação, porque fazem parte da operação.
- Condicional: validar o movimento fora da transação, com conferência de revisão
  dentro dela, só se as medições mostrarem que a validação domina a transação e se as
  mudanças de paredes tiverem uma revisão conferível.

Aceite: leituras não abrem `BEGIN IMMEDIATE`, uma leitura termina enquanto outra
escrita segura o lock, retentativas concorrentes da mesma requisição geram um único
recibo, e os resultados dos comandos mantêm o contrato atual.

### Etapa 4: um envelope por commit

- `dispatch.changed` agenda um único evento `room.changes` com a lista de projeções a
  atualizar. Os sinais para extensões não mudam.
- Um mapa declarativo de dependências no núcleo primeiro reproduz os conjuntos de
  atualização atuais, sem duplicatas. Depois é estreitado com um teste que compara as
  projeções de cada usuário antes e depois de cada comando representativo.
- Os consumidores autorizam uma vez por envelope, verificam de novo antes dos recursos
  adiados, mantêm a ordem de entrega atual e emitem `api.changed` uma vez por domínio.
- O histórico do chat só é recarregado quando o envelope pede, e a consulta do
  histórico carrega os destinatários sem uma consulta por mensagem.

Aceite: toda projeção que muda para qualquer usuário de teste aparece no envelope,
cada projeção é entregue uma vez, e os orçamentos ficam abaixo dos valores da etapa 0.

### Etapa 5: envio só do que mudou

- Cada socket guarda o que recebeu por último. Projeções sem mudança não enviam nada.
  Tokens e camadas enviam deltas `upserts`/`removes` calculados a partir da projeção
  completa do destinatário. As primeiras inscrições e as ressincronizações enviam o
  estado completo.
- O navegador aplica os deltas e dispara os mesmos eventos com payloads completos,
  então o tabuleiro e o SDK não percebem mudança.
- Uma revisão por campanha, incrementada dentro da transação que faz o commit, permite
  ao consumidor detectar um envelope perdido e ressincronizar. Esta etapa adiciona uma
  migração.
- Condicional: um cache de projeção com chave por cena, revisão e usuário só entra se
  as medições com cinco jogadores ou mais mostrarem que a projeção domina.

Aceite: aplicar os deltas sempre reproduz a projeção completa daquele usuário, tokens
ocultos nunca aparecem em frames de jogadores, e mover um token numa cena com 102
imagens sem alteração não envia dados de camada.

### Etapa 6: autorização do transporte em cache

Esta é uma mudança aprovada de comportamento de segurança. Hoje, como descreve a
[Arquitetura](architecture.md), o socket relê a sessão no banco, o backend de
autenticação, o hash da sessão e o vínculo com a campanha a cada frame recebido,
entrega e heartbeat.

Aprovado em 2026-11-09:

- Um socket pode reutilizar a última autorização bem-sucedida por até **2 segundos**,
  e nunca além da data de expiração da sessão.
- Os eventos a seguir invalidam uma autorização em cache antes do processamento do
  próximo frame: logout, exclusão da sessão, troca de senha (para as outras sessões),
  remoção do participante, mudança de papel, desativação do usuário, revogação ou
  expiração do link de streamer e exclusão da campanha. Mudanças no mesmo processo
  incrementam de forma síncrona uma época de autorização local; os outros processos
  recebem um evento de invalidação pela camada do Channels.
- Caminhos de código que não disparam sinais de modelo (`QuerySet.update()` ou
  `.delete()`) precisam incrementar a época e enviar a invalidação explicitamente.
- Os comandos de escrita continuam autorizados pelos seus serviços.
- Condição de início: as medições das etapas 0–5 mostram que a autorização é um custo
  relevante nos caminhos de cursor, arrasto ou pong. Caso contrário, o comportamento
  atual permanece.

Aceite: cada invalidação fecha o socket no frame seguinte, mesmo dentro da janela de
2 segundos, e os testes de revogação existentes passam sem mudança.

### Etapa 7: presença sem escrita a cada pong

- `renew` recria um lease que a limpeza de outro socket removeu.
- Um lease só é renovado na segunda metade da sua validade. A limpeza de leases
  expirados passa para a manutenção do heartbeat e roda no máximo uma vez a cada meio
  TTL em cada processo, depois de uma verificação de existência.

Aceite: a presença sobrevive a um comando mais longo que o TTL, e cada janela de
renovação causa no máximo uma escrita.

## Fora desta direção

- Substituir o SQLite ou ativar o WAL. Isso só será avaliado depois destas etapas, com
  testes de portabilidade, backup e concorrência; a medição acima mostra que o WAL
  sozinho não elimina a serialização entre escritores.
- Transmitir estado sem filtro e escondê-lo no navegador.
- Manter sessões ou presença só na memória do processo, o que quebraria implantações
  com vários workers sobre Redis.
- Remover recibos ou revisões para economizar consultas.

## Validação

Cada etapa mantém verdes as suítes existentes de Django, Node e navegador e adiciona
testes de regressão para as suas garantias; os [Testes](testing.md) os documentam à
medida que forem adicionados. Contagens de SQL, frames e bytes são determinísticas e
podem virar tetos nos testes. Tempos são observações comparadas na mesma máquina e
fixture, nunca critérios de aprovação.
