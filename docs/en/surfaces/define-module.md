# `defineModule`

`defineModule()` is the typed authoring helper for a module. It attaches an immutable definition to the default factory so tooling can generate `manifest.json` and `types.ts`.

```ts
export default defineModule({
  name: "dice-roller",
  kind: "addon",
  provider: "community",
  version: "1.0.0",
  exports: { get: ["roll"] },
  create(_ctx) {
    return { roll: (sides: number) => Math.floor(Math.random() * sides) + 1 };
  },
});
```

It provides inference; it does not replace static validation. The generated manifest remains the runtime boundary.

Rules:

- The default export must be the function returned by `defineModule()`.
- `name`, `kind`, `provider`, and `version` must match the generated manifest.
- Export and composition names must exist on the `create()` result.
- Do not perform external side effects while defining or importing the module.

Generate artifacts with `grave module build modules/dice-roller`.

## Example with every definition section

```ts
export default defineModule({
  name: "campaign-api",
  kind: "campaign",
  provider: "community",
  version: "1.0.0",
  dependencies: { "event-log": "^2.0.0" },
  routes: { "/campaign": "campaignRoute" },
  middleware: { "/campaign": ["authorize"] },
  slots: { "home.navigation": ["navigationItem"] },
  exports: { get: ["find", "campaignRoute", "authorize", "navigationItem"] },
  create(ctx) {
    const log = ctx.use("event-log");
    return {
      find: (id: string) => ({ id, title: "Example" }),
      campaignRoute: (_request, response) => response.json({ id: "demo" }),
      authorize: (_request, _response, next) => next(),
      navigationItem: { id: "campaign", label: "Campaign" },
    };
  },
});
```

`grave module build` turns the definition metadata into a static manifest. It never executes `create()`.
