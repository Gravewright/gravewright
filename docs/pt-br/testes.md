# Testes

## Gate Local Recomendado

```bash
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```

Para mudanças no CLI:

```bash
uv run pytest tests/unit/test_cli_run.py tests/unit/test_cli_scaffold.py tests/unit/test_sdk_cli.py -q
```

## Testes Unitários

```bash
uv run pytest tests/unit
```

## Checagem de Compilação

```bash
python3 -m compileall app tests scripts main.py
```

## Testes de CLI

Cobrem o comando `run` e o wiring de inicialização do servidor, o scaffolding de pacotes (`ruleset new`, `addon new`, etc.) e a descoberta de pacotes do SDK CLI com a saída JSON do doctor.

```bash
uv run pytest tests/unit/test_cli_run.py tests/unit/test_cli_scaffold.py tests/unit/test_sdk_cli.py -q
```

## Testes E2E

`tests/e2e/` sobe um servidor `uvicorn` real num subprocesso contra um banco temporário e o dirige por HTTP de verdade — sem nenhum pacote bundled e sem navegador. Ele semeia um GM e uma campanha, faz um login real de formulário protegido por CSRF, confirma que o dashboard autenticado renderiza, verifica que uma rota protegida redireciona visitantes anônimos para o login e que o script de runtime do SDK é servido como asset estático.

```bash
uv run pytest tests/e2e -q
```

A suíte não usa navegador (apenas `urllib`), então roda em qualquer ambiente, sem Selenium ou geckodriver.

## Docker e Performance

Os Compose de teste ficam em `tests/`:

```text
tests/docker-compose.perf.yml
tests/docker-compose.max-stress.yml
tests/docker-compose.i5-stress.yml
tests/docker-compose.chunk-stream.yml
```

Validação sem subir containers:

```bash
docker compose -f tests/docker-compose.perf.yml config
docker compose -f tests/docker-compose.max-stress.yml config
docker compose -f tests/docker-compose.i5-stress.yml config
docker compose -f tests/docker-compose.chunk-stream.yml config
```
