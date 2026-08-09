(() => {
    const activeRoomId = () => document.querySelector('input[name="selected-room"]:checked')?.value || "";
    const dialogFor = (campaignId) => document.querySelector(
        `[data-onboarding-dialog][data-campaign-id="${CSS.escape(campaignId)}"]`
    );

    function csrf() {
        return typeof window.csrfToken === "function" ? window.csrfToken() : "";
    }

    async function savePreference(dialog, dismissed) {
        const response = await fetch("/game/onboarding/preference", {
            method: "POST",
            credentials: "same-origin",
            headers: { Accept: "application/json", "Content-Type": "application/json", "x-csrftoken": csrf() },
            body: JSON.stringify({ campaign_id: dialog.dataset.campaignId, dismissed }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error_key || "onboarding.errors.generic");
        dialog.dataset.dismissed = String(Boolean(data.state?.dismissed));
    }

    async function refresh(dialog) {
        const response = await fetch(`/game/onboarding?campaign_id=${encodeURIComponent(dialog.dataset.campaignId)}`, {
            credentials: "same-origin", headers: { Accept: "application/json" },
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.state) return;
        dialog.dataset.dismissed = String(Boolean(data.state.dismissed));
        dialog.dataset.finished = String(Boolean(data.state.finished));
        dialog.querySelector("progress").value = data.state.completed;
        dialog.querySelector("[data-onboarding-progress]").textContent = dialog.dataset.progressTemplate
            .replace("{completed}", data.state.completed).replace("{total}", data.state.total);
        Object.entries(data.state.steps).forEach(([key, complete]) => {
            const row = dialog.querySelector(`[data-onboarding-step="${CSS.escape(key)}"]`);
            if (!row || !complete) return;
            row.classList.add("is-complete");
            row.dataset.complete = "true";
            const icon = row.querySelector("i");
            icon.className = "ph ph-check-circle";
            row.querySelector("[data-onboarding-action]")?.remove();
        });
    }

    function open(dialog, explicit = false) {
        if (!dialog || (!explicit && (dialog.dataset.dismissed === "true" || dialog.dataset.finished === "true"))) return;
        if (!dialog.open) dialog.showModal();
    }

    function openDestination(dialog, action) {
        const roomId = dialog.dataset.campaignId;
        dialog.close();
        if (action === "character") window.GravewrightModals?.open?.(`actor-create-${roomId}`);
        if (action === "scene") window.GravewrightModals?.open?.(`scene-manager-${roomId}`);
        if (action === "code") window.GravewrightModals?.open?.(`join-code-${roomId}`);
        if (action === "system") {
            window.GravewrightModals?.open?.(`panel-settings-${roomId}`);
            window.setTimeout(() => document.querySelector(
                `[data-modal-id="panel-settings-${CSS.escape(roomId)}"] .system-select`
            )?.focus(), 50);
        }
    }

    document.addEventListener("vtt:game-ready", async () => {
        const dialog = dialogFor(activeRoomId());
        if (dialog) await refresh(dialog);
        open(dialog);
    }, { once: true });
    document.addEventListener("click", async (event) => {
        const opener = event.target.closest("[data-onboarding-open]");
        if (opener) {
            const dialog = dialogFor(opener.dataset.campaignId || "");
            if (dialog) await refresh(dialog);
            open(dialog, true);
            return;
        }
        const close = event.target.closest("[data-onboarding-close]");
        if (close) { close.closest("[data-onboarding-dialog]")?.close(); return; }
        const action = event.target.closest("[data-onboarding-action]");
        if (action) { openDestination(action.closest("[data-onboarding-dialog]"), action.dataset.onboardingAction); return; }
        const dismiss = event.target.closest("[data-onboarding-dismiss]");
        if (!dismiss) return;
        const dialog = dismiss.closest("[data-onboarding-dialog]");
        dismiss.disabled = true;
        try { await savePreference(dialog, true); dialog.close(); }
        catch { const notice = dialog.querySelector("[data-onboarding-notice]"); notice.textContent = document.body.dataset.onboardingError || "Erro ao salvar."; notice.hidden = false; }
        finally { dismiss.disabled = false; }
    });
})();
