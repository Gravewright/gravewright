(function () {
  const currentUserId = () => document.body.dataset.currentUserId || "";
  const csrf = () => typeof window.csrfToken === "function" ? window.csrfToken() : "";

  async function request(url, options) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "application/json", "Content-Type": "application/json", "x-csrftoken": csrf() },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error_key || "lobby.errors.generic");
    return data;
  }

  function render(panel, data) {
    const form = panel.querySelector("[data-lobby-form]");
    const own = (data.members || []).find((member) => member.user_id === currentUserId());
    const select = form.elements.selected_actor_id;
    const previous = own?.selected_actor_id || select.value;
    select.replaceChildren(new Option(document.body.dataset.lobbyNoActor || "Sem personagem", ""));
    (data.actors || []).forEach((actor) => select.add(new Option(actor.name, actor.id)));
    select.value = previous;
    form.elements.is_ready.checked = Boolean(own?.is_ready);
    panel.querySelector("[data-lobby-summary]").textContent = `${data.summary.ready} / ${data.summary.total}`;
    const root = panel.querySelector("[data-lobby-members]");
    root.replaceChildren();
    (data.members || []).forEach((member) => {
      const card = document.createElement("article");
      card.className = "player-card";
      const status = member.is_online ? "●" : "○";
      const ready = member.is_ready ? (document.body.dataset.lobbyReady || "Pronto") : (document.body.dataset.lobbyWaiting || "Aguardando");
      card.textContent = `${status} ${member.name}: ${ready}: ${member.selected_actor_name || (document.body.dataset.lobbyNoActor || "Sem personagem")}: ${member.assets_state}`;
      root.append(card);
    });
  }

  async function refresh(panel) {
    const data = await request(`/game/lobby?campaign_id=${encodeURIComponent(panel.dataset.campaignId)}`);
    render(panel, data);
  }

  document.addEventListener("click", (event) => {
    const open = event.target.closest('[data-modal-open^="lobby-"]');
    if (!open) return;
    const panel = document.querySelector(`[data-modal-id="${CSS.escape(open.dataset.modalOpen)}"] [data-lobby-panel]`);
    if (panel) refresh(panel).catch(() => {
      const notice = panel.querySelector("[data-lobby-notice]"); notice.textContent = panel.dataset.error; notice.hidden = false;
    });
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-lobby-form]");
    if (!form) return;
    event.preventDefault();
    const panel = form.closest("[data-lobby-panel]");
    try {
      await request("/game/lobby/state", { method: "POST", body: JSON.stringify({
        campaign_id: panel.dataset.campaignId,
        is_ready: form.elements.is_ready.checked,
        selected_actor_id: form.elements.selected_actor_id.value || null,
        assets_state: document.readyState === "complete" ? "ready" : "loading",
      }) });
      await refresh(panel);
    } catch {
      const notice = panel.querySelector("[data-lobby-notice]"); notice.textContent = panel.dataset.error; notice.hidden = false;
    }
  });

  document.addEventListener("vtt:transport-event", (event) => {
    if (!["lobby.updated", "presence.updated", "presence.snapshot"].includes(event.detail?.event)) return;
    const roomId = event.detail?.payload?.room_id;
    const panel = document.querySelector(`[data-lobby-panel][data-campaign-id="${CSS.escape(roomId || "")}"]`);
    if (panel && !panel.closest("[data-modal-window]")?.hidden) refresh(panel).catch(() => {});
  });

  window.setInterval(() => {
    document.querySelectorAll("[data-lobby-panel]").forEach((panel) => {
      if (!panel.closest("[data-modal-window]")?.hidden) refresh(panel).catch(() => {});
    });
  }, 10000);
})();
