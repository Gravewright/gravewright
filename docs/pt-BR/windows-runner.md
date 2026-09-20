# Gravewright Runner para Windows

[Documentação](../README.pt-BR.md) · [English](../en/windows-runner.md)

O **Gravewright Runner** detecta ferramentas instaladas, prepara a aplicação e inicia o Gravewright no seu próprio computador Windows. Campanhas e configurações ficam fora da pasta do código, para que substituir os arquivos da aplicação não remova seus dados pessoais.

## Iniciar com dois cliques

1. Use **Windows 10 versão 1803 ou superior, ou Windows 11, em x64/AMD64**, com as ferramentas nativas `curl.exe`, `tar.exe` e `certutil.exe` e navegador moderno com WebGL. Este launcher não oferece suporte a Windows de 32 bits nem Windows em ARM.
2. Extraia o **ZIP completo do projeto** para uma pasta local em que você possa gravar. Não execute dentro do ZIP nem copie apenas o `.bat`.
3. Dê dois cliques em **`Gravewright Runner.bat`**. Ele verifica uv, Python e Node.js/npm instalados e mostra os caminhos e versões escolhidos. Internet é necessária para baixar ferramentas ou dependências ausentes.
4. Aguarde o executor instalar dependências, compilar o frontend quando necessário, preparar o banco e abrir o navegador. O endereço padrão é **http://127.0.0.1:3000**.
5. Crie a primeira conta de proprietário na tela de configuração. Nas próximas execuções, entre com a mesma conta. Veja o [guia de uso](user-guide.md) para campanhas e a mesa.

Ferramentas compatíveis já instaladas são reaproveitadas. Somente ferramentas ausentes ou incompatíveis exigem uma instalação local separada para seu usuário Windows; o executor não atualiza nem substitui suas ferramentas existentes, não exige administrador nem altera permanentemente o `PATH`. As dependências Python da aplicação ficam no ambiente isolado do executor. Docker e servidor Redis não são necessários.

O `.bat` executa diretamente no CMD do Windows e cuida da detecção de ferramentas, downloads, instalação de dependências, comandos de build npm e inicialização da aplicação. Usa os utilitários nativos do Windows para download, arquivos compactados e hashes e depois invoca os executáveis Python e Node selecionados.

Mantenha a janela do console aberta enquanto usar o Gravewright. **Pressione Ctrl+C nessa janela para encerrar o servidor.** Fechar o navegador não o encerra. Aguarde a saída do executor antes de substituir arquivos da aplicação ou fazer backup. Se a inicialização falhar, o `.bat` mantém a mensagem de erro visível.

## Detecção de ferramentas e preparação do frontend

| Ferramenta | Instalação existente compatível | Se nenhuma estiver disponível |
| --- | --- | --- |
| uv | Versão **0.12.0 ou superior** disponível para o launcher | Baixa a versão fixada **0.12.13** e verifica sua integridade |
| Python | **CPython 3.14**, Windows x64, build padrão com GIL; descoberto pelo uv, incluindo interpretadores instalados/do sistema e gerenciados compartilhados | Baixa um Python 3.14 gerenciado e privado |
| Node.js e npm | **Node.js 22 ou 24 LTS** estável, x64, com **npm 10 ou superior** funcionando | Baixa o pacote Windows verificado do **Node.js 24.19.0** com npm |

O console informa qual instalação foi reaproveitada ou baixada. O Python é usado por meio de um ambiente de dependências isolado, mesmo quando o interpretador base vem de uma instalação existente. Mantenha as ferramentas reaproveitadas instaladas enquanto usar esse ambiente do executor.

O executor verifica e sincroniza dependências Python de execução com `uv sync --locked --no-dev`. No npm, pode reaproveitar uma instalação de dependências quando as versões dos pacotes obrigatórios correspondem ao lock e uma verificação real do esbuild passa. Caso contrário, ou quando as entradas registradas das dependências mudam, executa `npm ci --include=dev --include=optional`, incluindo esbuild. Depois executa `npm run build` quando a preparação é necessária. Isso usa o projeto npm versionado em `gravewright/maps/frontend` e recompila os recursos gerados usados pela aplicação.

O frontend é compilado na primeira preparação e quando suas entradas mudam. As próximas execuções conferem os hashes registrados das entradas e saídas e pulam um build válido e inalterado; saídas geradas ausentes ou modificadas provocam uma nova compilação. A pasta do código precisa ser gravável porque a preparação atualiza recursos estáticos gerados. Veja [frontend](frontend.md) para o mapeamento entre código e saída. Esse processo não baixa novas versões do código Gravewright nem executa a suíte de testes de navegador.

## Ícone e atalho do projeto

O launcher tenta criar **`Gravewright Runner.lnk`** ao lado do `.bat`, com a marca do Gravewright como ícone. Dê dois cliques em qualquer um para iniciar. O `.bat` usa o ícone de arquivo em lote do Windows; o atalho gerado recebe o ícone do projeto. Nenhum atalho é adicionado automaticamente à área de trabalho.

