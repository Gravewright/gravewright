(() => {
    const MAX_TOASTS = 3;
    const ROLL_TTL_MS = 5000;
    let container = null;

    function getContainer() {
        if (!container) {
            container = document.createElement("div");
            container.className = "vtt-toast-container";
            document.body.appendChild(container);
        }
        return container;
    }

    function enforceMax() {
        if (!container) return;
        while (container.children.length > MAX_TOASTS) {
            const oldest = container.firstElementChild;
            if (!oldest) break;
            oldest.remove();
        }
    }

    function showToast(message, { duration = 4000, id = null, onClick = null } = {}) {
        const c = getContainer();

        if (id) {
            c.querySelector(`[data-toast-id="${CSS.escape(id)}"]`)?.remove();
        }

        const toast = document.createElement("div");
        toast.className = "vtt-toast";
        toast.textContent = message;
        if (id) toast.dataset.toastId = id;

        if (typeof onClick === "function") {
            toast.classList.add("vtt-toast--clickable");
            toast.addEventListener("click", () => onClick(toast));
        }

        c.appendChild(toast);
        enforceMax();
        toast.getBoundingClientRect(); 
        toast.classList.add("vtt-toast--visible");

        let timer = null;

        function dismiss() {
            clearTimeout(timer);
            if (!toast.isConnected) return;
            toast.classList.remove("vtt-toast--visible");
            toast.addEventListener("transitionend", () => toast.remove(), { once: true });
        }

        if (duration > 0) timer = setTimeout(dismiss, duration);

        return { dismiss };
    }

    function dismissToast(id) {
        if (!container) return;
        const toast = container.querySelector(`[data-toast-id="${CSS.escape(id)}"]`);
        if (!toast) return;
        toast.classList.remove("vtt-toast--visible");
        toast.addEventListener("transitionend", () => toast.remove(), { once: true });
    }

    function focusChatMessage(messageId) {
        if (!messageId) return;
        const targets = document.querySelectorAll(`[data-message-id="${CSS.escape(messageId)}"]`);
        if (!targets.length) return;
        const target = targets[targets.length - 1];

        const chatPanel = target.closest("[data-modal-window]");
        if (chatPanel && chatPanel.hidden) {
            const openBtn = document.querySelector(`[data-modal-open="${CSS.escape(chatPanel.dataset.modalId || "")}"]`);
            openBtn?.click();
        }

        target.scrollIntoView({ behavior: "smooth", block: "center" });
        target.classList.remove("chat-message--toast-highlight");
        void target.offsetWidth;
        target.classList.add("chat-message--toast-highlight");
    }

    document.addEventListener("vtt:show-toast", (e) => {
        const { message, duration, id } = e.detail ?? {};
        if (message) showToast(message, { duration, id });
    });

    document.addEventListener("vtt:dismiss-toast", (e) => {
        const { id } = e.detail ?? {};
        if (id) dismissToast(id);
    });

    document.addEventListener("vtt:transport-event", (e) => {
        const { event: evtName, payload } = e.detail ?? {};
        if (evtName !== "chat.message.created") return;

        
        
        if (payload?.kind === "system") {
            const content = payload.content || "";
            if (content) {
                showToast(content, {
                    duration: ROLL_TTL_MS,
                    id: payload.message_id ? `sys-${payload.message_id}` : null,
                });
            }
            return;
        }

        if (payload?.kind !== "roll") return;

        const author = payload.author || "?";
        const expr = payload.expression || "?";
        const total = payload.total ?? "?";
        const messageId = payload.message_id || null;
        const metadata = payload.metadata && typeof payload.metadata === "object" ? payload.metadata : {};
        const rendered = metadata.rendered && typeof metadata.rendered === "object" ? metadata.rendered : {};
        const rollToast = rendered.rollToast && typeof rendered.rollToast === "object" ? rendered.rollToast : null;

        let text;
        if (rollToast) {
            const title = rollToast.title || author;
            const subtitle = rollToast.subtitle ? ` — ${rollToast.subtitle}` : "";
            const value = rollToast.total ?? total;
            text = `${title}${subtitle}: ${value}`;
        } else {
            const template = document.body.dataset.toastRollResult || "{author}: {expr} = {total}";
            text = template
                .replace("{author}", author)
                .replace("{expr}", expr)
                .replace("{total}", total);
        }

        showToast(text, {
            duration: ROLL_TTL_MS,
            id: messageId ? `roll-${messageId}` : null,
            onClick: messageId ? () => focusChatMessage(messageId) : null,
        });
    });

    window.GravewrightToasts = { showToast, dismissToast };
})();
