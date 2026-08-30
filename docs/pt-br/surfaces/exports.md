# Exports

`exports` é a allowlist dos valores que atravessam a fronteira do módulo.

```ts
exports: {
  get: ["roll", "configure"],
  prop: ["status"],
}
```

- `get`: valores legíveis e comandos chamáveis.
- `prop`: propriedades legíveis e graváveis.
- `set`: superfície write-only legada e deprecated.

Todo nome deve existir na instância, ser único e não aparecer em categorias diferentes. Um valor retornado por `create()` mas omitido aqui permanece privado.

Prefira comandos como `configure(options)` em vez de publicar estado mutável.

## Instância privada versus pública

```ts
exports: { get: ["findCharacter"] },
create(_ctx) {
  const database = new Map([["elly", { name: "Elly", hp: 12 }]]);
  function normalize(name: string) { return name.trim().toLowerCase(); }
  return {
    database,  // retornado, mas privado
    normalize, // retornado, mas privado
    findCharacter(name: string) { return database.get(normalize(name)); },
  };
}
```

O consumidor obtém apenas `findCharacter`. `get("database")` é negado mesmo que a propriedade exista em runtime.
