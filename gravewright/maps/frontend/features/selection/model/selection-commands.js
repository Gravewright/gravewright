import { transformedPoint } from "./objects.js";
async function applySelection(api, tokens, container, block, map, cell, state, objects, action, center, dx = 0, dy = 0, angle = 0, origin = { x: 0, y: 0 }) {
  const failed = [], done = [];
  const drawings = objects.filter((o) => o.kind === "drawing");
  const point = (p) => transformedPoint(p, center, dx, dy, angle);
  const command = (area, action2, data) => api.command(container, block, area, action2, data);
  for (const o of objects.filter((o2) => !["drawing", "measure"].includes(o2.kind))) {
    const d = o.data, p = point(o);
    try {
      if (["hide", "show"].includes(action)) {
        if (o.kind !== "image") continue;
        await command("images", "update", { placement_id: o.id, layer: action === "hide" ? "gm" : "game", expected_version: d.version });
      } else if (action === "flip") {
        if (o.kind !== "card") continue;
        await command("cards", "update", { placement_id: o.id, expected_version:d.version, face_state: d.card?.face_state === "face_up" ? "face_down" : "face_up" });
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
      else if (o.kind === "card") await command("cards", action === "delete" ? "delete" : "update", { placement_id: o.id, expected_version:d.version, ...action === "delete" ? {} : { x: p.x, y: p.y, rotation: d.rotation + angle } });
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
export {
  applySelection,
  transformMeasures
};
