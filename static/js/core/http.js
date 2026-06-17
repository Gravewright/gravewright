








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

  
  function errorFrom(response, body) {
    const details = body && typeof body === "object" ? body : null;
    const message =
      (details && (details.message || details.detail || details.error)) ||
      (typeof body === "string" && body) ||
      response.statusText ||
      "Request failed";
    return { ok: false, status: response.status, message, details };
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
