




(function () {
  const registry = new Map();

  function normalizePlugin(plugin) {
    if (!plugin || typeof plugin !== "object") return {};
    const handlers = plugin.handlers && typeof plugin.handlers === "object" ? plugin.handlers : {};
    const slots = plugin.slots && typeof plugin.slots === "object" ? plugin.slots : {};
    return Object.freeze({
      handlers: Object.freeze({ ...handlers }),
      slots: Object.freeze({ ...slots }),
    });
  }

  function registerSystem(systemId, plugin) {
    const id = String(systemId || "").trim();
    if (!id) return false;
    registry.set(id, normalizePlugin(plugin));
    return true;
  }

  function pluginFor(systemId) {
    return registry.get(String(systemId || "")) || null;
  }

  function dispatch(systemId, name, payload) {
    const fn = pluginFor(systemId)?.handlers?.[name];
    if (typeof fn !== "function") return undefined;
    try {
      return fn(payload);
    } catch (error) {
      console.error("Gravewright combat runtime dispatch failed", { systemId, event: name, error });
      return undefined;
    }
  }

  function renderSlot(systemId, name, payload) {
    const fn = pluginFor(systemId)?.slots?.[name];
    if (typeof fn !== "function") return [];
    try {
      const result = fn(payload);
      if (Array.isArray(result)) return result.filter((node) => node instanceof Node);
      return result instanceof Node ? [result] : [];
    } catch (error) {
      console.error("Gravewright combat system slot failed", { systemId, slot: name, error });
      return [];
    }
  }

  function listSystems() {
    return Array.from(registry.keys());
  }

  window.GravewrightCombat = Object.freeze({
    dispatch,
    listSystems,
    pluginFor,
    registerSystem,
    renderSlot,
  });
})();
