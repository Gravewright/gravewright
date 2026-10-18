/** Reconcile permanent campaign image deletion with independent editor drafts. */
import { removeObject } from './object-removal.js';

function detachAppearanceActions(blueprint, assetId) {
    for (const graph of Object.values(blueprint.graphs || {})) {
        const removed = (graph.nodes || []).filter(node => node.type === 'setAppearance' && node.assetId === assetId);
        for (const node of removed) {
            const continuations = graph.edges.filter(edge => edge.kind !== 'data' && edge.from === node.id && edge.output === 'next');
            const edges = [], seen = new Set();
            const append = edge => {
                const identity = JSON.stringify([edge.kind, edge.from, edge.output, edge.to, edge.input]);
                if (!seen.has(identity)) { seen.add(identity); edges.push(edge); }
            };
            for (const edge of graph.edges) {
                if (edge.from === node.id) continue;
                if (edge.to === node.id) {
                    // A Target value must never become an execution predecessor.
                    if (edge.kind === 'data') continue;
                    for (const continuation of continuations) append({ ...edge, to: continuation.to });
                } else append(edge);
            }
            graph.edges = edges;
            graph.nodes = graph.nodes.filter(item => item.id !== node.id);
        }
        if (graph.edges.length > 64) throw new Error('The blueprint has too many nodes or connections.');
    }
}

export function detachDocumentAsset(document, assetId, availableIds = []) {
    const result = structuredClone(document), available = new Set(availableIds);
    if (result.backgroundImage?.assetId === assetId) delete result.backgroundImage;
    result.assets = (result.assets || []).filter(entry => entry.assetId !== assetId);
    for (const kind of ['floors', 'walls', 'doors', 'decorations', 'regions']) {
        for (const item of result[kind] || []) {
            if (item.assetId === assetId) {
                const replacement = kind === 'decorations' && item.lever
                    ? Object.values(item.blueprint?.states || {}).find(state => state.appearance === 'asset'
                        && state.assetId !== assetId && available.has(state.assetId))?.assetId
                    : null;
                item.assetId = replacement || null;
                if (kind === 'decorations' && item.torch && !replacement) removeObject(result, 'lights', item.torch.lightId);
                if (kind === 'decorations' && item.lever && !replacement) {
                    delete item.lever;
                    delete item.blueprint;
                }
            }
            if (!item.blueprint) continue;
            detachAppearanceActions(item.blueprint, assetId);
            const appearances = [...Object.values(item.blueprint.states || {}),
                ...Object.values(item.blueprint.graphs || {}).flatMap(graph =>
                    (graph.nodes || []).filter(node => node.type === 'sprite'))];
            for (const appearance of appearances) {
                if (appearance.appearance === 'asset' && appearance.assetId === assetId) {
                    appearance.appearance = 'inherit';
                    delete appearance.assetId;
                }
            }
        }
    }
    return result;
}

/** Compare plain JSON documents without depending on object property order. */
export function sameDocument(left, right) {
    if (left === right) return true;
    if (!left || !right || typeof left !== 'object' || typeof right !== 'object'
        || Array.isArray(left) !== Array.isArray(right)) return false;
    if (Array.isArray(left) && left.length !== right.length) return false;
    const keys = Object.keys(left);
    return keys.length === Object.keys(right).length && keys.every(key =>
        Object.prototype.hasOwnProperty.call(right, key) && sameDocument(left[key], right[key]));
}
