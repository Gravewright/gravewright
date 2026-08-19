const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

class Graphics {
    constructor() { this.ops = []; this.visible = true; }
    clear() { this.ops = []; return this; }
    record(name, args) { this.ops.push([name, ...args]); return this; }
    rect(...args) { return this.record("rect", args); }
    roundRect(...args) { return this.record("roundRect", args); }
    circle(...args) { return this.record("circle", args); }
    moveTo(...args) { return this.record("moveTo", args); }
    lineTo(...args) { return this.record("lineTo", args); }
    poly(...args) { return this.record("poly", args); }
    fill(...args) { return this.record("fill", args); }
    stroke(...args) { return this.record("stroke", args); }
}

class Container {
    constructor() {
        this.children = [];
        this.visible = true;
        this.position = { set: (x, y) => { this.x = x; this.y = y; } };
    }
    addChild(...children) { this.children.push(...children); return children[0]; }
}

class Text {
    constructor(options) {
        this.text = options.text;
        this.style = options.style;
        this.anchor = { set: () => {} };
    }
    get width() { return String(this.text).length * 7; }
    get height() { return 14 * String(this.text).split("\n").length; }
}

class Color {
    constructor(value) { this.value = value; }
    toNumber() { return Number.parseInt(String(this.value).replace("#", ""), 16) || 0; }
}

class Renderer {
    _color(value) { return new Color(value).toNumber(); }
}

const sandbox = {
    PIXI: { Color, Container, Graphics, Text },
    window: {
        devicePixelRatio: 1,
        GravewrightBoardInternals: { PixiBoardRenderer: Renderer },
    },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("static/js/board/pixi/pixi-measure-layer.js", "utf8"), sandbox);

const renderer = new Renderer();
renderer.camera = { offsetX: 0, offsetY: 0, zoom: 1 };
renderer.scene = { scaledTileSize: 100 };
const board = {
    measureGfx: new Graphics(),
    measureLabelLayer: new Container(),
    measureLayer: new Container(),
    measureLabels: [],
    measureSnapshot: {
        items: [
            {
                id: "line",
                kind: "shape",
                shape: "line",
                start: { worldX: 50, worldY: 50 },
                end: { worldX: 450, worldY: 50 },
                cells: [0, 1, 2, 3, 4].map((col) => ({ worldX: col * 100, worldY: 0, size: 100 })),
                label: "5 cel",
                style: { stroke: "#22c55e", fill: "rgba(34,197,94,0.18)", strokeWidth: 2 },
            },
            {
                id: "circle",
                kind: "shape",
                shape: "circle",
                start: { worldX: 250, worldY: 250 },
                end: { worldX: 450, worldY: 250 },
                label: "2 cel",
                style: { stroke: "#22c55e", fill: "rgba(34,197,94,0.18)", strokeWidth: 2 },
            },
        ],
    },
};

renderer._renderMeasurements(board);
assert.strictEqual(board.measureGfx.ops.filter(([name]) => name === "rect").length, 5);
assert(board.measureGfx.ops.some(([name]) => name === "circle"));
assert.strictEqual(board.measureLabels.length, 2);
assert.strictEqual(board.measureLabels[0].text.text, "5 cel");
assert.strictEqual(board.measureLabels[1].text.text, "2 cel");
assert.strictEqual(board.measureLayer.visible, true);

console.log("pixi measure layer harness: ok");
