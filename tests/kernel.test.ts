import assert from "node:assert/strict";
import { mkdtemp, symlink, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { Kernel as RuntimeKernel, type LoadOptions } from "@gravewright/kernel";
import type { ModuleKind } from "@gravewright/sdk";
import { activateModule, disableModule } from "../src/module-admin.js";
import type { ModuleStateStore } from "../src/module-state.js";

// Existing tests predate the safe default and explicitly model active fixtures.
class Kernel extends RuntimeKernel {
  override async load(moduleDirectory: string, options: LoadOptions = { state: "active" }): Promise<void> {
    await super.load(moduleDirectory, options);
  }
}

const contracts: Partial<Record<ModuleKind, string[]>> = {
  server: ["start", "stop", "route", "middleware", "slot"],
};

async function fixture(options: {
  name?: string;
  kind?: ModuleKind;
  version?: string;
  dependencies?: Record<string, string>;
  routes?: Record<string, string>;
  middleware?: Record<string, string[]>;
  slots?: Record<string, string[]>;
  exports?: { get?: string[]; set?: string[]; prop?: string[] };
  source?: string;
} = {}): Promise<string> {
  const directory = await mkdtemp(path.join(tmpdir(), "vtt-module-"));
  const name = options.name ?? path.basename(directory);
  const kind = options.kind ?? "addon";
  const declared = options.exports ?? { get: ["answer"] };
  const all = [...(declared.get ?? []), ...(declared.set ?? []), ...(declared.prop ?? [])];
  const properties = [...new Set(all)].map((key) =>
    `${JSON.stringify(key)}: ${key === "answer" ? "42" : "() => undefined"}`,
  ).join(",\n");
  const source = options.source ?? `export default function createModule(ctx) { return { ${properties} }; }`;
  await writeFile(path.join(directory, "manifest.json"), JSON.stringify({
    name, kind, provider: "community", version: options.version ?? "1.0.0", entry: "./index.ts",
    ...(options.dependencies ? { dependencies: options.dependencies } : {}),
    ...(options.routes ? { routes: options.routes } : {}),
    ...(options.middleware ? { middleware: options.middleware } : {}),
    ...(options.slots ? { slots: options.slots } : {}), exports: declared,
  }));
  await writeFile(path.join(directory, "index.ts"), source);
  return directory;
}

async function validKind(kind: "server" | "campaign" | "room" | "marketplace", name = `${kind}-module`) {
  return fixture({ name, kind, exports: { get: contracts[kind] } });
}

async function bootstrap(kernel: Kernel, includeBase = true): Promise<void> {
  await loadRequiredKinds(kernel, includeBase);
  await kernel.initialize();
}

async function loadRequiredKinds(kernel: Kernel, includeBase = true): Promise<void> {
  if (includeBase) await kernel.load(await validKind("server", `base-${crypto.randomUUID()}`));
  await kernel.load(await validKind("campaign", `campaign-${crypto.randomUUID()}`));
  await kernel.load(await validKind("room", `room-${crypto.randomUUID()}`));
  await kernel.load(await validKind("marketplace", `marketplace-${crypto.randomUUID()}`));
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

test("enforces set permission", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "writes", exports: { get: ["readOnly"], set: ["writeOnly"] } }));
  await bootstrap(kernel);
  kernel.use("writes").set("writeOnly", "changed");
  assert.throws(() => kernel.use("writes").get("writeOnly"), /Get not authorized/);
  assert.throws(() => kernel.use("writes").set("readOnly", 2), /Set not authorized/);
});

test("prop permits both get and set", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "properties", exports: { prop: ["hp"] }, source: "export default function createModule(ctx) { return { hp: 10 }; }" }));
  await bootstrap(kernel);
  const ref = kernel.use("properties");
  assert.equal(ref.get("hp"), 10);
  ref.set("hp", 20);
  assert.equal(ref.get("hp"), 20);
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

test("allows multiple implementations of one kind", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "room-a", kind: "room", exports: { get: ["answer"] } }));
  await kernel.load(await fixture({ name: "room-b", kind: "room", exports: { get: ["answer"] } }));
  await bootstrap(kernel);
  assert.equal(kernel.use("room-a").get("answer"), 42);
  assert.equal(kernel.use("room-b").get("answer"), 42);
});

test("initialization requires only one active server", async () => {
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
      keys: ["use", "diagnostic"],
    frozen: true,
  });
});

