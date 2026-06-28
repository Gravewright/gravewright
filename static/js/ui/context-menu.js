(function () {
  // Small shared right-click menu. Usage:
  //   GravewrightContextMenu.show(clientX, clientY, [
  //     { label, icon, danger, onClick }, { separator: true }, ...
  //   ]);
  const CM = (window.GravewrightContextMenu = window.GravewrightContextMenu || {});

  let el = null;

  function close() {
    if (!el) return;
    el.remove();
    el = null;
    document.removeEventListener("pointerdown", onPointerDown, true);
    document.removeEventListener("keydown", onKey, true);
    window.removeEventListener("blur", close);
    window.removeEventListener("resize", close);
  }

  function onPointerDown(event) {
    if (el && !el.contains(event.target)) close();
  }

  function onKey(event) {
    if (event.key === "Escape") close();
  }

  CM.close = close;

  CM.show = function show(clientX, clientY, items) {
    close();
    if (!Array.isArray(items) || !items.length) return;
    el = document.createElement("div");
    el.className = "context-menu";
    items.forEach((item) => {
      if (item.separator) {
        const sep = document.createElement("div");
        sep.className = "context-menu__sep";
        el.appendChild(sep);
        return;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.className = "context-menu__item" + (item.danger ? " is-danger" : "");
      const icon = item.icon ? `<i class="ph ${item.icon}" aria-hidden="true"></i>` : "";
      const label = document.createElement("span");
      label.textContent = item.label || "";
      button.innerHTML = icon;
      button.appendChild(label);
      button.addEventListener("click", () => {
        close();
        if (typeof item.onClick === "function") item.onClick();
      });
      el.appendChild(button);
    });
    document.body.appendChild(el);

    const rect = el.getBoundingClientRect();
    const x = Math.max(6, Math.min(clientX, window.innerWidth - rect.width - 8));
    const y = Math.max(6, Math.min(clientY, window.innerHeight - rect.height - 8));
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;

    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("keydown", onKey, true);
    window.addEventListener("blur", close);
    window.addEventListener("resize", close);
  };
})();
