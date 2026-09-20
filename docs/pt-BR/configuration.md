# Configuração

[Documentação](../README.pt-BR.md) · [English](../en/configuration.md)

## Carregamento e validação

As fontes de verdade são [config/environment.py](../../config/environment.py), [config/engine.py](../../config/engine.py), [config/settings.py](../../config/settings.py) e [.env.example](../../.env.example). As configurações são carregadas ao iniciar o processo. Variáveis exportadas têm prioridade sobre `.env`; não há interpolação, então `${VALUE}` permanece literal. Caminhos relativos partem da raiz do código; `~` expande para a pasta pessoal da conta do serviço.

Booleanos aceitam `1/true/yes/y/on` e `0/false/no/n/off`, sem distinguir maiúsculas. Grafias inválidas impedem a inicialização. Limites numéricos do engine devem ser positivos. Nos códigos, mínimo ≤ padrão ≤ máximo; a área do viewport não pode superar largura × altura. `GRAVEWRIGHT_PORT` deve ficar entre 1–65535. Origens públicas normalizam esquema e hostname para minúsculas, preservando portas explícitas e colchetes IPv6; assim, `HTTPS://VTT.EXAMPLE.COM` ativa as mesmas configurações HTTPS que `https://vtt.example.com`. Rejeitam caminhos, barra final, credenciais, portas vazias, caracteres de controle, query e fragmentos, incluindo delimitadores `?` ou `#` vazios. Isso não significa que toda configuração use o mesmo parser numérico ou limite superior.

O [executor Windows](windows-runner.md) possui um fluxo separado: padrões do `.env.example`, depois `%LOCALAPPDATA%\Gravewright\data\.env`, com segurança e armazenamento locais impostos por seu perfil específico. Ele não carrega o `.env` do código-fonte. A referência abaixo descreve as configurações padrão do servidor; os recursos também se aplicam ao executor, enquanto endereço de escuta, banco/mídia, debug, cookies, host/origem, confiança de proxy e Channels em um único processo são fixados para execução local. Configure a porta do executor no `.env` pessoal.

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
| `GRAVEWRIGHT_MODULES_ROOT` | `GRAVEWRIGHT_MEDIA_ROOT/modules` | Pasta privada onde arquivos ZIP de módulos e pacotes extraídos são instalados; pode ser absoluta ou relativa à raiz |
| `GRAVEWRIGHT_API_MODULES_ROOT` | `extensions/api` | Pasta padrão dos fontes de módulos de navegador, relativa à raiz; pacotes assinados instalados continuam sob a raiz de mídia |
| `GRAVEWRIGHT_DJANGO_MODULES_ROOT` | `extensions/django` | Pasta padrão dos apps Django confiáveis, relativa à raiz; acrescentada ao `sys.path` quando existe |
| `GRAVEWRIGHT_SERVER_APPS` | vazio | Caminhos de importação (separados por vírgula) dos apps Django confiáveis adicionados a `INSTALLED_APPS` |
| `GRAVEWRIGHT_SERVER_APP_PATHS` | vazio | Raízes adicionais de pacotes desses apps (`:` no Linux/macOS, `;` no Windows); têm precedência sobre a pasta padrão Django |
| `GRAVEWRIGHT_AUTH_MAX_ATTEMPTS` | `30` | Tentativas de autenticação por janela de IP do cliente |
| `GRAVEWRIGHT_AUTH_WINDOW_SECONDS` | `300` | Janela de autenticação em segundos |
| `GRAVEWRIGHT_REDIS_URL` | vazio | URL Redis do Channels; as configurações padrão do servidor permitem vazio/memória somente em debug |
| `APP_NAME` | `Gravewright` | Nome padrão do produto; preferências persistidas podem substituir |
| `DEFAULT_LOCALE` | `en` | Idioma padrão; o idioma da instância atualmente suportado é en |
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
| `WS_MAX_MESSAGE_BYTES` | `65536` | Limite da aplicação por mensagem WebSocket em bytes |
| `WS_COMMANDS_PER_SECOND` | `20` | Taxa de comandos WebSocket por conexão |
| `WS_BURST_COMMANDS` | `40` | Capacidade de rajada de comandos WebSocket |
| `APP_DEBUG` | `false` | Diagnóstico da aplicação/renderizador; independente de DJANGO_DEBUG |
| `COMMAND_PALETTE_ENABLED` | `true` | Ativa paleta de comandos da mesa |
| `LOBBY_READY_CHECK_ENABLED` | `true` | Ativa controles de prontidão do lobby |
| `DYNAMIC_LIGHTING_ENABLED` | `true` | Ativa iluminação dinâmica |
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
| `JOURNAL_IMAGE_MAX_BYTES` | `10485760` | Limite de imagem em diário em bytes (10 MiB) |
| `JOURNAL_PDF_MAX_BYTES` | `26214400` | Limite de PDF em diário em bytes (25 MiB) |
| `GRAVEWRIGHT_MAP_MAX_PIXELS` | `64000000` | Limite de pixels decodificados de mapa |
| `MAP_UPLOAD_MAX_BYTES` | `53687091200` | Limite de bytes de mapa (50 GiB); outros limites continuam aplicáveis |
| `MAP_IMAGE_MAX_WIDTH` | `500000` | Largura máxima do mapa-fonte em pixels |
| `MAP_IMAGE_MAX_HEIGHT` | `500000` | Altura máxima do mapa-fonte em pixels |
| `MAP_MAX_TILE_COUNT` | `4096` | Máximo de tiles gerados de mapa |
| `GRAVEWRIGHT_MARKETPLACE_URL` | vazio | URL HTTPS do JSON do catálogo de módulos |
| `GRAVEWRIGHT_MARKETPLACE_KEYS_FILE` | vazio | Caminho local do JSON de chaves Ed25519 confiáveis, relativo à raiz |
| `GRAVEWRIGHT_RELEASES_REPOSITORY` | `Gravewright/gravewright` | owner/repo para descobrir releases Django compatíveis; vazio deixa sem configuração |

