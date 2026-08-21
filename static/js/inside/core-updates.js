(() => {
  "use strict";
  const root = document.querySelector("[data-core-update]");
  if (!root) return;
  const status = root.querySelector("[data-core-update-status]");
  const available = root.querySelector("[data-core-update-available]");
  const channel = root.querySelector("[data-core-update-channel]");
  const action = root.querySelector("[data-core-update-action]");
  const details = root.querySelector("[data-core-update-details]");

  function render(update) {
    root.dataset.state = update.status || "failed";
    if (available) available.textContent = update.availableVersion || "—";
    if (channel) channel.textContent = update.channel || "—";
    if (status) status.textContent = update.status === "available"
      ? `Update available — ${update.currentVersion} → ${update.availableVersion}`
      : update.status === "current" ? "Up to date" : `Check failed — ${update.errorKey || "unknown error"}`;
    const artifact = update.artifact;
    if (action) {
      action.hidden = !artifact?.url;
      if (artifact?.url) action.href = artifact.url;
    }
    if (details) details.textContent = update.status === "available"
      ? `Create a verified backup before installing. SHA-256: ${artifact?.sha256 || "unavailable"}. `
        + `Install format: ${update.installFormat}. Data directories are not part of the product artifact.`
      : "";
  }

  root.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-core-update-check]");
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector("button");
    if (button) button.disabled = true;
    if (status) status.textContent = "Checking official releases…";
    try {
      const response = await fetch(form.action, {method: "POST", credentials: "same-origin",
        headers: {Accept: "application/json", "x-csrftoken": window.csrfToken?.() || ""}});
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.update?.errorKey || result.errorKey);
      render(result.update);
    } catch (error) {
      if (status) status.textContent = `Check failed — ${error?.message || error}`;
    } finally {
      if (button) button.disabled = false;
    }
  });
})();
