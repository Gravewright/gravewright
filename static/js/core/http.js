








(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  function csrf() {
    return Core.csrf || null;
  }

  async function parseBody(response) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json().catch(() => null);
    }
    return response.text().catch(() => null);
  }

  // Canonical error key per HTTP status so every caller maps failures the same
  // way. Status 0 means the request never reached the server (offline/DNS/etc).
  function errorKeyForStatus(status) {
    switch (status) {
      case 0:
        return "http.errors.network";
      case 401:
        return "auth.errors.session_expired";
      case 403:
        return "http.errors.forbidden";
      case 409:
        return "http.errors.conflict";
      case 429:
        return "http.errors.rate_limited";
      default:
        return status >= 500 ? "http.errors.server" : "http.errors.request";
    }
  }

  function errorFrom(response, body) {
    const details = body && typeof body === "object" ? body : null;
    const message =
      (details && (details.message || details.detail || details.error)) ||
      (typeof body === "string" && body) ||
      response.statusText ||
      "Request failed";
    // Prefer a specific error_key from the JSON envelope, else the status map.
    const errorKey =
      (details && details.error_key) || errorKeyForStatus(response.status);
    return { ok: false, status: response.status, message, details, errorKey };
  }

  async function request(url, options) {
    const opts = options ? { ...options } : {};
    const method = (opts.method || "GET").toUpperCase();
    const isSafe = method === "GET" || method === "HEAD";

    if (!isSafe && csrf()) {
      const withCsrf = csrf().attachToFetchOptions(opts);
      Object.assign(opts, withCsrf);
    } else if (opts.credentials === undefined) {
      opts.credentials = "same-origin";
    }

    let response;
    try {
      response = await fetch(url, opts);
    } catch (networkError) {
      return {
        ok: false,
        status: 0,
        message: networkError?.message || "Network error",
        details: null,
        errorKey: errorKeyForStatus(0),
      };
    }

    const body = await parseBody(response);
    if (!response.ok) {
      return errorFrom(response, body);
    }
    return { ok: true, status: response.status, data: body };
  }

  function jsonHeaders(extra) {
    const headers = new Headers(extra || undefined);
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }
    return headers;
  }

  function withJsonBody(payload, options) {
    const opts = options ? { ...options } : {};
    const headers = jsonHeaders(opts.headers);
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    opts.headers = headers;
    opts.body = JSON.stringify(payload ?? {});
    return opts;
  }

  function getJson(url, options) {
    const opts = options ? { ...options } : {};
    opts.method = "GET";
    opts.headers = jsonHeaders(opts.headers);
    return request(url, opts);
  }

  function postJson(url, payload, options) {
    const opts = withJsonBody(payload, options);
    opts.method = "POST";
    return request(url, opts);
  }

  function patchJson(url, payload, options) {
    const opts = withJsonBody(payload, options);
    opts.method = "PATCH";
    return request(url, opts);
  }

  function deleteJson(url, options) {
    const opts = options ? { ...options } : {};
    opts.method = "DELETE";
    opts.headers = jsonHeaders(opts.headers);
    return request(url, opts);
  }

  function postForm(url, formData, options) {
    const opts = options ? { ...options } : {};
    opts.method = "POST";
    opts.headers = jsonHeaders(opts.headers); 
    opts.body =
      formData instanceof FormData ? formData : new URLSearchParams(formData);
    return request(url, opts);
  }

  Core.http = { request, getJson, postJson, patchJson, deleteJson, postForm };
})();
