// gravewright/maps/frontend/shared/config/i18n/text.js
var listeners = /* @__PURE__ */ new Set();
function notifyTextChange() {
  for (const listener of listeners)
    listener();
}
var currentLocale = () => "en";
var formats = /* @__PURE__ */ new Map();
function formatNumber(value) {
  const locale = currentLocale();
  let format = formats.get(locale);
  if (!format) {
    format = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
    formats.set(locale, format);
  }
  return format.format(value);
}
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
    const translated2 = detail.messages?.text?.[source];
    return typeof translated2 === "string" ? translated2 : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
}

// gravewright/maps/frontend/features/drawing/model/drawing.js
function bounds(row) {
  const xs = row.points.map((p) => p.x), ys = row.points.map((p) => p.y), pad = row.width / 2 + 2;
  const x = Math.min(...xs), y = Math.min(...ys);
  return { x: x - pad, y: y - pad, width: Math.max(1, Math.max(...xs) - x, row.kind === "text" ? row.text.length * row.fontSize * 0.65 : 0) + pad * 2, height: Math.max(1, Math.max(...ys) - y, row.kind === "text" ? row.fontSize * 1.3 : 0) + pad * 2 };
}
function translated(row, dx, dy) {
  return { ...row, points: row.points.map((p) => ({ x: p.x + dx, y: p.y + dy })) };
}
function arrowHead(row) {
  const a = row.points[0], b = row.points.at(-1), angle = Math.atan2(b.y - a.y, b.x - a.x), size = Math.max(13, row.width * 3);
  return [-0.5, 0.5].map((offset) => ({ x: b.x - Math.cos(angle + offset) * size, y: b.y - Math.sin(angle + offset) * size }));
}
function path(row) {
  const a = row.points[0], b = row.points.at(-1);
  if (row.kind === "rect")
    return `M${a.x},${a.y}H${b.x}V${b.y}H${a.x}Z`;
  if (row.kind === "ellipse") {
    const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2, cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2;
    return `M${cx - rx},${cy}a${rx},${ry} 0 1,0 ${rx * 2},0a${rx},${ry} 0 1,0 ${-rx * 2},0`;
  }
  let d = row.points.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ");
  if (row.points.length === 1)
    d += `l0.01,0`;
  if (row.kind === "arrow")
    d += arrowHead(row).map((p) => `M${b.x},${b.y}L${p.x},${p.y}`).join("");
  return d;
}
function hit(row, p, tolerance) {
  const origin = row.points[0], r = -(row.rotation ?? 0) * Math.PI / 180, dx = p.x - origin.x, dy = p.y - origin.y;
  p = { x: origin.x + dx * Math.cos(r) - dy * Math.sin(r), y: origin.y + dx * Math.sin(r) + dy * Math.cos(r) };
  const a = row.points[0], b = row.points.at(-1), box = bounds(row), t = tolerance + row.width / 2;
  if (p.x < box.x - t || p.y < box.y - t || p.x > box.x + box.width + t || p.y > box.y + box.height + t)
    return false;
  if (row.kind === "text")
    return true;
  if (row.kind === "ellipse") {
    const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2;
    if (rx < 1 || ry < 1)
      return false;
    const r2 = Math.hypot((p.x - (a.x + b.x) / 2) / rx, (p.y - (a.y + b.y) / 2) / ry);
    return row.fill !== "none" ? r2 <= 1 + t / Math.min(rx, ry) : Math.abs(r2 - 1) <= t / Math.min(rx, ry);
  }
  if (row.kind === "rect" && row.fill !== "none")
    return true;
  const points = row.kind === "rect" ? [a, { x: b.x, y: a.y }, b, { x: a.x, y: b.y }, a] : row.points;
  if (points.length === 1)
    return Math.hypot(p.x - a.x, p.y - a.y) <= t;
  return points.slice(1).some((q, i) => {
    const o = points[i], dx2 = q.x - o.x, dy2 = q.y - o.y, n = dx2 * dx2 + dy2 * dy2, k = n ? Math.max(0, Math.min(1, ((p.x - o.x) * dx2 + (p.y - o.y) * dy2) / n)) : 0;
    return Math.hypot(p.x - o.x - k * dx2, p.y - o.y - k * dy2) <= t;
  });
}

// gravewright/maps/frontend/features/selection/model/objects.js
function rotate(p, c, degrees) {
  const a = degrees * Math.PI / 180, dx = p.x - c.x, dy = p.y - c.y;
  return { x: c.x + dx * Math.cos(a) - dy * Math.sin(a), y: c.y + dx * Math.sin(a) + dy * Math.cos(a) };
}
function transformedPoint(p, center, dx, dy, rotation) {
  const q = rotate(p, center, rotation);
  return { x: q.x + dx, y: q.y + dy };
}
function corners(o) {
  return [{ x: o.x - o.width / 2, y: o.y - o.height / 2 }, { x: o.x + o.width / 2, y: o.y - o.height / 2 }, { x: o.x + o.width / 2, y: o.y + o.height / 2 }, { x: o.x - o.width / 2, y: o.y + o.height / 2 }].map((p) => rotate(p, o, o.rotation));
}
function hit2(o, p, tolerance = 5) {
  if (o.kind === "drawing")
    return hit(o.data, p, tolerance);
  if (o.kind === "measure") {
    const m = o.data, q2 = rotate(p, m.origin, -m.direction), x = q2.x - m.origin.x, y = q2.y - m.origin.y;
    if (m.kind === "circle")
      return Math.hypot(x, y) <= m.length + tolerance;
    if (m.kind === "line")
      return x >= -tolerance && x <= m.length + tolerance && Math.abs(y) <= tolerance;
    if (m.kind === "rect")
      return x >= -tolerance && y >= -tolerance && x <= m.length + tolerance && y <= m.width + tolerance;
    if (m.kind === "cone")
      return x >= -tolerance && x <= m.length + tolerance && Math.abs(y) <= Math.max(0, x) * Math.tan(m.angle * Math.PI / 360) + tolerance;
    const r = Math.min(m.width / 2, m.length * 0.49), c = m.length - r, tx = c - r * r / c, ty = r * Math.sqrt(1 - r * r / (c * c));
    return x <= tx ? x >= -tolerance && Math.abs(y) <= x * ty / Math.max(0.01, tx) + tolerance : Math.hypot(x - c, y) <= r + tolerance;
  }
  if (o.kind === "wall") {
    const a = o.points[0], b = o.points[1], dx = b.x - a.x, dy = b.y - a.y, n = dx * dx + dy * dy, t = n ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / n)) : 0;
    return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy) <= tolerance;
  }
  const q = rotate(p, o, -o.rotation);
  return Math.abs(q.x - o.x) <= o.width / 2 + tolerance && Math.abs(q.y - o.y) <= o.height / 2 + tolerance;
}
function centerOf(rows) {
  const points = rows.flatMap(corners);
  return { x: (Math.min(...points.map((p) => p.x)) + Math.max(...points.map((p) => p.x))) / 2, y: (Math.min(...points.map((p) => p.y)) + Math.max(...points.map((p) => p.y))) / 2 };
}
function sceneObjects(state, tokens, cell, gm, measures, origin = { x: 0, y: 0 }) {
  const out = [];
  function add(kind, data, x, y, width = 18, height = 18, rotation = 0, rank = 10, label = kind, points) {
    out.push({ key: `${kind}:${data.id}`, id: data.id, kind, data, x, y, width, height, rotation, rank, label, points });
  }
  for (const t of tokens.filter((t2) => gm || t2.canControl))
    add("token", t, origin.x + (t.gridX + t.cells / 2) * cell, origin.y + (t.gridY + (t.heightCells ?? t.cells) / 2) * cell, t.cells * cell, (t.heightCells ?? t.cells) * cell, 0, 30, t.name);
  for (const c of state.cards.filter((c2) => c2.can_manage))
    add("card", c, c.x, c.y, 56 * c.scale, 80 * c.scale, c.rotation, 25, c.card?.face_state === "face_up" ? c.card?.name || text("Card") : text("Card (back)"));
  if (gm) {
    for (const i of state.images)
      add("image", i, i.x, i.y, i.natural_width * i.scale, i.natural_height * i.scale, i.rotation, 5, text("Image"));
    for (const w of state.walls)
      add("wall", w, (w.x1 + w.x2) / 2, (w.y1 + w.y2) / 2, Math.hypot(w.x2 - w.x1, w.y2 - w.y1), 4, Math.atan2(w.y2 - w.y1, w.x2 - w.x1) * 180 / Math.PI, 15, text("Wall"), [{ x: w.x1, y: w.y1 }, { x: w.x2, y: w.y2 }]);
    for (const [kind, list] of [["light", state.lights], ["particle", state.particles], ["shader", state.shaders], ["sound", state.spatialSounds]])
      for (const o of list)
        add(kind, o, o.x, o.y, 18, 18, 0, 35, { get light() {
          return text("Light");
        }, get particle() {
          return text("Particles");
        }, shader: "Shader", get sound() {
          return text("Audio");
        } }[kind]);
    for (const d of state.drawings?.rows ?? []) {
      const b = bounds(d), anchor = d.points[0], center = rotate({ x: b.x + b.width / 2, y: b.y + b.height / 2 }, anchor, d.rotation ?? 0);
      add("drawing", d, center.x, center.y, b.width, b.height, d.rotation ?? 0, 10, text("Drawing"));
    }
    for (const z of state.zones) {
      const g = z.geometry, points = g.shape === "polygon" ? g.points ?? [] : g.shape === "rect" ? [{ x: g.x ?? 0, y: g.y ?? 0 }, { x: (g.x ?? 0) + (g.width ?? 0), y: (g.y ?? 0) + (g.height ?? 0) }] : [{ x: (g.x ?? 0) - (g.radius ?? 0), y: (g.y ?? 0) - (g.radius ?? 0) }, { x: (g.x ?? 0) + (g.radius ?? 0), y: (g.y ?? 0) + (g.radius ?? 0) }];
      if (!points.length)
        continue;
      const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
      add("zone", z, (Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2, Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 0, 4, text("Zone"));
    }
  }
  for (const m of measures) {
    let w = m.length, h = m.kind === "rect" ? m.width : m.kind === "cone" ? 2 * m.length * Math.tan(m.angle * Math.PI / 360) : m.kind === "wide-cone" ? m.width : 4;
    const local = m.kind === "circle" ? { x: 0, y: 0 } : { x: w / 2, y: m.kind === "rect" ? h / 2 : 0 };
    if (m.kind === "circle")
      w = h = 2 * m.length;
    const p = rotate({ x: m.origin.x + local.x, y: m.origin.y + local.y }, m.origin, m.direction);
    add("measure", m, p.x, p.y, w, h, m.direction, 12, text("Measurement"));
  }
  return out.sort((a, b) => a.rank - b.rank);
}

// gravewright/maps/frontend/features/selection/model/selection-commands.js
async function applySelection(api, tokens, container, block, map, cell, state, objects, action, center, dx = 0, dy = 0, angle = 0, origin = { x: 0, y: 0 }) {
  const failed = [], done = [];
  const drawings = objects.filter((o) => o.kind === "drawing");
  const point = (p) => transformedPoint(p, center, dx, dy, angle);
  const command = (area2, action2, data) => api.command(container, block, area2, action2, data);
  for (const o of objects.filter((o2) => !["drawing", "measure"].includes(o2.kind))) {
    const d = o.data, p = point(o);
    try {
      if (["hide", "show"].includes(action)) {
        if (o.kind !== "image") continue;
        await command("images", "update", { placement_id: o.id, layer: action === "hide" ? "gm" : "game", expected_version: d.version });
      } else if (action === "flip") {
        if (o.kind !== "card") continue;
        await command("cards", "update", { placement_id: o.id, expected_version: d.version, face_state: d.card?.face_state === "face_up" ? "face_down" : "face_up" });
      } else if (o.kind === "token") {
        if (action === "delete") await tokens.remove(container, o.id);
        else {
          let version = d.version;
          if (dx || dy || angle) {
            const next = await tokens.move(container, o.id, { gridX: (p.x - origin.x) / cell - d.cells / 2, gridY: (p.y - origin.y) / cell - (d.heightCells ?? d.cells) / 2, expectedVersion: version });
            version = next.version;
          }
          if (angle) await tokens.command(container, map, "configure", { tokenIds: [o.id], expectedVersion: version, values: { rotation: (d.rotation ?? 0) + angle } });
        }
      } else if (o.kind === "image") await command("images", action === "delete" ? "delete" : "update", { placement_id: o.id, ...action === "delete" ? {} : { x: p.x, y: p.y, rotation: d.rotation + angle, expected_version: d.version } });
      else if (o.kind === "card") await command("cards", action === "delete" ? "delete" : "update", { placement_id: o.id, expected_version: d.version, ...action === "delete" ? {} : { x: p.x, y: p.y, rotation: d.rotation + angle } });
      else if (o.kind === "wall") {
        const a = point({ x: d.x1, y: d.y1 }), b = point({ x: d.x2, y: d.y2 });
        await command("walls", action === "delete" ? "delete" : "update", { wall_id: o.id, ...action === "delete" ? {} : { x1: a.x, y1: a.y, x2: b.x, y2: b.y } });
      } else if (["light", "particle", "shader"].includes(o.kind)) {
        await command(o.kind === "light" ? "light-selection" : "effects", action === "delete" ? "delete" : "transform", { effects: [{ kind: o.kind, id: o.id }], ...action === "delete" ? {} : { dx: p.x - o.x, dy: p.y - o.y, rotation: angle } });
      } else if (o.kind === "sound") await command("spatial-sounds", action === "delete" ? "delete" : "update", { rid: o.id, expected_version: d.version, ...action === "delete" ? {} : { patch: { x: p.x, y: p.y } } });
      else if (o.kind === "zone") {
        const g = d.geometry;
        let geometry;
        if (g.shape === "circle") geometry = { ...g, ...point({ x: g.x, y: g.y }) };
        else {
          const pts = g.shape === "polygon" ? g.points : [{ x: g.x, y: g.y }, { x: g.x + g.width, y: g.y }, { x: g.x + g.width, y: g.y + g.height }, { x: g.x, y: g.y + g.height }];
          geometry = { shape: "polygon", points: pts.map(point) };
        }
        await command("zones", action === "delete" ? "delete" : "update", { zone_id: o.id, expected_version: d.version, ...action === "delete" ? {} : { patch: { geometry } } });
      }
      done.push(o.key);
    } catch {
      failed.push(o.key);
    }
  }
  if (drawings.length && ["transform", "delete"].includes(action)) {
    const ids = new Set(drawings.map((d) => d.id));
    try {
      await command("drawings", "replace", { expected_version: state.drawings?.version ?? 0, rows: (state.drawings?.rows ?? []).filter((d) => action !== "delete" || !ids.has(d.id)).map((d) => {
        if (!ids.has(d.id)) return d;
        const a = d.points[0], next = point(a);
        return { ...d, points: d.points.map((p) => ({ x: p.x + next.x - a.x, y: p.y + next.y - a.y })), rotation: (d.rotation ?? 0) + angle };
      }) });
      done.push(...drawings.map((d) => d.key));
    } catch {
      failed.push(...drawings.map((d) => d.key));
    }
  }
  return { failed, done };
}
function transformMeasures(rows, ids, action, center, dx, dy, angle) {
  return rows.filter((m) => action !== "delete" || !ids.includes(m.id)).map((m) => ids.includes(m.id) ? { ...m, origin: transformedPoint(m.origin, center, dx, dy, angle), direction: m.direction + angle } : m);
}

// gravewright/maps/frontend/features/effects/model/effects.js
function defaults() {
  return { light_response: 0, light_emission: 0, bright_radius: 2, dim_radius: 4, angle: 360, animation: "none", x: 0, y: 0, kind: "smoke", scale: 3, density: 0.6, color: "#9aa3ad", enabled: true, rotation: 0, name: "Shader", source: "void main() { float a = 0.35 * uIntensity; finalColor = vec4(uColor * a, a); }", radius: 0, opacity: 1, intensity: 0.6, speed: 1, blend_mode: "normal" };
}
function effects(state, layer = "effects") {
  if (layer === "lighting")
    return state.lights.map((data) => ({ ...data, kind: "light", key: `light:${data.id}`, data: { ...defaults(), ...data, enabled: Boolean(data.enabled) } }));
  return [...state.particles.map((data) => ({ ...data, kind: "particle", data: { ...defaults(), ...data, enabled: Boolean(data.enabled) } })), ...state.shaders.map((data) => ({ ...data, kind: "shader", data: { ...defaults(), ...data, enabled: Boolean(data.enabled) } }))].map((e) => ({ ...e, key: `${e.kind}:${e.id}` }));
}
function hitEffect(items, point, scale) {
  return [...items].reverse().find((e) => Math.hypot(e.x - point.x, e.y - point.y) <= 13 / scale);
}
function inMarquee(items, from, to) {
  return items.filter((e) => e.x >= Math.min(from.x, to.x) && e.x <= Math.max(from.x, to.x) && e.y >= Math.min(from.y, to.y) && e.y <= Math.max(from.y, to.y)).map((e) => e.key);
}
function payload(kind, data) {
  const keys = kind === "light" ? "x y bright_radius dim_radius angle rotation animation intensity color enabled" : kind === "particle" ? "x y kind scale density color enabled rotation light_response light_emission" : "name source x y radius scale intensity opacity speed color rotation blend_mode enabled light_response light_emission";
  return Object.fromEntries(keys.split(" ").map((key) => [key, data[key]]));
}
function translatedCopies(items, at) {
  const center = { x: items.reduce((n, e) => n + e.x, 0) / items.length, y: items.reduce((n, e) => n + e.y, 0) / items.length };
  return items.map((e) => ({ kind: e.kind, data: payload(e.kind, { ...e.data, x: at.x + e.x - center.x, y: at.y + e.y - center.y }) }));
}

// gravewright/maps/frontend/features/selection/ui/selection-workspace.js
function createSelection(surface, board, map, gm, api, stateAPI, measurements) {
  const abort = new AbortController(), signal = abort.signal, svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("selection-workspace");
  svg.setAttribute("aria-label", "Scene object selection");
  surface.append(svg);
  const notice = document.createElement("p");
  notice.className = "selection-workspace__error";
  notice.hidden = true;
  surface.append(notice);
  let state = api.state, selected = [], drag, preview, busy = false, menu, dialog, timer, pingTimer, clipboard = [], lastPoint = { x: 0, y: 0 };
  const cell = () => map.gridSize * map.imageScale, origin = () => ({ x: (map.gridOffsetX || 0) * map.imageScale, y: (map.gridOffsetY || 0) * map.imageScale });
  const active = () => stateAPI.getPath("_tool") === "select" && !document.querySelector(".grid-calibration-panel") && document.querySelector("#table-workspace")?.dataset.role !== "streamer";
  const all = () => sceneObjects(state, window.gravewrightTokenState?.tokens || [], cell(), gm, measurements.rows(), origin());
  const chosen = () => all().filter((o) => selected.includes(o.key));
  const mixed = () => chosen().some((o) => o.kind !== "token");
  const point = (e) => {
    const b = surface.getBoundingClientRect(), v = board.viewport();
    return { x: (e.clientX - b.left - v.x) / v.scale, y: (e.clientY - b.top - v.y) / v.scale };
  };
  const pick = (p) => all().reverse().find((o) => hit2(o, p, 5 / board.viewport().scale));
  const stop = (e) => {
    e.preventDefault();
    e.stopImmediatePropagation();
  };
  function node(tag, attrs) {
    const n = document.createElementNS(svg.namespaceURI, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  }
  function paint() {
    svg.replaceChildren();
    if (!active()) return;
    const v = board.viewport();
    if (!v) return;
    const group = node("g", { transform: `translate(${v.x} ${v.y}) scale(${v.scale})` });
    svg.append(group);
    for (const o of all().filter((o2) => ["light", "particle", "shader", "sound"].includes(o2.kind))) group.append(node("circle", { cx: o.x, cy: o.y, r: 5 / v.scale, fill: o.kind === "sound" ? "#65c9b8" : "#cda5e8" }));
    for (const o of chosen()) {
      const points = corners(o).map((p) => preview ? transformedPoint(p, preview.center, preview.dx, preview.dy, preview.angle) : p).map((p) => `${p.x},${p.y}`).join(" ");
      group.append(node("polygon", { points, fill: "#e1b46608", stroke: "#ffe29a", "stroke-width": 1.5 / v.scale, "stroke-dasharray": `${5 / v.scale} ${3 / v.scale}`, "data-selected-object": o.key }));
    }
    if (drag && !drag.moving) {
      const a = drag.from, b = drag.to;
      group.append(node("rect", { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), width: Math.abs(a.x - b.x), height: Math.abs(a.y - b.y), fill: "#e1b46618", stroke: "#e1b466", "stroke-width": 1 / v.scale }));
    }
  }
  function publish() {
    const value = preview ? { ...preview, objects: drag?.objects || chosen() } : void 0;
    board.previewSelection?.(value);
    window.dispatchEvent(new CustomEvent("gravewright:selection-preview", { detail: value }));
    paint();
  }
  function select(keys) {
    selected = keys;
    window.dispatchEvent(new CustomEvent("gravewright:mixed-selection", { detail: { ids: chosen().filter((o) => o.kind === "token").map((o) => o.id), mixed: mixed() } }));
    paint();
  }
  function cancel() {
    clearTimeout(timer);
    clearTimeout(pingTimer);
    if (drag && surface.hasPointerCapture(drag.id)) surface.releasePointerCapture(drag.id);
    drag = void 0;
    preview = void 0;
    menu?.remove();
    menu = void 0;
    publish();
  }
  const ignored = (e) => e.target.closest("button,input,textarea,select,dialog,.gw-window,.directory-context-menu,.game-dock,.door-controls");
  function down(e) {
    if (!active() || busy || e.button !== 0 || ignored(e)) return;
    const p = point(e), o = pick(p);
    if (e.ctrlKey && !mixed() || o?.kind === "token" && !mixed() && !e.shiftKey) return;
    stop(e);
    cancel();
    notice.hidden = true;
    if (o) select(e.shiftKey ? selected.includes(o.key) ? selected.filter((k) => k !== o.key) : [...selected, o.key] : selected.includes(o.key) ? selected : [o.key]);
    else if (!e.shiftKey) select([]);
    drag = { id: e.pointerId, from: p, to: p, objects: chosen(), additive: [...selected], moving: !!o };
    surface.setPointerCapture(e.pointerId);
    if (!o) pingTimer = setTimeout(() => {
      if (drag) window.gravewrightMaps?.ping(p, e.shiftKey);
    }, 700);
    paint();
  }
  function move(e) {
    if (!active()) return;
    lastPoint = point(e);
    if (!drag || drag.id !== e.pointerId) return;
    stop(e);
    drag.to = lastPoint;
    if (Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) * board.viewport().scale > 10) clearTimeout(pingTimer);
    if (drag.moving) {
      preview = { center: centerOf(drag.objects), dx: lastPoint.x - drag.from.x, dy: lastPoint.y - drag.from.y, angle: 0 };
      publish();
    } else {
      const a = drag.from, b = lastPoint;
      select([.../* @__PURE__ */ new Set([...drag.additive, ...all().filter((o) => corners(o).every((p) => p.x >= Math.min(a.x, b.x) && p.x <= Math.max(a.x, b.x) && p.y >= Math.min(a.y, b.y) && p.y <= Math.max(a.y, b.y))).map((o) => o.key)])]);
    }
  }
  function up(e) {
    if (!drag || drag.id !== e.pointerId) return;
    move(e);
    stop(e);
    const t = preview;
    clearTimeout(pingTimer);
    if (surface.hasPointerCapture(e.pointerId)) surface.releasePointerCapture(e.pointerId);
    drag = void 0;
    if (t && Math.abs(t.dx) + Math.abs(t.dy) > 0.5) void execute("transform", t);
    else {
      preview = void 0;
      publish();
    }
  }
  const tokenCommand = (action, data) => window.gravewrightRealtime.resourceCommand("tokens", action, { ...data, mapId: map.id });
  const tokenApi = { remove: (_, id) => tokenCommand("remove", { tokenIds: [id] }), move: async (_, id, data) => {
    const result = await tokenCommand("move", { id, ...data });
    return result.tokens.find((t) => t.id === id);
  }, command: (_c, _m, action, data) => tokenCommand(action, data) };
  const adapter = { command: (_c, _b, area2, action, data) => ["cards", "spatial-sounds"].includes(area2) ? window.gravewrightTableMedia.areaCommand(area2, action, data) : api.command(area2, action, data) };
  async function execute(action, t = preview || { center: chosen().length ? centerOf(chosen()) : { x: 0, y: 0 }, dx: 0, dy: 0, angle: 0 }) {
    if (busy || !chosen().length) return;
    clearTimeout(timer);
    busy = true;
    menu?.remove();
    dialog?.close();
    notice.hidden = true;
    const rows = chosen();
    try {
      const result = await applySelection(adapter, tokenApi, map.containerId, map.blockId, map.id, cell(), state, rows, action, t.center, t.dx, t.dy, t.angle, origin());
      if (signal.aborted) return;
      if (["delete", "transform"].includes(action)) measurements.replace(transformMeasures(measurements.rows(), rows.filter((o) => o.kind === "measure").map((o) => o.id), action, t.center, t.dx, t.dy, t.angle));
      if (result.failed.length) {
        notice.textContent = `${result.failed.length} object(s) refused. Other changes were applied. Refreshing the scene\u2026`;
        notice.hidden = false;
        select(result.failed);
      } else if (action === "delete") select([]);
      await api.read();
    } catch (error) {
      if (!signal.aborted) {
        notice.textContent = error.message;
        notice.hidden = false;
      }
    } finally {
      busy = false;
      preview = void 0;
      if (!signal.aborted) publish();
    }
  }
  function rotate2(angle, defer = false) {
    if (busy || drag || !chosen().length) return;
    preview = { ...preview || { center: centerOf(chosen()), dx: 0, dy: 0, angle: 0 }, angle: (preview?.angle || 0) + angle };
    publish();
    clearTimeout(timer);
    if (defer) timer = setTimeout(() => void execute("transform"), 180);
    else void execute("transform");
  }
  function copy() {
    clipboard = [...effects(state), ...effects(state, "lighting")].filter((o) => selected.includes(o.key));
    menu?.remove();
  }
  async function paste() {
    if (!clipboard.length || busy) return;
    busy = true;
    try {
      for (const area2 of ["effects", "light-selection"]) {
        const rows = translatedCopies(clipboard, lastPoint).filter((o) => o.kind === "light" === (area2 === "light-selection"));
        if (rows.length) await api.command(area2, "paste", { effects: rows });
      }
      await api.read();
    } catch (error) {
      notice.textContent = error.message;
      notice.hidden = false;
    } finally {
      busy = false;
    }
  }
  function confirmDelete() {
    dialog?.remove();
    dialog = document.createElement("dialog");
    dialog.className = "directory-dialog";
    const form = document.createElement("form"), title = document.createElement("h3"), text2 = document.createElement("p"), remove = document.createElement("button"), close = document.createElement("button");
    title.textContent = "Remove scene objects";
    text2.textContent = `Remove ${chosen().length} object(s)? Cards go to the discard pile; actor and asset definitions are preserved.`;
    remove.textContent = "Remove selection";
    remove.type = "submit";
    close.textContent = "Cancel";
    close.type = "button";
    close.onclick = () => dialog.close();
    form.append(title, text2, close, remove);
    form.onsubmit = (e) => {
      e.preventDefault();
      void execute("delete");
    };
    dialog.append(form);
    document.body.append(dialog);
    dialog.onclose = () => dialog.remove();
    dialog.showModal();
  }
  function context(e) {
    if (!active() || ignored(e)) return;
    const o = pick(point(e));
    if (!o || o.kind === "token" && !mixed()) return;
    stop(e);
    cancel();
    lastPoint = point(e);
    if (!selected.includes(o.key)) select([o.key]);
    menu = document.createElement("menu");
    menu.className = "directory-context-menu gw-folder-menu";
    menu.style.position = "fixed";
    menu.style.left = `${e.clientX}px`;
    menu.style.top = `${e.clientY}px`;
    function add(label, fn) {
      const b = document.createElement("button");
      b.textContent = label;
      b.onclick = () => {
        menu?.remove();
        fn();
      };
      menu.append(b);
    }
    if (chosen().some((o2) => ["light", "particle", "shader"].includes(o2.kind))) add("Copy lights and effects", copy);
    if (clipboard.length) add("Paste lights and effects", () => void paste());
    if (chosen().length === 1 && !["image", "card", "zone"].includes(o.kind)) add("Edit", () => editObject(o, e));
    add("Rotate selection \u221290\xB0", () => rotate2(-90));
    add("Rotate selection +90\xB0", () => rotate2(90));
    if (chosen().some((o2) => o2.kind === "image")) {
      add("Hide images from players", () => void execute("hide"));
      add("Reveal images to players", () => void execute("show"));
    }
    if (chosen().some((o2) => o2.kind === "card")) add("Flip selected cards", () => void execute("flip"));
    add("Delete selection", confirmDelete);
    document.body.append(menu);
  }
  function editObject(object, event) {
    window.dispatchEvent(new CustomEvent("gravewright:selection-edit", { detail: { object, event } }));
  }
  function double(e) {
    if (!active() || ignored(e)) return;
    const o = pick(point(e));
    if (!o || o.kind === "token") return;
    stop(e);
    editObject(o, e);
  }
  function key(e) {
    if (!active() || e.target.closest?.("input,textarea,select,[contenteditable=true],.directory-dialog") || document.querySelector("dialog[open]")) return;
    const k = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && k === "a") {
      stop(e);
      select(all().map((o) => o.key));
    } else if (k === "escape" && (mixed() || drag || preview)) {
      stop(e);
      cancel();
      select([]);
    } else if ((e.ctrlKey || e.metaKey) && ["c", "v"].includes(k) && (clipboard.length || chosen().some((o) => ["light", "particle", "shader"].includes(o.kind)))) {
      stop(e);
      if (k === "c") copy();
      else void paste();
    } else if (k === "f" && chosen().length && chosen().every((o) => o.kind === "card")) {
      stop(e);
      void execute("flip");
    } else if (["delete", "backspace"].includes(k) && mixed()) {
      stop(e);
      confirmDelete();
    }
  }
  for (const [event, handler] of [["pointerdown", down], ["pointermove", move], ["pointerup", up], ["pointercancel", cancel], ["contextmenu", context], ["dblclick", double]]) surface.addEventListener(event, handler, { capture: true, signal });
  surface.addEventListener("wheel", (e) => {
    if (active() && e.shiftKey && chosen().length) {
      stop(e);
      rotate2(e.deltaY > 0 ? 15 : -15, true);
    }
  }, { capture: true, passive: false, signal });
  window.addEventListener("keydown", key, { capture: true, signal });
  window.addEventListener("blur", cancel, { signal });
  window.addEventListener("gravewright:token-selection", () => {
    if (!mixed()) select((window.gravewrightTokenSelection || []).map((id) => "token:" + id));
  }, { signal });
  window.addEventListener("gravewright:map-viewport", paint, { signal });
  return { update(next) {
    state = next;
    const valid = new Set(all().map((o) => o.key));
    selected = selected.filter((k) => valid.has(k));
    if (!active()) {
      cancel();
      selected = [];
    }
    paint();
  }, destroy() {
    abort.abort();
    cancel();
    dialog?.remove();
    svg.remove();
    notice.remove();
  } };
}

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
function model(options) {
  return { [CELL]: true, get value() {
    return options.props.modelValue;
  }, set value(v) {
    options.props.modelValue = v;
    options.emit("update:modelValue", v);
  } };
}
function widget(markup, setup) {
  return function mount2(host, initial) {
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

// gravewright/maps/frontend/features/drawing/ui/DrawingWorkspace.native.js
var PhCursor = "PhCursor";
var PhPencilSimple = "PhPencilSimple";
var PhLineSegment = "PhLineSegment";
var PhArrowUpRight = "PhArrowUpRight";
var PhRectangle = "PhRectangle";
var PhCircle = "PhCircle";
var PhTextT = "PhTextT";
var PhEraser = "PhEraser";
var PhArrowCounterClockwise = "PhArrowCounterClockwise";
var PhArrowClockwise = "PhArrowClockwise";
var PhTrash = "PhTrash";
var PhCopy = "PhCopy";
var PhClipboard = "PhClipboard";
var PhX = "PhX";
var DrawingWorkspace_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "drawing-workspace" }, "bind": { "class": "({ 'drawing-workspace--busy': busy })" }, "events": [{ "event": "pointerdown", "code": "down;", "mods": [] }, { "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }, { "event": "contextmenu", "code": "menu;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "(row.id)", "opacity": "(row.opacity)", "transform": "(`rotate(${row.rotation ?? 0} ${row.points[0].x} ${row.points[0].y})`)" }, "events": [{ "event": "dblclick", "code": "edit($event, row);", "mods": [] }], "children": [{ "tag": "text", "attrs": { "dominant-baseline": "text-before-edge", "font-family": "sans-serif", "style": "white-space:pre" }, "bind": { "x": "(row.points[0].x)", "y": "(row.points[0].y)", "fill": "(row.color)", "font-size": "(row.fontSize)" }, "events": [], "children": [{ "value": "(row.text)" }], "when": "(row.kind === 'text')" }, { "tag": "path", "attrs": { "stroke-linecap": "round", "stroke-linejoin": "round" }, "bind": { "d": "(path(row))", "stroke": "(row.color)", "stroke-width": "(row.width)", "fill": "(['rect', 'ellipse'].includes(row.kind) ? row.fill : 'none')" }, "events": [], "children": [], "otherwise": true }, { "tag": "rect", "attrs": { "fill": "none", "stroke": "#e1b466" }, "bind": { "stroke-width": "(1 / viewport.scale)", "stroke-dasharray": "(`${5 / viewport.scale} ${3 / viewport.scale}`)" }, "events": [], "children": [], "when": "(selected.includes(row.id))", "spread": "(bounds(row))" }], "each": { "names": ["row"], "value": "(visible)" } }, { "tag": "rect", "attrs": { "fill": "#e1b46622", "stroke": "#e1b466" }, "bind": { "x": "(Math.min(marquee.a.x, marquee.b.x))", "y": "(Math.min(marquee.a.y, marquee.b.y))", "width": "(Math.abs(marquee.b.x - marquee.a.x))", "height": "(Math.abs(marquee.b.y - marquee.a.y))", "stroke-width": "(1 / viewport.scale)" }, "events": [], "children": [], "when": "(marquee)" }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": { "class": "drawing-paint", "aria-label": "Mini Paint" }, "bind": {}, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "drawing-paint__header" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhPencilSimple", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "text": "Mini Paint " }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(audience === 'gm' ? gwText('GM only') : gwText('Table'))" }] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close drawing'))", "title": "(gwText('Close drawing'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "fieldset", "attrs": { "class": "drawing-paint__body" }, "bind": { "disabled": "(busy)" }, "events": [], "children": [{ "tag": "div", "attrs": { "class": "drawing-paint__tools" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(item.id)", "title": "(item.label)", "aria-label": "(item.label)", "aria-pressed": "(tool === item.id)" }, "events": [{ "event": "click", "code": "choose(item.id);", "mods": [] }], "children": [{ "tag": "component", "attrs": { "weight": "duotone" }, "bind": { "is": "(item.icon)" }, "events": [], "children": [] }], "each": { "names": ["item"], "value": "(tools)" } }] }, { "tag": "div", "attrs": { "class": "drawing-paint__palette" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(swatch)", "style": "({ background: swatch })", "aria-label": "(gwText('Color {0}', swatch))", "aria-pressed": "(color === swatch)" }, "events": [{ "event": "click", "code": "color = swatch;", "mods": [] }], "children": [], "each": { "names": ["swatch"], "value": "(palette)" } }, { "tag": "label", "attrs": {}, "bind": { "title": "(gwText('Custom color'))" }, "events": [], "children": [{ "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Stroke color'))" }, "events": [], "children": [], "model": { "path": "(color)", "mods": [] } }] }] }, { "tag": "div", "attrs": { "class": "drawing-paint__settings" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Stroke '))" }, { "tag": "input", "attrs": { "type": "range", "min": "1", "max": "64" }, "bind": {}, "events": [], "children": [], "model": { "path": "(width)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(width)" }, { "text": " px" }] }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Opacity '))" }, { "tag": "input", "attrs": { "type": "range", "min": "0.05", "max": "1", "step": "0.05" }, "bind": {}, "events": [], "children": [], "model": { "path": "(opacity)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(Math.round(opacity * 100))" }, { "text": "%" }] }] }] }, { "tag": "div", "attrs": { "class": "drawing-paint__fill" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "(filled)", "mods": [] } }, { "value": "(gwText('Fill shapes'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Fill color'))", "disabled": "(!filled)" }, "events": [], "children": [], "model": { "path": "(fill)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "drawing-paint__text" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "maxlength": "1000" }, "bind": { "placeholder": "(gwText('Type and click the map'))", "aria-label": "(gwText('Drawing text'))" }, "events": [], "children": [], "model": { "path": "(text)", "mods": [] } }, { "tag": "input", "attrs": { "type": "number", "min": "8", "max": "144" }, "bind": { "aria-label": "(gwText('Text size'))" }, "events": [], "children": [], "model": { "path": "(fontSize)", "mods": ["number"] } }], "when": "(tool === 'text' || rows.some(r => selected.includes(r.id) && r.kind === 'text'))" }, { "tag": "button", "attrs": { "class": "drawing-paint__apply" }, "bind": {}, "events": [{ "event": "click", "code": "styleSelection;", "mods": [] }], "children": [{ "value": "(gwText('Apply style to selection ('))" }, { "value": "(selected.length)" }, { "text": ")" }], "when": "(selected.length)" }, { "tag": "div", "attrs": { "class": "drawing-paint__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "(!undo.length)", "title": "(gwText('Undo (Ctrl+Z)'))", "aria-label": "(gwText('Undo'))" }, "events": [{ "event": "click", "code": "history('undo');", "mods": [] }], "children": [{ "tag": "PhArrowCounterClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!redo.length)", "title": "(gwText('Redo (Ctrl+Shift+Z)'))", "aria-label": "(gwText('Redo'))" }, "events": [{ "event": "click", "code": "history('redo');", "mods": [] }], "children": [{ "tag": "PhArrowClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!selected.length)", "title": "(gwText('Copy selection'))", "aria-label": "(gwText('Copy selection'))" }, "events": [{ "event": "click", "code": "copy;", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "title": "(gwText('Paste copy'))", "aria-label": "(gwText('Paste copy'))" }, "events": [{ "event": "click", "code": "paste;", "mods": [] }], "children": [{ "tag": "PhClipboard", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!selected.length)", "title": "(gwText('Delete selection'))", "aria-label": "(gwText('Delete selection'))" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": { "class": "drawing-paint__clear" }, "bind": {}, "events": [{ "event": "click", "code": "clearConfirm ? save(rows.filter(r => !editable(r))) : clearConfirm = true;", "mods": [] }], "children": [{ "value": "(clearConfirm ? gwText('Confirm clearing') : gwText('Clear layer'))" }] }] }] }, { "tag": "p", "attrs": { "class": "drawing-paint__hint" }, "bind": { "role": "(error ? 'alert' : 'status')" }, "events": [], "children": [{ "value": "(error || (busy ? gwText('Saving\u2026') : tool === 'erase' ? gwText('Drag to erase entire strokes.') : tool === 'select' ? gwText('Drag to move or select. Shift adds to the selection.') : tool === 'text' ? gwText('Type text and click to place it.') : gwText('Drag to draw. Shift constrains shapes and angles.')))" }] }] }, { "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "(context.x)", "y": "(context.y)" }, "events": [{ "event": "close", "code": "context = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "copy;", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Copy'))" }] }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "paste;", "mods": [] }], "children": [{ "tag": "PhClipboard", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Paste'))" }] }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Delete selection'))" }] }], "when": "(context)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const emit = options.emit;
  const abort = new AbortController(), api = new BlockStateApi(new HttpClient2(void 0, () => abort.signal));
  const root = ref(), tool = ref("pen");
  const rows = ref([]), version = ref(0), selected = ref([]), draft = ref(), marquee = ref();
  const color = ref("#e1b466"), fill = ref("#e1b466"), filled = ref(false), width = ref(3), opacity = ref(1), fontSize = ref(21), text2 = ref("");
  const busy = ref(false), error = ref(""), clearConfirm = ref(false), context = ref();
  const undo = ref([]), redo = ref([]);
  let clipboard = [];
  let drag;
  const tools = [{ id: "select", get label() {
    return text("Select and move");
  }, icon: PhCursor }, { id: "pen", get label() {
    return text("Brush");
  }, icon: PhPencilSimple }, { id: "line", get label() {
    return text("Line");
  }, icon: PhLineSegment }, { id: "arrow", get label() {
    return text("Arrow");
  }, icon: PhArrowUpRight }, { id: "rect", get label() {
    return text("Rectangle");
  }, icon: PhRectangle }, { id: "ellipse", get label() {
    return text("Ellipse");
  }, icon: PhCircle }, { id: "text", get label() {
    return text("Text");
  }, icon: PhTextT }, { id: "erase", get label() {
    return text("Stroke eraser");
  }, icon: PhEraser }];
  const palette = ["#ffffff", "#171d23", "#e1b466", "#ef5350", "#ff9800", "#fdd835", "#66bb6a", "#26c6da", "#42a5f5", "#ab47bc"];
  const visible = computed(() => draft.value ? [...rows.value, draft.value] : rows.value);
  const editable = (r) => r.audience === props.audience;
  const copyRows = (list) => list.map((r) => ({ ...r, points: r.points.map((p) => ({ ...p })) }));
  function point(e) {
    const b = root.value.getBoundingClientRect();
    return { x: (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - b.top - props.viewport.y) / props.viewport.scale };
  }
  function pick(p) {
    return [...rows.value].reverse().find((r) => editable(r) && hit(r, p, 5 / props.viewport.scale));
  }
  function release() {
    if (drag && root.value?.hasPointerCapture(drag.pointer))
      root.value.releasePointerCapture(drag.pointer);
    drag = void 0;
    draft.value = void 0;
    marquee.value = void 0;
  }
  function cancel() {
    if (drag)
      rows.value = drag.before;
    release();
  }
  watch(() => props.document, (doc) => {
    if (!doc || doc.version === version.value)
      return;
    cancel();
    rows.value = copyRows(doc.rows);
    version.value = doc.version;
    undo.value = [];
    redo.value = [];
    selected.value = [];
  }, { immediate: true });
  async function save(next, before = copyRows(rows.value), history2 = "normal") {
    if (busy.value)
      return;
    busy.value = true;
    error.value = "";
    context.value = void 0;
    clearConfirm.value = false;
    try {
      const result = await api.command(props.containerId, props.blockId, "drawings", "replace", { rows: next, expected_version: version.value });
      if (abort.signal.aborted)
        return;
      rows.value = result.rows;
      version.value = result.version;
      if (history2 === "normal") {
        undo.value = [...undo.value.slice(-29), before];
        redo.value = [];
      } else if (history2 === "undo") {
        undo.value.pop();
        redo.value.push(before);
      } else {
        redo.value.pop();
        undo.value.push(before);
      }
      emit("refresh");
    } catch {
      if (!abort.signal.aborted) {
        rows.value = before;
        error.value = text("Could not save. The scene will refresh; try again.");
        undo.value = [];
        redo.value = [];
        emit("refresh");
      }
    } finally {
      if (!abort.signal.aborted)
        busy.value = false;
    }
  }
  function create(p) {
    return { id: crypto.randomUUID(), kind: tool.value, audience: props.audience, points: [p], color: color.value, fill: filled.value ? fill.value : "none", width: width.value, opacity: opacity.value, fontSize: fontSize.value, text: text2.value };
  }
  function down(e) {
    if (e.button !== 0 || busy.value)
      return;
    e.preventDefault();
    e.stopPropagation();
    context.value = void 0;
    clearConfirm.value = false;
    const p = point(e), row = pick(p), before = copyRows(rows.value);
    if (tool.value === "text") {
      if (!text2.value.trim()) {
        error.value = text("Enter text in the panel before clicking the map.");
        return;
      }
      void save([...rows.value, create(p)]);
      return;
    }
    if (tool.value === "select") {
      if (row) {
        selected.value = e.shiftKey ? selected.value.includes(row.id) ? selected.value.filter((id) => id !== row.id) : [...selected.value, row.id] : selected.value.includes(row.id) ? selected.value : [row.id];
      } else {
        if (!e.shiftKey)
          selected.value = [];
        marquee.value = { a: p, b: p };
      }
    } else if (tool.value === "erase") {
      if (row)
        rows.value = rows.value.filter((r) => r.id !== row.id);
    } else {
      selected.value = [];
      draft.value = create(p);
    }
    drag = { pointer: e.pointerId, start: p, before, mode: tool.value, ids: [...selected.value] };
    root.value?.setPointerCapture(e.pointerId);
  }
  function move(e) {
    if (!drag || drag.pointer !== e.pointerId)
      return;
    e.stopPropagation();
    let p = point(e);
    const a = drag.start;
    if (drag.mode === "select") {
      if (marquee.value)
        marquee.value.b = p;
      else
        rows.value = drag.before.map((r) => drag.ids.includes(r.id) ? translated(r, p.x - a.x, p.y - a.y) : r);
    } else if (drag.mode === "erase") {
      const row = pick(p);
      if (row)
        rows.value = rows.value.filter((r) => r.id !== row.id);
    } else if (draft.value) {
      if (draft.value.kind === "pen") {
        const last = draft.value.points.at(-1);
        if (draft.value.points.length < 4096 && Math.hypot(p.x - last.x, p.y - last.y) >= 1 / props.viewport.scale)
          draft.value.points.push(p);
      } else {
        if (e.shiftKey) {
          const dx = p.x - a.x, dy = p.y - a.y;
          if (["rect", "ellipse"].includes(draft.value.kind)) {
            const size = Math.max(Math.abs(dx), Math.abs(dy));
            p = { x: a.x + Math.sign(dx || 1) * size, y: a.y + Math.sign(dy || 1) * size };
          } else {
            const angle = Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) * Math.PI / 4, len = Math.hypot(dx, dy);
            p = { x: a.x + Math.cos(angle) * len, y: a.y + Math.sin(angle) * len };
          }
        }
        draft.value.points = [a, p];
      }
    }
  }
  function up(e) {
    if (!drag || drag.pointer !== e.pointerId)
      return;
    move(e);
    e.stopPropagation();
    const before = drag.before;
    if (marquee.value) {
      const { a, b } = marquee.value;
      selected.value = [.../* @__PURE__ */ new Set([...selected.value, ...rows.value.filter((r) => {
        const box = bounds(r);
        return editable(r) && box.x >= Math.min(a.x, b.x) && box.y >= Math.min(a.y, b.y) && box.x + box.width <= Math.max(a.x, b.x) && box.y + box.height <= Math.max(a.y, b.y);
      }).map((r) => r.id)])];
      release();
      return;
    }
    const next = draft.value ? [...rows.value, copyRows([draft.value])[0]] : copyRows(rows.value);
    release();
    if (JSON.stringify(before) !== JSON.stringify(next))
      void save(next, before);
  }
  function choose(id) {
    cancel();
    tool.value = id;
    context.value = void 0;
    clearConfirm.value = false;
    error.value = "";
  }
  function remove() {
    void save(rows.value.filter((r) => !selected.value.includes(r.id)));
    selected.value = [];
  }
  function copy() {
    clipboard = copyRows(rows.value.filter((r) => selected.value.includes(r.id)));
    context.value = void 0;
  }
  function paste() {
    if (!clipboard.length)
      return;
    const added = clipboard.map((r) => ({ ...translated(r, 21, 21), id: crypto.randomUUID(), audience: props.audience }));
    void save([...rows.value, ...added]);
    selected.value = added.map((r) => r.id);
  }
  function history(direction) {
    cancel();
    const list = direction === "undo" ? undo.value : redo.value;
    const next = list.at(-1);
    if (next) {
      selected.value = [];
      void save(copyRows(next), copyRows(rows.value), direction);
    }
  }
  function styleSelection() {
    void save(rows.value.map((r) => selected.value.includes(r.id) ? { ...r, color: color.value, fill: filled.value ? fill.value : "none", width: width.value, opacity: opacity.value, fontSize: fontSize.value, text: r.kind === "text" ? text2.value : r.text } : r));
  }
  function edit(e, row) {
    if (tool.value !== "select" || !editable(row))
      return;
    e.stopPropagation();
    selected.value = [row.id];
    tool.value = row.kind === "text" ? "text" : "select";
    color.value = row.color;
    fill.value = row.fill === "none" ? row.color : row.fill;
    filled.value = row.fill !== "none";
    width.value = row.width;
    opacity.value = row.opacity;
    fontSize.value = row.fontSize;
    text2.value = row.text;
  }
  function menu(e) {
    const row = pick(point(e));
    if (!row)
      return;
    e.preventDefault();
    e.stopPropagation();
    if (!selected.value.includes(row.id))
      selected.value = [row.id];
    context.value = { x: e.clientX, y: e.clientY };
  }
  function key(e) {
    if (e.target instanceof Element && e.target.closest("input,textarea,select,[contenteditable=true]"))
      return;
    const mod = e.ctrlKey || e.metaKey;
    const handled = e.key === "Escape" || ["Delete", "Backspace"].includes(e.key) && selected.value.length || mod && ["z", "y", "c", "v", "a"].includes(e.key.toLowerCase());
    if (!handled)
      return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (busy.value)
      return;
    if (e.key === "Escape") {
      if (drag)
        cancel();
      else if (selected.value.length)
        selected.value = [];
      else
        emit("close");
    } else if (["Delete", "Backspace"].includes(e.key))
      remove();
    else if (e.key.toLowerCase() === "z")
      history(e.shiftKey ? "redo" : "undo");
    else if (e.key.toLowerCase() === "y")
      history("redo");
    else if (e.key.toLowerCase() === "c")
      copy();
    else if (e.key.toLowerCase() === "v")
      paste();
    else
      selected.value = rows.value.filter(editable).map((r) => r.id);
  }
  onMounted(() => {
    window.addEventListener("keydown", key, true);
    window.addEventListener("blur", cancel);
  });
  onBeforeUnmount(() => {
    abort.abort();
    cancel();
    window.removeEventListener("keydown", key, true);
    window.removeEventListener("blur", cancel);
  });
  defineExpose({ editId(id) {
    const row = rows.value.find((r) => r.id === id);
    if (row) {
      choose("select");
      edit(new MouseEvent("dblclick"), row);
    }
  } });
  return { gwText: text, PhCursor, PhPencilSimple, PhLineSegment, PhArrowUpRight, PhRectangle, PhCircle, PhTextT, PhEraser, PhArrowCounterClockwise, PhArrowClockwise, PhTrash, PhCopy, PhClipboard, PhX, BlockStateApi, HttpClient: HttpClient2, DirectoryContextMenu: DirectoryContextMenu_native_default, bounds, hit, path, translated, root, tool, rows, version, selected, draft, marquee, color, fill, filled, width, opacity, fontSize, text: text2, busy, error, clearConfirm, context, undo, redo, clipboard, drag, tools, palette, visible, editable, copyRows, point, pick, release, cancel, save, create, down, move, up, choose, remove, copy, paste, history, styleSelection, edit, menu, key, emit: options.emit };
});

