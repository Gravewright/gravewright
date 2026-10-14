# Instalação Linux e Gravewright Runner

[Documentação](../README.pt-BR.md) · [English](../en/linux-runner.md) · [macOS](macos-runner.md) · [Windows](windows-runner.md)

## Instalar, configurar e executar

O **pacote 0.2.1 atualizado em 13 de outubro de 2026** inclui estes launchers. Eles também fazem parte dos pacotes completos gerados por [build_release.py](../../scripts/build_release.py). Para uma instalação 0.2.1 existente, siga abaixo as instruções de reinstalação da mesma versão.

1. Use um checkout completo ou novo ZIP que contenha **`Install Linux.sh`**. Coloque-o em uma pasta local gravável, mantendo todos os arquivos juntos. Use Linux x64 ou ARM64 e navegador moderno com WebGL.
2. Abra um terminal nessa pasta e execute:

   ```bash
   bash "./Install Linux.sh"
   ```

3. O instalador detecta a distribuição, reaproveita ferramentas compatíveis, baixa as ferramentas privadas ausentes, instala dependências Python/npm fixadas e prepara o frontend. Responda às perguntas. Enter mantém o valor exibido; Ctrl+C cancela sem salvar as respostas.
4. O instalador prepara o banco, gera **`Gravewright Runner.sh`** na mesma pasta e termina sem iniciar o servidor. Inicie com:

   ```bash
   bash "./Gravewright Runner.sh"
   ```

5. Abra **http://127.0.0.1:3000** e crie a primeira conta proprietária. Mantenha o terminal aberto durante a sessão; **Ctrl+C** encerra a aplicação. Fechar o navegador não para o servidor. Gerenciadores de arquivos que oferecem “Executar no terminal” podem abrir os scripts executáveis diretamente.

Execute o instalador novamente para alterar configurações, reparar dependências ou preparar arquivos atualizados/movidos. O Runner gerado usa o ambiente pronto e nunca instala ferramentas, executa npm ou faz perguntas de instalação. Caminhos com espaços e Unicode são suportados; use aspas nos nomes em comandos de terminal.

## Distribuições e ferramentas

O instalador Bash lê `/etc/os-release` e considera `ID` e `ID_LIKE`. Reconhece estas famílias de gerenciadores quando faltam requisitos básicos de download/extração:

| Família | Exemplos | Gerenciador |
| --- | --- | --- |
| Debian | Debian, Ubuntu e derivados | `apt-get` |
| Fedora / RHEL | Fedora, RHEL, Rocky Linux, AlmaLinux | `dnf` ou `yum` |
| SUSE | openSUSE e derivados | `zypper` |
| Arch | Arch Linux, Manjaro e derivados | `pacman` |
| Alpine | Alpine Linux | `apk` |

