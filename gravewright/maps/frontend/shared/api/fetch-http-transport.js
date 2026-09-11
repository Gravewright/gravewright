import { TransportError } from "./api-error.js";
/**
 * The one file that knows the server is reached with the browser's own request machinery.
 * Everything above it speaks `HttpTransport`.
 */
export class FetchHttpTransport {
    request;
    /** The exchange itself is injectable so the transport can be driven without a network. */
    constructor(request = (...arguments_) => globalThis.fetch(...arguments_)) {
        this.request = request;
    }
    async send(request) {
        request.signal?.throwIfAborted();
        if (request.onProgress)
            return this.#withProgress(request);
        let response;
        try {
            response = await this.request(request.path, {
                method: request.method,
                headers: request.headers ? { ...request.headers } : undefined,
                body: request.body,
                credentials: "same-origin",
                cache: request.cache ?? "default",
                signal: request.timeoutMs === undefined ? request.signal : AbortSignal.any([AbortSignal.timeout(request.timeoutMs), ...(request.signal ? [request.signal] : [])]),
            });
        }
        catch (error) {
            // `fetch` reports being unable to reach anything as a `TypeError`, and an expired timeout as
            // an abort. Neither is something the server said, so both leave here as the same refusal.
            throw new TransportError(request.path, { cause: error });
        }
        return { status: response.status, ok: response.ok, text: await response.text() };
    }
    /** Only XHR reports how much of a body has gone up, which is why a map upload does not use fetch. */
    #withProgress(request) {
        return new Promise((resolve, reject) => {
            const exchange = new XMLHttpRequest();
            exchange.open(request.method, request.path);
            exchange.withCredentials = true;
            for (const [name, value] of Object.entries(request.headers ?? {}))
                exchange.setRequestHeader(name, value);
            if (request.timeoutMs !== undefined)
                exchange.timeout = request.timeoutMs;
            exchange.upload.addEventListener("progress", (event) => {
                if (event.lengthComputable)
                    request.onProgress?.(Math.round(event.loaded * 100 / event.total));
            });
            exchange.addEventListener("load", () => resolve({ status: exchange.status, ok: exchange.status >= 200 && exchange.status < 300, text: exchange.responseText }));
            exchange.addEventListener("error", () => reject(new TransportError(request.path)));
            exchange.addEventListener("timeout", () => reject(new TransportError(request.path)));
            const abort = () => { exchange.abort(); reject(request.signal?.reason ?? new DOMException("Aborted", "AbortError")); };
            exchange.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
            exchange.addEventListener("loadend", () => request.signal?.removeEventListener("abort", abort), { once: true });
            request.signal?.addEventListener("abort", abort, { once: true });
            if (request.signal?.aborted) {
                abort();
                return;
            }
            exchange.send(request.body);
        });
    }
}
