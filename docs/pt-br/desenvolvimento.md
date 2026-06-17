# Desenvolvimento

## Fluxo Local

```bash
uv sync --group dev
cp .env.example .env
chmod +x grave
./grave doctor
./grave run --open
```

Fallback:

```bash
uv run python -m app.cli doctor
uv run python -m app.cli run --open
```

## Comandos Úteis

```bash
uv run pytest tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit/test_cli_run.py tests/unit/test_cli_scaffold.py tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit -q
uv run pytest tests/e2e -q
python3 -m compileall app tests scripts main.py
docker compose -f tests/docker-compose.perf.yml config
```

## Versões de Dependências

As dependências são fixadas em versões exatas para instalações reprodutíveis:

- dependências diretas e grupos de dependências são declarados com pins `==` no `pyproject.toml`;
- a resolução completa (incluindo dependências transitivas) fica congelada no `uv.lock`, que é versionado;
- os instaladores e a imagem Docker instalam com `uv sync --frozen`, que usa o `uv.lock` exatamente e nunca re-resolve.

Para trocar a versão de uma dependência, edite o pin `==` no `pyproject.toml`, rode `uv lock` e versione o `uv.lock` atualizado. Verifique a consistência com `uv lock --check`.

## Padrões

- Prefira serviços e repositórios existentes antes de criar novas abstrações.
- Mantenha estado autoritativo no servidor.
- Mantenha CLI em `app/cli`.
- Mantenha serviços de SDK em `app/engine/sdk`.
- Atualize docs e testes quando alterar SDK, APIs públicas, schema, manifestos, rotas, CLI ou requisitos de deploy.
- Não misture refatorações grandes com mudanças de comportamento quando não for necessário.
- Não dependa de globals privados, DOM interno ou fallback visual como API pública.

## Contribuição

Leia `../../CONTRIBUTING.md`, `../../SECURITY.md` e `../../CODE_OF_CONDUCT.md`.

Contribuições para o core entram sob Apache-2.0. Contribuições para materiais públicos de API entram sob MIT, conforme `licenciamento.md`.
