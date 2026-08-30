(function () {
  const api = window.GravewrightDiceTray;
  if (!api?.registerExpressionModifier) return;

  const WILD_DIE = "1d6!";

  function inputFor(tray) {
    return tray.root.querySelector("[data-dice-bonus]");
  }

  function revealControls() {
    document.querySelectorAll("[data-dice-bonus]").forEach((input) => {
      const control = input.closest(".dice-bonus");
      if (control) control.hidden = false;
    });
  }

  api.registerExpressionModifier("swade-wild-die", {
    transform(expression, tray) {
      if (!expression || !inputFor(tray)?.checked || !tray.termos.length) return expression;
      const pool = tray.termos
        .map((term) => api.termoParaTexto({ ...term, explode: true }))
        .join("+");
      let result = `max(${pool},${WILD_DIE})`;
      if (tray.modificador > 0) result += `+${tray.modificador}`;
      else if (tray.modificador < 0) result += `-${Math.abs(tray.modificador)}`;
      return result;
    },
    reset(tray) {
      const input = inputFor(tray);
      if (input) input.checked = false;
    },
  });

  document.addEventListener("change", (event) => {
    const input = event.target.closest("[data-dice-bonus]");
    if (!input) return;
    const root = input.closest("[data-dice-tray]");
    const tray = root ? api.trays.get(root.dataset.roomId || "") : null;
    if (!tray) return;
    tray.formulaManual = "";
    tray.render();
  });

  revealControls();
})();
