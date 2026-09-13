import { HttpClient } from "./http-client.js";
import { BrowserBridge } from "./browser-bridge.js";
import { ModuleRuntime } from "./module-runtime.js";
import { DOMAIN_NAMES } from "./generated.js";
import { attachSurface } from "./frontend-api.js";
// Table integration: native DOM surfaces are attached to both host-page UI
// registrations and signed-package mounts, each with its own lifetime ownership.
const table = document.querySelector("#table-workspace");
if (table) {
  let render = function() {
    if (!pane) return;
    pane.classList.add("module-marketplace");
    pane.replaceChildren();
    const header = document.createElement("header");
    header.className = "module-marketplace__header";
    const title = document.createElement("h3");
    title.textContent = "Table modules";
    header.append(title);
    if (manage) {
      const browse = document.createElement("a");
      browse.href = "/inside?section=marketplace";
      browse.textContent = "Marketplace";
      browse.target = "_blank";
      browse.rel = "noopener";
      header.append(browse);
    }
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Refresh";
    retry.onclick = () => refresh(true);
    header.append(retry);
    pane.append(header);
    const error = document.createElement("p");
    error.className = "module-marketplace__error";
    error.role = "alert";
    error.hidden = true;
    pane.append(error);
    if (!packages.length) {
      const p = document.createElement("p");
      p.textContent = "No JavaScript modules installed.";
      pane.append(p);
    }
    for (const pkg of packages) {
      const row = document.createElement("article");
      row.className = "module-marketplace__item";
      const div = document.createElement("div"), strong = document.createElement("strong"), small = document.createElement("small");
      strong.textContent = pkg.name;
      small.textContent = `${pkg.version} \xB7 ${pkg.description}`;
      div.append(strong, small);
      row.append(div);
      const active = state?.modules.some((m) => m.id === pkg.id && m.version === pkg.version);
      if (!pkg.revoked && active && runtime.canCustomize(pkg.id)) {
        const customize = document.createElement("button");
        customize.type = "button";
        customize.dataset.moduleCustomize = pkg.id;
        const language = document.documentElement.lang;
        customize.textContent = language.startsWith("pt") || language.startsWith("es") ? "Personalizar" : "Customize";
        customize.onclick = async () => {
          customize.disabled = true;
          try { await runtime.customize(pkg.id); } catch (error) { report(error); }
          finally { customize.disabled = false; }
        };
        row.append(customize);
      }
      if (pkg.revoked) {
        const span = document.createElement("span");
        span.textContent = "Revoked";
        row.append(span);
      } else if (manage) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = active ? "Deactivate" : "Activate";
        b.onclick = async () => {
          b.disabled = true;
          const modules = Object.fromEntries(state.modules.map((m) => [m.id, m.version]));
          if (active) delete modules[pkg.id];
          else modules[pkg.id] = pkg.version;
          await configure(modules, Object.fromEntries(Object.entries(state.replacements).filter(([, id]) => modules[id])));
        };
        row.append(b);
      }
      pane.append(row);
    }
    if (manage && state?.modules.length) {
      const fieldset = document.createElement("fieldset");
      fieldset.className = "module-marketplace__replacements";
      const legend = document.createElement("legend");
      legend.textContent = "Interface replacements";
      fieldset.append(legend);
      for (const domain of DOMAIN_NAMES) {
        const label = document.createElement("label"), select = document.createElement("select");
        label.append(document.createTextNode(domain));
        select.add(new Option("Automatic", ""));
        for (const pkg of state.modules) select.add(new Option(pkg.id, pkg.id));
        select.value = state.replacements[domain] ?? "";
        select.onchange = () => {
          const replacements = { ...state.replacements };
          if (select.value) replacements[domain] = select.value;
          else delete replacements[domain];
          select.disabled = true;
          void configure(Object.fromEntries(state.modules.map((m) => [m.id, m.version])), replacements);
        };
        label.append(select);
        fieldset.append(label);
      }
      pane.append(fieldset);
    }
  }, attach = function(element, domain, context = {}, viewport) {
    if (surfaces.has(element)) return;
    const root = document.createElement("div");
    root.className = "gw-module-surface";
    root.dataset.domain = domain;
    element.append(root);
    const native = [...element.children].filter((e) => e !== root), hidden = native.map((e) => e.hidden);
    const release = runtime.attach({ domain, root, viewport, context: { tableId, mountId: "", moduleSetRevision: "0", ...context }, defaultVisible: async (visible) => {
      native.forEach((el, i) => el.hidden = visible ? hidden[i] : true);
    } });
    const releasePublic = attachSurface(element, domain, { tableId, ...context });
    surfaces.set(element, () => {
      releasePublic();
      release();
      root.remove();
      native.forEach((el, i) => el.hidden = hidden[i]);
    });
  }, scan = function() {
    document.querySelectorAll(".item-sheet[data-item-id]").forEach(el=>attach(el,"item.sheet",{itemId:el.dataset.itemId}));
    const combat=document.querySelector("#combat-panel .game-directory");
    if(combat){
      const sceneId=window.gravewrightMaps?.current?.id;
      if(combat.dataset.sceneId!==sceneId){surfaces.get(combat)?.();surfaces.delete(combat);combat.dataset.sceneId=sceneId||'';}
      if(sceneId)attach(combat,"combat.tracker",sceneContext());
    }
    document.querySelectorAll("[data-journal-id][data-journal-type]").forEach((el) => attach(el, "journal.sheet", { journalId: el.dataset.journalId }));
    for (const [element, release] of surfaces) if (!element.isConnected || element.dataset.sceneId && element.dataset.sceneId !== window.gravewrightMaps?.current?.id) {
      release();
      surfaces.delete(element);
    }
    for (const [selector, domain] of [["#items-panel .game-directory", "item.directory"], ["#actors-panel .game-directory", "actor.directory"], ["#maps-panel .game-directory", "scene.directory"], ["#chat-panel", "chat.log"], [".house-menu__preferences", "preferences"], ["#table-workspace", "table.interface"]]) {
      const el = document.querySelector(selector);
      if (el) attach(el, domain);
    }
    document.querySelectorAll(".actor-directory__sheet[data-actor-id],.token-sheet[data-actor-id]").forEach((el) => {
      if (el.dataset.sceneId && el.dataset.sceneId !== window.gravewrightMaps?.current?.id) return;
      attach(el, el.classList.contains("token-sheet") ? "token.sheet" : "actor.sheet", { actorId: el.dataset.actorId, ...el.dataset.tokenId ? { tokenId: el.dataset.tokenId } : {}, ...el.dataset.sceneId ? sceneContext() : {} });
    });
  }, sceneContext = function() {
    const map = window.gravewrightMaps?.current;
    if (!map) return {};
    const scale = map.imageScale ?? 1;
    return { sceneId: map.id, width: map.width * scale, height: map.height * scale, grid: { size: map.gridSize * scale, distance: map.measureValue, unit: map.measureUnit || "m", offsetX: (map.gridOffsetX || 0) * scale, offsetY: (map.gridOffsetY || 0) * scale } };
  }, scene = function() {
    const map = window.gravewrightMaps?.current, board = window.gravewrightMaps?.board, surface = document.querySelector(".game-board__surface");
    const key = JSON.stringify(sceneContext());
    if (!map || !board || !surface) return;
    if (key === sceneKey && overlay?.isConnected) return;
    sceneKey = key;
    for (const el of [overlay, controls]) {
      surfaces.get(el)?.();
      surfaces.delete(el);
      el?.remove();
    }
    overlay = document.createElement("div");
    overlay.className = "gw-module-overlay";
    surface.append(overlay);
    const view = () => board.viewport();
    attach(overlay, "scene.overlay", sceneContext(), { sceneToViewport: (p) => ({ x: p.x * view().scale + view().x, y: p.y * view().scale + view().y }), viewportToScene: (p) => ({ x: (p.x - view().x) / view().scale, y: (p.y - view().y) / view().scale }) });
    controls = document.createElement("div");
    controls.className = "gw-module-scene-controls";
    surface.append(controls);
    attach(controls, "scene.controls", sceneContext());
  };
  const tableId = table.dataset.tableId, scope = new AbortController(), http = new HttpClient(void 0, () => scope.signal), bridge = new BrowserBridge(tableId);
  const pane = document.querySelector("[data-table-modules]"), manage = pane?.dataset.manage === "true";
  let state, packages = [], timer, fetching = false, again = false;
  const report = (error) => {
    if (error?.code === "stale_context" || scope.signal.aborted) return;
    if (error?.status === 401 || error?.code === "authentication_required") {
      scope.abort();
      clearTimeout(timer);
      void runtime.close();
      const language = document.documentElement.lang;
      const label = (en, pt, es) => language.startsWith("pt") ? pt : language.startsWith("es") ? es : en;
      if (pane) {
        const message = pane.querySelector('[role="alert"]') ?? document.createElement("p");
        message.role = "alert";
        message.className = "module-marketplace__error";
        message.hidden = false;
        const login = document.createElement("a");
        login.href = "/login";
        login.textContent = label("Sign in again", "Entrar novamente", "Iniciar sesión de nuevo");
        message.replaceChildren(document.createTextNode(label(
          "Your session is no longer valid. Sign in again to load table modules. ",
          "Sua sessão não é mais válida. Entre novamente para carregar os módulos da mesa. ",
          "Tu sesión ya no es válida. Inicia sesión de nuevo para cargar los módulos de la mesa. "
        )), login);
        if (!message.isConnected) pane.append(message);
        for (const button of pane.querySelectorAll("button")) button.disabled = true;
      }
      return;
    }
    const p = pane?.querySelector("[role=alert]");
    if (p) {
      p.textContent = "A module could not load correctly. Refresh to retry.";
      p.hidden = false;
    }
    console.error("Module recovery required", error);
  };
  const runtime = new ModuleRuntime(bridge, report);
  async function refresh(force = false) {
    if (scope.signal.aborted) return;
    if (fetching) {
      again = true;
      return;
    }
    fetching = true;
    try {
      const next = await http.get(`/api/tables/${tableId}/modules`, { cache: "no-store" });
      if (scope.signal.aborted) return;
      if (force || next.moduleSetRevision !== state?.moduleSetRevision) {
        await runtime.reconcile(next);
        state = next;
      }
      packages = (await http.get("/api/module-packages")).filter((row) => !row.locales);
      render();
    } catch (error) {
      report(error);
    } finally {
      fetching = false;
      clearTimeout(timer);
      if (!scope.signal.aborted) timer = setTimeout(() => refresh(), again ? 0 : 15e3);
      again = false;
    }
  }
  async function configure(modules, replacements) {
    try {
      const next = await http.post(`/api/tables/${tableId}/modules`, { modules, replacements, expectedRevision: state.moduleSetRevision });
      await refresh();
    } catch (error) {
      report(error);
      await refresh();
    }
  }
  const surfaces = /* @__PURE__ */ new Map();
  let sceneKey = "", overlay, controls;
  window.addEventListener("gravewright:module-scene", scene, { signal: scope.signal });
  window.addEventListener("gravewright:map-viewport", (event) => {
    const map = window.gravewrightMaps?.current;
    if (map) bridge.publish("scene.viewport.changed", { tableId, sceneId: map.id, ...event.detail, width: overlay?.clientWidth ?? 0, height: overlay?.clientHeight ?? 0 });
  }, { signal: scope.signal });
  const originalScan = scan;
  const observer = new MutationObserver(() => {
    originalScan();
    scene();
  });
  observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-actor-id"] });
  scan();
  window.addEventListener("gravewright:modules.updated", (event) => {
    if (event.detail.moduleSetRevision !== state?.moduleSetRevision) {
      runtime.invalidate();
      void refresh();
    }
  }, { signal: scope.signal });
  window.addEventListener("gravewright:connected", () => refresh(), { signal: scope.signal });
  window.addEventListener("gravewright:access-revoked", () => {
    runtime.invalidate();
    void runtime.close();
  }, { signal: scope.signal });
  let actorIds = /* @__PURE__ */ new Set();
  // Compatibility SDK events are inferred from visible snapshots. A visibility
  // change or reconnect is not proof that a database actor was created/deleted.
  window.addEventListener("gravewright:actors.state", (event) => {
    const next = new Set(event.detail.actors.map((a) => a.id));
    for (const row of event.detail.actors) bridge.publish(actorIds.has(row.id) ? "actor.updated" : "actor.created", { tableId, id: row.id });
    for (const id of actorIds) if (!next.has(id)) bridge.publish("actor.deleted", { tableId, id });
    actorIds = next;
  }, { signal: scope.signal });
  window.addEventListener("pagehide", () => {
    scope.abort();
    clearTimeout(timer);
    observer.disconnect();
    for (const release of surfaces.values()) release();
    void runtime.close();
  }, { once: true });
  void refresh();
}
