# Referência de métodos da SDK 1

Gerada a partir dos registros congelados. Nomes e defaults dos parâmetros são assinaturas JavaScript exatas.

## `sdk.actors.create(input = {})`

Capability: `actors.write`
Retorno: `Promise<ActorMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ActorCreateInput` | Não | `{}` |

## `sdk.actors.data(actorId)`

Capability: `actors.read`
Retorno: `Promise<ActorDataDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |

## `sdk.actors.delete(actorId)`

Capability: `actors.write`
Retorno: `Promise<ActorMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |

## `sdk.actors.get(actorId)`

Capability: `actors.read`
Retorno: `Promise<ActorDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |

## `sdk.actors.items.insertCopy(actorId, sourceItemId, options = {})`

Capability: `actors.items.write`
Retorno: `Promise<ActorItemInsertResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |
| `sourceItemId` | `string` | Sim | `None` |
| `options` | `ActorItemSlotOptions` | Não | `{}` |

## `sdk.actors.items.listCopies(actorId, options = {})`

Capability: `actors.items.read`
Retorno: `Promise<ActorItemCopyDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |
| `options` | `ActorItemSlotOptions` | Não | `{}` |

## `sdk.actors.items.removeCopy(actorId, localInstanceId, options = {})`

Capability: `actors.items.write`
Retorno: `Promise<ActorItemRemoveResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |
| `localInstanceId` | `string` | Sim | `None` |
| `options` | `ActorItemSlotOptions` | Não | `{}` |

## `sdk.actors.items.slots(actorId)`

Capability: `actors.items.read`
Retorno: `Promise<ActorItemSlotDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |

## `sdk.actors.list(query = {})`

Capability: `actors.read`
Retorno: `Promise<ActorDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `EntityListQuery` | Não | `{}` |

## `sdk.actors.patchData(actorId, patch = {})`

Capability: `actors.data.write`
Retorno: `Promise<SheetDataPatchResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |
| `patch` | `RulesetSheetData` | Não | `{}` |

## `sdk.actors.update(actorId, patch = {}, options = {})`

Capability: `actors.write`
Retorno: `Promise<ActorMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sim | `None` |
| `patch` | `ActorUpdateInput` | Não | `{}` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.assets.cancelImport(assetId)`

Capability: `assets.import`
Retorno: `Promise<AssetCancelResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `assetId` | `string` | Sim | `None` |

## `sdk.assets.ingest(file)`

Capability: `assets.import`
Retorno: `Promise<AssetIngestResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `file` | `File` | Sim | `None` |

## `sdk.assets.list(options = {})`

Capability: `assets.library`
Retorno: `Promise<AssetDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `AssetListOptions` | Não | `{}` |

## `sdk.automation.audit()`

Capability: `automation.schedule`
Retorno: `Promise<AutomationAuditDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.automation.cancel(jobId)`

Capability: `automation.schedule`
Retorno: `Promise<AutomationCancelResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `jobId` | `string` | Sim | `None` |

## `sdk.automation.get(jobId)`

Capability: `automation.schedule`
Retorno: `Promise<AutomationJobDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `jobId` | `string` | Sim | `None` |

## `sdk.automation.list()`

Capability: `automation.schedule`
Retorno: `Promise<AutomationJobDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.automation.schedule(actionId, input = {}, options = {})`

Capability: `automation.schedule`
Retorno: `Promise<AutomationJobDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Sim | `None` |
| `input` | `ActionInput` | Não | `{}` |
| `options` | `AutomationScheduleOptions` | Não | `{}` |

## `sdk.bus.provide(method, handler)`

Capability: `bus.provide`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `method` | `string` | Sim | `None` |
| `handler` | `InteropHandler` | Sim | `None` |

## `sdk.bus.publish(name, payload)`

Capability: `bus.publish`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sim | `None` |
| `payload` | `InteropPayload` | Sim | `None` |

## `sdk.bus.request(method, payload, options)`

Capability: `bus.request`
Retorno: `Promise<BusResponse>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `method` | `string` | Sim | `None` |
| `payload` | `InteropPayload` | Sim | `None` |
| `options` | `BusRequestOptions` | Sim | `None` |

