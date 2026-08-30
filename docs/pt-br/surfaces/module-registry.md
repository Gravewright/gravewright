# `ModuleRegistry`

`ModuleRegistry` associa nomes exatos às APIs públicas inferidas pelo TypeScript.

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

A chave entre aspas é obrigatória porque nomes podem conter hífen. `npm run types:sync` importa as declarações por efeito colateral; é o bloco dentro de `types.ts` que registra o tipo.

Isso resolve descoberta em compile time. A autorização runtime continua no manifest.

## Inferência no consumidor

```ts
const dice = ctx.use("dice-roller");
const roll = dice.get("roll");
//    ^? (sides: number, actor?: string) => number

dice.get("missing");
//       ^ erro TypeScript: "missing" não é uma chave pública
```

Sem augmentation, um nome descoberto dinamicamente cai na superfície sem tipo. A chave registra o módulo concreto, nunca o kind genérico `"addon"`.
