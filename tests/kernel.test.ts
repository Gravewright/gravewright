import assert from "node:assert/strict";
import { mkdtemp, symlink, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { Kernel as RuntimeKernel, type LoadOptions } from "@gravewright/kernel";
import { ROOM_PROTOCOL, ROOM_SLOT_NAMES, type ModuleKind } from "@gravewright/sdk";
import { activateModule, disableModule } from "../src/module-admin.js";
import type { ModuleStateStore } from "../src/module-state.js";

// Existing tests predate the safe default and explicitly model active fixtures.
class Kernel extends RuntimeKernel {
  override async load(moduleDirectory: string, options: LoadOptions = { state: "active" }): Promise<void> {
    await super.load(moduleDirectory, options);
  }
}

const contracts: Partial<Record<ModuleKind, string[]>> = {
  server: ["start", "stop", "http", "route", "middleware"], room: ["mount", "unmount", "slots"], ruleset: [], backend: [],
  chat: ["send", "erase"], "dice-engine": ["roll"], assets: ["store", "resolve", "mimeTypeAllowed", "remove"], storage: ["create", "find", "where", "update", "delete"], addon: [],
};

async function fixture(options: {
  name?: string;
  kind?: ModuleKind;
  version?: string;
  dependencies?: Record<string, string>;
  uses?: Partial<Record<ModuleKind, "required" | "optional">>;
  requires?: Record<string, string>;
  provides?: Record<string, string>;
  exposes?: { slots: Array<{ name: string; mounts: "one"; contributions: "one" | "many" }> };
  routes?: Record<string, string>;
  middleware?: Record<string, string[]>;
  slots?: Record<string, string[]>;
  exports?: { get?: string[] };
  source?: string;
} = {}): Promise<string> {
  const directory = await mkdtemp(path.join(tmpdir(), "vtt-module-"));
  const name = options.name ?? path.basename(directory);
  const kind = options.kind ?? "addon";
  const requested = options.exports ?? { get: ["answer"] };
  const declared = { ...requested, get: [...(requested.get ?? [])] };
  const all = [...(declared.get ?? [])];
  const unsafeCharMap: Record<string, string> = {
    "<": "\\u003C",
    ">": "\\u003E",
    "/": "\\u002F",
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\0": "\\0",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
  };
  const escapeUnsafeForEmbeddedCode = (value: string): string =>
    value.replace(/[<>\/\\\b\f\n\r\t\0\u2028\u2029]/g, (ch) => unsafeCharMap[ch] ?? ch);
  const properties = [...new Set(all)].map((key) =>
    `${escapeUnsafeForEmbeddedCode(JSON.stringify(key))}: ${key === "answer" ? "42" : "() => undefined"}`,
  ).join(",\n");
  let source = options.source ?? `export default function createModule(ctx) { return { ${properties} }; }`;
  if (options.source?.includes("export default function")) {
    source = `${source.replace("export default function", "const __fixtureFactory = function")}
      export default function(ctx) {
        const value = __fixtureFactory(ctx);
        return value;
      }`;
  }
  await writeFile(path.join(directory, "manifest.json"), JSON.stringify({
    name, kind, provider: "community", version: options.version ?? "1.0.0", entry: "./index.ts",
    ...(options.dependencies ? { dependencies: options.dependencies } : {}),
    ...(options.uses ? { uses: options.uses } : {}),
    ...(options.requires ? { requires: options.requires } : {}),
    ...(options.provides ? { provides: options.provides } : {}),
    ...(options.routes ? { routes: options.routes } : {}),
    ...(options.middleware ? { middleware: options.middleware } : {}),
    ...(kind === "room" ? { exposes: options.exposes ?? { slots: ROOM_SLOT_NAMES.map((slot) => ({ name: slot, mounts: "one", contributions: "many" })) } } : {}),
    ...(kind === "room" ? { room_protocol: ROOM_PROTOCOL } : {}),
    ...(options.slots ? { slots: options.slots } : {}), exports: declared,
  }));
  await writeFile(path.join(directory, "index.ts"), source);
  return directory;
}

async function validKind(kind: "server" | "room" | "ruleset" | "backend", name = `${kind}-module`) {
  return fixture({ name, kind, exports: { get: contracts[kind] } });
}

async function bootstrap(kernel: Kernel, includeBase = true): Promise<void> {
  await loadRequiredKinds(kernel, includeBase);
  await kernel.initialize();
}

async function loadRequiredKinds(kernel: Kernel, includeBase = true): Promise<void> {
  if (includeBase) await kernel.load(await validKind("server", `base-${crypto.randomUUID()}`));
  await kernel.load(await validKind("room", `room-${crypto.randomUUID()}`));
  await kernel.load(await validKind("ruleset", `ruleset-${crypto.randomUUID()}`));
}

test("loads a valid module and permits declared get", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "valid" }));
  await bootstrap(kernel);
  assert.equal(kernel.use("valid").get("answer"), 42);
});

test("rejects a duplicate module name", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "same" }));
  await assert.rejects(kernel.load(await fixture({ name: "same" })), /Duplicate module: same/);
});

test("enforces get permission and hides internal exports", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "visibility", exports: { get: ["visible"] },
    source: "export default function createModule(ctx) { return { visible: 1, internal: 2 }; }",
  }));
  await bootstrap(kernel);
  assert.equal(kernel.use("visibility").get("visible"), 1);
  assert.throws(() => kernel.use("visibility").get("internal"), /Get not authorized/);
  assert.throws(() => kernel.use("visibility").get("unknown"), /Get not authorized/);
});

test("functions are ordinary values obtained and called through get", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "dice", exports: { get: ["roll"] }, source: "export default function createModule(ctx) { return { roll: () => 6 }; }" }));
  await bootstrap(kernel);
  assert.equal((kernel.use("dice").get("roll") as () => number)(), 6);
});

for (const kind of ["server"] as const) {
  test(`validates the minimum ${kind} contract`, async () => {
    const badKernel = new Kernel();
    await badKernel.load(await fixture({ name: `bad-${kind}`, kind, exports: { get: contracts[kind]!.slice(1) } }));
    await assert.rejects(
      bootstrap(badKernel, kind !== "server"),
      new RegExp(`Minimum contract not satisfied for ${kind}`),
    );
    const kernel = new Kernel();
    await kernel.load(await validKind(kind, `good-${kind}`));
    await bootstrap(kernel, kind !== "server");
  });
}

test("allows multiple addons", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "addon-a", kind: "addon", exports: { get: ["answer"] } }));
  await kernel.load(await fixture({ name: "addon-b", kind: "addon", exports: { get: ["answer"] } }));
  await bootstrap(kernel);
  assert.equal(kernel.use("addon-a").get("answer"), 42);
  assert.equal(kernel.use("addon-b").get("answer"), 42);
});

