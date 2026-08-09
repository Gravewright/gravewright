(() => {


    const GENERIC_MESSAGES = {
        "http.errors.network": "Network error. Check your connection and try again.",
        "http.errors.forbidden": "You don't have permission to do that.",
        "http.errors.conflict": "That action conflicts with the current state.",
        "http.errors.rate_limited": "Too many requests. Please slow down and try again.",
        "http.errors.server": "Something went wrong on the server. Please try again shortly.",
        "http.errors.request": "The request could not be completed.",
    };

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

        return messages[key] || GENERIC_MESSAGES[key] || key || "";
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

    async function submitInvitationForm(form) {
        const http = window.GravewrightCore && window.GravewrightCore.http;
        if (!http) {
            showNotice("error", getMessageForKey("http.errors.request"));
            return;
        }





        const result = await http.postForm(form.action, new FormData(form), {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        if (!result.ok) {


            showNotice("error", getMessageForKey(result.errorKey));
            return;
        }

        const data = result.data || {};
        if (data.ok === false) {
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
            showNotice("error", getMessageForKey("http.errors.request"));
        });
    });
})();