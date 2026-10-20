// gravewright/maps/frontend/widgets/game-board/model/scene-surface-art.js
import { surfaceMaterial } from "../../../features/images/model/surface-material.js";
import { surfaceGroupsLayout, surfaceGroupCanvas } from "../../../features/images/model/surface-group.js";
function geometry(row) {
  return {
    id: row.id,
    natural_width: row.natural_width,
    natural_height: row.natural_height,
    x: row.x,
    y: row.y,
    scale: row.scale,
    rotation: row.rotation,
    layer: row.layer,
    z_index: row.z_index,
    surfacePlane: row.surfacePlane,
    maskId: row.surface?.maskId
  };
}
function surfaceArtRows(images, width, height) {
  const groups = /* @__PURE__ */ new Map(), result = [];
  for (const row of images) {
    if (row.empty === true || !row.src) continue;
    if (row.surfacePlane?.group) {
      const id = row.surfacePlane.group;
      if (!groups.has(id)) groups.set(id, []);
      groups.get(id).push({ ...geometry(row), src: row.src, surface: row.surface });
    } else if (row.surface) {
      result.push({
        id: `surface:${JSON.stringify(geometry(row))}`,
        placementId: row.id,
        src: JSON.stringify({ rows: [{ id: row.id, src: row.src, surface: row.surface }] })
      });
    }
  }
  for (const { rows, bounds } of surfaceGroupsLayout([...groups.values()], width, height)) {
    result.push({
      id: `group:${JSON.stringify([rows.map(geometry), bounds])}`,
      bounds,
      order: Math.min(...rows.map((row) => row.z_index)),
      src: JSON.stringify({ rows, bounds })
    });
  }
  return result;
}
async function loadSurfaceArt(source, signal) {
  const { rows, bounds } = JSON.parse(source);
  const loads = /* @__PURE__ */ new Map(), decoded = /* @__PURE__ */ new Set();
  let finished = false;
  function bitmap(url) {
    if (!loads.has(url)) loads.set(url, (async () => {
      const response = await fetch(url, { signal, credentials: "same-origin" });
      if (!response.ok) throw new Error(`Unable to load surface artwork (${response.status}).`);
      const image = await createImageBitmap(await response.blob());
      if (finished || signal.aborted) {
        image.close();
        throw new Error("Surface artwork load cancelled.");
      }
      decoded.add(image);
      return image;
    })());
    return loads.get(url);
  }
  try {
    const results = await Promise.allSettled(rows.map(async (row) => {
      if (!row.surface?.materialId) return [row.id, await bitmap(row.src)];
      const [material, mask] = await Promise.all([
        bitmap(`/game/map-assets/${row.surface.materialId}`),
        bitmap(`/game/map-assets/${row.surface.maskId}`)
      ]);
      return [row.id, surfaceMaterial(row.surface, material, mask)];
    }));
    const failure = results.find((result) => result.status === "rejected");
    if (failure) throw failure.reason;
    if (signal.aborted) throw new Error("Surface artwork load cancelled.");
    const images = new Map(results.map((result) => result.value));
    let canvas;
    if (bounds) canvas = surfaceGroupCanvas(rows, images, bounds);
    else {
      const image = images.get(rows[0].id);
      canvas = document.createElement("canvas");
      canvas.width = image.width;
      canvas.height = image.height;
      canvas.getContext("2d").drawImage(image, 0, 0);
    }
    return { canvas, bytes: canvas.width * canvas.height * 4 };
  } finally {
    finished = true;
    await Promise.allSettled(loads.values());
    for (const image of decoded) image.close();
  }
}
export {
  loadSurfaceArt,
  surfaceArtRows
};
