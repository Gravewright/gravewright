# Estado Atual da SDK — Baseline da Fase 0

> Snapshot da SDK do Gravewright como existe no início do sprint de
> estabilidade. Este documento é descritivo: registra *o que é*, não *o que
> deveria ser*. O plano (`gravewright_sdk_stability_plan.md`) define o alvo. Onde
> o comportamento atual diverge do alvo, este documento marca como **DRIFT** para
> que as fases seguintes tenham um ponto de partida preciso.

Resultado do baseline de testes: `pytest tests/unit -k sdk` → **103 passed**
(793 deselected).

## 1. Kinds de package

Definidos em `app/engine/sdk/package_manifest.py` (`PackageKind`):

| kind | valor |
|---|---|
| Ruleset | `ruleset` |
| Addon | `addon` |
| Library | `library` |
| Content | `content` |
| Theme | `theme` |
| Assets | `assets` |

Todos os seis kinds que o plano exige já existem.

## 2. Status de package

Definidos em `app/engine/sdk/package_install_service.py`:

`available`, `installed`, `enabled`, `disabled`, `incompatible`, `error`.

Status persistidos (`_PERSISTED`): `installed`, `enabled`, `disabled`.

A ativação por campanha é rastreada separadamente em `campaign_packages.status`
(`active` / outros) e no slot exclusivo de ruleset (`campaigns.active_system_id`).

## 3. Capabilities (backend vs frontend)

Hoje existem duas fontes independentes — **ainda não há arquivo canônico** (alvo
da Fase 2: `app/engine/sdk/capabilities.json`).

### Backend — `KNOWN_CAPABILITIES` (`package_manifest_validator.py`)

```
actors.register, items.register, sheets.declarative, sheets.hooks,
sheets.components, rules.declarative, rules.extends, dice.roll, rolls.intent,
combat.config, combat.hooks, tokens.mappings, tokens.extends, scene.tools,
scene.overlays, chat.cards, content.packs, settings, locales,
assets.ui, assets.styles, assets.scripts, assets.pack, assets.images,
assets.audio, assets.maps, assets.icons, hooks.client, commands.register
```

### Backend — `FORBIDDEN_CAPABILITIES`

```
backend.execute, database.raw, filesystem.raw, network.raw, permissions.override
```

Idêntico ao conjunto proibido do plano.

### Frontend — `CAPABILITIES` (`static/js/sdk/sdk-capabilities.js`)

```
actors.register, items.register, sheets.declarative, sheets.hooks,
sheets.components, rules.declarative, rules.extends, dice.roll, rolls.intent,
combat.config, combat.hooks, tokens.mappings, tokens.extends, scene.tools,
scene.overlays, chat.cards, content.packs, settings, locales,
assets.ui, assets.styles, assets.scripts, hooks.client, commands.register
```

### DRIFT — divergência no conjunto de capabilities

O backend conhece 5 capabilities que o frontend não conhece: `assets.pack`,
`assets.images`, `assets.audio`, `assets.maps`, `assets.icons`. São capabilities
*apenas de declaração* (empacotamento de assets) sem método frontend, por isso o
mapa JS as omite — mas nada garante que as duas listas fiquem sincronizadas. A
Fase 2 torna `capabilities.json` canônico e a Fase 11 adiciona um teste de sync.

### Mapa método frontend → capability (`CAPABILITY_REQUIREMENTS`)

Métodos com gate hoje: `hooks.on/once/emit`, `events.on/once`,
`commands.register`, `chat.send`, `ui.toast/openModal/closeModal`,
`settings.definitions/all/get/set`, `sheets.helpers/register`,
`combat.register/registerPanel/callHook/renderSlot`, `tokens.centerOn`,
`scene.activeCanvas/activeCameraForScene`, `tools.activeTool`,
`content.packs/pack`, `i18n.t`.

Membros públicos sem gate (intencionalmente): `version`, `package`, `kind`,
`capabilities.*`, `context()`, `game.*`.

## 4. Campos públicos do manifest

Parseados por `PackageManifest.from_dict`:

`schemaVersion` (deve ser `1`), `sdkVersion` (deve ser `"1"`), `kind`, `id`,
`name`, `version`, `description`, `authors`, `license`, `homepage`,
`repository`, `compatibility{minimum,verified,maximum}`, `capabilities[]`,
`activation{scope,mode}`, `entrypoints{<name>{styles,scripts}}`,
`provides{storage,actorTypes,itemTypes,rules,mappings,contentPacks,locales,assets,areaMarkers}`,
`settings[]`, `distribution{type,url,sha256}`, `dependencies[]`, `conflicts[]`,
`display{color}`.

Ainda não existem blocos `storage` (SQLite gerenciado) ou `interop` (Fase 7A /
Fase 12).

## 5. Modelo de erro — strings `error_key`

O validator/loader da SDK retornam **strings de error key**, não um `SdkError`
estruturado. As chaves carregam o prefixo `sdk.validation.*`:

