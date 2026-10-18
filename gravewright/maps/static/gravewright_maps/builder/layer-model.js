/** Layer operations on authored documents, independent of the workspace and scene. */
import { clone, duplicateSelection, objectKinds, selectionBounds } from './model.js';
import { floorGeometryError } from './floor-geometry.js';
import { expandTorchSelection, torchOwner } from './torch-model.js';

const maxLayers = 32;
const maxObjects = 2000;
const editable = layer => layer.visible === true && layer.locked === false;
const reference = (kind, row) => ({ kind, id: row.id });

function inspectDocument(document) {
    if (!document || !Array.isArray(document.layers) || document.layers.length > maxLayers) return null;
    const layers = new Map(), objects = new Map(), identifiers = new Set();
    for (const [index, layer] of document.layers.entries()) {
        if (!layer || typeof layer.id !== 'string' || !layer.id || layers.has(layer.id)
            || typeof layer.visible !== 'boolean' || typeof layer.locked !== 'boolean') return null;
        layers.set(layer.id, { layer, index, count: 0, hasTerrainErase: false,
            counts: Object.fromEntries(objectKinds.map(kind => [kind, 0])), refs: [] });
    }
    let count = 0;
    for (const kind of objectKinds) {
        if (kind in document && !Array.isArray(document[kind])) return null;
        const rows = new Map(); objects.set(kind, rows);
        for (const row of document[kind] || []) {
            const group = row && layers.get(row.layerId);
            if (!group || typeof row.id !== 'string' || !row.id || identifiers.has(row.id) || ++count > maxObjects) return null;
            identifiers.add(row.id); rows.set(row.id, row);
            if (kind === 'floors' && row.brush?.operation === 'erase') group.hasTerrainErase = true;
            group.count++; group.counts[kind]++; group.refs.push(reference(kind, row));
        }
    }
    return { layers, objects, count };
}

function mergeTarget(context, sourceId) {
    const source = context?.layers.get(sourceId);
    if (!source || source.index === 0 || !editable(source.layer)) return null;
    const target = [...context.layers.values()][source.index - 1];
    // Erasure is local to its original layer; rebinding it could destroy lower backing.
    if (source.hasTerrainErase && target.counts.floors) return null;
    return editable(target.layer) ? target : null;
}

/** Stored layer order is bottom to top. Returned records never expose authored objects. */
export function layerSummaries(document) {
    const context = inspectDocument(document);
    if (!context) return [];
    return [...context.layers.values()].map(group => ({ ...group.layer, index: group.index,
        count: group.count, counts: group.counts, refs: group.refs,
        canMergeDown: Boolean(mergeTarget(context, group.layer.id)) }));
}

export function layerContents(document, layerId, { editable: editableOnly = false } = {}) {
    const group = inspectDocument(document)?.layers.get(layerId);
    return group && (!editableOnly || editable(group.layer)) ? group.refs : [];
}

/** Move a layer to its final bottom-to-top index without touching its contents. */
export function reorderLayer(document, layerId, index) {
    const context = inspectDocument(document), source = context?.layers.get(layerId);
    if (!source || !Number.isInteger(index) || index < 0 || index >= context.layers.size || source.index === index) return false;
    const layers = [...document.layers];
    layers.splice(source.index, 1); layers.splice(index, 0, source.layer);
    document.layers = layers;
    return true;
}

/** Copy a layer one cell down/right, including internal Smart Object targets. */
export function duplicateLayer(document, layerId, name) {
    const context = inspectDocument(document), source = context?.layers.get(layerId);
    if (!source || source.layer.locked || context.layers.size >= maxLayers || context.count + source.count > maxObjects
        || typeof name !== 'string' || !name.trim() || name.trim().length > 80 || name.includes('\0')) return null;
    const bounds = selectionBounds(document, source.refs);
    // Unlike selection duplication, copying a layer keeps the exact one-cell offset.
    if (bounds && (bounds.x + 1 < 0 || bounds.y + 1 < 0
        || bounds.x + bounds.width + 1 > document.columns || bounds.y + bounds.height + 1 > document.rows)) return null;
    const next = clone(document), layer = { id: crypto.randomUUID(), name: name.trim(), visible: true, locked: false };
    next.layers.splice(source.index + 1, 0, layer);
    const refs = source.count ? duplicateSelection(next, source.refs, 1, 1, { includeComponents: true }) : [];
    if (refs.length !== source.count) return null;
    const identifiers = new Set(refs.map(ref => ref.id));
    for (const kind of objectKinds) for (const row of next[kind] || []) if (identifiers.has(row.id)) row.layerId = layer.id;
    if (floorGeometryError(next)) return null;
    document.layers = next.layers;
    for (const kind of objectKinds) if (kind in next) document[kind] = next[kind];
    return { layerId: layer.id, refs };
}

export function canMergeLayerDown(document, sourceId) {
    return Boolean(mergeTarget(inspectDocument(document), sourceId));
}

/** Merge only into the adjacent lower layer, retaining every identity and reference. */
export function mergeLayerDown(document, sourceId) {
    const context = inspectDocument(document), target = mergeTarget(context, sourceId);
    if (!target) return null;
    const source = context.layers.get(sourceId), staged = new Map(), refs = [];
    for (const kind of objectKinds) {
        if (!(kind in document)) continue;
        // Once two layers share an ID, array order determines their paint order.
        // Preserve their old layer precedence before replacing the source ID.
        const rows = document[kind].map((row, index) => ({ row, index }))
            .sort((a, b) => context.layers.get(a.row.layerId).index - context.layers.get(b.row.layerId).index || a.index - b.index)
            .map(({ row }) => row.layerId === sourceId ? { ...row, layerId: target.layer.id } : row);
        staged.set(kind, rows);
        for (const row of rows) if (row.layerId === target.layer.id) refs.push(reference(kind, row));
    }
    const layers = document.layers.filter(layer => layer.id !== sourceId);
    document.layers = layers;
    for (const [kind, rows] of staged) document[kind] = rows;
    return { layerId: target.layer.id, refs, moved: source.refs };
}

/** Move a complete editable selection, or leave the document untouched. */
export function moveSelectionToLayer(document, refs, targetId) {
    const context = inspectDocument(document), target = context?.layers.get(targetId);
    if (!target || !editable(target.layer) || !Array.isArray(refs) || !refs.length) return false;
    const selected = new Map();
    let changed = false;
    const grouped = expandTorchSelection(document, refs.map(ref => {
        const owner = ref && torchOwner(document, ref.kind, ref.id);
        return owner ? { kind: 'decorations', id: owner.id } : ref;
    }));
    for (const ref of grouped) {
        const row = ref && context.objects.get(ref.kind)?.get(ref.id);
        if (!row || !editable(context.layers.get(row.layerId).layer)) return false;
        let ids = selected.get(ref.kind);
        if (!ids) selected.set(ref.kind, ids = new Set());
        ids.add(row.id);
        if (row.layerId !== targetId) changed = true;
    }
    if (!changed) return false;
    const staged = new Map();
    for (const [kind, ids] of selected) staged.set(kind, document[kind].map(row =>
        ids.has(row.id) && row.layerId !== targetId ? { ...row, layerId: targetId } : row));
    for (const [kind, rows] of staged) document[kind] = rows;
    return true;
}
