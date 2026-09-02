import { mkdir, open, type FileHandle } from "node:fs/promises";
import path from "node:path";
import type { DiagnosticAction, DiagnosticReporter } from "@gravewright/sdk";

const SAFE_NAME = /^[\p{L}\p{N} _.'-]{1,80}$/u;
const SAFE_EVENT = /^[a-z][a-z0-9]*(?:\.[a-z0-9]+)+$/;
const DETAIL_CATALOG: Readonly<Record<string, readonly string[]>> = Object.freeze({
  "player.dice.roll": ["die", "result"],
  "player.token.move": ["token", "scene"],
  "player.room.join": ["room"],
  "player.room.leave": ["room"],
  "gm.scene.activate": ["scene"],
  "gm.combat.start": ["scene"],
  "gm.combat.advance": ["round", "turn"],
  "system.module.initialize": ["module", "kind"],
  "system.start": [],
});

/** Normalizes untrusted text for the single-line journal format. */
function safeText(value: string, fallback: string, max = 120): string {
  const normalized = value.replace(/[\r\n|]+/g, " ").trim().slice(0, max);
  return normalized || fallback;
}

/** Returns the detail keys that may be recorded for a semantic event. */
function allowedKeys(event: string): readonly string[] {
  if (/^(server|frontend|backend|module)\.initialized$/.test(event)) return ["module"];
  return DETAIL_CATALOG[event] ?? [];
}

/** Renders only allow-listed detail values for a journal entry. */
function renderDetails(event: string, details: DiagnosticAction["details"]): string {
  if (!details) return "";
  const allowed = new Set(allowedKeys(event));
  const values = Object.entries(details)
    .filter(([key, value]) => allowed.has(key) && value !== null)
    .slice(0, 8)
    .map(([key, value]) => `${safeText(key, "detail", 40)}=${safeText(String(value), "", 100)}`);
  return values.length ? ` | ${values.join(", ")}` : "";
}

/** Writes a serialized, allow-listed diagnostic journal without sensitive fields. */
export class DiagnosticJournal implements DiagnosticReporter {
  readonly file: string;
  #handle: FileHandle;
  #writes = Promise.resolve();

  private constructor(file: string, handle: FileHandle) {
    this.file = file;
    this.#handle = handle;
  }

  /** Opens or creates an append-only journal at the requested path. */
  static async create(file: string): Promise<DiagnosticJournal> {
    const target = path.resolve(file);
    await mkdir(path.dirname(target), { recursive: true });
    return new DiagnosticJournal(target, await open(target, "a"));
  }

  /** Sanitizes and queues one diagnostic action for writing. */
  record(entry: DiagnosticAction): void {
    const timestamp = new Date().toISOString();
    const event = SAFE_EVENT.test(entry.event) ? entry.event : "system.unknown";
    const actor = SAFE_NAME.test(entry.actor) ? entry.actor : "Player";
    const action = safeText(entry.action, event);
    const status = entry.status === "success" ? "SUCCESS" : "FAILURE";
    const reason = entry.status === "failure" && entry.reason
      ? ` | ${safeText(entry.reason, "Action failed")}` : "";
    const line = `[${timestamp}] ${actor} | ${action} | ${status}${renderDetails(event, entry.details)}${reason}\n`;
    this.#writes = this.#writes.then(() => this.#handle.write(line).then(() => undefined));
  }

  /** Flushes queued entries and closes the journal file. */
  async close(): Promise<void> {
    await this.#writes;
    await this.#handle.close();
  }
}

/** Builds the default timestamped diagnostic path for a project. */
export function defaultDiagnosticPath(root: string, now = new Date()): string {
  const stamp = now.toISOString().replace(/[:.]/g, "-");
  return path.join(root, ".gravewright", "diagnostics", `session-${stamp}.txt`);
}
