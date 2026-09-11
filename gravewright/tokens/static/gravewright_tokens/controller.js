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
    const translated = detail.messages?.text?.[source];
    return typeof translated === "string" ? translated : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
}

// gravewright/maps/frontend/features/tokens/model/token-interaction.js
function hitToken(point, tokens, cell) {
  return [...tokens].reverse().find((t) => point.x >= t.gridX * cell && point.x <= (t.gridX + t.cells) * cell && point.y >= t.gridY * cell && point.y <= (t.gridY + (t.heightCells ?? t.cells)) * cell);
}
function inMarquee(token, a, b, cell) {
  const x = (token.gridX + token.cells / 2) * cell, y = (token.gridY + (token.heightCells ?? token.cells) / 2) * cell;
  return x >= Math.min(a.x, b.x) && x <= Math.max(a.x, b.x) && y >= Math.min(a.y, b.y) && y <= Math.max(a.y, b.y);
}
function position(token, delta, cell, width, height, grid) {
  return { gridX: Math.max(0, Math.min(Math.max(0, width / cell - token.cells), grid ? Math.round(token.gridX + delta.x / cell) : token.gridX + delta.x / cell)), gridY: Math.max(0, Math.min(Math.max(0, height / cell - (token.heightCells ?? token.cells)), grid ? Math.round(token.gridY + delta.y / cell) : token.gridY + delta.y / cell)) };
}
function movementBlocked(token, to, walls, cell) {
  const a = { x: (token.gridX + token.cells / 2) * cell, y: (token.gridY + (token.heightCells ?? token.cells) / 2) * cell }, b = { x: (to.gridX + token.cells / 2) * cell, y: (to.gridY + (token.heightCells ?? token.cells) / 2) * cell }, rx = b.x - a.x, ry = b.y - a.y;
  return walls.some((w) => {
    if (w.movement_behavior === "pass" || w.kind === "door" && w.door_state === "open" || w.vertical_bottom != null && (token.elevation ?? 0) < w.vertical_bottom || w.vertical_top != null && (token.elevation ?? 0) > w.vertical_top)
      return false;
    const sx = w.x2 - w.x1, sy = w.y2 - w.y1, den = rx * sy - ry * sx;
    if (Math.abs(den) < 1e-9)
      return false;
    const qx = w.x1 - a.x, qy = w.y1 - a.y, t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
    return t >= 0 && t <= 1 && u >= 0 && u <= 1;
  });
}

// gravewright/maps/frontend/features/tokens/model/token-vision.js
function distancePerCell(value) {
  return Number.isFinite(value) && value > 0 ? value : 1;
}

// gravewright/maps/frontend/features/tokens/model/token-route.js
function routeMeasurements(route, measureValue) {
  const scale = distancePerCell(measureValue);
  const segments = route.slice(1).map((step, index) => {
    const from = route[index][0], to = step[0];
    return {
      distance: Math.hypot(to.gridX - from.gridX, to.gridY - from.gridY) * scale,
      x: (from.gridX + from.cells / 2 + to.gridX + to.cells / 2) / 2,
      y: (from.gridY + (from.heightCells ?? from.cells) / 2 + to.gridY + (to.heightCells ?? to.cells) / 2) / 2
    };
  });
  return { segments, total: segments.reduce((sum, segment) => sum + segment.distance, 0) };
}
var ROUTE_CELLS_PER_SECOND = 4;
var MAX_ROUTE_POINTS = 64;
function routeLengths(route) {
  return route.slice(1).map((step, index) => Math.max(0, ...step.map((token, i) => {
    const previous = route[index][i];
    return Math.hypot(token.gridX - previous.gridX, token.gridY - previous.gridY);
  })));
}
function routePosition(route, lengths, distance) {
  let segment = 0, remaining = Math.max(0, distance);
  while (segment < lengths.length && remaining >= lengths[segment]) {
    remaining -= lengths[segment];
    segment++;
  }
  if (segment >= lengths.length)
    return { tokens: route.at(-1) ?? [], passed: lengths.length, done: true };
  const from = route[segment], to = route[segment + 1], t = lengths[segment] > 0 ? remaining / lengths[segment] : 1;
  return { tokens: to.map((token, i) => ({ ...token, gridX: from[i].gridX + (token.gridX - from[i].gridX) * t, gridY: from[i].gridY + (token.gridY - from[i].gridY) * t })), passed: segment, done: false };
}

