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
    const translated = detail.messages?.text?.[source];
    return typeof translated === "string" ? translated : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
}

// gravewright/maps/frontend/shared/lifecycle/scope.js
var ResourceScope = class {
  #abort = new AbortController();
  #cleanups = [];
  get signal() {
    return this.#abort.signal;
  }
  get closed() {
    return this.signal.aborted;
  }
  own(cleanup) {
    if (this.closed) {
      cleanup();
      return () => {
      };
    }
    this.#cleanups.push(cleanup);
    return () => {
      const i = this.#cleanups.indexOf(cleanup);
      if (i >= 0)
        this.#cleanups.splice(i, 1);
    };
  }
  dispose() {
    if (this.closed)
      return;
    this.#abort.abort();
    const errors = [];
    for (const cleanup of this.#cleanups.splice(0).reverse()) {
      try {
        cleanup();
      } catch (error) {
        errors.push(error);
      }
    }
    if (errors.length)
      throw new AggregateError(errors, "scope_cleanup_failed");
  }
};

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
function scoped(base2, extras = {}) {
  return new Proxy(extras, { has: (_, key) => key !== Symbol.unscopables, get: (o, k) => k === Symbol.unscopables ? void 0 : k in o ? o[k] : base2[k], set: (o, k, v) => {
    if (k in o)
      o[k] = v;
    else
      base2[k] = v;
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
function patch(parent, fresh2) {
  const nodes2 = [...fresh2.childNodes];
  for (let i = 0; i < nodes2.length; i++) {
    const next = nodes2[i];
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
  while (parent.childNodes.length > nodes2.length) {
    dispose(parent.lastChild);
    parent.lastChild.remove();
  }
}
function widget(markup, setup) {
  return function mount(host2, initial) {
    const options2 = { ...initial, props: { ...initial.props } };
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
      const v = key in locals ? locals[key] : key in options2.props ? options2.props[key] : globalThis[key];
      return v?.[CELL] ? v.value : v;
    }, set: (_, key, v) => {
      if (locals[key]?.[CELL])
        locals[key].value = v;
      else if (key in locals)
        locals[key] = v;
      else
        options2.props[key] = v;
      schedule();
      return true;
    } });
    locals = setup(options2, api);
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
          fragment.append(options2.slots?.() || document.createDocumentFragment());
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
          el._options = { ...options2, props, slots: () => children(item.children, scope, false, portalTarget), emit: (name, ...args) => {
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
        const fresh2 = children(markup, ctx, false, freshPortal);
        patch(host2, fresh2);
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
      Object.assign(options2.props, props);
      for (const key of ["emit", "slots"])
        if (next[key])
          options2[key] = next[key];
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
      for (const node of host2.childNodes)
        dispose(node);
      host2.replaceChildren();
      dispose(portal);
      portal.remove();
    } };
  };
}

// gravewright/maps/frontend/features/table-library/ui/ContentDirectory.native.js
var ContentDirectory_native_default = widget([{ "tag": "section", "attrs": { "class": "content-directory" }, "bind": { "aria-label": 'gwText("Table compendiums")' }, "events": [], "children": [{ "tag": "p", "attrs": { "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "p", "attrs": { "class": "content-directory__empty" }, "bind": {}, "events": [], "children": [{ "tag": "PhBooks", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("No active content package.")' }], "when": "!packages.length && !error" }, { "tag": "details", "attrs": { "class": "content-directory__package" }, "bind": { "key": "item.id" }, "events": [{ "event": "toggle", "code": "$event.target.open && openPackage(item);", "mods": [] }], "children": [{ "tag": "summary", "attrs": { "class": "content-directory__heading" }, "bind": {}, "events": [], "children": [{ "tag": "PhBooks", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "item.name || item.id" }] }, { "tag": "details", "attrs": { "class": "content-directory__pack" }, "bind": { "key": "pack.id" }, "events": [{ "event": "toggle", "code": "$event.target.open && openPack(item, pack);", "mods": [] }], "children": [{ "tag": "summary", "attrs": { "class": "content-directory__heading" }, "bind": {}, "events": [], "children": [{ "tag": "PhFolder", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "pack.label || pack.name || pack.id" }] }, { "tag": "div", "attrs": { "class": "content-directory__entry" }, "bind": { "key": "entry.id" }, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "entry.name || entry.id" }] }, { "tag": "button", "attrs": { "class": "content-directory__import", "type": "button" }, "bind": { "disabled": "!!busy", "aria-label": "`Importar ${entry.name || entry.id}`" }, "events": [{ "event": "click", "code": "importEntry(item, pack, entry);", "mods": [] }], "children": [{ "tag": "PhDownloadSimple", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "each": { "names": ["entry"], "value": "pack.entries" } }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Empty package.")' }], "when": "pack.entries?.length === 0" }], "each": { "names": ["pack"], "value": "item.packs" } }], "each": { "names": ["item"], "value": "packages" } }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhBooks = "PhBooks";
  const PhFolder = "PhFolder";
  const PhDownloadSimple = "PhDownloadSimple";
  const HttpClient = options2.HttpClient;
  const props = options2.props;
  const packages = ref([]), error = ref(""), busy = ref("");
  const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal);
  const query = `?campaign_id=${encodeURIComponent(props.containerId)}`;
  async function load() {
    try {
      const data = await http.get(`/game/content/active-packages${query}`);
      if (!scope.closed) packages.value = data.packages;
    } catch {
      if (!scope.closed) error.value = text("Could not load compendiums.");
    }
  }
  async function openPackage(item) {
    if (item.packs) return;
    try {
      const data = await http.get(`/game/content/packs/${encodeURIComponent(item.id)}${query}`);
      if (!scope.closed) item.packs = data.packs;
      packages.value = [...packages.value];
    } catch {
      if (!scope.closed) error.value = text("Could not load packages.");
    }
  }
  async function openPack(item, pack) {
    if (pack.entries) return;
    try {
      const data = await http.get(`/game/content/pack/${encodeURIComponent(item.id)}/${encodeURIComponent(pack.id)}${query}`);
      if (!scope.closed) pack.entries = data.entries;
      packages.value = [...packages.value];
    } catch {
      if (!scope.closed) error.value = text("Could not load entries.");
    }
  }
  async function importEntry(item, pack, entry) {
    busy.value = entry.id;
    error.value = "";
    try {
      await http.post(["item_pack", "spell_pack"].includes(pack.type) ? "/game/item/content/import" : "/game/content/import", { campaign_id: props.containerId, package_id: item.id, pack_id: pack.id, entry_id: entry.id });
    } catch {
      if (!scope.closed) error.value = text("Could not import this entry.");
    } finally {
      if (!scope.closed) busy.value = "";
    }
  }
  onMounted(load);
  onBeforeUnmount(() => scope.dispose());
  return { gwText: text, PhBooks, PhFolder, PhDownloadSimple, ResourceScope, HttpClient, props, packages, error, busy, scope, http, query, load, openPackage, openPack, importEntry, emit: options2.emit };
});

// gravewright/maps/frontend/features/table-library/model/library-upload.js
var IMAGE_ACCEPT = "image/png,image/jpeg,image/webp";
var AUDIO_ACCEPT = "audio/ogg,audio/opus,audio/mpeg,audio/mp4,audio/wav,.ogg,.opus,.mp3,.m4a,.wav";
var mimeByExtension = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", ogg: "audio/ogg", opus: "audio/opus", mp3: "audio/mpeg", m4a: "audio/mp4", wav: "audio/wav", pdf: "application/pdf" };
function uploadMime(file) {
  return file.type || mimeByExtension[file.name.split(".").at(-1)?.toLowerCase() ?? ""] || "";
}
function validateUpload(file, imagesOnly = false) {
  const mime = uploadMime(file), image = IMAGE_ACCEPT.split(",").includes(mime), audio = AUDIO_ACCEPT.split(",").includes(mime), pdf = mime === "application/pdf";
  if (!image && (imagesOnly || !audio && !pdf))
    return text("Unsupported format.");
  if (!file.size)
    return text("The file is empty.");
  const max = (image ? 10 : pdf ? 25 : 100) * 1024 * 1024;
  if (file.size > max)
    return text("This file's limit is {0} MB.", max / 1024 / 1024);
}
function uploadFile(file) {
  const type = uploadMime(file);
  return type === file.type ? file : new File([file], file.name, { type, lastModified: file.lastModified });
}
function uploadError(error) {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes("asset_in_use"))
    return text("This file is in use and cannot be deleted.");
  if (message.includes("too_large"))
    return "O arquivo excede o tamanho permitido.";
  if (message.includes("unsupported") || message.includes("invalid_image"))
    return text("Invalid file or unsupported format.");
  if (message.includes("denied") || message.includes("forbidden"))
    return text("You do not have permission for this action.");
  return text("Could not complete the action. Check the connection and try again.");
}

// gravewright/maps/frontend/features/table-library/ui/DeckUpload.native.js
var DeckUpload_native_default = widget([{ "tag": "form", "attrs": { "class": "deck-upload" }, "bind": {}, "events": [{ "event": "submit", "code": "create;", "mods": ["prevent"] }], "children": [{ "tag": "p", "attrs": { "class": "deck-upload__intro" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("One image per card, with an optional shared back for the deck.")' }] }, { "tag": "fieldset", "attrs": {}, "bind": { "disabled": "busy || !!definition" }, "events": [], "children": [{ "tag": "label", "attrs": { "class": "deck-upload__field" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Deck name")' }, { "tag": "input", "attrs": { "name": "name", "minlength": "2", "maxlength": "120", "required": "" }, "bind": { "placeholder": 'gwText("Deck name")' }, "events": [], "children": [], "model": { "path": "name", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "deck-upload__files" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "deck-upload__file" }, "bind": {}, "events": [], "children": [{ "tag": "PhCardsThree", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Card fronts")' }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("PNG, JPEG or WebP \\xB7 up to 10 MB per image")' }] }] }, { "tag": "input", "attrs": { "type": "file", "name": "fronts", "multiple": "" }, "bind": { "accept": "IMAGE_ACCEPT", "aria-label": 'gwText("Card fronts")' }, "events": [{ "event": "change", "code": 'files($event, "front");', "mods": [] }], "children": [] }] }, { "tag": "label", "attrs": { "class": "deck-upload__file" }, "bind": {}, "events": [], "children": [{ "tag": "img", "attrs": {}, "bind": { "src": "back.url", "alt": 'gwText("Card back preview")' }, "events": [], "children": [], "when": "back" }, { "tag": "PhUploadSimple", "attrs": {}, "bind": {}, "events": [], "children": [], "otherwise": true }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'back ? back.file.name : gwText("Optional back")' }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Used for all cards")' }] }] }, { "tag": "input", "attrs": { "type": "file", "name": "back" }, "bind": { "accept": "IMAGE_ACCEPT", "aria-label": 'gwText("Card backs")' }, "events": [{ "event": "change", "code": 'files($event, "back");', "mods": [] }], "children": [] }] }] }, { "tag": "button", "attrs": { "type": "button", "class": "deck-upload__remove-back" }, "bind": {}, "events": [{ "event": "click", "code": "dispose(back);\nback = void 0;", "mods": [] }], "children": [{ "value": 'gwText("Remove card back")' }], "when": "back" }, { "tag": "div", "attrs": { "class": "deck-upload__previews" }, "bind": {}, "events": [], "children": [{ "tag": "article", "attrs": { "class": "deck-upload__card" }, "bind": { "key": "draft.url" }, "events": [], "children": [{ "tag": "img", "attrs": { "loading": "lazy" }, "bind": { "src": "draft.url", "alt": "draft.name" }, "events": [], "children": [] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "aria-label": 'gwText("Remove {0}", draft.name)' }, "events": [{ "event": "click", "code": "remove(index);", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "input", "attrs": { "maxlength": "191", "required": "" }, "bind": { "aria-label": 'gwText("Card {0} name", index + 1)' }, "events": [], "children": [], "model": { "path": "draft.name", "mods": [] } }], "each": { "names": ["draft", "index"], "value": "fronts" } }], "when": "fronts.length" }] }, { "tag": "p", "attrs": { "class": "deck-upload__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "p", "attrs": { "class": "deck-upload__notice", "role": "status" }, "bind": {}, "events": [], "children": [{ "value": "notice" }], "when": "notice" }, { "tag": "progress", "attrs": { "max": "100" }, "bind": { "value": "progress", "aria-label": 'gwText("Card upload progress")' }, "events": [], "children": [], "when": "busy" }, { "tag": "footer", "attrs": { "class": "deck-upload__footer" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "fronts.length" }, { "text": " " }, { "value": 'gwText("card(s)")' }] }, { "tag": "button", "attrs": { "type": "submit" }, "bind": { "disabled": "busy || !fronts.length || name.trim().length < 2" }, "events": [], "children": [{ "tag": "PhUploadSimple", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'busy ? gwText("Uploading\\u2026") : definition ? gwText("Add to table") : gwText("Create deck")' }] }] }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhCardsThree = "PhCardsThree";
  const PhUploadSimple = "PhUploadSimple";
  const PhX = "PhX";
  const HttpClient = options2.HttpClient;
  const props = options2.props;
  const emit = options2.emit;
  const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal), root2 = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
  const name = ref(""), fronts = ref([]), back = ref(), busy = ref(false), error = ref(""), notice = ref(""), progress = ref(0), definition = ref();
  function dispose2(draft) {
    URL.revokeObjectURL(draft.url);
  }
  function files(event, side) {
    const input = event.target, chosen = Array.from(input.files ?? []);
    input.value = "";
    error.value = "";
    if (busy.value || definition.value) return;
    for (const file of chosen) {
      const invalid = validateUpload(file, true);
      if (invalid) {
        error.value += `${file.name}: ${invalid}
`;
        continue;
      }
      if (side === "front" && fronts.value.length >= 500) {
        error.value += text("The deck accepts up to 500 cards.\n");
        break;
      }
      const draft = { file, url: URL.createObjectURL(file), name: file.name.replace(/\.[^.]+$/, "") || text("Card") };
      if (side === "back") {
        if (back.value) dispose2(back.value);
        back.value = draft;
      } else fronts.value.push(draft);
    }
  }
  function remove(index) {
    const draft = fronts.value.splice(index, 1)[0];
    if (draft) dispose2(draft);
  }
  function clear() {
    fronts.value.forEach(dispose2);
    fronts.value = [];
    if (back.value) dispose2(back.value);
    back.value = void 0;
    name.value = "";
    definition.value = void 0;
  }
  async function upload(draft, purpose) {
    if (draft.assetId) return draft.assetId;
    const form = new FormData();
    form.append("file", uploadFile(draft.file));
    form.append("purpose", purpose);
    progress.value = 0;
    const result = await http.upload(root2 + "/card-upload", form, (p) => {
      if (!scope.closed) progress.value = p;
    });
    draft.assetId = result.asset_id;
    return result.asset_id;
  }
  async function create() {
    if (busy.value || name.value.trim().length < 2 || !fronts.value.length) return;
    busy.value = true;
    error.value = "";
    try {
      if (!definition.value) {
        notice.value = text("Uploading card back\u2026");
        const backId = back.value ? await upload(back.value, "card_back") : null;
        const cards = [];
        for (const [index, draft] of fronts.value.entries()) {
          scope.signal.throwIfAborted();
          notice.value = `Enviando carta ${index + 1}/${fronts.value.length} \xB7 ${draft.file.name}`;
          cards.push({ name: draft.name, front_asset_id: await upload(draft, "card_front"), back_asset_id: backId });
        }
        notice.value = text("Creating deck\u2026");
        const result = await http.post(root2 + "/cards/define", { name: name.value.trim(), description: "", default_back_asset_id: backId, cards });
        definition.value = result.deck.id;
      }
      notice.value = text("Adding deck to the table\u2026");
      await http.post(root2 + "/cards/instantiate", { deck_definition_id: definition.value });
      if (!scope.closed) {
        const title = name.value;
        clear();
        notice.value = text("Deck \u201C{0}\u201D created and available at the table.", title);
        emit("created");
      }
    } catch (e) {
      if (!scope.closed) {
        error.value = uploadError(e);
        notice.value = definition.value ? text("The deck was created. Try again to add it to the table.") : text("Uploaded files will be reused when you try again.");
      }
    } finally {
      if (!scope.closed) {
        busy.value = false;
        progress.value = 0;
      }
    }
  }
  onBeforeUnmount(() => {
    scope.dispose();
    clear();
  });
  return { gwText: text, PhCardsThree, PhUploadSimple, PhX, HttpClient, ResourceScope, IMAGE_ACCEPT, uploadError, uploadFile, validateUpload, props, emit, scope, http, root: root2, name, fronts, back, busy, error, notice, progress, definition, dispose: dispose2, files, remove, clear, upload, create };
});

// gravewright/maps/frontend/features/audio/ui/IndividualAudioControl.native.js
var IndividualAudioControl_native_default = widget([{ "tag": "div", "attrs": { "class": "individual-audio", "role": "group" }, "bind": { "aria-label": 'gwText("Audio on this device")' }, "events": [], "children": [{ "tag": "button", "attrs": { "class": "individual-audio__toggle", "type": "button" }, "bind": { "aria-label": 'enabled ? gwText("Mute audio") : gwText("Enable audio")', "title": 'enabled ? gwText("Mute only on this device") : gwText("Play audio on this device")', "aria-pressed": "enabled" }, "events": [{ "event": "click", "code": 'emit("toggle");', "mods": [] }], "children": [{ "tag": "component", "attrs": { "aria-hidden": "true" }, "bind": { "is": "enabled && volume > 0 ? PhSpeakerHigh : PhSpeakerSlash" }, "events": [], "children": [] }] }, { "tag": "input", "attrs": { "class": "individual-audio__volume", "type": "range", "min": "0", "max": "100", "step": "1" }, "bind": { "value": "Math.round(volume * 100)", "aria-label": 'gwText("Individual volume")', "aria-valuetext": "`${Math.round(volume * 100)}% \\u2014 somente neste dispositivo`", "title": "`Volume individual: ${Math.round(volume * 100)}%`" }, "events": [{ "event": "input", "code": "changeVolume;", "mods": [] }], "children": [] }, { "tag": "button", "attrs": { "class": "individual-audio__toggle" }, "bind": { "aria-label": 'gwText("Individual mixer")', "aria-expanded": "expanded" }, "events": [{ "event": "click", "code": "expanded = !expanded;", "mods": [] }], "children": [{ "tag": "PhSlidersHorizontal", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "div", "attrs": { "class": "individual-audio__mixer" }, "bind": {}, "events": [{ "event": "keydown", "code": "expanded = false;", "mods": ["esc", "stop"] }], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Audio on this device")' }] }, { "tag": "label", "attrs": {}, "bind": { "key": "key" }, "events": [], "children": [{ "value": "label" }, { "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": "0.01" }, "bind": { "value": "channels[key] ?? 1", "aria-label": "`Volume de ${label}`" }, "events": [{ "event": "input", "code": 'emit("channels", { ...channels, [key]: Number($event.target.value) });', "mods": [] }], "children": [] }], "each": { "names": ["[key", "label]"], "value": '[["music", gwText("Music")], ["ambience", gwText("Ambience")], ["sfx", gwText("Effects")], ["cinematic", gwText("Cinematic")]]' } }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": `gwText("Does not change other players' volume.")` }] }], "when": "expanded" }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhSpeakerHigh = "PhSpeakerHigh";
  const PhSpeakerSlash = "PhSpeakerSlash";
  const PhSlidersHorizontal = "PhSlidersHorizontal";
  options2.props;
  const emit = options2.emit;
  const expanded = ref(false);
  function changeVolume(event) {
    emit("volume", Number(event.target.value) / 100);
  }
  return { gwText: text, PhSpeakerHigh, PhSpeakerSlash, PhSlidersHorizontal, emit, expanded, changeVolume };
});

// gravewright/maps/frontend/features/cards/model/hand.js
function fanLayout(count, available) {
  let width = 130, step = width * 0.62;
  if (count > 1 && width + (count - 1) * step > available) step = Math.max(width * 0.26, (available - width) / (count - 1));
  if (count > 1 && width + (count - 1) * step > available) {
    width = Math.max(64, available / (1 + (count - 1) * 0.26));
    step = width * 0.26;
  }
  return { width: Math.round(width), overlap: Math.round(step - width) };
}
function fanPose(index, count) {
  const offset = index - (count - 1) / 2;
  return { rotation: offset * Math.min(7, 22 / Math.max(1, count - 1)), arc: Math.abs(offset) * 5 };
}
function cardFace(card, flipped) {
  return (flipped ? card.backUrl : card.frontUrl) || "";
}

// gravewright/maps/frontend/features/cards/ui/CardHand.native.js
var CardHand_native_default = widget([{ "tag": "section", "attrs": { "ref": "host", "class": "card-hand" }, "bind": { "aria-label": 'gwText("Your hand")' }, "events": [], "children": [{ "tag": "header", "attrs": { "class": "card-hand__bar" }, "bind": {}, "events": [], "children": [{ "tag": "PhCardsThree", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "select", "attrs": {}, "bind": { "aria-label": 'gwText("Deck")', "disabled": "!state.decks.length" }, "events": [], "children": [{ "tag": "option", "attrs": { "value": "" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("No deck available")' }], "when": "!state.decks.length" }, { "tag": "option", "attrs": {}, "bind": { "key": "d.id", "value": "d.id" }, "events": [], "children": [{ "value": "d.name" }], "each": { "names": ["d"], "value": "state.decks" } }], "model": { "path": "deckId", "mods": [] } }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy || !deck?.draw_count" }, "events": [{ "event": "click", "code": "deck && openDraw(deck);", "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Draw")' }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "deck?.draw_count ?? 0" }, { "text": " " }, { "value": 'gwText("remaining")' }] }, { "tag": "button", "attrs": {}, "bind": { "aria-pressed": "manage" }, "events": [{ "event": "click", "code": "manage = !manage;", "mods": [] }], "children": [{ "tag": "PhCardsThree", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'manage ? gwText("Hand") : gwText("Decks")' }], "when": "gm" }] }, { "tag": "p", "attrs": { "class": "card-hand__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "div", "attrs": { "class": "card-hand__fan" }, "bind": { "style": '({ "--card-width": `${layout.width}px`, "--overlap": `${layout.overlap}px` })' }, "events": [], "children": [{ "tag": "p", "attrs": { "class": "card-hand__empty" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Your hand is empty. Draw a card.")' }], "when": "!cards.length" }, { "tag": "article", "attrs": { "class": "card-hand__card", "tabindex": "0" }, "bind": { "key": "card.id", "style": "pose(index)", "draggable": "!busy", "aria-label": "card.name", "title": 'gwText("Drag to the table")' }, "events": [{ "event": "dragstart", "code": "drag($event, card);", "mods": [] }, { "event": "dblclick", "code": "preview = card;", "mods": [] }, { "event": "keydown", "code": "preview = card;", "mods": ["enter", "prevent"] }], "children": [{ "tag": "img", "attrs": { "draggable": "false" }, "bind": { "src": "cardFace(card, flipped.has(card.id))", "alt": 'flipped.has(card.id) ? gwText("Back") : card.name' }, "events": [], "children": [], "when": "cardFace(card, flipped.has(card.id))" }, { "tag": "PhCardsThree", "attrs": { "class": "card-hand__back" }, "bind": {}, "events": [], "children": [], "otherwise": true }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "card.name" }] }, { "tag": "div", "attrs": { "class": "card-hand__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "aria-label": "`Ampliar ${card.name}`" }, "events": [{ "event": "click", "code": "preview = card;", "mods": [] }], "children": [{ "tag": "PhMagnifyingGlassPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": 'flipped.has(card.id) ? gwText("Show front") : gwText("Show back")' }, "events": [{ "event": "click", "code": "flip(card);", "mods": [] }], "children": [{ "tag": "PhArrowsClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Discard card")' }, "events": [{ "event": "click", "code": 'command("discard", { card_ids: [card.id] });', "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }], "each": { "names": ["card", "index"], "value": "cards" } }], "when": "!manage" }, { "tag": "div", "attrs": { "class": "card-hand__decks" }, "bind": {}, "events": [], "children": [{ "tag": "details", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "summary", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Create deck")' }] }, { "tag": "DeckUpload", "attrs": {}, "bind": { "container-id": "containerId" }, "events": [{ "event": "created", "code": "refresh;", "mods": [] }], "children": [] }] }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("No deck in play.")' }], "when": "!state.decks.length" }, { "tag": "article", "attrs": { "class": "card-hand__deck" }, "bind": { "key": "d.id" }, "events": [], "children": [{ "tag": "PhCardsThree", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "div", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "d.name" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "d.draw_count" }, { "text": " " }, { "value": 'gwText("cards remaining")' }] }] }, { "tag": "div", "attrs": { "class": "card-hand__deck-actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "busy || !d.draw_count" }, "events": [{ "event": "click", "code": "openDraw(d);", "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Draw")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("shuffle", { deck_instance_id: d.id });', "mods": [] }], "children": [{ "tag": "PhShuffle", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Shuffle")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("reset", { deck_instance_id: d.id });', "mods": [] }], "children": [{ "tag": "PhArrowsClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Recall")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "deleteDeck = d;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Remove")' }] }] }], "each": { "names": ["d"], "value": "state.decks" } }], "otherwise": true }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "card-hand__veil" }, "bind": {}, "events": [{ "event": "keydown", "code": "", "mods": ["stop"] }, { "event": "click", "code": "preview = void 0;", "mods": ["self"] }, { "event": "keydown", "code": "preview = void 0;", "mods": ["esc", "stop"] }], "children": [{ "tag": "section", "attrs": { "class": "card-hand__preview", "role": "dialog", "aria-modal": "true" }, "bind": { "aria-label": "preview.name" }, "events": [], "children": [{ "tag": "header", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'flipped.has(preview.id) ? gwText("Back") : preview.name' }] }, { "tag": "button", "attrs": { "autofocus": "" }, "bind": { "aria-label": 'gwText("Close preview")' }, "events": [{ "event": "click", "code": "preview = void 0;", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "img", "attrs": {}, "bind": { "src": "cardFace(preview, flipped.has(preview.id))", "alt": "preview.name" }, "events": [], "children": [], "when": "cardFace(preview, flipped.has(preview.id))" }, { "tag": "PhCardsThree", "attrs": {}, "bind": {}, "events": [], "children": [], "otherwise": true }] }], "when": "preview" }, { "tag": "div", "attrs": { "class": "card-hand__veil" }, "bind": {}, "events": [{ "event": "keydown", "code": "", "mods": ["stop"] }, { "event": "click", "code": "!busy && (drawDeck = void 0);", "mods": ["self"] }, { "event": "keydown", "code": "!busy && (drawDeck = void 0);", "mods": ["esc", "stop"] }], "children": [{ "tag": "form", "attrs": { "class": "card-hand__draw", "role": "dialog", "aria-modal": "true" }, "bind": { "aria-label": 'gwText("Draw cards")' }, "events": [{ "event": "submit", "code": "draw;", "mods": ["prevent"] }], "children": [{ "tag": "header", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhCardsThree", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "div", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "drawDeck.name" }] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Draw cards")' }] }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy", "aria-label": 'gwText("Close draw dialog")' }, "events": [{ "event": "click", "code": "drawDeck = void 0;", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "card-hand__choices" }, "bind": {}, "events": [], "children": [{ "tag": "fieldset", "attrs": {}, "bind": { "disabled": "busy" }, "events": [], "children": [{ "tag": "legend", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Destination")' }] }, { "tag": "label", "attrs": {}, "bind": { "key": "choice.id" }, "events": [], "children": [{ "tag": "input", "attrs": { "type": "radio" }, "bind": { "value": "choice.id" }, "events": [], "children": [], "model": { "path": "destination", "mods": [] } }, { "tag": "component", "attrs": {}, "bind": { "is": "choice.icon" }, "events": [], "children": [] }, { "value": "choice.label" }], "each": { "names": ["choice"], "value": '[{ id: "hand", label: gwText("Hand"), icon: PhHand }, { id: "table", label: gwText("Table"), icon: PhMapTrifold }, { id: "chat", label: "Chat", icon: PhChatCircleText }]' } }] }, { "tag": "fieldset", "attrs": {}, "bind": { "disabled": "busy" }, "events": [], "children": [{ "tag": "legend", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("State")' }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "radio", "value": "face_up" }, "bind": {}, "events": [], "children": [], "model": { "path": "face", "mods": [] } }, { "tag": "PhEye", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Front")' }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "radio", "value": "face_down" }, "bind": {}, "events": [], "children": [], "model": { "path": "face", "mods": [] } }, { "tag": "PhEyeSlash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Back")' }] }] }] }, { "tag": "label", "attrs": { "class": "card-hand__quantity" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Quantity")' }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy || count <= 1", "aria-label": 'gwText("Decrease quantity")' }, "events": [{ "event": "click", "code": "count--;", "mods": [] }], "children": [{ "tag": "PhMinus", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "input", "attrs": { "type": "number", "min": "1", "step": "1", "required": "" }, "bind": { "max": "drawDeck.draw_count", "disabled": "busy" }, "events": [], "children": [], "model": { "path": "count", "mods": ["number"] } }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy || count >= drawDeck.draw_count", "aria-label": 'gwText("Increase quantity")' }, "events": [{ "event": "click", "code": "count++;", "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "drawDeck.draw_count" }, { "value": 'gwText(" available")' }] }] }, { "tag": "p", "attrs": { "class": "card-hand__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "footer", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "drawDeck = void 0;", "mods": [] }], "children": [{ "value": 'gwText("Cancel")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [], "children": [{ "value": 'busy ? gwText("Drawing\\u2026") : gwText("Draw")' }] }] }] }], "when": "drawDeck" }, { "tag": "div", "attrs": { "class": "card-hand__veil" }, "bind": {}, "events": [{ "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "section", "attrs": { "class": "card-hand__draw", "role": "dialog" }, "bind": { "aria-label": 'gwText("Remove deck")' }, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Remove ")' }, { "value": "deleteDeck.name" }, { "text": "?" }] }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": `gwText("This deck's cards in hands, the discard pile, and the table will be removed.")` }] }, { "tag": "footer", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "deleteDeck = void 0;", "mods": [] }], "children": [{ "value": 'gwText("Cancel")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("delete", { deck_instance_id: deleteDeck.id }).then((result) => {\n  if (result) deleteDeck = void 0;\n});', "mods": [] }], "children": [{ "value": 'gwText("Remove")' }] }] }] }], "when": "deleteDeck" }] }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhCardsThree = "PhCardsThree";
  const PhPlus = "PhPlus";
  const PhMinus = "PhMinus";
  const PhMagnifyingGlassPlus = "PhMagnifyingGlassPlus";
  const PhArrowsClockwise = "PhArrowsClockwise";
  const PhTrash = "PhTrash";
  const PhShuffle = "PhShuffle";
  const PhX = "PhX";
  const PhHand = "PhHand";
  const PhEye = "PhEye";
  const PhEyeSlash = "PhEyeSlash";
  const PhChatCircleText = "PhChatCircleText";
  const PhMapTrifold = "PhMapTrifold";
  const HttpClient = options2.HttpClient;
  const props = options2.props;
  const emit = options2.emit;
  const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal), root2 = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
  const state = ref({ decks: [], hand: [] }), deckId = ref(""), manage = ref(false), busy = ref(false), error = ref(""), flipped = ref(/* @__PURE__ */ new Set()), preview = ref(), drawDeck = ref(), count = ref(1), destination = ref("hand"), face = ref("face_up"), deleteDeck = ref();
  const host2 = ref(), available = ref(550);
  let observer, visit = 0;
  const deck = computed(() => state.value.decks.find((d) => d.id === deckId.value));
  const cards = computed(() => state.value.hand.filter((c) => c.deck_instance_id === deckId.value));
  const layout = computed(() => fanLayout(cards.value.length, available.value - 42));
  function pose(index) {
    const p = fanPose(index, cards.value.length);
    return { "--rotation": `${p.rotation}deg`, "--arc": `${p.arc}px`, "--order": index + 1 };
  }
  async function refresh2() {
    const id = ++visit;
    try {
      const next = await http.get(root2 + "/card-state");
      if (scope.closed || id !== visit) return;
      state.value = next;
      if (!next.decks.some((d) => d.id === deckId.value)) deckId.value = next.decks[0]?.id ?? "";
      flipped.value = new Set([...flipped.value].filter((id2) => next.hand.some((c) => c.id === id2)));
      if (preview.value && !next.hand.some((c) => c.id === preview.value.id)) preview.value = void 0;
    } catch {
      if (!scope.closed) error.value = text("Could not load your cards.");
    }
  }
  async function command2(action, data) {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      const result = await http.post(root2 + "/cards/" + action, data);
      await refresh2();
      return result;
    } catch {
      if (!scope.closed) error.value = text("Could not complete the action. The deck may have changed or the action is not allowed.");
    } finally {
      if (!scope.closed) busy.value = false;
    }
  }
  function openDraw(target) {
    drawDeck.value = target;
    count.value = 1;
    try {
      destination.value = sessionStorage.getItem("gravewright.cards.draw.destination") || "hand";
      face.value = sessionStorage.getItem("gravewright.cards.draw.face") || "face_up";
    } catch {
    }
    if (!["hand", "table", "chat"].includes(destination.value)) destination.value = "hand";
    if (!["face_up", "face_down"].includes(face.value)) face.value = "face_up";
  }
  async function draw() {
    if (!drawDeck.value || busy.value) return;
    if (destination.value !== "hand" && !props.blockId) {
      error.value = text("Open a scene to use this destination.");
      return;
    }
    const result = await command2("draw", { deck_instance_id: drawDeck.value.id, count: count.value, destination: destination.value === "table" ? "hand" : destination.value, reveal: face.value === "face_up", ...destination.value === "chat" ? { block_id: props.blockId } : {} });
    if (!result || scope.closed) return;
    try {
      sessionStorage.setItem("gravewright.cards.draw.destination", destination.value);
      sessionStorage.setItem("gravewright.cards.draw.face", face.value);
    } catch {
    }
    drawDeck.value = void 0;
    if (destination.value === "table") emit("place", result.cards ?? [], face.value === "face_up");
  }
  function flip(card) {
    const next = new Set(flipped.value);
    if (next.has(card.id)) next.delete(card.id);
    else next.add(card.id);
    flipped.value = next;
  }
  function drag(event, card) {
    if (busy.value) {
      event.preventDefault();
      return;
    }
    event.dataTransfer?.setData("application/x-gravewright-hand-card", JSON.stringify({ cardId: card.id, reveal: !flipped.value.has(card.id) }));
  }
  watch(() => props.revision, () => void refresh2());
  function escape(event) {
    if (event.key === "Escape" && !busy.value) {
      preview.value = void 0;
      drawDeck.value = void 0;
      deleteDeck.value = void 0;
    }
  }
  onMounted(() => {
    window.addEventListener("keydown", escape);
    void refresh2();
    observer = new ResizeObserver((entries) => {
      available.value = entries[0]?.contentRect.width ?? 550;
    });
    if (host2.value) observer.observe(host2.value);
  });
  onBeforeUnmount(() => {
    window.removeEventListener("keydown", escape);
    scope.dispose();
    observer?.disconnect();
  });
  return { gwText: text, PhCardsThree, PhPlus, PhMinus, PhMagnifyingGlassPlus, PhArrowsClockwise, PhTrash, PhShuffle, PhX, PhHand, PhEye, PhEyeSlash, PhChatCircleText, PhMapTrifold, HttpClient, ResourceScope, DeckUpload: DeckUpload_native_default, cardFace, fanLayout, fanPose, props, emit, scope, http, root: root2, state, deckId, manage, busy, error, flipped, preview, drawDeck, count, destination, face, deleteDeck, host: host2, available, observer, visit, deck, cards, layout, pose, refresh: refresh2, command: command2, openDraw, draw, flip, drag, escape };
});

