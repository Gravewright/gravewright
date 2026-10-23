import { test } from "node:test";
import assert from "node:assert/strict";
import {
    MAX_MANUAL_FIELDS, MIN_MANUAL_SIZE, sourceKey, manualFieldKey, validManualField,
    validateManualFields, manualFieldsForSource, manualFieldSpec, normalizedRect,
    manualFieldBounds, moveManualField, resizeManualField,
} from "./manual-fields.js";
import { readCanonical, writeCanonical } from "./mapping.js";

const ID = "d6bd209a-120c-4e2a-8de7-1b53771e87d4";
const OTHER_ID = "d6bd209a-120c-4e2a-8de7-1b53771e87d5";
const ASSET = "a71259ad-6d49-476a-924e-dbeae1182af0";
const field = (changes = {}) => ({
    id: ID, source: `asset:${ASSET}`, page: 1, type: "text", name: "Character name",
    x: 0.1, y: 0.2, width: 0.4, height: 0.05, ...changes,
});

test("source identity keeps uploaded PDFs and templates separate", () => {
    assert.equal(sourceKey({ kind: "asset", id: ASSET }), `asset:${ASSET}`);
    assert.equal(sourceKey({ kind: "asset", id: ASSET.toUpperCase() }), `asset:${ASSET}`);
    assert.equal(sourceKey({ kind: "template", id: "generic_2-A" }), "template:generic_2-A");
    assert.equal(sourceKey("template:generic"), "template:generic");
    for (const source of [null, {}, { kind: "asset", id: 12 }, "asset:../other", "template:", "template:a.b", "template:" + "a".repeat(121)])
        assert.equal(sourceKey(source), "");
});

test("manual fields retain distinct value paths when names collide or change", () => {
    const first = field();
    const second = field({ id: OTHER_ID });
    const firstSpec = manualFieldSpec(first);
    const actor = { name: "Hero", data: { fields: {} } };
    writeCanonical(actor, firstSpec.path, "Ada");
    writeCanonical(actor, manualFieldSpec(second).path, "Lin");
    assert.notEqual(manualFieldKey(first), manualFieldKey(second));
    assert.equal(manualFieldKey(first), "manual_d6bd209a120c4e2a8de71b53771e87d4");
    assert.equal(manualFieldSpec({ ...first, name: "__proto__.renamed" }).path, firstSpec.path);
    assert.equal(readCanonical(actor, firstSpec.path), "Ada");
    assert.equal(readCanonical(actor, manualFieldSpec(second).path), "Lin");
    assert.equal(manualFieldKey("__proto__"), "");
    assert.equal(manualFieldSpec(field({ id: "../invalid" })), null);
});

test("manual field types use the existing canonical mapping value contract", () => {
    assert.equal(manualFieldSpec(field()).type, "string");
    assert.equal(manualFieldSpec(field({ type: "multiline" })).type, "string");
    assert.equal(manualFieldSpec(field({ type: "number" })).type, "number");
    assert.equal(manualFieldSpec(field({ type: "checkbox" })).type, "boolean");
    assert.equal(manualFieldSpec(field({ type: "script" })), null);
});

test("definition validation rejects malformed, oversized and out of page fields", () => {
    assert.equal(validManualField(field()), true);
    assert.equal(validManualField(field({ x: 0, y: 0, width: 1, height: 1, page: 100000 })), true);
    for (const changes of [
        { id: ID.toUpperCase() }, { source: "asset:bad" }, { source: { kind: "template", id: "generic" } },
        { page: 0 }, { page: 1.5 }, { page: 100001 }, { type: "script" }, { name: "  \n" },
        { name: "a".repeat(121) }, { name: 12 }, { x: -0.01 }, { x: "0.1" }, { x: NaN },
        { y: Infinity }, { x: 0.8 }, { width: 0 }, { height: MIN_MANUAL_SIZE / 2 },
        { width: 1.1 }, { unexpected: true },
    ])
        assert.equal(validManualField(field(changes)), false, JSON.stringify(changes));
    assert.equal(validateManualFields([field(), field({ id: OTHER_ID })]), true);
    assert.equal(validateManualFields([field(), field({ name: "Duplicate UUID" })]), false);
    assert.equal(validateManualFields(Array.from({ length: MAX_MANUAL_FIELDS + 1 }, () => field())), false);
    assert.equal(validateManualFields(null), false);
    assert.equal(validateManualFields([]), true);
});

