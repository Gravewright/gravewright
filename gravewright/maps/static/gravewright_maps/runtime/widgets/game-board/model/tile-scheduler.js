// widgets/game-board/model/tile-scheduler.js
var PRIORITY = { immediate: 0, high: 1, normal: 2, low: 3, background: 4 };
var PROMOTE_AFTER_MS = 500;
var MAX_AGED_PRIORITY = PRIORITY.high;
var TileScheduler = class {
  promoteAfterMs;
  #items = /* @__PURE__ */ new Map();
  #sequence = 0;
  constructor(promoteAfterMs = PROMOTE_AFTER_MS) {
    this.promoteAfterMs = promoteAfterMs;
  }
  get size() {
    return this.#items.size;
  }
  /**
   * Queues work, or refreshes what is already queued under that key.
   *
   * The newest payload wins — a tile re-planned at a new priority is the same tile — but the
   * original wait is preserved, because a key that has been queued for a second has been starving
   * for a second no matter how many times the viewport asked for it again.
   */
  enqueue(work, now) {
    const existing = this.#items.get(work.key);
    this.#items.set(work.key, {
      ...work,
      queuedAt: existing?.queuedAt ?? now,
      sequence: existing?.sequence ?? this.#sequence++
    });
  }
  /** Takes the most urgent work the budget allows, most urgent first. */
  drain(now, budget) {
    const ranked = [...this.#items.values()].map((item) => ({ item, effective: this.#effectivePriority(item, now) })).sort((left, right) => left.effective - right.effective || left.item.order - right.item.order || left.item.sequence - right.item.sequence).slice(0, Math.max(0, budget.maxItems));
    for (const { item } of ranked)
      this.#items.delete(item.key);
    return ranked.map(({ item }) => item.payload);
  }
  cancel(key) {
    return this.#items.delete(key);
  }
  /** Drops work that a scene change or a newer viewport made pointless. Returns how much it dropped. */
  cancelScope(scope) {
    let dropped = 0;
    for (const [key, item] of this.#items) {
      const staleScene = scope.sceneNot !== void 0 && item.scene !== scope.sceneNot;
      const staleView = scope.olderThanGeneration !== void 0 && item.generation < scope.olderThanGeneration;
      if (staleScene || staleView) {
        this.#items.delete(key);
        dropped += 1;
      }
    }
    return dropped;
  }
  clear() {
    this.#items.clear();
  }
  /** What the queue holds right now, most urgent first. For diagnostics and tests, not for draining. */
  pending(now) {
    return [...this.#items.values()].map((item) => ({ key: item.key, priority: this.#effectivePriority(item, now) })).sort((left, right) => left.priority - right.priority);
  }
  #effectivePriority(item, now) {
    const waited = Math.max(0, now - item.queuedAt);
    if (waited < this.promoteAfterMs)
      return item.priority;
    const promoted = item.priority - Math.floor(waited / this.promoteAfterMs);
    return Math.max(MAX_AGED_PRIORITY, promoted);
  }
};
function classifyTile(tile, visible, focus) {
  const distance = Math.round(Math.hypot(tile.column - focus.column, tile.row - focus.row));
  const onScreen = tile.column >= visible.firstColumn && tile.column <= visible.lastColumn && tile.row >= visible.firstRow && tile.row <= visible.lastRow;
  if (!onScreen)
    return { priority: PRIORITY.low, ring: "prefetch", distance };
  if (distance <= 1)
    return { priority: PRIORITY.high, ring: "visible-center", distance };
  return { priority: PRIORITY.normal, ring: "visible-edge", distance };
}
export {
  PRIORITY,
  TileScheduler,
  classifyTile
};
