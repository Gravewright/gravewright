




(function () {
    const selectedTokens = new Map();
    const lastState = new Map();



    const ACTIONS = {
        "start": ["start"],
        "end": ["end"],
        "combatants/remove": ["combatants/remove", (btn) => ({ combatant_id: btn.dataset.combatantId })],
        "flags/hidden": ["combatants/flags", (btn) => ({
            combatant_id: btn.dataset.combatantId,
            hidden: btn.dataset.value === "1",
        })],
        "flags/defeated": ["combatants/flags", (btn) => ({
            combatant_id: btn.dataset.combatantId,
            defeated: btn.dataset.value === "1",
        })],
        "initiative/roll-all": ["initiative/roll", () => ({ scope: "all" })],
        "initiative/roll-npcs": ["initiative/roll", () => ({ scope: "npc" })],
        "initiative/roll-missing": ["initiative/roll", () => ({ scope: "missing" })],
        "initiative/roll-one": ["initiative/roll", (btn) => ({ combatant_id: btn.dataset.combatantId })],
        "turn/next": ["turn", () => ({ delta: 1 })],
        "turn/previous": ["turn", () => ({ delta: -1 })],
        "turn/set": ["turn", (btn) => ({ combatant_id: btn.dataset.combatantId })],
        "order/up": ["order", (btn) => ({ combatant_id: btn.dataset.combatantId, delta: -1 })],
        "order/down": ["order", (btn) => ({ combatant_id: btn.dataset.combatantId, delta: 1 })],
        "round/next": ["round", () => ({ delta: 1 })],
        "round/previous": ["round", () => ({ delta: -1 })],
    };

    function panelFor(roomId) {
        return document.querySelector(`[data-combat-panel][data-room-id="${CSS.escape(roomId)}"]`);
    }

    async function post(roomId, path, body) {
        const res = await fetch(`/game/combat/${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                campaign_id: roomId,
                csrf_token: panelFor(roomId)?.dataset.csrf || window.csrfToken(),
                ...(body || {}),
            }),
        });
        if (!res.ok) {
            console.warn("Combat request failed", path, res.status);
            return null;
        }
        return res.json().catch(() => null);
    }

    function publish(roomId, state) {
        if (!roomId) return;
        lastState.set(roomId, state || {});
        window.GravewrightCombatState?.set?.(roomId, state || {});
        const panel = panelFor(roomId);
        if (!panel) return;
        panel.dataset.selectedTokenCount = String(selectedTokens.get(roomId)?.size || 0);
        window.GravewrightCombatPanel?.renderPanel?.(panel, state || {});
    }

    async function perform(roomId, path, body) {
        const previousState = lastState.get(roomId) || {};
        const state = await post(roomId, path, body);
        if (state) {
            publish(roomId, state);
            const systemId = String(state?.config?.system_id || previousState?.config?.system_id || "");
            window.GravewrightCombat?.dispatch?.(systemId, "afterAction", {
                action: path,
                state,
                previousState,
                roomId,
            });
        }
    }

    async function refreshRoom(roomId) {
        if (!roomId) return;
        const res = await fetch(`/game/combat/state/${encodeURIComponent(roomId)}`, {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        });
        publish(roomId, res.ok ? await res.json().catch(() => ({})) : {});
    }


    function selectionPayload(roomId) {
        const tokenIds = [...(selectedTokens.get(roomId) || new Set())];
        const actorIds = [];
        const canvas = window.GravewrightMap?.activeCanvas?.();
        const store = canvas && window.GravewrightMap?.tokenStoreFor
            ? window.GravewrightMap.tokenStoreFor(canvas)
            : null;
        if (store && canvas?.dataset?.roomId === roomId) {
            tokenIds.forEach((tokenId) => {
                const actorId = store.get(tokenId)?.actor_id;
                if (actorId && !actorIds.includes(actorId)) actorIds.push(actorId);
            });
        }
        return { token_ids: tokenIds, actor_ids: actorIds };
    }

    document.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-combat-action]");
        if (!btn) return;
        const panel = btn.closest("[data-combat-panel]");
        if (!panel) return;
        const roomId = panel.dataset.roomId;
        const action = btn.dataset.combatAction;
        btn.closest("details")?.removeAttribute("open");

        if (action === "token/focus") {
            if (btn.dataset.tokenId) window.GravewrightMap?.centerOnToken?.(btn.dataset.tokenId);
            return;
        }
        if (action === "token/sheet") {
            if (btn.dataset.tokenId) {
                document.dispatchEvent(new CustomEvent("vtt:open-token-sheet", {
                    detail: { tokenId: btn.dataset.tokenId },
                }));
            }
            return;
        }
        if (action === "combatants/add-selected") {
            const payload = selectionPayload(roomId);
            if (!payload.token_ids.length && !payload.actor_ids.length) return;
            perform(roomId, "combatants/add", payload);
            return;
        }

        const entry = ACTIONS[action];
        if (!entry) return;
        const [path, bodyFor] = entry;
        perform(roomId, path, bodyFor ? bodyFor(btn) : {});
    });



    function commitInitiative(input) {
        const panel = input.closest("[data-combat-panel]");
        if (!panel) return;
        const raw = input.value.trim();
        perform(panel.dataset.roomId, "initiative/set", {
            combatant_id: input.dataset.combatInitiative,
            value: raw === "" ? null : raw,
        });
    }

    document.addEventListener("change", (event) => {
        const input = event.target.closest("[data-combat-initiative]");
        if (input) commitInitiative(input);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        const input = event.target.closest("[data-combat-initiative]");
        if (!input) return;
        event.preventDefault();
        input.blur();
    });

    document.addEventListener("vtt:token-selection-changed", (event) => {
        const roomId = event.detail?.roomId || "";
        if (!roomId) return;
        selectedTokens.set(roomId, new Set(event.detail?.tokenIds || []));
        publish(roomId, lastState.get(roomId) || {});
    });

    document.addEventListener("vtt:combat-sdk-state", (event) => {
        const state = event.detail || {};
        const roomId = String(state.campaign_id || "");
        if (roomId) publish(roomId, state);
    });

    document.addEventListener("DOMContentLoaded", () => {
        const rooms = new Set();
        document.querySelectorAll("[data-combat-panel]").forEach((panel) => {
            if (panel.dataset.roomId) rooms.add(panel.dataset.roomId);
        });
        rooms.forEach(refreshRoom);
    });

    window.GravewrightCombatActions = { refreshRoom, receiveState: publish };
})();
