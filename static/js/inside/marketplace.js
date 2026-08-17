(() => {
  const root = document.querySelector("[data-marketplace]");
  if (!root) return;
  const navigate = window.GravewrightMarketplaceNavigate || ((hash) => {
    location.hash = hash;
    location.reload();
  });
  const sectionForHash = {
    "#marketplace": "section-marketplace",
    "#rulesets": "section-systems",
    "#modules": "section-modules",
  }[location.hash];
  if (sectionForHash) document.querySelector(`#${sectionForHash}`)?.click();

  const search = root.querySelector("[data-marketplace-search]");
  const kind = root.querySelector("[data-marketplace-kind]");
  const filter = () => {
    const query = (search?.value || "").trim().toLocaleLowerCase();
    root.querySelectorAll("[data-marketplace-package]").forEach((card) => {
      card.hidden = Boolean((kind?.value && card.dataset.kind !== kind.value)
        || (query && !card.dataset.search.toLocaleLowerCase().includes(query)));
    });
    root.querySelectorAll("[data-marketplace-band]").forEach((band) => {
      band.hidden = !band.querySelector("[data-marketplace-package]:not([hidden])");
    });
  };
  search?.addEventListener("input", filter);
  kind?.addEventListener("change", filter);
  root.querySelectorAll("[data-marketplace-time]").forEach((time) => {
    time.textContent = new Date(Number(time.dataset.marketplaceTime) * 1000).toLocaleString();
  });

  root.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-marketplace-install], [data-marketplace-refresh]");
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const status = form.closest("[data-marketplace-package]")?.querySelector("[data-marketplace-package-status]")
      || root.querySelector("[data-marketplace-status]");
    const old = status?.textContent || "";
    if (status) status.textContent = form.matches("[data-marketplace-refresh]") ? "Refreshing…" : "Installing…";
    if (button) button.disabled = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new URLSearchParams(new FormData(form)),
        headers: {Accept: "application/json"},
        credentials: "same-origin",
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error_key || "Marketplace action failed");
      if (form.matches("[data-marketplace-refresh]")) {
        location.hash = "marketplace";
        location.reload();
      } else {
        const installedKind = form.closest("[data-marketplace-package]")?.dataset.kind;
        navigate(installedKind === "ruleset" ? "rulesets" : "modules");
      }
    } catch (error) {
      if (status) status.textContent = String(error?.message || error);
      if (button) button.disabled = false;
      if (!status) console.error(error);
      else status.dataset.previousStatus = old;
    }
  });
})();
