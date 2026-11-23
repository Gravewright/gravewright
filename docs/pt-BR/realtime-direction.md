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
| 8 | Carga de fundo encontrada numa sessão reproduzida | Entregue |
| 9 | Log de escrita antecipada (WAL) do SQLite | Entregue (decisão do dono, 2026-11-15) |
| 10 | Entregas numa faixa própria | Entregue (decisão do dono, 2026-11-15) |
| 11 | Trabalho repetido a cada amostra e troca de cena | Entregue (2026-11-15); as respostas de cena seguem a regra da etapa 6 |

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

### Etapa 8: carga de fundo encontrada numa sessão reproduzida

Em 2026-11-15, um mestre e três jogadores reproduziram uma sessão real da 0.3.5 com
navegadores reais, numa cópia daquela campanha e no perfil do Runner, no ritmo de
comandos dos seus recibos. Não houve erro de trava. Cada entrega de `room.changes`
custou cerca de 60 consultas SQL e 0,4 s por destinatário, e as ativações de cena pelo
mestre fizeram todos os clientes reassinarem ao mesmo tempo, o que gerou filas de
vários segundos. A maior parte do trabalho no banco não vinha do jogo:

- cada chamada de módulo instalado regravava o lease da montagem (cerca de 106
  escritas por minuto com quatro clientes, mais que todas as escritas do jogo juntas);
- o espaço de mapas mentais relia por HTTP a cada frame do socket, inclusive cursores
  de outros usuários (250–310 leituras por minuto);
- o cliente HTTP do SDK buscava um token CSRF novo antes de cada escrita;
- o tabuleiro do mestre renova o viewport a cada segundo, e cada amostra de câmera do
  mestre (`room.gm_sample`) esperava na faixa de comandos de cada destinatário
  (700–800 s por hora).

Mudanças:

- Chamadas de módulo só estendem o lease da montagem na segunda metade dos seus 30
  minutos.
- O espaço de mapas mentais ignora frames que não carregam estado da mesa: presença,
  amostras de ponteiro, arrasto e câmera e dicas de pré-carga.
- O cliente HTTP do SDK reaproveita um token CSRF por cliente e o busca de novo uma
  vez quando o servidor o recusa (`invalid_csrf_token`); a recusa acontece antes da
  view, então repetir a requisição não repete o efeito.
- As amostras de câmera do mestre usam a faixa de amostras de outros participantes,
  com um slot de valor mais recente por mestre.
- Enquanto o trabalho de um socket espera, o leitor do channel mantém no máximo um
  `room.presence` e um `room.lobby` na fila e junta um envelope `room.changes` ao que
  está logo antes dele na fila quando as revisões são consecutivas. O envelope
  juntado atualiza a união das projeções na ordem de entrega e leva `first_revision`,
  então um envelope perdido ainda provoca a atualização completa. Envelopes com
  teleportes não são juntados.
- A renovação de presença conta o meio TTL a partir de quando começou, então uma
  renovação que esperou o SQLite não empurra mais a próxima para depois do vencimento
  do lease.

Juntar as inscrições de cena que cada cliente envia depois de uma ativação não foi
feito: cada `resources.sync` executava em cerca de 22 ms e esperava cerca de 0,4 s
(p95 de 2,4 s) atrás de outro trabalho, então menos frames não removeriam esse trabalho.

Aceite: uma amostra do mestre chega a um destinatário com comando bloqueado e só a
amostra mais recente de cada mestre espera; leituras de presença repetidas rodam uma
vez; envelopes consecutivos são entregues uma vez com a união das projeções, enquanto
lacunas ainda atualizam tudo; um lease recente é lido sem escrita.

### Etapa 9: log de escrita antecipada (WAL) do SQLite

- `DATABASE_JOURNAL_MODE` escolhe o journal em cada conexão; `wal` é o padrão e
  `delete` mantém o journal de rollback para um banco numa pasta de rede. Com WAL um
  escritor confirma enquanto os leitores mantêm seu snapshot, então entregas, amostras
  e leituras de presença deixam de esperar cada commit. Os escritores continuam se
  revezando.
- Os arquivos `-wal` e `-shm` do banco fazem parte dele. O atualizador já os protege,
  faz backup pela API de backup do SQLite (que inclui o log) e os remove antes de
  restaurar um arquivo de banco. O executor de testes remove arquivos auxiliares
  deixados por uma execução interrompida antes de criar o banco de teste, porque o
  SQLite aplica um `-wal` a qualquer banco com aquele nome.
- O modo síncrono continua no padrão do SQLite, então um commit é durável quando
  retorna.

Aceite: as conexões informam `wal`; um escritor confirma enquanto um leitor mantém uma
transação de leitura aberta (o mesmo commit espera com `delete`); a atualização
gerenciada, a restauração após falha e o rollback mantêm o banco consistente.

