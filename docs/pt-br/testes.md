# Testes

## Gate Local Recomendado

```bash
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```

Para mudanças no CLI:

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
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

Cobrem parser, backup/restore, doctor, package validate e integração básica com o SDK CLI.

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
```

## Testes E2E de Browser

`tests/e2e/` roda Firefox headless contra um servidor real, faz login, abre a mesa e valida o runtime `window.GravewrightSDK`.

```bash
uv run pytest tests/e2e -q
```

A suite pula automaticamente quando Selenium, Firefox ou geckodriver não estão disponíveis.

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
