// gravewright/maps/frontend/native/tools.js
import { createSelection } from "./runtime/features/selection/ui/selection-workspace.js";
import Drawing from "./runtime/features/drawing/ui/DrawingWorkspace.native.js";
import Measurement from "./runtime/features/measurement/ui/MeasurementWorkspace.native.js";
import Images from "./runtime/features/images/ui/ImageWorkspace.native.js";
import { previewBoardImage } from "./runtime/features/images/model/image-preview.js";
import { createLeverControls } from "./runtime/features/images/ui/lever-controls.js";
import { imageInWorkspace } from "./runtime/features/images/model/image-layer.js";
import { openRegionEditor } from "./runtime/features/regions/ui/region-editor.js";
import Sources from "./runtime/features/scene-layers/ui/SceneSourcesWorkspace.native.js";
import Library from "./runtime/features/table-library/ui/AssetUploadLibrary.native.js";
import { vMovableResizable } from "./runtime/shared/lib/dom/movable-resizable.js";
var HttpClient = class {
  signal;
  constructor(_base, signal = () => void 0) {
    this.signal = signal;
  }
  async request(url, body) {
    const csrf = body === void 0 ? {} : await (await fetch("/__gravewright/csrf", { signal: this.signal() })).json();
    const response = await fetch(url, { method: body === void 0 ? "GET" : "POST", signal: this.signal(), headers: body === void 0 ? {} : { [csrf.header || "X-CSRF-Token"]: csrf.token, ...body instanceof FormData ? {} : { "Content-Type": "application/json" } }, body: body === void 0 ? void 0 : body instanceof FormData ? body : JSON.stringify(body) });
    const value = await response.json();
    if (!response.ok)
      throw Error(value.error || "Could not save the change.");
    return value;
  }
  get(url) {
    return this.request(url);
  }
  post(url, body) {
    return this.request(url, body);
  }
  upload(url, body, progress) {
    progress?.(0);
    return this.request(url, body).then((value) => {
      progress?.(100);
      return value;
    });
  }
};
function createTools(surface, board, map, gm, api, stateAPI) {
  let state = api.state, drawing, images, effects, library, libraryHost, regionEditor, closed = false;
  const hosts = { drawing: document.createElement("div"), images: document.createElement("div"), effects: document.createElement("div"), measurement: document.createElement("div"), markers: document.createElement("div") };
  for (const host of Object.values(hosts)) {
    host.style.display = "contents";
    surface.append(host);
  }
  const common = { HttpClient, command: api.command, read: api.read };
  const base = () => ({ viewport: board.viewport(), containerId: map.containerId, blockId: map.blockId, cell: map.gridSize * map.imageScale, grid: map.gridVisible });
  let measureRows = [], selection;
  const levers = createLeverControls(surface, board, gm, api, stateAPI);
  const measurement = Measurement(hosts.measurement, { ...common, props: { ...base(), active: false, maxRows: state.capabilities?.maxMeasurements, measureValue: map.measureValue, measureUnit: map.measureUnit }, emit(type, value) {
    if (type === "change") measureRows = value;
    if (type === "close") {
      stateAPI.mergePatch({ _tool: "select" });
      sync();
    }
  } });
  const markerProps = () => ({ ...base(), active: false, shared: true, rows: state.markers || [], measureValue: map.measureValue, measureUnit: map.measureUnit });
  const markers = Measurement(hosts.markers, { props: markerProps(), emit() {
  } });
  selection = createSelection(surface, board, map, gm, api, stateAPI, { rows: () => measureRows, replace: (rows) => measurement.call("replace", rows) });
  function sync() {
    if (closed || !board.viewport())
      return;
    const layer = stateAPI.getPath("_layer"), tool = stateAPI.getPath("_tool");
    board.editingLayer?.(layer || "game");
    levers.update(state);
    selection?.update(state);
    const measure = tool === "measure";
    markers.update(markerProps());
    measurement.update({ ...base(), active: tool === "measure", maxRows: state.capabilities?.maxMeasurements, measureValue: map.measureValue, measureUnit: map.measureUnit });
    const draw = gm && tool === "draw" && ["game", "gm"].includes(layer);
    if (draw && !drawing)
      drawing = Drawing(hosts.drawing, { ...common, props: { ...base(), document: state.drawings, audience: layer === "gm" ? "gm" : "campaign" }, emit(type) {
        if (type === "refresh")
          void api.read();
        if (type === "close") {
          stateAPI.mergePatch({ _tool: "select" });
          sync();
        }
      } });
    else if (!draw && drawing) {
      drawing.destroy();
      drawing = void 0;
    } else
      drawing?.update({ ...base(), document: state.drawings, audience: layer === "gm" ? "gm" : "campaign" });
    const compose = gm && layer === "composition" && !measure;
    const editableImages = state.images.filter((image) => imageInWorkspace(image, layer));
    if (compose && !images)
      images = Images(hosts.images, { ...common, props: { ...base(), images: editableImages, tool }, emit(type, value) {
        if (type === "refresh")
          void api.read();
        if (type === "preview")
          void previewBoardImage(board, state, value);
      } });
    else if (!compose && images) {
      images.destroy();
      images = void 0;
    } else
      images?.update({ ...base(), images: editableImages, tool });
    const effect = gm && layer === "effects" && !measure;
    if (effect && !effects)
      effects = Sources(hosts.effects, { ...common, props: { ...base(), state, layer: "effects", tool }, emit(type, value) {
        if (type === "changed")
          update(value);
        if (type === "preview")
          void board.update({ state: value || state });
        if (type === "tool") {
          stateAPI.mergePatch({ _tool: value });
          sync();
        }
      } });
    else if (!effect && effects) {
      effects.destroy();
      effects = void 0;
    } else
      effects?.update({ ...base(), state, tool });
  }
  function update(next) {
    state = next;
    sync();
  }
  function openLibrary() {
    if (library) {
      library.destroy();
      library = void 0;
      vMovableResizable.unmounted(libraryHost);
      libraryHost.remove();
      return;
    }
    const template = document.querySelector("#map-image-library");
    libraryHost = template.content.firstElementChild.cloneNode(true);
    document.body.append(libraryHost);
    libraryHost.querySelector("[data-library-close]").onclick = openLibrary;
    library = Library(libraryHost.querySelector("[data-library-body]"), { ...common, props: { containerId: map.containerId, gm, revision: 0 }, emit() {
    } });
    library.update({ revision: 1 });
    const tabs = libraryHost.querySelectorAll(".upload-library__tabs button");
    if (gm && tabs[1]) {
      tabs[1].disabled = false;
      tabs[1].removeAttribute("aria-disabled");
    }
    tabs.forEach((tab, index) => tab.onclick = () => {
      if (index === 1 && !gm) return;
      library?.destroy();
      const body = libraryHost.querySelector("[data-library-body]");
      body.replaceChildren();
      library = index === 1 ? window.gravewrightTableMedia.mountDecks(body) : Library(body, { ...common, props: { containerId: map.containerId, gm, revision: 0 }, emit() {
      } });
      tabs.forEach((button, i) => button.setAttribute("aria-pressed", String(i === index)));
    });
    vMovableResizable.mounted(libraryHost);
  }
  function editSelection({ detail: { object, event } }) {
    if (gm && object.kind === "zone" && object.data.region) {
      regionEditor?.close();
      regionEditor = openRegionEditor(object.data, { campaignId: map.containerId, sceneId: map.id, save: async (patch) => {
        try {
          await api.command("zones", "update", { zone_id: object.id, expected_version: object.data.version, patch });
        } catch (error) {
          if (!closed) await api.read().catch(() => {
          });
          throw error;
        }
        if (!closed) await api.read();
      } });
    }
    if (object.kind === "drawing") {
      stateAPI.mergePatch({ _layer: object.data.audience === "gm" ? "gm" : "game", _tool: "draw" });
      sync();
      drawing?.call("editId", object.id);
    }
    if (object.kind === "measure") {
      stateAPI.mergePatch({ _layer: "game", _tool: "measure" });
      sync();
      measurement.call("editId", object.id);
    }
    if (["shader", "particle"].includes(object.kind)) {
      stateAPI.mergePatch({ _layer: "effects", _tool: "select" });
      sync();
      effects?.call("doubleClick", event);
    }
  }
  window.addEventListener("gravewright:selection-edit", editSelection);
  function click(event) {
    if (event.target.closest("input,textarea,select,.gw-window,.effect-picker"))
      return;
    sync();
    const button = event.target.closest("[data-native-tool],.game-menubar__library");
    if (!button)
      return;
    if (button.matches(".game-menubar__library") || button.dataset.nativeTool === "images")
      openLibrary();
    else if (effects) {
      const tool = button.dataset.nativeTool;
      if (["particle", "shader"].includes(tool)) {
        stateAPI.mergePatch({ _tool: tool });
        sync();
      }
      effects.call("action", tool);
    }
  }
  window.addEventListener("click", click);
  window.addEventListener("gravewright:map-viewport", sync);
  sync();
  return { update, setMap(next) {
    Object.assign(map, next);
    sync();
  }, destroy() {
    closed = true;
    regionEditor?.close(true);
    window.removeEventListener("gravewright:selection-edit", editSelection);
    levers.destroy();
    selection?.destroy();
    drawing?.destroy();
    images?.destroy();
    effects?.destroy();
    measurement.destroy();
    markers.destroy();
    library?.destroy();
    if (libraryHost) {
      vMovableResizable.unmounted(libraryHost);
      libraryHost.remove();
    }
    for (const host of Object.values(hosts))
      host.remove();
    window.removeEventListener("click", click);
    window.removeEventListener("gravewright:map-viewport", sync);
  } };
}
export {
  createTools
};
