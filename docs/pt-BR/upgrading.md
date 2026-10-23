# Atualização e recuperação

[Documentação](../README.pt-BR.md) · [English](../en/upgrading.md)

Este guia cobre a release **Gravewright 0.3.2 — Alpha**. Seu artefato de
código-fonte é `Gravewright-0.3.2-django.zip`, com o arquivo correspondente
`Gravewright-0.3.2-django.zip.sha256`. Consulte as [notas da release](../releases/0.3.2.md)
para os recursos e [implantação](deployment.md) para servidores públicos.

## Antes de atualizar

1. Registre a versão em execução e os caminhos configurados. Interrompa escritas
   da mesa e do gestor de campanha; depois pare o Runner e todos os processos
   ASGI/de manutenção que usam a instalação. Fechar apenas o navegador não para
   o servidor.
2. Faça backup conjunto de `.env`, banco configurado e mídias privadas. Inclua
   pastas externas de módulos/conteúdo, `extensions/` local, chaves de confiança e
   estado de recuperação do Runner/atualizador. Por padrão, `.env` e `extensions/`
   ficam na raiz da instalação; banco, mídias e estado de execução/recuperação
   ficam em `data/`. Proteja esse backup: contém contas, segredos de mestre,
   fichas privadas e anexos retidos de documentos excluídos.
3. Guarde o código da versão correspondente e os lock files com o backup. Teste
   a recuperação em outra pasta, com configuração de banco/mídia separada, antes
   de usar uma campanha importante como primeira verificação da atualização.
4. Use o pacote completo e seu SHA-256 correspondente. Nunca reutilize o
   checksum de outro ZIP nem substitua somente o script de entrada do instalador.

Não redirecione padrões para um perfil compartilhado do sistema operacional
para reparar uma instalação. Uma pasta sem permissão de escrita deve informar o
caminho que falhou. Caminhos explicitamente configurados pelo operador continuam
suportados e também precisam de backup.

## Formas de atualização

Após concluir o backup com a instância parada, reinicie o Runner **atual** da
instalação gerenciada compatível e use
**Administração → Atualizações → Instalar atualização**. Mantenha **Manter cópia
.old para rollback** ativo quando desejar recuperação. Deixe esse Runner aberto
enquanto o supervisor baixa, verifica, prepara dependências, copia dados, migra,
substitui arquivos e reinicia. Os navegadores reconectados recarregam após a
confirmação da versão de destino. Não execute um segundo servidor contra esse
banco durante o processo.

Para atualização manual, pare a instalação, preserve as configurações e os dados
listados acima, substitua os arquivos da aplicação pelo pacote completo, execute
o instalador da plataforma e use o Runner regenerado:

| Plataforma | Preparar a atualização | Iniciar |
| --- | --- | --- |
| Windows | `Install Windows.bat` | `Gravewright Runner.bat` |
| Linux | `bash "./Install Linux.sh"` | `bash "./Gravewright Runner.sh"` |
| macOS | `bash "./Install macOS.command"` | `bash "./Gravewright Runner.command"` |

Os instaladores preservam o `.env` do projeto e preparam as dependências fixadas
de Python/frontend. Aplicam migrações antes da inicialização. Repita a instalação
ao mover o código, pois inicializadores e ambientes referenciam sua localização.
Não copie um Runner gerado de outra máquina ou instalação.

Implantações do código-fonte iniciadas diretamente pelo Daphne exigem atualização
pelo operador. Configure abaixo o armazenamento local das ferramentas, prepare
o frontend conforme o [guia de frontend](frontend.md) e execute na raiz da
instalação com as configurações pretendidas:

```bash
uv sync --locked --no-dev
uv run --locked --no-dev python manage.py migrate --plan
uv run --locked --no-dev python manage.py migrate --noinput
uv run --locked --no-dev python manage.py collectstatic --noinput
uv run --locked --no-dev python manage.py check
```

Mantenha `--extra vips` na sincronização de dependências se essa instalação usa
o gerador opcional libvips. Após os comandos, reinicie o serviço com seu perfil
de implantação existente. `check --deploy` e verificação pública de HTTPS/WSS
também se aplicam a servidores públicos.

### Numeração e pacotes da mesma versão

O identificador da release é **0.3.2**, depois da **0.3.1**. O atualizador compara
números de versão, então uma instalação compatível na 0.3.1 pode descobrir a
0.3.2 pelo repositório de releases configurado. O projeto permanece em Alpha e o contrato do SDK do host
continua igual; APIs opcionais continuam exigindo verificação de capacidade.
Notas históricas preservam seus identificadores.

Uma instalação que informa a versão anterior numerada incorretamente como
**3.0.1** considera a 0.3.2 uma versão inferior e não a recebe pela descoberta
automática. Faça backup do código, banco e mídias correspondentes, depois siga
a instalação manual com o pacote completo da 0.3.2 e seu checksum. Isso corrige
a numeração da release; não tente fazer downgrade do banco apenas sobrepondo
código antigo. Se precisar recuperar a instalação, restaure juntos código,
banco e mídias correspondentes.