## `sdk.bus.subscribe(name, fn)`

Capability: `bus.subscribe`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sim | `None` |
| `fn` | `InteropSubscriber` | Sim | `None` |

## `sdk.cards.definitions.get(id, version)`

Capability: `cards.read`
Retorno: `Promise<CardDefinitionDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sim | `None` |
| `version` | `number` | Sim | `None` |

## `sdk.cards.definitions.instantiate(id, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardDefinitionInstantiateResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sim | `None` |
| `options` | `CardDefinitionInstantiateOptions` | Não | `{}` |

## `sdk.cards.definitions.list()`

Capability: `cards.read`
Retorno: `Promise<CardDefinitionDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.cards.discard(cardIds)`

Capability: `cards.manage`
Retorno: `Promise<CardIdsResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardIds` | `string[]` | Sim | `None` |

## `sdk.cards.discardPlacement(placementId)`

Capability: `cards.manage`
Retorno: `Promise<CardPlacementDiscardResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sim | `None` |

## `sdk.cards.draw(deckId, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardDrawResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Sim | `None` |
| `options` | `CardDrawOptions` | Não | `{}` |

## `sdk.cards.play(cardId, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardPlayResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardId` | `string` | Sim | `None` |
| `options` | `CardPlayOptions` | Não | `{}` |

## `sdk.cards.reset(deckId, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardDeckMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Sim | `None` |
| `options` | `CardResetOptions` | Não | `{}` |

## `sdk.cards.reveal(cardIds)`

Capability: `cards.manage`
Retorno: `Promise<CardIdsResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardIds` | `string[]` | Sim | `None` |

## `sdk.cards.shuffle(deckId)`

Capability: `cards.manage`
Retorno: `Promise<CardDeckMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Sim | `None` |

## `sdk.cards.state()`

Capability: `cards.read`
Retorno: `Promise<CardStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.cards.updatePlacement(placementId, patch = {})`

Capability: `cards.manage`
Retorno: `Promise<CardPlacementResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sim | `None` |
| `patch` | `CardPlacementPatch` | Não | `{}` |

## `sdk.chat.get(messageId)`

Capability: `chat.read`
Retorno: `Promise<ChatMessageDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `messageId` | `string` | Sim | `None` |

## `sdk.chat.list(options = {})`

Capability: `chat.read`
Retorno: `Promise<ChatMessageDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `ChatListOptions` | Não | `{}` |

## `sdk.chat.send(message)`

Capability: `chat.cards`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `message` | `string | ChatSendMessage` | Sim | `None` |

## `sdk.combat.add(input = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `CombatAddInput` | Não | `{}` |

## `sdk.combat.advance(delta = 1)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `delta` | `number` | Não | `1` |

## `sdk.combat.advanceRound(delta = 1)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `delta` | `number` | Não | `1` |

## `sdk.combat.combatants()`

Capability: `combat.read`
Retorno: `Promise<CombatantDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.combat.current()`

Capability: `combat.read`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.combat.dispatch(name, payload)`

Capability: `combat.runtime`
Retorno: `CombatProtocolPayload | undefined`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sim | `None` |
| `payload` | `CombatProtocolPayload` | Sim | `None` |

## `sdk.combat.end()`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.combat.moveCombatant(combatantId, delta)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sim | `None` |
| `delta` | `number` | Sim | `None` |

## `sdk.combat.register(plugin)`

Capability: `combat.runtime`
Retorno: `boolean`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `plugin` | `CombatPlugin` | Sim | `None` |

## `sdk.combat.registerPanel(panel)`

Capability: `combat.runtime`
Retorno: `boolean`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `panel` | `CombatPanelDefinition` | Sim | `None` |

## `sdk.combat.remove(combatantId)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sim | `None` |

## `sdk.combat.renderSlot(name, payload)`

Capability: `combat.runtime`
Retorno: `Node[]`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sim | `None` |
| `payload` | `CombatProtocolPayload` | Sim | `None` |

## `sdk.combat.rollInitiative(options = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `CombatRollInitiativeOptions` | Não | `{}` |

## `sdk.combat.setFlags(combatantId, flags = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sim | `None` |
| `flags` | `CombatFlagsPatch` | Não | `{}` |

## `sdk.combat.setInitiative(combatantId, value)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sim | `None` |
| `value` | `number` | Sim | `None` |

## `sdk.combat.setInitiativeOrder(entries)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `entries` | `CombatInitiativeOrderEntry[]` | Sim | `None` |

## `sdk.combat.setTurn(combatantId)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sim | `None` |

## `sdk.combat.start(input = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `CombatStartInput` | Não | `{}` |

## `sdk.commands.register(name, handler)`

Capability: `commands.register`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sim | `None` |
| `handler` | `CommandHandler` | Sim | `None` |

## `sdk.content.can(reference, action = "read")`

Capability: `content.references`
Retorno: `Promise<boolean>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sim | `None` |
| `action` | `string` | Não | `"read"` |

## `sdk.content.get(reference)`

Capability: `content.references`
Retorno: `Promise<ContentResolvedValue>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sim | `None` |

## `sdk.content.link(reference, options = {})`

Capability: `content.references`
Retorno: `ContentLinkDTO`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sim | `None` |
| `options` | `ContentLinkOptions` | Não | `{}` |

## `sdk.content.open(reference, options = {})`

Capability: `content.references`
Retorno: `Promise<ContentResolutionDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sim | `None` |
| `options` | `ContentOpenOptions` | Não | `{}` |

## `sdk.content.pack(packId)`

Capability: `content.packs`
Retorno: `Promise<ContentPackDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packId` | `string` | Sim | `None` |

## `sdk.content.packs()`

Capability: `content.packs`
Retorno: `Promise<ContentPackSummaryDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.content.ref(kind, resourceId, options = {})`

Capability: `content.references`
Retorno: `string`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `kind` | `string` | Sim | `None` |
| `resourceId` | `string` | Sim | `None` |
| `options` | `ContentRefOptions` | Não | `{}` |

## `sdk.content.resolve(reference)`

Capability: `content.references`
Retorno: `Promise<ContentResolutionDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sim | `None` |

## `sdk.content.search(query = "", options = {})`

Capability: `content.index`
Retorno: `Promise<ContentSearchPageDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `string` | Não | `""` |
| `options` | `ContentSearchOptions` | Não | `{}` |

## `sdk.dice.roll({ formula, label = "", actorId = "" } = {})`

Capability: `dice.roll`
Retorno: `Promise<RollResultDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `DiceRollInput` | Não | `"", actorId = "" } = {}` |

## `sdk.events.available()`

Capability: `events.subscribe`
Retorno: `SdkEventName[]`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.events.on(event, handler)`

Capability: `events.subscribe`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `event` | `string` | Sim | `None` |
| `handler` | `SdkEventHandler` | Sim | `None` |

## `sdk.events.once(event, handler)`

Capability: `events.subscribe`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `event` | `string` | Sim | `None` |
| `handler` | `SdkEventHandler` | Sim | `None` |

## `sdk.handouts.present(resourceType, resourceId, audience = {})`

Capability: `handouts.present`
Retorno: `Promise<HandoutPresentResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `resourceType` | `string` | Sim | `None` |
| `resourceId` | `string` | Sim | `None` |
| `audience` | `HandoutAudience` | Não | `{}` |

## `sdk.i18n.t(key, fallback)`

Capability: `locales`
Retorno: `string`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sim | `None` |
| `fallback` | `string` | Sim | `None` |

## `sdk.items.create(input = {})`

Capability: `items.write`
Retorno: `Promise<ItemMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ItemCreateInput` | Não | `{}` |

## `sdk.items.delete(itemId)`

Capability: `items.write`
Retorno: `Promise<ItemMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sim | `None` |

## `sdk.items.get(itemId)`

Capability: `items.read`
Retorno: `Promise<ItemDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sim | `None` |

## `sdk.items.list(query = {})`

Capability: `items.read`
Retorno: `Promise<ItemDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `EntityListQuery` | Não | `{}` |

## `sdk.items.patchData(itemId, patch = {})`

Capability: `items.data.write`
Retorno: `Promise<ItemDataPatchResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sim | `None` |
| `patch` | `RulesetSheetData` | Não | `{}` |

## `sdk.items.update(itemId, patch = {}, options = {})`

Capability: `items.write`
Retorno: `Promise<ItemMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sim | `None` |
| `patch` | `ItemUpdateInput` | Não | `{}` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.journals.create(input = {})`

Capability: `journals.write`
Retorno: `Promise<JournalMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `JournalCreateInput` | Não | `{}` |

## `sdk.journals.delete(journalId)`

Capability: `journals.write`
Retorno: `Promise<JournalMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Sim | `None` |

## `sdk.journals.get(journalId)`

Capability: `journals.read`
Retorno: `Promise<JournalDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Sim | `None` |

## `sdk.journals.list(options = {})`

Capability: `journals.read`
Retorno: `Promise<JournalListResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `JournalListOptions` | Não | `{}` |

## `sdk.journals.update(journalId, patch = {})`

Capability: `journals.write`
Retorno: `Promise<JournalMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Sim | `None` |
| `patch` | `JournalUpdatePatch` | Não | `{}` |

## `sdk.packages.get(packageId)`

Capability: `packages.inspect`
Retorno: `Promise<PackageDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packageId` | `string` | Sim | `None` |

## `sdk.packages.has(packageId)`

Capability: `packages.inspect`
Retorno: `Promise<boolean>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packageId` | `string` | Sim | `None` |

## `sdk.pdf.annotations.create(documentId, annotation = {})`

Capability: `pdf.annotations.write`
Retorno: `Promise<PdfAnnotationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `annotation` | `PdfAnnotationInput` | Não | `{}` |

## `sdk.pdf.annotations.delete(documentId, annotationId)`

Capability: `pdf.annotations.write`
Retorno: `Promise<PdfAnnotationDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `annotationId` | `string` | Sim | `None` |

## `sdk.pdf.annotations.list(documentId)`

Capability: `pdf.annotations.read`
Retorno: `Promise<PdfAnnotationDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |

## `sdk.pdf.annotations.update(documentId, annotationId, annotation = {})`

Capability: `pdf.annotations.write`
Retorno: `Promise<PdfAnnotationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `annotationId` | `string` | Sim | `None` |
| `annotation` | `PdfAnnotationInput` | Não | `{}` |

## `sdk.pdf.get(documentId)`

Capability: `pdf.read`
Retorno: `Promise<PdfDocumentDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |

## `sdk.pdf.metadata(documentId)`

Capability: `pdf.read`
Retorno: `Promise<PdfMetadataDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |

## `sdk.pdf.presentation.current(documentId)`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |

## `sdk.pdf.presentation.end(documentId)`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |

## `sdk.pdf.presentation.start(documentId, input = {})`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `input` | `PdfPresentationStartInput` | Não | `{}` |

## `sdk.pdf.presentation.update(documentId, page, options = {})`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `page` | `number` | Sim | `None` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.pdf.viewer.currentPage(documentId)`

Capability: `pdf.viewer`
Retorno: `number | null`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |

## `sdk.pdf.viewer.goToPage(documentId, page)`

Capability: `pdf.viewer`
Retorno: `Promise<number>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `page` | `number` | Sim | `None` |

## `sdk.pdf.viewer.open(reference, options = {})`

Capability: `pdf.viewer`
Retorno: `Promise<PdfViewerOpenResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string` | Sim | `None` |
| `options` | `PdfViewerOpenOptions` | Não | `{}` |

## `sdk.pdf.viewer.search(documentId, query)`

Capability: `pdf.viewer`
Retorno: `Promise<PdfSearchMatch[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sim | `None` |
| `query` | `string` | Sim | `None` |

## `sdk.permissions.can(action, resource = {})`

Capability: `permissions.inspect`
Retorno: `Promise<boolean>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `action` | `string` | Sim | `None` |
| `resource` | `PermissionResource` | Não | `{}` |

## `sdk.permissions.check(action, resource = {})`

Capability: `permissions.inspect`
Retorno: `Promise<PermissionCheckDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `action` | `string` | Sim | `None` |
| `resource` | `PermissionResource` | Não | `{}` |

## `sdk.rolls.intent(payload = {})`

Capability: `rolls.intent`
Retorno: `Promise<RollResultDTO | SheetDataPatchResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `payload` | `RollIntentInput` | Não | `{}` |

## `sdk.rules.actions.execute(actionId, input = {}, options = {})`

Capability: `rules.actions`
Retorno: `Promise<ActionExecutionResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Sim | `None` |
| `input` | `ActionInput` | Não | `{}` |
| `options` | `ActionExecuteOptions` | Não | `{}` |

## `sdk.rules.actions.executeReference(reference, input = {}, options = {})`

Capability: `rules.actions`
Retorno: `Promise<ActionExecutionResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string` | Sim | `None` |
| `input` | `ActionInput` | Não | `{}` |
| `options` | `ActionReferenceExecuteOptions` | Não | `{}` |

## `sdk.rules.actions.get(actionId)`

Capability: `rules.actions`
Retorno: `Promise<ActionDefinitionDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Sim | `None` |

## `sdk.rules.actions.list()`

Capability: `rules.actions`
Retorno: `Promise<ActionDefinitionDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.rules.actions.resolve({ provider, semantic } = {})`

Capability: `rules.actions`
Retorno: `Promise<ActionDefinitionDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ActionResolveInput` | Não | `{}` |

## `sdk.scene.active()`

Capability: `scene.read`
Retorno: `Promise<SceneDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.scene.activeCameraForScene(sceneId)`

Capability: `scene.tools`
Retorno: `CameraDTO | null`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |

## `sdk.scene.activeCanvas()`

Capability: `scene.tools`
Retorno: `HTMLElement | null`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.scene.effects.create(sceneId, kind, values = {})`

Capability: `scene.effects.write`
Retorno: `Promise<ParticleResultDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `kind` | `string` | Sim | `None` |
| `values` | `ParticleValues` | Não | `{}` |

## `sdk.scene.effects.delete(effectId, kind)`

Capability: `scene.effects.write`
Retorno: `Promise<ParticleDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `effectId` | `string` | Sim | `None` |
| `kind` | `string` | Sim | `None` |

## `sdk.scene.effects.list(sceneId = context.scene?.id)`

Capability: `scene.effects.read`
Retorno: `Promise<EffectStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.effects.presets()`

Capability: `scene.effects.read`
Retorno: `Promise<ParticlePresetDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.scene.effects.update(effectId, kind, values = {})`

Capability: `scene.effects.write`
Retorno: `Promise<ParticleResultDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `effectId` | `string` | Sim | `None` |
| `kind` | `string` | Sim | `None` |
| `values` | `ParticleValues` | Não | `{}` |

## `sdk.scene.fog.disable(sceneId = context.scene?.id)`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.fog.enable(sceneId = context.scene?.id, initial = "hide_all")`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |
| `initial` | `string` | Não | `"hide_all"` |

## `sdk.scene.fog.paint(sceneId = context.scene?.id, ops = [], options = {})`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |
| `ops` | `FogOp[]` | Não | `[]` |
| `options` | `FogPaintOptions` | Não | `{}` |

## `sdk.scene.fog.reset(sceneId = context.scene?.id, to = "hide_all")`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |
| `to` | `string` | Não | `"hide_all"` |

## `sdk.scene.fog.state(sceneId = context.scene?.id)`

Capability: `scene.fog.read`
Retorno: `Promise<FogStateDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.geometry.createLight(sceneId, input = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<LightResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `input` | `LightCreateInput` | Não | `{}` |

## `sdk.scene.geometry.createWall(sceneId, input = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<WallResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `input` | `WallCreateInput` | Não | `{}` |

## `sdk.scene.geometry.deleteLight(lightId)`

Capability: `scene.geometry.write`
Retorno: `Promise<LightDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `lightId` | `string` | Sim | `None` |

## `sdk.scene.geometry.deleteWall(wallId)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sim | `None` |

## `sdk.scene.geometry.deleteWalls(wallIds)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallIds` | `string[]` | Sim | `None` |

## `sdk.scene.geometry.lights(sceneId = context.scene?.id)`

Capability: `scene.geometry.read`
Retorno: `Promise<LightDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.geometry.moveWallNode(sceneId, from, to)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `from` | `WorldPointDTO` | Sim | `None` |
| `to` | `WorldPointDTO` | Sim | `None` |

## `sdk.scene.geometry.moveWalls(sceneId, wallIds, delta)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `wallIds` | `string[]` | Sim | `None` |
| `delta` | `WorldPointDTO` | Sim | `None` |

## `sdk.scene.geometry.setDoorState(wallId, state)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sim | `None` |
| `state` | `string` | Sim | `None` |

## `sdk.scene.geometry.splitWall(wallId, x, y)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sim | `None` |
| `x` | `number` | Sim | `None` |
| `y` | `number` | Sim | `None` |

## `sdk.scene.geometry.updateLight(lightId, patch = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<LightResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `lightId` | `string` | Sim | `None` |
| `patch` | `LightUpdatePatch` | Não | `{}` |

## `sdk.scene.geometry.updateWall(wallId, patch = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<WallResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sim | `None` |
| `patch` | `WallUpdatePatch` | Não | `{}` |

## `sdk.scene.geometry.walls(sceneId = context.scene?.id)`

Capability: `scene.geometry.read`
Retorno: `Promise<WallDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.get(sceneId)`

Capability: `scene.read`
Retorno: `Promise<SceneDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |

## `sdk.scene.images.delete(placementId)`

Capability: `scene.images.write`
Retorno: `Promise<SceneImageDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sim | `None` |

## `sdk.scene.images.list(sceneId = context.scene?.id)`

Capability: `scene.images.read`
Retorno: `Promise<SceneImageListResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.images.place(sceneId, assetId, options = {})`

Capability: `scene.images.write`
Retorno: `Promise<SceneImageResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `assetId` | `string` | Sim | `None` |
| `options` | `SceneImagePlaceOptions` | Não | `{}` |

## `sdk.scene.images.update(placementId, patch = {}, options = {})`

Capability: `scene.images.write`
Retorno: `Promise<SceneImageResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sim | `None` |
| `patch` | `SceneImageUpdatePatch` | Não | `{}` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.scene.list()`

Capability: `scene.read`
Retorno: `Promise<SceneDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.scene.measurements.cancel(sceneId, measurementId)`

Capability: `scene.measurements.shared`
Retorno: `Promise<SharedMeasurementDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `measurementId` | `string` | Sim | `None` |

## `sdk.scene.measurements.listShared(sceneId = context.scene?.id)`

Capability: `scene.measurements.shared`
Retorno: `Promise<SharedMeasurementDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.measurements.measure(sceneId, from, to)`

Capability: `scene.tools`
Retorno: `Promise<MeasurementResultDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `from` | `WorldPointDTO` | Sim | `None` |
| `to` | `WorldPointDTO` | Sim | `None` |

## `sdk.scene.measurements.share(sceneId, geometry, options = {})`

Capability: `scene.measurements.shared`
Retorno: `Promise<SharedMeasurementDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `geometry` | `SharedMeasurementGeometry` | Sim | `None` |
| `options` | `SharedMeasurementOptions` | Não | `{}` |

## `sdk.scene.shaders.apply(sceneId, input = {})`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderInstanceDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `input` | `ShaderApplyInput` | Não | `{}` |

## `sdk.scene.shaders.enable(id, enabled, options = {})`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderInstanceDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sim | `None` |
| `enabled` | `boolean` | Sim | `None` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.scene.shaders.getPreset(presetId)`

Capability: `scene.shaders.read`
Retorno: `Promise<ShaderPresetDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `presetId` | `string` | Sim | `None` |

## `sdk.scene.shaders.list(sceneId = context.scene?.id)`

Capability: `scene.shaders.read`
Retorno: `Promise<ShaderInstanceDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.shaders.presets()`

Capability: `scene.shaders.read`
Retorno: `Promise<ShaderPresetDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.scene.shaders.remove(id)`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderRemovalResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sim | `None` |

## `sdk.scene.shaders.update(id, patch = {}, options = {})`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderInstanceDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sim | `None` |
| `patch` | `ShaderUpdateInput` | Não | `{}` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.scene.templates.create(sceneId, values = {})`

Capability: `scene.templates.write`
Retorno: `Promise<SceneTemplateResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `values` | `SceneTemplateValues` | Não | `{}` |

## `sdk.scene.templates.delete(templateId, options = {})`

Capability: `scene.templates.write`
Retorno: `Promise<SceneTemplateDeleteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `templateId` | `string` | Sim | `None` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.scene.templates.get(sceneId, templateId)`

Capability: `scene.templates.read`
Retorno: `Promise<SceneTemplateDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sim | `None` |
| `templateId` | `string` | Sim | `None` |

## `sdk.scene.templates.list(sceneId = context.scene?.id)`

Capability: `scene.templates.read`
Retorno: `Promise<SceneTemplateListResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.scene.templates.update(templateId, patch = {}, options = {})`

Capability: `scene.templates.write`
Retorno: `Promise<SceneTemplateResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `templateId` | `string` | Sim | `None` |
| `patch` | `Partial<SceneTemplateValues>` | Não | `{}` |
| `options` | `ExpectedVersionOptions` | Não | `{}` |

## `sdk.settings.all()`

Capability: `settings`
Retorno: `SettingValues`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.settings.definitions()`

Capability: `settings`
Retorno: `SettingDefinitionDTO[]`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.settings.get(key, fallback = undefined)`

Capability: `settings`
Retorno: `SettingValue | undefined`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sim | `None` |
| `fallback` | `string` | Não | `undefined` |

## `sdk.settings.onChange(key, handler)`

Capability: `settings`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sim | `None` |
| `handler` | `SettingChangeHandler` | Sim | `None` |

## `sdk.settings.scope(key)`

Capability: `settings`
Retorno: `SettingScope | null`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sim | `None` |

## `sdk.settings.set(key, value, options = {})`

Capability: `settings`
Retorno: `Promise<SettingSetResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sim | `None` |
| `value` | `number` | Sim | `None` |
| `options` | `SettingSetOptions` | Não | `{}` |

## `sdk.sheets.helpers()`

Capability: `sheets.runtime`
Retorno: `SheetHelpers`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.sheets.register(plugin)`

Capability: `sheets.runtime`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `plugin` | `SheetPlugin` | Sim | `None` |

## `sdk.sheets.registerController(sheetType, controller)`

Capability: `sheets.controller`
Retorno: `boolean`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sheetType` | `string` | Sim | `None` |
| `controller` | `SheetController` | Sim | `None` |

## `sdk.storage.sqlite.execute(scope, name, params = {})`

Capability: `storage.sqlite`
Retorno: `Promise<StorageExecuteResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Sim | `None` |
| `name` | `string` | Sim | `None` |
| `params` | `StorageParams` | Não | `{}` |

## `sdk.storage.sqlite.query(scope, name, params = {})`

Capability: `storage.sqlite`
Retorno: `Promise<StorageQueryResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Sim | `None` |
| `name` | `string` | Sim | `None` |
| `params` | `StorageParams` | Não | `{}` |

## `sdk.storage.sqlite.status(scope)`

Capability: `storage.sqlite`
Retorno: `Promise<StorageStatusDTO>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Sim | `None` |

## `sdk.tokens.centerOn(tokenId)`

Capability: `tokens.extends`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sim | `None` |

## `sdk.tokens.create(input = {})`

Capability: `tokens.manage`
Retorno: `Promise<TokenMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `TokenCreateInput` | Não | `{}` |

## `sdk.tokens.delete(tokenId, options = {})`

Capability: `tokens.manage`
Retorno: `Promise<TokenMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sim | `None` |
| `options` | `TokenOptions` | Não | `{}` |

## `sdk.tokens.get(tokenId, options = {})`

Capability: `tokens.read`
Retorno: `Promise<TokenDTO | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sim | `None` |
| `options` | `TokenReadOptions` | Não | `{}` |

## `sdk.tokens.list(options = {})`

Capability: `tokens.read`
Retorno: `Promise<TokenDTO[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `TokenReadOptions` | Não | `{}` |

## `sdk.tokens.move(tokenId, position = {}, options = {})`

Capability: `tokens.move`
Retorno: `Promise<TokenMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sim | `None` |
| `position` | `TokenMoveInput` | Não | `{}` |
| `options` | `TokenOptions` | Não | `{}` |

## `sdk.tokens.targets.clear(sceneId = context.scene?.id)`

Capability: `tokens.targets`
Retorno: `Promise<string[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.tokens.targets.list(sceneId = context.scene?.id)`

Capability: `tokens.targets`
Retorno: `Promise<string[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.tokens.targets.set(ids, sceneId = context.scene?.id)`

Capability: `tokens.targets`
Retorno: `Promise<string[]>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `ids` | `string[]` | Sim | `None` |
| `sceneId` | `string` | Não | `context.scene?.id` |

## `sdk.tokens.update(tokenId, patch = {}, options = {})`

Capability: `tokens.manage`
Retorno: `Promise<TokenMutationResult>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sim | `None` |
| `patch` | `TokenOverrides` | Não | `{}` |
| `options` | `TokenOptions` | Não | `{}` |

## `sdk.tools.activeTool()`

Capability: `scene.tools`
Retorno: `string`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.tools.register(definition = {})`

Capability: `scene.tools`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `ToolDefinition` | Não | `{}` |

## `sdk.ui.applications.close(applicationId)`

Capability: `ui.applications`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Sim | `None` |

## `sdk.ui.applications.register(applicationId, definition)`

Capability: `ui.applications`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Sim | `None` |
| `definition` | `ApplicationDefinition` | Sim | `None` |

## `sdk.ui.applications.render(applicationId, host, appContext = {}, options = {})`

Capability: `ui.applications`
Retorno: `Promise<ApplicationInstance | null>`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Sim | `None` |
| `host` | `HTMLElement` | Sim | `None` |
| `appContext` | `ApplicationContext` | Não | `{}` |
| `options` | `ApplicationRenderOptions` | Não | `{}` |

## `sdk.ui.closeModal(modalOrId)`

Capability: `assets.ui`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `modalOrId` | `string` | Sim | `None` |

## `sdk.ui.openModal(modalId)`

Capability: `assets.ui`
Retorno: `void`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `modalId` | `string` | Sim | `None` |

## `sdk.ui.slots.available()`

Capability: `ui.slots`
Retorno: `string[]`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

## `sdk.ui.slots.register(slotId, render)`

Capability: `ui.slots`
Retorno: `Disposer`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `slotId` | `string` | Sim | `None` |
| `render` | `SlotRenderCallback` | Sim | `None` |

## `sdk.ui.toast(message, options)`

Capability: `assets.ui`
Retorno: `ToastHandle | undefined`
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.

Parâmetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `message` | `string` | Sim | `None` |
| `options` | `ToastOptions` | Sim | `None` |
