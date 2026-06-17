




(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  
  function el(tag, className, attrs) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (attrs) {
      for (const key of Object.keys(attrs)) {
        const value = attrs[key];
        if (value == null || value === false) {
          continue;
        }
        if (key === "dataset" && typeof value === "object") {
          Object.assign(node.dataset, value);
        } else if (key in node && key !== "list" && key !== "form") {
          node[key] = value;
        } else {
          node.setAttribute(key, value === true ? "" : String(value));
        }
      }
    }
    return node;
  }

  function text(value) {
    return document.createTextNode(value == null ? "" : String(value));
  }

  function clear(node) {
    if (node) {
      while (node.firstChild) {
        node.removeChild(node.firstChild);
      }
    }
    return node;
  }

  function qs(root, selector) {
    return (root || document).querySelector(selector);
  }

  function qsa(root, selector) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  
  
  function delegate(root, selector, eventName, handler) {
    const host = root || document;
    const listener = (event) => {
      const match = event.target.closest(selector);
      if (match && host.contains(match)) {
        event.delegateTarget = match;
        handler.call(match, event);
      }
    };
    host.addEventListener(eventName, listener);
    return () => host.removeEventListener(eventName, listener);
  }

  function setHidden(node, hidden) {
    if (node) {
      node.hidden = Boolean(hidden);
    }
    return node;
  }

  Core.dom = { el, text, clear, qs, qsa, delegate, setHidden };
})();
