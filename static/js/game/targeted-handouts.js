(function () {
  function csrf() {
    return typeof window.csrfToken === "function" ? window.csrfToken() : "";
  }

  async function request(url, options) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "application/json", "Content-Type": "application/json", "x-csrftoken": csrf() },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error_key || "handout.errors.generic");
    return data;
  }

  function notice(panel, text, danger) {
    const node = panel.querySelector("[data-handout-notice]");
    node.textContent = text;
    node.hidden = false;
    node.classList.toggle("game-notice--danger", Boolean(danger));
  }

  document.addEventListener("click", async (event) => {
    const opener = event.target.closest("[data-handout-resource]");
    if (opener) {
      const dialog = document.querySelector(`[data-handout-dialog][data-campaign-id="${CSS.escape(opener.dataset.campaignId || "")}"]`);
      if (!dialog) return;
      const form = dialog.querySelector("[data-handout-form]");
      form.elements.resource_type.value = opener.dataset.handoutResource;
      form.elements.resource_id.value = opener.dataset.resourceId;
      form.elements.all_players.checked = true;
      form.querySelectorAll('[name="players"]').forEach((input) => {
        input.checked = false;
        input.disabled = true;
      });
      dialog.querySelector("[data-handout-notice]").hidden = true;
      dialog.showModal();
      return;
    }
    const close = event.target.closest("[data-handout-close]");
    if (close) close.closest("[data-handout-dialog]")?.close();
  });

  document.addEventListener("change", (event) => {
    if (event.target.name !== "all_players") return;
    const form = event.target.closest("[data-handout-form]");
    form?.querySelectorAll('[name="players"]').forEach((input) => {
      input.disabled = event.target.checked;
      if (event.target.checked) input.checked = false;
    });
  });

  async function showRemoteResource(resourceType, ticket) {
    const response = await fetch(`/game/handouts/presentation/${encodeURIComponent(ticket)}`, {
      credentials: "same-origin", headers: { Accept: "text/html" },
    });
    if (!response.ok) return;
    const template = document.createElement("template");
    template.innerHTML = (await response.text()).trim();
    const modal = template.content.querySelector("[data-modal-window]");
    if (!modal) return;
    modal.querySelectorAll('img[src^="/game/journal/asset/"]').forEach((image) => {
      const assetId = image.getAttribute("src").slice("/game/journal/asset/".length).split(/[?#]/, 1)[0];
      if (assetId && !assetId.includes("/")) {
        image.src = `/game/handouts/presentation/${encodeURIComponent(ticket)}/asset/${encodeURIComponent(assetId)}`;
      }
    });
    document.querySelector(`[data-modal-id="${CSS.escape(modal.dataset.modalId)}"]`)?.remove();
    document.querySelector(".game-modal-layer")?.append(modal);
    document.dispatchEvent(new CustomEvent(
      resourceType === "journal" ? "vtt:journal-modal-mounted" : "vtt:item-sheet-modal-mounted",
      { detail: { modal } },
    ));
    window.GravewrightModals?.open?.(modal.dataset.modalId);
  }

  function showAsset(ticket) {
    const modalId = `handout-asset-${ticket.slice(0, 12)}`;
    let modal = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`);
    if (!modal) {
      modal = document.createElement("article");
      modal.className = "game-modal-window game-panel";
      modal.dataset.modalWindow = "";
      modal.dataset.modalId = modalId;
      modal.dataset.windowKey = modalId;
      modal.hidden = true;
      modal.innerHTML = `<header class="game-modal-titlebar" data-modal-drag-handle>
        <span class="game-panel-title">Show to Players</span>
        <div class="game-modal-controls"><button class="game-modal-control" type="button" data-modal-close aria-label="Close"><i class="ph ph-x" aria-hidden="true"></i></button></div>
      </header><div class="game-panel-body"><img alt="" style="display:block;max-width:100%;max-height:75vh;margin:auto"></div>`;
      modal.querySelector("img").src = `/game/handouts/presentation/${encodeURIComponent(ticket)}`;
      document.querySelector(".game-modal-layer")?.append(modal);
    }
    window.GravewrightModals?.open?.(modalId);
  }

  document.addEventListener("vtt:transport-event", (event) => {
    if (event.detail?.event !== "handout.presented") return;
    const payload = event.detail.payload || {};
    if (!payload.ticket) return;
    if (payload.resource_type === "asset") showAsset(payload.ticket);
    else if (["journal", "item"].includes(payload.resource_type)) {
      showRemoteResource(payload.resource_type, payload.ticket).catch(() => {});
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-handout-form]");
    if (!form) return;
    event.preventDefault();
    const dialog = form.closest("[data-handout-dialog]");
    const selected = Array.from(form.querySelectorAll('[name="players"]:checked')).map((input) => input.value);
    if (!form.elements.all_players.checked && !selected.length) {
      notice(dialog, dialog.dataset.errorGeneric, true);
      return;
    }
    try {
      const audiences = form.elements.all_players.checked ? [""] : selected;
      await Promise.all(audiences.map((userId) => request("/game/handouts/present", {
        method: "POST", body: JSON.stringify({
          campaign_id: dialog.dataset.campaignId,
          resource_type: form.elements.resource_type.value,
          resource_id: form.elements.resource_id.value.trim(),
          subject_type: userId ? "user" : "everyone", subject_id: userId,
        }),
      })));
      dialog.close();
    } catch { notice(dialog, dialog.dataset.errorGeneric, true); }
  });
})();
