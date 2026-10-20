// gravewright/maps/frontend/native/builder-preview.js
import { Application } from "/static/gravewright_maps/vendor/pixi.js";
import { PixiBoardRenderer } from "./runtime/widgets/game-board/lib/pixi-board-renderer.js";
import { SceneLayers } from "./runtime/widgets/game-board/lib/scene-layers.js";
import { renderingPreferences } from "/static/gravewright_maps/render-profile.js";
import { ShaderDraftValidator } from "./runtime/features/effects/model/shader-validation.js";
import { shaderPresets } from "./runtime/features/scene-layers/lib/shader-presets.js";
function mountNativePreview({ host, svg, onError }) {
  let board, layers, latest, closed = false, frame = 0, initializing = false, validator;
  const validated = /* @__PURE__ */ new Set();
  const resize = new ResizeObserver(() => queue());
  const camera = new MutationObserver(() => queue(false));
  resize.observe(host);
  camera.observe(svg, { attributes: true, attributeFilter: ["viewBox"] });
  let stateChanged = true;
  const stopProfile = renderingPreferences.subscribe(() => {
    stateChanged = true;
    queue();
  });
  function queue(changed = true) {
    if (closed) return;
    stateChanged ||= changed;
    if (!frame) frame = requestAnimationFrame(render);
  }
  function viewport() {
    const matrix = svg.getScreenCTM(), bounds = host.getBoundingClientRect();
    if (!matrix || !latest) return null;
    return { x: matrix.e - bounds.left, y: matrix.f - bounds.top, scale: matrix.a / latest.cell };
  }
  async function render() {
    frame = 0;
    if (closed || !latest || !host.clientWidth || !host.clientHeight) return;
    if (!board) {
      if (initializing) return;
      initializing = true;
      const application = new Application();
      try {
        await application.init({
          resizeTo: host,
          backgroundAlpha: 0,
          antialias: true,
          autoDensity: true,
          autoStart: false,
          resolution: Math.min(globalThis.devicePixelRatio || 1, 2)
        });
        if (closed) {
          application.destroy(false, { children: true });
          return;
        }
        host.append(application.canvas);
        application.canvas.setAttribute("aria-hidden", "true");
        application.canvas.style.pointerEvents = "none";
        board = new PixiBoardRenderer(application, "Native map effects preview");
        layers = new SceneLayers(board);
        stateChanged = true;
      } catch (cause) {
        try {
          if (application.renderer) application.destroy({ removeView: true, releaseGlobalResources: false }, { children: true });
        } catch {
        }
        if (!closed) onError(cause);
        return;
      } finally {
        initializing = false;
      }
    }
    if (closed) return;
    try {
      board.resize();
      const view = viewport();
      if (view) board.setViewport(view);
      if (stateChanged) {
        stateChanged = false;
        for (const shader of latest.state.shaders) {
          const preset = /^gravewright-preset:\/\/([^/]+)\/v1$/.exec(shader.source);
          if (preset) {
            if (!shaderPresets.some((value) => value.id === preset[1])) throw new Error("Unknown shader preset.");
            continue;
          }
          if (validated.has(shader.source)) continue;
          validator ??= new ShaderDraftValidator();
          const issue = validator.validate(shader.source);
          if (issue) throw new Error(issue);
          if (validated.size >= 64) validated.clear();
          validated.add(shader.source);
        }
        layers.render(latest.state, latest.cell, latest.width, latest.height, true);
      }
      host.dataset.renderState = "ready";
    } catch (cause) {
      if (!closed) onError(cause);
    }
  }
  return {
    update(value) {
      if (!closed) {
        latest = value;
        queue();
      }
    },
    dispose() {
      if (closed) return;
      closed = true;
      cancelAnimationFrame(frame);
      frame = 0;
      stopProfile();
      resize.disconnect();
      camera.disconnect();
      validator?.dispose();
      validator = void 0;
      validated.clear();
      layers?.dispose();
      layers = void 0;
      board?.destroy();
      board = void 0;
    }
  };
}
export {
  mountNativePreview
};
