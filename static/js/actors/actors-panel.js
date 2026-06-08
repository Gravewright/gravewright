



(() => {
    const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});
    const panelFor = FI.panelFor;
    const closeDialog = FI.closeDialog;
    const postJson = FI.postJson;
    const refreshPanel = FI.refreshPanel;

    
    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-actor-create-form]");
        if (!form) return;
        event.preventDefault();
        const roomId = form.dataset.roomId || "";
        const name = (form.querySelector("[data-actor-create-name]")?.value || "").trim();
        const target = form.querySelector("[data-actor-create-target]")?.value || "";
        const [systemId, type] = target.split("::");
        if (!name || !systemId || !type) return;
        const res = await postJson("/game/actor", {
            campaign_id: roomId, system_id: systemId, type, name,
        });
        if (!res.ok) return;
        const data = await res.json().catch(() => ({}));
        form.querySelector("[data-actor-create-name]").value = "";
        closeDialog(form);
        await refreshPanel(roomId);
        if (data.actor_id) {
            document.dispatchEvent(new CustomEvent("vtt:open-actor-sheet", { detail: { actorId: data.actor_id } }));
        }
    });

    
    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-actor-folder-create-form]");
        if (!form) return;
        event.preventDefault();
        const roomId = form.dataset.roomId || "";
        const name = (form.querySelector("input[name='name']")?.value || "").trim();
        if (!name) return;
        const color = form.querySelector("[data-actor-folder-color-text]")?.value || "";
        const ok = await window.GravewrightActors.folderAction(
            "actor-folder", { campaign_id: roomId, name, color }, roomId,
        );
        if (ok) {
            form.querySelector("input[name='name']").value = "";
            closeDialog(form);
        }
    });

    
    document.addEventListener("input", (event) => {
        const pick = event.target.closest("[data-actor-folder-color-pick]");
        if (pick) {
            const text = pick.closest(".dialog-color-row")?.querySelector("[data-actor-folder-color-text]");
            if (text) text.value = pick.value;
            return;
        }
        const text = event.target.closest("[data-actor-folder-color-text]");
        if (text && /^#[0-9a-fA-F]{6}$/.test(text.value)) {
            const picker = text.closest(".dialog-color-row")?.querySelector("[data-actor-folder-color-pick]");
            if (picker) picker.value = text.value;
        }
    });

    
    document.addEventListener("vtt:transport-event", (event) => {
        const env = event.detail || {};
        if (!["actor.created", "actor.deleted", "actor.updated"].includes(env.event)) return;
        const roomId = env.payload?.room_id;
        if (roomId && panelFor(roomId)) refreshPanel(roomId);
    });

    document.addEventListener("vtt:resource-permissions-saved", (event) => {
        if (event.detail?.resourceType !== "actor") return;
        
        document.querySelectorAll("[data-actor-panel]").forEach((p) => {
            if (p.dataset.roomId) refreshPanel(p.dataset.roomId);
        });
    });
})();
