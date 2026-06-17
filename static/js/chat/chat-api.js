



(() => {
    const FI = (window.GravewrightChatInternals = window.GravewrightChatInternals || {});

    function getErrorLabel(key) {
        const dataMap = {
            "auth.errors.session_expired": "chatErrorSessionExpired",
            "game.chat.errors.empty_message": "chatErrorEmptyMessage",
            "game.chat.errors.message_too_long": "chatErrorMessageTooLong",
            "game.chat.errors.invalid_roll": "chatErrorInvalidRoll",
            "game.chat.errors.not_a_member": "chatErrorNotAMember",
            "game.chat.errors.not_found": "chatErrorNotFound",
            "game.chat.errors.invalid_whisper_target": "chatErrorInvalidWhisperTarget",
            "permissions.errors.denied": "chatErrorDenied",
        };
        const prop = dataMap[key];
        return prop ? (document.body.dataset[prop] || key) : key;
    }

    function showChatError(form, message) {
        let notice = form.querySelector(".chat-error-notice");
        if (!notice) {
            notice = document.createElement("div");
            notice.className = "chat-error-notice game-notice game-notice--danger";
            notice.setAttribute("role", "alert");
            form.insertBefore(notice, form.firstChild);
        }
        notice.textContent = message;
        notice.hidden = false;
        window.setTimeout(() => {
            notice.hidden = true;
        }, 4000);
    }

    async function postChatAction(form, path, params) {
        const csrf = window.csrfToken();
        const body = new URLSearchParams({
            csrf_token: csrf,
            ...params,
        });

        const res = await fetch(path, {
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

        return res.ok;
    }

    FI.getErrorLabel = getErrorLabel;
    FI.showChatError = showChatError;
    FI.postChatAction = postChatAction;
})();