Medido na reprodução da etapa 8 com troca de cena (uma sessão de 20 minutos por
journal, as duas com a faixa de entregas da etapa 10): o WAL baixou o percentil 99 do
tempo de SQL por consulta de 12,2 para 8,2 ms e o percentil 95 da ida e volta ao salvar
ficha de 1,6 s para 0,4 s. A maior parte do tempo restante é trabalho em Python, não
SQL.

### Etapa 10: entregas numa faixa própria

- Eventos do servidor (`room.changes` e os demais eventos do channel) esperam numa
  fila de entregas tratada por uma terceira tarefa por socket, com thread síncrona
  própria. Comandos e inscrições mantêm sua ordem na faixa de comandos e não esperam
  mais atrás de entregas; a faixa de entregas começa depois do connect, então eventos
  anteriores esperam em ordem.
- Comandos e entregas atualizam projeções. Cada projeção é lida e enviada sob uma
  trava própria (tokens, camadas, atores, diários, a lista de cenas com o histórico do
  chat, cada recurso da mesa, o lobby), e uma inscrição muda seu estado sob a mesma
  trava. Os envios de uma projeção seguem então a ordem das leituras, e uma atualização
  da inscrição anterior nunca chega depois da nova nem vira base de um delta para ela.
  Projeções diferentes seguem em paralelo.
- A confirmação de um comando pode chegar depois da projeção que seu commit atualizou,
  como já podia acontecer com o comando de outro usuário.
- O agrupamento e a junção (etapa 8) valem para a fila de entregas.

Aceite: um comando é confirmado enquanto uma entrega está bloqueada; uma mudança de
inscrição espera a atualização em andamento da mesma projeção e seu estado é o último
enviado; leituras de presença repetidas rodam uma vez e envelopes consecutivos se
juntam enquanto as entregas esperam.

Medido na mesma reprodução sem troca de cena, com o WAL e esta faixa contra a etapa 8
sozinha: comandos acima de um segundo caíram de 8 para 2 por hora e o comando mais
lento de 1,8 s para 1,1 s, e as entregas deixaram de fazer fila (percentil 95 de 1 ms).
Cada entrega de `room.changes` ficou mais demorada, cerca de 760 ms em média em vez de
540 ms: a thread a mais por socket disputa o lock do interpretador, e o tempo dentro da
thread fora do SQL e da CPU subiu de cerca de 180 para 290 ms. As sessões com troca de
cena separam os dois efeitos: só a faixa elevou a entrega média de 520 para 611 ms, e o
WAL a trouxe de volta para 560 ms. Com troca de cena, as rajadas de
reinscrição ainda esperaram 2–3 s na faixa de comandos: são os frames de inscrição do
próprio cliente. Reduzir o trabalho em Python por projeção é o próximo passo; se isso
não eliminar esse custo, a faixa deve ser revista.

### Etapa 11: trabalho repetido a cada amostra e troca de cena

Um perfil da reprodução da etapa 10 com troca de cena, pela CPU síncrona de cada
operação, mostrou que as projeções não eram o custo principal: o repasse de cursores
usava 65% dela (cada amostra resolvia membro e cena no banco, uma vez para quem envia
e uma para cada destinatário), as amostras de câmera do mestre e os viewports outros
21%, e `room.changes` 8%. Toda troca de cena também reenviava os diretórios de itens e
compêndios de cada cliente, que não dependem da cena (cerca de 340 KB por cliente), e
toda atualização da lista de cenas reenviava o histórico de chat inteiro (cerca de
84 KB), quase sempre inalterado.

- As amostras reaproveitam a resposta a "este membro pode ver esta cena" (cursores
  repassados, a identidade do ponteiro de quem envia, as amostras de câmera do mestre e
  a drenagem de tiles) por no máximo a janela da etapa 6, enquanto a época de acesso
  não muda e até o socket receber o próximo evento do servidor que não seja amostra,
  presença ou leitura do lobby. As mudanças são anunciadas após o commit, então uma
  resposta lida antes de um anúncio nunca é guardada depois dele; uma leitura recusada
  descarta todas as respostas. O viewport do próprio socket sempre lê o banco. Linhas
  alteradas direto no banco, sem evento, chegam às amostras quando a resposta expira,
  como na autorização em cache.
- A mesa inscreve itens e compêndios sem cena, então uma troca de cena reinscreve só
  combate, cartas, áudio, relógios e pistas.
- Uma mudança de inscrição de tokens ou de camadas não recalcula mais áudio e combate,
  cujas entradas ela não altera; as extensões continuam recebendo os mesmos avisos
  `api.changed`.
