import { openPermissions } from '/static/gravewright_table/permissions.js';
import { detachWindow, restoreWindow } from '/static/gravewright_table/window-controls.js';
import { mountModal } from '/static/gravewright_table/modal.js';
import { mountFormTabs, modalText } from '/static/gravewright_table/form-modal.js';
import '/static/gravewright_table/realtime.js';
import { initialContent, sceneRestored, afterContentReady } from '/static/gravewright_table/content-state.js';
import { directoryView } from "./directory.js";
import { openUniversalVtt } from './universal-vtt.js';
import { createSceneBuilder } from './scene-builder.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import {
  mergePatch,
  getPath,
} from "/static/gravewright_web/vendor/datastar-1.0.3.js";
const panel = document.getElementById("maps-panel");
const workspace = document.getElementById("table-workspace");
const campaign = workspace.dataset.tableId;
const builderLifetime = new AbortController();
const builderHttp = new HttpClient(undefined, () => builderLifetime.signal);
const editWithBuilder = createSceneBuilder({ campaignId: campaign, signal: builderLifetime.signal,
  post: (...args) => builderHttp.post(...args), navigate: projectId => {
    const url = new URL(`/game/${campaign}/map-builder`, window.location.origin);
    url.searchParams.set('project', projectId); window.location.assign(url.href);
  },
});
const interchangeTranslator = createTranslator();
const interchangeText = key => interchangeTranslator.t(key);
const labels = JSON.parse(
  document.getElementById("map-text")?.textContent || "{}",
);
const clone = (name) =>
  document
    .getElementById("map-" + name)
    .content.firstElementChild.cloneNode(true);
const show = (element, on) => element.toggleAttribute("hidden", !on);
const builderButton = document.querySelector('[data-scene-builder-open]');
let builderOpening = false;
function updateBuilderButton() {
  if (!builderButton) return;
  show(builderButton, state.is_gm && Boolean(current) && !builderLifetime.signal.aborted);
  builderButton.disabled = builderOpening;
  builderButton.setAttribute('aria-busy', String(builderOpening));
}
const defaults = {
  name: "",
  gridSize: 70,
  gridOffsetX: 0,
  gridOffsetY: 0,
  imageScale: 1,
  measureValue: 1,
  measureUnit: "",
  visibility: "players",
  gridVisible: true,
  gridColor: "#79d9c0",
  gridOpacity: 0.4,
  activate: true,
};
let state = { maps: [], folders: [], activeMapId: null, is_gm: false },
  current,
  following = true,
  board,
  boardNode,
  generation = 0,
  dialog,
  menu,
  popup,
  calibration,
  layers,
  tokens,
  boardMapId;
const sceneText = {
  preview: modalText('View scene', 'Visualizar cena'),
  activate: modalText('Activate for players', 'Ativar para jogadores'),
  preload: modalText('Preload scene', 'Pré-carregar cena'),
  preparing: modalText('Preparing', 'Em preparação'),
  loading: modalText('Preloading', 'Pré-carregando'),
  ready: modalText('Preloaded', 'Pré-carregada'),
  editBuilder: modalText('Edit with MapBuilder', 'Editar com MapBuilder'),
  exportUniversal: interchangeText('Export Universal VTT'),
};
let preloadTask, preloadAbort, preloadGeneration = 0, preparing, prepared, preparedTimer;
function cancelPreparation() {
  ++preloadGeneration;
  preloadAbort?.abort(); preloadTask?.cancel();
  preloadAbort = preloadTask = undefined; preparing = undefined;
}
async function prepare(map) {
  cancelPreparation();
  const revision = preloadGeneration;
  clearTimeout(preparedTimer);
  preparing = map.id; prepared = undefined; tree();
  await new Promise(resolve => afterContentReady(resolve));
  if (revision !== preloadGeneration) return;
  const abort = preloadAbort = new AbortController();
  try {
    const [{ preloadScene }, response] = await Promise.all([
      import('./vendor/board.js?v=scene-preparation-1'),
      fetch(`/api/maps/${map.id}/manifest`, {signal: abort.signal, cache: 'no-store', priority: 'low'}),
    ]);
    if (!response.ok) throw Error(labels.mapFailed);
    const manifest = await response.json();
    if (revision !== preloadGeneration) return;
    const surface = document.querySelector('.game-table__scene-frame');
    preloadTask = preloadScene(manifest, {width: surface.clientWidth, height: surface.clientHeight}, map.initialView);
    await preloadTask.done;
    if (revision === preloadGeneration) {
      prepared = {id: map.id, version: map.version};
      preparedTimer = setTimeout(() => { prepared = undefined; tree(); }, 60_000);
    }
  } catch (cause) { if (revision === preloadGeneration && cause.name !== 'AbortError') error(cause.message); }
  finally { if (revision === preloadGeneration) { preparing = undefined; tree(); } }
}
const closedKey = `gravewright.directory.${campaign}.scenes`;
const expandedFolder = (id) => {
  try {
    return localStorage.getItem(closedKey + "." + id) === "true";
  } catch {
    return false;
  }
};
const command = (action, data) =>
  window.gravewrightRealtime.mapCommand(action, data);