```
not_object, schema_version, sdk_version, kind, id_required, id_invalid,
name_required, version_required, authors_invalid, license_invalid,
compatibility_required, capabilities_required, capability_forbidden,
capability_unknown, activation_required, activation_invalid,
ruleset_activation_mode, ruleset_storage_required, ruleset_actor_types_required,
addon_activation_mode, library_activation_mode, assets_activation_mode,
assets_invalid_assets, assets_image_extension (warn), assets_map_extension (warn),
assets_audio_extension (warn), setting_invalid, content_pack_invalid,
entrypoint_invalid, path_unsafe, dependency_invalid, conflict_invalid,
distribution_invalid, incompatible (warn), manifest_missing, manifest_unreadable,
file_missing
```

### DRIFT — contrato de erro

O plano (Fase 1) exige um contrato estruturado `SdkError` / `SdkActionResult` /
`DoctorFinding` com campos `code` estáveis sob os namespaces `sdk.manifest.*`,
`sdk.capabilities.*`, `sdk.storage.*` etc. As chaves atuais vivem sob um único
namespace `sdk.validation.*` e são strings simples.

### Uso de `error_key` na aplicação

`error_key` é amplamente usado na **camada de actions** (`app/actions/**`) como o
contrato estabelecido de UI/rotas — este é o uso de "borda" legítimo que o plano
permite. Os *serviços* da SDK ainda não emitem um contrato estruturado; retornam
as strings `sdk.validation.*` acima. A Fase 1 introduz `SdkError`/`DoctorFinding`
para serviços novos/refatorados e mantém `error_key` apenas como adapter de
borda.

## 6. `manifest_json` como autoridade

`manifest_json` (o snapshot completo do manifest) é armazenado em
`installed_packages` e lido de volta em vários pontos:

```
app/engine/content/content_pack_service.py
app/engine/rules/rules_registry.py
app/engine/sdk/package_asset_service.py
app/engine/sdk/package_install_service.py
app/engine/sdk/package_locale_service.py
app/engine/sheets/schema_service.py
app/engine/sheets/system_layout_service.py
app/persistence/repositories/installed_package_repository.py
app/persistence/tables.py
```

### DRIFT — autoridade disco vs DB

O plano (Princípio 7, Fase 6) exige que o **disco** seja a autoridade do
manifest; o snapshot do DB serve só para auditoria/hash. Vários serviços acima
leem `manifest_json` do DB como o manifest de trabalho. A Fase 6 audita e
reescreve esses pontos para carregar o manifest validado atual do disco.

## 7. Schema de `installed_packages`

Colunas (`app/persistence/tables.py`):

`id (pk)`, `kind`, `name`, `version`, `status`, `package_dir`, `manifest_json`,
`compatibility_status`, `validation_errors_json`, `package_sha256 (nullable)`,
`installed_by_user_id`, `installed_at`, `updated_at`, `enabled_at`, `disabled_at`.

### DRIFT — campos de integridade ausentes

`package_sha256` existe. O plano (Fase 6) exige adicionalmente `manifest_hash`,
`last_validated_at`, `last_validation_status`. Esses estão **ausentes** e devem
ser adicionados via migration Alembic.

## 8. Infraestrutura de migrations

Alembic (`migrations/versions/`). Revisão mais recente: `0007_sdk_packages.py`.
`alembic.ini` presente. O schema também é expresso em definições
`metadata`/`Table` do SQLAlchemy (`app/persistence/tables.py`). Colunas novas
exigem tanto migration quanto atualização de `tables.py`.

## 9. Uso de `sdk.hooks`

O frontend expõe `sdk.hooks.{on,once,emit}` e `sdk.events.{on,once}`, todos com
gate na única capability `hooks.client`, apoiados num `Map` de listeners
in-process em `gravewright-sdk.js`. Ainda não existe `sdk.bus.*`.

### DRIFT — hooks como interop

O plano marca `hooks.client` como `legacy_experimental` e `sdk.bus.*` como o
caminho formal de interop (Fase 12). Hoje os hooks são o único canal de interop e
estão documentados em `docs/sdk/messaging.md` sem marcação legacy/experimental.

## 10. Layout de dados

`app/engine/sdk/package_registry.py`: `PACKAGES_DIR = data_dir / "packages"`. Os
pacotes são descobertos como diretórios **flat** `data/packages/{id}/`. Pacotes
atuais em disco: `data/packages/dnd5e`, `data/packages/dice-so-nice-lite`.

### DRIFT — layout universal

O plano exige `data/packages/{kind_plural}/{id}/` mais uma árvore paralela
`data/storage/packages/{kind_plural}/{id}/`. Veja `docs/pt-br/sdk/data-layout.md`
para o layout atual vs alvo e o caminho de migração. Ainda não existe árvore de
storage gerenciado.

## 11. Lifecycle do runtime frontend (como construído)

`window.GravewrightSDK` expõe apenas `version` e `register(definition)`.
`register` impõe: id não vazio, script dono do package (nonce validado ou match
de URL), id == dono do script, package ativo, sem duplicidade. `setup` roda uma
vez por package; `ready` roda uma vez após `init` (DOMContentLoaded). Um objeto
de introspecção `GravewrightSDKDebug` é exposto apenas quando
`context.debug === true`. Isto já corresponde a boa parte do alvo da Fase 11; a
Fase 11 vai adicionar testes e sync do mapa de capabilities, em vez de
reconstruir.
