/** Merge an editable draft with a newly imported scene without browser state. */
const missing = Symbol('missing');
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const own = (value, key) => value !== missing && Object.hasOwn(value, key) ? value[key] : missing;
const pointer = (path, key) => `${path}/${String(key).replaceAll('~', '~0').replaceAll('/', '~1')}`;
const define = (value, key, entry) => Object.defineProperty(value, key, {
    value: entry, enumerable: true, configurable: true, writable: true,
});

function copy(value) {
    if (Array.isArray(value)) return value.map(copy);
    if (!record(value)) return value;
    const result = {};
    for (const key of Object.keys(value)) define(result, key, copy(value[key]));
    return result;
}

function equal(left, right) {
    if (left === right) return true;
    if (left === missing || right === missing || !record(left) && !Array.isArray(left)
        || !record(right) && !Array.isArray(right) || Array.isArray(left) !== Array.isArray(right)) return false;
    if (Array.isArray(left)) return left.length === right.length && left.every((entry, index) => equal(entry, right[index]));
    const keys = Object.keys(left);
    return keys.length === Object.keys(right).length && keys.every(key => Object.hasOwn(right, key) && equal(left[key], right[key]));
}

function indexed(array, key) {
    const entries = new Map();
    for (const entry of array) {
        if (!record(entry) || !Object.hasOwn(entry, key)) return null;
        const id = entry[key];
        if (!(typeof id === 'string' || typeof id === 'number' && Number.isFinite(id))
            || entries.has(id)) return null;
        entries.set(id, entry);
    }
    return entries;
}

/** Combine inserted rows around their shared anchors, retaining both sides' rows. */
function weave(primary, secondary) {
    const present = new Set(primary), before = new Map();
    let next = null;
    for (let index = secondary.length - 1; index >= 0; index--) {
        const id = secondary[index];
        if (present.has(id)) next = id;
        else {
            if (!before.has(next)) before.set(next, []);
            before.get(next).push(id);
        }
    }
    const result = [];
    for (const id of primary) {
        result.push(...(before.get(id) || []).reverse(), id);
    }
    result.push(...(before.get(null) || []).reverse());
    return result;
}

/**
 * Three-way merge JSON project documents using the last saved source as base.
 * Rows in arrays with unique IDs merge by identity; the top-level asset catalog
 * uses its unique `assetId` instead. Other geometry/reference arrays without IDs
 * remain atomic. Authored strings and IDs are copied verbatim.
 *
 * Conflicts are JSON Pointer paths (row IDs replace array indices; `$order`
 * denotes incompatible ordering). The result retains local conflicting values
 * by default. Callers must resolve conflicts before applying that result.
 * `preferRemote` also reports conflicts but retains remote values, allowing
 * already accepted scene changes to be carried through older undo snapshots.
 * Inputs and every returned object remain independent; own special JSON keys
 * are copied as data properties rather than invoking prototype setters.
 */
export function mergeSceneProject(baseDocument, localDocument, remoteDocument, { preferRemote = false } = {}) {
    const conflicts = new Set();
    function conflict(base, local, remote, path) {
        conflicts.add(path);
        return copy(preferRemote ? remote : local);
    }
    function order(base, local, remote, merged, path) {
        const kept = new Set(merged.keys()), localIds = new Set(local.keys()), remoteIds = new Set(remote.keys());
        // Insertions get anchored separately so an addition does not turn an
        // otherwise independent reorder into a conflict.
        const shared = new Set([...base.keys()].filter(id => kept.has(id) && localIds.has(id) && remoteIds.has(id)));
        const backbone = entries => [...entries.keys()].filter(id => shared.has(id));
        const baseOrder = backbone(base), localOrder = backbone(local), remoteOrder = backbone(remote);
        let selected;
        if (equal(localOrder, remoteOrder) || equal(remoteOrder, baseOrder)) selected = localOrder;
        else if (equal(localOrder, baseOrder)) selected = remoteOrder;
        else {
            conflicts.add(pointer(path, '$order'));
            selected = preferRemote ? remoteOrder : localOrder;
        }
        const slots = entries => {
            const result = new Map();
            let previous = null;
            for (const id of entries.keys()) {
                if (!kept.has(id)) continue;
                if (shared.has(id)) previous = id;
                else result.set(id, previous);
            }
            return result;
        };
        const localSlots = slots(local), remoteSlots = slots(remote), selectedSlots = new Map(localSlots);
        for (const [id, anchor] of remoteSlots) {
            if (localSlots.has(id) && localSlots.get(id) !== anchor) {
                conflicts.add(pointer(path, '$order'));
                if (preferRemote) selectedSlots.set(id, anchor);
            } else selectedSlots.set(id, anchor);
        }
        const groups = entries => {
            const result = new Map();
            for (const id of entries.keys()) if (selectedSlots.has(id)) {
                const anchor = selectedSlots.get(id);
                if (!result.has(anchor)) result.set(anchor, []);
                result.get(anchor).push(id);
            }
            return result;
        };
        const localGroups = groups(local), remoteGroups = groups(remote);
        const group = anchor => {
            const first = localGroups.get(anchor) || [], second = remoteGroups.get(anchor) || [];
            const firstSet = new Set(first), secondSet = new Set(second);
            if (!equal(first.filter(id => secondSet.has(id)), second.filter(id => firstSet.has(id)))) {
                conflicts.add(pointer(path, '$order'));
                return preferRemote ? weave(second, first) : weave(first, second);
            }
            return weave(first, second);
        };
        const result = group(null);
        for (const id of selected) result.push(id, ...group(id));
        return result.map(id => merged.get(id));
    }
    function merge(base, local, remote, path) {
        if (equal(local, remote)) return copy(local);
        if (equal(local, base)) return copy(remote);
        if (equal(remote, base)) return copy(local);
        // A missing row/property is a deletion, not an empty editable object.
        if (local === missing || remote === missing) return conflict(base, local, remote, path);
        if (record(local) && record(remote) && (base === missing || record(base))) {
            const result = {}, keys = new Set([...Object.keys(base === missing ? {} : base), ...Object.keys(local), ...Object.keys(remote)]);
            for (const key of keys) {
                const entry = merge(own(base, key), own(local, key), own(remote, key), pointer(path, key));
                if (entry !== missing) define(result, key, entry);
            }
            return result;
        }
        if (Array.isArray(local) && Array.isArray(remote) && (base === missing || Array.isArray(base))) {
            const key = path === '/assets' ? 'assetId' : 'id';
            const original = indexed(base === missing ? [] : base, key), draft = indexed(local, key), imported = indexed(remote, key);
            if (original && draft && imported) {
                const entries = new Map(), ids = new Set([...original.keys(), ...draft.keys(), ...imported.keys()]);
                for (const id of ids) {
                    const entry = merge(original.has(id) ? original.get(id) : missing,
                        draft.has(id) ? draft.get(id) : missing, imported.has(id) ? imported.get(id) : missing, pointer(path, id));
                    if (entry !== missing) entries.set(id, entry);
                }
                return order(original, draft, imported, entries, path);
            }
        }
        return conflict(base, local, remote, path);
    }
    return { document: merge(baseDocument, localDocument, remoteDocument, ''), conflicts: [...conflicts] };
}
