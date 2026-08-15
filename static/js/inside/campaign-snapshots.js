











(() => {
  "use strict";

  function itemOf(target) {
    return target.closest("[data-snapshot-item]");
  }

  function closeAll(item) {
    item.querySelectorAll("[data-snapshot-confirm]").forEach((form) => {
      form.hidden = true;
    });
    item.querySelectorAll("[data-snapshot-ask]").forEach((button) => {
      button.setAttribute("aria-expanded", "false");
    });
    const actions = item.querySelector(".snapshot-actions");
    if (actions) actions.hidden = false;
  }

  function open(item, intent) {
    closeAll(item);
    const form = item.querySelector(`[data-snapshot-confirm="${intent}"]`);
    if (!form) return;
    form.hidden = false;
    const actions = item.querySelector(".snapshot-actions");
    if (actions) actions.hidden = true;
    const ask = item.querySelector(`[data-snapshot-ask="${intent}"]`);
    if (ask) ask.setAttribute("aria-expanded", "true");
    form.querySelector("button[type='submit']")?.focus();
  }

  document.addEventListener("click", (event) => {
    const ask = event.target.closest("[data-snapshot-ask]");
    if (ask) {
      const item = itemOf(ask);
      if (!item) return;
      event.preventDefault();
      open(item, ask.dataset.snapshotAsk);
      return;
    }

    const cancel = event.target.closest("[data-snapshot-cancel]");
    if (cancel) {
      const item = itemOf(cancel);
      if (!item) return;
      event.preventDefault();
      closeAll(item);
      const intent = cancel.closest("[data-snapshot-confirm]")?.dataset.snapshotConfirm;
      item.querySelector(`[data-snapshot-ask="${intent}"]`)?.focus();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const item = itemOf(event.target);
    if (item) closeAll(item);
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest(".campaign-snapshot-create, .snapshot-confirm");
    if (!form || event.defaultPrevented) return;
    event.preventDefault();
    form.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: new URLSearchParams(new FormData(form)),
      });
      const payload = await response.json().catch(() => ({}));
      const key = response.ok && payload.ok !== false ? payload.message_key : payload.error_key;
      const query = response.ok && payload.ok !== false ? "campaign_message_key" : "campaign_error_key";
      await window.GravewrightInside?.refresh(`/inside?${query}=${encodeURIComponent(key || "campaign.snapshot.errors.failed")}`);
    } catch (_) {
      await window.GravewrightInside?.refresh("/inside?campaign_error_key=campaign.snapshot.errors.failed");
    } finally {
      form.removeAttribute("aria-busy");
    }
  });



  function stampTimes(root) {
    (root || document).querySelectorAll("[data-snapshot-time]").forEach((el) => {
      if (el.dataset.stamped) return;
      const seconds = Number(el.dataset.snapshotTime);
      if (!Number.isFinite(seconds)) return;
      const when = new Date(seconds * 1000);
      el.dateTime = when.toISOString();
      el.textContent = when.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
      el.dataset.stamped = "1";
    });
  }

  document.addEventListener("DOMContentLoaded", () => stampTimes());

  document.addEventListener("inside:rendered", () => stampTimes());
  stampTimes();
})();