// gravewright/maps/frontend/features/measurement/model/measurement.js
var unitsPerPixel = (cell, value) => (Number.isFinite(value) && value > 0 ? value : 1) / (Number.isFinite(cell) && cell > 0 ? cell : 70);
function dragMeasure(seed, end, constrain = false) {
  let dx = end.x - seed.origin.x, dy = end.y - seed.origin.y;
  if (seed.kind === "rect") {
    if (constrain) {
      const n = Math.max(Math.abs(dx), Math.abs(dy));
      dx = Math.sign(dx || 1) * n;
      dy = Math.sign(dy || 1) * n;
    }
    return { ...seed, origin: { x: seed.origin.x + Math.min(0, dx), y: seed.origin.y + Math.min(0, dy) }, length: Math.abs(dx), width: Math.abs(dy), direction: 0 };
  }
  let direction = Math.atan2(dy, dx) * 180 / Math.PI;
  if (constrain)
    direction = Math.round(direction / 45) * 45;
  const length = Math.hypot(dx, dy);
  return { ...seed, length, direction, width: seed.kind === "wide-cone" ? length / 3 : seed.width };
}
function measurePath(m) {
  const l = Math.max(0.01, m.length), w = Math.max(0.01, m.width);
  if (m.kind === "line")
    return `M0 0H${l}`;
  if (m.kind === "circle")
    return `M${-l} 0a${l} ${l} 0 1 0 ${2 * l} 0a${l} ${l} 0 1 0 ${-2 * l} 0`;
  if (m.kind === "rect")
    return `M0 0H${l}V${w}H0Z`;
  if (m.kind === "cone") {
    const half = l * Math.tan(m.angle * Math.PI / 360);
    return `M0 0L${l} ${-half}V${half}Z`;
  }
  const r = Math.min(w / 2, l * 0.49), c = l - r, tx = c - r * r / c, ty = r * Math.sqrt(Math.max(0, 1 - r * r / (c * c)));
  return `M0 0L${tx} ${-ty}A${r} ${r} 0 1 1 ${tx} ${ty}Z`;
}
function area(m) {
  if (m.kind === "line")
    return 0;
  if (m.kind === "circle")
    return Math.PI * m.length * m.length;
  if (m.kind === "rect")
    return m.length * m.width;
  if (m.kind === "cone")
    return m.length * m.length * Math.tan(m.angle * Math.PI / 360);
  const r = Math.min(m.width / 2, m.length * 0.49), c = m.length - r;
  if (c <= 0)
    return 0;
  const alpha = Math.acos(-r / c), ty = r * Math.sqrt(Math.max(0, 1 - r * r / (c * c)));
  return c * ty + r * r * alpha;
}
function summary(m, factor, unit) {
  const n = formatNumber;
  const length = m.length * factor, width = m.width * factor, measure = (v) => `${n(v)} ${unit}`.trim();
  if (m.kind === "line")
    return measure(length);
  if (m.kind === "circle")
    return `R ${measure(length)} \xB7 \xD8 ${measure(length * 2)} \xB7 ${n(area(m) * factor * factor)} ${unit}\xB2`;
  if (m.kind === "rect")
    return `${measure(length)} \xD7 ${measure(width)} \xB7 ${n(area(m) * factor * factor)} ${unit}\xB2`;
  return `${measure(length)} \xB7 ${m.kind === "cone" ? `${n(m.angle)}\xB0` : `${text("width")} ${measure(width)}`} \xB7 ${n(area(m) * factor * factor)} ${unit}\xB2`;
}