test("allows multiple backend modules and rejects duplicate singleton kinds", async () => {
  const systems = new Kernel();
  await systems.load(await fixture({ name: "backend-a", kind: "backend" }));
  await systems.load(await fixture({ name: "backend-b", kind: "backend" }));
  await systems.load(await validKind("server"));
  await systems.load(await validKind("room"));
  await systems.load(await validKind("ruleset"));
  await assert.doesNotReject(systems.initialize());

  for (const kind of ["room", "ruleset"] as const) {
    const kernel = new Kernel();
    await loadRequiredKinds(kernel);
    await kernel.load(await validKind(kind, `second-${kind}`));
    await assert.rejects(kernel.initialize(), new RegExp(`Multiple active modules implement singleton kind "${kind}"`));
  }
});

test("initialization requires exactly one server kind", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "optional-addon" }));
  await assert.rejects(kernel.initialize(), /Missing active module for required kind "server"/);
  await kernel.load(await validKind("server"));
  await assert.doesNotReject(kernel.initialize());
});

 test("rejects a declared export missing from the entry", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "missing-export", exports: { get: ["absent"] }, source: "export default function createModule(ctx) { return { other: 1 }; }" }));
  await assert.rejects(
    bootstrap(kernel),
    /Declared export does not exist/,
  );
});

test("factory receives Context and can use a previously loaded module", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "module-b", dependencies: { "module-a": "^1.0.0" }, exports: { get: ["valueFromA"] }, source: `
    export default function createModule(ctx) {
      const moduleA = ctx.use("module-a");
      return { valueFromA: moduleA.get("value") };
    }
  ` }));
  await kernel.load(await fixture({ name: "module-a", exports: { get: ["value"] }, source: `
    export default function createModule(ctx) { return { value: 42 }; }
  ` }));
  await bootstrap(kernel);
  assert.equal(kernel.use("module-b").get("valueFromA"), 42);
});

test("module context rejects use of an undeclared dependency", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "undeclared-consumer", source: `
    export default function createModule(ctx) {
      ctx.use("undeclared-library");
      return { answer: 42 };
    }
  ` }));
  await kernel.load(await fixture({ name: "undeclared-library" }));
  await assert.rejects(
    bootstrap(kernel),
    /Module "undeclared-consumer" cannot use undeclared dependency "undeclared-library"/,
  );
});

test("module context does not grant transitive dependency access", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "transitive-consumer", dependencies: { "direct-library": "^1.0.0" }, source: `
      export default function createModule(ctx) {
        ctx.use("transitive-library");
        return { answer: 42 };
      }
    `,
  }));
  await kernel.load(await fixture({ name: "direct-library", dependencies: { "transitive-library": "^1.0.0" } }));
  await kernel.load(await fixture({ name: "transitive-library" }));
  await assert.rejects(
    bootstrap(kernel),
    /Module "transitive-consumer" cannot use undeclared dependency "transitive-library"/,
  );
});

test("ctx.kind resolves every architectural role with singleton and plural cardinality", async () => {
  const kernel = new Kernel();
  await kernel.load(await validKind("server", "kind-server"));
  await kernel.load(await validKind("room", "kind-room"));
  await kernel.load(await validKind("ruleset", "kind-ruleset"));
  for (const [kind, name] of [
    ["chat", "kind-chat"], ["dice-engine", "kind-dice"], ["assets", "kind-assets"], ["storage", "kind-storage"],
  ] as const) await kernel.load(await fixture({ name, kind, exports: { get: contracts[kind] } }));
  await kernel.load(await fixture({ name: "kind-backend-a", kind: "backend" }));
  await kernel.load(await fixture({ name: "kind-backend-b", kind: "backend" }));
  await kernel.load(await fixture({ name: "kind-addon", kind: "addon" }));
  await kernel.load(await fixture({
    name: "kind-consumer",
    uses: Object.fromEntries(["server", "room", "ruleset", "chat", "dice-engine", "assets", "storage", "backend"].map((kind) => [kind, "required"])) as Partial<Record<ModuleKind, "required">>,
    exports: { get: ["resolved"] },
    source: `export default function(ctx) { return { resolved: {
      server: ctx.kind("server"), room: ctx.kind("room"), ruleset: ctx.kind("ruleset"),
      chat: ctx.kind("chat"), dice: ctx.kind("dice-engine"), assets: ctx.kind("assets"), storage: ctx.kind("storage"),
      backends: ctx.kind("backend")
    } }; }`,
  }));
  await kernel.initialize();
  const resolved = kernel.use("kind-consumer").get("resolved") as Record<string, unknown>;
  assert.equal(Array.isArray(resolved.backends) && resolved.backends.length, 2);
  for (const name of ["server", "room", "ruleset", "chat", "dice", "assets", "storage"]) assert.ok(resolved[name]);

  const addonKernel = new Kernel();
  await addonKernel.load(await validKind("server"));
  await addonKernel.load(await validKind("room"));
  await addonKernel.load(await fixture({
    name: "addon-kind-consumer", kind: "ruleset", uses: { addon: "required" }, exports: { get: ["addons"] },
    source: `export default function(ctx) { return { addons: ctx.kind("addon") }; }`,
  }));
  await addonKernel.load(await fixture({ name: "addon-provider-a", kind: "addon" }));
  await addonKernel.load(await fixture({ name: "addon-provider-b", kind: "addon" }));
  await addonKernel.initialize();
  assert.equal((addonKernel.use("addon-kind-consumer").get("addons") as unknown[]).length, 2);
});

test("ctx.kind enforces uses and optional absence semantics", async () => {
  const optional = new Kernel();
  await optional.load(await fixture({
    name: "optional-kinds", uses: { chat: "optional", backend: "optional" }, exports: { get: ["values"] },
    source: `export default function(ctx) { return { values: [ctx.kind("chat"), ctx.kind("backend")] }; }`,
  }));
  await bootstrap(optional);
  assert.deepEqual(optional.use("optional-kinds").get("values"), [undefined, []]);

  const undeclared = new Kernel();
  await undeclared.load(await fixture({ name: "undeclared-kind", source: `export default function(ctx) { ctx.kind("chat"); return { answer: 42 }; }` }));
  await assert.rejects(bootstrap(undeclared), /cannot use undeclared kind "chat"/);

  const required = new Kernel();
  await required.load(await fixture({ name: "required-chat", uses: { chat: "required" } }));
  await loadRequiredKinds(required);
  await assert.rejects(required.initialize(), /requires missing kind "chat"/);
});

