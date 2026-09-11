class BrowserKeyValueStore {
    open;
    constructor(open) {
        this.open = open;
    }
    read(key) {
        try {
            return this.open().getItem(key) ?? undefined;
        }
        catch {
            return undefined;
        }
    }
    write(key, value) {
        try {
            this.open().setItem(key, value);
        }
        catch { /* Nothing was remembered; the page carries on. */ }
    }
    forget(key) {
        try {
            this.open().removeItem(key);
        }
        catch { /* Already unreachable, so already forgotten. */ }
    }
}
/** `device` outlives the visit; `tab` is gone when this tab is, which is what per-tab state wants. */
export function browserStore(lifetime) {
    return new BrowserKeyValueStore(() => lifetime === "device" ? localStorage : sessionStorage);
}
