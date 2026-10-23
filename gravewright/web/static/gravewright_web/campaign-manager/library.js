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
function widget(markup, setup) {
  return function mount(host, initial) {
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

// gravewright/maps/frontend/shared/ui/directory/DirectoryContextMenu.native.js
var DirectoryContextMenu_native_default = widget([{ "tag": "menu", "attrs": { "ref": "menu", "class": "gw-folder-menu directory-context-menu" }, "bind": { "aria-label": "label", "style": "{ left: `${position.x}px`, top: `${position.y}px` }" }, "events": [{ "event": "click", "code": "", "mods": ["stop"] }, { "event": "contextmenu", "code": "", "mods": ["prevent", "stop"] }], "children": [{ "tag": "slot", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const props = options.props;
  const emit = options.emit;
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
function assetKinds(asset) {
  if (asset.kind !== "audio")
    return [asset.kind];
  return asset.audio_kinds?.length ? [...new Set(asset.audio_kinds.map((kind) => kind === "music" || kind === "ambience" ? "ambient" : kind === "sound-effect" ? "effect" : "audio"))] : ["audio"];
}
function bytesLabel(bytes) {
  return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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

// gravewright/maps/frontend/features/table-library/ui/AssetUploadLibrary.native.js
var PhImage = "PhImage";
var PhMusicNotes = "PhMusicNotes";
var PhWaveform = "PhWaveform";
var PhFilePdf = "PhFilePdf";
var PhFolder = "PhFolder";
var PhFolderOpen = "PhFolderOpen";
var PhFolderPlus = "PhFolderPlus";
var PhMagnifyingGlass = "PhMagnifyingGlass";
var PhTrash = "PhTrash";
var PhArrowsLeftRight = "PhArrowsLeftRight";
var AssetUploadLibrary_native_default = widget([{ "tag": "section", "attrs": { "class": "asset-library" }, "bind": { "aria-label": 'gwText("Table assets")' }, "events": [], "children": [{ "tag": "header", "attrs": { "class": "asset-library__bar" }, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "asset-library__uploads" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "asset-library__upload" }, "bind": { "key": "u.id", "class": '({ "asset-library__upload--disabled": busy })' }, "events": [], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "u.icon" }, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "u.label" }] }, { "tag": "input", "attrs": { "type": "file", "multiple": "" }, "bind": { "aria-label": 'gwText("Upload {0}", u.label)', "accept": "u.accept", "disabled": "busy" }, "events": [{ "event": "change", "code": "choose($event, u.purpose);", "mods": [] }], "children": [] }], "each": { "names": ["u"], "value": "uploads" } }], "when": "gm" }, { "tag": "label", "attrs": { "class": "asset-library__search" }, "bind": {}, "events": [], "children": [{ "tag": "PhMagnifyingGlass", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "input", "attrs": { "type": "search" }, "bind": { "placeholder": 'gwText("Search files")', "aria-label": 'gwText("Search files")' }, "events": [], "children": [], "model": { "path": "(search)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "asset-library__filters", "role": "group" }, "bind": { "aria-label": 'gwText("File type")' }, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "f.id", "aria-pressed": "kind === f.id" }, "events": [{ "event": "click", "code": "kind = f.id;", "mods": [] }], "children": [{ "value": "f.label" }, { "text": " " }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "f.count" }] }], "each": { "names": ["f"], "value": "filters" } }] }] }, { "tag": "p", "attrs": { "class": "asset-library__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "div", "attrs": { "class": "asset-library__notice", "role": "status" }, "bind": {}, "events": [], "children": [{ "value": 'notice || gwText("Saving\\u2026")' }, { "tag": "progress", "attrs": { "max": "100" }, "bind": { "value": "progress", "aria-label": 'gwText("Upload progress")' }, "events": [], "children": [], "when": 'busy && notice.startsWith(gwText("Uploading"))' }], "when": "busy || notice" }, { "tag": "div", "attrs": { "class": "asset-library__body" }, "bind": {}, "events": [], "children": [{ "tag": "aside", "attrs": { "class": "asset-library__folders" }, "bind": { "aria-label": 'gwText("Asset folders")' }, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "aria-pressed": "!folder" }, "events": [{ "event": "click", "code": 'folder = "";', "mods": [] }, { "event": "dragover", "code": "", "mods": ["prevent"] }, { "event": "drop", "code": 'drop($event, "");', "mods": ["stop", "prevent"] }], "children": [{ "tag": "PhFolderOpen", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Root")' }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "state.assets.filter((a) => !a.folder_id).length" }] }] }, { "tag": "button", "attrs": {}, "bind": { "key": "f.id", "aria-pressed": "folder === f.id" }, "events": [{ "event": "click", "code": "folder = f.id;", "mods": [] }, { "event": "dragover", "code": "", "mods": ["prevent"] }, { "event": "drop", "code": "drop($event, f.id);", "mods": ["stop", "prevent"] }], "children": [{ "tag": "PhFolder", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "f.name" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "state.assets.filter((a) => a.folder_id === f.id).length" }] }], "each": { "names": ["f"], "value": "state.folders" } }, { "tag": "form", "attrs": { "class": "asset-library__folder-create" }, "bind": {}, "events": [{ "event": "submit", "code": 'command("folder-create", { name: folderName.trim() });', "mods": ["prevent"] }], "children": [{ "tag": "input", "attrs": { "maxlength": "120", "required": "" }, "bind": { "placeholder": 'gwText("New folder")', "aria-label": 'gwText("Folder name")', "disabled": "busy" }, "events": [], "children": [], "model": { "path": "(folderName)", "mods": [] } }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy || !folderName.trim()", "aria-label": 'gwText("Create folder")' }, "events": [], "children": [{ "tag": "PhFolderPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "when": "gm" }] }, { "tag": "div", "attrs": { "class": "asset-library__grid" }, "bind": { "class": '({ "asset-library__grid--drop": dragging })' }, "events": [{ "event": "dragover", "code": "dragging = true;", "mods": ["prevent"] }, { "event": "dragleave", "code": "dragging = false;", "mods": ["self"] }, { "event": "drop", "code": "drop($event);", "mods": ["prevent"] }], "children": [{ "tag": "article", "attrs": { "class": "asset-library__card" }, "bind": { "key": "asset.id", "draggable": "gm && !busy", "title": "asset.filename" }, "events": [{ "event": "dragstart", "code": "dragAsset($event, asset);", "mods": [] }, { "event": "contextmenu", "code": "openContext($event, asset);", "mods": [] }], "children": [{ "tag": "div", "attrs": { "class": "asset-library__thumb" }, "bind": {}, "events": [], "children": [{ "tag": "img", "attrs": { "alt": "", "loading": "lazy", "draggable": "false" }, "bind": { "src": "asset.src" }, "events": [], "children": [], "when": 'asset.kind === "image"' }, { "tag": "PhFilePdf", "attrs": {}, "bind": {}, "events": [], "children": [], "otherwiseWhen": 'asset.kind === "pdf"' }, { "tag": "PhWaveform", "attrs": {}, "bind": {}, "events": [], "children": [], "otherwise": true }] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "asset.filename" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'asset.kind === "image" ? `${asset.width} \\xD7 ${asset.height}` : bytesLabel(asset.byte_size)' }] }, { "tag": "div", "attrs": { "class": "asset-library__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Move file")' }, "events": [{ "event": "click", "code": 'moving = asset;\ntarget = asset.folder_id || "";', "mods": [] }], "children": [{ "tag": "PhArrowsLeftRight", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Delete file")' }, "events": [{ "event": "click", "code": "removing = asset;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "when": "gm" }], "each": { "names": ["asset"], "value": "visible" } }, { "tag": "p", "attrs": { "class": "asset-library__empty" }, "bind": {}, "events": [], "children": [{ "value": 'search ? gwText("No files found.") : gm ? gwText("This folder is empty. Upload or drop files here.") : gwText("This folder is empty.")' }], "when": "!visible.length" }] }] }, { "tag": "footer", "attrs": { "class": "asset-library__foot" }, "bind": {}, "events": [], "children": [{ "value": "visible.length" }, { "text": "/" }, { "value": "state.assets.length" }, { "text": " \xB7 " }, { "value": "bytesLabel(visibleBytes)" }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Images: 10 MB \\xB7 Audio: 100 MB \\xB7 PDF: 25 MB")' }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "context.x", "y": "context.y", "label": 'gwText("File actions")' }, "events": [{ "event": "close", "code": "context = void 0;", "mods": [] }], "children": [{ "tag": "li", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": 'moving = context.asset;\ntarget = moving.folder_id || "";\ncontext = void 0;', "mods": [] }], "children": [{ "tag": "PhArrowsLeftRight", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Move to folder")' }] }] }, { "tag": "li", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "class": "is-danger" }, "bind": {}, "events": [{ "event": "click", "code": "removing = context.asset;\ncontext = void 0;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Delete file")' }] }] }], "when": "context" }] }, { "tag": "form", "attrs": { "class": "asset-library__dialog", "role": "dialog" }, "bind": { "aria-label": 'moving ? gwText("Move file") : gwText("Delete file")' }, "events": [{ "event": "submit", "code": 'moving ? command("move", { asset_id: moving.id, folder_id: target || null }) : command("delete", { asset_id: removing.id });', "mods": ["prevent"] }], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'moving ? gwText("Move") : gwText("Delete")' }, { "text": " " }, { "value": "(moving || removing)?.filename" }] }, { "tag": "select", "attrs": {}, "bind": { "aria-label": 'gwText("Destination folder")' }, "events": [], "children": [{ "tag": "option", "attrs": { "value": "" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Root")' }] }, { "tag": "option", "attrs": {}, "bind": { "key": "f.id", "value": "f.id" }, "events": [], "children": [{ "value": "f.name" }], "each": { "names": ["f"], "value": "state.folders" } }], "when": "moving", "model": { "path": "(target)", "mods": [] } }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Delete this file from the library?")' }], "otherwise": true }, { "tag": "footer", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "moving = void 0;\nremoving = void 0;", "mods": [] }], "children": [{ "value": 'gwText("Cancel")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [], "children": [{ "value": 'moving ? gwText("Move") : gwText("Delete")' }] }] }], "when": "moving || removing" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
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
  const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal), root = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
  const state = ref({ assets: [], folders: [] }), folder = ref(""), kind = ref(""), search = ref(""), folderName = ref(""), busy = ref(false), error = ref(""), notice = ref(""), progress = ref(0), dragging = ref(false);
  const context = ref(), removing = ref(), moving = ref(), target = ref("");
  const uploads = [{ id: "image", get label() {
    return text("Images");
  }, icon: PhImage, accept: IMAGE_ACCEPT, purpose: "" }, { id: "ambient", get label() {
    return text("Ambient audio");
  }, icon: PhMusicNotes, accept: AUDIO_ACCEPT, purpose: "ambient" }, { id: "effect", get label() {
    return text("Sound effect");
  }, icon: PhWaveform, accept: AUDIO_ACCEPT, purpose: "effect" }, { id: "pdf", label: "PDFs", icon: PhFilePdf, accept: "application/pdf", purpose: "pdf-sheet" }];
  const filters = computed(() => [{ id: "", get label() {
    return text("All");
  } }, ...uploads.map((u) => ({ id: u.id, label: u.label })), { id: "audio", get label() {
    return text("Audio");
  } }].map((f) => ({ ...f, count: state.value.assets.filter((a) => !f.id || assetKinds(a).includes(f.id)).length })).filter((f) => !f.id || f.count));
  const visible = computed(() => state.value.assets.filter((a) => (a.folder_id || "") === folder.value && (!kind.value || assetKinds(a).includes(kind.value)) && a.filename.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())));
  const visibleBytes = computed(() => visible.value.reduce((sum, a) => sum + a.byte_size, 0));
  let refreshId = 0;
  async function refresh() {
    const id = ++refreshId;
    try {
      const result = await http.get(root + "/asset-state");
      if (!scope.closed && id === refreshId) {
        state.value = result;
        if (kind.value && !result.assets.some((a) => assetKinds(a).includes(kind.value)))
          kind.value = "";
        if (folder.value && !result.folders.some((f) => f.id === folder.value))
          folder.value = "";
      }
    } catch (e) {
      if (!scope.closed)
        error.value = uploadError(e);
    }
  }
  async function command(action, data) {
    if (busy.value)
      return;
    busy.value = true;
    error.value = "";
    try {
      await http.post(root + "/assets/" + action, data);
      if (!scope.closed) {
        removing.value = void 0;
        moving.value = void 0;
        folderName.value = "";
        await refresh();
      }
    } catch (e) {
      if (!scope.closed)
        error.value = uploadError(e);
    } finally {
      if (!scope.closed)
        busy.value = false;
    }
  }
  async function upload(files, purpose = "", destination = folder.value) {
    if (!props.gm || busy.value || !files.length)
      return;
    busy.value = true;
    error.value = "";
    notice.value = "";
    let sent = 0;
    const failures = [];
    try {
      for (const [index, file] of files.entries()) {
        if (scope.closed)
          break;
        const invalid = validateUpload(file);
        if (invalid) {
          failures.push(`${file.name}: ${invalid}`);
          continue;
        }
        notice.value = `Enviando ${index + 1}/${files.length} \xB7 ${file.name}`;
        progress.value = 0;
        const form = new FormData();
        form.append("file", uploadFile(file));
        if (destination)
          form.append("folder_id", destination);
        if (purpose)
          form.append("purpose", purpose);
        try {
          await http.upload(root + "/upload", form, (p) => {
            if (!scope.closed)
              progress.value = p;
          });
          sent++;
        } catch (e) {
          if (scope.closed)
            break;
          failures.push(`${file.name}: ${uploadError(e)}`);
        }
      }
      if (!scope.closed) {
        notice.value = `${sent} arquivo(s) enviado(s).`;
        error.value = failures.join("\n");
        await refresh();
      }
    } finally {
      if (!scope.closed) {
        busy.value = false;
        progress.value = 0;
      }
    }
  }
  function choose(event, purpose) {
    const input = event.target;
    void upload(Array.from(input.files ?? []), purpose);
    input.value = "";
  }
  function openContext(event, asset) {
    if (!props.gm || busy.value)
      return;
    event.preventDefault();
    context.value = { x: event.clientX, y: event.clientY, asset };
  }
  function dragAsset(event, asset) {
    event.dataTransfer?.setData("application/x-gravewright-library-asset", asset.id);
    if (asset.kind === "image")
      event.dataTransfer?.setData("application/x-gravewright-library-image", asset.id);
  }
  function drop(event, destination = folder.value) {
    dragging.value = false;
    if (!props.gm || busy.value)
      return;
    const id = event.dataTransfer?.getData("application/x-gravewright-library-asset");
    if (id) {
      void command("move", { asset_id: id, folder_id: destination || null });
      return;
    }
    void upload(Array.from(event.dataTransfer?.files ?? []), "", destination);
  }
  watch(() => props.revision, () => void refresh());
  onMounted(() => void refresh());
  onBeforeUnmount(() => scope.dispose());
  return { gwText: text, PhImage, PhMusicNotes, PhWaveform, PhFilePdf, PhFolder, PhFolderOpen, PhFolderPlus, PhMagnifyingGlass, PhTrash, PhArrowsLeftRight, HttpClient, ResourceScope, DirectoryContextMenu: DirectoryContextMenu_native_default, IMAGE_ACCEPT, AUDIO_ACCEPT, assetKinds, bytesLabel, uploadError, uploadFile, validateUpload, scope, http, root, state, folder, kind, search, folderName, busy, error, notice, progress, dragging, context, removing, moving, target, uploads, filters, visible, visibleBytes, refreshId, refresh, command, upload, choose, openContext, dragAsset, drop, emit: options.emit };
});
export {
  AssetUploadLibrary_native_default as mountAssetLibrary
};
