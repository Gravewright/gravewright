import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { ModuleState } from "@gravewright/sdk";

export interface ModuleStateStore {
  get(name: string): ModuleState;
  set(name: string, state: ModuleState): Promise<void>;
}

interface StateFileOperations {
  read(file: string): Promise<string>;
  mkdir(directory: string): Promise<void>;
  write(file: string, content: string): Promise<void>;
  rename(from: string, to: string): Promise<void>;
  unlink(file: string): Promise<void>;
}

const defaultOperations: StateFileOperations = {
  read: (file) => readFile(file, "utf8"),
  async mkdir(directory) { await mkdir(directory, { recursive: true }); },
  async write(file, content) { await writeFile(file, content); },
  rename,
  unlink,
};

function ordered(states: Record<string, ModuleState>): Record<string, ModuleState> {
  return Object.fromEntries(Object.entries(states).sort(([left], [right]) => left.localeCompare(right)));
}

export async function createModuleStateStore(
  file: string | URL,
  operations: StateFileOperations = defaultOperations,
): Promise<ModuleStateStore> {
  const filePath = path.resolve(file instanceof URL ? fileURLToPath(file) : file);
  const temporaryPath = `${filePath}.tmp`;
  let states: Record<string, ModuleState> = {};
  let writes = Promise.resolve();
  try {
    const parsed: unknown = JSON.parse(await operations.read(filePath));
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new Error("expected an object");
    for (const [name, state] of Object.entries(parsed)) {
      if (state !== "active" && state !== "disabled") {
        throw new Error(`Invalid module state ${JSON.stringify(state)} for ${JSON.stringify(name)}`);
      }
      states[name] = state;
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  return {
    get: (name) => states[name] ?? "disabled",
    set(name, state) {
      if (state !== "active" && state !== "disabled") {
        return Promise.reject(new Error(`Invalid module state ${JSON.stringify(state)} for ${JSON.stringify(name)}`));
      }
      const persist = async (): Promise<void> => {
        const nextStates = ordered({ ...states, [name]: state });
        await operations.mkdir(path.dirname(filePath));
        try {
          await operations.write(temporaryPath, `${JSON.stringify(nextStates, null, 2)}\n`);
          await operations.rename(temporaryPath, filePath);
        } catch (error) {
          try { await operations.unlink(temporaryPath); } catch { /* best-effort cleanup */ }
          throw error;
        }
        states = nextStates;
      };
      const result = writes.then(persist, persist);
      writes = result.then(() => undefined, () => undefined);
      return result;
    },
  };
}
