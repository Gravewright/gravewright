/** Torch composition references the existing authored native light and effects. */
import { defaultBlueprint, blueprintAppearance } from './blueprint-model.js';
const components = Object.freeze({ lightId: 'lights', particleId: 'particles', shaderId: 'shaders' });

export function torchChildren(document, decoration) {
    const parent = typeof decoration === 'string' ? document.decorations?.find(row => row.id === decoration) : decoration;
    if (!parent?.torch) return [];
    return Object.entries(components).flatMap(([field, kind]) => {
        const id = parent.torch[field];
        return id && document[kind]?.some(row => row.id === id) ? [{ kind, id }] : [];
    });
}

export function torchOwner(document, kind, id) {
    const field = Object.keys(components).find(key => components[key] === kind);
    return field ? document.decorations?.find(row => row.torch?.[field] === id) ?? null : null;
}

/** Selecting a parent includes each component once; direct component editing stays possible. */
export function expandTorchSelection(document, refs) {
    if (!Array.isArray(refs)) return [];
    const result = [], seen = new Set();
    for (const ref of refs) {
        const children = ref?.kind === 'decorations' ? torchChildren(document, ref.id) : [];
        for (const entry of [ref, ...children]) {
            const key = `${entry?.kind}:${entry?.id}`;
            if (!seen.has(key)) { seen.add(key); result.push(entry); }
        }
    }
    return result;
}

/** Bind existing components without changing their independent native settings. */
export function attachTorch(document, decorationId, configuration) {
    const parent = document.decorations?.find(row => row.id === decorationId);
    if (!parent || !parent.assetId || parent.lever || !configuration || typeof configuration !== 'object' || Array.isArray(configuration)
        || Object.keys(configuration).some(key => !['state', 'lit', ...Object.keys(components)].includes(key))) return false;
    const torch = { state: 'off', lit: true, ...structuredClone(configuration) };
    if (!['off', 'on'].includes(torch.state) || typeof torch.lit !== 'boolean' || !torch.lightId) return false;
    const layer = document.layers?.find(row => row.id === parent.layerId);
    if (!layer || layer.locked || layer.visible === false) return false;
    for (const [field, kind] of Object.entries(components)) {
        if (!Object.hasOwn(torch, field)) continue;
        const item = document[kind]?.find(row => row.id === torch[field]), owner = torchOwner(document, kind, torch[field]);
        if (typeof torch[field] !== 'string' || !item || item.layerId !== parent.layerId || owner && owner.id !== parent.id) return false;
    }
    if (parent.blueprint && parent.blueprint.kind !== 'torch') return false;
    if (JSON.stringify(parent.torch) === JSON.stringify(torch)) return false;
    parent.torch = torch;
    parent.blueprint ||= defaultBlueprint('torch');
    return true;
}

/** Preview the mechanism and flame without overwriting authored positions or enabled flags. */
export function torchComponentState(document, kind, item) {
    if (item.testNative) return item;
    const owner = torchOwner(document, kind, item.id);
    if (!owner) return item;
    const result = { ...item, enabled: item.enabled !== false && owner.torch.lit && blueprintAppearance(owner).visible };
    if (owner.torch.state === 'on') {
        const cx = owner.x + owner.width / 2, cy = owner.y + owner.height / 2;
        result.x = cx - (item.y - cy); result.y = cy + (item.x - cx);
        result.rotation = ((item.rotation ?? 0) + 90) % 360;
    }
    return result;
}

/** Invert only the mechanism transform for a component position edited on the canvas. */
export function torchSourcePoint(document, kind, id, point) {
    const owner = torchOwner(document, kind, id);
    if (owner?.torch.state !== 'on') return { x: point.x, y: point.y };
    const cx = owner.x + owner.width / 2, cy = owner.y + owner.height / 2;
    return { x: cx + (point.y - cy), y: cy - (point.x - cx) };
}
