/** Open a linked project or adopt native scene geometry with retry-safe receipts. */
export function createSceneBuilder({ campaignId, post, navigate, signal }) {
    const attempts = new Map();
    let pending;
    return async function open(map) {
        if (pending || signal?.aborted) return false;
        if (map.builderProjectId) { navigate(map.builderProjectId); return; }
        let attempt = attempts.get(map.id);
        if (!attempt || attempt.expected_scene_version !== map.version) {
            attempt = { request_id: crypto.randomUUID(), expected_scene_version: map.version };
            attempts.set(map.id, attempt);
        }
        pending = map.id;
        try {
            const result = await post(`/api/containers/${encodeURIComponent(campaignId)}/map-builder/scenes/${encodeURIComponent(map.id)}/adopt`, attempt, { signal, timeoutMs: null });
            if (signal?.aborted) return false;
            attempts.delete(map.id);
            navigate(result.project.id);
        } catch (error) {
            // Definitive refusals end this logical operation. An uncertain reply
            // retains its body and UUID so a retry cannot create another project.
            if (error.status >= 400 && error.status < 500 && error.status !== 408 && error.status !== 429) attempts.delete(map.id);
            if (!signal?.aborted && error.name !== 'AbortError') throw error;
            return false;
        } finally { pending = undefined; }
    };
}
