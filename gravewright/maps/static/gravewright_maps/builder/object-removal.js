/** Atomic object deletion and native component reference reconciliation. */
import { torchChildren, torchOwner } from './torch-model.js';
const clone = value => structuredClone(value);

export function removeObject(document, kind, id) {
    const removals = new Map([[kind, new Set([id])]]), dissolved = new Set(), detached = [];
    const remove = ref => {
        if (!removals.has(ref.kind)) removals.set(ref.kind, new Set());
        removals.get(ref.kind).add(ref.id);
    };
    const target = document[kind]?.find(row => row.id === id), owner = torchOwner(document, kind, id);
    if (kind === 'decorations' && target?.torch) for (const ref of torchChildren(document, target)) remove(ref);
    if (owner && kind === 'lights') {
        dissolved.add(owner.id);
        for (const ref of torchChildren(document, owner)) remove(ref);
    } else if (owner) detached.push({ owner, field: kind === 'particles' ? 'particleId' : 'shaderId' });
    const replacements = [], removedLights = removals.get('lights'),removedShaders=removals.get('shaders');
    if (removedLights?.size||removedShaders?.size) for (const element of [...document.doors || [], ...document.decorations || [], ...document.regions || []]) {
        if (removals.get('decorations')?.has(element.id) || dissolved.has(element.id)) continue;
        for (const [event, original] of Object.entries(element.blueprint?.graphs || {})) {
            // Removing an action keeps the execution path connected to its
            // continuation, including condition branches and adjacent actions.
            const removed = original.nodes.filter(node => node.type === 'light' && removedLights?.has(node.targetId)||node.type==='shaderControl'&&removedShaders?.has(node.targetId));
            if (!removed.length) continue;
            const graph = clone(original);
            for (const node of removed) {
                if (element.blueprint.version === 2) {
                    const continuations = graph.edges.filter(edge => edge.kind !== 'data' && edge.from === node.id && edge.output === 'next');
                    const edges = [], seen = new Set();
                    function append(edge) {
                        const key = JSON.stringify([edge.kind, edge.from, edge.output, edge.to, edge.input]);
                        if (!seen.has(key)) { seen.add(key); edges.push(edge); }
                    }
                    for (const edge of graph.edges) {
                        if (edge.from === node.id) continue;
                        if (edge.to === node.id) {
                            if (edge.kind === 'data') continue;
                            for (const continuation of continuations) append({ ...edge, to: continuation.to, kind: 'execution' });
                        } else append(edge);
                    }
                    graph.edges = edges;
                } else {
                    const incoming = graph.edges.filter(edge => edge.to === node.id);
                    const continuation = graph.edges.find(edge => edge.from === node.id && edge.output === 'next');
                    graph.edges = graph.edges.filter(edge => edge.from !== node.id && edge.to !== node.id);
                    if (continuation) for (const edge of incoming) graph.edges.push({ ...edge, to: continuation.to });
                }
                graph.nodes = graph.nodes.filter(item => item.id !== node.id);
            }
            if (graph.edges.length > 64) throw new Error('The blueprint has too many nodes or connections.');
            replacements.push({ graphs: element.blueprint.graphs, event, graph });
        }
    }
    // A failed graph rewrite must leave the light and every element untouched.
    for (const [type, ids] of removals) if (document[type]) document[type] = document[type].filter(item => !ids.has(item.id));
    for (const element of document.decorations || []) if (dissolved.has(element.id)) {
        if (element.torch.state === 'on') element.rotation = (((element.rotation || 0) + 90) % 360 + 360) % 360;
        delete element.torch; delete element.blueprint;
    }
    for (const { owner: parent, field } of detached) delete parent.torch[field];
    for (const { graphs, event, graph } of replacements) graphs[event] = graph;
}
