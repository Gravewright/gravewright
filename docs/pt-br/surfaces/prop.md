# `prop`

`exports.prop` publica uma propriedade através de `get()` e `set()`.

```ts
exports: { prop: ["status"] }
```

Use apenas quando uma propriedade compartilhada fizer parte real do contrato. É adequada para pequenos valores observáveis, não stores internos ou agregados complexos.

Como a escrita usa o caminho genérico deprecated, comandos explícitos são preferíveis em APIs novas. Um comando preserva invariantes e facilita mudanças futuras de representação.

## Exemplo de propriedade

```ts
exports: { prop: ["debug"] },
create(_ctx) { return { debug: false }; }
```

```ts
const logger = ctx.use("logger");
const enabled = logger.get("debug");
logger.set("debug", true);
```

Isso é aceitável para um boolean simples. Se habilitar debug exigir autorização, persistência, cleanup ou diagnóstico, publique `enableDebug()` e `disableDebug()`.
