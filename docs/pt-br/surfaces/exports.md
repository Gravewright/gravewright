# Exports

`exports` é a allowlist dos valores que atravessam a fronteira do módulo.

```ts
exports: {
  get: ["roll", "configure", "status"],
}
```

`get` é a única superfície pública. Ela contém valores legíveis e comandos
chamáveis. Mudanças de estado usam comandos do próprio módulo, como
`configure(options)`, em vez de atribuição genérica entre módulos.

Todo nome deve existir na instância e ser único. Um valor retornado por `create()` mas omitido aqui permanece privado.

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
