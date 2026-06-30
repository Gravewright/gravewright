# Superficie de API da SDK

Esta e a superficie publica da SDK do Gravewright, dividida por camada. Os
status seguem `stability-policy.md`. O namespace `sdk.bus` e o backend/doctor
de `sdk.bus` fazem parte do contrato estavel de interop.

## Frontend Global

| API | Status | Notas |
|---|---|---|
| `window.GravewrightSDK.version` | `stable` | Retorna `"1"`. |
| `window.GravewrightSDK.register(definition)` | `stable` | Registra `{ id, setup, ready }` com ownership validado. |
| `window.GravewrightSDKDebug.*` | `internal` | Disponivel apenas em contexto debug. |
| `window.GravewrightHTMLSheets.*` | `stable` | Runtime interno de montagem/update/unmount de sheets HTML. |

## SDK Escopada

| Membro | Capability | Status |
|---|---|---|
| `sdk.version` | publico | `stable` |
| `sdk.package` | publico | `stable` |
| `sdk.kind` | publico | `stable` |
| `sdk.capabilities.has/require/list` | publico | `stable` |
| `sdk.context()` | publico | `stable` |
| `sdk.game.context/campaign/scene/user/ready` | publico | `stable` |
| `sdk.settings.definitions/all/get/set` | `settings` | `stable` |
| `sdk.content.packs/pack` | `content.packs` | `stable` |
| `sdk.i18n.t` | `locales` | `stable` |
| `sdk.commands.register` | `commands.register` | `stable` |
| `sdk.chat.send` | `chat.cards` | `stable` |
| `sdk.dice.roll` | `dice.roll` | `stable` |
| `sdk.rolls.intent` | `rolls.intent` | `stable` |
| `sdk.ui.toast/openModal/closeModal` | `assets.ui` | `stable` |
| `sdk.tokens.centerOn` | `tokens.extends` | `stable` |
| `sdk.scene.activeCanvas/activeCameraForScene` | `scene.tools` | `stable` |
| `sdk.tools.activeTool` | `scene.tools` | `stable` |
| `sdk.storage.sqlite.query/execute/status` | `storage.sqlite` | `stable` |
| `sdk.bus.publish/subscribe/request/provide` | `bus.*` | `stable` |
| `sdk.sheets.registerController` | `sheets.controller` | `stable` |
| `sdk.sheets.helpers/register` | `sheets.runtime` | `stable` |
| `sdk.combat.register/registerPanel/dispatch/renderSlot` | `combat.runtime` | `stable` |

Atalhos ergonomicos (`sdk.toast`, `sdk.setting`) delegam aos namespaces acima e
herdam o status deles.

## Manifest

| Campo | Status |
|---|---|
| `schemaVersion`, `sdkVersion` | `stable` |
| `kind`, `id`, `name`, `version`, `description` | `stable` |
| `authors`, `license`, `homepage`, `repository` | `stable` |
| `compatibility{minimum,verified,maximum}` | `stable` |
| `capabilities[]` | `stable` |
| `activation{scope,mode}` | `stable` |
| `entrypoints{<name>{styles,scripts}}` | `stable` |
| `provides{...}` | `stable` |
| `settings[]` | `stable` |
| `dependencies[]`, `conflicts[]` | `stable` |
| `distribution{type,url,sha256}` | `stable` |
| `display{color}` | `stable` |
| `storage.sqlite{...}` | `stable` |
| `interop{emits,listens,provides,requires}` | `stable` |
| `provides.*.sheet{mode:"html",...}` | `stable` |

## Backend

| Simbolo | Status | Notas |
|---|---|---|
| `validate_manifest(raw)` | `stable` | Valida manifest v1. |
| `PackageManifest` / `PackageKind` | `stable` | Modelo canonico de manifest. |
| `capability_registry.*` | `stable` | Registro canonico de capabilities. |
| `PackageInstallService` / `PackageActivationService` | `stable` | Instalacao e ativacao. |
| `PackageSettingsService` | `stable` | Settings de pacote. |
| `PackageDependencyService` | `stable` | Dependencias e conflitos. |
| `PackageDoctorService` / `DoctorFinding` | `stable` | Auditoria de pacote/campanha/storage/interop. |
| `PackageStorageRuntime` | `stable` | SQLite gerenciado. |
| `package_interop.*` | `stable` | Validacao de declaracoes interop. |
| `sdk.bus` backend/doctor checks | `stable` | Checks de declaracao interop. |

O modelo legado de erro ainda inclui strings `sdk.validation.*` em adapters de
borda.

## Persistence

| Tabela | Status |
|---|---|
| `installed_packages` | `stable` |
| `campaign_packages` | `stable` |
| `package_settings` | `stable` |
| `package_content_imports` | `stable` |
| `gravewright_package_migrations` | `stable` |
| `gravewright_package_migration_state` | `stable` |
