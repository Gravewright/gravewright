# Mensageria Entre Pacotes

O canal estavel de interop entre pacotes e `sdk.bus.*`. Ele e local a aba da
mesa aberta e e a unica superficie de mensageria client-side no SDK 1.

## Capabilities

```json
{
  "capabilities": [
    "bus.publish",
    "bus.subscribe",
    "bus.request",
    "bus.provide"
  ],
  "interop": {
    "emits": {
      "my-addon.inventory.changed": {
        "schema": "schemas/events/inventory-changed.schema.json"
      }
    },
    "listens": {
      "other-addon.inventory.changed": { "optional": true }
    },
    "provides": {
      "my-addon.getWeight": {
        "params": "schemas/rpc/get-weight.request.json",
        "returns": "schemas/rpc/get-weight.response.json"
      }
    },
    "requires": {
      "other-addon.getPrice": { "optional": false }
    }
  }
}
```

Política estrita (Alpha 2.0.0 SDK Freeze) — todas as quatro direções são
hard-enforced em runtime:

`sdk.bus.publish` exige uma declaracao em `interop.emits`.
`sdk.bus.subscribe` exige uma declaracao em `interop.listens` (qualquer
namespace, incluindo eventos do core); um subscribe não declarado lança
`sdk.interop.event_undeclared`.
`sdk.bus.provide` exige uma declaracao em `interop.provides`.
`sdk.bus.request` exige uma declaracao em `interop.requires`; um request não
declarado lança `sdk.interop.method_undeclared`.

## Eventos

```ts
sdk.bus.subscribe("other-addon.inventory.changed", (payload) => {
  // ...
});

sdk.bus.publish("my-addon.inventory.changed", {
  itemId,
  count,
});
```

Um pacote so pode publicar ou prover no seu proprio namespace `{packageId}.*`.
Namespaces `gravewright.*`, `core.*`, `system.*` e `sdk.*` sao reservados para o
engine.

## Request / Provide

```ts
sdk.bus.provide("my-addon.getWeight", async (params, context) => {
  return computeWeight(params.itemId, context.callerPackageId);
});

const result = await sdk.bus.request(
  "my-addon.getWeight",
  { itemId },
  { timeoutMs: 2000 },
);

// { ok: true, value } | { ok: false, error: { code, message } }
```

Um provider recebe um contexto com `callerPackageId`, `providerPackageId`,
`userId`, `campaignId` e `permissions`. O bus preserva `BusResult` retornado
pelo provider e normaliza valores simples para `{ ok: true, value }`.

## Erros e Doctor

Erros comuns incluem `bus.provider_not_found`, `bus.provider_timeout`,
`bus.provider_conflict`, `bus.response_invalid`,
`sdk.interop.event_undeclared` e `sdk.interop.method_undeclared`.

O doctor detecta providers duplicados ativos na mesma campanha e metodos
obrigatorios declarados em `interop.requires` sem provider ativo.
