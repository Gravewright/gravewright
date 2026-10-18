// gravewright/maps/frontend/shared/config/i18n/text.js
var listeners = /* @__PURE__ */ new Set();
function notifyTextChange() {
  for (const listener of listeners)
    listener();
}
var currentLocale = () => "en";
var resolve = (source) => source;
function registerTextResolver(resolver, locale = () => "en") {
  resolve = resolver;
  currentLocale = locale;
  notifyTextChange();
  return () => {
    if (resolve === resolver) {
      resolve = (source) => source;
      currentLocale = () => "en";
      notifyTextChange();
    }
  };
}
function text(source, ...values) {
  return resolve(source).replace(/\{(\d+)\}/g, (match, index) => Number(index) < values.length ? String(values[Number(index)]) : match);
}
if (typeof window !== "undefined") {
  const apply = (detail) => registerTextResolver((source) => {
    const messages = detail.messages?.text ?? detail.messages ?? {};
    if (typeof messages[source] === "string") return messages[source];
    const translated = messages[source.trim()];
    return typeof translated === "string" ? source.replace(source.trim(), () => translated) : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
  else {
    const config = document.getElementById("gravewright-language");
    if (config) apply(JSON.parse(config.textContent));
  }
}

// gravewright/maps/frontend/shared/lib/dom/movable-resizable.js
var cleanups = /* @__PURE__ */ new WeakMap();
var windows = /* @__PURE__ */ new Set();
function mount(element) {
  const doc = element.ownerDocument, view = doc.defaultView;
  const originalZ = element.style.zIndex;
  const entry = { element, base: Number.parseInt(view.getComputedStyle(element).zIndex) || 7 };
  windows.add(entry);
  function raise() {
    const doc2 = element.ownerDocument;
    const peers = [...windows].filter((w) => w.element.ownerDocument === doc2 && w.base === entry.base);
    windows.delete(entry);
    windows.add(entry);
    for (const peer of peers)
      peer.element.classList.toggle("gw-window--focused", peer === entry);
    [...windows].filter((w) => w.element.ownerDocument === doc2 && w.base === entry.base).forEach((w, index) => {
      w.element.style.zIndex = String(w.base + index);
    });
  }
  element.classList.add("gw-movable-resizable");
  const handle = element.querySelector("[data-move-handle]") ?? element;
  handle.classList.add("gw-move-handle");
  let stopDrag = () => {
  };
  const pointerDown = (event) => {
    if (event.button !== 0 || event.target.closest("button,input,select,textarea,a,[data-no-move]"))
      return;
    stopDrag();
    const doc2 = element.ownerDocument, view2 = doc2.defaultView;
    const bounds = element.getBoundingClientRect(), offsetX = event.clientX - bounds.left, offsetY = event.clientY - bounds.top;
    Object.assign(element.style, { position: "fixed", width: `${bounds.width}px`, height: `${bounds.height}px`, left: `${bounds.left}px`, top: `${bounds.top}px`, right: "auto", bottom: "auto" });
    const move = (next) => {
      if (next.pointerId !== event.pointerId)
        return;
      element.style.left = `${Math.min(view2.innerWidth - 55, Math.max(55 - element.offsetWidth, next.clientX - offsetX))}px`;
      element.style.top = `${Math.min(view2.innerHeight - 55, Math.max(0, next.clientY - offsetY))}px`;
    };
    const up = () => {
      doc2.removeEventListener("pointermove", move);
      doc2.removeEventListener("pointerup", up);
      doc2.removeEventListener("pointercancel", up);
      view2.removeEventListener("blur", up);
      handle.classList.remove("gw-move-handle--active");
      stopDrag = () => {
      };
    };
    stopDrag = up;
    handle.classList.add("gw-move-handle--active");
    doc2.addEventListener("pointermove", move);
    doc2.addEventListener("pointerup", up);
    doc2.addEventListener("pointercancel", up);
    view2.addEventListener("blur", up);
    event.preventDefault();
  };
  const resize = () => {
    const box = element.getBoundingClientRect();
    if (box.top > view.innerHeight - 55)
      element.style.top = `${Math.max(0, view.innerHeight - 55)}px`;
    if (box.left > view.innerWidth - 55) {
      element.style.left = `${Math.max(0, view.innerWidth - 55)}px`;
      element.style.right = "auto";
    }
  };
  element.addEventListener("pointerdown", raise, true);
  element.addEventListener("focusin", raise);
  handle.addEventListener("pointerdown", pointerDown);
  view.addEventListener("resize", resize);
  raise();
  cleanups.set(element, () => {
    stopDrag();
    windows.delete(entry);
    element.style.zIndex = originalZ;
    element.classList.remove("gw-window--focused");
    element.removeEventListener("pointerdown", raise, true);
    element.removeEventListener("focusin", raise);
    handle.removeEventListener("pointerdown", pointerDown);
    view.removeEventListener("resize", resize);
  });
}
var vMovableResizable = { mounted: mount, unmounted(element) {
  cleanups.get(element)?.();
  cleanups.delete(element);
} };

// gravewright/maps/frontend/native/widget.js
var CELL = /* @__PURE__ */ Symbol("cell");
var expressions = /* @__PURE__ */ new Map();
function evaluate(code, ctx, eventMode = false) {
  const key = (eventMode ? "event:" : "value:") + code;
  let fn = expressions.get(key);
  if (!fn) {
    fn = new Function("scope", `with(scope){${eventMode ? code : "return " + code}}`);
    expressions.set(key, fn);
  }
  return fn(ctx);
}
function scoped(base, extras = {}) {
  return new Proxy(extras, { has: (_, key) => key !== Symbol.unscopables, get: (o, k) => k === Symbol.unscopables ? void 0 : k in o ? o[k] : base[k], set: (o, k, v) => {
    if (k in o)
      o[k] = v;
    else
      base[k] = v;
    return true;
  } });
}
function className(v) {
  return typeof v === "object" ? Array.isArray(v) ? v.map(className).join(" ") : Object.keys(v || {}).filter((k) => v[k]).join(" ") : v ?? "";
}
function setAttr(el, key, value) {
  if (key === "key" || key === "ref")
    return;
  if (key === "style" && value && typeof value === "object") {
    for (const [k, v] of Object.entries(value)) {
      if (k.startsWith("--")) el.style.setProperty(k, v);
      else el.style[k] = v;
    }
    return;
  }
  if (key === "class")
    value = className(value);
  if (["disabled", "checked", "selected", "multiple", "required", "hidden"].includes(key)) {
    el.toggleAttribute(key, !!value);
    return;
  }
  if (value === void 0 || value === null || value === false && !key.startsWith("aria-"))
    el.removeAttribute(key);
  else
    el.setAttribute(key, String(value));
}
function dispose(el) {
  el._instance?.destroy();
  el._cleanup?.();
  for (const child of el.childNodes)
    dispose(child);
}
function patch(parent, fresh) {
  const nodes = [...fresh.childNodes];
  for (let i = 0; i < nodes.length; i++) {
    const next = nodes[i];
    let old = parent.childNodes[i];
    if (!old || old.nodeName !== next.nodeName || old._key !== next._key) {
      if (old) {
        dispose(old);
        old.replaceWith(next);
      } else
        parent.append(next);
      old = next;
    } else if (next.nodeType === 3) {
      if (old.textContent !== next.textContent)
        old.textContent = next.textContent;
      continue;
    }
    if (next.nodeType !== 1)
      continue;
    if (old !== next) {
      for (const name of ["gw-movable-resizable", "gw-window--focused", "gw-move-handle", "gw-move-handle--active"])
        if (old.classList.contains(name)) next.classList.add(name);
      for (const attr of [...old.attributes])
        if (!next.hasAttribute(attr.name) && attr.name !== "style" && !(old.nodeName === "DETAILS" && attr.name === "open") && !(old.nodeName === "CANVAS" && ["width", "height"].includes(attr.name)))
          old.removeAttribute(attr.name);
      for (const attr of next.attributes)
        if (old.getAttribute(attr.name) !== attr.value)
          old.setAttribute(attr.name, attr.value);
      for (const name of old._events || [])
        old[name] = null;
      for (const name of next._events || [])
        old[name] = next[name];
      old._events = next._events;
    }
    if (next._component) {
      if (!old._instance)
        old._instance = next._component(old, next._options);
      else
        old._instance.update(next._options.props, next._options);
    } else if (old !== next)
      patch(old, next);
    else {
      const content = document.createDocumentFragment();
      content.append(...old.childNodes);
      patch(old, content);
    }
    if (next._ref)
      next._ref.value = old;
    if (next._value !== void 0 && old.value !== String(next._value))
      old.value = String(next._value);
    if (next._checked !== void 0)
      old.checked = next._checked;
    if (next._movable && !old._cleanup) {
      next._movable.mounted(old);
      old._cleanup = () => next._movable.unmounted(old);
    }
  }
  while (parent.childNodes.length > nodes.length) {
    dispose(parent.lastChild);
    parent.lastChild.remove();
  }
}
function model(options) {
  return { [CELL]: true, get value() {
    return options.props.modelValue;
  }, set value(v) {
    options.props.modelValue = v;
    options.emit("update:modelValue", v);
  } };
}
function widget(markup, setup) {
  return function mount2(host, initial) {
    const options = { ...initial, props: { ...initial.props } };
    let stopped = false, queued = false, rendering = false, locals = {}, exposed = {};
    const mounted = [], unmount = [], watches = [];
    const portal = document.createElement("div");
    portal.style.display = "contents";
    document.body.append(portal);
    const schedule = () => {
      if (!queued && !stopped) {
        queued = true;
        queueMicrotask(() => {
          queued = false;
          if (!stopped)
            render();
        });
      }
    };
    const api = {
      ref(value) {
        return { [CELL]: true, get value() {
          return value;
        }, set value(next) {
          if (value !== next) {
            value = next;
            if (!(next instanceof Node))
              schedule();
          }
        } };
      },
      computed(read) {
        return { [CELL]: true, get value() {
          return read();
        } };
      },
      watch(read, fn, opts = {}) {
        const get = typeof read === "function" ? read : () => read.value;
        const entry = { get, fn, value: get(), signature: void 0 };
        entry.signature = signature(entry.value);
        watches.push(entry);
        if (opts.immediate)
          fn(entry.value);
      },
      onMounted(fn) {
        mounted.push(fn);
      },
      onBeforeUnmount(fn) {
        unmount.push(fn);
      },
      nextTick() {
        return Promise.resolve();
      },
      defineExpose(value) {
        exposed = value;
      }
    };
    function signature(value) {
      try {
        return JSON.stringify(value);
      } catch {
        return value;
      }
    }
    const ctx = new Proxy({}, { has: () => true, get: (_, key) => {
      if (key === Symbol.unscopables)
        return;
      const v = key in locals ? locals[key] : key in options.props ? options.props[key] : globalThis[key];
      return v?.[CELL] ? v.value : v;
    }, set: (_, key, v) => {
      if (locals[key]?.[CELL])
        locals[key].value = v;
      else if (key in locals)
        locals[key] = v;
      else
        options.props[key] = v;
      schedule();
      return true;
    } });
    locals = setup(options, api);
    function trigger(code, scope, event, args) {
      const valueScope = scoped(scope, { $event: event, $args: args });
      try {
        const bare = code.trim().replace(/;$/, "");
        let result;
        if (/^[\w$.]+$/.test(bare)) {
          const fn = evaluate(bare, valueScope);
          result = typeof fn === "function" ? fn(...args || [event]) : fn;
        } else
          result = evaluate(code, valueScope, true);
        if (result?.finally)
          result.finally(schedule).catch(console.error);
      } finally {
        schedule();
      }
    }
    function children(list, scope, svg = false, portalTarget) {
      const fragment = document.createDocumentFragment();
      let branch = false;
      for (const item of list) {
        if (item.when !== void 0) {
          branch = !!evaluate(item.when, scope);
          if (!branch)
            continue;
        } else if (item.otherwiseWhen !== void 0) {
          if (branch)
            continue;
          branch = !!evaluate(item.otherwiseWhen, scope);
          if (!branch)
            continue;
        } else if (item.otherwise) {
          if (branch)
            continue;
          branch = true;
        } else if (item.text === void 0 || item.text.trim())
          branch = false;
        if (item.each) {
          const values = evaluate(item.each.value, scope) || [];
          let i = 0;
          for (const [key, value] of Array.isArray(values) ? values.map((v, i2) => [i2, v]) : Object.entries(values)) {
            const tuple = item.each.names[0]?.startsWith("[");
            const extra = tuple ? Object.fromEntries(item.each.names.map((name, index) => [name.replace(/[\[\]]/g, "").trim(), value[index]])) : { [item.each.names[0]]: value };
            if (!tuple && item.each.names[1])
              extra[item.each.names[1]] = key;
            if (!tuple && item.each.names[2])
              extra[item.each.names[2]] = i++;
            fragment.append(children([{ ...item, each: void 0, when: void 0 }], scoped(scope, extra), svg, portalTarget));
          }
          continue;
        }
        if (item.text !== void 0 || item.value !== void 0) {
          fragment.append(document.createTextNode(item.text ?? String(evaluate(item.value, scope) ?? "")));
          continue;
        }
        if (item.tag === "Teleport") {
          portalTarget.append(children(item.children, scope, false, portalTarget));
          continue;
        }
        if (item.tag === "template") {
          fragment.append(children(item.children, scope, svg, portalTarget));
          continue;
        }
        if (item.tag === "slot") {
          fragment.append(options.slots?.() || document.createDocumentFragment());
          continue;
        }
        let tag = item.tag === "component" ? evaluate(item.bind.is, scope) : item.tag;
        const attrs = { ...item.attrs, ...item.spread ? evaluate(item.spread, scope) : {} };
        for (const [k, v] of Object.entries(item.bind))
          attrs[k] = evaluate(v, scope);
        if (item.bind.class)
          attrs.class = [item.attrs.class, attrs.class];
        if (typeof tag === "string" && tag.startsWith("Ph")) {
          const template = document.querySelector("#map-native-icons");
          const svgIcon = template?.content.querySelector(`[data-icon="${tag}"][data-weight="${attrs.weight || "regular"}"]`)?.firstElementChild;
          if (svgIcon) {
            const el2 = svgIcon.cloneNode(true);
            for (const [k, v] of Object.entries(attrs))
              setAttr(el2, k, v);
            fragment.append(el2);
          }
          continue;
        }
        const component = typeof tag === "function" ? tag : scope[tag];
        const isComponent = typeof component === "function" && (/^[A-Z]/.test(String(tag)) || typeof tag === "function");
        const el = svg && !isComponent || tag === "svg" ? document.createElementNS("http://www.w3.org/2000/svg", tag) : document.createElement(isComponent ? "div" : tag);
        el._key = attrs.key ?? (isComponent ? tag : void 0);
        if (isComponent) {
          el.style.display = "contents";
          el._component = component;
          const props = {};
          for (const [k, v] of Object.entries(attrs))
            props[k.replace(/-([a-z])/g, (_, x) => x.toUpperCase())] = v;
          if (item.model)
            props.modelValue = evaluate(item.model.path, scope);
          el._options = { ...options, props, slots: () => children(item.children, scope, false, portalTarget), emit: (name, ...args) => {
            if (name === "update:modelValue" && item.model) {
              evaluate(item.model.path + "=$event", scoped(scope, { $event: args[0] }), true);
              schedule();
            }
            for (const handler of item.events)
              if (handler.event === name)
                trigger(handler.code, scope, args[0], args);
          } };
        } else {
          for (const [k, v] of Object.entries(attrs))
            setAttr(el, k, v);
          if (["input", "textarea", "select"].includes(tag) && attrs.value !== void 0)
            el._value = attrs.value;
          if (attrs.checked !== void 0)
            el._checked = !!attrs.checked;
          if (attrs.ref)
            el._ref = locals[attrs.ref];
          if (item.movable)
            el._movable = locals.vMovableResizable;
          if (item.show && !evaluate(item.show, scope))
            el.style.display = "none";
          el._events = [];
          if (item.model) {
            const val = evaluate(item.model.path, scope);
            if (attrs.type === "checkbox")
              el._checked = !!val;
            else
              el._value = val ?? "";
            const name = tag === "select" ? "onchange" : "oninput";
            el._events.push(name);
            el[name] = (event) => {
              let value = attrs.type === "checkbox" ? event.target.checked : event.target.value;
              if (item.model.mods.includes("number"))
                value = Number(value);
              evaluate(item.model.path + "=$event", scoped(scope, { $event: value }), true);
              schedule();
            };
            if (attrs.type === "checkbox") {
              el.onclick = el.onchange = el.oninput;
              el._events.push("onclick", "onchange");
            }
          }
          for (const handler of item.events) {
            const name = "on" + handler.event;
            const previous = el[name];
            el._events.push(name);
            el[name] = (event) => {
              const keys = { enter: "Enter", esc: "Escape", escape: "Escape", space: " " };
              for (const mod of handler.mods)
                if (keys[mod] && event.key !== keys[mod])
                  return;
              if (handler.mods.includes("self") && event.target !== event.currentTarget)
                return;
              if (handler.mods.includes("stop"))
                event.stopPropagation();
              if (handler.mods.includes("prevent"))
                event.preventDefault();
              previous?.(event);
              trigger(handler.code, scope, event);
            };
          }
          el.append(children(item.children, scope, svg || tag === "svg", portalTarget));
        }
        fragment.append(el);
      }
      return fragment;
    }
    function render() {
      if (rendering || stopped)
        return;
      rendering = true;
      try {
        for (const watch of watches) {
          const value = watch.get(), next = signature(value);
          if (next !== watch.signature) {
            const old = watch.value;
            watch.signature = next;
            watch.value = value;
            watch.fn(value, old);
          }
        }
        const freshPortal = document.createDocumentFragment();
        const fresh = children(markup, ctx, false, freshPortal);
        patch(host, fresh);
        patch(portal, freshPortal);
      } finally {
        rendering = false;
      }
    }
    render();
    for (const fn of mounted)
      fn();
    schedule();
    return { update(props, next = {}) {
      Object.assign(options.props, props);
      for (const key of ["emit", "slots"])
        if (next[key])
          options[key] = next[key];
      schedule();
    }, get scope() {
      return ctx;
    }, call(name, ...args) {
      const result = (exposed[name] || ctx[name])?.(...args);
      schedule();
      return result;
    }, destroy() {
      if (stopped)
        return;
      stopped = true;
      for (const fn of unmount)
        fn();
      for (const node of host.childNodes)
        dispose(node);
      host.replaceChildren();
      dispose(portal);
      portal.remove();
    } };
  };
}

// gravewright/maps/frontend/features/lighting/ui/LightEditor.native.js
var PhX = "PhX";
var PhTrash = "PhTrash";
var LightEditor_native_default = widget([{ "tag": "section", "attrs": { "class": "gw-window light-editor", "role": "dialog" }, "bind": { "aria-label": "(gwText('Light source'))", "role": "(transactional ? 'group' : 'dialog')" }, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "wheel", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "light-editor__header", "data-move-handle": "" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Light source'))" }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close'))", "disabled": "(transactional && busy)" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "light-editor__body" }, "bind": { "inert": "(transactional && busy)" }, "events": [], "children": [{ "tag": "template", "attrs": {}, "bind": { "key": "(range.key)" }, "events": [], "children": [{ "tag": "label", "attrs": { "class": "light-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(range.name)" }] }, { "tag": "div", "attrs": { "class": "light-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range" }, "bind": { "min": "(range.min)", "max": "(Math.max(range.max, draft[range.key]))", "step": "(range.step)", "disabled": "(range.key === 'dim_radius' && draft.dim_radius === 0)", "aria-label": "(range.name)" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft[range.key])", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(range.key === 'dim_radius' && draft.dim_radius === 0 ? '\u221E' : draft[range.key])" }, { "value": "(['angle', 'rotation'].includes(range.key) ? '\xB0' : '')" }] }] }], "when": "(range.key !== 'rotation' || draft.angle < 360)" }, { "tag": "label", "attrs": { "class": "light-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "checked": "(draft.dim_radius === 0)" }, "events": [{ "event": "change", "code": "unlimited;", "mods": [] }], "children": [] }, { "value": "(gwText('Unlimited'))" }], "when": "(range.key === 'dim_radius')" }], "each": { "names": ["range"], "value": "(ranges)" } }, { "tag": "div", "attrs": { "class": "light-editor__pair" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "light-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Animation'))" }] }, { "tag": "select", "attrs": {}, "bind": { "aria-label": "(gwText('Animation'))" }, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [{ "tag": "option", "attrs": { "value": "none" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Steady'))" }] }, { "tag": "option", "attrs": { "value": "torch" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Torch'))" }] }, { "tag": "option", "attrs": { "value": "pulse" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Pulse'))" }] }, { "tag": "option", "attrs": {}, "bind": { "value": "(draft.animation)" }, "events": [], "children": [{ "value": "(draft.animation)" }], "when": "(!['none', 'torch', 'pulse'].includes(draft.animation))" }], "model": { "path": "(draft.animation)", "mods": [] } }] }, { "tag": "label", "attrs": { "class": "light-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Color'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Color'))" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.color)", "mods": [] } }] }] }, { "tag": "label", "attrs": { "class": "light-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "aria-label": "(gwText('On'))" }, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.enabled)", "mods": [] } }, { "value": "(gwText('On'))" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Radii use grid cells. Walls block light.'))" }] }, { "tag": "p", "attrs": { "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "(props.error)" }], "when": "(props.error)" }, { "tag": "footer", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": { "role": "status" }, "bind": {}, "events": [], "children": [{ "value": "(busy ? gwText('Saving\u2026') : gwText('Changes saved automatically'))" }], "when": "(!transactional)" }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('remove');", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Remove'))" }], "when": "(!transactional)" }, { "tag": "button", "attrs": { "type": "button", "data-native-editor-cancel": "" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "value": "(gwText('Cancel'))" }], "when": "(transactional)" }, { "tag": "button", "attrs": { "type": "button", "data-native-editor-save": "" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('save');", "mods": [] }], "children": [{ "value": "(gwText('Save'))" }], "when": "(transactional)" }] }] }], "movable": true }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const draft = model(options);
  const emit = options.emit;
  const ranges = [{ key: "bright_radius", get name() {
    return text("Bright radius");
  }, max: 30, step: 0.5, min: 0 }, { key: "dim_radius", get name() {
    return text("Dim radius");
  }, max: 60, step: 0.5, min: 0 }, { key: "intensity", get name() {
    return text("Intensity");
  }, max: 1, step: 0.05, min: 0 }, { key: "angle", get name() {
    return text("Cover");
  }, max: 360, step: 5, min: 5 }, { key: "rotation", get name() {
    return text("Direction");
  }, max: 355, step: 5, min: 0 }];
  function unlimited(e) {
    draft.value.dim_radius = e.target.checked ? 0 : Math.max(6, draft.value.bright_radius);
    emit("change");
  }
  return { gwText: text, PhX, PhTrash, vMovableResizable, props, draft, ranges, unlimited, emit: options.emit };
});

