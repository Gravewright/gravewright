/** Remember transient, authoritative teleports for this one mounted token workspace. */
export function createTokenTeleports() {
    const markers = new Map(), versions = new Map();
    return {
        apply(rows, teleports = []) {
            const current = new Map(rows.map(token => [token.id, token]));
            for (const id of versions.keys()) {
                if (!current.has(id)) {
                    versions.delete(id);
                    markers.delete(id);
                }
            }
            for (const token of rows)
                versions.set(token.id, Math.max(versions.get(token.id) ?? 0, token.version));
            for (const marker of Array.isArray(teleports) ? teleports : []) {
                const token = marker && current.get(marker.id);
                if (token && Number.isSafeInteger(marker.version) && marker.version > 0 &&
                    marker.version === token.version && marker.version === versions.get(marker.id))
                    markers.set(marker.id, Math.max(markers.get(marker.id) ?? 0, marker.version));
            }
            return rows.map(token => ({ ...token, teleportVersion: markers.get(token.id) ?? 0 }));
        },
        clear() {
            markers.clear();
            versions.clear();
        },
    };
}