test("kind relations determine order, cycles, activation and disable safety", async () => {
  const key = `__gravewright_kind_order_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "kind-order-consumer", uses: { chat: "required" },
    source: `export default function(ctx) { globalThis.${key}.push("consumer"); ctx.kind("chat"); return { answer: 42 }; }`,
  }));
  await kernel.load(await fixture({
    name: "kind-order-chat", kind: "chat", exports: { get: contracts.chat },
    source: `export default function() { globalThis.${key}.push("chat"); return { send() { return "id"; }, erase() {} }; }`,
  }));
  await loadRequiredKinds(kernel);
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["chat", "consumer"]);
  await assert.rejects(kernel.disable("kind-order-chat"), /requires missing kind "chat"/);
  delete (globalThis as Record<string, unknown>)[key];

  const incremental = new Kernel();
  await incremental.load(await fixture({ name: "optional-chat-consumer", uses: { chat: "optional" } }));
  await incremental.load(await fixture({ name: "disabled-chat", kind: "chat", exports: { get: contracts.chat } }), { state: "disabled" });
  await bootstrap(incremental);
  await assert.doesNotReject(incremental.activate("disabled-chat"));

  const cycle = new Kernel();
  await cycle.load(await fixture({ name: "cycle-chat", kind: "chat", uses: { addon: "required" }, exports: { get: contracts.chat } }));
  await cycle.load(await fixture({ name: "cycle-addon", kind: "addon", uses: { chat: "required" } }));
  await loadRequiredKinds(cycle);
  assert.throws(() => cycle.plan(), /Circular dependency detected/);
});

test("factory receives a Context facade without Kernel methods", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "context-inspector",
    exports: { get: ["inspectContext"] },
    source: `export default function createModule(ctx) {
      return {
        inspectContext() {
          return {
            hasUse: typeof ctx.use === "function",
            hasLoad: typeof ctx.load !== "undefined",
            hasInitialize: typeof ctx.initialize !== "undefined",
            keys: Object.keys(ctx),
            frozen: Object.isFrozen(ctx)
          };
        }
      };
    }`,
  }));
  await bootstrap(kernel);
  const inspect = kernel.use("context-inspector").get("inspectContext") as () => {
    hasUse: boolean;
    hasLoad: boolean;
    hasInitialize: boolean;
    keys: string[];
    frozen: boolean;
  };
  assert.deepEqual(inspect(), {
    hasUse: true,
    hasLoad: false,
    hasInitialize: false,
      keys: ["use", "kind", "capability", "onDispose", "diagnostic"],
    frozen: true,
  });
});

test("diagnostics are optional no-op observability and custom reporters receive events", async () => {
  const source = `export default function createModule(ctx) {
    ctx.diagnostic.record({ event: "module.created", actor: "System", action: "Create module", status: "success" });
    return { answer: 42 };
  }`;
  const withoutReporter = new Kernel();
  await withoutReporter.load(await fixture({ name: "diagnostic-noop", source }));
  await bootstrap(withoutReporter);
  assert.equal(withoutReporter.use("diagnostic-noop").get("answer"), 42);

  const events: string[] = [];
  const withReporter = new Kernel({ diagnostic: { record(action) { events.push(action.event); } } });
  await withReporter.load(await fixture({ name: "diagnostic-reported", source }));
  await bootstrap(withReporter);
  assert.equal(withReporter.use("diagnostic-reported").get("answer"), 42);
  assert.deepEqual(events, ["module.created"]);
});

test("get commands operate on the exact same module instance", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "character",
    exports: { get: ["damage", "hp"] },
    source: `export default function createModule(ctx) {
      let currentHp = 10;
      const api = { hp: () => currentHp, damage(amount) { currentHp -= amount; } };
      return api;
    }`,
  }));
  await bootstrap(kernel);
  const character = kernel.use("character");
  (character.get("damage") as (amount: number) => void)(5);
  assert.equal((character.get("hp") as () => number)(), 5);
});

for (const [kind, invalidName, invalidValue] of [
  ["server", "start", "42"],
] as const) {
  test(`${kind} contract requires ${invalidName} to be a function`, async () => {
    const declared = contracts[kind] as string[];
    const properties = declared.map((name) => `${JSON.stringify(name)}: ${name === invalidName ? invalidValue : "() => undefined"}`).join(",");
    const kernel = new Kernel();
    await kernel.load(await fixture({
        name: `invalid-${kind}-function`, kind, exports: { get: declared },
        source: `export default function createModule(ctx) { return { ${properties} }; }`,
    }));
    await assert.rejects(
      bootstrap(kernel, kind !== "server"),
      new RegExp(`'${invalidName}' must be a function`),
    );
  });
}

for (const operation of ["start", "stop", "route", "middleware"] as const) {
  test(`server contract rejects missing ${operation}`, async () => {
    const kernel = new Kernel();
    const remaining = contracts.server!.filter((name) => name !== operation);
    await kernel.load(await fixture({ name: `base-missing-${operation}`, kind: "server", exports: { get: remaining } }));
    await assert.rejects(bootstrap(kernel, false), new RegExp(`'${operation}' must be declared in exports.get`));
  });

  test(`server contract rejects non-function ${operation}`, async () => {
    const kernel = new Kernel();
    const properties = contracts.server!.map((name) =>
      `${JSON.stringify(name)}: ${name === operation ? "42" : "() => undefined"}`,
    ).join(",");
    await kernel.load(await fixture({
      name: `base-value-${operation}`, kind: "server", exports: { get: contracts.server },
      source: `export default function() { return { ${properties} }; }`,
    }));
    await assert.rejects(bootstrap(kernel, false), new RegExp(`'${operation}' must be a function`));
  });
}

test("server contract rejects a missing HTTP provider", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "missing-http", kind: "server", exports: { get: contracts.server!.filter((name) => name !== "http") } }));
  await assert.rejects(bootstrap(kernel, false), /'http' must be declared in exports.get/);
});

test("server accepts an opaque HTTP provider", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "opaque-http", kind: "server", exports: { get: contracts.server },
    source: "export default function() { return { start() {}, stop() {}, http: { adapter: 'test' }, route() {}, middleware() {} }; }",
  }));
  await loadRequiredKinds(kernel, false);
  await assert.doesNotReject(kernel.initialize());
});

for (const kind of ["chat", "dice-engine", "assets", "storage"] as const) {
  test(`${kind} enforces its complete minimum contract`, async () => {
    const required = contracts[kind]!;
    for (const missing of required) {
      const kernel = new Kernel();
      await kernel.load(await fixture({ name: `${kind}-without-${missing}`, kind, exports: { get: required.filter((name) => name !== missing) } }));
      await loadRequiredKinds(kernel);
      await assert.rejects(kernel.initialize(), new RegExp(`'${missing}' must be declared in exports.get`));
    }
    const valid = new Kernel();
    await valid.load(await fixture({ name: `valid-${kind}`, kind, exports: { get: required } }));
    await loadRequiredKinds(valid);
    await assert.doesNotReject(valid.initialize());
  });
}

test("ruleset, backend and addon require no universal domain exports", async () => {
  const kernel = new Kernel();
  await kernel.load(await validKind("server"));
  await kernel.load(await validKind("room"));
  await kernel.load(await fixture({ name: "empty-ruleset", kind: "ruleset", exports: { get: [] } }));
  await kernel.load(await fixture({ name: "empty-backend", kind: "backend", exports: { get: [] } }));
  await kernel.load(await fixture({ name: "empty-addon", kind: "addon", exports: { get: [] } }));
  await assert.doesNotReject(kernel.initialize());
});

     test("initialize starts the unique server exactly once and awaits it", async () => {
  const key = `__gravewright_start_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = { calls: 0, resolved: false };
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "awaited-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() { globalThis.${key}.calls += 1; return new Promise(resolve => setTimeout(() => { globalThis.${key}.resolved = true; resolve(); }, 10)); },
      stop() {}, http: {}, route() {}, middleware() {}
    }; }`,
  }));
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], { calls: 1, resolved: true });
  delete (globalThis as Record<string, unknown>)[key];
});

test("initialize propagates a base start failure", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "failing-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return { start() { throw new Error("base failed"); }, stop() {}, http: {}, route() {}, middleware() {} }; }`,
  }));
  await loadRequiredKinds(kernel, false);
  await assert.rejects(kernel.initialize(), /base failed/);
});

