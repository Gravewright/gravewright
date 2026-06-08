# Desenvolvimento

## Fluxo Local

```bash
uv sync
cp .env.example .env
uv run uvicorn main:app --reload
```

Use testes focados durante a implementacao e rode a suite relevante antes de abrir uma mudanca.

## Comandos Uteis

```bash
uv run pytest tests/unit
python3 -m compileall app tests scripts main.py
docker compose -f tests/docker-compose.perf.yml config
```

## Padroes

- Prefira servicos e repositorios existentes antes de criar novos pontos de abstracao.
- Mantenha estado autoritativo no servidor.
- Atualize docs e testes quando alterar APIs publicas, schema, manifestos, rotas ou requisitos de deploy.
- Nao misture refatoracoes grandes com mudancas de comportamento quando nao for necessario.

## Contribuicao

Leia `../../CONTRIBUTING.md`, `../../SECURITY.md` e `../../CODE_OF_CONDUCT.md`.

Contribuicoes para o core entram sob Apache-2.0. Contribuicoes para materiais publicos de API entram sob MIT, conforme `licenciamento.md`.
