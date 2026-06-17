




(() => {
    const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});
    const panelFor = FI.panelFor;
    const closeDialog = FI.closeDialog;
    const postJson = FI.postJson;
    const refreshPanel = FI.refreshPanel;

    
    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-item-create-form]");
        if (!form) return;
        event.preventDefault();
        const roomId = form.dataset.roomId || "";
        const name = (form.querySelector("[data-item-create-name]")?.value || "").trim();
        const target = form.querySelector("[data-item-create-target]")?.value || "";
        const [systemId, type] = target.split("::");
        if (!name || !systemId || !type) return;
        const res = await postJson("/game/item", {
            campaign_id: roomId, system_id: systemId, type, name,
        });
        if (!res.ok) return;
        const data = await res.json().catch(() => ({}));
        form.querySelector("[data-item-create-name]").value = "";
        closeDialog(form);
        await refreshPanel(roomId);
        if (data.item_id) {
            document.dispatchEvent(new CustomEvent("vtt:open-item-sheet", { detail: { itemId: data.item_id } }));
        }
    });

    
    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-item-folder-create-form]");
        if (!form) return;
        event.preventDefault();
        const roomId = form.dataset.roomId || "";
        const name = (form.querySelector("input[name='name']")?.value || "").trim();
        if (!name) return;
        const color = form.querySelector("[data-item-folder-color-text]")?.value || "";
        const ok = await window.GravewrightItems.folderAction(
            "item-folder", { campaign_id: roomId, name, color }, roomId,
        );
        if (ok) {
            form.querySelector("input[name='name']").value = "";
            closeDialog(form);
        }
    });

    document.addEventListener("input", (event) => {
        const pick = event.target.closest("[data-item-folder-color-pick]");
        if (pick) {
            const text = pick.closest(".dialog-color-row")?.querySelector("[data-item-folder-color-text]");
            if (text) text.value = pick.value;
            return;
        }
        const text = event.target.closest("[data-item-folder-color-text]");
        if (text && /^#[0-9a-fA-F]{6}$/.test(text.value)) {
            const picker = text.closest(".dialog-color-row")?.querySelector("[data-item-folder-color-pick]");
            if (picker) picker.value = text.value;
        }
    });

    
    document.addEventListener("vtt:transport-event", (event) => {
        const env = event.detail || {};
        if (!["item.created", "item.deleted", "item.updated"].includes(env.event)) return;
        const roomId = env.payload?.room_id;
        if (roomId && panelFor(roomId)) refreshPanel(roomId);
    });

    document.addEventListener("vtt:resource-permissions-saved", (event) => {
        if (event.detail?.resourceType !== "item") return;
        document.querySelectorAll("[data-item-panel]").forEach((p) => {
            if (p.dataset.roomId) refreshPanel(p.dataset.roomId);
        });
    });
})();
