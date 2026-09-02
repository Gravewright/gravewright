import type { Kernel } from "@gravewright/kernel";
import type { ModuleStateStore } from "./module-state.js";

const operations = new WeakMap<Kernel, Promise<void>>();

/** Serializes administrative changes for one kernel instance. */
function coordinate(kernel: Kernel, operation: () => Promise<void>): Promise<void> {
  const previous = operations.get(kernel) ?? Promise.resolve();
  const result = previous.then(operation, operation);
  operations.set(kernel, result.then(() => undefined, () => undefined));
  return result;
}

/** Checks module activation without exposing kernel internals. */
function isActive(kernel: Kernel, name: string): boolean {
  try {
    kernel.use(name);
    return true;
  } catch {
    return false;
  }
}

/** Activates a module and rolls the runtime back if state persistence fails. */
export function activateModule(kernel: Kernel, store: ModuleStateStore, name: string): Promise<void> {
  return coordinate(kernel, async () => {
    const changedRuntime = !isActive(kernel, name);
    await kernel.activate(name);
    try {
      await store.set(name, "active");
    } catch (persistenceError) {
      if (changedRuntime) {
        try {
          await kernel.disable(name);
        } catch (rollbackError) {
          throw new AggregateError(
            [persistenceError, rollbackError],
            `Failed to persist module state for "${name}" and rollback also failed`,
            { cause: persistenceError },
          );
        }
      }
      throw persistenceError;
    }
  });
}

/** Disables a module and restores it if state persistence fails. */
export function disableModule(kernel: Kernel, store: ModuleStateStore, name: string): Promise<void> {
  return coordinate(kernel, async () => {
    const changedRuntime = isActive(kernel, name);
    await kernel.disable(name);
    try {
      await store.set(name, "disabled");
    } catch (persistenceError) {
      if (changedRuntime) {
        try {
          await kernel.activate(name);
        } catch (rollbackError) {
          throw new AggregateError(
            [persistenceError, rollbackError],
            `Failed to persist module state for "${name}" and rollback also failed`,
            { cause: persistenceError },
          );
        }
      }
      throw persistenceError;
    }
  });
}