// gravewright/maps/frontend/features/cards/ui/CardPlacement.native.js
var CardPlacement_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "card-placement" }, "bind": {}, "events": [{ "event": "pointermove", "code": "move;", "mods": ["stop"] }, { "event": "pointerdown", "code": "place;", "mods": ["stop", "prevent"] }, { "event": "pointerup", "code": "", "mods": ["stop"] }, { "event": "contextmenu", "code": '!busy && emit("close");', "mods": ["stop", "prevent"] }], "children": [{ "tag": "g", "attrs": { "opacity": ".75" }, "bind": { "transform": "`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale}) translate(${point.x} ${point.y})`" }, "events": [], "children": [{ "tag": "rect", "attrs": { "x": "-28", "y": "-40", "width": "56", "height": "80", "rx": "5", "fill": "#182328", "stroke": "#c09a5a" }, "bind": {}, "events": [], "children": [] }, { "tag": "image", "attrs": { "x": "-28", "y": "-40", "width": "56", "height": "80" }, "bind": { "href": "cardFace(cards[index], !reveal)" }, "events": [], "children": [] }], "when": "point && cards[index]" }] }, { "tag": "p", "attrs": { "class": "card-placement__hint", "role": "status" }, "bind": {}, "events": [], "children": [{ "value": 'error || (busy ? gwText("Playing card\\u2026") : gwText("Click to play {0}/{1}. Esc cancels; remaining cards stay in your hand.", index + 1, cards.length))' }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const BlockStateApi = class {
    command(c, b, area, action, data) {
      return options2.command(area, action, data);
    }
    state() {
      return options2.read();
    }
  };
  const HttpClient = options2.HttpClient;
  const props = options2.props;
  const emit = options2.emit;
  const root2 = ref(), point = ref(), busy = ref(false), index = ref(0), error = ref("");
  const abort = new AbortController(), api = new BlockStateApi(new HttpClient(void 0, () => abort.signal));
  function move(e) {
    const box = root2.value.getBoundingClientRect();
    point.value = { x: (e.clientX - box.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - box.top - props.viewport.y) / props.viewport.scale };
  }
  async function place(e) {
    if (e.button !== 0 || busy.value) return;
    e.stopPropagation();
    move(e);
    const card = props.cards[index.value];
    if (!card || !point.value) return;
    busy.value = true;
    try {
      await api.command(props.containerId, props.blockId, "cards", "play", { card_id: card.id, ...point.value, reveal: props.reveal });
      if (abort.signal.aborted) return;
      emit("refresh");
      index.value++;
      if (index.value >= props.cards.length) emit("close");
    } catch {
      if (!abort.signal.aborted) error.value = text("Could not play the card. Try again.");
    } finally {
      busy.value = false;
    }
  }
  function cancel(e) {
    if (e.key === "Escape" && !busy.value) {
      e.stopPropagation();
      emit("close");
    }
  }
  onMounted(() => window.addEventListener("keydown", cancel));
  onBeforeUnmount(() => {
    abort.abort();
    window.removeEventListener("keydown", cancel);
  });
  return { gwText: text, BlockStateApi, HttpClient, cardFace, props, emit, root: root2, point, busy, index, error, abort, api, move, place, cancel };
});

