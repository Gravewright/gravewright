# Configuração

[Documentação](../README.pt-BR.md) · [English](../en/configuration.md)

## Carregamento e validação

As fontes de verdade são [config/environment.py](../../config/environment.py), [config/engine.py](../../config/engine.py), [config/settings.py](../../config/settings.py) e [.env.example](../../.env.example). As configurações são carregadas ao iniciar o processo. Variáveis exportadas têm prioridade sobre `.env`; não há interpolação, então `${VALUE}` permanece literal. Caminhos relativos partem da raiz do código; `~` expande para a pasta pessoal da conta do serviço.

Booleanos aceitam `1/true/yes/y/on` e `0/false/no/n/off`, sem distinguir maiúsculas. Grafias inválidas impedem a inicialização. Limites numéricos do engine devem ser positivos. Nos códigos, mínimo ≤ padrão ≤ máximo; a área do viewport não pode superar largura × altura. `GRAVEWRIGHT_PORT` deve ficar entre 1–65535. Origens públicas normalizam esquema e hostname para minúsculas, preservando portas explícitas e colchetes IPv6; assim, `HTTPS://VTT.EXAMPLE.COM` ativa as mesmas configurações HTTPS que `https://vtt.example.com`. Rejeitam caminhos, barra final, credenciais, portas vazias, caracteres de controle, query e fragmentos, incluindo delimitadores `?` ou `#` vazios. Isso não significa que toda configuração use o mesmo parser numérico ou limite superior.

O Runner nativo para [Windows](windows-runner.md), [Linux](linux-runner.md) e [macOS](macos-runner.md) lê os padrões do `.env.example` e depois o `.env` na raiz do projeto, com limites de segurança locais impostos por seu perfil específico. Se o `.env` do projeto não existir, gera uma configuração completa a partir de `.env.example`, com uma nova chave privada. Nunca importa configurações da pasta de dados do usuário. A referência abaixo descreve as configurações padrão do servidor; os recursos também se aplicam ao Runner, enquanto endereço de escuta, debug, cookies, host/origem, confiança de proxy e Channels em um único processo são fixados para execução local. Configure a porta do Runner no `.env` do projeto.

## Referência de ambiente