function error(message) {
  const el = panel.querySelector("[role=alert]");
  el.textContent = message;
  show(el, true);
}
function options(select) {
  select.replaceChildren();
  const empty = new Option(labels.noGroup || "No group", "");
  if (select.closest(".game-scene-settings")) select.append(empty);
  for (const folder of state.folders)
    select.append(new Option(folder.label, folder.id));
}
function form(kind, onSubmit) {
  if (dialog?.close) dialog.close(); else dialog?.remove();
  const el = clone(kind);
  el.classList.add('table-modal-window');
  el.dataset.windowKey = 'scene-form:' + kind;
  dialog = el;
  let saving = false;
  el.querySelector("header button").onclick = () => { if (!saving) el.close(); };
  const cancel = el.querySelector('[data-cancel]');
  if (cancel) { cancel.textContent = modalText('Cancel','Cancelar'); cancel.onclick = () => { if (!saving) el.close(); }; }
  el.onsubmit = async (e) => {
    e.preventDefault();
    if (saving) return;
    saving = true;
    const button = el.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await onSubmit(el);
      el.close();
    } catch (cause) {
      const error = el.querySelector("[role=alert]");
      error.textContent = cause.message;
      show(error, true);
    } finally {
      button.disabled = false;
      saving = false;
    }
  };
  mountFormTabs(el);
  mountModal(el, {canClose: () => !saving});
  return el;
}
function populate(el, data) {
  for (const field of el.querySelectorAll("[name]")) {
    if (field.type === "file") continue;
    if (field.name === "groupId") options(field);
    if (field.type === "checkbox") field.checked = !!data[field.name];
    else field.value = data[field.name] ?? "";
  }
  const range = el.querySelector("[name=gridOpacity]");
  if (range) {
    const output = range.parentElement.querySelector("output");
    output.value = Number(range.value).toFixed(1);
    range.oninput = () => (output.value = Number(range.value).toFixed(1));
  }
}
function values(el) {
  const data = {};
  for (const input of el.querySelectorAll("[name]")) {
    if (input.type === "file") continue;
    data[input.name] =
      input.type === "checkbox"
        ? input.checked
        : ["number", "range"].includes(input.type) ||
            ["gridOffsetX", "gridOffsetY"].includes(input.name)
          ? Number(input.value)
          : input.value;
  }
  return data;
}
function csrf() {
  return (
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("gravewright-csrf="))
      ?.split("=")
      .slice(1)
      .join("=") || ""
  );
}
function createScene(groupId = "") {
  if (!state.is_gm) return;
  if (dialog?.close) dialog.close(); else dialog?.remove();
  const el = clone("create");
  dialog = el;
  el.querySelector("header button").onclick = () => el.close();
  el.querySelector('[data-map-create="upload"]').onclick = () => upload(groupId);
  el.querySelector('[data-map-create="uvtt"]').onclick = () => {
    el.close(); dialog = openUniversalVtt({ campaignId: campaign, folderId: groupId, t: interchangeText });
  };
  const builder = new URL(`/game/${campaign}/map-builder`, window.location.origin);
  if (groupId) builder.searchParams.set("folder", groupId);
  el.querySelector('[data-map-create="builder"]').href = builder.href;
  mountModal(el);
}
function upload(groupId = "") {
  const el = form(
    "upload",
    (form) =>
      new Promise((resolve, reject) => {
        const file = form.querySelector("input[type=file]").files[0];
        if (!file) {
          reject(new Error("Choose a map image."));
          return;
        }
        const data = values(form),
          body = new FormData();
        body.append("name", data.name);
        body.append("map", file);
        body.append("settings", JSON.stringify(data));
        body.append("activate", String(data.activate));
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `/api/containers/${campaign}/scene-upload`);
        xhr.setRequestHeader("X-CSRF-Token", decodeURIComponent(csrf()));
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable)
            form.querySelector("[data-upload-label]").textContent =
              labels.mapUploading.replace(
                "{percent}",
                Math.round((e.loaded / e.total) * 100),
              );
        };
        xhr.onload = () => {
          let result;
          try {
            result = JSON.parse(xhr.responseText);
          } catch {
            reject(new Error(labels.mapFailed));
            return;
          }
          if (xhr.status < 200 || xhr.status >= 300) {
            reject(new Error(result.error || labels.mapFailed));
            return;
          }
          following = data.activate;
          state.maps = state.maps
            .filter((m) => m.id !== result.id)
            .concat(result);
          if (data.activate) state.activeMapId = result.id;
          void navigate(result, false);
          resolve(result);
        };
        xhr.onerror = () => reject(new Error("Could not upload the map."));
        xhr.send(body);
      }),
  );
  populate(el, { ...defaults, groupId });
  const input = el.querySelector("input[type=file]"),
    button = el.querySelector("button[type=submit]");
  button.disabled = true;
  el.querySelector(".game-scene-editor__file").onclick = () => input.click();
  input.onchange = () => {
    el.querySelector("em").textContent = input.files[0]?.name || labels.noFile;
    if (input.files[0] && !el.elements.name.value)
      el.elements.name.value = input.files[0].name.replace(/\.[^.]+$/, "");
    button.disabled = !input.files.length || !el.elements.name.value.trim();
  };
  el.elements.name.oninput = () =>
    (button.disabled = !input.files.length || !el.elements.name.value.trim());
}
function settings(map) {
  let initialView = map.initialView;
  let environmentVersion, originalLighting;
  const el = form("settings", async (el) => {
    const {lightingMode, darkness, lightsOut, ...settings} = values(el);
    const lighting = {mode: lightingMode, darkness, lights_out: lightsOut};
    return command("update", {
      mapId: map.id,
      version: map.version,
      settings: { ...settings, initialView },
      ...(JSON.stringify(lighting) === originalLighting ? {} : {lighting, environmentVersion}),
    });
  });
  populate(el, { ...defaults, ...map });
  const save = el.querySelector('[type=submit]');
  save.disabled = true;
  el.querySelector('.table-modal-body').inert = true;
  void fetch(`/api/maps/${map.id}/state`, {cache: 'no-store'}).then(async response => {
    if (!response.ok) throw Error(labels.mapFailed);
    const state = await response.json();
    if (!el.isConnected) return;
    environmentVersion = state.version;
    const lighting = state.lighting;
    el.elements.lightingMode.querySelector('[value=dynamic]').disabled = !state.capabilities?.dynamicLighting;
    el.elements.lightingMode.value = lighting.mode;
    el.elements.darkness.value = lighting.darkness;
    el.elements.lightsOut.checked = lighting.lights_out;
    originalLighting = JSON.stringify({mode: lighting.mode, darkness: lighting.darkness, lights_out: lighting.lights_out});
    el.querySelector('[data-darkness-value]').textContent = Math.round(lighting.darkness * 100) + '%';
    save.disabled = false;
    el.querySelector('.table-modal-body').inert = false;
  }).catch(cause => { if (el.isConnected) { const alert = el.querySelector('[role=alert]'); alert.textContent = cause.message; alert.hidden = false; } });
  el.elements.darkness.oninput = () => { el.querySelector('[data-darkness-value]').textContent = Math.round(el.elements.darkness.value * 100) + '%'; };
  el.querySelector("[data-settings-title]").textContent =
    labels.editSceneTitle.replace("{name}", map.name);
  el.querySelector("[data-current-view]").onclick = () => {
    initialView = board?.viewport();
    const status = el.querySelector('[data-view-status]');
    status.textContent = modalText('Current view captured. Save to apply.', 'Visão atual capturada. Salve para aplicar.');
    status.hidden = false;
  };
  el.querySelector('[data-view-hint]').textContent = modalText('Choose the view used when this scene opens.', 'Escolha a visão usada ao abrir esta cena.');
  el.querySelector('[data-current-view]').disabled = current?.id !== map.id;
  const calibrate = el.querySelector("[data-calibrate]");
  calibrate.disabled = current?.id !== map.id;
  calibrate.onclick = async () => {
    const module = await import("./calibration.js");
    el.suspend();
    show(el, false);
    calibration = module.calibrate(
      boardNode.querySelector(".game-board__surface"),
      board,
      map,
      Number(el.elements.imageScale.value),
      (result) => {
        if (result)
          for (const [key, value] of Object.entries(result)) {
            let input = el.querySelector(`[name=${key}]`);
            if (!input) {
              input = document.createElement("input");
              input.type = "hidden";
              input.name = key;
              el.append(input);
            }
            if (input.type === "checkbox") input.checked = value;
            else input.value = value;
          }
        show(el, true);
        el.resume();
      },
    );
  };
}
function folderForm(parentId = "", existing) {
  const el = form("folder-form", (el) =>
    command(existing ? "folder-update" : "folder-create", {
      ...values(el),
      folderId: existing?.id,
      parentId,
    }),
  );
  if (existing || parentId) {
    const title = existing ? "Edit folder" : "Create folder";
    el.setAttribute("aria-label", title);
    el.querySelector("header strong").textContent = title;
  }
  if (existing) {
    el.elements.label.value = existing.label;
    el.elements.color.value = existing.color;
    el.elements.picker.value = existing.color;
    el.querySelector("button[type=submit]").textContent = "Save changes";
  }
  el.elements.picker.oninput = (e) =>
    (el.elements.color.value = e.target.value);
  el.elements.color.oninput = (e) =>
    (el.elements.picker.value = e.target.value);
}
function context(event, items) {
  event.preventDefault();
  event.stopPropagation();
  menu?.close();
  const source = event.currentTarget;
  const owner = source.ownerDocument;
  const view = owner.defaultView;
  const bounds = source.getBoundingClientRect();
  const x = Number.isFinite(event.clientX) ? event.clientX : bounds.left + 16;
  const y = Number.isFinite(event.clientY) ? event.clientY : bounds.bottom;
  const element = owner.createElement("menu");
  menu = element;
  element.className = "gw-folder-menu directory-context-menu";
  element.style.zIndex = "1500";
  element.setAttribute("role", "menu");
  element.style.left =
    Math.max(8, Math.min(x, view.innerWidth - 205)) + "px";
  element.style.top =
    Math.max(8, Math.min(y, view.innerHeight - 170)) + "px";
  const icons = {
    "Add subfolder": "FolderPlus",
    "Edit folder": "PencilSimple",
    "Delete folder": "Trash",
    [labels.newScene]: "Plus",
    [labels.activateScene]: "Broadcast",
    [labels.navigateScene]: "NavigationArrow",
    [sceneText.preview]: 'Eye',
    [sceneText.activate]: 'Broadcast',
    [sceneText.preload]: 'DownloadSimple',
    [labels.editScene]: "PencilSimple",
    [sceneText.editBuilder]: "PencilSimple",
    [labels.removeScene]: "Trash",
  };
  for (const [label, action, hook] of items) {
    const button = owner.createElement("button");
    button.type = "button";
    button.setAttribute("role", "menuitem");
    if (hook) button.dataset[hook] = '';
    if (icons[label])
      button.append(
        document
          .getElementById("map-icons")
          .content.querySelector(`[data-map-icon="${icons[label]}"]`)
          .firstElementChild.cloneNode(true),
      );
    button.append(document.createTextNode(label));
    if (label === labels.removeScene)
      button.className = "gw-folder-menu__danger";
    button.onclick = async (e) => {
      e.stopPropagation();
      try {
        if ((await action(button)) !== false) element.close();
      } catch (cause) {
        error(cause.message);
      }
    };
    element.append(button);
  }
  element.oncontextmenu = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };
  element.onkeydown = (e) => {
    if (e.key === "Escape") {
      element.close();
      source.focus();
      e.stopPropagation();
    }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
      e.preventDefault();
      const buttons = [...element.querySelectorAll("button")],
        index = buttons.indexOf(owner.activeElement);
      buttons[
        e.key === "Home"
          ? 0
          : e.key === "End"
            ? buttons.length - 1
            : (index + (e.key === "ArrowUp" ? -1 : 1) + buttons.length) %
              buttons.length
      ].focus();
    }
  };
  element.close = () => {
    owner.removeEventListener('click', element.close);
    view.removeEventListener('pagehide', element.close);
    element.remove();
    if (menu === element) menu = undefined;
  };
  owner.addEventListener('click', element.close);
  view.addEventListener('pagehide', element.close, {once: true});
  owner.body.append(element);
  const rect = element.getBoundingClientRect();
  element.style.left =
    Math.max(
      8,
      Math.min(parseFloat(element.style.left), view.innerWidth - rect.width - 8),
    ) + "px";
  element.style.top =
    Math.max(
      8,
      Math.min(parseFloat(element.style.top), view.innerHeight - rect.height - 8),
    ) + "px";
  element.querySelector('button')?.focus({preventScroll: true});
}
function deleteFolder(folder, source) {
  const el = clone("folder-delete"),
    r = source.getBoundingClientRect();
  el.style.left = Math.max(8, Math.min(innerWidth - 228, r.right - 220)) + "px";
  el.style.top = Math.max(8, Math.min(innerHeight - 165, r.top + 5)) + "px";
  const b = el.querySelectorAll("button");
  for (const [i, recursive] of [false, true].entries())
    b[i].onclick = async () => {
      try {
        await command("folder-delete", { folderId: folder.id, recursive });
        el.remove();
      } catch (e) {
        error(e.message);
      }
    };
  b[2].onclick = () => el.remove();
  document.body.append(el);
}
function tree() {
  if (!panel) return;
  const root = panel.querySelector("[data-map-tree]");
  root.replaceChildren();
  const query = panel.querySelector("input[type=search]").value;
  const view = directoryView(
    state.folders.map((f) => ({ ...f, name: f.label })),
    state.maps.map((m) => ({ ...m, folderId: m.groupId })),
    query,
  );
  const maps = state.maps.filter((m) => view.visibleEntries.has(m.id)),
    visible = view.visibleFolders;
  function draw(host, parent = "", depth = 0) {
    host.dataset.mapFolder = parent;
    for (const f of state.folders.filter(
      (f) => (f.parentId || "") === parent && (!query || visible.has(f.id)),
    )) {
      const el = document
        .getElementById("journal-folder")
        .content.firstElementChild.cloneNode(true);
      el.style.setProperty("--folder-color", f.color);
      el.dataset.mapFolder = f.id;
      el.querySelector(".gw-folder__label").textContent = f.label;
      el.querySelector(".gw-folder__count").textContent = view.counts.get(f.id);
      const toggle = el.querySelector(".gw-folder__toggle"),
        expanded = !!query || expandedFolder(f.id);
      toggle.setAttribute("aria-expanded", String(expanded));
      el.classList.toggle("gw-folder--open", expanded);
      show(el.querySelector(".gw-folder__content"), expanded);
      toggle.onclick = () => {
        try {
          localStorage.setItem(closedKey + "." + f.id, String(!expanded));
        } catch {}
        tree();
      };
      toggle.draggable = true;
      toggle.ondragstart = (e) =>
        e.dataTransfer.setData(
          "application/x-gravewright-scene",
          JSON.stringify({ folderId: f.id }),
        );
      const buttons = el.querySelectorAll(".gw-folder__actions button");
      buttons[0].title = labels.newScene;
      buttons[0].onclick = () => createScene(f.id);
      buttons[1].hidden = depth >= 2;
      buttons[1].onclick = () => folderForm(f.id);
      toggle.oncontextmenu = (e) =>
        context(e, [
          [labels.newScene, () => createScene(f.id)],
          ...(depth < 2 ? [["Add subfolder", () => folderForm(f.id)]] : []),
          ["Edit folder", () => folderForm(f.parentId, f)],
          ["Permissions", () => openPermissions('scene-folders', f.id)],
          ["Delete folder", () => deleteFolder(f, el)],
        ]);
      draw(el.querySelector(".directory-tree"), f.id, depth + 1);
      host.append(el);
    }
    const list = document.createElement("div");
    list.className = "game-scene-list";
    host.append(list);
    for (const map of maps.filter((m) => (m.groupId || "") === parent)) {
      const el = clone("entry");
      el.dataset.sceneId = map.id;
      el.onclick = () => navigate(map);
      el.querySelector("strong").textContent = map.name;
      el.querySelector("strong").title = map.name;
      const builderProjectId = state.is_gm ? map.builderProjectId : null;
      if (builderProjectId) {
        el.dataset.sceneBuilderOrigin = '';
        const icon = el.querySelector('svg');
        icon.removeAttribute('aria-hidden');
        icon.setAttribute('role', 'img');
        icon.setAttribute('aria-label', 'MapBuilder');
      }
      show(el.querySelector("[data-broadcast]"), map.id === state.activeMapId);
      el.querySelector('[data-broadcast]').textContent = modalText('Active for players', 'Ativa para jogadores');
      el.querySelector('[data-navigating]').textContent = sceneText.preparing;
      show(el.querySelector("[data-navigating]"), map.id === current?.id && map.id !== state.activeMapId);
      if (preparing === map.id || prepared?.id === map.id && prepared.version === map.version) {
        const badge = document.createElement('small'); badge.dataset.scenePrepared = '';
        badge.textContent = preparing === map.id ? sceneText.loading : sceneText.ready;
        el.append(badge);
      }
      el.classList.toggle("gw-folder-item--active", map.id === current?.id);
      el.draggable = true;
      el.ondragstart = (e) =>
        e.dataTransfer.setData(
          "application/x-gravewright-scene",
          JSON.stringify({ mapId: map.id }),
        );
      el.oncontextmenu = (e) =>
        context(e, [
          [
            sceneText.activate,
            async () => {
              await command("activate", { mapId: map.id });
            },
          ],
          [sceneText.preview, () => navigate(map)],
          [sceneText.preload, () => prepare(map)],
          [labels.editScene, () => settings(map)],
          [sceneText.exportUniversal, () => openUniversalVtt({ campaignId: campaign, sceneId: map.id, t: interchangeText })],
          ...(state.is_gm ? [[sceneText.editBuilder, async button => {
            button.disabled = true; button.setAttribute('aria-busy', 'true');
            try { return await editWithBuilder(map); }
            finally { button.disabled = false; button.removeAttribute('aria-busy'); }
          }, 'sceneBuilderEdit']] : []),
          ["Permissions", () => openPermissions('scenes', map.id)],
          [
            labels.removeScene,
            (button) => {
              if (!button.dataset.confirm) {
                button.dataset.confirm = "true";
                button.lastChild.textContent = labels.confirmRemoveScene;
                return false;
              }
              return command("delete", { mapId: map.id });
            },
          ],
        ]);
      el.onkeydown = event => {
        if (event.key === 'ContextMenu' || event.key === 'F10' && event.shiftKey) {
          el.oncontextmenu(event);
        }
      };
      list.append(el);
    }
  }
  draw(root);
}
async function navigate(map, privateView = true) {
  if (!panel) return;
  cancelPreparation();
  if (prepared?.id === map?.id) { prepared = undefined; clearTimeout(preparedTimer); }
  if (privateView && state.is_gm) {
    try {
      await command("navigate", {
        mapId: map?.id === state.activeMapId ? null : (map?.id || null),
      });
    } catch (cause) {
      error(cause.message);
      return;
    }
  }
  calibration?.();
  calibration = undefined;
  if (privateView) following = map?.id === state.activeMapId;
  current = map;
  updateBuilderButton();
  window.gravewrightRealtime.chatScope(map?.id);
  mergePatch({ _hasMap: !!map });
  tree();
  const version = ++generation;
  if (!map) {
    sceneRestored();
    window.dispatchEvent(new CustomEvent("gravewright:module-scene"));
    window.gravewrightRealtime.mapLayers(null);
    boardMapId = undefined;
    tokens?.destroy();
    tokens=undefined;
    layers?.destroy();
    layers = undefined;
    window.gravewrightRealtime.stopViewport();
    board?.destroy();
    board = undefined;
    boardNode?.remove();
    boardNode = undefined;
    show(document.querySelector(".game-table__empty-scene"), true);
    return;
  }
  try {
    // Network reads and module loading are independent; avoid a startup waterfall.
    const read = async path => {
      const response = await fetch(`/api/maps/${map.id}/${path}`, {cache: 'no-store'});
      if (!response.ok) throw Error(labels.mapFailed);
      return response.json();
    };
    const [manifest, layerState, {createBoard}, {createLayers}, {createTokens}] = await Promise.all([
      read('manifest'), read('state'), import('./vendor/board.js?v=ingame-perf-1'), import('./layers.js'),
      import('/static/gravewright_tokens/workspace.js?v=ingame-perf-1'),
    ]);
    if (version !== generation) return;
    const grid = {
      width: manifest.width,
      height: manifest.height,
      cellSize: map.gridSize * map.imageScale,
      offsetX: (map.gridOffsetX || 0) * map.imageScale,
      offsetY: (map.gridOffsetY || 0) * map.imageScale,
      color: map.gridColor,
      opacity: map.gridOpacity,
      visible: map.gridVisible,
    };
    const options = {
      manifest,
      grid,
      state: layerState,
      label: map.name,
      initialView: map.initialView,
      gm: state.is_gm,
      interactivePieces: false,
      tool: getPath("_tool"),
    };
    if (board && boardMapId === map.id) {
      await board.update(options);
      tokens?.setMap(map);
      tokens?.update(layerState);
      layers?.setMap(map);
      layers?.update(layerState);
      sceneRestored();
      window.dispatchEvent(new Event("gravewright:module-scene"));
      return;
    }
    tokens?.destroy();
    tokens=undefined;
    layers?.destroy();
    layers = undefined;
    window.gravewrightRealtime.stopViewport();
    board?.destroy({preservePrefetch: true});
    board = undefined;
    boardMapId = undefined;
    boardNode?.remove();
    boardNode = clone("board");
    document.querySelector(".game-table__scene-frame").append(boardNode);
    show(document.querySelector(".game-table__empty-scene"), false);
    if (version !== generation) return;
    board = createBoard(
      boardNode.querySelector(".game-board__surface"),
      options,
      (type, ...args) => {
        if (type === "region") window.gravewrightRealtime.sceneViewport(args[0], args[1]);
        if (type === "assetDrop") void window.gravewrightRealtime.mapCommand("objects", {mapId:map.id,area:"images",action:"create",data:{asset_id:args[0].assetId,x:args[0].x,y:args[0].y}}).then(()=>layers?.read()).catch(cause=>error(cause.message));
        if (type === "cardDrop") window.dispatchEvent(new CustomEvent("gravewright:cards-drop",{detail:args[0]}));
        if (type === "ping") window.gravewrightMaps.ping(args[0], args[1]);
        if (type === "viewport")
          window.dispatchEvent(
            new CustomEvent("gravewright:map-viewport", { detail: args[0] }),
          );
      },
    );
    boardMapId = map.id;
    await board.ready;
    if (version !== generation) return;
    if (version !== generation) return;
    layers = createLayers(
      boardNode.querySelector(".game-board__surface"),
      board,
      map,
      state.is_gm,
      layerState,
    );
    if(version!==generation)return;
    tokens=createTokens(boardNode.querySelector('.game-board__surface'),board,map,state.is_gm,layerState);
    window.gravewrightRealtime.mapLayers(map.id);
    sceneRestored();
    window.dispatchEvent(new Event("gravewright:module-scene"));
  } catch (cause) {
    if (version === generation) { error(cause.message); sceneRestored(); }
  }
}
if (panel) {
  panel.onclick = (e) => {
    const action = e.target.closest("[data-map-panel]")?.dataset.mapPanel;
    if (action === "create") createScene();
    if (action === "folder") folderForm();
    if (action === "close") mergePatch({ _mapsOpen: false });
    if (action === "minimize") panel.classList.toggle("game-panel--minimized");
    if (action === "detach") {
      if (popup && !popup.closed) {
        popup.focus();
        return;
      }
      popup = detachWindow(panel, 'maps-directory', labels.scenes || 'Scenes', {width:377});
    }
  };
  panel.querySelector("input[type=search]").oninput = tree;
  const root = panel.querySelector("[data-map-tree]");
  root.ondragover = (e) => e.preventDefault();
  root.ondrop = async (e) => {
    e.preventDefault();
    try {
      const data = JSON.parse(
        e.dataTransfer.getData("application/x-gravewright-scene"),
      );
      const target =
        e.target.closest("[data-map-folder]")?.dataset.mapFolder || "";
      await command(data.mapId ? "move" : "folder-update", {
        ...data,
        ...(data.mapId ? { groupId: target } : { parentId: target }),
      });
    } catch (cause) {
      error(cause.message);
    }
  };
}
window.gravewrightMaps = {
  createScene() {
    if (panel) createScene();
  },
  showDirectory() {
    if (popup && !popup.closed) { popup.focus(); return; }
    restoreWindow(panel);
    mergePatch({ _mapsOpen: true });
    requestAnimationFrame(() => panel.dispatchEvent(new Event('focusin', { bubbles: true })));
    window.gravewrightRealtime.mapsSubscribe();
  },
  toggle() {
    if (popup && !popup.closed) { popup.focus(); return; }
    if (panel.classList.contains('game-panel--minimized')) { restoreWindow(panel); mergePatch({_mapsOpen:true}); return; }
    mergePatch({ _mapsOpen: !getPath("_mapsOpen") });
    requestAnimationFrame(() =>
      panel.dispatchEvent(new Event("focusin", { bubbles: true })),
    );
    window.gravewrightRealtime.mapsSubscribe();
  },
  ping(point, focus) {
    if (current)
      window.gravewrightRealtime.mapPing({
        mapId: current.id,
        ...point,
        focus,
      });
  },
  get current() {
    return current;
  },
  get board() {
    return board;
  },
};
window.addEventListener("gravewright:map-ping", (event) => {
  const p = event.detail;
  if (p.mapId === current?.id)
    board?.ping({ x: p.x, y: p.y }, p.focus, p.color);
});
window.addEventListener("click", () => menu?.close());
window.addEventListener("gravewright:connected", () => {
  if (panel) window.gravewrightRealtime.mapsSubscribe();
});
function receiveState(nextState) {
  if (!panel) return;
  state = nextState;
  mergePatch({ _hasScenes: state.maps.length > 0 });
  following = state.followingActiveMap ?? true;
  const next = state.maps.find(
    (m) =>
      m.id === (following || !state.is_gm ? state.activeMapId : state.navigatingMapId),
  );
  if (!next && current) {
    following = true;
    void navigate(
      state.maps.find((m) => m.id === state.activeMapId),
      false,
    );
  } else if (!next && !current || next?.id !== current?.id || next?.version !== current?.version)
    void navigate(next, false);
  updateBuilderButton();
  tree();
}
builderButton?.addEventListener('click', async () => {
  if (!state.is_gm || !current || builderOpening || builderLifetime.signal.aborted) return;
  builderOpening = true;
  updateBuilderButton();
  try {
    await editWithBuilder(state.maps.find(map => map.id === current.id) || current);
  } catch (cause) {
    if (!builderLifetime.signal.aborted) error(cause.message);
  } finally {
    builderOpening = false;
    updateBuilderButton();
  }
}, { signal: builderLifetime.signal });
window.addEventListener('gravewright:maps', event => receiveState(event.detail));
const initial = initialContent('maps');
if(initial)receiveState(initial);
window.addEventListener("gravewright:access-revoked", () => {
  builderLifetime.abort();
  clearTimeout(preparedTimer);
  cancelPreparation(); prepared = undefined;
  state = { maps: [], folders: [], activeMapId: null, is_gm: false };
  void navigate(undefined, false);
  tree();
  dialog?.close();
  popup?.close();
});
window.addEventListener("pagehide", () => {
  builderLifetime.abort();
  menu?.close();
  clearTimeout(preparedTimer);
  cancelPreparation();
  calibration?.();
  tokens?.destroy();
    tokens=undefined;
    layers?.destroy();
  board?.destroy();
  popup?.close();
});
window.addEventListener('pageshow', event => {
  // The table renderer and module lifetimes were disposed on pagehide.
  // Rebuild the document when history restores its cached DOM.
  if (event.persisted) window.location.reload();
});
window.addEventListener("click", () => {
  if (board) void board.update({ tool: getPath("_tool") });
});
if (panel && window.gravewrightRealtime)
  window.gravewrightRealtime.mapsSubscribe();