// gravewright/maps/frontend/shared/ui/directory/DirectoryContextMenu.native.js
var DirectoryContextMenu_native_default = widget([{ "tag": "menu", "attrs": { "ref": "menu", "class": "gw-folder-menu directory-context-menu" }, "bind": { "aria-label": "label", "style": "{ left: `${position.x}px`, top: `${position.y}px` }" }, "events": [{ "event": "click", "code": "", "mods": ["stop"] }, { "event": "contextmenu", "code": "", "mods": ["prevent", "stop"] }], "children": [{ "tag": "slot", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const props = options2.props;
  const emit = options2.emit;
  const menu = ref();
  const position = ref({ x: props.x, y: props.y });
  function place() {
    const rect = menu.value?.getBoundingClientRect();
    if (rect) position.value = { x: Math.max(8, Math.min(props.x, innerWidth - rect.width - 8)), y: Math.max(8, Math.min(props.y, innerHeight - rect.height - 8)) };
  }
  function outside(event) {
    if (!menu.value?.contains(event.target)) emit("close");
  }
  function other(event) {
    if (event.detail !== menu.value) emit("close");
  }
  function keyboard(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      emit("close");
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const buttons = [...menu.value?.querySelectorAll("button:not(:disabled)") ?? []];
    if (!buttons.length) return;
    event.preventDefault();
    const index = buttons.indexOf(document.activeElement);
    buttons[event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (index + (event.key === "ArrowUp" ? -1 : 1) + buttons.length) % buttons.length]?.focus();
  }
  watch(() => [props.x, props.y], async () => {
    await nextTick();
    place();
  });
  onMounted(() => {
    place();
    document.dispatchEvent(new CustomEvent("gravewright:directory-menu", { detail: menu.value }));
    document.addEventListener("gravewright:directory-menu", other);
    document.addEventListener("pointerdown", outside);
    document.addEventListener("contextmenu", outside);
    document.addEventListener("keydown", keyboard);
    window.addEventListener("resize", place);
  });
  onBeforeUnmount(() => {
    document.removeEventListener("gravewright:directory-menu", other);
    document.removeEventListener("pointerdown", outside);
    document.removeEventListener("contextmenu", outside);
    document.removeEventListener("keydown", keyboard);
    window.removeEventListener("resize", place);
  });
  return { props, emit, menu, position, place, outside, other, keyboard };
});

// gravewright/maps/frontend/features/cards/ui/SceneCardWorkspace.native.js
var SceneCardWorkspace_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "scene-cards" }, "bind": {}, "events": [{ "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "card.id", "transform": "`translate(${card.x} ${card.y}) rotate(${card.rotation}) scale(${card.scale || 1})`" }, "events": [], "children": [{ "tag": "rect", "attrs": { "class": "scene-cards__hit", "x": "-28", "y": "-40", "width": "56", "height": "80", "rx": "5", "fill": "transparent", "role": "button" }, "bind": { "class": '({ "scene-cards__hit--enabled": tool === "select" && card.can_manage })', "stroke": 'selected === card.id ? "#ffe29a" : "none"', "stroke-width": "2 / (viewport.scale * (card.scale || 1))", "tabindex": 'tool === "select" && card.can_manage ? 0 : -1', "aria-label": 'card.card?.face_state === "face_up" ? card.card?.name || gwText("Card on the table") : gwText("Face-down card")', "aria-pressed": "selected === card.id" }, "events": [{ "event": "pointerdown", "code": "down($event, card);", "mods": [] }, { "event": "contextmenu", "code": "context($event, card);", "mods": [] }, { "event": "wheel", "code": "wheel($event, card);", "mods": [] }, { "event": "keydown", "code": "selected = card.id;", "mods": ["enter", "stop"] }], "children": [] }], "each": { "names": ["card"], "value": "rows" } }] }] }, { "tag": "p", "attrs": { "class": "scene-cards__hint" }, "bind": { "role": 'error ? "alert" : "status"' }, "events": [], "children": [{ "value": 'error || (busy ? gwText("Saving card\\u2026") : gwText("Drag to move \\xB7 Shift + wheel to rotate \\xB7 F to flip \\xB7 Delete to discard"))' }], "when": "error || busy || selected" }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "menu.x", "y": "menu.y", "label": 'gwText("Card on the table")' }, "events": [{ "event": "close", "code": "menu = void 0;", "mods": [] }], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "flip;", "mods": [] }], "children": [{ "tag": "PhArrowsClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'current.card?.face_state === "face_up" ? gwText("Flip face down") : gwText("Flip face up")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "rotate(-90);", "mods": [] }], "children": [{ "tag": "PhArrowCounterClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Rotate 90\\xB0 left")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "rotate(90);", "mods": [] }], "children": [{ "tag": "PhArrowClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Rotate 90\\xB0 right")' }] }, { "tag": "button", "attrs": { "class": "gw-folder-menu__danger" }, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Remove from table (discard)")' }] }], "when": "menu && current" }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhArrowsClockwise = "PhArrowsClockwise";
  const PhArrowClockwise = "PhArrowClockwise";
  const PhArrowCounterClockwise = "PhArrowCounterClockwise";
  const PhTrash = "PhTrash";
  const BlockStateApi = class {
    command(c, b, area, action, data) {
      return options2.command(area, action, data);
    }
    state() {
      return options2.read();
    }
  };
  const HttpClient = options2.HttpClient;
  const props = options2.props;
  const emit = options2.emit;
  const root2 = ref(), selected = ref(""), preview = ref(), busy = ref(false), error = ref(""), menu = ref();
  const abort = new AbortController(), api = new BlockStateApi(new HttpClient(void 0, () => abort.signal));
  const rows = computed(() => [...props.cards].sort((a, b) => (a.z_index ?? 0) - (b.z_index ?? 0)).map((c) => preview.value?.id === c.id ? preview.value : c));
  const current = computed(() => rows.value.find((c) => c.id === selected.value));
  let drag, rotationTimer;
  function show(card) {
    preview.value = card;
    emit("preview", card);
  }
  function point(e) {
    const b = root2.value.getBoundingClientRect();
    return { x: (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - b.top - props.viewport.y) / props.viewport.scale };
  }
  function release() {
    if (drag && root2.value?.hasPointerCapture(drag.pointer)) root2.value.releasePointerCapture(drag.pointer);
    drag = void 0;
  }
  function cancel() {
    release();
    clearTimeout(rotationTimer);
    rotationTimer = void 0;
    show();
    menu.value = void 0;
  }
  function down(e, card) {
    if (e.button !== 0 || props.tool !== "select" || busy.value || !card.can_manage) return;
    e.preventDefault();
    e.stopPropagation();
    clearTimeout(rotationTimer);
    rotationTimer = void 0;
    selected.value = card.id;
    menu.value = void 0;
    error.value = "";
    drag = { pointer: e.pointerId, point: point(e), card: { ...card } };
    root2.value?.setPointerCapture(e.pointerId);
  }
  function move(e) {
    if (!drag || e.pointerId !== drag.pointer) return;
    e.stopPropagation();
    const p = point(e);
    show({ ...drag.card, x: drag.card.x + p.x - drag.point.x, y: drag.card.y + p.y - drag.point.y });
  }
  async function command2(action, data) {
    if (busy.value || !current.value?.can_manage) return;
    busy.value = true;
    menu.value = void 0;
    error.value = "";
    try {
      await api.command(props.containerId, props.blockId, "cards", action, { placement_id: selected.value, ...data });
      if (!abort.signal.aborted) emit("refresh");
    } catch {
      if (!abort.signal.aborted) {
        show();
        error.value = text("Could not change the card. Refreshing the scene\u2026");
        emit("refresh");
      }
    } finally {
      if (!abort.signal.aborted) busy.value = false;
    }
  }
  function up(e) {
    if (!drag || drag.pointer !== e.pointerId) return;
    move(e);
    e.stopPropagation();
    const original = drag.card, next = preview.value;
    release();
    if (next && (next.x !== original.x || next.y !== original.y)) void command2("update", { x: next.x, y: next.y, rotation: next.rotation });
    else show();
  }
  function context(e, card) {
    if (props.tool !== "select" || !card.can_manage) return;
    e.preventDefault();
    e.stopPropagation();
    cancel();
    selected.value = card.id;
    menu.value = { x: e.clientX, y: e.clientY };
  }
  function rotate2(degrees, defer = false) {
    if (busy.value || drag || !current.value?.can_manage) return;
    const c = { ...current.value, rotation: ((current.value.rotation + degrees) % 360 + 360) % 360 };
    show(c);
    clearTimeout(rotationTimer);
    const save = () => {
      rotationTimer = void 0;
      void command2("update", { rotation: c.rotation });
    };
    if (defer) rotationTimer = setTimeout(save, 180);
    else save();
  }
  function wheel(e, card) {
    if (props.tool !== "select" || !e.shiftKey || !card.can_manage) return;
    e.preventDefault();
    e.stopPropagation();
    if (selected.value !== card.id) {
      cancel();
      selected.value = card.id;
    }
    rotate2(e.deltaY > 0 ? 15 : -15, true);
  }
  function flip() {
    cancel();
    void command2("update", { face_state: current.value?.card?.face_state === "face_up" ? "face_down" : "face_up" });
  }
  function remove() {
    cancel();
    void command2("delete", {});
  }
  function outside(e) {
    if (e.target instanceof Element && (e.target.closest(".scene-cards__hit") || menu.value && e.target.closest(".directory-context-menu"))) return;
    if (!drag) {
      cancel();
      selected.value = "";
    }
  }
  function key(e) {
    if (props.tool !== "select" || !selected.value || e.target instanceof Element && e.target.closest("input,textarea,select,[contenteditable=true]")) return;
    if (e.key === "Escape") {
      e.stopImmediatePropagation();
      cancel();
      selected.value = "";
    } else if (["Delete", "Backspace", "f", "F"].includes(e.key)) {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (!busy.value) {
        if (e.key.toLowerCase() === "f") flip();
        else remove();
      }
    }
  }
  watch(() => props.cards, (cards) => {
    if (drag && !cards.some((c) => c.id === drag.card.id && c.x === drag.card.x && c.y === drag.card.y && c.rotation === drag.card.rotation)) cancel();
    if (!drag && !rotationTimer) show();
    if (!cards.some((c) => c.id === selected.value && c.can_manage)) selected.value = "";
  });
  watch(() => props.tool, () => {
    cancel();
    selected.value = "";
  });
  onMounted(() => {
    document.addEventListener("pointerdown", outside, true);
    window.addEventListener("keydown", key, true);
    window.addEventListener("blur", cancel);
  });
  onBeforeUnmount(() => {
    document.removeEventListener("pointerdown", outside, true);
    abort.abort();
    cancel();
    window.removeEventListener("keydown", key, true);
    window.removeEventListener("blur", cancel);
  });
  return { gwText: text, PhArrowsClockwise, PhArrowClockwise, PhArrowCounterClockwise, PhTrash, BlockStateApi, HttpClient, DirectoryContextMenu: DirectoryContextMenu_native_default, props, emit, root: root2, selected, preview, busy, error, menu, abort, api, rows, current, drag, rotationTimer, show, point, release, cancel, down, move, command: command2, up, context, rotate: rotate2, wheel, flip, remove, outside, key };
});

// gravewright/maps/frontend/features/audio/ui/SoundtrackPanel.native.js
var SoundtrackPanel_native_default = widget([{ "tag": "section", "attrs": { "class": "soundtrack-panel" }, "bind": {}, "events": [], "children": [{ "tag": "header", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Soundtracks and ambience")' }] }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": 'create("playlist");', "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "text": "Playlist" }] }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": 'create("preset");', "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "text": "Preset" }] }] }, { "tag": "p", "attrs": { "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "form", "attrs": {}, "bind": {}, "events": [{ "event": "submit", "code": "save;", "mods": ["prevent"] }], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Name")' }, { "tag": "input", "attrs": { "required": "", "maxlength": "80" }, "bind": {}, "events": [], "children": [], "model": { "path": "name", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "soundtrack-panel__row" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "key": "label" }, "events": [{ "event": "click", "code": "name = label;", "mods": [] }], "children": [{ "value": "label" }], "each": { "names": ["label"], "value": '[gwText("Exploration"), gwText("Tavern"), gwText("Combat")]' } }], "when": 'kind === "preset"' }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Order")' }, { "tag": "select", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "option", "attrs": { "value": "sequential" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Sequential")' }] }, { "tag": "option", "attrs": { "value": "shuffle" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Random")' }] }], "model": { "path": "mode", "mods": [] } }], "when": 'kind === "playlist"' }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Transition (seconds)")' }, { "tag": "input", "attrs": { "type": "number", "min": "0", "max": "30", "step": "0.5", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "fade", "mods": ["number"] } }] }, { "tag": "div", "attrs": { "class": "soundtrack-panel__row" }, "bind": {}, "events": [], "children": [{ "tag": "select", "attrs": {}, "bind": { "aria-label": 'gwText("Add track")' }, "events": [], "children": [{ "tag": "option", "attrs": { "value": "" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Choose a sound")' }] }, { "tag": "option", "attrs": {}, "bind": { "key": "s.id", "value": "s.id" }, "events": [], "children": [{ "value": "s.name" }], "each": { "names": ["s"], "value": "sounds" } }], "model": { "path": "chosen", "mods": [] } }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy || !chosen || entries.length >= 64" }, "events": [{ "event": "click", "code": "add;", "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "ol", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "li", "attrs": {}, "bind": { "key": "index" }, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "sounds.find((s) => s.id === entry.soundId)?.name" }, { "text": " " }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "time(entry.duration)" }] }, { "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": "0.01" }, "bind": { "aria-label": 'gwText("Layer volume")' }, "events": [], "children": [], "model": { "path": "entry.gain", "mods": ["number"] } }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "index === 0", "aria-label": 'gwText("Move track up")' }, "events": [{ "event": "click", "code": "entries.splice(index - 1, 0, entries.splice(index, 1)[0]);", "mods": [] }], "children": [{ "tag": "PhArrowUp", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "index === entries.length - 1", "aria-label": 'gwText("Move track down")' }, "events": [{ "event": "click", "code": "entries.splice(index + 1, 0, entries.splice(index, 1)[0]);", "mods": [] }], "children": [{ "tag": "PhArrowDown", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "aria-label": 'gwText("Remove track")' }, "events": [{ "event": "click", "code": "entries.splice(index, 1);", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "each": { "names": ["entry", "index"], "value": "entries" } }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'kind === "preset" ? gwText("Layers play together and loop.") : gwText("Tracks advance automatically with crossfades.")' }] }, { "tag": "div", "attrs": { "class": "soundtrack-panel__row" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "submit" }, "bind": { "disabled": "busy || !entries.length" }, "events": [], "children": [{ "value": 'gwText("Save")' }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "editing = false;", "mods": [] }], "children": [{ "value": 'gwText("Cancel")' }] }] }], "when": "editing" }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "soundtrack-panel__repeat" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "repeat", "mods": [] } }, { "value": 'gwText("Loop playlist")' }] }, { "tag": "article", "attrs": {}, "bind": { "key": "item.id" }, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "item.name" }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'item.kind === "preset" ? gwText("Ambience") : item.playback_mode === "shuffle" ? gwText("Shuffled playlist") : gwText("Sequential playlist")' }] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Play composition")' }, "events": [{ "event": "click", "code": 'command("start", { id: item.id, kind: item.kind, repeat });', "mods": [] }], "children": [{ "tag": "PhPlay", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "each": { "names": ["item"], "value": '[...lists.playlists.map((x) => ({ ...x, kind: "playlist" })), ...lists.presets.map((x) => ({ ...x, kind: "preset" }))]' } }], "otherwise": true }, { "tag": "div", "attrs": { "class": "soundtrack-panel__transport" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "state.name" }] }, { "tag": "span", "attrs": {}, "bind": { "key": "track.id" }, "events": [], "children": [{ "value": "track.name" }, { "text": " \xB7 " }, { "value": "time(track.position ?? Date.now() / 1e3 - track.startedAt)" }, { "text": " / " }, { "value": "time(track.duration)" }], "each": { "names": ["track"], "value": "state.playbacks.filter((t) => t.startedAt <= Date.now() / 1e3 && !t.fade)" } }, { "tag": "div", "attrs": { "class": "soundtrack-panel__row" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "aria-label": 'gwText("Previous track")', "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("previous");', "mods": [] }], "children": [{ "tag": "PhSkipBack", "attrs": {}, "bind": {}, "events": [], "children": [] }], "when": 'state.kind === "playlist"' }, { "tag": "button", "attrs": {}, "bind": { "aria-label": 'state.state === "paused" ? gwText("Resume") : gwText("Pause")', "disabled": "busy" }, "events": [{ "event": "click", "code": 'command(state.state === "paused" ? "resume" : "pause");', "mods": [] }], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": 'state.state === "paused" ? PhPlay : PhPause' }, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": 'gwText("Stop composition")', "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("stop");', "mods": [] }], "children": [{ "tag": "PhStop", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": 'gwText("Next track")', "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("next");', "mods": [] }], "children": [{ "tag": "PhSkipForward", "attrs": {}, "bind": {}, "events": [], "children": [] }], "when": 'state.kind === "playlist"' }] }], "when": 'state.state !== "stopped"' }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhPlay = "PhPlay";
  const PhPause = "PhPause";
  const PhStop = "PhStop";
  const PhSkipForward = "PhSkipForward";
  const PhSkipBack = "PhSkipBack";
  const PhPlus = "PhPlus";
  const PhTrash = "PhTrash";
  const PhArrowUp = "PhArrowUp";
  const PhArrowDown = "PhArrowDown";
  const HttpClient = options2.HttpClient;
  const props = options2.props;
  const emit = options2.emit;
  const scope = new AbortController(), http = new HttpClient(void 0, () => scope.signal), base2 = `/api/containers/${props.containerId}`;
  const lists = ref({ playlists: [], presets: [] }), state = ref({ state: "stopped", version: 0, playbacks: [] });
  const editing = ref(false), kind = ref("playlist"), name = ref(""), mode = ref("sequential"), fade = ref(2), repeat = ref(true), chosen = ref(""), busy = ref(false), error = ref("");
  const entries = ref([]);
  let timer;
  const probes = /* @__PURE__ */ new Set();
  const time = (seconds) => `${Math.floor(Math.max(0, seconds) / 60)}:${String(Math.floor(Math.max(0, seconds) % 60)).padStart(2, "0")}`;
  async function refresh2() {
    try {
      state.value = await http.get(base2 + `/blocks/${props.blockId}/soundtrack`);
    } catch {
      if (!scope.signal.aborted) error.value = text("Could not update playback.");
    }
  }
  async function definitions() {
    lists.value = await http.get(base2 + "/soundtracks");
  }
  async function add() {
    if (!chosen.value || busy.value) return;
    const sound = props.sounds.find((s) => s.id === chosen.value), asset = props.assets.find((a) => a.id === sound?.asset_id);
    if (!sound || !asset) return;
    busy.value = true;
    error.value = "";
    const audio = new Audio();
    probes.add(audio);
    try {
      const duration = await new Promise((resolve2, reject) => {
        const timeout = setTimeout(() => finish(new Error(text("Could not read the file duration."))), 8e3);
        const finish = (error2) => {
          clearTimeout(timeout);
          scope.signal.removeEventListener("abort", cancel);
          audio.onloadedmetadata = null;
          audio.onerror = null;
          error2 ? reject(error2) : resolve2(audio.duration);
        };
        const cancel = () => finish(new Error("cancelled"));
        scope.signal.addEventListener("abort", cancel, { once: true });
        audio.onloadedmetadata = () => Number.isFinite(audio.duration) && audio.duration >= 1 ? finish() : finish(new Error(text("Invalid duration.")));
        audio.onerror = () => finish(new Error(text("Could not open the audio.")));
        audio.preload = "metadata";
        audio.src = asset.src;
      });
      if (!scope.signal.aborted) entries.value.push({ soundId: sound.id, duration, gain: 1 });
    } catch (e) {
      if (!scope.signal.aborted) error.value = e.message;
    } finally {
      audio.removeAttribute("src");
      audio.load();
      probes.delete(audio);
      busy.value = false;
    }
  }
  async function save() {
    busy.value = true;
    error.value = "";
    try {
      await http.post(base2 + "/soundtracks", { kind: kind.value, name: name.value, mode: mode.value, fade: fade.value, entries: entries.value });
      await definitions();
      editing.value = false;
    } catch {
      error.value = text("Could not save the composition.");
    } finally {
      busy.value = false;
    }
  }
  async function command2(action, data = {}) {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      state.value = await http.post(base2 + `/blocks/${props.blockId}/soundtrack/${action}`, { ...data, expectedVersion: state.value.version });
      emit("refresh");
    } catch {
      if (!scope.signal.aborted) {
        error.value = text("Playback changed or the action was refused. Try again.");
        await refresh2();
      }
    } finally {
      busy.value = false;
    }
  }
  function create(type, label = "") {
    kind.value = type;
    name.value = label;
    entries.value = [];
    editing.value = true;
  }
  onMounted(() => {
    void definitions().catch(() => error.value = text("Could not load compositions."));
    void refresh2();
    timer = setInterval(() => {
      if (!busy.value) void refresh2();
    }, 1e3);
  });
  onBeforeUnmount(() => {
    scope.abort();
    clearInterval(timer);
    for (const audio of probes) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    }
  });
  return { gwText: text, PhPlay, PhPause, PhStop, PhSkipForward, PhSkipBack, PhPlus, PhTrash, PhArrowUp, PhArrowDown, HttpClient, props, emit, scope, http, base: base2, lists, state, editing, kind, name, mode, fade, repeat, chosen, busy, error, entries, timer, probes, time, refresh: refresh2, definitions, add, save, command: command2, create };
});

