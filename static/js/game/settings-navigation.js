(() => {
    const shownThisPage = new Set();

    function makeControl(iconClass, attribute, label) {
        const button = document.createElement("button");
        button.className = "game-modal-control";
        button.type = "button";
        button.setAttribute(attribute, "");
        button.setAttribute("aria-label", label);
        button.innerHTML = `<i class="ph ${iconClass}" aria-hidden="true"></i>`;
        return button;
    }

    function installedModules(layout) {
        const source = layout?.dataset.modulesPackages || "[]";
        try {
            const packages = JSON.parse(source);
            return (Array.isArray(packages) ? packages : [])
                .filter((pkg) => pkg?.id)
                .map((pkg) => ({
                    id: String(pkg.id), name: String(pkg.name || pkg.id),
                    kind: String(pkg.kind || "addon"), active: pkg.active === true,
                }));
        } catch (_error) {
            return [];
        }
    }

    function initialiseModulesSettings(section) {
        const layout = section.querySelector("[data-modules-settings]");
        const list = section.querySelector("[data-modules-settings-list]");
        const slot = section.querySelector('[data-sdk-slot="settings.modules"]');
        const empty = section.querySelector("[data-modules-settings-empty]");
        if (!layout || !list || !slot || layout.dataset.ready === "true") return;
        const modules = installedModules(layout);
        let selectedId = modules.find((pkg) => pkg.active)?.id || modules[0]?.id || "";

        function renderSelection() {
            list.querySelectorAll("[data-module-settings-package]").forEach((button) => {
                const active = button.dataset.moduleSettingsPackage === selectedId;
                button.classList.toggle("is-active", active);
                button.setAttribute("aria-selected", active ? "true" : "false");
            });
            let hasPanel = false;
            [...slot.children].forEach((root) => {
                const active = root.dataset.sdkPackage === selectedId;
                root.hidden = !active;
                if (active && root.childNodes.length) hasPanel = true;
            });
            empty.hidden = Boolean(selectedId && hasPanel);
            if (!selectedId) empty.querySelector("p").textContent = document.body.dataset.modulesEmpty || "Nenhum módulo ativo nesta mesa.";
            else if (!hasPanel) {
                const selected = modules.find((pkg) => pkg.id === selectedId);
                empty.querySelector("p").textContent = selected?.active
                    ? "Este módulo não fornece configurações."
                    : "Ative este módulo na campanha para configurar.";
            }
        }

        modules.forEach((pkg) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "modules-settings-package";
            button.dataset.moduleSettingsPackage = pkg.id;
            button.setAttribute("role", "tab");
            const icon = document.createElement("i");
            icon.className = "ph ph-puzzle-piece";
            icon.setAttribute("aria-hidden", "true");
            const text = document.createElement("span");
            const name = document.createElement("strong");
            name.textContent = pkg.name;
            const kind = document.createElement("small");
            kind.textContent = pkg.active ? pkg.kind : `${pkg.kind} · inativo`;
            text.append(name, kind);
            button.append(icon, text);
            button.addEventListener("click", () => { selectedId = pkg.id; renderSelection(); });
            list.append(button);
        });
        new MutationObserver(renderSelection).observe(slot, { childList: true, subtree: true });
        layout.dataset.ready = "true";
        renderSelection();
    }

    function createSettingsModal({ modalLayer, panel, roomId, section, sectionName, title, sourceSectionName = sectionName }) {
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
        if (sectionName === "modules") initialiseModulesSettings(section);

        const sourceButton = panel.querySelector(`[data-settings-section-tab="${sourceSectionName}"]`);
        if (!sourceButton) return null;
        sourceButton.removeAttribute("data-settings-section-tab");
        sourceButton.removeAttribute("aria-selected");
        sourceButton.removeAttribute("tabindex");
        sourceButton.removeAttribute("data-tooltip");
        sourceButton.className = "settings-launcher-button";
        sourceButton.dataset.modalOpen = modalId;

        const text = sourceButton.querySelector("span");
        const description = section.querySelector(".settings-card-description")?.textContent?.trim();
        if (["system", "modules"].includes(sectionName)) section.querySelector(".settings-card-header")?.remove();
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

    function buildGeneralSettings(interfaceSection, managementSection, panel) {
        const dashboard = panel.querySelector("[data-settings-dashboard]");
        const labels = {
            general: dashboard?.dataset.generalLabel || "General",
            interface: dashboard?.dataset.interfaceLabel || "Interface",
            administration: dashboard?.dataset.administrationLabel || "Administration",
            selectAdministration: dashboard?.dataset.administrationSelectLabel || "Select an administration option.",
        };
        const wrapper = document.createElement("section");
        wrapper.className = "settings-section settings-card general-settings";
        const layout = document.createElement("div");
        layout.className = "settings-master-detail general-settings-layout";
        const navigation = document.createElement("nav");
        navigation.className = "settings-master-list general-settings-list";
        navigation.setAttribute("aria-label", labels.general);
        const content = document.createElement("div");
        content.className = "settings-master-content general-settings-content";
        const entries = [
            { id: "interface", label: labels.interface, icon: "ph-monitor", section: interfaceSection },
        ].filter(entry => entry.section);
        let selectedId = entries[0]?.id || "";
        let administrationDetail = null;

        function select(id) {
            selectedId = id;
            navigation.querySelectorAll("button").forEach(button => {
                const active = button.dataset.generalSettingsSection === selectedId;
                button.classList.toggle("is-active", active);
                button.setAttribute("aria-selected", active ? "true" : "false");
            });
            entries.forEach(entry => { entry.section.hidden = entry.id !== selectedId; });
            if (administrationDetail) administrationDetail.hidden = true;
        }

        entries.forEach(entry => {
            entry.section.removeAttribute("data-settings-section");
            entry.section.classList.add("general-settings-panel");
            const source = panel.querySelector(`[data-settings-section-tab="${entry.id}"] span`);
            if (source?.textContent?.trim() && entry.id !== "interface") entry.label = source.textContent.trim();
            const button = document.createElement("button");
            button.type = "button";
            button.className = "settings-master-option general-settings-option";
            button.dataset.generalSettingsSection = entry.id;
            button.setAttribute("role", "tab");
            const icon = document.createElement("i");
            icon.className = `ph ${entry.icon}`;
            icon.setAttribute("aria-hidden", "true");
            const text = document.createElement("span");
            const name = document.createElement("strong");
            name.textContent = entry.label;
            text.append(name);
            button.append(icon, text);
            button.addEventListener("click", () => select(entry.id));
            navigation.append(button);
            content.append(entry.section);
        });
        if (managementSection) {
            administrationDetail = prepareAdministration(managementSection, navigation, content, labels, () => {
                selectedId = "administration";
                entries.forEach(entry => { entry.section.hidden = true; });
                navigation.querySelectorAll("button").forEach(button => {
                    const active = button.classList.contains("is-active") && button.dataset.administrationTarget;
                    if (!active) button.classList.remove("is-active");
                    button.setAttribute("aria-selected", active ? "true" : "false");
                });
            });
        }
        layout.append(navigation, content);
        wrapper.append(layout);
        select(selectedId);
        return wrapper;
    }

    function prepareAdministration(section, navigation, content, labels, onSelect) {
        const actions = section.querySelector(".settings-room-list");
        if (!actions) return null;
        const separator = document.createElement("p");
        separator.className = "general-settings-separator";
        separator.textContent = labels.administration;
        navigation.append(separator);
        const detail = document.createElement("section");
        detail.className = "administration-settings-detail general-settings-panel";
        detail.hidden = true;
        const empty = document.createElement("div");
        empty.className = "modules-settings-empty";
        const emptyIcon = document.createElement("i");
        emptyIcon.className = "ph ph-sliders-horizontal";
        emptyIcon.setAttribute("aria-hidden", "true");
        const emptyText = document.createElement("p");
        emptyText.textContent = labels.selectAdministration;
        empty.append(emptyIcon, emptyText);
        detail.append(empty);
        let mounted = null;

        [...actions.children].forEach(button => {
            button.classList.remove("settings-open-modal", "settings-open-modal--primary");
            button.classList.add("settings-master-option", "administration-settings-option");
            navigation.append(button);
            const modalId = button.dataset.modalOpen;
            if (!modalId) return;
            button.removeAttribute("data-modal-open");
            button.dataset.administrationTarget = modalId;
            button.addEventListener("click", () => {
                const target = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`);
                const body = target?.querySelector(":scope > .game-modal-body, :scope > .game-panel-body");
                if (!target || !body) return;
                if (mounted) {
                    mounted.marker.replaceWith(mounted.body);
                    mounted.button.classList.remove("is-active");
                }
                const marker = document.createComment(`administration:${modalId}`);
                body.before(marker);
                const title = target.querySelector(".game-panel-title, h2")?.textContent?.trim();
                const heading = document.createElement("h3");
                heading.className = "administration-settings-title";
                heading.textContent = title || button.textContent.trim();
                detail.replaceChildren(heading, body);
                detail.hidden = false;
                target.hidden = true;
                button.classList.add("is-active");
                onSelect();
                mounted = { body, marker, button };
            });
        });
        content.append(detail);
        section.remove();
        return detail;
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

            ["system", "modules"].forEach((sectionName) => {
                const section = sectionByName.get(sectionName);
                if (!section) return;
                const title = section.querySelector(".sidebar-section-title")?.textContent?.trim() || sectionName;
                const button = createSettingsModal({ modalLayer, panel, roomId, section, sectionName, title });
                if (button) launcher.append(button);
            });

            const managementSection = sectionByName.get("management");
            if (interfaceSection || managementSection) {
                const generalTitle = panel.querySelector('[data-settings-section-tab="interface"] span')?.textContent?.trim() || "Geral";
                const generalSection = buildGeneralSettings(interfaceSection, managementSection, panel);
                const button = createSettingsModal({
                    modalLayer, panel, roomId, section: generalSection,
                    sectionName: "general", sourceSectionName: "interface", title: generalTitle,
                });
                panel.querySelector('[data-settings-section-tab="management"]')?.remove();
                if (button) launcher.append(button);
            }

            const inlineSections = [];

            const playersSection = sectionByName.get("players");
            const usersHost = document.querySelector("[data-system-tray-users-host]");
            if (playersSection && usersHost) {
                playersSection.removeAttribute("data-settings-section");
                playersSection.classList.add("system-tray-users-panel");
                playersSection.dataset.systemTrayRoom = roomId;
                playersSection.hidden = activeRoomId() !== roomId;
                usersHost.append(playersSection);
            }

            dashboard.dataset.launcherReady = "true";
            dashboard.replaceChildren(launcher, ...inlineSections);
        });

        openPlayerFirstVisitForActiveRoom();
    }

    function activeRoomId() {
        return document.querySelector('input[name="selected-room"]:checked')?.value
            || document.querySelector("[data-panel-room]")?.dataset.panelRoom
            || "";
    }

    async function openPlayerFirstVisit(roomId) {
        if (!roomId || shownThisPage.has(roomId)) return;
        const settingsPanel = document.querySelector(
            `[data-modal-id="panel-settings-${CSS.escape(roomId)}"]`,
        );
        if (!settingsPanel || settingsPanel.dataset.memberRole !== "player") return;

        const modalId = `settings-general-${roomId}`;
        if (!document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`)) return;
        shownThisPage.add(roomId);
        try {
            const response = await fetch("/game/player-onboarding/claim", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ campaign_id: roomId }),
            });
            if (!response.ok) return;
            const payload = await response.json();
            if (payload.show === true) window.GravewrightModalInternals?.open?.(modalId);
        } catch {
            shownThisPage.delete(roomId);
        }
    }

    function openPlayerFirstVisitForActiveRoom() {
        openPlayerFirstVisit(activeRoomId());
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialise, { once: true });
    } else {
        initialise();
    }

    document.addEventListener("change", (event) => {
        if (!event.target.matches('input[name="selected-room"]')) return;
        window.requestAnimationFrame(() => openPlayerFirstVisit(event.target.value));
    });
})();