// gravewright/maps/frontend/features/measurement/ui/MeasurementWorkspace.native.js
var PhRuler = "PhRuler";
var PhTrash2 = "PhTrash";
var PhX2 = "PhX";
var PhPlus = "PhPlus";
var MeasurementWorkspace_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "measurement-workspace" }, "bind": { "class": "({ 'measurement-workspace--active': active })" }, "events": [{ "event": "pointerdown", "code": "down($event);", "mods": [] }, { "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "(m.id)", "transform": "(`translate(${m.origin.x} ${m.origin.y})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`rotate(${m.direction})`)" }, "events": [], "children": [{ "tag": "path", "attrs": { "stroke-linejoin": "round" }, "bind": { "d": "(measurePath(m))", "fill": "(m.kind === 'line' ? 'none' : m.color)", "fill-opacity": "(.16)", "stroke": "(m.color)", "stroke-width": "((selected === m.id ? 2 : 1.5) / viewport.scale)" }, "events": [], "children": [] }, { "tag": "path", "attrs": {}, "bind": { "d": "(`M0 0H${m.length}`)", "stroke": "(m.color)", "stroke-width": "(1 / viewport.scale)", "stroke-dasharray": "(`${5 / viewport.scale} ${3 / viewport.scale}`)" }, "events": [], "children": [], "when": "(m.kind !== 'rect')" }] }, { "tag": "circle", "attrs": { "class": "measurement-workspace__handle", "role": "button" }, "bind": { "r": "(5 / viewport.scale)", "fill": "(m.color)", "stroke": "(selected === m.id ? 'white' : '#171d23')", "stroke-width": "(1.5 / viewport.scale)", "class": "({ 'measurement-workspace__handle--active': active })", "tabindex": "(active ? 0 : -1)", "aria-label": "(`Mover ${formats.find(f => f.id === m.kind)?.label}`)" }, "events": [{ "event": "pointerdown", "code": "down($event, m);", "mods": ["stop"] }, { "event": "wheel", "code": "wheel($event, m);", "mods": [] }, { "event": "keydown", "code": "load(m);", "mods": ["enter", "stop"] }], "children": [] }, { "tag": "text", "attrs": { "fill": "white", "stroke": "#111820", "paint-order": "stroke", "font-family": "sans-serif" }, "bind": { "x": "(8 / viewport.scale)", "y": "(-13 / viewport.scale)", "font-size": "(12 / viewport.scale)", "stroke-width": "(3 / viewport.scale)" }, "events": [], "children": [{ "value": "(summary(m, factor, measureUnit))" }] }], "each": { "names": ["m"], "value": "(visible)" } }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": { "class": "measure-panel" }, "bind": { "aria-label": "(gwText('Measurement tool'))" }, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "measure-panel__header" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhRuler", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Measurement '))" }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(measureValue)" }, { "text": " " }, { "value": "(measureUnit)" }, { "value": "(gwText(' / cell'))" }] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close measurement'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "measure-panel__body" }, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "measure-panel__tools" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(f.id)", "aria-label": "(f.label)", "title": "(f.label)", "aria-pressed": "(kind === f.id)" }, "events": [{ "event": "click", "code": "choose(f.id);", "mods": [] }], "children": [{ "tag": "svg", "attrs": { "viewBox": "0 0 24 24", "aria-hidden": "true" }, "bind": {}, "events": [], "children": [{ "tag": "path", "attrs": { "fill": "none", "stroke": "currentColor", "stroke-width": "1.5", "stroke-linejoin": "round" }, "bind": { "d": "(f.icon)" }, "events": [], "children": [] }] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(f.label)" }] }], "each": { "names": ["f"], "value": "(formats)" } }] }, { "tag": "div", "attrs": { "class": "measure-panel__options" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "(snap)", "mods": [] } }, { "value": "(gwText('Snap to grid'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Measurement color'))" }, "events": [{ "event": "change", "code": "apply;", "mods": [] }], "children": [], "model": { "path": "(color)", "mods": [] } }] }, { "tag": "form", "attrs": { "class": "measure-panel__form" }, "bind": {}, "events": [{ "event": "submit", "code": "apply;", "mods": ["prevent"] }], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(kind === 'circle' ? gwText('Radius') : gwText('Length'))" }, { "text": " (" }, { "value": "(measureUnit)" }, { "text": ")" }, { "tag": "input", "attrs": { "type": "number", "min": "0.001", "max": "100000", "step": "any", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "(lengthValue)", "mods": ["number"] } }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Width ('))" }, { "value": "(measureUnit)" }, { "text": ")" }, { "tag": "input", "attrs": { "type": "number", "min": "0.001", "step": "any", "required": "" }, "bind": { "max": "(kind === 'wide-cone' ? lengthValue * .98 : 100000)" }, "events": [], "children": [], "model": { "path": "(widthValue)", "mods": ["number"] } }], "when": "(['rect', 'wide-cone'].includes(kind))" }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Spread (\xB0)'))" }, { "tag": "input", "attrs": { "type": "number", "min": "5", "max": "170", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "(angle)", "mods": ["number"] } }], "when": "(kind === 'cone')" }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Direction (\xB0)'))" }, { "tag": "input", "attrs": { "type": "number", "min": "-360", "max": "360", "step": "any", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "(direction)", "mods": ["number"] } }], "when": "(kind !== 'circle')" }, { "tag": "button", "attrs": { "class": "measure-panel__apply", "type": "submit" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Apply dimensions'))" }] }], "when": "(current)" }, { "tag": "label", "attrs": { "class": "measure-panel__angle" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Cover'))" }, { "text": " " }, { "value": "(angle)" }, { "text": "\xB0" }, { "tag": "input", "attrs": { "type": "range", "min": "5", "max": "170", "step": "5" }, "bind": {}, "events": [], "children": [], "model": { "path": "(angle)", "mods": ["number"] } }], "otherwiseWhen": "(kind === 'cone')" }, { "tag": "p", "attrs": { "class": "measure-panel__hint" }, "bind": {}, "events": [], "children": [{ "value": "(current ? gwText('Drag the origin to move. Shift + wheel at the origin rotates.') : gwText('Drag on the map to measure. Shift constrains the angle or creates a square.'))" }, { "text": " " }, { "value": "(gwText('Alt ignores snapping.'))" }] }, { "tag": "div", "attrs": { "class": "measure-panel__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "selected = '';", "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('New'))" }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!selected)" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Delete'))" }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!rows.length)" }, "events": [{ "event": "click", "code": "confirmClear ? (rows = rows.filter(r => r.canEdit===false), selected = '', confirmClear = false) : confirmClear = true;", "mods": [] }], "children": [{ "value": "(confirmClear ? gwText('Confirm clearing') : gwText('Clear'))" }] }] }, { "tag": "small", "attrs": { "class": "measure-panel__scope" }, "bind": {}, "events": [], "children": [{ "value": "(shared ? gwText('Area markers')+' \xB7 ' : gwText('Local scene measurements \xB7 '))" }, { "value": "(rows.length)" }, { "value": "('/'+(maxRows || 50))" }] }] }], "when": "(active)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const emit = options.emit;
  const root = ref(), rows = ref([]), draft = ref(), selected = ref(""), kind = ref("line"), color = ref("#e1b466"), snap = ref(false), angle = ref(60), confirmClear = ref(false);
  const lengthValue = ref(5), widthValue = ref(5), direction = ref(0);
  const factor = computed(() => unitsPerPixel(props.cell, props.measureValue));
  const current = computed(() => draft.value ?? rows.value.find((m) => m.id === selected.value));
  const visible = computed(() => draft.value ? [...rows.value.filter((r) => r.id !== draft.value.id), draft.value] : rows.value);
  const formats2 = [{ id: "line", get label() {
    return text("Line");
  }, icon: "M3 21L21 3M3 16V21H8M16 3H21V8" }, { id: "circle", get label() {
    return text("Circle");
  }, icon: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0 -18" }, { id: "rect", get label() {
    return text("Cube / rectangle");
  }, icon: "M3 5H21V19H3Z" }, { id: "cone", get label() {
    return text("Triangular cone");
  }, icon: "M3 12L21 3V21Z" }, { id: "wide-cone", get label() {
    return text("Wide cone");
  }, icon: "M2 12L15 5A7 7 0 1 1 15 19Z" }];
  let drag;
  function point(e) {
    const b = root.value.getBoundingClientRect();
    let x = (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y = (e.clientY - b.top - props.viewport.y) / props.viewport.scale;
    if (snap.value && !e.altKey) {
      x = Math.round(x / props.cell) * props.cell;
      y = Math.round(y / props.cell) * props.cell;
    }
    return { x, y };
  }
  function release() {
    if (drag && root.value?.hasPointerCapture(drag.pointer))
      root.value.releasePointerCapture(drag.pointer);
    drag = void 0;
    draft.value = void 0;
  }
  function cancel() {
    release();
    confirmClear.value = false;
  }
  function load(m) {
    selected.value = m.id;
    kind.value = m.kind;
    lengthValue.value = Number((m.length * factor.value).toFixed(3));
    widthValue.value = Number((m.width * factor.value).toFixed(3));
    angle.value = m.angle;
    direction.value = (m.direction % 360 + 360) % 360;
    color.value = m.color;
  }
  function down(e, m) {
    if (!props.active || e.button !== 0 || m?.canEdit === false)
      return;
    e.preventDefault();
    e.stopPropagation();
    cancel();
    const p = point(e);
    if (m)
      load(m);
    else
      selected.value = "";
    const seed = m ?? { id: crypto.randomUUID(), kind: kind.value, origin: p, length: 0, width: 0, direction: 0, angle: angle.value, color: color.value };
    drag = { pointer: e.pointerId, start: p, seed, move: !!m };
    draft.value = { ...seed };
    root.value?.setPointerCapture(e.pointerId);
  }
  function move(e) {
    if (!drag || drag.pointer !== e.pointerId)
      return;
    e.stopPropagation();
    const p = point(e);
    draft.value = drag.move ? { ...drag.seed, origin: { x: drag.seed.origin.x + p.x - drag.start.x, y: drag.seed.origin.y + p.y - drag.start.y } } : dragMeasure(drag.seed, p, e.shiftKey);
  }
  function up(e) {
    if (!drag || drag.pointer !== e.pointerId)
      return;
    move(e);
    e.stopPropagation();
    const m = draft.value;
    release();
    if (m && m.length * props.viewport.scale > 2 && (m.kind !== "rect" || m.width * props.viewport.scale > 2)) {
      rows.value = [...rows.value.filter((r) => r.id !== m.id), m].slice(-Math.max(1, props.maxRows || 50));
      load(m);
    }
  }
  function choose(id) {
    cancel();
    selected.value = "";
    kind.value = id;
  }
  function apply() {
    const m = current.value;
    if (!m || m.canEdit === false)
      return;
    const l = Number(lengthValue.value), w = Number(widthValue.value), a = Number(angle.value), d = Number(direction.value);
    if (!Number.isFinite(l) || l <= 0 || l > 1e5 || ["rect", "wide-cone"].includes(m.kind) && (!Number.isFinite(w) || w <= 0 || w > 1e5) || !Number.isFinite(a) || a < 5 || a > 170 || !Number.isFinite(d))
      return;
    const next = { ...m, length: l / factor.value, width: (m.kind === "wide-cone" ? Math.min(w, l * 0.98) : w) / factor.value, angle: a, direction: d % 360, color: color.value };
    rows.value = rows.value.map((r) => r.id === m.id ? next : r);
    load(next);
  }
  function wheel(e, m) {
    if (!props.active || !e.shiftKey || m.canEdit === false)
      return;
    e.preventDefault();
    e.stopPropagation();
    const next = { ...m, direction: (m.direction + (e.deltaY > 0 ? 15 : -15) + 360) % 360 };
    rows.value = rows.value.map((r) => r.id === m.id ? next : r);
    load(next);
  }
  function remove() {
    if (current.value?.canEdit === false) return;
    rows.value = rows.value.filter((r) => r.id !== selected.value);
    selected.value = "";
  }
  function key(e) {
    if (!props.active || e.target instanceof Element && e.target.closest("input,select,textarea,[contenteditable=true]"))
      return;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (drag)
        cancel();
      else
        emit("close");
    } else if (["Delete", "Backspace"].includes(e.key) && selected.value) {
      e.preventDefault();
      e.stopImmediatePropagation();
      remove();
    }
  }
  watch(() => props.active, (active) => {
    if (!active)
      cancel();
  });
  watch(factor, () => {
    if (current.value)
      load(current.value);
  });
  onMounted(() => {
    window.addEventListener("keydown", key, true);
    window.addEventListener("blur", cancel);
  });
  onBeforeUnmount(() => {
    cancel();
    window.removeEventListener("keydown", key, true);
    window.removeEventListener("blur", cancel);
  });
  watch(() => props.rows, (value) => {
    if (props.shared && value) rows.value = value;
  }, { deep: true, immediate: true });
  watch(rows, (value) => emit("change", value), { deep: true });
  defineExpose({ replace(value) {
    cancel();
    rows.value = value;
  }, editId(id) {
    const row = rows.value.find((r) => r.id === id);
    if (row)
      load(row);
  } });
  return { gwText: text, PhRuler, PhTrash: PhTrash2, PhX: PhX2, PhPlus, dragMeasure, measurePath, summary, unitsPerPixel, root, rows, draft, selected, kind, color, snap, angle, confirmClear, lengthValue, widthValue, direction, factor, current, visible, formats: formats2, drag, point, release, cancel, load, down, move, up, choose, apply, wheel, remove, key, emit: options.emit };
});

// gravewright/maps/frontend/features/images/ui/ImageWorkspace.native.js
var PhTrash3 = "PhTrash";
var ImageWorkspace_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "image-workspace" }, "bind": {}, "events": [{ "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "(image.id)", "transform": "(`translate(${image.x} ${image.y}) rotate(${image.rotation})`)" }, "events": [], "children": [{ "tag": "rect", "attrs": { "class": "image-workspace__image", "fill": "transparent", "role": "button" }, "bind": { "class": "({ 'image-workspace__image--active': tool === 'select' })", "x": "(-image.natural_width * image.scale / 2)", "y": "(-image.natural_height * image.scale / 2)", "width": "(image.natural_width * image.scale)", "height": "(image.natural_height * image.scale)", "stroke": "(selected === image.id ? '#e9c46a' : 'none')", "stroke-width": "(2 / viewport.scale)", "tabindex": "(tool === 'select' ? 0 : -1)", "aria-label": "(gwText('Scene image'))", "aria-pressed": "(selected === image.id)" }, "events": [{ "event": "pointerdown", "code": "down($event, image);", "mods": [] }, { "event": "contextmenu", "code": "menu($event, image);", "mods": [] }, { "event": "keydown", "code": "selected = image.id;", "mods": ["enter", "stop"] }], "children": [] }], "each": { "names": ["image"], "value": "(images)" } }] }] }, { "tag": "p", "attrs": { "class": "image-workspace__status" }, "bind": { "role": "(error ? 'alert' : 'status')" }, "events": [], "children": [{ "value": "(error || gwText('Saving image\u2026'))" }], "when": "(error || busy)" }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "(context.x)", "y": "(context.y)", "label": "(gwText('Image actions'))" }, "events": [{ "event": "close", "code": "context = undefined;", "mods": [] }], "children": [{ "tag": "li", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "class": "is-danger" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Remove from scene'))" }] }] }], "when": "(context)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const emit = options.emit;
  const abort = new AbortController(), api = new BlockStateApi(new HttpClient2(void 0, () => abort.signal));
  const root = ref(), selected = ref(""), preview = ref(), busy = ref(false), error = ref(""), context = ref();
  const images = computed(() => [...props.images].sort((a, b) => a.z_index - b.z_index).map((image) => preview.value?.id === image.id ? preview.value : image));
  let drag;
  function show(image) {
    preview.value = image;
    emit("preview", image);
  }
  function point(e) {
    const box = root.value.getBoundingClientRect();
    return { x: (e.clientX - box.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - box.top - props.viewport.y) / props.viewport.scale };
  }
  function down(e, image) {
    if (e.button !== 0 || busy.value || props.tool !== "select")
      return;
    e.preventDefault();
    e.stopPropagation();
    selected.value = image.id;
    context.value = void 0;
    error.value = "";
    const p = point(e);
    drag = { pointer: e.pointerId, ...p, image: { ...image } };
    root.value?.setPointerCapture(e.pointerId);
  }
  function move(e) {
    if (!drag || drag.pointer !== e.pointerId)
      return;
    e.stopPropagation();
    const p = point(e);
    show({ ...drag.image, x: drag.image.x + p.x - drag.x, y: drag.image.y + p.y - drag.y });
  }
  function release() {
    if (drag && root.value?.hasPointerCapture(drag.pointer))
      root.value.releasePointerCapture(drag.pointer);
    drag = void 0;
  }
  function cancel() {
    release();
    show();
    context.value = void 0;
  }
  async function save(image) {
    if (busy.value)
      return;
    busy.value = true;
    error.value = "";
    show(image);
    try {
      await api.command(props.containerId, props.blockId, "images", "update", { placement_id: image.id, x: image.x, y: image.y, expected_version: image.version });
      if (!abort.signal.aborted)
        emit("refresh");
    } catch {
      if (!abort.signal.aborted) {
        show();
        error.value = text("Could not move the image. Refreshing the scene\u2026");
        emit("refresh");
      }
    } finally {
      if (!abort.signal.aborted)
        busy.value = false;
    }
  }
  function up(e) {
    if (!drag || drag.pointer !== e.pointerId)
      return;
    e.stopPropagation();
    const original = drag.image;
    const image = preview.value;
    release();
    if (!image || image.x === original.x && image.y === original.y) {
      show();
      return;
    }
    const cell = props.cell;
    void save({ ...image, x: props.grid && !e.altKey ? Math.round(image.x / cell) * cell : image.x, y: props.grid && !e.altKey ? Math.round(image.y / cell) * cell : image.y });
  }
  async function remove() {
    if (!selected.value || busy.value)
      return;
    busy.value = true;
    context.value = void 0;
    try {
      await api.command(props.containerId, props.blockId, "images", "delete", { placement_id: selected.value });
      if (!abort.signal.aborted) {
        selected.value = "";
        emit("refresh");
      }
    } catch {
      if (!abort.signal.aborted)
        error.value = text("Could not remove the image.");
    } finally {
      if (!abort.signal.aborted)
        busy.value = false;
    }
  }
  function menu(e, image) {
    if (props.tool !== "select")
      return;
    e.preventDefault();
    e.stopPropagation();
    selected.value = image.id;
    context.value = { x: e.clientX, y: e.clientY };
  }
  function key(e) {
    if (e.target instanceof Element && e.target.closest("input,textarea,select,[contenteditable=true]"))
      return;
    if (e.key === "Escape") {
      cancel();
      selected.value = "";
      return;
    }
    if (!selected.value || busy.value || drag || props.tool !== "select")
      return;
    if (["Delete", "Backspace"].includes(e.key)) {
      e.preventDefault();
      e.stopPropagation();
      void remove();
      return;
    }
    const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
    const image = props.images.find((i) => i.id === selected.value);
    if (delta && image) {
      e.preventDefault();
      e.stopPropagation();
      const step = e.altKey ? 1 : props.cell;
      void save({ ...image, x: image.x + delta[0] * step, y: image.y + delta[1] * step });
    }
  }
  watch(() => props.images, (rows) => {
    if (drag && !rows.some((i) => i.id === drag.image.id && i.version === drag.image.version))
      cancel();
    if (!drag)
      show();
    if (!rows.some((i) => i.id === selected.value))
      selected.value = "";
  });
  watch(() => props.tool, cancel);
  onMounted(() => {
    window.addEventListener("keydown", key);
    window.addEventListener("blur", cancel);
  });
  onBeforeUnmount(() => {
    abort.abort();
    cancel();
    window.removeEventListener("keydown", key);
    window.removeEventListener("blur", cancel);
  });
  return { gwText: text, PhTrash: PhTrash3, BlockStateApi, HttpClient: HttpClient2, DirectoryContextMenu: DirectoryContextMenu_native_default, root, selected, preview, busy, error, context, images, drag, show, point, down, move, release, cancel, save, up, remove, menu, key, emit: options.emit };
});

// gravewright/maps/frontend/features/lighting/ui/LightPicker.native.js
import { renderingPreferences } from "/static/gravewright_maps/render-profile.js";

// gravewright/maps/frontend/shared/rendering/effect-quality.js
var EFFECT_QUALITY = {
  performance: { fps: 15, lightFps: 8, particles: 0.25, particleLimit: 300, lightMap: 256, shaderDetail: 1, shaders: true },
  balanced: { fps: 30, lightFps: 15, particles: 0.5, particleLimit: 600, lightMap: 512, shaderDetail: 3, shaders: true },
  quality: { fps: 60, lightFps: 30, particles: 1, particleLimit: 1200, lightMap: 1024, shaderDetail: 5, shaders: true }
};
function effectQuality(profile) {
  return EFFECT_QUALITY[profile];
}

// gravewright/maps/frontend/features/lighting/model/light-profiles.js
var lightPresets = [
  { id: "torch", get name() {
    return text("Torch");
  }, bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#ff9a3c", angle: 360 },
  { id: "pulse", get name() {
    return text("Pulse");
  }, bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#55aaff", angle: 360 },
  { id: "none", get name() {
    return text("Steady");
  }, bright_radius: 2, dim_radius: 4, intensity: 0.85, color: "#ffd8a8", angle: 360 }
];
function lightAnimation(light, now) {
  let hash = 0;
  for (const c of light.id)
    hash = (hash * 31 + c.charCodeAt(0)) % 9973;
  const phase = hash / 9973 * Math.PI * 2;
  if (light.animation === "pulse") {
    const wave = 0.5 + 0.5 * Math.sin(now * 2 * Math.PI / 2800 + phase);
    return 0.9 + 0.1 * wave * wave * (3 - 2 * wave);
  }
  if (["torch", "candle", "fire"].includes(light.animation ?? "")) {
    const wave = 0.5 + 0.5 * (0.5 * Math.sin(now * 2 * Math.PI / 1300 + phase) + 0.32 * Math.sin(now * 2 * Math.PI / 620 + phase * 2) + 0.18 * Math.sin(now * 2 * Math.PI / 350 + phase * 3));
    return 0.92 + 0.08 * wave;
  }
  return 1;
}
var falloffs = /* @__PURE__ */ new Map();
function falloff(color, flame) {
  const key = `${color}:${flame}`;
  if (falloffs.has(key)) return falloffs.get(key);
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const ctx = canvas.getContext("2d"), image = ctx.createImageData(256, 256);
  const base = parseInt(color.slice(1), 16);
  const channels = [base >> 16 & 255, base >> 8 & 255, base & 255];
  const luma = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  const tint = channels.map((c) => Math.round(luma + (c - luma) * 0.7));
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
    const dx = (x - 128) / 128, dy = (y - 128) / 128;
    const distance = Math.hypot(dx, dy), angle = Math.atan2(dy, dx);
    if (distance >= 1) continue;
    const wave = Math.sin(angle * 6 + 0.6 * Math.sin(angle * 6));
    const shrink = flame ? 0.26 * (0.5 + 0.5 * wave) * Math.min(1, distance / 0.25) : 0;
    const reach = Math.min(1, distance / Math.max(0.05, 1 - shrink));
    const i = (y * 256 + x) * 4;
    image.data.set([...tint, Math.round((1 - reach) ** 2 * 255)], i);
  }
  ctx.putImageData(image, 0, 0);
  if (falloffs.size >= 32) falloffs.delete(falloffs.keys().next().value);
  falloffs.set(key, canvas);
  return canvas;
}
function paintAnimatedLight(ctx, light, x, y, radius, now) {
  let hash = 0;
  for (const c of light.id) hash = (hash * 31 + c.charCodeAt(0)) % 9973;
  const phase = hash / 9973 * Math.PI * 2;
  const torch = ["torch", "candle", "fire"].includes(light.animation);
  const animated = torch || light.animation === "pulse";
  const flame = (p) => 0.5 + 0.5 * (0.5 * Math.sin(now * 2 * Math.PI / (1300 * 0.7) + p) + 0.32 * Math.sin(now * 2 * Math.PI / (620 * 0.7) + p * 2) + 0.18 * Math.sin(now * 2 * Math.PI / (350 * 0.7) + p * 3));
  const shape = (p) => {
    if (torch) return flame(p * 1.3 + 0.9);
    const wave = 0.5 + 0.5 * Math.sin(now * 2 * Math.PI / 2800 + p);
    return wave * wave * (3 - 2 * wave);
  };
  const bright = light.dim_radius > 0 ? light.bright_radius / light.dim_radius : 0.05;
  const layers = torch ? [{ scale: 1, phase: 0, weight: 0.5 }, { scale: 0.62, phase: 2.1, weight: 0.4 }] : [{ scale: 1, phase: 0, weight: animated ? 0.55 : 0.5 }];
  const angle = (light.angle ?? 360) * Math.PI / 180;
  ctx.save();
  ctx.translate(x, y);
  if (angle < Math.PI * 2) {
    const direction = (light.rotation ?? 0) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, radius, direction - angle / 2, direction + angle / 2);
    ctx.closePath();
    ctx.clip();
  }
  ctx.globalCompositeOperation = "lighter";
  if (torch) {
    const reach = radius * (bright || 1) * 0.05;
    ctx.translate(Math.sin(now / 340 + phase) * reach, Math.sin(now / 470 + phase * 2) * reach);
  }
  const factor = light.intensity * lightAnimation(light, now);
  for (const [index, layer] of layers.entries()) {
    const p = phase + layer.phase;
    const r = radius * layer.scale * (animated ? 1 + 0.3 * (shape(p) - 0.5) * 2 : 1);
    ctx.save();
    if (animated) ctx.translate(Math.sin(now / (380 + index * 47) + p) * radius * 0.025, Math.sin(now / (530 + index * 61) + p * 1.7) * radius * 0.018);
    if (torch) ctx.rotate((now / 1e3 * 0.05 * Math.PI * 2 + phase) * (index % 2 ? -1.6 : 1));
    ctx.globalAlpha = factor * layer.weight;
    ctx.drawImage(falloff(light.color, torch), -r, -r, r * 2, r * 2);
    ctx.restore();
  }
  if (bright > 0) {
    const r = radius * bright;
    ctx.globalAlpha = factor * 0.45;
    ctx.drawImage(falloff(light.color, false), -r, -r, r * 2, r * 2);
  }
  ctx.restore();
}

// gravewright/maps/frontend/features/lighting/ui/LightPicker.native.js
var PhFlame = "PhFlame";
var PhWaveform = "PhWaveform";
var PhLightbulb = "PhLightbulb";
var PhX3 = "PhX";
var LightPicker_native_default = widget([{ "tag": "section", "attrs": { "ref": "panel", "class": "light-picker", "role": "dialog" }, "bind": { "style": "(position)", "aria-label": "(gwText('Light types'))" }, "events": [{ "event": "keydown", "code": "emit('close');", "mods": ["esc", "stop"] }], "children": [{ "tag": "div", "attrs": { "class": "light-picker__preview", "role": "img" }, "bind": { "aria-label": "(gwText('Preview: {0}', current.name))" }, "events": [], "children": [{ "tag": "canvas", "attrs": { "ref": "canvas", "width": "430", "height": "123" }, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(current.name)" }] }] }, { "tag": "header", "attrs": { "class": "light-picker__header" }, "bind": {}, "events": [], "children": [{ "tag": "PhLightbulb", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Lighting'))" }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close picker'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "light-picker__options" }, "bind": {}, "events": [{ "event": "mouseleave", "code": "hovered = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(p.id)", "aria-pressed": "(selected === p.id)" }, "events": [{ "event": "mouseenter", "code": "hovered = p.id;", "mods": [] }, { "event": "focus", "code": "hovered = p.id;", "mods": [] }, { "event": "click", "code": "emit('choose', p.id);", "mods": [] }], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "(icons[p.id])" }, "events": [], "children": [] }, { "value": "(p.name)" }], "each": { "names": ["p"], "value": "(lightPresets)" } }] }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const emit = options.emit;
  const hovered = ref();
  const current = computed(() => lightPresets.find((p) => p.id === (hovered.value ?? props.selected)) ?? lightPresets[0]);
  const panel = ref(), canvas = ref();
  const position = ref({ left: "13px", bottom: "89px" });
  let frame = 0;
  let restart = () => {
  };
  let stopProfile;
  const icons = { torch: PhFlame, pulse: PhWaveform, none: PhLightbulb };
  function place() {
    const r = document.querySelector('[data-effect-tool="light"]')?.getBoundingClientRect();
    if (r)
      position.value = { left: `${Math.max(8, Math.min(innerWidth - 438, r.left))}px`, bottom: `${innerHeight - r.top + 8}px` };
  }
  function outside(e) {
    if (e.target instanceof Element && !panel.value?.contains(e.target) && !e.target.closest("[data-effect-tool]"))
      emit("close");
  }
  onMounted(() => {
    place();
    window.addEventListener("resize", place);
    document.addEventListener("pointerdown", outside);
    const ctx = canvas.value.getContext("2d");
    let last = 0;
    const tick = (time) => {
      const fps = effectQuality(renderingPreferences.current().name).fps;
      if (!fps || time - last >= 1e3 / fps) {
        last = time;
        ctx.clearRect(0, 0, 430, 123);
        paintAnimatedLight(ctx, { ...current.value, id: "preview", animation: current.value.id, x: 215, y: 61, enabled: true }, 215, 61, 55, fps ? time : 0);
      }
      if (fps)
        frame = requestAnimationFrame(tick);
    };
    restart = () => {
      cancelAnimationFrame(frame);
      last = 0;
      tick(performance.now());
    };
    stopProfile = renderingPreferences.subscribe(restart);
  });
  watch(current, () => restart());
  onBeforeUnmount(() => {
    stopProfile?.();
    cancelAnimationFrame(frame);
    window.removeEventListener("resize", place);
    document.removeEventListener("pointerdown", outside);
  });
  return { gwText: text, PhFlame, PhWaveform, PhLightbulb, PhX: PhX3, renderingPreferences, effectQuality, lightPresets, paintAnimatedLight, hovered, current, panel, canvas, position, frame, restart, stopProfile, icons, place, outside, emit: options.emit };
});

// gravewright/maps/frontend/shared/lib/dom/movable-resizable.js
var cleanups = /* @__PURE__ */ new WeakMap();
var windows = /* @__PURE__ */ new Set();
function mount(element) {
  const doc = element.ownerDocument, view = doc.defaultView;
  const originalZ = element.style.zIndex;
  const entry = { element, base: Number.parseInt(view.getComputedStyle(element).zIndex) || 7 };
  windows.add(entry);
  function raise() {
    const doc2 = element.ownerDocument;
    const peers = [...windows].filter((w) => w.element.ownerDocument === doc2 && w.base === entry.base);
    windows.delete(entry);
    windows.add(entry);
    for (const peer of peers)
      peer.element.classList.toggle("gw-window--focused", peer === entry);
    [...windows].filter((w) => w.element.ownerDocument === doc2 && w.base === entry.base).forEach((w, index) => {
      w.element.style.zIndex = String(w.base + index);
    });
  }
  element.classList.add("gw-movable-resizable");
  const handle = element.querySelector("[data-move-handle]") ?? element;
  handle.classList.add("gw-move-handle");
  let stopDrag = () => {
  };
  const pointerDown = (event) => {
    if (event.button !== 0 || event.target.closest("button,input,select,textarea,a,[data-no-move]"))
      return;
    stopDrag();
    const doc2 = element.ownerDocument, view2 = doc2.defaultView;
    const bounds2 = element.getBoundingClientRect(), offsetX = event.clientX - bounds2.left, offsetY = event.clientY - bounds2.top;
    Object.assign(element.style, { position: "fixed", width: `${bounds2.width}px`, height: `${bounds2.height}px`, left: `${bounds2.left}px`, top: `${bounds2.top}px`, right: "auto", bottom: "auto" });
    const move = (next) => {
      if (next.pointerId !== event.pointerId)
        return;
      element.style.left = `${Math.min(view2.innerWidth - 55, Math.max(55 - element.offsetWidth, next.clientX - offsetX))}px`;
      element.style.top = `${Math.min(view2.innerHeight - 55, Math.max(0, next.clientY - offsetY))}px`;
    };
    const up = () => {
      doc2.removeEventListener("pointermove", move);
      doc2.removeEventListener("pointerup", up);
      doc2.removeEventListener("pointercancel", up);
      view2.removeEventListener("blur", up);
      handle.classList.remove("gw-move-handle--active");
      stopDrag = () => {
      };
    };
    stopDrag = up;
    handle.classList.add("gw-move-handle--active");
    doc2.addEventListener("pointermove", move);
    doc2.addEventListener("pointerup", up);
    doc2.addEventListener("pointercancel", up);
    view2.addEventListener("blur", up);
    event.preventDefault();
  };
  const resize = () => {
    const box = element.getBoundingClientRect();
    if (box.top > view.innerHeight - 55)
      element.style.top = `${Math.max(0, view.innerHeight - 55)}px`;
    if (box.left > view.innerWidth - 55) {
      element.style.left = `${Math.max(0, view.innerWidth - 55)}px`;
      element.style.right = "auto";
    }
  };
  element.addEventListener("pointerdown", raise, true);
  element.addEventListener("focusin", raise);
  handle.addEventListener("pointerdown", pointerDown);
  view.addEventListener("resize", resize);
  raise();
  cleanups.set(element, () => {
    stopDrag();
    windows.delete(entry);
    element.style.zIndex = originalZ;
    element.classList.remove("gw-window--focused");
    element.removeEventListener("pointerdown", raise, true);
    element.removeEventListener("focusin", raise);
    handle.removeEventListener("pointerdown", pointerDown);
    view.removeEventListener("resize", resize);
  });
}
var vMovableResizable = { mounted: mount, unmounted(element) {
  cleanups.get(element)?.();
  cleanups.delete(element);
} };

// gravewright/maps/frontend/features/lighting/ui/LightEditor.native.js
var PhX4 = "PhX";
var PhTrash4 = "PhTrash";
var LightEditor_native_default = widget([{ "tag": "section", "attrs": { "class": "gw-window light-editor", "role": "dialog" }, "bind": { "aria-label": "(gwText('Light source'))" }, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "wheel", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "light-editor__header", "data-move-handle": "" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Light source'))" }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "light-editor__body" }, "bind": {}, "events": [], "children": [{ "tag": "template", "attrs": {}, "bind": { "key": "(range.key)" }, "events": [], "children": [{ "tag": "label", "attrs": { "class": "light-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(range.name)" }] }, { "tag": "div", "attrs": { "class": "light-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range" }, "bind": { "min": "(range.min)", "max": "(Math.max(range.max, draft[range.key]))", "step": "(range.step)", "disabled": "(range.key === 'dim_radius' && draft.dim_radius === 0)" }, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft[range.key])", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(range.key === 'dim_radius' && draft.dim_radius === 0 ? '\u221E' : draft[range.key])" }, { "value": "(['angle', 'rotation'].includes(range.key) ? '\xB0' : '')" }] }] }], "when": "(range.key !== 'rotation' || draft.angle < 360)" }, { "tag": "label", "attrs": { "class": "light-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "checked": "(draft.dim_radius === 0)" }, "events": [{ "event": "change", "code": "unlimited;", "mods": [] }], "children": [] }, { "value": "(gwText('Unlimited'))" }], "when": "(range.key === 'dim_radius')" }], "each": { "names": ["range"], "value": "(ranges)" } }, { "tag": "div", "attrs": { "class": "light-editor__pair" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "light-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Animation'))" }] }, { "tag": "select", "attrs": {}, "bind": {}, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [{ "tag": "option", "attrs": { "value": "none" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Steady'))" }] }, { "tag": "option", "attrs": { "value": "torch" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Torch'))" }] }, { "tag": "option", "attrs": { "value": "pulse" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Pulse'))" }] }, { "tag": "option", "attrs": {}, "bind": { "value": "(draft.animation)" }, "events": [], "children": [{ "value": "(draft.animation)" }], "when": "(!['none', 'torch', 'pulse'].includes(draft.animation))" }], "model": { "path": "(draft.animation)", "mods": [] } }] }, { "tag": "label", "attrs": { "class": "light-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Color'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": {}, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.color)", "mods": [] } }] }] }, { "tag": "label", "attrs": { "class": "light-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.enabled)", "mods": [] } }, { "value": "(gwText('On'))" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Radii use grid cells. Walls block light.'))" }] }, { "tag": "p", "attrs": { "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "(props.error)" }], "when": "(props.error)" }, { "tag": "footer", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": { "role": "status" }, "bind": {}, "events": [], "children": [{ "value": "(busy ? gwText('Saving\u2026') : gwText('Changes saved automatically'))" }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('remove');", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Remove'))" }] }] }] }], "movable": true }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const draft = model(options);
  const emit = options.emit;
  const ranges = [{ key: "bright_radius", get name() {
    return text("Bright radius");
  }, max: 30, step: 0.5, min: 0 }, { key: "dim_radius", get name() {
    return text("Dim radius");
  }, max: 60, step: 0.5, min: 0 }, { key: "intensity", get name() {
    return text("Intensity");
  }, max: 1, step: 0.05, min: 0 }, { key: "angle", get name() {
    return text("Cover");
  }, max: 360, step: 5, min: 5 }, { key: "rotation", get name() {
    return text("Direction");
  }, max: 355, step: 5, min: 0 }];
  function unlimited(e) {
    draft.value.dim_radius = e.target.checked ? 0 : Math.max(6, draft.value.bright_radius);
    emit("change");
  }
  return { gwText: text, PhX: PhX4, PhTrash: PhTrash4, vMovableResizable, draft, ranges, unlimited, emit: options.emit };
});

// gravewright/maps/frontend/features/scene-layers/lib/shader-presets.js
var shaderPresets = [
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-1",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Arcane Sun");
    },
    get "description"() {
      return text("Radiant disk with a turbulent corona, long rays, and sparks.");
    },
    "color": "#8f6bff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;float d=length(p);float a0=atan(p.y,p.x);\nfloat corona=gwpFbm(vec2(a0*3.4,t*0.22)+vec2(d*5.0,-t*0.11));\nfloat core=exp(-d*d*6.2);float rim=gwpBand(d,0.61+0.035*sin(t*1.7),0.055);\nfloat rayMask=pow(max(0.0,cos(a0*9.0+t*0.9+corona*2.7)),10.0);\nfloat rays=rayMask*exp(-d*1.45)*(1.0-smoothstep(0.18,0.95,d));\nfloat sparks=pow(gwpNoise(p*18.0+vec2(t,-t*0.7)),16.0)*(1.0-smoothstep(0.28,1.0,d));\nfloat e=(core*1.15+rim*0.9+rays*0.72+sparks*0.45)*(0.78+0.32*corona)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.92,0.72),gwpSat(core+rim+rays*0.4));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1.1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-2",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Solar Star");
    },
    get "description"() {
      return text("Pulsing star with two flare patterns and a living corona.");
    },
    "color": "#ff9a32",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float d=length(p);float ang=atan(p.y,p.x);\nfloat disk=exp(-d*d*9.0);float pulse=0.82+0.18*sin(t*3.0);\nfloat flareA=pow(max(0.0,cos(ang*14.0-t*1.6)),22.0)*exp(-d*1.8);\nfloat flareB=pow(max(0.0,cos(ang*5.0+t*0.8)),12.0)*exp(-d*2.4);\nfloat crown=gwpBand(d,0.48+0.03*sin(ang*7.0+t*2.0),0.035);\nfloat grain=0.7+0.45*gwpFbm(p*7.0+vec2(t*0.25));\nfloat e=(disk*1.35*pulse+crown+flareA*0.9+flareB*0.45)*grain*uIntensity;\nfloat a=gwpSat(e);\nvec3 hot=mix(uColor,vec3(1.0,0.98,0.82),gwpSat(disk*1.5+crown));\nfinalColor=vec4(hot*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 0.9,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "orb-3",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Glacial Core");
    },
    get "description"() {
      return text("Hexagonal crystal with facets, spikes, and shimmering frost.");
    },
    "color": "#58cfff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;float d=length(p);float ang=atan(p.y,p.x);\nfloat facets=abs(cos(ang*3.0));\nfloat crystalR=0.52+0.13*facets;\nfloat shell=gwpBand(d,crystalR,0.035);\nfloat spokes=pow(abs(cos(ang*6.0)),18.0)*(1.0-smoothstep(0.08,0.82,d));\nfloat inner=exp(-d*d*13.0)*(0.8+0.2*sin(t*2.0));\nfloat frost=pow(gwpNoise(p*16.0-vec2(t*0.2)),10.0)*gwpDisk(p,0.75,0.2);\nfloat e=(shell*1.15+spokes*0.52+inner+frost*0.28)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.92,1.0,1.0),gwpSat(shell+inner+frost*0.4));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1.1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "orb-4",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Crimson Eye");
    },
    get "description"() {
      return text("Living arcane eye with an iris, vertical pupil, and pulsing veins.");
    },
    "color": "#ff253a",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;\np=gwpRot(p,0.08*sin(t*0.7));\nfloat d=length(p);\nfloat eye=1.0-smoothstep(0.0,0.055,abs(length(vec2(p.x,p.y*1.8))-0.63));\nfloat iris=gwpBand(d,0.34+0.025*sin(t*1.7),0.12)*(0.65+0.35*gwpFbm(p*8.0+vec2(t*0.2)));\nfloat pupil=1.0-smoothstep(0.035,0.11,abs(p.x));\npupil*=gwpDisk(vec2(p.x,p.y*1.5),0.31,0.07);\nfloat veins=pow(max(0.0,sin(atan(p.y,p.x)*11.0+d*24.0+gwpFbm(p*5.0)*4.0)),12.0)*gwpDisk(p,0.62,0.12);\nfloat e=(eye*0.85+iris*0.9+veins*0.42)*(1.0-pupil*0.8)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.55,0.32),iris*0.65);\nc*=1.0-pupil*0.75;\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.6,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-5",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Spectral Moon");
    },
    get "description"() {
      return text("Spectral crescent with a halo, motes, and ghostly mist.");
    },
    "color": "#b9d5ff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.25;\nfloat d1=length(p-vec2(-0.06,0.0));\nfloat moon=gwpDisk(p-vec2(-0.06,0.0),0.58,0.08)*(1.0-gwpDisk(p-vec2(0.18,0.02),0.52,0.08));\nfloat halo=gwpBand(d1,0.61,0.13)*0.65;\nfloat ghosts=gwpFbm(p*4.5+vec2(t*0.18,-t*0.08))*gwpBand(d1,0.54,0.34);\nfloat motes=pow(gwpNoise(p*14.0+vec2(0.0,t*0.2)),18.0)*gwpDisk(p,0.9,0.2);\nfloat e=(moon+halo+ghosts*0.24+motes*0.38)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.94,0.98,1.0),moon+halo*0.45);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-1",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Violet Portal");
    },
    get "description"() {
      return text("Spiral ring with a turbulent inner surface.");
    },
    "color": "#9b55ff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;float d=length(p);float ang=atan(p.y,p.x);\nfloat warp=(gwpFbm(p*4.0+vec2(t))-0.5)*0.16;\nfloat ring=gwpBand(d,0.69+warp,0.06);\nfloat spiral=0.5+0.5*sin(ang*5.0-d*15.0+t*3.0+warp*10.0);\nfloat inner=(1.0-smoothstep(0.08,0.67,d))*(0.25+0.75*gwpFbm(gwpRot(p,t*0.15)*4.0));\nfloat e=(ring*(0.65+0.75*spiral)+inner*0.5)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0),ring*0.9);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.95,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "portal-2",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Infernal Rift");
    },
    get "description"() {
      return text("Jagged, glowing, unstable vertical rift.");
    },
    "color": "#ff3b18",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.1;\nvec2 q=gwpRot(p,0.17*sin(t*0.3));\nfloat jag=(gwpFbm(vec2(q.y*5.0,t*0.35))-0.5)*0.28;\nfloat crack=gwpLine(q.x+jag,0.055+0.018*sin(q.y*18.0+t*2.0));\nfloat body=crack*(1.0-smoothstep(0.82,1.05,abs(q.y)));\nfloat glow=exp(-abs(q.x+jag)*7.0)*(1.0-smoothstep(0.76,1.05,abs(q.y)));\nfloat teeth=pow(max(0.0,sin(q.y*19.0+t*1.7+gwpFbm(q*4.0)*3.0)),10.0)*glow;\nfloat e=(body*1.2+glow*0.65+teeth*0.38)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.72,0.22),body+teeth*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-3",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Fey Passage");
    },
    get "description"() {
      return text("A crown of petals and runes with a shimmering interior.");
    },
    "color": "#55e89b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;float d=length(p);float ang=atan(p.y,p.x);\nfloat petals=0.56+0.11*cos(ang*7.0+t*0.7);\nfloat wreath=gwpBand(d,petals,0.055);\nfloat runes=pow(max(0.0,cos(ang*14.0-t*0.4)),16.0)*gwpBand(d,0.73,0.09);\nfloat shimmer=(1.0-smoothstep(0.12,0.7,d))*(0.3+0.7*gwpFbm(p*5.0+vec2(t*0.15,-t*0.2)));\nfloat e=(wreath+runes*0.65+shimmer*0.34)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.95,1.0,0.82),wreath+runes*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 0.9,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-4",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Astral Hole");
    },
    get "description"() {
      return text("Empty core with gravitational lensing, a disk, and stars.");
    },
    "color": "#467cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;float d=length(p);float ang=atan(p.y,p.x);\nfloat hole=1.0-smoothstep(0.22,0.36,d);\nfloat lens=gwpBand(d,0.48+0.03*sin(ang*4.0+t),0.055);\nfloat acc=pow(0.5+0.5*sin(ang*4.0-d*22.0+t*2.2),5.0)*gwpBand(d,0.62,0.25);\nfloat stars=pow(gwpNoise(p*22.0+vec2(t*0.03)),24.0)*gwpDisk(p,0.88,0.12)*(1.0-hole);\nfloat e=(lens*1.15+acc*0.7+stars*0.7)*(1.0-hole*0.92)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.88,0.95,1.0),lens+stars);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.5,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "portal-5",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Golden Seal");
    },
    get "description"() {
      return text("Precise ritual geometry with rings, glyphs, and symmetrical rays.");
    },
    "color": "#ffc95b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;float d=length(p);float ang=atan(p.y,p.x);\nfloat r1=gwpBand(d,0.35,0.018);\nfloat r2=gwpBand(d,0.58,0.022);\nfloat r3=gwpBand(d,0.76,0.018);\nfloat spokes=pow(abs(cos(ang*6.0+t*0.25)),30.0)*step(0.34,d)*(1.0-step(0.76,d));\nfloat glyph=pow(max(0.0,cos(ang*12.0+t*0.15)),28.0)*gwpBand(d,0.67,0.065);\nvec2 q1=gwpRot(p,3.14159/6.0);\nvec2 q2=gwpRot(p,-3.14159/6.0);\nfloat triangle=gwpLine(max(abs(q1.x)*0.866+q1.y*0.5,q2.x*0.866-q2.y*0.5)-0.38,0.018);\nfloat e=(r1+r2+r3+spokes*0.45+glyph*0.8+triangle*0.3)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.96,0.7),gwpSat(r1+r2+r3+glyph));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 2.2,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-1",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Swamp Mist");
    },
    get "description"() {
      return text("Layered banks of damp mist that respond to light.");
    },
    "color": "#708f68",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;\nvec2 q=p*2.4+vec2(t*0.7,t*0.16);\nfloat low=gwpFbm(q+vec2(0.0,p.y*0.4));\nfloat high=gwpFbm(q*2.1-vec2(t*0.22,0.0));\nfloat bank=smoothstep(0.42,0.78,low+high*0.35);\nfloat strata=0.58+0.42*sin(p.y*5.0+low*4.0);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=bank*strata*uIntensity*0.7*mix(0.55,1.0,lit);\nvec3 c=mix(uColor,uColor+L.rgb*0.45,lit);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.9,
    "scale": 1.8,
    "speed": 1,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "fog-2",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Black Smoke");
    },
    get "description"() {
      return text("Turbulent columns of dense smoke rising and curling.");
    },
    "color": "#30343d",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.28;\nvec2 q=vec2(p.x*2.2,p.y*1.25+t*0.55);\nfloat curl=gwpFbm(q*2.0+vec2(gwpFbm(q+3.0),-gwpFbm(q-4.0)));\nfloat columns=gwpFbm(vec2(p.x*4.0,p.y*1.2+t*0.45));\nfloat smoke=smoothstep(0.32,0.74,curl*0.7+columns*0.5);\nfloat feather=1.0-smoothstep(0.65,1.12,length(vec2(p.x*0.9,p.y*0.6)));\nvec4 L=gwLight(vTextureCoord);\nfloat a=smoke*feather*uIntensity*0.82;\nvec3 c=mix(uColor*0.55,uColor+L.rgb*0.12,clamp(L.a,0.0,1.0));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.58,
    "intensity": 0.8,
    "scale": 2.5,
    "speed": 0.55,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-3",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Frost Mist");
    },
    get "description"() {
      return text("Low mist with suspended ice crystals.");
    },
    "color": "#a8dcf0",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nfloat floorBand=1.0-smoothstep(-0.95,0.65,p.y);\nfloat curls=gwpFbm(vec2(p.x*3.0+t*0.3,p.y*5.0)+vec2(sin(p.y*5.0+t)*0.3,0.0));\nfloat mist=smoothstep(0.46,0.77,curls)*floorBand;\nfloat crystals=pow(gwpNoise(p*18.0+vec2(t*0.12,0.0)),20.0)*floorBand;\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=(mist*0.55+crystals*0.28)*uIntensity*mix(0.65,1.0,lit);\nvec3 c=mix(uColor,vec3(0.94,1.0,1.0),crystals+lit*0.18);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.76,
    "intensity": 0.9,
    "scale": 1.6,
    "speed": 1,
    "rotation": 0,
    "radius": 9,
    "enabled": true,
    "id": "fog-4",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Purple Miasma");
    },
    get "description"() {
      return text("Cellular toxic gas with bubbles and internal veins.");
    },
    "color": "#9a45b8",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;\nvec2 q=p*4.0+vec2(-t*0.5,t*0.22);\nvec2 cell=floor(q);vec2 f=fract(q)-0.5;\nfloat h=gwpHash(cell);\nvec2 drift=vec2(sin(t+h*8.0),cos(t*0.7+h*11.0))*0.18;\nfloat bubble=exp(-dot(f+drift,f+drift)*(12.0+18.0*h));\nfloat cloud=smoothstep(0.4,0.72,gwpFbm(p*3.0+vec2(t*0.16)));\nfloat veins=pow(max(0.0,sin((p.x-p.y)*9.0+t*1.6+cloud*4.0)),8.0);\nfloat e=(bubble*0.7+cloud*0.65+veins*cloud*0.15)*uIntensity;\nfloat a=min(e,0.76);\nvec3 c=mix(uColor,vec3(0.65,1.0,0.45),bubble*0.12);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.5,
    "intensity": 0.8,
    "scale": 2,
    "speed": 0.45,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-5",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Ancient Dust");
    },
    get "description"() {
      return text("Suspended motes, haze, and faint backlit shafts.");
    },
    "color": "#b69a70",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;\nvec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf.y+=fract(t*0.18+h)-0.5;\nf.x+=sin(t*0.7+h*20.0)*0.12;\nfloat mote=exp(-dot(f,f)*(75.0+90.0*h))*step(0.56,h);\nfloat haze=smoothstep(0.52,0.82,gwpFbm(p*2.1+vec2(t*0.05,0.0)));\nfloat shafts=pow(max(0.0,0.5+0.5*sin((p.x+p.y*0.35)*7.0+t*0.15)),10.0)*0.12;\nvec4 L=gwLight(vTextureCoord);float lit=clamp(L.a,0.0,1.0);\nfloat a=(mote*0.85+haze*0.22+shafts)*uIntensity*mix(0.35,1.0,lit);\nvec3 c=mix(uColor,uColor+L.rgb*0.7,lit);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-1",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Campfire");
    },
    get "description"() {
      return text("Broad flame with irregular tongues and rising embers.");
    },
    "color": "#ff6a18",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float y=p.y+0.72;\nfloat sway=(gwpFbm(vec2(y*3.0,t*0.8))-0.5)*0.35;\nfloat width=max(0.08,0.68-(y+0.1)*0.5);\nfloat body=1.0-smoothstep(width*0.35,width,abs(p.x+sway));\nbody*=smoothstep(-0.35,-0.05,y)*(1.0-smoothstep(0.1,1.12,y));\nfloat tongues=0.55+0.55*gwpFbm(vec2((p.x+sway)*5.0,y*4.0-t*1.8));\nfloat ember=pow(gwpNoise(p*16.0-vec2(0.0,t*2.0)),18.0)*smoothstep(-0.3,0.9,y);\nfloat a=gwpSat((body*tongues+ember*0.25)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,0.95,0.55),gwpSat(body*(1.0-y*0.45)));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 0.9,
    "speed": 1.1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-2",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Blue Flame");
    },
    get "description"() {
      return text("Narrow blue jet with a white core and fast oscillation.");
    },
    "color": "#299cff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.25;float y=p.y+0.78;\nfloat wiggle=sin(y*7.0-t*2.2)*0.05+(gwpNoise(vec2(y*5.0,t))-0.5)*0.12;\nfloat cone=max(0.045,0.34-(y+0.15)*0.2);\nfloat outer=1.0-smoothstep(cone*0.55,cone,abs(p.x+wiggle));\nouter*=smoothstep(-0.3,-0.05,y)*(1.0-smoothstep(0.12,1.18,y));\nfloat core=1.0-smoothstep(cone*0.12,cone*0.42,abs(p.x+wiggle*0.4));\ncore*=1.0-smoothstep(0.05,0.82,y);\nfloat a=gwpSat((outer*0.7+core)*uIntensity);\nvec3 c=mix(uColor,vec3(0.92,0.98,1.0),core);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-3",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Green Fire");
    },
    get "description"() {
      return text("Bubbling alchemical combustion with green flames.");
    },
    "color": "#52e858",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;float y=p.y+0.65;\nfloat bubbling=0.18*sin(p.x*12.0+t*3.0)+0.12*sin(p.x*23.0-t*2.0);\nfloat w=max(0.09,0.56-(y+0.12)*0.4+bubbling*0.18);\nfloat flame=1.0-smoothstep(w*0.45,w,abs(p.x+(gwpFbm(vec2(y*5.0,t))-0.5)*0.28));\nflame*=smoothstep(-0.42,-0.08,y)*(1.0-smoothstep(0.0,0.9,y));\nfloat bubbles=pow(gwpNoise(p*12.0+vec2(t*0.3,-t*1.4)),14.0)*gwpDisk(vec2(p.x,y-0.05),0.72,0.22);\nfloat a=gwpSat((flame*(0.6+0.7*gwpFbm(p*6.0-vec2(0.0,t)))+bubbles*0.35)*uIntensity);\nvec3 c=mix(uColor,vec3(0.85,1.0,0.35),bubbles+flame*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 0.85,
    "intensity": 0.8,
    "scale": 1.05,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-4",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Dark Ember");
    },
    get "description"() {
      return text("Dark fire pierced by charcoal and red embers.");
    },
    "color": "#d52b20",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;float y=p.y+0.7;\nfloat drift=(gwpFbm(vec2(y*3.0,t*0.4))-0.5)*0.42;\nfloat w=max(0.07,0.5-(y+0.2)*0.38);\nfloat silhouette=1.0-smoothstep(w*0.4,w,abs(p.x+drift));\nsilhouette*=smoothstep(-0.38,-0.05,y)*(1.0-smoothstep(0.0,0.82,y));\nfloat holes=smoothstep(0.48,0.8,gwpFbm(p*7.0-vec2(0.0,t*0.7)));\nfloat ember=pow(gwpNoise(p*18.0+vec2(t*0.2,-t)),20.0)*silhouette;\nfloat a=gwpSat((silhouette*(0.48+0.35*holes)+ember*0.7)*uIntensity);\nvec3 c=mix(uColor*0.38,vec3(1.0,0.16,0.04),ember+silhouette*(1.0-holes)*0.2);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "flame-5",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Sacred Fire");
    },
    get "description"() {
      return text("Symmetrical flame with a halo and golden rays.");
    },
    "color": "#ffd35a",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;float y=p.y+0.72;\nfloat w=max(0.08,0.45-(y+0.05)*0.3);\nfloat flame=1.0-smoothstep(w*0.36,w,abs(p.x+sin(y*6.0+t)*0.06));\nflame*=smoothstep(-0.35,-0.08,y)*(1.0-smoothstep(0.0,1.05,y));\nfloat halo=gwpBand(length(p-vec2(0.0,-0.18)),0.62,0.12)*0.35;\nfloat rays=pow(max(0.0,cos(atan(p.y,p.x)*8.0+t*0.35)),22.0)*exp(-length(p)*2.1)*0.5;\nfloat a=gwpSat((flame+halo+rays)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,1.0,0.86),flame+halo*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 0.65,
    "intensity": 0.8,
    "scale": 1.4,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-1",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Water Reflection");
    },
    get "description"() {
      return text("Crossing wave caustics with small concentric ripples.");
    },
    "color": "#45a8d8",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;\nfloat w1=sin(p.x*8.0+t*1.7+p.y*2.3);\nfloat w2=sin(p.y*11.0-t*1.2+p.x*3.4);\nfloat w3=sin((p.x+p.y)*6.5+t*0.7);\nfloat caustic=pow(abs(w1+w2+w3)*0.333,5.0);\nfloat ripples=gwpBand(abs(sin(length(p-vec2(sin(t)*0.2,cos(t)*0.2))*18.0-t*2.0)),0.0,0.12);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=(caustic*0.72+ripples*0.15)*uIntensity*0.65;\nvec3 c=mix(uColor,vec3(0.78,0.96,1.0)+L.rgb*0.35,gwpSat(caustic+lit*0.25));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-2",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Ocean Abyss");
    },
    get "description"() {
      return text("Broad, crossing, deep waves with dark troughs.");
    },
    "color": "#164f83",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;\nfloat swell=0.5+0.5*sin(p.x*3.2+t*0.55+sin(p.y*2.4-t*0.2));\nfloat cross=0.5+0.5*sin(p.y*4.1-t*0.42+p.x*1.6);\nfloat trenches=smoothstep(0.38,0.72,gwpFbm(p*2.3+vec2(t*0.07,-t*0.04)));\nfloat foam=pow(abs(swell-cross),5.0)*0.32;\nfloat a=gwpSat((swell*0.3+cross*0.22+trenches*0.45+foam)*uIntensity*0.72);\nvec3 c=mix(uColor*0.45,uColor*1.15,foam+0.15*swell);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.7,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.9,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "liquid-3",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Acid Pool");
    },
    get "description"() {
      return text("Corrosive film with cellular bubbles and glowing veins.");
    },
    "color": "#78d934",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;\nvec2 q=p*6.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;\nfloat h=gwpHash(cell);float r=0.12+0.28*h;\nfloat bubble=gwpBand(length(f+vec2(sin(t+h*8.0),cos(t*0.6+h*10.0))*0.12),r,0.055);\nfloat film=gwpFbm(p*5.0+vec2(t*0.18));\nfloat veins=pow(max(0.0,sin((p.x-p.y)*10.0+t+film*4.0)),9.0);\nfloat a=gwpSat((bubble*0.9+film*0.25+veins*0.18)*uIntensity*0.7);\nvec3 c=mix(uColor,vec3(0.9,1.0,0.18),bubble+veins*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.9,
    "intensity": 0.95,
    "scale": 1.3,
    "speed": 1,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "liquid-4",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Flowing Lava");
    },
    get "description"() {
      return text("Dark plates separated by moving incandescent veins.");
    },
    "color": "#ff4b18",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;\nfloat n=gwpFbm(p*3.2+vec2(t*0.18,-t*0.06));\nfloat n2=gwpFbm(p*7.0-vec2(t*0.1,t*0.12));\nfloat veins=pow(gwpSat(1.0-abs(n-n2)*3.2),6.0);\nfloat plates=smoothstep(0.43,0.62,n);\nfloat glow=veins*(0.75+0.25*sin(t*1.4+n*8.0));\nfloat a=gwpSat((plates*0.42+glow*1.1)*uIntensity*0.9);\nvec3 c=mix(vec3(0.22,0.025,0.01),uColor,plates);\nc=mix(c,vec3(1.0,0.82,0.22),glow);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.55,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.8,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-5",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Mercury");
    },
    get "description"() {
      return text("Metallic surface with specular ridges and liquid interference.");
    },
    "color": "#b9c5d2",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat h=sin(p.x*14.0+t)+sin(p.y*9.0-t*0.7)+sin((p.x+p.y)*17.0+t*0.35);\nh/=3.0;\nfloat ridges=pow(abs(h),9.0);\nfloat warp=gwpFbm(p*8.0+vec2(t*0.08));\nfloat spec=pow(gwpSat(0.5+0.5*sin(h*8.0+warp*5.0)),12.0);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=gwpSat((0.18+ridges*0.42+spec*0.65)*uIntensity*0.55);\nvec3 c=mix(uColor*0.7,vec3(1.0)+L.rgb*0.25,spec*0.8+lit*0.2);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.65,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-1",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Light Rain");
    },
    get "description"() {
      return text("Thin, subtle drops tilted by the wind.");
    },
    "color": "#9bc9e8",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;\nvec2 q=gwpRot(p,0.18)*vec2(14.0,8.0)+vec2(t*0.7,-t*3.2);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat streak=(1.0-smoothstep(0.025,0.06,abs(f.x-h)))*\n             (1.0-smoothstep(0.0,0.55,fract(f.y+h)));\nfloat e=streak*step(0.52,h)*uIntensity;\nfloat a=min(e,0.62);\nvec3 c=mix(uColor,vec3(0.88,0.96,1.0),h*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.85,
    "intensity": 0.9,
    "scale": 1.7,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-2",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Storm");
    },
    get "description"() {
      return text("Heavy rain with clouds and occasional flashes.");
    },
    "color": "#b6d9ef",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.4;\nvec2 q=gwpRot(p,0.32)*vec2(20.0,6.0)+vec2(t*1.8,-t*5.6);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat rain=(1.0-smoothstep(0.045,0.1,abs(f.x-h)))*\n           (1.0-smoothstep(0.08,0.8,fract(f.y+h)))*step(0.30,h);\nfloat flash=pow(max(0.0,sin(t*0.37+floor(t*0.37)*4.1)),32.0);\nfloat cloud=smoothstep(0.42,0.72,gwpFbm(p*2.2+vec2(t*0.08)))*0.18;\nfloat a=gwpSat((rain*1.35+cloud+flash*0.28)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),flash*0.8);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.8,
    "intensity": 0.8,
    "scale": 1.9,
    "speed": 0.8,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-3",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Blizzard");
    },
    get "description"() {
      return text("Large flakes and ice crystals blown in a whirlwind.");
    },
    "color": "#edf7ff",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;\nvec2 q=p*9.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat phase=t*(0.25+0.65*h);\nf+=vec2(sin(phase+h*20.0)*0.42,fract(phase*0.45+h)-0.5);\nfloat d=length(f);\nfloat flake=exp(-d*d*(26.0+45.0*h))*step(0.36,h);\nfloat cross=(gwpLine(f.x,0.025)+gwpLine(f.y,0.025))*exp(-d*d*22.0)*step(0.72,h);\nfloat a=gwpSat((flake+cross*0.5)*uIntensity*0.8);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.62,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 0.6,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-4",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Ash");
    },
    get "description"() {
      return text("Flat fragments tumbling slowly in dark haze.");
    },
    "color": "#77736e",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;\nvec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat fall=fract(t*0.2+h);\nf.y+=fall-0.5;\nf.x+=sin(t+h*18.0)*0.18;\nfloat angle=t*0.7+h*6.28;\nvec2 r=gwpRot(f,angle);\nfloat shard=exp(-(r.x*r.x*120.0+r.y*r.y*35.0))*step(0.42,h);\nfloat haze=smoothstep(0.56,0.8,gwpFbm(p*2.5+vec2(t*0.04)))*0.18;\nfloat a=gwpSat((shard+haze)*uIntensity*0.62);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.75,
    "intensity": 0.8,
    "scale": 1.7,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-5",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Arcane Rain");
    },
    get "description"() {
      return text("Magical trails rising and leaving fleeting runes.");
    },
    "color": "#b75cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;\nvec2 q=gwpRot(p,-0.14)*vec2(15.0,8.0)+vec2(-t*0.45,t*2.6);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat streak=(1.0-smoothstep(0.03,0.07,abs(f.x-h)))*\n             (1.0-smoothstep(0.0,0.5,fract(1.0-f.y+h)))*step(0.55,h);\nfloat rune=pow(max(0.0,cos((f.x+f.y)*12.0+h*20.0+t)),14.0)*step(0.82,h);\nfloat a=gwpSat((streak+rune*0.5)*uIntensity*0.78);\nvec3 c=mix(uColor,vec3(0.9,0.7,1.0),rune);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.8,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-1",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Fireflies");
    },
    get "description"() {
      return text("Organic lights wandering and blinking out of phase.");
    },
    "color": "#ffd95a",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;\nvec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf+=vec2(sin(t*0.9+h*21.0),cos(t*0.63+h*17.0))*0.28;\nfloat dotv=exp(-dot(f,f)*(55.0+35.0*h))*step(0.48,h);\nfloat blink=pow(0.5+0.5*sin(t*3.0+h*30.0),3.0);\nfloat a=gwpSat(dotv*blink*uIntensity*1.2);\nvec3 c=mix(uColor,vec3(1.0,0.96,0.62),blink*0.7);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.6,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-2",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Spores");
    },
    get "description"() {
      return text("Soft spheres rising slowly with occasional halos.");
    },
    "color": "#8dcc73",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;\nvec2 q=p*8.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf.y+=fract(t*0.18+h)-0.5;\nf.x+=sin(t*0.5+h*12.0)*0.22;\nfloat big=exp(-dot(f,f)*(24.0+24.0*h))*step(0.38,h);\nfloat halo=exp(-dot(f,f)*8.0)*step(0.78,h)*0.22;\nfloat a=gwpSat((big+halo)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.72,1.0,0.65),halo);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1.15,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "particles-3",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Sparks");
    },
    get "description"() {
      return text("Ballistic trails with incandescent heads and short tails.");
    },
    "color": "#ff8b24",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.2;\nvec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat age=fract(t*0.42+h);\nf.y+=age*1.2-0.62;\nf.x+=sin(age*3.14+h*8.0)*0.18;\nvec2 r=gwpRot(f,-0.28+0.4*h);\nfloat streak=exp(-(r.x*r.x*140.0+r.y*r.y*18.0))*step(0.60,h)*(1.0-age);\nfloat head=exp(-dot(f,f)*120.0)*step(0.6,h);\nfloat a=gwpSat((streak+head*0.7)*uIntensity*1.25);\nvec3 c=mix(uColor,vec3(1.0,0.95,0.55),head);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.25,
    "speed": 0.75,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-4",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Souls");
    },
    get "description"() {
      return text("Floating spectral silhouettes with tails and glowing eyes.");
    },
    "color": "#55bfff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.3;\nvec2 q=p*4.5;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf+=vec2(sin(t*0.65+h*14.0)*0.32,fract(t*0.12+h)-0.5);\nfloat head=exp(-dot(f-vec2(0.0,-0.08),f-vec2(0.0,-0.08))*26.0)*step(0.42,h);\nfloat tail=exp(-(f.x*f.x*18.0+(f.y-0.22)*(f.y-0.22)*5.0))*step(0.42,h)*(0.6+0.4*sin(t+h*20.0));\nfloat eyes=\n    (exp(-dot(f-vec2(-0.07,-0.11),f-vec2(-0.07,-0.11))*260.0)+\n     exp(-dot(f-vec2(0.07,-0.11),f-vec2(0.07,-0.11))*260.0))*step(0.75,h);\nfloat a=gwpSat((head*0.65+tail*0.5+eyes)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),eyes);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.3,
    "speed": 0.5,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "particles-5",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Cosmic Dust");
    },
    get "description"() {
      return text("Star field with crosses, twinkling, and a faint nebula.");
    },
    "color": "#a88cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nvec2 q=p*15.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat star=exp(-dot(f,f)*(120.0+120.0*h))*step(0.68,h);\nfloat twinkle=pow(0.5+0.5*sin(t*5.0+h*40.0),5.0);\nfloat cross=(gwpLine(f.x,0.012)+gwpLine(f.y,0.012))*exp(-dot(f,f)*35.0)*step(0.9,h);\nfloat nebula=smoothstep(0.52,0.78,gwpFbm(p*2.1+vec2(t*0.03,-t*0.02)))*0.16;\nfloat a=gwpSat((star*twinkle+cross*0.4+nebula)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),star*twinkle*0.8);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-1",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Arcane Grid");
    },
    get "description"() {
      return text("Hexagonal mesh with pulsing nodes instead of a simple grid.");
    },
    "color": "#655cff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;\nvec2 q=p*4.5;\nvec2 hq=vec2(q.x+q.y*0.57735,q.y*1.1547);\nvec2 f=abs(fract(hq)-0.5);\nfloat hex=1.0-smoothstep(0.43,0.48,max(f.x,f.y));\nfloat edge=smoothstep(0.31,0.42,max(f.x,f.y))*hex;\nvec2 local=fract(hq)-0.5;\nfloat node=exp(-dot(local,local)*75.0);\nfloat pulse=0.55+0.45*sin(t*2.0+floor(hq.x)+floor(hq.y));\nfloat a=gwpSat((edge*0.52+node*pulse*0.85)*uIntensity*0.72);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.7,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-2",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Hologram");
    },
    get "description"() {
      return text("Digital grid with scanlines, glitches, and glowing nodes.");
    },
    "color": "#24d9e8",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;\nvec2 q=p*8.0;vec2 f=abs(fract(q)-0.5);\nfloat grid=(1.0-smoothstep(0.04,0.08,min(f.x,f.y)))*0.45;\nfloat scan=pow(0.5+0.5*sin((p.y-t)*18.0),12.0);\nfloat glitch=step(0.82,gwpNoise(vec2(floor(p.y*18.0),floor(t*6.0))))*0.22;\nvec2 local=fract(q)-0.5;\nfloat nodes=exp(-dot(local,local)*90.0)*(0.4+0.6*sin(t*4.0));\nfloat a=gwpSat((grid+scan*0.7+glitch+nodes*0.5)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.85,1.0,1.0),scan);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.62,
    "intensity": 0.8,
    "scale": 1.15,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-3",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Circuit");
    },
    get "description"() {
      return text("Pseudorandom orthogonal tracks with data pads.");
    },
    "color": "#45e078",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;\nvec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat horiz=gwpLine(f.y-(step(0.5,h)-0.5)*0.34,0.035)*step(0.35,h);\nfloat vert=gwpLine(f.x-(step(0.72,h)-0.5)*0.34,0.035)*step(0.52,1.0-h);\nfloat pad=exp(-dot(f,f)*120.0)*step(0.76,h);\nfloat data=0.45+0.55*sin(t*5.0+cell.x*0.7+cell.y*1.3);\nfloat a=gwpSat((horiz*0.55+vert*0.55+pad*data)*uIntensity*0.62);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "grid-4",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Runic Prison");
    },
    get "description"() {
      return text("Concentric rings, radial bars, and pulsing glyphs.");
    },
    "color": "#ed3948",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat rings=gwpBand(d,0.38,0.025)+gwpBand(d,0.68,0.025)+gwpBand(d,0.9,0.018);\nfloat bars=pow(abs(cos(ang*4.0)),24.0)*step(0.32,d)*(1.0-step(0.93,d));\nfloat glyph=pow(max(0.0,cos(ang*8.0+t*0.5)),24.0)*gwpBand(d,0.78,0.055);\nfloat flash=0.65+0.35*sin(t*2.0+d*12.0);\nfloat a=gwpSat((rings+bars*0.55+glyph*0.85)*flash*uIntensity*0.82);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.38,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.45,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-5",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Ghost Board");
    },
    get "description"() {
      return text("Alternating spectral squares slowly appearing and disappearing.");
    },
    "color": "#c4d6e8",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;\nvec2 q=floor(p*6.0);\nfloat checker=mod(q.x+q.y,2.0);\nfloat fade=0.28+0.24*sin(t*1.5+q.x*0.7-q.y*0.4);\nvec2 f=abs(fract(p*6.0)-0.5);\nfloat seams=1.0-smoothstep(0.44,0.49,max(f.x,f.y));\nfloat ghost=(checker*0.32+seams*0.18)*fade;\nfloat drift=gwpFbm(p*2.0+vec2(t*0.03))*0.1;\nfloat a=gwpSat((ghost+drift)*uIntensity*0.38);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-1",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Whirlpool");
    },
    get "description"() {
      return text("Water spiral with foam and concentric rings.");
    },
    "color": "#3b9fd1",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat n=gwpFbm(vec2(d*4.0,ang*1.5+t*0.4));\nfloat spiral=pow(0.5+0.5*sin(ang*6.0-d*17.0+t*2.0+n*2.0),3.0);\nfloat basin=smoothstep(0.1,0.22,d)*(1.0-smoothstep(0.72,1.1,d));\nfloat foam=pow(spiral,2.0)*basin;\nfloat rings=(gwpBand(d,0.42,0.025)+gwpBand(d,0.7,0.03))*0.3;\nfloat a=gwpSat((foam+rings)*uIntensity);\nvec3 c=mix(uColor,vec3(0.78,0.96,1.0),foam*0.55);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.9,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-2",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Singularity");
    },
    get "description"() {
      return text("Black hole with an accretion disk and gravitational lensing.");
    },
    "color": "#7038c8",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat hole=1.0-smoothstep(0.17,0.33,d);\nfloat disk=gwpBand(d,0.53,0.16)*(0.5+0.5*sin(ang*9.0-d*27.0+t*1.4));\nfloat lens=gwpBand(d,0.36,0.025)+gwpBand(d,0.78,0.018)*0.45;\nfloat sparks=pow(gwpNoise(vec2(ang*8.0,d*15.0+t)),18.0)*gwpBand(d,0.62,0.22);\nfloat e=(disk*1.2+lens+sparks*0.65)*(1.0-hole)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0),lens+sparks*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "vortex-3",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Sand Cyclone");
    },
    get "description"() {
      return text("Tapered sand column with turbulent bands and grains.");
    },
    "color": "#b79058",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;\nfloat y=p.y;\nfloat taper=0.24+0.52*(1.0-gwpSat((y+1.0)*0.5));\nfloat ang=atan(p.y,p.x);\nfloat bands=pow(0.5+0.5*sin(ang*11.0-length(p)*18.0+t*2.5+gwpFbm(p*5.0)*4.0),2.0);\nfloat column=1.0-smoothstep(taper,taper+0.22,abs(p.x));\nfloat grains=pow(gwpNoise(p*18.0+vec2(t*0.3,-t)),12.0)*column;\nfloat a=gwpSat((bands*column*0.52+grains*0.35)*uIntensity*0.85);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-4",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Green Tempest");
    },
    get "description"() {
      return text("Poisonous vortex with thick arms and internal eddies.");
    },
    "color": "#4fc96b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.9;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat n=gwpFbm(gwpRot(p,t*0.1)*6.0);\nfloat arms=pow(0.5+0.5*sin(ang*7.0-d*30.0+t*3.2+n*5.0),2.5);\nfloat eddies=pow(gwpFbm(p*10.0+vec2(t*0.12)),2.0);\nfloat body=smoothstep(0.1,0.2,d)*(1.0-smoothstep(0.72,1.2,d));\nfloat a=gwpSat((arms*0.72+eddies*0.32)*body*uIntensity*0.9);\nvec3 c=mix(uColor,vec3(0.7,1.0,0.38),eddies*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.55,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "vortex-5",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Galaxy");
    },
    get "description"() {
      return text("Spiral galaxy with arms, a central bulge, stars, and dust.");
    },
    "color": "#826cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat arm=pow(0.5+0.5*cos(ang*4.0-d*12.0+t*0.7),7.0)*exp(-d*1.5);\nfloat dust=gwpFbm(vec2(ang*2.0-d*3.0,d*8.0+t*0.15))*arm;\nvec2 q=p*18.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat stars=exp(-dot(f,f)*180.0)*step(0.74,h)*gwpDisk(p,1.05,0.12);\nfloat bulge=exp(-d*d*10.0);\nfloat a=gwpSat((arm*0.75+dust*0.42+stars+bulge*0.65)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,0.92,0.76),bulge+stars*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-1",
    "category": "Auras",
    get "name"() {
      return text("Sacred Aura");
    },
    get "description"() {
      return text("Golden halo with outer rays and rising motes.");
    },
    "color": "#ffd86a",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat halo=gwpBand(d,0.72+0.025*sin(t*2.0),0.055);\nfloat rays=pow(max(0.0,cos(ang*6.0+t*0.3)),18.0)*gwpBand(d,0.78,0.24);\nfloat inner=exp(-d*d*3.2)*0.18;\nfloat motes=pow(gwpNoise(p*16.0-vec2(0.0,t*0.3)),20.0)*gwpBand(d,0.6,0.38);\nfloat a=gwpSat((halo+rays*0.5+inner+motes*0.3)*uIntensity*0.78);\nvec3 c=mix(uColor,vec3(1.0,1.0,0.86),halo+rays*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-2",
    "category": "Auras",
    get "name"() {
      return text("Dark Aura");
    },
    get "description"() {
      return text("Smoky outline with inward-facing purple-black tendrils.");
    },
    "color": "#5b337e",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat wob=(gwpFbm(vec2(ang*5.0,t*0.4))-0.5)*0.15;\nfloat rim=gwpBand(d,0.68+wob,0.09);\nfloat tendrils=pow(max(0.0,sin(ang*9.0+d*17.0-t*2.0+gwpFbm(p*6.0)*4.0)),5.0)*gwpBand(d,0.55,0.32);\nfloat inner=exp(-d*d*2.0)*0.36;\nfloat a=gwpSat((rim*0.8+tendrils*0.5+inner)*uIntensity*0.82);\nvec3 c=mix(uColor*0.48,uColor,rim);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.65,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-3",
    "category": "Auras",
    get "name"() {
      return text("Arcane Shield");
    },
    get "description"() {
      return text("Precise hexagonal barrier with scanlines, nodes, and inner rings.");
    },
    "color": "#438cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat hexR=0.77/max(abs(cos(mod(ang+0.523599,1.047198)-0.523599)),0.5);\nfloat shell=gwpBand(d,hexR,0.028);\nfloat rings=gwpBand(d,0.58,0.018)*0.45;\nfloat scan=gwpBand(p.y,0.62*sin(t*2.0),0.025)*gwpDisk(p,0.82,0.08);\nfloat nodes=pow(max(0.0,cos(ang*6.0)),28.0)*gwpBand(d,0.77,0.07);\nfloat a=gwpSat((shell+rings+scan*0.55+nodes*0.7)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.9,0.98,1.0),shell+nodes);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.68,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.9,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-4",
    "category": "Auras",
    get "name"() {
      return text("Poison");
    },
    get "description"() {
      return text("Pulsing toxic cloud with distinct bubbles around its origin.");
    },
    "color": "#6fbf37",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;\nfloat d=length(p);\nfloat cloud=smoothstep(0.4,0.72,gwpFbm(p*5.0+vec2(t*0.18,-t*0.08)))*\n            (1.0-smoothstep(0.58,0.92,d));\nvec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat bubble=gwpBand(length(f),0.18+0.15*h,0.05)*step(0.45,h);\nfloat pulse=0.72+0.28*sin(t*2.5+d*7.0);\nfloat a=gwpSat((cloud*0.75+bubble*0.48)*pulse*uIntensity*0.7);\nvec3 c=mix(uColor,vec3(0.82,1.0,0.28),bubble*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-5",
    "category": "Auras",
    get "name"() {
      return text("Blood Aura");
    },
    get "description"() {
      return text("Crimson halo with radial spikes, drops, and an aggressive pulse.");
    },
    "color": "#d9263c",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat pulse=0.68+0.12*sin(t*5.0);\nfloat rim=gwpBand(d,0.69+pulse*0.04,0.055);\nfloat spikes=pow(max(0.0,cos(ang*11.0+t*0.8)),10.0)*gwpBand(d,0.75,0.22);\nfloat drops=pow(gwpNoise(vec2(ang*8.0,t*0.2+d*5.0)),14.0)*gwpBand(d,0.62,0.3);\nfloat inner=exp(-d*d*4.0)*0.2;\nfloat a=gwpSat((rim*0.9+spikes*0.55+drops*0.4+inner)*uIntensity*0.8);\nvec3 c=mix(uColor,vec3(0.85,0.05,0.08),drops+spikes*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  }
];

// gravewright/maps/frontend/features/effects/model/shader-source.js
function normalizeShaderSource(value) {
  const lines = value.replace(/\r\n?/g, "\n").trim().split("\n");
  const output = [];
  let blockComment = false, continuation = false;
  for (const line of lines) {
    const markerLine = line.replace(/\\([`'~])/g, "$1").replace(/[\u200B\uFEFF]/g, "").replace(/[‘’]/g, "'").replace(/\\[ \t]*$/, "");
    if (!blockComment && !continuation && /^[ \t]*(`{3,}|~{3,}|'{3,})[ \t]*([\w.+#-]+(?:[ \t]+[\w.+#-]+)*)?[ \t]*$/.test(markerLine)) continue;
    const directive = continuation || !blockComment && /^[ \t]*#/.test(line);
    let clean = "", quote = "";
    for (let i = 0; i < line.length; i++) {
      const char = line[i], next = line[i + 1];
      if (blockComment) {
        clean += char;
        if (char === "*" && next === "/") {
          clean += next;
          i++;
          blockComment = false;
        }
      } else if (quote) {
        clean += char;
        if (char === "\\" && next) {
          clean += next;
          i++;
        } else if (char === quote) quote = "";
      } else if (char === "/" && next === "/") {
        clean += line.slice(i);
        break;
      } else if (char === "/" && next === "*") {
        clean += "/*";
        i++;
        blockComment = true;
      } else if (char === '"' || char === "'") {
        quote = char;
        clean += char;
      } else if (char === "\\" && !directive) {
        if (/^[ \t]*$/.test(line.slice(i + 1))) break;
        if (/[\\`*_{}\[\]()#+\-.!<>|]/.test(next || "")) {
          clean += next;
          i++;
        } else clean += char;
      } else if (char !== "\u200B" && char !== "\uFEFF") clean += char === "\xA0" ? " " : char;
    }
    output.push(clean);
    continuation = directive && /\\[ \t]*$/.test(line);
  }
  return output.join("\n").trim();
}

