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

| Ferramenta | Ferramenta gerenciada dentro da instalação |
| --- | --- |
| uv | uv 0.12.13 com SHA-256 verificado |
| Python | CPython 3.14 gerenciado, GIL padrão, para a plataforma nativa |
| Node.js/npm | Node.js 24.19.0/npm verificado |

Não exige administrador, mudanças permanentes no PATH, Docker ou servidor Redis. Ferramentas verificadas são reutilizadas dentro desta instalação, sem depender do perfil global do usuário. Dependências Python usam ambiente isolado e `uv sync --locked --no-dev`. O frontend usa `npm ci --include=dev --include=optional` quando necessário e depois `npm run build`; hashes permitem reaproveitar assets inalterados. A instalação atualiza assets gerados e o `node_modules` ignorado na pasta do código.

## Configuração e dados pessoais

O `.env` do projeto inclui todas as configurações e seções do `.env.example`. Opções ausentes são preenchidas automaticamente, preservando os valores salvos, a chave privada e as opções personalizadas.

O instalador pergunta nome da mesa, idioma (`en` ou `pt-BR`), porta local, pasta de módulos, códigos de convite, snapshots, exportação de campanhas e se deseja liberar túneis. A opção de túnel é apenas sim/não; não pede URL. Salva as respostas juntas e preserva a chave secreta e outras configurações. Nas próximas instalações, as respostas salvas aparecem como padrão. Caminhos relativos de banco, mídias e módulos partem da raiz do projeto.

Escolher `pt-BR` instala e ativa globalmente o [Translator](https://github.com/Gravewright/translator) oficial assinado. A ausência de tradução ou uma falha de verificação impede a conclusão da instalação; o pacote instalado e verificado é reutilizado offline. As chaves oficiais são adicionadas sem remover as chaves confiáveis existentes.

Antes de preparar o Translator, o instalador configura automaticamente o Marketplace oficial do Gravewright quando não há catálogo configurado, incluindo instalações que recusaram essa opção anteriormente. Ele verifica as chaves públicas oficiais e salva as configurações sem uma pergunta adicional. Catálogos personalizados são preservados; arquivos de chaves personalizados continuam intactos, com eventuais chaves oficiais adicionadas a uma cópia gerenciada. Uma configuração oficial completa e verificada é reutilizada offline nas próximas instalações. O modo `--check` não configura o Marketplace.

O banco e as mídias usam `GRAVEWRIGHT_DATABASE` e `GRAVEWRIGHT_MEDIA_ROOT` do `.env` do projeto, com padrões `data/gravewright.sqlite3` e `data/media` dentro do projeto. Estado do Runner, assets coletados, ferramentas gerenciadas e caches também ficam **dentro da pasta descompactada do projeto**:

| Caminho | Finalidade |
| --- | --- |
| `data/compendiums/` | Conteúdo local |
| `data/staticfiles/` | Assets públicos coletados |
| `data/logs/runner.log` | Diagnósticos de inicialização e execução |
| `data/runner.lock` | Impede uso simultâneo dos mesmos dados |
| `data/marketplace/<hash-da-pasta>/trusted-keys.json` | Chaves públicas oficiais e de outros publicadores preservadas, quando necessário |
| `data/runner/` | Ferramentas, caches e ambientes por pasta do código |
| `data/runner/prepare.lock` | Impede preparação simultânea de dependências |
| `data/runner/frontend/<hash-da-pasta>/state.json` | Estado da preparação do frontend |

O instalador cria e lê o `.env` na raiz do projeto, ao lado de `Install Windows.bat`. Se não existir, gera uma configuração completa a partir de `.env.example`, com uma nova chave privada. Arquivos de configuração na pasta de dados do usuário nunca são importados. Os ambientes Python são gerenciados separadamente. Os padrões vêm de `.env.example` e depois do `.env` do projeto; os limites locais de rede e segurança são impostos pelo runner. A chave é gerada automaticamente. Pare o servidor antes de reconfigurar ou copiar o `.env` do projeto e toda a pasta pessoal `data` para backup. Preserve chave, banco e mídia juntos. Faça backup antes de instalar uma nova versão: migrações podem impedir o uso de versões anteriores.

## Limite da execução local

O runner serve HTTP apenas em `127.0.0.1`, com um processo servidor e Channels em memória. Debug Django permanece desligado; verificações de origem, host, sessão, CSRF e permissões continuam ativas. Uploads privados usam rotas protegidas. Use `GRAVEWRIGHT_ALLOW_TUNNELS=true` para aceitar qualquer hostname de túnel por um agente local, sem cadastrar URL nem restringir o provedor. Origens HTTP e HTTPS acompanham o Host de cada requisição; WebSockets e CSRF continuam exigindo uma origem correspondente. O servidor continua escutando em `127.0.0.1:<porta>` e confia em cabeçalhos de esquema apenas de agentes locais. Mudar a URL do túnel não exige alterar a configuração. Use `false` para restringir o acesso ao host local. O Runner não instala nem inicia o programa de túnel. Para hospedagem direta em rede local ou internet, siga [implantação](deployment.md).

## Diagnóstico e validação

Para instalar com os padrões, sem perguntas nem inicialização do servidor:

```bat
"Install Windows.bat" --check --no-pause --data-dir "data\check"
```

Isso instala dependências, prepara assets/banco e gera um runner apontando para a pasta escolhida. Não é somente leitura. Uma instalação normal posterior faz as perguntas. `--data-dir` escolhe a pasta persistida; `--port` altera apenas a verificação da instalação, não a porta salva.

O runner gerado aceita `--no-browser`, `--no-pause`, `--data-dir`, `--port` e `--check`. O `--check` do runner verifica aplicação/banco sem instalar ferramentas nem preparar frontend; pode aplicar migrações e coletar assets. `--port` vale apenas naquela execução. Para alterar valores salvos, abra o instalador.

Em falhas de download, confira o console e acesso ao GitHub, nodejs.org e fontes de pacotes. Não ignore erros de integridade. Se um launcher antigo informar `No download found` para `cpython-3.14+gil-windows-x86_64-none`, use o projeto atualizado completo. Se faltarem arquivos ou o Python preparado, execute o instalador novamente. Se a porta estiver ocupada, pare o outro servidor ou altere a porta salva. Para falhas da aplicação, consulte `data/logs/runner.log` e remova informações privadas antes de compartilhar.

O instalador prepara ferramentas e dependências. [create_runner.py](../../scripts/windows/create_runner.py) gera o BAT de execução pelo [modelo](../../scripts/windows/runner.bat); [create_shortcut.py](../../scripts/windows/create_shortcut.py) cria o atalho opcional. [gravewright_runner.py](../../scripts/gravewright_runner.py) gerencia configurações pessoais, bloqueios e ciclo do servidor. Veja [testes](testing.md): o cenário nativo Windows cobre instalação, reconfiguração, download privado do Python, reaproveitamento offline e runner gerado. A validação de navegador é separada quando se usa `--skip-browser`.

## Atualização e rollback

A atualização substitui os arquivos na própria pasta do projeto, incluindo o instalador, e regenera o runner com o novo ambiente Python. Em Administração → Atualizações, **Manter cópia .old para rollback** controla se o código anterior e o snapshot correspondente dos dados serão preservados após o sucesso. A recuperação temporária durante a instalação é sempre mantida. Veja [implantação](deployment.md) para restaurar uma cópia.

O runner usa uma cópia imutável do inicializador em `data/.runner-launchers` durante a execução, permitindo substituir o `.bat` do projeto com segurança enquanto a atualização acontece. Preserve essa pasta junto dos dados e backups.
