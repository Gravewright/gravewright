




(function () {
  const selectedTokensByRoom = new Map();
  const lastStateByRoom = new Map();

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      console.warn("Combat request failed", url, res.status, error);
      return null;
    }
    return res.json().catch(() => ({}));
  }

  async function fetchState(roomId) {
    if (!roomId) return null;
    const res = await fetch(`/game/combat/state/${encodeURIComponent(roomId)}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    return res.ok ? res.json().catch(() => null) : null;
  }

  function publishState(roomId, state) {
    if (!roomId) return;
    lastStateByRoom.set(roomId, state || {});
    window.GravewrightCombatState?.set?.(roomId, state || {});
  }

  function selectedTokenCount(roomId) {
    return selectedTokensByRoom.get(roomId)?.size || 0;
  }

  function selectedTokenPayload(roomId) {
    const tokenIds = [...(selectedTokensByRoom.get(roomId) || new Set())];
    const actorIds = [];
    const canvas = window.GravewrightMap?.activeCanvas?.();
    const store = canvas && window.GravewrightMap?.tokenStoreFor ? window.GravewrightMap.tokenStoreFor(canvas) : null;
    if (store && canvas?.dataset?.roomId === roomId) {
      tokenIds.forEach((tokenId) => {
        const token = store.get(tokenId);
        if (token?.actor_id && !actorIds.includes(token.actor_id)) actorIds.push(token.actor_id);
      });
    }
    return { token_ids: tokenIds, actor_ids: actorIds };
  }

  function renderRoom(roomId, state) {
    const payload = state || lastStateByRoom.get(roomId) || {};
    document.querySelectorAll(`[data-combat-hud][data-room-id="${CSS.escape(roomId)}"]`).forEach((hud) => window.GravewrightCombatPanel?.renderHud?.(hud, payload));
    document.querySelectorAll(`[data-combat-panel][data-room-id="${CSS.escape(roomId)}"]`).forEach((panel) => {
      panel.dataset.selectedTokenCount = String(selectedTokenCount(roomId));
      window.GravewrightCombatPanel?.renderPanel?.(panel, payload);
    });
  }

  async function refreshRoom(roomId) {
    const state = await fetchState(roomId);
    publishState(roomId, state || {});
    renderRoom(roomId, state || {});
  }

  async function perform(roomId, action, extra) {
    const csrf = document.querySelector(`[data-combat-panel][data-room-id="${CSS.escape(roomId)}"]`)?.dataset.csrf ||
      document.querySelector(`[data-combat-hud][data-room-id="${CSS.escape(roomId)}"]`)?.dataset.csrf ||
      window.csrfToken();
    const url = `/game/combat/${action}`;
    const data = await postJSON(url, { campaign_id: roomId, csrf_token: csrf, ...(extra || {}) });
    if (data) {
      publishState(roomId, data);
      renderRoom(roomId, data);
    }
  }

  function handlePanelAction(button, panel) {
    const action = button.dataset.combatPanelAction;
    const roomId = panel.dataset.roomId;
    button.closest("details")?.removeAttribute("open");
    if (action === "token/focus") {
      const tokenId = button.dataset.tokenId || "";
      if (tokenId) window.GravewrightMap?.centerOnToken?.(tokenId);
      return;
    }
    if (action === "token/sheet") {
      const tokenId = button.dataset.tokenId || "";
      if (tokenId) {
        document.dispatchEvent(new CustomEvent("vtt:open-token-sheet", { detail: { tokenId } }));
      }
      return;
    }

    const extra = {};
    if (action === "participants/remove") {
      extra.participant_id = button.dataset.participantId || "";
    } else if (action === "initiative/participant/roll") {
      extra.participant_id = button.dataset.participantId || "";
    } else if (action === "turn/set") {
      extra.turn_index = Number(button.dataset.turnIndex || 0);
    } else if (action === "participants/add-selected") {
      Object.assign(extra, selectedTokenPayload(roomId));
      if (!extra.token_ids?.length && !extra.actor_ids?.length) return;
    }
    perform(roomId, action, extra);
  }

  document.addEventListener("click", (event) => {
    const hudButton = event.target.closest("[data-combat-action]");
    if (hudButton) {
      const hud = hudButton.closest("[data-combat-hud]");
      if (hud) perform(hud.dataset.roomId, hudButton.dataset.combatAction);
      return;
    }

    const filter = event.target.closest("[data-combat-filter]");
    if (filter) {
      const panel = filter.closest("[data-combat-panel]");
      if (!panel) return;
      panel.dataset.combatFilter = filter.dataset.combatFilter || "all";
      window.GravewrightCombatPanel?.renderPanel?.(panel, lastStateByRoom.get(panel.dataset.roomId) || {});
      return;
    }

    const button = event.target.closest("[data-combat-panel-action]");
    if (!button) return;
    const panel = button.closest("[data-combat-panel]");
    if (!panel) return;
    handlePanelAction(button, panel);
  });

  document.addEventListener("input", (event) => {
    const input = event.target.closest("[data-combat-search]");
    if (!input) return;
    const panel = input.closest("[data-combat-panel]");
    if (!panel) return;
    panel.dataset.combatSearch = input.value || "";
    window.GravewrightCombatPanel?.renderPanel?.(panel, lastStateByRoom.get(panel.dataset.roomId) || {});
    const restored = panel.querySelector("[data-combat-search]");
    if (restored) {
      restored.focus();
      const pos = restored.value.length;
      restored.setSelectionRange?.(pos, pos);
    }
  });

  document.addEventListener("vtt:token-selection-changed", (event) => {
    const roomId = event.detail?.roomId || "";
    if (!roomId) return;
    selectedTokensByRoom.set(roomId, new Set(event.detail?.tokenIds || []));
    renderRoom(roomId, lastStateByRoom.get(roomId) || {});
  });

  document.addEventListener("DOMContentLoaded", () => {
    const roomIds = new Set();
    document.querySelectorAll("[data-combat-hud], [data-combat-panel]").forEach((node) => {
      if (node.dataset.roomId) roomIds.add(node.dataset.roomId);
    });
    roomIds.forEach((roomId) => refreshRoom(roomId));
  });

  function receiveState(roomId, state) {
    if (!roomId) return;
    publishState(roomId, state || {});
    renderRoom(roomId, state || {});
  }

  window.GravewrightCombatActions = { refreshRoom, receiveState };
})();