Reconhecer uma família não significa que todas as versões foram testadas. Os binários privados oficiais do Node.js exigem **glibc 2.28+ e kernel Linux 4.18+**, em x64/ARM64, conforme os [requisitos do Node.js 24](https://github.com/nodejs/node/blob/v24.19.0/BUILDING.md#platform-list). Em Alpine/musl, coloque Node.js 22/24 nativo e npm 10+ em `data/runner/node/native/` (`bin/node` e `lib/node_modules/npm`); o instalador não usa um binário glibc nesse ambiente. Arquiteturas não suportadas ou ferramentas incompatíveis geram um diagnóstico, em vez de instalar ferramentas globais.

Os requisitos básicos são **Bash 3.2+**, `curl` com HTTPS, certificados CA, `tar`/gzip e verificação SHA-256 (`sha256sum` ou `shasum`). Alpine mínimo pode precisar da instalação do Bash antes de executar o launcher. Requisitos ausentes da distribuição podem precisar do gerenciador de pacotes e `sudo`; execute o Gravewright como usuário comum. Um `ID`/`ID_LIKE` não reconhecido interrompe o instalador antes dos requisitos, mesmo que as ferramentas estejam presentes. Informe esses identificadores para permitir suporte à família ou use o [fluxo manual pelo terminal](getting-started.md).

| Ferramenta | Ferramenta gerenciada dentro da instalação |
| --- | --- |
| uv | uv 0.12.13 com SHA-256 verificado |
| Python | CPython 3.14 gerenciado, GIL padrão, para a plataforma nativa |
| Node.js/npm | Node.js 24.19.0/npm verificado; Alpine exige distribuição nativa na pasta local de ferramentas |

Downloads de ferramentas e pacotes ausentes exigem internet. Mantenha disponíveis as ferramentas reaproveitadas. Ferramentas privadas, ambientes Python e caches ficam na pasta do Runner. O instalador não altera perfis de shell nem o PATH permanente; dispensa Docker, Homebrew e Redis. O Python usa `uv sync --locked --no-dev`; o frontend usa `npm ci --include=dev --include=optional` e `npm run build` quando os hashes indicam necessidade. O `.venv` de desenvolvimento e os lock files do código são preservados. Assets existentes são reutilizados quando entradas e saídas não mudaram.

## Configuração e armazenamento

As configurações são salvas **no `.env` do projeto**, ao lado do instalador. Opções ausentes vêm de `.env.example`; chave privada, opções extras e respostas salvas são preservadas. O instalador pergunta nome da mesa, idioma, porta local, pasta de módulos, códigos de convite, snapshots, exportações e acesso por túneis. Caminhos relativos de banco/mídia/módulos partem da raiz do projeto. Escolher `pt-BR` instala e ativa o Translator oficial assinado; um pacote instalado e verificado pode ser reutilizado offline. O Marketplace oficial é configurado automaticamente quando não há catálogo configurado. Catálogos personalizados são preservados, e as configurações oficiais verificadas são reutilizadas offline. O modo `--check` não configura o catálogo.

| Local | Finalidade |
| --- | --- |
| `.env` do projeto | Configuração e chave privada persistente |
| `data/gravewright.sqlite3` do projeto | Banco padrão (`GRAVEWRIGHT_DATABASE`) |
| `data/media/` do projeto | Uploads privados e módulos padrão (`GRAVEWRIGHT_MEDIA_ROOT`) |
| `data/runner/` | Ferramentas privadas, caches e ambientes preparados |
| `data/` | Estado padrão do Runner, logs e assets públicos coletados |
| `logs/runner.log` no estado do Runner | Diagnóstico de inicialização/execução |
| `runner.lock`, `.runner-launchers/`, `updates/` no estado | Bloqueio da instância, cópias imutáveis do launcher e recuperação de atualização |

`--data-dir` escolhe **o estado do Runner**, não o banco nem os uploads. Altere o `.env` para movê-los. `GRAVEWRIGHT_RUNNER_ROOT` pode indicar uma pasta absoluta para ferramentas privadas antes de executar o instalador; serve para verificações isoladas e não muda HOME. Ambientes e estado do frontend são separados pela localização do código; mover o projeto exige executar novamente o instalador.

## Execução local e atualização

O Runner escuta apenas em `127.0.0.1`, com um processo servidor e Channels em memória. Debug continua desligado; host/origem, CSRF, sessões e permissões das campanhas continuam ativos. `--no-browser` mostra o endereço sem abrir o navegador. Para rede local/HTTPS público, siga [implantação](deployment.md); o launcher local não configura um servidor público. A opção de túnel permite um agente local administrado separadamente; o Runner não instala o software de túnel.

Pare o Runner antes de reconfigurar ou fazer backup. Preserve juntos banco configurado, mídias privadas e `.env`, além do estado do Runner para recuperação de atualizações. Migrações podem impedir que código antigo abra um banco atualizado. Atualizações gerenciadas compatíveis substituem arquivos e regeneram o launcher da plataforma; `.runner-launchers` separa o launcher em execução dos arquivos substituídos. Em atualização manual, extraia/obtenha o projeto novo completo e rode seu instalador antes de iniciar. Consulte [implantação e rollback](deployment.md).

### Reinstalar o pacote 0.2.1 atualizado

O reempacotamento de 13 de outubro de 2026 mantém versão `0.2.1`, canal `stable`, estágio Alpha e **Gravewright-0.2.1-django.zip**. Um host que já usa 0.2.1 não recebe atualização automática para essa mesma versão. Baixe o ZIP atualizado **e seu SHA-256 correspondente**; o checksum anterior pertence ao pacote anterior.

Pare o Runner e faça backup de `.env`, dos caminhos configurados de banco/mídias/módulos e do estado do Runner. Substitua os arquivos da aplicação pelo conteúdo completo do novo pacote na pasta existente, preservando configuração e dados. Execute novamente `bash "./Install Linux.sh"` e use o Runner regenerado. Não substitua somente o script de entrada: os scripts de apoio também fazem parte da atualização. Se mover o projeto, preserve os caminhos de armazenamento e instale novamente na nova pasta.

O `SIGHUP` POSIX é tratado como encerramento ordenado, inclusive ao fechar o terminal, sem pular a limpeza do supervisor. Transações de atualização interrompidas são recuperadas na próxima inicialização. Preserve `.runner-launchers/` e `updates/` junto do estado. Consulte as [notas bilíngues da atualização 0.2.1](../releases/0.2.1.md).

## Verificações e solução de problemas

Preparação sem perguntas nem inicialização do servidor:

```bash
bash "./Install Linux.sh" --check --no-pause --data-dir "data/check"
bash "./Gravewright Runner.sh" --check --no-browser --data-dir "data/check"
```

Essas verificações **gravam arquivos**: a instalação prepara ferramentas/dependências/frontend, `.env`, banco e Runner; o `--check` do Runner pode executar migrações e coletar assets. Não são somente leitura. Use uma cópia descartável e pastas explícitas para experimentos. Flags do instalador: `--check`, `--data-dir PATH`, `--port NUMBER`, `--no-browser`, `--no-pause` e `--help`. Flags do Runner: `--check`, `--data-dir PATH`, `--port NUMBER` e `--no-browser`; a porta informada vale apenas naquela execução.

Após uma instalação bem-sucedida, ferramentas/pacotes/assets inalterados podem ser reaproveitados com `UV_OFFLINE=1` e `npm_config_offline=true`. Isso não promete instalação nova ou dependências alteradas sem internet. Veja o [modo offline do uv](https://docs.astral.sh/uv/reference/environment/#uv_offline).

| Sintoma | Ação |
| --- | --- |
| Gerenciador abre o script como texto | Abra um terminal e use o comando `bash` com aspas |
| Faltam curl, certificados CA, tar ou hash | Instale os requisitos indicados para a distribuição; tente novamente como usuário comum |
| Node não inicia / falta GLIBC | Confira os requisitos; Alpine/musl precisa de Node/npm nativos em `data/runner/node/native/` |
| Falha de download/integridade | Confira GitHub, nodejs.org e fontes de pacotes; use o projeto completo e mantenha a verificação de hash |
| Projeto movido / Python preparado ausente | Execute `Install Linux.sh` novamente na nova pasta |
| Porta ocupada | Encerre o outro processo ou use `--port 3001`; o instalador muda o padrão salvo |
| Outro Runner usa o mesmo estado | Encerre-o; o bloqueio do SO é liberado ao sair. O arquivo de lock permanecer é normal |
| Falha ao iniciar | Leia `logs/runner.log` na pasta de estado escolhida; remova dados privados antes de compartilhar |

Os [smoke tests POSIX](../../tests/posix/smoke.py) usam uma cópia descartável, ferramentas privadas, caminhos com espaços/Unicode, preparação sem perguntas, reutilização offline, prontidão HTTP real e encerramento correto. O [workflow POSIX](../../.github/workflows/posix-runner.yml) executa testes nativos em Linux/macOS; testes de distribuição com simulações cobrem separadamente os ramos de detecção. CI de plataforma não significa que toda distribuição reconhecida foi testada.

Todos os caminhos da tabela são relativos à pasta descompactada. `data/runner/tmp/` guarda arquivos temporários do bootstrap. Opções explícitas relativas de estado/ferramentas são resolvidas a partir deste projeto, nunca da pasta de trabalho de quem executa.