test("get, set and module functions operate on the exact same instance", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "character",
    exports: { get: ["damage"], prop: ["hp"] },
    source: `export default function createModule(ctx) {
      const api = { hp: 10, damage(amount) { api.hp -= amount; } };
      return api;
    }`,
  }));
  await bootstrap(kernel);
  const character = kernel.use("character");
  character.set("hp", 20);
  (character.get("damage") as (amount: number) => void)(5);
  assert.equal(character.get("hp"), 15);
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

test("optional VTT and platform kinds have no kernel-level minimum contract", async () => {
  const kernel = new Kernel();
  for (const kind of ["campaign", "room", "marketplace", "ruleset", "system"] as const) {
    await kernel.load(await fixture({ name: `optional-${kind}`, kind, exports: { get: [] } }));
  }
  await assert.doesNotReject(bootstrap(kernel));
});

for (const operation of ["start", "stop", "route", "middleware", "slot"] as const) {
  test(`server contract rejects missing ${operation}`, async () => {
    const kernel = new Kernel();
    const remaining = contracts.server!.filter((name) => name !== operation);
    await kernel.load(await fixture({ name: `base-missing-${operation}`, kind: "server", exports: { get: remaining } }));
    await assert.rejects(bootstrap(kernel, false), new RegExp(`'${operation}' must be declared in exports.get`));
  });

  test(`server contract rejects ${operation} declared as prop`, async () => {
    const kernel = new Kernel();
    const remaining = contracts.server!.filter((name) => name !== operation);
    await kernel.load(await fixture({
      name: `base-prop-${operation}`, kind: "server", exports: { get: remaining, prop: [operation] },
    }));
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

     test("initialize starts the unique server exactly once and awaits it", async () => {
  const key = `__gravewright_start_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = { calls: 0, resolved: false };
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "awaited-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() { globalThis.${key}.calls += 1; return new Promise(resolve => setTimeout(() => { globalThis.${key}.resolved = true; resolve(); }, 10)); },
      stop() {}, route() {}, middleware() {}, slot() {}
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
    source: `export default function() { return { start() { throw new Error("base failed"); }, stop() {}, route() {}, middleware() {}, slot() {} }; }`,
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
      source: `export default function() { return { start() { globalThis.${key} += 1; }, stop() {}, route() {}, middleware() {}, slot() {} }; }`,
    }));
  }
  await loadRequiredKinds(kernel, false);
  await assert.rejects(
    kernel.initialize(),
    /Multiple active modules implement required kind "server": express-like-base, fastify-like-base/,
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
    source: `export default function() { return { start() { globalThis.${key} += 1; }, stop() {}, route() {}, middleware() {}, slot() {} }; }`,
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
      route(name, handler) { globalThis.${key}.push(["route", name, typeof handler]); return () => {}; },
      middleware(name, handler) { globalThis.${key}.push(["middleware", name, typeof handler]); return () => {}; },
      slot(name, value) { globalThis.${key}.push(["slot", name, value]); return () => {}; },
      start() { globalThis.${key}.push(["start"]); }, stop() {}
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "composed-module", routes: { "/foo": "foo" }, middleware: { "/foo": ["before"] }, slots: { app: ["panel"] },
    exports: { get: ["foo", "before", "panel"] },
    source: `export default function() { return { foo() {}, before() {}, panel: "content" }; }`,
  }));
  await loadRequiredKinds(kernel, false);
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
      route() { return () => {}; }, middleware() { return () => {}; }, slot(name, value) { globalThis.${key}.push([name, value]); return () => {}; }, start() {}, stop() {}
    }; }`,
  }));
  for (const [name, exportName, value] of [["ui-a", "foo", "A"], ["ui-b", "bar", "B"]] as const) {
    await kernel.load(await fixture({
      name, slots: { app: [exportName] }, exports: { get: [exportName] },
      source: `export default function() { return { ${exportName}: "${value}" }; }`,
    }));
  }
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  assert.deepEqual((globalThis as Record<string, unknown>)[key], [["app", "A"], ["app", "B"]]);
  delete (globalThis as Record<string, unknown>)[key];
});

test("rejects middleware outside exports.get", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "bad-middleware-access", middleware: { "/foo": ["foo"] }, exports: { prop: ["foo"] } }));
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
  await kernel.load(await fixture({ name: "bad-route-access", routes: { "/foo": "foo" }, exports: { prop: ["foo"] } }));
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
  await kernel.load(await fixture({ name: "bad-slot-access", slots: { app: ["foo"] }, exports: { prop: ["foo"] } }));
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
      middleware(mount, handler) { globalThis.${key}.push(handler()); return () => {}; }, route() { return () => {}; }, slot() { return () => {}; }, start() {}, stop() {}
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

