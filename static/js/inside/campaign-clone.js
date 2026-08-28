(() => {
  "use strict";
  const labels = document.body.dataset;
  function summaryText(summary) {
    return ["packages", "scenes", "actors", "items", "journals"]
      .map((key) => `${labels[`clone${key[0].toUpperCase()}${key.slice(1)}`] || key}: ${summary[key] || 0}`)
      .join(" \u00b7 ");
  }
  function encodedForm(form) {
    return new URLSearchParams(new FormData(form));
  }
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-campaign-clone-dry-run]");
    if (!button) return;
    const form = button.closest("[data-campaign-clone-form]");
    const preview = form.querySelector("[data-campaign-clone-preview]");
    button.disabled = true;
    const result = await window.GravewrightCore.http.postForm(
      "/campaigns/clone/preview", encodedForm(form),
      { headers: { "X-Requested-With": "XMLHttpRequest" } }
    );
    button.disabled = false;
    preview.hidden = false;
    if (!result.ok || result.data?.ok === false) {
      preview.textContent = labels.cloneError;
      preview.classList.add("notice--danger");
      return;
    }
    preview.classList.remove("notice--danger");
    preview.textContent = `${labels.clonePreview}: ${summaryText(result.data.summary)}`;
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-campaign-clone-form]");
    if (!form || event.defaultPrevented) return;
    event.preventDefault();
    form.setAttribute("aria-busy", "true");
    const result = await window.GravewrightCore.http.postForm(
      form.action, encodedForm(form),
      { headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" } }
    );
    form.removeAttribute("aria-busy");
    const payload = result.data || {};
    const success = result.ok && payload.ok !== false;
    const key = success ? payload.message_key : payload.error_key;
    const query = success ? "campaign_message_key" : "campaign_error_key";
    await window.GravewrightInside.refresh(`/inside?${query}=${encodeURIComponent(key || "campaign.clone.errors.failed")}`);
  });
})();