// gravewright/maps/frontend/features/selection/model/objects.js
function rotate(p, c, degrees) {
  const a = degrees * Math.PI / 180, dx = p.x - c.x, dy = p.y - c.y;
  return { x: c.x + dx * Math.cos(a) - dy * Math.sin(a), y: c.y + dx * Math.sin(a) + dy * Math.cos(a) };
}
function transformedPoint(p, center, dx, dy, rotation) {
  const q = rotate(p, center, rotation);
  return { x: q.x + dx, y: q.y + dy };
}

// gravewright/maps/frontend/features/audio/ui/AudioWorkspace.native.js
var AudioWorkspace_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "audio-workspace" }, "bind": { "class": '({ "audio-workspace--placing": placing })' }, "events": [{ "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerdown", "code": "place;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "source.id", "transform": "sourceTransform(source)" }, "events": [], "children": [{ "tag": "circle", "attrs": { "fill": "#65c9b808", "stroke": "#65c9b8" }, "bind": { "cx": "source.x", "cy": "source.y", "r": "source.radius", "stroke-opacity": "0.35", "stroke-width": "1 / viewport.scale" }, "events": [], "children": [] }, { "tag": "circle", "attrs": { "class": "audio-workspace__source" }, "bind": { "cx": "source.x", "cy": "source.y", "r": "9 / viewport.scale", "fill": 'source.enabled ? "#65c9b8" : "#777"' }, "events": [{ "event": "dblclick", "code": "edit(source.id);", "mods": ["stop"] }], "children": [] }, { "tag": "text", "attrs": { "fill": "#b1e7dc" }, "bind": { "x": "source.x + 13 / viewport.scale", "y": "source.y", "font-size": "11 / viewport.scale" }, "events": [], "children": [{ "value": 'library.sounds.find((s) => s.id === source.sound_id)?.name || gwText("Audio source")' }] }], "each": { "names": ["source"], "value": "state.spatialSounds" } }, { "tag": "circle", "attrs": { "fill": "#65c9b822", "stroke": "#65c9b8" }, "bind": { "cx": "position.x", "cy": "position.y", "r": "radius * toPixels", "stroke-width": "2 / viewport.scale" }, "events": [], "children": [], "when": "placing && position" }] }], "when": "viewport && !embedded" }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": { "disabled": "embedded" }, "events": [], "children": [{ "tag": "section", "attrs": { "class": "audio-panel" }, "bind": { "class": '({ "audio-panel--embedded": embedded })', "aria-label": 'gwText("Scene audio")' }, "events": [], "children": [{ "tag": "header", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhWaveform", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'editor ? gwText("Edit source") : gwText("Scene audio")' }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": 'gwText("Close audio")' }, "events": [{ "event": "click", "code": "close;", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }], "when": "!embedded" }] }, { "tag": "p", "attrs": { "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": 'emit("unlock");', "mods": [] }], "children": [{ "tag": "PhSpeakerHigh", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": `gwText("Play this scene's audio")` }] }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "form", "attrs": { "class": "audio-panel__editor" }, "bind": {}, "events": [{ "event": "submit", "code": "save;", "mods": ["prevent"] }], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "library.sounds.find((s) => s.id === chosen)?.name" }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Range (")' }, { "value": "unit" }, { "text": ")" }, { "tag": "input", "attrs": { "type": "number", "min": "0.01", "max": "100000", "step": "any", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "radius", "mods": ["number"] } }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "text": "Volume " }, { "value": "Math.round(gain * 100)" }, { "text": "%" }, { "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": "0.01" }, "bind": {}, "events": [], "children": [], "model": { "path": "gain", "mods": ["number"] } }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Volume falloff")' }, { "tag": "select", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "option", "attrs": { "value": "smooth" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Smooth")' }] }, { "tag": "option", "attrs": { "value": "linear" }, "bind": {}, "events": [], "children": [{ "text": "Linear" }] }], "model": { "path": "falloff", "mods": [] } }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "loop", "mods": [] } }, { "value": 'gwText("Loop")' }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "walls", "mods": [] } }, { "value": 'gwText("Respect walls")' }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "enabled", "mods": [] } }, { "value": 'gwText("Active")' }] }, { "tag": "button", "attrs": { "type": "submit" }, "bind": { "disabled": "busy" }, "events": [], "children": [{ "value": 'gwText("Save source")' }], "when": "editor" }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Click the map to place the source. Esc cancels.")' }], "otherwise": true }], "when": "editor || placing" }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": {}, "bind": { "aria-label": 'gwText("Search audio")', "placeholder": 'gwText("Search the table library")' }, "events": [], "children": [], "model": { "path": "query", "mods": [] } }, { "tag": "div", "attrs": { "class": "audio-panel__list" }, "bind": {}, "events": [], "children": [{ "tag": "article", "attrs": {}, "bind": { "key": "sound.id" }, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "sound.name" }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'sound.kind === "music" ? gwText("Music") : sound.kind === "ambience" ? gwText("Ambience") : gwText("Effect")' }] }] }, { "tag": "div", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "title": 'gwText("Local preview")', "aria-label": 'gwText("Local preview")' }, "events": [{ "event": "click", "code": "listen(sound);", "mods": [] }], "children": [{ "tag": "PhSpeakerHigh", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("audio", "play", { sound_id: sound.id });', "mods": [] }], "children": [{ "tag": "PhPlay", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Scene")' }], "when": 'sound.kind !== "sound-effect"' }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "select(sound);", "mods": [] }], "children": [{ "value": 'gwText("Place")' }], "when": "viewport" }] }], "each": { "names": ["sound"], "value": "sounds" } }] }, { "tag": "details", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "summary", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Add library file")' }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Category")' }, { "tag": "select", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "option", "attrs": { "value": "music" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Music")' }] }, { "tag": "option", "attrs": { "value": "ambience" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Ambience")' }] }, { "tag": "option", "attrs": { "value": "sound-effect" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Effect")' }] }], "model": { "path": "category", "mods": [] } }] }, { "tag": "article", "attrs": {}, "bind": { "key": "asset.id" }, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "asset.name || asset.filename" }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "register(asset);", "mods": [] }], "children": [{ "value": 'gwText("Add")' }] }], "each": { "names": ["asset"], "value": 'library.assets.filter((a) => a.content_type.startsWith("audio/"))' } }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Upload files through Library at the top.")' }] }] }], "otherwise": true }, { "tag": "SoundtrackPanel", "attrs": {}, "bind": { "key": "blockId", "container-id": "containerId", "block-id": "blockId", "sounds": "library.sounds", "assets": "library.assets" }, "events": [{ "event": "refresh", "code": 'emit("refresh");', "mods": [] }], "children": [] }, { "tag": "h4", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Playback in this scene")' }] }, { "tag": "article", "attrs": {}, "bind": { "key": "playback.id" }, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "library.sounds.find((s) => s.asset_id === playback.asset.id)?.name || playback.channel" }, { "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": "0.01" }, "bind": { "aria-label": 'gwText("Track volume")', "value": "playback.baseGain ?? playback.gain", "disabled": "busy" }, "events": [{ "event": "change", "code": 'command("playbacks", "update", { playback_id: playback.id, expected_version: playback.version, patch: { gain: Number($event.target.value) } });', "mods": [] }], "children": [] }] }, { "tag": "div", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Play")' }, "events": [{ "event": "click", "code": 'command("playbacks", "update", { playback_id: playback.id, expected_version: playback.version, patch: { state: "playing" } });', "mods": [] }], "children": [{ "tag": "PhPlay", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Pause")' }, "events": [{ "event": "click", "code": 'command("playbacks", "update", { playback_id: playback.id, expected_version: playback.version, patch: { state: "paused" } });', "mods": [] }], "children": [{ "tag": "PhPause", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Stop")' }, "events": [{ "event": "click", "code": 'command("playbacks", "stop", { playback_id: playback.id, expected_version: playback.version });', "mods": [] }], "children": [{ "tag": "PhStop", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }], "each": { "names": ["playback"], "value": 'state.audio.filter((a) => a.state !== "stopped")' } }, { "tag": "h4", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Spatial sources")' }] }, { "tag": "article", "attrs": {}, "bind": { "key": "source.id" }, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "edit(source.id);", "mods": [] }], "children": [{ "value": 'library.sounds.find((s) => s.id === source.sound_id)?.name || gwText("Source")' }, { "text": " \xB7 " }, { "value": 'source.enabled ? gwText("active") : gwText("off")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": 'command("spatial-sounds", "update", { rid: source.id, expected_version: source.version, patch: { enabled: !source.enabled } });', "mods": [] }], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "source.enabled ? PhPause : PhPlay" }, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Delete source")' }, "events": [{ "event": "click", "code": 'command("spatial-sounds", "delete", { rid: source.id, expected_version: source.version });', "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "each": { "names": ["source"], "value": "state.spatialSounds" } }], "when": "gm" }, { "tag": "p", "attrs": { "class": "audio-panel__hint" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Table library \\xB7 Playback and sources for this scene. Spatial audio uses controlled tokens as listeners.")' }] }], "when": "panel" }] }], (options2, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const PhWaveform = "PhWaveform";
  const PhPlay = "PhPlay";
  const PhPause = "PhPause";
  const PhStop = "PhStop";
  const PhX = "PhX";
  const PhSpeakerHigh = "PhSpeakerHigh";
  const PhTrash = "PhTrash";
  const HttpClient = options2.HttpClient;
  const BlockStateApi = class {
    command(c, b, area, action, data) {
      return options2.command(area, action, data);
    }
    state() {
      return options2.read();
    }
  };
  const props = options2.props;
  const emit = options2.emit;
  const abort = new AbortController(), http = new HttpClient(void 0, () => abort.signal), api = new BlockStateApi(http), root2 = ref();
  const library = ref({ sounds: [], assets: [] }), query = ref(""), busy = ref(false), error = ref(""), editor = ref(""), chosen = ref(""), placing = ref(false), position = ref();
  const radius = ref(25), gain = ref(0.7), loop = ref(true), walls = ref(true), enabled = ref(true), falloff = ref("smooth"), category = ref("ambience");
  let preview;
  function sourceTransform(source) {
    const p = props.selectionPreview;
    if (!p?.objects.some((o) => o.key === "sound:" + source.id)) return "";
    const next = transformedPoint(source, p.center, p.dx, p.dy, p.angle);
    return "translate(" + (next.x - source.x) + " " + (next.y - source.y) + ")";
  }
  const sounds = computed(() => library.value.sounds.filter((s) => s.name.toLowerCase().includes(query.value.toLowerCase())));
  const panel = computed(() => props.embedded || props.tool === "sound" || !!editor.value);
  const toPixels = computed(() => props.cell / (props.measureValue || 1));
  async function refresh2() {
    try {
      const value = await http.get(`/api/containers/${props.containerId}/library`);
      if (!abort.signal.aborted) library.value = value;
    } catch {
      if (!abort.signal.aborted) error.value = text("Could not load the audio library.");
    }
  }
  async function command2(area, action, data) {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      await api.command(props.containerId, props.blockId, area, action, data);
      if (!abort.signal.aborted) emit("refresh");
    } catch {
      if (!abort.signal.aborted) {
        error.value = text("The audio change was refused. Refreshing the scene\u2026");
        emit("refresh");
      }
    } finally {
      if (!abort.signal.aborted) busy.value = false;
    }
  }
  async function register(asset) {
    busy.value = true;
    try {
      await http.post(`/api/containers/${props.containerId}/library/sounds/create`, { name: asset.name || asset.filename, assetId: asset.id, kind: category.value, defaultGain: 0.7, defaultLoop: true });
      await refresh2();
    } catch {
      error.value = text("Could not add the audio.");
    } finally {
      busy.value = false;
    }
  }
  function select(sound) {
    stopPreview();
    editor.value = "";
    chosen.value = sound.id;
    placing.value = !!props.viewport;
    position.value = void 0;
    if (!props.viewport) error.value = text("Open the Audio layer to place a source on the map.");
  }
  function edit(id) {
    const row = props.state.spatialSounds.find((s) => s.id === id);
    if (!row) return;
    placing.value = false;
    editor.value = id;
    chosen.value = row.sound_id || "";
    radius.value = row.radius / toPixels.value;
    gain.value = row.gain ?? 0.7;
    loop.value = row.loop ?? true;
    walls.value = row.constrained_by_walls ?? true;
    enabled.value = row.enabled;
    falloff.value = row.falloff ?? "smooth";
  }
  function move(e) {
    if (!root2.value || !props.viewport) return;
    const b = root2.value.getBoundingClientRect();
    position.value = { x: (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - b.top - props.viewport.y) / props.viewport.scale };
  }
  async function place(e) {
    if (e.button !== 0 || !placing.value || busy.value) return;
    e.preventDefault();
    e.stopPropagation();
    move(e);
    await command2("spatial-sounds", "create", { soundId: chosen.value, ...position.value, radius: radius.value * toPixels.value, gain: gain.value, loop: loop.value, enabled: enabled.value, falloff: falloff.value, constrainedByWalls: walls.value, audience: { kind: "campaign" } });
    if (!error.value) {
      placing.value = false;
      emit("tool", "select");
    }
  }
  async function save() {
    const row = props.state.spatialSounds.find((s) => s.id === editor.value);
    if (!row) return;
    await command2("spatial-sounds", "update", { rid: row.id, expected_version: row.version, patch: { radius: radius.value * toPixels.value, gain: gain.value, loop: loop.value, enabled: enabled.value, falloff: falloff.value, constrainedByWalls: walls.value } });
    if (!error.value) editor.value = "";
  }
  function stopPreview() {
    if (preview) {
      preview.pause();
      preview.removeAttribute("src");
      preview.load();
      preview = void 0;
    }
  }
  async function listen(sound) {
    stopPreview();
    const asset = library.value.assets.find((a) => a.id === sound.asset_id);
    if (!asset) return;
    preview = new Audio(asset.src);
    preview.volume = 0.5;
    try {
      await preview.play();
    } catch {
      if (!abort.signal.aborted) error.value = text("Click again to listen to the preview.");
    }
  }
  function close2() {
    stopPreview();
    placing.value = false;
    editor.value = "";
    emit("tool", "select");
  }
  function key(e) {
    if (e.key === "Escape" && (placing.value || editor.value)) {
      e.stopImmediatePropagation();
      close2();
    }
  }
  watch(() => props.revision, refresh2);
  watch(() => props.tool, (tool) => {
    if (tool !== "sound") {
      placing.value = false;
      stopPreview();
    }
  });
  onMounted(() => {
    void refresh2();
    window.addEventListener("keydown", key, true);
  });
  onBeforeUnmount(() => {
    abort.abort();
    stopPreview();
    window.removeEventListener("keydown", key, true);
  });
  defineExpose({ edit });
  return { gwText: text, SoundtrackPanel: SoundtrackPanel_native_default, transformedPoint, PhWaveform, PhPlay, PhPause, PhStop, PhX, PhSpeakerHigh, PhTrash, HttpClient, BlockStateApi, props, emit, abort, http, api, root: root2, library, query, busy, error, editor, chosen, placing, position, radius, gain, loop, walls, enabled, falloff, category, preview, sourceTransform, sounds, panel, toPixels, refresh: refresh2, command: command2, register, select, edit, move, place, save, stopPreview, listen, close: close2, key };
});

