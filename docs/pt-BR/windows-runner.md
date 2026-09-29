# Instalação Windows e Gravewright Runner

[Documentação](../README.pt-BR.md) · [English](../en/windows-runner.md)

## Instalar, configurar e executar

1. Extraia o ZIP completo para uma pasta local gravável. Use Windows 10 versão 1803 ou posterior, ou Windows 11, em x64/AMD64, com `curl.exe`, `tar.exe`, `certutil.exe` e navegador com WebGL. Este instalador não suporta ARM nem Windows de 32 bits.
2. Abra **`Install Windows.bat`**. Ele detecta ferramentas compatíveis, baixa as ausentes, instala dependências fixadas e compila o frontend quando necessário. Downloads ausentes exigem internet.
3. Responda às perguntas. Enter mantém o valor exibido; Ctrl+C cancela sem salvar as respostas. O instalador prepara o banco e gera **`Gravewright Runner.bat`** na mesma pasta, além de um atalho opcional com ícone.
4. Abra **`Gravewright Runner.bat`** ou seu atalho para iniciar a aplicação. Ele usa o Python preparado e as configurações salvas, sem baixar ferramentas, instalar dependências, compilar o frontend ou fazer perguntas. O endereço padrão é **http://127.0.0.1:3000**.
5. Crie a primeira conta proprietária no navegador. Mantenha o console aberto; pressione **Ctrl+C** para encerrar. Fechar o navegador não para o servidor.

O instalador termina sem iniciar o servidor. Abra-o novamente para mudar configurações, reparar dependências ausentes ou preparar uma nova versão do projeto. Ferramentas compatíveis e assets inalterados são reaproveitados. O runner é gerado para esta instalação Windows; não o distribua para outro computador. Após mover ou substituir o projeto, execute o instalador na nova pasta para regenerar runner e atalho.

## Ferramentas e preparação

| Ferramenta | Instalação compatível | Alternativa privada |
| --- | --- | --- |
| uv | Versão 0.12.0 ou posterior | uv 0.12.13 com integridade verificada |
| Python | CPython 3.14, Windows x64, GIL padrão | `cpython-3.14-windows-x86_64-none`, validado após a descoberta |
| Node.js/npm | Node.js 22 ou 24 LTS estável x64, npm 10 ou posterior | Node.js 24.19.0 verificado, com npm |

Não exige administrador, mudanças permanentes no PATH, Docker ou servidor Redis. Mantenha instaladas as ferramentas reaproveitadas. Dependências Python usam ambiente isolado e `uv sync --locked --no-dev`. O frontend usa `npm ci --include=dev --include=optional` quando necessário e depois `npm run build`; hashes permitem reaproveitar assets inalterados. A instalação atualiza assets gerados e o `node_modules` ignorado na pasta do código.

## Configuração e dados pessoais

O instalador pergunta nome da mesa, idioma (`en` ou `pt-BR`), porta local, pasta de módulos, códigos de convite, snapshots e exportação de campanhas. Salva as respostas juntas e preserva a chave secreta e outras configurações. Nas próximas instalações, as respostas salvas aparecem como padrão. Caminhos relativos de módulos partem da pasta de dados pessoal.

Ele também oferece o Marketplace padrão do Gravewright uma vez. Aceitar baixa as chaves oficiais, confere o SHA-256 e salva as configurações do catálogo. Recusar registra a escolha; o proprietário ainda pode instalar em Configurações → Marketplace. Apagar `data/.default-marketplace-choice` permite que o instalador ofereça novamente.

Os arquivos pessoais ficam, por padrão, em **`%LOCALAPPDATA%\Gravewright`**:

