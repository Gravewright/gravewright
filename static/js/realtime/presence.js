






(function () {
  const MEMBER_JOINED_EVENT = "member.joined";
  const MEMBER_REMOVED_EVENT = "member.removed";

  let didSendLeave = false;

  function escapeHtml(value) {
    const core = window.GravewrightCore;
    if (core && core.sanitization) {
      return core.sanitization.escapeHtml(value);
    }
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getCsrfToken() {
    return document.body.dataset.presenceCsrfToken || "";
  }

  function getOnlineLabel() {
    return document.body.dataset.presenceOnlineLabel || "Online";
  }

  function getOfflineLabel() {
    return document.body.dataset.presenceOfflineLabel || "Offline";
  }

  function getCurrentUserId() {
    return document.body.dataset.currentUserId || "";
  }

  function getRoleLabel(role) {
    const labels = {
      gm: document.body.dataset.roleGm || "GM",
      assistant_gm: document.body.dataset.roleAssistantGm || "Assistant GM",
      player: document.body.dataset.rolePlayer || "Player",
      streamer: document.body.dataset.roleStreamer || "Streamer",
    };

    return labels[role] || role || "";
  }

  function getBanErrorLabel(key) {
    const labels = {
      "auth.errors.session_expired": "playerBanErrorSessionExpired",
      "inside.campaigns.errors.gm_required": "playerBanErrorDenied",
      "game.players.errors.cannot_ban_self": "playerBanErrorSelf",
      "game.players.errors.cannot_ban_gm": "playerBanErrorGm",
      "game.players.errors.not_found": "playerBanErrorNotFound",
    };
    const prop = labels[key];
    return prop ? document.body.dataset[prop] || key : key;
  }

  function updatePlayerStatus(roomId, player) {
    const selector = `.player-card[data-room-id="${roomId}"][data-player-id="${player.user_id}"]`;
    const cards = document.querySelectorAll(selector);

    cards.forEach((card) => {
      const dot = card.querySelector(".status-dot");
      const statusText = card.querySelector(".player-status-text");

      if (dot) {
        dot.classList.toggle("status-dot--online", Boolean(player.is_online));
        dot.classList.toggle("status-dot--offline", !player.is_online);
      }

      if (statusText) {
        statusText.textContent = player.is_online
          ? getOnlineLabel()
          : getOfflineLabel();
      }
    });
  }

  function getPlayerList(roomId) {
    return document.querySelector(`[data-player-list][data-room-id="${roomId}"]`);
  }

  function markCurrentUserOnline() {
    const userId = getCurrentUserId();
    if (!userId) {
      return;
    }

    document
      .querySelectorAll(`.player-card[data-player-id="${userId}"]`)
      .forEach((card) => {
        const dot = card.querySelector(".status-dot");
        const statusText = card.querySelector(".player-status-text");

        if (dot) {
          dot.classList.add("status-dot--online");
          dot.classList.remove("status-dot--offline");
        }

        if (statusText) {
          statusText.textContent = getOnlineLabel();
        }
      });
  }

  function buildBanForm(roomId, userId) {
    const label = document.body.dataset.playerBanLabel || "Ban";
    return `
            <form class="player-ban-form" method="post" action="/game/member/ban">
                <input type="hidden" name="_csrf_token" value="${escapeHtml(getCsrfToken())}" />
                <input type="hidden" name="campaign_id" value="${escapeHtml(roomId)}" />
                <input type="hidden" name="user_id" value="${escapeHtml(userId)}" />
                <button class="player-ban-button" type="submit" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}">
                    <i class="ph ph-user-minus" aria-hidden="true"></i>
                </button>
            </form>
        `;
  }

  function buildPlayerCard(roomId, player, canBan) {
    const card = document.createElement("article");
    card.className = "player-card";
    card.dataset.roomId = roomId;
    card.dataset.playerId = player.user_id || "";

    const isOnline = Boolean(player.is_online);
    const canBanPlayer =
      canBan && player.role !== "gm" && player.user_id !== getCurrentUserId();

    card.innerHTML = `
            <div class="player-main">
                <div class="player-name-row">
                    <span class="status-dot ${isOnline ? "status-dot--online" : "status-dot--offline"}" aria-hidden="true"></span>
                    <strong>${escapeHtml(player.name)}</strong>
                </div>
            </div>
            <div class="player-side">
                <small class="player-status-text">${isOnline ? escapeHtml(getOnlineLabel()) : escapeHtml(getOfflineLabel())}</small>
                <em>${escapeHtml(getRoleLabel(player.role))}</em>
                ${canBanPlayer ? buildBanForm(roomId, player.user_id) : ""}
            </div>
        `;

    return card;
  }

  function upsertPlayer(roomId, player) {
    if (!roomId || !player || !player.user_id) {
      return;
    }

    const list = getPlayerList(roomId);
    if (!list) {
      return;
    }

    const selector = `.player-card[data-room-id="${roomId}"][data-player-id="${player.user_id}"]`;
    const existing = document.querySelector(selector);

    if (existing) {
      existing.querySelector("strong").textContent = player.name || "";
      const role = existing.querySelector(".player-side em");
      if (role) {
        role.textContent = getRoleLabel(player.role);
      }
      updatePlayerStatus(roomId, player);
      return;
    }

    list.appendChild(buildPlayerCard(roomId, player, list.dataset.canBan === "true"));
  }

  function removePlayer(roomId, userId) {
    const selector = `.player-card[data-room-id="${roomId}"][data-player-id="${userId}"]`;
    document.querySelectorAll(selector).forEach((card) => card.remove());
  }

  function processPresenceUpdated(payload) {
    if (!payload || !payload.room_id || !payload.user_id) {
      return;
    }

    updatePlayerStatus(payload.room_id, {
      user_id: payload.user_id,
      is_online: payload.is_online,
    });
  }

  function processPresenceSnapshot(payload) {
    if (!payload || !payload.room_id || !Array.isArray(payload.players)) {
      return;
    }

    payload.players.forEach((player) => {
      upsertPlayer(payload.room_id, player);
    });
  }

  function processPlayerJoined(payload) {
    if (!payload || !payload.room_id || !payload.player) {
      return;
    }

    upsertPlayer(payload.room_id, payload.player);
  }

  function processPlayerLeft(payload) {
    if (!payload || !payload.room_id || !payload.user_id) {
      return;
    }

    removePlayer(payload.room_id, payload.user_id);

    if (payload.user_id === getCurrentUserId() && payload.reason === "banned") {
      window.location.href = "/inside";
    }
  }

  

  function sendLeave() {
    const csrfToken = getCsrfToken();

    if (!csrfToken || didSendLeave) {
      return;
    }

    didSendLeave = true;

    
    
    const body = new URLSearchParams({ _csrf_token: csrfToken }).toString();

    if (navigator.sendBeacon) {
      const payload = new Blob([body], {
        type: "application/x-www-form-urlencoded",
      });

      navigator.sendBeacon("/game/presence/leave", payload);
      return;
    }

    fetch("/game/presence/leave", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
      },
      body,
      credentials: "same-origin",
      keepalive: true,
      cache: "no-store",
    }).catch(() => {});
  }

  

  function showPlayerNotice(form, message) {
    let notice = form
      .closest(".players-section")
      ?.querySelector(".player-action-notice");

    if (!notice) {
      notice = document.createElement("div");
      notice.className = "player-action-notice game-notice game-notice--danger";
      notice.setAttribute("role", "alert");
      form
        .closest(".players-section")
        ?.insertBefore(notice, form.closest(".player-list"));
    }

    notice.textContent = message;
    notice.hidden = false;
  }

  async function submitBanForm(form) {
    const confirmMessage = document.body.dataset.playerBanConfirm || "";
    if (confirmMessage && !window.confirm(confirmMessage)) {
      return;
    }

    const response = await fetch(form.action, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
      },
      body: new URLSearchParams(new FormData(form)),
      credentials: "same-origin",
      cache: "no-store",
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok || !data.ok) {
      showPlayerNotice(
        form,
        getBanErrorLabel(data.error_key || "game.players.errors.not_found")
      );
    }
  }

  document.addEventListener("submit", (event) => {
    const form = event.target.closest(".player-ban-form");

    if (!form) {
      return;
    }

    event.preventDefault();

    submitBanForm(form).catch(() => {
      showPlayerNotice(form, getBanErrorLabel("game.players.errors.not_found"));
    });
  });

  // The current user is online the moment their socket is open — reflect it
  // immediately instead of waiting on the server presence snapshot.
  document.addEventListener("vtt:ws-open", markCurrentUserOnline);

  window.addEventListener("pagehide", sendLeave);
  window.addEventListener("beforeunload", sendLeave);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      didSendLeave = false;
    }
  });

  window.GravewrightPresence = {
    processPlayerJoined,
    processPlayerLeft,
    processPresenceUpdated,
    processPresenceSnapshot,
    upsertPlayer,
    removePlayer,
    MEMBER_JOINED_EVENT,
    MEMBER_REMOVED_EVENT,
  };
})();
