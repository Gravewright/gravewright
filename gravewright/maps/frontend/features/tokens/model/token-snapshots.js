/** Reconcile acknowledgements with snapshots received while their command was pending. */
export function createTokenSnapshots() {
    let current = [];
    const pending = new Set();
    function accept(rows) {
        const ids = new Set(rows.map(token => token.id));
        for (const request of pending)
            for (const token of current)
                if (!ids.has(token.id)) request.removed.add(token.id);
        current = rows;
        return rows;
    }
    return {
        accept,
        begin() {
            const request = { original: new Map(current.map(token => [token.id, token.version])), removed: new Set() };
            pending.add(request);
            return request;
        },
        confirm(request, rows) {
            pending.delete(request);
            const latest = new Map(current.map(token => [token.id, token]));
            const ids = new Set(rows.map(token => token.id));
            const merged = rows.flatMap(token => {
                const fresh = latest.get(token.id);
                if (!fresh && request.removed.has(token.id)) return [];
                return [fresh && fresh.version > token.version ? fresh : token];
            });
            for (const token of current) {
                const original = request.original.get(token.id);
                if (!ids.has(token.id) && (original === undefined || token.version > original))
                    merged.push(token);
            }
            return accept(merged);
        },
        cancel(request) { pending.delete(request); },
        clear() { current = []; pending.clear(); },
    };
}
