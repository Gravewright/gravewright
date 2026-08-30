# Slots

Slots são pontos de extensão nomeados que recebem valores de módulos sem criar dependências diretas entre contribuidores.

```ts
slots: { "room.toolbar": ["toolbarButton"] },
exports: { get: ["toolbarButton"] },
```

```ts
const toolbarButton = {
  id: "fog-toggle",
  label: "Fog",
};
```

O server ativo possui o registrar e decide como entregar os valores à experiência host. O kernel apenas coordena registro e dispose.

O valor deve existir e estar em `exports.get`. Nomes de slot são contratos: documente o formato esperado e versione mudanças cuidadosamente.

## Contrato compartilhado de slot

```ts
interface ToolbarContribution {
  id: string;
  label: string;
  order?: number;
  invoke(): void | Promise<void>;
}
```

```ts
const toolbarButton: ToolbarContribution = {
  id: "roll-d20",
  label: "Roll d20",
  order: 20,
  invoke: async () => { await roll(20); },
};

slots: { "room.toolbar.v1": ["toolbarButton"] },
exports: { get: ["toolbarButton"] },
```

O sufixo `v1` torna futuras incompatibilidades explícitas em vez de quebrar contribuidores silenciosamente.
