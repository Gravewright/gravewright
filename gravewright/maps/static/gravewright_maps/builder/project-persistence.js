import { createAutosave } from './autosave.js';
import { clone, normalizeDocument } from './model.js';

function draftKeys(campaignId) {
    const legacy = 'gravewright.map-builder.draft.' + campaignId;
    return { legacy, prefix: legacy + '.', latest: legacy + '.latest' };
}

/** Recover the selected project's draft without replacing unreadable storage. */
export function recoverProjectDraft({ campaignId, projectId, folderId, storage }) {
    const keys = draftKeys(campaignId);
    try {
        storage ??= globalThis.sessionStorage;
        const legacy = JSON.parse(storage.getItem(keys.legacy));
        if ([1, 2, 3].includes(legacy?.document?.schemaVersion) && typeof legacy.id === 'string') {
            if (!storage.getItem(keys.prefix + legacy.id)) storage.setItem(keys.prefix + legacy.id, JSON.stringify(legacy));
            if (!storage.getItem(keys.latest)) storage.setItem(keys.latest, legacy.id);
            storage.removeItem(keys.legacy);
        }
        const draft = JSON.parse(storage.getItem(keys.prefix + (projectId || storage.getItem(keys.latest))));
        if ([1, 2, 3].includes(draft?.document?.schemaVersion)
            && (projectId ? draft.id === projectId : (draft.folderId || null) === folderId)) {
            const document = normalizeDocument(draft.document);
            const saved = draft.saved ? JSON.stringify(normalizeDocument(JSON.parse(draft.saved))) : '';
            return { recovered: { ...draft, document, saved, pending: new Map(draft.pending || []) } };
        }
    } catch (cause) {
        if (cause instanceof TypeError) return { recoveryError: cause.message };
    }
    return {};
}

/** Page-owned transport; cancellation and CSRF lifetime end with the workspace. */
export function createProjectApi({ base, signal, t, csrfUrl = '/__gravewright/csrf', fetch: request = globalThis.fetch }) {
    let csrf;
    return async function api(path = '', body, method = body ? 'POST' : 'GET') {
        if (body && !csrf) {
            const response = await request(csrfUrl, { credentials: 'same-origin', cache: 'no-store', signal });
            if (!response.ok) {
                const cause = new Error(t('Request failed ({status}).', { status: response.status })); cause.status = response.status; throw cause;
            }
            csrf = await response.json();
        }
        const response = await request(path.startsWith('/api/') ? path : base + path, {
            method, credentials: 'same-origin', cache: 'no-store', signal,
            headers: { ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
                ...(body ? { [csrf.header]: csrf.token } : {}) },
            ...(body ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}),
        });
        let result;
        try { result = await response.json(); } catch {
            const cause = new Error(t('Request failed ({status}).', { status: response.status })); cause.retryable = true; throw cause;
        }
        if (!response.ok) {
            const cause = new Error(t(result.error || 'Request failed ({status}).', { status: response.status }));
            cause.status = response.status; cause.conflict = response.status === 409; throw cause;
        }
        return result;
    };
}

/** Own project receipts, recoverable drafts and the serialized save queue.
 * UI callbacks receive acknowledgements; they never replace the current draft.
 */
export function createProjectPersistence({ state, campaignId, api, canSave, onSaved = () => {}, onState = () => {},
    storage, autosaveOptions = {} }) {
    const keys = draftKeys(campaignId);
    let queue, epoch = 0, disposed = false, discarded = false, write, flushing = false;
    const dirty = () => state.saved !== JSON.stringify(state.document);
    const projectKey = document => JSON.stringify([state.id, state.folderId, document]);

    function rememberDraft() {
        try {
            const target = storage ?? globalThis.sessionStorage, key = keys.prefix + state.id;
            if (!discarded && (dirty() || state.pending.size || state.saveAttempt || state.assetRemovals.length)) {
                target.setItem(key, JSON.stringify({ ...state, assets: [], projects: [], pending: [...state.pending] }));
                target.setItem(keys.latest, state.id);
            } else {
                target.removeItem(key);
                if (target.getItem(keys.latest) === state.id) target.removeItem(keys.latest);
            }
        } catch { /* No destructive action depends on browser storage succeeding. */ }
    }

    function updateDrafts(update) {
        try {
            const target = storage ?? globalThis.sessionStorage;
            for (const key of Object.keys(target).filter(key => key.startsWith(keys.prefix) && key !== keys.latest)) {
                try {
                    const draft = JSON.parse(target.getItem(key));
                    if (!draft?.document) continue;
                    update(draft); target.setItem(key, JSON.stringify(draft));
                } catch { /* Preserve unreadable drafts for recovery. */ }
            }
        } catch { /* Browser storage may be unavailable; current work stays in memory. */ }
    }

    async function operation(path, payload) {
        const generation = epoch;
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(payload)));
        if (disposed || generation !== epoch) throw new DOMException('Project persistence was disposed.', 'AbortError');
        const key = path + ':' + Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
        if (!state.pending.has(key)) state.pending.set(key, crypto.randomUUID());
        rememberDraft();
        try {
            const result = await api(path, { ...payload, request_id: state.pending.get(key) });
            if (disposed || generation !== epoch) return result;
            state.pending.delete(key); rememberDraft(); return result;
        } catch (cause) {
            if (!disposed && generation === epoch && (cause.status === 400 || cause.conflict)) {
                state.pending.delete(key); rememberDraft();
            }
            throw cause;
        }
    }

    function start() {
        queue?.dispose(); disposed = false;
        const generation = ++epoch;
        queue = createAutosave({
            ...autosaveOptions,
            initialKey: state.version && state.saved ? projectKey(JSON.parse(state.saved)) : null,
            pendingSnapshot: state.saveAttempt,
            read: () => ({ key: projectKey(state.document), payload: {
                id: state.id, expected_version: state.version, folder_id: state.folderId, document: state.document,
            } }),
            canSave: () => !disposed && !state.recoveryConflict && canSave({ flushing }),
            save: snapshot => {
                const job = (async () => {
                    const { id, ...payload } = snapshot.payload;
                    state.saveAttempt = clone(snapshot); rememberDraft();
                    let result;
                    try { result = await operation('/projects/' + id, payload); }
                    catch (cause) {
                        if ((cause.status === 400 || cause.conflict) && !disposed && generation === epoch && state.id === id) {
                            state.saveAttempt = null; rememberDraft();
                        }
                        throw cause;
                    }
                    if (disposed || generation !== epoch || state.id !== id) return result.project;
                    state.version = result.project.version;
                    state.saved = JSON.stringify(payload.document);
                    state.saveAttempt = null;
                    state.projects = [{ id, name: result.project.document.name, version: state.version, updatedAt: result.project.updatedAt },
                        ...state.projects.filter(item => item.id !== id)];
                    onSaved(result.project); rememberDraft();
                    return result.project;
                })();
                write = job;
                return job.finally(() => { if (write === job) write = null; });
            },
            onState: value => {
                if (disposed || generation !== epoch) return;
                onState(value); rememberDraft();
            },
        });
    }

    return {
        start, operation, dirty, rememberDraft, updateDrafts,
        schedule() { queue?.schedule(); },
        retry() { queue.retry(); },
        async flush() {
            flushing = true;
            try { return await queue.flush(); }
            finally { flushing = false; }
        },
        keepDraft() { discarded = false; },
        discardDraft() { discarded = true; rememberDraft(); },
        dispose() { disposed = true; queue?.dispose(); },
        get discarded() { return discarded; },
        get pendingWrite() { return write; },
        get state() { return queue?.state ?? { status: 'idle' }; },
    };
}
