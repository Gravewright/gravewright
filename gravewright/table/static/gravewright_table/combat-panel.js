













(function () {
    let activeMenu, menuSequence = 0;

    function closeMenu(restoreFocus = false) {
        activeMenu?.close(restoreFocus);
    }

    function openMenu(details, trigger, originals, last = false) {
        closeMenu();
        const doc = trigger.ownerDocument, view = doc.defaultView;
        const panel = trigger.closest('[data-native-directory]');
        const popup = doc.createElement('div');
        popup.className = 'gw-combat-menu__list directory-context-menu';
        popup.id = `combat-actions-${++menuSequence}`;
        popup.setAttribute('role', 'menu');
        popup.setAttribute('aria-label', trigger.getAttribute('aria-label'));
        Object.assign(popup.style, {position: 'fixed', right: 'auto', top: '0px', left: '0px',
            zIndex: String(Math.max(1500, (Number.parseInt(view.getComputedStyle(panel || trigger).zIndex) || 0) + 1)),
            boxSizing: 'border-box', minWidth: `${Math.max(0, Math.min(180, view.innerWidth - 16))}px`,
            maxWidth: `${Math.max(0, view.innerWidth - 16)}px`, maxHeight: `${Math.max(0, view.innerHeight - 16)}px`, overflowY: 'auto'});
        const releases = [];
        const listen = (target, type, handler, options) => {
            target.addEventListener(type, handler, options);
            releases.push(() => target.removeEventListener(type, handler, options));
        };
        let observer;
        const close = restoreFocus => {
            if (activeMenu?.popup !== popup) return;
            activeMenu = undefined;
            observer?.disconnect();
            for (const release of releases) release();
            popup.remove();
            details.open = false;
            trigger.setAttribute('aria-expanded', 'false');
            trigger.removeAttribute('aria-controls');
            if (restoreFocus && trigger.isConnected) trigger.focus();
        };
        activeMenu = {popup, panel, close};
        for (const original of originals.querySelectorAll('button')) {
            const choice = original.cloneNode(true);
            choice.setAttribute('role', 'menuitem');
            choice.tabIndex = -1;
            choice.addEventListener('click', event => {
                event.preventDefault();event.stopPropagation();
                const enabled = original.isConnected && !original.disabled;
                close(true);
                // Keep the original button in the panel so its delegated command
                // retains the combatant identity and the native action handler.
                if (enabled) original.click();
            });
            popup.appendChild(choice);
        }
        details.open = true;
        trigger.setAttribute('aria-expanded', 'true');
        trigger.setAttribute('aria-controls', popup.id);
        doc.body.appendChild(popup);
        const anchor = trigger.getBoundingClientRect(), box = popup.getBoundingClientRect();
        const top = anchor.bottom + box.height + 4 <= view.innerHeight - 8 ? anchor.bottom + 4 : anchor.top - box.height - 4;
        popup.style.left = `${Math.max(8, Math.min(anchor.right - box.width, view.innerWidth - box.width - 8))}px`;
        popup.style.top = `${Math.max(8, Math.min(top, view.innerHeight - box.height - 8))}px`;
        const choices = () => [...popup.querySelectorAll('button')].filter(button => !button.disabled);
        (last ? choices().at(-1) : choices()[0])?.focus();
        const outside = event => {if (!popup.contains(event.target) && !trigger.contains(event.target)) close(false);};
        listen(doc, 'pointerdown', outside, true);
        listen(doc, 'click', outside, true);
        listen(doc, 'keydown', event => {
            if (event.key === 'Escape') {event.preventDefault();event.stopPropagation();close(true);return;}
            if (event.key === 'Tab') {close(true);return;}
            if (!popup.contains(event.target) || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const buttons = choices(), index = buttons.indexOf(doc.activeElement);
            buttons[event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
                : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length]?.focus();
        });
        const scrollPosition = target => target === view || target === doc
            ? [view.scrollX || 0, view.scrollY || 0] : [target.scrollLeft || 0, target.scrollTop || 0];
        const scrollPositions = new Map([[view, scrollPosition(view)], [doc, scrollPosition(doc)]]);
        for (let parent = trigger.parentElement; parent; parent = parent.parentElement) scrollPositions.set(parent, scrollPosition(parent));
        listen(view, 'scroll', event => {
            if (popup.contains(event.target)) return;
            const previous = scrollPositions.get(event.target), current = scrollPosition(event.target);
            // Clicking a clipped trigger can queue its scroll-into-view event
            // before this menu opens. Only a later position change dismisses it.
            if (!previous || previous.some((value, index) => value !== current[index])) close(false);
        }, true);
        for (const event of ['resize', 'pagehide', 'gravewright:module-scene']) listen(view, event, () => close(false));
        observer = new view.MutationObserver(records => {
            if (!trigger.isConnected || panel?.hidden || panel?.hasAttribute('data-window-minimized')
                || records.some(record => record.target === panel && record.type === 'attributes')) close(false);
        });
        observer.observe(doc.body, {childList: true, subtree: true});
        if (panel) observer.observe(panel, {attributes: true, attributeFilter: ['hidden', 'class', 'style', 'data-window-minimized']});
    }

    const FALLBACK_LABELS = {
        start: "Start combat",
        end: "End combat",
        empty: "No combat is active in this table.",
        noCombatants: "Nobody in the order yet.",
        inactive: "Out of combat",
        waitingGm: "Waiting for the GM.",
        round: "Round",
        turn: "Turn",
        initiative: "Initiative",
        rollAll: "Roll initiative",
        rollNpcs: "Roll for NPCs",
        rollMissing: "Roll the missing ones",
        rollOne: "Roll for this combatant",
        setInitiative: "Set initiative",
        previousTurn: "Previous turn",
        nextTurn: "Next turn",
        previousRound: "Previous round",
        nextRound: "Next round",
        addSelected: "Add selected tokens",
        actions: "Combatant actions",
        centerToken: "Center token",
        openSheet: "Open sheet",
        setTurn: "Give the turn",
        remove: "Remove from combat",
        hide: "Hide from players",
        reveal: "Show to players",
        markDefeated: "Mark as defeated",
        clearDefeated: "Clear defeated",
        nextUp: "Next",
        moveUp: "Move up",
        moveDown: "Move down",
        configure: "Configure initiative",
        bar1: "Bar 1",
        bar2: "Bar 2",
        adjustResource: "Adjust resource",
    };

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = String(text);
        return node;
    }

    function icon(name) {
        const source=document.querySelector("#combat-icons")?.content.querySelector(`[data-combat-icon="${safeIcon(name)}"] svg`);
        const node=source?source.cloneNode(true):el("span");
        node.setAttribute("aria-hidden", "true");
        return node;
    }

    function safeIcon(value) {
        const text = String(value || "").trim().toLowerCase();
        const prefixed = text.startsWith("ph-") ? text : `ph-${text}`;
        const clean = prefixed.replace(/[^a-z0-9-]/g, "").slice(0, 48);
        return clean.length > 3 ? clean : "ph-dice-five";
    }



    function labelsFor(panel) {
        const data = panel?.dataset || {};
        const out = { ...FALLBACK_LABELS };
        if (document.documentElement.lang.toLowerCase().startsWith('pt')) Object.assign(out, {
            start: 'Iniciar combate', end: 'Encerrar combate', empty: 'Nenhum combatente nesta cena.',
            noCombatants: 'Nenhum combatente na ordem.', inactive: 'Fora de combate', waitingGm: 'Aguardando o mestre.',
            round: 'Rodada', turn: 'Turno', initiative: 'Iniciativa', rollAll: 'Rolar iniciativa',
            rollNpcs: 'Rolar para NPCs', rollMissing: 'Rolar iniciativas pendentes', rollOne: 'Rolar iniciativa',
            setInitiative: 'Definir iniciativa', previousTurn: 'Turno anterior', nextTurn: 'Próximo turno',
            previousRound: 'Rodada anterior', nextRound: 'Próxima rodada', addSelected: 'Adicionar tokens selecionados',
            actions: 'Ações do combatente', centerToken: 'Centralizar token', openSheet: 'Abrir ficha',
            setTurn: 'Definir turno atual', remove: 'Remover do combate', hide: 'Ocultar dos jogadores',
            reveal: 'Exibir aos jogadores', markDefeated: 'Marcar como derrotado', clearDefeated: 'Remover derrota',
            nextUp: 'Próximo', moveUp: 'Mover para cima', moveDown: 'Mover para baixo', configure: 'Configurar iniciativa',
            bar1: 'Barra 1', bar2: 'Barra 2', adjustResource: 'Ajustar recurso',
        });
        Object.keys(FALLBACK_LABELS).forEach((key) => {
            const value = data[`label${key.charAt(0).toUpperCase()}${key.slice(1)}`];
            if (value) out[key] = value;
        });
        return out;
    }

    function systemId(state) {
        return String(state?.config?.system_id || "");
    }

    function dispatch(state, name, payload) {
        return window.GravewrightCombat?.dispatch?.(systemId(state), name, payload);
    }

    function slot(state, name, payload) {
        return window.GravewrightCombat?.renderSlot?.(systemId(state), name, payload) || [];
    }

    function initiativeLabel(state, L) {
        return state?.config?.label || L.initiative;
    }

    function initiativeIcon(state) {
        return safeIcon(state?.config?.icon || "ph-dice-five");
    }

    function button(action, iconName, title, { primary = false, danger = false, disabled = false, data = {} } = {}) {
        const btn = el("button", "gw-combat-icon"
            + (primary ? " gw-combat-icon--primary" : "")
            + (danger ? " gw-combat-icon--danger" : ""));
        btn.type = "button";
        btn.title = title;
        btn.setAttribute("aria-label", title);
        btn.disabled = disabled;
        btn.dataset.combatAction = action;
        Object.entries(data).forEach(([key, value]) => { btn.dataset[key] = String(value); });
        btn.appendChild(icon(iconName));
        return btn;
    }

    function menuItem(action, iconName, text, { danger = false, data = {} } = {}) {
        const btn = el("button", "gw-combat-menu-item" + (danger ? " gw-combat-menu-item--danger" : ""));
        btn.type = "button";
        btn.dataset.combatAction = action;
        Object.entries(data).forEach(([key, value]) => { btn.dataset[key] = String(value); });
        btn.append(icon(iconName), el("span", null, text));
        return btn;
    }

    function portrait(combatant) {
        const wrap = el("span", "gw-combat-combatant__portrait");
        if (combatant.portrait_url) {
            const img = document.createElement("img");
            img.src = combatant.portrait_url;
            img.alt = "";
            img.loading = "lazy";
            wrap.appendChild(img);
        } else {
            const initial = String(combatant.name || "?").trim().charAt(0).toUpperCase() || "?";
            wrap.appendChild(el("span", "gw-combat-combatant__initial", initial));
        }
        if (combatant.defeated) {
            const defeated=icon('ph-skull');
            defeated.classList.add('gw-combat-combatant__defeated-icon');
            wrap.appendChild(defeated);
        }
        return wrap;
    }




    function resourceBar(bar, combatant, L) {
        if (!bar) return null;
        const percent = bar.percent == null ? 0 : Math.max(0, Math.min(100, Number(bar.percent) || 0));
        const level = percent <= 25 ? "is-critical" : (percent <= 50 ? "is-wounded" : "is-healthy");
        const wrap = el("button", `gw-combat-bar ${level}`);
        wrap.type = 'button';
        wrap.dataset.combatAction = 'resource/edit';
        wrap.dataset.combatantId = combatant.id;
        wrap.dataset.resourceSlot = bar.slot || 'bar_1';
        wrap.disabled = !combatant.canControl;
        const label = bar.slot === 'bar_2' ? L.bar2 : L.bar1;
        wrap.title = `${L.adjustResource}: ${label}`;
        wrap.setAttribute('aria-label', `${L.adjustResource}: ${combatant.name}, ${label}, ${bar.value}/${bar.max}`);
        if (bar.slot === 'bar_2') wrap.classList.add('gw-combat-bar--secondary');
        const track = el("span", "gw-combat-bar__track");
        const fill = el("span", "gw-combat-bar__fill");
        fill.style.width = `${percent}%`;
        track.appendChild(fill);
        wrap.append(track, el("span", "gw-combat-bar__value", `${bar.value ?? "-"}/${bar.max ?? "-"}`));
        return wrap;
    }



    function initiativeCell(combatant, state, isGm, L) {
        const text = combatant.initiative == null ? "" : String(combatant.initiative);
        if (!isGm) {
            const cell = el("span", "gw-combat-combatant__score", text || "-");
            cell.title = initiativeLabel(state, L);
            return cell;
        }
        const numeric = state?.config?.input !== "text";
        const input = el(
            "input",
            "gw-combat-combatant__score gw-combat-combatant__score--editable"
            + (numeric ? "" : " gw-combat-combatant__score--text"),
        );
        if (numeric) {
            input.type = "number";
            input.step = "any";
        } else {
            input.type = "text";
            input.maxLength = 24;
        }
        input.value = text;
        input.placeholder = "-";
        input.title = L.setInitiative;
        input.setAttribute("aria-label", `${initiativeLabel(state, L)}: ${combatant.name}`);
        input.dataset.combatInitiative = combatant.id;
        input.dataset.combatVersion = state.version;
        return input;
    }

    function combatantMenu(combatant, state, isGm, L) {
        const wrap = el("div", "gw-combat-combatant__actions");
        slot(state, "combatantActions", { combatant, state, isGm }).forEach((node) => wrap.appendChild(node));

        const menu = el("details", "gw-combat-menu");
        const trigger = el("summary", "gw-combat-menu__trigger");
        trigger.title = L.actions;
        trigger.setAttribute("aria-label", L.actions);
        trigger.setAttribute('aria-haspopup', 'menu');
        trigger.setAttribute('aria-expanded', 'false');
        trigger.appendChild(icon("ph-dots-three-outline-vertical"));
        menu.appendChild(trigger);

        const list = el("div", "gw-combat-menu__list");
        list.hidden = true;
        if (combatant.token_id) {
            list.append(
                menuItem("token/focus", "ph-crosshair", L.centerToken, { data: { tokenId: combatant.token_id } }),
                menuItem("token/sheet", "ph-identification-card", L.openSheet, { data: { tokenId: combatant.token_id } }),
            );
        }
        if (isGm) {
            const id = { combatantId: combatant.id };
            if (canRoll(state)) {
                list.appendChild(
                    menuItem("initiative/roll-one", initiativeIcon(state), L.rollOne, { data: id }),
                );
            }
            if (combatant.can_move_up) {
                list.appendChild(menuItem("order/up", "ph-arrow-up", L.moveUp, { data: id }));
            }
            if (combatant.can_move_down) {
                list.appendChild(menuItem("order/down", "ph-arrow-down", L.moveDown, { data: id }));
            }
            list.append(
                menuItem("turn/set", "ph-flag", L.setTurn, { data: id }),
                menuItem(
                    "flags/hidden",
                    combatant.hidden ? "ph-eye" : "ph-eye-slash",
                    combatant.hidden ? L.reveal : L.hide,
                    { data: { ...id, value: combatant.hidden ? "0" : "1" } },
                ),
                menuItem(
                    "flags/defeated",
                    combatant.defeated ? "ph-arrow-counter-clockwise" : "ph-skull",
                    combatant.defeated ? L.clearDefeated : L.markDefeated,
                    { data: { ...id, value: combatant.defeated ? "0" : "1" } },
                ),
                menuItem("combatants/remove", "ph-x", L.remove, { danger: true, data: id }),
            );
        }
        if (list.children.length) menu.appendChild(list); else return wrap;
        trigger.addEventListener('click', event => {
            event.preventDefault();event.stopPropagation();
            if (activeMenu?.popup && menu.open) closeMenu();
            else openMenu(menu, trigger, list);
        });
        trigger.addEventListener('keydown', event => {
            if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
            event.preventDefault();event.stopPropagation();openMenu(menu, trigger, list, event.key === 'ArrowUp');
        });
        wrap.appendChild(menu);
        return wrap;
    }

    function combatantRow(combatant, state, isGm, L) {
        const row = el("article", "gw-combat-combatant");
        if (combatant.is_current) row.classList.add("is-current");
        if (combatant.is_next) row.classList.add("is-next");
        if (combatant.has_acted) row.classList.add("has-acted");
        if (combatant.defeated) row.classList.add("is-defeated");
        if (combatant.hidden) row.classList.add("is-hidden-combatant");
        row.dataset.combatantId = combatant.id;
        row.dataset.tokenId = combatant.token_id || "";

        const position = el("span", "gw-combat-combatant__position", combatant.is_current ? '★' : combatant.position);
        if (combatant.is_current) {
            position.classList.add('gw-combat-combatant__turn-star');
            position.setAttribute('aria-label', L.turn);
            position.title = L.turn;
        }
        row.append(position, portrait(combatant));

        const main = el("div", "gw-combat-combatant__main");
        main.appendChild(el("span", "gw-combat-combatant__name", combatant.name || "???"));

        const meta = [];
        if (combatant.conditions_count) meta.push(`${combatant.conditions_count} ⊘`);
        if (combatant.effects_count) meta.push(`${combatant.effects_count} ✦`);
        const extra = dispatch(state, "combatantMeta", { combatant, state, isGm });
        (Array.isArray(extra) ? extra : [extra]).forEach((item) => {
            const text = String(item || "").trim();
            if (text) meta.push(text);
        });
        if (meta.length) main.appendChild(el("span", "gw-combat-combatant__meta", meta.join(" · ")));

        for (const value of combatant.bars || (combatant.bar ? [combatant.bar] : [])) {
            const bar = resourceBar(value, combatant, L);
            if (bar) main.appendChild(bar);
        }
        row.appendChild(main);

        row.append(initiativeCell(combatant, state, isGm, L), combatantMenu(combatant, state, isGm, L));
        return row;
    }

    function header(state, L, active) {
        const wrap = el("header", "gw-combat-header");
        if (!active) {
            wrap.appendChild(el("strong", "gw-combat-header__title", L.inactive));
            return wrap;
        }
        wrap.appendChild(el("strong", "gw-combat-header__title", `${L.round} ${state.round}`));
        const current = state.current_name || "-";
        wrap.appendChild(el("span", "gw-combat-header__current", current));
        if (state.next_name && state.next_name !== current) {
            wrap.appendChild(el("span", "gw-combat-header__next", `${L.nextUp}: ${state.next_name}`));
        }
        return wrap;
    }

    function toolbar(panel, state, L, active) {
        const bar = el("div", "gw-combat-toolbar");
        bar.append(
            button(active ? "end" : "start", active ? "ph-stop" : "ph-play", active ? L.end : L.start, {disabled: !state.sceneId || !active && !state.combatants?.length}),
            button("turn/previous", "ph-caret-left", L.previousTurn, { disabled: !active }),
            button("turn/next", "ph-caret-right", L.nextTurn, { primary: true, disabled: !active }),
            button("round/previous", "ph-arrow-counter-clockwise", L.previousRound, { disabled: !active || state.round <= 1 }),
            button("round/next", "ph-arrow-clockwise", L.nextRound, { disabled: !active }),
        );
        slot(state, "toolbar", { panel, state, isGm: true }).forEach((node) => bar.appendChild(node));
        return bar;
    }


    function canRoll(state) {
        return state?.config?.can_roll !== false && state?.config?.input === "roll";
    }

    function rollBar(state, L, active) {
        const bar = el("div", "gw-combat-rollbar");
        const die = initiativeIcon(state);
        bar.append(
            button("initiative/roll-all", die, L.rollAll, { disabled: !active, primary: true }),
            button("initiative/roll-npcs", "ph-skull", L.rollNpcs, { disabled: !active }),
            button("initiative/roll-missing", "ph-question", L.rollMissing, { disabled: !active }),
        );
        return bar;
    }

    function renderPanel(panel, state) {
        if (activeMenu?.panel === panel) closeMenu();
        const target = panel.querySelector("[data-combat-state]");
        if (!target) return;
        const L = labelsFor(panel);
        const isGm = panel.dataset.isGm === "true";
        const active = !!state?.active;
        const combatants = Array.isArray(state?.combatants) ? state.combatants : [];

        dispatch(state, "beforeRender", { panel, state, isGm });
        target.innerHTML = "";
        target.classList.toggle("is-active", active);
        if (state?.config?.accent) target.style.setProperty("--gw-combat-accent", state.config.accent);

        target.appendChild(header(state, L, active));
        if (isGm) {
            target.appendChild(toolbar(panel, state, L, active));
            if (canRoll(state)) target.appendChild(rollBar(state, L, combatants.length > 0));
        } else if (active && combatants.some(row => row.current && row.canControl)) {
            const controls = el('div', 'gw-combat-toolbar');
            controls.appendChild(button('turn/next', 'ph-caret-right', L.nextTurn, {primary: true}));
            target.appendChild(controls);
        }

        const list = el("div", "gw-combat-list");
        if (!combatants.length) {
            const empty = el("div", "tool-empty gw-combat-empty");
            empty.appendChild(icon("ph-sword"));
            empty.appendChild(el("p", null, active ? L.noCombatants : (isGm ? L.empty : L.waitingGm)));
            list.appendChild(empty);
        } else {
            combatants.forEach((combatant) => list.appendChild(combatantRow(combatant, state, isGm, L)));
        }
        target.appendChild(list);

        dispatch(state, "afterRender", { panel, state, target, isGm });
    }


    if (!window.GravewrightCombatPanel) {
        window.GravewrightCombatPanel = { renderPanel };
    }
})();
