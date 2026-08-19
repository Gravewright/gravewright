const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const scene = { id: "scene", width: 1000, height: 1000, scaledTileSize: 100 };
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(
    fs.readFileSync("static/js/map/measures/map-measure-geometry.js", "utf8"),
    sandbox,
);

const geometry = sandbox.window.GravewrightMapMeasureGeometry.createMeasureGeometry({
    defaultGridSize: 100,
    sceneDataFor: () => scene,
    stateFor: () => ({ offsetX: 0, offsetY: 0, zoom: 1 }),
    screenFromWorld: (value) => value,
    screenToWorldXY: (x, y) => ({ worldX: x, worldY: y }),
    measureStoreFor: () => [],
});

const pointer = { clientX: 126, clientY: 174, shiftKey: true };
assert.deepStrictEqual(
    JSON.parse(JSON.stringify(geometry.measureStartPointFromEvent({}, pointer))),
    { worldX: 150, worldY: 150 },
    "Shift no longer creates a second vertex-based marker model",
);

const horizontal = {
    shape: "line",
    start: { worldX: 50, worldY: 50 },
    end: { worldX: 450, worldY: 50 },
};
assert.strictEqual(geometry.measureLabelFor(horizontal, scene), "5 cel");
assert.deepStrictEqual(
    JSON.parse(JSON.stringify(
        geometry.gridCellsForMeasure(horizontal, scene).map((cell) => `${cell.col},${cell.row}`),
    )),
    ["0,0", "1,0", "2,0", "3,0", "4,0"],
    "A five-square line must occupy and report all five squares",
);

const rectangle = {
    shape: "square",
    start: { worldX: 50, worldY: 50 },
    end: { worldX: 450, worldY: 250 },
};
assert.strictEqual(geometry.measureLabelFor(rectangle, scene), "5 cel x 3 cel");
assert.strictEqual(geometry.gridCellsForMeasure(rectangle, scene).length, 15);

const circle = {
    shape: "circle",
    start: { worldX: 250, worldY: 250 },
    end: { worldX: 450, worldY: 250 },
};
const circleCells = geometry.gridCellsForMeasure(circle, scene);
assert(circleCells.some((cell) => cell.col === 2 && cell.row === 2));
assert(circleCells.some((cell) => cell.col === 2 && cell.row === 0), "Circle must cover cells above its horizontal radius handle");
assert(circleCells.some((cell) => cell.col === 2 && cell.row === 4), "Circle must cover cells below its horizontal radius handle");
assert(circleCells.every((cell) => {
    const x = (cell.col + 0.5) * 100 - circle.start.worldX;
    const y = (cell.row + 0.5) * 100 - circle.start.worldY;
    return Math.hypot(x, y) <= 200.001;
}));

const cone = {
    shape: "cone",
    start: { worldX: 150, worldY: 250 },
    end: { worldX: 550, worldY: 250 },
};
const coneCells = geometry.gridCellsForMeasure(cone, scene);
assert(coneCells.some((cell) => cell.col === 1 && cell.row === 2));
assert(coneCells.some((cell) => cell.col === 5 && cell.row === 2));
assert(!coneCells.some((cell) => cell.col === 1 && cell.row === 5));

const verticalCone = {
    shape: "cone",
    start: { worldX: 250, worldY: 150 },
    end: { worldX: 250, worldY: 550 },
};
const verticalConeCells = geometry.gridCellsForMeasure(verticalCone, scene);
assert(verticalConeCells.some((cell) => cell.col === 2 && cell.row === 5));
assert(verticalConeCells.some((cell) => cell.col === 1 && cell.row === 4));

console.log("measure grid footprint harness: ok");
