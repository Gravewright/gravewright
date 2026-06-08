# Inicio Rapido

## Requisitos

- Python 3.11 ou mais novo.
- [`uv`](https://docs.astral.sh/uv/).
- Navegador moderno com suporte a JavaScript.

SQLite e usado por padrao no desenvolvimento local.

## Instalar Dependencias

```bash
uv sync
```

## Configurar Ambiente Local

```bash
cp .env.example .env
```

O `.env.example` funciona para desenvolvimento local. Troque `SESSION_SECRET` antes de usar qualquer instancia compartilhada ou publica.

## Rodar A Aplicacao

```bash
uv run uvicorn main:app --reload
```

Abra:

```text
http://127.0.0.1:8000
```

## Primeiro Fluxo Local

1. Registre um usuario local.
2. Abra `/inside`.
3. Crie uma campanha.
4. Instale e habilite um sistema pela aba Sistemas.
5. Associe o sistema a campanha.
6. Abra a mesa da campanha.
7. Envie um mapa pelo painel de cenas.
8. Crie atores, itens, diarios e tokens.

## Dados Locais

Arquivos de runtime ficam por padrao em:

```text
storage/
```

Pacotes e dados base ficam por padrao em:

```text
data/
```

Use `GRAVEWRIGHT_DATA_DIR` para manter sistemas e modulos instalaveis fora do repositorio.
