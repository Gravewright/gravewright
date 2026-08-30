# Slots

Slots are named extension points that collect values from modules without requiring direct dependencies between contributors.

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

The active server owns the slot registrar and decides how collected values are delivered to the host experience. The kernel only coordinates registration and disposal.

A slot value must exist and be exported through `get`. Slot names are contracts: document their expected value shape and version them carefully.

## Shared slot contract

The UI distribution documents this value shape:

```ts
interface ToolbarContribution {
  id: string;
  label: string;
  order?: number;
  invoke(): void | Promise<void>;
}
```

A module contributes:

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

Adding `v1` to the name makes incompatible future slot formats explicit rather than silently breaking contributors.
