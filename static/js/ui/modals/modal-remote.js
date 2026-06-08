(() => {
    function createModalRemote(deps) {
        const { cssEscape } = deps;

        function layer() {
            return document.querySelector(".game-modal-layer");
        }

        function appendModalFromHtml(html, mountedEvent = null) {
            const targetLayer = layer();
            if (!targetLayer) return null;

            const template = document.createElement("template");
            template.innerHTML = html.trim();
            const modal = template.content.querySelector("[data-modal-window]");
            if (!modal) return null;

            targetLayer.appendChild(modal);
            if (mountedEvent) {
                document.dispatchEvent(new CustomEvent(mountedEvent, { detail: { modal } }));
            }
            return modal;
        }

        async function fetchModal(url, mountedEvent = null) {
            const response = await fetch(url, {
                credentials: "same-origin",
                headers: { Accept: "text/html" },
            });
            if (!response.ok) return false;
            return Boolean(appendModalFromHtml(await response.text(), mountedEvent));
        }

        async function ensureJournalModal(journalId) {
            const modalId = `journal-${journalId}`;
            if (document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)) return true;
            return fetchModal(
                `/game/journal/modal/${encodeURIComponent(journalId)}`,
                "vtt:journal-modal-mounted",
            );
        }

        async function ensureJournalCreateModal(campaignId, folderId) {
            const modalId = `journal-create-${campaignId}`;
            document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)?.remove();

            const url = new URL(`/game/journal/modal/new/${encodeURIComponent(campaignId)}`, window.location.origin);
            if (folderId) url.searchParams.set("folder_id", folderId);
            return fetchModal(url.toString(), "vtt:journal-modal-mounted");
        }

        async function ensureResourcePermissionsModal(resourceType, resourceId) {
            const modalId = `resource-permissions-${resourceType}-${resourceId}`;
            document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)?.remove();
            return fetchModal(
                `/game/resource-permissions/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceId)}`,
            );
        }

        async function ensureActorSheetModal(actorId) {
            const modalId = `actor-${actorId}`;
            document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)?.remove();
            return fetchModal(
                `/game/actor/sheet/modal/${encodeURIComponent(actorId)}`,
                "vtt:actor-sheet-modal-mounted",
            );
        }

        async function ensureTokenSheetModal(tokenId) {
            const modalId = `token-${tokenId}`;
            document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)?.remove();
            return fetchModal(
                `/game/token/sheet/modal/${encodeURIComponent(tokenId)}`,
                "vtt:actor-sheet-modal-mounted",
            );
        }

        async function ensureItemSheetModal(itemId) {
            const modalId = `item-${itemId}`;
            document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)?.remove();
            return fetchModal(
                `/game/item/sheet/modal/${encodeURIComponent(itemId)}`,
                "vtt:item-sheet-modal-mounted",
            );
        }

        async function ensureSceneEditModal(sceneId) {
            const modalId = `scene-edit-${sceneId}`;
            document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)?.remove();
            return fetchModal(`/game/scenes/${encodeURIComponent(sceneId)}/edit-modal`);
        }

        return {
            ensureActorSheetModal,
            ensureItemSheetModal,
            ensureJournalCreateModal,
            ensureJournalModal,
            ensureResourcePermissionsModal,
            ensureSceneEditModal,
            ensureTokenSheetModal,
        };
    }

    window.GravewrightModalRemote = { createModalRemote };
})();
