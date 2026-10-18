/** Serialize document writes while keeping retries attached to their original snapshot. */
export function createAutosave({ read, save, canSave = () => true, onState = () => {}, delay = 700,
    retryDelays = [1000, 3000, 10000], initialKey, pendingSnapshot, timers = {} }) {
    if (typeof read !== 'function' || typeof save !== 'function') throw new TypeError('Autosave requires read and save callbacks.');
    const setTimer = timers.setTimeout || globalThis.setTimeout.bind(globalThis);
    const clearTimer = timers.clearTimeout || globalThis.clearTimeout.bind(globalThis);
    const now = timers.now || Date.now;
    let acknowledged = initialKey === undefined ? read()?.key : initialKey;
    let state = { status: 'idle' }, dirty = false, active = false, disposed = false;
    let timer, due = 0, attempt = 0, paused, lastResult;
    // Recovered writes retain their exact payload and caller-owned receipt UUID.
    let operation = pendingSnapshot ? structuredClone(pendingSnapshot) : undefined;
    let operationAbort = operation ? new AbortController() : undefined;
    const waiters = new Set();

    function publish(status, error, retrying) {
        state = { status, ...(error ? { error } : {}), ...(retrying === undefined ? {} : { retrying }) };
        onState({ ...state });
    }
    function cancelTimer() { if (timer !== undefined) clearTimer(timer); timer = undefined; }
    function arm(milliseconds) {
        if (disposed || paused || active) return;
        cancelTimer();
        timer = setTimer(() => { timer = undefined; void pump(); }, Math.max(0, milliseconds));
    }
    function settle(error) {
        for (const waiter of waiters) error ? waiter.reject(error) : waiter.resolve(lastResult);
        waiters.clear();
    }
    function finish() {
        if (dirty) { publish('pending'); arm(waiters.size ? 0 : due - now()); }
        else {
            publish('saved');
            if (dirty) arm(waiters.size ? 0 : due - now());
            else settle();
        }
    }
    function stop(error, kind) {
        paused = { kind, error };
        publish(kind === 'network' ? 'error' : kind, error, kind === 'network' ? false : undefined);
        settle(error);
    }
    function retryable(error) {
        if (error?.validation || error?.name === 'AbortError') return false;
        return error?.status === undefined || error.status === 0 || error.status >= 500;
    }
    async function pump() {
        if (disposed || active || paused) return;
        if (!dirty && !operation) { settle(); return; }
        try { if (!canSave()) { publish('pending'); arm(100); return; } }
        catch (error) { stop(error, 'blocked'); return; }
        if (!operation) {
            dirty = false;
            try {
                const current = read();
                if (current === null || current === undefined || current.key === acknowledged) { finish(); return; }
                if (typeof current.key !== 'string' || !Object.hasOwn(current, 'payload'))
                    throw new TypeError('Autosave read must return a key and payload.');
                // Capture only when this write starts, after the previous acknowledgement.
                operation = structuredClone(current);
                operationAbort = new AbortController(); attempt = 0;
            } catch (error) { stop(error, 'blocked'); return; }
        }
        active = true; publish('saving');
        try {
            const result = await save(operation, { signal: operationAbort.signal, attempt: ++attempt });
            if (disposed) return;
            acknowledged = operation.key; lastResult = result;
            operation = operationAbort = undefined; attempt = 0;
            active = false; finish();
        } catch (error) {
            if (disposed) return;
            active = false;
            if (error?.conflict || error?.status === 409) stop(error, 'conflict');
            else if (retryable(error)) {
                if (attempt <= retryDelays.length) {
                    publish('error', error, true); arm(retryDelays[attempt - 1]);
                } else stop(error, 'network');
            } else {
                let newer = false;
                if (dirty) {
                    try { newer = read()?.key !== operation.key; } catch { /* The latest draft still needs validation. */ }
                }
                if (newer) {
                    operation = operationAbort = undefined; attempt = 0; finish();
                } else stop(error, 'blocked');
            }
        } finally { active = false; }
    }
    function schedule() {
        if (disposed) return;
        dirty = true; due = now() + delay;
        // A new authored edit can repair validation, but cannot resolve a version conflict.
        if (paused?.kind === 'blocked') {
            paused = undefined; operation = operationAbort = undefined; attempt = 0;
        }
        if (paused || active || operation && timer !== undefined) return;
        publish('pending'); arm(waiters.size ? 0 : delay);
    }
    function flush() {
        if (disposed) return Promise.reject(new DOMException('Autosave was disposed.', 'AbortError'));
        if (paused) return Promise.reject(paused.error);
        dirty = true; due = 0;
        const result = new Promise((resolve, reject) => waiters.add({ resolve, reject }));
        // A flush skips the editing debounce, while respecting a network backoff.
        if (!(operation && attempt > 0 && timer !== undefined)) { cancelTimer(); void pump(); }
        return result;
    }
    function retry() {
        if (disposed) return;
        if (paused) {
            if (paused.kind !== 'network') operation = operationAbort = undefined;
            paused = undefined; attempt = 0;
        }
        dirty = true; due = now();
        if (!active) { publish('pending'); arm(0); }
    }
    function dispose() {
        if (disposed) return;
        disposed = true; cancelTimer(); operationAbort?.abort();
        settle(new DOMException('Autosave was disposed.', 'AbortError'));
        operation = operationAbort = undefined;
    }
    return { schedule, flush, retry, dispose, get state() { return { ...state }; } };
}
