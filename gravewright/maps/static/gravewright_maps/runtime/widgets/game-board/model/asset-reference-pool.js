// gravewright/maps/frontend/widgets/game-board/model/asset-reference-pool.js
var AssetReferencePool = class {
  load;
  unload;
  #references = /* @__PURE__ */ new Map();
  #unloads = /* @__PURE__ */ new Map();
  constructor(load, unload) {
    this.load = load;
    this.unload = unload;
  }
  async acquire(url) {
    this.#references.set(url, (this.#references.get(url) ?? 0) + 1);
    try {
      const unloading = this.#unloads.get(url);
      if (unloading) await unloading;
      return await this.load(url);
    } catch {
      this.release(url);
      return void 0;
    }
  }
  release(url) {
    const references = this.#references.get(url);
    if (references === void 0)
      return;
    if (references > 1) {
      this.#references.set(url, references - 1);
      return;
    }
    this.#references.delete(url);
    const unloading = Promise.resolve().then(() => this.unload(url)).catch(() => {
    }).finally(() => {
      if (this.#unloads.get(url) === unloading) this.#unloads.delete(url);
    });
    this.#unloads.set(url, unloading);
  }
};
export {
  AssetReferencePool
};
