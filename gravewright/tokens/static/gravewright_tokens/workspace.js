import { onForeignDrop } from "/static/gravewright_actors/tree-drag.js";
import { tokenController } from "./controller.js";
import { getPath } from "/static/gravewright_web/vendor/datastar-1.0.3.js";
import { node, patchSVG } from "/static/gravewright_maps/layers.js";
import { clone, icon, context } from "/static/gravewright_actors/workspace.js";
import { openSheet } from "/static/gravewright_pdf_system/sheet.js";
export function createTokens(surface, board, map, gm, initial) {
  const campaign = document.getElementById("table-workspace").dataset.tableId,
    svg = node("svg", {
      class: "token-workspace",
      "aria-label": "Scene tokens",
    }),
    status = document.createElement("p");
  status.className = "token-workspace__status";
  surface.append(svg, status);
  let state = initial,
    rows = [],
    readRevision = 0,
    controller,
    closed = false,
    queued = false,
    hover,
    editor,
    editorKey,
    confirmation,
    contextKey,
    sheet,
    sheetId,
    menu,
    lastRender = "",
    frame = 0,
    selectionPreview;
  const repaint = () => {
    if (closed || queued) return;
    queued = true;
    queueMicrotask(() => {
      queued = false;
      if (controller && !closed) paint();
    });
  };
  const grid = () => ({
    cell: map.gridSize * map.imageScale,
    x: (map.gridOffsetX || 0) * map.imageScale,
    y: (map.gridOffsetY || 0) * map.imageScale,
  });
  const props = () => {
    const g = grid(),
      view = board.viewport() || { x: 0, y: 0, scale: 1 };
    return {
      tokens: rows,
      walls: state.walls.map((w) => ({
        ...w,
        x1: w.x1 - g.x,
        y1: w.y1 - g.y,
        x2: w.x2 - g.x,
        y2: w.y2 - g.y,
      })),
      viewport: {
        ...view,
        x: view.x + g.x * view.scale,
        y: view.y + g.y * view.scale,
      },
      containerId: campaign,
      blockId: map.blockId,
      mapId: map.id,
      systemId: "gravewright-pdf-system",
      scene: map,
      gm,
      cell: g.cell,
      width: Math.max(0, map.width - g.x),
      height: Math.max(0, map.height - g.y),
      grid: map.gridVisible,
      dynamic: state.lighting.mode === "dynamic",
      measureValue: map.measureValue,
      measureUnit: map.measureUnit,
      tool: ["game", "gm"].includes(getPath("_layer"))
        ? getPath("_tool")
        : "inactive",
    };
  };
  async function read() {
    const revision = ++readRevision;
    const r = await fetch(`/api/containers/${campaign}/maps/${map.id}/tokens`, {
      cache: "no-store",
    });
    if (!r.ok) throw Error("Tokens unavailable.");
    const value = await r.json();
    if (!closed && revision === readRevision) {
      rows = value.tokens;
      controller.update({ tokens: rows });
    }
    return rows;
  }
  const command = (action, data) =>
    window.gravewrightRealtime.resourceCommand("tokens", action, {
      ...data,
      mapId: map.id,
    });
  controller = tokenController(svg, {
    props: props(),
    repaint,
    read,
    command,
    emit(type, ...args) {
      if (closed) return;
      if (type === "motion")
        window.gravewrightRealtime.tokenDrag({ mapId: map.id, ...args[0] });
      if (type === "hover") hover = args[0];
      if (type === "changed") {
        rows = args[0];
        controller?.update({ tokens: rows });
      }
      if (type === "ping") {
        const g = grid();
        window.gravewrightMaps.ping(
          { x: args[0].x + g.x, y: args[0].y + g.y },
          args[1],
        );
      }
      if (type === "refresh") window.gravewrightRealtime.mapLayers(map.id);
      repaint();
    },
  });
  function dialog(v) {
    const key = v.editor
      ? `${v.editor.mode}:${v.editor.tokens.map((t) => t.id).join(":")}`
      : "";
    if (key !== editorKey) {
      editor?.remove();
      editor = undefined;
      editorKey = key;
      if (v.editor) {
        editor = clone("token-editor");
        const mode = v.editor.mode,
          t = v.editor.tokens[0],
          el = editor,
          form = el.querySelector("form"),
          f = form.elements,
          scale = map.measureValue || 1;
        const title =
          mode === "vision"
            ? "Token vision"
            : mode === "conditions"
              ? "Conditions"
              : "Configure token";
        el.setAttribute("aria-label", title);
        el.querySelector("header strong").textContent = title;
        el.querySelector("header button").onclick = () =>
          controller.call("closeEditor");
        for (const section of el.querySelectorAll("[data-mode]"))
          section.hidden = section.dataset.mode !== mode;
        el.querySelector("[data-token-name]").textContent =
          v.editor.tokens.length > 1
            ? `${v.editor.tokens.length} tokens selecionados`
            : t.name;
        el.querySelector(".token-editor__notice").hidden =
          state.lighting.mode === "dynamic";
        el.querySelector("[data-range-label]").textContent =
          `Range (${map.measureUnit || "units"})`;
        f.enabled.checked = t.visionEnabled !== false;
        f.range.max = Math.max(60 * scale, (t.visionRange || 0) * scale);
        f.range.step = scale;
        f.range.value = (t.visionRange || 0) * scale;
        const range = () => {
          el.querySelector("output").textContent = Number(f.range.value)
            ? `${Number(Number(f.range.value).toFixed(4))} ${map.measureUnit}`
            : "Unlimited";
          f.unlimited.checked = Number(f.range.value) === 0;
        };
        f.range.oninput = range;
        f.unlimited.onchange = () => {
          f.range.value = Number(f.range.value) === 0 ? 8 * scale : 0;
          range();
        };
        range();
        f.rotation.value = t.rotation || 0;
        f.elevation.value = t.elevation || 0;
        f.locked.checked = !!t.locked;
        f.disposition.value = t.disposition || "neutral";
        el.querySelector("[data-token-size]").textContent =
          `Size: ${t.cells} × ${t.heightCells ?? t.cells} cells. Defined by the system's character sheet.`;
        for (const c of t.conditions || []) {
          const li = document.createElement("li"),
            span = document.createElement("span"),
            b = document.createElement("button");
          span.textContent = c.label;
          b.type = "button";
          b.setAttribute("aria-label", "Remove " + c.label);
          b.append(icon("Trash"));
          b.onclick = () =>
            controller.call(
              "command",
              "condition-remove",
              { conditionId: c.condition_id },
              v.editor.tokens.map((t) => t.id),
            );
          li.append(span, b);
          el.querySelector("ul").append(li);
        }
        f.label.required = mode === "conditions";
        f.rotation.required = mode === "configure";
        f.elevation.required = mode === "configure";
        form.onsubmit = (e) => {
          e.preventDefault();
          const values =
            mode === "vision"
              ? {
                  enabled: f.enabled.checked,
                  range: Number(f.range.value) / scale,
                }
              : mode === "configure"
                ? {
                    expectedVersion: t.version,
                    values: {
                      rotation: Number(f.rotation.value),
                      elevation: Number(f.elevation.value),
                      locked: f.locked.checked,
                      disposition: f.disposition.value,
                    },
                  }
                : {
                    label: f.label.value,
                    kind: f.kind.value,
                    visibility: f.visibility.value,
                  };
          controller.call(
            "command",
            mode === "conditions" ? "condition-add" : mode,
            values,
            v.editor.tokens.map((t) => t.id),
          );
        };
        el.onkeydown = (e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            controller.call("closeEditor");
          }
        };
        document.body.append(el);
      }
    }
    if (editor) {
      editor.querySelector("fieldset").disabled = v.busy;
      const p = editor.querySelector("[role=alert]");
      p.hidden = !v.error;
      p.textContent = v.error;
      editor.querySelector("[type=submit]").textContent = v.busy
        ? "Saving…"
        : v.editor.mode === "conditions"
          ? "Add"
          : "Save";
    }
    if (v.confirm && !confirmation) {
      confirmation = clone("token-confirm");
      confirmation.querySelector("[data-cancel]").onclick = () =>
        controller.call("closeConfirm");
      confirmation.querySelector("[data-remove]").onclick = () =>
        controller.call("command", "remove");
      document.body.append(confirmation);
    }
    if (!v.confirm) {
      confirmation?.remove();
      confirmation = undefined;
    }
    if (confirmation) {
      confirmation.querySelector("strong").textContent =
        `Remove ${v.selected.length} token(s) from this scene?`;
      confirmation.querySelector("[data-remove]").disabled = v.busy;
    }
    if (v.sheet?.id !== sheetId) {
      const previousSheet = sheet;
      sheet = undefined;
      sheetId = v.sheet?.id;
      previousSheet?.close();
      if (v.sheet)
        sheet = openSheet(campaign, v.sheet.actorId, v.sheet, gm, () => {
          if (sheetId !== v.sheet.id) return;
          sheetId = undefined;
          sheet = undefined;
          if (!closed) controller.call("closeSheet");
        });
    }
    const ckey = v.context;
    if (ckey !== contextKey) {
      contextKey = ckey;
      menu?.remove();
      if (v.context) {
        const t = v.context.token,
          items = [];
        const item = (glyph, label, run, disabled = false, danger = false) =>
          items.push({
            icon: glyph,
            label,
            run: () => {
              controller.call("closeContext");
              return run();
            },
            disabled,
            danger,
          });
        if (v.selection.length === 1 && t.canOpenSheet)
          item("BookOpenText", "Open character sheet", () =>
            controller.call("openSheet", t),
          );
        if (gm) {
          item(
            t.hidden ? "Eye" : "EyeSlash",
            (t.hidden ? "Reveal" : "Hide") + " selection",
            () => controller.call("command", "hidden", { hidden: !t.hidden }),
          );
          item("Eye", "Vision", () => controller.call("edit", "vision"));
          if (v.selection.length === 1)
            item("Gear", "Configure", () =>
              controller.call("edit", "configure"),
            );
          item("Heart", "Conditions", () =>
            controller.call("edit", "conditions"),
          );
          item("Copy", "Copy", () => controller.call("copy"));
          item(
            "Clipboard",
            "Paste copy",
            () => controller.call("paste"),
            !v.clipboard.length,
          );
          item(
            "Trash",
            "Remove from scene",
            () => controller.call("remove"),
            false,
            true,
          );
        }
        item(
          "ArrowCounterClockwise",
          "Undo movement",
          () => controller.call("history", true),
          !v.undo.length || v.busy,
        );
        item(
          "ArrowClockwise",
          "Redo movement",
          () => controller.call("history", false),
          !v.redo.length || v.busy,
        );
        menu = context(
          {
            clientX: v.context.x,
            clientY: v.context.y,
            preventDefault() {},
            stopPropagation() {},
          },
          items,
          "Token actions",
        );
      }
    }
  }
  function mixedSelection({detail}) {controller.call('select',detail.ids);}
  function mixedPreview({detail}) {selectionPreview=detail;repaint();}
  window.addEventListener('gravewright:mixed-selection',mixedSelection);
  window.addEventListener('gravewright:selection-preview',mixedPreview);
  function paint() {
    const selection = [...controller.view.selected];
    const changed = JSON.stringify(selection) !== JSON.stringify(window.gravewrightTokenSelection);
    window.gravewrightTokenSelection = selection;
    window.gravewrightTokenState = {tokens: rows};
    if (changed) window.dispatchEvent(new CustomEvent('gravewright:token-selection'));
    const v = controller.view,
      p = props(),
      g = grid(),
      view = p.viewport,
      scale = view.scale;
    svg.classList.toggle("token-workspace--pass", !v.interactive);
    svg.classList.toggle("token-workspace--routing", !!v.route.length);
    const group = node("g", {
      transform: `translate(${view.x} ${view.y}) scale(${scale})`,
    });
    for (const stored of v.displayed) {
      let t=stored;
      if(selectionPreview?.objects.some(o=>o.key==='token:'+stored.id)){
        const {center,dx,dy,angle}=selectionPreview,a=angle*Math.PI/180;
        const x=g.x+(stored.gridX+stored.cells/2)*g.cell-center.x;
        const y=g.y+(stored.gridY+(stored.heightCells??stored.cells)/2)*g.cell-center.y;
        t={...stored,gridX:(center.x+x*Math.cos(a)-y*Math.sin(a)+dx-g.x)/g.cell-stored.cells/2,
          gridY:(center.y+x*Math.sin(a)+y*Math.cos(a)+dy-g.y)/g.cell-(stored.heightCells??stored.cells)/2,rotation:(stored.rotation||0)+angle};
      }
      const r = node("rect", {
        x: t.gridX * g.cell,
        y: t.gridY * g.cell,
        width: t.cells * g.cell,
        height: (t.heightCells ?? t.cells) * g.cell,
        fill: "transparent",
        role: "button",
        tabindex: 0,
        "aria-label": "Token: " + t.name,
        "aria-pressed": String(v.selected.includes(t.id)),
      });
      r.onkeydown = (e) => {
        if (e.key === "Enter" && t.canOpenSheet) {
          e.preventDefault();
          e.stopPropagation();
          controller.call("openSheet", t);
        }
      };
      group.append(r);
    }
    for (const t of v.destinations)
      group.append(
        node("rect", {
          class: "token-workspace__destination",
          x: t.gridX * g.cell,
          y: t.gridY * g.cell,
          width: t.cells * g.cell,
          height: (t.heightCells ?? t.cells) * g.cell,
          fill: "#c09a5a0d",
          stroke: "#c09a5a",
          "stroke-width": 1 / scale,
          "stroke-dasharray": `${5 / scale} ${3 / scale}`,
          "pointer-events": "none",
        }),
      );
    const distance = (n) =>
      `${Number(n.toFixed(2)).toLocaleString("en-US")} ${map.measureUnit || "units"}`;
    if (v.route.length) {
      const route = node("g", {
        class: "token-workspace__route",
        "pointer-events": "none",
      });
      route.append(
        node("polyline", {
          points: v.routeLine,
          fill: "none",
          stroke: "#e9c46a",
          "stroke-width": 2 / scale,
        }),
      );
      if (v.suggestedLine)
        route.append(
          node("polyline", {
            points: v.suggestedLine,
            class: "token-workspace__suggested",
            fill: "none",
            stroke: "#7bdcb5",
            "stroke-width": 2 / scale,
            "stroke-dasharray": `${8 / scale} ${5 / scale}`,
          }),
        );
      for (const s of v.routeMeasurement.segments)
        route.append(
          node(
            "text",
            {
              class: "token-workspace__route-distance",
              x: s.x * g.cell,
              y: s.y * g.cell - 13 / scale,
              "font-size": 13 / scale,
              "stroke-width": 5 / scale,
              "text-anchor": "middle",
            },
            distance(s.distance),
          ),
        );
      v.route.slice(1).forEach((step, i) => {
        const t = step[0],
          point = node("g", {
            transform: `translate(${(t.gridX + t.cells / 2) * g.cell} ${(t.gridY + (t.heightCells ?? t.cells) / 2) * g.cell})`,
          });
        point.append(
          node("circle", {
            r: 10 / scale,
            fill: "#171d23",
            stroke: "#e9c46a",
            "stroke-width": 1 / scale,
          }),
          node(
            "text",
            {
              fill: "#e9c46a",
              "text-anchor": "middle",
              "dominant-baseline": "central",
              "font-size": 11 / scale,
            },
            i + 1,
          ),
        );
        route.append(point);
      });
      const t = v.routeEnd;
      if (t) {
        const summary = node("g", {
          transform: `translate(${(t.gridX + t.cells / 2) * g.cell} ${(t.gridY + (t.heightCells ?? t.cells) / 2) * g.cell}) scale(${1 / scale})`,
        });
        summary.append(
          node(
            "text",
            {
              x: 21,
              y: -13,
              class: "token-workspace__route-distance",
              "font-size": 13,
              "stroke-width": 5,
            },
            "Your route: " + distance(v.routeMeasurement.total),
          ),
        );
        if (v.suggestedMeasurement) {
          summary.append(
            node(
              "text",
              {
                x: 21,
                y: 8,
                class:
                  "token-workspace__route-distance token-workspace__route-distance--suggested",
                "font-size": 13,
                "stroke-width": 5,
              },
              "Suggested: " + distance(v.suggestedMeasurement.total),
            ),
            node(
              "text",
              {
                x: 21,
                y: 29,
                class:
                  "token-workspace__route-distance token-workspace__route-distance--suggested",
                "font-size": 11,
                "stroke-width": 5,
              },
              v.routeMeasurement.total > v.suggestedMeasurement.total
                ? "Save " + distance(v.routeMeasurement.total - v.suggestedMeasurement.total)
                : "Route avoids walls",
            ),
          );
          const foreign = node("foreignObject", {
              x: 21,
              y: 37,
              width: 200,
              height: 34,
              class: "token-workspace__route-action",
            }),
            button = document.createElement("button");
          button.className = "token-workspace__use-route";
          button.textContent = "Use suggested route";
          button.onpointerdown = (e) => {
            e.preventDefault();
            e.stopPropagation();
          };
          button.onclick = (e) => {
            e.stopPropagation();
            controller.call("useSuggestedRoute");
          };
          foreign.append(button);
          summary.append(foreign);
        }
        route.append(summary);
      }
      group.append(route);
    }
    if (v.marquee) {
      const a = v.marquee.from,
        b = v.marquee.to;
      group.append(
        node("rect", {
          x: Math.min(a.x, b.x),
          y: Math.min(a.y, b.y),
          width: Math.abs(a.x - b.x),
          height: Math.abs(a.y - b.y),
          fill: "#c09a5a22",
          stroke: "#c09a5a",
          "stroke-width": 1 / scale,
        }),
      );
    }
    const fragment = document.createDocumentFragment();
    fragment.append(group);
    patchSVG(svg, fragment);
    status.hidden = !(v.error || v.busy || v.route.length);
    status.setAttribute("role", v.error ? "alert" : "status");
    status.textContent =
      v.error ||
      (v.walking
        ? "Following the route…"
        : v.route.length
          ? (v.routeBlocked ? "This route crosses a wall. Choose a suggested route or change the points. " : "") + "Ctrl+click adds points. Hold Ctrl to choose a suggestion; release to walk. Esc cancels."
          : "Saving…");
    const pieces = v.displayed.map((t) => ({
      key: t.id,
      x: g.x + (t.gridX + t.cells / 2) * g.cell,
      y: g.y + (t.gridY + (t.heightCells ?? t.cells) / 2) * g.cell,
      size: t.cells * g.cell,
      height: (t.heightCells ?? t.cells) * g.cell,
      label: t.name,
      imageUrl: t.imageUrl,
      accent:
        {
          friendly: "#79c39a",
          hostile: "#e17b7b",
          neutral: "#c09a5a",
          unknown: "#a9a193",
        }[t.disposition] || "#c09a5a",
      rotation: t.rotation,
      hidden: t.hidden,
      selected: v.selected.includes(t.id),
      hovered: hover === t.id,
      bars: t.bars,
      conditions: t.conditions,
    }));
    const preview =
      gm &&
      v.interactive &&
      v.selected.length > 0 &&
      state.lighting.mode === "dynamic";
    const vision = v.displayed
      .filter(
        (t) =>
          t.visionEnabled !== false &&
          (preview ? v.selected.includes(t.id) : !gm && t.canControl),
      )
      .map((t) => ({
        x: g.x + (t.gridX + t.cells / 2) * g.cell,
        y: g.y + (t.gridY + (t.heightCells ?? t.cells) / 2) * g.cell,
        radius: (t.visionRange || 0) * g.cell,
        elevation: t.elevation || 0,
      }));
    const presentation = {
      pieces,
      tokenPresentation: {
        vision: gm && !preview ? state.vision : vision,
        previewTokenVision: preview,
      },
    };
    const key = JSON.stringify(presentation);
    if (key !== lastRender) {
      lastRender = key;
      board.update(presentation);
    }
    dialog(v);
  }
  const motion = (e) => controller.receiveMotion(e.detail),
    snapshot = (e) => {
      if (e.detail.mapId !== map.id) return;
      readRevision++;
      rows = e.detail.tokens;
      controller.update({ tokens: rows });
    },
    layers = (e) => {
      if (e.detail.sceneId !== map.id) return;
      state = e.detail;
      controller.update(props());
    },
    viewport = () => controller.update({ viewport: props().viewport });
  const focusToken=({detail})=>{
    const token=rows.find(row=>row.id===detail.id);if(!token)return;
    const g=grid();board.ping({x:g.x+(token.gridX+token.cells/2)*g.cell,y:g.y+(token.gridY+(token.heightCells||token.cells)/2)*g.cell},true);
  };
  window.addEventListener('gravewright:focus-token',focusToken);
  window.addEventListener("gravewright:token.drag", motion);
  window.addEventListener("gravewright:tokens.state", snapshot);
  window.addEventListener("gravewright:map-layers", layers);
  window.addEventListener("gravewright:map-viewport", viewport);
  const observer = new MutationObserver(() =>
    controller.update({ tool: props().tool }),
  );
  observer.observe(document.getElementById("table-workspace"), {
    attributes: true,
    attributeFilter: ["data-table-layer"],
  });
  const click = () => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      if (!closed) controller.update({ tool: props().tool });
    });
  };
  window.addEventListener("click", click);
  function dragover(e) {
    if (
      gm &&
      e.dataTransfer.types.includes("application/x-gravewright-actor")
    ) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    }
  }
  async function drop(e) {
    const raw = e.dataTransfer.getData("application/x-gravewright-actor");
    if (!gm || !raw) return;
    e.preventDefault();
    e.stopPropagation();
    try {
      const a = JSON.parse(raw);
      if (!a.actorId) return;
      const point = board.worldAt({ x: e.clientX, y: e.clientY }),
        g = grid(),
        snap = (v) => (map.gridVisible ? Math.round(v) : v);
      await command("place", {
        actorId: a.actorId,
        gridX: Math.max(0, snap((point.x - g.x) / g.cell)),
        gridY: Math.max(0, snap((point.y - g.y) / g.cell)),
      });
    } catch (error) {
      status.hidden = false;
      status.textContent = error.message;
      status.setAttribute("role", "alert");
    }
  }
  const stopForeign = onForeignDrop((event) => {
    if (
      !gm ||
      event.subject.kind !== "actor" ||
      event.subject.folder ||
      event.surface !== "board"
    )
      return;
    const point = board.worldAt({ x: event.x, y: event.y }),
      g = grid(),
      snap = (v) => (map.gridVisible ? Math.round(v) : v);
    command("place", {
      actorId: event.subject.id,
      gridX: Math.max(0, snap((point.x - g.x) / g.cell)),
      gridY: Math.max(0, snap((point.y - g.y) / g.cell)),
    }).catch((error) => {
      status.hidden = false;
      status.textContent = error.message;
      status.setAttribute("role", "alert");
    });
  });
  surface.addEventListener("dragover", dragover);
  surface.addEventListener("drop", drop);
  window.gravewrightRealtime.tokensSubscribe(map.id);
  read().catch((e) => {
    status.hidden = false;
    status.textContent = e.message;
  });
  return {
    setMap(next) {
      map = next;
      controller.update(props());
    },
    update(next) {
      state = next;
      controller.update(props());
    },
    destroy() {
      if (closed) return;
      closed = true;
      window.removeEventListener('gravewright:mixed-selection',mixedSelection);
      window.removeEventListener('gravewright:selection-preview',mixedPreview);
      stopForeign();
      cancelAnimationFrame(frame);
      controller.destroy();
      observer.disconnect();
      window.gravewrightRealtime.tokensSubscribe(null);
      for (const [name, fn] of [
        ["gravewright:focus-token", focusToken],
        ["gravewright:token.drag", motion],
        ["gravewright:tokens.state", snapshot],
        ["gravewright:map-layers", layers],
        ["gravewright:map-viewport", viewport],
        ["click", click],
      ])
        window.removeEventListener(name, fn);
      surface.removeEventListener("dragover", dragover);
      surface.removeEventListener("drop", drop);
      svg.remove();
      status.remove();
      editor?.remove();
      confirmation?.remove();
      menu?.remove();
      sheet?.close();
    },
  };
}
