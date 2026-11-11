// widgets/game-board/model/tile-blob-cache.js
import { promoted, discarded } from "./prefetch-metrics.js";
var TileBlobCache = class {
  limit;
  clock;
  entries = /* @__PURE__ */ new Map();
  bytes = 0;
  constructor(limit = 64 * 1024 * 1024, clock = Date.now) {
    this.limit = limit;
    this.clock = clock;
  }
  put(url, blob, expires, hint, networkMs = 0) {
    this.prune();
    this.remove(url);
    if (blob.size > this.limit || expires <= this.clock())
      return;
    while (this.bytes + blob.size > this.limit)
      this.remove(this.entries.keys().next().value);
    this.entries.set(url, { blob, expires, hint, networkMs, downloadedAt: Date.now() });
    this.bytes += blob.size;
  }
  take(url) {
    this.prune();
    const entry = this.entries.get(url);
    if (entry)
      promoted(entry.hint, entry.blob.size, entry.downloadedAt, entry.networkMs);
    this.remove(url, "used");
    return entry?.blob;
  }
  has(url) {
    this.prune();
    return this.entries.has(url);
  }
  clear() {
    for (const url of this.entries.keys())
      this.remove(url);
  }
  remove(url, reason = "evicted") {
    const old = this.entries.get(url);
    if (old) {
      if (reason !== "used")
        discarded(old.hint, old.blob.size, reason);
      this.bytes -= old.blob.size;
      this.entries.delete(url);
    }
  }
  prune() {
    for (const [url, entry] of this.entries)
      if (entry.expires <= this.clock())
        this.remove(url, "expired");
  }
};
var tileBlobCache = new TileBlobCache();
export {
  TileBlobCache,
  tileBlobCache
};
