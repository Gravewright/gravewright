# Contrato de Diagnostics da SDK

> O formato comum, machine-readable, que todo serviço da SDK fala para erros,
> findings e resultados de ação. Definido em `app/engine/sdk/diagnostics.py`
> (Fase 1 do plano de estabilidade).

## Por quê

Strings `error_key` simples são aceitáveis nas *bordas* (rotas, templates, CLI),
mas são um contrato interno fraco: misturam namespaces, são fáceis de errar e
tentam os testes a asserir sobre texto humano. O contrato de diagnostics é o
formato **interno**.

> Os serviços da SDK retornam `SdkError` / `SdkActionResult` / `DoctorFinding`.
> Na borda HTTP o `code` estruturado também é exposto como `error_key`.

## Tipos

### `SdkError`

```python
SdkError(
    code: str,                       # estável, machine-readable
    message: str = "",               # legível por humano; nunca asserido
    details: dict[str, Any] = {},
    package_id: str | None = None,
    campaign_id: str | None = None,
)
```

### `SdkActionResult`

```python
SdkActionResult(
    success: bool,
    package_id: str | None = None,
    campaign_id: str | None = None,
    error: SdkError | None = None,
    warnings: tuple[SdkError, ...] = (),
)
```

Construa com `SdkActionResult.ok(...)` / `SdkActionResult.fail(error)`.

### `DoctorFinding`

```python
DoctorFinding(
    code: str,
    severity: Literal["error", "warning", "info"],
    message: str = "",
    details: dict[str, Any] = {},
    package_id: str | None = None,
    campaign_id: str | None = None,
)
```

Os três expõem `to_dict()` para a UI/CLI; campos opcionais são *omitidos* (não
null) quando ausentes.

## Convenção de códigos

Um código é um identificador minúsculo separado por pontos cujo primeiro
segmento é `sdk`, casando `^sdk(\.[a-z0-9]+(_[a-z0-9]+)*)+$`. Namespaces
públicos:

```text
sdk.manifest.*        sdk.compatibility.*   sdk.capabilities.*
sdk.paths.*           sdk.dependencies.*    sdk.conflicts.*
sdk.settings.*        sdk.assets.*          sdk.content.*
sdk.locale.*          sdk.frontend.*        sdk.interop.*
sdk.persistence.*     sdk.storage.*
```

Catálogo inicial (veja `SDK_ERROR_CODES`), por exemplo:

```text
sdk.manifest.id_mismatch
sdk.manifest.kind_root_mismatch
sdk.capabilities.unknown
sdk.capabilities.forbidden
sdk.paths.unsafe
sdk.dependencies.active_dependents
sdk.settings.invalid_value
sdk.persistence.manifest_hash_mismatch
sdk.storage.sqlite.query_missing
```

Os testes asseguram sobre `code` e `details`, **nunca** sobre `message`.

## Borda HTTP

Os endpoints da SDK retornam o `code` estruturado. Na borda HTTP o mesmo valor é
espelhado no campo `error_key`, dando à camada de rotas/templates/CLI uma única
string de erro estável; não há vocabulário de erro separado nem mapeamento.

## Status de adoção

A Fase 1 estabelece o contrato, o catálogo, o adapter e estes testes. As fases
seguintes emitem esses códigos conforme tocam cada serviço: compatibilidade
(Fase 3), identidade de manifest (Fase 5), integridade de persistência (Fase 6),
storage (Fase 7), dependências reversas (Fase 8). O doctor estrito (Fase 9)
migra o `PackageDoctorService` para o `DoctorFinding` canônico; até lá ele mantém
seus dicts de finding existentes.

## Códigos de finding do doctor

O `grave doctor` emite findings cujo campo `code` está **congelado e estável na
Alpha 2.0.0** — ferramentas e testes podem casar com eles. O conjunto atual
mistura dois estilos de nomenclatura por razões históricas.

Namespaced (`sdk.<área>.<detalhe>`):

```text
sdk.manifest.snapshot_stale
sdk.persistence.manifest_hash_mismatch
sdk.storage.orphaned_storage
sdk.storage.sqlite.database_unreadable
sdk.storage.sqlite.migration_dirty
sdk.storage.sqlite.migration_hash_mismatch
sdk.doctor.audit_error
```

Sem namespace (mantidos como estão por compatibilidade): `active_but_disabled`,
`capability_unknown`, `capability_forbidden`, `enabled_but_invalid`,
`package_missing_on_disk`, `bus.provider_conflict`, `bus.provider_not_found`,
entre outros.

A normalização completa para a convenção `sdk.<área>.<detalhe>` (ex.:
`sdk.dependency.missing`, `sdk.capability.unknown`,
`sdk.bus.provider_conflict`) é trabalho **pós-freeze** rumo à LTS 1. Quando
acontecer, os códigos sem namespace serão mantidos como aliases documentados para
não quebrar ferramentas existentes; o freeze não os renomeia.