// gravewright/maps/frontend/features/effects/model/shader-prompt.js
var shaderPrompt = "Write a generative GLSL ES 3.00 fragment shader for Gravewright.\n\nOUTPUT CONTRACT \u2014 RAW SOURCE FILE\nYour entire reply will be pasted directly into a GLSL compiler, not a Markdown renderer.\nReturn exactly one complete, compilable shader source as plain text.\nDo not use Markdown: no code fences (including glsl fences), headings, lists, blockquotes, inline backticks, or explanatory paragraphs.\nDo not escape GLSL operators for Markdown (write * directly, never backslash-star), and do not add backslashes at the ends of source lines. Do not label any part as arduino, cpp, java, or another language.\nDo not split the shader into snippets. Do not include a filename, language label, introduction, conclusion, or instructions for copying it.\nStart directly with GLSL source. Keep top-level declarations at column 1; indent only inside functions. End immediately after the final closing brace.\nReturn helper functions and exactly one void main(). Do not include #version, precision, uniform/input/output declarations: the engine supplies them.\nBefore replying, silently verify that the entire response can be pasted unchanged into the source field. Output only that source.\n\nRENDERING CONTRACT\nThe shader draws a transparent frame over the map. It does not receive the scene image. The frame already matches the range and is clipped by range, walls, and doors; do not implement this clipping in GLSL. Always write premultiplied alpha: finalColor = vec4(color * a, a). The engine applies blending afterward: Normal, Add, Multiply, or Screen. Do not implement blending in the shader.\n\nALREADY AVAILABLE: DO NOT DECLARE\n  in vec2 vTextureCoord;\n  out vec4 finalColor;\n  uniform sampler2D uTexture;      // white frame texture, not the map\n  uniform sampler2D uLightBuffer;  // accumulated scene lighting\n  uniform float uTime;            // seconds, resets every hour\n  uniform float uIntensity;       // 0..1, internal effect strength\n  uniform float uOpacity;         // 0..1, applied automatically after main()\n  uniform float uScale;           // 0.1..20\n  uniform float uSpeed;           // 0..8\n  uniform vec3 uColor;            // channels 0..1\n  uniform vec2 uResolution;       // frame size in pixels\n  uniform float uAspect;\n  uniform vec2 uOrigin;           // origin in world coordinates\n  uniform float uRadius;          // world range; 0 = entire scene\n  uniform float uRotation;        // radians\n  uniform vec3 uCamera;           // x/y offset and zoom\n  uniform vec2 uScreen;           // screen size in pixels\n  vec2 gwScreen(vec2 uv);         // screen pixel\n  vec2 gwScreenUV(vec2 uv);       // screen position 0..1\n  vec2 gwWorld(vec2 uv);          // world point; stays fixed during pan/zoom\n  vec2 gwRotated(vec2 uv);        // world rotated around uOrigin\n  float gwFeature();             // feature size tied to range and uScale\n  vec2 gwPattern(vec2 uv);        // (gwRotated(uv) - uOrigin) / gwFeature(); returns (0,0) at the click\n  vec4 gwLight(vec2 uv);          // rgb = light color; a = intensity\n\nRULES\n1. Build patterns in gwPattern(vTextureCoord): it returns exactly vec2(0.0) at the clicked point, which is always the effect's center/start. Use gwWorld/gwRotated only for absolute world coordinates. Do not use raw vTextureCoord for map-bound patterns or subtract uOrigin from gwPattern again.\n2. Use uTime * uSpeed for animation, uIntensity for internal strength/alpha, and uColor as the dominant color. uScale already affects gwFeature(); do not apply it again with gwPattern.\n3. The engine multiplies finalColor by uOpacity after main(). Do not multiply by uOpacity, or transparency will be applied twice.\n4. gwLight(vTextureCoord) is optional. Use it for effects that respond to lights. Do not make effects disappear completely without light unless requested.\n5. Use GLSL ES 3.00 syntax and explicit, compatible types. Define every helper you call. Do not use Shadertoy mainImage, iTime, iResolution, or gl_FragColor.\n6. In smoothstep(edge0, edge1, x), keep edge0 < edge1. Invert with 1.0 - smoothstep(low, high, x); reversed edges have undefined results.\n7. Avoid division by zero, NaN/Inf, unbounded loops, and excessive per-pixel work. Multiple shaders may run simultaneously. Code can contain up to 32,000 characters.\n\nDESIRED EFFECT\n<describe appearance, motion, density, and lighting behavior here>\n\nFINAL REMINDER\nReply with raw GLSL only, from the first source line to the last closing brace. No Markdown or surrounding text.";

