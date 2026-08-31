# `create`

`create(context)` constrói uma instância runtime quando o módulo é ativado.

```ts
create(ctx) {
  const cache = new Map<string, unknown>();
  return {
    clear() { cache.clear(); },
    size() { return cache.size; },
  };
}
```

Estado privado deve ficar na closure. O objeto retornado pode ser grande, mas apenas exports e valores de composição declarados ficam visíveis externamente.

- Adie conexões, timers e listeners até a ativação ou um comando explícito.
- Uma exceção em `create()` falha a ativação e dispara rollback.
- Reativar cria outra instância; estado volátil não é preservado.
- Não use o contexto como atalho para dependências não declaradas.

## Exemplo de isolamento da instância

```ts
create(ctx) {
  let connected = false;
  const pending = new Map<string, Promise<unknown>>();
  return {
    async connect() {
      if (connected) return;
      connected = true;
      ctx.diagnostic.record({ event: "storage.connected", actor: "Backend", action: "Connect storage", status: "success" });
    },
    pendingCount() { return pending.size; },
  };
}
```

`connected` e `pending` são privados. Após disable e reativação, ambos voltam ao estado inicial porque uma nova instância é criada.