test("only definitions for the current document enter its field list", () => {
    const first = field();
    const template = field({ id: OTHER_ID, source: "template:generic" });
    const pdf = { manualFields: [first, template, field({ page: 0 })] };
    assert.deepEqual(manualFieldsForSource(pdf, { kind: "asset", id: ASSET }), [first]);
    assert.deepEqual(manualFieldsForSource(pdf, { kind: "template", id: "generic" }), [template]);
    assert.deepEqual(manualFieldsForSource(pdf, "template:other"), []);
    assert.deepEqual(manualFieldsForSource({}, "template:generic"), []);
});

test("drawing rectangles handles reversed gestures and clamps to one displayed page", () => {
    assert.deepEqual(normalizedRect({ x: 0.7, y: 0.6 }, { x: 0.2, y: 0.3 }), { x: 0.2, y: 0.3, width: 0.49999999999999994, height: 0.3 });
    assert.deepEqual(normalizedRect({ x: 50, y: 100 }, { x: 500, y: 1000 }, { left: 100, top: 200, width: 400, height: 800 }), { x: 0, y: 0, width: 1, height: 1 });
    assert.equal(normalizedRect({ x: 0.2, y: 0.2 }, { x: 0.2, y: 0.5 }), null);
    assert.equal(normalizedRect({ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 + MIN_MANUAL_SIZE / 2 }), null);
    assert.equal(normalizedRect({ x: NaN, y: 0 }, { x: 1, y: 1 }), null);
    assert.equal(normalizedRect({ x: 0, y: 0 }, { x: 1, y: 1 }, { width: 0, height: 2 }), null);
});

test("drawing is independent of zoom and page screen offsets", () => {
    const atNormalZoom = normalizedRect({ x: 140, y: 240 }, { x: 300, y: 320 }, { left: 100, top: 200, width: 400, height: 800 });
    const atDoubleZoom = normalizedRect({ x: 230, y: 160 }, { x: 550, y: 320 }, { left: 150, top: 80, width: 800, height: 1600 });
    assert.deepEqual(atNormalZoom, atDoubleZoom);
    assert.deepEqual(atNormalZoom, { x: 0.1, y: 0.05, width: 0.4, height: 0.09999999999999999 });
});

test("overlays follow rotated display viewports, zoom, and spread offsets", () => {
    const definition = field({ x: 0.25, y: 0.1, width: 0.5, height: 0.2 });
    const portrait = manualFieldBounds(definition, { width: 600, height: 800 });
    const landscape = manualFieldBounds(definition, { width: 800, height: 600, rotation: 90 });
    const zoomedLandscape = manualFieldBounds(definition, { width: 1600, height: 1200, rotation: 90 }, 1300);
    assert.deepEqual(portrait, { left: 150, top: 80, width: 300, height: 160, hidden: false });
    assert.deepEqual(landscape, { left: 200, top: 60, width: 400, height: 120, hidden: false });
    assert.deepEqual(zoomedLandscape, { left: 400, top: 1420, width: 800, height: 240, hidden: false });
    assert.equal(definition.x, 0.25);
});

test("moving and resizing preserve identity and keep the entire field on the page", () => {
    const original = field();
    const moved = moveManualField(original, 4, -4);
    assert.deepEqual(moved, { ...original, x: 0.6, y: 0 });
    assert.equal(manualFieldKey(moved), manualFieldKey(original));
    assert.equal(validManualField(moved), true);
    assert.deepEqual(original, field());
    const resized = resizeManualField(original, { x: 0.8, y: -0.1, width: 0.5, height: 0 });
    assert.deepEqual(resized, { ...original, x: 0.5, y: 0, width: 0.5, height: MIN_MANUAL_SIZE });
    assert.equal(validManualField(resized), true);
    assert.equal(moveManualField(original, Infinity, 0), null);
    assert.equal(resizeManualField(original, { x: 0, y: 0, width: NaN, height: 1 }), null);
});
