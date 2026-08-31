# Seu primeiro módulo

Este tutorial cria um pequeno `addon` chamado `hello-table`. Ele guarda um valor
e expõe os três comandos comuns a todo módulo.

## Gere os arquivos

```bash
npm run grave -- new addon hello-table
```

O comando cria `modules/hello-table/` com `index.ts`, `manifest.json`,
`package.json` e `types.ts`. O módulo começa desativado.

## Implemente o comportamento

Use um factory como este em `index.ts`:

```ts
import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "hello-table",
  kind: "addon",
  provider: "community",
  version: "0.1.0",
  exports: { get: [] },
  create(_ctx) {
    const values = new Map<string, unknown>();
    return {
      read(resource: string) { return values.get(resource); },
      write(resource: string, value: unknown) { values.set(resource, value); },
      stat() { return { entries: values.size }; },
    };
  },
});
```

`read`, `write` e `stat` são comandos comuns. O vocabulário de recursos e os
retornos pertencem ao contrato do módulo; os nomes inspirados no POSIX não
significam acesso ao filesystem.

## Gere e confira os artefatos

```bash
npm run grave -- module build modules/hello-table
npm run grave -- module build modules/hello-table --check
npm run types:sync
npm run typecheck
npm run grave -- doctor
```

O build deriva o manifest e o registro TypeScript da definição. `--check` é
apropriado para CI porque falha quando os arquivos gerados estão desatualizados.

## Ative conscientemente

Defina `"hello-table": "active"` em `gravewright.modules.json` e execute
`doctor` novamente. Instalação e scaffold nunca ativam código automaticamente.

## Próximos passos

- Escolha o [kind](../concepts/module-kinds.md) correto.
- Entenda [dependências e capabilities](../concepts/dependencias-e-capabilities.md).
- Consulte o contrato de [`defineModule`](../surfaces/define-module.md).
- Copie um [template mínimo](../../minimal-templates/README.md).