// gravewright/maps/frontend/features/effects/ui/shader-prompt-dialog.js
function shaderInstructions(description) {
  return shaderPrompt.replace("<describe appearance, motion, density, and lighting behavior here>", () => description.trim());
}
function shaderSource(value) {
  const source = normalizeShaderSource(value);
  const code = source.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, "");
  if (!source) throw new Error(text("Paste the GLSL code returned by your AI. The field is empty."));
  if (source.length > 32e3) throw new Error(text("The shader exceeds the limit of 32,000 characters. Ask your AI for a shorter version."));
  if (!/\bvoid\s+main\s*\(\s*(?:void\s*)?\)/.test(code)) {
    throw new Error(text("The pasted code does not contain void main(). Copy the complete shader, including its main function."));
  }
  return source;
}
function openShaderPrompt(onInsert, onClose) {
  const previousFocus = document.activeElement;
  const dialog = document.createElement("dialog");
  dialog.className = "shader-prompt-dialog";
  dialog.setAttribute("aria-labelledby", "shader-prompt-title");
  document.body.append(dialog);
  let description = "", response = "", disposed = false;
  function element(tag, text2, parent = dialog) {
    const node = document.createElement(tag);
    if (text2) node.textContent = text(text2);
    parent.append(node);
    return node;
  }
  function close() {
    if (disposed) return;
    disposed = true;
    window.removeEventListener("keydown", modalEscape, true);
    dialog.close();
    dialog.remove();
    if (previousFocus?.isConnected) previousFocus.focus();
    onClose();
  }
  function modalEscape(event) {
    if (event.key !== "Escape" || disposed) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    close();
  }
  window.addEventListener("keydown", modalEscape, true);
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    close();
  });
  dialog.addEventListener("keydown", (event) => event.stopPropagation());
  dialog.addEventListener("click", (event) => event.stopPropagation());
  function render(step) {
    dialog.replaceChildren();
    element("h2", step === 1 ? "Describe your shader" : "Paste the AI-generated code").id = "shader-prompt-title";
    const hint = element("p", step === 1 ? "Describe the appearance, colors and movement you want. We will add the technical instructions and copy everything for your AI." : "Instructions copied! Paste them into your favorite AI. Then copy its complete GLSL response and paste it below. Insert into editor will place the code in the GLSL code field; save it there when you are ready.");
    hint.id = "shader-prompt-hint";
    const label = element("label", step === 1 ? "Desired effect" : "GLSL returned by the AI");
    label.htmlFor = "shader-prompt-input";
    const input = element("textarea");
    input.id = "shader-prompt-input";
    input.setAttribute("aria-describedby", hint.id);
    input.rows = 8;
    input.maxLength = step === 1 ? 4e3 : 4e4;
    input.spellcheck = step === 1;
    input.value = step === 1 ? description : response;
    input.placeholder = text(step === 1 ? "Example: slow violet mist with a few glowing sparks." : "Paste the complete shader code here.");
    const error = element("p");
    error.className = "shader-prompt-dialog__error";
    error.setAttribute("role", "alert");
    const actions = element("footer");
    const cancel = element("button", "Cancel", actions);
    cancel.type = "button";
    cancel.onclick = close;
    if (step === 2) {
      const back = element("button", "Back", actions);
      back.type = "button";
      back.onclick = () => {
        response = input.value;
        render(1);
      };
    }
    const confirm = element("button", step === 1 ? "Copy instructions and continue" : "Insert into editor", actions);
    confirm.type = "button";
    confirm.className = "shader-prompt-dialog__confirm";
    confirm.disabled = !input.value.trim();
    input.oninput = () => {
      confirm.disabled = !input.value.trim();
      error.textContent = "";
    };
    confirm.onclick = async () => {
      error.textContent = "";
      if (step === 1) {
        description = input.value.trim();
        if (!description) return;
        confirm.disabled = true;
        try {
          await navigator.clipboard.writeText(shaderInstructions(description));
          if (!disposed) render(2);
        } catch {
          if (!disposed) {
            error.textContent = text("Could not copy the instructions. Allow clipboard access in your browser and try again.");
            confirm.disabled = false;
          }
        }
      } else {
        try {
          input.value = normalizeShaderSource(input.value);
          onInsert(shaderSource(input.value));
          close();
        } catch (failure) {
          error.textContent = failure.message;
        }
      }
    };
    input.focus();
  }
  render(1);
  dialog.showModal();
  dialog.querySelector("textarea").focus();
  return close;
}

