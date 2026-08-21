(() => {
  "use strict";
  const root = document.querySelector("[data-core-update]");
  if (!root) return;
  const status = root.querySelector("[data-core-update-status]");
  const available = root.querySelector("[data-core-update-available]");
  const channel = root.querySelector("[data-core-update-channel]");
  const resolvedChannel = root.querySelector("[data-core-update-resolved-channel]");
  const action = root.querySelector("[data-core-update-action]");
  const details = root.querySelector("[data-core-update-details]");
  const stateBadge = root.querySelector("[data-core-update-state]");

  const statusLabel = (state) => ({
    available: root.dataset.textAvailable,
    current: root.dataset.textCurrent,
    "ahead-of-channel": root.dataset.textAhead,
    failed: root.dataset.textFailed,
    unchecked: root.dataset.textUnchecked,
  })[state] || root.dataset.textUnchecked;

  function render(update) {
    root.dataset.state = update.status || "failed";
    if (stateBadge) stateBadge.textContent = statusLabel(root.dataset.state);
    if (available) available.textContent = update.availableVersion || "—";
    if (channel) channel.textContent = update.channel || "—";
    if (resolvedChannel) resolvedChannel.textContent = update.resolvedChannel || "—";
    if (status) status.textContent = update.status === "available"
      ? `${root.dataset.textAvailable} — ${update.currentVersion} → ${update.availableVersion}`
      : update.status === "current" ? root.dataset.textCurrent
        : update.status === "ahead-of-channel" ? `${root.dataset.textAhead} — ${update.channel}`
          : root.dataset.textFailed;
    const artifact = update.artifact;
    if (action) {
      action.hidden = !artifact?.url;
      if (artifact?.url) action.href = artifact.url;
    }
    if (details) details.textContent = update.status === "available"
      ? `${root.dataset.textBackup} ${root.dataset.textSha}: ${artifact?.sha256 || "—"}.`
      : "";
  }

  root.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-core-update-check]");
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector("button");
    if (button) button.disabled = true;
    root.dataset.state = "checking";
    if (stateBadge) stateBadge.textContent = root.dataset.textChecking;
    if (status) status.textContent = root.dataset.textChecking;
    try {
      const response = await fetch(form.action, {method: "POST", credentials: "same-origin",
        headers: {Accept: "application/json", "x-csrftoken": window.csrfToken?.() || ""}});
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.update?.errorKey || result.errorKey);
      render(result.update);
    } catch {
      root.dataset.state = "failed";
      if (stateBadge) stateBadge.textContent = root.dataset.textFailed;
      if (status) status.textContent = root.dataset.textFailed;
    } finally {
      if (button) button.disabled = false;
    }
  });

  const channelForm = document.querySelector("[data-update-channel-form]");
  if (channelForm) {
    const coreSelect = channelForm.querySelector("[data-core-channel-select]");
    const packageSelect = channelForm.querySelector("[data-packages-channel-select]");
    const linked = channelForm.querySelector("[data-channels-linked]");
    const testingWarning = channelForm.querySelector("[data-testing-channel-warning]");
    const devWarning = channelForm.querySelector("[data-dev-channel-warning]");
    const coreHint = channelForm.querySelector("[data-core-channel-hint]");
    const packageHint = channelForm.querySelector("[data-packages-channel-hint]");
    const effectiveChannels = () => {
      const core = coreSelect?.value || "";
      return [core, linked?.checked ? core : packageSelect?.value || ""].filter(Boolean);
    };
    const showChannelRisk = () => {
      if (packageSelect && linked?.checked) packageSelect.value = coreSelect?.value || "";
      if (packageSelect) packageSelect.disabled = Boolean(linked?.checked);
      if (coreHint) coreHint.textContent = coreSelect?.selectedOptions[0]?.dataset.description || "";
      if (packageHint) packageHint.textContent = packageSelect?.selectedOptions[0]?.dataset.description || "";
      const channels = effectiveChannels();
      if (testingWarning) testingWarning.hidden = !channels.includes("testing");
      if (devWarning) devWarning.hidden = !channels.includes("dev");
    };
    [coreSelect, packageSelect, linked].forEach((control) => control?.addEventListener("change", showChannelRisk));
    channelForm.addEventListener("submit", (event) => {
      if (!effectiveChannels().includes("dev")) return;
      const accepted = window.confirm(channelForm.dataset.devConfirm);
      if (!accepted) event.preventDefault();
    });
    showChannelRisk();
  }
})();
