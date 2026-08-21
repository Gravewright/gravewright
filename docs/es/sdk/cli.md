# CLI `grave`

`grave` es la interfaz operativa del SDK 1 RC 1. Los seis kinds públicos son
`ruleset`, `addon`, `library`, `content`, `theme` y `assets`.

## Scaffold y wizard

Cada kind admite `new`. Los flags comunes son `--name`, `--version`,
`--output-dir`, `--yes`, `--force`, `--dry-run`, `--wizard` (`-i`) y `--json`.
El wizard guía una sesión interactiva; `--yes --json` es la forma recomendada
para automatización. `ruleset` también admite `--template` y
`--list-templates`. Un template incompatible con selecciones explícitas falla
con `scaffold.template_intent_conflict`; los flags no soportados no se ignoran.

```bash
grave ruleset new --wizard
grave addon new my-addon --yes --json
grave content new my-content --dry-run --json
grave ruleset new --list-templates
grave ruleset new my-rpg --template blank --yes --json
```

El scaffold de `content` emite content packs v2 con `formatVersion: 2`,
`documentType`, `indexFields` y un archivo con `index`.

## Validación y diagnóstico

```bash
grave package validate ruta/del/package --json
grave package doctor package-id --json
grave doctor --json
grave doctor --ai
```

`validate` verifica un árbol de authoring. Package Doctor inspecciona un package
instalado. `grave doctor` inspecciona la instalación completa y admite
`--packages-dir`, `--skip-db`, `--strict` y `--verbose`. `--json` y `--ai` son
mutuamente excluyentes; Package Doctor solo ofrece JSON.

Los modos JSON emiten un único documento y conservan `error_key` y clase de
salida estables. JSON no confirma acciones destructivas automáticamente.

## Lifecycle y canales

`grave package` ofrece `list`, `install`, `enable`, `disable`, `remove`,
`update`, `doctor` y `validate`. Una actualización local relee los metadatos del
disco; `grave package update ID --remote --json` usa el instalador del
Marketplace.

```bash
grave channel set testing --target all --yes --json
```

La CLI acepta los valores de protocolo `stable`, `testing` y `dev`. Esto no
publica un canal: su disponibilidad se resuelve contra el registro remoto y un
canal ausente falla de forma segura, sin fallback ascendente.