// gravewright/maps/frontend/features/effects/model/legacy-labels.js
var effectLabels = {
  get "lighting.shaders.whole_scene"() {
    return text("Entire scene");
  },
  get "lighting.particles.tool"() {
    return text("Particles");
  },
  get "lighting.particles.smoke"() {
    return text("Smoke");
  },
  get "lighting.particles.ember"() {
    return text("Ember");
  },
  get "lighting.particles.dust"() {
    return text("Dust");
  },
  get "lighting.particles.arcane"() {
    return text("Arcane");
  },
  get "lighting.shaders.tool"() {
    return text("Scene shader");
  },
  get "lighting.shaders.editor"() {
    return text("Scene shader");
  },
  get "lighting.shaders.reference"() {
    return text("Reference");
  },
  get "lighting.shaders.source"() {
    return text("GLSL code");
  },
  get "lighting.shaders.intensity"() {
    return text("Intensity");
  },
  get "lighting.shaders.opacity"() {
    return text("Opacity");
  },
  get "lighting.shaders.blend_mode"() {
    return text("Blend mode");
  },
  get "lighting.shaders.blend_hint"() {
    return text("Defines how the effect blends with the map and shaders below it.");
  },
  "lighting.shaders.blend.normal": "Normal",
  get "lighting.shaders.blend.multiply"() {
    return text("Multiply");
  },
  get "lighting.shaders.blend.darken"() {
    return text("Darken");
  },
  get "lighting.shaders.blend.lighten"() {
    return text("Lighten");
  },
  get "lighting.shaders.blend.screen"() {
    return text("Screen");
  },
  get "lighting.shaders.blend.add"() {
    return text("Add (glow)");
  },
  get "lighting.shaders.blend.overlay"() {
    return text("Overlay");
  },
  get "lighting.shaders.blend.soft_light"() {
    return text("Soft light");
  },
  get "lighting.shaders.blend.hard_light"() {
    return text("Hard light");
  },
  get "lighting.shaders.blend.color_dodge"() {
    return text("Color dodge");
  },
  get "lighting.shaders.blend.color_burn"() {
    return text("Color burn");
  },
  get "lighting.shaders.blend.difference"() {
    return text("Difference");
  },
  get "lighting.shaders.blend.exclusion"() {
    return text("Exclusion");
  },
  get "lighting.shaders.blend.subtract"() {
    return text("Subtract");
  },
  get "lighting.shaders.rotation"() {
    return text("Rotation");
  },
  get "lighting.shaders.radius"() {
    return text("Range");
  },
  get "lighting.shaders.radius_hint"() {
    return text("In cells, from the origin you drag on the map. The effect is drawn inside a frame of this size and clipped by a mask. Anything outside it cannot appear. Zero = entire scene.");
  },
  get "lighting.shaders.scale"() {
    return text("Scale");
  },
  get "lighting.shaders.speed"() {
    return text("Speed");
  },
  get "lighting.shaders.color"() {
    return text("Color");
  },
  get "lighting.shaders.enabled"() {
    return text("Active");
  },
  get "lighting.shaders.save"() {
    return text("Save");
  },
  get "lighting.shaders.remove"() {
    return text("Remove shader");
  },
  get "lighting.shaders.group.appearance"() {
    return text("Appearance");
  },
  get "lighting.shaders.group.pattern"() {
    return text("Pattern and motion");
  },
  get "lighting.shaders.group.area"() {
    return text("Area");
  },
  get "lighting.shaders.mode_hint"() {
    return text("Shaders appear only in cinematic mode; lightweight mode uses particles for scene effects.");
  },
  get "lighting.shaders.preview"() {
    return text("Validate");
  },
  get "lighting.shaders.preview_final"() {
    return text("Result");
  },
  get "lighting.shaders.preview_mask"() {
    return text("Mask (range and walls)");
  },
  get "lighting.shaders.preview_light"() {
    return text("Light buffer");
  },
  get "lighting.shaders.prompt_title"() {
    return text("AI prompt");
  },
  get "lighting.shaders.prompt_failed"() {
    return text("Could not copy. Check clipboard permissions and try again.");
  },
  get "lighting.shaders.prompt_copy"() {
    return text("Copy prompt");
  },
  get "lighting.shaders.prompt_copied"() {
    return text("Copied");
  },
  get "lighting.particles.editor"() {
    return text("Particle emitter");
  },
  get "lighting.particles.kind"() {
    return text("Type");
  },
  get "lighting.particles.scale"() {
    return text("Size");
  },
  get "lighting.particles.density"() {
    return text("Quantity");
  },
  get "lighting.particles.color"() {
    return text("Color");
  },
  get "lighting.particles.enabled"() {
    return text("Active");
  },
  get "lighting.particles.remove"() {
    return text("Delete emitter");
  },
  get "lighting.particles.density_hint"() {
    return text("Quantity controls performance: lower it if the scene slows down.");
  },
  get "lighting.particles.hint"() {
    return text("Scene effect: does not emit light.");
  },
  get "lighting.shaders.presets.title"() {
    return text("Preset library (50)");
  },
  get "lighting.shaders.presets.hint"() {
    return text("Choose a preset. Applying it replaces the code and adjusts this shader's controls.");
  },
  get "lighting.shaders.presets.search"() {
    return text("Search presets...");
  },
  get "lighting.shaders.presets.category"() {
    return text("Category");
  },
  get "lighting.shaders.presets.all"() {
    return text("All categories");
  },
  get "lighting.shaders.presets.apply"() {
    return text("Apply preset");
  },
  get "lighting.shaders.presets.applied"() {
    return text("Preset applied and saved.");
  },
  get "lighting.shaders.presets.empty"() {
    return text("No preset found.");
  },
  "lighting.shaders.picker.title": "Shaders",
  "lighting.shaders.picker.custom": "Custom",
  get "lighting.shaders.picker.loading"() {
    return text("Loading presets...");
  },
  get "lighting.shaders.picker.error"() {
    return text("Could not load presets.");
  },
  get "lighting.particles.rain"() {
    return text("Rain");
  },
  get "lighting.particles.snow"() {
    return text("Snow");
  },
  get "lighting.particles.firefly"() {
    return text("Fireflies");
  },
  get "lighting.particles.leaves"() {
    return text("Leaves");
  },
  get "lighting.particles.bubbles"() {
    return text("Bubbles");
  },
  get "lighting.particles.ash"() {
    return text("Ash");
  },
  get "lighting.particles.blood"() {
    return text("Blood");
  },
  get "lighting.particles.runes"() {
    return text("Runes");
  }
};

// gravewright/maps/frontend/features/effects/ui/EffectEditor.native.js
var PhX5 = "PhX";
var PhTrash5 = "PhTrash";
var PhCheck = "PhCheck";
var PhBooks = "PhBooks";
var PhMagicWand = "PhMagicWand";
var PhCopy2 = "PhCopy";
var EffectEditor_native_default = widget([{ "tag": "section", "attrs": { "class": "gw-window effect-editor", "role": "dialog" }, "bind": { "class": "({ 'effect-editor--shader': kind === 'shader' })", "aria-label": "(t('editor'))" }, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "wheel", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "effect-editor__header gw-move-handle", "data-move-handle": "" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('editor'))" }] }, { "tag": "button", "attrs": { "type": "button", "class": "gw-window__control" }, "bind": { "aria-label": "(gwText('Close'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "effect-editor__body" }, "bind": {}, "events": [{ "event": "input", "code": "kind === 'shader' && emit('change');", "mods": [] }, { "event": "change", "code": "kind === 'shader' && emit('change');", "mods": [] }], "children": [{ "tag": "fieldset", "attrs": { "class": "effect-editor__interaction" }, "bind": {}, "events": [], "children": [{ "tag": "legend", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Light interaction'))" }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Receive lighting'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": "0.05" }, "bind": {}, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.light_response)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(Math.round(draft.light_response * 100))" }, { "text": "%" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Emit light'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "2", "step": "0.05" }, "bind": {}, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.light_emission)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.light_emission.toFixed(2))" }] }] }] }] }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('kind'))" }] }, { "tag": "select", "attrs": {}, "bind": {}, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [{ "tag": "option", "attrs": {}, "bind": { "key": "(kind)", "value": "(kind)" }, "events": [], "children": [{ "value": "(t(kind))" }], "each": { "names": ["kind"], "value": "(['smoke', 'ember', 'dust', 'arcane', 'rain', 'snow', 'firefly', 'leaves', 'bubbles', 'ash', 'blood', 'runes'])" } }], "model": { "path": "(draft.kind)", "mods": [] } }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('scale'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": ".5", "max": "20", "step": ".5" }, "bind": {}, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.scale)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.scale)" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('density'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": ".05" }, "bind": {}, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.density)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.density.toFixed(2))" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('color'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": {}, "events": [{ "event": "input", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.color)", "mods": [] } }] }, { "tag": "label", "attrs": { "class": "effect-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [{ "event": "change", "code": "emit('change');", "mods": [] }], "children": [], "model": { "path": "(draft.enabled)", "mods": [] } }, { "value": "(t('enabled'))" }] }, { "tag": "p", "attrs": { "class": "effect-editor__hint" }, "bind": {}, "events": [], "children": [{ "value": "(t('density_hint'))" }] }, { "tag": "p", "attrs": { "class": "effect-editor__hint" }, "bind": {}, "events": [], "children": [{ "value": "(t('hint'))" }] }], "when": "(kind === 'particle')" }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "details", "attrs": { "class": "effect-editor__library" }, "bind": {}, "events": [], "children": [{ "tag": "summary", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhBooks", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "text": " " }, { "value": "(t('presets.title'))" }] }, { "tag": "p", "attrs": { "class": "effect-editor__hint" }, "bind": {}, "events": [], "children": [{ "value": "(t('presets.hint'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "search" }, "bind": { "placeholder": "(t('presets.search'))", "aria-label": "(t('presets.search'))" }, "events": [], "children": [], "model": { "path": "(search)", "mods": [] } }, { "tag": "select", "attrs": {}, "bind": { "aria-label": "(t('presets.category'))" }, "events": [], "children": [{ "tag": "option", "attrs": { "value": "" }, "bind": {}, "events": [], "children": [{ "value": "(t('presets.all'))" }] }, { "tag": "option", "attrs": {}, "bind": { "key": "(c)" }, "events": [], "children": [{ "value": "(c)" }], "each": { "names": ["c"], "value": "(categories)" } }], "model": { "path": "(category)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "effect-editor__presets", "role": "listbox" }, "bind": { "aria-label": "(t('presets.title'))" }, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button", "role": "option" }, "bind": { "key": "(p.id)", "aria-selected": "(choice === p.id)" }, "events": [{ "event": "click", "code": "choice = p.id;", "mods": [] }], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(p.name)" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(p.category)" }] }], "each": { "names": ["p"], "value": "(presets)" } }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('presets.empty'))" }], "when": "(!presets.length)" }] }, { "tag": "div", "attrs": { "class": "effect-editor__choice" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(chosen.name)" }] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(chosen.description)" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "apply;", "mods": [] }], "children": [{ "tag": "PhMagicWand", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(t('presets.apply'))" }] }], "when": "(chosen)" }] }, { "tag": "div", "attrs": { "class": "effect-editor__columns" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": { "class": "effect-editor__code" }, "bind": {}, "events": [], "children": [{ "tag": "header", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "for": "effect-shader-source" }, "bind": {}, "events": [], "children": [{ "value": "(t('source'))" }] }, { "tag": "label", "attrs": { "class": "effect-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "(draft.enabled)", "mods": [] } }, { "value": "(t('enabled'))" }] }] }, { "tag": "textarea", "attrs": { "id": "effect-shader-source", "spellcheck": "false", "rows": "10" }, "bind": {}, "events": [], "children": [], "model": { "path": "(draft.source)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "effect-editor__controls" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "h3", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('group.appearance'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('opacity'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "1", "step": ".05" }, "bind": {}, "events": [], "children": [], "model": { "path": "(draft.opacity)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.opacity.toFixed(2))" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('color'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": {}, "events": [], "children": [], "model": { "path": "(draft.color)", "mods": [] } }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('blend_mode'))" }] }, { "tag": "select", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "option", "attrs": {}, "bind": { "key": "(mode)", "value": "(mode)" }, "events": [], "children": [{ "value": "(t(`blend.${mode}`))" }], "each": { "names": ["mode"], "value": "(['normal', 'multiply', 'screen', 'add'])" } }], "model": { "path": "(draft.blend_mode)", "mods": [] } }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('blend_hint'))" }] }] }] }, { "tag": "section", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "h3", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('group.pattern'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": { "key": "(range.key)" }, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t(range.key))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range" }, "bind": { "min": "(range.min)", "max": "(range.max)", "step": "(range.step)" }, "events": [], "children": [], "model": { "path": "(draft[range.key])", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft[range.key])" }, { "value": "(range.key === 'rotation' ? '\xB0' : '')" }] }] }], "each": { "names": ["range"], "value": "(ranges)" } }] }] }, { "tag": "section", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "h3", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('group.area'))" }] }, { "tag": "div", "attrs": { "class": "effect-editor__grid" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "effect-editor__field" }, "bind": {}, "events": [], "children": [{ "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(t('radius'))" }] }, { "tag": "span", "attrs": { "class": "effect-editor__slider" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "range", "min": "0", "max": "120", "step": "1" }, "bind": {}, "events": [], "children": [], "model": { "path": "(draft.radius)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(draft.radius)" }] }] }] }, { "tag": "label", "attrs": { "class": "effect-editor__check" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": { "checked": "(draft.radius === 0)" }, "events": [{ "event": "click", "code": "draft.radius = $event.target.checked ? 0 : 8; emit('change');", "mods": [] }], "children": [] }, { "value": "(t('whole_scene'))" }] }] }] }] }] }, { "tag": "div", "attrs": { "class": "effect-editor__reference" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "showPrompt();", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(t('prompt_title'))" }] }] }], "otherwise": true }] }, { "tag": "footer", "attrs": { "class": "effect-editor__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button", "class": "effect-editor__remove" }, "bind": { "disabled": "(busy)", "aria-label": "(t('remove'))" }, "events": [{ "event": "click", "code": "emit('remove');", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }], "when": "(existing)" }, { "tag": "span", "attrs": { "role": "status" }, "bind": {}, "events": [], "children": [{ "value": "(error || (!existing ? gwText('Click the scene to place the origin.') : ''))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "emit('save');", "mods": [] }], "children": [{ "tag": "PhCheck", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(existing ? t('save') : gwText('Create'))" }], "when": "(kind === 'shader' || !existing)" }] }], "movable": true }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const draft = model(options);
  const emit = options.emit;
  const particleNames = { get rain() {
    return text("Rain");
  }, get snow() {
    return text("Snow");
  }, get firefly() {
    return text("Fireflies");
  }, get leaves() {
    return text("Leaves");
  }, get bubbles() {
    return text("Bubbles");
  }, get ash() {
    return text("Ash");
  }, get blood() {
    return text("Blood");
  }, get runes() {
    return text("Runes");
  } };
  const t = (key) => effectLabels[`lighting.${props.kind === "particle" ? "particles" : "shaders"}.${key}`] || (props.kind === "particle" ? particleNames[key] : void 0) || key;
  const search = ref(""), category = ref(""), choice = ref("");
  let closePrompt;
  onBeforeUnmount(() => closePrompt?.());
  const categories = computed(() => [...new Set(shaderPresets.map((p) => p.category))]);
  const presets = computed(() => shaderPresets.filter((p) => (!category.value || p.category === category.value) && `${p.name} ${p.description}`.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())));
  const chosen = computed(() => shaderPresets.find((p) => p.id === choice.value));
  function apply() {
    const p = chosen.value;
    if (!p)
      return;
    draft.value = { ...draft.value, ...p, source: p.source };
    emit("change");
  }
  function showPrompt() {
    if (closePrompt) return;
    closePrompt = openShaderPrompt((source) => {
      draft.value = { ...draft.value, source };
      emit("change");
    }, () => {
      closePrompt = null;
    });
  }
  const ranges = [{ key: "intensity", min: 0, max: 1, step: 0.05 }, { key: "scale", min: 0.1, max: 20, step: 0.1 }, { key: "speed", min: 0, max: 8, step: 0.1 }, { key: "rotation", min: 0, max: 359, step: 1 }];
  return { gwText: text, PhX: PhX5, PhTrash: PhTrash5, PhCheck, PhBooks, PhMagicWand, PhCopy: PhCopy2, vMovableResizable, shaderPresets, effectLabels, draft, particleNames, t, search, category, choice, categories, presets, chosen, apply, showPrompt, ranges, emit: options.emit };
});

// gravewright/maps/frontend/features/effects/ui/EffectPreview.native.js
import { renderingPreferences as renderingPreferences2 } from "/static/gravewright_maps/render-profile.js";

// gravewright/maps/frontend/features/scene-layers/lib/shader-language.js
var PREAMBLE = `#version 300 es
precision highp float;

in vec2 vTextureCoord;
out vec4 finalColor;



uniform sampler2D gwUTexture;

uniform float gwUQuality;
uniform float gwULightResponse;
uniform float gwUAmbient;
uniform float gwUTime;
uniform float gwUIntensity;
uniform float gwUOpacity;
uniform float gwUScale;
uniform float gwUSpeed;
uniform vec3 gwUColor;


uniform vec2 gwUResolution;
uniform float gwUAspect;



uniform vec2 gwUOrigin;
uniform float gwURadius;
uniform float gwURotation;


uniform vec3 gwUCamera;



uniform sampler2D gwULightBuffer;


uniform vec2 gwUScreen;










uniform vec2 gwUFrameOrigin;


vec2 gwScreen(vec2 uv) {
    return uv * gwUResolution + gwUFrameOrigin;
}


vec2 gwScreenUV(vec2 uv) {
    return gwScreen(uv) / max(gwUScreen, vec2(1.0));
}



vec4 gwLight(vec2 uv) {
    return texture(gwULightBuffer, gwScreenUV(uv));
}



vec4 gwIlluminate(vec4 color, vec2 uv, float strength) {
    vec3 illumination = clamp(vec3(gwUAmbient) + gwLight(uv).rgb, vec3(0.0), vec3(1.5));
    float alpha = max(color.a, 0.0001);
    vec3 linearColor = pow(max(color.rgb / alpha, vec3(0.0)), vec3(2.2));
    vec3 lit = pow(linearColor * mix(vec3(1.0), illumination, clamp(strength, 0.0, 1.0)), vec3(1.0 / 2.2));
    return vec4(lit * color.a, color.a);
}
vec2 gwWorld(vec2 uv) {
    return (gwScreen(uv) - gwUCamera.xy) / max(gwUCamera.z, 0.0001);
}


vec2 gwRotated(vec2 uv) {
    vec2 d = gwWorld(uv) - gwUOrigin;
    float c = cos(gwURotation);
    float s = sin(gwURotation);
    return gwUOrigin + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
}










float gwFeature() {
    float base = gwURadius > 0.0 ? gwURadius * 0.6 : 420.0;
    return max(base * gwUScale, 1.0);
}



vec2 gwPattern(vec2 uv) {


    return (gwRotated(uv) - gwUOrigin) / gwFeature();
}
`;
var USER_PREFIX = `#define uTexture gwUTexture
#define uQuality gwUQuality
#define uTime gwUTime
#define uIntensity gwUIntensity
#define uOpacity gwUOpacity
#define uScale gwUScale
#define uSpeed gwUSpeed
#define uColor gwUColor
#define uResolution gwUResolution
#define uAspect gwUAspect
#define uOrigin gwUOrigin
#define uRadius gwURadius
#define uRotation gwURotation
#define uCamera gwUCamera
#define uLightBuffer gwULightBuffer
#define uScreen gwUScreen
#define uFrameOrigin gwUFrameOrigin
#define main gwUserMain
`;
var USER_SUFFIX = "\n#undef main\nvoid main() { gwUserMain(); finalColor *= gwUOpacity; finalColor = gwIlluminate(finalColor, vTextureCoord, gwULightResponse); }\n";

// gravewright/maps/frontend/features/effects/model/particle-profiles.js
function phaseOf(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i++)
    hash = (hash * 31 + id.charCodeAt(i)) % 9973;
  return hash / 9973 * Math.PI * 2;
}
var PARTICLE_KINDS = {
  smoke: {
    count: 22,
    life: 6200,
    rise: 2.4,
    spread: 0.5,
    drift: 0.55,
    size: 0.4,
    grow: 2.4,
    alpha: 0.28,
    blend: "normal",
    color: "#9aa3ad"
  },
  ember: {
    count: 26,
    life: 2300,
    rise: 2.2,
    spread: 0.42,
    drift: 0.3,
    size: 0.08,
    grow: 0.4,
    alpha: 0.95,
    blend: "add",
    color: "#ff9040"
  },
  dust: {
    count: 30,
    life: 8e3,
    rise: 0.25,
    spread: 0.9,
    drift: 0.9,
    size: 0.05,
    grow: 0.1,
    alpha: 0.35,
    blend: "normal",
    color: "#d8cdb4"
  },
  arcane: {
    count: 16,
    life: 4200,
    rise: 0,
    orbit: 0.62,
    spread: 1,
    drift: 0,
    size: 0.07,
    grow: 0.2,
    alpha: 0.8,
    blend: "add",
    color: "#c9a6ff"
  },
  rain: {
    count: 46,
    life: 1350,
    rise: -3.8,
    spread: 0.95,
    drift: 0.08,
    wind: 0.7,
    size: 0.16,
    grow: 0,
    aspect: 0.12,
    alpha: 0.62,
    blend: "screen",
    color: "#9bc9e8",
    rotation: -0.18
  },
  snow: {
    count: 38,
    life: 7200,
    rise: -0.75,
    spread: 1.1,
    drift: 0.85,
    wind: 0.22,
    size: 0.07,
    grow: 0.25,
    alpha: 0.8,
    blend: "normal",
    color: "#edf7ff"
  },
  firefly: {
    count: 18,
    life: 5600,
    rise: 0,
    orbit: 0.38,
    spread: 1,
    drift: 0.35,
    size: 0.055,
    grow: 0.15,
    alpha: 0.95,
    pulse: 3.5,
    blend: "add",
    color: "#ffe46b"
  },
  leaves: {
    count: 24,
    life: 6800,
    rise: -0.9,
    spread: 1.15,
    drift: 1.1,
    wind: 0.5,
    size: 0.12,
    grow: 0.05,
    aspect: 0.55,
    spin: 8,
    alpha: 0.72,
    blend: "normal",
    color: "#a87035"
  },
  bubbles: {
    count: 22,
    life: 5200,
    rise: 1.5,
    spread: 0.7,
    drift: 0.7,
    size: 0.08,
    grow: 0.65,
    alpha: 0.48,
    blend: "screen",
    color: "#8de8ff"
  },
  ash: {
    count: 34,
    life: 9e3,
    rise: -0.35,
    spread: 1.25,
    drift: 1,
    wind: 0.35,
    size: 0.045,
    grow: 0.1,
    aspect: 0.65,
    spin: 5,
    alpha: 0.5,
    blend: "normal",
    color: "#77736e"
  },
  blood: {
    count: 28,
    life: 1800,
    burst: true,
    spread: 1.2,
    gravity: 1.9,
    wind: 0.08,
    size: 0.07,
    grow: 0.35,
    aspect: 0.5,
    spin: 7,
    alpha: 0.9,
    blend: "normal",
    color: "#a10f20"
  },
  runes: {
    count: 12,
    life: 6400,
    rise: 0,
    orbit: 0.42,
    spread: 0.82,
    drift: 0,
    size: 0.11,
    grow: 0,
    aspect: 0.35,
    spin: -2,
    pulse: 2.2,
    alpha: 0.9,
    blend: "add",
    color: "#69a7ff"
  }
};
var PARTICLE_DEFAULTS = {
  smoke: { scale: 3, density: 0.6, color: "#9aa3ad" },
  ember: { scale: 2, density: 0.5, color: "#ff9040" },
  dust: { scale: 6, density: 0.45, color: "#d8cdb4" },
  arcane: { scale: 2.5, density: 0.6, color: "#c9a6ff" },
  rain: { scale: 8, density: 0.7, color: "#9bc9e8" },
  snow: { scale: 8, density: 0.65, color: "#edf7ff" },
  firefly: { scale: 5, density: 0.55, color: "#ffe46b" },
  leaves: { scale: 7, density: 0.55, color: "#a87035" },
  bubbles: { scale: 4, density: 0.6, color: "#8de8ff" },
  ash: { scale: 8, density: 0.6, color: "#77736e" },
  blood: { scale: 3, density: 0.7, color: "#a10f20" },
  runes: { scale: 3, density: 0.65, color: "#69a7ff" }
};
function particlesOf(emitter, now, cellSize) {
  const spec = PARTICLE_KINDS[emitter.kind];
  if (!spec || !(cellSize > 0))
    return [];
  if (!emitter.enabled)
    return [];
  const scale = Math.max(0.5, Number(emitter.scale) || 1);
  const density = Math.max(0, Math.min(1, Number(emitter.density ?? 0.6)));
  const count = Math.round(spec.count * density);
  const seed = phaseOf(emitter.id || "");
  const reach = cellSize * scale;
  const angle = (emitter.rotation || 0) * Math.PI / 180;
  const out = [];
  for (let index = 0; index < count; index += 1) {
    const own = (index * 0.6180339887 + seed) % 1;
    const age = ((now / spec.life + own) % 1 + 1) % 1;
    const around = own * Math.PI * 2;
    const sway = Math.sin(now / 900 + around * 3) * (spec.drift || 0);
    const orbit = spec.orbit || 0;
    const radial = spec.burst ? {
      x: Math.cos(around) * spec.spread * age,
      y: Math.sin(around) * spec.spread * age + (spec.gravity || 0) * age * age
    } : orbit ? {
      x: Math.cos(around + now / 1e3 * orbit) * spec.spread,
      y: Math.sin(around + now / 1e3 * orbit) * spec.spread * 0.6
    } : {
      x: Math.sin(around) * spec.spread * (0.35 + age) + sway * age,
      y: -(spec.rise || 0) * age
    };
    radial.x += (spec.wind || 0) * age;
    const fade = Math.sin(age * Math.PI);
    out.push({
      age,
      x: emitter.x + (radial.x * Math.cos(angle) - radial.y * Math.sin(angle)) * reach,
      y: emitter.y + (radial.x * Math.sin(angle) + radial.y * Math.cos(angle)) * reach,
      size: spec.size * (1 + spec.grow * age) * reach,
      alpha: spec.alpha * fade * (spec.pulse ? 0.55 + 0.45 * Math.sin(now / 1e3 * spec.pulse + around * 5) : 1),
      tint: emitter.color || spec.color,
      blend: spec.blend,
      aspect: spec.aspect || 1,
      rotation: angle + (spec.rotation ?? around + age * (spec.spin || (orbit ? 2 : 0.8)))
    });
  }
  return out;
}

// gravewright/maps/frontend/features/effects/ui/EffectPreview.native.js
var EffectPreview_native_default = widget([{ "tag": "div", "attrs": { "class": "effect-preview", "role": "img" }, "bind": { "aria-label": "(gwText('Preview: {0}', label))" }, "events": [], "children": [{ "tag": "div", "attrs": { "ref": "host", "class": "effect-preview__surface" }, "bind": {}, "events": [], "children": [{ "tag": "canvas", "attrs": { "ref": "canvas" }, "bind": {}, "events": [], "children": [] }] }, { "tag": "span", "attrs": { "class": "effect-preview__label" }, "bind": {}, "events": [], "children": [{ "value": "(failed ? gwText('Preview unavailable') : label)" }] }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const host = ref(), canvas = ref();
  const failed = ref(false);
  let gl = null, ctx = null;
  let program = null, buffer = null, white = null;
  let observer, frame = 0, closed = false, started = 0;
  let stopProfile;
  let animate;
  function compile(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      gl.deleteShader(shader);
      throw new Error("Shader preview compilation failed");
    }
    return shader;
  }
  function render() {
    if (!canvas.value || !host.value || closed)
      return;
    animate = void 0;
    failed.value = false;
    if (program) {
      gl.deleteProgram(program);
      program = null;
    }
    const width = host.value.clientWidth, height = host.value.clientHeight;
    if (!width || !height)
      return;
    const ratio = Math.min(devicePixelRatio, 2);
    canvas.value.width = Math.round(width * ratio);
    canvas.value.height = Math.round(height * ratio);
    try {
      if (props.kind === "shader") {
        if (!gl)
          throw new Error("WebGL unavailable");
        const preset = { ...defaults(), ...shaderPresets.find((p) => p.id === props.choice) };
        const vertex = compile(gl.VERTEX_SHADER, "#version 300 es\nin vec2 position;out vec2 vTextureCoord;void main(){vTextureCoord=(position+1.0)*0.5;gl_Position=vec4(position.x,-position.y,0.0,1.0);}");
        let fragment;
        try {
          fragment = compile(gl.FRAGMENT_SHADER, PREAMBLE + USER_PREFIX + preset.source + USER_SUFFIX);
        } catch (error) {
          gl.deleteShader(vertex);
          throw error;
        }
        program = gl.createProgram();
        gl.attachShader(program, vertex);
        gl.attachShader(program, fragment);
        gl.linkProgram(program);
        gl.deleteShader(vertex);
        gl.deleteShader(fragment);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS))
          throw new Error("Shader preview linking failed");
        gl.useProgram(program);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        const position = gl.getAttribLocation(program, "position");
        gl.enableVertexAttribArray(position);
        gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
        gl.viewport(0, 0, canvas.value.width, canvas.value.height);
        const loc = (name) => gl.getUniformLocation(program, name);
        const worldHeight = 610, worldWidth = worldHeight * width / height;
        const values = { gwUQuality: (effectQuality(renderingPreferences2.current().name).shaderDetail - 1) / 4, gwUIntensity: preset.intensity, gwUOpacity: preset.opacity, gwUScale: preset.scale, gwUSpeed: preset.speed, gwUAspect: worldWidth / worldHeight, gwURadius: preset.radius > 0 ? 500 : 0, gwURotation: preset.rotation * Math.PI / 180 };
        for (const [name, value] of Object.entries(values))
          gl.uniform1f(loc(name), value);
        gl.uniform2f(loc("gwUResolution"), worldWidth, worldHeight);
        gl.uniform2f(loc("gwUScreen"), worldWidth, worldHeight);
        gl.uniform2f(loc("gwUOrigin"), worldWidth / 2, worldHeight / 2);
        gl.uniform2f(loc("gwUFrameOrigin"), 0, 0);
        gl.uniform3f(loc("gwUCamera"), 0, 0, 1);
        const color = parseInt(preset.color.slice(1), 16);
        gl.uniform3f(loc("gwUColor"), (color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, white);
        gl.uniform1i(loc("gwUTexture"), 0);
        gl.uniform1i(loc("gwULightBuffer"), 0);
        const timeUniform = loc("gwUTime");
        animate = (time) => {
          gl.uniform1f(timeUniform, time);
          gl.drawArrays(gl.TRIANGLES, 0, 6);
        };
      } else {
        if (!ctx)
          throw new Error("Canvas unavailable");
        const settings = PARTICLE_DEFAULTS[props.choice], spec = PARTICLE_KINDS[props.choice];
        if (!settings || !spec)
          return;
        const emitter = { ...defaults(), ...settings, id: "preview", kind: props.choice, x: width / 2, y: spec.orbit ? height / 2 : (spec.rise ?? 0) > 0 ? height * 0.85 : height * 0.15 };
        const cell = Math.min(height * 0.7 / (Math.max(1, Math.abs(spec.rise ?? 0), spec.gravity ?? 0) * settings.scale), width / (settings.scale * 3));
        const dot = document.createElement("canvas");
        dot.width = dot.height = 64;
        const dc = dot.getContext("2d");
        const gradient = dc.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, settings.color);
        gradient.addColorStop(0.35, `${settings.color}bf`);
        gradient.addColorStop(1, `${settings.color}00`);
        dc.fillStyle = gradient;
        dc.fillRect(0, 0, 64, 64);
        animate = (time) => {
          ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
          ctx.clearRect(0, 0, width, height);
          for (const p of particlesOf(emitter, time * 1e3, cell)) {
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(p.rotation);
            ctx.globalAlpha = p.alpha;
            ctx.globalCompositeOperation = p.blend === "add" ? "lighter" : p.blend === "screen" ? "screen" : "source-over";
            ctx.drawImage(dot, -p.size * p.aspect, -p.size, p.size * 2 * p.aspect, p.size * 2);
            ctx.restore();
          }
        };
      }
      started = performance.now();
      animate?.(0);
    } catch {
      failed.value = true;
    }
  }
  watch(() => props.choice, render);
  onMounted(() => {
    if (props.kind === "shader") {
      gl = canvas.value.getContext("webgl2", { alpha: true, premultipliedAlpha: true });
      if (gl) {
        buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW);
        white = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, white);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      }
    } else
      ctx = canvas.value.getContext("2d");
    render();
    observer = new ResizeObserver(render);
    observer.observe(host.value);
    let last = 0;
    const tick = () => {
      if (closed)
        return;
      const fps = effectQuality(renderingPreferences2.current().name).fps;
      if (!fps) {
        animate?.(0);
        return;
      }
      const now = performance.now();
      if (now - last >= 1e3 / fps) {
        last = now;
        animate?.((now - started) / 1e3);
      }
      frame = requestAnimationFrame(tick);
    };
    stopProfile = renderingPreferences2.subscribe(() => {
      cancelAnimationFrame(frame);
      render();
      tick();
    });
  });
  onBeforeUnmount(() => {
    closed = true;
    stopProfile?.();
    cancelAnimationFrame(frame);
    observer?.disconnect();
    animate = void 0;
    if (gl) {
      gl.deleteProgram(program);
      gl.deleteBuffer(buffer);
      gl.deleteTexture(white);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    }
    gl = null;
    ctx = null;
  });
  return { gwText: text, renderingPreferences: renderingPreferences2, effectQuality, PREAMBLE, USER_PREFIX, USER_SUFFIX, shaderPresets, PARTICLE_DEFAULTS, PARTICLE_KINDS, particlesOf, defaults, host, canvas, failed, gl, ctx, program, buffer, white, observer, frame, closed, started, stopProfile, animate, compile, render, emit: options.emit };
});

