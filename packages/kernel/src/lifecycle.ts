import type { Dispose } from "@gravewright/sdk";

export async function disposeAll(disposers: readonly Dispose[], aggregateMessage = "Multiple composition disposers failed"): Promise<void> {
  const errors: unknown[] = [];
  for (const dispose of [...disposers].reverse()) {
    try { await dispose(); } catch (error) { errors.push(error); }
  }
  if (errors.length === 1) throw errors[0];
  if (errors.length > 1) throw new AggregateError(errors, aggregateMessage);
}
