# Room slots

A room renders exactly one DOM mount point for each canonical class:
`gw-toolbar`, `gw-main`, `gw-sidebar`, `gw-chat`, `gw-overlay`, and `gw-grid`.
Its manifest declares each under `exposes.slots` with `mounts: "one"` and
`contributions: "many"`.

After `room.mount`, the compositor validates the real DOM. Contributions are
sorted by `order`, module name, and contribution id. Each receives a new, empty,
exclusive child element, so one module cannot erase a neighbor's DOM. Disposers
run in reverse order during unmount.

```ts
const chatButton = {
  id: "open-chat",
  order: 20,
  mount(container: HTMLElement) {
    const button = container.ownerDocument.createElement("button");
    button.textContent = "Chat";
    container.append(button);
  },
};
```

Publish it in `exports.get`, then map it with
`slots: { "gw-toolbar": ["chatButton"] }`.