// gravewright/maps/frontend/native/table-modules.js
import { getPath, mergePatch } from "/static/gravewright_web/vendor/datastar-1.0.3.js";
import { gravewright } from "/static/gravewright_modules/frontend-api.js";
import { executeNative } from "/static/gravewright_modules/domain-api.js";
var root = document.querySelector("#table-workspace");
var campaign = root?.dataset.tableId;
var states = {};
var widgets = {};
var nodes = {};
var media = /* @__PURE__ */ new Map();
var scene = null;
var revision = 0;
var muted = false;
var master = 0.7;
var unlocked = false;
var placement;
var clockOffset = 0;
var channels = { music: 1, ambience: 1, sfx: 1, cinematic: 1 };
var map = () => window.gravewrightMaps?.current;
var rt = () => window.gravewrightRealtime;
var who = () => root?.dataset.role === "gm";
var previewToken = () => who() && window.gravewrightTokenSelection?.length === 1 ? window.gravewrightTokenSelection[0] : null;
async function fresh(module) {
  const requestedScene = scene;
  const v = await gravewright[module].state({ sceneId: scene, previewTokenId: module === "audio" ? previewToken() : null });
  if (["cards", "audio"].includes(module) && requestedScene !== scene) return v;
  states[module] = v;
  if (module === "audio" && v.serverTime) clockOffset = v.serverTime - Date.now() / 1e3;
  return v;
}
async function command(module, action, data = {}) {
  return executeNative(gravewright, module, action, { sceneId: scene, ...data });
}
function cardById(id) {
  return [...states.cards?.hand || [], ...states.cards?.cards || []].find((c) => c.id === id);
}
async function cardCommand(action, data) {
  const row = cardById(data.id || data.card_id || data.placement_id);
  const deck = states.cards?.decks?.find((d) => d.id === data.deck_instance_id);
  const mapped = { ...data, id: row?.id || data.id || data.card_id || data.placement_id, version: data.expected_version ?? data.version ?? row?.version ?? deck?.version, sceneId: scene };
  if (action === "delete") action = data.deck_instance_id ? "delete-deck" : "discard";
  if (action === "play") action = "place";
  if (action === "update") {
    if (data.face_state !== void 0) action = "flip";
    else action = "move";
  }
  if (action === "draw") mapped.face_state = data.reveal === false ? "face_down" : "face_up";
  const result = await command("cards", action, mapped);
  await fresh("cards");
  revision++;
  refresh();
  return result;
}
function soundLibrary() {
  const tracks = states.audio?.tracks || [];
  return { sounds: tracks.map((t) => ({ id: t.id, name: t.name, kind: t.kind === "effect" ? "sound-effect" : t.kind, asset_id: t.id })), assets: tracks.map((t) => ({ id: t.id, name: t.name, filename: t.name, src: t.src, content_type: "audio/mpeg" })) };
}
var Client = class {
  constructor(_base, signal = () => void 0) {
    this.signal = signal;
  }
  async get(url) {
    if (url.startsWith("/game/content/")) {
      const state2 = await fresh("compendiums"), path = url.split("?")[0].split("/").map(decodeURIComponent);
      if (path[3] === "active-packages") return { packages: state2.packs.map((p) => ({ id: p.id, name: p.name })) };
      const pack = state2.packs.find((p) => p.id === path[4]);
      if (!pack) throw Error("Compendium not found.");
      if (path[3] === "packs") return { packs: [...new Set(pack.entries.map((e) => e.kind))].map((kind) => ({ id: kind, name: kind, type: kind === "item" ? "item_pack" : kind + "_pack" })) };
      return { entries: pack.entries.filter((e) => e.kind === path[5]) };
    }
    if (url.endsWith("/card-state")) return fresh("cards");
    const state = await fresh("audio");
    if (url.endsWith("/soundtracks")) return { playlists: state.playlists.filter((p) => p.kind === "playlist").map((p) => ({ ...p, entries: p.tracks })), presets: state.playlists.filter((p) => p.kind === "preset").map((p) => ({ ...p, layers: p.tracks })) };
    if (url.endsWith("/soundtrack")) return state.score;
    if (url.endsWith("/library")) return soundLibrary();
    throw Error("Unknown resource.");
  }
  async post(url, data) {
    if (url.endsWith("/content/import")) return command("compendiums", "import", { packId: data.package_id, id: data.entry_id });
    if (url.includes("/cards/")) return cardCommand(url.split("/").at(-1), data);
    if (url.endsWith("/soundtracks")) {
      const result = await command("audio", "playlist-create", { name: data.name, tracks: data.entries, kind: data.kind, mode: data.mode, fade: data.fade });
      await fresh("audio");
      return result;
    }
    if (url.includes("/soundtrack/")) {
      const result = await command("audio", "score-" + url.split("/").at(-1), data);
      await fresh("audio");
      return result;
    }
    if (url.endsWith("/sounds/create")) {
      const row = states.audio.tracks.find((t) => t.id === data.assetId);
      return command("audio", "track-update", { id: row.id, version: row.version, kind: data.kind === "sound-effect" ? "effect" : data.kind, name: data.name });
    }
    throw Error("Unknown command.");
  }
  async upload(url, body, progress) {
    const endpoint = url.endsWith("/card-upload") ? "card-asset" : "audio";
    const { token, header } = await (await fetch("/__gravewright/csrf")).json();
    const r = await fetch(`/api/containers/${campaign}/media/${endpoint}`, { method: "POST", body, signal: this.signal(), headers: { [header || "x-csrf-token"]: token } });
    const value = await r.json();
    if (!r.ok) throw Error(value.error);
    progress?.(100);
    return value;
  }
};
async function areaCommand(area, action, data = {}) {
  if (area === "cards") return cardCommand(action, data);
  if (area === "spatial-sounds") {
    const values = data.patch || data, id = data.rid || data.id, row = states.audio.spatialSounds.find((s) => s.id === id), m = map(), factor = (m?.gridSize || 70) * (m?.imageScale || 1) / (m?.measureValue || 1);
    const patch2 = { ...values, id, version: data.expected_version ?? row?.version, trackId: values.soundId || row?.trackId, occlusion: values.constrainedByWalls ?? row?.occlusion };
    if (values.radius !== void 0) patch2.radius = values.radius / factor;
    const result2 = await command("audio", "spatial-" + action, patch2);
    await fresh("audio");
    refresh();
    return result2;
  }
  if (area === "playbacks") {
    const patch2 = data.patch || {}, row = states.audio.playback.ambient.find((p) => p.trackId === data.playback_id);
    if (!row) throw Error("Playback not found.");
    action = action === "stop" ? "stop" : patch2.state === "playing" ? "play" : patch2.state === "paused" ? "pause" : "volume";
    data = { trackId: row.trackId, volume: patch2.gain, version: data.expected_version };
  }
  const trackId = data.trackId || data.soundId || data.sound_id || data.id;
  const result = await command("audio", action, { ...data, trackId, version: states.audio?.version || 0 });
  await fresh("audio");
  refresh();
  return result;
}
function options(props, emit) {
  return { props, emit, HttpClient: Client, command: areaCommand, read: () => fresh("cards") };
}
function host(name) {
  if (!nodes[name]) {
    nodes[name] = document.createElement("div");
    nodes[name].style.display = "contents";
    (["cards", "placement", "audio"].includes(name) ? document.querySelector(".game-board__surface") || document.body : document.body).append(nodes[name]);
  }
  return nodes[name];
}
function close(name) {
  widgets[name]?.destroy();
  delete widgets[name];
  nodes[name]?.remove();
  delete nodes[name];
}
function cardProjection(c) {
  return { id: c.id, x: c.x, y: c.y, rotation: c.rotation, scale: c.scale, z_index: c.z_index, width: 56, height: 80, version: c.version, card: { ...c, src: c.face_state === "face_up" ? c.frontUrl : c.backUrl }, can_manage: c.canControl, can_move: c.canControl, can_reveal: c.canControl };
}
function audioProjection() {
  const m = map(), factor = (m?.gridSize || 70) * (m?.imageScale || 1) / (m?.measureValue || 1);
  return { spatialSounds: (states.audio?.spatialSounds || []).map((s) => ({ ...s, sound_id: s.trackId, radius: s.radius * factor, constrained_by_walls: s.occlusion })), audio: (states.audio?.playback?.ambient || []).map((s) => ({ ...s, id: s.trackId, state: s.status, sound_id: s.trackId, asset: { id: s.trackId }, version: states.audio.version, gain: s.volume, baseGain: s.volume })) };
}
function base() {
  const m = map();
  return { containerId: campaign, blockId: m?.blockId, gm: who(), revision, viewport: window.gravewrightMaps?.board?.viewport(), cell: (m?.gridSize || 70) * (m?.imageScale || 1), measureValue: m?.measureValue || 1, unit: m?.measureUnit || "m", tool: getPath("_tool") };
}
function refresh() {
  const props = base();
  widgets.hand?.update(props);
  const surface = document.querySelector(".map-surface") || document.querySelector("[data-map-surface]") || window.gravewrightMaps?.board?.surface;
  if (widgets.audio) widgets.audio.update({ ...props, state: audioProjection(), tool: "sound" });
  if (widgets.cards) widgets.cards.update({ ...props, cards: (states.cards?.cards || []).map(cardProjection), active: true });
  if (widgets.placement) widgets.placement.update({ ...props, cards: placement.cards, reveal: placement.reveal });
  syncAudio();
}
function showHand() {
  if (widgets.hand) {
    close("hand");
    return;
  }
  widgets.hand = CardHand_native_default(host("hand"), options(base(), (event, cards, reveal) => {
    if (event === "place" && scene) {
      placement = { cards, reveal };
      close("placement");
      widgets.placement = CardPlacement_native_default(host("placement"), options({ ...base(), ...placement }, (type) => {
        if (type === "close") close("placement");
        if (type === "refresh") void fresh("cards").then(refresh);
      }));
    }
  }));
}
function showAudio() {
  if (!scene) return;
  if (widgets.audio) {
    close("audio");
    return;
  }
  widgets.audio = AudioWorkspace_native_default(host("audio"), options({ ...base(), state: audioProjection(), tool: "sound" }, (event, value) => {
    if (event === "unlock") {
      unlocked = true;
      syncAudio();
    } else if (event === "tool" && value === "select") close("audio");
    else if (event === "refresh") void fresh("audio").then(refresh);
  }));
}
function syncAudio() {
  const state = states.audio;
  if (!state) return;
  const now = Date.now() / 1e3 + clockOffset, desired = /* @__PURE__ */ new Map(), tracks = new Map((state.tracks || []).map((t) => [t.id, t]));
  for (const p of state.playback?.ambient || []) if (p.status !== "stopped") desired.set("ambient-" + p.trackId + "-" + (p.playId || "initial"), { trackId: p.trackId, playing: p.status === "playing", offset: p.position + (p.status === "playing" ? now - p.startedAt : 0), gain: p.volume, loop: p.loop });
  for (const s of state.spatialSounds || []) if (s.enabled) desired.set("spatial-" + s.id, { trackId: s.trackId, playing: true, offset: 0, gain: s.effectiveGain, loop: s.loop, spatial: true });
  for (const p of state.score?.playbacks || []) {
    const elapsed = now - p.startedAt;
    let gain = p.gain;
    if (p.fadeIn) gain *= Math.max(0, Math.min(1, elapsed / p.fadeIn));
    if (p.fadeOut) gain *= Math.max(0, Math.min(1, (p.duration - elapsed) / p.fadeOut));
    if (p.fade) gain *= Math.max(0, 1 - (now * 1e3 - p.fade.startedAt) / p.fade.durationMs);
    desired.set(p.id, { trackId: p.asset.id, playing: p.state === "playing" && elapsed >= 0, offset: p.position ?? Math.max(0, elapsed), gain, loop: p.loop });
  }
  for (const [id, row] of media) if (!desired.has(id) || !tracks.has(desired.get(id).trackId)) {
    row.audio.pause();
    row.audio.removeAttribute("src");
    row.audio.load();
    media.delete(id);
  }
  for (const [id, p] of desired) {
    const track = tracks.get(p.trackId);
    if (!track) continue;
    let row = media.get(id);
    if (!row) {
      row = { audio: new Audio(track.src) };
      row.audio.preload = "auto";
      media.set(id, row);
    }
    const a = row.audio;
    a.loop = p.loop;
    a.volume = Math.max(0, Math.min(1, p.gain * master * (channels[track.kind === "effect" ? "sfx" : track.kind] ?? 1)));
    a.muted = muted;
    if (!p.spatial && a.readyState && Number.isFinite(a.duration) && a.duration > 0) {
      const offset = p.loop ? p.offset % a.duration : Math.min(p.offset, a.duration);
      if (Math.abs(a.currentTime - offset) > 0.5) a.currentTime = offset;
    }
    if (unlocked && p.playing && (p.loop || !Number.isFinite(a.duration) || p.spatial && !a.ended || p.offset < a.duration)) {
      if (a.paused && !a.ended) void a.play().catch(() => {
      });
    } else a.pause();
  }
}
window.addEventListener("gravewright:resources", ({ detail }) => {
  if ((detail.module === "cards" || detail.module === "audio") && (detail.sceneId ?? null) === scene) {
    states[detail.module] = detail.state;
    if (detail.module === "audio" && detail.state.serverTime) clockOffset = detail.state.serverTime - Date.now() / 1e3;
    revision++;
    refresh();
  }
});
window.addEventListener("gravewright:connected", () => {
  for (const module of ["cards", "audio"]) rt().subscribeModule(module, scene, module === "audio" ? previewToken() : null);
});
window.addEventListener("gravewright:module-scene", () => {
  scene = map()?.id || null;
  delete states.cards;
  delete states.audio;
  for (const row of media.values()) {
    row.audio.pause();
    row.audio.removeAttribute("src");
    row.audio.load();
  }
  media.clear();
  for (const module of ["cards", "audio"]) rt()?.subscribeModule(module, scene);
  close("cards");
  close("placement");
  close("audio");
  if (scene) {
    widgets.cards = SceneCardWorkspace_native_default(host("cards"), options({ ...base(), cards: [], active: true }, (event, value) => {
      if (event === "refresh") void fresh("cards").then(refresh);
      if (event === "preview") window.gravewrightMaps?.board?.previewCard(value);
    }));
  }
  refresh();
});
window.addEventListener("gravewright:selection-edit", ({ detail: { object } }) => {
  if (object.kind === "sound") {
    if (!widgets.audio) showAudio();
    widgets.audio?.call("edit", object.id);
  }
});
window.addEventListener("gravewright:map-viewport", refresh);
window.addEventListener("gravewright:selection-preview", ({ detail }) => {
  widgets.audio?.update({ selectionPreview: detail });
});
window.addEventListener("gravewright:cards-drop", ({ detail }) => {
  void cardCommand("play", { card_id: detail.cardId, ...detail }).catch(console.error);
});
document.addEventListener("click", (e) => {
  const button = e.target.closest("button");
  if (!button) return;
  if (button.dataset.dockTool === "cards") {
    e.stopImmediatePropagation();
    showHand();
  }
  if (["sound", "sounds"].includes(button.dataset.dockTool)) {
    e.stopImmediatePropagation();
    showAudio();
  }
}, true);
window.gravewrightTableMedia = { areaCommand, showHand, showAudio, mountCompendiums: (mount) => ContentDirectory_native_default(mount, options(base(), () => {
})), mountDecks: (mount) => DeckUpload_native_default(mount, options(base(), () => {
  void fresh("cards").then(refresh);
})), upload: async (file) => {
  const body = new FormData();
  body.append("file", file);
  body.append("name", file.name);
  await new Client().upload("/audio", body);
  await fresh("audio");
  refresh();
}, setMuted(value) {
  muted = value;
  syncAudio();
}, setVolume(value) {
  master = value;
  syncAudio();
}, unlock() {
  unlocked = true;
  syncAudio();
} };
setInterval(() => {
  if (scene && unlocked) void fresh("audio").then(syncAudio).catch(() => {
  });
}, 2e3);
window.addEventListener("pagehide", () => {
  for (const row of media.values()) {
    row.audio.pause();
    row.audio.removeAttribute("src");
  }
  for (const name of Object.keys(widgets)) close(name);
});
var muteButton = document.querySelector('[data-audio-control="mute"]');
var volume = document.querySelector('[data-audio-control="volume"]');
var mixer = document.querySelector('[data-audio-control="mixer"]');
try {
  master = Number(localStorage.getItem("gravewright.audio.volume") || 1);
  muted = localStorage.getItem("gravewright.audio.muted") === "true";
  channels = { ...channels, ...JSON.parse(localStorage.getItem("gravewright.audio.channels") || "{}") };
} catch {
}
if (volume) {
  volume.value = String(master * 100);
  volume.oninput = () => {
    master = Number(volume.value) / 100;
    volume.setAttribute("aria-valuetext", Math.round(master * 100) + "%");
    try {
      localStorage.setItem("gravewright.audio.volume", String(master));
    } catch {
    }
    syncAudio();
  };
}
if (muteButton) muteButton.onclick = () => {
  if (!unlocked) {
    unlocked = true;
    muted = false;
  } else muted = !muted;
  muteButton.setAttribute("aria-pressed", String(!muted));
  muteButton.setAttribute("aria-label", muted ? "Enable audio" : "Mute audio");
  try {
    localStorage.setItem("gravewright.audio.muted", String(muted));
  } catch {
  }
  syncAudio();
};
var individual = mixer?.closest(".individual-audio");
if (individual) {
  const mount = document.createElement("div");
  mount.style.display = "contents";
  individual.replaceWith(mount);
  nodes.individual = mount;
  widgets.individual = IndividualAudioControl_native_default(mount, options({ enabled: unlocked && !muted, volume: master, channels }, (event, value) => {
    if (event === "toggle") {
      if (!unlocked) {
        unlocked = true;
        muted = false;
      } else muted = !muted;
    }
    if (event === "volume") master = value;
    if (event === "channels") channels = value;
    try {
      localStorage.setItem("gravewright.audio.volume", String(master));
      localStorage.setItem("gravewright.audio.channels", JSON.stringify(channels));
      localStorage.setItem("gravewright.audio.muted", String(muted));
    } catch {
    }
    widgets.individual?.update({ enabled: unlocked && !muted, volume: master, channels });
    syncAudio();
  }));
}
var fadeTimer = setInterval(() => {
  if (unlocked) syncAudio();
}, 100);
window.addEventListener("pagehide", () => clearInterval(fadeTimer));
window.addEventListener("gravewright:token-selection", () => {
  if (scene && who()) {
    rt()?.subscribeModule("audio", scene, previewToken());
    void fresh("audio").then(syncAudio).catch(() => {
    });
  }
});