for (const [first, second] of [["get", "set"], ["get", "prop"], ["set", "prop"]] as const) {
  test(`manifest rejects exports.${first} + exports.${second} overlap`, async () => {
    await assert.rejects(
      new Kernel().load(await fixture({ name: `overlap-${first}-${second}`, exports: { [first]: ["hp"], [second]: ["hp"] } })),
      /export 'hp' overlaps/,
    );
  });
}

for (const category of ["get", "set", "prop"] as const) {
  test(`manifest rejects duplicate names inside exports.${category}`, async () => {
    await assert.rejects(
      new Kernel().load(await fixture({
        name: `duplicate-${category}`,
        exports: { [category]: ["foo", "foo"] },
      })),
      new RegExp(`duplicate export 'foo' in exports.${category}`),
    );
  });
}

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
      start() {}, stop() {}, route() { return () => {}; }, middleware() { return () => {}; },
      slot(name, value) { globalThis.${key}.push(value); return () => { const i = globalThis.${key}.indexOf(value); if (i >= 0) globalThis.${key}.splice(i, 1); }; }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "dynamic-slot", slots: { app: ["content"] }, exports: { get: ["content"] },
    source: `export default function() { return { content: "panel" }; }`,
  }), { state: "disabled" });
  await loadRequiredKinds(kernel, false);
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
      start() {}, stop() {},
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

test("cannot disable an active dependency or active server, but optional kinds can be disabled", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({ name: "library" }));
  await kernel.load(await fixture({ name: "consumer", dependencies: { library: "^1.0.0" } }));
  const basePath = await validKind("server", "protected-base");
  const roomPath = await validKind("room", "protected-room");
  await kernel.load(basePath);
  await kernel.load(roomPath);
  await kernel.load(await validKind("campaign"));
  await kernel.load(await validKind("marketplace"));
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
  for (const kind of ["server"] as const) {
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
    name: "logical-handle", exports: { get: ["instanceId"], prop: ["value"] },
    source: `export default function() { return { instanceId: ++globalThis.${key}, value: 10 }; }`,
  }));
  await bootstrap(kernel);
  const ref = kernel.use("logical-handle");
  assert.equal(ref.get("instanceId"), 1);
  await kernel.disable("logical-handle");
  assert.throws(() => ref.get("instanceId"), /Module "logical-handle" is not active/);
  assert.throws(() => ref.set("value", 20), /Module "logical-handle" is not active/);
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

test("disable runs every disposer and retains the active instance when cleanup fails", async () => {
  const key = `__gravewright_dispose_failure_${crypto.randomUUID().replaceAll("-", "")}`;
  (globalThis as Record<string, unknown>)[key] = [];
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "cleanup-base", kind: "server", exports: { get: contracts.server },
    source: `export default function() { return {
      start() {}, stop() {},
      middleware() { return () => { globalThis.${key}.push("middleware"); }; },
      route() { return () => { globalThis.${key}.push("route"); throw new Error("route cleanup failed"); }; },
      slot() { return () => { globalThis.${key}.push("slot"); throw new Error("slot cleanup failed"); }; }
    }; }`,
  }));
  await kernel.load(await fixture({
    name: "cleanup-module", middleware: { "/": ["middleware"] }, routes: { "/cleanup": "route" },
    slots: { app: ["content"] }, exports: { get: ["middleware", "route", "content", "answer"] },
    source: "export default function() { return { middleware() {}, route() {}, content: 'panel', answer: 42 }; }",
  }));
  await loadRequiredKinds(kernel, false);
  await kernel.initialize();
  await assert.rejects(
    kernel.disable("cleanup-module"),
    (error: unknown) => error instanceof AggregateError && error.errors.length === 2,
  );
  assert.deepEqual((globalThis as Record<string, unknown>)[key], ["slot", "route", "middleware"]);
  assert.equal(kernel.use("cleanup-module").get("answer"), 42);
  delete (globalThis as Record<string, unknown>)[key];
});

test("composition fails when a server registrar does not provide its required disposer", async () => {
  const kernel = new Kernel();
  await kernel.load(await fixture({
    name: "invalid-registrar-base", kind: "server", exports: { get: contracts.server },
    source: "export default function() { return { start() {}, stop() {}, middleware() { return () => {}; }, route() {}, slot() { return () => {}; } }; }",
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
