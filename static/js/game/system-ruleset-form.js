(() => {








    const csrf = () => (typeof window.csrfToken === "function" ? window.csrfToken() : "");

    function message(key, fallback) {
        return document.body?.dataset?.[key] || fallback;
    }

    function showError(form, text) {
        const panel = form.closest(".game-modal-body") || form.parentElement;
        if (!panel) return;
        let notice = panel.querySelector("[data-system-notice]");
        if (!notice) {
            notice = document.createElement("div");
            notice.className = "game-notice game-notice--danger";
            notice.setAttribute("role", "alert");
            notice.dataset.systemNotice = "";
            form.before(notice);
        }
        notice.textContent = text;
    }

    async function submit(form) {
        const submitter = form.querySelector('button[type="submit"]');
        if (submitter) submitter.disabled = true;
        try {
            const response = await fetch(form.action, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "x-csrftoken": csrf(),
                },
                body: new URLSearchParams(new FormData(form)),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || !data.ok) {
                showError(form, message("systemRulesetError", "Não foi possível trocar o sistema."));
                return;
            }


            if (window.GravewrightUiState?.reload) {
                window.GravewrightUiState.reload("system-ruleset-changed");
            } else {
                window.location.reload();
            }
        } catch {
            showError(form, message("systemRulesetError", "Não foi possível trocar o sistema."));
        } finally {
            if (submitter) submitter.disabled = false;
        }
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest(".system-inline-form");
        if (!form) return;
        event.preventDefault();
        void submit(form);
    });
})();