// gravewright/maps/frontend/features/effects/ui/EffectPicker.native.js
var PhCloud = "PhCloud";
var PhFireSimple = "PhFireSimple";
var PhDotsThreeOutline = "PhDotsThreeOutline";
var PhSparkle = "PhSparkle";
var PhCloudRain = "PhCloudRain";
var PhSnowflake = "PhSnowflake";
var PhLightbulb2 = "PhLightbulb";
var PhLeaf = "PhLeaf";
var PhCirclesThreePlus = "PhCirclesThreePlus";
var PhWind = "PhWind";
var PhDrop = "PhDrop";
var PhPentagram = "PhPentagram";
var PhCode = "PhCode";
var PhCodeBlock = "PhCodeBlock";
var PhX6 = "PhX";
var EffectPicker_native_default = widget([{ "tag": "section", "attrs": { "ref": "panel", "class": "effect-picker", "role": "dialog" }, "bind": { "class": "({ 'effect-picker--shader': kind === 'shader' })", "style": "(position)", "aria-label": "(title)" }, "events": [{ "event": "keydown", "code": "emit('close');", "mods": ["esc", "stop"] }], "children": [{ "tag": "EffectPreview", "attrs": {}, "bind": { "kind": "(kind)", "choice": "(previewChoice)", "label": "(previewLabel)" }, "events": [], "children": [] }, { "tag": "header", "attrs": { "class": "effect-picker__header" }, "bind": {}, "events": [], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "(kind === 'shader' ? PhCode : PhSparkle)" }, "events": [], "children": [] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(title)" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "aria-label": "(gwText('Close picker'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "effect-picker__particles" }, "bind": { "aria-label": "(gwText('Particle types'))" }, "events": [{ "event": "mouseleave", "code": "hovered = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "key": "(id)", "aria-pressed": "(particle === id)" }, "events": [{ "event": "mouseenter", "code": "hovered = id;", "mods": [] }, { "event": "focus", "code": "hovered = id;", "mods": [] }, { "event": "click", "code": "emit('choose', id);", "mods": [] }], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "(icon)" }, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(effectLabels[`lighting.particles.${id}`])" }] }], "each": { "names": ["icon", "id"], "value": "(icons)" } }], "when": "(kind === 'particle')" }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "effect-picker__presets", "role": "listbox" }, "bind": { "aria-label": "(gwText('Shader presets'))" }, "events": [{ "event": "mouseleave", "code": "hovered = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": { "type": "button", "role": "option" }, "bind": { "key": "(preset.id)", "data-shader-preset": "(preset.id)", "aria-selected": "(shader === preset.id)", "title": "(preset.description)" }, "events": [{ "event": "mouseenter", "code": "hovered = preset.id;", "mods": [] }, { "event": "focus", "code": "hovered = preset.id;", "mods": [] }, { "event": "click", "code": "emit('choose', preset.id);", "mods": [] }], "children": [{ "tag": "span", "attrs": { "class": "effect-picker__swatch" }, "bind": { "style": "({ '--preset-color': preset.color })" }, "events": [], "children": [] }, { "tag": "span", "attrs": { "class": "effect-picker__label" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(preset.name)" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(preset.category)" }] }] }], "each": { "names": ["preset"], "value": "(shaderPresets)" } }] }, { "tag": "button", "attrs": { "class": "effect-picker__custom", "type": "button" }, "bind": { "aria-pressed": "(!shader)" }, "events": [{ "event": "mouseenter", "code": "hovered = '';", "mods": [] }, { "event": "focus", "code": "hovered = '';", "mods": [] }, { "event": "click", "code": "emit('choose', '');", "mods": [] }], "children": [{ "tag": "PhCodeBlock", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Custom shader'))" }] }], "otherwise": true }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const emit = options.emit;
  const icons = { smoke: PhCloud, ember: PhFireSimple, dust: PhDotsThreeOutline, arcane: PhSparkle, rain: PhCloudRain, snow: PhSnowflake, firefly: PhLightbulb2, leaves: PhLeaf, bubbles: PhCirclesThreePlus, ash: PhWind, blood: PhDrop, runes: PhPentagram };
  const title = computed(() => props.kind === "particle" ? text("Particles") : text("Shader presets"));
  const hovered = ref();
  const previewChoice = computed(() => hovered.value ?? (props.kind === "particle" ? props.particle : props.shader));
  const previewLabel = computed(() => props.kind === "particle" ? effectLabels[`lighting.particles.${previewChoice.value}`] ?? text("Particles") : shaderPresets.find((p) => p.id === previewChoice.value)?.name ?? text("Custom shader"));
  const panel = ref();
  const position = ref({ left: "13px", bottom: "89px" });
  function place() {
    const trigger = document.querySelector(`[data-effect-tool="${props.kind}"]`);
    if (!trigger)
      return;
    const r = trigger.getBoundingClientRect();
    const width = panel.value?.getBoundingClientRect().width ?? (props.kind === "shader" ? 754 : 430);
    position.value = { left: `${Math.max(8, Math.min(innerWidth - width - 8, r.left))}px`, bottom: `${innerHeight - r.top + 8}px` };
  }
  function outside(event) {
    if (event.target instanceof Element && !panel.value?.contains(event.target) && !event.target.closest("[data-effect-tool]"))
      emit("close");
  }
  onMounted(() => {
    place();
    window.addEventListener("resize", place);
    document.addEventListener("pointerdown", outside);
  });
  onBeforeUnmount(() => {
    window.removeEventListener("resize", place);
    document.removeEventListener("pointerdown", outside);
  });
  return { gwText: text, PhCloud, PhFireSimple, PhDotsThreeOutline, PhSparkle, PhCloudRain, PhSnowflake, PhLightbulb: PhLightbulb2, PhLeaf, PhCirclesThreePlus, PhWind, PhDrop, PhPentagram, PhCode, PhCodeBlock, PhX: PhX6, shaderPresets, effectLabels, EffectPreview: EffectPreview_native_default, icons, title, hovered, previewChoice, previewLabel, panel, position, place, outside, emit: options.emit };
});

// gravewright/maps/frontend/features/effects/model/shader-validation.js
var ShaderDraftValidator = class {
  gl;
  validate(source) {
    if (!source.trim())
      return text("The shader is empty.");
    if (source.length > 32e3)
      return text("Text is too long (32000 character limit).");
    this.gl ??= document.createElement("canvas").getContext("webgl2");
    const gl = this.gl;
    if (!gl)
      return text("WebGL 2 is unavailable to validate this shader.");
    const shader = gl.createShader(gl.FRAGMENT_SHADER);
    if (!shader)
      return text("Could not validate the shader.");
    try {
      gl.shaderSource(shader, PREAMBLE + USER_PREFIX + source + USER_SUFFIX);
      gl.compileShader(shader);
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? "" : gl.getShaderInfoLog(shader)?.replaceAll("\0", "").trim() || text("Invalid GLSL code.");
    } finally {
      gl.deleteShader(shader);
    }
  }
  dispose() {
    this.gl?.getExtension("WEBGL_lose_context")?.loseContext();
    this.gl = void 0;
  }
};

// gravewright/maps/frontend/features/scene-layers/ui/SceneSourcesWorkspace.native.js
var PhCopy3 = "PhCopy";
var PhClipboard2 = "PhClipboard";
var PhTrash6 = "PhTrash";
var SceneSourcesWorkspace_native_default = widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "scene-sources", "role": "group" }, "bind": { "aria-label": "(`Origens de ${noun} da cena`)" }, "events": [{ "event": "pointerdown", "code": "down;", "mods": [] }, { "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "up;", "mods": [] }, { "event": "dblclick", "code": "doubleClick;", "mods": [] }, { "event": "contextmenu", "code": "menu;", "mods": [] }, { "event": "wheel", "code": "wheel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x},${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": { "role": "button", "tabindex": "0", "class": "scene-sources__origin" }, "bind": { "key": "(effect.key)", "data-effect-id": "(effect.id)", "aria-label": "(gwText('{0}: {1}', effect.kind === 'light' ? 'Light' : effect.kind === 'particle' ? 'Particle' : 'Shader', effect.kind === 'light' ? effect.data.animation : effect.kind === 'particle' ? effect.data.kind : effect.data.name))", "data-effect-kind": "(effect.kind)", "class": "({ 'scene-sources__origin--selected': selection.includes(effect.key) })", "transform": "(`translate(${effect.x + (selection.includes(effect.key) ? delta.x : 0)},${effect.y + (selection.includes(effect.key) ? delta.y : 0)}) scale(${1 / viewport.scale})`)" }, "events": [], "children": [{ "tag": "title", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(effect.kind === 'light' ? effect.data.animation : effect.kind === 'shader' ? effect.data.name : effect.data.kind)" }, { "text": " " }, { "value": "(gwText('\xB7 double-click to edit'))" }] }, { "tag": "circle", "attrs": { "r": "13" }, "bind": {}, "events": [], "children": [] }, { "tag": "path", "attrs": {}, "bind": { "transform": "(`rotate(${effect.data.rotation})`)", "d": "(effect.kind === 'light' ? 'M 13 0 L 21 0 M 17 -5 L 21 0 L 17 5' : 'M 0 -21 L 0 -13 M -5 -17 L 0 -21 L 5 -17')" }, "events": [], "children": [] }, { "tag": "text", "attrs": { "text-anchor": "middle", "dominant-baseline": "central" }, "bind": {}, "events": [], "children": [{ "value": "(effect.kind === 'light' ? '\u2600' : effect.kind === 'particle' ? '\u2726' : '\u2318')" }] }], "each": { "names": ["effect"], "value": "(items)" } }, { "tag": "rect", "attrs": { "class": "scene-sources__marquee" }, "bind": { "x": "(Math.min(marquee.from.x, marquee.to.x))", "y": "(Math.min(marquee.from.y, marquee.to.y))", "width": "(Math.abs(marquee.to.x - marquee.from.x))", "height": "(Math.abs(marquee.to.y - marquee.from.y))", "stroke-width": "(1 / viewport.scale)" }, "events": [], "children": [], "when": "(marquee)" }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "(context.x)", "y": "(context.y)", "label": "(lights ? gwText('Lights') : gwText('Effects'))" }, "events": [{ "event": "close", "code": "context = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(!selected.length)" }, "events": [{ "event": "click", "code": "copy;", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Copy'))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(!clipboard.length)" }, "events": [{ "event": "click", "code": "paste;", "mods": [] }], "children": [{ "tag": "PhClipboard", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Paste'))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(!selected.length || busy)" }, "events": [{ "event": "click", "code": "remove();", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Remove'))" }, { "value": "(selected.length > 1 ? ` (${selected.length})` : '')" }] }], "when": "(context)" }, { "tag": "LightPicker", "attrs": {}, "bind": { "selected": "(lightChoice)" }, "events": [{ "event": "choose", "code": "choose;", "mods": [] }, { "event": "close", "code": "closePicker;", "mods": [] }], "children": [], "when": "(picker === 'light')" }, { "tag": "EffectPicker", "attrs": {}, "bind": { "key": "(picker)", "kind": "(picker)", "particle": "(particleChoice)", "shader": "(shaderChoice)" }, "events": [{ "event": "choose", "code": "choose;", "mods": [] }, { "event": "close", "code": "closePicker;", "mods": [] }], "children": [], "when": "(picker && picker !== 'light')" }, { "tag": "LightEditor", "attrs": {}, "bind": { "busy": "(busy)", "error": "(error)" }, "events": [{ "event": "close", "code": "closeEditor;", "mods": [] }, { "event": "change", "code": "changed;", "mods": [] }, { "event": "remove", "code": "remove(items.filter(e => e.id === editing));", "mods": [] }], "children": [], "when": "(editor === 'light')", "model": { "path": "(draft)", "mods": [] } }, { "tag": "EffectEditor", "attrs": {}, "bind": { "kind": "(editor)", "existing": "(!!editing)", "busy": "(busy)", "error": "(error)" }, "events": [{ "event": "close", "code": "closeEditor;", "mods": [] }, { "event": "change", "code": "changed;", "mods": [] }, { "event": "save", "code": "save();", "mods": [] }, { "event": "remove", "code": "remove(items.filter(e => e.id === editing));", "mods": [] }], "children": [], "when": "(editor && editor !== 'light')", "model": { "path": "(draft)", "mods": [] } }, { "tag": "section", "attrs": { "class": "gw-window scene-sources__confirm", "role": "alertdialog" }, "bind": { "aria-label": "(gwText('Clear scene {0}', noun))" }, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Clear '))" }, { "value": "(lights ? gwText('all lights') : gwText('all effects'))" }, { "text": " " }, { "value": "(gwText('from this scene?'))" }] }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(lights ? gwText('Light sources will be removed.') : gwText('Particles and shaders will be removed.'))" }] }, { "tag": "div", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "clearConfirm = false;", "mods": [] }], "children": [{ "value": "(gwText('Cancel'))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "clear;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Clear '))" }, { "value": "(noun)" }] }] }], "when": "(clearConfirm)" }, { "tag": "p", "attrs": { "class": "scene-sources__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "(error)" }], "when": "(error && !editor)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const emit = options.emit;
  const lights = props.layer === "lighting";
  const batchArea = lights ? "light-selection" : "effects";
  const lightChoice = ref("torch");
  const noun = lights ? text("lights") : text("effects");
  const area2 = (kind) => kind === "light" ? "lights" : kind === "particle" ? "particles" : "shaders";
  const identityKey = (kind) => kind === "light" ? "light_id" : kind === "particle" ? "emitter_id" : "shader_id";
  const rowKey = (kind) => kind === "light" ? "light" : kind === "particle" ? "emitter" : "shader";
  const root = ref();
  const items = computed(() => effects(props.state, props.layer));
  const selection = ref([]), clipboard = ref([]);
  const selected = computed(() => items.value.filter((e) => selection.value.includes(e.key)));
  const context = ref();
  const picker = ref(), particleChoice = ref("smoke"), shaderChoice = ref("orb-1");
  const editor = ref(), editing = ref();
  const draft = ref(defaults()), error = ref(""), busy = ref(false), clearConfirm = ref(false);
  const delta = ref({ x: 0, y: 0 });
  const marquee = ref();
  let gesture;
  let editorVisit = 0, previewFrame = 0;
  let pendingDelta = { x: 0, y: 0 };
  let lastPoint = { x: 0, y: 0 }, closed = false, queue = Promise.resolve();
  let saveTimer;
  let shaderTimer;
  const validator = new ShaderDraftValidator();
  const abort = new AbortController();
  const api = new BlockStateApi(new HttpClient2(void 0, () => abort.signal));
  const writer = new BlockStateApi();
  const containerId = props.containerId, blockId = props.blockId;
  function point(event) {
    const r = root.value.getBoundingClientRect();
    return { x: (event.clientX - r.left - props.viewport.x) / props.viewport.scale, y: (event.clientY - r.top - props.viewport.y) / props.viewport.scale };
  }
  function center() {
    const r = root.value?.getBoundingClientRect();
    return { x: ((r?.width ?? 0) / 2 - props.viewport.x) / props.viewport.scale, y: ((r?.height ?? 0) / 2 - props.viewport.y) / props.viewport.scale };
  }
  function refs(list = selected.value) {
    return list.map((e) => ({ id: e.id, kind: e.kind }));
  }
  function run(area3, action2, data, after) {
    const operation = async () => {
      if (closed)
        return;
      busy.value = true;
      error.value = "";
      try {
        const result = await writer.command(containerId, blockId, area3, action2, data);
        if (closed)
          return;
        after?.(result);
        const state = await api.state(containerId, blockId);
        if (!closed) {
          emit("changed", state);
          if (area3 === batchArea && action2 === "transform" && editing.value) {
            const row = effects(state, props.layer).find((e) => e.id === editing.value);
            if (row)
              draft.value = { ...draft.value, x: row.x, y: row.y, rotation: row.data.rotation };
          }
        }
      } catch (reason) {
        if (!closed)
          error.value = text("Could not save the change. Check the data and try again.");
      } finally {
        if (!closed) {
          busy.value = false;
          emit("preview", void 0);
        }
      }
    };
    queue = queue.then(operation);
    return queue;
  }
  function open(kind, effect) {
    closePicker();
    flush();
    if (shaderTimer)
      clearTimeout(shaderTimer);
    emit("preview", void 0);
    ++editorVisit;
    context.value = void 0;
    editor.value = kind;
    editing.value = effect.id;
    draft.value = { ...effect.data };
    if (kind === "shader") {
      const match = /^gravewright-preset:\/\/([^/]+)\/v1$/.exec(draft.value.source);
      if (match)
        draft.value.source = shaderPresets.find((p) => p.id === match[1])?.source ?? draft.value.source;
    }
  }
  function closePicker() {
    picker.value = void 0;
    emit("preview", void 0);
  }
  function action(id) {
    const previous = picker.value;
    closePicker();
    closeEditor();
    if (id === "clear-effects" || id === "clear-lights") {
      clearConfirm.value = true;
      return;
    }
    if ((id === "particle" || id === "shader" || id === "light") && previous !== id)
      picker.value = id;
  }
  function choose(id) {
    if (picker.value === "light")
      lightChoice.value = id;
    else if (picker.value === "particle")
      particleChoice.value = id;
    else
      shaderChoice.value = id;
    closePicker();
  }
  function shaderData(id) {
    const preset = shaderPresets.find((p) => p.id === id);
    return { ...defaults(), scale: 1, color: "#8fb6ff", ...preset };
  }
  defineExpose({ action, doubleClick });
  function save(at) {
    if (!editor.value)
      return;
    if (saveTimer)
      clearTimeout(saveTimer);
    saveTimer = void 0;
    const kind = editor.value;
    if (kind === "shader") {
      error.value = validator.validate(draft.value.source);
      if (error.value)
        return;
    }
    const data = payload(kind, { ...draft.value, ...at });
    const identity = editing.value, visit = editorVisit;
    void run(area2(kind), identity ? "update" : "create", identity ? { ...data, [identityKey(kind)]: identity } : data, (result) => {
      const row = result[rowKey(kind)];
      if (row && editor.value === kind && visit === editorVisit) {
        editing.value = row.id;
        selection.value = [`${kind}:${row.id}`];
      }
    });
  }
  function previewShader() {
    if (closed || editor.value !== "shader")
      return;
    error.value = validator.validate(draft.value.source);
    if (error.value)
      return;
    const shader = { ...draft.value, id: editing.value ?? "draft-shader" };
    emit("preview", { ...props.state, shaders: [...props.state.shaders.filter((s) => s.id !== shader.id), shader] });
  }
  function changed() {
    if (editor.value === "light" && draft.value.dim_radius > 0)
      draft.value.dim_radius = Math.max(draft.value.dim_radius, draft.value.bright_radius);
    if (editor.value === "shader") {
      if (shaderTimer)
        clearTimeout(shaderTimer);
      shaderTimer = setTimeout(previewShader, 250);
      return;
    }
    if (editor.value && editing.value) {
      if (saveTimer)
        clearTimeout(saveTimer);
      saveTimer = setTimeout(() => save(), 250);
    }
  }
  function flush() {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = void 0;
      save();
    }
  }
  function closeEditor() {
    flush();
    if (shaderTimer)
      clearTimeout(shaderTimer);
    emit("preview", void 0);
    validator.dispose();
    ++editorVisit;
    editor.value = void 0;
    editing.value = void 0;
  }
  function createAt(at) {
    const kind = props.tool;
    const data = kind === "light" ? { ...defaults(), ...lightPresets.find((p) => p.id === lightChoice.value), animation: lightChoice.value, ...at } : kind === "particle" ? { ...defaults(), ...PARTICLE_DEFAULTS[particleChoice.value], light_response: ["smoke", "dust", "rain", "snow", "leaves", "bubbles", "ash", "blood"].includes(particleChoice.value) ? 0.8 : 0, light_emission: ["ember", "firefly", "arcane", "runes"].includes(particleChoice.value) ? 0.15 : 0, kind: particleChoice.value, ...at } : { ...shaderData(shaderChoice.value), ...at };
    closePicker();
    void run(area2(kind), "create", payload(kind, data), (result) => {
      const row = result[rowKey(kind)];
      if (row)
        selection.value = [`${kind}:${row.id}`];
    });
  }
  function down(event) {
    if (!["select", "light", "particle", "shader"].includes(props.tool))
      return;
    if (event.button === 1)
      return;
    if (event.button === 2 && !hitEffect(items.value, point(event), props.viewport.scale))
      return;
    event.stopPropagation();
    event.preventDefault();
    context.value = void 0;
    closePicker();
    if (event.button !== 0 || busy.value)
      return;
    const from = point(event);
    lastPoint = from;
    const hit3 = hitEffect(items.value, from, props.viewport.scale);
    if (hit3) {
      if (event.shiftKey)
        selection.value = selection.value.includes(hit3.key) ? selection.value.filter((k) => k !== hit3.key) : [...selection.value, hit3.key];
      else if (!selection.value.includes(hit3.key))
        selection.value = [hit3.key];
    }
    const original = [...selection.value];
    if (!hit3 && !event.shiftKey && props.tool === "select")
      selection.value = [];
    gesture = { pointer: event.pointerId, from, to: from, hit: hit3, original, additive: event.shiftKey };
    root.value?.setPointerCapture(event.pointerId);
  }
  function paintPreview(dx, dy) {
    const move2 = (kind, data) => selection.value.includes(`${kind}:${data.id}`) ? { ...data, x: data.x + dx, y: data.y + dy } : data;
    emit("preview", { ...props.state, particles: props.state.particles.map((p) => move2("particle", p)), shaders: props.state.shaders.map((p) => move2("shader", p)), lights: props.state.lights.map((p) => move2("light", p)) });
  }
  function previewMove(dx, dy) {
    pendingDelta = { x: dx, y: dy };
    if (!previewFrame)
      previewFrame = requestAnimationFrame(() => {
        previewFrame = 0;
        if (!closed)
          paintPreview(pendingDelta.x, pendingDelta.y);
      });
  }
  function move(event) {
    lastPoint = point(event);
    if (!gesture || gesture.pointer !== event.pointerId)
      return;
    event.stopPropagation();
    gesture.to = lastPoint;
    if (gesture.hit) {
      delta.value = { x: lastPoint.x - gesture.from.x, y: lastPoint.y - gesture.from.y };
      previewMove(delta.value.x, delta.value.y);
    } else if (props.tool === "select") {
      marquee.value = { from: gesture.from, to: lastPoint };
      selection.value = [.../* @__PURE__ */ new Set([...gesture.additive ? gesture.original : [], ...inMarquee(items.value, gesture.from, lastPoint)])];
    }
  }
  function up(event) {
    if (!gesture || gesture.pointer !== event.pointerId)
      return;
    event.stopPropagation();
    const g = gesture;
    gesture = void 0;
    marquee.value = void 0;
    cancelAnimationFrame(previewFrame);
    previewFrame = 0;
    if (event.type === "pointercancel") {
      selection.value = g.original;
      delta.value = { x: 0, y: 0 };
      emit("preview", void 0);
      return;
    }
    const to = point(event);
    const moved = Math.hypot(to.x - g.from.x, to.y - g.from.y) * props.viewport.scale > 3;
    if (g.hit && moved) {
      delta.value = { x: to.x - g.from.x, y: to.y - g.from.y };
      paintPreview(delta.value.x, delta.value.y);
      void run(batchArea, "transform", { effects: refs(), dx: delta.value.x, dy: delta.value.y }).finally(() => {
        delta.value = { x: 0, y: 0 };
      });
    } else if (g.hit && !moved && !g.additive)
      selection.value = [g.hit.key];
    else if (!g.hit && (props.tool === "particle" || props.tool === "shader" || props.tool === "light"))
      createAt(to);
    else
      emit("preview", void 0);
    if (!g.hit || !moved)
      delta.value = { x: 0, y: 0 };
  }
  function doubleClick(event) {
    const hit3 = hitEffect(items.value, point(event), props.viewport.scale);
    if (hit3) {
      event.stopPropagation();
      selection.value = [hit3.key];
      emit("tool", "select");
      open(hit3.kind, hit3);
    }
  }
  function menu(event) {
    const world = point(event), hit3 = hitEffect(items.value, world, props.viewport.scale);
    if (!hit3)
      return;
    event.preventDefault();
    event.stopPropagation();
    if (hit3 && !selection.value.includes(hit3.key))
      selection.value = [hit3.key];
    context.value = { x: event.clientX, y: event.clientY, world };
  }
  function copy() {
    clipboard.value = selected.value.map((e) => ({ ...e, data: structuredClone({ ...e.data }) }));
    context.value = void 0;
  }
  function paste() {
    if (!clipboard.value.length)
      return;
    const at = context.value?.world ?? lastPoint;
    context.value = void 0;
    void run(batchArea, "paste", { effects: translatedCopies(clipboard.value, at) }, (r) => {
      selection.value = r.effects.map((e) => `${e.kind}:${e.id}`);
    });
  }
  function discardPending() {
    if (saveTimer)
      clearTimeout(saveTimer);
    saveTimer = void 0;
    if (shaderTimer)
      clearTimeout(shaderTimer);
    shaderTimer = void 0;
    ++editorVisit;
  }
  function remove(list = selected.value) {
    if (list.some((e) => e.id === editing.value))
      discardPending();
    context.value = void 0;
    if (!list.length)
      return;
    const ids = refs(list);
    void run(batchArea, "delete", { effects: ids }, () => {
      selection.value = [];
      if (list.some((e) => e.id === editing.value)) {
        editor.value = void 0;
        editing.value = void 0;
      }
    });
  }
  function clear() {
    discardPending();
    clearConfirm.value = false;
    void run(batchArea, "clear", {}, () => {
      selection.value = [];
      editor.value = void 0;
      editing.value = void 0;
    });
  }
  function wheel(event) {
    if (!event.shiftKey)
      return;
    event.preventDefault();
    event.stopPropagation();
    if (selected.value.length)
      void run(batchArea, "transform", { effects: refs(), rotation: event.deltaY > 0 ? 15 : -15 });
  }
  function keyboard(event) {
    if (props.tool === "managed" || document.querySelector(".house-menu-scrim")?.getClientRects().length)
      return;
    if (event.target instanceof Element && event.target.closest("input,textarea,select,[contenteditable=true],.gw-window,dialog[open]"))
      return;
    const key = event.key.toLowerCase();
    if (event.key === "Escape") {
      if (gesture) {
        cancelAnimationFrame(previewFrame);
        previewFrame = 0;
        gesture = void 0;
        delta.value = { x: 0, y: 0 };
        marquee.value = void 0;
        emit("preview", void 0);
      } else {
        context.value = void 0;
        clearConfirm.value = false;
        closePicker();
        closeEditor();
        selection.value = [];
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    if (["Delete", "Backspace"].includes(event.key)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      remove();
    }
    if (event.ctrlKey || event.metaKey) {
      if (key === "c") {
        event.preventDefault();
        event.stopImmediatePropagation();
        copy();
      }
      if (key === "v") {
        event.preventDefault();
        event.stopImmediatePropagation();
        paste();
      }
    }
  }
  watch(() => props.state, () => {
    const available = new Set(items.value.map((e) => e.key));
    selection.value = selection.value.filter((k) => available.has(k));
  });
  onMounted(() => {
    lastPoint = center();
    document.addEventListener("keydown", keyboard, true);
  });
  onBeforeUnmount(() => {
    if (saveTimer && editor.value && editor.value !== "shader" && editing.value) {
      clearTimeout(saveTimer);
      const kind = editor.value;
      const data = { ...payload(kind, draft.value), [identityKey(kind)]: editing.value };
      queue = queue.then(async () => {
        await writer.command(containerId, blockId, area2(kind), "update", data);
      }).catch(() => {
      });
    }
    closed = true;
    abort.abort();
    cancelAnimationFrame(previewFrame);
    if (shaderTimer)
      clearTimeout(shaderTimer);
    validator.dispose();
    document.removeEventListener("keydown", keyboard, true);
    emit("preview", void 0);
  });
  return { gwText: text, PhCopy: PhCopy3, PhClipboard: PhClipboard2, PhTrash: PhTrash6, BlockStateApi, HttpClient: HttpClient2, DirectoryContextMenu: DirectoryContextMenu_native_default, LightPicker: LightPicker_native_default, LightEditor: LightEditor_native_default, lightPresets, EffectEditor: EffectEditor_native_default, EffectPicker: EffectPicker_native_default, PARTICLE_DEFAULTS, ShaderDraftValidator, shaderPresets, effects, defaults, hitEffect, inMarquee, payload, translatedCopies, lights, batchArea, lightChoice, noun, area: area2, identityKey, rowKey, root, items, selection, clipboard, selected, context, picker, particleChoice, shaderChoice, editor, editing, draft, error, busy, clearConfirm, delta, marquee, gesture, editorVisit, previewFrame, pendingDelta, lastPoint, closed, queue, saveTimer, shaderTimer, validator, writer, containerId, blockId, point, center, refs, run, open, closePicker, action, choose, shaderData, save, previewShader, changed, flush, closeEditor, createAt, down, paintPreview, previewMove, move, up, doubleClick, menu, copy, paste, discardPending, remove, clear, wheel, keyboard, emit: options.emit };
});

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
var PhWaveform2 = "PhWaveform";
var PhFilePdf = "PhFilePdf";
var PhFolder = "PhFolder";
var PhFolderOpen = "PhFolderOpen";
var PhFolderPlus = "PhFolderPlus";
var PhMagnifyingGlass = "PhMagnifyingGlass";
var PhTrash7 = "PhTrash";
var PhArrowsLeftRight = "PhArrowsLeftRight";
var AssetUploadLibrary_native_default = widget([{ "tag": "section", "attrs": { "class": "asset-library" }, "bind": { "aria-label": 'gwText("Table assets")' }, "events": [], "children": [{ "tag": "header", "attrs": { "class": "asset-library__bar" }, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "asset-library__uploads" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": { "class": "asset-library__upload" }, "bind": { "key": "u.id", "class": '({ "asset-library__upload--disabled": busy })' }, "events": [], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "u.icon" }, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "u.label" }] }, { "tag": "input", "attrs": { "type": "file", "multiple": "" }, "bind": { "aria-label": 'gwText("Upload {0}", u.label)', "accept": "u.accept", "disabled": "busy" }, "events": [{ "event": "change", "code": "choose($event, u.purpose);", "mods": [] }], "children": [] }], "each": { "names": ["u"], "value": "uploads" } }], "when": "gm" }, { "tag": "label", "attrs": { "class": "asset-library__search" }, "bind": {}, "events": [], "children": [{ "tag": "PhMagnifyingGlass", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "input", "attrs": { "type": "search" }, "bind": { "placeholder": 'gwText("Search files")', "aria-label": 'gwText("Search files")' }, "events": [], "children": [], "model": { "path": "(search)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "asset-library__filters", "role": "group" }, "bind": { "aria-label": 'gwText("File type")' }, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "f.id", "aria-pressed": "kind === f.id" }, "events": [{ "event": "click", "code": "kind = f.id;", "mods": [] }], "children": [{ "value": "f.label" }, { "text": " " }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "f.count" }] }], "each": { "names": ["f"], "value": "filters" } }] }] }, { "tag": "p", "attrs": { "class": "asset-library__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "error" }], "when": "error" }, { "tag": "div", "attrs": { "class": "asset-library__notice", "role": "status" }, "bind": {}, "events": [], "children": [{ "value": 'notice || gwText("Saving\\u2026")' }, { "tag": "progress", "attrs": { "max": "100" }, "bind": { "value": "progress", "aria-label": 'gwText("Upload progress")' }, "events": [], "children": [], "when": 'busy && notice.startsWith(gwText("Uploading"))' }], "when": "busy || notice" }, { "tag": "div", "attrs": { "class": "asset-library__body" }, "bind": {}, "events": [], "children": [{ "tag": "aside", "attrs": { "class": "asset-library__folders" }, "bind": { "aria-label": 'gwText("Asset folders")' }, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "aria-pressed": "!folder" }, "events": [{ "event": "click", "code": 'folder = "";', "mods": [] }, { "event": "dragover", "code": "", "mods": ["prevent"] }, { "event": "drop", "code": 'drop($event, "");', "mods": ["stop", "prevent"] }], "children": [{ "tag": "PhFolderOpen", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Root")' }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "state.assets.filter((a) => !a.folder_id).length" }] }] }, { "tag": "button", "attrs": {}, "bind": { "key": "f.id", "aria-pressed": "folder === f.id" }, "events": [{ "event": "click", "code": "folder = f.id;", "mods": [] }, { "event": "dragover", "code": "", "mods": ["prevent"] }, { "event": "drop", "code": "drop($event, f.id);", "mods": ["stop", "prevent"] }], "children": [{ "tag": "PhFolder", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "f.name" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "state.assets.filter((a) => a.folder_id === f.id).length" }] }], "each": { "names": ["f"], "value": "state.folders" } }, { "tag": "form", "attrs": { "class": "asset-library__folder-create" }, "bind": {}, "events": [{ "event": "submit", "code": 'command("folder-create", { name: folderName.trim() });', "mods": ["prevent"] }], "children": [{ "tag": "input", "attrs": { "maxlength": "120", "required": "" }, "bind": { "placeholder": 'gwText("New folder")', "aria-label": 'gwText("Folder name")', "disabled": "busy" }, "events": [], "children": [], "model": { "path": "(folderName)", "mods": [] } }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy || !folderName.trim()", "aria-label": 'gwText("Create folder")' }, "events": [], "children": [{ "tag": "PhFolderPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "when": "gm" }] }, { "tag": "div", "attrs": { "class": "asset-library__grid" }, "bind": { "class": '({ "asset-library__grid--drop": dragging })' }, "events": [{ "event": "dragover", "code": "dragging = true;", "mods": ["prevent"] }, { "event": "dragleave", "code": "dragging = false;", "mods": ["self"] }, { "event": "drop", "code": "drop($event);", "mods": ["prevent"] }], "children": [{ "tag": "article", "attrs": { "class": "asset-library__card" }, "bind": { "key": "asset.id", "draggable": "gm && !busy", "title": "asset.filename" }, "events": [{ "event": "dragstart", "code": "dragAsset($event, asset);", "mods": [] }, { "event": "contextmenu", "code": "openContext($event, asset);", "mods": [] }], "children": [{ "tag": "div", "attrs": { "class": "asset-library__thumb" }, "bind": {}, "events": [], "children": [{ "tag": "img", "attrs": { "alt": "", "loading": "lazy", "draggable": "false" }, "bind": { "src": "asset.src" }, "events": [], "children": [], "when": 'asset.kind === "image"' }, { "tag": "PhFilePdf", "attrs": {}, "bind": {}, "events": [], "children": [], "otherwiseWhen": 'asset.kind === "pdf"' }, { "tag": "PhWaveform", "attrs": {}, "bind": {}, "events": [], "children": [], "otherwise": true }] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "asset.filename" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'asset.kind === "image" ? `${asset.width} \\xD7 ${asset.height}` : bytesLabel(asset.byte_size)' }] }, { "tag": "div", "attrs": { "class": "asset-library__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Move file")' }, "events": [{ "event": "click", "code": 'moving = asset;\ntarget = asset.folder_id || "";', "mods": [] }], "children": [{ "tag": "PhArrowsLeftRight", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy", "aria-label": 'gwText("Delete file")' }, "events": [{ "event": "click", "code": "removing = asset;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }], "when": "gm" }], "each": { "names": ["asset"], "value": "visible" } }, { "tag": "p", "attrs": { "class": "asset-library__empty" }, "bind": {}, "events": [], "children": [{ "value": 'search ? gwText("No files found.") : gm ? gwText("This folder is empty. Upload or drop files here.") : gwText("This folder is empty.")' }], "when": "!visible.length" }] }] }, { "tag": "footer", "attrs": { "class": "asset-library__foot" }, "bind": {}, "events": [], "children": [{ "value": "visible.length" }, { "text": "/" }, { "value": "state.assets.length" }, { "text": " \xB7 " }, { "value": "bytesLabel(visibleBytes)" }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Images: 10 MB \\xB7 Audio: 100 MB \\xB7 PDF: 25 MB")' }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "context.x", "y": "context.y", "label": 'gwText("File actions")' }, "events": [{ "event": "close", "code": "context = void 0;", "mods": [] }], "children": [{ "tag": "li", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": 'moving = context.asset;\ntarget = moving.folder_id || "";\ncontext = void 0;', "mods": [] }], "children": [{ "tag": "PhArrowsLeftRight", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Move to folder")' }] }] }, { "tag": "li", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "class": "is-danger" }, "bind": {}, "events": [{ "event": "click", "code": "removing = context.asset;\ncontext = void 0;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": 'gwText("Delete file")' }] }] }], "when": "context" }] }, { "tag": "form", "attrs": { "class": "asset-library__dialog", "role": "dialog" }, "bind": { "aria-label": 'moving ? gwText("Move file") : gwText("Delete file")' }, "events": [{ "event": "submit", "code": 'moving ? command("move", { asset_id: moving.id, folder_id: target || null }) : command("delete", { asset_id: removing.id });', "mods": ["prevent"] }], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'moving ? gwText("Move") : gwText("Delete")' }, { "text": " " }, { "value": "(moving || removing)?.filename" }] }, { "tag": "select", "attrs": {}, "bind": { "aria-label": 'gwText("Destination folder")' }, "events": [], "children": [{ "tag": "option", "attrs": { "value": "" }, "bind": {}, "events": [], "children": [{ "value": 'gwText("Root")' }] }, { "tag": "option", "attrs": {}, "bind": { "key": "f.id", "value": "f.id" }, "events": [], "children": [{ "value": "f.name" }], "each": { "names": ["f"], "value": "state.folders" } }], "when": "moving", "model": { "path": "(target)", "mods": [] } }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": 'gwText("Delete this file from the library?")' }], "otherwise": true }, { "tag": "footer", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "busy" }, "events": [{ "event": "click", "code": "moving = void 0;\nremoving = void 0;", "mods": [] }], "children": [{ "value": 'gwText("Cancel")' }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "busy" }, "events": [], "children": [{ "value": 'moving ? gwText("Move") : gwText("Delete")' }] }] }], "when": "moving || removing" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
  const HttpClient2 = options.HttpClient;
  const BlockStateApi = class {
    command(_c, _b, a, b, p) {
      return options.command(a, b, p);
    }
    state() {
      return options.read();
    }
  };
  const props = options.props;
  const scope = new ResourceScope(), http = new HttpClient2(void 0, () => scope.signal), root = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
  const state = ref({ assets: [], folders: [] }), folder = ref(""), kind = ref(""), search = ref(""), folderName = ref(""), busy = ref(false), error = ref(""), notice = ref(""), progress = ref(0), dragging = ref(false);
  const context = ref(), removing = ref(), moving = ref(), target = ref("");
  const uploads = [{ id: "image", get label() {
    return text("Images");
  }, icon: PhImage, accept: IMAGE_ACCEPT, purpose: "" }, { id: "ambient", get label() {
    return text("Ambient audio");
  }, icon: PhMusicNotes, accept: AUDIO_ACCEPT, purpose: "ambient" }, { id: "effect", get label() {
    return text("Sound effect");
  }, icon: PhWaveform2, accept: AUDIO_ACCEPT, purpose: "effect" }, { id: "pdf", label: "PDFs", icon: PhFilePdf, accept: "application/pdf", purpose: "pdf-sheet" }];
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
  return { gwText: text, PhImage, PhMusicNotes, PhWaveform: PhWaveform2, PhFilePdf, PhFolder, PhFolderOpen, PhFolderPlus, PhMagnifyingGlass, PhTrash: PhTrash7, PhArrowsLeftRight, HttpClient: HttpClient2, ResourceScope, DirectoryContextMenu: DirectoryContextMenu_native_default, IMAGE_ACCEPT, AUDIO_ACCEPT, assetKinds, bytesLabel, uploadError, uploadFile, validateUpload, scope, http, root, state, folder, kind, search, folderName, busy, error, notice, progress, dragging, context, removing, moving, target, uploads, filters, visible, visibleBytes, refreshId, refresh, command, upload, choose, openContext, dragAsset, drop, emit: options.emit };
});

