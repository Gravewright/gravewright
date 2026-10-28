# Gravewright VTT

[English](README.md) · [Português (Brasil)](README.pt-BR.md)

Gravewright é uma mesa virtual que você pode hospedar para jogar RPG pelo navegador. Este repositório contém a implementação em Django: páginas renderizadas com Jinja2, interações com Datastar, tabuleiro JavaScript/PixiJS e WebSockets com Django Channels.

A versão atual do projeto é **0.3.4**, uma prévia alpha. O código inclui campanhas, mapas e cenas, fichas independentes por sistema e o PDF System integrado, tokens, chat e dados, diários e missões, relógios de progresso e pistas, mapas mentais colaborativos, áudio, cartas, combate, compêndios e módulos de navegador e apps Django confiáveis instaláveis. Regras e tipos de documento pertencem aos provedores de cada sistema. O [guia de uso](docs/pt-BR/user-guide.md) apresenta os principais fluxos e as limitações atuais; consulte os [identificadores da versão](docs/pt-BR/development.md#identificadores-da-versão) para os nomes de pacotes e tags.

## Preparação da campanha e jogo

| Ferramenta | O que permite fazer |
| --- | --- |
| [Diários e referências](docs/pt-BR/journals.md) | Organizar páginas em capítulos e subcapítulos independentes e vincular fichas, diários, missões e outros recursos no texto, respeitando as permissões de cada destino |
| [Gestor de campanha](docs/pt-BR/campaign-management.md) | Abrir **Gerenciar campanha** antes de entrar na mesa. Usar documentos, biblioteca de arquivos, fichas e ferramentas de cena nativos, com painel pessoal, planejador de sessões, cronologia/calendário, colunas de missões, conexões, prévia de jogador e histórico/lixeira de diários |
| [Relógios de progresso](docs/pt-BR/clocks.md) | Acompanhar objetivos por segmentos na mesa e no gestor, com escopo de campanha/cena, controle de público, alteração opcional de progresso por jogadores e exibição fixada |
| [Pistas](docs/pt-BR/clues.md) | Preparar descobertas e notas privadas do mestre; revelar o conteúdo aos jogadores quando o progresso da descoberta for concluído |
| [Mapas mentais](docs/pt-BR/mindmaps.md) | Organizar tópicos na mesa e no gestor, conceder edição a jogadores selecionados e vincular 37 tipos de recursos conforme as permissões atuais |
| [PDF System](docs/pt-BR/pdf-system.md) | Mapear campos de texto, número e checkbox sobre um PDF não editável; vincular campos às barras do token, criar rolagens e cálculos salvos e reutilizar mapeamentos |
| [Map Builder](docs/pt-BR/map-builder.md) | Criar mapas editáveis, adotar cenas existentes compatíveis, sincronizar edições da mesa e conectar mecanismos de Objetos Inteligentes às ferramentas nativas, relógios, pistas e mapas mentais |
| [Universal VTT](docs/pt-BR/universal-vtt.md) | Importar mapas `.uvtt`, `.dd2vtt` e `.df2vtt` como cenas nativas ou projetos editáveis do Builder, com avisos de aproximações e limites do formato |

O gestor e a mesa compartilham os registros da campanha. Preparação exclusiva do
mestre, pistas não descobertas e documentos privados são filtrados no servidor.
Um vínculo com cena ou documento não concede permissão ao destino. Os guias
explicam autorização, edição concorrente e comportamento dos backups.

## Instalar e executar localmente

Comece pelo [guia do Map Builder](docs/pt-BR/map-builder.md) para criar um projeto
de mapa editável ou colocar elementos interativos sobre uma imagem de mapa pronto.
O [guia do Universal VTT](docs/pt-BR/universal-vtt.md) explica como importar
arquivos `.uvtt`, `.dd2vtt` e `.df2vtt` como cenas nativas, exportar cenas e conferir
os limites do formato. As [notas da 0.3.4](docs/releases/0.3.4.md) apresentam
públicos individuais por cena, mapas vazios, cursores compartilhados, apresentação
dos tokens, produtividade no Builder e controle de shaders por Objetos Inteligentes,
além das três migrações de banco necessárias desde a 0.3.2.

Extraia o projeto completo para uma pasta gravável, execute o instalador do seu sistema operacional e depois use o Runner gerado. O instalador prepara ferramentas, dependências, frontend e configurações; o Runner inicia a aplicação já preparada.

| Plataforma | Instalador | Executor gerado | Guia |
| --- | --- | --- | --- |
| Windows x64 | `Install Windows.bat` | `Gravewright Runner.bat` | [Windows](docs/pt-BR/windows-runner.md) |
| Linux x64 / ARM64 | `bash "./Install Linux.sh"` | `Gravewright Runner.sh` | [Linux](docs/pt-BR/linux-runner.md) |
| macOS Intel / Apple Silicon | `Install macOS.command` | `Gravewright Runner.command` | [macOS](docs/pt-BR/macos-runner.md) |

A distribuição do código inclui os instaladores das três plataformas. Os identificadores da release são **`v0.3.4`** e **`Gravewright-0.3.4-django.zip`**, com o arquivo SHA-256 correspondente. Instalações gerenciadas podem consultar o repositório configurado em **Administração → Atualizações → Verificar atualizações**. Faça backup de `.env`, dados configurados e extensões locais antes. Na atualização manual, pare o Runner, substitua os arquivos da aplicação preservando configuração, dados e extensões e execute novamente o instalador da plataforma. Veja [atualização e recuperação](docs/pt-BR/upgrading.md) e as [instruções da release](docs/releases/0.3.4.md#download-e-atualização). Esta versão não acrescenta migrações em relação à 0.3.3; use o fluxo normal do instalador ao atualizar instalações mais antigas.

Os downloads Linux usam distribuições com glibc; Alpine/musl precisa de uma instalação compatível do Node.js já disponível. O instalador macOS atende ao macOS 13.5 ou superior. Downloads de ferramentas e pacotes ausentes exigem internet. Python 3.14, uv e Node.js são preparados de forma privada quando faltam ferramentas compatíveis, sem alterações permanentes no PATH. Os executores usam um perfil local em `127.0.0.1`, sem precisar de um serviço Redis. Os guias apresentam requisitos e caminhos exatos.

**Mac Intel também precisa das Command Line Tools e do SDK da Apple.** A primeira instalação compila a dependência cryptography fixada usando Rust/OpenSSL privados, sem Homebrew, e pode demorar mais. Se faltarem as ferramentas Apple, o modo interativo abre o instalador do sistema; conclua-o e execute novamente o instalador Gravewright. `--check` sem perguntas informa o requisito. O [guia macOS](docs/pt-BR/macos-runner.md) explica os limites desse build e o reaproveitamento do cache.

### Windows

Extraia o projeto completo e dê dois cliques em **`Install Windows.bat`**. Ele instala ferramentas ausentes, prepara dependências e frontend, faz as perguntas de configuração e gera **`Gravewright Runner.bat`**. Abra o runner gerado para iniciar a aplicação sem instalações ou perguntas. Execute o instalador novamente para mudar configurações ou preparar uma versão atualizada do projeto. Mantenha a janela do executor aberta enquanto usar o Gravewright; pressione **Ctrl+C** para encerrar.

O executor funciona diretamente no **CMD do Windows**. Use Windows 10 versão 1803 ou superior, ou Windows 11, em x64; `curl.exe`, `tar.exe` e `certutil.exe` nativos cuidam dos downloads, extração e verificação de integridade.

O instalador salva configurações no `.env` do projeto. Os caminhos do banco e uploads seguem essa configuração; os padrões são `data/gravewright.sqlite3` e `data/media` no projeto. O estado, os logs e os arquivos estáticos coletados do Runner ficam em `data/`; ferramentas gerenciadas, ambientes, caches e arquivos temporários ficam em `data/runner/` nesta instalação. O executor atende apenas este computador e dispensa Redis. Um atalho com o ícone do Gravewright é criado ao lado do launcher. Veja o [guia do executor Windows](docs/pt-BR/windows-runner.md) para requisitos e solução de problemas, e o guia de [implantação e backups](docs/pt-BR/deployment.md).

Antes de atualizar, pare a aplicação e faça backup conjunto do banco configurado,
mídias privadas e `.env`. Instalações gerenciadas podem usar Administração →
Atualizações; instalações pelo código-fonte precisam instalar dependências
fixadas e executar migrações. Depois de mover ou substituir um projeto Windows,
execute novamente **`Install Windows.bat`** para prepará-lo e regenerar o Runner.

### Linux e macOS

No Linux, abra um terminal na pasta extraída e execute `bash "./Install Linux.sh"`. No macOS, abra **`Install macOS.command`** pelo Finder ou use `bash "./Install macOS.command"` nessa pasta. Responda às perguntas e depois inicie **`Gravewright Runner.sh`** ou **`Gravewright Runner.command`**. Mantenha o terminal aberto; Ctrl+C encerra a aplicação. Execute o instalador novamente após mover o projeto, atualizar seus arquivos ou alterar configurações salvas.

O `.env` permanece no projeto; os padrões de banco e uploads continuam `data/gravewright.sqlite3` e `data/media` dentro dele. O estado, os logs e os arquivos estáticos coletados do Runner ficam em `data/`; ferramentas gerenciadas, ambientes, caches e arquivos temporários ficam em `data/runner/` nesta instalação. `--data-dir` muda o estado do Runner, não os caminhos do banco/mídias no `.env`. Os guias [Linux](docs/pt-BR/linux-runner.md) e [macOS](docs/pt-BR/macos-runner.md) explicam verificações sem perguntas, reaproveitamento offline, permissões, atualização e backups.

## Executar localmente pelo terminal

Requisitos: **Python 3.14 ou superior**, [uv](https://docs.astral.sh/uv/) e navegador moderno com WebGL. As configurações padrão do servidor exigem Redis quando `DJANGO_DEBUG=false` e sempre que vários processos ASGI precisarem se comunicar. Os Runners gerados usam um perfil local separado; seus instaladores administram Node.js/npm para preparar o frontend. O fluxo de terminal abaixo serve os recursos versionados; recompilá-los ou executar testes JavaScript exige Node.js.

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

Sistemas que usam `system.combat`, `content.compendiums` ou a API de modais de módulos exigem **VTT 0.2.1 ou superior**. São capacidades adicionais do host; o SDK de navegador permanece **1.0.0**, e uma faixa de SDK isolada não comprova suporte em versões antigas do VTT. Sistemas e seu conteúdo são distribuídos separadamente; o sistema 5e SRD 0.1.0 não está incluído nesta release.

Verificação rápida:

```bash
uv run --locked python manage.py check
uv run --locked python manage.py test config gravewright --noinput
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

O executor de testes Django usa `data/test-gravewright.sqlite3`; `--noinput` permite substituir esse banco de testes. Não execute suítes simultâneas contra ele. Veja [testes](docs/pt-BR/testing.md) para a suíte JavaScript completa, ambiente controlado e cenários Playwright.

## Contribuir

Leia [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md) e o [guia de desenvolvimento](docs/pt-BR/development.md). Inglês é o idioma principal da documentação, com guias correspondentes em português. Comentários e docstrings usam inglês. O idioma base da aplicação é inglês; o módulo oficial [Translator](https://github.com/Gravewright/translator) oferece idiomas instaláveis, incluindo português e espanhol. Módulos e sistemas registram seus catálogos privados pela API de tradução do host. Conteúdo criado pelos usuários preserva o texto original.

Relate problemas comuns nas issues do repositório, com passos para reproduzir e versões relevantes. Para vulnerabilidades, siga [SECURITY.pt-BR.md](SECURITY.pt-BR.md).

## Licença

O código próprio e a documentação do Gravewright usam **GNU GPL versão 3 somente (`GPL-3.0-only`)**, com a [permissão para módulos independentes](LICENSE-EXCEPTION.pt-BR.md) prevista na seção 7. Módulos de terceiros escritos de forma independente podem usar **qualquer licença, inclusive proprietária**, utilizando ou não as APIs fornecidas. Cópias e modificações do núcleo continuam sujeitas à GPL-3.0-only; chamar uma cópia do núcleo de módulo não muda sua licença.

Leia a [política de licenciamento](LICENSING.pt-BR.md), o [texto original da GPLv3](LICENSE) e os [avisos de terceiros](THIRD_PARTY_NOTICES.pt-BR.md). Dependências, recursos herdados e conteúdo fornecido pelos usuários preservam seus próprios termos aplicáveis.
