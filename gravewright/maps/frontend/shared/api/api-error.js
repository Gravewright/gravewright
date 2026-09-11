/** A refusal the server explained: the HTTP status it answered with, and the domain code it named. */
export class ApiError extends Error {
    status;
    code;
    constructor(status, code) {
        super(code);
        this.status = status;
        this.code = code;
        this.name = "ApiError";
    }
}
/**
 * The exchange never happened: offline, DNS, a refused connection, a request that timed out.
 *
 * It is deliberately not an `ApiError`: there is no status and no code, because the server never
 * spoke. Callers that ask "what did the server say" get the same answer whichever mechanism the
 * transport used, which is the whole point of it existing.
 */
export class TransportError extends Error {
    path;
    code = "unreachable";
    constructor(path, options) {
        super("unreachable", options);
        this.path = path;
        this.name = "TransportError";
    }
}