// gravewright/maps/frontend/native/tools.js
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
  let state = api.state, drawing, images, effects2, library, libraryHost, closed = false;
  const hosts = { drawing: document.createElement("div"), images: document.createElement("div"), effects: document.createElement("div"), measurement: document.createElement("div"), markers: document.createElement("div") };
  for (const host of Object.values(hosts)) {
    host.style.display = "contents";
    surface.append(host);
  }
  const common = { HttpClient, command: api.command, read: api.read };
  const base = () => ({ viewport: board.viewport(), containerId: map.containerId, blockId: map.blockId, cell: map.gridSize * map.imageScale, grid: map.gridVisible });
  let measureRows = [], selection;
  const measurement = MeasurementWorkspace_native_default(hosts.measurement, { ...common, props: { ...base(), active: false, maxRows: state.capabilities?.maxMeasurements, measureValue: map.measureValue, measureUnit: map.measureUnit }, emit(type, value) {
    if (type === "change") measureRows = value;
    if (type === "close") {
      stateAPI.mergePatch({ _tool: "select" });
      sync();
    }
  } });
  let markerQueue = Promise.resolve();
  const markerKeys = ["id", "kind", "origin", "length", "width", "direction", "angle", "color"];
  const clean = (rows) => rows.map((row) => Object.fromEntries(markerKeys.map((k) => [k, row[k]])));
  const markers = MeasurementWorkspace_native_default(hosts.markers, { ...common, props: { ...base(), active: false, shared: true, rows: state.markers || [], maxRows: state.capabilities?.maxMarkers, measureValue: map.measureValue, measureUnit: map.measureUnit }, emit(type, rows) {
    if (type === "close") {
      stateAPI.mergePatch({ _tool: "select" });
      sync();
    }
    if (type !== "change" || JSON.stringify(clean(rows)) === JSON.stringify(clean(state.markers || []))) return;
    const expected = state.version;
    markerQueue = markerQueue.then(() => api.command("markers", "replace", { rows: clean(rows), expected_version: expected })).catch((error) => {
      window.dispatchEvent(new CustomEvent("gravewright:tool-error", { detail: { message: error.message } }));
      return api.read();
    });
  } });
  selection = createSelection(surface, board, map, gm, api, stateAPI, { rows: () => measureRows, replace: (rows) => measurement.call("replace", rows) });
  function sync() {
    if (closed || !board.viewport())
      return;
    const layer = stateAPI.getPath("_layer"), tool = stateAPI.getPath("_tool");
    selection?.update(state);
    const measure = ["measure", "templates"].includes(tool);
    markers.update({ ...base(), active: tool === "templates", shared: true, rows: state.markers || [], maxRows: state.capabilities?.maxMarkers, measureValue: map.measureValue, measureUnit: map.measureUnit });
    measurement.update({ ...base(), active: tool === "measure", maxRows: state.capabilities?.maxMeasurements, measureValue: map.measureValue, measureUnit: map.measureUnit });
    const draw = gm && tool === "draw" && ["game", "gm"].includes(layer);
    if (draw && !drawing)
      drawing = DrawingWorkspace_native_default(hosts.drawing, { ...common, props: { ...base(), document: state.drawings, audience: layer === "gm" ? "gm" : "campaign" }, emit(type) {
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
    if (compose && !images)
      images = ImageWorkspace_native_default(hosts.images, { ...common, props: { ...base(), images: state.images, tool }, emit(type, value) {
        if (type === "refresh")
          void api.read();
        if (type === "preview")
          void board.update({ state: value ? { ...state, images: state.images.map((i) => i.id === value.id ? value : i) } : state });
      } });
    else if (!compose && images) {
      images.destroy();
      images = void 0;
    } else
      images?.update({ ...base(), images: state.images, tool });
    const effect = gm && layer === "effects" && !measure;
    if (effect && !effects2)
      effects2 = SceneSourcesWorkspace_native_default(hosts.effects, { ...common, props: { ...base(), state, layer: "effects", tool }, emit(type, value) {
        if (type === "changed")
          update(value);
        if (type === "preview")
          void board.update({ state: value || state });
        if (type === "tool") {
          stateAPI.mergePatch({ _tool: value });
          sync();
        }
      } });
    else if (!effect && effects2) {
      effects2.destroy();
      effects2 = void 0;
    } else
      effects2?.update({ ...base(), state, tool });
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
    libraryHost.querySelector('[aria-label="Close library"]').onclick = openLibrary;
    library = AssetUploadLibrary_native_default(libraryHost.querySelector("[data-library-body]"), { ...common, props: { containerId: map.containerId, gm, revision: 0 }, emit() {
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
      library = index === 1 ? window.gravewrightTableMedia.mountDecks(body) : AssetUploadLibrary_native_default(body, { ...common, props: { containerId: map.containerId, gm, revision: 0 }, emit() {
      } });
      tabs.forEach((button, i) => button.setAttribute("aria-pressed", String(i === index)));
    });
    vMovableResizable.mounted(libraryHost);
  }
  function editSelection({ detail: { object, event } }) {
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
      effects2?.call("doubleClick", event);
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
    else if (effects2) {
      const tool = button.dataset.nativeTool;
      if (["particle", "shader"].includes(tool)) {
        stateAPI.mergePatch({ _tool: tool });
        sync();
      }
      effects2.call("action", tool);
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
    window.removeEventListener("gravewright:selection-edit", editSelection);
    selection?.destroy();
    drawing?.destroy();
    images?.destroy();
    effects2?.destroy();
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
