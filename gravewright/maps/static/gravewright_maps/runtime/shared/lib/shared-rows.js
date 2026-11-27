// shared/lib/shared-rows.js
var clone = (value) => structuredClone(value);
var authored = (row) => {
  const { version, canEdit, owner, expected_version, ...value } = row;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, value[key]]));
};
var same = (a, b) => JSON.stringify(authored(a)) === JSON.stringify(authored(b));
function rowChanges(before, after) {
  const previous = new Map(before.map((row) => [row.id, row]));
  const incoming = new Set(after.map((row) => row.id));
  return {
    upserts: after.filter((row) => !previous.has(row.id) || !same(row, previous.get(row.id))).map((row) => ({ ...authored(row), expected_version: previous.get(row.id)?.version ?? null })),
    removed: before.filter((row) => !incoming.has(row.id) && row.canEdit !== false).map((row) => ({ id: row.id, expected_version: row.version }))
  };
}
function changedRows(before, after) {
  const previous = new Map(before.map((row) => [row.id, row])), next = new Map(after.map((row) => [row.id, row]));
  const undo = [], redo = [];
  for (const [id, row] of next)
    if (!previous.has(id) || !same(previous.get(id), row)) {
      undo.push([id, previous.get(id) ?? null]);
      redo.push([id, row]);
    }
  for (const [id, row] of previous)
    if (!next.has(id)) {
      undo.push([id, row]);
      redo.push([id, null]);
    }
  return { undo, redo };
}
function applyRowChanges(rows, changes) {
  const pending = new Map(changes), result = [];
  for (const row of rows) {
    if (!pending.has(row.id)) {
      result.push(row);
      continue;
    }
    const next = pending.get(row.id);
    pending.delete(row.id);
    if (next) result.push(next);
  }
  for (const next of pending.values()) if (next) result.push(next);
  return result;
}
function createSharedRows({ initial = [], save, refresh, render, error, delay = 160, key = "rows" }) {
  let confirmed = clone(initial), desired = clone(initial), pending, timer, closed = false, deferred;
  const publish = () => {
    if (!closed) render(clone(desired));
  };
  const changed = (patch) => patch.upserts.length || patch.removed.length;
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(flush, delay);
  };
  function reconcile(rows) {
    const patch = rowChanges(confirmed, desired);
    const dirty = new Set([...patch.upserts, ...patch.removed].map((row) => row.id));
    confirmed = [...clone(rows).filter((row) => !dirty.has(row.id)), ...confirmed.filter((row) => dirty.has(row.id))];
    desired = [...clone(rows).filter((row) => !dirty.has(row.id)), ...desired.filter((row) => dirty.has(row.id))];
    publish();
  }
  async function flush() {
    clearTimeout(timer);
    if (pending) return;
    const patch = rowChanges(confirmed, desired);
    if (!changed(patch)) return;
    const sent = clone(desired);
    pending = true;
    try {
      const result = await save(patch);
      const queued = rowChanges(sent, desired);
      confirmed = clone(result[key]);
      const remove = new Set(queued.removed.map((row) => row.id));
      const updates = new Map(queued.upserts.map((row) => [row.id, row]));
      desired = confirmed.filter((row) => !remove.has(row.id)).map((row) => {
        const update = updates.get(row.id);
        updates.delete(row.id);
        return update ? { ...row, ...authored(update) } : row;
      });
      for (const row of updates.values()) desired.push(authored(row));
      if (deferred && deferred.version >= result.version) reconcile(deferred.rows);
      deferred = void 0;
      publish();
    } catch (reason) {
      desired = clone(confirmed);
      deferred = void 0;
      if (closed) return;
      publish();
      error(reason);
      try {
        const state = await refresh();
        if (!closed) reconcile(state[key]);
      } catch (readError) {
        if (!closed) error(readError);
      }
    } finally {
      pending = false;
      clearTimeout(timer);
      if (changed(rowChanges(confirmed, desired))) {
        if (closed) void flush();
        else timer = setTimeout(flush, delay);
      }
    }
  }
  return {
    /** Replace the desired list; the caller already displays it. */
    edit(rows) {
      if (closed) return;
      desired = clone(rows);
      schedule();
    },
    /** Change only the named rows of the current list, so unrelated peer rows are never resubmitted. */
    apply(changes) {
      if (closed) return;
      desired = applyRowChanges(desired, [...changes].map(([id, row]) => [id, row && clone(row)]));
      publish();
      schedule();
    },
    update(rows, version = 0) {
      if (closed) return;
      if (pending) {
        if (!deferred || version >= deferred.version) deferred = { rows: clone(rows), version };
        return;
      }
      reconcile(rows);
    },
    flush,
    destroy() {
      closed = true;
      clearTimeout(timer);
      void flush();
    }
  };
}
export {
  applyRowChanges,
  changedRows,
  createSharedRows,
  rowChanges
};