// gravewright/maps/frontend/features/scene-layers/lib/shader-presets.js
var shaderPresets = [
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-1",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Arcane Sun");
    },
    get "description"() {
      return text("Radiant disk with a turbulent corona, long rays, and sparks.");
    },
    "color": "#8f6bff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;float d=length(p);float a0=atan(p.y,p.x);\nfloat corona=gwpFbm(vec2(a0*3.4,t*0.22)+vec2(d*5.0,-t*0.11));\nfloat core=exp(-d*d*6.2);float rim=gwpBand(d,0.61+0.035*sin(t*1.7),0.055);\nfloat rayMask=pow(max(0.0,cos(a0*9.0+t*0.9+corona*2.7)),10.0);\nfloat rays=rayMask*exp(-d*1.45)*(1.0-smoothstep(0.18,0.95,d));\nfloat sparks=pow(gwpNoise(p*18.0+vec2(t,-t*0.7)),16.0)*(1.0-smoothstep(0.28,1.0,d));\nfloat e=(core*1.15+rim*0.9+rays*0.72+sparks*0.45)*(0.78+0.32*corona)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.92,0.72),gwpSat(core+rim+rays*0.4));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1.1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-2",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Solar Star");
    },
    get "description"() {
      return text("Pulsing star with two flare patterns and a living corona.");
    },
    "color": "#ff9a32",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float d=length(p);float ang=atan(p.y,p.x);\nfloat disk=exp(-d*d*9.0);float pulse=0.82+0.18*sin(t*3.0);\nfloat flareA=pow(max(0.0,cos(ang*14.0-t*1.6)),22.0)*exp(-d*1.8);\nfloat flareB=pow(max(0.0,cos(ang*5.0+t*0.8)),12.0)*exp(-d*2.4);\nfloat crown=gwpBand(d,0.48+0.03*sin(ang*7.0+t*2.0),0.035);\nfloat grain=0.7+0.45*gwpFbm(p*7.0+vec2(t*0.25));\nfloat e=(disk*1.35*pulse+crown+flareA*0.9+flareB*0.45)*grain*uIntensity;\nfloat a=gwpSat(e);\nvec3 hot=mix(uColor,vec3(1.0,0.98,0.82),gwpSat(disk*1.5+crown));\nfinalColor=vec4(hot*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 0.9,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "orb-3",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Glacial Core");
    },
    get "description"() {
      return text("Hexagonal crystal with facets, spikes, and shimmering frost.");
    },
    "color": "#58cfff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;float d=length(p);float ang=atan(p.y,p.x);\nfloat facets=abs(cos(ang*3.0));\nfloat crystalR=0.52+0.13*facets;\nfloat shell=gwpBand(d,crystalR,0.035);\nfloat spokes=pow(abs(cos(ang*6.0)),18.0)*(1.0-smoothstep(0.08,0.82,d));\nfloat inner=exp(-d*d*13.0)*(0.8+0.2*sin(t*2.0));\nfloat frost=pow(gwpNoise(p*16.0-vec2(t*0.2)),10.0)*gwpDisk(p,0.75,0.2);\nfloat e=(shell*1.15+spokes*0.52+inner+frost*0.28)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.92,1.0,1.0),gwpSat(shell+inner+frost*0.4));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1.1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "orb-4",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Crimson Eye");
    },
    get "description"() {
      return text("Living arcane eye with an iris, vertical pupil, and pulsing veins.");
    },
    "color": "#ff253a",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;\np=gwpRot(p,0.08*sin(t*0.7));\nfloat d=length(p);\nfloat eye=1.0-smoothstep(0.0,0.055,abs(length(vec2(p.x,p.y*1.8))-0.63));\nfloat iris=gwpBand(d,0.34+0.025*sin(t*1.7),0.12)*(0.65+0.35*gwpFbm(p*8.0+vec2(t*0.2)));\nfloat pupil=1.0-smoothstep(0.035,0.11,abs(p.x));\npupil*=gwpDisk(vec2(p.x,p.y*1.5),0.31,0.07);\nfloat veins=pow(max(0.0,sin(atan(p.y,p.x)*11.0+d*24.0+gwpFbm(p*5.0)*4.0)),12.0)*gwpDisk(p,0.62,0.12);\nfloat e=(eye*0.85+iris*0.9+veins*0.42)*(1.0-pupil*0.8)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.55,0.32),iris*0.65);\nc*=1.0-pupil*0.75;\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.6,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-5",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Spectral Moon");
    },
    get "description"() {
      return text("Spectral crescent with a halo, motes, and ghostly mist.");
    },
    "color": "#b9d5ff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.25;\nfloat d1=length(p-vec2(-0.06,0.0));\nfloat moon=gwpDisk(p-vec2(-0.06,0.0),0.58,0.08)*(1.0-gwpDisk(p-vec2(0.18,0.02),0.52,0.08));\nfloat halo=gwpBand(d1,0.61,0.13)*0.65;\nfloat ghosts=gwpFbm(p*4.5+vec2(t*0.18,-t*0.08))*gwpBand(d1,0.54,0.34);\nfloat motes=pow(gwpNoise(p*14.0+vec2(0.0,t*0.2)),18.0)*gwpDisk(p,0.9,0.2);\nfloat e=(moon+halo+ghosts*0.24+motes*0.38)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.94,0.98,1.0),moon+halo*0.45);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-1",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Violet Portal");
    },
    get "description"() {
      return text("Spiral ring with a turbulent inner surface.");
    },
    "color": "#9b55ff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;float d=length(p);float ang=atan(p.y,p.x);\nfloat warp=(gwpFbm(p*4.0+vec2(t))-0.5)*0.16;\nfloat ring=gwpBand(d,0.69+warp,0.06);\nfloat spiral=0.5+0.5*sin(ang*5.0-d*15.0+t*3.0+warp*10.0);\nfloat inner=(1.0-smoothstep(0.08,0.67,d))*(0.25+0.75*gwpFbm(gwpRot(p,t*0.15)*4.0));\nfloat e=(ring*(0.65+0.75*spiral)+inner*0.5)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0),ring*0.9);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.95,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "portal-2",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Infernal Rift");
    },
    get "description"() {
      return text("Jagged, glowing, unstable vertical rift.");
    },
    "color": "#ff3b18",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.1;\nvec2 q=gwpRot(p,0.17*sin(t*0.3));\nfloat jag=(gwpFbm(vec2(q.y*5.0,t*0.35))-0.5)*0.28;\nfloat crack=gwpLine(q.x+jag,0.055+0.018*sin(q.y*18.0+t*2.0));\nfloat body=crack*(1.0-smoothstep(0.82,1.05,abs(q.y)));\nfloat glow=exp(-abs(q.x+jag)*7.0)*(1.0-smoothstep(0.76,1.05,abs(q.y)));\nfloat teeth=pow(max(0.0,sin(q.y*19.0+t*1.7+gwpFbm(q*4.0)*3.0)),10.0)*glow;\nfloat e=(body*1.2+glow*0.65+teeth*0.38)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.72,0.22),body+teeth*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-3",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Fey Passage");
    },
    get "description"() {
      return text("A crown of petals and runes with a shimmering interior.");
    },
    "color": "#55e89b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;float d=length(p);float ang=atan(p.y,p.x);\nfloat petals=0.56+0.11*cos(ang*7.0+t*0.7);\nfloat wreath=gwpBand(d,petals,0.055);\nfloat runes=pow(max(0.0,cos(ang*14.0-t*0.4)),16.0)*gwpBand(d,0.73,0.09);\nfloat shimmer=(1.0-smoothstep(0.12,0.7,d))*(0.3+0.7*gwpFbm(p*5.0+vec2(t*0.15,-t*0.2)));\nfloat e=(wreath+runes*0.65+shimmer*0.34)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.95,1.0,0.82),wreath+runes*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 0.9,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-4",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Astral Hole");
    },
    get "description"() {
      return text("Empty core with gravitational lensing, a disk, and stars.");
    },
    "color": "#467cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;float d=length(p);float ang=atan(p.y,p.x);\nfloat hole=1.0-smoothstep(0.22,0.36,d);\nfloat lens=gwpBand(d,0.48+0.03*sin(ang*4.0+t),0.055);\nfloat acc=pow(0.5+0.5*sin(ang*4.0-d*22.0+t*2.2),5.0)*gwpBand(d,0.62,0.25);\nfloat stars=pow(gwpNoise(p*22.0+vec2(t*0.03)),24.0)*gwpDisk(p,0.88,0.12)*(1.0-hole);\nfloat e=(lens*1.15+acc*0.7+stars*0.7)*(1.0-hole*0.92)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.88,0.95,1.0),lens+stars);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.5,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "portal-5",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Golden Seal");
    },
    get "description"() {
      return text("Precise ritual geometry with rings, glyphs, and symmetrical rays.");
    },
    "color": "#ffc95b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;float d=length(p);float ang=atan(p.y,p.x);\nfloat r1=gwpBand(d,0.35,0.018);\nfloat r2=gwpBand(d,0.58,0.022);\nfloat r3=gwpBand(d,0.76,0.018);\nfloat spokes=pow(abs(cos(ang*6.0+t*0.25)),30.0)*step(0.34,d)*(1.0-step(0.76,d));\nfloat glyph=pow(max(0.0,cos(ang*12.0+t*0.15)),28.0)*gwpBand(d,0.67,0.065);\nvec2 q1=gwpRot(p,3.14159/6.0);\nvec2 q2=gwpRot(p,-3.14159/6.0);\nfloat triangle=gwpLine(max(abs(q1.x)*0.866+q1.y*0.5,q2.x*0.866-q2.y*0.5)-0.38,0.018);\nfloat e=(r1+r2+r3+spokes*0.45+glyph*0.8+triangle*0.3)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.96,0.7),gwpSat(r1+r2+r3+glyph));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 2.2,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-1",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Swamp Mist");
    },
    get "description"() {
      return text("Layered banks of damp mist that respond to light.");
    },
    "color": "#708f68",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;\nvec2 q=p*2.4+vec2(t*0.7,t*0.16);\nfloat low=gwpFbm(q+vec2(0.0,p.y*0.4));\nfloat high=gwpFbm(q*2.1-vec2(t*0.22,0.0));\nfloat bank=smoothstep(0.42,0.78,low+high*0.35);\nfloat strata=0.58+0.42*sin(p.y*5.0+low*4.0);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=bank*strata*uIntensity*0.7*mix(0.55,1.0,lit);\nvec3 c=mix(uColor,uColor+L.rgb*0.45,lit);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.9,
    "scale": 1.8,
    "speed": 1,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "fog-2",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Black Smoke");
    },
    get "description"() {
      return text("Turbulent columns of dense smoke rising and curling.");
    },
    "color": "#30343d",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.28;\nvec2 q=vec2(p.x*2.2,p.y*1.25+t*0.55);\nfloat curl=gwpFbm(q*2.0+vec2(gwpFbm(q+3.0),-gwpFbm(q-4.0)));\nfloat columns=gwpFbm(vec2(p.x*4.0,p.y*1.2+t*0.45));\nfloat smoke=smoothstep(0.32,0.74,curl*0.7+columns*0.5);\nfloat feather=1.0-smoothstep(0.65,1.12,length(vec2(p.x*0.9,p.y*0.6)));\nvec4 L=gwLight(vTextureCoord);\nfloat a=smoke*feather*uIntensity*0.82;\nvec3 c=mix(uColor*0.55,uColor+L.rgb*0.12,clamp(L.a,0.0,1.0));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.58,
    "intensity": 0.8,
    "scale": 2.5,
    "speed": 0.55,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-3",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Frost Mist");
    },
    get "description"() {
      return text("Low mist with suspended ice crystals.");
    },
    "color": "#a8dcf0",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nfloat floorBand=1.0-smoothstep(-0.95,0.65,p.y);\nfloat curls=gwpFbm(vec2(p.x*3.0+t*0.3,p.y*5.0)+vec2(sin(p.y*5.0+t)*0.3,0.0));\nfloat mist=smoothstep(0.46,0.77,curls)*floorBand;\nfloat crystals=pow(gwpNoise(p*18.0+vec2(t*0.12,0.0)),20.0)*floorBand;\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=(mist*0.55+crystals*0.28)*uIntensity*mix(0.65,1.0,lit);\nvec3 c=mix(uColor,vec3(0.94,1.0,1.0),crystals+lit*0.18);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.76,
    "intensity": 0.9,
    "scale": 1.6,
    "speed": 1,
    "rotation": 0,
    "radius": 9,
    "enabled": true,
    "id": "fog-4",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Purple Miasma");
    },
    get "description"() {
      return text("Cellular toxic gas with bubbles and internal veins.");
    },
    "color": "#9a45b8",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;\nvec2 q=p*4.0+vec2(-t*0.5,t*0.22);\nvec2 cell=floor(q);vec2 f=fract(q)-0.5;\nfloat h=gwpHash(cell);\nvec2 drift=vec2(sin(t+h*8.0),cos(t*0.7+h*11.0))*0.18;\nfloat bubble=exp(-dot(f+drift,f+drift)*(12.0+18.0*h));\nfloat cloud=smoothstep(0.4,0.72,gwpFbm(p*3.0+vec2(t*0.16)));\nfloat veins=pow(max(0.0,sin((p.x-p.y)*9.0+t*1.6+cloud*4.0)),8.0);\nfloat e=(bubble*0.7+cloud*0.65+veins*cloud*0.15)*uIntensity;\nfloat a=min(e,0.76);\nvec3 c=mix(uColor,vec3(0.65,1.0,0.45),bubble*0.12);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.5,
    "intensity": 0.8,
    "scale": 2,
    "speed": 0.45,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-5",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Ancient Dust");
    },
    get "description"() {
      return text("Suspended motes, haze, and faint backlit shafts.");
    },
    "color": "#b69a70",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;\nvec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf.y+=fract(t*0.18+h)-0.5;\nf.x+=sin(t*0.7+h*20.0)*0.12;\nfloat mote=exp(-dot(f,f)*(75.0+90.0*h))*step(0.56,h);\nfloat haze=smoothstep(0.52,0.82,gwpFbm(p*2.1+vec2(t*0.05,0.0)));\nfloat shafts=pow(max(0.0,0.5+0.5*sin((p.x+p.y*0.35)*7.0+t*0.15)),10.0)*0.12;\nvec4 L=gwLight(vTextureCoord);float lit=clamp(L.a,0.0,1.0);\nfloat a=(mote*0.85+haze*0.22+shafts)*uIntensity*mix(0.35,1.0,lit);\nvec3 c=mix(uColor,uColor+L.rgb*0.7,lit);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-1",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Campfire");
    },
    get "description"() {
      return text("Broad flame with irregular tongues and rising embers.");
    },
    "color": "#ff6a18",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float y=p.y+0.72;\nfloat sway=(gwpFbm(vec2(y*3.0,t*0.8))-0.5)*0.35;\nfloat width=max(0.08,0.68-(y+0.1)*0.5);\nfloat body=1.0-smoothstep(width*0.35,width,abs(p.x+sway));\nbody*=smoothstep(-0.35,-0.05,y)*(1.0-smoothstep(0.1,1.12,y));\nfloat tongues=0.55+0.55*gwpFbm(vec2((p.x+sway)*5.0,y*4.0-t*1.8));\nfloat ember=pow(gwpNoise(p*16.0-vec2(0.0,t*2.0)),18.0)*smoothstep(-0.3,0.9,y);\nfloat a=gwpSat((body*tongues+ember*0.25)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,0.95,0.55),gwpSat(body*(1.0-y*0.45)));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 0.9,
    "speed": 1.1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-2",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Blue Flame");
    },
    get "description"() {
      return text("Narrow blue jet with a white core and fast oscillation.");
    },
    "color": "#299cff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.25;float y=p.y+0.78;\nfloat wiggle=sin(y*7.0-t*2.2)*0.05+(gwpNoise(vec2(y*5.0,t))-0.5)*0.12;\nfloat cone=max(0.045,0.34-(y+0.15)*0.2);\nfloat outer=1.0-smoothstep(cone*0.55,cone,abs(p.x+wiggle));\nouter*=smoothstep(-0.3,-0.05,y)*(1.0-smoothstep(0.12,1.18,y));\nfloat core=1.0-smoothstep(cone*0.12,cone*0.42,abs(p.x+wiggle*0.4));\ncore*=1.0-smoothstep(0.05,0.82,y);\nfloat a=gwpSat((outer*0.7+core)*uIntensity);\nvec3 c=mix(uColor,vec3(0.92,0.98,1.0),core);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-3",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Green Fire");
    },
    get "description"() {
      return text("Bubbling alchemical combustion with green flames.");
    },
    "color": "#52e858",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;float y=p.y+0.65;\nfloat bubbling=0.18*sin(p.x*12.0+t*3.0)+0.12*sin(p.x*23.0-t*2.0);\nfloat w=max(0.09,0.56-(y+0.12)*0.4+bubbling*0.18);\nfloat flame=1.0-smoothstep(w*0.45,w,abs(p.x+(gwpFbm(vec2(y*5.0,t))-0.5)*0.28));\nflame*=smoothstep(-0.42,-0.08,y)*(1.0-smoothstep(0.0,0.9,y));\nfloat bubbles=pow(gwpNoise(p*12.0+vec2(t*0.3,-t*1.4)),14.0)*gwpDisk(vec2(p.x,y-0.05),0.72,0.22);\nfloat a=gwpSat((flame*(0.6+0.7*gwpFbm(p*6.0-vec2(0.0,t)))+bubbles*0.35)*uIntensity);\nvec3 c=mix(uColor,vec3(0.85,1.0,0.35),bubbles+flame*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 0.85,
    "intensity": 0.8,
    "scale": 1.05,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-4",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Dark Ember");
    },
    get "description"() {
      return text("Dark fire pierced by charcoal and red embers.");
    },
    "color": "#d52b20",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;float y=p.y+0.7;\nfloat drift=(gwpFbm(vec2(y*3.0,t*0.4))-0.5)*0.42;\nfloat w=max(0.07,0.5-(y+0.2)*0.38);\nfloat silhouette=1.0-smoothstep(w*0.4,w,abs(p.x+drift));\nsilhouette*=smoothstep(-0.38,-0.05,y)*(1.0-smoothstep(0.0,0.82,y));\nfloat holes=smoothstep(0.48,0.8,gwpFbm(p*7.0-vec2(0.0,t*0.7)));\nfloat ember=pow(gwpNoise(p*18.0+vec2(t*0.2,-t)),20.0)*silhouette;\nfloat a=gwpSat((silhouette*(0.48+0.35*holes)+ember*0.7)*uIntensity);\nvec3 c=mix(uColor*0.38,vec3(1.0,0.16,0.04),ember+silhouette*(1.0-holes)*0.2);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "flame-5",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Sacred Fire");
    },
    get "description"() {
      return text("Symmetrical flame with a halo and golden rays.");
    },
    "color": "#ffd35a",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;float y=p.y+0.72;\nfloat w=max(0.08,0.45-(y+0.05)*0.3);\nfloat flame=1.0-smoothstep(w*0.36,w,abs(p.x+sin(y*6.0+t)*0.06));\nflame*=smoothstep(-0.35,-0.08,y)*(1.0-smoothstep(0.0,1.05,y));\nfloat halo=gwpBand(length(p-vec2(0.0,-0.18)),0.62,0.12)*0.35;\nfloat rays=pow(max(0.0,cos(atan(p.y,p.x)*8.0+t*0.35)),22.0)*exp(-length(p)*2.1)*0.5;\nfloat a=gwpSat((flame+halo+rays)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,1.0,0.86),flame+halo*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 0.65,
    "intensity": 0.8,
    "scale": 1.4,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-1",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Water Reflection");
    },
    get "description"() {
      return text("Crossing wave caustics with small concentric ripples.");
    },
    "color": "#45a8d8",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;\nfloat w1=sin(p.x*8.0+t*1.7+p.y*2.3);\nfloat w2=sin(p.y*11.0-t*1.2+p.x*3.4);\nfloat w3=sin((p.x+p.y)*6.5+t*0.7);\nfloat caustic=pow(abs(w1+w2+w3)*0.333,5.0);\nfloat ripples=gwpBand(abs(sin(length(p-vec2(sin(t)*0.2,cos(t)*0.2))*18.0-t*2.0)),0.0,0.12);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=(caustic*0.72+ripples*0.15)*uIntensity*0.65;\nvec3 c=mix(uColor,vec3(0.78,0.96,1.0)+L.rgb*0.35,gwpSat(caustic+lit*0.25));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-2",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Ocean Abyss");
    },
    get "description"() {
      return text("Broad, crossing, deep waves with dark troughs.");
    },
    "color": "#164f83",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;\nfloat swell=0.5+0.5*sin(p.x*3.2+t*0.55+sin(p.y*2.4-t*0.2));\nfloat cross=0.5+0.5*sin(p.y*4.1-t*0.42+p.x*1.6);\nfloat trenches=smoothstep(0.38,0.72,gwpFbm(p*2.3+vec2(t*0.07,-t*0.04)));\nfloat foam=pow(abs(swell-cross),5.0)*0.32;\nfloat a=gwpSat((swell*0.3+cross*0.22+trenches*0.45+foam)*uIntensity*0.72);\nvec3 c=mix(uColor*0.45,uColor*1.15,foam+0.15*swell);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.7,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.9,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "liquid-3",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Acid Pool");
    },
    get "description"() {
      return text("Corrosive film with cellular bubbles and glowing veins.");
    },
    "color": "#78d934",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;\nvec2 q=p*6.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;\nfloat h=gwpHash(cell);float r=0.12+0.28*h;\nfloat bubble=gwpBand(length(f+vec2(sin(t+h*8.0),cos(t*0.6+h*10.0))*0.12),r,0.055);\nfloat film=gwpFbm(p*5.0+vec2(t*0.18));\nfloat veins=pow(max(0.0,sin((p.x-p.y)*10.0+t+film*4.0)),9.0);\nfloat a=gwpSat((bubble*0.9+film*0.25+veins*0.18)*uIntensity*0.7);\nvec3 c=mix(uColor,vec3(0.9,1.0,0.18),bubble+veins*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.9,
    "intensity": 0.95,
    "scale": 1.3,
    "speed": 1,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "liquid-4",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Flowing Lava");
    },
    get "description"() {
      return text("Dark plates separated by moving incandescent veins.");
    },
    "color": "#ff4b18",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;\nfloat n=gwpFbm(p*3.2+vec2(t*0.18,-t*0.06));\nfloat n2=gwpFbm(p*7.0-vec2(t*0.1,t*0.12));\nfloat veins=pow(gwpSat(1.0-abs(n-n2)*3.2),6.0);\nfloat plates=smoothstep(0.43,0.62,n);\nfloat glow=veins*(0.75+0.25*sin(t*1.4+n*8.0));\nfloat a=gwpSat((plates*0.42+glow*1.1)*uIntensity*0.9);\nvec3 c=mix(vec3(0.22,0.025,0.01),uColor,plates);\nc=mix(c,vec3(1.0,0.82,0.22),glow);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.55,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.8,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-5",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Mercury");
    },
    get "description"() {
      return text("Metallic surface with specular ridges and liquid interference.");
    },
    "color": "#b9c5d2",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat h=sin(p.x*14.0+t)+sin(p.y*9.0-t*0.7)+sin((p.x+p.y)*17.0+t*0.35);\nh/=3.0;\nfloat ridges=pow(abs(h),9.0);\nfloat warp=gwpFbm(p*8.0+vec2(t*0.08));\nfloat spec=pow(gwpSat(0.5+0.5*sin(h*8.0+warp*5.0)),12.0);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=gwpSat((0.18+ridges*0.42+spec*0.65)*uIntensity*0.55);\nvec3 c=mix(uColor*0.7,vec3(1.0)+L.rgb*0.25,spec*0.8+lit*0.2);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.65,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-1",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Light Rain");
    },
    get "description"() {
      return text("Thin, subtle drops tilted by the wind.");
    },
    "color": "#9bc9e8",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;\nvec2 q=gwpRot(p,0.18)*vec2(14.0,8.0)+vec2(t*0.7,-t*3.2);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat streak=(1.0-smoothstep(0.025,0.06,abs(f.x-h)))*\n             (1.0-smoothstep(0.0,0.55,fract(f.y+h)));\nfloat e=streak*step(0.52,h)*uIntensity;\nfloat a=min(e,0.62);\nvec3 c=mix(uColor,vec3(0.88,0.96,1.0),h*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.85,
    "intensity": 0.9,
    "scale": 1.7,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-2",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Storm");
    },
    get "description"() {
      return text("Heavy rain with clouds and occasional flashes.");
    },
    "color": "#b6d9ef",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.4;\nvec2 q=gwpRot(p,0.32)*vec2(20.0,6.0)+vec2(t*1.8,-t*5.6);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat rain=(1.0-smoothstep(0.045,0.1,abs(f.x-h)))*\n           (1.0-smoothstep(0.08,0.8,fract(f.y+h)))*step(0.30,h);\nfloat flash=pow(max(0.0,sin(t*0.37+floor(t*0.37)*4.1)),32.0);\nfloat cloud=smoothstep(0.42,0.72,gwpFbm(p*2.2+vec2(t*0.08)))*0.18;\nfloat a=gwpSat((rain*1.35+cloud+flash*0.28)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),flash*0.8);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.8,
    "intensity": 0.8,
    "scale": 1.9,
    "speed": 0.8,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-3",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Blizzard");
    },
    get "description"() {
      return text("Large flakes and ice crystals blown in a whirlwind.");
    },
    "color": "#edf7ff",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;\nvec2 q=p*9.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat phase=t*(0.25+0.65*h);\nf+=vec2(sin(phase+h*20.0)*0.42,fract(phase*0.45+h)-0.5);\nfloat d=length(f);\nfloat flake=exp(-d*d*(26.0+45.0*h))*step(0.36,h);\nfloat cross=(gwpLine(f.x,0.025)+gwpLine(f.y,0.025))*exp(-d*d*22.0)*step(0.72,h);\nfloat a=gwpSat((flake+cross*0.5)*uIntensity*0.8);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.62,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 0.6,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-4",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Ash");
    },
    get "description"() {
      return text("Flat fragments tumbling slowly in dark haze.");
    },
    "color": "#77736e",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;\nvec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat fall=fract(t*0.2+h);\nf.y+=fall-0.5;\nf.x+=sin(t+h*18.0)*0.18;\nfloat angle=t*0.7+h*6.28;\nvec2 r=gwpRot(f,angle);\nfloat shard=exp(-(r.x*r.x*120.0+r.y*r.y*35.0))*step(0.42,h);\nfloat haze=smoothstep(0.56,0.8,gwpFbm(p*2.5+vec2(t*0.04)))*0.18;\nfloat a=gwpSat((shard+haze)*uIntensity*0.62);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.75,
    "intensity": 0.8,
    "scale": 1.7,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-5",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Arcane Rain");
    },
    get "description"() {
      return text("Magical trails rising and leaving fleeting runes.");
    },
    "color": "#b75cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;\nvec2 q=gwpRot(p,-0.14)*vec2(15.0,8.0)+vec2(-t*0.45,t*2.6);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat streak=(1.0-smoothstep(0.03,0.07,abs(f.x-h)))*\n             (1.0-smoothstep(0.0,0.5,fract(1.0-f.y+h)))*step(0.55,h);\nfloat rune=pow(max(0.0,cos((f.x+f.y)*12.0+h*20.0+t)),14.0)*step(0.82,h);\nfloat a=gwpSat((streak+rune*0.5)*uIntensity*0.78);\nvec3 c=mix(uColor,vec3(0.9,0.7,1.0),rune);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.8,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-1",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Fireflies");
    },
    get "description"() {
      return text("Organic lights wandering and blinking out of phase.");
    },
    "color": "#ffd95a",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;\nvec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf+=vec2(sin(t*0.9+h*21.0),cos(t*0.63+h*17.0))*0.28;\nfloat dotv=exp(-dot(f,f)*(55.0+35.0*h))*step(0.48,h);\nfloat blink=pow(0.5+0.5*sin(t*3.0+h*30.0),3.0);\nfloat a=gwpSat(dotv*blink*uIntensity*1.2);\nvec3 c=mix(uColor,vec3(1.0,0.96,0.62),blink*0.7);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.6,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-2",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Spores");
    },
    get "description"() {
      return text("Soft spheres rising slowly with occasional halos.");
    },
    "color": "#8dcc73",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;\nvec2 q=p*8.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf.y+=fract(t*0.18+h)-0.5;\nf.x+=sin(t*0.5+h*12.0)*0.22;\nfloat big=exp(-dot(f,f)*(24.0+24.0*h))*step(0.38,h);\nfloat halo=exp(-dot(f,f)*8.0)*step(0.78,h)*0.22;\nfloat a=gwpSat((big+halo)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.72,1.0,0.65),halo);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1.15,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "particles-3",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Sparks");
    },
    get "description"() {
      return text("Ballistic trails with incandescent heads and short tails.");
    },
    "color": "#ff8b24",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.2;\nvec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat age=fract(t*0.42+h);\nf.y+=age*1.2-0.62;\nf.x+=sin(age*3.14+h*8.0)*0.18;\nvec2 r=gwpRot(f,-0.28+0.4*h);\nfloat streak=exp(-(r.x*r.x*140.0+r.y*r.y*18.0))*step(0.60,h)*(1.0-age);\nfloat head=exp(-dot(f,f)*120.0)*step(0.6,h);\nfloat a=gwpSat((streak+head*0.7)*uIntensity*1.25);\nvec3 c=mix(uColor,vec3(1.0,0.95,0.55),head);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.25,
    "speed": 0.75,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-4",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Souls");
    },
    get "description"() {
      return text("Floating spectral silhouettes with tails and glowing eyes.");
    },
    "color": "#55bfff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.3;\nvec2 q=p*4.5;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf+=vec2(sin(t*0.65+h*14.0)*0.32,fract(t*0.12+h)-0.5);\nfloat head=exp(-dot(f-vec2(0.0,-0.08),f-vec2(0.0,-0.08))*26.0)*step(0.42,h);\nfloat tail=exp(-(f.x*f.x*18.0+(f.y-0.22)*(f.y-0.22)*5.0))*step(0.42,h)*(0.6+0.4*sin(t+h*20.0));\nfloat eyes=\n    (exp(-dot(f-vec2(-0.07,-0.11),f-vec2(-0.07,-0.11))*260.0)+\n     exp(-dot(f-vec2(0.07,-0.11),f-vec2(0.07,-0.11))*260.0))*step(0.75,h);\nfloat a=gwpSat((head*0.65+tail*0.5+eyes)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),eyes);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.3,
    "speed": 0.5,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "particles-5",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Cosmic Dust");
    },
    get "description"() {
      return text("Star field with crosses, twinkling, and a faint nebula.");
    },
    "color": "#a88cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nvec2 q=p*15.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat star=exp(-dot(f,f)*(120.0+120.0*h))*step(0.68,h);\nfloat twinkle=pow(0.5+0.5*sin(t*5.0+h*40.0),5.0);\nfloat cross=(gwpLine(f.x,0.012)+gwpLine(f.y,0.012))*exp(-dot(f,f)*35.0)*step(0.9,h);\nfloat nebula=smoothstep(0.52,0.78,gwpFbm(p*2.1+vec2(t*0.03,-t*0.02)))*0.16;\nfloat a=gwpSat((star*twinkle+cross*0.4+nebula)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),star*twinkle*0.8);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-1",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Arcane Grid");
    },
    get "description"() {
      return text("Hexagonal mesh with pulsing nodes instead of a simple grid.");
    },
    "color": "#655cff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;\nvec2 q=p*4.5;\nvec2 hq=vec2(q.x+q.y*0.57735,q.y*1.1547);\nvec2 f=abs(fract(hq)-0.5);\nfloat hex=1.0-smoothstep(0.43,0.48,max(f.x,f.y));\nfloat edge=smoothstep(0.31,0.42,max(f.x,f.y))*hex;\nvec2 local=fract(hq)-0.5;\nfloat node=exp(-dot(local,local)*75.0);\nfloat pulse=0.55+0.45*sin(t*2.0+floor(hq.x)+floor(hq.y));\nfloat a=gwpSat((edge*0.52+node*pulse*0.85)*uIntensity*0.72);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.7,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-2",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Hologram");
    },
    get "description"() {
      return text("Digital grid with scanlines, glitches, and glowing nodes.");
    },
    "color": "#24d9e8",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;\nvec2 q=p*8.0;vec2 f=abs(fract(q)-0.5);\nfloat grid=(1.0-smoothstep(0.04,0.08,min(f.x,f.y)))*0.45;\nfloat scan=pow(0.5+0.5*sin((p.y-t)*18.0),12.0);\nfloat glitch=step(0.82,gwpNoise(vec2(floor(p.y*18.0),floor(t*6.0))))*0.22;\nvec2 local=fract(q)-0.5;\nfloat nodes=exp(-dot(local,local)*90.0)*(0.4+0.6*sin(t*4.0));\nfloat a=gwpSat((grid+scan*0.7+glitch+nodes*0.5)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.85,1.0,1.0),scan);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.62,
    "intensity": 0.8,
    "scale": 1.15,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-3",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Circuit");
    },
    get "description"() {
      return text("Pseudorandom orthogonal tracks with data pads.");
    },
    "color": "#45e078",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;\nvec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat horiz=gwpLine(f.y-(step(0.5,h)-0.5)*0.34,0.035)*step(0.35,h);\nfloat vert=gwpLine(f.x-(step(0.72,h)-0.5)*0.34,0.035)*step(0.52,1.0-h);\nfloat pad=exp(-dot(f,f)*120.0)*step(0.76,h);\nfloat data=0.45+0.55*sin(t*5.0+cell.x*0.7+cell.y*1.3);\nfloat a=gwpSat((horiz*0.55+vert*0.55+pad*data)*uIntensity*0.62);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "grid-4",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Runic Prison");
    },
    get "description"() {
      return text("Concentric rings, radial bars, and pulsing glyphs.");
    },
    "color": "#ed3948",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat rings=gwpBand(d,0.38,0.025)+gwpBand(d,0.68,0.025)+gwpBand(d,0.9,0.018);\nfloat bars=pow(abs(cos(ang*4.0)),24.0)*step(0.32,d)*(1.0-step(0.93,d));\nfloat glyph=pow(max(0.0,cos(ang*8.0+t*0.5)),24.0)*gwpBand(d,0.78,0.055);\nfloat flash=0.65+0.35*sin(t*2.0+d*12.0);\nfloat a=gwpSat((rings+bars*0.55+glyph*0.85)*flash*uIntensity*0.82);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.38,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.45,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-5",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Ghost Board");
    },
    get "description"() {
      return text("Alternating spectral squares slowly appearing and disappearing.");
    },
    "color": "#c4d6e8",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;\nvec2 q=floor(p*6.0);\nfloat checker=mod(q.x+q.y,2.0);\nfloat fade=0.28+0.24*sin(t*1.5+q.x*0.7-q.y*0.4);\nvec2 f=abs(fract(p*6.0)-0.5);\nfloat seams=1.0-smoothstep(0.44,0.49,max(f.x,f.y));\nfloat ghost=(checker*0.32+seams*0.18)*fade;\nfloat drift=gwpFbm(p*2.0+vec2(t*0.03))*0.1;\nfloat a=gwpSat((ghost+drift)*uIntensity*0.38);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-1",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Whirlpool");
    },
    get "description"() {
      return text("Water spiral with foam and concentric rings.");
    },
    "color": "#3b9fd1",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat n=gwpFbm(vec2(d*4.0,ang*1.5+t*0.4));\nfloat spiral=pow(0.5+0.5*sin(ang*6.0-d*17.0+t*2.0+n*2.0),3.0);\nfloat basin=smoothstep(0.1,0.22,d)*(1.0-smoothstep(0.72,1.1,d));\nfloat foam=pow(spiral,2.0)*basin;\nfloat rings=(gwpBand(d,0.42,0.025)+gwpBand(d,0.7,0.03))*0.3;\nfloat a=gwpSat((foam+rings)*uIntensity);\nvec3 c=mix(uColor,vec3(0.78,0.96,1.0),foam*0.55);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.9,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-2",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Singularity");
    },
    get "description"() {
      return text("Black hole with an accretion disk and gravitational lensing.");
    },
    "color": "#7038c8",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat hole=1.0-smoothstep(0.17,0.33,d);\nfloat disk=gwpBand(d,0.53,0.16)*(0.5+0.5*sin(ang*9.0-d*27.0+t*1.4));\nfloat lens=gwpBand(d,0.36,0.025)+gwpBand(d,0.78,0.018)*0.45;\nfloat sparks=pow(gwpNoise(vec2(ang*8.0,d*15.0+t)),18.0)*gwpBand(d,0.62,0.22);\nfloat e=(disk*1.2+lens+sparks*0.65)*(1.0-hole)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0),lens+sparks*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "vortex-3",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Sand Cyclone");
    },
    get "description"() {
      return text("Tapered sand column with turbulent bands and grains.");
    },
    "color": "#b79058",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;\nfloat y=p.y;\nfloat taper=0.24+0.52*(1.0-gwpSat((y+1.0)*0.5));\nfloat ang=atan(p.y,p.x);\nfloat bands=pow(0.5+0.5*sin(ang*11.0-length(p)*18.0+t*2.5+gwpFbm(p*5.0)*4.0),2.0);\nfloat column=1.0-smoothstep(taper,taper+0.22,abs(p.x));\nfloat grains=pow(gwpNoise(p*18.0+vec2(t*0.3,-t)),12.0)*column;\nfloat a=gwpSat((bands*column*0.52+grains*0.35)*uIntensity*0.85);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-4",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Green Tempest");
    },
    get "description"() {
      return text("Poisonous vortex with thick arms and internal eddies.");
    },
    "color": "#4fc96b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.9;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat n=gwpFbm(gwpRot(p,t*0.1)*6.0);\nfloat arms=pow(0.5+0.5*sin(ang*7.0-d*30.0+t*3.2+n*5.0),2.5);\nfloat eddies=pow(gwpFbm(p*10.0+vec2(t*0.12)),2.0);\nfloat body=smoothstep(0.1,0.2,d)*(1.0-smoothstep(0.72,1.2,d));\nfloat a=gwpSat((arms*0.72+eddies*0.32)*body*uIntensity*0.9);\nvec3 c=mix(uColor,vec3(0.7,1.0,0.38),eddies*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.55,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "vortex-5",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Galaxy");
    },
    get "description"() {
      return text("Spiral galaxy with arms, a central bulge, stars, and dust.");
    },
    "color": "#826cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat arm=pow(0.5+0.5*cos(ang*4.0-d*12.0+t*0.7),7.0)*exp(-d*1.5);\nfloat dust=gwpFbm(vec2(ang*2.0-d*3.0,d*8.0+t*0.15))*arm;\nvec2 q=p*18.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat stars=exp(-dot(f,f)*180.0)*step(0.74,h)*gwpDisk(p,1.05,0.12);\nfloat bulge=exp(-d*d*10.0);\nfloat a=gwpSat((arm*0.75+dust*0.42+stars+bulge*0.65)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,0.92,0.76),bulge+stars*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-1",
    "category": "Auras",
    get "name"() {
      return text("Sacred Aura");
    },
    get "description"() {
      return text("Golden halo with outer rays and rising motes.");
    },
    "color": "#ffd86a",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat halo=gwpBand(d,0.72+0.025*sin(t*2.0),0.055);\nfloat rays=pow(max(0.0,cos(ang*6.0+t*0.3)),18.0)*gwpBand(d,0.78,0.24);\nfloat inner=exp(-d*d*3.2)*0.18;\nfloat motes=pow(gwpNoise(p*16.0-vec2(0.0,t*0.3)),20.0)*gwpBand(d,0.6,0.38);\nfloat a=gwpSat((halo+rays*0.5+inner+motes*0.3)*uIntensity*0.78);\nvec3 c=mix(uColor,vec3(1.0,1.0,0.86),halo+rays*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-2",
    "category": "Auras",
    get "name"() {
      return text("Dark Aura");
    },
    get "description"() {
      return text("Smoky outline with inward-facing purple-black tendrils.");
    },
    "color": "#5b337e",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat wob=(gwpFbm(vec2(ang*5.0,t*0.4))-0.5)*0.15;\nfloat rim=gwpBand(d,0.68+wob,0.09);\nfloat tendrils=pow(max(0.0,sin(ang*9.0+d*17.0-t*2.0+gwpFbm(p*6.0)*4.0)),5.0)*gwpBand(d,0.55,0.32);\nfloat inner=exp(-d*d*2.0)*0.36;\nfloat a=gwpSat((rim*0.8+tendrils*0.5+inner)*uIntensity*0.82);\nvec3 c=mix(uColor*0.48,uColor,rim);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.65,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-3",
    "category": "Auras",
    get "name"() {
      return text("Arcane Shield");
    },
    get "description"() {
      return text("Precise hexagonal barrier with scanlines, nodes, and inner rings.");
    },
    "color": "#438cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat hexR=0.77/max(abs(cos(mod(ang+0.523599,1.047198)-0.523599)),0.5);\nfloat shell=gwpBand(d,hexR,0.028);\nfloat rings=gwpBand(d,0.58,0.018)*0.45;\nfloat scan=gwpBand(p.y,0.62*sin(t*2.0),0.025)*gwpDisk(p,0.82,0.08);\nfloat nodes=pow(max(0.0,cos(ang*6.0)),28.0)*gwpBand(d,0.77,0.07);\nfloat a=gwpSat((shell+rings+scan*0.55+nodes*0.7)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.9,0.98,1.0),shell+nodes);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.68,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.9,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-4",
    "category": "Auras",
    get "name"() {
      return text("Poison");
    },
    get "description"() {
      return text("Pulsing toxic cloud with distinct bubbles around its origin.");
    },
    "color": "#6fbf37",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;\nfloat d=length(p);\nfloat cloud=smoothstep(0.4,0.72,gwpFbm(p*5.0+vec2(t*0.18,-t*0.08)))*\n            (1.0-smoothstep(0.58,0.92,d));\nvec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat bubble=gwpBand(length(f),0.18+0.15*h,0.05)*step(0.45,h);\nfloat pulse=0.72+0.28*sin(t*2.5+d*7.0);\nfloat a=gwpSat((cloud*0.75+bubble*0.48)*pulse*uIntensity*0.7);\nvec3 c=mix(uColor,vec3(0.82,1.0,0.28),bubble*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-5",
    "category": "Auras",
    get "name"() {
      return text("Blood Aura");
    },
    get "description"() {
      return text("Crimson halo with radial spikes, drops, and an aggressive pulse.");
    },
    "color": "#d9263c",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat pulse=0.68+0.12*sin(t*5.0);\nfloat rim=gwpBand(d,0.69+pulse*0.04,0.055);\nfloat spikes=pow(max(0.0,cos(ang*11.0+t*0.8)),10.0)*gwpBand(d,0.75,0.22);\nfloat drops=pow(gwpNoise(vec2(ang*8.0,t*0.2+d*5.0)),14.0)*gwpBand(d,0.62,0.3);\nfloat inner=exp(-d*d*4.0)*0.2;\nfloat a=gwpSat((rim*0.9+spikes*0.55+drops*0.4+inner)*uIntensity*0.8);\nvec3 c=mix(uColor,vec3(0.85,0.05,0.08),drops+spikes*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  }
];

// gravewright/maps/frontend/features/effects/model/shader-source.js
function normalizeShaderSource(value) {
  const lines = value.replace(/\r\n?/g, "\n").trim().split("\n");
  const output = [];
  let blockComment = false, continuation = false;
  for (const line of lines) {
    const markerLine = line.replace(/\\([`'~])/g, "$1").replace(/[\u200B\uFEFF]/g, "").replace(/[‘’]/g, "'").replace(/\\[ \t]*$/, "");
    if (!blockComment && !continuation && /^[ \t]*(`{3,}|~{3,}|'{3,})[ \t]*([\w.+#-]+(?:[ \t]+[\w.+#-]+)*)?[ \t]*$/.test(markerLine)) continue;
    const directive = continuation || !blockComment && /^[ \t]*#/.test(line);
    let clean = "", quote = "";
    for (let i = 0; i < line.length; i++) {
      const char = line[i], next = line[i + 1];
      if (blockComment) {
        clean += char;
        if (char === "*" && next === "/") {
          clean += next;
          i++;
          blockComment = false;
        }
      } else if (quote) {
        clean += char;
        if (char === "\\" && next) {
          clean += next;
          i++;
        } else if (char === quote) quote = "";
      } else if (char === "/" && next === "/") {
        clean += line.slice(i);
        break;
      } else if (char === "/" && next === "*") {
        clean += "/*";
        i++;
        blockComment = true;
      } else if (char === '"' || char === "'") {
        quote = char;
        clean += char;
      } else if (char === "\\" && !directive) {
        if (/^[ \t]*$/.test(line.slice(i + 1))) break;
        if (/[\\`*_{}\[\]()#+\-.!<>|]/.test(next || "")) {
          clean += next;
          i++;
        } else clean += char;
      } else if (char !== "\u200B" && char !== "\uFEFF") clean += char === "\xA0" ? " " : char;
    }
    output.push(clean);
    continuation = directive && /\\[ \t]*$/.test(line);
  }
  return output.join("\n").trim();
}
function shaderSource(value) {
  const source = normalizeShaderSource(value);
  const code = source.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, "");
  if (!source) throw new Error(text("Paste the GLSL code returned by your AI. The field is empty."));
  if (source.length > 32e3) throw new Error(text("The shader exceeds the limit of 32,000 characters. Ask your AI for a shorter version."));
  if (!/\bvoid\s+main\s*\(\s*(?:void\s*)?\)/.test(code)) {
    throw new Error(text("The pasted code does not contain void main(). Copy the complete shader, including its main function."));
  }
  return source;
}

// gravewright/maps/frontend/features/effects/model/shader-prompt.js
var shaderPrompt = "Write a generative GLSL ES 3.00 fragment shader for Gravewright.\n\nOUTPUT CONTRACT \u2014 RAW SOURCE FILE\nYour entire reply will be pasted directly into a GLSL compiler, not a Markdown renderer.\nReturn exactly one complete, compilable shader source as plain text.\nDo not use Markdown: no code fences (including glsl fences), headings, lists, blockquotes, inline backticks, or explanatory paragraphs.\nDo not escape GLSL operators for Markdown (write * directly, never backslash-star), and do not add backslashes at the ends of source lines. Do not label any part as arduino, cpp, java, or another language.\nDo not split the shader into snippets. Do not include a filename, language label, introduction, conclusion, or instructions for copying it.\nStart directly with GLSL source. Keep top-level declarations at column 1; indent only inside functions. End immediately after the final closing brace.\nReturn helper functions and exactly one void main(). Do not include #version, precision, uniform/input/output declarations: the engine supplies them.\nBefore replying, silently verify that the entire response can be pasted unchanged into the source field. Output only that source.\n\nRENDERING CONTRACT\nThe shader draws a transparent frame over the map. It does not receive the scene image. The frame already matches the range and is clipped by range, walls, and doors; do not implement this clipping in GLSL. Always write premultiplied alpha: finalColor = vec4(color * a, a). The engine applies blending afterward: Normal, Add, Multiply, or Screen. Do not implement blending in the shader.\n\nALREADY AVAILABLE: DO NOT DECLARE\n  in vec2 vTextureCoord;\n  out vec4 finalColor;\n  uniform sampler2D uTexture;      // white frame texture, not the map\n  uniform sampler2D uLightBuffer;  // accumulated scene lighting\n  uniform float uTime;            // seconds, resets every hour\n  uniform float uIntensity;       // 0..1, internal effect strength\n  uniform float uOpacity;         // 0..1, applied automatically after main()\n  uniform float uScale;           // 0.1..20\n  uniform float uSpeed;           // 0..8\n  uniform vec3 uColor;            // channels 0..1\n  uniform vec2 uResolution;       // frame size in pixels\n  uniform float uAspect;\n  uniform vec2 uOrigin;           // origin in world coordinates\n  uniform float uRadius;          // world range; 0 = entire scene\n  uniform float uRotation;        // radians\n  uniform vec3 uCamera;           // x/y offset and zoom\n  uniform vec2 uScreen;           // screen size in pixels\n  vec2 gwScreen(vec2 uv);         // screen pixel\n  vec2 gwScreenUV(vec2 uv);       // screen position 0..1\n  vec2 gwWorld(vec2 uv);          // world point; stays fixed during pan/zoom\n  vec2 gwRotated(vec2 uv);        // world rotated around uOrigin\n  float gwFeature();             // feature size tied to range and uScale\n  vec2 gwPattern(vec2 uv);        // (gwRotated(uv) - uOrigin) / gwFeature(); returns (0,0) at the click\n  vec4 gwLight(vec2 uv);          // rgb = light color; a = intensity\n\nRULES\n1. Build patterns in gwPattern(vTextureCoord): it returns exactly vec2(0.0) at the clicked point, which is always the effect's center/start. Use gwWorld/gwRotated only for absolute world coordinates. Do not use raw vTextureCoord for map-bound patterns or subtract uOrigin from gwPattern again.\n2. Use uTime * uSpeed for animation, uIntensity for internal strength/alpha, and uColor as the dominant color. uScale already affects gwFeature(); do not apply it again with gwPattern.\n3. The engine multiplies finalColor by uOpacity after main(). Do not multiply by uOpacity, or transparency will be applied twice.\n4. gwLight(vTextureCoord) is optional. Use it for effects that respond to lights. Do not make effects disappear completely without light unless requested.\n5. Use GLSL ES 3.00 syntax and explicit, compatible types. Define every helper you call. Do not use Shadertoy mainImage, iTime, iResolution, or gl_FragColor.\n6. In smoothstep(edge0, edge1, x), keep edge0 < edge1. Invert with 1.0 - smoothstep(low, high, x); reversed edges have undefined results.\n7. Avoid division by zero, NaN/Inf, unbounded loops, and excessive per-pixel work. Multiple shaders may run simultaneously. Code can contain up to 32,000 characters.\n\nDESIRED EFFECT\n<describe appearance, motion, density, and lighting behavior here>\n\nFINAL REMINDER\nReply with raw GLSL only, from the first source line to the last closing brace. No Markdown or surrounding text.";

// gravewright/maps/frontend/features/effects/ui/shader-prompt-dialog.js
import { mountModal } from "/static/gravewright_table/modal.js";
function shaderInstructions(description) {
  return shaderPrompt.replace("<describe appearance, motion, density, and lighting behavior here>", () => description.trim());
}
function openShaderPrompt(onInsert, onClose, { nested = false } = {}) {
  const previousFocus = document.activeElement;
  const dialog = document.createElement("section");
  dialog.className = "table-modal-window shader-prompt-dialog";
  dialog.setAttribute("aria-labelledby", "shader-prompt-title");
  let description = "", response = "", disposed = false;
  function element(tag, text2, parent = dialog) {
    const node = document.createElement(tag);
    if (text2) node.textContent = text(text2);
    parent.append(node);
    return node;
  }
  function close() {
    if (disposed) return;
    disposed = true;
    dialog.close();
    if (previousFocus?.isConnected) previousFocus.focus();
    onClose();
  }
  dialog.addEventListener("close", close);
  dialog.addEventListener("keydown", (event) => event.stopPropagation());
  dialog.addEventListener("click", (event) => event.stopPropagation());
  function render(step) {
    dialog.replaceChildren();
    const header = element("header");
    element("strong", step === 1 ? "Describe your shader" : "Paste the AI-generated code", header).id = "shader-prompt-title";
    const dismiss = element("button", "\xD7", header);
    dismiss.type = "button";
    dismiss.dataset.close = "";
    dismiss.setAttribute("aria-label", text("Close"));
    dismiss.onclick = close;
    const body = element("div");
    body.className = "table-modal-body";
    const hint = element("p", step === 1 ? "Describe the appearance, colors and movement you want. We will add the technical instructions and copy everything for your AI." : "Instructions copied! Paste them into your favorite AI. Then copy its complete GLSL response and paste it below. Insert into editor will place the code in the GLSL code field; save it there when you are ready.", body);
    hint.id = "shader-prompt-hint";
    const label = element("label", step === 1 ? "Desired effect" : "GLSL returned by the AI", body);
    label.htmlFor = "shader-prompt-input";
    const input = element("textarea", "", body);
    input.id = "shader-prompt-input";
    input.setAttribute("aria-describedby", hint.id);
    input.rows = 8;
    input.maxLength = step === 1 ? 4e3 : 4e4;
    input.spellcheck = step === 1;
    input.value = step === 1 ? description : response;
    input.placeholder = text(step === 1 ? "Example: slow violet mist with a few glowing sparks." : "Paste the complete shader code here.");
    const error = element("p", "", body);
    error.className = "shader-prompt-dialog__error";
    error.setAttribute("role", "alert");
    const actions = element("footer");
    const cancel = element("button", "Cancel", actions);
    cancel.type = "button";
    cancel.onclick = close;
    if (step === 2) {
      const back = element("button", "Back", actions);
      back.type = "button";
      back.onclick = () => {
        response = input.value;
        render(1);
      };
    }
    const confirm = element("button", step === 1 ? "Copy instructions and continue" : "Insert into editor", actions);
    confirm.type = "button";
    confirm.className = "shader-prompt-dialog__confirm";
    confirm.disabled = !input.value.trim();
    input.oninput = () => {
      confirm.disabled = !input.value.trim();
      error.textContent = "";
    };
    confirm.onclick = async () => {
      error.textContent = "";
      if (step === 1) {
        description = input.value.trim();
        if (!description) return;
        confirm.disabled = true;
        try {
          await navigator.clipboard.writeText(shaderInstructions(description));
          if (!disposed) render(2);
        } catch {
          if (!disposed) {
            error.textContent = text("Could not copy the instructions. Allow clipboard access in your browser and try again.");
            confirm.disabled = false;
          }
        }
      } else {
        try {
          input.value = normalizeShaderSource(input.value);
          onInsert(shaderSource(input.value));
          close();
        } catch (failure) {
          error.textContent = failure.message;
        }
      }
    };
    input.focus();
  }
  render(1);
  mountModal(dialog, { nested });
  dialog.querySelector("textarea").focus();
  return close;
}

// gravewright/maps/frontend/features/effects/model/legacy-labels.js
var effectLabels = {
  get "lighting.shaders.whole_scene"() {
    return text("Entire scene");
  },
  get "lighting.particles.tool"() {
    return text("Particles");
  },
  get "lighting.particles.smoke"() {
    return text("Smoke");
  },
  get "lighting.particles.ember"() {
    return text("Ember");
  },
  get "lighting.particles.dust"() {
    return text("Dust");
  },
  get "lighting.particles.arcane"() {
    return text("Arcane");
  },
  get "lighting.shaders.tool"() {
    return text("Scene shader");
  },
  get "lighting.shaders.editor"() {
    return text("Scene shader");
  },
  get "lighting.shaders.reference"() {
    return text("Reference");
  },
  get "lighting.shaders.source"() {
    return text("GLSL code");
  },
  get "lighting.shaders.intensity"() {
    return text("Intensity");
  },
  get "lighting.shaders.opacity"() {
    return text("Opacity");
  },
  get "lighting.shaders.blend_mode"() {
    return text("Blend mode");
  },
  get "lighting.shaders.blend_hint"() {
    return text("Defines how the effect blends with the map and shaders below it.");
  },
  "lighting.shaders.blend.normal": "Normal",
  get "lighting.shaders.blend.multiply"() {
    return text("Multiply");
  },
  get "lighting.shaders.blend.darken"() {
    return text("Darken");
  },
  get "lighting.shaders.blend.lighten"() {
    return text("Lighten");
  },
  get "lighting.shaders.blend.screen"() {
    return text("Screen");
  },
  get "lighting.shaders.blend.add"() {
    return text("Add (glow)");
  },
  get "lighting.shaders.blend.overlay"() {
    return text("Overlay");
  },
  get "lighting.shaders.blend.soft_light"() {
    return text("Soft light");
  },
  get "lighting.shaders.blend.hard_light"() {
    return text("Hard light");
  },
  get "lighting.shaders.blend.color_dodge"() {
    return text("Color dodge");
  },
  get "lighting.shaders.blend.color_burn"() {
    return text("Color burn");
  },
  get "lighting.shaders.blend.difference"() {
    return text("Difference");
  },
  get "lighting.shaders.blend.exclusion"() {
    return text("Exclusion");
  },
  get "lighting.shaders.blend.subtract"() {
    return text("Subtract");
  },
  get "lighting.shaders.rotation"() {
    return text("Rotation");
  },
  get "lighting.shaders.radius"() {
    return text("Range");
  },
  get "lighting.shaders.radius_hint"() {
    return text("In cells, from the origin you drag on the map. The effect is drawn inside a frame of this size and clipped by a mask. Anything outside it cannot appear. Zero = entire scene.");
  },
  get "lighting.shaders.scale"() {
    return text("Scale");
  },
  get "lighting.shaders.speed"() {
    return text("Speed");
  },
  get "lighting.shaders.color"() {
    return text("Color");
  },
  get "lighting.shaders.enabled"() {
    return text("Active");
  },
  get "lighting.shaders.save"() {
    return text("Save");
  },
  get "lighting.shaders.remove"() {
    return text("Remove shader");
  },
  get "lighting.shaders.group.appearance"() {
    return text("Appearance");
  },
  get "lighting.shaders.group.pattern"() {
    return text("Pattern and motion");
  },
  get "lighting.shaders.group.area"() {
    return text("Area");
  },
  get "lighting.shaders.mode_hint"() {
    return text("Shaders appear only in cinematic mode; lightweight mode uses particles for scene effects.");
  },
  get "lighting.shaders.preview"() {
    return text("Validate");
  },
  get "lighting.shaders.preview_final"() {
    return text("Result");
  },
  get "lighting.shaders.preview_mask"() {
    return text("Mask (range and walls)");
  },
  get "lighting.shaders.preview_light"() {
    return text("Light buffer");
  },
  get "lighting.shaders.prompt_title"() {
    return text("AI prompt");
  },
  get "lighting.shaders.prompt_failed"() {
    return text("Could not copy. Check clipboard permissions and try again.");
  },
  get "lighting.shaders.prompt_copy"() {
    return text("Copy prompt");
  },
  get "lighting.shaders.prompt_copied"() {
    return text("Copied");
  },
  get "lighting.particles.editor"() {
    return text("Particle emitter");
  },
  get "lighting.particles.kind"() {
    return text("Type");
  },
  get "lighting.particles.scale"() {
    return text("Size");
  },
  get "lighting.particles.density"() {
    return text("Quantity");
  },
  get "lighting.particles.color"() {
    return text("Color");
  },
  get "lighting.particles.enabled"() {
    return text("Active");
  },
  get "lighting.particles.remove"() {
    return text("Delete emitter");
  },
  get "lighting.particles.density_hint"() {
    return text("Quantity controls performance: lower it if the scene slows down.");
  },
  get "lighting.particles.hint"() {
    return text("Scene effect: can receive and emit light.");
  },
  get "lighting.shaders.presets.title"() {
    return text("Preset library (50)");
  },
  get "lighting.shaders.presets.hint"() {
    return text("Choose a preset. Applying it replaces the code and adjusts this shader's controls.");
  },
  get "lighting.shaders.presets.search"() {
    return text("Search presets...");
  },
  get "lighting.shaders.presets.category"() {
    return text("Category");
  },
  get "lighting.shaders.presets.all"() {
    return text("All categories");
  },
  get "lighting.shaders.presets.apply"() {
    return text("Apply preset");
  },
  get "lighting.shaders.presets.applied"() {
    return text("Preset applied and saved.");
  },
  get "lighting.shaders.presets.empty"() {
    return text("No preset found.");
  },
  "lighting.shaders.picker.title": "Shaders",
  "lighting.shaders.picker.custom": "Custom",
  get "lighting.shaders.picker.loading"() {
    return text("Loading presets...");
  },
  get "lighting.shaders.picker.error"() {
    return text("Could not load presets.");
  },
  get "lighting.particles.rain"() {
    return text("Rain");
  },
  get "lighting.particles.snow"() {
    return text("Snow");
  },
  get "lighting.particles.firefly"() {
    return text("Fireflies");
  },
  get "lighting.particles.leaves"() {
    return text("Leaves");
  },
  get "lighting.particles.bubbles"() {
    return text("Bubbles");
  },
  get "lighting.particles.ash"() {
    return text("Ash");
  },
  get "lighting.particles.blood"() {
    return text("Blood");
  },
  get "lighting.particles.runes"() {
    return text("Runes");
  }
};

// gravewright/maps/frontend/features/effects/ui/EffectEditor.native.js
var PhX2 = "PhX";
var PhTrash2 = "PhTrash";
var PhCheck = "PhCheck";
var PhBooks = "PhBooks";
var PhMagicWand = "PhMagicWand";
var PhCopy = "PhCopy";
var EffectEditor_native_default = widget([{ "tag": "section", "attrs": { "class": "gw-window effect-editor", "role": "dialog" }, "bind": { "class": "({ 'effect-editor--shader': kind === 'shader' })", "aria-label": "(t('editor'))", "role": "(transactional ? 'group' : 'dialog')" }, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "wheel", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "effect-editor__header gw-move-handle", "data-move-handle": "" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('editor'))" }] }, { "tag": "button", "attrs": { "type": "button", "class": "gw-window__control" }, "bind": { "aria-label": "(gwText('Close'))", "disabled": "(transactional && busy)" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "effect-editor__body" }, "bind": { "inert": "(transactional && busy)" }, "events": [{ "event": "input", "code": "kind === 'shader' && emit('change');", "mods": [] }, { "event": "change", "code": "kind === 'shader' && emit('change');", "mods": [] }], "children": [{ "tag": "fieldset", "attrs": { "class": "effect-editor__interaction" }, "bind": {}, "events": [], "children": [{ "tag": "legend", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Light interaction'))" }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Receive lighting'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": "0.05" }, "bind": { "aria-label": "(gwText('Receive lighting'))" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.light_response)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(Math.round(draft.light_response * 100))" }, { "text": "%" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Emit light'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "2", "step": "0.05" }, "bind": { "aria-label": "(gwText('Emit light'))" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.light_emission)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.light_emission.toFixed(2))" }] }] }] }] }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('kind'))" }] }, { "tag": "select", "attrs": {}, "bind": { "aria-label": "(t('kind'))" }, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [{ "tag": "option", "attrs": {}, "bind": { "key": "(kind)", "value": "(kind)" }, "events": [], "children": [{ "value": "(t(kind))" }], "each": { "names": ["kind"], "value": "(['smoke', 'ember', 'dust', 'arcane', 'rain', 'snow', 'firefly', 'leaves', 'bubbles', 'ash', 'blood', 'runes'])" } }], "model": { "path": "(draft.kind)", "mods": [] } }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('scale'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": ".5", "max": "20", "step": ".5" }, "bind": { "aria-label": "(t('scale'))" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.scale)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.scale)" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('density'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": ".05" }, "bind": { "aria-label": "(t('density'))" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.density)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.density.toFixed(2))" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('color'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(t('color'))" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.color)", "mods": [] } }] }, { "tag": "label", "attrs": { "class": "effect-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "aria-label": "(t('enabled'))" }, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.enabled)", "mods": [] } }, { "value": "(t('enabled'))" }] }, { "tag": "p", "attrs": { "class": "effect-editor__hint" }, "bind": {}, "events": [], "children": [{ "value": "(t('density_hint'))" }] }, { "tag": "p", "attrs": { "class": "effect-editor__hint" }, "bind": {}, "events": [], "children": [{ "value": "(t('hint'))" }] }], "when": "(kind === 'particle')" }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "details", "attrs": { "class": "effect-editor__library" }, "bind": {}, "events": [], "children": [{ "tag": "summary", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhBooks", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "text": " " }, { "value": "(t('presets.title'))" }] }, { "tag": "p", "attrs": { "class": "effect-editor__hint" }, "bind": {}, "events": [], "children": [{ "value": "(t('presets.hint'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "search" }, "bind": { "placeholder": "(t('presets.search'))", "aria-label": "(t('presets.search'))" }, "events": [], "children": [], "model": { "path": "(search)", "mods": [] } }, { "tag": "select", "attrs": {}, "bind": { "aria-label": "(t('presets.category'))" }, "events": [], "children": [{ "tag": "option", "attrs": { "value": "" }, "bind": {}, "events": [], "children": [{ "value": "(t('presets.all'))" }] }, { "tag": "option", "attrs": {}, "bind": { "key": "(c)" }, "events": [], "children": [{ "value": "(c)" }], "each": { "names": ["c"], "value": "(categories)" } }], "model": { "path": "(category)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "effect-editor__presets", "role": "listbox" }, "bind": { "aria-label": "(t('presets.title'))" }, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button", "role": "option" }, "bind": { "key": "(p.id)", "aria-selected": "(choice === p.id)" }, "events": [{ "event": "click", "code": "choice = p.id;", "mods": [] }], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(p.name)" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(p.category)" }] }], "each": { "names": ["p"], "value": "(presets)" } }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('presets.empty'))" }], "when": "(!presets.length)" }] }, { "tag": "div", "attrs": { "class": "effect-editor__choice" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(chosen.name)" }] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(chosen.description)" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "apply;", "mods": [] }], "children": [{ "tag": "PhMagicWand", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(t('presets.apply'))" }] }], "when": "(chosen)" }] }, { "tag": "div", "attrs": { "class": "effect-editor__columns" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": { "class": "effect-editor__code" }, "bind": {}, "events": [], "children": [{ "tag": "header", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "for": "effect-shader-source" }, "bind": {}, "events": [], "children": [{ "value": "(t('source'))" }] }, { "tag": "label", "attrs": { "class": "effect-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "aria-label": "(t('enabled'))" }, "events": [], "children": [], "model": { "path": "(draft.enabled)", "mods": [] } }, { "value": "(t('enabled'))" }] }] }, { "tag": "textarea", "attrs": { "id": "effect-shader-source", "spellcheck": "false", "rows": "10" }, "bind": {}, "events": [], "children": [], "model": { "path": "(draft.source)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "effect-editor__controls" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "h3", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('group.appearance'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('opacity'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": ".05" }, "bind": { "aria-label": "(t('opacity'))" }, "events": [], "children": [], "model": { "path": "(draft.opacity)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.opacity.toFixed(2))" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('color'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(t('color'))" }, "events": [], "children": [], "model": { "path": "(draft.color)", "mods": [] } }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('blend_mode'))" }] }, { "tag": "select", "attrs": {}, "bind": { "aria-label": "(t('blend_mode'))" }, "events": [], "children": [{ "tag": "option", "attrs": {}, "bind": { "key": "(mode)", "value": "(mode)" }, "events": [], "children": [{ "value": "(t(`blend.${mode}`))" }], "each": { "names": ["mode"], "value": "(['normal', 'multiply', 'screen', 'add'])" } }], "model": { "path": "(draft.blend_mode)", "mods": [] } }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('blend_hint'))" }] }] }] }, { "tag": "section", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "h3", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('group.pattern'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": { "key": "(range.key)" }, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t(range.key))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range" }, "bind": { "min": "(range.min)", "max": "(range.max)", "step": "(range.step)", "aria-label": "(t(range.key))" }, "events": [], "children": [], "model": { "path": "(draft[range.key])", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft[range.key])" }, { "value": "(range.key === 'rotation' ? '\xB0' : '')" }] }] }], "each": { "names": ["range"], "value": "(ranges)" } }] }] }, { "tag": "section", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "h3", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('group.area'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('radius'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "120", "step": "1" }, "bind": { "aria-label": "(t('radius'))" }, "events": [], "children": [], "model": { "path": "(draft.radius)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.radius)" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "checked": "(draft.radius === 0)" }, "events": [{ "event": "click", "code": "draft.radius = $event.target.checked ? 0 : 8; emit('change');", "mods": [] }], "children": [] }, { "value": "(t('whole_scene'))" }] }] }] }] }] }, { "tag": "div", "attrs": { "class": "effect-editor__reference" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "showPrompt();", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(t('prompt_title'))" }] }] }], "otherwise": true }] }, { "tag": "footer", "attrs": { "class": "effect-editor__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button", "class": "effect-editor__remove" }, "bind": { "disabled": "(busy)", "aria-label": "(t('remove'))" }, "events": [{ "event": "click", "code": "emit('remove');", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }], "when": "(existing && !transactional)" }, { "tag": "span", "attrs": { "role": "status" }, "bind": {}, "events": [], "children": [{ "value": "(error || (!existing ? gwText('Click the scene to place the origin.') : ''))" }] }, { "tag": "button", "attrs": { "type": "button", "data-native-editor-cancel": "" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "value": "(gwText('Cancel'))" }], "when": "(transactional)" }, { "tag": "button", "attrs": { "type": "button", "data-native-editor-save": "" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('save');", "mods": [] }], "children": [{ "tag": "PhCheck", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(existing ? t('save') : gwText('Create'))" }], "when": "(transactional || kind === 'shader' || !existing)" }] }], "movable": true }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const draft = model(options);
  const emit = options.emit;
  const particleNames = { get rain() {
    return text("Rain");
  }, get snow() {
    return text("Snow");
  }, get firefly() {
    return text("Fireflies");
  }, get leaves() {
    return text("Leaves");
  }, get bubbles() {
    return text("Bubbles");
  }, get ash() {
    return text("Ash");
  }, get blood() {
    return text("Blood");
  }, get runes() {
    return text("Runes");
  } };
  const t = (key) => effectLabels[`lighting.${props.kind === "particle" ? "particles" : "shaders"}.${key}`] || (props.kind === "particle" ? particleNames[key] : void 0) || key;
  const search = ref(""), category = ref(""), choice = ref("");
  let closePrompt;
  onBeforeUnmount(() => closePrompt?.());
  const categories = computed(() => [...new Set(shaderPresets.map((p) => p.category))]);
  const presets = computed(() => shaderPresets.filter((p) => (!category.value || p.category === category.value) && `${p.name} ${p.description}`.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())));
  const chosen = computed(() => shaderPresets.find((p) => p.id === choice.value));
  function apply() {
    const p = chosen.value;
    if (!p)
      return;
    draft.value = { ...draft.value, ...p, source: p.source };
    emit("change");
  }
  function showPrompt() {
    if (closePrompt) return;
    closePrompt = openShaderPrompt((source) => {
      draft.value = { ...draft.value, source };
      emit("change");
    }, () => {
      closePrompt = null;
    }, { nested: props.transactional === true });
  }
  const ranges = [{ key: "intensity", min: 0, max: 1, step: 0.05 }, { key: "scale", min: 0.1, max: 20, step: 0.1 }, { key: "speed", min: 0, max: 8, step: 0.1 }, { key: "rotation", min: 0, max: 359, step: 1 }];
  return { gwText: text, PhX: PhX2, PhTrash: PhTrash2, PhCheck, PhBooks, PhMagicWand, PhCopy, vMovableResizable, shaderPresets, effectLabels, draft, particleNames, t, search, category, choice, categories, presets, chosen, apply, showPrompt, ranges, emit: options.emit };
});

// gravewright/maps/frontend/features/scene-layers/lib/shader-language.js
var PREAMBLE = `#version 300 es
precision highp float;

in vec2 vTextureCoord;
out vec4 finalColor;



uniform sampler2D gwUTexture;

uniform float gwUQuality;
uniform float gwULightResponse;
uniform float gwUAmbient;
uniform float gwUTime;
uniform float gwUIntensity;
uniform float gwUOpacity;
uniform float gwUScale;
uniform float gwUSpeed;
uniform vec3 gwUColor;


uniform vec2 gwUResolution;
uniform float gwUAspect;



uniform vec2 gwUOrigin;
uniform float gwURadius;
uniform float gwURotation;


uniform vec3 gwUCamera;



uniform sampler2D gwULightBuffer;


uniform vec2 gwUScreen;










uniform vec2 gwUFrameOrigin;


vec2 gwScreen(vec2 uv) {
    return uv * gwUResolution + gwUFrameOrigin;
}


vec2 gwScreenUV(vec2 uv) {
    return gwScreen(uv) / max(gwUScreen, vec2(1.0));
}



vec4 gwLight(vec2 uv) {
    return texture(gwULightBuffer, gwScreenUV(uv));
}



vec4 gwIlluminate(vec4 color, vec2 uv, float strength) {
    vec3 illumination = clamp(vec3(gwUAmbient) + gwLight(uv).rgb, vec3(0.0), vec3(1.5));
    float alpha = max(color.a, 0.0001);
    vec3 linearColor = pow(max(color.rgb / alpha, vec3(0.0)), vec3(2.2));
    vec3 lit = pow(linearColor * mix(vec3(1.0), illumination, clamp(strength, 0.0, 1.0)), vec3(1.0 / 2.2));
    return vec4(lit * color.a, color.a);
}
vec2 gwWorld(vec2 uv) {
    return (gwScreen(uv) - gwUCamera.xy) / max(gwUCamera.z, 0.0001);
}


vec2 gwRotated(vec2 uv) {
    vec2 d = gwWorld(uv) - gwUOrigin;
    float c = cos(gwURotation);
    float s = sin(gwURotation);
    return gwUOrigin + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
}










float gwFeature() {
    float base = gwURadius > 0.0 ? gwURadius * 0.6 : 420.0;
    return max(base * gwUScale, 1.0);
}



vec2 gwPattern(vec2 uv) {


    return (gwRotated(uv) - gwUOrigin) / gwFeature();
}
`;
var USER_PREFIX = `#define uTexture gwUTexture
#define uQuality gwUQuality
#define uTime gwUTime
#define uIntensity gwUIntensity
#define uOpacity gwUOpacity
#define uScale gwUScale
#define uSpeed gwUSpeed
#define uColor gwUColor
#define uResolution gwUResolution
#define uAspect gwUAspect
#define uOrigin gwUOrigin
#define uRadius gwURadius
#define uRotation gwURotation
#define uCamera gwUCamera
#define uLightBuffer gwULightBuffer
#define uScreen gwUScreen
#define uFrameOrigin gwUFrameOrigin
#define main gwUserMain
`;
var USER_SUFFIX = "\n#undef main\nvoid main() { gwUserMain(); finalColor *= gwUOpacity; finalColor = gwIlluminate(finalColor, vTextureCoord, gwULightResponse); }\n";

// gravewright/maps/frontend/features/effects/model/shader-validation.js
var ShaderDraftValidator = class {
  gl;
  validate(source) {
    if (!source.trim())
      return text("The shader is empty.");
    if (source.length > 32e3)
      return text("Text is too long (32000 character limit).");
    this.gl ??= document.createElement("canvas").getContext("webgl2");
    const gl = this.gl;
    if (!gl)
      return text("WebGL 2 is unavailable to validate this shader.");
    const shader = gl.createShader(gl.FRAGMENT_SHADER);
    if (!shader)
      return text("Could not validate the shader.");
    try {
      gl.shaderSource(shader, PREAMBLE + USER_PREFIX + source + USER_SUFFIX);
      gl.compileShader(shader);
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? "" : gl.getShaderInfoLog(shader)?.replaceAll("\0", "").trim() || text("Invalid GLSL code.");
    } finally {
      gl.deleteShader(shader);
    }
  }
  dispose() {
    this.gl?.getExtension("WEBGL_lose_context")?.loseContext();
    this.gl = void 0;
  }
};

// gravewright/maps/frontend/features/effects/model/effects.js
function defaults() {
  return { light_response: 0, light_emission: 0, bright_radius: 2, dim_radius: 4, angle: 360, animation: "none", x: 0, y: 0, kind: "smoke", scale: 3, density: 0.6, color: "#9aa3ad", enabled: true, rotation: 0, name: "Shader", source: "void main() { float a = 0.35 * uIntensity; finalColor = vec4(uColor * a, a); }", radius: 0, opacity: 1, intensity: 0.6, speed: 1, blend_mode: "normal" };
}

// gravewright/maps/frontend/features/effects/model/particle-profiles.js
var PARTICLE_DEFAULTS = {
  smoke: { scale: 3, density: 0.6, color: "#9aa3ad" },
  ember: { scale: 2, density: 0.5, color: "#ff9040" },
  dust: { scale: 6, density: 0.45, color: "#d8cdb4" },
  arcane: { scale: 2.5, density: 0.6, color: "#c9a6ff" },
  rain: { scale: 8, density: 0.7, color: "#9bc9e8" },
  snow: { scale: 8, density: 0.65, color: "#edf7ff" },
  firefly: { scale: 5, density: 0.55, color: "#ffe46b" },
  leaves: { scale: 7, density: 0.55, color: "#a87035" },
  bubbles: { scale: 4, density: 0.6, color: "#8de8ff" },
  ash: { scale: 8, density: 0.6, color: "#77736e" },
  blood: { scale: 3, density: 0.7, color: "#a10f20" },
  runes: { scale: 3, density: 0.65, color: "#69a7ff" }
};

// gravewright/maps/frontend/native/builder-editor-model.js
var fields = {
  lights: ["bright_radius", "dim_radius", "intensity", "color", "enabled", "angle", "rotation", "animation"],
  particles: ["kind", "scale", "density", "color", "enabled", "rotation", "light_response", "light_emission"],
  shaders: ["name", "source", "radius", "scale", "intensity", "opacity", "speed", "color", "rotation", "blend_mode", "enabled", "light_response", "light_emission"]
};
var radiusFields = { bright_radius: "brightRadius", dim_radius: "dimRadius" };
var presetSource = /^gravewright-preset:\/\/([^/]+)\/v1$/;
function builderNativeDraft(kind, item) {
  if (!Object.hasOwn(fields, kind)) throw new Error("Invalid effect.");
  const draft = { ...defaults(), ...structuredClone(item) };
  if (kind === "lights") {
    draft.bright_radius = item.brightRadius;
    draft.dim_radius = item.dimRadius;
  } else if (kind === "shaders") {
    const match = presetSource.exec(draft.source);
    if (match) {
      const preset = shaderPresets.find((value) => value.id === match[1]);
      if (!preset) throw new Error("Unknown shader preset.");
      draft.source = preset.source;
    }
  }
  return draft;
}
function validateBuilderNativeDraft(kind, draft) {
  if (!Object.hasOwn(fields, kind)) throw new Error("Invalid effect.");
  const invalid = kind === "lights" ? "Invalid light." : "Invalid effect.";
  const ranges = kind === "lights" ? { bright_radius: [0, 200], dim_radius: [0, 200], intensity: [0, 1], angle: [5, 360], rotation: [-36e3, 36e3] } : {
    scale: [0.1, 20],
    rotation: [-36e3, 36e3],
    light_response: [0, 1],
    light_emission: [0, 2],
    ...kind === "particles" ? { density: [0, 1] } : { radius: [0, 1e6], intensity: [0, 1], opacity: [0, 1], speed: [0, 8] }
  };
  for (const [key, [min, max]] of Object.entries(ranges)) {
    if (typeof draft[key] !== "number" || !Number.isFinite(draft[key]) || draft[key] < min || draft[key] > max) throw new Error(invalid);
  }
  if (typeof draft.enabled !== "boolean" || !/^#[0-9a-f]{6}$/i.test(draft.color)) throw new Error(invalid);
  if (kind === "lights" && !["none", "torch", "pulse", "candle", "fire", "arcane", "smoke"].includes(draft.animation)) throw new Error(invalid);
  if (kind === "particles" && !Object.hasOwn(PARTICLE_DEFAULTS, draft.kind)) throw new Error(invalid);
  if (kind === "shaders") {
    if (typeof draft.name !== "string" || !draft.name.trim() || draft.name.length > 120) throw new Error("Use a name with 1 to 120 characters.");
    if (!["normal", "add", "screen", "multiply"].includes(draft.blend_mode)) throw new Error(invalid);
    if (typeof draft.source !== "string" || !draft.source.trim() || draft.source.length > 32e3 || draft.source.includes("\0")) throw new Error("Invalid shader source.");
  }
}
function builderNativeItem(kind, original, draft) {
  validateBuilderNativeDraft(kind, draft);
  const initial = builderNativeDraft(kind, original), next = structuredClone(original);
  const normalized = { ...draft, rotation: (draft.rotation % 360 + 360) % 360 };
  if (kind === "lights" && normalized.dim_radius > 0) normalized.dim_radius = Math.max(normalized.dim_radius, normalized.bright_radius);
  for (const key of fields[kind]) {
    if (Object.is(normalized[key], initial[key])) continue;
    let value = normalized[key];
    if (key === "name") value = value.trim();
    if (key === "source") {
      const preset = shaderPresets.find((entry) => entry.source === value);
      if (preset) value = `gravewright-preset://${preset.id}/v1`;
    }
    next[kind === "lights" ? radiusFields[key] || key : key] = value;
  }
  return next;
}

// gravewright/maps/frontend/native/builder-editors.js
import { mountModal as mountModal2 } from "/static/gravewright_table/modal.js";
function openBuilderNativeEditor({ kind, item, onSave, onPreview, onClose, t = text }) {
  const original = structuredClone(item);
  let draft = builderNativeDraft(kind, original), closed = false, busy = false, previewTimer, validator;
  const wrapper = document.createElement("section");
  wrapper.className = "table-modal-window map-builder-native-editor";
  wrapper.dataset.builderNativeEditor = kind;
  wrapper.setAttribute("aria-label", t({ lights: "Light source", particles: "Particles", shaders: "Scene shader" }[kind]));
  const host = document.createElement("div");
  host.className = "map-builder-native-editor__host";
  wrapper.append(host);
  const widget2 = kind === "lights" ? LightEditor_native_default : EffectEditor_native_default;
  const editor = widget2(host, { props: { modelValue: draft, kind: kind.slice(0, -1), existing: true, transactional: true, busy: false, error: "" }, emit });
  function issue(error) {
    if (!closed) editor.update({ error: t(error?.message || "Could not save the change.") });
  }
  function candidate() {
    const next = builderNativeItem(kind, original, draft);
    if (kind === "shaders") {
      validator ??= new ShaderDraftValidator();
      const error = validator.validate(draft.source);
      if (error) throw new Error(error);
    }
    return next;
  }
  function preview() {
    clearTimeout(previewTimer);
    if (closed || busy || !onPreview) return;
    previewTimer = setTimeout(() => {
      if (closed || busy) return;
      try {
        const next = candidate();
        editor.update({ error: "" });
        Promise.resolve(onPreview(next)).catch(issue);
      } catch (error) {
        issue(error);
      }
    }, kind === "shaders" ? 250 : 50);
  }
  async function save() {
    if (closed || busy) return;
    clearTimeout(previewTimer);
    let next;
    try {
      next = candidate();
    } catch (error) {
      issue(error);
      return;
    }
    busy = true;
    editor.update({ busy: true, error: "" });
    try {
      await onSave(next);
      if (!closed) wrapper.close(true);
    } catch (error) {
      busy = false;
      if (!closed) {
        editor.update({ busy: false });
        issue(error);
      }
    }
  }
  function emit(type, value) {
    if (closed || busy) return;
    if (type === "update:modelValue") draft = value;
    else if (type === "change") {
      if (kind === "lights" && draft.dim_radius > 0) draft.dim_radius = Math.max(draft.dim_radius, draft.bright_radius);
      preview();
    } else if (type === "save") void save();
    else if (type === "close") wrapper.close();
  }
  wrapper.addEventListener("close", () => {
    if (closed) return;
    closed = true;
    clearTimeout(previewTimer);
    validator?.dispose();
    editor.destroy();
    try {
      Promise.resolve(onPreview?.(null)).catch(() => {
      });
    } finally {
      onClose?.();
    }
  }, { once: true });
  mountModal2(wrapper, { canClose: () => !busy });
  return { close(force = false) {
    if (!closed && (!busy || force)) wrapper.close(force);
  } };
}
export {
  openBuilderNativeEditor
};
