



(() => {
    const FI = (window.GravewrightChatInternals = window.GravewrightChatInternals || {});
    const escapeHtml = FI.escapeHtml;

    function renderedRollCard(payload) {
        const metadata = payload && typeof payload.metadata === "object" ? payload.metadata : {};
        const rendered = metadata && typeof metadata.rendered === "object" ? metadata.rendered : {};
        const card = rendered && typeof rendered.chatCard === "object" ? rendered.chatCard : null;
        return card;
    }

    function buildRollMessage(payload) {
        const el = document.createElement("div");
        el.className = "chat-message chat-message--roll";
        el.dataset.messageId = payload.message_id || "";
        el.dataset.authorId = payload.author_id || "";

        let secretHtml = "";
        if (payload.secret) {
            el.classList.add("chat-message--secret");
            const label = document.body.dataset.chatSecretRoll || "Secret roll";
            secretHtml = `<span class="chat-secret-badge"><i class="ph ph-eye-slash" aria-hidden="true"></i>${escapeHtml(label)}</span>`;
        }

        const card = renderedRollCard(payload);
        if (card) {
            const lines = Array.isArray(card.lines) ? card.lines : [];
            const lineHtml = lines.map((line) => {
                const label = line && line.label != null ? String(line.label) : "";
                const value = line && line.value != null ? String(line.value) : "";
                if (!value) return "";
                return `<div class="roll-card-line"><span class="roll-card-line__label">${escapeHtml(label)}</span><span class="roll-card-line__value">${escapeHtml(value)}</span></div>`;
            }).join("");
            const title = card.title || payload.content || payload.author || "Roll";
            const subtitle = card.subtitle || "";
            const total = card.total ?? payload.total ?? "";
            el.innerHTML = `
                <div class="chat-message-content roll-card">
                    <span class="chat-author">${escapeHtml(payload.author)}</span>
                    ${secretHtml}
                    <div class="roll-card__header">
                        <div>
                            <span class="roll-card__title">${escapeHtml(title)}</span>
                            ${subtitle ? `<span class="roll-card__subtitle">${escapeHtml(subtitle)}</span>` : ""}
                        </div>
                        <span class="roll-total roll-card__total">${escapeHtml(total)}</span>
                    </div>
                    ${lineHtml ? `<div class="roll-card__lines">${lineHtml}</div>` : ""}
                </div>
            `;
            return el;
        }

        const groups = Array.isArray(payload.groups) ? payload.groups : [];
        const groupParts = groups.map((g) => {
            const dice = Array.isArray(g.results) ? g.results.join(", ") : "";
            return `<span class="roll-group">${escapeHtml(g.notation)}: [${escapeHtml(dice)}]</span>`;
        });

        const modifierHtml =
            payload.modifier && payload.modifier !== 0
                ? `<span class="roll-modifier">${payload.modifier > 0 ? "+" : ""}${payload.modifier}</span>`
                : "";

        el.innerHTML = `
            <div class="chat-message-content">
                <span class="chat-author">${escapeHtml(payload.author)}</span>
                ${secretHtml}
                <span class="roll-expression">${escapeHtml(payload.expression)}</span>
                <div class="roll-breakdown">${groupParts.join("")}${modifierHtml}</div>
                <span class="roll-total">${payload.total}</span>
            </div>
        `;
        return el;
    }

    FI.buildRollMessage = buildRollMessage;
})();
