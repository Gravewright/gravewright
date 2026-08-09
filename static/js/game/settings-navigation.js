(() => {
    function makeControl(iconClass, attribute, label) {
        const button = document.createElement("button");
        button.className = "game-modal-control";
        button.type = "button";
        button.setAttribute(attribute, "");
        button.setAttribute("aria-label", label);
        button.innerHTML = `<i class="ph ${iconClass}" aria-hidden="true"></i>`;
        return button;
    }

    function createSettingsModal({ modalLayer, panel, roomId, section, sectionName, title }) {
        const modalId = `settings-${sectionName}-${roomId}`;
        const modal = document.createElement("article");
        modal.className = "game-modal-window settings-config-modal";
        modal.dataset.modalWindow = "";
        modal.dataset.modalId = modalId;
        modal.dataset.windowKey = modalId;
        modal.dataset.settingsModal = sectionName;
        modal.hidden = true;

        const titlebar = document.createElement("header");
        titlebar.className = "game-modal-titlebar";
        titlebar.dataset.modalDragHandle = "";

        const grip = document.createElement("span");
        grip.className = "game-modal-drag-grip";
        grip.setAttribute("aria-hidden", "true");

        const heading = document.createElement("span");
        heading.className = "game-panel-title";
        heading.textContent = title;

        const controls = document.createElement("div");
        controls.className = "game-modal-controls";
        controls.append(
            makeControl("ph-arrows-out", "data-modal-detach", "Detach"),
            makeControl("ph-minus", "data-modal-minimize", "Minimize"),
            makeControl("ph-x", "data-modal-close", "Close")
        );
        titlebar.append(grip, heading, controls);

        const body = document.createElement("div");
        body.className = "game-panel-body settings-config-modal-body";
        section.hidden = false;
        section.removeAttribute("data-settings-section");
        body.append(section);
        modal.append(titlebar, body);
        modalLayer.append(modal);

        const sourceButton = panel.querySelector(`[data-settings-section-tab="${sectionName}"]`);
        if (!sourceButton) return null;
        sourceButton.removeAttribute("data-settings-section-tab");
        sourceButton.removeAttribute("aria-selected");
        sourceButton.removeAttribute("tabindex");
        sourceButton.removeAttribute("data-tooltip");
        sourceButton.className = "settings-launcher-button";
        sourceButton.dataset.modalOpen = modalId;

        const text = sourceButton.querySelector("span");
        const description = section.querySelector(".settings-card-description")?.textContent?.trim();
        if (text) {
            const copy = document.createElement("small");
            copy.textContent = description || title;
            text.append(copy);
        }
        const arrow = document.createElement("i");
        arrow.className = "ph ph-caret-right settings-launcher-arrow";
        arrow.setAttribute("aria-hidden", "true");
        sourceButton.append(arrow);
        return sourceButton;
    }

    function initialise() {
        const modalLayer = document.querySelector(".game-modal-layer");
        if (!modalLayer) return;

        document.querySelectorAll("[data-settings-dashboard]").forEach((dashboard) => {
            const panel = dashboard.closest("[data-modal-id][data-panel-room]");
            const roomId = panel?.dataset.panelRoom;
            if (!panel || !roomId || dashboard.dataset.launcherReady === "true") return;

            const sections = [...dashboard.querySelectorAll("[data-settings-section]")];
            const sectionByName = new Map(sections.map((section) => [section.dataset.settingsSection, section]));
            const launcher = document.createElement("div");
            launcher.className = "settings-launcher-grid";

            const interfaceSection = sectionByName.get("interface");
            const visionSection = sectionByName.get("vision");
            if (interfaceSection && visionSection) {
                visionSection.hidden = false;
                visionSection.classList.add("settings-card-subsection");
                interfaceSection.append(visionSection);
                panel.querySelector('[data-settings-section-tab="vision"]')?.remove();
            }

            ["interface", "management"].forEach((sectionName) => {
                const section = sectionByName.get(sectionName);
                if (!section) return;
                const title = section.querySelector(".sidebar-section-title")?.textContent?.trim() || sectionName;
                const button = createSettingsModal({ modalLayer, panel, roomId, section, sectionName, title });
                if (button) launcher.append(button);
            });

            const inlineSections = ["system", "players"].map((sectionName) => {
                const section = sectionByName.get(sectionName);
                panel.querySelector(`[data-settings-section-tab="${sectionName}"]`)?.remove();
                if (!section) return null;
                section.hidden = false;
                section.removeAttribute("data-settings-section");
                section.classList.add("settings-inline-section");
                return section;
            }).filter(Boolean);

            dashboard.dataset.launcherReady = "true";
            dashboard.replaceChildren(launcher, ...inlineSections);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialise, { once: true });
    } else {
        initialise();
    }
})();
