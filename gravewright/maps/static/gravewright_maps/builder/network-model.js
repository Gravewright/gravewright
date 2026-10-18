/** Derive a read-only overview from the same element-owned graphs the editor saves. */
export function sceneNetwork(catalog) {
    const nodes = new Map(), edges = new Map();
    const keyFor = (resource, id) => resource === 'element' ? id : `${resource}:${id}`;
    const kinds = { elements: 'element', lights: 'light', sounds: 'sound', assets: 'asset', handouts: 'handout', users: 'user' };
    for (const [collection, resource] of Object.entries(kinds)) {
        for (const item of catalog[collection] || []) nodes.set(keyFor(resource, item.id), { ...item, id: keyFor(resource, item.id), resourceId: item.id, resource, missing: false,
            editable: resource === 'element' && (item.editable ?? ['door', 'lever', 'torch', 'region'].includes(item.kind)),
            events: Object.keys(item.blueprint?.graphs || {}), references: 0 });
    }
    function link(owner, target, resource, event, kind) {
        if (!target) return;
        const resourceId = target;
        target = keyFor(resource, target);
        if (!nodes.has(target)) nodes.set(target, { id: target, resourceId, resource, missing: true, editable: false, events: [], references: 0 });
        const key = JSON.stringify([owner.id, target, kind]);
        if (!edges.has(key)) edges.set(key, { id: key, from: owner.id, to: target, kind, events: [] });
        const edge = edges.get(key);
        if (!edge.events.includes(event)) edge.events.push(event);
        nodes.get(target).references++;
    }
    for (const owner of catalog.elements || []) {
        for (const [state, appearance] of Object.entries(owner.blueprint?.states || {})) {
            if (appearance.appearance === 'asset') link(owner, appearance.assetId, 'asset', `state:${state}`, 'appearance');
        }
        for (const [event, graph] of Object.entries(owner.blueprint?.graphs || {})) {
            const byId = new Map(graph.nodes.map(node => [node.id, node])), executed = new Set();
            const visit = id => {
                if (executed.has(id)) return;
                executed.add(id);
                for (const edge of graph.edges) if (edge.kind !== 'data' && edge.from === id) visit(edge.to);
            };
            const entry = graph.nodes.find(node => node.type === 'event');
            if (entry) visit(entry.id);
            const needed = new Set(executed), pending = [...executed];
            while (pending.length) {
                const id = pending.pop();
                for (const edge of graph.edges) if (edge.kind === 'data' && edge.to === id && !needed.has(edge.from)) {
                    needed.add(edge.from); pending.push(edge.from);
                }
            }
            for (const id of needed) {
                const node = byId.get(id); if (!node) continue;
                const targetConnected = graph.edges.some(edge => edge.kind === 'data' && edge.to === id && edge.input === 'target');
                if (node.type === 'reference') link(owner, node.targetId, 'element', event, 'reference');
                if (node.type === 'elementGroup') for (const target of node.targetIds) link(owner, target, node.memberType, event, 'group');
                if (node.type === 'lightReference' || node.type === 'light' && !targetConnected) link(owner, node.targetId, 'light', event, 'light');
                if (node.type === 'soundReference' || ['sound', 'soundControl'].includes(node.type) && !targetConnected) link(owner, node.trackId, 'sound', event, 'sound');
                if (node.type === 'teleport') link(owner, node.destinationId, 'element', event, 'teleport');
                if (node.assetId) link(owner, node.assetId, 'asset', event, 'appearance');
                if (node.type === 'showHandout') link(owner, node.journalId, 'handout', event, 'handout');
                if (node.audience?.scope === 'users') for (const target of node.audience.userIds) link(owner, target, 'user', event, 'audience');
                if (node.type === 'emitEvent' && executed.has(id)) {
                    const signal = `signal:${node.name}`;
                    if (node.scope === 'scene') for (const recipient of catalog.elements || []) {
                        if (Object.hasOwn(recipient.blueprint?.graphs || {}, signal)) link(owner, recipient.id, 'element', event, 'signal');
                    } else {
                        const connection = graph.edges.find(edge => edge.kind === 'data' && edge.to === node.id && edge.input === 'target');
                        const reference = connection && byId.get(connection.from);
                        const targets = !connection ? [owner.id] : reference?.type === 'reference' ? [reference.targetId]
                            : reference?.type === 'elementGroup' ? reference.targetIds : [];
                        for (const target of targets) {
                            const recipient = nodes.get(target);
                            if (recipient?.events.includes(signal)) link(owner, target, 'element', event, 'signal');
                        }
                    }
                }
            }
        }
    }
    const sources = new Set([...edges.values()].map(edge => edge.from));
    return { nodes: [...nodes.values()].filter(node => node.editable || node.references || sources.has(node.id)), edges: [...edges.values()] };
}

/** Bound rendered cards without discarding searchable source data. */
export function networkPage(network, { query = '', page = 0, pageSize = 40, problems = false } = {}) {
    pageSize = Number.isFinite(pageSize) ? Math.max(1, Math.min(100, Math.trunc(pageSize))) : 40;
    page = Number.isFinite(page) ? Math.max(0, Math.trunc(page)) : 0;
    const text = query.trim().toLocaleLowerCase();
    const missing = new Set(network.nodes.filter(node => node.missing).map(node => node.id));
    const affected = new Set(network.edges.filter(edge => missing.has(edge.to)).map(edge => edge.from));
    const matches = network.nodes.filter(node => (!problems || node.missing || affected.has(node.id))
        && (!text || `${node.name || ''} ${node.id} ${node.kind || node.resource} ${node.events.join(' ')}`.toLocaleLowerCase().includes(text)));
    const pages = Math.max(1, Math.ceil(matches.length / pageSize)), current = Math.max(0, Math.min(pages - 1, page));
    const nodes = matches.slice(current * pageSize, (current + 1) * pageSize);
    const ids = new Set(nodes.map(node => node.id));
    return { nodes, edges: network.edges.filter(edge => ids.has(edge.from) && ids.has(edge.to)), pages, page: current,
        total: matches.length, outgoing: network.edges.filter(edge => ids.has(edge.from) && !ids.has(edge.to)) };
}