- O histórico de chat segue como as outras projeções: um histórico inalterado não é
  reenviado, uma mensagem ao vivo (`chat.message`, `chat.ack`) torna o próximo
  completo, e `chat.sync` sempre o recebe. Não foram criados deltas: na reprodução, os
  históricos que mudaram entre atualizações somaram 0,18 MB, enquanto as trocas de
  escopo precisam da lista inteira.
- As mensagens ao vivo saem sob a trava do histórico de chat. Desde a etapa 10, um
  histórico lido numa faixa podia chegar ao navegador depois de uma mensagem enviada
  pela outra, e o navegador então trocava sua lista por uma sem essa mensagem.
- As projeções inteiras guardam só o texto canônico, então a anterior não é
  serializada de novo a cada comparação.
- Um frame enviado entre o handshake de fechamento do Daphne e o evento de desconexão
  é descartado, em vez de derrubar a sua faixa.

Aceite: um repasse de cursor lê cada cena uma vez, um anúncio de cena o interrompe na
hora e uma mudança de acesso no processo faz ler de novo; mudanças de inscrição não
recalculam áudio nem combate; um histórico inalterado não é enviado, e nem uma
mensagem ao vivo nem uma confirmação chegam ao navegador antes de um histórico mais
antigo.

Medido na mesma reprodução com troca de cena, com o WAL e a faixa de entregas, contra a
etapa 10 (uma sessão de 20 minutos cada): a CPU síncrona do servidor caiu de 326 para
114 s e a CPU do processo de 553 para 304 s (mediana de 0,41 para 0,17 núcleo); o
repasse de cursores passou de 212 para 26 s e as amostras de câmera do mestre de 36
para 12 s. Os navegadores receberam 15,6 MB em vez de 26,7 MB: diretórios de compêndios
1,7 MB em vez de 10,3 MB e histórico de chat 3,1 MB em vez de 5,9 MB. Os comandos acima
de um segundo caíram de 197 para 95 por hora e o percentil 95 da espera de 1,9 para
1,1 s; um movimento de token chegou aos outros jogadores em 0,49 s no percentil 95 em
vez de 1,36 s, uma ativação do mestre foi confirmada em 1,4 s em vez de 3,9 s, e os
ponteiros chegaram aos outros em 6 ms em vez de 32 ms na mediana. Salvar a ficha ficou
mais lento no percentil 95 (0,9 s em vez de 0,4 s; rodadas anteriores variaram de 0,4 a
1,6 s).

Cada entrega de `room.changes` ainda leva cerca de 540 ms em média: um envelope chega a
todos os sockets ao mesmo tempo, e cada entrega usa cerca de 74 ms de CPU, então as
threads dos destinatários se revezam no lock do interpretador (263 ms fora do SQL para
74 ms de CPU). O custo por projeção multiplicado pelo número de destinatários é agora a
alavanca que resta; a faixa de entregas fica, porque os comandos não esperam mais atrás
dela.

### Etapa 12: custo das projeções por destinatário

- As camadas leem somente as cartas da cena. As contagens dos baralhos da biblioteca
  usam uma consulta agregada; as camadas deixam de montar primeiro a biblioteca e a
  mão do destinatário.
- O combate resolve tokens, atores e imagens em lotes, preservando a visibilidade
  por destinatário, os atores de fallback e a ordem do encontro.
- A prévia de arraste carrega somente os tokens pedidos. O navegador pula testes
  de interseção com paredes quando o destino do token é sua posição atual.
- Aplicar um delta no navegador faz uma cópia profunda privada em vez de duas. Os
  consumidores continuam recebendo snapshots completos e mutáveis; alterá-los não
  corrompe a próxima atualização. Isso não preserva a identidade dos objetos internos
  entre atualizações.
- O áudio espacial calcula cada ouvinte uma vez, carrega paredes somente para um raio
  audível e pula raios cujo ganho máximo possível não melhora o resultado. Fontes
  desativadas, silenciadas ou fora de alcance não calculam oclusão.
- O áudio envia deltas do estado interno em vez de repetir catálogos inalterados.
  Reprodução, fades e hora do servidor continuam atuais. O navegador reconstrói o
  estado completo antes dos eventos nativos e do SDK; a ressincronização preserva cena
  e prévia atuais. Mudar a inscrição descarta sua base anterior. Os catálogos continuam
  vindo do banco; a redução é no transporte e na serialização canônica repetida.
- Uma autorização vencida é conferida mesmo com presença ainda válida, mas não grava
  nem adia essa presença. As renovações efetivas mantêm a cadência de meio TTL.

Medições locais sintéticas antes/depois, aplicando e testando cada alteração em
sequência na mesma máquina (medianas; tempos não são critérios dos testes):

