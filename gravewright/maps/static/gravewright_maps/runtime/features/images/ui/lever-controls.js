// gravewright/maps/frontend/features/images/ui/lever-controls.js
import { createInteractiveImageHitTest, interactiveImageKind, canInteractWithImage } from "../model/lever-interaction.js";
import { text as gwText, onTextChange } from "../../../shared/config/i18n/text.js";
import { imageInWorkspace } from "../model/image-layer.js";
function createLeverControls(surface, board, gm, api, stateAPI) {
  const abort = new AbortController(), signal = abort.signal, pending = /* @__PURE__ */ new Set(), nodes = /* @__PURE__ */ new Map();
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("smart-image-controls");
  surface.append(svg);
  let state = api.state, hit = createInteractiveImageHitTest(state.images, gm, stateAPI.getPath("_layer")), hovered;
  const ignored = "button,input,textarea,select,[contenteditable=true],[data-image-resize],.gw-window,.directory-context-menu,.game-dock,.door-controls,.smart-image-controls,.image-workspace,.token-workspace [role=button],.token-workspace [role=img],.card-placement,.scene-sources,.wall-workspace";
  const active = () => stateAPI.getPath("_tool") === "select" && ["game", "gm"].includes(stateAPI.getPath("_layer")) && document.querySelector("#table-workspace")?.dataset.role !== "streamer" && !document.querySelector(".grid-calibration-panel");
  const node = (tag, attributes = {}) => {
    const element = document.createElementNS(svg.namespaceURI, tag);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    return element;
  };
  function makeControls(image) {
    const group = node("g", { "data-smart-image": image.id });
    const main = node("rect", {
      class: "smart-image-controls__object",
      role: "button",
      tabindex: 0,
      "data-smart-image-id": image.id,
      "data-smart-image-action": "interact",
      fill: "transparent"
    });
    const light = node("g", {
      class: "smart-image-controls__light",
      role: "button",
      tabindex: -1,
      "data-smart-image-id": image.id,
      "data-smart-image-action": "torch-light"
    });
    light.append(node("circle", { r: 14 }), node("path", {
      d: "M0 -8 C2 -3 7 -2 6 3 C6 7 3 9 0 9 C-5 9 -8 5 -6 1 C-5 -1 -3 -2 -3 -5 C-2 -2 1 0 0 -8Z"
    }));
    group.append(main, light);
    const entry = { group, main, light };
    nodes.set(image.id, entry);
    svg.append(group);
    return entry;
  }
  function render() {
    const view = board.viewport(), enabled = active();
    const valid = /* @__PURE__ */ new Set();
    svg.toggleAttribute("hidden", !enabled || !view);
    if (enabled && view) for (const image of state.images) {
      const kind = interactiveImageKind(image);
      if (!kind || !canInteractWithImage(image, gm) || hit(image)?.id !== image.id) continue;
      const width = image.natural_width * image.scale * view.scale;
      const height = image.natural_height * image.scale * view.scale;
      const x = view.x + image.x * view.scale, y = view.y + image.y * view.scale;
      const angle = image.rotation * Math.PI / 180;
      const right = Math.abs(Math.cos(angle) * width / 2) + Math.abs(Math.sin(angle) * height / 2);
      const top = Math.abs(Math.sin(angle) * width / 2) + Math.abs(Math.cos(angle) * height / 2);
      const bounds = surface.getBoundingClientRect();
      if (x + right < 0 || y + top < 0 || x - right > bounds.width || y - top > bounds.height) continue;
      valid.add(image.id);
      const { group, main, light } = nodes.get(image.id) ?? makeControls(image);
      group.setAttribute("transform", `translate(${x} ${y})`);
      group.setAttribute("data-smart-image-kind", kind);
      group.toggleAttribute("data-hovered", hovered === image.id);
      main.setAttribute("transform", `rotate(${image.rotation})`);
      for (const [key, value] of Object.entries({ x: -width / 2, y: -height / 2, width, height }))
        main.setAttribute(key, value);
      const pressed = (kind === "torch" ? image.torch : image.lever).state === "on";
      main.setAttribute("aria-pressed", String(pressed));
      main.setAttribute("aria-disabled", String(pending.has(image.id)));
      main.setAttribute("aria-label", image.empty === true ? gwText("Empty Object: {0}.", gwText(pressed ? "Activated" : "Deactivated")) : kind === "torch" ? gwText(
        "Torch: {0}. {1}. {2}.",
        gwText(pressed ? "Turned" : "Normal"),
        gwText(image.torch.lit ? "Lit" : "Unlit"),
        gwText(pressed ? "Return torch" : "Turn torch")
      ) : gwText("Lever: {0}.", gwText(pressed ? "Activated" : "Deactivated")));
      const anchorX = Math.min(Math.max(16, x + right + 16), Math.max(16, bounds.width - 16));
      const anchorY = Math.min(Math.max(16, y - top), Math.max(16, bounds.height - 16));
      light.setAttribute("transform", `translate(${anchorX - x} ${anchorY - y})`);
      light.toggleAttribute("hidden", kind !== "torch");
      light.setAttribute("aria-label", gwText(image.torch?.lit ? "Extinguish torch" : "Light torch"));
      light.setAttribute("aria-pressed", String(image.torch?.lit === true));
      light.setAttribute("aria-disabled", String(pending.has(image.id)));
      light.setAttribute("tabindex", kind === "torch" ? 0 : -1);
    }
    for (const [id, entry] of nodes) if (!valid.has(id)) {
      entry.group.remove();
      nodes.delete(id);
    }
  }
  async function operate(image, action2 = "interact") {
    if (!active() || pending.has(image.id)) return;
    image = state.images.find((row) => row.id === image.id);
    if (!canInteractWithImage(image, gm) || !imageInWorkspace(image, stateAPI.getPath("_layer")) || action2 === "torch-light" && !image.torch) return;
    pending.add(image.id);
    render();
    try {
      await api.command("images", action2, {
        image_id: image.id,
        ...action2 === "torch-light" ? { lit: !image.torch.lit } : {}
      });
      if (!signal.aborted) await api.read();
    } catch (error) {
      if (!signal.aborted) {
        window.dispatchEvent(new CustomEvent("gravewright:tool-error", { detail: { message: error.message } }));
        try {
          await api.read();
        } catch {
        }
      }
    } finally {
      pending.delete(image.id);
      if (!signal.aborted) render();
    }
  }
  const stop = (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
  };
  function double(event) {
    if (event.target.closest(".smart-image-controls")) {
      stop(event);
      return;
    }
    if (event.button !== 0 || !active() || event.target.closest(ignored)) return;
    const view = board.viewport();
    if (!view) return;
    const bounds = surface.getBoundingClientRect();
    const image = hit({
      x: (event.clientX - bounds.left - view.x) / view.scale,
      y: (event.clientY - bounds.top - view.y) / view.scale
    });
    if (!image) return;
    stop(event);
    void operate(image);
  }
  function action(event) {
    const target = event.target.closest("[data-smart-image-action]");
    if (!target || !active() || event.type === "keydown" && !["Enter", " "].includes(event.key)) return;
    if (event.type === "click" && target.dataset.smartImageAction !== "torch-light") return;
    stop(event);
    if (event.repeat) return;
    const image = state.images.find((row) => row.id === target.dataset.smartImageId);
    if (image) void operate(image, target.dataset.smartImageAction);
  }
  function hover(event) {
    const view = board.viewport();
    if (!active() || !view) return;
    if (event.target.closest(".smart-image-controls")) return;
    const bounds = surface.getBoundingClientRect();
    const image = hit({
      x: (event.clientX - bounds.left - view.x) / view.scale,
      y: (event.clientY - bounds.top - view.y) / view.scale
    });
    if (!image && hovered) {
      const nearby = nodes.get(hovered)?.group.getBoundingClientRect();
      if (nearby && event.clientX >= nearby.left - 8 && event.clientX <= nearby.right + 8 && event.clientY >= nearby.top - 8 && event.clientY <= nearby.bottom + 8) return;
    }
    if (hovered !== image?.id) {
      hovered = image?.id;
      render();
    }
  }
  surface.addEventListener("dblclick", double, { capture: true, signal });
  surface.addEventListener("keydown", action, { capture: true, signal });
  surface.addEventListener("click", action, { capture: true, signal });
  surface.addEventListener("pointerdown", (event) => {
    const target = event.target.closest('[data-smart-image-action="torch-light"]');
    if (target) {
      stop(event);
      target.focus();
    }
  }, { capture: true, signal });
  surface.addEventListener("pointermove", hover, { signal });
  surface.addEventListener("pointerleave", () => {
    hovered = void 0;
    render();
  }, { signal });
  window.addEventListener("gravewright:map-viewport", render, { signal });
  const stopText = onTextChange(render);
  render();
  return {
    update(next) {
      state = next;
      hit = createInteractiveImageHitTest(state.images, gm, stateAPI.getPath("_layer"));
      render();
    },
    destroy() {
      abort.abort();
      stopText();
      pending.clear();
      nodes.clear();
      svg.remove();
    }
  };
}
export {
  createLeverControls
};