// gravewright/maps/frontend/features/tokens/model/token-pathfinding.js
function suggestTokenRoute(route, walls, cell, width, height, limits = {}) {
  if (route.length < 2 || !(cell > 0) || !Number.isFinite(width + height + cell))
    return;
  const first = route[0], last = route.at(-1);
  if (!first.length || first.length !== last.length)
    return;
  const anchor = first[0], dx = last[0].gridX - anchor.gridX, dy = last[0].gridY - anchor.gridY;
  if (first.some((t, i) => t.id !== last[i].id || Math.abs(last[i].gridX - t.gridX - dx) > 1e-7 || Math.abs(last[i].gridY - t.gridY - dy) > 1e-7))
    return;
  const rows = (x, y) => first.map((t) => ({ ...t, gridX: t.gridX + x, gridY: t.gridY + y }));
  const inside = (x, y) => first.every((t) => t.gridX + x >= 0 && t.gridY + y >= 0 && t.gridX + x + t.cells <= width / cell && t.gridY + y + (t.heightCells ?? t.cells) <= height / cell);
  if (!inside(0, 0) || !inside(dx, dy))
    return;
  const clear = (x, y, nx, ny) => first.every((t) => !movementBlocked({ ...t, gridX: t.gridX + x, gridY: t.gridY + y }, { gridX: t.gridX + nx, gridY: t.gridY + ny }, walls, cell));
  const chosenBlocked = route.slice(1).some((step, i) => step.some((token, j) => movementBlocked(route[i][j], token, walls, cell)));
  const shorter = (candidate) => candidate.length <= 512 && (chosenBlocked || routeMeasurements(candidate, 1).total + 1e-6 < routeMeasurements(route, 1).total) ? candidate : void 0;
  if (clear(0, 0, dx, dy))
    return shorter([first, last]);
  const heap = [];
  const push = (node) => {
    let i = heap.length;
    heap.push(node);
    while (i) {
      const p = i - 1 >> 1;
      if (heap[p].f <= node.f)
        break;
      heap[i] = heap[p];
      i = p;
    }
    heap[i] = node;
  };
  const pop = () => {
    const result = heap[0], tail = heap.pop();
    if (heap.length) {
      let i = 0;
      while (i * 2 + 1 < heap.length) {
        let child = i * 2 + 1;
        if (child + 1 < heap.length && heap[child + 1].f < heap[child].f)
          child++;
        if (heap[child].f >= tail.f)
          break;
        heap[i] = heap[child];
        i = child;
      }
      heap[i] = tail;
    }
    return result;
  };
  const key = (x, y) => `${x},${y}`;
  const best = /* @__PURE__ */ new Map([[key(0, 0), 0]]);
  const deadline = performance.now() + (limits.milliseconds ?? 100);
  const budget = limits.nodes ?? 12e3;
  push({ x: 0, y: 0, g: 0, f: Math.hypot(dx, dy) });
  let explored = 0;
  while (heap.length && explored++ < budget) {
    if (performance.now() > deadline)
      return;
    const current = pop();
    if (current.g !== best.get(key(current.x, current.y)))
      continue;
    if (current.x === dx && current.y === dy) {
      const points = [];
      for (let n = current; n; n = n.parent)
        points.push(n);
      points.reverse();
      const compact = [points[0]];
      for (let i = 1; i < points.length - 1; i++) {
        const a = compact.at(-1), b = points[i], c = points[i + 1];
        if (Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) > 1e-8)
          compact.push(b);
      }
      compact.push(current);
      return shorter(compact.map((n) => rows(n.x, n.y)));
    }
    const neighbors = [];
    for (let x = -1; x <= 1; x++)
      for (let y = -1; y <= 1; y++)
        if (x || y)
          neighbors.push([current.x + x, current.y + y]);
    if (Math.hypot(current.x - dx, current.y - dy) <= Math.SQRT2)
      neighbors.push([dx, dy]);
    for (const [x, y] of neighbors) {
      const g = current.g + Math.hypot(x - current.x, y - current.y), id = key(x, y);
      if (g >= (best.get(id) ?? Infinity) || !inside(x, y) || !clear(current.x, current.y, x, y))
        continue;
      best.set(id, g);
      push({ x, y, g, f: g + Math.hypot(dx - x, dy - y), parent: current });
    }
  }
}

// gravewright/maps/frontend/features/tokens/model/token-motion.js
var TOKEN_SETTLE_MS = 120;
function interpolateTokens(from, to, progress) {
  const starts = new Map(from.map((token) => [token.id, token]));
  const t = 1 - Math.pow(1 - Math.max(0, Math.min(1, progress)), 3);
  return to.map((token) => {
    const start = starts.get(token.id);
    if (!start || t === 1)
      return token;
    return { ...token, gridX: start.gridX + (token.gridX - start.gridX) * t, gridY: start.gridY + (token.gridY - start.gridY) * t };
  });
}

// gravewright/maps/frontend/features/tokens/ui/controller.js
import { renderingPreferences } from "/static/gravewright_maps/render-profile.js";