test("initialize rejects multiple server implementations before starting either", async () => {
  const key = `__gravewright_multiple_base_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  for (const name of ["express-like-base", "fastify-like-base"]) {
    await kernel.load(await fixture({
      name, kind: "server", exports: { get: contracts.server },
      source: `export default function() { return { start() { globalThis.${key} += 1; }, stop() {}, http: {}, route() {}, middleware() {} }; }`,
    }));
  }
  await loadRequiredKinds(kernel, false);
  await assert.rejects(
    kernel.initialize(),
    /Multiple active modules implement singleton kind "server": express-like-base, fastify-like-base/,
  );
  assert.equal((globalThis as Record<string, unknown>)[key], 0);
  delete (globalThis as Record<string, unknown>)[key];
});

test("initialize is one-shot and does not start the server twice", async () => {
  const key = `__gravewright_one_shot_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "one-shot-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return { start() { globalThis.${key} += 1; }, stop() {}, http: {}, route() {}, middleware() {} }; }`,
  }));
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  await assert.rejects(kernel.initialize(), /Kernel already initialized/);
  assert.equal((globalThis as Record<string, unknown>)[key], 1);
  delete (globalThis as Record<string, unknown>)[key];
});

test("load rejects modules after successful initialization", async () => {
  const kernel = new Kernel();
  const lateModule = await fixture({ name: "late-module" });
  await bootstrap(kernel);
  await assert.rejects(kernel.load(lateModule), /Cannot load modules after kernel initialization/);
});

test("failed initialization does not set the one-shot flag", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "dependent", dependencies: { dependency: "^1.0.0" } }));
  await loadRequiredKinds(kernel);
  await assert.rejects(kernel.initialize(), /requires missing dependency "dependency"/);
  await kernel.load(await fixture({ name: "dependency" }));
  await assert.doesNotReject(kernel.initialize());
});

test("composes middleware and slots before starting the base", async () => {
  const key = `__gravewright_composition_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "composition-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      http: {}, route(name, handler) { globalThis.${key}.push(["route", name, typeof handler]); return () => {}; },
      middleware(name, handler) { globalThis.${key}.push(["middleware", name, typeof handler]); return () => {}; },
      slot(name, value) { globalThis.${key}.push(["slot", name, value]); return () => {}; },
      start() { globalThis.${key}.push(["start"]); }, stop() {}
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "composition-room", kind: "room", exports: { get: contracts.room },
    source: `export default function() { return { mount() {}, unmount() {}, slots(name, module, value) { globalThis.${key}.push(["slot", name, value]); return () => {}; } }; }`,
  }));
  await kernel.load(await fixture({
    name: "composed-module", routes: { "/foo": "foo" }, middleware: { "/foo": ["before"] }, slots: { app: ["panel"] },
    exports: { get: ["foo", "before", "panel"] },
    source: `export default function() { return { foo() {}, before() {}, panel: "content" }; }`,
  }));
  await kernel.load(await validKind("ruleset"));
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], [
    ["middleware", "/foo", "function"], ["route", "/foo", "function"], ["slot", "app", "content"], ["start"],
  ]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("registers multiple values in the same slot", async () => {
  const key = `__gravewright_slots_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "slot-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      http: {}, route() { return () => {}; }, middleware() { return () => {}; }, start() {}, stop() {}
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "slot-room", kind: "room", exports: { get: contracts.room },
    source: `export default function() { return { mount() {}, unmount() {}, slots(name, module, value) { globalThis.${key}.push([name, value]); return () => {}; } }; }`,
  }));
  for (const [name, exportName, value] of [["ui-a", "foo", "A"], ["ui-b", "bar", "B"]] as const) {
    await kernel.load(await fixture({
      name, slots: { app: [exportName] }, exports: { get: [exportName] },
      source: `export default function() { return { ${exportName}: "${value}" }; }`,
    }));
  }
  await kernel.load(await validKind("ruleset"));
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], [["app", "A"], ["app", "B"]]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("rejects middleware outside exports.get", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "bad-middleware-access", middleware: { "/foo": ["foo"] }, exports: { get: [] } }));
  await assert.rejects(bootstrap(kernel), /Invalid middleware.*'foo' must be declared in exports.get/);
});

test("rejects middleware whose value is not a function", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "bad-middleware-value", middleware: { "/foo": ["foo"] }, exports: { get: ["foo"] },
    source: `export default function() { return { foo: 123 }; }`,
  }));
  await assert.rejects(bootstrap(kernel), /Invalid middleware.*'foo' must be a function/);
});

test("rejects routes outside exports.get", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "bad-route-access", routes: { "/foo": "foo" }, exports: { get: [] } }));
  await assert.rejects(bootstrap(kernel), /Invalid route.*'foo' must be declared in exports.get/);
});

test("rejects a route whose value is not a function", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "bad-route-value", routes: { "/foo": "foo" }, exports: { get: ["foo"] },
    source: `export default function() { return { foo: 123 }; }`,
  }));
  await assert.rejects(bootstrap(kernel), /Invalid route.*'foo' must be a function/);
});

test("rejects a slot export missing from the instance", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "missing-slot-value", slots: { app: ["foo"] }, exports: { get: ["foo"] },
    source: `export default function() { return {}; }`,
  }));
  await assert.rejects(bootstrap(kernel), /Declared export does not exist: missing-slot-value.foo/);
});

test("rejects slot values outside exports.get", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "bad-slot-access", slots: { app: ["foo"] }, exports: { get: [] } }));
  await assert.rejects(bootstrap(kernel), /Invalid slot 'app'.*'foo' must be declared in exports.get/);
});

test("rejects an empty middleware mount", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "empty-mount", middleware: { "": ["foo"] }, exports: { get: ["foo"] } })),
    /middleware mounts must be non-empty strings/,
  );
});

test("rejects empty route mounts and export names", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "empty-route-mount", routes: { "": "foo" }, exports: { get: ["foo"] } })),
    /route mounts must be non-empty strings/,
  );
  await assert.rejects(
    new Kernel().load(await fixture({ name: "empty-route-export", routes: { "/foo": "" }, exports: { get: ["foo"] } })),
    /route export for mount '\/foo' must be a non-empty string/,
  );
});

test("rejects an empty middleware export name", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "empty-middleware-export", middleware: { "/foo": [""] }, exports: { get: ["foo"] } })),
    /middleware\.\/foo must be an array of non-empty strings/,
  );
});

test("rejects duplicate middleware exports within one mount", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "duplicate-middleware", middleware: { "/foo": ["auth", "auth"] }, exports: { get: ["auth"] } })),
    /middleware mount '\/foo' must not contain duplicate names/,
  );
});

