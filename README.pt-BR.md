# Gravewright VTT

[English](README.md) · [Português (Brasil)](README.pt-BR.md)

Gravewright é uma mesa virtual que você pode hospedar para jogar RPG pelo navegador. Este repositório contém a implementação em Django: páginas renderizadas com Jinja2, interações com Datastar, tabuleiro JavaScript/PixiJS e WebSockets com Django Channels.

A versão atual do projeto é **Alpha 0.1.0**, uma prévia em estágio alpha. O código inclui campanhas, mapas e cenas, atores com fichas PDF, tokens, chat e dados, diários e missões, áudio, cartas, combate, compêndios e módulos de frontend instaláveis. O [guia de uso](docs/pt-BR/user-guide.md) apresenta os principais fluxos e as limitações atuais; consulte os [identificadores da versão](docs/pt-BR/development.md#identificadores-da-versão) para os nomes de pacotes e tags.

## Executar no Windows

Extraia o projeto completo e dê dois cliques em **`Gravewright Runner.bat`**. Ele detecta **uv, Python e Node.js/npm** compatíveis já instalados, instala as ferramentas ausentes quando necessário, prepara as dependências Python e npm fixadas, compila o frontend e abre a aplicação no navegador. As próximas execuções reaproveitam as ferramentas e o build do frontend quando nada mudou. Mantenha a janela do executor aberta enquanto usar o Gravewright; pressione **Ctrl+C** para encerrar.

O executor funciona diretamente no **CMD do Windows**. Use Windows 10 versão 1803 ou superior, ou Windows 11, em x64; `curl.exe`, `tar.exe` e `certutil.exe` nativos cuidam dos downloads, extração e verificação de integridade.

O executor guarda configurações, campanhas e uploads em `%LOCALAPPDATA%\Gravewright`, separados da pasta do código. Funciona apenas neste computador e dispensa um servidor Redis. Um atalho com o ícone do Gravewright é criado ao lado do launcher. Veja o [guia do executor Windows](docs/pt-BR/windows-runner.md) para requisitos, backups e solução de problemas.

## Executar localmente pelo terminal

Requisitos: **Python 3.14 ou superior**, [uv](https://docs.astral.sh/uv/) e navegador moderno com WebGL. As configurações padrão do servidor exigem Redis quando `DJANGO_DEBUG=false` e sempre que vários processos ASGI precisarem se comunicar. O executor Windows usa um perfil local separado e administra Node.js/npm para preparar o frontend. O fluxo de terminal abaixo serve os recursos versionados; recompilá-los ou executar testes JavaScript exige Node.js.

Na pasta do código-fonte:

```bash
uv sync --locked
cp -n .env.example .env
uv run --locked python manage.py migrate
uv run --locked python main.py
```

O comando de cópia preserva um `.env` existente. Acesse **http://127.0.0.1:3000** e use `/setup` para criar o primeiro proprietário do VTT. As contas seguintes são cadastradas como participantes. `createsuperuser` concede privilégios administrativos do Django; não cria o proprietário do VTT.

O banco padrão é `data/gravewright.sqlite3`; uploads privados e módulos instalados ficam em `data/media/`. O `db.sqlite3` na raiz não é o banco padrão configurado. Mantenha `.env` e dados de execução fora do controle de versão.

Veja [primeiros passos](docs/pt-BR/getting-started.md) para requisitos, primeiro acesso e solução de problemas. Para HTTPS público e WebSockets seguros, siga o guia de [implantação e backups](docs/pt-BR/deployment.md), incluindo o exemplo de proxy Nginx e a configuração de origem pública.

## Para desenvolvedores

Comece pelo [índice da documentação](docs/README.pt-BR.md), pela [arquitetura](docs/pt-BR/architecture.md) e pelo [mapa do código](docs/pt-BR/code-map.md).

| Área | Por onde começar |
| --- | --- |
| Inicialização, configuração e rotas | `main.py`, `manage.py`, `config/` |
| Fachada pública Python | `api/` |
| Regras de negócio e persistência | `gravewright/<domínio>/services.py`, `models.py` |
| Autenticação WebSocket e despacho de comandos | `gravewright/realtime/` |
| Composição da mesa e código do navegador | `gravewright/table/`, `gravewright/maps/frontend/` |
| Módulos, contratos e SDK | `gravewright/modules/` |
| Cenários de regressão no navegador | `tests/e2e/` |

O [guia de APIs](docs/pt-BR/api.md) distingue chamadas Python, rotas HTTP e contratos WebSocket/do navegador. O [guia de módulos](docs/pt-BR/modules.md) explica manifestos, verificação de pacotes, ciclo de vida e exemplos. O [guia de frontend](docs/pt-BR/frontend.md) apresenta os recursos estáticos, a renderização e os contratos gerados.

Verificação rápida:

```bash
uv run --locked python manage.py check
uv run --locked python manage.py test config gravewright --noinput
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

O executor de testes Django usa `data/test-gravewright.sqlite3`; `--noinput` permite substituir esse banco de testes. Não execute suítes simultâneas contra ele. Veja [testes](docs/pt-BR/testing.md) para a suíte JavaScript completa, ambiente controlado e cenários Playwright.

## Contribuir

Leia [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md) e o [guia de desenvolvimento](docs/pt-BR/development.md). Inglês é o idioma principal da documentação, com guias correspondentes em português. Comentários e docstrings usam inglês. A configuração de idioma da aplicação atualmente oferece inglês; a documentação em português não significa que a interface já esteja traduzida.

Relate problemas comuns nas issues do repositório, com passos para reproduzir e versões relevantes. Para vulnerabilidades, siga [SECURITY.pt-BR.md](SECURITY.pt-BR.md).

## Licença

O código próprio e a documentação do Gravewright usam **GNU GPL versão 3 somente (`GPL-3.0-only`)**, com a [permissão para módulos independentes](LICENSE-EXCEPTION.pt-BR.md) prevista na seção 7. Módulos de terceiros escritos de forma independente podem usar **qualquer licença, inclusive proprietária**, utilizando ou não as APIs fornecidas. Cópias e modificações do núcleo continuam sujeitas à GPL-3.0-only; chamar uma cópia do núcleo de módulo não muda sua licença.

Leia a [política de licenciamento](LICENSING.pt-BR.md), o [texto original da GPLv3](LICENSE) e os [avisos de terceiros](THIRD_PARTY_NOTICES.pt-BR.md). Dependências, recursos herdados e conteúdo fornecido pelos usuários preservam seus próprios termos aplicáveis.
