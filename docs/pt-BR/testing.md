# Testes

[Documentação](../README.pt-BR.md) · [English](../en/testing.md)

Execute na raiz após `uv sync --locked`. O projeto usa Django/unittest para Python, o executor nativo do Node para JavaScript e scripts Playwright independentes para navegador. Não há `npm test` na raiz nem executor pytest configurado.

### Limitações conhecidas no Windows

- O Windows limita caminhos a 260 caracteres. Os cenários do Map Builder instalam
  um módulo de fixture dentro da pasta de saída; um `--output` longo, como um
  aninhado na pasta temporária do usuário, faz essa instalação falhar com "Invalid
  module archive". Use a saída padrão em `data/` ou outro caminho curto.
- `tests/e2e/escape_windows.py` não inicia servidor próprio. Ele precisa de
  `ownership_server.py` em `127.0.0.1:30002` e de `data/permissions-review-seed.json`
  dessa fixture.

## Ambiente local controlado

Os testes carregam `.env` quando uma variável do processo não a substitui. Para testes HTTP locais, use um shell com estes valores em vez de herdar origem HTTPS de produção ou Redis externo:

```bash
export DJANGO_DEBUG=true
export DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost,[::1],testserver'
export GRAVEWRIGHT_PUBLIC_ORIGIN=''
export DJANGO_SECURE_COOKIES=false
export GRAVEWRIGHT_REDIS_URL=''
export TRUSTED_PROXIES=''
export GRAVEWRIGHT_MARKETPLACE_URL=''
export GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=''
export GRAVEWRIGHT_RELEASES_REPOSITORY=''
```

Isso altera apenas o shell, não o `.env`. Fixtures de navegador normalmente substituem banco e arquivos por diretórios temporários. Cada cenário pode sobrescrever configurações específicas.

## Python

```bash
uv run --locked python manage.py check
uv run --locked python manage.py makemigrations --check --dry-run
uv run --locked python manage.py test config gravewright --noinput
```

O executor usa explicitamente `data/test-gravewright.sqlite3`, em arquivo, para testar locks do SQLite. `--noinput` autoriza substituir esse banco de testes caso já exista. Não aponte para dados importantes nem execute suítes simultâneas no mesmo caminho. Alterar `GRAVEWRIGHT_DATABASE` não altera o nome explícito desse banco de testes. Testes que escrevem arquivos geralmente criam armazenamento temporário; use `GRAVEWRIGHT_MEDIA_ROOT` descartável como proteção adicional ao executar a suíte inteira.

Exemplos focados:

```bash
uv run --locked python manage.py test config gravewright.accounts gravewright.realtime --noinput
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.modules --noinput
uv run --locked python manage.py test gravewright.dice --noinput
```

As verificações de release para apps Django e atualizações gerenciadas incluem:

```bash
uv run --locked python tests/e2e/django_marketplace.py
uv run --locked python tests/e2e/automatic_updates.py --runner
```

Esses cenários usam dados isolados e verificam dependências, rotas Django,
recuperação de falhas de migração, preservação nas atualizações e rollback `.old`.

## JavaScript

Use Node.js atual com módulos ES nativos e `node:test`; estes comandos foram verificados com Node 24. Não é necessário instalar pacotes na raiz para esses testes.

```bash
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

Para incluir todos os testes JavaScript junto ao código, este lançador Python evita globs recursivos específicos do shell:

```bash
uv run --locked python - <<'PY'
from pathlib import Path
import subprocess
files = sorted(str(p) for base in ('gravewright', 'tests')
               for p in Path(base).rglob('*')
               if p.name.endswith(('.test.js', '.test.mjs')))
