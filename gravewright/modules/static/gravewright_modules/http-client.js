import { ApiError } from "./api-error.js";
import { FetchHttpTransport } from "./fetch-http-transport.js";
import { ApiError as ApiError2, TransportError } from "./api-error.js";
const TIMEOUT_MS = 1e4;
function configuredPath(metaName, fallback) {
  return globalThis.document?.querySelector(`meta[name="${metaName}"]`)?.content || fallback;
}
function backendPath(path) {
  return path.startsWith("/api") ? `${configuredPath("gravewright-backend-api", "/api")}${path.slice(4)}` : path;
}
class HttpClient {
  constructor(transport = new FetchHttpTransport(), scopeSignal) {
    this.transport = transport;
    this.scopeSignal = scopeSignal;
  }
  transport;
  scopeSignal;
  get(path, options = {}) {
    return this.#send({ method: "GET", path: backendPath(path), cache: options.cache, signal: options.signal ?? this.scopeSignal?.(), ...timing(options) });
  }
  post(path, body, options) {
    return this.#guarded("POST", path, body, options);
  }
  patch(path, body, options) {
    return this.#guarded("PATCH", path, body, options);
  }
  delete(path, body, options) {
    return this.#guarded("DELETE", path, body, options);
  }
  /**
   * Sends a form and reports how much of it has gone up. Nothing cuts an upload short: a large map
   * legitimately takes longer than any request ceiling worth setting.
   */
  async upload(path, form, onProgress) {
    const signal = this.scopeSignal?.();
    const csrf = await this.#csrf(signal);
    return this.#send({ method: "POST", path: backendPath(path), headers: csrf, body: form, onProgress, signal });
  }
  /** Every state change carries a fresh CSRF token; the server refuses the ones that do not. */
  async #guarded(method, path, body, options = {}) {
    const signal = options.signal ?? this.scopeSignal?.();
    const csrf = await this.#csrf(signal);
    return this.#send({
      method,
      signal,
      path: backendPath(path),
      headers: body === void 0 ? csrf : { ...csrf, "content-type": "application/json" },
      body: body === void 0 ? void 0 : JSON.stringify(body),
      ...timing(options)
    });
  }
  async #csrf(signal) {
    const { token, header } = await this.#send({ method: "GET", path: configuredPath("gravewright-csrf-url", "/__gravewright/csrf"), timeoutMs: TIMEOUT_MS, signal });
    return { [header]: token };
  }
  async #send(request) {
    request.signal?.throwIfAborted();
    const reply = await this.transport.send(request);
    request.signal?.throwIfAborted();
    if (!reply.ok) throw new ApiError(reply.status, code(reply.text));
    if (reply.status === 204 || reply.text === "") return void 0;
    return JSON.parse(reply.text);
  }
}
function code(body) {
  try {
    return JSON.parse(body).error ?? "request_failed";
  } catch {
    return "request_failed";
  }
}
function timing({ timeoutMs }) {
  if (timeoutMs === null) return {};
  return { timeoutMs: timeoutMs ?? TIMEOUT_MS };
}
export {
  ApiError2 as ApiError,
  HttpClient,
  TransportError
};
