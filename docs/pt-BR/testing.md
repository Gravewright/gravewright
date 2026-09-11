# Testes

[Documentação](../README.pt-BR.md) · [English](../en/testing.md)

Execute na raiz após `uv sync --locked`. O projeto usa Django/unittest para Python, o executor nativo do Node para JavaScript e scripts Playwright independentes para navegador. Não há `npm test` na raiz nem executor pytest configurado.

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

## Cenários no navegador

```bash
uv run --locked playwright install chromium
uv run --locked python tests/e2e/authentication.py
uv run --locked python tests/e2e/realtime.py
uv run --locked python tests/e2e/frontend_api.py
uv run --locked python tests/e2e/https.py
uv run --locked python tests/e2e/runner.py
```

No Linux, o Playwright pode precisar de bibliotecas do sistema; `uv run --locked playwright install --with-deps chromium` também as instala e pode exigir privilégios administrativos. Os cenários iniciam servidores próprios em portas temporárias e criam dados fictícios. A maioria usa configurações de desenvolvimento e grava diagnósticos em `test-results/`; os cenários HTTPS e do executor usam configurações específicas descritas abaixo. Execute em sequência: vários compartilham `test-results/migration-closure/`.

| Alteração | Cenários pertinentes |
| --- | --- |
| Contas e campanhas | `authentication.py`, `inside.py`, `campaign_controls.py` |
| Tempo real e permissões | `realtime.py`, `lighting_realtime.py`, `map_prefetch.py` |
| HTTPS, WSS e confiança em proxies | `https.py`; testes Django em `config` e `gravewright.realtime` |
| Executor Windows local | `runner.py`; testes Django em `config.test_runner` e `config.test_frontend_preparation`; workflow do executor CMD Windows |
| Tabuleiro, tokens e fichas PDF | `maps.py`, `tokens_pdf.py`, `token_routes.py`, `mixed_selection.py` |
| Efeitos e renderização | `effects.py`, `effect_editor.py`, `effect_pixels.py`, `light_rendering.py` |
| Diários e dados | `journals.py`, `journal_types.py`, `dice.py`, `dice_validation.py` |
| SDK e módulos de mesa | `frontend_api.py`, `table_modules.py`, `management.py` |
| Áudio e chat | `audio_lifecycle.py`, `chat_controls.py` |

Alguns cenários aceitam `--original /caminho/da/referencia` para comparação opcional de pixels com `dist/frontend` de outro checkout. Esse checkout não é necessário para testes comuns. `reference_tokens.cjs` é uma ferramenta auxiliar de comparação, não parte do comando de testes unitários Node.

[`tests/e2e/https.py`](../../tests/e2e/https.py) executa o Daphne instalado com TLS direto e atrás de um proxy TLS temporário. Verifica criação de conta no navegador, cookies `__Host-` com Secure, HSTS, rejeição CSRF, entrada/chat por WSS autenticado e recarga da página. Handshakes TLS verificam a rejeição de origens WebSocket ausentes, externas, HTTP e com porta incorreta. O cenário gera certificados temporários e usa caminhos isolados de banco/mídia, configurações de segurança de produção, um handler estático de teste e uma camada Channels em memória. Exige as dependências Python fixadas e o Chromium do Playwright acima; não precisa de Redis externo nem Nginx. Preserva o armazenamento de certificados do sistema e os dados da aplicação e grava diagnósticos em `test-results/https/`. Isso testa o contrato de transporte da aplicação; verifique a configuração Nginx e o certificado implantados conforme o [guia de implantação](deployment.md).

`tests/e2e/realtime_processes.py` inicia especificamente um contêiner Docker temporário `redis:7-alpine` e dois processos ASGI. Exige acesso ao Docker e disponibilidade de rede/imagem; remove seu próprio contêiner ao terminar. É separado das suítes padrão Django/Node.

## Validação do executor Windows

[`tests/e2e/runner.py`](../../tests/e2e/runner.py) inicia o executor Python real com dados pessoais temporários e sem Redis. Verifica configuração inicial, estáticos coletados, segurança HTTP, mensagens autenticadas entre duas sessões WebSocket, rejeição de porta ocupada e persistência de configuração, sessão, campanha, chat e mídia após reiniciar. Também confere que o `.env` do código e os dados de desenvolvimento existentes permanecem intactos. O cenário exige as dependências de desenvolvimento e o Chromium do Playwright acima; a inicialização comum do executor não exige isso.

[`config/test_frontend_preparation.py`](../../config/test_frontend_preparation.py) cobre reaproveitamento/instalação de dependências, mudanças nos fontes e saídas, pacotes ausentes ou executável esbuild quebrado, novas tentativas após falha no build, estado corrompido e preparação concorrente. Também verifica a passagem entre os modos `--plan`/`--record` usados pelo arquivo em lote, dependências incompletas e manifestos inválidos, sem executar instalação/build npm nesses modos do helper. Esses testes com subprocessos controlados fazem parte da suíte Django normal e não substituem um build npm real. Execute a suíte específica com `uv run --locked python manage.py test config.test_frontend_preparation --noinput`.

O [workflow Windows](../../.github/workflows/windows-runner.yml) usa CMD para executar [`tests/windows/runner.py`](../../tests/windows/runner.py). Em qualquer sistema operacional, sua verificação do código confere que scripts e referências do launcher antigo estão ausentes:

```sh
python tests/windows/runner.py --source-check
```

No Windows, execute o cenário nativo completo a partir da raiz do código:

```bat
python tests\windows\runner.py
```

O cenário cria um checkout temporário com espaços, pontuação e Unicode no caminho, oculta uv e Node/npm do `PATH` do processo filho e executa o BAT real para instalar ferramentas ausentes e preparar a aplicação. O Python ainda pode ser encontrado no registro ou em instalações compartilhadas e reaproveitado. Depois, disponibiliza as ferramentas instaladas e repete offline, verificando o reaproveitamento das ferramentas, dependências e build inalterado do frontend. Lê o atalho com ícone por COM do Windows, confere que uma porta inválida falha sem pausar e verifica a preservação de `.env`, `.venv`, locks Python/npm do código, configuração pessoal e `PATH` do usuário/máquina/processo pai. As saídas geradas do frontend são preparadas intencionalmente no checkout descartável.

O mesmo cenário executa os testes unitários de preparação do frontend e o cenário do servidor Python real no Chromium. `--skip-browser` omite a instalação das dependências de testes de navegador e o cenário no navegador, mantendo as verificações do arquivo em lote. Diagnósticos são salvos em `test-results/windows-runner/`. Código, ambiente e dados de campanha temporários são removidos ao terminar o cenário.

Use `"Gravewright Runner.bat" --check --no-pause --data-dir "<diretório-temporário-de-dados>"` para uma preparação manual pelo arquivo em lote que termina sem servir requisições. Isso ainda instala dependências ausentes, compila recursos quando necessário e aplica migrações. A existência do workflow não significa que seus jobs já passaram para uma versão; apenas `--source-check` não valida a execução nativa do arquivo em lote.

Antes de publicar um pacote Windows, execute esse workflow e verifique a inicialização comum com dois cliques, abertura automática do navegador, Ctrl+C e fechamento do console em um computador Windows. O [guia do executor](windows-runner.md) descreve o modo de diagnóstico com diretório de dados isolado. Testes no Linux ou em outro sistema verificam o ambiente Python naquele sistema, não o CMD nem os atalhos nativos do Windows.

Ao relatar resultados, informe comandos, versões e falhas. Um cenário que não conseguiu abrir o navegador não é um teste aprovado.
