/* Ferramenta Visibilidade: escolhe o regime de luz da cena.
 *
 * Tres modos, exclusivos entre si:
 *   none    - mapa aberto para todos;
 *   dynamic - escuridao + focos, com um interruptor que apaga e acende sem
 *             perder a intensidade ajustada;
 *   manual  - a nevoa pintada a mao, que continua sendo do modulo fog/*.
 *
 * O modo mora na cena (`lighting_mode`), nao no navegador: trocar de modo tem
 * de valer para a mesa inteira, e o mestre precisa reencontrar a cena como a
 * deixou. Por isso tudo passa por /game/scenes/lighting, que transmite um
 * scene.updated para a sala.
 */
(function () {
  "use strict";

  const MODES = ["none", "dynamic", "manual"];

  function csrf() {
    return typeof window.csrfToken === "function" ? window.csrfToken() : "";
  }

  function canvasFor(roomId) {
    return document.querySelector(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`) || null;
  }

  function clampDarkness(value, fallback = 0) {
    const number = Number(value);
    if (!Number.isFinite(number)) return fallback;
    return Math.min(1, Math.max(0, Math.round(number * 20) / 20));
  }

  function normalizedMode(value) {
    return MODES.includes(String(value)) ? String(value) : "none";
  }

  class LightingPanel {
    constructor(root) {
      this.root = root;
      this.roomId = root.dataset.roomId || "";
      this.pending = false;
      this.bind();
      this.sync();
    }

    canvas() {
      return canvasFor(this.roomId);
    }

    /* O canvas e a fonte da verdade: e ele que o scene.updated atualiza. */
    state() {
      const canvas = this.canvas();
      if (!canvas || !canvas.dataset.sceneId) return null;
      return {
        sceneId: canvas.dataset.sceneId,
        mode: normalizedMode(canvas.dataset.sceneLightingMode),
        darkness: clampDarkness(canvas.dataset.sceneDarknessConfig, 0),
        lightsOut: canvas.dataset.sceneLightsOut !== "false",
      };
    }

    bind() {
      this.root.addEventListener("click", (event) => {
        const modeBtn = event.target.closest("[data-lighting-mode]");
        if (modeBtn) {
          void this.setMode(modeBtn.dataset.lightingMode);
          return;
        }
        const lightsBtn = event.target.closest("[data-lighting-lights]");
        if (lightsBtn) void this.save({ lights_out: lightsBtn.dataset.lightingLights === "off" });
      });

      const slider = this.root.querySelector("[data-lighting-darkness]");
      if (slider) {
        // O output acompanha o arrasto; a gravacao so acontece ao soltar, para
        // nao inundar a sala com um scene.updated por passo do slider.
        slider.addEventListener("input", () => this.paintDarknessOutput(slider.value));
        slider.addEventListener("change", () => {
          void this.save({ darkness: clampDarkness(slider.value, 0) });
        });
      }
    }

    paintDarknessOutput(value) {
      const output = this.root.querySelector("[data-lighting-darkness-output]");
      if (output) output.textContent = clampDarkness(value, 0).toFixed(2);
    }

    async setMode(raw) {
      const mode = normalizedMode(raw);
      const current = this.state();
      if (!current || current.mode === mode) return;

      // Sair do manual apaga a nevoa que ficou pintada. Isso vai pelo comando
      // de fog que ja existe, que e quem transmite a mudanca para a sala.
      if (current.mode === "manual" && mode !== "manual") {
        window.GravewrightFogInternals?.sendDisable?.(this.roomId, current.sceneId);
      }
      await this.save({ mode });
    }

    async save(patch) {
      const current = this.state();
      if (!current || this.pending) return;
      this.pending = true;
      try {
        const response = await fetch("/game/scenes/lighting", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "x-csrftoken": csrf(),
          },
          credentials: "same-origin",
          body: JSON.stringify({
            campaign_id: this.roomId,
            scene_id: current.sceneId,
            mode: patch.mode ?? current.mode,
            ...(patch.darkness !== undefined ? { darkness: patch.darkness } : {}),
            ...(patch.lights_out !== undefined ? { lights_out: patch.lights_out } : {}),
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error_key || "game.lighting_panel.save_failed");
        // O scene.updated volta pelo WebSocket, mas quem editou nao deve esperar
        // a ida e volta para ver o proprio clique valer.
        this.applyToCanvas(data);
      } catch {
        const message = this.root.dataset.lightingSaveFailed;
        if (message) window.GravewrightToasts?.showToast?.(message, { duration: 2600 });
      } finally {
        this.pending = false;
        this.sync();
      }
    }

    applyToCanvas(data) {
      const canvas = this.canvas();
      if (!canvas || !data?.scene_id || canvas.dataset.sceneId !== data.scene_id) return;
      canvas.dataset.sceneLightingMode = normalizedMode(data.lighting_mode);
      canvas.dataset.sceneDarknessConfig = String(data.darkness ?? 0);
      canvas.dataset.sceneLightsOut = data.lights_out ? "true" : "false";
      canvas.dataset.sceneDarkness = String(data.effective_darkness ?? 0);
      window.GravewrightMap?.redraw?.();
    }

    sync() {
      const state = this.state();
      const empty = this.root.querySelector("[data-lighting-empty]");
      if (empty) empty.hidden = Boolean(state);

      this.root.querySelectorAll("[data-lighting-mode]").forEach((button) => {
        button.setAttribute("aria-pressed", String(Boolean(state) && button.dataset.lightingMode === state.mode));
        button.disabled = !state;
      });

      const hint = this.root.querySelector("[data-lighting-mode-hint]");
      if (hint) {
        const key = `lightingHint${state ? state.mode[0].toUpperCase() + state.mode.slice(1) : "None"}`;
        hint.textContent = state ? (this.root.dataset[key] || "") : "";
      }

      this.root.querySelectorAll("[data-lighting-pane]").forEach((pane) => {
        pane.hidden = !state || pane.dataset.lightingPane !== state.mode;
      });

      if (!state) return;
      const slider = this.root.querySelector("[data-lighting-darkness]");
      if (slider && document.activeElement !== slider) slider.value = String(state.darkness);
      this.paintDarknessOutput(slider ? slider.value : state.darkness);

      this.root.querySelectorAll("[data-lighting-lights]").forEach((button) => {
        const wantsOut = button.dataset.lightingLights === "off";
        button.setAttribute("aria-pressed", String(wantsOut === state.lightsOut));
      });
    }
  }

  const panels = new Map();

  function syncAll() {
    panels.forEach((panel) => panel.sync());
  }

  function init() {
    document.querySelectorAll("[data-lighting-panel]").forEach((root) => {
      if (panels.has(root)) return;
      panels.set(root, new LightingPanel(root));
    });

    // O scene.updated chega depois que map-streaming reescreve os data-* do
    // canvas, entao ler o estado no proximo tick da sempre o valor novo.
    document.addEventListener("vtt:transport-event", (event) => {
      const name = event.detail?.event;
      if (name !== "scene.updated" && name !== "scene.activated") return;
      window.setTimeout(syncAll, 0);
    });
    document.addEventListener("scene:activated", () => window.setTimeout(syncAll, 0));
  }

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", init, { once: true })
    : init();
})();
