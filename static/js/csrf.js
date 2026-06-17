










(function () {
  const SAFE = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

  function csrfToken() {
    return (document.cookie.match(/(?:^|; )csrftoken=([^;]*)/) || [])[1] || "";
  }

  function isCrossOrigin(input) {
    try {
      const url = new URL(
        typeof input === "string" ? input : input.url,
        window.location.href,
      );
      return url.origin !== window.location.origin;
    } catch {
      return false;
    }
  }

  const original = window.fetch.bind(window);

  window.fetch = function (input, init) {
    init = init || {};
    const method = (
      init.method ||
      (typeof input === "object" && input ? input.method : "") ||
      "GET"
    ).toUpperCase();

    if (!SAFE.has(method) && !isCrossOrigin(input)) {
      const headers = new Headers(
        init.headers || (typeof input === "object" && input ? input.headers : undefined),
      );
      if (!headers.has("x-csrftoken")) {
        headers.set("x-csrftoken", csrfToken());
      }
      init.headers = headers;
      if (init.credentials === undefined) {
        init.credentials = "same-origin";
      }
    }

    return original(input, init);
  };

  
  window.csrfToken = csrfToken;
})();