subprocess.run(['node', '--test', *files], check=True)
PY
```

A cobertura inclui ciclos de vida e contratos de módulos, parsing de shaders, entradas do tabuleiro, agendamento de tiles, visibilidade, paredes, seleção, rotas de tokens e mapeamento PDF. Testes de geometria/modelos não substituem a conferência da renderização real na GPU.

Os testes de módulos cobrem uploads multipart de imagens de cartas na
inicialização, duração de ativação, permissões nativas e operações canceladas.
A suíte Django `gravewright.modules.test_card_assets` também verifica validação
de imagens, reutilização de recursos, isolamento de mesas e limpeza após falha.

## Cenários no navegador

`uv run --locked python tests/e2e/door_rotation_anchor.py` verifica a escolha do
pivô da porta, rotação, desfazer, imagem ao abrir/fechar, editor compartilhado de
paredes e configurações salvas em inglês, português e espanhol, em larguras de
desktop e celular. Usa uma campanha isolada e aceita `--output` e
`--browser-executable`.

```bash
uv run --locked playwright install chromium
uv run --locked python tests/e2e/authentication.py
uv run --locked python tests/e2e/realtime.py
uv run --locked python tests/e2e/frontend_api.py
uv run --locked python tests/e2e/https.py
uv run --locked python tests/e2e/runner.py
uv run --locked python tests/web/window_i18n_browser.py
uv run --locked python tests/web/form_controls_browser.py
```

O teste independente de janelas serve apenas arquivos estáticos do host e
confere os controles em inglês, português e espanhol, incluindo liberação dos
listeners e preservação dos textos do usuário. Não carrega campanha ou banco.

O teste independente de controles de formulário verifica o tema compartilhado,
seleção de arquivos pelo teclado, caixas de seleção, sliders, validação, campos
desabilitados/somente leitura e layouts de 320px. Também confere se campos mapeados
sobre PDFs mantêm suas dimensões autoradas em janelas da mesa. Serve arquivos
estáticos com controles sintéticos e grava capturas em `test-results/form-controls/`,
sem banco de dados.

`uv run --locked python tests/e2e/board_scene_refresh.py` verifica atualizações
da mesma cena com WebGL real, imagens sintéticas e respostas de tiles atrasadas.
Confere continuidade da câmera e das imagens, novas tentativas de substituição,
requisições superadas, mudanças da grade e trocas de cena sem carregar dados de
campanhas. Os diagnósticos usam um diretório exclusivo em `data/runner/`;
`--workdir`, `--browser-executable` e `--node` selecionam uma saída isolada e
ambientes de execução existentes.

`uv run --locked python tests/e2e/scene_layer_continuity.py` confere superfícies
de piso e grupos de pintura/apagadores durante entrada/saída de regiões, luzes,
escuridão, trocas de material atrasadas, remoção e mudanças de cena/papel.
Amostra pixels reais da GPU entre quadros e serve apenas imagens sintéticas,
com as mesmas opções de saída local e ambientes do cenário de atualização do tabuleiro.

`uv run --locked python tests/e2e/token_teleport_presentation.py` verifica que o
teleporte destrói e recria somente o objeto visual do token no destino, enquanto
movimentos normais continuam interpolados. Os casos WebGL sintéticos cobrem
atualizações duplicadas, identidade da seleção e da ficha, imagens atrasadas ou
superadas, descarte e preservação dos recursos da câmera/piso. Usa as mesmas
opções de saída local e ambientes dos demais cenários de renderização independentes.

`uv run --locked python tests/e2e/token_saving.py` abre o tabuleiro nativo com
atores sintéticos em uma campanha descartável e controla as respostas de tokens
para verificar confirmações silenciosas rápidas/lentas, movimentos sem deslocamento,
desfazer, movimentos em grupo, conflitos, estados mais recentes, teleporte e
descarte. Registra leituras de tokens, atualizações de camadas e mutações do DOM
do aviso; movimentos confirmados devem usar sua resposta e falhas devem
ressincronizar. `--output` e `--browser-executable` selecionam resultados isolados
e um navegador existente. `--baseline-dir` pode servir assets de tokens salvos
anteriormente para comparação sem alterar os arquivos da aplicação.

`uv run --locked python tests/e2e/mapbuilder_ingame_performance.py` gera uma cena
representativa do MapBuilder e executa movimentos reais pelo transporte nativo
WebSocket com dois clientes de navegador. Mede confirmação e apresentação do
estado autorizado, vazão de movimentos sequenciais, intervalos entre quadros,
atividade de recursos GPU e tráfego, incluindo trocas de sprite por região e
teleporte. Capturas de tela ficam fora dos intervalos medidos. Usa dados de
campanha descartáveis e aceita `--output` e `--browser-executable`. As opções
`--baseline-dir` e `--backend-source` carregam assets públicos e código do servidor
salvos apenas na fixture isolada para comparação antes/depois. A suíte Django
`gravewright.realtime.tests.test_token_refresh_cost` verifica o custo das
notificações, estabilidade da projeção de atores, áudio independente e revogação
de acesso durante a entrega.

No Linux, o Playwright pode precisar de bibliotecas do sistema; `uv run --locked playwright install --with-deps chromium` também as instala e pode exigir privilégios administrativos. Os cenários iniciam servidores próprios em portas temporárias e criam dados fictícios. A maioria usa configurações de desenvolvimento e grava diagnósticos em `test-results/`; os cenários HTTPS e do executor usam configurações específicas descritas abaixo. Execute em sequência: vários compartilham `test-results/migration-closure/`.

`tests/e2e/compendium_server.py --fixture <diretório-novo-vazio>` inicia uma
fixture descartável em localhost com sistema de navegador, catálogos de idiomas
e compêndios sintéticos. Repita `--archive <sistema.zip>` para revisar sistemas
locais reais; nenhum dado do operador é reutilizado. Execute
`tests/e2e/compendium_layout.py --seed <fixture>/seed.json
[--browser-executable <chromium>]` para verificar layouts desktop, 390px e 320px,
ordenação em en/pt-BR/es, busca sem distinção de acentos, filtros de tipo/pacote,
prévias e foco nativo por teclado, importações independentes, recuperação de
falhas de importação, permissões, acesso somente para leitura e criação do
primeiro pacote. Os resultados ficam em `test-results/compendiums/` por padrão.
Em outra fixture nova, `tests/e2e/item_directory_layout.py --seed
<fixture>/seed.json --output <diretório-de-resultados>
[--browser-executable <chromium>]` verifica a densidade do diretório nativo de
itens, ordenação de itens/pastas/tipos, busca, menus pelo teclado, duplicação,
movimentação e controles de leitura. Encerre cada servidor pertencente ao teste
depois da execução.

`tests/e2e/actor_form_layout.py --seed <fixture>/seed.json --output <diretório-de-resultados>`
usa a mesma fixture descartável para verificar os modais de personagens/pastas
em desktop, 390px e 320px, contenção e restauração de foco, Escape/cancelar,
salvamentos pendentes e falha/nova tentativa com persistência real. Também aceita
`--browser-executable`.

| Alteração | Cenários pertinentes |
| --- | --- |
| Contas e campanhas | `authentication.py`, `inside.py`, `campaign_controls.py` |
| Alertas de atualização do VTT | `update_notification.py`; testes Django em `gravewright.administration.test_update_notifications` |
| Progresso de atualização e reconexão após reinício | `update_progress.py` (atualizações simuladas e isoladas; não substitui arquivos da aplicação) |
| Nome completo e notas da versão instalada | `release_presentation.py`; testes Django em `gravewright.administration.test_release_presentation` |
| Tempo real e permissões | `realtime.py`, `lighting_realtime.py`, `map_prefetch.py` |
| HTTPS, WSS e confiança em proxies | `https.py`; testes Django em `config` e `gravewright.realtime` |
| Executor Windows local | `runner.py`; testes Django em `config.test_runner` e `config.test_frontend_preparation`; workflow do executor CMD Windows |
| Tabuleiro, tokens e fichas PDF | `maps.py`, `tokens_pdf.py`, `token_routes.py`, `mixed_selection.py` |
| Map Builder | `map_builder.py`, `map_builder_studio.py`, `map_builder_expansion.py`; Django `gravewright.maps.tests.test_builder_projects`, `test_builder_expansion`, `test_builder_update`, `test_builder_render_expansion`, `test_builder_door_art` e `gravewright.administration.test_builder_archives` |
| Efeitos e renderização | `effects.py`, `effect_editor.py`, `effect_pixels.py`, `light_rendering.py` |
| Diários e dados | `journals.py`, `journal_types.py`, `dice.py`, `dice_validation.py` |
| SDK e módulos de mesa | `frontend_api.py`, `table_modules.py`, `management.py`, `marketplace.py`, `modal_flush.py` |
| Áudio e chat | `audio_lifecycle.py`, `chat_controls.py` |

O cenário de expansão do Map Builder cria sua campanha sintética, banco e mídia
num diretório de saída novo dentro da instalação e encerra seu servidor ao sair:

```sh
uv run --locked python tests/e2e/map_builder_expansion.py
```

As opções `--output <diretorio-novo-vazio>` e `--browser-executable <chromium>`
escolhem os diagnósticos e um navegador existente. Ele verifica camadas e
metadados da biblioteca salvos, pincéis/encaixe, transformações de grupos,
decorações/luzes nativas, atualização segura de cenas com conteúdo manual,
conflitos de revisão e layouts localizados e responsivos do Estúdio. `--large-only`
mede seleção e movimento de grupo com 1.000 objetos sintéticos de chão, registrando
os tempos observados sem um limite de duração. Os testes
do modelo geométrico executam diretamente com
`node --test gravewright/maps/static/gravewright_maps/builder/model.test.mjs`.

`uv run --locked python tests/e2e/map_builder_wall_art.py` verifica a arte de
paredes com uma faixa transparente sintética. Compara pixels do navegador e da
imagem gerada, encaixe nas bordas da grade, movimento e desfazer, diagonais livres,
recortes de portas e coordenadas fracionárias salvas. Aceita as mesmas opções de
saída/navegador acima; Django `gravewright.maps.tests.test_builder_wall_art` cobre
os casos especiais da rasterização.

`uv run --locked python tests/e2e/map_builder_collections.py` verifica importação,
edição, cancelamento, remoção e filtros de coleções do projeto, inclusive famílias
com membros em coleções diferentes. Também arrasta um grupo de parede/objeto junto
a uma borda fracionária e verifica os layouts em inglês, português e espanhol a
320/390 px. Os cenários do Estúdio e da expansão usam a modal atual de importação,
tiles de chão de uma célula e painéis auxiliares visíveis, inclusive **Projetos → Novo projeto**.

`uv run --locked python tests/e2e/map_builder_asset_removal.py` verifica o botão
de remover assets da campanha, confirmação/cancelamento, falhas e respostas
perdidas, preservação de edições não salvas e desfazer, conflitos de revisão,
limpeza de cenas/projetos dependentes e modais desktop/móveis localizadas. Usa
as mesmas opções isoladas de saída e navegador.

`uv run --locked python tests/e2e/map_builder_scene_directory.py` verifica o ícone
vermelho da cena e a edição pelo MapBuilder no menu de contexto, navegação normal
de cenas, preservação da transmissão, acesso pelo teclado e layouts localizados
em painéis estreitos. Usa as mesmas opções isoladas de saída e navegador.
`gravewright.maps.tests.test_builder_scene_directory` cobre isolamento de
campanha e papel, vínculo atual do projeto e consultas limitadas no diretório.

`uv run --locked python tests/e2e/map_builder_player_broadcast.py` mantém um jogador
conectado enquanto o mestre gera uma cena privada no MapBuilder e usa
**Ativar para jogadores** no diretório, sem editar a visibilidade separadamente.
Verifica a entrega ao vivo e após recarregar por pixels do chão e das imagens,
tiles e assets públicos, e pela exclusão de imagens do mestre, blueprints e
projetos de origem. Usa as mesmas opções isoladas de saída e navegador.
`gravewright.maps.tests.test_builder_player_activation` cobre revisões de ativação,
repetições, rollback, leitura por streamer e limites de autorização.

`uv run --locked python tests/e2e/map_builder_native_effects.py` verifica as
predefinições nativas de luzes, partículas e shaders no builder, edição de
propriedades, pixels de prévia animados, salvamento/reabertura, catálogos
desktop/móveis localizados, cena nativa para mestre/jogador, propriedade dos
objetos e estados ativos na atualização e descarte do renderizador. A cobertura
do servidor fica em `gravewright.maps.tests.test_builder_effects`; as opções de
navegador e o isolamento são os mesmos dos outros cenários do builder.

`uv run --locked python tests/e2e/pixi_board_lifetime.py` compila as fontes locais
do renderizador e verifica pixels reais da GPU ao liberar e readquirir a imagem
de um token imediatamente e ao fechar outro tabuleiro. Confere máscaras
circulares, redimensionamento e descarte independente sem Django ou dados de
campanha. Use `--workdir <diretorio-de-saida>`, `--node <executavel-node>` e
`--browser-executable <chromium>` para escolher ferramentas locais e diagnósticos;
as dependências de compilação do frontend precisam estar instaladas. Os testes
unitários de referências de imagens também exercitam essa corrida pelo loader
real do Pixi.

`uv run --locked python tests/e2e/map_builder_render_lifetime.py` exercita
teletransportes recíprocos por áreas de presença com imagem de token compartilhada,
visão dinâmica, luzes com máscaras, partículas e shaders nas telas de mestre e
jogador. Confere exceções do navegador e a continuidade da animação na GPU após
teletransportes repetidos, ocultação/exibição, teste nativo de comportamento e
redimensionamento. Usa a fixture isolada do builder e as mesmas opções
`--output`/`--browser-executable`.

`uv run --locked python tests/e2e/map_builder_torches.py` exercita uma tocha
composta da configuração no builder à interação real na mesa. Verifica janelas
de componentes nativos, chama/mecanismo independentes, transformações, cópias,
camadas e exclusão/desfazer do conjunto, ações de porta/chama no Blueprint,
layouts estreitos traduzidos, teclado/ponteiro do jogador, transformações
nativas da imagem e recusa de streamer. Usa arte sintética e os isolamentos de
campanha, banco, mídia, porta e saída do cenário compartilhado. A cobertura de
domínio fica em `gravewright.maps.tests.test_torches`; testes puros dos modelos
do builder e das imagens nativas verificam vínculos, transformações afins,
referências ausentes e IDs de cópia.

`uv run --locked python tests/e2e/map_builder_interactions.py` cria pedidos de
dados, abertura de diários e mudanças de status de missões pelo editor real de
nós, depois os executa como jogadores em uma campanha descartável. Verifica
entrega para um ou todos os jogadores, resultados de dados pelo servidor,
simulações e layouts traduzidos no desktop e celular. Use `--output` e
`--browser-executable` para diagnósticos isolados e um navegador existente. A
cobertura de domínio fica em `gravewright.maps.tests.test_blueprint_interactions`.

`uv run --locked python tests/e2e/map_builder_ingame_sync.py` edita objetos gerados
pelo jogo, reabre o Builder vinculado e atualiza a mesma cena. Verifica geometria,
imagens e luzes importadas, exclusão, rascunhos locais independentes, conflitos,
Desfazer, conteúdo manual e estado de jogo preservado, incluindo uma tela móvel
em português. Usa a fixture descartável do Builder e aceita `--output` e
`--browser-executable`. A cobertura Django fica em
`gravewright.maps.tests.test_builder_sync`; mesclagem e histórico usam
`node --test gravewright/maps/static/gravewright_maps/builder/scene-sync-model.test.mjs`.

`uv run --locked python tests/e2e/map_builder_object_menu.py` verifica menus dos
objetos por mouse/teclado, modais de propriedades, seleção de porta no mapa por
região e os 14 modelos configuráveis em uma campanha isolada do Builder.
Confere cancelamento, substituição, omissão de recursos desmarcados, Desfazer/
Refazer, simulação e geração salva; depois mede pixels das imagens ativa/inativa
na mesa e a reprodução real de som. Os layouts cobrem inglês, português e
espanhol no desktop, em 390px e 320px, incluindo a ação Opções do objeto para
toque. Use `--output` e `--browser-executable` para resultados isolados e um
navegador existente.

`uv run --locked python tests/web/automation_roll_browser.py` verifica a modal
nativa de dados e o transporte em tempo real com respostas sintéticas do socket:
envio explícito, identidade e cena estáveis nas tentativas, estados de espera,
erro e sucesso, foco por teclado, tradução, conteúdo longo e descarte.
`tests/web/interactive_object_catalog_browser.py` verifica a configuração dos
modelos, escolha de diário/jogador, som e imagem opcionais, confirmação de
substituição, catálogos vazios e layouts em inglês/português/espanhol até 320px.
Ambos servem arquivos estáticos
do host com dados sintéticos e aceitam as mesmas opções de saída/navegador,
sem acessar dados de campanha.

`uv run --locked python tests/e2e/map_builder_composite_conditions.py` constrói
All/Any pelo editor real de Blueprint, verifica simulação sem escrita, conexões
tipadas salvas e layouts desktop/celular traduzidos; depois testa uma passagem
com três tochas como jogador e muda a regra para Any por atualização vinculada.
Usa arte sintética e a fixture isolada do builder. Testes do servidor ficam em
`gravewright.maps.tests.test_blueprint_logic`; o modelo puro verifica tabelas de
verdade, composição, avaliação completa, referências ausentes e limites de
versão/tipo/ciclo.

`uv run --locked python tests/e2e/map_builder_variables_signals.py` configura
variáveis tipadas de elemento/cena e grafos receptores nomeados pelo editor real.
Verifica simulação privada, mudança de tipo e desfazer, sinais por alvo e por
cena a partir de interações reais do jogador, recibos, reconexão, atualizações
vinculadas, projeções privadas e a visão de variáveis/redefinição do mestre.
Layouts em inglês, português e espanhol usam arte sintética e os mesmos
isolamentos de campanha, banco, mídia, porta e navegador. A cobertura de domínio
fica em `gravewright.maps.tests.test_blueprint_variables`; o modelo puro verifica
valores falsos/zero/vazio, retrato inicial, portas tipadas, memória inválida,
limites de sinais e compatibilidade de versão. Testes de arquivo de campanha e
duplicação nativa cobrem preservação de progresso e memória própria das cópias.

`uv run --locked python tests/e2e/map_builder_choices.py` configura Escolher
caminho e Aleatório com pesos pelo editor real, com conexões de Valor tipadas,
controles de casos/caminhos, correção de valores duplicados, Desfazer/Refazer,
Cancelar e simulação local. Verifica layouts desktop/celular traduzidos sem
interseção dos cartões de escolha e ações do jogador, caminhos escolhidos pelo servidor,
recibos, privacidade, atualizações vinculadas e interações agendadas na cena
isolada. Testes de domínio em `gravewright.maps.tests.test_blueprint_choices`
cobrem casos tipados e pesos estritos, saídas Padrão/desconectadas, um sorteio na
convergência, sorteios privados estáveis nas repetições inclusive após reversão,
permissões, trilhas do mestre, continuações de Delay, leituras atuais do
Temporizador, posições antigas/privadas dos sorteios, eventos de presença em
lote/trajeto, exclusão de personagens e pastas recursivas e valores autorados
na reescrita de arquivos. Testes puros em `builder/blueprint-choices.test.mjs`
cobrem portas dinâmicas estáveis, valores falso/zero/vazio/Unicode, retratos
imutáveis, definições e sorteios inválidos, limites dos intervalos de pesos,
escolhas não alcançadas/convergentes, ordem com Delay e composição com controles.

`uv run --locked python tests/e2e/map_builder_capabilities.py` exercita grupos,
referências tipadas, transformações, ações de interação/região e Contexto do
evento pelo editor real, com assets sintéticos e campanha, banco, mídia, porta
e navegador isolados. Verifica autoria, simulação temporária, layouts traduzidos,
fonte salva e efeitos/permissões nativos durante o jogo.
`gravewright.maps.tests.test_blueprint_capabilities` cobre grupos ordenados
tipados, referências de luz/som, alvos ausentes/incompatíveis, transformações
nativas e componentes de tocha, configuração de interação, identidade original
por sinais e trabalho temporizado, reversão/recibos, atualização de cenas e
remapeamento em arquivos/cópias. `gravewright.maps.tests.test_region_filters`
cobre predicados E/OU, mudanças de ocultação/disposição, propriedade de IDs,
bases silenciosas de configuração, ativação de regiões durante o jogo,
supressão de presença por comando, sincronização das entradas atuais e filtros
preservados/remapeados em atualizações e arquivos.
`builder/blueprint-capabilities.test.mjs` verifica conexões de conjuntos tipados,
limites de grupos/ações, padrões/tipos de contexto, simulação sob demanda, cópias,
referências ausentes preservadas e conexão somente de execução após exclusão.
Testes de região usam o mesmo helper de filtros nativo e verificam correspondência,
normalização e omissões legadas; testes de interação de alavanca verificam
controles desabilitados, teclado desatualizado, oclusão e operação pelo mestre.
Execute também os cenários reais de cena/navegador para conferir visualmente
geometria, permissões e ocupação filtrada.

Os cenários de modelos reutilizáveis, rede e mundo dinâmico são
`tests/e2e/map_builder_templates.py`, `map_builder_network.py` e
`map_builder_world.py`. Usam as mesmas opções de isolamento/execução do navegador
e dados sintéticos. Modelos verificam vínculos tipados, limites de parâmetros,
cópias independentes e Aplicar/Desfazer/Refazer/Cancelar pelo editor real. A rede
verifica edição do proprietário existente e relações filtradas; o mundo cobre
arte promovida, mudanças de material/visibilidade, públicos de apresentação,
preferências de câmera e transporte de token na mesma cena. Execute-os como
cenários de navegador: simulação pura não verifica entrega nem renderização nativa.

As suítes de servidor focadas são `gravewright.maps.tests.test_blueprint_templates`,
`test_blueprint_network`, `test_builder_dynamic`, `test_blueprint_world`, `test_surface_archives` e
`gravewright.realtime.tests.test_automation_presentations`. Cobrem propriedade
de recursos, recibos vinculados ao conteúdo, conflitos de revisão, salvamento
atômico da fonte/cena, reversão, remapeamento em arquivos, propriedade de máscaras,
orçamentos agregados de superfícies, travas de chegada persistentes e destinatários
autorizados. A cobertura JavaScript pura fica junto
dos modelos em `blueprint-templates.test.mjs`, `network-model.test.mjs`,
`blueprint-presentation.test.mjs`, `dynamic-surfaces.test.mjs` e junto dos helpers
nativos de imagem. Reconstrua o tabuleiro ao alterar esses helpers.

O ensaio pelo motor real e os controles do jogo possuem cobertura de servidor em
`gravewright.maps.tests.test_blueprint_testing` e
`gravewright.maps.tests.test_scene_controls`. Execute essas suítes com banco e
mídia descartáveis, conforme a configuração acima. O ensaio verifica vínculos
da fonte não salva, contexto autenticado de token, superfícies apenas com
metadados, evento exato escolhido, sinais, avisos de tempo, repetição
determinística e reversão completa de dados, recibos, arquivos e entregas após
commit. Os controles verificam isolamento de mestre/jogador/streamer, revisões,
recibos vinculados ao conteúdo, distinção entre estado e interação, componentes
da tocha, ocupação silenciosa de regiões, restauração de material e preservação
do projeto autoral durante atualização vinculada.

`uv run --locked python tests/e2e/map_builder_playtest.py` exercita as APIs
públicas e os controles reais de ensaio do Builder e da cena com dados
sintéticos. Compara snapshots da campanha/banco/mídia e observa um jogador
conectado para detectar entrega acidental de apresentação. Os testes JavaScript
ficam em `builder/playtest-model.test.mjs`, `builder/run-format.test.mjs` (resumos
de passos e mudanças compartilhados com o registro de automação) e
`scene-controls.test.mjs`. O ensaio
no servidor não avança o agendador: confira vencimentos reais de Delay e
Temporizador nos cenários separados abaixo.

`uv run --locked python tests/e2e/map_builder_universal_vtt.py` exercita a escolha
de importação nativa, avisos, repetição após perda de confirmação, cancelamento
da exportação, download e reimportação de geometria/luzes. Confere permissões de
mestre/jogador/streamer e os layouts de importação/exportação em inglês,
português e espanhol a 1440px e 390px, com imagem gerada e campanha descartável.

`uv run --locked python tests/e2e/map_builder_region_filters.py` verifica falha
e repetição do catálogo de atores, ausência legada ao abrir e limpar filtros,
salvar/Desfazer/Refazer, IDs ausentes de token inertes e Cancelar/Salvar nativos.
As formas isoladas do Builder e editor nativo usam nomes longos autorados em
inglês, português e espanhol a 1440px e 390px, conferindo acesso aos controles,
tamanho de texto, overflow e configuração sem eventos artificiais de automação.

`uv run --locked python tests/e2e/map_builder_persistent_gates.py` configura
Contador, Uma vez e Recarga pelo editor real de Blueprint, verifica a memória
temporária da simulação e os layouts desktop/celular traduzidos; depois exercita
interações do jogador, recibos, reconexão, atualizações vinculadas, projeções
privadas e a redefinição de memória dos nós pelo mestre. Usa arte sintética e a
fixture compartilhada com campanha/banco/mídia/navegador isolados. A cobertura de
domínio em `gravewright.maps.tests.test_blueprint_controls` verifica progresso
persistente, reversão atômica, reconciliação, cópias/arquivos e Recarga pelo
relógio do servidor. A cobertura pura em `builder/blueprint-controls.test.mjs`
verifica ramos por meta, saturação, primeiro uso, prazo exato de Recarga,
tentativas bloqueadas, isolamento por evento, convergência, entradas imutáveis
e limites estritos de memória/tempo. Esses cenários validam Recarga por eventos.
A espera persistente tem um cenário separado abaixo.

`uv run --locked python tests/e2e/map_builder_delay.py` configura Delay pelo
editor real de Blueprint e verifica simulação que suspende sem agendar,
conexões tipadas salvas e layouts desktop/celular em inglês, português e
espanhol. Em uma cena real, verifica ações adiadas de porta, a visão Aguardando
do mestre e cancelamento, pausa/retomada, navegadores desconectados e recuperação
após reiniciar o servidor ASGI. A fixture compartilhada isola campanha, banco,
mídia, portas e saída, sem tocar na fila do operador. Testes puros em
`builder/blueprint-delay.test.mjs` cobrem suspensão do evento inteiro, ordem de
Sequência/ramificação, convergência, entradas lidas sob demanda, memória dos
controles, eventos nomeados, imutabilidade, limites de duração e compatibilidade
de versão.
`gravewright.maps.tests.test_blueprint_delays` cobre continuações privadas,
retomada ordenada, valores originais do evento e memória atual dos controles,
recibos, reversão por trecho, permissões do autor/cena, cancelamento por edição
de comportamento, projeções privadas, limites de fila/arquivo/cópia, esperas em
série, executores SQLite concorrentes e limites da cadeia entre esperas.
`gravewright.maps.tests.test_delay_worker` verifica início
automático pelo host, processamento sem navegador, encerramento seguro, executor
desativado, diagnóstico de erros, liberação das conexões e suspensão durante a
manutenção do atualizador gerenciado.

`uv run --locked python tests/e2e/map_builder_timer.py` configura ações nomeadas
Iniciar/Parar/Reiniciar Temporizador e seus receptores de sinal pelo editor real,
verifica execução imediata de Próximo e simulação sem contagem regressiva e
inspeciona layouts desktop/celular em inglês, português e espanhol. Sua cena
real isolada exercita ações do jogador e recibos, projeções privadas,
parar/reiniciar e controles desatualizados do mestre, preservação em atualizações
vinculadas, leitura atual de variáveis ao vencer, pausa/retomada, navegadores
fechados e recuperação após reiniciar o ASGI. Não reutiliza dados nem a fila do
operador. Testes de domínio em
`gravewright.maps.tests.test_blueprint_timers` cobrem validação tipada,
preservação de identidade/prazo/autor, ordem de iniciar/parar/reiniciar, autoridade
do reinício pelo mestre, recibos, reversão, capacidade compartilhada com Delay,
limites herdados de tempo/elemento, cancelamento, arquivos/cópias e executores
concorrentes. Os testes puros em `builder/blueprint-timer.test.mjs` cobrem
validação estrita de ação/duração/nome/versão, continuação imediata, receptores
separados de vencimento, ordem com Delay, nós não alcançados/convergentes e
dados autorados/de prévia imutáveis.

`uv run --locked python tests/e2e/map_builder_library_controls.py` verifica a
posição estável da barra entre materiais, luzes e catálogos de partículas/shaders,
filtros com nomes longos, busca e recolhimento, com galeria vazia e mídia
sintética. Confere alinhamento compacto dos checkboxes e ativação por clique ou
Espaço em configurações, camadas e propriedades de luz, tocha e região, em inglês,
português e espanhol, no desktop e celular. Usa a fixture isolada do builder.

`uv run --locked python tests/e2e/map_builder_regions.py` exercita retângulos
nomeados, a placa ligada à porta e o editor real de Blueprint, layouts estreitos
traduzidos, dois tokens de jogador, primeira chegada/última saída, ocupação
nativa privada, atualização/reabertura da cena e editor nativo de região do
mestre. Usa os mesmos isolamentos de campanha, banco, mídia, porta e navegador.
Testes de domínio ficam em `gravewright.maps.tests.test_regions`; os modelos de
região do builder e da mesa cobrem geometria, referências tipadas e cópias/camadas.

`uv run --locked python tests/e2e/map_builder_native_editors.py` exercita as
mesmas janelas de luzes, partículas, shaders e paredes/portas usadas no jogo.
Verifica rascunhos privados, cancelar/Escape, uma etapa de desfazer por
salvamento, GLSL completo, biblioteca de presets e assistente de prompt interno,
canais/elevação de barreiras, arraste de janelas, foco e presets pelo teclado,
salvar/reabrir e geração/atualização nativa. Também abre essas janelas na mesa
real do jogo para conferir seu host normal. Cenas
ativas permanecem intactas até uma ação explícita de gerar/atualizar. Layouts
desktop em inglês/português e 390px em português/espanhol conferem foco, controles
traduzidos e ações de salvar acessíveis. Usa as mesmas opções isoladas de
campanha, saída e navegador.

`uv run --locked python tests/e2e/map_builder_native_effects_occlusion.py`
compara pixels reais da prévia em paredes sólidas e portas fechadas/abertas.
Também verifica diagnósticos de GLSL inválido e preset ausente, recuperação,
shaders personalizados que ignoram o uniforme de intensidade e descarte do
renderizador enquanto o documento está oculto.

`uv run --locked python tests/e2e/map_builder_refinements.py` verifica a área e o
cursor do pincel redondo, atalhos de tamanho, borracha por área, célula inicial do
preenchimento, captura de material e cancelamento de polígonos pelo teclado.
Exercita seleção, transferência, isolamento, criação durante o isolamento,
bloqueios e mesclagens seguras de camadas, incluindo desfazer, reabrir e atualizar
cenas nativas preservando identidades e ativação das luzes durante o jogo.
Layouts em inglês, português e espanhol cobrem desktop e celular, inclusive
ações das camadas após rolagem e recorte do estado da camada ativa.
As operações puras de geometria e camadas têm cobertura nas suítes `node:test`
junto ao código do builder.

`uv run --locked python tests/e2e/map_builder_custom_layers.py` verifica a camada
inicial única, vazia e renomeável, a remoção da última camada vazia, criação
explícita, mistura de tipos de objeto, conteúdo expansível e restrições de
seleção. Exercita duplicação com deslocamento de uma célula, novas identidades e
referências remapeadas de Objetos Inteligentes, reordenação por arraste real,
desfazer, filtro visível de coleção, salvar/reabrir e gerar. Os layouts cobrem
inglês, português e espanhol, inclusive telas móveis estreitas. No servidor,
`gravewright.maps.tests.test_builder_layers` verifica salvar/reabrir sem camadas,
geração apenas com fundo, atualização que preserva objetos manuais da cena,
rejeição de objetos órfãos nos sete tipos e compatibilidade com projetos existentes.

`uv run --locked python tests/e2e/map_builder_clean_layout.py` verifica o canvas
ampliado, controles de desenho na aba Ferramentas do painel existente e a
identidade única dos controles. Exercita o nome do mapa no cabeçalho, aplicação
com Enter/saída do campo, cancelamento com Escape, desfazer/refazer e salvamento
do nome que está digitado. Também verifica as categorias da biblioteca ativando
ferramentas e layouts localizados de desktop/celular, preservando os dados do
projeto e dos objetos nativos.

`uv run --locked python tests/e2e/map_builder_header_tools.py` verifica os atalhos
Selecionar/Pintar/Apagar do cabeçalho, seleção com Shift e por caixa, movimento
de grupo e desfazer. Confere Pintar restaurando o pincel de chão sem trocar o
material, áreas reais do pincel, tamanho sincronizado com Ferramentas e atalhos
de colchetes, geometria fracionária sem encaixe e exclusão de objetos inteiros.
Interceptar o salvamento e ativar a Prévia verificam a desativação dos controles
de edição. Layouts em inglês, português e espanhol exercitam os controles em
larguras de desktop e celular.

`uv run --locked python tests/e2e/map_builder_tiles_only.py` mantém a regressão
de Tiles apesar do nome histórico do arquivo. Confere projetos Tiles padrão
intactos, preserva geometria, cor/opacidade e objetos nativos de projetos antigos
e gera os pixels esperados antes de escolher Tiles explicitamente para novas
edições. Novos gestos Tiles mantêm células com encaixe e formas contínuas com
o encaixe desligado. Cobre ferramentas de chão, camadas e layouts localizados
no desktop/celular, com as mesmas opções isoladas de campanha, saída e navegador.
`gravewright.maps.tests.test_builder_paint_modes` mantém a
cobertura do servidor para ler e renderizar metadados de pintura já salvos.

`uv run --locked python tests/e2e/map_builder_floor_repaint.py` verifica a
repintura de chão com e sem encaixe. Confere a preservação dos registros de
origem, IDs, ordem, revisão salva e histórico de desfazer, variações de famílias,
cobertura pela união de pisos e substituição sem chão antigo escondido por
baixo. Furos, outras camadas, projetos salvos, prévias e pixels gerados mantêm
a cobertura esperada. Testes unitários de modelo, pincel e geometria também
cobrem a recusa atômica nos limites de geometria.

`uv run --locked python tests/e2e/map_builder_editor_panels.py` verifica os seis
painéis do editor, vínculos entre abas e painéis, navegação por setas, restauração
do foco e posições independentes de rolagem sem alterar documento ou revisão.
Exercita estados vazios, edição real de propriedades e desfazer, controles de
pincel Tiles/Pintura e prévia de Shift-arrastar, filtros de efeitos nativos e
controles de edição pausados na Prévia. Nomes sintéticos longos de mapa, imagem e
camada cobrem inglês/português no desktop e português/espanhol em 390px e 320px.
Usa a mesma fixture descartável e opções de saída/navegador dos demais cenários.

`uv run --locked python tests/e2e/map_builder_terrain_paint.py` exercita o seletor
Tiles/Pintura do cabeçalho e o pincel circular de terreno com texturas sintéticas
assimétricas. Um cálculo independente do kernel radial e da composição por
camada confere bordas suaves, dureza, acúmulo parado de intensidade, mistura de
materiais e borracha suave, inclusive camadas protegidas e pintura posterior à
borracha. Gestos reais exercitam desfazer em um passo, Escape, bloqueios,
posições fracionárias e a otimização Tiles sem alteração. Shift e arrastar
conferem a área e o tamanho do pincel ao vivo sem mudar origem/revisão, em
Pintura e Tiles com/sem encaixe. Compara a região de
terreno do SVG real com tiles gerados e atualizados, confere a origem exata ao
salvar/reabrir e preserva dados nativos de parede/porta/luz, estado da porta em
jogo e paredes manuais da cena. Capturas focadas em inglês/português/espanhol
no desktop/celular inspecionam os controles reais de modo e pincel. Usa a mesma
fixture descartável e opções de saída/navegador dos demais testes do builder.
Kernel, limites e raster têm cobertura focada em
`gravewright.maps.tests.test_builder_terrain_brush`,
`builder/terrain-brush.test.mjs` e `builder/terrain-painter.test.mjs`.

`uv run --locked python tests/e2e/map_builder_smart_walls.py` verifica a arte de
paredes e seus nós editáveis com uma faixa sintética assimétrica e margens
transparentes. Compara uma parede contínua com segmentos colineares e pontas
invertidas, testa encontros L/T e aberturas de portas e compara a cobertura da
Prévia com os tiles gerados. Gestos reais exercitam movimento de nó compartilhado,
encaixe, bloqueio de camada, preservação das portas, divisão pelo meio, arraste de
canto, prolongamento sobre outra parede e desfazer em um passo. Inclui foco de
teclado, cancelamento com Escape, arraste por toque no celular com zoom,
salvar/reabrir e gerar. Usa as mesmas opções isoladas de saída e navegador dos
outros cenários do Map Builder. A cobertura JavaScript focada fica em
`builder/wall-edit.test.mjs` e `builder/wall-joins.test.mjs`, junto às fontes.

`uv run --locked python tests/e2e/map_builder_free_paint.py` verifica traços
fracionários sem encaixe, círculos suaves, retângulos e polígonos, borracha por
área contínua, preenchimento da forma exata, guias e transformações dos contornos
e furos. Compara a área renderizada pelo SVG do editor com os tiles da cena
gerada, incluindo salvar/reabrir e voltar às células com encaixe. Validação do
servidor, máscaras par/ímpar, transparência, fase da textura e limites de recursos
ficam em `gravewright.maps.tests.test_builder_free_paint`.

`uv run --locked python tests/e2e/map_builder_asset_types.py` verifica categorias
exatas na biblioteca após importação com tipo, salvamento automático,
recarregamento e abertura em outra aba. Confere Pintar e o filtro de Material,
troca do tipo de um asset existente e classificação de uma imagem anterior da
campanha pelo Material, sem regravar recursos da campanha. Imagens e estado são
descartáveis.

`uv run --locked python tests/e2e/map_builder_autosave.py` exercita a persistência
automática do projeto sem clicar em Salvar: digitação, desenho, desfazer/refazer,
confirmações atrasadas durante um traço, repetição de recibo após resposta perdida,
recarregamento com escrita confirmada no servidor e rascunho desfeito mais recente,
falha de carregamento inicial/tentativa, conflitos de revisão com
cópia/recarregamento e conclusão ao navegar. Os Objetos
Inteligentes verificam aplicação automática do grafo, campos inválidos, estado
localizado em desktop/celular, configuração nativa e do projeto e proteção contra
revisão antiga sem executar ações de jogo. Usa estado descartável e imagens
geradas. Os cenários anteriores de Salvar/Cancelar manual nos Objetos Inteligentes
descrevem o fluxo anterior da modal; este cenário verifica o contrato automático.

`uv run --locked python tests/e2e/map_builder_lifecycle_events.py` configura
`onDestroy` pelo editor real e verifica conectores de região/sinal por capacidade,
layouts localizados em desktop/celular e previsão da remoção sob rollback
completo. Travessias reais de tokens de jogador verificam eventos por token e
mudanças de ocupação na primeira chegada/última saída. A remoção nativa verifica
permissões, pausa, rollback de cadeias com falha, efeitos por sinal entre elementos
e recibos idempotentes; o projeto autoral permanece intacto. Banco, mídia e saída
são isolados.

`tests/e2e/map_builder_events.py` é anterior ao contrato simplificado de eventos
de início. Use o cenário focado abaixo para o fluxo atual de interação.

`uv run --locked python tests/e2e/map_builder_event_origins.py` verifica eventos
básicos sem comparações ou filtros de estado, origem visível dos cabos em dois
níveis de zoom, layouts em inglês/português/espanhol e dois cliques reais na cena
com **Selecionar** na camada **Jogo**. Configura a sequência completa de
`onInteract` com Verificar estado, Mudar estado e Trocar imagem; verifica
salvamento automático, desfazer/refazer, reabertura, teste pelo servidor e
interação nativa; e confirma que sequências vazias ou apenas de imagem não
alternam implicitamente. Também verifica o descarte de grafos removidos no
carregamento, sem remover elementos ou assets. A fixture isola campanha, banco,
mídia, porta e saída com arte sintética. Testes de servidor em
`gravewright.maps.tests.test_blueprint_state_sprite` exercitam ações explícitas
de estado e imagem, condições com retrato inicial e recibos de repetição.

O contrato atual de eventos no servidor é coberto por `test_blueprint_events`,
`test_blueprint_base_events` e `test_blueprint_references`. Suas fixtures usam
eventos de início e nós explícitos de estado/condição; a execução entre elementos
usa sinais nomeados. A cobertura inclui descarte de grafos removidos, validação
de UUID e tipos nos grafos ativos, permissões de tranca, limites de cadeias,
rollback completo e recibos de repetição. `test_blueprint_testing` também verifica
que o mestre pode ensaiar uma cena pausada sem alterar a pausa salva: ações
normais, destruição e falhas inesperadas mantêm o jogo pausado e não persistem
efeitos do ensaio.

`uv run --locked python tests/e2e/map_builder_object_areas.py` verifica conectores
de área em objetos, tochas e Empty Objects, simulação local, ensaio com rollback,
travessias de tokens de jogador autorizado e ocupação privada. Inclui limites
rotacionados e travessias completas, com layouts desktop e móveis traduzidos.
As suítes de servidor `test_object_areas` e `test_object_area_integration` cobrem
eventos por token, ações explícitas, pausa, movimentos bloqueados, edição de
geometria, atualização de cena, importação, contagens, limites de áreas e rollback.

`uv run --locked python tests/e2e/map_builder_target_connections.py` verifica a
ligação de ações de área de um Empty Object a outros objetos por **Alvo**,
arrastando nos dois sentidos em diferentes níveis de zoom, seleção de nós
compatíveis, teclado e cancelamento, autosave, ensaio e entrada real de token.

`uv run --locked python tests/e2e/map_builder_area_live_sync.py` verifica um Empty
Object interagindo explicitamente com uma alavanca que possui ações de estado,
imagem e luz. O jogador arrasta um token para dentro, para fora e de volta; os
estados recebidos, controles, pixels da imagem e luz se atualizam nas telas de
mestre e jogador sem recarregar. A fixture também diferencia autosave do projeto
e aplicação do novo grafo de saída por **Atualizar cena**.
`test_blueprint_interact_action` cobre alvos nativos e autorais, grupos tipados,
componentes de tocha, trancas, limites, rollback, repetição, ensaio e contexto de
token após espera.

A matriz finita de combinações de Objetos Inteligentes é verificada em três
camadas:

- `tests/fixtures/map_builder_connections.json` define 28 produtores de valor e
  38 variantes consumidoras, incluindo nós sem entrada Alvo. Tanto
  `gravewright.maps.tests.test_blueprint_connection_matrix` quanto
  `builder/blueprint-connection-matrix.test.mjs` verificam os 1.064 pares com
  os mesmos tipos esperados. Também exigem que toda porta de valor registrada
  apareça na fixture. Conexões recusadas preservam o grafo; as aceitas passam
  pela validação completa e recusam um segundo fio de valor na mesma entrada.
- `gravewright.maps.tests.test_blueprint_action_matrix` verifica 362 casos de
  ação, tipo de alvo e referência/grupo, incluindo todos os estados graváveis,
  interação nativa e autoral, luzes, sons, referências ausentes/de outra cena e
  grupos mistos. Confere efeitos e identidades separadas dos alvos atendidos,
  ausentes e incompatíveis. `test_blueprint_event_matrix` verifica 387 casos de
  proprietário/evento/estado, controles, permissões, pausa, públicos,
  temporizador/espera e presença com dois tokens. Eventos apenas iniciam fluxos;
  mudar estado não executa implicitamente a interação de outro objeto.
- `uv run --locked python tests/e2e/map_builder_combination_matrix.py` exercita
  131 casos no navegador real: referências/grupos tipados nos dois sentidos de
  conexão, criação de nós em ambos os sentidos, adaptação de booleanos/números/
  textos, composição de lógica, eventos disponíveis, recursos indisponíveis,
  cancelamento, desfazer atômico, autosave, recarregamento e atualização da mesma
  cena. Um ensaio no servidor identifica pelo nome um alvo existente
  incompatível. Usa assets sintéticos e a fixture compartilhada com campanha,
  banco, mídia, porta, saída e navegador isolados.

Essas matrizes cobrem os contratos enumerados, sem garantir todos os grafos
autorais possíveis. Execute também as suítes de comportamento acima para
cadeias maiores e sincronização ao vivo entre mestre e jogador.

`uv run --locked python tests/e2e/map_builder_sprite_targets.py` verifica o
catálogo completo de nós em portas, alavancas, tochas, Objetos vazios e regiões.
Configura entrada/saída da área de um Objeto vazio diretamente em **Trocar
imagem**, com uma imagem comum ligada ao **Alvo**, sem grafo de interação no
alvo. Movimentos reais do token de jogador conferem a imagem recebida e os pixels
renderizados nas telas de mestre e jogador, além de autosave/recarregamento,
remapeamento de referências, atualização da mesma cena, movimento/redimensionamento
nativo e restauração. Mudanças manuais de geometria mantêm a proteção de conflito
na atualização. Usa a fixture descartável compartilhada e arte sintética.
`gravewright.maps.tests.test_blueprint_sprite_targets` cobre referências e grupos
tipados, todos os tipos de proprietário e modos visuais, restauração privada da
imagem-base, edições nativas, exclusão de recursos, remapeamento/validação de
arquivos, rollback e recibos de repetição.
`builder/blueprint-sprite-targets.test.mjs` verifica os contratos de catálogo e
recursos de imagem; a matriz de conexões inclui a entrada Alvo tipada de sprite.

`uv run --locked python tests/e2e/map_builder_gm_layers.py` verifica que Objetos
vazios só podem ser editados em GM, imagens públicas podem ir ao GM e voltar pelo
menu de contexto, e controladores ocultos continuam disparando ações de área com
movimentos reais dos tokens de jogador. Confere imagens comuns, alavancas, tochas
e trocas ativas de sprite nas duas telas, dados privados, geração, atualização
da fonte e recarregamento. `gravewright.maps.tests.test_empty_gm_layer` verifica
roteamento nativo, privacidade na leitura de cenas antigas, recusa de comandos de
jogador, atualização vinculada e manutenção dos conflitos de geometria manual.
Os testes dos modelos de camada e interação conferem seleção por aba, seleção
mista e controles de teclado antigos.

`uv run --locked python tests/e2e/map_builder_element_names.py` confere os campos
de nome dos oito tipos de elemento, salvamento automático, reabertura,
desfazer/refazer, duplicação e rótulos de referências. Cria Objetos vazios e
regiões diretamente pela faixa de ferramentas da biblioteca, verifica acesso
por teclado e layouts traduzidos em desktop/390/320 px, e gera/atualiza a cena
vinculada sem substituir identidades ou UUIDs de alvos.
`gravewright.maps.tests.test_builder_element_names` cobre validação, Unicode,
elementos antigos sem nome, edições nativas, superfícies dinâmicas e falhas
atômicas de gravação.

`uv run --locked python tests/e2e/map_builder_event_latency.py` mede entrada/saída
real de tokens em áreas e interação direta em uma cena com 52 imagens sintéticas
nas telas do GM e do jogador. Registra desde soltar o mouse ou interagir até o
primeiro pixel WebGL correspondente, confirmações/projeções do socket e contagens
de busca/decodificação/envio de imagens à GPU. Consultas por screenshot ficam fora
do intervalo medido. Compare execuções na mesma máquina e fixture; os tempos são
observações, não limites de aprovação. O cenário também confere marcadores de
Objetos vazios, imagens e desenhos privados sutis entre abas, edição restrita a
GM e privacidade dos dados do jogador. Aceita as opções usuais `--output` novo e
`--browser-executable`. Os testes do modelo de imagens cobrem reutilização,
remoção limitada, falhas, resultados atrasados e descarte;
`gravewright.realtime.tests.test_scene_update_priority` verifica entrega por
socket real antes de áudio bloqueado, ordem após commit e autorização atual.

`gravewright.maps.tests.test_blueprint_performance` mede comandos reais de domínio
com dados sintéticos. Confere consultas limitadas aos inventários, projeção de
trajetos, efeitos de estado/imagem/luz, atualização de metadados e propriedade
no comando seguinte, limpeza após falhas e uma notificação do histórico depois
do commit. Para registrar consultas SQL e tempos, defina
`GRAVEWRIGHT_EVENT_BENCHMARK_OUTPUT` como um arquivo JSON explícito em uma pasta
de testes dentro da instalação e execute a suíte com banco/mídia descartáveis
conforme a configuração acima. Testes normais executam uma amostra; o modo de
medição executa cinco cadeias de oito objetos e três entradas em dezesseis áreas.
Cada amostra usa um UUID de recibo novo e faz rollback ao terminar; as asserções
de efeitos ficam fora do intervalo medido. O intervalo inclui autorização,
recibos, SQL e serialização síncrona, sem a gravação final da transação em disco,
entrega pela rede ou renderização no navegador. Na fixture sintética medida,
as consultas caíram de 101 para 42 na cadeia e de 286 para 174 na entrada em
áreas. Os tempos dependem da máquina e não são limites de aprovação dos testes.

`uv run --locked python tests/e2e/map_builder_blueprints.py` verifica a modal
Objeto Inteligente da porta, cancelamento do rascunho, conexões, simulação local,
desfazer, projetos salvos e layouts móveis localizados. Também abre clientes de
mestre e jogador para verificar estado nativo, arte ativa, sincronização de luz
e áudio, repetição de comandos, permissões de portas trancadas, a janela
Automação do mestre, atualização da cena e limpeza de imagens. Usa as mesmas opções isoladas de saída e navegador.
A validação e a compatibilidade em Python estão em `test_blueprints`,
`test_blueprint_data_nodes`, `test_automation_runs`, `test_blueprint_references`, `test_builder_blueprints` e `test_blueprint_compatibility` sob
`gravewright.maps.tests`; testes dos grafos do editor executam com
`node --test gravewright/maps/static/gravewright_maps/builder/blueprint-model.test.mjs`.
`uv run --locked python tests/e2e/map_builder_levers.py` verifica a ativação do
comportamento de alavanca, editor de dois estados e imagens de objeto, referências
e simulação, salvamento/reabertura, layouts desktop/móveis localizados, geração
e dois cliques reais do jogador destrancando uma porta. Confere a projeção da
imagem ativa e o registro privado de Automação com estado isolado e assets
sintéticos. `gravewright.maps.tests.test_levers` cobre interação nativa, repetição
de comandos, cadeias limitadas e reversão, papéis, atualizações, exclusão de
imagens e arquivos de campanha.
`tests/e2e/map_builder_blueprint_assets.py` cobre os bloqueios de tipo de imagens
usadas somente em estados, precisão do volume salvo e cópia nativa sem imagem
base na porta.
`tests/e2e/map_builder_instance_nodes.py` verifica duas instâncias reais de porta,
seus conectores com verbos, aparência por estado independente, estado nativo e isolamento do
rascunho, salvamento legado sem alterações, conversão explícita após edição e
layouts localizados com teclado em telas pequenas. Usa as mesmas opções
isoladas de saída e navegador.

`tests/e2e/map_builder_drag_connections.py` exercita arraste de conexões com mouse
e toque reais, seletor de nós no ponto de soltura, conexões diretas a entradas,
vários ramos, conexões de valor tipadas, cancelamento e rejeição de ciclos. Verifica conexões salvas e
reabertas, posicionamento com zoom e arraste da vista e layouts móveis localizados.
Usa as mesmas opções isoladas de saída e navegador.

Alguns cenários aceitam `--original /caminho/da/referencia` para comparação opcional de pixels com `dist/frontend` de outro checkout. Esse checkout não é necessário para testes comuns. `reference_tokens.cjs` é uma ferramenta auxiliar de comparação, não parte do comando de testes unitários Node.

[`tests/e2e/https.py`](../../tests/e2e/https.py) executa o Daphne instalado com TLS direto e atrás de um proxy TLS temporário. Verifica criação de conta no navegador, cookies `__Host-` com Secure, HSTS, rejeição CSRF, entrada/chat por WSS autenticado e recarga da página. Handshakes TLS verificam a rejeição de origens WebSocket ausentes, externas, HTTP e com porta incorreta. O cenário gera certificados temporários e usa caminhos isolados de banco/mídia, configurações de segurança de produção, um handler estático de teste e uma camada Channels em memória. Exige as dependências Python fixadas e o Chromium do Playwright acima; não precisa de Redis externo nem Nginx. Preserva o armazenamento de certificados do sistema e os dados da aplicação e grava diagnósticos em `test-results/https/`. Isso testa o contrato de transporte da aplicação; verifique a configuração Nginx e o certificado implantados conforme o [guia de implantação](deployment.md).

`tests/e2e/realtime_processes.py` inicia especificamente um contêiner Docker temporário `redis:7-alpine` e dois processos ASGI. Exige acesso ao Docker e disponibilidade de rede/imagem; remove seu próprio contêiner ao terminar. É separado das suítes padrão Django/Node.

## Validação do executor Windows

[`tests/e2e/runner.py`](../../tests/e2e/runner.py) inicia o executor Python real com dados pessoais temporários e sem Redis. Verifica configuração inicial, estáticos coletados, segurança HTTP, mensagens autenticadas entre duas sessões WebSocket, rejeição de porta ocupada e persistência de configuração, sessão, campanha, chat e mídia após reiniciar. Também confere que o `.env` do projeto é preservado após reiniciar e os dados de desenvolvimento existentes permanecem intactos. O cenário exige as dependências de desenvolvimento e o Chromium do Playwright acima; a inicialização comum do executor não exige isso.

[`config/test_frontend_preparation.py`](../../config/test_frontend_preparation.py) cobre reaproveitamento/instalação de dependências, mudanças nos fontes e saídas, pacotes ausentes ou executável esbuild quebrado, novas tentativas após falha no build, estado corrompido e preparação concorrente. Também verifica a passagem entre os modos `--plan`/`--record` usados pelo arquivo em lote, dependências incompletas e manifestos inválidos, sem executar instalação/build npm nesses modos do helper. Esses testes com subprocessos controlados fazem parte da suíte Django normal e não substituem um build npm real. Execute a suíte específica com `uv run --locked python manage.py test config.test_frontend_preparation --noinput`.

O [workflow Windows](../../.github/workflows/windows-runner.yml) usa CMD para executar [`tests/windows/runner.py`](../../tests/windows/runner.py). Em qualquer sistema operacional, sua verificação do código confere que scripts e referências do launcher antigo estão ausentes:

```sh
python tests/windows/runner.py --source-check
```

No Windows, execute o cenário nativo completo a partir da raiz do código:

```bat
python tests\windows\runner.py
```

O cenário cria um checkout temporário com espaços, pontuação e Unicode e executa o BAT real sem override de diretório de dados. uv, Python, Node/npm, caches e temporários gerenciados ficam em `data/runner/`; estado e logs ficam em `data/`. Um perfil AppData legado fictício contém o ponteiro de outra instalação, e snapshots comprovam que ele permanece intacto. A reinstalação offline também ignora ferramentas externas compatíveis no PATH. O teste lê o atalho pelo COM do Windows, confere falha sem pausa para porta inválida e verifica criação/reutilização do `.env`, preservação de `.venv`, locks Python/npm, configuração e `PATH` do usuário/máquina/processo pai. Assets gerados são preparados apenas no checkout descartável.

O mesmo cenário executa os testes unitários de preparação do frontend e o cenário do servidor Python real no Chromium. `--skip-browser` omite a instalação das dependências de testes de navegador e o cenário no navegador, mantendo as verificações do arquivo em lote. Diagnósticos são salvos em `test-results/windows-runner/`. Código, ambiente e dados de campanha temporários são removidos ao terminar o cenário.

Use `"Install Windows.bat" --check --no-pause --data-dir "<diretório-temporário-de-dados>"` para uma preparação manual pelo arquivo em lote que termina sem servir requisições. Isso ainda instala dependências ausentes, compila recursos quando necessário e aplica migrações. A existência do workflow não significa que seus jobs já passaram para uma versão; apenas `--source-check` não valida a execução nativa do arquivo em lote.

Antes de publicar um pacote Windows, execute esse workflow e verifique a inicialização comum com dois cliques, abertura automática do navegador, Ctrl+C e fechamento do console em um computador Windows. O [guia do executor](windows-runner.md) descreve o modo de diagnóstico com diretório de dados isolado. Testes no Linux ou em outro sistema verificam o ambiente Python naquele sistema, não o CMD nem os atalhos nativos do Windows.

Ao relatar resultados, informe comandos, versões e falhas. Um cenário que não conseguiu abrir o navegador não é um teste aprovado.
