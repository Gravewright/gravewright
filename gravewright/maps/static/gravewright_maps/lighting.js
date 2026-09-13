import { sourceController } from "./sources/sources.js";
import { lightPresets, paintAnimatedLight } from "./sources/light-profiles.js";
import {
  getPath,
  mergePatch,
} from "/static/gravewright_web/vendor/datastar-1.0.3.js";
import { renderingPreferences } from "./render-profile.js";
import { node, clone, icon, patchSVG } from "./layers.js";
export function lightingWorkspace(surface, board, map, gm, api) {
  let state = api.state,
    closed = false,
    controller,
    panel,
    popup,
    picker,
    editor,
    confirm,
    context,
    size = 3,
    opacity = 0.5,
    shape = "circle",
    busy = false,
    error = "",
    cursor,
    points = [],
    pointer,
    mode = "reveal",
    painting = false;
  const svg = node("svg", {
      class: "scene-sources",
      role: "group",
      "aria-label": "Origens de lights da cena",
    }),
    fog = node("svg", {
      class: "fog-workspace",
      "aria-label": "Manual lighting brush",
    });
  surface.append(svg, fog);
  let previewFrame = 0, previewChoice, previewLast = 0;
  let strokeTimer, strokeOps = [], queuedStrokes = [], strokeQueue = Promise.resolve();
  let darknessTimer, pendingDarkness;
  let fogFrame = 0;
  const render = () => {
    if (fogFrame || closed) return;
    fogFrame = requestAnimationFrame(() => {
      fogFrame = 0;
      if (closed) return;
      void board.update({
        state: {
          ...state,
          fog: {
            ...state.fog,
            gmOpacity: opacity,
            ops: [...state.fog.ops, ...queuedStrokes.flat(), ...strokeOps],
          },
        },
      });
    });
  };
  async function command(area, action, data = {}) {
    busy = true;
    error = "";
    paint();
    try {
      let result;
      if (area === 'fog') {
        // Serialize strokes and rebase on the authoritative version after a conflict.
        // Reset/enable actions are never silently replayed over another GM's edit.
        for (let attempt = 0; ; attempt++) {
          try {
            result = await api.command(area, action, {...data, expected_version: state.fog.version});
            break;
          } catch (err) {
            await api.read();
            if (err.code !== 'conflict' || action !== 'paint' || attempt >= 2 || !state.fog.enabled) throw err;
          }
        }
      } else result = await api.command(area, action, data);
      await api.read();
      return result;
    } catch (e) {
      error = e.message;
      throw e;
    } finally {
      busy = false;
      paint();
    }
  }
  const fire = (...args) => void command(...args).catch(() => {});
  function tool(value) {
    mergePatch({ _tool: value });
    sync();
  }
  function openPanel() {
    if (panel) {
      popup?.close();
      panel.remove();
      panel = undefined;
      return;
    }
    panel = clone("visibility");
    panel.querySelector("[data-visibility-action=close]").onclick = () => {
      popup?.close();
      panel.remove();
      panel = undefined;
    };
    panel.querySelector("[data-visibility-action=detach]").onclick = () => {
      if (popup && !popup.closed) {
        popup.focus();
        return;
      }
      popup = window.open("", "map-visibility", "popup,width=420,height=700");
      if (!popup) return;
      for (const css of document.querySelectorAll("link[rel=stylesheet]"))
        popup.document.head.append(css.cloneNode(true));
      popup.document.body.append(panel);
      panel.classList.add("game-panel--detached");
      popup.onpagehide = () => {
        if (panel && !closed) {
          document.getElementById("table-workspace").append(panel);
          panel.classList.remove("game-panel--detached");
        }
      };
    };
    panel.querySelector("[data-visibility-action=minimize]").onclick = () =>
      panel.classList.toggle("game-panel--minimized");
    panel.onclick = (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.dataset.mode)
        fire("lighting", "update", { ...state.lighting, mode: b.dataset.mode });
      if (b.dataset.lights)
        fire("lighting", "update", {
          ...state.lighting,
          lights_out: b.dataset.lights === "off",
        });
      if (b.dataset.fogAction)
        fire(
          "fog",
          b.dataset.fogAction,
          b.dataset.value
            ? {
                [b.dataset.fogAction === "enable" ? "initial" : "to"]:
                  b.dataset.value,
              }
            : {},
        );
      if (b.dataset.brush) {
        mode = b.dataset.brush;
        points = [];
        tool("fog-" + mode);
      }
      if (b.dataset.shape) {
        shape = b.dataset.shape;
        points = [];
        tool("fog-" + mode);
      }
    };
    const flushDarkness = () => {
      clearTimeout(darknessTimer); darknessTimer = undefined;
      if (pendingDarkness === undefined) return;
      const darkness = pendingDarkness; pendingDarkness = undefined;
      fire("lighting", "update", { ...state.lighting, darkness });
    };
    panel.querySelector("[name=darkness]").oninput = (e) => {
      pendingDarkness = Number(e.target.value);
      e.target.parentElement.querySelector("output").value = pendingDarkness.toFixed(2);
      void board.update({ state: { ...state, lighting: { ...state.lighting, darkness: pendingDarkness, effective_darkness: state.lighting.lights_out ? pendingDarkness : 0 } } });
      if (!darknessTimer) darknessTimer = setTimeout(flushDarkness, 100);
    };
    panel.querySelector("[name=darkness]").onchange = flushDarkness;
    panel.querySelector("[name=size]").oninput = (e) => {
      size = Number(e.target.value);
      paint();
    };
    panel.querySelector("[name=opacity]").oninput = (e) => {
      opacity = Number(e.target.value);
      void render();
      paint();
    };
    document.getElementById("table-workspace").append(panel);
    paint();
  }
  function lightPicker(view) {
    if (!picker) {
      picker = clone("light-picker");
      document.body.append(picker);
      const r = document
        .querySelector("[data-effect-tool=light]")
        ?.getBoundingClientRect();
      picker.style.left =
        Math.max(8, Math.min(innerWidth - 438, r?.left || 13)) + "px";
      picker.style.bottom = (r ? innerHeight - r.top + 8 : 89) + "px";
      picker.querySelector("header button").onclick = () =>
        controller.call("closePicker");
      picker.onkeydown = (e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          controller.call("closePicker");
        }
      };
      for (const p of lightPresets) {
        const b = document.createElement("button");
        b.dataset.choice = p.id;
        b.append(
          icon({ torch: "Flame", pulse: "Waveform", none: "Lightbulb" }[p.id]),
          document.createTextNode(p.name),
        );
        b.onmouseenter = b.onfocus = () => preview(p);
        b.onclick = () => controller.call("choose", p.id);
        picker.querySelector(".light-picker__options").append(b);
      }
      picker.querySelector(".light-picker__options").onmouseleave = () =>
        preview(lightPresets.find((p) => p.id === controller.view.lightChoice));
    }
    for (const b of picker.querySelectorAll("[data-choice]"))
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.choice === view.lightChoice),
      );
    if (!previewChoice) preview(lightPresets.find((p) => p.id === view.lightChoice));
  }
  function preview(p) {
    if (!p || !picker) return;
    previewChoice = p;
    picker.querySelector(".light-picker__preview").setAttribute("aria-label", "Preview: " + p.name);
    picker.querySelector(".light-picker__preview span").textContent = p.name;
    if (!previewFrame) previewFrame = requestAnimationFrame(animatePreview);
  }
  function animatePreview(time) {
    previewFrame = 0;
    if (closed || !picker || !previewChoice) return;
    const fps = { performance: 15, balanced: 30, quality: 60 }[renderingPreferences.current().name];
    if (time - previewLast >= 1000 / fps) {
      previewLast = time;
      const ctx = picker.querySelector("canvas").getContext("2d");
      ctx.clearRect(0, 0, 430, 123);
      paintAnimatedLight(ctx, { ...previewChoice, id: "preview", animation: previewChoice.id, enabled: true }, 215, 61, 55, time);
    }
    previewFrame = requestAnimationFrame(animatePreview);
  }
  function lightEditor(view) {
    if (editor?.dataset.id !== view.editing) {
      editor?.remove();
      editor = clone("light-editor");
      editor.dataset.id = view.editing;
      editor.querySelector("header button").onclick = () =>
        controller.call("closeEditor");
      for (const event of ["pointerdown", "wheel", "keydown"])
        editor.addEventListener(event, (e) => e.stopPropagation());
      editor.oninput = (e) => {
        const input = e.target;
        if (!input.name) return;
        const d = controller.view.draft;
        if (input.name === "unlimited")
          d.dim_radius = input.checked ? 0 : Math.max(6, d.bright_radius);
        else
          d[input.name] =
            input.type === "checkbox"
              ? input.checked
              : input.type === "range"
                ? Number(input.value)
                : input.value;
        controller.call("changed");
      };
      editor.querySelector("footer button").onclick = () =>
        controller.call(
          "remove",
          controller.view.items.filter((e) => e.id === controller.view.editing),
        );
      document.body.append(editor);
    }
    const d = view.draft;
    for (const input of editor.querySelectorAll("[name]")) {
      if (input.name === "unlimited") input.checked = d.dim_radius === 0;
      else if (input.type === "checkbox") input.checked = !!d[input.name];
      else input.value = d[input.name];
      if (input.type === "range") {
        input.max = Math.max(Number(input.max), d[input.name]);
        input.closest("label").querySelector("output").value =
          (input.name === "dim_radius" && d.dim_radius === 0
            ? "∞"
            : d[input.name]) +
          (["angle", "rotation"].includes(input.name) ? "°" : "");
        input.disabled = input.name === "dim_radius" && d.dim_radius === 0;
      }
    }
    editor.querySelector("[data-range=rotation]").hidden = d.angle >= 360;
    editor.querySelector("[role=status]").textContent = view.busy
      ? "Saving…"
      : "Changes saved automatically";
    editor.querySelector("[role=alert]").hidden = !view.error;
    editor.querySelector("[role=alert]").textContent = view.error;
    editor.querySelector("footer button").disabled = view.busy;
  }
  function paint() {
    if (closed || painting || !controller) return;
    painting = true;
    try {
      const active = gm && getPath("_layer") === "lighting",
        v = board.viewport(),
        view = controller.view;
      svg.style.display = active ? "" : "none";
      const g = node("g", {
        transform: `translate(${v.x},${v.y}) scale(${v.scale})`,
      });
      if (active) {
        for (const e of view.items) {
          const selected = view.selection.includes(e.key),
            origin = node("g", {
              "data-effect-id": e.id,
              "data-effect-kind": "light",
              role: "button",
              tabindex: 0,
              "aria-label": `Light: ${e.data.animation}`,
              class:
                "scene-sources__origin" +
                (selected ? " scene-sources__origin--selected" : ""),
              transform: `translate(${e.x + (selected ? view.delta.x : 0)},${e.y + (selected ? view.delta.y : 0)}) scale(${1 / v.scale})`,
            });
          origin.append(
            node("title", {}, `${e.data.animation} · double-click to edit`),
            node("circle", { r: 13 }),
            node("path", {
              transform: `rotate(${e.data.rotation})`,
              d: "M 13 0 L 21 0 M 17 -5 L 21 0 L 17 5",
            }),
            node(
              "text",
              { "text-anchor": "middle", "dominant-baseline": "central" },
              "☀",
            ),
          );
          g.append(origin);
        }
        if (view.marquee) {
          const { from, to } = view.marquee;
          g.append(
            node("rect", {
              class: "scene-sources__marquee",
              x: Math.min(from.x, to.x),
              y: Math.min(from.y, to.y),
              width: Math.abs(to.x - from.x),
              height: Math.abs(to.y - from.y),
              "stroke-width": 1 / v.scale,
            }),
          );
        }
      }
      const tree = document.createDocumentFragment();
      tree.append(g);
      patchSVG(svg, tree);
      if (active && view.picker === "light") lightPicker(view);
      else {
        picker?.remove();
        picker = undefined;
        previewChoice = undefined;
        cancelAnimationFrame(previewFrame); previewFrame = 0;
      }
      if (active && view.editor === "light") lightEditor(view);
      else {
        editor?.remove();
        editor = undefined;
      }
      if (active && view.clearConfirm) {
        if (!confirm) {
          confirm = clone("light-clear");
          const b = confirm.querySelectorAll("button");
          b[0].onclick = () => controller.call("closeClear");
          b[1].onclick = () => controller.call("clear");
          document.body.append(confirm);
        }
      } else {
        confirm?.remove();
        confirm = undefined;
      }
      if (active && view.context) {
        if (!context) {
          context = document.createElement("menu");
          context.className = "gw-folder-menu directory-context-menu";
          context.setAttribute("role", "menu");
          context.style.zIndex = 1500;
          for (const [name, label, action] of [
            ["Copy", "Copy", "copy"],
            ["Clipboard", "Paste", "paste"],
            ["Trash", "Remove", "remove"],
          ]) {
            const b = document.createElement("button");
            b.append(icon(name), document.createTextNode(label));
            b.disabled =
              action === "paste"
                ? !view.clipboard.length
                : !view.selected.length;
            b.onclick = () => controller.call(action);
            context.append(b);
          }
          document.body.append(context);
        }
        context.style.left =
          Math.max(8, Math.min(innerWidth - 210, view.context.x)) + "px";
        context.style.top =
          Math.max(8, Math.min(innerHeight - 150, view.context.y)) + "px";
      } else {
        context?.remove();
        context = undefined;
      }
      if (panel) {
        const lighting = state.lighting;
        panel.querySelector("fieldset").disabled = !gm;
        for (const button of panel.querySelectorAll("[data-mode],[data-fog-action]")) button.disabled = busy || (button.dataset.mode === 'dynamic' && state.capabilities?.dynamicLighting === false);
        panel.querySelector("[role=alert]").hidden = !error;
        panel.querySelector("[role=alert]").textContent = error;
        for (const b of panel.querySelectorAll("[data-mode]"))
          b.setAttribute(
            "aria-pressed",
            String(b.dataset.mode === lighting.mode),
          );
        panel.querySelector("[data-mode-hint]").textContent = {
          none: "The whole map is visible to everyone. Nothing is hidden.",
          dynamic:
            "Players only see what their tokens and lights reach. Walls block vision.",
          manual:
            "Paint revealed areas by hand, independently of tokens and lights.",
        }[lighting.mode];
        for (const el of panel.querySelectorAll("[data-mode-section]"))
          el.hidden = el.dataset.modeSection !== lighting.mode;
        for (const b of panel.querySelectorAll("[data-lights]"))
          b.setAttribute(
            "aria-pressed",
            String(b.dataset.lights === (lighting.lights_out ? "off" : "on")),
          );
        panel.querySelector("[data-fog-status]").textContent = state.fog.enabled
          ? "Manual lighting is active."
          : "Manual lighting is off. Choose an initial state to enable it.";
        panel.querySelector("[data-fog-disabled]").hidden = state.fog.enabled;
        panel.querySelector("[data-fog-enabled]").hidden = !state.fog.enabled;
        for (const b of panel.querySelectorAll("[data-brush]"))
          b.setAttribute(
            "aria-pressed",
            String(getPath("_tool") === "fog-" + b.dataset.brush),
          );
        for (const b of panel.querySelectorAll("[data-shape]"))
          b.setAttribute("aria-pressed", String(shape === b.dataset.shape));
        for (const [name, value] of Object.entries({
          darkness: lighting.darkness,
          size,
          opacity,
        })) {
          const input = panel.querySelector(`[name=${name}]`);
          if (document.activeElement !== input) input.value = value;
          input.parentElement.querySelector("output").value =
            name === "opacity"
              ? Math.round(value * 100) + "%"
              : name === "darkness"
                ? value.toFixed(2)
                : value;
        }
        panel.querySelector("[data-brush-size]").hidden = shape === "polygon";
        panel.querySelector("[data-brush-hint]").textContent =
          shape === "polygon"
            ? "Click to add points. Click the first point to close."
            : "Alt+scroll no mapa para ajustar rapidamente.";
      }
      const brush =
        gm &&
        state.lighting.mode === "manual" &&
        state.fog.enabled &&
        getPath("_tool").startsWith("fog-");
      fog.style.display = brush ? "" : "none";
      fog.replaceChildren();
      if (brush) {
        mode = getPath("_tool").slice(4);
        const g = node("g", {
            transform: `translate(${v.x},${v.y}) scale(${v.scale})`,
            "stroke-width": 1 / v.scale,
            class: mode === "hide" ? "fog-workspace__hide" : "",
          }),
          diameter = size * map.gridSize * map.imageScale;
        if (cursor && shape === "circle")
          g.append(
            node("circle", { cx: cursor.x, cy: cursor.y, r: diameter / 2 }),
          );
        if (cursor && shape === "square")
          g.append(
            node("rect", {
              x: cursor.x - diameter / 2,
              y: cursor.y - diameter / 2,
              width: diameter,
              height: diameter,
            }),
          );
        if (shape === "polygon" && points.length) {
          g.append(
            node("polyline", {
              points: [...points, ...(cursor ? [cursor] : [])]
                .map((p) => `${p.x},${p.y}`)
                .join(" "),
            }),
            node("circle", {
              cx: points[0].x,
              cy: points[0].y,
              r: 8 / v.scale,
            }),
          );
        }
        fog.append(g);
      }
    } finally {
      painting = false;
    }
  }
  function at(e) {
    const r = surface.getBoundingClientRect(),
      v = board.viewport();
    return {
      x: (e.clientX - r.left - v.x) / v.scale,
      y: (e.clientY - r.top - v.y) / v.scale,
    };
  }
  function flushStroke() {
    clearTimeout(strokeTimer); strokeTimer = undefined;
    if (!strokeOps.length) return;
    while (strokeOps.length) {
      const ops = strokeOps.splice(0, Math.min(state.capabilities?.fogMaxOps || 64, 32));
      queuedStrokes.push(ops);
      strokeQueue = strokeQueue.then(async () => {
        if (closed) return;
        try { await command("fog", "paint", { ops }); }
        catch { /* command displays the error; remove the optimistic batch below */ }
        finally {
          queuedStrokes = queuedStrokes.filter(batch => batch !== ops);
          if (!closed) void render();
        }
      });
    }
  }
  function stamp(p) {
    const cell = map.gridSize * map.imageScale;
    strokeOps.push({ mode, shape, geom: {
      center_x_cells: p.x / cell, center_y_cells: p.y / cell,
      [shape === "circle" ? "radius_cells" : "size_cells"]: shape === "circle" ? size / 2 : size,
    } });
    if (!strokeTimer) strokeTimer = setTimeout(flushStroke, 100);
  }
  function finish() {
    if (points.length < 3) return;
    const cell = map.gridSize * map.imageScale;
    fire("fog", "paint", {
      ops: [
        {
          mode,
          shape: "polygon",
          geom: { points_cells: points.map((p) => [p.x / cell, p.y / cell]) },
        },
      ],
    });
    points = [];
    paint();
  }
  fog.onpointerdown = (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    cursor = at(e);
    if (shape === "polygon") {
      if (
        points.length >= 3 &&
        Math.hypot(cursor.x - points[0].x, cursor.y - points[0].y) <
          13 / board.viewport().scale
      ) {
        finish();
        return;
      }
      if (points.length < (state.capabilities?.fogMaxPoints || 128)) points.push(cursor);
    } else {
      pointer = e.pointerId;
      points = [cursor];
      stamp(cursor);
      void render();
      fog.setPointerCapture(pointer);
    }
    paint();
  };
  fog.onpointermove = (e) => {
    cursor = at(e);
    if (pointer === e.pointerId) {
      e.stopPropagation();
      const last = points.at(-1),
        distance = Math.hypot(cursor.x - last.x, cursor.y - last.y),
        step = Math.max(1, (size * map.gridSize * map.imageScale) / 4);
      if (distance >= step) {
        const count = Math.min(100, Math.ceil(distance / step));
        for (let i = 1; i <= count; i++) {
          const point = {
            x: last.x + ((cursor.x - last.x) * i) / count,
            y: last.y + ((cursor.y - last.y) * i) / count,
          };
          stamp(point);
        }
        points = [cursor];
        void render();
      }
    }
    paint();
  };
  fog.onpointerup = fog.onpointercancel = (e) => {
    if (pointer !== e.pointerId) return;
    e.stopPropagation();
    pointer = undefined;
    if (fog.hasPointerCapture(e.pointerId))
      fog.releasePointerCapture(e.pointerId);
    if (e.type !== "pointercancel") flushStroke();
    else { clearTimeout(strokeTimer); strokeTimer = undefined; strokeOps = []; void render(); }
    points = [];
    paint();
  };
  fog.onpointerleave = () => {
    cursor = undefined;
    paint();
  };
  fog.onwheel = (e) => {
    if (!e.altKey) return;
    e.preventDefault();
    e.stopPropagation();
    size = Math.max(1, Math.min(40, size + (e.deltaY > 0 ? -1 : 1)));
    paint();
  };
  controller = sourceController(svg, {
    props: {
      layer: "lighting",
      state,
      viewport: board.viewport(),
      tool: "managed",
      containerId: map.containerId,
      blockId: map.blockId,
    },
    command: api.command,
    read: api.read,
    repaint: paint,
    emit(type, next) {
      if (type === "changed") update(next);
      if (type === "tool") tool(next);
      if (type === "preview")
        void board.update({
          state: next || {
            ...state,
            fog: { ...state.fog, gmOpacity: opacity, ops: [...state.fog.ops, ...queuedStrokes.flat(), ...strokeOps] },
          },
        });
    },
  });
  function sync() {
    controller.update({
      viewport: board.viewport(),
      tool:
        gm && getPath("_layer") === "lighting" ? getPath("_tool") : "managed",
    });
    paint();
  }
  function click(e) {
    const b = e.target.closest("[data-map-visibility],[data-effect-tool]");
    if (b?.hasAttribute("data-map-visibility")) openPanel();
    if (b?.dataset.effectTool && gm)
      controller.call("action", b.dataset.effectTool);
    sync();
  }
  function key(e) {
    if (
      fog.style.display === "none" ||
      e.target.closest("input,textarea,select,.gw-window")
    )
      return;
    if (e.key === "Escape") {
      points = [];
      pointer = undefined;
      clearTimeout(strokeTimer); strokeTimer = undefined; strokeOps = []; void render();
      e.stopImmediatePropagation();
      paint();
    }
    if (e.key === "Enter" && shape === "polygon") {
      finish();
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }
  function outside(e) {
    if (
      !e.target.closest(".light-picker,[data-effect-tool]") &&
      controller.view.picker
    )
      controller.call("closePicker");
    if (!e.target.closest(".directory-context-menu") && controller.view.context)
      controller.call("closeMenu");
  }
  function update(next) {
    if (closed || next.sceneId !== map.id || next.version < state.version)
      return;
    const before = `${state.lighting.mode}:${state.fog.enabled}`;
    state = next;
    controller.update({ state });
    if (before !== `${state.lighting.mode}:${state.fog.enabled}`) {
      points = [];
      pointer = undefined;
      if (gm && state.lighting.mode === "manual" && state.fog.enabled)
        tool("fog-" + mode);
      else if (getPath("_tool").startsWith("fog-")) tool("select");
    }
    void render();
    paint();
  }
  window.addEventListener("click", click);
  window.addEventListener("pointerdown", outside);
  window.addEventListener("gravewright:map-viewport", sync);
  document.addEventListener("keydown", key, true);
  sync();
  return {
    edit(row){mergePatch({_layer:'lighting',_tool:'select'});sync();controller.call('open','light',{id:row.id,data:row});},
    update,
    destroy() {
      closed = true;
      clearTimeout(strokeTimer); clearTimeout(darknessTimer); cancelAnimationFrame(previewFrame); cancelAnimationFrame(fogFrame);
      popup?.close();
      controller.destroy();
      for (const el of [svg, fog, panel, picker, editor, context, confirm])
        el?.remove();
      window.removeEventListener("click", click);
      window.removeEventListener("pointerdown", outside);
      window.removeEventListener("gravewright:map-viewport", sync);
      document.removeEventListener("keydown", key, true);
    },
  };
}