Um host que já informa **0.3.2** não recebe uma reedição da 0.3.2 pela descoberta
de versões. Siga a atualização manual com o ZIP substituto e seu próprio
checksum. Não faça downgrade de um banco apenas sobrepondo código antigo;
recuperação exige código, banco e mídias correspondentes.

## Migrações de banco da 0.3.2

Em comparação com a 0.3.1, esta release acrescenta sete migrações:

| Migração | Capacidade armazenada |
| --- | --- |
| [table/0003_progress_clock.py](../../gravewright/table/migrations/0003_progress_clock.py) | Relógios de progresso e recibos de repetição |
| [table/0004_progress_clue.py](../../gravewright/table/migrations/0004_progress_clue.py) | Pistas por etapas e seus recibos separados |
| [table/0005_mind_maps.py](../../gravewright/table/migrations/0005_mind_maps.py) | Grafos de mapas mentais, visibilidade, editores selecionados e recibos separados |
| [table/0006_clock_description.py](../../gravewright/table/migrations/0006_clock_description.py) | Descrições autorais de relógios, vazias nos relógios existentes |
| [campaigns/0005_preparation.py](../../gravewright/campaigns/migrations/0005_preparation.py) | Painéis pessoais de mestre, planos de sessão, eventos e recibos de preparação |
| [journals/0004_revision.py](../../gravewright/journals/migrations/0004_revision.py) | Revisões de diários, lixeira e metadados de anexos retidos |
| [pdf_system/0001_initial.py](../../gravewright/pdf_system/migrations/0001_initial.py) | Modelos reutilizáveis de mapeamento PDF, seus pacotes e revisões |

Execute o comando normal de migração em vez de aplicar somente esses arquivos:
o Django ordena as dependências e inclui migrações anteriores pendentes. As novas
tabelas não fabricam histórico de alterações anteriores ao recurso. Preserve o
backup prévio; não suponha que código antigo possa abrir o banco migrado com
segurança.

## Pacotes de campanha e backups da instância

| Material de recuperação | O que preserva |
| --- | --- |
| Exportação completa ou cópia de campanha | Conteúdo selecionado, relógios/pistas, mapas mentais, preparação, cronologia, metadados portáveis do painel e histórico/lixeira; referências tipadas são remapeadas |
| Snapshot de campanha | Dados de recuperação da campanha, incluindo preparação/histórico; restauração de painéis se aplica aos vínculos atuais de mestre |
| Backup completo e coordenado da instância | Banco, arquivos privados, contas, permissões, estado do host/módulos e automações pendentes, junto da configuração e do código correspondente |

A seleção `preparation` controla planos de sessão, eventos e metadados do painel.
A seleção `journals` controla histórico/lixeira. Importações portáveis não
recriam usuários de origem nem vínculos na campanha; permissões individuais são
removidas. Um snapshot completo pode preservar permissões, mas não transforma
um usuário ausente em membro atual. A importação portável atribui metadados
adequados do painel ao mestre importador; mesclagem preserva um painel existente.

Documentos na lixeira podem reter anexos físicos. Exportações completas, cópias e
snapshots incluem esses arquivos; uma exportação sem arquivos é rejeitada quando
eles são necessários para preservar a lixeira. Não exclua manualmente arquivos
retidos das mídias. A restauração valida disponibilidade dos arquivos,
propriedade dos recursos, revisões e pré-requisitos das missões antes de confirmar.

Pacotes antigos continuam importáveis. Quando não possuem metadados de
preparação, restaurá-los preserva preparação/histórico existentes, em vez de
apagar dados que nunca estiveram no pacote. Pacotes de campanha continuam sem
incluir continuações Blueprint pendentes e recibos de comandos; um backup
completo do banco os inclui. Consulte [gestão de campanha](campaign-management.md)
para as regras detalhadas de seleção.

## Verificação e recuperação

Depois de iniciar, confira se a Administração informa **0.3.2**. Entre como mestre
e jogador em uma campanha sintética ou copiada. Verifique gestor e mesa, PDF
mapeado, upload de mapa/importação Universal VTT, relógio e pista cujo conteúdo
continua oculto até completar. Confira visibilidade de diários privados,
gravação/reabertura de sessão, restauração de histórico/lixeira e um ciclo
representativo de backup/restauração. Confira um [mapa mental](mindmaps.md) com
um jogador editor: vínculos sem acesso ficam indisponíveis, edições comuns
preservam esses vínculos e grafos copiados apontam aos recursos copiados da
campanha. O [guia de testes](testing.md) descreve cenários automatizados isolados.

Se a instalação gerenciada falhar, preserve transações, backups e logs; o
supervisor tenta recuperar e trata transações interrompidas na próxima
inicialização. Guarde juntos `.env`, `data/`, ambientes e cópias imutáveis dos
inicializadores. Não apague pastas de recuperação para suprimir uma falha.

