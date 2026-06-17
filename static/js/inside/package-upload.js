// Inside package upload: submit the ZIP without losing the chosen file so an
// id conflict can prompt "replace?" and re-send the same file with replace=on.
(() => {
    async function send(form, replace) {
        const body = new FormData(form);
        if (replace) {
            body.set("replace", "true");
        } else {
            body.delete("replace");
        }
        const response = await fetch(form.action, {
            method: "POST",
            credentials: "same-origin",
            cache: "no-store",
            headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
            body,
        });
        try {
            return await response.json();
        } catch (err) {
            return { ok: false };
        }
    }

    function done(form, result) {
        const url = result.redirect || "/inside";
        // Close the upload modal so the in-place refresh does not reopen it.
        const modal = form.closest("[data-inside-modal]");
        if (modal) modal.hidden = true;
        const inside = window.GravewrightInside;
        if (inside && typeof inside.refresh === "function") {
            // Refresh in place, keeping the current section (Rulesets / Add-ons)
            // instead of a full reload that bounces back to Campaigns.
            inside.refresh(url).catch(() => window.location.assign(url));
        } else {
            window.location.assign(url);
        }
    }

    async function handleUpload(form) {
        form.setAttribute("aria-busy", "true");
        try {
            let result = await send(form, false);
            if (result.ok) return done(form, result);

            if (result.conflict) {
                const prompt = form.dataset.replaceConfirm || "Replace the existing package?";
                if (!window.confirm(prompt)) return;
                result = await send(form, true);
                if (result.ok) return done(form, result);
            }

            if (result.message) window.alert(result.message);
        } finally {
            form.removeAttribute("aria-busy");
        }
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest(".package-upload-form");
        if (!form) return;
        event.preventDefault();
        handleUpload(form).catch(() => form.removeAttribute("aria-busy"));
    });
})();
