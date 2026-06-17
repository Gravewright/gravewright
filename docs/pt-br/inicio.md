# Início Rápido

## Requisitos

- Python 3.11 ou mais novo.
- [`uv`](https://docs.astral.sh/uv/).
- Navegador moderno com suporte a JavaScript.

SQLite é usado por padrão no desenvolvimento local.

## Instalação Fácil (Instaladores)

Para usuários não técnicos, instaladores de um clique configuram tudo — incluindo
a versão correta do Python (via `uv`) — e abrem o Gravewright no navegador. Não é
necessário ser administrador.

- **Windows:** dê duplo-clique em `install-windows.bat`.
- **macOS / Linux:** rode `bash install-macos-linux.sh` nesta pasta.

Cada instalador instala o `uv` se necessário, instala as dependências fixadas com
`uv sync --frozen`, cria o `.env` com um `SESSION_SECRET` único, roda o
diagnóstico e inicia o servidor em `http://127.0.0.1:8000`. Rode o mesmo arquivo
de novo quando quiser jogar depois. Os passos abaixo são o caminho manual.

## Rodar com Docker

Com o [Docker](https://docs.docker.com/get-docker/) instalado:

```bash
docker compose up -d --build
```

Abra `http://localhost:8000`. Seus dados persistem em volumes nomeados do Docker.
Pare com `docker compose down`. Veja o `docker-compose.yml` e o guia de deploy
para notas de segurança antes de expor publicamente.

## Instalar Dependências

```bash
uv sync
```

## Configurar Ambiente Local

```bash
cp .env.example .env
```

O `.env.example` funciona para desenvolvimento local. Troque `SESSION_SECRET` antes de usar qualquer instância compartilhada ou pública.

## Rodar Diagnóstico

```bash
chmod +x grave
./grave doctor
```

Fallback:

```bash
uv run python -m app.cli doctor
```

## Rodar a Aplicação

```bash
./grave run --open
```

Fallback:

```bash
uv run python -m app.cli run --open
```

Abra:

```text
http://127.0.0.1:8000
```

Windows:

```bat
grave.bat doctor
grave.bat run --open
```

## Primeiro Fluxo Local

1. Registre um usuário local.
2. Abra `/inside`.
3. Crie uma campanha.
4. Confira os pacotes:

   ```bash
   ./grave package list
   ```

5. Instale e habilite um ruleset se necessário:

   ```bash
   ./grave package install <ruleset-id> --yes --enable
   ```

   Você também pode instalar um ruleset ou add-on sem o CLI: como owner, abra
   **Inside > Add-ons** e envie o pacote `.zip`. Marque "Substituir existente"
   para sobrescrever um pacote com o mesmo id. Pacotes enviados ficam instalados;
   habilite-os na mesma tela.

6. Associe o ruleset à campanha.
7. Abra a mesa.
8. Envie um mapa pelo painel de cenas.
9. Crie atores, itens, diários e tokens.

## Backup Antes de Atualizar

```bash
./grave doctor
./grave backup -o gravewright-backup.zip --include-assets --verify
```

Teste restauração em uma cópia antes de atualizar dados reais.

## Dados Locais

Arquivos de runtime ficam por padrão em:

```text
storage/
```

Pacotes ficam por padrão em:

```text
data/packages/
```

Use `GRAVEWRIGHT_DATA_DIR` para manter pacotes SDK instaláveis fora do repositório.
