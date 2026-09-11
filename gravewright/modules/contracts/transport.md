# SDK 1.0 transport binding

[English](transport.md) · [Português](transport.pt-BR.md)

See the [module guide](../../../docs/en/modules.md) and [API reference](../../../docs/en/api.md) for complete examples and the newer domain API.

[`api.json`](api.json) describes lifecycle/storage semantics and has a document schema in [`schemas/protocol.json`](schemas/protocol.json). [`registry.json`](registry.json) references operation input/output schemas, event payloads and surface contexts. The server validates original SDK operation inputs and outputs at the call boundary. These JSON documents do not validate JavaScript callbacks or sandbox package execution.

The host opens a mount lease before a server operation. Calls bind module identity, table identity, `moduleSetRevision` and `mountId`, plus `sceneId` for scene mounts. The server checks membership, active revision, lease and native entity permissions before execution. Closing a mount closes its lease; later operations return `stale_context`. Local disposal immediately invalidates handles, but cannot undo an already committed mutation.

Original SDK JSON operations send `{name,payload,moduleSetRevision,mountId,sceneId?}` and return `{value}`. Errors use `{error}` and the seven public module codes. Multipart operations send the same envelope in `metadata` plus a `file` part. The server derives `{name,contentType,size}` from the actual upload. JavaScript `Blob` arguments map to that part; binary downloads become `{blob,name,contentType,size}`. JSON output schemas cover the download metadata, not the browser Blob itself. Fetch progress callbacks report completion and cancellation uses `AbortSignal`.

The separate browser domain API uses [`frontend.json`](frontend.json), sends `{domain,method,payload,requestId,...context}` and delegates to public Python services through `modules/frontend.py`. Native pages and installed modules share methods; module calls additionally require a lease and activation identity. Use the provided `api` or `host.call` for supported operations, and the provided storage/assets helpers for module persistence and files. URLs and internal browser globals are implementation details.

Lifecycle callbacks are implemented in `module-runtime.js`: `start` and mount callbacks may be asynchronous, `register` must be synchronous, and `stop` runs during teardown. This checkout does not include a TypeScript declaration package or an automated major-version compatibility checker. Maintain compatibility deliberately through registry/schema review and the Python/JavaScript contract tests.

Signed modules run in the main page without a JavaScript sandbox. The SDK does not expose a generic backend execution/SQL/renderer/module-to-module interface; this is an API boundary, not isolation from other browser APIs. The legacy actor events are inferred from authorized visible snapshots and should be treated as refresh hints, not an exactly-once mutation history.
