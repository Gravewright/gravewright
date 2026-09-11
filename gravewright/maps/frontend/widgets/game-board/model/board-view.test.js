import assert from "node:assert/strict";
import test from "node:test";
import { fitToSurface, levelFor, planTiles, tileUrl, worldPoint } from "./board-view.js";
import { PRIORITY } from "./tile-scheduler.js";
/** The planner classifies as well as places; these tests care about one or the other. */
const visibleTiles = (...args) => planTiles(...args).map(({ tile }) => tile);
const manifest = {
    blockId: "block-a",
    mapId: "map-1",
    width: 4000,
    height: 2000,
    tileSize: 512,
    maxLod: 2,
    levels: [
        { lod: 0, width: 4000, height: 2000, columns: 8, rows: 4 },
        { lod: 1, width: 2000, height: 1000, columns: 4, rows: 2 },
        { lod: 2, width: 1000, height: 500, columns: 2, rows: 1 },
    ],
    tileUrlTemplate: "/maps/map-1/{lod}/{x}_{y}",
};
const surface = { width: 800, height: 600 };
test("a scene opens with the whole map on screen and centred", () => {
    const view = fitToSurface(surface, manifest);
    assert.equal(view.scale, 800 / 4000, "the wider axis is the one that has to fit");
    assert.equal(view.x, 0);
    assert.equal(view.y, (600 - 2000 * view.scale) / 2);
});
test("a point on the surface maps back to the coordinate under it", () => {
    const view = { x: 50, y: 20, scale: .5 };
    assert.deepEqual(worldPoint({ x: 250, y: 120 }, view), { x: 400, y: 200 });
});
test("zooming out walks down the pyramid and stops at the coarsest level", () => {
    assert.equal(levelFor(manifest, 1).lod, 0);
    assert.equal(levelFor(manifest, .5).lod, 1);
    assert.equal(levelFor(manifest, .25).lod, 2);
    assert.equal(levelFor(manifest, .01).lod, 2, "past the last level the coarsest one is reused");
    assert.equal(levelFor(manifest, 4).lod, 0, "zooming in never asks for detail the pyramid lacks");
});
test("tile urls fill the template and always name a webp", () => {
    assert.equal(tileUrl(manifest, manifest.levels[1], 3, 2), "/maps/map-1/1/3_2.webp");
    assert.equal(tileUrl({ ...manifest, tileUrlTemplate: "/t/{lod}/{x}/{y}.webp" }, manifest.levels[0], 1, 0), "/t/0/1/0.webp");
});
test("only the tiles the viewport covers are asked for, with a row of slack around them", () => {
    const tiles = visibleTiles(manifest, { x: 0, y: 0, scale: 1 }, surface);
    const keys = new Set(tiles.map((tile) => tile.key));
    assert.ok(keys.has("map-1:0:0:0"));
    // The surface shows 800x600 of a 512-tile grid: columns 0-1 and rows 0-1 are covered, plus one
    // row of slack, which the grid's own edge clamps to the same tiles.
    assert.ok(keys.has("map-1:0:2:2"), "the slack row is loaded ahead of the pan");
    assert.ok(!keys.has("map-1:0:4:0"), "tiles well past the right edge stay unloaded");
    assert.ok(!keys.has("map-1:0:0:3"));
});
test("tiles are placed and scaled so a coarse level still covers the whole map", () => {
    const tiles = visibleTiles(manifest, { x: 0, y: 0, scale: .25 }, surface);
    const first = tiles.find((tile) => tile.key === "map-1:2:0:0");
    assert.ok(first, "the coarsest level covers the map from the origin");
    assert.equal(first.scale, 4, "a quarter-size level is drawn four times bigger");
    assert.equal(first.x, 0);
    const next = tiles.find((tile) => tile.key === "map-1:2:1:0");
    assert.equal(next?.x, 512 * 4, "neighbouring tiles sit one scaled tile apart");
});
test("two scenes never share a tile identity", () => {
    const other = { ...manifest, mapId: "map-2", tileUrlTemplate: "/maps/map-2/{lod}/{x}_{y}" };
    const [first] = visibleTiles(manifest, { x: 0, y: 0, scale: 1 }, surface);
    const [second] = visibleTiles(other, { x: 0, y: 0, scale: 1 }, surface);
    assert.notEqual(first?.key, second?.key, "the same cell of two maps must not collide: a load in flight for one would suppress the other's");
    assert.equal(first?.key, "map-1:0:0:0");
    assert.equal(second?.key, "map-2:0:0:0");
});
test("the tile under the eye outranks the one at the edge of the screen", () => {
    // A screen wide enough to hold several tiles, so "near the eye" and "on screen" differ at all.
    const wide = { width: 2400, height: 1600 };
    const planned = planTiles(manifest, { x: 0, y: 0, scale: 1 }, wide);
    const at = (key) => planned.find((entry) => entry.tile.key === key);
    assert.equal(at("map-1:0:2:1")?.ring, "visible-center", "the middle of the screen is where the eye is");
    assert.equal(at("map-1:0:2:1")?.priority, PRIORITY.high);
    assert.equal(at("map-1:0:0:0")?.ring, "visible-edge", "on screen, but a corner away from the eye");
    assert.equal(at("map-1:0:0:0")?.priority, PRIORITY.normal);
});
test("the slack ring is fetched, but only after the screen is whole", () => {
    const planned = planTiles(manifest, { x: 0, y: 0, scale: 1 }, surface);
    const slack = planned.filter(({ ring }) => ring === "prefetch");
    assert.ok(slack.length > 0, "there is a ring to pan into");
    for (const tile of slack)
        assert.equal(tile.priority, PRIORITY.low);
});
test("a level carries where it sits in the stack, so a coarse backdrop stays underneath", () => {
    const [fine] = planTiles(manifest, { x: 0, y: 0, scale: 1 }, surface);
    const [coarse] = planTiles(manifest, { x: 0, y: 0, scale: .25 }, surface);
    assert.equal(fine?.tile.depth, manifest.maxLod, "the full-resolution level is the top of the stack");
    assert.equal(coarse?.tile.depth, 0, "the coarsest level is the floor");
    assert.ok((fine?.tile.depth ?? 0) > (coarse?.tile.depth ?? 0), "finer draws over coarser whichever way the zoom went");
});
test("a map panned entirely off the surface asks for nothing", () => {
    assert.deepEqual(visibleTiles(manifest, { x: -100_000, y: 0, scale: 1 }, surface), []);
});
test("tile URLs with query parameters are preserved for the Python engine", () => {
    assert.equal(tileUrl({ ...manifest, tileUrlTemplate: "/game/tiles/{x}/{y}?lod={lod}" }, manifest.levels[0], 1, 0), "/game/tiles/1/0?lod=0");
});

test('viewport limits choose a common coarser level for reports and tile drawing',()=>{
 const capped={...manifest,viewportLimits:{width:2,height:2,area:4}};
 const tiles=visibleTiles(capped,{x:0,y:0,scale:1},{width:4000,height:2000});
 assert.ok(tiles.length<=4);
 assert.ok(tiles.every(tile=>tile.key.startsWith('map-1:2:')));
});
