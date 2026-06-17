




(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  function backend(session) {
    try {
      return session ? window.sessionStorage : window.localStorage;
    } catch {
      return null;
    }
  }

  function getJson(key, fallback, options) {
    const store = backend(options && options.session);
    if (!store) {
      return fallback;
    }
    try {
      const raw = store.getItem(key);
      if (raw == null) {
        return fallback;
      }
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  function setJson(key, value, options) {
    const store = backend(options && options.session);
    if (!store) {
      return false;
    }
    try {
      store.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  }

  function remove(key, options) {
    const store = backend(options && options.session);
    if (store) {
      try {
        store.removeItem(key);
      } catch {
        
      }
    }
  }

  
  function scoped(scopeParts, key) {
    const parts = Array.isArray(scopeParts) ? scopeParts : [scopeParts];
    return [...parts, key].filter((part) => part != null && part !== "").join(":");
  }

  Core.storage = { getJson, setJson, remove, scoped };
})();
