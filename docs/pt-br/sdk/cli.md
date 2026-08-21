# CLI `grave`

A CLI ajuda autores a criar, validar, instalar e diagnosticar pacotes SDK.

Ela também é a interface operacional para executar, fazer backup/restore,
inspecionar banco e canais, e manter a instalação.

Executar `grave` sem argumentos mostra um guia rápido e termina sem erro. Use
`grave --help` para a lista completa e `grave <comando> --help` para opções de
um comando. Erros de digitação sugerem o comando válido mais próximo. Para logs
sem estilo, use `grave --no-color <comando>`.

## Launchers e códigos de saída

Use `./grave` em Linux/macOS, `grave.bat` no Windows ou
`uv run python -m app.cli` como fallback. Os códigos são:

| Código | Significado |
|---:|---|
| `0` | sucesso |
| `1` | erro de validação/diagnóstico |
| `2` | uso inválido da CLI |
| `3` | operação recusada sem confirmação |
| `4` | dependência externa ou download indisponível |
| `5` | incompatibilidade de package |

Comandos com `--json` escrevem exatamente um documento JSON no stdout, sem
prompts, prosa ou ANSI. Falhas usam `ok: false`, `error_key` estável e o exit
code correspondente. JSON não implica consentimento: automações ainda precisam
fornecer `--yes` quando exigido. `grave doctor --ai` gera um prompt limitado a
partir dos mesmos findings e nunca edita arquivos.

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

Todos os seis kinds aceitam `new`, `--wizard`/`-i`, `--dry-run`, `--force`,
`--output-dir`, `--yes` e `--json`:

```bash
grave ruleset new --wizard
grave addon new -i
grave content new my-content --dry-run --json
grave assets new my-assets --output-dir data/packages --yes --json
```

O wizard é o fluxo guiado; flags são o fluxo reproduzível para automação.
Rulesets também possuem templates mantidos:

```bash
grave ruleset new --list-templates
grave ruleset new my-rpg --template blank --name "My RPG" --yes --json
```

Template e flags de intenção incompatíveis falham com
`scaffold.template_intent_conflict`; nenhuma intenção é descartada em silêncio.
Flags sem significado para um kind são rejeitadas. Scaffolds novos de ruleset e
content geram content packs v2 com `documentType`, `formatVersion: 2`,
`indexFields` e array `index`.

## Validação

```bash
grave channel show
grave channel set testing
grave channel set stable --target packages
grave package validate data/packages/my-package
```

`validate` examina diretório ainda não instalado: manifesto, schema,
capabilities, regras do kind, paths seguros e arquivos referenciados.

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

`grave package doctor` diagnostica um package instalado. `grave doctor`
diagnostica a instalação inteira, incluindo banco, todos os packages descobertos
e estado órfão.

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

## Lifecycle e canais

O lifecycle operacional é descobrir/validar → instalar → habilitar → ativar na
campanha → atualizar → desativar/desabilitar → remover. Rulesets são exclusivos,
libraries são dependências passivas e addon/theme/content/assets usam ativação
múltipla.

```bash
grave channel show --json
grave channel set dev --target core --yes --json
grave campaign package activate <campaign_id> my-package
grave campaign package deactivate <campaign_id> my-package
```

A CLI reconhece os três valores do protocolo (`stable`, `testing`, `dev`), mas
quem publica disponibilidade é o `marketplace.toml`. Portanto `channel set` pode
salvar um valor ainda não publicado; a consulta/update posterior falha de forma
segura, sem subir para canal mais arriscado.
