(() => {
    function csrfToken() {
        return document.body.dataset.csrfToken || "";
    }

    function roleLabel(role) {
        const labels = {
            gm: document.body.dataset.roleGm || "GM",
            assistant_gm: document.body.dataset.roleAssistantGm || "Assistant GM",
            player: document.body.dataset.rolePlayer || "Player",
            streamer: document.body.dataset.roleStreamer || "Streamer",
        };

        return labels[role] || role;
    }

    function invitedByLabel(name) {
        const template = document.body.dataset.invitationInvitedByTemplate || "Invited by {name}";
        return template.replace("{name}", name || "");
    }

    function invitationRoleLabel(role) {
        const template = document.body.dataset.invitationRoleTemplate || "Role: {role}";
        return template.replace("{role}", roleLabel(role));
    }

    function campaignMemberRoleLabel(role) {
        const template = document.body.dataset.campaignMemberRoleTemplate || "Role: {role}";
        return template.replace("{role}", roleLabel(role));
    }

    function messageForKey(key) {
        const messages = {
            "inside.invitations.accepted": document.body.dataset.invitationAccepted,
            "inside.invitations.declined": document.body.dataset.invitationDeclined,
            "auth.errors.session_expired": document.body.dataset.invitationErrorSessionExpired,
            "inside.invitations.errors.not_found": document.body.dataset.invitationErrorNotFound,
            "inside.invitations.errors.not_pending": document.body.dataset.invitationErrorNotPending,
        };

        return messages[key] || key || "";
    }

    function showNotice(kind, message) {
        const notice = document.querySelector("#inside-invitation-notice");

        if (!notice) {
            return;
        }

        notice.hidden = false;
        notice.textContent = message;
        notice.classList.toggle("notice--danger", kind === "error");
    }

    function createHiddenInput(name, value) {
        const input = document.createElement("input");

        input.type = "hidden";
        input.name = name;
        input.value = value;

        return input;
    }

    function createButton(className, text) {
        const button = document.createElement("button");

        button.className = className;
        button.type = "submit";
        button.textContent = text;

        return button;
    }

    function createInvitationCard(invitation) {
        const card = document.createElement("article");
        card.className = "invitation-card";
        card.dataset.invitationId = invitation.id;

        const main = document.createElement("div");
        main.className = "invitation-main";

        const title = document.createElement("h2");
        title.textContent = invitation.campaign_title || "";

        main.appendChild(title);

        if (invitation.campaign_description) {
            const description = document.createElement("p");
            description.textContent = invitation.campaign_description;
            main.appendChild(description);
        }

        const meta = document.createElement("div");
        meta.className = "campaign-meta";

        const invitedBy = document.createElement("span");
        invitedBy.textContent = invitedByLabel(invitation.invited_by_name);

        const role = document.createElement("span");
        role.textContent = invitationRoleLabel(invitation.role);

        meta.appendChild(invitedBy);
        meta.appendChild(role);
        main.appendChild(meta);

        const actions = document.createElement("div");
        actions.className = "invitation-actions";

        const acceptForm = document.createElement("form");
        acceptForm.className = "invitation-accept-form";
        acceptForm.method = "post";
        acceptForm.action = "/campaigns/invitations/accept";
        acceptForm.appendChild(createHiddenInput("csrf_token", csrfToken()));
        acceptForm.appendChild(createHiddenInput("invitation_id", invitation.id));
        acceptForm.appendChild(
            createButton(
                "primary-action",
                document.body.dataset.invitationAcceptLabel || "Accept",
            ),
        );

        const declineForm = document.createElement("form");
        declineForm.className = "invitation-decline-form";
        declineForm.method = "post";
        declineForm.action = "/campaigns/invitations/decline";
        declineForm.appendChild(createHiddenInput("csrf_token", csrfToken()));
        declineForm.appendChild(createHiddenInput("invitation_id", invitation.id));
        declineForm.appendChild(
            createButton(
                "secondary-action",
                document.body.dataset.invitationDeclineLabel || "Decline",
            ),
        );

        actions.appendChild(acceptForm);
        actions.appendChild(declineForm);

        card.appendChild(main);
        card.appendChild(actions);

        return card;
    }

    function renderInvitations(invitations) {
        const section = document.querySelector("#pending-invitations-section");
        const list = document.querySelector("#pending-invitations-list");

        if (!section || !list) {
            return;
        }

        list.replaceChildren();

        if (!Array.isArray(invitations) || invitations.length === 0) {
            section.hidden = true;
            return;
        }

        invitations.forEach((invitation) => {
            list.appendChild(createInvitationCard(invitation));
        });

        section.hidden = false;
    }

    function ensureCampaignList() {
        let list = document.querySelector(".campaign-list");

        if (list) {
            return list;
        }

        const layout = document.querySelector(".campaign-layout");
        const emptyState = layout?.querySelector(".empty-state");

        if (!layout) {
            return null;
        }

        if (emptyState) {
            emptyState.remove();
        }

        list = document.createElement("div");
        list.className = "campaign-list";
        layout.appendChild(list);

        return list;
    }

    function campaignAlreadyRendered(campaignId) {
        return Boolean(document.querySelector(`.campaign-card[data-campaign-id="${campaignId}"]`));
    }

    function appendCampaignCard(campaign) {
        if (!campaign || !campaign.id || campaignAlreadyRendered(campaign.id)) {
            return;
        }

        const list = ensureCampaignList();

        if (!list) {
            return;
        }

        const card = document.createElement("article");
        card.className = "campaign-card";
        card.dataset.campaignId = campaign.id;

        const main = document.createElement("div");
        main.className = "campaign-card-main";

        const titleRow = document.createElement("div");
        titleRow.className = "campaign-title-row";

        const textWrap = document.createElement("div");

        const title = document.createElement("h2");
        title.textContent = campaign.title || "";

        textWrap.appendChild(title);

        if (campaign.description) {
            const description = document.createElement("p");
            description.textContent = campaign.description;
            textWrap.appendChild(description);
        }

        const openLink = document.createElement("a");
        openLink.className = "secondary-action";
        openLink.href = `/game?room=${encodeURIComponent(campaign.id)}`;
        openLink.textContent = document.body.dataset.campaignOpenLabel || "Open";

        titleRow.appendChild(textWrap);
        titleRow.appendChild(openLink);

        const meta = document.createElement("div");
        meta.className = "campaign-meta";

        const system = document.createElement("span");
        system.textContent = document.body.dataset.campaignSystemlessLabel || "No system attached";

        const role = document.createElement("span");
        role.textContent = campaignMemberRoleLabel(campaign.member_role);

        meta.appendChild(system);
        meta.appendChild(role);

        main.appendChild(titleRow);
        main.appendChild(meta);
        card.appendChild(main);

        list.prepend(card);
    }

    async function refreshInvitations() {
        const response = await fetch("/inside/invitations/pending", {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Cache-Control": "no-store",
            },
            credentials: "same-origin",
            cache: "no-store",
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        if (!data.ok) {
            return;
        }

        renderInvitations(data.invitations);
    }

    function asUrlEncodedBody(form) {
        return new URLSearchParams(new FormData(form));
    }

    async function submitInvitationAction(form) {
        const response = await fetch(form.action, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: asUrlEncodedBody(form),
            credentials: "same-origin",
            cache: "no-store",
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            showNotice("error", messageForKey(data.error_key));
            await refreshInvitations();
            return;
        }

        showNotice("success", messageForKey(data.message_key));

        const card = form.closest(".invitation-card");

        if (card) {
            card.remove();
        }

        if (data.campaign) {
            appendCampaignCard(data.campaign);
        }

        await refreshInvitations();
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest(".invitation-accept-form, .invitation-decline-form");

        if (!form) {
            return;
        }

        event.preventDefault();

        submitInvitationAction(form).catch(() => {
            showNotice("error", messageForKey("inside.invitations.errors.not_found"));
        });
    });
})();
