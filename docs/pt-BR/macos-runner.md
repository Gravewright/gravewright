# Instalação macOS e Gravewright Runner

[Documentação](../README.pt-BR.md) · [English](../en/macos-runner.md) · [Linux](linux-runner.md) · [Windows](windows-runner.md)

## Instalar, configurar e executar

Use **macOS 13.5 ou superior**, em Intel x64 ou Apple Silicon ARM64, com navegador moderno com WebGL. A alternativa privada do Node.js segue os [requisitos macOS do Node.js 24](https://github.com/nodejs/node/blob/v24.19.0/BUILDING.md#platform-list). O **pacote 0.2.1 atualizado em 13 de outubro de 2026** inclui estes launchers, assim como pacotes completos gerados por [build_release.py](../../scripts/build_release.py).

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

| Ferramenta | Instalação reaproveitada | Alternativa privada |
| --- | --- | --- |
| uv | Versão 0.12.0 ou superior | uv 0.12.13 com SHA-256 fixado |
| Python | CPython 3.14 com GIL padrão para a arquitetura nativa | CPython 3.14 gerenciado pelo uv |
| Node.js/npm | Node.js 22 ou 24 LTS estável, npm 10+ | Node.js 24.19.0/npm com SHA-256 fixado |

O instalador escolhe `darwin-x64` ou `darwin-arm64` conforme a arquitetura em execução; as ferramentas devem ser compatíveis. Downloads ausentes exigem internet. Mantenha instaladas as ferramentas reaproveitadas. O Python usa `uv sync --locked --no-dev` em ambiente privado; o frontend usa `npm ci --include=dev --include=optional` e `npm run build` quando necessário. Entradas/saídas inalteradas são reaproveitadas. O `.venv` de desenvolvimento e os lock files do código são preservados. O perfil local dispensa Docker e Redis.

Se o Finder informar falta de permissão após extrair, use o Terminal na pasta do projeto:

```bash
chmod u+x "Install macOS.command"
```

O Runner gerado é executável. Se o macOS bloquear um script baixado, use o fluxo individual **Privacidade e Segurança → Abrir Mesmo Assim** apenas para um download confiável; consulte as [instruções da Apple](https://support.apple.com/en-us/102445). Não remova as proteções globalmente. Executar com `bash` também ajuda a diagnosticar um problema comum de permissão de execução.

## Configuração e armazenamento

O instalador cria/completa **o `.env` do projeto** a partir de `.env.example`, preservando valores salvos, chave privada e opções extras. Pergunta nome da mesa, idioma, porta, pasta de módulos, códigos de convite, snapshots, exportações e túneis. Caminhos relativos de banco/mídia/módulos partem da raiz do projeto. Escolher `pt-BR` instala e ativa o Translator oficial verificado; o pacote instalado e verificado pode ser reutilizado offline. O Marketplace padrão é opcional na configuração interativa; `--check` não faz perguntas.

| Local | Finalidade |
| --- | --- |
| `.env` do projeto | Configuração e chave privada persistente |
| `data/gravewright.sqlite3` do projeto | Banco padrão (`GRAVEWRIGHT_DATABASE`) |
| `data/media/` do projeto | Uploads privados e módulos padrão (`GRAVEWRIGHT_MEDIA_ROOT`) |
| `~/Library/Application Support/Gravewright/runner/` | Ferramentas privadas, caches e ambientes por localização do código |
| `~/Library/Application Support/Gravewright/data/` | Estado padrão do Runner, logs e assets coletados |
| `logs/runner.log` no estado do Runner | Diagnóstico de inicialização/execução |
| `runner.lock`, `.runner-launchers/`, `updates/` no estado | Bloqueio da instância, cópias imutáveis do launcher e recuperação de atualização |

`--data-dir` muda **o estado do Runner**, não o banco ou uploads; configure-os no `.env`. Defina `GRAVEWRIGHT_RUNNER_ROOT` com um caminho absoluto antes de instalar para escolher outra pasta de ferramentas privadas, por exemplo em um teste isolado. Isso não muda HOME nem importa configuração de outra instalação. Mover o projeto exige instalar novamente: o ambiente preparado e o estado do frontend ficam associados à localização do código.

## Execução local, atualização e backups

O Runner atende HTTP apenas em `127.0.0.1`, com um processo servidor e Channels em memória. Debug permanece desligado; verificações de host/origem, CSRF, sessão e campanhas continuam ativas. `--no-browser` mostra o endereço sem abrir o navegador padrão. O instalador pode liberar um agente de túnel local administrado separadamente, mas não instala esse software. Para acesso direto pela rede ou HTTPS público, siga [implantação](deployment.md).

Pare o Runner antes de alterar configurações ou fazer backup. Preserve juntos banco configurado, mídias privadas e `.env`; guarde também o estado do Runner para recuperação de atualizações. Migrações podem tornar versões antigas incompatíveis. Atualizações gerenciadas compatíveis substituem arquivos e regeneram o launcher macOS; cópias imutáveis em `.runner-launchers` separam o launcher em execução dos arquivos substituídos. Em atualização manual ou projeto movido, execute o instalador da nova pasta antes de iniciar. Veja [implantação e rollback](deployment.md).

### Reinstalar o pacote 0.2.1 atualizado

O reempacotamento de 13 de outubro de 2026 preserva versão `0.2.1`, canal `stable`, estágio Alpha e **Gravewright-0.2.1-django.zip**. Hosts que já usam 0.2.1 não recebem atualização automática da mesma versão. Baixe o ZIP atualizado e seu arquivo SHA-256 correspondente; não reutilize o checksum do pacote anterior.

Pare o Runner e faça backup do `.env`, dos caminhos configurados de banco/mídias/módulos e do estado. Substitua os arquivos da aplicação pelo pacote atualizado completo na pasta existente, preservando configuração e dados. Abra novamente **`Install macOS.command`** e use o Runner regenerado. O script de entrada e seus scripts de apoio precisam ser substituídos juntos. Ao mover o projeto, preserve os caminhos dos dados e prepare a nova pasta com o instalador.

`SIGHUP` usa o encerramento ordenado do Runner, incluindo a limpeza do supervisor. Uma transação de atualização interrompida é recuperada na próxima inicialização; preserve `.runner-launchers/` e `updates/` junto do estado. Veja as [notas bilíngues da atualização 0.2.1](../releases/0.2.1.md). A matriz nativa de CI inclui Intel e Apple Silicon; consulte os resultados do workflow para a validação efetiva de cada plataforma.

## Verificações sem perguntas e solução de problemas

```bash
bash "./Install macOS.command" --check --no-pause --data-dir "/tmp/Gravewright check"
bash "./Gravewright Runner.command" --check --no-browser --data-dir "/tmp/Gravewright check"
```

O `--check` do instalador prepara ferramentas/dependências/frontend, grava configuração, migra o banco e gera o Runner sem perguntas nem inicialização do servidor. O `--check` do Runner valida a aplicação preparada e pode migrar/coletar assets. **Nenhum é somente leitura.** Use uma cópia descartável e pastas explícitas nos experimentos.

Flags do instalador: `--check`, `--data-dir PATH`, `--port NUMBER`, `--no-browser`, `--no-pause` e `--help`. Flags do Runner: `--check`, `--data-dir PATH`, `--port NUMBER` e `--no-browser`. `--port` vale apenas naquela execução. Após instalar com sucesso, ferramentas/pacotes/assets inalterados podem ser reutilizados com `UV_OFFLINE=1` e `npm_config_offline=true`; dependências novas ou alteradas ainda precisam de downloads. Veja o [modo offline do uv](https://docs.astral.sh/uv/reference/environment/#uv_offline).

| Sintoma | Ação |
| --- | --- |
| Finder não executa o arquivo | Confira a permissão ou use o comando `bash` com aspas no Terminal |
| macOS bloqueia o download | Siga o fluxo individual da Apple para aprovar downloads confiáveis |
| Falha de download ou hash | Confira GitHub, nodejs.org e fontes de pacotes; preserve a verificação de integridade |
| Arquitetura ou SO incompatível | Use ferramentas nativas compatíveis e macOS 13.5+; não misture ferramentas Intel/ARM |
| Python preparado ausente ou projeto movido | Execute `Install macOS.command` novamente na nova pasta |
| Porta ocupada | Encerre o outro processo ou use `--port 3001`; reabra o instalador para mudar a porta salva |
| Outro Runner usa o mesmo estado | Encerre-o; o bloqueio do SO é liberado ao sair. O arquivo de lock permanecer é normal |
| Aplicação não inicia | Consulte `logs/runner.log` no estado escolhido e remova dados privados antes de compartilhar |

O [smoke test POSIX](../../tests/posix/smoke.py) instala em uma cópia descartável com ferramentas/estado isolados, sem mudar HOME ou configurações pessoais. Cobre espaços/Unicode, reaproveitamento offline, prontidão HTTP real e encerramento correto. O [workflow nativo](../../.github/workflows/posix-runner.yml) executa Linux e macOS Intel/Apple Silicon; o comportamento no navegador é coberto separadamente pelos testes de browser do projeto.
