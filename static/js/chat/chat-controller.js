




(() => {
    const FI = (window.GravewrightChatInternals = window.GravewrightChatInternals || {});
    const getMessageList = FI.getMessageList;
    const renderMessage = FI.renderMessage;
    const getErrorLabel = FI.getErrorLabel;
    const showChatError = FI.showChatError;
    const postChatAction = FI.postChatAction;

    const CHAT_EVENT = "chat.message.created";
    const CHAT_DELETE_EVENT = "chat.message.deleted";
    const CHAT_CLEAR_EVENT = "chat.messages.cleared";

    function clearConfirmLabel() {
        return document.body.dataset.chatDeleteAllConfirm || "Delete all messages in this chat?";
    }

    function getFormRoomId(form) {
        if (form.dataset.roomId) {
            return form.dataset.roomId;
        }

        const panel = form.closest("[data-panel-room]");
        return panel ? panel.dataset.panelRoom : null;
    }

    function handleChatEvent(payload) {
        if (!payload || !payload.room_id) return;
        const list = getMessageList(payload.room_id);
        if (!list) return;
        renderMessage(payload, list);
    }

    function handleChatDeleteEvent(payload) {
        if (!payload || !payload.message_id) return;
        document.querySelectorAll(`[data-message-id="${payload.message_id}"]`).forEach((el) => {
            el.remove();
        });
    }

    function handleChatClearEvent(payload) {
        if (!payload || !payload.room_id) return;
        const list = getMessageList(payload.room_id);
        if (!list) return;
        list.replaceChildren();
    }

    document.addEventListener("vtt:transport-event", (e) => {
        if (e.detail.event === CHAT_EVENT) {
            handleChatEvent(e.detail.payload);
        }

        if (e.detail.event === CHAT_DELETE_EVENT) {
            handleChatDeleteEvent(e.detail.payload);
        }

        if (e.detail.event === CHAT_CLEAR_EVENT) {
            handleChatClearEvent(e.detail.payload);
        }
    });

    document.addEventListener("submit", async (e) => {
        const form = e.target.closest("[data-chat-form]");
        if (!form) return;
        e.preventDefault();

        const roomId = getFormRoomId(form);
        if (!roomId) return;

        const input = form.querySelector('[name="message"]');
        const msg = input.value.trim();
        if (!msg) return;

        const csrf = window.csrfToken();
        const body = new URLSearchParams({
            csrf_token: csrf,
            campaign_id: roomId,
            message: msg,
        });

        input.value = "";

        try {
            const res = await fetch("/game/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    Accept: "application/json",
                },
                body,
                credentials: "same-origin",
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                showChatError(form, getErrorLabel(data.error_key || ""));
            }
        } catch { }
    });

    document.addEventListener("keydown", (e) => {
        const input = e.target.closest("[data-chat-form] textarea[name='message']");
        if (!input || e.key !== "Enter" || e.shiftKey || e.isComposing) return;

        e.preventDefault();
        input.closest("[data-chat-form]").requestSubmit();
    });

    document.addEventListener("click", async (e) => {
        const deleteButton = e.target.closest("[data-chat-delete]");

        if (deleteButton) {
            const message = deleteButton.closest("[data-message-id]");
            const list = deleteButton.closest(".chat-messages");
            const form = list?.closest(".game-panel-body--chat")?.querySelector("[data-chat-form]");

            if (!message || !list || !form) return;

            try {
                await postChatAction(form, "/game/chat/delete", {
                    campaign_id: list.dataset.roomId,
                    message_id: deleteButton.dataset.chatDelete,
                });
            } catch { }
            return;
        }

        const clearButton = e.target.closest("[data-chat-clear]");
        if (!clearButton) return;

        const form = clearButton.closest("[data-chat-form]");
        if (!form) return;

        const roomId = getFormRoomId(form);
        if (!roomId || !window.confirm(clearConfirmLabel())) return;

        try {
            await postChatAction(form, "/game/chat/clear", {
                campaign_id: roomId,
            });
        } catch { }
    });

    
    document.querySelectorAll(".chat-messages").forEach((list) => {
        list.scrollTop = list.scrollHeight;
    });
})();
