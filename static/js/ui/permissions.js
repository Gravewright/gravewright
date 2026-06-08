(() => {
    function getBodyMessage(key) {
        const map = {
            "permissions.updated": document.body.dataset.permissionsUpdated,
            "permissions.errors.denied": document.body.dataset.permissionsErrorDenied,
            "auth.errors.session_expired": document.body.dataset.permissionsErrorSessionExpired,
            "inside.campaigns.errors.not_found": document.body.dataset.permissionsErrorNotFound,
        };

        return map[key] || key || "";
    }

    function getOrCreateNotice(form) {
        let notice = form.querySelector(".game-permissions-notice");

        if (!notice) {
            notice = document.createElement("div");
            notice.className = "game-notice game-permissions-notice";

            const body = form.querySelector(".game-modal-body");

            if (body) {
                body.prepend(notice);
            } else {
                form.prepend(notice);
            }
        }

        return notice;
    }

    function showNotice(form, kind, message) {
        const notice = getOrCreateNotice(form);

        notice.hidden = false;
        notice.textContent = message;
        notice.classList.toggle("game-notice--danger", kind === "error");
    }

    async function submitPermissionsForm(form) {
        const response = await fetch(form.action, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams(new FormData(form)),
            credentials: "same-origin",
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            showNotice(form, "error", getBodyMessage(data.error_key));
            return;
        }

        showNotice(form, "success", getBodyMessage(data.message_key));
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest(".game-modal-form");

        if (!form) {
            return;
        }

        event.preventDefault();

        submitPermissionsForm(form).catch(() => {
            showNotice(form, "error", getBodyMessage("auth.errors.session_expired"));
        });
    });
})();
