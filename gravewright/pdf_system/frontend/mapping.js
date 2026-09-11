import { text as gwText } from './text.js';
// The token bar reads fixed, system-owned paths. Choosing a PDF field for a
// bar only changes where that field WRITES — one value, one place, never a
// mirrored second write.
export const BAR_SLOTS = [
    { key: "bar1Value", label: gwText('Bar 1 · Current'), path: "sheet.bars.bar_1.value" },
    { key: "bar1Max", label: gwText('Bar 1 · Maximum'), path: "sheet.bars.bar_1.max" },
    { key: "bar2Value", label: gwText('Bar 2 · Current'), path: "sheet.bars.bar_2.value" },
    { key: "bar2Max", label: gwText('Bar 2 · Maximum'), path: "sheet.bars.bar_2.max" },
    { key: "initiative", label: gwText('Initiative'), path: "sheet.init" },
    { key: "defense", label: gwText('Defense'), path: "sheet.ac" },
];
// A PDF form field name is free text; since it becomes one segment of a
// dotted path, anything outside [A-Za-z0-9_-] collapses to "_" or the field
// would open an unintended nested object and its value would vanish from
// where a reader expects it.
export function safeSegment(name) {
    return (name || "").replace(/[^A-Za-z0-9_-]/g, "_").replace(/^_+|_+$/g, "") || "campo";
}
// A PDF uploaded straight to the campaign library has no hand-written
// mapping: every field name falls back to `sheet.fields.<name>`, which the
// schema leaves open on purpose. A field chosen to feed a token bar instead
// writes directly to that bar's canonical path.
export function autoMapFields(fieldNames, canonicalFields, fieldType, barChoices) {
    const fields = Object.create(null);
    const forBar = new Map();
    for (const slot of BAR_SLOTS) {
        const chosen = barChoices[slot.key];
        if (chosen)
            forBar.set(chosen, slot.path);
    }
    const used = new Set();
    for (const name of fieldNames) {
        const barPath = forBar.get(name);
        if (barPath) {
            fields[name] = { path: barPath, type: "number" };
            continue;
        }
        const known = canonicalFields && Object.hasOwn(canonicalFields, name) ? canonicalFields[name] : undefined;
        if (known) {
            fields[name] = known;
            continue;
        }
        let segment = safeSegment(name);
        const base = segment;
        let suffix = 2;
        while (used.has(segment))
            segment = `${base}_${suffix++}`;
        used.add(segment);
        fields[name] = { path: `sheet.fields.${segment}`, type: fieldType(name) === "Btn" ? "boolean" : "string" };
    }
    return fields;
}
// Two path vocabularies exist on purpose: the mapping and the token reader
// speak the canonical one (`core.name`, `sheet.hp.value`) because both need
// to agree on the same address. Resolved directly against the actor here —
// no intermediate ctx.data wrapper, since this sheet owns its own data. The
// caller's `data` keeps its own concrete shape (not `Record<string, unknown>`,
// which a named interface without an index signature can't satisfy); paths
// are walked dynamically here instead.
export function readCanonical(actor, path) {
    if (path === "core.name")
        return actor.name;
    if (!path.startsWith("sheet.") || path.split(".").some(key => ["__proto__", "prototype", "constructor"].includes(key)))
        return;
    const rest = path.slice("sheet.".length);
    return rest.split(".").reduce((cursor, key) => (cursor && typeof cursor === "object" ? cursor[key] : undefined), actor.data);
}
export function writeCanonical(actor, path, value) {
    if (path === "core.name") {
        actor.name = String(value ?? "");
        return;
    }
    if (!path.startsWith("sheet.") || path.split(".").some(key => ["__proto__", "prototype", "constructor"].includes(key)))
        return;
    const rest = path.slice("sheet.".length);
    const keys = rest.split(".");
    const last = keys.pop();
    if (!last)
        return;
    let cursor = actor.data;
    for (const key of keys) {
        if (!cursor[key] || typeof cursor[key] !== "object")
            cursor[key] = {};
        cursor = cursor[key];
    }
    cursor[last] = value;
}
