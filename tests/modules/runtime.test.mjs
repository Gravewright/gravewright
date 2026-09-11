import test from "node:test";
import assert from "node:assert/strict";
import { Lifetime } from "../../gravewright/modules/static/gravewright_modules/lifetime.js";
import { ModuleRuntime } from "../../gravewright/modules/static/gravewright_modules/module-runtime.js";
class Element {
  children = [];
  dataset = {};
  className = "";
  parent;
  append(child) {
    this.children.push(child);
    child.parent = this;
  }
  remove() {
    if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this);
  }
}
Object.assign(globalThis, { location: { origin: "https://example.test" }, document: { createElement: () => new Element() } });
function fixture(modules) {
  const errors = [];
  let ack = "";
  const bridge = {
    context: (_m, _i, life) => ({ signal: life.signal, onDispose: life.onDispose }),
    host: () => ({ call: async () => null }),
    events: () => ({ on: () => () => {
    } }),
    acknowledge: async (rev) => {
      ack = rev;
    }
  };
  const runtime = new ModuleRuntime(bridge, (e) => errors.push(e), async (url) => ({ default: modules[new URL(url).pathname.split("/")[3]] }));
  const state = (ids, revision = "1", replacements = {}) => ({
    tableId: "table",
    moduleSetRevision: revision,
    replacements,
    modules: ids.map((id) => ({ id, version: "1.0.0", baseUrl: `/api/module-packages/${id}/1.0.0/hash/`, entry: "index.js" }))
  });
  return { runtime, state, errors, get ack() {
    return ack;
  } };
}
function surface() {
  const root = new Element();
  const visibility = [];
  return { root, visibility, surface: {
    domain: "actor.directory",
    root,
    context: { tableId: "table", mountId: "mount", moduleSetRevision: "1" },
    defaultVisible: async (v) => {
      visibility.push(v);
    }
  } };
}
test("all cleanups drain and pending operations reject when their scope closes", async () => {
  const failures = [];
  const life = new Lifetime((e) => failures.push(e));
  let cleaned = 0;
  life.onDispose(() => {
    cleaned++;
  });
  life.onDispose(() => {
    throw new Error("broken cleanup");
  });
  const wait = life.wait(() => new Promise(() => {
  }));
  const rejection = assert.rejects(wait, { code: "stale_context" });
  await life.close();
  await rejection;
  await life.close();
  assert.equal(cleaned, 1);
  assert.equal(failures.length, 1);
  assert.throws(() => life.check(), { code: "stale_context" });
});
test("multiple replace registrations do not mount until a preference selects one", async () => {
  const mounted = [];
  const stopped = [];
  const mod = (id) => ({ start() {
  }, register(ctx) {
    ctx.register("actor.directory", { mode: "replace", mount(block) {
      mounted.push(id);
      block.onDispose(() => {
        stopped.push(id);
      });
    } });
  }, stop() {
  } });
  const f = fixture({ a: mod("a"), b: mod("b") }), s = surface();
  const release = f.runtime.attach(s.surface);
  await f.runtime.reconcile(f.state(["a", "b"]));
  assert.deepEqual(mounted, []);
  assert.equal(s.visibility.at(-1), true);
  await f.runtime.reconcile(f.state(["a", "b"], "2", { "actor.directory": "b" }));
  assert.deepEqual(mounted, ["b"]);
  assert.equal(s.visibility.at(-1), false);
  assert.equal(s.root.children.length, 1);
  await f.runtime.reconcile(f.state(["a"], "3"));
  assert.deepEqual(stopped, ["b"]);
  assert.deepEqual(mounted, ["b", "a"]);
  assert.equal(f.ack, "3");
  release();
  await f.runtime.close();
  assert.deepEqual(stopped, ["b", "a"]);
  assert.equal(s.root.children.length, 0);
});
test("async register is rejected and start resources are disposed", async () => {
  let disposed = 0, stopped = 0;
  const f = fixture({ bad: { start(ctx) {
    ctx.onDispose(() => {
      disposed++;
    });
  }, async register() {
  }, stop() {
    stopped++;
  } } });
  await assert.rejects(f.runtime.reconcile(f.state(["bad"])), { code: "invalid_data" });
  assert.equal(disposed, 1);
  assert.equal(stopped, 1);
  assert.equal(f.ack, "");
  await f.runtime.close();
});
test("failed replacement restores native content and removes its root", async () => {
  const f = fixture({ bad: { start() {
  }, register(ctx) {
    ctx.register("actor.directory", { mode: "replace", mount() {
      throw new Error("mount failed");
    } });
  }, stop() {
  } } });
  const s = surface();
  f.runtime.attach(s.surface);
  await f.runtime.reconcile(f.state(["bad"]));
  assert.equal(s.visibility.at(-1), true);
  assert.equal(s.root.children.length, 0);
  assert.equal(f.errors.length, 1);
  await f.runtime.close();
});
test("every registration completes before any mount; instances are isolated and revoke independently", async () => {
  const order = [];
  const blocks = [];
  const f = fixture({ a: { start() {
    order.push("start");
  }, register(ctx) {
    order.push("register");
    ctx.register("actor.directory", (block) => {
      order.push("mount");
      blocks.push(block);
    });
  }, stop() {
    order.push("stop");
  } }, b: { start() {
  }, register() {
    order.push("registered-b");
  }, stop() {
  } } });
  const a = surface(), b = surface();
  const detach = f.runtime.attach(a.surface);
  f.runtime.attach(b.surface);
  await f.runtime.reconcile(f.state(["a", "b"]));
  assert.deepEqual(order, ["start", "register", "registered-b", "mount", "mount"]);
  assert.notEqual(blocks[0].context.mountId, blocks[1].context.mountId);
  assert.notEqual(blocks[0].root, blocks[1].root);
  detach();
  assert.equal(blocks[0].signal.aborted, true);
  assert.equal(blocks[1].signal.aborted, false);
  await f.runtime.close();
  assert.equal(blocks[1].signal.aborted, true);
});
test("pending mounting cannot retain a scene after a revision change", async () => {
  let count = 0;
  const signals = [];
  const f = fixture({ a: { start() {
  }, register(ctx) {
    ctx.register("actor.directory", (block) => {
      signals.push(block.signal);
      return ++count === 1 ? new Promise(() => {
      }) : void 0;
    });
  }, stop() {
  } } });
  const s = surface();
  f.runtime.attach(s.surface);
  const first = f.runtime.reconcile(f.state(["a"]));
  while (!signals.length) await new Promise((resolve) => setTimeout(resolve, 0));
  const next = f.runtime.reconcile(f.state(["a"], "2"));
  await Promise.allSettled([first, next]);
  assert.equal(signals[0].aborted, true);
  assert.equal(signals[1].aborted, false);
  assert.equal(f.ack, "2");
  await f.runtime.close();
});
test("failed start and stop still permit a clean subsequent activation", async () => {
  let disposed = 0;
  const f = fixture({ bad: { start(ctx) {
    ctx.onDispose(() => {
      disposed++;
    });
    throw new Error("start");
  }, register() {
  }, stop() {
    throw new Error("stop");
  } }, good: { start() {
  }, register() {
  }, stop() {
  } } });
  await assert.rejects(f.runtime.reconcile(f.state(["bad"])));
  assert.equal(disposed, 1);
  await f.runtime.reconcile(f.state(["good"], "2"));
  assert.equal(f.ack, "2");
  await f.runtime.close();
});
test("scene transforms and nested context are immutable and revoked with the surface", async () => {
  let saved;
  const f = fixture({ a: { start() {
  }, register(ctx) {
    ctx.register("scene.overlay", (block) => {
      saved = block;
    });
  }, stop() {
  } } });
  const s = surface();
  s.surface.domain = "scene.overlay";
  s.surface.viewport = { sceneToViewport: (p) => ({ x: p.x * 2 + 10, y: p.y * 2 + 20 }), viewportToScene: (p) => ({ x: (p.x - 10) / 2, y: (p.y - 20) / 2 }) };
  s.surface.context = { tableId: "table", mountId: "", moduleSetRevision: "1", sceneId: "scene", width: 100, height: 100, grid: { size: 10, distance: 1, unit: "m", offsetX: 0, offsetY: 0 } };
  const detach = f.runtime.attach(s.surface);
  await f.runtime.reconcile(f.state(["a"]));
  assert.deepEqual(saved.viewport.sceneToViewport({ x: 5, y: 7 }), { x: 20, y: 34 });
  assert.deepEqual(saved.viewport.viewportToScene({ x: 20, y: 34 }), { x: 5, y: 7 });
  assert.throws(() => {
    saved.context.grid.size = 999;
  }, TypeError);
  detach();
  assert.throws(() => saved.viewport.sceneToViewport({ x: 0, y: 0 }), { code: "stale_context" });
  await f.runtime.close();
});
