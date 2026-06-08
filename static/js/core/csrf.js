








(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  function token() {
    if (typeof window.csrfToken === "function") {
      return window.csrfToken() || "";
    }
    return (document.cookie.match(/(?:^|; )csrftoken=([^;]*)/) || [])[1] || "";
  }

  
  function headers(extra) {
    const merged = new Headers(extra || undefined);
    if (!merged.has("x-csrftoken")) {
      merged.set("x-csrftoken", token());
    }
    return merged;
  }

  
  function attachToFetchOptions(options) {
    const opts = options ? { ...options } : {};
    opts.headers = headers(opts.headers);
    if (opts.credentials === undefined) {
      opts.credentials = "same-origin";
    }
    return opts;
  }

  Core.csrf = { token, headers, attachToFetchOptions };
})();