| Caminho | Finalidade |
| --- | --- |
| `data/.env` | Chave privada e configurações |
| `data/gravewright.sqlite3` | Contas e campanhas |
| `data/media/`, `data/compendiums/` | Arquivos privados e conteúdo local |
| `data/staticfiles/` | Assets públicos coletados |
| `data/logs/runner.log` | Diagnósticos de inicialização e execução |
| `data/runner.lock` | Impede uso simultâneo dos mesmos dados |
| `runner/` | Ferramentas, caches e ambientes por pasta do código |
| `runner/prepare.lock` | Impede preparação simultânea de dependências |
| `runner/frontend/<hash-da-pasta>/state.json` | Estado da preparação do frontend |

O `.env`, `.venv` e banco de desenvolvimento do código-fonte são separados. Os padrões vêm de `.env.example` e depois do `.env` pessoal; os limites locais de rede, segurança e armazenamento são impostos pelo runner. A chave é gerada automaticamente. Pare o servidor antes de reconfigurar ou copiar toda a pasta pessoal `data` para backup. Preserve chave, banco e mídia juntos. Faça backup antes de instalar uma nova versão: migrações podem impedir o uso de versões anteriores.

## Limite da execução local

O runner serve HTTP apenas em `127.0.0.1`, com um processo servidor e Channels em memória. Debug Django permanece desligado; verificações de origem, host, sessão, CSRF e permissões continuam ativas. Uploads privados usam rotas protegidas. Para rede local ou internet, siga [implantação](deployment.md) com o perfil ASGI padrão. Não exponha o runner local por túnel ou proxy reverso público.

## Diagnóstico e validação

Para instalar com os padrões, sem perguntas nem inicialização do servidor:

```bat
"Install Windows.bat" --check --no-pause --data-dir "%TEMP%\Gravewright Install Check"
```

Isso instala dependências, prepara assets/banco e gera um runner apontando para a pasta escolhida. Não é somente leitura. Uma instalação normal posterior faz as perguntas. `--data-dir` escolhe a pasta persistida; `--port` altera apenas a verificação da instalação, não a porta salva.

O runner gerado aceita `--no-browser`, `--no-pause`, `--data-dir`, `--port` e `--check`. O `--check` do runner verifica aplicação/banco sem instalar ferramentas nem preparar frontend; pode aplicar migrações e coletar assets. `--port` vale apenas naquela execução. Para alterar valores salvos, abra o instalador.

Em falhas de download, confira o console e acesso ao GitHub, nodejs.org e fontes de pacotes. Não ignore erros de integridade. Se um launcher antigo informar `No download found` para `cpython-3.14+gil-windows-x86_64-none`, use o projeto atualizado completo. Se faltarem arquivos ou o Python preparado, execute o instalador novamente. Se a porta estiver ocupada, pare o outro servidor ou altere a porta salva. Para falhas da aplicação, consulte `data/logs/runner.log` e remova informações privadas antes de compartilhar.

O instalador prepara ferramentas e dependências. [create_runner.py](../../scripts/windows/create_runner.py) gera o BAT de execução pelo [modelo](../../scripts/windows/runner.bat); [create_shortcut.py](../../scripts/windows/create_shortcut.py) cria o atalho opcional. [gravewright_runner.py](../../scripts/gravewright_runner.py) gerencia configurações pessoais, bloqueios e ciclo do servidor. Veja [testes](testing.md): o cenário nativo Windows cobre instalação, reconfiguração, download privado do Python, reaproveitamento offline e runner gerado. A validação de navegador é separada quando se usa `--skip-browser`.

## Atualização e rollback

A atualização substitui os arquivos na própria pasta do projeto, incluindo o instalador, e regenera o runner com o novo ambiente Python. Em Administração → Atualizações, **Manter cópia .old para rollback** controla se o código anterior e o snapshot correspondente dos dados serão preservados após o sucesso. A recuperação temporária durante a instalação é sempre mantida. Veja [implantação](deployment.md) para restaurar uma cópia.

O runner usa uma cópia imutável do inicializador em `data/.runner-launchers` durante a execução, permitindo substituir o `.bat` do projeto com segurança enquanto a atualização acontece. Preserve essa pasta junto dos dados e backups.
