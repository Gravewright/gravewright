# Instalação macOS e Gravewright Runner

[Documentação](../README.pt-BR.md) · [English](../en/macos-runner.md) · [Linux](linux-runner.md) · [Windows](windows-runner.md)

## Instalar, configurar e executar

Use **macOS 13.5 ou superior**, em Intel x64 ou Apple Silicon ARM64, com navegador moderno com WebGL. A alternativa privada do Node.js segue os [requisitos macOS do Node.js 24](https://github.com/nodejs/node/blob/v24.19.0/BUILDING.md#platform-list). O **pacote 0.2.1 atualizado em 13 de outubro de 2026** inclui estes launchers, assim como pacotes completos gerados por [build_release.py](../../scripts/build_release.py).

**Mac Intel exige as Command Line Tools da Apple (ou um Xcode selecionado com compilador e SDK)** para compilar a dependência descrita abaixo. Homebrew não é necessário.

1. Extraia o novo pacote completo ou use um checkout que contenha **`Install macOS.command`**, em uma pasta local gravável. Mantenha todos os arquivos juntos.
2. Abra **`Install macOS.command`** pelo Finder. Ele abre o Terminal e prepara a instalação. Também é possível abrir o Terminal na pasta do projeto e executar:

   ```bash
   bash "./Install macOS.command"
   ```

3. O instalador detecta a arquitetura nativa, reaproveita ferramentas compatíveis, baixa as privadas ausentes, instala dependências fixadas e prepara o frontend. Responda às perguntas. Enter mantém o valor exibido; Ctrl+C cancela sem salvar as respostas.
4. Ele prepara o banco, cria **`Gravewright Runner.command`** na mesma pasta e termina sem iniciar o servidor. Abra o arquivo gerado no Finder ou execute:

   ```bash
   bash "./Gravewright Runner.command"
   ```

5. Abra **http://127.0.0.1:3000** e crie a primeira conta proprietária. Mantenha o Terminal aberto; **Ctrl+C** encerra a aplicação. Fechar o navegador não para o servidor.

O Runner gerado usa o Python preparado e as configurações salvas, sem perguntas, downloads de dependências ou compilação npm. Reabra o instalador para alterar configurações, reparar dependências ou preparar arquivos novos/movidos. Caminhos com espaços e Unicode são suportados; use aspas. O launcher `.command` é um script de Terminal, não um pacote `.app` assinado.

## Permissões e ferramentas

O Bash 3.2 do macOS é suportado; não é preciso instalar outro shell ou Homebrew. O bootstrap usa `curl`, certificados do sistema, `tar`/gzip e `shasum -a 256` ou outro utilitário SHA-256 compatível. Execute como usuário comum; Python, uv e Node.js ausentes são preparados de forma privada, sem `sudo`, instalação global ou alteração permanente de PATH/perfis de shell.

| Ferramenta | Ferramenta gerenciada dentro da instalação |
| --- | --- |
| uv | uv 0.12.13 com SHA-256 verificado |
| Python | CPython 3.14 gerenciado, GIL padrão, para a plataforma nativa |
| Node.js/npm | Node.js 24.19.0/npm verificado |

O instalador escolhe `darwin-x64` ou `darwin-arm64` conforme a arquitetura em execução; as ferramentas devem ser compatíveis. Downloads ausentes exigem internet. Ferramentas verificadas são reutilizadas dentro desta instalação, sem depender do perfil global do usuário. O Python usa `uv sync --locked --no-dev` em ambiente privado; o frontend usa `npm ci --include=dev --include=optional` e `npm run build` quando necessário. Entradas/saídas inalteradas são reaproveitadas. O `.venv` de desenvolvimento e os lock files do código são preservados. O perfil local dispensa Docker e Redis.

### Compilação de dependências no Intel

Cryptography removeu o suporte oficial a macOS x86_64 e os wheels Intel na versão 49; consulte o [changelog](https://cryptography.io/en/50.0.1/changelog/#v49-0-0). O Gravewright compila localmente a versão cryptography 50.x fixada no Intel. Esse caminho é mantido pelo Gravewright e coberto pelo nosso CI de plataforma; não representa a volta do suporte oficial upstream. A versão fixada de cryptography permanece igual.

O build precisa do SDK selecionado pelo `xcrun` da Apple, Clang, Make e Perl. Se faltarem, o instalador interativo abre o diálogo oficial do sistema com:

```bash
xcode-select --install
```

Conclua a instalação da Apple e execute novamente **`Install macOS.command`**. O Gravewright não fica aguardando a conclusão do diálogo. O `--check` não o abre: termina indicando como instalar os requisitos e tentar novamente. Um Xcode completo e selecionado corretamente também pode fornecê-los. O [guia de compilação do cryptography](https://cryptography.io/en/50.0.1/installation/#building-cryptography-on-macos) apresenta os requisitos de compilador/bibliotecas.

Com os requisitos Apple disponíveis, o Gravewright baixa componentes Rust com SHA-256 fixado, compila um OpenSSL estático privado e compila cryptography com essas ferramentas. Usa [Rust 1.99.0](https://blog.rust-lang.org/2026/10/01/Rust-1.99.0/) (`rustc`, Cargo e biblioteca padrão), sem rustup, e [OpenSSL 3.5.9 LTS](https://openssl-library.org/source/), sem Homebrew. A primeira instalação Intel pode levar vários minutos a mais; ferramentas, OpenSSL preparado e caches verificados são reutilizados. Reutilização offline exige uma preparação anterior concluída, incluindo a dependência compilada e os insumos em cache.

Nas duas arquiteturas Mac, o instalador define `AUTOBAHN_USE_NVX=0` ao preparar dependências, usando a alternativa Python do Autobahn em vez da extensão nativa opcional NVX. Isso evita exigir esse build opcional no Apple Silicon, inclusive em macOS 13.5/14. O requisito de compilador/SDK do cryptography no Intel continua necessário. A inicialização normal do Runner não compila dependências.

Se o Finder informar falta de permissão após extrair, use o Terminal na pasta do projeto:

```bash
chmod u+x "Install macOS.command"
```

O Runner gerado é executável. Se o macOS bloquear um script baixado, use o fluxo individual **Privacidade e Segurança → Abrir Mesmo Assim** apenas para um download confiável; consulte as [instruções da Apple](https://support.apple.com/en-us/102445). Não remova as proteções globalmente. Executar com `bash` também ajuda a diagnosticar um problema comum de permissão de execução.

## Configuração e armazenamento

O instalador cria/completa **o `.env` do projeto** a partir de `.env.example`, preservando valores salvos, chave privada e opções extras. Pergunta nome da mesa, idioma, porta, pasta de módulos, códigos de convite, snapshots, exportações e túneis. Caminhos relativos de banco/mídia/módulos partem da raiz do projeto. Escolher `pt-BR` instala e ativa o Translator oficial verificado; o pacote instalado e verificado pode ser reutilizado offline. O Marketplace oficial é configurado automaticamente quando não há catálogo configurado. Catálogos personalizados são preservados, e as configurações oficiais verificadas são reutilizadas offline. O modo `--check` não configura o catálogo.

| Local | Finalidade |
| --- | --- |
| `.env` do projeto | Configuração e chave privada persistente |
| `data/gravewright.sqlite3` do projeto | Banco padrão (`GRAVEWRIGHT_DATABASE`) |
| `data/media/` do projeto | Uploads privados e módulos padrão (`GRAVEWRIGHT_MEDIA_ROOT`) |
| `data/runner/` | Ferramentas privadas, caches e ambientes por localização do código |
| `rust/1.99.0-x86_64-apple-darwin/` nas ferramentas | Compilador Rust/Cargo/biblioteca padrão privados e verificados para Intel |
| `openssl/3.5.9-darwin-x64/` nas ferramentas | OpenSSL estático privado para compilar a dependência no Intel |
| `cargo/` nas ferramentas | Cache Cargo privado, sem usar a instalação pessoal de `~/.cargo` |
| `data/` | Estado padrão do Runner, logs e assets coletados |
| `logs/runner.log` no estado do Runner | Diagnóstico de inicialização/execução |
| `runner.lock`, `.runner-launchers/`, `updates/` no estado | Bloqueio da instância, cópias imutáveis do launcher e recuperação de atualização |

`--data-dir` muda **o estado do Runner**, não o banco ou uploads; configure-os no `.env`. Defina `GRAVEWRIGHT_RUNNER_ROOT` com um caminho expl?cito absoluto ou relativo ao projeto antes de instalar para escolher outra pasta de ferramentas privadas, por exemplo em um teste isolado. Isso não muda HOME nem importa configuração de outra instalação. Mover o projeto exige instalar novamente: o ambiente preparado e o estado do frontend ficam associados à localização do código.

## Execução local, atualização e backups

O Runner atende HTTP apenas em `127.0.0.1`, com um processo servidor e Channels em memória. Debug permanece desligado; verificações de host/origem, CSRF, sessão e campanhas continuam ativas. `--no-browser` mostra o endereço sem abrir o navegador padrão. O instalador pode liberar um agente de túnel local administrado separadamente, mas não instala esse software. Para acesso direto pela rede ou HTTPS público, siga [implantação](deployment.md).

Pare o Runner antes de alterar configurações ou fazer backup. Preserve juntos banco configurado, mídias privadas e `.env`; guarde também o estado do Runner para recuperação de atualizações. Migrações podem tornar versões antigas incompatíveis. Atualizações gerenciadas compatíveis substituem arquivos e regeneram o launcher macOS; cópias imutáveis em `.runner-launchers` separam o launcher em execução dos arquivos substituídos. Em atualização manual ou projeto movido, execute o instalador da nova pasta antes de iniciar. Veja [implantação e rollback](deployment.md).

### Reinstalar o pacote 0.2.1 atualizado

O reempacotamento de 13 de outubro de 2026 preserva versão `0.2.1`, canal `stable`, estágio Alpha e **Gravewright-0.2.1-django.zip**. Hosts que já usam 0.2.1 não recebem atualização automática da mesma versão. Baixe o ZIP atualizado e seu arquivo SHA-256 correspondente; não reutilize o checksum do pacote anterior.

Pare o Runner e faça backup do `.env`, dos caminhos configurados de banco/mídias/módulos e do estado. Substitua os arquivos da aplicação pelo pacote atualizado completo na pasta existente, preservando configuração e dados. Abra novamente **`Install macOS.command`** e use o Runner regenerado. O script de entrada e seus scripts de apoio precisam ser substituídos juntos. Ao mover o projeto, preserve os caminhos dos dados e prepare a nova pasta com o instalador.

`SIGHUP` usa o encerramento ordenado do Runner, incluindo a limpeza do supervisor. Uma transação de atualização interrompida é recuperada na próxima inicialização; preserve `.runner-launchers/` e `updates/` junto do estado. Veja as [notas bilíngues da atualização 0.2.1](../releases/0.2.1.md). A matriz nativa de CI inclui Intel e Apple Silicon; consulte os resultados do workflow para a validação efetiva de cada plataforma.

## Verificações sem perguntas e solução de problemas

```bash
bash "./Install macOS.command" --check --no-pause --data-dir "data/check"
bash "./Gravewright Runner.command" --check --no-browser --data-dir "data/check"
```

O `--check` do instalador prepara ferramentas/dependências/frontend, grava configuração, migra o banco e gera o Runner sem perguntas nem inicialização do servidor. O `--check` do Runner valida a aplicação preparada e pode migrar/coletar assets. **Nenhum é somente leitura.** Use uma cópia descartável e pastas explícitas nos experimentos.

Flags do instalador: `--check`, `--data-dir PATH`, `--port NUMBER`, `--no-browser`, `--no-pause` e `--help`. Flags do Runner: `--check`, `--data-dir PATH`, `--port NUMBER` e `--no-browser`. `--port` vale apenas naquela execução. Após instalar com sucesso, ferramentas/pacotes/assets inalterados podem ser reutilizados com `UV_OFFLINE=1` e `npm_config_offline=true`; dependências novas ou alteradas ainda precisam de downloads. Veja o [modo offline do uv](https://docs.astral.sh/uv/reference/environment/#uv_offline).

| Sintoma | Ação |
| --- | --- |
| Finder não executa o arquivo | Confira a permissão ou use o comando `bash` com aspas no Terminal |
| macOS bloqueia o download | Siga o fluxo individual da Apple para aprovar downloads confiáveis |
| Falha de download ou hash | Confira GitHub, nodejs.org e fontes de pacotes; preserve a verificação de integridade |
| Arquitetura ou SO incompatível | Use ferramentas nativas compatíveis e macOS 13.5+; não misture ferramentas Intel/ARM |
| Faltam compilador/SDK no Intel | Conclua `xcode-select --install` e execute novamente o instalador; `--check` não abre o diálogo Apple |
| Primeira instalação Intel demora mais | A preparação de Rust/OpenSSL e cryptography inclui compilação; acompanhe o progresso e preserve o cache privado |
| Python preparado ausente ou projeto movido | Execute `Install macOS.command` novamente na nova pasta |
| Porta ocupada | Encerre o outro processo ou use `--port 3001`; reabra o instalador para mudar a porta salva |
| Outro Runner usa o mesmo estado | Encerre-o; o bloqueio do SO é liberado ao sair. O arquivo de lock permanecer é normal |
| Aplicação não inicia | Consulte `logs/runner.log` no estado escolhido e remova dados privados antes de compartilhar |

O [smoke test POSIX](../../tests/posix/smoke.py) instala em uma cópia descartável com ferramentas/estado isolados, sem mudar HOME ou configurações pessoais. Cobre espaços/Unicode, reaproveitamento offline, prontidão HTTP real e encerramento correto. O [workflow nativo](../../.github/workflows/posix-runner.yml) executa Linux e macOS Intel/Apple Silicon; o comportamento no navegador é coberto separadamente pelos testes de browser do projeto.

Todos os caminhos da tabela são relativos à pasta descompactada. `data/runner/tmp/` guarda arquivos temporários do bootstrap. Opções explícitas relativas de estado/ferramentas são resolvidas a partir deste projeto, nunca da pasta de trabalho de quem executa.
