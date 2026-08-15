(() => {
  "use strict";

  function responseFilename(response) {
    const disposition = response.headers.get("Content-Disposition") || "";
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    if (encoded) return decodeURIComponent(encoded);
    return disposition.match(/filename="([^"]+)"/i)?.[1] || "campaign.gwcampaign";
  }

  async function refreshFor(payload, success, fallback) {
    const key = success ? payload.message_key : payload.error_key;
    const query = success ? "campaign_message_key" : "campaign_error_key";
    await window.GravewrightInside.refresh(
      `/inside?${query}=${encodeURIComponent(key || fallback)}`,
    );
  }

  async function exportCampaign(form) {
    const response = await fetch(form.action, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/zip",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: new URLSearchParams(new FormData(form)),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      await refreshFor(payload, false, "campaign.export.errors.validation");
      return;
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = responseFilename(response);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function importCampaign(form) {
    const response = await fetch(form.action, {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
      body: new FormData(form),
    });
    const payload = await response.json().catch(() => ({}));
    await refreshFor(payload, response.ok && payload.ok !== false, "campaign.import.errors.failed");
  }

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest(".campaign-export-form, .campaign-import-form");
    if (!form || event.defaultPrevented) return;
    event.preventDefault();
    form.setAttribute("aria-busy", "true");
    try {
      if (form.matches(".campaign-export-form")) await exportCampaign(form);
      else await importCampaign(form);
    } finally {
      form.removeAttribute("aria-busy");
    }
  });
})();
