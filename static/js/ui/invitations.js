(() => {
    function getMessageForKey(key) {
        const messages = {
            "game.invite.success": document.body.dataset.inviteSuccess,
            "auth.errors.session_expired": document.body.dataset.inviteErrorSessionExpired,
            "game.invite.errors.invalid_email": document.body.dataset.inviteErrorInvalidEmail,
            "game.invite.errors.invalid_role": document.body.dataset.inviteErrorInvalidRole,
            "game.invite.errors.gm_required": document.body.dataset.inviteErrorGmRequired,
            "game.invite.errors.user_not_found": document.body.dataset.inviteErrorUserNotFound,
            "game.invite.errors.already_member": document.body.dataset.inviteErrorAlreadyMember,
            "game.invite.errors.already_pending": document.body.dataset.inviteErrorAlreadyPending,
        };

        return messages[key] || key || "";
    }

    function showNotice(kind, message) {
        const notice = document.querySelector("#game-invite-notice");

        if (!notice) {
            return;
        }

        notice.hidden = false;
        notice.textContent = message;
        notice.classList.toggle("game-notice--danger", kind === "error");
    }

    function asUrlEncodedBody(form) {
        return new URLSearchParams(new FormData(form));
    }

    async function submitInvitationForm(form) {
        const response = await fetch(form.action, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: asUrlEncodedBody(form),
            credentials: "same-origin",
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            showNotice("error", getMessageForKey(data.error_key));
            return;
        }

        form.reset();
        showNotice("success", getMessageForKey(data.message_key));
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest(".invite-form");

        if (!form) {
            return;
        }

        event.preventDefault();

        submitInvitationForm(form).catch(() => {
            showNotice("error", getMessageForKey("game.invite.errors.invalid_email"));
        });
    });
})();