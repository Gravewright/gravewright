






(function () {
  "use strict";

  function csrfOptions(body) {
    const core = window.GravewrightCore;
    const base = {
      method: "POST",
      body,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
    };
    if (core && core.csrf && typeof core.csrf.attachToFetchOptions === "function") {
      return core.csrf.attachToFetchOptions(base);
    }
    const token = (document.cookie.match(/(?:^|; )csrftoken=([^;]*)/) || [])[1] || "";
    base.headers["x-csrftoken"] = token;
    return base;
  }

  function panelFor(el) {
    return el.closest("[data-streamer-link]");
  }

  function showError(panel, message) {
    const box = panel.querySelector("[data-streamer-error]");
    if (!box) return;
    box.textContent = message || "";
    box.hidden = !message;
  }

  function setBusy(panel, busy) {
    panel.querySelectorAll("button").forEach((b) => {
      b.disabled = busy;
    });
  }

  function renderLink(panel, payload) {
    const result = panel.querySelector("[data-streamer-result]");
    const input = panel.querySelector("[data-streamer-url]");
    const expiry = panel.querySelector("[data-streamer-expiry]");
    if (input) input.value = payload.url || "";
    if (expiry && payload.expires_at) {
      const when = new Date(payload.expires_at * 1000);
      const tmpl = panel.dataset.expiryTemplate || "Expires {when}";
      expiry.textContent = tmpl.replace("{when}", when.toLocaleString());
    }
    if (result) result.hidden = false;
  }

  async function generate(panel) {
    const roomId = panel.dataset.roomId || "";
    showError(panel, "");
    setBusy(panel, true);
    try {
      const res = await fetch(
        "/game/streamer-link",
        csrfOptions(new URLSearchParams({ campaign_id: roomId }))
      );
      const payload = await res.json().catch(() => ({}));
      if (!res.ok || !payload.ok) {
        showError(panel, panel.dataset.errorGeneric || "Could not generate the link.");
        return;
      }
      renderLink(panel, payload);
    } catch {
      showError(panel, panel.dataset.errorGeneric || "Could not generate the link.");
    } finally {
      setBusy(panel, false);
    }
  }

  async function revoke(panel) {
    const roomId = panel.dataset.roomId || "";
    showError(panel, "");
    setBusy(panel, true);
    try {
      const res = await fetch(
        "/game/streamer-link/revoke",
        csrfOptions(new URLSearchParams({ campaign_id: roomId }))
      );
      const payload = await res.json().catch(() => ({}));
      if (!res.ok || !payload.ok) {
        showError(panel, panel.dataset.errorGeneric || "Could not revoke the link.");
        return;
      }
      const result = panel.querySelector("[data-streamer-result]");
      const input = panel.querySelector("[data-streamer-url]");
      if (input) input.value = "";
      if (result) result.hidden = true;
    } catch {
      showError(panel, panel.dataset.errorGeneric || "Could not revoke the link.");
    } finally {
      setBusy(panel, false);
    }
  }

  async function copy(panel, button) {
    const input = panel.querySelector("[data-streamer-url]");
    if (!input || !input.value) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(input.value);
      } else {
        input.focus();
        input.select();
        document.execCommand("copy");
      }
      const label = button.querySelector("span");
      if (label) {
        const original = label.textContent;
        label.textContent = panel.dataset.copiedLabel || "Copied!";
        setTimeout(() => {
          label.textContent = original;
        }, 1500);
      }
    } catch {
      input.focus();
      input.select();
    }
  }

  document.addEventListener("click", (event) => {
    const generateBtn = event.target.closest("[data-streamer-generate]");
    if (generateBtn) {
      const panel = panelFor(generateBtn);
      if (panel) generate(panel);
      return;
    }
    const copyBtn = event.target.closest("[data-streamer-copy]");
    if (copyBtn) {
      const panel = panelFor(copyBtn);
      if (panel) copy(panel, copyBtn);
      return;
    }
    const revokeBtn = event.target.closest("[data-streamer-revoke]");
    if (revokeBtn) {
      const panel = panelFor(revokeBtn);
      if (panel) revoke(panel);
    }
  });
})();
