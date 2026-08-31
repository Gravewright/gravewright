# Slots de room

Uma room renderiza exatamente um ponto DOM para cada classe canônica:
`gw-toolbar`, `gw-main`, `gw-sidebar`, `gw-chat`, `gw-overlay` e `gw-grid`.
O manifest declara cada região em `exposes.slots`, com `mounts: "one"` e
`contributions: "many"`.

Depois de `room.mount`, o compositor valida o DOM real. As contribuições são
ordenadas por `order`, nome do módulo e id. Cada uma recebe um filho novo, vazio e
exclusivo, impedindo que um módulo apague o DOM do vizinho. Os disposers rodam em
ordem inversa no unmount.

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

Publique em `exports.get` e associe com
`slots: { "gw-toolbar": ["chatButton"] }`.