window.addEventListener("gravewright:map-layers", (e) =>
  layers?.update(e.detail),
);

window.addEventListener('gravewright:scene.viewport.ready', ({detail}) => {
  board?.prioritize(detail.region, detail.tiles);
});
window.addEventListener('gravewright:scene.gm_prefetch.hint', ({detail}) => {
  if (!state.is_gm && detail.expires_at_ms > Date.now()) board?.hint(detail);
});

window.addEventListener('gravewright:open-scene', ({detail}) => {
  const map=state.maps.find(row=>row.id===detail.id);
  if(map)void navigate(map);
});
window.addEventListener('gravewright:locate-journal-marker', async ({detail}) => {
  try {
    const map = state.maps.find(row => row.id === detail.sceneId);
    if (!map) return;
    const {gravewright} = await import('/static/gravewright_modules/frontend-api.js');
    // Revalidate the marker through the current member's projection before navigating.
    const layers = await gravewright.maps.layers({mapId:map.id,sceneId:map.id});
    const pin = layers.journalPins?.find(row => row.id === detail.pinId);
    if (!pin) return;
    if (current?.id !== map.id) await navigate(map);
    if (current?.id === map.id) board?.ping({x:pin.x,y:pin.y},true,'#c09a5a');
  } catch (cause) { error(cause.message); }
});
window.addEventListener('gravewright:tool-error', ({detail})=>error(detail.message));