Duas opções comentadas também são reconhecidas:

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Fallback inseguro somente para desenvolvimento | Defina valor privado aleatório e persistente fora do debug; não use o fallback em produção |
| `DJANGO_SECURE_COOKIES` | `false` | Ativa cookies seguros; origem pública HTTPS configurada sempre os ativa. A opção não configura TLS nem a origem WebSocket |

`GRAVEWRIGHT_CONTAINER` é lido pela descoberta de releases para identificar formato de instalação quando vale `1`, `true` ou `yes`; não configura contêiner nem oferece atualização automática. `DJANGO_SETTINGS_MODULE` seleciona o módulo Python de configuração; os pontos de entrada usam `config.settings` por padrão.

## Configurações sem variáveis de ambiente

Estas opções são definidas em Python, sem leitura automática de entradas com o mesmo nome no `.env`:

| Configuração | Comportamento atual |
| --- | --- |
| `DATABASES.default.TEST.NAME` | `data/test-gravewright.sqlite3`, independentemente de `GRAVEWRIGHT_DATABASE` |
| `GRAVEWRIGHT_HEARTBEAT_SECONDS` / `GRAVEWRIGHT_PRESENCE_TTL` | Heartbeat de 5 segundos / TTL de presença de 20 segundos |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 8 MiB para tratamento de dados de requisição Django; não é limite universal de arquivos enviados |
| `SESSION_COOKIE_AGE` | 12 horas; dados de sessão ficam no banco |
| `TIME_ZONE` | `America/Sao_Paulo`, com datas que consideram fuso |
| `STATIC_ROOT` | `staticfiles/` na raiz do código |
| `GRAVEWRIGHT_CONTENT_ROOT` | Override opcional nas configurações Django para o catálogo; fallback `data/vtt/compendiums/`. Apenas exportar esse nome no `.env` não tem efeito |
| `MAILERS.default` | Backend de e-mail de console |

Corpos de autenticação têm limite separado de 16 KiB no middleware. Importações/exportações têm limites em `gravewright/administration/archives.py`. Uploads de mapa têm limites independentes de bytes, imagem decodificada e tiles gerados. Confira o código responsável antes de presumir que um limite governa todos os caminhos.

## Preferências persistidas da instância

`gravewright.administration.preferences` armazena identidade, canais de atualização e conteúdo de privacidade no singleton `HostSettings`. `APP_NAME` e `DEFAULT_LOCALE` são fallbacks, sem substituir obrigatoriamente os valores salvos. A lista de idiomas suportados é `('en',)`. Definir `DEFAULT_LOCALE=pt-BR` não acrescenta uma interface em português.

A publicação da privacidade fica ativa se a opção de ambiente ou a persistida for verdadeira. Retenção de snapshots/auditoria é aplicada pelos fluxos das operações, não por um agendador em segundo plano fornecido pelo projeto. Preferências individuais e configurações de campanha são separadas das configurações da instância.

Para HTTPS, defina a origem pública exata acessada pelo navegador, incluindo portas diferentes da padrão. Outras entradas em `DJANGO_ALLOWED_HOSTS` não se tornam origens WebSocket adicionais quando existe origem pública configurada. Sem ela, a validação WebSocket deriva a origem do esquema ASGI e Host; esquema ausente assume HTTP.

O [adaptador de proxy ASGI](../../config/proxy.py) aceita exatamente um cabeçalho `X-Forwarded-Proto` com valor `http` ou `https` apenas do par imediato conectado em `TRUSTED_PROXIES`. Ignora valores duplicados, separados por vírgula, malformados ou de origem não confiável. Mantenha `--proxy-headers` do Daphne desativado para preservar o endereço original nessa verificação. A mesma lista controla o [IP encaminhado](../../gravewright/accounts/client_ip.py). Veja [implantação](deployment.md) para um exemplo de proxy TLS e requisitos de Redis e armazenamento.
