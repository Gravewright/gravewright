(() => {
    function activeSectionId() {
        return document.querySelector(".nav-control:checked")?.id || "section-campaigns";
    }

    function restoreSection(id) {
        const input = document.getElementById(id || "section-campaigns");
        if (input && input.matches(".nav-control")) input.checked = true;
    }

    function replaceInsideFromHtml(html, sectionId = activeSectionId()) {
        const doc = new DOMParser().parseFromString(html, "text/html");
        const next = doc.querySelector(".inside-content");
        const current = document.querySelector(".inside-content");
        if (!next || !current) return false;
        current.replaceWith(next);
        restoreSection(sectionId);
        window.history.replaceState({}, "", "/inside");
        return true;
    }

    async function fetchInside(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            cache: "no-store",
            ...options,
            headers: {
                Accept: "text/html",
                "X-Requested-With": "XMLHttpRequest",
                ...(options.headers || {}),
            },
        });
        const html = await response.text();
        replaceInsideFromHtml(html);
    }

    function formBody(form) {
        if ((form.enctype || "").toLowerCase() === "multipart/form-data") {
            return { body: new FormData(form), headers: {} };
        }
        return {
            body: new URLSearchParams(new FormData(form)),
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
        };
    }

    function shouldHandleForm(form) {
        if (!form || form.method.toLowerCase() !== "post") return false;
        if (form.matches(".invitation-accept-form, .invitation-decline-form")) return false;
        if (form.action.endsWith("/logout")) return false;
        return true;
    }

    async function submitForm(form) {
        const { body, headers } = formBody(form);
        form.setAttribute("aria-busy", "true");
        try {
            await fetchInside(form.action, {
                method: "POST",
                headers,
                body,
            });
        } finally {
            form.removeAttribute("aria-busy");
        }
    }

    function openModal(id) {
        const modal = document.querySelector(`[data-inside-modal="${CSS.escape(id || "")}"]`);
        if (!modal) return;
        modal.hidden = false;
        modal.querySelector("[data-inside-modal-close]")?.focus();
    }

    function closeModal(target) {
        const modal = target.closest("[data-inside-modal]");
        if (modal) modal.hidden = true;
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest("form");
        if (!shouldHandleForm(form)) return;
        if (event.defaultPrevented) return;
        event.preventDefault();
        submitForm(form).catch(() => {
            form.removeAttribute("aria-busy");
        });
    });

    document.addEventListener("click", (event) => {
        const open = event.target.closest("[data-inside-modal-open]");
        if (open) {
            event.preventDefault();
            openModal(open.dataset.insideModalOpen);
            return;
        }

        const close = event.target.closest("[data-inside-modal-close]");
        if (close) {
            event.preventDefault();
            closeModal(close);
            return;
        }

        const insideLink = event.target.closest('a[href="/inside"]');
        if (insideLink && insideLink.closest(".modal-backdrop")) {
            event.preventDefault();
            fetchInside("/inside").catch(() => {});
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        document.querySelectorAll("[data-inside-modal]:not([hidden])").forEach((modal) => {
            modal.hidden = true;
        });
    });
})();
