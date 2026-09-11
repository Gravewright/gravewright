import { createTools } from "./tools.js";
import { lightingWorkspace } from "./lighting.js";
import { wallController } from "./walls/ui/walls.js";
import { wallPresets, wallPreset, wallPayload } from "./walls/model/walls.js";
import {
  getPath,
  mergePatch,
} from "/static/gravewright_web/vendor/datastar-1.0.3.js";
export const node = (tag, attrs = {}, text) => {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs))
    if (v !== undefined) el.setAttribute(k, v);
  if (text !== undefined) el.textContent = text;
  return el;
};
export const clone = (id) =>
  document
    .getElementById("map-" + id)
    .content.firstElementChild.cloneNode(true);
export const icon = (name) =>
  document
    .getElementById("map-layer-icons")
    .content.querySelector(`[data-icon="${name}"]`)
    .firstElementChild.cloneNode(true);
// Keep SVG hit targets stable while pointer gestures and double-clicks are in flight.
export function patchSVG(root, next) {
  const fresh = [...next.childNodes];
  for (let i = 0; i < fresh.length; i++) {
    const value = fresh[i],
      old = root.childNodes[i];
    if (!old) {
      root.append(value);
      continue;
    }
    if (old.nodeName !== value.nodeName) {
      old.replaceWith(value);
      continue;
    }
    if (value.nodeType === Node.TEXT_NODE) {
      if (old.textContent !== value.textContent)
        old.textContent = value.textContent;
      continue;
    }
    for (const a of [...old.attributes])
      if (!value.hasAttribute(a.name)) old.removeAttribute(a.name);
    for (const a of value.attributes)
      if (old.getAttribute(a.name) !== a.value)
        old.setAttribute(a.name, a.value);
    for (const event of [
      "onclick",
      "onkeydown",
      "onpointerdown",
      "oncontextmenu",
    ])
      old[event] = value[event];
    patchSVG(old, value);
  }
  while (root.childNodes.length > fresh.length) root.lastChild.remove();
}
export function createLayers(surface, board, map, gm, initial) {
  let state = initial,
    controller,
    closed = false,
    picker,
    editor,
    menu,
    confirm,
    painting = false,
    lighting, extra;
  const walls = node("svg", { class: "wall-workspace" }),
    doors = node("svg", { class: "door-controls" }),
    hint = document.createElement("div");
  hint.className = "wall-workspace__hint";
  hint.setAttribute("role", "status");
  surface.append(doors, walls, hint);
  const command = (area, action, data) =>
    window.gravewrightRealtime.mapCommand("objects", {
      mapId: map.id,
      area,
      action,
      data,
    });
  const read = async () => {
    const r = await fetch(`/api/maps/${map.id}/state`, { cache: "no-store" });
    if (!r.ok) throw Error("Could not load scene.");
    const next = await r.json();
    update(next);
    return next;
  };
  function update(next) {
    if (closed || next.sceneId !== map.id || next.version < state.version)
      return;
    state = next;
    if (!lighting) void board.update({ state });
    controller?.update({ state });
    lighting?.update(state);
    extra?.update(state);
    paint();
  }
  function closeDialog(name) {
    if (name === "picker") {
      picker?.remove();
      picker = undefined;
    }
    if (name === "editor") {
      editor?.remove();
      editor = undefined;
    }
    if (name === "menu") {
      menu?.remove();
      menu = undefined;
    }
    if (name === "confirm") {
      confirm?.remove();
      confirm = undefined;
    }
  }
  function openPicker(view) {
    if (!picker) {
      picker = clone("wall-picker");
      document.body.append(picker);
      picker.querySelector("header button").onclick = () =>
        controller.call("closePicker");
      picker.onkeydown = (e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          controller.call("closePicker");
        }
      };
      const r = document
        .querySelector('[data-wall-tool="wall"]')
        ?.getBoundingClientRect();
      picker.style.left =
        Math.max(8, Math.min(innerWidth - 438, r?.left || 13)) + "px";
      picker.style.bottom = (r ? innerHeight - r.top + 8 : 89) + "px";
      const choices = picker.querySelector(".wall-picker__options");
      for (const [i, p] of wallPresets.entries()) {
        const b = document.createElement("button");
        b.dataset.preset = p.id;
        b.append(
          icon(
            [
              "LineSegment",
              "EyeSlash",
              "Steps",
              "Square",
              "GridFour",
              "Prohibit",
            ][i],
          ),
        );
        b.firstChild.style.color = p.color;
        const span = document.createElement("span");
        span.textContent = p.name;
        b.append(span);
        b.onmouseenter = b.onfocus = () => preview(p);
        b.onclick = () => controller.call("choose", p.id);
        choices.append(b);
      }
      choices.onmouseleave = () =>
        preview(wallPresets.find((p) => p.id === controller.view.choice));
    }
    for (const b of picker.querySelectorAll("[data-preset]"))
      b.setAttribute("aria-pressed", String(b.dataset.preset === view.choice));
    preview(view.preset);
  }
  function preview(p) {
    if (!picker) return;
    const el = picker.querySelector(".wall-picker__preview");
    el.style.setProperty("--wall-color", p.color);
    el.classList.toggle(
      "wall-picker__preview--pass",
      p.behavior.movement === "pass",
    );
    el.classList.toggle(
      "wall-picker__preview--animated",
      document.documentElement.dataset.renderProfile !== "performance",
    );
    el.setAttribute("role", "img");
    el.setAttribute("aria-label", `Preview: ${p.name}. ${p.description}`);
    el.querySelector("span").textContent = p.description;
    const line = el.querySelector("[data-wall-line]");
    line.setAttribute(
      "d",
      p.id === "elevation" ? "M195 102V75H208V48H221V21" : "M215 16V107",
    );
    line.setAttribute("stroke", p.color);
    line.setAttribute(
      "stroke-dasharray",
      ["secret", "invisible"].includes(p.id) ? "8 5" : "none",
    );
    el.querySelector("[data-wall-bars]").setAttribute("stroke", p.color);
    el.querySelector("[data-wall-bars]").style.display = [
      "bars",
      "window",
    ].includes(p.id)
      ? ""
      : "none";
    el.querySelector("[data-wall-beam]").setAttribute(
      "opacity",
      p.behavior.light === "pass" ? 0.15 : 0.03,
    );
  }
  function openEditor(view) {
    if (editor?.dataset.id !== view.editing.id) {
      closeDialog("editor");
      editor = clone("wall-editor");
      editor.dataset.id = view.editing.id;
      const w = view.editing,
        d = wallPayload(w),
        f = editor.querySelector("form");
      editor.querySelector("strong").textContent =
        w.kind === "door" ? "Configure door" : "Configure wall";
      const p = f.elements.preset;
      for (const preset of wallPresets)
        p.append(new Option(preset.name, preset.id));
      p.value = wallPreset(w).id;
      for (const [k, v] of Object.entries(d.behavior)) f.elements[k].value = v;
      f.elements.finite.checked = d.vertical.bottom != null;
      f.elements.bottom.value = d.vertical.bottom ?? 0;
      f.elements.top.value = d.vertical.top ?? 3;
      f.elements.discovered.checked = !!w.discovered;
      const sync = () => {
        const finite = f.elements.finite.checked;
        for (const el of f.querySelectorAll("[data-finite]"))
          el.hidden = !finite;
        f.elements.bottom.disabled = f.elements.top.disabled = !finite;
        f.querySelector("[data-secret]").hidden =
          wallPresets.find((p) => p.id === f.elements.preset.value)
            .presentation !== "secret";
        const valid =
          !finite ||
          Number(f.elements.top.value) > Number(f.elements.bottom.value);
        f.elements.top.setCustomValidity(
          valid ? "" : "Upper height must be greater than lower height.",
        );
      };
      p.onchange = () => {
        const p = wallPresets.find((p) => p.id === f.elements.preset.value);
        for (const [k, v] of Object.entries(p.behavior))
          f.elements[k].value = v;
        f.elements.finite.checked = !!p.vertical;
        f.elements.bottom.value = p.vertical?.bottom ?? 0;
        f.elements.top.value = p.vertical?.top ?? 3;
        sync();
      };
      f.oninput = sync;
      f.onsubmit = (e) => {
        e.preventDefault();
        if (!f.reportValidity()) return;
        const behavior = Object.fromEntries(
          ["movement", "vision", "light", "sound"].map((k) => [
            k,
            f.elements[k].value,
          ]),
        );
        controller.call(
          "run",
          "walls",
          "update",
          {
            wall_id: w.id,
            version: w.version,
            behavior,
            presentation: wallPresets.find((preset) => preset.id === p.value)
              .presentation,
            vertical: {
              bottom: f.elements.finite.checked
                ? Number(f.elements.bottom.value)
                : null,
              top: f.elements.finite.checked
                ? Number(f.elements.top.value)
                : null,
            },
            discovered: f.elements.discovered.checked,
          },
          () => controller.call("closeEditor"),
        );
      };
      editor.querySelector("header button").onclick = () =>
        controller.call("closeEditor");
      editor.onkeydown = (e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          controller.call("closeEditor");
        }
      };
      document.body.append(editor);
      sync();
    }
    editor.querySelector("fieldset").disabled = view.busy;
    const error = editor.querySelector("[role=alert]");
    error.hidden = !view.error;
    error.textContent = view.error;
  }
  function context(view) {
    if (menu?.dataset.id === view.context.wall.id) return;
    closeDialog("menu");
    menu = document.createElement("menu");
    menu.className = "gw-folder-menu directory-context-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Wall actions");
    menu.dataset.id = view.context.wall.id;
    menu.style.zIndex = 1500;
    menu.style.left =
      Math.max(8, Math.min(innerWidth - 210, view.context.x)) + "px";
    menu.style.top =
      Math.max(8, Math.min(innerHeight - 270, view.context.y)) + "px";
    const c = view.context,
      w = c.wall,
      items = [
        ["PencilSimple", "Configure", () => controller.call("edit", w)],
        ...(w.kind === "door"
          ? [
              [
                "Door",
                w.door_state === "open" ? "Close" : "Open",
                () => controller.call("operate", w),
              ],
              [
                "Lock",
                w.door_state === "locked" ? "Unlock" : "Lock",
                () => controller.call("operate", w, true),
              ],
            ]
          : [
              [
                "Scissors",
                "Split here",
                () => controller.call("split", w, c.world),
              ],
            ]),
        ["Copy", "Copy selection", () => controller.call("copy")],
        ["Clipboard", "Paste", () => controller.call("paste", c.world)],
        ["Trash", "Remove selection", () => controller.call("remove")],
      ];
    for (const [name, label, action] of items) {
      const li = document.createElement("li"),
        b = document.createElement("button");
      b.append(icon(name), document.createTextNode(label));
      if (name === "Trash") b.className = "is-danger";
      if (name === "Clipboard") b.disabled = !view.clipboard.length;
      b.onclick = action;
      li.append(b);
      menu.append(li);
    }
    document.body.append(menu);
  }
  function paint() {
    if (closed || painting || !controller) return;
    painting = true;
    try {
      const v = board.viewport(),
        view = controller.view,
        active = gm && getPath("_layer") === "walls";
      walls.hidden = !active;
      walls.style.display = active ? "" : "none";
      walls.classList.toggle(
        "wall-workspace--measure",
        getPath("_tool") === "measure",
      );
      hint.hidden = !active;
      const wallTree = document.createDocumentFragment(),
        doorTree = document.createDocumentFragment();
      if (active) {
        const g = node("g", {
          transform: `translate(${v.x} ${v.y}) scale(${v.scale})`,
        });
        for (const w of view.rendered) {
          const color =
            w.kind === "door"
              ? w.door_state === "open"
                ? "#79c3a3"
                : w.door_state === "locked"
                  ? "#ef9393"
                  : "#dfba75"
              : wallPreset(w).color;
          const group = node("g", {
            style: `color:${color}`,
            "aria-label": w.kind === "door" ? "Door" : wallPreset(w).name,
            role: "button",
            tabindex: 0,
          });
          group.onkeydown = (e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              controller.call("edit", w);
            }
          };
          const a = { x1: w.x1, y1: w.y1, x2: w.x2, y2: w.y2 };
          group.append(
            node("line", {
              ...a,
              stroke: "transparent",
              "stroke-width": 16 / v.scale,
            }),
            node("line", {
              ...a,
              stroke: "currentColor",
              "stroke-width": (view.selected.includes(w.id) ? 5 : 3) / v.scale,
              "stroke-dasharray":
                w.door_state === "open" ||
                ["secret", "invisible"].includes(w.presentation)
                  ? `${8 / v.scale} ${5 / v.scale}`
                  : undefined,
            }),
          );
          for (const n of [1, 2])
            group.append(
              node("circle", {
                cx: w["x" + n],
                cy: w["y" + n],
                r: 4 / v.scale,
                fill: "var(--surface)",
                stroke: "currentColor",
                "stroke-width": 1 / v.scale,
              }),
            );
          if (w.kind === "door" || w.vertical_top != null)
            group.append(
              node(
                "text",
                {
                  x: (w.x1 + w.x2) / 2,
                  y: (w.y1 + w.y2) / 2 - 8 / v.scale,
                  "font-size": 11 / v.scale,
                  "text-anchor": "middle",
                  fill: "currentColor",
                },
                w.kind === "door"
                  ? w.door_state === "open"
                    ? "Open"
                    : w.door_state === "locked"
                      ? "Locked"
                      : "Door"
                  : `${w.vertical_bottom} – ${w.vertical_top}`,
              ),
            );
          g.append(group);
        }
        if (view.start)
          g.append(
            node("line", {
              x1: view.start.x,
              y1: view.start.y,
              x2: view.cursor.x,
              y2: view.cursor.y,
              stroke: view.preset.color,
              "stroke-width": 2 / v.scale,
              "stroke-dasharray": `${5 / v.scale} ${3 / v.scale}`,
            }),
          );
        if (view.marquee) {
          const { from, to } = view.marquee;
          g.append(
            node("rect", {
              x: Math.min(from.x, to.x),
              y: Math.min(from.y, to.y),
              width: Math.abs(to.x - from.x),
              height: Math.abs(to.y - from.y),
              fill: "#d6b57822",
              stroke: "#d6b578",
              "stroke-width": 1 / v.scale,
            }),
          );
        }
        wallTree.append(g);
        hint.textContent = view.busy
          ? "Saving…"
          : ["wall", "door"].includes(getPath("_tool"))
            ? "Click endpoints or drag · Alt ends the chain · Shift snaps to grid · Ctrl ignores snapping · Esc cancels"
            : "Drag to select · Shift separates an endpoint · Double-click splits";
        if (view.error) {
          const e = document.createElement("span");
          e.setAttribute("role", "alert");
          e.textContent = view.error;
          hint.append(e);
        }
      }
      for (const w of state.walls.filter((w) => w.kind === "door")) {
        const g = node("g", {
          transform: `translate(${v.x + ((w.x1 + w.x2) / 2) * v.scale} ${v.y + ((w.y1 + w.y2) / 2) * v.scale})`,
          role: "button",
          tabindex: 0,
          "aria-label": `Porta ${w.door_state}`,
          "aria-disabled": String(
            view.busy || (!gm && w.door_state === "locked"),
          ),
        });
        g.append(
          node("rect", {
            x: -13,
            y: -13,
            width: 26,
            height: 26,
            rx: 5,
            fill: "#10151be6",
            stroke: w.door_state === "locked" ? "#ef9393" : "#d6b578",
          }),
          node("path", {
            d:
              w.door_state === "open"
                ? "M-5 8V-8L5 -5V8 M-8 8H8"
                : "M-5 8V-8H5V8 M-8 8H8 M1 0H2",
            fill: "none",
            stroke: "#d6b578",
            "stroke-width": 1.5,
          }),
          node(
            "title",
            {},
            gm
              ? "Click to open/close; right-click to lock/unlock"
              : "Click to open/close",
          ),
        );
        g.onpointerdown = (e) => e.stopPropagation();
        const operate = (e, lock = false) => {
          e.preventDefault();
          e.stopPropagation();
          if (view.busy || (!gm && (lock || w.door_state === "locked"))) return;
          controller.call("operate", w, lock);
        };
        g.onclick = operate;
        g.oncontextmenu = (e) => operate(e, true);
        g.onkeydown = (e) => {
          if (e.key === "Enter") operate(e);
        };
        doorTree.append(g);
      }
      patchSVG(walls, wallTree);
      patchSVG(doors, doorTree);
      if (active && view.picker) openPicker(view);
      else closeDialog("picker");
      if (active && view.editing) openEditor(view);
      else closeDialog("editor");
      if (active && view.context) context(view);
      else closeDialog("menu");
      if (active && view.clearConfirm && !confirm) {
        confirm = clone("layer-confirm");
        confirm.setAttribute("aria-label", "Clear walls");
        confirm.querySelector("strong").textContent =
          "Clear all walls and doors in this scene?";
        const b = confirm.querySelectorAll("button");
        b[0].onclick = () => controller.call("closeClear");
        b[1].onclick = () =>
          controller.call("run", "wall-selection", "clear", {}, () =>
            controller.call("closeClear"),
          );
        document.body.append(confirm);
      }
      if (!active || !view.clearConfirm) closeDialog("confirm");
      if (confirm) confirm.querySelectorAll("button")[1].disabled = view.busy;
    } finally {
      painting = false;
    }
  }
  controller = wallController(walls, {
    props: {
      state,
      viewport: board.viewport(),
      tool: "managed",
      containerId: map.containerId,
      blockId: map.blockId,
      cell: map.gridSize * map.imageScale,
      grid: map.gridVisible,
    },
    command,
    read,
    repaint: paint,
    emit(type, next) {
      if (type === "changed") update(next);
      if (type === "tool") {
        mergePatch({ _tool: next });
        sync();
      }
    },
  });
  function sync() {
    controller.update({
      viewport: board.viewport(),
      tool: gm && getPath("_layer") === "walls" ? getPath("_tool") : "managed",
    });
    paint();
  }
  function click(e) {
    const button = e.target.closest("[data-wall-tool]");
    if (button && gm && getPath("_layer") === "walls")
      controller.call("action", button.dataset.wallTool);
    sync();
  }
  function outside(e) {
    if (
      !e.target.closest(".wall-picker,[data-wall-tool]") &&
      controller.view.picker
    )
      controller.call("closePicker");
    if (!e.target.closest(".directory-context-menu") && controller.view.context)
      controller.call("closeMenu");
  }
  function editSelection({detail:{object}}){
    if(object.kind==='wall'){mergePatch({_layer:'walls',_tool:'select'});sync();controller.call('edit',object.data);}
    if(object.kind==='light')lighting?.edit(object.data);
  }
  window.addEventListener('gravewright:selection-edit',editSelection);
  window.addEventListener("click", click);
  window.addEventListener("pointerdown", outside);
  window.addEventListener("gravewright:map-viewport", sync);
  sync();
  lighting = lightingWorkspace(surface, board, map, gm, {
    command,
    read,
    get state() {
      return state;
    },
  });
  extra = createTools(surface,board,map,gm,{command,read,get state(){return state;}},{getPath,mergePatch});
  return {
    update,
    command,
    read,
    setMap(next) {
      Object.assign(map, next);
      extra?.setMap(next);
      controller.update({
        cell: map.gridSize * map.imageScale,
        grid: map.gridVisible,
      });
    },
    get state() {
      return state;
    },
    destroy() {
      closed = true;
      window.removeEventListener('gravewright:selection-edit',editSelection);
      extra?.destroy();
      lighting?.destroy();
      controller.destroy();
      for (const name of ["picker", "editor", "menu", "confirm"])
        closeDialog(name);
      walls.remove();
      doors.remove();
      hint.remove();
      window.removeEventListener("click", click);
      window.removeEventListener("pointerdown", outside);
      window.removeEventListener("gravewright:map-viewport", sync);
    },
  };
}
