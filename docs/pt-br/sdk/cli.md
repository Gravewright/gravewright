# CLI `grave`

A CLI ajuda autores a criar, validar, instalar e diagnosticar pacotes SDK.

Executar `grave` sem argumentos mostra um guia rápido e termina sem erro. Use
`grave --help` para a lista completa e `grave <comando> --help` para opções de
um comando. Erros de digitação sugerem o comando válido mais próximo. Para logs
sem estilo, use `grave --no-color <comando>`.

## Telemetria local forte

```bash
grave run --diagnostics
grave run --diagnostics --diagnostics-file ./diagnostics/mesa.jsonl
```

`--diagnostics` grava eventos estruturados já sanitizados e snapshots completos
das métricas a cada 30 segundos. O arquivo JSONL gira ao atingir 10 MiB e mantém
cinco backups. O padrão é `data/diagnostics/gravewright.jsonl`. Nada é enviado
pela rede; antes de iniciar, a CLI informa destino e retenção.
O arquivo resultante é próprio para anexar a uma issue: identificadores viram
pseudônimos estáveis somente naquela execução, e caminhos, hosts, origins e URLs
são ocultados. Ainda assim, revise o anexo antes de publicar.

## Scaffold

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"
```

## Validação

```bash
grave channel show
grave channel set testing
grave channel set stable --target packages
grave package validate data/packages/my-package
```

Valida manifesto, schema, capabilities, paths, entrypoints e coerência básica do pacote.

## Instalação e ativação

```bash
grave package install my-package --yes --enable
```

Use em ambiente local para testar o fluxo completo do usuário.

## Diagnóstico

```bash
grave package doctor my-package
grave doctor --json
grave doctor --ai
grave doctor --strict
```

Use para encontrar dependências ausentes, conflitos, capabilities inconsistentes, arquivos faltando e problemas de ativação.

`--strict` faz warnings também produzirem falha. As saídas humana, JSON e para
IA partem da mesma coleção de findings; com `--json`, nenhum texto humano é
misturado ao stdout.

## Atualização

```bash
grave package update my-package
grave package update my-package --remote --json
grave package update all --remote --json
```

Sem `--remote`, a CLI atualiza o snapshot instalado a partir do disco. Com
`--remote`, ela delega ao mesmo instalador canônico do Marketplace usado pela
interface, incluindo checksum, compatibilidade, dependências, rollback e
diagnóstico de recovery.

## Workflow recomendado

```bash
grave package validate data/packages/my-package
grave package install my-package --yes --enable
grave package doctor my-package
```

Rode esse ciclo antes de publicar qualquer release.
