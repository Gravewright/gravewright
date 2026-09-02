import type { Dispose } from "@gravewright/sdk";

/** Runs resource disposers in LIFO order and preserves every cleanup failure. */
export async function disposeAll(disposers: Dispose[], aggregateMessage = "Multiple module resources failed to dispose"): Promise<void> {
  const errors: unknown[] = [];
  while (disposers.length) {
    const dispose = disposers.pop()!;
    try { await dispose(); } catch (error) { errors.push(error); }
  }
  if (errors.length === 1) throw errors[0];
  if (errors.length > 1) throw new AggregateError(errors, aggregateMessage);
}
