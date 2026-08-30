# `ModuleRegistry`

`ModuleRegistry` maps exact module names to inferred public APIs for TypeScript.

```ts
import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type DiceRollerAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "dice-roller": DiceRollerAPI;
  }
}
```

The quoted key is required because names may contain hyphens. `npm run types:sync` imports these declarations for side effects; the augmentation inside `types.ts` is what actually registers the type.

This is compile-time discovery only. Runtime authorization still comes from the manifest.

## Consumer inference

With the registry augmentation in place:

```ts
const dice = ctx.use("dice-roller");
const roll = dice.get("roll");
//    ^? (sides: number, actor?: string) => number

dice.get("missing");
//       ^ TypeScript error: "missing" is not a public key
```

Without the augmentation, a dynamically discovered name falls back to an untyped surface. Never replace the quoted module key with a kind such as `"addon"`; registration is per concrete module.