A [nota sobre a origem do ícone](../../scripts/windows/ICON-NOTICE.md) registra a conversão dos estilos existentes da aplicação e a licença preservada da interface original.

Se a pasta do código não permitir criar o atalho, a inicialização continua e informa a falha. Mova o projeto extraído para uma pasta gravável e execute o `.bat` novamente para criar o atalho. Depois de mover o projeto, use o `.bat` no novo local para atualizar o destino do atalho.

## Onde seus arquivos ficam

Cole **`%LOCALAPPDATA%\Gravewright`** na barra de endereços do Explorador de Arquivos. O executor usa estes caminhos para sua conta Windows:

| Caminho dentro dessa pasta | Finalidade |
| --- | --- |
| `data\.env` | Chave persistente, porta e configuração opcional de recursos |
| `data\gravewright.sqlite3` | Contas, campanhas e estado da aplicação |
| `data\media\` | Uploads privados e módulos instalados |
| `data\compendiums\` | Conteúdo local de compêndios |
| `data\staticfiles\` | Recursos públicos gerados; reconstruídos pelo executor |
| `data\logs\runner.log` | Diagnóstico de execução e inicialização, com rotação |
| `data\runner.lock` | Bloqueio que impede dois executores de usar os mesmos dados |
| `runner\` | Ferramentas baixadas apenas quando necessário, caches de pacotes e ambientes Python isolados por localização do código |
| `runner\prepare.lock` | Trava de arquivo do Windows que impede preparações simultâneas de ferramentas/dependências; liberada automaticamente ao terminar |
| `runner\frontend\<hash-local-do-código>\state.json` | Estado da preparação do frontend usado para verificar versões das ferramentas, entradas e saídas geradas |

O `.env`, `.venv` e `data/` do código-fonte são separados e permanecem intactos nesse fluxo. A preparação do frontend atualiza os recursos estáticos gerados do projeto e o diretório ignorado de dependências npm `gravewright/maps/frontend/node_modules`. Campanhas existentes criadas com `main.py` não aparecem automaticamente no banco separado do executor. Use exportação/importação de campanhas quando adequado, ou migre deliberadamente o banco completo e a mídia correspondente com ambos os servidores parados e backups preservados.

Todas as cópias do launcher usadas pela mesma conta Windows compartilham a pasta pessoal padrão. Elas não representam instalações independentes das suas campanhas. O executor verifica o bloqueio dos dados e a porta escolhida antes de preparar o banco; não encerra outro programa para liberar a porta.

## Configuração e backups

Pare o executor antes de editar **`data\.env`**. Para mudar a porta padrão, altere a entrada `GRAVEWRIGHT_PORT=3000`, por exemplo para `GRAVEWRIGHT_PORT=3001`, e inicie novamente. O endereço no navegador acompanha a porta. Mantenha a `DJANGO_SECRET_KEY` gerada privada e preserve-a entre execuções e restaurações.

Na primeira inicialização normal sem marketplace configurado, o `.bat` pergunta se deseja instalar o **Marketplace padrão do Gravewright**. Ao aceitar com `S`/`Y`, o executor baixa o arquivo oficial de chaves públicas, confere seu SHA-256, grava-o em `data\marketplace\trusted-keys.json` e adiciona ao `.env` pessoal a URL do catálogo e o caminho das chaves. O proprietário também pode fazer a mesma instalação em **Configurações → Marketplace**. Ao recusar no `.bat`, a decisão fica registrada em `data\.default-marketplace-choice` e a pergunta não reaparece; o botão da interface continua disponível. Para fazer a pergunta reaparecer, pare o executor, apague esse arquivo e execute o `.bat`. O modo `--check` nunca faz perguntas nem altera essa escolha.

O executor carrega os padrões do `.env.example` fornecido e depois o seu `.env` pessoal. Opções de recursos descritas no [guia de configuração](configuration.md) podem ser adicionadas ali. O perfil local impõe endereço de escuta, caminhos de armazenamento, debug, cookies, host/origem, proxy e Channels; alterar variáveis de implantação não transforma o executor em um servidor de rede. O `.env` do código-fonte não é carregado.

Para fazer backup, pare o Gravewright e copie **a pasta `data` inteira** para um local seguro. Preserve juntos a chave, o banco e os arquivos privados. Antes de instalar uma versão mais nova do projeto, guarde um backup correspondente à versão anterior do código: a inicialização aplica migrações, que podem tornar uma versão antiga incompatível com o banco atualizado.

As atualizações são manuais: pare o executor, faça backup dos dados, extraia o novo código completo e execute seu `.bat`. A nova inicialização verifica as ferramentas disponíveis, sincroniza as dependências com os locks Python/npm daquela versão, prepara o frontend e aplica migrações. Ela não baixa automaticamente novas versões do código do Gravewright. Remover a pasta do código ou a pasta descartável de ferramentas `runner` não desinstala suas campanhas; remover a pasta `data` apaga seus dados.

## Limite da execução local

O executor serve **HTTP somente em `127.0.0.1`**, com um processo Daphne e Channels em memória. O debug Django permanece desativado. As verificações de origem, host, sessão, CSRF e permissões da campanha continuam ativas, e uploads privados passam pelas rotas protegidas da aplicação. Apenas os recursos públicos coletados são servidos diretamente.

Esse perfil é para o computador que executa o launcher. Para jogadores em outro computador, serviço na rede local, HTTPS ou instância exposta à internet, siga [implantação](deployment.md) e configure separadamente a aplicação ASGI padrão, Redis e armazenamento. Não exponha o executor por um túnel ou proxy reverso público.

## Problemas comuns

| Sintoma | O que verificar |
| --- | --- |
| Arquivos do projeto ausentes | Extraia o ZIP completo; mantenha juntos o `.bat`, `scripts`, `config`, pastas da aplicação e lockfile |
| Download ou instalação de dependência falhou | Leia o erro no console do executor; confirme acesso aos releases GitHub, nodejs.org e às URLs de pacotes Python/npm usadas pelos locks, depois execute novamente |
| Falha na verificação de integridade de ferramenta | Não ignore a verificação; tente novamente com uma cópia nova do projeto e investigue o download ou arquivo em cache indicado |
| Falha na preparação do frontend | Leia o erro npm/build no console do executor e confirme que a pasta do projeto extraído é gravável |
| Falta um utilitário Windows de download/arquivo/hash | Use uma instalação Windows compatível com `curl.exe`, `tar.exe` e `certutil.exe` disponíveis; confira o nome da ferramenta ausente informado pelo executor |
| Outra instância está executando | Use a janela existente ou encerre aquela instância com Ctrl+C antes de tentar novamente |
| Porta ocupada | Pare seu outro servidor local ou altere `GRAVEWRIGHT_PORT` no `.env` pessoal |
| O navegador não abriu | Abra o endereço exato mostrado pelo executor quando ele indicar que está pronto |
| Campanhas antigas não aparecem | Confira se foram criadas no banco do código-fonte ou em outra conta Windows |
| A aplicação falha ao iniciar | Consulte `data\logs\runner.log`; remova segredos, dados de contas e caminhos privados antes de compartilhar diagnósticos |

## Implementação e validação

[`Gravewright Runner.bat`](../../Gravewright%20Runner.bat) detecta instalações compatíveis, baixa ferramentas ausentes com `curl.exe`, extrai arquivos com `tar.exe` e verifica hashes com `certutil.exe`. Os comandos `uv sync`, `npm ci` e `npm run build` são implementados no arquivo em lote. [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) fornece operações `--plan` e `--record` para conferir dependências, impressões dos arquivos e saídas geradas; o arquivo em lote fornece os caminhos das ferramentas escolhidas e o diretório de estado por código. O [helper de atalho](../../scripts/windows/create_shortcut.py) usa a biblioteca padrão do Python e COM do Windows para criar o `.lnk`. Veja [avisos de terceiros](../../THIRD_PARTY_NOTICES.pt-BR.md) para o escopo das licenças das ferramentas reaproveitadas e baixadas.

[`scripts/gravewright_runner.py`](../../scripts/gravewright_runner.py) cuida da configuração, bloqueio dos dados, migrações, coleta de estáticos, verificação de prontidão, abertura do navegador e ciclo de vida do servidor. Aceita `--data-dir PATH`, `--port NUMBER`, `--no-browser` e `--check` para execuções controladas de desenvolvimento com ambiente já preparado. `--port` substitui a porta daquela execução sem editar a configuração salva; `--check` prepara e verifica a instalação, incluindo migrações e coleta de estáticos, e sai sem servir requisições. Não é uma verificação somente de leitura.

O `.bat` aceita as mesmas opções `--data-dir`, `--port`, `--no-browser` e `--check` quando também são necessárias detecção de ferramentas, instalação de dependências e preparação do frontend. Dê dois cliques para iniciar normalmente ou passe argumentos no CMD do Windows. Por exemplo, na raiz do código, prepare um diretório isolado de diagnóstico sem iniciar o servidor:

```bat
"Gravewright Runner.bat" --check --data-dir "%TEMP%\Gravewright Runner Check"
```

A pasta de dados do exemplo fica separada das campanhas normais e pode ser removida após a verificação. `--check` ainda prepara dependências e recursos gerados do frontend, além do banco; não é um comando somente de leitura. Adicione `--no-pause` em CI ou scripts para que falhas retornem um código de saída em vez de esperar uma tecla. Diagnósticos de download/instalação/build aparecem no console; o arquivo em lote não cria uma transcrição automaticamente. Diagnósticos da aplicação são gravados em `data\logs\runner.log`.

As configurações e entradas ASGI específicas são [`config/runner.py`](../../config/runner.py), [`config/runner_asgi.py`](../../config/runner_asgi.py) e [`config/runner_urls.py`](../../config/runner_urls.py). As entradas padrão do servidor mantêm a exigência de Redis com debug desativado. Siga [testes](testing.md) para validar antes de distribuir uma versão Windows, incluindo uma execução real no Windows; testes em outro sistema não verificam o shell, os atalhos nem o comportamento do console Windows.
