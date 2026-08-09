(() => {
  "use strict";

  const panels = new WeakMap();

  function stateFor(panel) {
    if (!panels.has(panel)) panels.set(panel, { hasCode: false, busy: false });
    return panels.get(panel);
  }

  function message(panel, key) {
    const values = {
      "http.errors.network": panel.dataset.errorNetwork,
      "campaign.join_code.errors.permission_denied": panel.dataset.errorPermission,
      "auth.errors.session_expired": panel.dataset.errorSession,
    };
    return values[key] || panel.dataset.errorGeneric || key || "";
  }

  function showNotice(panel, text, error = false) {
    const notice = panel.querySelector("[data-join-code-notice]");
    notice.textContent = text || "";
    notice.hidden = !text;
    notice.classList.toggle("game-notice--danger", error);
    notice.setAttribute("role", error ? "alert" : "status");
  }

  function setBusy(panel, busy) {
    stateFor(panel).busy = busy;
    panel.setAttribute("aria-busy", String(busy));
    panel.querySelectorAll("button, input").forEach((element) => {
      element.disabled = busy;
    });
  }

  function clearPlaintext(panel) {
    const area = panel.querySelector("[data-join-code-plaintext]");
    const input = panel.querySelector("[data-join-code-value]");
    input.value = "";
    area.hidden = true;
  }

  function renderStatus(panel, status) {
    const container = panel.querySelector("[data-join-code-status]");
    const revoke = panel.querySelector("[data-join-code-revoke]");
    const generateLabel = panel.querySelector("[data-join-code-generate-label]");
    const hasCode = Boolean(status);
    stateFor(panel).hasCode = hasCode;
    container.hidden = !hasCode;
    revoke.hidden = !hasCode || Boolean(status && status.revoked_at);
    generateLabel.textContent = hasCode ? panel.dataset.labelRotate : panel.dataset.labelGenerate;
    if (!status) return;

    const expired = status.expires_at <= Math.floor(Date.now() / 1000);
    const state = status.revoked_at
      ? panel.dataset.labelRevoked
      : expired
        ? panel.dataset.labelExpired
        : panel.dataset.labelActive;
    panel.querySelector("[data-join-code-display]").textContent = status.masked_code;
    panel.querySelector("[data-join-code-state]").textContent = state;
    panel.querySelector("[data-join-code-expiry]").textContent =
      `${panel.dataset.labelExpires}: ${new Date(status.expires_at * 1000).toLocaleString()}`;
    const limit = status.max_uses == null ? panel.dataset.labelUnlimited : status.max_uses;
    panel.querySelector("[data-join-code-uses]").textContent =
      `${panel.dataset.labelUses}: ${status.use_count}/${limit}`;
  }

  async function loadStatus(panel) {
    const http = window.GravewrightCore?.http;
    if (!http || stateFor(panel).busy) return;
    setBusy(panel, true);
    clearPlaintext(panel);
    const result = await http.getJson(
      `/campaigns/join-code/status?campaign_id=${encodeURIComponent(panel.dataset.campaignId)}`
    );
    setBusy(panel, false);
    if (!result.ok || result.data?.ok === false) {
      showNotice(panel, message(panel, result.errorKey || result.data?.error_key), true);
      return;
    }
    showNotice(panel, "");
    renderStatus(panel, result.data.join_code);
  }

  async function generate(panel, form) {
    const current = stateFor(panel);
    if (current.busy) return;
    if (current.hasCode && !(await window.GravewrightCore.dialog.confirm(panel.dataset.confirmRotate))) return;
    const formData = new FormData(form);
    const campaignId = panel.dataset.campaignId || formData.get("campaign_id") || "";
    const data = new URLSearchParams(formData);
    data.set("campaign_id", campaignId);
    if (!data.get("max_uses")) data.delete("max_uses");
    setBusy(panel, true);
    showNotice(panel, "");
    const result = await window.GravewrightCore.http.postForm(
      "/campaigns/join-code/generate",
      data,
      { headers: { "X-Requested-With": "XMLHttpRequest" } }
    );
    setBusy(panel, false);
    if (!result.ok || result.data?.ok === false) {
      showNotice(panel, message(panel, result.errorKey || result.data?.error_key), true);
      return;
    }
    renderStatus(panel, result.data);
    const input = panel.querySelector("[data-join-code-value]");
    input.value = result.data.code;
    panel.querySelector("[data-join-code-plaintext]").hidden = false;
    input.focus();
    input.select();
  }

  async function revoke(panel) {
    if (stateFor(panel).busy) return;
    if (!(await window.GravewrightCore.dialog.confirm(panel.dataset.confirmRevoke, { variant: "danger" }))) return;
    const data = new URLSearchParams();
    data.set("campaign_id", panel.dataset.campaignId);
    setBusy(panel, true);
    const result = await window.GravewrightCore.http.postForm(
      "/campaigns/join-code/revoke",
      data,
      { headers: { "X-Requested-With": "XMLHttpRequest" } }
    );
    setBusy(panel, false);
    if (!result.ok || result.data?.ok === false) {
      showNotice(panel, message(panel, result.errorKey || result.data?.error_key), true);
      return;
    }
    clearPlaintext(panel);
    renderStatus(panel, result.data);
  }

  async function copyCode(panel, button) {
    const input = panel.querySelector("[data-join-code-value]");
    if (!input.value) return;
    try {
      await navigator.clipboard.writeText(input.value);
    } catch {
      input.focus();
      input.select();
      document.execCommand("copy");
    }
    const label = button.querySelector("span");
    const original = label.textContent;
    label.textContent = panel.dataset.labelCopied;
    window.setTimeout(() => { label.textContent = original; }, 1500);
  }

  document.addEventListener("click", (event) => {
    const opener = event.target.closest('[data-modal-open^="join-code-"]');
    if (opener) {
      const modal = document.querySelector(`[data-modal-id="${opener.dataset.modalOpen}"]`);
      const panel = modal?.querySelector("[data-join-code-panel]");
      if (panel) loadStatus(panel);
      return;
    }
    const revokeButton = event.target.closest("[data-join-code-revoke]");
    if (revokeButton) revoke(revokeButton.closest("[data-join-code-panel]"));
    const copyButton = event.target.closest("[data-join-code-copy]");
    if (copyButton) copyCode(copyButton.closest("[data-join-code-panel]"), copyButton);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-join-code-form]");
    if (!form) return;
    event.preventDefault();
    generate(form.closest("[data-join-code-panel]"), form);
  });
})();