test("allows middleware from different modules on the same mount in module order", async () => {
  const key = `__gravewright_shared_middleware_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "shared-middleware-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      http: {}, middleware(mount, handler) { globalThis.${key}.push(handler()); return () => {}; }, route() { return () => {}; }, start() {}, stop() {}
    }; }`,
  }));
  for (const [name, exportName] of [["middleware-a", "first"], ["middleware-b", "second"]] as const) {
    await kernel.load(await fixture({
      name, middleware: { "/same": [exportName] }, exports: { get: [exportName] },
      source: `export default function() { return { ${exportName}() { return "${exportName}"; } }; }`,
    }));
  }
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["first", "second"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("rejects duplicate exports within one slot", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "duplicate-slot", slots: { app: ["foo", "foo"] }, exports: { get: ["foo"] } })),
    /slot 'app' must not contain duplicate names/,
  );
});

test("manifest rejects duplicate names inside exports.get", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({
      name: "duplicate-get",
      exports: { get: ["foo", "foo"] },
    })),
    /duplicate export 'foo' in exports.get/,
  );
});

test("module entry must default-export a factory", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "not-a-factory", source: "export const answer = 42;" }));
  await loadRequiredKinds(kernel);
  await assert.rejects(
    kernel.initialize(),
    /must default-export a factory/,
  );
});

test("accepts a valid SemVer module version", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "semver-valid", version: "1.2.3" }));
  await bootstrap(kernel);
  assert.equal(kernel.use("semver-valid").get("answer"), 42);
});

test("rejects an invalid module SemVer version", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "semver-invalid", version: "banana" })),
    /version 'banana' is not valid SemVer/,
  );
});

test("rejects an invalid dependency SemVer range", async () => {
  await assert.rejects(
    new Kernel().load(await fixture({ name: "bad-range", dependencies: { dice: "not-a-range" } })),
    /dependency 'dice' has invalid SemVer range/,
  );
});

test("instantiates a simple dependency before its dependent regardless of load order", async () => {
  const key = `__gravewright_order_${crypto.randomUUID().replaceAll("-", "")}`;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "order-b", dependencies: { "order-a": "^1.0.0" },
    source: `export default function(ctx) { globalThis.${key}.push("B"); return { answer: 42 }; }`,
  }));
  await kernel.load(await fixture({
    name: "order-a",
    source: `export default function(ctx) { globalThis.${key}.push("A"); return { answer: 42 }; }`,
  }));
  (globalThis as Record<string, unknown>)[key] = [];
  await bootstrap(kernel);
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["A", "B"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("imports entries and runs factories in topological order", async () => {
  const key = `__gravewright_import_${crypto.randomUUID().replaceAll("-", "")}`;
  const kernel = new Kernel();
  (globalThis as Record<string, unknown>)[key] = [];
  await kernel.load(await fixture({
    name: "evaluated-b", dependencies: { "evaluated-a": "^1.0.0" },
    source: `globalThis.${key}.push("B:import");
      export default function(ctx) { globalThis.${key}.push("B:factory"); return { answer: 42 }; }`,
  }));
  await kernel.load(await fixture({
    name: "evaluated-a",
    source: `globalThis.${key}.push("A:import");
      export default function(ctx) { globalThis.${key}.push("A:factory"); return { answer: 42 }; }`,
  }));
  assert.deepEqual((globalThis as Record<string, unknown>)[key], []);
  await bootstrap(kernel);
  assert.deepEqual((globalThis as Record<string, unknown>)[key], [
    "A:import", "A:factory", "B:import", "B:factory",
  ]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("instantiates a dependency chain in topological order", async () => {
  const key = `__gravewright_chain_${crypto.randomUUID().replaceAll("-", "")}`;
  const kernel = new Kernel();
  for (const [name, dependencies] of [
    ["chain-c", { "chain-b": "^1.0.0" }],
    ["chain-b", { "chain-a": "^1.0.0" }],
    ["chain-a", undefined],
  ] as const) {
    await kernel.load(await fixture({
      name, dependencies,
      source: `export default function(ctx) { globalThis.${key}.push("${name.at(-1)!.toUpperCase()}"); return { answer: 42 }; }`,
    }));
  }
  (globalThis as Record<string, unknown>)[key] = [];
  await bootstrap(kernel);
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["A", "B", "C"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("rejects a missing dependency", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "needs-dice", dependencies: { dice: "^1.0.0" } }));
  await assert.rejects(kernel.initialize(), /Module "needs-dice" requires missing dependency "dice"/);
});

test("rejects an incompatible dependency version", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "consumer", dependencies: { library: "^2.0.0" } }));
  await kernel.load(await fixture({ name: "library", version: "1.0.0" }));
  await assert.rejects(kernel.initialize(), /requires "library" \^2\.0\.0, but 1\.0\.0 is loaded/);
});

test("accepts a compatible dependency version", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "consumer", dependencies: { library: "^1.0.0" } }));
  await kernel.load(await fixture({ name: "library", version: "1.5.0" }));
  await bootstrap(kernel);
  assert.equal(kernel.use("consumer").get("answer"), 42);
});

for (const cycle of [
  ["cycle-a", "cycle-b"],
  ["large-a", "large-b", "large-c"],
]) {
  test(`rejects circular dependency ${cycle.join(" -> ")}`, async () => {
    const kernel = new Kernel();
    for (let index = 0; index < cycle.length; index += 1) {
      const next = cycle[(index + 1) % cycle.length]!;
      await kernel.load(await fixture({ name: cycle[index]!, dependencies: { [next]: "^1.0.0" } }));
    }
    await assert.rejects(kernel.initialize(), /Circular dependency detected:/);
  });
}

test("rejects a module depending on itself", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "self", dependencies: { self: "^1.0.0" } }));
  await assert.rejects(kernel.initialize(), /Module "self" cannot depend on itself/);
});

test("independent modules retain deterministic insertion order", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "independent-a" }));
  await kernel.load(await fixture({ name: "independent-b" }));
  await bootstrap(kernel);
  assert.equal(kernel.use("independent-a").get("answer"), 42);
  assert.equal(kernel.use("independent-b").get("answer"), 42);
});

