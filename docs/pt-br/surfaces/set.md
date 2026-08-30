# `set` (deprecated)

`ref.set(name, value)` escreve em um nome declarado em `exports.set` ou `exports.prop`.

```ts
ctx.use("theme").set("mode", "dark");
```

Essa superfície permanece por compatibilidade, mas está deprecated: mutação cross-module genérica expõe estado compartilhado e ignora validações de domínio.

Prefira:

```ts
ctx.use("theme").get("setMode")("dark");
```

O módulo proprietário pode validar, diagnosticar, persistir ou rejeitar a transição. Módulos novos normalmente devem deixar `exports.set` vazio.

## API legada versus comando

Evite o campo gravável genérico:

```ts
exports: { set: ["volume"] },
create(_ctx) { return { volume: 50 }; }
```

Prefira um comando explícito:

```ts
exports: { get: ["setVolume", "volume"] },
create(ctx) {
  let current = 50;
  return {
    volume: () => current,
    setVolume(next: number) {
      if (!Number.isInteger(next) || next < 0 || next > 100) throw new RangeError("volume must be 0..100");
      current = next;
      ctx.diagnostic.record({ event: "audio.volume", actor: "User", action: "Change volume", status: "success", details: { volume: next } });
    },
  };
}
```

O comando controla validação e auditoria; consumidores não colocam o módulo em estado inválido.
