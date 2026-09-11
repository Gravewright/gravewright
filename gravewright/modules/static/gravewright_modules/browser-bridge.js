import { OPERATION_TRANSPORTS } from "./generated.js";
import { applyLocale } from "./module-locale.js";
import { HttpClient, ApiError } from "./http-client.js";
import { ModuleError } from "./lifetime.js";
import { createDomainApi, createEvents } from "./domain-api.js";
const errorCodes = ["not_found", "permission_denied", "invalid_data", "conflict", "unavailable", "cancelled", "stale_context"];
/** Translate module-owned handles into authenticated, revision-checked requests. */
class BrowserBridge {
  constructor(tableId) {
    this.tableId = tableId;
  }
  tableId;
  http = new HttpClient();
  leases = /* @__PURE__ */ new WeakMap();
  leaseTimes = new WeakMap();
  listeners = /* @__PURE__ */ new Map();
  root(moduleId) {
    return `/api/tables/${encodeURIComponent(this.tableId)}/modules/${encodeURIComponent(moduleId)}`;
  }
  async request(path, payload, signal) {
    try {
      return (await this.http.post(path, payload, { signal })).value;
    } catch (error) {
      if (error instanceof ApiError && errorCodes.includes(error.code)) throw new ModuleError(error.code);
      if (signal.aborted) throw new ModuleError("cancelled");
      throw new ModuleError("unavailable");
    }
  }
  ensure(identity, life) {
    // One lazily opened lease per lifetime; renew before the server's 30-minute expiry.
    life.check();
    let pending = this.leases.get(life);
    if (pending && Date.now() - this.leaseTimes.get(life) < 10 * 60 * 1000) return pending;
    const first = !pending;
    const root = this.root(identity.moduleId) + "/context";
    pending = this.http.post(root, { action: "open", mountId: identity.mountId, moduleSetRevision: identity.moduleSetRevision, ...identity.sceneId ? { sceneId: identity.sceneId } : {} }).then(() => {
    });
    this.leases.set(life, pending);
    this.leaseTimes.set(life, Date.now());
    if (first) life.onDispose(async () => {
      try {
        await this.leases.get(life);
        await this.http.post(root, { action: "close", mountId: identity.mountId });
      } catch {
      }
    });
    return pending.catch((error) => {
      throw normalized(error);
    });
  }
  async binary(identity, name, payload, signal, onProgress) {
    const csrf = await this.http.get("/__gravewright/csrf", { signal });
    const metadata = { name, payload, moduleSetRevision: identity.moduleSetRevision, mountId: identity.mountId, ...identity.sceneId ? { sceneId: identity.sceneId } : {} };
    const headers = { [csrf.header]: csrf.token };
    let body;
    const file = payload.file;
    if (file instanceof Blob) {
      const form = new FormData();
      form.append("metadata", JSON.stringify({ ...metadata, payload: { ...payload, file: void 0 } }));
      form.append("file", file, file instanceof File ? file.name : "upload.pdf");
      body = form;
    } else {
      headers["content-type"] = "application/json";
      body = JSON.stringify(metadata);
    }
    const response = await fetch(this.root(identity.moduleId) + "/call", { method: "POST", body, headers, signal, credentials: "same-origin" });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: "unavailable" }));
      throw new ModuleError(errorCodes.includes(error.error) ? error.error : "unavailable");
    }
    if (name === "asset.download") {
      const blob = await response.blob();
      onProgress?.({ loaded: blob.size, total: blob.size });
      const disposition = response.headers.get("content-disposition") ?? "";
      let filename = disposition.match(/filename="([^"\r\n]*)"/)?.[1] ?? "download.pdf";
      const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i)?.[1];
      if (encoded) filename = decodeURIComponent(encoded);
      return { blob, name: filename, contentType: blob.type, size: blob.size };
    }
    if (file instanceof Blob) onProgress?.({ loaded: file.size, total: file.size });
    return (await response.json()).value;
  }
  host(identity, life) {
    return { call: (name, payload, options) => life.wait(async (signal) => {
      try {
        if (name === "locale.apply") {
          const value = payload;
          return applyLocale(life, value.id, value.messages);
        }
        await this.ensure(identity, life);
        life.check();
        if (!(name in OPERATION_TRANSPORTS)) throw new ModuleError("unavailable");
        if (OPERATION_TRANSPORTS[name] !== "json") return await this.binary(identity, name, payload, signal, options?.onProgress);
        encodeJson(payload);
        return await this.request(this.root(identity.moduleId) + "/call", {
          name,
          payload,
          moduleSetRevision: identity.moduleSetRevision,
          mountId: identity.mountId,
          ...identity.sceneId ? { sceneId: identity.sceneId } : {}
        }, signal);
      } catch (error) {
        throw normalized(error);
      }
    }, options?.signal) };
  }
  api(identity, life, ui) {
    const call = (domain, method, payload, options) => life.wait(async signal => {
      await this.ensure(identity, life);
      life.check();
      return this.request(this.root(identity.moduleId) + '/api', {
        domain, method, payload, requestId: options.requestId ?? crypto.randomUUID(),
        mountId: identity.mountId, moduleSetRevision: identity.moduleSetRevision,
        ...(identity.sceneId ? { sceneId: identity.sceneId } : {}),
      }, signal);
    }, options.signal);
    return createDomainApi(call, { context: identity, events: createEvents(window, life, identity,
      domain => call(domain === 'maps.layers' ? 'maps' : domain, domain === 'maps.layers' ? 'layers' : 'state', {}, {})), ui });
  }
  events(identity, life) {
    return { on: (name, handler) => {
      life.check();
      let entries = this.listeners.get(name);
      if (!entries) this.listeners.set(name, entries = /* @__PURE__ */ new Set());
      const callback = ((value) => {
        if (!life.signal.aborted && (!value.sceneId || value.sceneId === identity.sceneId)) handler(value);
      });
      entries.add(callback);
      const release = () => {
        entries.delete(callback);
        if (!entries.size) this.listeners.delete(name);
      };
      life.onDispose(release);
      return release;
    } };
  }
  publish(name, payload) {
    if (payload.tableId !== this.tableId) return;
    for (const handler of [...this.listeners.get(name) ?? []]) {
      try {
        handler(structuredClone(payload));
      } catch (error) {
        console.error(error);
      }
    }
  }
  context(module, identity, life) {
    // These helpers share the mount lifetime; storing a handle never extends it.
    const url = (path) => {
      life.check();
      if (!path || path.split("/").some((p) => !p || p === "." || p === "..") || /[\\%?#:\x00]/.test(path)) throw new ModuleError("invalid_data");
      const base = new URL(module.baseUrl, location.origin), value = new URL(path, base);
      if (value.origin !== location.origin || !value.href.startsWith(base.href)) throw new ModuleError("invalid_data");
      return value.href;
    };
    const read = (path) => life.wait(async (signal) => {
      const response = await fetch(url(path), { signal, credentials: "same-origin" });
      if (!response.ok) throw new ModuleError(response.status === 404 ? "not_found" : "unavailable");
      return response.arrayBuffer();
    });
    const persistent = (scope) => {
      const call = (action, key2, rest = {}) => life.wait(async (signal) => {
        encodeJson(rest);
        await this.ensure(identity, life);
        life.check();
        return this.request(this.root(module.id) + "/storage", {
          scope,
          action,
          key: key2,
          ...rest,
          moduleSetRevision: identity.moduleSetRevision,
          mountId: identity.mountId,
          ...identity.sceneId ? { sceneId: identity.sceneId } : {}
        }, signal);
      });
      return {
        get: (key2) => call("get", key2),
        set: (key2, value, options) => call("set", key2, { value, ...options }),
        delete: (key2, options) => call("delete", key2, options),
        list: (prefix = "") => call("list", prefix)
      };
    };
    const key = (name) => {
      life.check();
      if (!name || name.length > 240) throw new ModuleError("invalid_data");
      return `gravewright.module.${module.id}.${name}`;
    };
    return {
      api: this.api(identity, life),
      signal: life.signal,
      onDispose: life.onDispose,
      assets: { url, bytes: read, text: async (path) => new TextDecoder().decode(await read(path)), json: async (path) => {
        const text = new TextDecoder().decode(await read(path));
        try {
          return JSON.parse(text);
        } catch {
          throw new ModuleError("invalid_data");
        }
      } },
      styles: { use: (path) => {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = url(path);
        document.head.append(link);
        const dispose = () => link.remove();
        life.onDispose(dispose);
        return dispose;
      } },
      storage: { user: persistent("user"), table: persistent("table"), local: {
        get: async (name) => {
          const id = key(name);
          try {
            return JSON.parse(localStorage.getItem(id) ?? "null");
          } catch (error) {
            throw normalized(error);
          }
        },
        set: async (name, value) => {
          const id = key(name), encoded = encodeJson(value);
          if (new TextEncoder().encode(encoded).length > 256 * 1024) throw new ModuleError("invalid_data");
          try {
            localStorage.setItem(id, encoded);
          } catch (error) {
            throw normalized(error);
          }
        },
        delete: async (name) => {
          const id = key(name);
          try {
            localStorage.removeItem(id);
          } catch (error) {
            throw normalized(error);
          }
        }
      } }
    };
  }
  async acknowledge(moduleSetRevision) {
    await this.http.post(`/api/tables/${encodeURIComponent(this.tableId)}/modules/ack`, { moduleSetRevision });
  }
}
function normalized(error) {
  const code = error?.code;
  if (code && errorCodes.includes(code)) return new ModuleError(code);
  if (code === "invalid_request" || error instanceof SyntaxError) return new ModuleError("invalid_data");
  return new ModuleError("unavailable");
}
function encodeJson(value) {
  try {
    return JSON.stringify(value, (_, v) => {
      if (v === void 0 || typeof v === "function" || typeof v === "symbol" || typeof v === "bigint" || typeof v === "number" && !Number.isFinite(v)) throw new Error();
      return v;
    });
  } catch {
    throw new ModuleError("invalid_data");
  }
}
export {
  BrowserBridge
};
