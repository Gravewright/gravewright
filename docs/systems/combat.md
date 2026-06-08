# System API v1: Combat

O combate combina configuracao declarativa em `rules/combat.gw.json`, CSS do sistema e hooks pequenos via `window.GravewrightCombat`. Sistemas nao substituem o renderer central do tracker.

Configuracao minima:

```json
{
  "version": 1,
  "turnOrder": {
    "strategy": "formula_sort",
    "label": "Iniciativa",
    "formula": "1d20 + @sheet.combat.initiative",
    "sort": "desc"
  },
  "resources": {
    "hp": {
      "label": "HP",
      "path": "sheet.hp.value",
      "maxPath": "sheet.hp.max",
      "min": 0
    }
  }
}
```

API JS publica:

```js
window.GravewrightCombat.registerSystem("dnd5e", {
  hooks: {
    participantMeta({ participant }) {
      return participant.actor_type === "monster" ? "Criatura" : "";
    },
    afterRender({ target }) {
      target.classList.add("dnd5e-combat-ready");
    }
  },
  slots: {
    participantActions({ participant }) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Marcar";
      button.dataset.participantId = participant.id;
      return button;
    }
  }
});
```

Hooks v1:

- `beforeRender({ panel, state, isGm })`
- `afterRender({ panel, state, target, isGm })`
- `participantMeta({ participant, state, isGm })`

Slots v1:

- `participantActions({ participant, state, isGm })`

Slots devem retornar um `Node` ou array de `Node`. Erros de hooks/slots sao isolados e registrados no console.
