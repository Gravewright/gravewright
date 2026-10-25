/** SVG map artwork and selection overlays, with disposable artwork caches. */
import { createTerrainMaskCache } from './terrain-render.js';
import { createWallArtCache } from './wall-art.js';
import { wallJoinGeometry } from './wall-joins.js';
import { torchComponentState } from './torch-model.js';
import { blueprintAppearance } from './blueprint-model.js';
import { isNativeKind } from './native-controls.js';
import { length, wallSegments, doorDisplaySegment, objectKinds, doorRotationPoint, floorShapeRings } from './model.js';

export function ringPath(ring) {
    return ring.length ? 'M' + ring.map(([x, y]) => `${x} ${y}`).join('L') + 'Z' : '';
}

/** getView supplies only preview, grid, per-kind visibility and the solo layer. */
export function createCanvasRenderer({ root, getDocument, getView, assetById, onWallArtReady = () => {}, onError = () => {} }) {
    const $ = selector => root.querySelector(selector);
    const svgDocument = root.ownerDocument;
    const terrainMasks = createTerrainMaskCache();
    const wallPatterns = new Map([...root.querySelectorAll('[data-wall-texture]')].map(pattern => [pattern.dataset.wallTexture, pattern]));
    let disposed = false, wallMeshes = new Map(), wallMeshError;
    const layerVisible = (layer, view) => Boolean(layer?.visible && (!view.soloLayer || view.soloLayer === layer.id));
    const isSmartDecoration = item => Boolean(item?.lever || item?.torch);
    const wallArt = createWallArtCache({
        onError: (asset, cause) => onError(cause, asset),
        onReady: id => {
            if (disposed) return;
            const doc = getDocument(), view = getView();
            const items = new Map(doc.walls.filter(item => item.assetId === id).map(item => [item.id, item]));
            for (const element of $('[data-builder-walls]').children) {
                const item = items.get(element.dataset.objectId);
                if (item) element.replaceWith(objectNode('walls', item, doc, view));
            }
            onWallArtReady(id);
        },
    });
    function svg(tag, attrs = {}) {
        const element = svgDocument.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [key, value] of Object.entries(attrs)) if (value !== undefined) element.setAttribute(key, value);
        return element;
    }
    function objectNode(kind, item, doc = getDocument(), view = getView()) {
        const result = baseObjectNode(kind, item, doc, view);
        if (item.name) {
            result.setAttribute('aria-label', item.name);
            const title = svg('title', { translate: 'no' }); title.textContent = item.name; result.append(title);
        }
        if (item.testHidden) result.style.display = 'none';
        if (!item.testTransform) return result;
        const wrapper = svg('g', { transform: item.testTransform }); wrapper.append(result); return wrapper;
    }
    function baseObjectNode(kind, item, doc, view) {
        const attrs = { 'data-object-kind': kind, 'data-object-id': item.id, 'data-object-layer': item.layerId };
        if (kind === 'regions') {
            const group = svg('g', attrs);
            if (!view.preview || item.testRegion) group.append(svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height,
                fill: '#7ecabb18', stroke: item.enabled ? '#7ecabb' : '#899098', 'stroke-width': 1,
                'stroke-dasharray': '6 4', 'vector-effect': 'non-scaling-stroke' }));
            return group;
        }
        if (kind === 'floors') {
            if (item.brush?.operation === 'erase' || item.brush && !view.preview && (!view.layers.floors || !layerVisible(doc.layers.find(layer => layer.id === item.layerId), view))) return svg('g', attrs);
            const fill = item.paint?.color || (item.assetId && assetById(item.assetId) ? `url(#texture-${item.assetId}-${item.rotation || 0})` : '#49473f');
            if (item.paint) attrs.opacity = item.paint.opacity;
            if (!item.shape && !item.brush) return svg('rect', { ...attrs, x: item.x, y: item.y, width: item.width, height: item.height, fill });
            const group = svg('g', { ...attrs, 'data-builder-free-floor': '' }), defs = svg('defs');
            let shape = svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height, fill });
            if (item.brush) {
                const id = `floor-brush-${item.id}`, raster = terrainMasks.get(item, doc.cellSize);
                const mask = svg('mask', { id, maskUnits: 'userSpaceOnUse', maskContentUnits: 'userSpaceOnUse',
                    x: raster.x, y: raster.y, width: raster.width, height: raster.height, 'mask-type': 'alpha' });
                mask.append(svg('image', { href: raster.url, x: raster.x, y: raster.y, width: raster.width, height: raster.height,
                    preserveAspectRatio: 'none', 'image-rendering': 'pixelated' }));
                defs.append(mask); shape.setAttribute('mask', `url(#${id})`);
            }
            if (item.shape) {
                const id = `floor-shape-${item.id}`, mask = floorGeometryMask(item, id);
                defs.append(mask);
                const clip = svg('g', { mask: `url(#${id})` }); clip.append(shape); shape = clip;
            }
            group.append(defs, shape);
            return group;
        }
        if (kind === 'decorations') {
            const group = svg('g', attrs);
            group.setAttribute('transform', `rotate(${(item.rotation || 0) + (item.torch?.state === 'on' ? 90 : 0)} ${item.x + item.width / 2} ${item.y + item.height / 2})`);
            if (item.empty) {
                if (!view.preview) {
                    group.dataset.builderEmptyMarker = '';
                    group.append(svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height,
                        fill: '#c09a5a18', stroke: '#c09a5a', 'stroke-width': 1, 'stroke-dasharray': '5 4', 'vector-effect': 'non-scaling-stroke' }));
                    const cx = item.x + item.width / 2, cy = item.y + item.height / 2, size = Math.min(item.width, item.height) * .2;
                    group.append(svg('path', { d: `M ${cx - size} ${cy} H ${cx + size} M ${cx} ${cy - size} V ${cy + size}`,
                        stroke: '#c09a5a', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }));
                }
                return group;
            }
            const appearance = item.testAppearance || (isSmartDecoration(item) ? blueprintAppearance(item) : { visible: true, assetId: item.assetId });
            const asset = appearance.visible && assetById(appearance.assetId);
            if (asset) group.append(svg('image', { href: asset.url, x: item.x, y: item.y, width: item.width, height: item.height, preserveAspectRatio: 'xMidYMid meet' }));
            else if (!view.preview) group.append(svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height,
                fill: '#c09a5a22', stroke: '#c09a5a', 'stroke-width': .03, 'stroke-dasharray': '.15 .1' }));
            return group;
        }
        if (isNativeKind(kind)) {
            item = torchComponentState(doc, kind, item);
            const group = svg('g', attrs);
            if (!view.preview) {
                const radius = (kind === 'lights' ? Math.max(item.brightRadius, item.dimRadius) : kind === 'shaders' ? item.radius : 0)
                    * (doc.sceneGeometry?.gridSize || doc.cellSize) * (doc.sceneGeometry?.imageScale ?? 1) / doc.cellSize;
                if (radius > 0) group.append(svg('circle', { cx: item.x, cy: item.y, r: radius, fill: 'none',
                    stroke: item.color, opacity: .3, 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'pointer-events': 'none' }));
                group.append(svg('circle', { cx: item.x, cy: item.y, r: .16, fill: item.enabled ? item.color : '#899098', stroke: '#fff', 'stroke-width': .025 }));
                const mark = svg('text', { x: item.x, y: item.y, 'text-anchor': 'middle', 'dominant-baseline': 'central',
                    fill: '#10171c', 'font-size': .18, 'pointer-events': 'none' });
                mark.textContent = kind === 'lights' ? '☀' : kind === 'particles' ? '✦' : '◈'; group.append(mark);
            }
            return group;
        }
        if (item.artwork === false) {
            const group = svg('g', { ...attrs, 'data-builder-geometry-guide': kind });
            if (!view.preview) group.append(svg('line', { x1: item.x1, y1: item.y1, x2: item.x2, y2: item.y2,
                stroke: kind === 'walls' ? '#79d9c0' : '#c09a5a', 'stroke-width': 2, 'stroke-dasharray': '6 4',
                'vector-effect': 'non-scaling-stroke' }));
            return group;
        }
        if (kind === 'walls') {
            const group = svg('g', attrs);
            const size = length(item), dx = item.x2 - item.x1, dy = item.y2 - item.y1;
            const art = wallTexture(item);
            group.dataset.wallArt = art.status;
            const mesh = wallMeshes.get(item.id);
            if (mesh) {
                const strip = svg('g', { 'data-builder-wall-strip': '',
                    transform: `translate(${mesh.origin.x} ${mesh.origin.y}) rotate(${Math.atan2(mesh.direction.y, mesh.direction.x) * 180 / Math.PI})` });
                const path = mesh.polygons.map(polygon => ringPath(polygon.map(([x, y]) => [x + mesh.phase, y]))).join(' ');
                strip.append(svg('path', { d: path, fill: art.fill, 'fill-rule': 'nonzero',
                    transform: `translate(${-mesh.phase} 0)`, 'data-builder-wall-mesh': '' }));
                group.append(strip); return group;
            }
            const strip = svg('g', { 'data-builder-wall-strip': '',
                transform: `translate(${item.x1} ${item.y1}) rotate(${Math.atan2(dy, dx) * 180 / Math.PI})` });
            // Keep the texture's origin on the original wall when doors split it.
            if (size) for (const segment of wallSegments(doc, item)) {
                const from = ((segment.x1 - item.x1) * dx + (segment.y1 - item.y1) * dy) / size;
                const to = ((segment.x2 - item.x1) * dx + (segment.y2 - item.y1) * dy) / size;
                strip.append(svg('rect', { x: from, y: -item.thickness / 2, width: Math.max(0, to - from),
                    height: item.thickness, fill: art.fill }));
            }
            group.append(strip);
            return group;
        }
        const segment = doorDisplaySegment(item); if (!segment) return svg('g');
        const group = svg('g', attrs);
        const appearance = item.testAppearance || blueprintAppearance(item), doorAsset = assetById(appearance.assetId);
        if (!appearance.visible) {
            if (!view.preview) group.append(svg('line', { x1: segment.x1, y1: segment.y1, x2: segment.x2, y2: segment.y2,
                stroke: '#c09a5a', 'stroke-width': .05, 'stroke-dasharray': '.15 .1' })); return group;
        }
        const shape = svg('g', { transform: `translate(${segment.x1} ${segment.y1}) rotate(${segment.angle})` });
        if (doorAsset) shape.append(svg('image', { href: doorAsset.url, x: 0, y: -segment.thickness / 2,
            width: length(item), height: segment.thickness, preserveAspectRatio: 'none' }));
        else shape.append(svg('rect', { x: 0, y: -Math.max(.16, segment.thickness) / 2, width: length(item),
            height: Math.max(.16, segment.thickness), fill: item.state === 'locked' ? '#c38155' : '#c09a5a', stroke: '#27221b', 'stroke-width': .04 }));
        group.append(shape);
        return group;
    }
    function ensureTexturePatterns(keys, prune = false) {
        const defs = $('[data-builder-defs]');
        const existing = new Map([...defs.querySelectorAll('[data-texture]')].map(item => [item.dataset.texture, item]));
        if (prune) for (const [key, element] of existing) if (!keys.has(key)) element.remove();
        for (const key of keys) {
            const split = key.lastIndexOf('-'), id = key.slice(0, split), rotation = Number(key.slice(split + 1));
            const asset = assetById(id); if (!asset || existing.has(key)) continue;
            const pattern = svg('pattern', { id: `texture-${key}`, 'data-texture': key, width: 1, height: 1, patternUnits: 'userSpaceOnUse', patternTransform: `rotate(${rotation})` });
            pattern.append(svg('image', { href: asset.url, x: 0, y: 0, width: 1, height: 1, preserveAspectRatio: 'none' })); defs.append(pattern);
        }
    }
    function wallPatternKey(item) { return `${item.assetId}-${item.thickness}`; }
    function wallTexture(item) {
        const asset = assetById(item.assetId);
        if (!asset) return { status: 'ready', fill: '#8d8170' };
        const art = wallArt.get(asset);
        if (art.status !== 'ready') return { status: art.status, fill: '#8d8170' };
        const key = wallPatternKey(item);
        if (!wallPatterns.has(key)) {
            const bounds = art.bounds, height = item.thickness, width = height * bounds.width / bounds.height;
            const pattern = svg('pattern', { id: `wall-texture-${key}`, 'data-wall-texture': key,
                x: 0, y: -height / 2, width, height, patternUnits: 'userSpaceOnUse' });
            const crop = svg('svg', { x: 0, y: 0, width, height,
                viewBox: `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`, preserveAspectRatio: 'none', overflow: 'hidden' });
            crop.append(svg('image', { href: asset.url, x: 0, y: 0, width: art.width, height: art.height, preserveAspectRatio: 'none' }));
            pattern.append(crop); $('[data-builder-defs]').append(pattern); wallPatterns.set(key, pattern);
        }
        return { status: 'ready', fill: `url(#wall-texture-${key})` };
    }
    function floorGeometryMask(item, id) {
        const mask = svg('mask', { id, maskUnits: 'userSpaceOnUse', maskContentUnits: 'userSpaceOnUse',
            x: item.x, y: item.y, width: item.width, height: item.height, 'mask-type': 'luminance' });
        for (const ring of floorShapeRings(item)) mask.append(svg('path', { d: ringPath(ring), fill: 'white', 'fill-rule': 'evenodd' }));
        for (const ring of floorShapeRings(item, 'cuts')) mask.append(svg('path', { d: ringPath(ring), fill: 'black', 'fill-rule': 'evenodd' }));
        return mask;
    }
    function renderFloors(doc, view = getView()) {
        const children = [];
        for (const layer of doc.layers) {
            const floors = doc.floors.filter(item => item.layerId === layer.id);
            if (!floors.some(item => item.brush?.operation === 'erase')) {
                children.push(...floors.map(item => objectNode('floors', item, doc, view))); continue;
            }
            const group = svg('g', { 'data-builder-floor-layer': layer.id });
            if (!view.preview && (!view.layers.floors || !layerVisible(layer, view))) group.style.display = 'none';
            for (const item of floors) {
                if (item.brush?.operation !== 'erase') { group.append(objectNode('floors', item, doc, view)); continue; }
                if (view.preview || view.layers.floors && layerVisible(layer, view)) {
                    const id = `floor-erase-${item.id}`, raster = terrainMasks.get(item, doc.cellSize), defs = svg('defs');
                    const mask = svg('mask', { id, maskUnits: 'userSpaceOnUse', maskContentUnits: 'userSpaceOnUse',
                        x: 0, y: 0, width: doc.columns, height: doc.rows, 'mask-type': 'luminance' });
                    mask.append(svg('rect', { x: 0, y: 0, width: doc.columns, height: doc.rows, fill: 'white' }));
                    let image = svg('image', { href: raster.url, x: raster.x, y: raster.y, width: raster.width, height: raster.height,
                        preserveAspectRatio: 'none', 'image-rendering': 'pixelated', opacity: item.paint?.opacity ?? 1 });
                    if (item.shape) {
                        const clipId = `floor-shape-${item.id}`; defs.append(floorGeometryMask(item, clipId));
                        const clip = svg('g', { mask: `url(#${clipId})` }); clip.append(image); image = clip;
                    }
                    mask.append(image); defs.append(mask);
                    const previous = svg('g', { mask: `url(#${id})` }); previous.append(...group.childNodes);
                    group.append(defs, previous);
                }
                group.append(objectNode('floors', item, doc, view));
            }
            children.push(group);
        }
        $('[data-builder-floors]').replaceChildren(...children);
    }
    function render({ wallDraft } = {}) {
        const doc = getDocument(), view = getView();
        try {
            const artwork = { ...doc, walls: doc.walls.filter(wall => wall.artwork !== false) };
            wallMeshes = wallJoinGeometry(artwork, artwork.walls
                .flatMap(wall => wallSegments(doc, wall).map(span => ({ ...span, wall }))));
            wallMeshError = undefined;
        } catch (cause) {
            if (!(cause instanceof RangeError) || cause.message !== 'The map produces too many wall segments.') throw cause;
            wallMeshes = new Map();
            if (wallMeshError !== cause.message) onError(cause);
            wallMeshError = cause.message;
        }
        const used = new Set(doc.floors.map(item => item.assetId && `${item.assetId}-${item.rotation || 0}`).filter(Boolean));
        ensureTexturePatterns(used, true);
        const wallKeys = new Set(doc.walls.map(wallPatternKey));
        if (wallDraft) wallKeys.add(wallPatternKey(wallDraft));
        for (const [key, pattern] of wallPatterns) if (!wallKeys.has(key)) { pattern.remove(); wallPatterns.delete(key); }
        const layerOrder = new Map(doc.layers.map((layer, index) => [layer.id, index]));
        terrainMasks.prune(doc.floors); renderFloors(doc, view);
        for (const kind of objectKinds) if (kind !== 'floors') $('[data-builder-' + kind + ']').replaceChildren(...(doc[kind] || []).slice()
            .sort((a, b) => layerOrder.get(a.layerId) - layerOrder.get(b.layerId)).map(item => objectNode(kind, item, doc, view)));
        for (const element of root.querySelectorAll('[data-builder-paper],[data-builder-grid],[data-builder-outline]')) {
            element.setAttribute('width', doc.columns); element.setAttribute('height', doc.rows);
        }
        $('[data-builder-paper]').setAttribute('fill', doc.background);
        const backgroundAsset = assetById(doc.backgroundImage?.assetId);
        const width = doc.sceneGeometry ? doc.sceneGeometry.width / doc.cellSize : doc.columns;
        const height = doc.sceneGeometry ? doc.sceneGeometry.height / doc.cellSize : doc.rows;
        $('[data-builder-background-image]').replaceChildren(...(backgroundAsset ? [svg('image', { href: backgroundAsset.url,
            x: 0, y: 0, width, height, preserveAspectRatio: 'none' })] : []));
        $('[data-builder-outline]').setAttribute('width', width); $('[data-builder-outline]').setAttribute('height', height);
        const grid = $('[data-builder-defs]').querySelector('#builder-grid');
        if (grid) {
            const scale = doc.sceneGeometry?.imageScale ?? 1;
            const size = (doc.sceneGeometry?.gridSize || doc.cellSize) * scale / doc.cellSize;
            grid.setAttribute('width', size); grid.setAttribute('height', size);
            grid.setAttribute('x', (doc.sceneGeometry?.gridOffsetX || 0) * scale / doc.cellSize);
            grid.setAttribute('y', (doc.sceneGeometry?.gridOffsetY || 0) * scale / doc.cellSize);
            grid.querySelector('path').setAttribute('d', `M ${size} 0 L 0 0 0 ${size}`);
        }
        $('[data-builder-background-name]').textContent = backgroundAsset ? backgroundAsset.name : '';
        $('[data-builder-background-remove]').hidden = !doc.backgroundImage;
        $('[data-builder-grid]').style.display = view.grid && !view.preview ? '' : 'none';
        $('[data-builder-outline]').style.display = view.preview ? 'none' : '';
        return doc;
    }
    function renderSelection(refs, scale) {
        const doc = getDocument();
        const container = $('[data-builder-selection]'); container.replaceChildren();
        for (const ref of refs) {
            const source = doc[ref.kind]?.find(item => item.id === ref.id), item = isNativeKind(ref.kind) ? torchComponentState(doc, ref.kind, source) : source;
            const style = { fill: 'none', stroke: '#e4bf76', 'stroke-width': 2, 'stroke-dasharray': '5 3', 'vector-effect': 'non-scaling-stroke' };
            if (ref.kind === 'decorations' && Number.isFinite(item.presenceRadius)) {
                const cx = item.x + item.width / 2, cy = item.y + item.height / 2;
                container.append(svg('circle', { cx, cy, r: item.presenceRadius, fill: 'none', stroke: '#e4bf76',
                    'stroke-width': 2, 'vector-effect': 'non-scaling-stroke', 'pointer-events': 'none',
                    'data-builder-presence-area': item.id }));
                if (refs.length === 1) container.append(svg('circle', { cx: cx + item.presenceRadius, cy,
                    r: 6 / scale, fill: '#e4bf76', stroke: '#253038', 'stroke-width': 1,
                    'vector-effect': 'non-scaling-stroke', 'pointer-events': 'all', cursor: 'ew-resize',
                    'data-builder-area-handle': item.id }));
            }
            if (ref.kind === 'doors' || ref.kind === 'walls') {
                container.append(svg('line', { x1: item.x1, y1: item.y1, x2: item.x2, y2: item.y2, ...style }));
                if (ref.kind === 'doors' && refs.length === 1) {
                    const anchor = doorRotationPoint(item);
                    container.append(svg('circle', { cx: anchor.x, cy: anchor.y, r: 5 / scale,
                        fill: '#e4bf76', stroke: '#253038', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke',
                        'data-builder-door-anchor': item.rotationAnchor ?? 'center' }));
                }
            } else if (isNativeKind(ref.kind)) {
                container.append(svg('circle', { cx: item.x, cy: item.y, r: .22, ...style }));
            } else {
                const shape = svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height, ...style });
                if (ref.kind === 'decorations') shape.setAttribute('transform', `rotate(${(item.rotation || 0) + (item.torch?.state === 'on' ? 90 : 0)} ${item.x + item.width / 2} ${item.y + item.height / 2})`);
                container.append(shape);
            }
        }
        return container;
    }
    function renderLayerVisibility() {
        const doc = getDocument(), view = getView();
        const layers = new Map(doc.layers.map(layer => [layer.id, layer]));
        for (const kind of objectKinds) {
            $('[data-builder-' + kind + ']').style.display = view.layers[kind] || view.preview ? '' : 'none';
            const items = new Map((doc[kind] || []).map(item => [item.id, item]));
            for (const element of $('[data-builder-' + kind + ']').querySelectorAll('[data-object-id], [data-builder-floor-layer]')) {
                const item = items.get(element.dataset.objectId);
                const layer = layers.get(item?.layerId || element.dataset.builderFloorLayer);
                element.style.display = item?.testHidden ? 'none' : view.preview || !layer || layerVisible(layer, view) ? '' : 'none';
            }
        }
        $('[data-builder-selection]').style.display = view.preview ? 'none' : '';
    }
    return { objectNode, ensureTexturePatterns, renderFloors, render, renderSelection, renderLayerVisibility,
        dispose() {
            if (disposed) return;
            disposed = true;
            terrainMasks.dispose(); wallArt.dispose(); wallPatterns.clear(); wallMeshes.clear();
        },
    };
}