test("disabled modules never evaluate their entry or factory", async () => {
  const key = `__gravewright_disabled_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "disabled-code",
    source: `globalThis.${key} += 1; export default function() { globalThis.${key} += 1; return { answer: 42 }; }`,
  }), { state: "disabled" });
  await bootstrap(kernel);
  assert.equal((globalThis as Record<string, unknown>)[key], 0);
  assert.throws(() => kernel.use("disabled-code"), /Module "disabled-code" is not active/);
  delete (globalThis as Record<string, unknown>)[key];
});

test("active dependency cannot resolve to an installed but disabled module", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "active-consumer", dependencies: { "disabled-library": "^1.0.0" } }));
  await kernel.load(await fixture({ name: "disabled-library" }), { state: "disabled" });
  await loadRequiredKinds(kernel);
  await assert.rejects(kernel.initialize(), /requires dependency "disabled-library", but "disabled-library" is disabled/);
});

test("required server considers only active definitions", async () => {
  const kernel = new Kernel();
  await kernel.load(await validKind("server"), { state: "disabled" });
  await assert.rejects(kernel.initialize(), /Missing active module for required kind "server"/);
});

test("one active and one disabled server is valid", async () => {
  const kernel = new Kernel();
  await kernel.load(await validKind("server", "active-base"));
  await kernel.load(await validKind("server", "disabled-base"), { state: "disabled" });
  await loadRequiredKinds(kernel, false);
  await assert.doesNotReject(kernel.initialize());
});

  test("slot activation and disable use the module's disposer", async () => {
  const key = `__gravewright_dynamic_slot_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "dynamic-slot-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() {}, stop() {}, http: {}, route() { return () => {}; }, middleware() { return () => {}; }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "dynamic-slot-room", kind: "room", exports: { get: contracts.room },
    source: `export default function() { return { mount() {}, unmount() {}, slots(name, module, value) { globalThis.${key}.push(value); return () => { const i = globalThis.${key}.indexOf(value); if (i >= 0) globalThis.${key}.splice(i, 1); }; } }; }`,
  }));
  await kernel.load(await fixture({
    name: "dynamic-slot", slots: { app: ["content"] }, exports: { get: ["content"] },
    source: `export default function() { return { content: "panel" }; }`,
  }), { state: "disabled" });
  await kernel.load(await validKind("ruleset"));
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], []);
  await kernel.activate("dynamic-slot");
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["panel"]);
  await kernel.disable("dynamic-slot");
  assert.deepEqual((globalThis as Record<string, unknown>)[key], []);
  await kernel.activate("dynamic-slot");
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["panel"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("failed activation rolls back middleware, instance and partial composition", async () => {
  const key = `__gravewright_atomic_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "atomic-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { const routes = new Set(["/conflict"]); return {
      start() {}, stop() {}, http: {},
      middleware(name, value) { globalThis.${key}.push("middleware"); return () => globalThis.${key}.splice(globalThis.${key}.indexOf("middleware"), 1); },
      route(name) { if (routes.has(name)) throw new Error("route conflict"); routes.add(name); return () => routes.delete(name); },
      slot(name, value) { globalThis.${key}.push("slot"); return () => globalThis.${key}.splice(globalThis.${key}.indexOf("slot"), 1); }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "atomic-module", middleware: { "/": ["before"] }, routes: { "/conflict": "route" }, slots: { app: ["content"] },
    exports: { get: ["before", "route", "content"] },
    source: `export default function() { return { before() {}, route() {}, content: "panel" }; }`,
  }), { state: "disabled" });
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  await assert.rejects(kernel.activate("atomic-module"), /route conflict/);
  assert.deepEqual((globalThis as Record<string, unknown>)[key], []);
  assert.throws(() => kernel.use("atomic-module"), /Module "atomic-module" is not active/);
  delete (globalThis as Record<string, unknown>)[key];
});

test("cannot disable an active dependency or the active server, but room is optional", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "library" }));
  await kernel.load(await fixture({ name: "consumer", dependencies: { library: "^1.0.0" } }));
  const basePath = await validKind("server", "protected-base");
  const roomPath = await validKind("room", "protected-room");
  await kernel.load(basePath);
  await kernel.load(roomPath);
  await kernel.load(await validKind("ruleset"));
  await kernel.load(await validKind("backend"));
  await kernel.initialize();
  await assert.rejects(kernel.disable("library"), /active module "consumer" depends on it/);
  await assert.doesNotReject(kernel.disable("protected-room"));
  await assert.rejects(kernel.disable("protected-base"), /Cannot disable the active server while the kernel is running/);
});

test("load defaults to disabled without importing or instantiating the module", async () => {
  const key = `__gravewright_default_disabled_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new RuntimeKernel();
  await kernel.load(await fixture({
    name: "default-disabled",
    source: `globalThis.${key} += 1; export default function() { globalThis.${key} += 1; return { answer: 42 }; }`,
  }));
  for (const kind of ["server", "room", "ruleset", "backend"] as const) {
    await kernel.load(await validKind(kind, `default-${kind}`), { state: "active" });
  }
  await kernel.initialize();
  assert.equal((globalThis as Record<string, unknown>)[key], 0);
  assert.throws(() => kernel.use("default-disabled"), /Module "default-disabled" is not active/);
  delete (globalThis as Record<string, unknown>)[key];
});

test("ModuleRef resolves the current instance and is unavailable only while disabled", async () => {
  const key = `__gravewright_ref_instance_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "logical-handle", exports: { get: ["instanceId", "value"] },
    source: `export default function() { return { instanceId: ++globalThis.${key}, value: 10 }; }`,
  }));
  await bootstrap(kernel);
  const ref = kernel.use("logical-handle");
  assert.equal(ref.get("instanceId"), 1);
  await kernel.disable("logical-handle");
  assert.throws(() => ref.get("instanceId"), /Module "logical-handle" is not active/);
  await kernel.activate("logical-handle");
  assert.equal(ref.get("instanceId"), 2);
  assert.equal(ref.get("value"), 10);
  delete (globalThis as Record<string, unknown>)[key];
});

test("host admin helpers persist successful activation and disable", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "admin-module" }), { state: "disabled" });
  await bootstrap(kernel);
  const states = new Map<string, "active" | "disabled">();
  const store: ModuleStateStore = {
    get: (name) => states.get(name) ?? "disabled",
    async set(name, state) { states.set(name, state); },
  };
  await activateModule(kernel, store, "admin-module");
  assert.equal(kernel.use("admin-module").get("answer"), 42);
  assert.equal(store.get("admin-module"), "active");
  await disableModule(kernel, store, "admin-module");
  assert.throws(() => kernel.use("admin-module"), /not active/);
  assert.equal(store.get("admin-module"), "disabled");
});

test("activateModule rolls runtime back when persistence fails", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "activate-rollback" }), { state: "disabled" });
  await bootstrap(kernel);
  const failure = new Error("state write failed");
  const store: ModuleStateStore = { get: () => "disabled", async set() { throw failure; } };
  await assert.rejects(activateModule(kernel, store, "activate-rollback"), failure);
  assert.throws(() => kernel.use("activate-rollback"), /not active/);
});

test("disableModule reactivates the module when persistence fails", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "disable-rollback" }));
  await bootstrap(kernel);
  const failure = new Error("state write failed");
  const store: ModuleStateStore = { get: () => "active", async set() { throw failure; } };
  await assert.rejects(disableModule(kernel, store, "disable-rollback"), failure);
  assert.equal(kernel.use("disable-rollback").get("answer"), 42);
});

test("admin helper exposes persistence and rollback failures together", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "double-failure" }), { state: "disabled" });
  await bootstrap(kernel);
  const persistenceError = new Error("state write failed");
  const rollbackError = new Error("rollback failed");
  const originalDisable = kernel.disable.bind(kernel);
  kernel.disable = async (name: string) => {
    if (name === "double-failure") throw rollbackError;
    await originalDisable(name);
  };
  const store: ModuleStateStore = { get: () => "disabled", async set() { throw persistenceError; } };
  await assert.rejects(
    activateModule(kernel, store, "double-failure"),
    (error: unknown) => error instanceof AggregateError
      && error.message === 'Failed to persist module state for "double-failure" and rollback also failed'
      && error.errors[0] === persistenceError
      && error.errors[1] === rollbackError,
  );
});

test("load rejects an entry symlink escaping its module directory", async () => {
  const directory = await fixture({ name: "entry-symlink" });
  const entry = path.join(directory, "index.ts");
  const outside = path.join(path.dirname(directory), `outside-${crypto.randomUUID()}.ts`);
  await writeFile(outside, "export default function() { return { answer: 42 }; }\n");
  await unlink(entry);
  await symlink(outside, entry);
  const kernel = new RuntimeKernel();
  await assert.rejects(kernel.load(directory, { state: "active" }), /entry must stay inside the module directory/);
});

test("activate factory failure leaves the module disabled and unregistered", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "throwing-activation",
    source: 'export default function() { throw new Error("factory exploded"); }',
  }), { state: "disabled" });
  await bootstrap(kernel);
  await assert.rejects(kernel.activate("throwing-activation"), /factory exploded/);
  assert.throws(() => kernel.use("throwing-activation"), /not active/);
});

test("disable commits removal after teardown starts even when cleanup fails", async () => {
  const key = `__gravewright_dispose_failure_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "cleanup-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() {}, stop() {}, http: {},
      middleware() { return () => { globalThis.${key}.push("middleware"); }; },
      route() { return () => { globalThis.${key}.push("route"); throw new Error("route cleanup failed"); }; }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "cleanup-room", kind: "room", exports: { get: contracts.room },
    source: `export default function() { return { mount() {}, unmount() {}, slots() { return () => { globalThis.${key}.push("slot"); throw new Error("slot cleanup failed"); }; } }; }`,
  }));
  await kernel.load(await fixture({
    name: "cleanup-module", middleware: { "/": ["middleware"] }, routes: { "/cleanup": "route" },
    slots: { app: ["content"] }, exports: { get: ["middleware", "route", "content", "answer"] },
    source: "export default function() { return { middleware() {}, route() {}, content: 'panel', answer: 42 }; }",
  }));
  await kernel.load(await validKind("ruleset"));
  await kernel.initialize();
  await assert.rejects(
    kernel.disable("cleanup-module"),
    (error: unknown) => error instanceof AggregateError && error.errors.length === 2,
  );
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["slot", "route", "middleware"]);
  assert.throws(() => kernel.use("cleanup-module"), /Module "cleanup-module" is not active/);
  await assert.doesNotReject(kernel.shutdown());
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["slot", "route", "middleware"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("failed disable removes capability providers and disposes module resources at most once", async () => {
  const key = `__gravewright_failed_disable_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await validKind("server"));
  await kernel.load(await fixture({
    name: "failing-provider", provides: { "gravewright.test": "1.0.0" },
    source: `export default function(ctx) {
      ctx.onDispose(() => globalThis.${key}.push("resource-first"));
      ctx.onDispose(() => { globalThis.${key}.push("resource-second"); throw new Error("resource cleanup failed"); });
      return { answer: 42 };
    }`,
  }));
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  await assert.rejects(kernel.disable("failing-provider"), /resource cleanup failed/);
  assert.throws(() => kernel.use("failing-provider"), /not active/);
  assert.equal(kernel.plan().capabilities["gravewright.test"], undefined);
  await assert.doesNotReject(kernel.shutdown());
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["resource-second", "resource-first"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("composition fails when a server registrar does not provide its required disposer", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "invalid-registrar-base", kind: "server", exports: { get: contracts.server },
    source: "export default function() { return { start() {}, stop() {}, http: {}, middleware() { return () => {}; }, route() {} }; }",
  }));
  await kernel.load(await fixture({
    name: "needs-disposer", routes: { "/invalid": "route" }, exports: { get: ["route"] },
    source: "export default function() { return { route() {} }; }",
  }));
  await loadRequiredKinds(kernel, false);
  await assert.rejects(kernel.initialize(), /Base route registrar did not return a disposer/);
  assert.throws(() => kernel.use("needs-disposer"), /not active/);
});

test("admin rollback does not invert runtime when the requested state was already applied", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "already-active" }));
  await kernel.load(await fixture({ name: "already-disabled" }), { state: "disabled" });
  await bootstrap(kernel);
  const failure = new Error("state write failed");
  const store: ModuleStateStore = { get: () => "disabled", async set() { throw failure; } };
  await assert.rejects(activateModule(kernel, store, "already-active"), failure);
  assert.equal(kernel.use("already-active").get("answer"), 42);
  await assert.rejects(disableModule(kernel, store, "already-disabled"), failure);
  assert.throws(() => kernel.use("already-disabled"), /not active/);
});

test("concurrent activation attempts are serialized and instantiate once", async () => {
  const key = `__gravewright_concurrent_activation_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "concurrent-activation",
    source: `export default function() { globalThis.${key} += 1; return { answer: 42 }; }`,
  }), { state: "disabled" });
  await bootstrap(kernel);
  await Promise.all([kernel.activate("concurrent-activation"), kernel.activate("concurrent-activation")]);
  assert.equal((globalThis as Record<string, unknown>)[key], 1);
  assert.equal(kernel.use("concurrent-activation").get("answer"), 42);
  delete (globalThis as Record<string, unknown>)[key];
});