Os valores abaixo correspondem à configuração de exemplo/padrão. “Vazio” significa ausência de valor configurado. As explicações de bytes usam unidades binárias.

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `GRAVEWRIGHT_HOST` | `127.0.0.1` | Endereço do lançador; somente main.py |
| `GRAVEWRIGHT_PORT` | `3000` | Porta do lançador, 1–65535; somente main.py |
| `DJANGO_DEBUG` | `true` | Debug Django; false exige chave privada e Redis nas configurações padrão do servidor |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost,[::1]` | Hosts separados por vírgula, sem esquema nem porta |
| `GRAVEWRIGHT_PUBLIC_ORIGIN` | vazio | Origem pública HTTP(S); fixa origem/Host WebSocket incluindo porta, adiciona host e origem CSRF, ativa cookies Secure em HTTPS |
| `GRAVEWRIGHT_DATABASE` | `data/gravewright.sqlite3` | Arquivo SQLite relativo à raiz; :memory: é aceito |
| `GRAVEWRIGHT_MEDIA_ROOT` | `data/media` | Armazenamento privado de uploads/módulos relativo à raiz |
| `GRAVEWRIGHT_CONTENT_ROOT` | `data/vtt/compendiums` | Coleções em disco nas configurações padrão de servidor; o Runner usa `compendiums/` em sua pasta de estado |
| `GRAVEWRIGHT_MODULES_ROOT` | `GRAVEWRIGHT_MEDIA_ROOT/modules` | Pasta privada onde arquivos ZIP de módulos e pacotes extraídos são instalados; pode ser absoluta ou relativa à raiz |
| `GRAVEWRIGHT_API_MODULES_ROOT` | `extensions/api` | Pasta padrão dos fontes de módulos de navegador, relativa à raiz; pacotes assinados instalados continuam sob a raiz de mídia |
| `GRAVEWRIGHT_DJANGO_MODULES_ROOT` | `extensions/django` | Pasta padrão dos apps Django confiáveis, relativa à raiz; acrescentada ao `sys.path` quando existe |
| `GRAVEWRIGHT_SERVER_APPS` | vazio | Caminhos de importação (separados por vírgula) dos apps Django confiáveis adicionados a `INSTALLED_APPS` |
| `GRAVEWRIGHT_SERVER_APP_PATHS` | vazio | Raízes adicionais de pacotes desses apps (`:` no Linux/macOS, `;` no Windows); têm precedência sobre a pasta padrão Django |
| `GRAVEWRIGHT_AUTH_MAX_ATTEMPTS` | `30` | Tentativas de autenticação por janela de IP do cliente |
| `GRAVEWRIGHT_AUTH_WINDOW_SECONDS` | `300` | Janela de autenticação em segundos |
| `GRAVEWRIGHT_REDIS_URL` | vazio | URL Redis do Channels; as configurações padrão do servidor permitem vazio/memória somente em debug |
| `APP_NAME` | `Gravewright` | Nome padrão do produto; preferências persistidas podem substituir |
| `DEFAULT_LOCALE` | `en` | Idioma padrão; idiomas adicionais exigem pacote de tradução instalado e ativo |
| `PRIVACY_ENABLED` | `false` | Valor inicial de publicação da privacidade; o checkbox salvo em Privacidade prevalece |
| `CAMPAIGN_JOIN_CODE_ENABLED` | `true` | Ativa fluxo de códigos de entrada |
| `CAMPAIGN_CLONE_ENABLED` | `true` | Ativa clonagem de campanhas |
| `CAMPAIGN_SNAPSHOTS_ENABLED` | `true` | Ativa snapshots de campanhas |
| `CAMPAIGN_SNAPSHOT_RETENTION` | `20` | Máximo de snapshots por campanha; limpeza ao criar snapshot |
| `ADMINISTRATIVE_AUDIT_ENABLED` | `true` | Ativa registros de auditoria administrativa |
| `ADMINISTRATIVE_AUDIT_RETENTION_DAYS` | `180` | Retenção de auditoria em dias; limpeza quando o código de auditoria executa |
| `TARGETED_HANDOUTS_ENABLED` | `true` | Ativa compartilhamento direcionado de diários/materiais |
| `CAMPAIGN_EXPORT_ENABLED` | `true` | Ativa exportação portável de campanhas |
| `JOIN_CODE_DEFAULT_EXPIRES_HOURS` | `168` | Validade padrão dos códigos em horas |
| `JOIN_CODE_MIN_EXPIRES_HOURS` | `1` | Validade mínima solicitada em horas |
| `JOIN_CODE_MAX_EXPIRES_HOURS` | `720` | Validade máxima solicitada em horas |
| `JOIN_CODE_MAX_USES_LIMIT` | `1000` | Limite superior de usos permitidos por código |
| `JOIN_CODE_REDEEM_MAX_ATTEMPTS` | `10` | Máximo de tentativas de resgate por janela |
| `JOIN_CODE_REDEEM_WINDOW_SECONDS` | `600` | Janela de tentativas de resgate em segundos |
| `TRUSTED_PROXIES` | vazio | IPs/CIDRs de proxies, separados por vírgula, confiáveis para IP encaminhado e esquemas ASGI HTTP/WebSocket; vazio ignora cabeçalhos de encaminhamento |
| `DATABASE_POOL_TIMEOUT` | `30` | Espera por lock SQLite em segundos; não é tamanho de pool |
| `DATABASE_ECHO` | `false` | Configura log debug de django.db.backends; captura efetiva também depende do cursor debug do Django |
| `WS_MAX_MESSAGE_MB` | `0.0625` | Limite da aplicação por mensagem WebSocket em MB (1 MB = 1024 * 1024 bytes) |
| `WS_COMMANDS_PER_SECOND` | `20` | Taxa de comandos WebSocket por conexão |
| `WS_BURST_COMMANDS` | `40` | Capacidade de rajada de comandos WebSocket |
| `APP_DEBUG` | `false` | Diagnóstico da aplicação/renderizador; independente de DJANGO_DEBUG |
| `COMMAND_PALETTE_ENABLED` | `true` | Ativa paleta de comandos da mesa |
| `LOBBY_READY_CHECK_ENABLED` | `true` | Ativa controles de prontidão do lobby |
| `DYNAMIC_LIGHTING_ENABLED` | `true` | Ativa iluminação dinâmica |
| `GRAVEWRIGHT_AUTOMATION_WORKER_ENABLED` | `true` | Executa em segundo plano no ASGI as continuações persistentes Delay do Blueprint; false conserva esperas pendentes sem executá-las |
| `SCENE_VIEWPORT_MAX_WIDTH_CHUNKS` | `16` | Largura máxima do viewport transmitido em chunks |
| `SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS` | `16` | Altura máxima do viewport transmitido em chunks |
| `SCENE_VIEWPORT_MAX_AREA_CHUNKS` | `256` | Área máxima do viewport transmitido em chunks |
| `FOG_MAX_OPS_PER_COMMAND` | `64` | Máximo de operações de neblina por comando |
| `FOG_MAX_POLYGON_POINTS` | `128` | Máximo de pontos por polígono de neblina |
| `FOG_MAX_COORDINATE_ABS` | `100000` | Valor absoluto máximo de coordenada de neblina |
| `FOG_REQUIRE_EXPECTED_VERSION` | `true` | Exige versão esperada do estado da cena para alterar neblina |
| `TOKEN_CREATE_MANY_MAX` | `50` | Máximo de tokens criados por comando em lote |
| `BOARD_MARKERS_MAX_PER_SCENE` | `500` | Máximo de marcadores por cena |
| `BOARD_MEASUREMENTS_MAX_PER_USER` | `50` | Máximo de medições persistidas no tabuleiro por usuário |
| `JOURNAL_IMAGE_MAX_MB` | `10` | Limite de imagem em diário em MB (1 MB = 1024 * 1024 bytes) |
| `JOURNAL_PDF_MAX_MB` | `25` | Limite de PDF em diário em MB (1 MB = 1024 * 1024 bytes) |
| `PDF_SYSTEM_UPLOAD_MAX_MB` | `10` | Limite de upload de fichas PDF em MB (1 MB = 1024 * 1024 bytes) |
| `GRAVEWRIGHT_MAP_MAX_PIXELS` | `64000000` | Limite de pixels decodificados de mapa |
| `GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS` | `64000000` | Teto adicional de pixels decodificados ao usar o gerador Pillow |
| `GRAVEWRIGHT_MAP_TILER` | `auto` | Gerador de tiles: `auto`, `vips` ou `pillow` |
| `MAP_UPLOAD_MAX_MB` | `51200` | Limite de upload de mapa em MB (50 GiB); outros limites continuam aplicáveis |
| `MAP_IMAGE_MAX_WIDTH` | `500000` | Largura máxima do mapa-fonte em pixels |
| `MAP_IMAGE_MAX_HEIGHT` | `500000` | Altura máxima do mapa-fonte em pixels |
| `MAP_MAX_TILE_COUNT` | `4096` | Máximo de tiles gerados de mapa |
| `GRAVEWRIGHT_MARKETPLACE_URL` | vazio | URL HTTPS do JSON do catálogo de módulos |
| `GRAVEWRIGHT_MARKETPLACE_KEYS_FILE` | vazio | Caminho local do JSON de chaves Ed25519 confiáveis, relativo à raiz |
| `GRAVEWRIGHT_RELEASES_REPOSITORY` | `Gravewright/gravewright` | owner/repo para descobrir releases Django compatíveis; vazio deixa sem configuração |

O instalador nativo configura automaticamente o Marketplace oficial quando não há catálogo configurado. Catálogos personalizados existentes são preservados.

Duas opções comentadas também são reconhecidas:

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Fallback inseguro somente para desenvolvimento | Defina valor privado aleatório e persistente fora do debug; não use o fallback em produção |
| `DJANGO_SECURE_COOKIES` | `false` | Ativa cookies seguros; origem pública HTTPS configurada sempre os ativa. A opção não configura TLS nem a origem WebSocket |

`GRAVEWRIGHT_CONTAINER` é lido pela descoberta de releases para identificar formato de instalação quando vale `1`, `true` ou `yes`; não configura contêiner nem oferece atualização automática. `DJANGO_SETTINGS_MODULE` seleciona o módulo Python de configuração; os pontos de entrada usam `config.settings` por padrão.

## Executor de Delay do Blueprint

O host ASGI inicia automaticamente o executor de Delay. Daphne usa os hooks de
início/encerramento do reactor, inclusive no Runner habitual; outros hosts ASGI
precisam enviar eventos lifespan de início/encerramento. Importar Django ou
executar um comando de gerenciamento não inicia um agendador. O executor consulta
as entradas vencidas no banco a cada 250 ms e processa até 20 por passagem; a
execução pode ocorrer depois do prazo sob carga ou após indisponibilidade. Ele
não exige navegadores conectados, consultas HTTP, tarefas Redis ou um processo
iniciado separadamente.

Esperas pendentes ficam no SQLite configurado e sobrevivem ao reinício do
servidor. `GRAVEWRIGHT_AUTOMATION_WORKER_ENABLED=false` desativa o processamento
naquele processo sem descartar a fila. **Pausar automação** da cena conserva
somente as esperas daquela cena até retomar. O sinalizador de manutenção existente
do atualizador conserva a fila durante a verificação de saúde até confirmar ou
reverter a atualização. Aplique as migrações habituais antes
de iniciar o host; falhas de banco aparecem nos logs do servidor e geram novas
tentativas, sem fingir execução bem-sucedida. Veja
[Delay persistente](map-builder.md#delay-persistente) para cancelamento e cópia.

## Geração de tiles e imagens grandes

`GRAVEWRIGHT_MAP_MAX_PIXELS` define o limite exato de pixels do mapa. Na inicialização, a proteção de cabeçalho do Pillow é elevada até pelo menos esse valor configurado, evitando um teto inferior sem relação com a configuração. Exceder qualquer proteção de pixels informa um erro de limite de pixels. Os limites independentes de bytes, dimensões e quantidade de tiles continuam aplicáveis. As duas configurações de pixels devem ser positivas; reinicie o servidor após alterá-las.

`GRAVEWRIGHT_MAP_TILER=auto` usa libvips quando disponível e Pillow nos demais casos. `pillow` sempre seleciona Pillow; `vips` exige libvips e impede a inicialização quando ele está indisponível. As dependências padrão e os instaladores nativos não selecionam o extra opcional `vips`. Para um ambiente do código-fonte, instale com:

```bash
uv sync --locked --extra vips
```

Para um Runner nativo, instale no ambiente Python indicado pelo inicializador gerado; a `.venv` do checkout pode ser outro ambiente. Mantenha `--extra vips` nas sincronizações de dependências seguintes. Um `uv sync` exato sem esse argumento, uma reinstalação nativa ou a preparação de uma atualização gerenciada do núcleo seleciona as dependências padrão e pode remover ou omitir o extra. Verifique novamente a disponibilidade após essas operações; definir `GRAVEWRIGHT_MAP_TILER=vips` não instala dependências.

Pillow decodifica o mapa inteiro. Seu teto adicional `GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS` tem padrão de 64 milhões de pixels, mesmo com um limite geral maior. Uma imagem maior exige libvips ou um aumento explícito desse teto após avaliar a memória disponível. Esse teto limita o tamanho de imagem aceito, não a memória residente: decodificação, orientação, reamostragem e codecs também alocam memória. Libvips processa mapas comuns em faixas, mas formatos, codecs e rotações EXIF podem exigir memória adicional e espaço temporário em disco.

Apenas uma pirâmide de mapa é gerada por vez em cada processo do servidor, incluindo a decodificação. Workers separados ainda podem processar mapas simultaneamente. Os dois mecanismos produzem tiles WebP sem perdas, com a mesma disposição de 512 pixels e tiles parciais nas bordas; os níveis reduzidos podem diferir porque os filtros de reamostragem são diferentes.

A geração nativa prepara a imagem-fonte e os tiles em `data/runner/tmp/` dentro da instalação. Um `GRAVEWRIGHT_RUNNER_ROOT` explícito altera a raiz das ferramentas, e um override Django de `FILE_UPLOAD_TEMP_DIR` tem prioridade para a área temporária dos tiles; caminhos relativos partem da raiz da instalação. A pasta deve permitir escrita e comportar a fonte, os tiles preparados e eventuais arquivos temporários dos codecs enquanto os tiles finais são gravados na mídia. Falhas de armazenamento ou de geração nativa permanecem erros do servidor, e tiles já gravados são removidos se o upload falhar. Consulte [implantação](deployment.md) para timeouts de upload síncrono e dimensionamento.

## Configurações sem variáveis de ambiente

Estas opções são definidas em Python, sem leitura automática de entradas com o mesmo nome no `.env`:

| Configuração | Comportamento atual |
| --- | --- |
| `DATABASES.default.TEST.NAME` | `data/test-gravewright.sqlite3`, independentemente de `GRAVEWRIGHT_DATABASE` |
| `GRAVEWRIGHT_HEARTBEAT_SECONDS` / `GRAVEWRIGHT_PRESENCE_TTL` | Heartbeat de 5 segundos / TTL de presença de 20 segundos |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 8 MiB para tratamento de dados de requisição Django; não é limite universal de arquivos enviados |
| `SESSION_COOKIE_AGE` | 12 horas; dados de sessão ficam no banco |
| `TIME_ZONE` | `America/Sao_Paulo`, com datas que consideram fuso |
| `STATIC_ROOT` | `staticfiles/` na raiz do código; o Runner usa `staticfiles/` em sua pasta de estado |
| `MAILERS.default` | Backend de e-mail de console |

Corpos de autenticação têm limite separado de 16 KiB no middleware. Importações/exportações têm limites em `gravewright/administration/archives.py`. Uploads de mapa têm limites independentes de bytes, imagem decodificada e tiles gerados. Confira o código responsável antes de presumir que um limite governa todos os caminhos.

## Preferências persistidas da instância

`gravewright.administration.preferences` armazena identidade, canais de atualização e conteúdo de privacidade no singleton `HostSettings`. `APP_NAME` e `DEFAULT_LOCALE` são fallbacks, sem substituir obrigatoriamente os valores salvos. Inglês é nativo; a lista de idiomas disponíveis vem dos pacotes compatíveis instalados e ativos globalmente. O instalador nativo instala e ativa o Translator oficial quando `pt-BR` é escolhido. Apenas definir `DEFAULT_LOCALE=pt-BR` em uma instalação manual do código-fonte não instala esse pacote. Escolhas de idioma dos usuários têm prioridade sobre os padrões da instância.

A publicação da privacidade fica ativa se a opção de ambiente ou a persistida for verdadeira. Retenção de snapshots/auditoria é aplicada pelos fluxos das operações, não por um agendador em segundo plano fornecido pelo projeto. Preferências individuais e configurações de campanha são separadas das configurações da instância.

Para HTTPS, defina a origem pública exata acessada pelo navegador, incluindo portas diferentes da padrão. Outras entradas em `DJANGO_ALLOWED_HOSTS` não se tornam origens WebSocket adicionais quando existe origem pública configurada. Sem ela, a validação WebSocket deriva a origem do esquema ASGI e Host; esquema ausente assume HTTP.

O [adaptador de proxy ASGI](../../config/proxy.py) aceita exatamente um cabeçalho `X-Forwarded-Proto` com valor `http` ou `https` apenas do par imediato conectado em `TRUSTED_PROXIES`. Ignora valores duplicados, separados por vírgula, malformados ou de origem não confiável. Mantenha `--proxy-headers` do Daphne desativado para preservar o endereço original nessa verificação. A mesma lista controla o [IP encaminhado](../../gravewright/accounts/client_ip.py). Veja [implantação](deployment.md) para um exemplo de proxy TLS e requisitos de Redis e armazenamento.

## Armazenamento do Runner dentro da instalação

O estado padrão permanece no projeto descompactado: `data/` para logs, locks,
assets coletados e coleções de conteúdo; `data/runner/` para ferramentas
gerenciadas, ambientes, caches e arquivos temporários; `data/updates/` para
transações de atualização e recuperação. Instalador, Runner e `main.py`
configuram o armazenamento dos processos filhos antes de executar ferramentas.
Nenhum padrão escolhe configurações ou release ativa em AppData, HOME, XDG ou
Library do macOS.

`--data-dir` do Runner escolhe sua pasta de estado, inclusive `compendiums/` e
`staticfiles/`; não muda o banco nem os uploads. Defina os caminhos explícitos
deles no `.env` do projeto. Um `GRAVEWRIGHT_RUNNER_ROOT` explícito escolhe o
armazenamento de ferramentas/caches. Caminhos relativos partem da raiz da
instalação. Uma pasta sem permissão de escrita gera erro, sem trocar para uma
pasta compartilhada do usuário. Para comandos manuais de terminal, configure o
[armazenamento local das ferramentas](upgrading.md#armazenamento-local-das-ferramentas)
antes de executar uv ou npm.
