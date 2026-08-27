



(() => {
    const FI = (window.GravewrightChatInternals = window.GravewrightChatInternals || {});
    const escapeHtml = FI.escapeHtml;
    const rollActions = new Map();

    function matchesAction(entry, payload) {
        const metadata = payload?.metadata || {};
        if (String(metadata.systemId || "") !== entry.systemId) return false;
        if (entry.intents.length && !entry.intents.includes(String(metadata.intent || ""))) return false;
        if (entry.actionIds.length && !entry.actionIds.includes(String(metadata.actionId || ""))) return false;
        if (entry.excludeActionIds.includes(String(metadata.actionId || ""))) return false;
        return true;
    }

    function decorateRollActions(element, payload) {
        if (!element || !payload) return;
        element._gwRollPayload = payload;
        element.querySelector("[data-roll-actions]")?.remove();
        const matched = [...rollActions.values()].filter((entry) => matchesAction(entry, payload));
        if (!matched.length) return;
        const host = document.createElement("div");
        host.className = "roll-card__actions";
        host.dataset.rollActions = "";
        matched.forEach((entry) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "roll-card__action";
            button.textContent = entry.label;
            button.dataset.rollAction = entry.id;
            button.addEventListener("click", () => entry.handler(Object.freeze(structuredClone(payload))));
            host.appendChild(button);
        });
        element.querySelector(".chat-message-content")?.appendChild(host);
    }

    function registerRollAction(systemId, definition, handler) {
        const id = String(definition?.id || "").trim();
        const label = String(definition?.label || "").trim();
        if (!systemId || !id || !label || typeof handler !== "function") return false;
        const key = `${systemId}:${id}`;
        rollActions.set(key, Object.freeze({
            id, label, systemId,
            intents: Object.freeze((definition.intents || []).map(String)),
            actionIds: Object.freeze((definition.actionIds || []).map(String)),
            excludeActionIds: Object.freeze((definition.excludeActionIds || []).map(String)),
            handler,
        }));
        document.querySelectorAll(".chat-message--roll[data-message-id]").forEach((element) => {
            if (element._gwRollPayload) decorateRollActions(element, element._gwRollPayload);
        });
        return true;
    }

    window.GravewrightRollActions = Object.freeze({ register: registerRollAction });




    function breakdownLabel() {
        return document.body.dataset.chatRollBreakdown || "Detalhes";
    }

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
                const key = line && line.labelKey ? ` data-package-i18n="${escapeHtml(String(line.labelKey))}"` : "";
                return `<div class="roll-card-line"><span class="roll-card-line__label"${key}>${escapeHtml(label)}</span><span class="roll-card-line__value">${escapeHtml(value)}</span></div>`;
            }).join("");
            const title = card.title || payload.content || payload.author || "Roll";
            const subtitle = card.subtitle || "";
            const total = card.total ?? payload.total ?? "";




            const groups = Array.isArray(card.groups) ? card.groups : [];
            const modifier = Number(card.modifier) || 0;
            const toneClass = card.tone ? ` roll-card--${escapeHtml(String(card.tone))}` : "";
            const status = card.status || "";


            const systemAttr = card.system
                ? ` data-system="${escapeHtml(String(card.system))}"`
                : "";
            const titleI18n = card.titleTemplateKey
                ? ` data-package-i18n-template="${escapeHtml(String(card.titleTemplateKey))}" data-package-i18n-args="${escapeHtml(JSON.stringify(card.titleTemplateArgs || {}))}"`
                : card.titleKey
                    ? ` data-package-i18n="${escapeHtml(String(card.titleKey))}"`
                    : "";
            el.innerHTML = `
                <div class="chat-message-content roll-card${toneClass}"${systemAttr}>
                    <span class="chat-author">${escapeHtml(payload.author)}</span>
                    ${secretHtml}
                    <div class="roll-card__header">
                        <div>
                            <span class="roll-card__title"${titleI18n}>${escapeHtml(title)}</span>
                            ${subtitle && subtitle !== payload.author ? `<span class="roll-card__subtitle">${escapeHtml(subtitle)}</span>` : ""}
                        </div>
                        <span class="roll-total roll-card__total">${escapeHtml(total)}</span>
                    </div>
                    ${status ? `<div class="roll-card__status"${card.statusKey ? ` data-package-i18n="${escapeHtml(String(card.statusKey))}"` : ""}>${escapeHtml(status)}</div>` : ""}
                    ${lineHtml ? `<div class="roll-card__lines">${lineHtml}</div>` : ""}
                    ${groups.length ? `
                        <details class="roll-box roll-card__dice">
                            <summary class="roll-summary roll-summary--quiet">
                                <span class="roll-card__detail-label">${escapeHtml(breakdownLabel())}</span>
                            </summary>
                            <div class="roll-parts">${partsHtml(groups, modifier)}</div>
                            ${payload.expression ? `<div class="roll-card__formula">${escapeHtml(payload.expression)}</div>` : ""}
                        </details>` : ""}
                </div>
            `;
            queueMicrotask(() => decorateRollActions(el, payload));
            return el;
        }

        el.innerHTML = rollBreakdown(payload, secretHtml);
        queueMicrotask(() => decorateRollActions(el, payload));
        return el;
    }




    function diceHtml(group) {
        const sides = Number(group.sides) || 0;
        const kept = Array.isArray(group.results) ? group.results : [];
        const dropped = Array.isArray(group.dropped) ? group.dropped : [];

        const pill = (value, descartado) => {
            const classes = ["roll-die"];
            if (descartado) classes.push("is-dropped");
            else if (sides && value === sides) classes.push("is-max");
            else if (sides && value === 1) classes.push("is-min");
            return `<li class="${classes.join(" ")}">${escapeHtml(String(value))}</li>`;
        };

        return (
            kept.map((v) => pill(v, false)).join("")
            + dropped.map((v) => pill(v, true)).join("")
        );
    }

    function partsHtml(groups, modificador) {
        const partes = groups.map((group) => `
            <div class="roll-part">
                <span class="roll-part__formula">${escapeHtml(group.notation || "")}</span>
                <ol class="roll-dice">${diceHtml(group)}</ol>
                <span class="roll-part__subtotal">${escapeHtml(String(group.subtotal ?? ""))}</span>
            </div>`).join("");

        const modHtml = modificador
            ? `<div class="roll-part roll-part--modifier">
                 <span class="roll-part__formula">${modificador > 0 ? "+" : "−"}</span>
                 <span class="roll-part__subtotal">${Math.abs(modificador)}</span>
               </div>`
            : "";

        return partes + modHtml;
    }

    function rollBreakdown(payload, secretHtml) {
        const groups = Array.isArray(payload.groups) ? payload.groups : [];
        const modificador = Number(payload.modifier) || 0;


        // Nome que a pessoa deu à rolagem na bandeja: vira o rótulo da mensagem
        // e a fórmula desce para subtítulo, que é o que se lê na mesa.
        const rotulo = String(payload.content || "").trim();

        return `
            <div class="chat-message-content roll">
                <span class="chat-author">${escapeHtml(payload.author)}</span>
                ${secretHtml}
                ${rotulo ? `<span class="roll-label">${escapeHtml(rotulo)}</span>` : ""}
                <details class="roll-box">
                    <summary class="roll-summary">
                        <span class="roll-formula">${escapeHtml(payload.expression || "")}</span>
                        <span class="roll-total">${escapeHtml(String(payload.total ?? ""))}</span>
                    </summary>
                    <div class="roll-parts">${partsHtml(groups, modificador)}</div>
                </details>
            </div>
        `;
    }





    function hydrateHistory(root = document) {
        root.querySelectorAll("[data-roll-payload]").forEach((placeholder) => {
            let payload;
            try {
                payload = JSON.parse(placeholder.dataset.rollPayload);
            } catch {
                return;
            }
            const rebuilt = buildRollMessage(payload);
            rebuilt._gwRollPayload = payload;


            placeholder.querySelectorAll("[data-chat-delete]").forEach((btn) => rebuilt.appendChild(btn));
            placeholder.replaceWith(rebuilt);
            decorateRollActions(rebuilt, payload);
        });
    }

    document.addEventListener("DOMContentLoaded", () => hydrateHistory());

    FI.buildRollMessage = buildRollMessage;
    FI.hydrateRollHistory = hydrateHistory;
})();
