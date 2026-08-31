# `use`

`ctx.use(name)` retorna um `ModuleRef` para uma dependência declarada pelo nome exato.

```ts
dependencies: { "dice-roller": "^1.0.0" },
create(ctx) {
  const dice = ctx.use("dice-roller");
  return { attack: () => dice.get("roll")(20) };
}
```

A referência é um handle lógico e revogável, não a instância. Cada `get()` resolve a instância ativa atual.

O kernel rejeita o acesso quando a dependência não foi declarada, está ausente ou desabilitada, possui versão incompatível ou não publicou o export solicitado.

Não retenha valores extraídos se precisar de revogação: valores JavaScript já obtidos não podem ser recuperados.

## Produtor e consumidor completos

```ts
// Produtor: modules/dice-roller/index.ts
export default defineModule({
  name: "dice-roller", kind: "addon", provider: "community", version: "1.2.0",
  exports: { get: ["roll"] },
  create(_ctx) { return {
    read(_resource: string) { return undefined; }, write(_resource: string, _value: unknown) {}, stat() { return { ready: true }; },
    roll: (sides: number) => Math.floor(Math.random() * sides) + 1,
  }; },
});
```

```ts
// Consumidor: modules/combat/index.ts
export default defineModule({
  name: "combat", kind: "ruleset", provider: "community", version: "1.0.0",
  dependencies: { "dice-roller": "^1.2.0" },
  exports: { get: ["attack"] },
  create(ctx) {
    const dice = ctx.use("dice-roller");
    return {
      read(_resource: string) { return undefined; }, write(_resource: string, _value: unknown) {}, stat() { return { ready: true }; },
      attack: () => dice.get("roll")(20),
    };
  },
});
```

Remover `dependencies` faz a ativação falhar mesmo com `dice-roller` instalado. Exigir `^2.0.0` também falha enquanto a versão disponível for `1.2.0`.
