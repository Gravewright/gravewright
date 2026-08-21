# Distribuição opcional da interface Windows

Gravewright Core e Gravewright Windows UI são produtos separados. A instalação
padrão do Core fornece servidor, aplicação web e CLI de operação `grave`. Ela não
depende de PySide6 ou Qt e não carrega interface desktop nativa.

A Windows UI opcional é mantida e compilada no projeto separado
`gravewright-windows-ui`. Ela localiza uma instalação independente do Core e usa
somente a CLI pública `grave` e readiness HTTP local. Não importa módulos do Core,
não acessa o banco e não escreve diretamente no diretório de dados.

## ZIP Windows oficial do Core

O release recomendado do Core é baseado no código-fonte e contém o launcher
mínimo de console `Gravewright.exe` na raiz. Para gerar:

```powershell
uv run python scripts/build_windows_release.py
```

O launcher é definido por `packaging/windows-launcher.spec`. Ele congela somente
código da biblioteca padrão para bootstrap/orquestração, sem módulos do Core,
web, banco, Qt ou PySide6. O ZIP contém `Gravewright.exe`, `pyproject.toml`,
`uv.lock` e o código/assets exigidos por `uv sync --frozen`.

Na primeira execução ele encontra ou instala o `uv 0.9.11` verificado, prepara o
ambiente travado, delega configuração e Doctor aos comandos existentes e executa
`grave run --open`. `grave.spec` permanece como build alternativo de mantenedor
para uma CLI totalmente congelada; não é o launcher do ZIP de um clique.

## UI opcional

A Windows UI deve ser compilada e publicada independentemente a partir do seu
próprio repositório. Ela pode ficar ao lado de `Gravewright Core`, ser localizada
por `PATH` ou `GRAVEWRIGHT_COMMAND`, ou selecionada pelo usuário. Seu ciclo de
releases e futuro updater são independentes das atualizações do Core.

A UI preserva início/parada do servidor, readiness, abertura do navegador, logs,
Doctor, Backup, Restore e comandos de packages. O shutdown começa com um sinal
gracioso e só usa encerramento forçado como fallback após timeout.
