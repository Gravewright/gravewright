// gravewright/maps/frontend/widgets/game-board/model/scene-image-art.js
var SceneImageArt = class {
  #load;
  #apply;
  #remove;
  #release;
  #cache = /* @__PURE__ */ new Map();
  #wanted = /* @__PURE__ */ new Map();
  #applied = /* @__PURE__ */ new Map();
  #generation = 0;
  #clock = 0;
  #idleLimit;
  #idleBytes;
  constructor({ load, apply, remove, release, idleLimit = 8, idleBytes = 16777216 }) {
    this.#load = load;
    this.#apply = apply;
    this.#remove = remove;
    this.#release = release;
    this.#idleLimit = idleLimit;
    this.#idleBytes = idleBytes;
  }
  sync(rows) {
    const wanted = new Map(rows.filter((row) => row.src).map((row) => [row.id, row.src]));
    for (const id of /* @__PURE__ */ new Set([...this.#wanted.keys(), ...this.#applied.keys()])) if (!wanted.has(id)) {
      this.#remove(id);
      this.#applied.delete(id);
    }
    const previous = this.#wanted;
    this.#wanted = wanted;
    for (const [id, url] of wanted) {
      let entry = this.#cache.get(url);
      if (previous.get(id) === url && entry) continue;
      if (!entry) {
        entry = { abort: new AbortController(), used: ++this.#clock };
        this.#cache.set(url, entry);
        entry.pending = Promise.resolve().then(() => this.#load(url, entry.abort.signal)).then((resource) => {
          if (this.#cache.get(url) !== entry) {
            if (resource) this.#release(resource);
            return;
          }
          if (!resource) {
            this.#cache.delete(url);
            return;
          }
          entry.resource = resource;
          this.#prune();
          return resource;
        }).catch(() => {
          if (this.#cache.get(url) === entry) this.#cache.delete(url);
        });
      }
      entry.used = ++this.#clock;
      const generation = this.#generation;
      if (!previous.has(id) && !entry.resource) {
        const fallback = this.#cache.get(this.#applied.get(id))?.resource;
        if (fallback) this.#apply(id, fallback);
      }
      const apply = (resource) => {
        if (!resource || generation !== this.#generation || this.#wanted.get(id) !== url) return;
        this.#apply(id, resource);
        this.#applied.set(id, url);
        this.#prune();
      };
      if (entry.resource) apply(entry.resource);
      else void entry.pending.then(apply);
    }
    this.#prune();
  }
  #discard(url, entry) {
    this.#cache.delete(url);
    entry.abort.abort();
    if (entry.resource) this.#release(entry.resource);
  }
  #prune() {
    const retained = /* @__PURE__ */ new Set([...this.#wanted.values(), ...this.#applied.values()]);
    const idle = [...this.#cache].filter(([url]) => !retained.has(url));
    let bytes = idle.reduce((total, [, entry]) => total + (entry.resource?.bytes || 0), 0);
    let count = idle.length;
    for (const [url, entry] of idle.sort((a, b) => a[1].used - b[1].used)) {
      if (entry.resource && count <= this.#idleLimit && bytes <= this.#idleBytes) continue;
      bytes -= entry.resource?.bytes || 0;
      count--;
      this.#discard(url, entry);
    }
  }
  reset(preserveResources = false) {
    this.#generation++;
    for (const id of this.#wanted.keys()) this.#remove(id);
    this.#wanted.clear();
    if (!preserveResources) {
      this.#applied.clear();
      for (const [url, entry] of this.#cache) this.#discard(url, entry);
    }
  }
};
export {
  SceneImageArt
};
