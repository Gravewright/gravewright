/** Reference-counts a shared asynchronous asset cache by its stable URL. */
export class AssetReferencePool {
    load;
    unload;
    #references = new Map();
    constructor(load, unload) {
        this.load = load;
        this.unload = unload;
    }
    async acquire(url) {
        this.#references.set(url, (this.#references.get(url) ?? 0) + 1);
        try {
            return await this.load(url);
        }
        catch {
            this.release(url);
            return undefined;
        }
    }
    release(url) {
        const references = this.#references.get(url);
        if (references === undefined)
            return;
        if (references > 1) {
            this.#references.set(url, references - 1);
            return;
        }
        this.#references.delete(url);
        void this.unload(url).catch(() => { });
    }
}