| Operação e cenário | Antes | Depois |
| --- | ---: | ---: |
| Entrega de mudança de token a um jogador, 10 baralhos | 25,91 ms / 54 SQL | 19,50 ms / 28 SQL |
| Mesma entrega, 20 combatentes, após a mudança das cartas | 42,85 ms / 69 SQL | 25,86 ms / 31 SQL |
| Prévia de um token pelo jogador numa cena com 1.000 tokens | 47,58 ms / 1.000 tokens carregados | 3,33 ms / 1 token carregado |
| Modelo do navegador, 100 tokens imóveis e 1.000 paredes | 100.000 testes de parede | 0 testes de parede |
| Aplicação de delta, 1.000 imagens, 1.000 paredes e 100 tokens | 6,12 ms | 2,88 ms |
| Estado de áudio do jogador, 12 ouvintes, 60 fontes e 500 paredes | 153,32 ms | 9,37 ms |
| Serialização de áudio GM após a mudança espacial, 500 faixas e 40 playlists | 2,44 ms / 198.303 bytes | 1,78 ms / 317 bytes |
| Pong com autorização vencida e presença ainda válida | 7,07 ms / 3 SQL / 1 escrita | 2,19 ms / 2 SQL / 0 escritas |

Os testes de entrega e arraste usaram 25 amostras após aquecimento, presença usou 30,
áudio usou 10 e JavaScript usou nove lotes após aquecimento. As medições de entrega
cobrem o handler de um destinatário no servidor, não a ida e volta de um comando.
As medições JavaScript usam Node e não medem FPS no navegador. Os bytes de áudio são
o tamanho dos frames codificados, sem overhead de rede. Esses cenários não estabelecem
ganhos para uma sessão real inteira.

As regressões verificam crescimento de consultas, cartas e combatentes privados,
fallback de atores, autorização/revisões/paredes no arraste, bases privadas dos deltas,
equivalência do ganho de áudio, fim de faixas e fades, mudanças de papel,
ressincronização e expiração da presença.

### Etapa 13: limite de leituras simultâneas das projeções

`GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY` permite, por padrão, duas leituras
pesadas por vez em cada event loop ASGI, compartilhadas pelos seus sockets. Zero
desativa esse controle. O limite cobre camadas da cena, tokens, áudio e combate.
As travas por projeção continuam ordenando inscrições, leituras e envios; a vaga
compartilhada cobre a leitura, não o envio pelo socket, comandos, renovação de
presença ou amostras.

A autorização é conferida depois de obter a vaga e novamente antes de entregar o
resultado. Uma espera cancelada não inicia a leitura. Se uma leitura síncrona já
começou, conserva sua vaga até terminar mesmo que o destinatário pare de esperar;
falhas abandonadas são observadas. Os limitadores pertencem ao seu event loop e não
retêm loops de teste encerrados. Outros workers têm limites próprios. O agrupamento
das entregas continua funcionando; este não é um limite para todos os eventos na fila.

O protótipo comparou limites de zero, um, dois e quatro com 1, 5 e 10 clientes ASGI
e repetiu a matriz em ordem inversa. Dois preservaram a maior parte do ganho e
permitem outra leitura ao lado de uma demorada. A implementação final foi medida
separadamente com sua configuração em zero e dois, com 20 atualizações após dois
aquecimentos por cenário:

| Clientes conectados | Entrega p95, desativado | Entrega p95, limite 2 | CPU mediana do lote, desativado → limite 2 |
| --- | ---: | ---: | ---: |
| 1 | 58,10 ms | 53,33 ms | 43,45 → 40,88 ms |
| 5 | 369,92 ms | 279,24 ms | 563,21 → 315,05 ms |
| 10 | 1.082,46 ms | 524,78 ms | 2.007,47 → 610,05 ms |

O cenário contém 100 tokens, 102 imagens, 10 baralhos e 20 combatentes, com um mestre
e os demais clientes como jogadores. O tempo de entrega inclui fila, espera pela
vaga, cálculo das projeções e emissão pelo transporte ASGI em memória; exclui rede
real e renderização no navegador. Um `chat.sync` e uma renovação de presença
concorrentes, com 10 clientes, tiveram p95 de 86,24 → 32,44 ms e 58,16 → 17,48 ms,
respectivamente. O benefício principal aparece sob concorrência; a diferença com
um único cliente é pequena.

Repetir a comparação da implementação final em ordem inversa confirmou o ganho:
com 10 clientes, o p95 de entrega foi 1.248,92 ms sem limite e 508,53 ms com duas
vagas. Com um cliente, a mediana de entrega ficou essencialmente igual
(35,98 contra 36,46 ms).

## Fora desta direção

- Substituir o SQLite. O WAL deixa os leitores seguirem durante um commit, mas não
  elimina a serialização entre escritores (veja a medição acima e a etapa 9).
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