// gravewright/maps/frontend/widgets/game-board/model/board-input.js
var LONG_PRESS_MS = 700;

// gravewright/maps/frontend/features/tokens/ui/controller.js
function tokenController(element, options) {
  const props = { ...options.props }, emit = options.emit, nextTick = () => Promise.resolve();
  const box = (initial) => {
    let value = initial;
    return {
      get value() {
        return value;
      },
      set value(next) {
        value = next;
        options.repaint();
      }
    };
  };
  const derive = (read) => ({
    get value() {
      return read();
    }
  });
  const root = box(), selected = box([]), busy = box(false), error = box(""), context = box(), marquee = box(), sheet = box(), editor = box(), confirm = box(false), clipboard = box([]);
  const displayed = box(props.tokens), destinations = box([]);
  let animation = 0, heldArrow = "", queuedArrow;
  function stopAnimation() {
    cancelAnimationFrame(animation);
    animation = 0;
  }
  function present(rows) {
    displayed.value = rows;
    emit("preview", rows);
  }
  function merged(rows) {
    const changed = new Map(rows.map((t) => [t.id, t]));
    return remoteRows().map((t) => changed.get(t.id) ?? t);
  }
  function animate(rows, immediate = false) {
    stopAnimation();
    const previous = new Map(displayed.value.map((t) => [t.id, t]));
    const from = rows.map((t) => {
      const old = previous.get(t.id);
      return old && old.hidden === t.hidden && !movementBlocked(old, t, props.walls, props.cell) ? old : t;
    });
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches || renderingPreferences.current().capabilities.motion === "none";
    if (immediate || reduced || !rows.some((t, i) => t.gridX !== from[i].gridX || t.gridY !== from[i].gridY)) {
      present(rows);
      return;
    }
    const start = performance.now();
    const tick = (now) => {
      if (closed)
        return;
      const progress = Math.min(1, (now - start) / TOKEN_SETTLE_MS);
      present(interpolateTokens(from, rows, progress));
      if (progress < 1)
        animation = requestAnimationFrame(tick);
      else
        animation = 0;
    };
    present(interpolateTokens(from, rows, 0));
    animation = requestAnimationFrame(tick);
  }
  const remote = /* @__PURE__ */ new Map();
  let stream = "", livePositions = [], lastSent = 0;
  const livePaths = /* @__PURE__ */ new Map();
  let heartbeat;
  function remoteRows(rows = props.tokens) {
    return rows.map((t) => {
      const preview = remote.get(t.id);
      return preview && preview.version === t.version ? { ...t, gridX: preview.gridX, gridY: preview.gridY } : t;
    });
  }
  function transmit() {
    if (!stream || !livePositions.length || closed)
      return;
    lastSent = performance.now();
    emit("motion", {
      stream,
      phase: "update",
      positions: livePositions.map((p) => ({
        ...p,
        path: livePaths.get(p.id) ?? []
      }))
    });
    for (const p of livePositions)
      livePaths.set(p.id, [[p.gridX, p.gridY]]);
  }
  function publish(rows) {
    if (!stream)
      return;
    livePositions = rows.map(({ id, gridX, gridY, version }) => ({
      id,
      gridX: Number(gridX.toFixed(4)),
      gridY: Number(gridY.toFixed(4)),
      version
    }));
    for (const p of livePositions) {
      const path = livePaths.get(p.id) ?? [];
      path.push([p.gridX, p.gridY]);
      livePaths.set(p.id, path.slice(-16));
    }
    if (performance.now() - lastSent >= 100)
      transmit();
  }
  function finishBroadcast(phase) {
    if (heartbeat)
      clearInterval(heartbeat);
    heartbeat = void 0;
    if (stream)
      emit("motion", { stream, phase });
    stream = "";
    livePositions = [];
    livePaths.clear();
  }
  function receiveMotion(value) {
    const packet = value;
    if (closed || !packet || packet.scene_id !== scope.map || typeof packet.stream !== "string" || typeof packet.connection !== "string")
      return;
    const key2 = packet.connection + ":" + packet.stream;
    if (packet.phase === "update" && Array.isArray(packet.positions)) {
      for (const p of packet.positions) {
        const token = props.tokens.find((t) => t.id === p.id);
        if (token && p.version === token.version && Number.isFinite(p.gridX) && Number.isFinite(p.gridY))
          remote.set(p.id, {
            ...p,
            stream: key2,
            expires: performance.now() + 1500
          });
      }
    } else if (packet.phase === "cancel") {
      for (const [id, p] of remote)
        if (p.stream === key2)
          remote.delete(id);
    } else if (packet.phase === "end") {
      for (const p of remote.values())
        if (p.stream === key2)
          p.expires = performance.now() + 700;
      emit("refresh");
    } else
      return;
    if (drag)
      present(merged(drag.current));
    else if (!busy.value)
      animate(remoteRows());
  }
  const expireRemote = setInterval(() => {
    let changed = false;
    for (const [id, p] of remote)
      if (p.expires <= performance.now()) {
        remote.delete(id);
        changed = true;
      }
    if (changed && !drag && !busy.value)
      animate(remoteRows());
  }, 250);
  const route = box([]), walking = box(false);
  let routeFrame = 0;
  const routeMeasurement = derive(() => routeMeasurements(route.value, props.measureValue));
  function formatDistance(value) {
    return `${formatNumber(value)} ${props.measureUnit || text("units")}`;
  }
  const routeLine = derive(() => route.value.map((step) => {
    const t = step[0];
    return `${(t.gridX + t.cells / 2) * props.cell},${(t.gridY + (t.heightCells ?? t.cells) / 2) * props.cell}`;
  }).join(" "));
  let suggestionKey, suggestionValue, suggestionInputs = [];
  const suggested = derive(() => {
    if (walking.value) return void 0;
    const inputs = [route.value, props.walls, props.cell, props.width, props.height];
    if (inputs.every((value, i) => value === suggestionInputs[i])) return suggestionValue;
    suggestionInputs = inputs;
    const key2 = JSON.stringify(inputs);
    if (key2 !== suggestionKey) {
      suggestionKey = key2;
      suggestionValue = suggestTokenRoute(route.value, props.walls, props.cell, props.width, props.height);
    }
    return suggestionValue;
  });
  const suggestedMeasurement = derive(() => suggested.value ? routeMeasurements(suggested.value, props.measureValue) : void 0);
  const suggestedLine = derive(() => suggested.value?.map((step) => {
    const t = step[0];
    return `${(t.gridX + t.cells / 2) * props.cell},${(t.gridY + (t.heightCells ?? t.cells) / 2) * props.cell}`;
  }).join(" "));
  const routeEnd = derive(() => route.value.at(-1)?.[0]);
  function useSuggestedRoute() {
    const candidate = suggested.value;
    if (walking.value || busy.value || !candidate)
      return;
    route.value = candidate;
    error.value = "";
  }
  function startBroadcast() {
    finishBroadcast("cancel");
    stream = crypto.randomUUID();
    lastSent = 0;
    heartbeat = setInterval(() => {
      if (performance.now() - lastSent >= 100)
        transmit();
    }, 250);
  }
  function addWaypoint(p, free) {
    if (busy.value || drag)
      return;
    const first = route.value[0] ?? selection.value.filter((t) => t.canControl && !t.locked).map((t) => ({ ...t }));
    if (!first.length) {
      error.value = text("Select a token you control.");
      return;
    }
    const previous = route.value.at(-1) ?? first;
    if (route.value.length >= MAX_ROUTE_POINTS + 1) {
      error.value = text("The route accepts up to {0} points.", MAX_ROUTE_POINTS);
      return;
    }
    const anchor = previous[0];
    const delta = {
      x: p.x - (anchor.gridX + anchor.cells / 2) * props.cell,
      y: p.y - (anchor.gridY + (anchor.heightCells ?? anchor.cells) / 2) * props.cell
    };
    const next = previous.map((t) => ({
      ...t,
      ...position(t, delta, props.cell, props.width, props.height, props.grid && !free)
    }));
    if (next.every((t, i) => t.gridX === previous[i].gridX && t.gridY === previous[i].gridY))
      return;
    stopAnimation();
    context.value = void 0;
    error.value = "";
    route.value = [...route.value.length ? route.value : [first], next];
  }
  function walkRoute() {
    if (walking.value || busy.value || route.value.length < 2)
      return;
    const steps = route.value, first = steps[0], lengths = routeLengths(steps);
    if (first.some((t) => !props.tokens.some((v) => v.id === t.id && v.version === t.version && v.canControl && !v.locked))) {
      cancel();
      error.value = "A rota foi cancelada porque um token mudou.";
      return;
    }
    if (!props.gm && steps.slice(1).some((step, i) => step.some((t, j) => movementBlocked(steps[i][j], t, props.walls, props.cell)))) {
      cancel();
      error.value = "A rota foi bloqueada por uma parede.";
      return;
    }
    stopAnimation();
    walking.value = true;
    busy.value = true;
    startBroadcast();
    let previousFrame, distance = 0, passed = 0;
    const tick = (now) => {
      if (closed || !walking.value)
        return;
      if (previousFrame !== void 0)
        distance += Math.min(100, Math.max(0, now - previousFrame)) / 1e3 * ROUTE_CELLS_PER_SECOND;
      previousFrame = now;
      const sample = routePosition(steps, lengths, distance);
      while (passed < sample.passed) {
        passed++;
        publish(steps[passed]);
      }
      present(merged(sample.tokens));
      publish(sample.tokens);
      if (!sample.done) {
        routeFrame = requestAnimationFrame(tick);
        return;
      }
      routeFrame = 0;
      walking.value = false;
      route.value = [];
      const paths = new Map(first.map((t, i) => [
        t.id,
        steps.map((step) => ({
          gridX: step[i].gridX,
          gridY: step[i].gridY
        }))
      ]));
      transmit();
      saveMoves(first, steps.at(-1), paths, true);
    };
    publish(first);
    routeFrame = requestAnimationFrame(tick);
  }
  const selection = derive(() => props.tokens.filter((t) => selected.value.includes(t.id)));
  const interactive = derive(() => props.tool === "select");
  let closed = false, queue = Promise.resolve(), drag;
  const abort = new AbortController(), reader = { list: () => options.read() }, writer = {
    command: (_a, _b, action, data) => options.command(action, data),
    move: (_a, id, data) => options.command("move", { id, ...data }).then((r) => r.tokens.find((t) => t.id === id))
  }, scope = {
    container: props.containerId,
    block: props.blockId,
    map: props.mapId
  };
  const undo = box([]), redo = box([]);
  let pressTimer;
  function clearPress() {
    if (pressTimer)
      clearTimeout(pressTimer);
    pressTimer = void 0;
  }
  let lastPoint = { x: 0, y: 0 };
  function point(e) {
    const r = root.value.getBoundingClientRect();
    return {
      x: (e.clientX - r.left - props.viewport.x) / props.viewport.scale,
      y: (e.clientY - r.top - props.viewport.y) / props.viewport.scale
    };
  }
  function stop(e) {
    e.preventDefault();
    e.stopPropagation();
  }
  async function run(operation) {
    queue = queue.then(async () => {
      if (closed)
        return;
      busy.value = true;
      error.value = "";
      try {
        await operation();
      } catch (e) {
        if (!closed)
          error.value = text("Could not complete the action. Check permissions or reload the scene state.");
      } finally {
        if (!closed) {
          try {
            const rows = await reader.list(scope.container, scope.map);
            if (!closed) {
              emit("changed", rows);
              animate(remoteRows(rows));
              emit("refresh");
            }
          } catch {
            if (!closed)
              animate(remoteRows());
          }
          if (!closed) {
            finishBroadcast(error.value ? "cancel" : "end");
            await nextTick();
            busy.value = false;
            if (queuedArrow && heldArrow === queuedArrow.key) {
              const event = queuedArrow;
              queuedArrow = void 0;
              keys(event);
            }
          }
        }
      }
    });
    return queue;
  }
  function command(action, data = {}, ids = selected.value) {
    const chosen = [...ids];
    context.value = void 0;
    void run(async () => {
      const result = await writer.command(scope.container, scope.map, action, {
        tokenIds: chosen,
        ...data
      });
      if (closed)
        return;
      emit("changed", result.tokens);
      editor.value = void 0;
      confirm.value = false;
      if (result.createdIds.length)
        selected.value = result.createdIds;
    });
  }
  function down(e) {
    if (!interactive.value)
      return;
    const p = point(e), token = hitToken(p, displayed.value, props.cell);
    if (e.button === 0 && e.ctrlKey && selected.value.length) {
      stop(e);
      addWaypoint(p, e.altKey);
      return;
    }
    if (route.value.length) {
      if (e.button === 0)
        stop(e);
      return;
    }
    if (e.button === 2) {
      if (token && (props.gm || token.canControl))
        stop(e);
      return;
    }
    if (e.button !== 0)
      return;
    if (token) {
      stop(e);
      if (busy.value)
        return;
      if (e.shiftKey) {
        selected.value = selected.value.includes(token.id) ? selected.value.filter((id) => id !== token.id) : [...selected.value, token.id];
        return;
      }
      if (!selected.value.includes(token.id))
        selected.value = [token.id];
      if (!token.canControl || token.locked)
        return;
    } else {
      stop(e);
      if (busy.value)
        return;
      marquee.value = { from: p, to: p };
    }
    stopAnimation();
    const original = token ? selection.value.filter((t) => t.canControl && !t.locked).map((t) => ({ ...t })) : [];
    const visualOrigin = original.map((t) => {
      const visual = displayed.value.find((v) => v.id === t.id);
      return {
        ...t,
        gridX: visual?.gridX ?? t.gridX,
        gridY: visual?.gridY ?? t.gridY
      };
    });
    drag = {
      pointer: e.pointerId,
      from: p,
      original,
      visualOrigin,
      current: visualOrigin,
      paths: new Map(original.map((t, i) => [
        t.id,
        [
          { gridX: t.gridX, gridY: t.gridY },
          { gridX: visualOrigin[i].gridX, gridY: visualOrigin[i].gridY }
        ]
      ])),
      moved: false,
      additive: e.shiftKey,
      selection: [...selected.value]
    };
    if (original.length)
      startBroadcast();
    context.value = void 0;
    root.value?.setPointerCapture(e.pointerId);
    clearPress();
    pingShift = e.shiftKey;
    if (!token)
      pressTimer = setTimeout(() => {
        if (!closed && drag)
          emit("ping", p, pingShift);
      }, LONG_PRESS_MS);
  }
  function move(e) {
    lastPoint = point(e);
    pingShift = e.shiftKey;
    if (drag && Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) * props.viewport.scale > 10)
      clearPress();
    if (!interactive.value)
      return;
    if (!drag) {
      emit("hover", hitToken(lastPoint, props.tokens, props.cell)?.id);
      return;
    }
    if (drag.pointer !== e.pointerId)
      return;
    stop(e);
    if (!drag.original.length) {
      drag.moved = Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) * props.viewport.scale >= 3;
      marquee.value = { from: drag.from, to: lastPoint };
      selected.value = [
        .../* @__PURE__ */ new Set([
          ...drag.additive ? drag.selection : [],
          ...props.tokens.filter((t) => inMarquee(t, drag.from, lastPoint, props.cell) && (props.gm || t.canControl)).map((t) => t.id)
        ])
      ];
      return;
    }
    if (!drag.moved && Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) * props.viewport.scale < 3)
      return;
    const delta = {
      x: lastPoint.x - drag.from.x,
      y: lastPoint.y - drag.from.y
    }, next = drag.visualOrigin.map((t) => ({
      ...t,
      ...position(t, delta, props.cell, props.width, props.height, false)
    }));
    if (!props.gm && next.some((t, i) => movementBlocked(drag.current[i], t, props.walls, props.cell))) {
      error.value = text("Movement blocked by a wall.");
      return;
    }
    if (next.some((t) => (drag.paths.get(t.id)?.length ?? 0) >= 511)) {
      error.value = text("Release the token to finish this movement segment.");
      return;
    }
    error.value = "";
    drag.moved = true;
    drag.current = next;
    for (const t of next) {
      const path = drag.paths.get(t.id);
      const last = path[path.length - 1];
      if (last.gridX !== t.gridX || last.gridY !== t.gridY)
        path.push({ gridX: t.gridX, gridY: t.gridY });
    }
    destinations.value = props.grid && !e.altKey ? next.map((t) => ({
      ...t,
      ...position(t, { x: 0, y: 0 }, props.cell, props.width, props.height, true)
    })).filter((t, i) => props.gm || !movementBlocked(next[i], t, props.walls, props.cell)) : [];
    present(merged(next));
    publish(next);
  }
  function up(e) {
    clearPress();
    if (!drag || drag.pointer !== e.pointerId)
      return;
    stop(e);
    const d = drag;
    drag = void 0;
    destinations.value = [];
    marquee.value = void 0;
    if (root.value?.hasPointerCapture(e.pointerId))
      root.value.releasePointerCapture(e.pointerId);
    if (d.original.length && d.moved) {
      const target = d.current.map((t) => {
        const snapped = {
          ...t,
          ...position(t, { x: 0, y: 0 }, props.cell, props.width, props.height, props.grid && !e.altKey)
        };
        return !props.gm && movementBlocked(t, snapped, props.walls, props.cell) ? t : snapped;
      });
      for (const t of target) {
        const path = d.paths.get(t.id);
        const last = path.at(-1);
        if (last.gridX !== t.gridX || last.gridY !== t.gridY)
          path.push({ gridX: t.gridX, gridY: t.gridY });
      }
      publish(target);
      transmit();
      saveMoves(d.original, target, d.paths, true);
    } else {
      finishBroadcast("cancel");
      if (!d.original.length && !d.additive && !d.moved)
        selected.value = [];
    }
  }
  function cancel() {
    clearPress();
    stopAnimation();
    finishBroadcast("cancel");
    cancelAnimationFrame(routeFrame);
    routeFrame = 0;
    route.value = [];
    if (walking.value) {
      walking.value = false;
      busy.value = false;
    }
    if (drag && root.value?.hasPointerCapture(drag.pointer))
      root.value.releasePointerCapture(drag.pointer);
    drag = void 0;
    marquee.value = void 0;
    destinations.value = [];
    displayed.value = remoteRows();
    if (!closed)
      present(displayed.value);
    else
      emit("preview", void 0);
  }
  function saveMoves(from, to, paths, record, after) {
    animate(merged(to));
    void run(async () => {
      const accepted = [], starts = [];
      let failed = 0;
      for (const t of to) {
        const old = from.find((v) => v.id === t.id);
        if (old.gridX === t.gridX && old.gridY === t.gridY && !(paths.get(t.id) ?? []).some((p) => p.gridX !== old.gridX || p.gridY !== old.gridY))
          continue;
        try {
          const result = await writer.move(scope.container, t.id, {
            gridX: t.gridX,
            gridY: t.gridY,
            expectedVersion: old.version,
            path: paths.get(t.id)
          });
          accepted.push(result);
          starts.push(old);
        } catch {
          failed++;
        }
      }
      if (closed)
        return;
      if (failed)
        error.value = text("{0} movement(s) refused: wall, locked token, no control, or a change in another window.", failed);
      if (!failed)
        after?.();
      if (record && accepted.length) {
        undo.value = [
          ...undo.value.slice(-49),
          { from: starts, to: accepted, paths }
        ];
        redo.value = [];
      }
    });
  }
  function history(back) {
    if (busy.value)
      return;
    const source = back ? undo : redo, destination = back ? redo : undo;
    const item = source.value.at(-1);
    if (!item)
      return;
    const target = back ? item.from : item.to, from = target.map((t) => props.tokens.find((v) => v.id === t.id)).filter((t) => !!t);
    const path = new Map([...item.paths].map(([id, points]) => [
      id,
      back ? [...points].reverse() : points
    ]));
    if (from.length !== target.length) {
      error.value = text("A token in this movement is no longer in the scene.");
      return;
    }
    saveMoves(from, target, path, false, () => {
      source.value.pop();
      destination.value.push(item);
    });
  }
  function menu(e) {
    if (!interactive.value)
      return;
    const token = hitToken(point(e), displayed.value, props.cell);
    if (!token || !props.gm && !token.canControl)
      return;
    stop(e);
    if (!selected.value.includes(token.id))
      selected.value = [token.id];
    context.value = { x: e.clientX, y: e.clientY, token };
  }
  function double(e) {
    if (!interactive.value)
      return;
    const token = hitToken(point(e), displayed.value, props.cell);
    if (token?.canOpenSheet) {
      stop(e);
      cancel();
      sheet.value = { ...token };
    }
  }
  function edit(mode) {
    context.value = void 0;
    editor.value = { mode, tokens: selection.value.map((t) => ({ ...t })) };
  }
  function copy() {
    clipboard.value = selection.value.map((t) => t.id);
    context.value = void 0;
  }
  function paste() {
    if (props.gm && clipboard.value.length)
      command("duplicate", {}, clipboard.value);
  }
  let pingShift = false;
  function keys(e) {
    pingShift = e.shiftKey;
    if (props.externalMixed || !interactive.value || e.defaultPrevented || e.target instanceof Element && e.target.closest("input,textarea,select,[contenteditable=true],[role=dialog],.directory-context-menu"))
      return;
    const mod = e.ctrlKey || e.metaKey;
    if (e.key === "Escape") {
      cancel();
      context.value = void 0;
      selected.value = [];
      return;
    }
    if (e.key.startsWith("Arrow"))
      heldArrow = e.key;
    if (busy.value || route.value.length) {
      if (!walking.value && !route.value.length && e.key.startsWith("Arrow") && selected.value.length) {
        stop(e);
        queuedArrow = new KeyboardEvent("keydown", { key: e.key });
      }
      return;
    }
    if (mod && e.key.toLowerCase() === "a") {
      stop(e);
      selected.value = props.tokens.filter((t) => props.gm || t.canControl).map((t) => t.id);
      return;
    }
    if (mod && e.key.toLowerCase() === "c") {
      stop(e);
      copy();
      return;
    }
    if (mod && e.key.toLowerCase() === "v") {
      stop(e);
      paste();
      return;
    }
    if (mod && ["z", "y"].includes(e.key.toLowerCase())) {
      stop(e);
      history(e.key.toLowerCase() === "z" && !e.shiftKey);
      return;
    }
    if (["Delete", "Backspace"].includes(e.key) && props.gm && selection.value.length) {
      stop(e);
      confirm.value = true;
      return;
    }
    const direction = {
      ArrowUp: { x: 0, y: -props.cell },
      ArrowDown: { x: 0, y: props.cell },
      ArrowLeft: { x: -props.cell, y: 0 },
      ArrowRight: { x: props.cell, y: 0 }
    }[e.key];
    if (!direction || !selection.value.length || drag)
      return;
    stop(e);
    const from = selection.value.filter((t) => t.canControl && !t.locked), to = from.map((t) => ({
      ...t,
      ...position(t, direction, props.cell, props.width, props.height, false)
    }));
    if (!props.gm && to.some((t, i) => movementBlocked(from[i], t, props.walls, props.cell))) {
      error.value = text("Movement blocked by a wall.");
      return;
    }
    saveMoves(from, to, new Map(to.map((t, i) => [
      t.id,
      [
        { gridX: from[i].gridX, gridY: from[i].gridY },
        { gridX: t.gridX, gridY: t.gridY }
      ]
    ])), true);
  }
  function keyup(e) {
    pingShift = e.shiftKey;
    if (e.key === "Control" && !e.ctrlKey && route.value.length) {
      walkRoute();
      return;
    }
    if (e.key === heldArrow) {
      heldArrow = "";
      queuedArrow = void 0;
    }
  }
  function blur() {
    heldArrow = "";
    queuedArrow = void 0;
    cancel();
  }
  root.value = element;
  const events = {
    pointerdown: down,
    pointermove: move,
    pointerup: up,
    pointercancel: cancel,
    contextmenu: menu,
    dblclick: double
  };
  const listeners2 = Object.entries(events).map(([name, fn]) => {
    const handler = (e) => {
      fn(e);
      options.repaint();
    };
    element.addEventListener(name, handler);
    return [name, handler];
  });
  const key = (e) => {
    keys(e);
    options.repaint();
  };
  window.addEventListener("keydown", key);
  window.addEventListener("keyup", keyup);
  window.addEventListener("blur", blur);
  return {
    get view() {
      return {
        displayed: displayed.value,
        destinations: destinations.value,
        selected: selected.value,
        selection: selection.value,
        context: context.value,
        editor: editor.value,
        sheet: sheet.value,
        confirm: confirm.value,
        clipboard: clipboard.value,
        busy: busy.value,
        error: error.value,
        marquee: marquee.value,
        route: route.value,
        routeLine: routeLine.value,
        routeMeasurement: routeMeasurement.value,
        suggestedLine: suggestedLine.value,
        suggestedMeasurement: suggestedMeasurement.value,
        routeEnd: routeEnd.value,
        walking: walking.value,
        routeBlocked: route.value.slice(1).some((step, i) => step.some((token, j) => movementBlocked(route.value[i][j], token, props.walls, props.cell))),
        undo: undo.value,
        redo: redo.value,
        interactive: interactive.value
      };
    },
    receiveMotion,
    call(name, ...args) {
      const methods = {
        command,
        edit,
        copy,
        paste,
        select: (ids) => {
          selected.value = ids;
        },
        history,
        cancel,
        useSuggestedRoute,
        closeContext: () => context.value = void 0,
        closeEditor: () => editor.value = void 0,
        closeSheet: () => sheet.value = void 0,
        closeConfirm: () => confirm.value = false,
        remove: () => {
          context.value = void 0;
          confirm.value = true;
        },
        openSheet: (t) => {
          sheet.value = t;
          context.value = void 0;
        }
      };
      const result = methods[name](...args);
      options.repaint();
      return result;
    },
    update(next) {
      const oldTool = props.tool;
      Object.assign(props, next);
      if (oldTool !== props.tool)
        cancel();
      if (next.tokens) {
        const rows = props.tokens;
        if (sheet.value) {
          const fresh = rows.find((t) => t.id === sheet.value.id);
          if (!fresh?.canOpenSheet || fresh.linkMode !== sheet.value.linkMode || sheet.value.canControl && !fresh.canControl)
            sheet.value = void 0;
        }
        selected.value = selected.value.filter((id) => rows.some((t) => t.id === id));
        if (drag?.original.some((t) => !rows.some((r) => r.id === t.id && r.version === t.version && r.canControl && !r.locked)))
          cancel();
        if (route.value.length && route.value[0].some((t) => !rows.some((r) => r.id === t.id && r.version === t.version && r.canControl && !r.locked)))
          cancel();
        for (const [id, p] of remote)
          if (!rows.some((t) => t.id === id && t.version === p.version))
            remote.delete(id);
        if (!drag && !busy.value)
          animate(remoteRows());
      }
      if (next.walls && walking.value && route.value.length && !props.gm && route.value.slice(1).some((step, i) => step.some((t, j) => movementBlocked(route.value[i][j], t, props.walls, props.cell))))
        cancel();
      options.repaint();
    },
    destroy() {
      closed = true;
      abort.abort();
      clearInterval(expireRemote);
      remote.clear();
      cancel();
      for (const [name, fn] of listeners2)
        element.removeEventListener(name, fn);
      window.removeEventListener("keydown", key);
      window.removeEventListener("keyup", keyup);
      window.removeEventListener("blur", blur);
    }
  };
}
export {
  tokenController
};
