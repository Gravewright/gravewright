/** Project disposable native deltas onto a copy of the authored map. */
export function projectTestDocument(source, result) {
    const document = structuredClone(source), cell = document.cellSize;
    const items = new Map(['floors', 'walls', 'doors', 'decorations', 'lights', 'particles', 'shaders', 'regions']
        .flatMap(kind => (document[kind] || []).map(item => [item.id, { kind, item }])));
    for (const change of result?.changes?.elements || []) {
        const entry = items.get(change.sourceId || result.sourceIds?.[change.id]);
        if (!entry) continue;
        if (change.after === null) {
            document[entry.kind] = document[entry.kind].filter(item => item.id !== entry.item.id);
            items.delete(entry.item.id);
            continue;
        }
        if (!change.after) continue;
        const { kind, item } = entry, data = change.after.data, before = change.before?.data || {};
        if (kind === 'doors') {
            item.state = data.door_state;
            for (const key of ['x1', 'y1', 'x2', 'y2', 'thickness']) if (Number.isFinite(data[key])) item[key] = data[key] / cell;
        }
        if (item.lever) item.lever.state = data.lever?.state || item.lever.state;
        if (item.torch) Object.assign(item.torch, { state: data.torch?.state || item.torch.state, lit: data.torch?.lit ?? item.torch.lit });
        item.testHidden = ['gm', 'gm-image-layer'].includes(data.layer);
        if (['doors', 'decorations'].includes(kind)) {
            const config = data.sprite || item.blueprint?.states?.[item.torch?.state || item.lever?.state || item.state] || {};
            item.testAppearance = {
                visible: !item.testHidden && config.appearance !== 'hidden' && (kind !== 'doors' || item.state !== 'open' || config.appearance === 'asset'),
                assetId: config.appearance === 'asset' ? config.assetId : data.asset_id || item.assetId,
            };
        }
        if (['floors', 'walls'].includes(kind)) {
            if (data.surface?.materialId) item.assetId = data.surface.materialId;
            const x = data.x / cell, y = data.y / cell, bx = before.x / cell, by = before.y / cell;
            if ([x, y, bx, by].every(Number.isFinite)) item.testTransform = `translate(${x} ${y}) rotate(${(data.rotation || 0) - (before.rotation || 0)}) scale(${(data.scale || 1) / (before.scale || 1)}) translate(${-bx} ${-by})`;
        } else if (kind === 'decorations') {
            const width = data.natural_width * data.scale / cell, height = data.natural_height * data.scale / cell;
            if (Number.isFinite(width) && Number.isFinite(height)) Object.assign(item, { x: data.x / cell - width / 2, y: data.y / cell - height / 2, width, height,
                rotation: (data.rotation || 0) - (item.torch?.state === 'on' ? 90 : 0) });
        } else if (['lights', 'particles', 'shaders'].includes(kind)) {
            for (const key of Object.keys(item)) if (Object.hasOwn(data, key) && !['id', 'layerId', 'x', 'y'].includes(key)) item[key] = structuredClone(data[key]);
            item.x = data.x / cell; item.y = data.y / cell;
            if (kind === 'lights') { item.brightRadius = data.bright_radius; item.dimRadius = data.dim_radius; }
            item.testNative = true;
        } else if (kind === 'regions') {
            item.enabled = data.enabled;
            for (const key of ['x', 'y', 'width', 'height']) if (Number.isFinite(data.geometry?.[key])) item[key] = data.geometry[key] / cell;
            item.testRegion = true;
        }
    }
    return document;
}

