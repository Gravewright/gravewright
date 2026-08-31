# Slots

Slots são pontos de extensão nomeados que recebem valores de módulos sem criar dependências diretas entre contribuidores.

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

O server ativo possui o registrar e decide como entregar os valores à experiência host. O kernel apenas coordena registro e dispose.

O valor deve existir e estar em `exports.get`. Nomes de slot são contratos: documente o formato esperado e versione mudanças cuidadosamente.

## Contrato compartilhado de slot

```ts
interface ToolbarContribution {
  id: string;
  order?: number;
  mount(container: HTMLElement): void | (() => void) | Promise<void | (() => void)>;
}
```

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

Os slots canônicos de room são versionados em conjunto por `room_protocol`,
atualmente `gravewright.room/v1`. Slots customizados devem versionar o nome se o
formato de suas contribuições puder mudar de forma incompatível.
