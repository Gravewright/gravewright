import { classifyTile } from "./tile-scheduler.js";
/**
 * Everything the board decides before an engine is involved: how a scene is framed, where a point
 * on the surface lands on the map, and which tiles the viewport is currently covering.
 */
/** Fits the whole map on screen and centres it, which is where a scene opens before any panning. */
export function fitToSurface(surface, map) {
    const scale = Math.min(surface.width / map.width, surface.height / map.height);
    return { x: (surface.width - map.width * scale) / 2, y: (surface.height - map.height * scale) / 2, scale };
}
/** Turns a point on the surface into the map coordinate underneath it. */
export function worldPoint(point, view) {
    return { x: (point.x - view.x) / view.scale, y: (point.y - view.y) / view.scale };
}
/** Picks the coarsest level that still out-resolves the screen, so zooming out stops fetching detail. */
export function levelFor(manifest, scale) {
    const lod = Math.max(0, Math.min(manifest.maxLod, Math.floor(Math.log2(1 / Math.max(scale, 1e-5)))));
    return manifest.levels.find((level) => level.lod === lod) ?? manifest.levels[0];
}
function viewportLevel(manifest,view,surface){
    const preferred=levelFor(manifest,view.scale),limits=manifest.viewportLimits;
    if(!limits)return preferred;
    for(const level of manifest.levels.filter(l=>l.lod>=preferred.lod).sort((a,b)=>a.lod-b.lod)){
        const size=manifest.tileSize*(manifest.width/level.width);
        const left=Math.max(0,Math.min(level.columns-1,Math.floor(-view.x/view.scale/size)));
        const top=Math.max(0,Math.min(level.rows-1,Math.floor(-view.y/view.scale/size)));
        const right=Math.max(left,Math.min(level.columns-1,Math.floor((surface.width-view.x)/view.scale/size)));
        const bottom=Math.max(top,Math.min(level.rows-1,Math.floor((surface.height-view.y)/view.scale/size)));
        if(right-left+1<=limits.width&&bottom-top+1<=limits.height&&(right-left+1)*(bottom-top+1)<=limits.area)return level;
    }
    return manifest.levels.reduce((a,b)=>a.lod>b.lod?a:b);
}
export function tileUrl(manifest, level, column, row) {
    const url = manifest.tileUrlTemplate.replace("{lod}", String(level.lod)).replace("{x}", String(column)).replace("{y}", String(row));
    return /[?#]/.test(url) || /\.(?:webp|png|jpe?g)$/i.test(url) ? url : `${url}.webp`;
}
/**
 * The tiles the screen is strictly showing, with no slack.
 *
 * This is what the table is told about — where this client is looking — so it deliberately excludes
 * the prefetch ring: reporting speculation as attention would teach the table the wrong thing.
 */
export function visibleRange(manifest, view, surface) {
    const level = viewportLevel(manifest, view, surface);
    const size = manifest.tileSize * (manifest.width / level.width);
    const left = Math.max(0, -view.x / view.scale);
    const top = Math.max(0, -view.y / view.scale);
    const right = Math.min(manifest.width, (surface.width - view.x) / view.scale);
    const bottom = Math.min(manifest.height, (surface.height - view.y) / view.scale);
    return {
        mapId: manifest.mapId,
        lod: level.lod,
        firstColumn: Math.max(0, Math.floor(left / size)),
        firstRow: Math.max(0, Math.floor(top / size)),
        lastColumn: Math.max(0, Math.min(level.columns - 1, Math.floor(right / size))),
        lastRow: Math.max(0, Math.min(level.rows - 1, Math.floor(bottom / size))),
    };
}
/** True when two ranges cover exactly the same tiles, which is how a report knows to stay quiet. */
export function sameRegion(left, right) {
    if (!left || !right)
        return left === right;
    return left.mapId === right.mapId && left.lod === right.lod
        && left.firstColumn === right.firstColumn && left.firstRow === right.firstRow
        && left.lastColumn === right.lastColumn && left.lastRow === right.lastRow;
}
/** Every tile url a region covers, for warming a cache rather than drawing anything. */
export function regionTileUrls(manifest, region, limit = Infinity, include = () => true) {
    const level = manifest.levels.find(({ lod }) => lod === region.lod);
    if (!level)
        return [];
    const urls = [];
    for (let row = Math.max(0, region.firstRow); row <= Math.min(level.rows - 1, region.lastRow); row += 1) {
        for (let column = Math.max(0, region.firstColumn); column <= Math.min(level.columns - 1, region.lastColumn); column += 1) {
            const url = tileUrl(manifest, level, column, row);
            if (include(url))
                urls.push(url);
            if (urls.length >= limit)
                return urls;
        }
    }
    return urls;
}
/**
 * The tiles a viewport wants, each classified by where it sits relative to the eye.
 *
 * The range is padded by one tile on every side so that panning meets loaded pixels rather than
 * gaps; that padding is the prefetch ring, and it is deliberately the lowest priority — a pan that
 * has not happened yet must never delay the screen that is already being looked at.
 */
export function planTiles(manifest, view, surface) {
    const level = viewportLevel(manifest, view, surface);
    const ratio = manifest.width / level.width;
    const size = manifest.tileSize * ratio;
    const visible = visibleRange(manifest, view, surface);
    // Where the player is actually looking. Taking the centre of the clamped range instead would put
    // the focus off to one side whenever the map runs out before the screen does.
    const focus = {
        column: ((surface.width / 2 - view.x) / view.scale) / size,
        row: ((surface.height / 2 - view.y) / view.scale) / size,
    };
    const planned = [];
    for (let row = Math.max(0, visible.firstRow - 1); row <= Math.min(level.rows - 1, visible.lastRow + 1); row += 1) {
        for (let column = Math.max(0, visible.firstColumn - 1); column <= Math.min(level.columns - 1, visible.lastColumn + 1); column += 1) {
            const { priority, ring, distance } = classifyTile({ column, row }, visible, focus);
            planned.push({
                // The map is part of a tile's identity, not just its coordinates: two scenes both have a
                // `0:0:0`, and sharing that key lets one scene's in-flight load suppress the other's.
                tile: {
                    key: `${manifest.mapId}:${level.lod}:${column}:${row}`,
                    url: tileUrl(manifest, level, column, row),
                    x: column * size,
                    y: row * size,
                    scale: ratio,
                    // Depth counts up from the coarsest level, so finer tiles draw over coarser ones and a
                    // level being replaced can stay underneath as a backdrop instead of the map going blank.
                    depth: manifest.maxLod - level.lod,
                },
                priority,
                ring,
                distance,
            });
        }
    }
    return planned;
}
