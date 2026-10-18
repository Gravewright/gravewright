/** Resolve only the door's public, active appearance outside the map raster. */
export function doorArt(wall) {
    if (wall.kind !== 'door') return;
    const appearance = wall.blueprintAppearance;
    let assetId;
    if (appearance !== undefined) {
        if (!appearance || appearance.visible !== true) return;
        assetId = appearance.assetId;
    } else {
        if (wall.door_state === 'open') return;
        assetId = wall.asset_id;
    }
    if (typeof assetId !== 'string'
        || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(assetId)) return;
    const dx = wall.x2 - wall.x1, dy = wall.y2 - wall.y1;
    const width = Math.hypot(dx, dy), height = wall.thickness ?? 14;
    if (![wall.x1, wall.y1, width, height].every(Number.isFinite) || width <= 0 || height <= 0 || height > 512) return;
    return { src: `/game/map-assets/${assetId}`, x: wall.x1, y: wall.y1,
        width, height, angle: Math.atan2(dy, dx) * 180 / Math.PI };
}