test("module resources dispose in reverse order during shutdown after server stop", async () => {
  const key = `__gravewright_shutdown_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "shutdown-server", kind: "server", exports: { get: contracts.server },
    source: `export default function(ctx) { ctx.onDispose(() => globalThis.${key}.push("server-resource")); return {
      start() {}, stop() { globalThis.${key}.push("server-stop"); }, http: {},
      route() { return () => {}; }, middleware() { return () => {}; }
    }; }`,
  }));
  await kernel.load(await fixture({ name: "resource-owner", source: `export default function(ctx) {
    ctx.onDispose(() => globalThis.${key}.push("first"));
    ctx.onDispose(() => globalThis.${key}.push("second"));
    return { answer: 42 };
  }` }));
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  await kernel.shutdown();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["server-stop", "second", "first", "server-resource"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("create failure rolls back registered resources", async () => {
  const key = `__gravewright_create_rollback_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await validKind("server"));
  await kernel.load(await fixture({ name: "created-first", source: `export default function(ctx) {
    ctx.onDispose(() => globalThis.${key}.push("previous")); return { answer: 42 };
  }` }));
  await kernel.load(await fixture({ name: "broken-resource", source: `export default function(ctx) {
    ctx.onDispose(() => globalThis.${key}.push("first"));
    ctx.onDispose(() => globalThis.${key}.push("second"));
    throw new Error("create failed");
  }` }));
  await loadRequiredKinds(kernel, false);
  await assert.rejects(kernel.initialize(), /create failed/);
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["second", "first", "previous"]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("activation plan rejects route conflicts before factories execute", async () => {
  const key = `__gravewright_plan_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  await kernel.load(await validKind("server"));
  for (const name of ["route-a", "route-b"]) await kernel.load(await fixture({
    name, routes: { "/same": "handler" }, exports: { get: ["handler"] },
    source: `export default function() { globalThis.${key} += 1; return { handler() {} }; }`,
  }));
  assert.throws(() => kernel.plan(), /Route conflict/);
  await assert.rejects(kernel.initialize(), /Route conflict/);
  assert.equal((globalThis as Record<string, unknown>)[key], 0);
  delete (globalThis as Record<string, unknown>)[key];
});

test("incremental activation rejects a duplicate capability provider without disturbing the active provider", async () => {
  const key = `__gravewright_capability_activation_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = 0;
  const kernel = new Kernel();
  await kernel.load(await validKind("server"));
  await kernel.load(await fixture({
    name: "provider-a", provides: { "gravewright.incremental": "1.0.0" }, exports: { get: ["identity"] },
    source: `export default function() { return { identity: "A" }; }`,
  }));
  await kernel.load(await fixture({
    name: "capability-consumer", requires: { "gravewright.incremental": "^1.0.0" }, exports: { get: ["provider"] },
    source: `export default function(ctx) { const provider = ctx.capability("gravewright.incremental"); return { provider: () => provider.get("identity") }; }`,
  }));
  await kernel.load(await fixture({
    name: "provider-b", provides: { "gravewright.incremental": "1.1.0" }, exports: { get: ["identity"] },
    source: `export default function() { globalThis.${key} += 1; return { identity: "B" }; }`,
  }), { state: "disabled" });
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();

  const provider = kernel.use("capability-consumer").get("provider") as () => string;
  assert.equal(provider(), "A");
  await assert.rejects(kernel.activate("provider-b"), /multiple active providers/);
  assert.equal((globalThis as Record<string, unknown>)[key], 0);
  assert.throws(() => kernel.use("provider-b"), /not active/);
  assert.equal(provider(), "A");
  delete (globalThis as Record<string, unknown>)[key];
});

test("incremental activation rejects a route conflict before registration", async () => {
  const key = `__gravewright_route_activation_${crypto.randomUUID().replaceAll("-", "")}`;
  const state = { routes: new Map<string, () => string>(), createdB: 0 };
  (globalThis as Record<string, unknown>)[key] = state;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "route-server", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() {}, stop() {}, http: {}, middleware() { return () => {}; },
      route(mount, handler) { globalThis.${key}.routes.set(mount, handler); return () => globalThis.${key}.routes.delete(mount); }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "route-active", routes: { "/x": "handler" }, exports: { get: ["handler"] },
    source: `export default function() { return { handler: () => "A" }; }`,
  }));
  await kernel.load(await fixture({
    name: "route-disabled", routes: { "/x": "handler" }, exports: { get: ["handler"] },
    source: `export default function() { globalThis.${key}.createdB += 1; return { handler: () => "B" }; }`,
  }), { state: "disabled" });
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  assert.equal(state.routes.get("/x")?.(), "A");

  await assert.rejects(kernel.activate("route-disabled"), /Route conflict/);
  assert.equal(state.createdB, 0);
  assert.throws(() => kernel.use("route-disabled"), /not active/);
  assert.equal(state.routes.size, 1);
  assert.equal(state.routes.get("/x")?.(), "A");
  delete (globalThis as Record<string, unknown>)[key];
});

