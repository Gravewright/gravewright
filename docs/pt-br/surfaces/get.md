# `get`

`ref.get(name)` lê um valor listado em `exports.get`.

```ts
const roll = ctx.use("dice-roller").get("roll");
const result = roll(20);
```

Funções são valores comuns: `get()` autoriza e devolve a função; o consumidor a chama depois. Ela continua operando sobre a instância original da dependência.

`get()` falha quando o módulo está desabilitado, a instância não existe ou o nome não foi declarado. `ModuleRegistry` limita os nomes no TypeScript e o kernel repete a autorização em runtime.

Use funções em formato de comando para manter mutações e invariantes dentro do módulo proprietário.

## Valores e comandos

```ts
// Produtor
exports: { get: ["systemName", "roll"] },
create(_ctx) {
  return {
    systemName: "D20 Basic",
    roll(sides: number) {
      if (!Number.isInteger(sides) || sides < 2) throw new RangeError("invalid die");
      return Math.floor(Math.random() * sides) + 1;
    },
  };
}
```

```ts
// Consumidor
const dice = ctx.use("dice-roller");
const name = dice.get("systemName"); // string
const roll = dice.get("roll");       // (sides: number) => number
const result = roll(20);              // number
```

`dice.get("secretSeed")` é rejeitado em compile time e runtime quando não está exportado, mesmo que exista privadamente no produtor.
