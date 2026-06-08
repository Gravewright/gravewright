




(function () {
  
  
  
  const SOURCE_MIME = "application/x-gravewright-drop-source+json";

  function csrf() {
    return window.csrfToken();
  }

  async function getJSON(url) {
    const res = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
    return res.ok ? res.json().catch(() => null) : null;
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    return res.ok ? res.json().catch(() => ({})) : null;
  }

  window.GravewrightContentApi = { SOURCE_MIME, csrf, getJSON, postJSON };
})();