test("incremental activation rejects a single-contribution slot conflict before registration", async () => {
  const key = `__gravewright_slot_activation_${crypto.randomUUID().replaceAll("-", "")}`;
  const state = { slots: [] as unknown[], createdB: 0 };
  (globalThis as Record<string, unknown>)[key] = state;
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "slot-server", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() {}, stop() {}, http: {}, route() { return () => {}; }, middleware() { return () => {}; }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "slot-room", kind: "room", exports: { get: contracts.room },
    exposes: { slots: [
      ...ROOM_SLOT_NAMES.map((name) => ({ name, mounts: "one" as const, contributions: "many" as const })),
      { name: "gw-renderer", mounts: "one", contributions: "one" },
    ] }, source: `export default function() { return { mount() {}, unmount() {}, slots(_name, _module, value) { globalThis.${key}.slots.push(value); return () => { const index = globalThis.${key}.slots.indexOf(value); if (index >= 0) globalThis.${key}.slots.splice(index, 1); }; } }; }`,
  }));
  await kernel.load(await fixture({
    name: "slot-active", slots: { "gw-renderer": ["contribution"] }, exports: { get: ["contribution"] },
    source: `export default function() { return { contribution: { id: "A", mount() {} } }; }`,
  }));
  await kernel.load(await fixture({
    name: "slot-disabled", slots: { "gw-renderer": ["contribution"] }, exports: { get: ["contribution"] },
    source: `export default function() { globalThis.${key}.createdB += 1; return { contribution: { id: "B", mount() {} } }; }`,
  }), { state: "disabled" });
  await kernel.load(await validKind("ruleset"));
  await kernel.initialize();
  assert.equal(state.slots.length, 1);
  assert.equal((state.slots[0] as { id: string }).id, "A");

  await assert.rejects(kernel.activate("slot-disabled"), /accepts only one contribution/);
  assert.equal(state.createdB, 0);
  assert.throws(() => kernel.use("slot-disabled"), /not active/);
  assert.equal(state.slots.length, 1);
  assert.equal((state.slots[0] as { id: string }).id, "A");
  delete (globalThis as Record<string, unknown>)[key];
});

test("capabilities resolve a compatible active provider", async () => {
  const kernel = new Kernel();
  await kernel.load(await validKind("server"));
  await kernel.load(await fixture({
    name: "storage-consumer", requires: { "gravewright.storage": "^1.0.0" }, exports: { get: ["readValue"] },
    source: `export default function(ctx) { const storage = ctx.capability("gravewright.storage"); return { readValue: () => storage.get("value") }; }`,
  }));
  await kernel.load(await fixture({ name: "sqlite", provides: { "gravewright.storage": "1.2.0" }, exports: { get: ["value"] }, source: "export default function() { return { value: 42 }; }" }));
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  assert.equal((kernel.use("storage-consumer").get("readValue") as () => number)(), 42);
});

test("activation plan rejects missing and ambiguous capabilities", async () => {
  const missing = new Kernel(); await missing.load(await validKind("server"));
  await missing.load(await fixture({ name: "consumer", requires: { "gravewright.storage": "^1.0.0" } }));
  assert.throws(() => missing.plan(), /requires missing capability/);

  const ambiguous = new Kernel(); await ambiguous.load(await validKind("server"));
  await ambiguous.load(await fixture({ name: "sqlite", provides: { "gravewright.storage": "1.0.0" } }));
  await ambiguous.load(await fixture({ name: "postgres", provides: { "gravewright.storage": "1.1.0" } }));
  assert.throws(() => ambiguous.plan(), /multiple active providers/);
});