Uma pasta `.old` retida contém o código anterior e os dados correspondentes em
`.gravewright-rollback`. Seu nome vem da pasta de instalação, com sufixo único
em caso de colisão. Padrões do Runner a colocam em `data/updates/retained/`; a
execução normal de `main.py`, em
`data/updates/<installation-hash>/retained/`. Com todos os servidores parados,
execute [rollback_update.py](../../scripts/rollback_update.py) com o Python da
instalação e o caminho retido real, conforme [implantação](deployment.md).
Isso retorna os dados ao momento do backup e descarta alterações posteriores.

Ao inspecionar um banco completo restaurado, use
`GRAVEWRIGHT_AUTOMATION_WORKER_ENABLED=false` antes de iniciar se esperas Blueprint
vencidas precisarem permanecer pausadas durante a inspeção. Reative somente
quando a cópia de recuperação tiver de executar sua automação. Um pacote apenas
da campanha não restaura essa fila pendente.

## Armazenamento local das ferramentas

Instaladores nativos, Runners gerados e `main.py` configuram automaticamente
caches e temporários em `data/runner/`. Comandos manuais de uv/npm precisam do
mesmo ambiente antes de executar. Na raiz gravável da instalação, use um terminal
novo e mantenha essas variáveis limitadas a esse terminal.

No Bash de Linux/macOS:

```bash
export GRAVEWRIGHT_RUNNER_ROOT="$PWD/data/runner"
mkdir -p "$GRAVEWRIGHT_RUNNER_ROOT/tmp"
export UV_CACHE_DIR="$GRAVEWRIGHT_RUNNER_ROOT/cache"
export UV_PYTHON_INSTALL_DIR="$GRAVEWRIGHT_RUNNER_ROOT/python"
export UV_PYTHON_BIN_DIR="$GRAVEWRIGHT_RUNNER_ROOT/python-bin"
export UV_PYTHON_INSTALL_BIN=0 UV_PYTHON_INSTALL_REGISTRY=0 UV_PYTHON_NO_REGISTRY=1
export npm_config_cache="$GRAVEWRIGHT_RUNNER_ROOT/npm-cache"
export CARGO_HOME="$GRAVEWRIGHT_RUNNER_ROOT/cargo"
export RUSTUP_HOME="$GRAVEWRIGHT_RUNNER_ROOT/rustup"
export XDG_CACHE_HOME="$GRAVEWRIGHT_RUNNER_ROOT/xdg-cache"
export XDG_DATA_HOME="$GRAVEWRIGHT_RUNNER_ROOT/xdg-data"
export XDG_CONFIG_HOME="$GRAVEWRIGHT_RUNNER_ROOT/xdg-config"
export TEMP="$GRAVEWRIGHT_RUNNER_ROOT/tmp" TMP="$GRAVEWRIGHT_RUNNER_ROOT/tmp" TMPDIR="$GRAVEWRIGHT_RUNNER_ROOT/tmp"
```

No PowerShell do Windows:

```powershell
$env:GRAVEWRIGHT_RUNNER_ROOT = Join-Path (Get-Location).Path 'data/runner'
$gravewrightTools = $env:GRAVEWRIGHT_RUNNER_ROOT
New-Item -ItemType Directory -Force -Path (Join-Path $gravewrightTools 'tmp') | Out-Null
$gravewrightPaths = @{
    UV_CACHE_DIR = 'cache'; UV_PYTHON_INSTALL_DIR = 'python'; UV_PYTHON_BIN_DIR = 'python-bin'
    npm_config_cache = 'npm-cache'; CARGO_HOME = 'cargo'; RUSTUP_HOME = 'rustup'
    XDG_CACHE_HOME = 'xdg-cache'; XDG_DATA_HOME = 'xdg-data'; XDG_CONFIG_HOME = 'xdg-config'
    TEMP = 'tmp'; TMP = 'tmp'; TMPDIR = 'tmp'; LOCALAPPDATA = 'profile/local'; APPDATA = 'profile/roaming'
}
foreach ($entry in $gravewrightPaths.GetEnumerator()) {
    $gravewrightPath = Join-Path $gravewrightTools $entry.Value
    New-Item -ItemType Directory -Force -Path $gravewrightPath | Out-Null
    [Environment]::SetEnvironmentVariable($entry.Key, $gravewrightPath, 'Process')
}
$env:UV_PYTHON_INSTALL_BIN = '0'
$env:UV_PYTHON_INSTALL_REGISTRY = '0'
$env:UV_PYTHON_NO_REGISTRY = '1'
```

Esses comandos não alteram HOME nem a configuração permanente do sistema. Uma
raiz de ferramentas explícita do operador pode substituir `data/runner/`; use
caminho absoluto ou relativo a esta instalação, nunca o estado ativo de outra.
Para duas instalações independentes, prepare cada uma em seu próprio terminal
e raiz.
