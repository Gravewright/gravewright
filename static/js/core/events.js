





(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  
  const wrappers = new WeakMap();

  function wrap(handler) {
    let byName = wrappers.get(handler);
    if (!byName) {
      byName = new Map();
      wrappers.set(handler, byName);
    }
    return byName;
  }

  function emit(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  function on(name, handler) {
    const listener = (event) => handler(event.detail, event);
    wrap(handler).set(name, listener);
    window.addEventListener(name, listener);
    return () => off(name, handler);
  }

  function once(name, handler) {
    const listener = (event) => {
      off(name, handler);
      handler(event.detail, event);
    };
    wrap(handler).set(name, listener);
    window.addEventListener(name, listener);
    return () => off(name, handler);
  }

  function off(name, handler) {
    const byName = wrappers.get(handler);
    const listener = byName && byName.get(name);
    if (listener) {
      window.removeEventListener(name, listener);
      byName.delete(name);
    }
  }

  Core.events = { emit, on, once, off };
})();
