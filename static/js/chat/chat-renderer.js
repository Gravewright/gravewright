





(() => {
    const FI = (window.GravewrightChatInternals = window.GravewrightChatInternals || {});

    function deleteLabel() {
        return document.body.dataset.chatDeleteMessageLabel || "Delete message";
    }

    function getMessageList(roomId) {
        return document.getElementById(`chat-messages-${roomId}`);
    }

    function isAlreadyRendered(list, messageId) {
        return !!list.querySelector(`[data-message-id="${messageId}"]`);
    }

    function canDeleteMessage(payload, list) {
        if (!payload.message_id) {
            return false;
        }

        
        if (payload.visibility === "whisper") {
            return false;
        }

        if (list.dataset.canDeleteAny === "true") {
            return true;
        }

        return (
            list.dataset.canDeleteOwn === "true"
            && payload.author_id
            && payload.author_id === document.body.dataset.currentUserId
        );
    }

    function appendDeleteButton(el, payload, list) {
        if (!canDeleteMessage(payload, list)) {
            return;
        }

        const button = document.createElement("button");
        button.className = "chat-message-delete";
        button.type = "button";
        button.dataset.chatDelete = payload.message_id;
        button.setAttribute("aria-label", deleteLabel());
        button.title = deleteLabel();
        button.innerHTML = '<i class="ph ph-trash" aria-hidden="true"></i>';
        el.appendChild(button);
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function assetUrl(assetId) {
        return `/game/journal/asset/${encodeURIComponent(assetId)}`;
    }

    function cardName(card) {
        return card && typeof card === "object" ? String(card.name || "Card") : "Card";
    }

    function buildCardRevealHtml(payload) {
        const metadata = payload && typeof payload.metadata === "object" ? payload.metadata : {};
        if (metadata.type !== "cards.revealed" || !Array.isArray(metadata.cards) || !metadata.cards.length) {
            return "";
        }
        const cards = metadata.cards.map((card) => {
            const name = cardName(card);
            const image = card.front_asset_id
                ? `<img src="${assetUrl(card.front_asset_id)}" alt="${escapeHtml(name)}" loading="lazy">`
                : '<i class="ph ph-cardholder" aria-hidden="true"></i>';
            return `
                <article class="chat-card-preview">
                    <div class="chat-card-preview__image">${image}</div>
                    <strong>${escapeHtml(name)}</strong>
                </article>
            `;
        }).join("");
        return `<div class="chat-card-reveal">${cards}</div>`;
    }

    function whisperTargetLabel(payload) {
        const targets = Array.isArray(payload.target_names) ? payload.target_names : [];
        if (!targets.length) {
            return "";
        }
        const template = document.body.dataset.chatWhisperTo || "to {target}";
        const text = template.replace("{target}", targets.join(", "));
        return `<span class="chat-whisper-target">${escapeHtml(text)}</span>`;
    }

    function buildTextMessage(payload) {
        const el = document.createElement("div");
        el.className = "chat-message chat-message--text";
        if (payload.visibility === "gm_only") {
            el.classList.add("chat-message--gm");
        }
        let whisperHtml = "";
        if (payload.visibility === "whisper") {
            el.classList.add("chat-message--whisper");
            whisperHtml = whisperTargetLabel(payload);
        }
        el.dataset.messageId = payload.message_id || "";
        el.dataset.authorId = payload.author_id || "";
        el.innerHTML = `
            <div class="chat-message-content">
                <span class="chat-author">${escapeHtml(payload.author)}</span>
                ${whisperHtml}
                <span class="chat-content">${escapeHtml(payload.content)}</span>
            </div>
        `;
        return el;
    }

    function buildEmoteMessage(payload) {
        const el = document.createElement("div");
        el.className = "chat-message chat-message--emote";
        el.dataset.messageId = payload.message_id || "";
        el.dataset.authorId = payload.author_id || "";
        el.innerHTML = `
            <div class="chat-message-content">
                <span class="chat-emote-text">* ${escapeHtml(payload.author)} ${escapeHtml(payload.content)}</span>
            </div>
        `;
        return el;
    }

    function buildSystemMessage(payload) {
        const el = document.createElement("div");
        el.className = "chat-message chat-message--system";
        el.dataset.messageId = payload.message_id || "";
        el.dataset.authorId = payload.author_id || "";
        const cardRevealHtml = buildCardRevealHtml(payload);
        el.innerHTML = `
            <div class="chat-message-content">
                <span class="chat-content">${escapeHtml(payload.content || "")}</span>
                ${cardRevealHtml}
            </div>
        `;
        return el;
    }

    function renderMessage(payload, list) {
        if (payload.message_id && isAlreadyRendered(list, payload.message_id)) {
            return;
        }

        let el;
        switch (payload.kind) {
            case "emote":
                el = buildEmoteMessage(payload);
                break;
            case "roll":
                el = FI.buildRollMessage(payload);
                break;
            case "system":
                el = buildSystemMessage(payload);
                break;
            default:
                el = buildTextMessage(payload);
        }

        appendDeleteButton(el, payload, list);
        list.appendChild(el);

        const isNearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 80;
        if (isNearBottom) {
            list.scrollTop = list.scrollHeight;
        }
    }

    FI.escapeHtml = escapeHtml;
    FI.getMessageList = getMessageList;
    FI.renderMessage = renderMessage;
})();
