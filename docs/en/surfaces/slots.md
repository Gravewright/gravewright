# Slots

Slots are named extension points that collect values from modules without requiring direct dependencies between contributors.

```ts
slots: { "gw-toolbar": ["toolbarButton"] },
exports: { get: ["toolbarButton"] },
```

```ts
const toolbarButton = {
  id: "fog-toggle",
  order: 20,
  mount(container: HTMLElement) {
    const button = container.ownerDocument.createElement("button");
    button.textContent = "Fog";
    container.append(button);
  },
};
```

The active server owns the slot registrar and decides how collected values are delivered to the host experience. The kernel only coordinates registration and disposal.

A slot value must exist and be exported through `get`. Slot names are contracts: document their expected value shape and version them carefully.

## Shared slot contract

The room protocol documents this value shape:

```ts
interface ToolbarContribution {
  id: string;
  order?: number;
  mount(container: HTMLElement): void | (() => void) | Promise<void | (() => void)>;
}
```

A module contributes:

```ts
const toolbarButton: ToolbarContribution = {
  id: "roll-d20",
  order: 20,
  mount(container) {
    const button = container.ownerDocument.createElement("button");
    button.textContent = "Roll d20";
    button.addEventListener("click", () => { roll(20); });
    container.append(button);
  },
};

slots: { "gw-toolbar": ["toolbarButton"] },
exports: { get: ["toolbarButton"] },
```

Canonical room slots are versioned together by `room_protocol`, currently
`gravewright.room/v1`. Custom non-room slots should carry an explicit protocol
version in their name when incompatible value formats may evolve.
