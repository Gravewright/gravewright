# Primeiros passos

[Documentação](../README.pt-BR.md) · [English](../en/getting-started.md)

No Windows, o [Gravewright Runner](windows-runner.md) detecta e reaproveita ferramentas instaladas, instala os requisitos ausentes, prepara dependências Python/npm e o build do frontend e inicia a aplicação local com dois cliques. O fluxo de terminal abaixo usa o código-fonte com configuração administrada manualmente.

## Requisitos

Use Python 3.14 ou superior, conforme [pyproject.toml](../../pyproject.toml). O código usa sintaxe do Python 3.14; interpretadores antigos não são suportados. Instale uv pelas [instruções oficiais](https://docs.astral.sh/uv/getting-started/installation/). Execute os comandos na pasta que contém `manage.py`.

```bash
uv sync --locked
cp -n .env.example .env
uv run --locked python manage.py migrate
uv run --locked python main.py
```

`uv sync` inclui o grupo de dependências de desenvolvimento. O lock file fornece as versões reproduzíveis. Esse fluxo de terminal serve os recursos JavaScript e CSS existentes. Para recompilá-los, use o projeto npm em `gravewright/maps/frontend`, conforme [frontend](frontend.md); o executor Windows faz essa preparação automaticamente. No CMD do Windows, substitua a cópia por `if not exist .env copy .env.example .env`.

## Primeiro acesso

Abra `http://127.0.0.1:3000`. Antes de existir um proprietário, `/setup` cria essa conta e inicia a sessão. Escolha nome, e-mail e senha com pelo menos 12 caracteres. Depois da configuração, `/register` cria participantes e `/login` autentica contas existentes.

O proprietário pode criar campanhas em `/inside`, convidar jogadores e entrar na mesa. O vínculo com a campanha define permissões de mestre/jogador. Veja o [guia de uso](user-guide.md).

Para acessar a administração separada do Django em `/admin/`:

```bash
uv run --locked python manage.py createsuperuser
```

Isso cria uma conta administrativa, não o proprietário do VTT. Não substitui `/setup`.

## Arquivos e configuração

O `.env` é opcional e carregado automaticamente. Variáveis exportadas no processo têm prioridade; `${NAME}` no `.env` permanece literal. Reinicie o servidor após alterar valores. Consulte a [referência de configuração](configuration.md).

| Caminho | Finalidade |
| --- | --- |
| `.env` | Configuração local e segredos privados |
| `data/gravewright.sqlite3` | Banco padrão da aplicação |
| `data/media/` | Uploads privados e pacotes de módulos instalados |
| `data/vtt/compendiums/` | Coleções opcionais de conteúdo nativo lidas do disco |
| `staticfiles/` | Saída de `collectstatic`, regenerada na implantação |
| `data/test-gravewright.sqlite3` | Banco de testes Django |
| `test-results/` | Logs, relatórios e capturas de testes no navegador |

Se alterar os caminhos do banco ou dos arquivos, crie as pastas necessárias e conceda escrita à conta do serviço. O desenvolvimento local usa um processo ASGI e Channels em memória. Hospedagem pública e múltiplos processos precisam de configuração adicional; veja [implantação](deployment.md).

## Problemas comuns

| Sintoma | Verificação |
| --- | --- |
| Tabela ausente / `no such table` | Execute migrações no `GRAVEWRIGHT_DATABASE` correto |
| Campanhas antigas não aparecem | Confira o caminho; `db.sqlite3` na raiz não é o banco padrão configurado |
| Inicialização rejeita um valor | Confira a variável indicada; booleanos e limites são validados |
| Inicialização exige chave ou Redis | As configurações padrão do servidor com `DJANGO_DEBUG=false` exigem chave persistente e URL do Redis; o executor Windows possui um perfil local separado |
| Login funciona, mas cookies somem no HTTP local | Esvazie `GRAVEWRIGHT_PUBLIC_ORIGIN`, desative `DJANGO_SECURE_COOKIES` para HTTP local e abra nova sessão no navegador |
| Host inválido ou WebSocket rejeitado | Use no navegador a origem de `GRAVEWRIGHT_PUBLIC_ORIGIN`, incluindo porta; confira hosts permitidos e cabeçalhos do proxy confiável em [implantação](deployment.md) |
| Porta 3000 ocupada | Altere `GRAVEWRIGHT_PORT` ou use `manage.py runserver 127.0.0.1:3001` |
| Alterações não chegam a outro processo | Configure todos os processos com a mesma camada Redis |
| Tabuleiro vazio ou falha de renderização | Confira console, disponibilidade de WebGL e erros de recursos/rede |

Para verificações de desenvolvimento e preparo do navegador, continue em [testes](testing.md).
