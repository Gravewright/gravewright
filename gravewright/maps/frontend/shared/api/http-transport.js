/**
 * How the frontend reaches its own server.
 *
 * This contract is deliberately mechanism-neutral, the sibling of `TableLink` for request/response
 * traffic: nothing here says whether the exchange rides on `fetch`, `XMLHttpRequest` or anything
 * else, and nothing above it interprets a status code. Only `fetch-http-transport.ts` knows.
 *
 * Two guarantees hold for every implementation: the session travels with the request (same-origin
 * credentials), and the body is passed through exactly as it was handed over — encoding, CSRF and
 * error meaning belong to `HttpClient`, one layer up.
 */
export {};
