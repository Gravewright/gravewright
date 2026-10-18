/** Reference-counts a shared asynchronous asset cache by its stable URL. */
export class AssetReferencePool {
    load;
    unload;
    #references = new Map();
    #unloads = new Map();
    constructor(load, unload) {
        this.load = load;
        this.unload = unload;
    }
    async acquire(url) {
        this.#references.set(url, (this.#references.get(url) ?? 0) + 1);
        try {
            // Pixi unload awaits its cached load before destroying the texture.
            // A new owner must not borrow that cached texture in the meantime.
            const unloading = this.#unloads.get(url);
            if (unloading) await unloading;
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
        const unloading = Promise.resolve().then(() => this.unload(url)).catch(() => { }).finally(() => {
            if (this.#unloads.get(url) === unloading) this.#unloads.delete(url);
        });
        this.#unloads.set(url, unloading);
    }
}
