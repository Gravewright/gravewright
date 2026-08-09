(() => {
  "use strict";
  const labels = document.body.dataset;
  function summaryText(summary) {
    return ["packages", "scenes", "actors", "items", "journals"]
      .map((key) => `${labels[`clone${key[0].toUpperCase()}${key.slice(1)}`] || key}: ${summary[key] || 0}`)
      .join(" \u00b7 ");
  }
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-campaign-clone-dry-run]");
    if (!button) return;
    const form = button.closest("[data-campaign-clone-form]");
    const preview = form.querySelector("[data-campaign-clone-preview]");
    button.disabled = true;
    const result = await window.GravewrightCore.http.postForm(
      "/campaigns/clone/preview", new FormData(form),
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
})();
