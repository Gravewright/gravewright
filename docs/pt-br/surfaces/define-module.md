# `defineModule`

`defineModule()` é o helper tipado para autoria. Ele anexa uma definição imutável à factory default para o tooling gerar `manifest.json` e `types.ts`.

```ts
export default defineModule({
  name: "dice-roller",
  kind: "addon",
  provider: "community",
  version: "1.0.0",
  exports: { get: ["read", "write", "stat", "roll"] },
  create(_ctx) {
    return {
      read(_resource: string) { return undefined; },
      write(_resource: string, _value: unknown) {},
      stat() { return { ready: true }; },
      roll: (sides: number) => Math.floor(Math.random() * sides) + 1,
    };
  },
});
```

Ele fornece inferência, mas não substitui a validação estática. O manifest gerado continua sendo a fronteira runtime.

Regras:

- O export default deve ser a função retornada por `defineModule()`.
- Nome, kind, provider e versão devem coincidir com o manifest.
- Exports e pontos de composição devem existir no retorno de `create()`.
- Importar ou definir o módulo não deve causar efeitos externos.

Gere os artefatos com `grave module build modules/dice-roller`.

## Exemplo com todas as seções

```ts
export default defineModule({
  name: "campaign-api",
  kind: "system",
  provider: "community",
  version: "1.0.0",
  dependencies: { "event-log": "^2.0.0" },
  routes: { "/campaign": "campaignRoute" },
  middleware: { "/campaign": ["authorize"] },
  slots: { "home.navigation": ["navigationItem"] },
  exports: { get: ["read", "write", "stat", "find", "campaignRoute", "authorize", "navigationItem"] },
  create(ctx) {
    const log = ctx.use("event-log");
    return {
      read: (id: string) => ({ id, title: "Exemplo" }),
      write: (_id: string, _value: unknown) => {},
      stat: () => ({ ready: true }),
      find: (id: string) => ({ id, title: "Example" }),
      campaignRoute: (_request, response) => response.json({ id: "demo" }),
      authorize: (_request, _response, next) => next(),
      navigationItem: { id: "campaign", label: "Campaign" },
    };
  },
});
```

`grave module build` transforma os metadados em manifest estático sem executar `create()`.
