








(function () {
  const DEFAULT_COMBAT_UI = {
    skin: "default",
    density: "compact",
    palette: {
      accent: "#c09a5a",
      accentStrong: "#f8e5ad",
      danger: "#ef4444",
      dangerSoft: "#fca5a5",
      current: "#28d17c",
      next: "#ef4444",
      acted: "#9ca3af",
      scrollbarThumb: "#c09a5a",
      scrollbarTrack: "#080a0d",
      surface: "#22120f",
    },
    initiative: {
      icon: "ph-dice-five",
      monsterIcon: "ph-skull",
      rollAllLabel: "Rolar todas",
      rollMonstersLabel: "Só monstros",
      rollSubtitle: "d20 + mod.",
      monsterSubtitle: "NPCs e criaturas",
      scoreLabel: "Iniciativa",
    },
    statusLabels: {
      current: "Turno atual",
      next: "Próximo",
      acted: "Já agiu",
      waiting: "Aguardando",
    },
  };

  const PALETTE_VARS = {
    accent: "--gw-combat-ui-accent",
    accentStrong: "--gw-combat-ui-accent-strong",
    danger: "--gw-combat-ui-danger",
    dangerSoft: "--gw-combat-ui-danger-soft",
    current: "--combat-current",
    next: "--combat-next",
    acted: "--combat-acted",
    scrollbarThumb: "--gw-combat-ui-scrollbar-thumb",
    scrollbarTrack: "--gw-combat-ui-scrollbar-track",
    surface: "--gw-combat-ui-surface",
    surfaceRaised: "--gw-combat-ui-surface-raised",
    text: "--gw-combat-ui-text",
    muted: "--gw-combat-ui-muted",
    border: "--gw-combat-ui-border",
    gold: "--gw-combat-ui-gold",
    blood: "--gw-combat-ui-blood",
  };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function safeNumber(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function safeToken(value, fallback = "default") {
    const text = String(value || "").trim().toLowerCase().replace(/_/g, "-");
    const clean = text.replace(/[^a-z0-9-]/g, "").slice(0, 40).replace(/^-+|-+$/g, "");
    return clean || fallback;
  }

  function safeIcon(value, fallback = "ph-dice-five") {
    const text = String(value || "").trim().toLowerCase();
    const prefixed = text.startsWith("ph-") ? text : (text ? `ph-${text}` : fallback);
    const clean = prefixed.replace(/[^a-z0-9-]/g, "").slice(0, 48);
    return clean.startsWith("ph-") ? clean : fallback;
  }

  function mergeObject(base, override) {
    return { ...(base || {}), ...((override && typeof override === "object") ? override : {}) };
  }

  function systemIdFor(state) {
    return String(state?.config?.systemId || state?.system_id || "");
  }

  function combatHook(state, name, payload) {
    return window.GravewrightCombat?.callHook?.(systemIdFor(state), name, payload);
  }

  function combatSlot(state, name, payload) {
    return window.GravewrightCombat?.renderSlot?.(systemIdFor(state), name, payload) || [];
  }

  function combatUi(state) {
    const config = state?.config || {};
    const authored = config.ui?.combat && typeof config.ui.combat === "object" ? config.ui.combat : {};
    const legacy = config.initiative?.appearance && typeof config.initiative.appearance === "object" ? config.initiative.appearance : {};
    const ui = {
      ...DEFAULT_COMBAT_UI,
      ...authored,
      skin: authored.skin || authored.theme || legacy.theme || DEFAULT_COMBAT_UI.skin,
      palette: mergeObject(DEFAULT_COMBAT_UI.palette, authored.palette),
      initiative: mergeObject(DEFAULT_COMBAT_UI.initiative, authored.initiative),
      statusLabels: mergeObject(DEFAULT_COMBAT_UI.statusLabels, authored.statusLabels),
    };

    if (legacy.rollAllLabel && !authored.initiative?.rollAllLabel) ui.initiative.rollAllLabel = legacy.rollAllLabel;
    if (legacy.rollMonstersLabel && !authored.initiative?.rollMonstersLabel) ui.initiative.rollMonstersLabel = legacy.rollMonstersLabel;
    if (legacy.rollSubtitle && !authored.initiative?.rollSubtitle) ui.initiative.rollSubtitle = legacy.rollSubtitle;
    if (legacy.monsterSubtitle && !authored.initiative?.monsterSubtitle) ui.initiative.monsterSubtitle = legacy.monsterSubtitle;
    if (legacy.icon && !authored.initiative?.icon) ui.initiative.icon = legacy.icon;
    if (legacy.monsterIcon && !authored.initiative?.monsterIcon) ui.initiative.monsterIcon = legacy.monsterIcon;

    ui.skin = safeToken(ui.skin);
    ui.density = safeToken(ui.density || "compact");
    ui.initiative.icon = safeIcon(ui.initiative.icon);
    ui.initiative.monsterIcon = safeIcon(ui.initiative.monsterIcon, "ph-skull");
    return ui;
  }

  function applyCombatUi(target, state) {
    const ui = combatUi(state);
    [...target.classList]
      .filter((className) => className.startsWith("gw-combat-state--skin-") || className.startsWith("gw-combat-density--"))
      .forEach((className) => target.classList.remove(className));
    target.classList.remove("gw-combat-state--dnd5e");
    target.classList.add(`gw-combat-state--skin-${ui.skin}`);
    target.classList.add(`gw-combat-density--${ui.density}`);

    Object.entries(PALETTE_VARS).forEach(([key, cssVar]) => {
      if (ui.palette?.[key]) target.style.setProperty(cssVar, String(ui.palette[key]));
    });
    return ui;
  }

  function currentLabel(state) {
    const current = state?.current || {};
    return current.name || "—";
  }

  function participantId(participant) {
    return participant?.id || participant?.participant_id || "";
  }

  function participantStatus(participant) {
    if (participant?.is_current || participant?.is_active_turn) return "current";
    if (participant?.is_next) return "next";
    if (participant?.has_acted || participant?.turn_status === "acted") return "acted";
    return "waiting";
  }

  function nextParticipant(state) {
    const participants = Array.isArray(state?.participants) ? state.participants : [];
    if (participants.length <= 1) return null;
    const explicit = state?.next_participant_id || "";
    if (explicit) {
      const matched = participants.find((participant) => participantId(participant) === explicit);
      if (matched) return matched;
    }
    const currentIndex = safeNumber(state?.turn_index, -1);
    if (currentIndex >= 0 && currentIndex < participants.length) return participants[(currentIndex + 1) % participants.length];
    const currentId = state?.current_participant_id || state?.active_participant_id || state?.current?.id || "";
    const foundIndex = currentId ? participants.findIndex((participant) => participantId(participant) === currentId) : -1;
    return foundIndex >= 0 ? participants[(foundIndex + 1) % participants.length] : null;
  }

  function nextParticipantId(state) {
    return participantId(nextParticipant(state));
  }

  function turnSummary(state) {
    const round = state?.round || 1;
    const position = state?.turn_position || 0;
    const count = state?.turn_count || (Array.isArray(state?.participants) ? state.participants.length : 0);
    const suffix = count ? ` · Turno ${position}/${count}` : "";
    return `Rodada ${round}${suffix}`;
  }

  function statusLabel(status, state) {
    const labels = combatUi(state).statusLabels || DEFAULT_COMBAT_UI.statusLabels;
    return labels[status] || DEFAULT_COMBAT_UI.statusLabels[status] || "Aguardando";
  }

  function participantPortrait(participant, className = "gw-combat-participant__portrait") {
    const wrap = el("span", className);
    const url = participant?.portrait_url || participant?.token_asset_url || "";
    if (url) {
      const img = document.createElement("img");
      img.src = url;
      img.alt = "";
      img.loading = "lazy";
      wrap.appendChild(img);
      return wrap;
    }
    const initial = String(participant?.name || "?").trim().charAt(0).toUpperCase() || "?";
    wrap.appendChild(el("span", "gw-combat-participant__initial", initial));
    return wrap;
  }

  function iconButton(action, icon, title, { primary = false, danger = false, disabled = false, className = "" } = {}) {
    const btn = el(
      "button",
      "gw-combat-icon"
      + (primary ? " gw-combat-icon--primary" : "")
      + (danger ? " gw-combat-icon--danger" : "")
      + (className ? ` ${className}` : ""),
    );
    btn.type = "button";
    btn.title = title;
    btn.setAttribute("aria-label", title);
    btn.disabled = disabled;
    btn.dataset.combatPanelAction = action;
    const iconNode = el("i", `ph ${safeIcon(icon)}`);
    iconNode.setAttribute("aria-hidden", "true");
    btn.appendChild(iconNode);
    return btn;
  }

  function textActionButton(action, icon, label, { sublabel = "", disabled = false, primary = false } = {}) {
    const btn = el("button", `gw-combat-roll-btn${primary ? " gw-combat-roll-btn--primary" : ""}`);
    btn.type = "button";
    btn.disabled = disabled;
    btn.dataset.combatPanelAction = action;
    const iconNode = el("i", `ph ${safeIcon(icon)}`);
    iconNode.setAttribute("aria-hidden", "true");
    const text = el("span", "gw-combat-roll-btn__text");
    text.appendChild(el("strong", null, label));
    if (sublabel) text.appendChild(el("small", null, sublabel));
    btn.append(iconNode, text);
    return btn;
  }

  function actionMenuItem(action, icon, label, { danger = false, disabled = false } = {}) {
    const btn = el(
      "button",
      "gw-combat-menu-item" + (danger ? " gw-combat-menu-item--danger" : ""),
    );
    btn.type = "button";
    btn.disabled = disabled;
    btn.dataset.combatPanelAction = action;
    const iconNode = el("i", `ph ${safeIcon(icon)}`);
    iconNode.setAttribute("aria-hidden", "true");
    btn.appendChild(iconNode);
    btn.appendChild(el("span", null, label));
    return btn;
  }

  function participantActionsMenu(participant, state, isGm) {
    const actions = el("div", "gw-combat-participant__actions");
    combatSlot(state, "participantActions", { participant, state, isGm }).forEach((node) => {
      actions.appendChild(node);
    });
    const menu = el("details", "gw-combat-participant-menu");
    const trigger = el("summary", "gw-combat-participant-menu__trigger");
    trigger.title = "Ações do participante";
    trigger.setAttribute("aria-label", "Ações do participante");
    trigger.innerHTML = '<i class="ph ph-dots-three-outline-vertical" aria-hidden="true"></i>';
    menu.appendChild(trigger);

    const list = el("div", "gw-combat-participant-menu__list");
    if (participant.token_id) {
      const focus = actionMenuItem("token/focus", "ph-crosshair", "Centralizar token");
      focus.dataset.tokenId = participant.token_id;
      list.appendChild(focus);
      const sheet = actionMenuItem("token/sheet", "ph-identification-card", "Abrir ficha");
      sheet.dataset.tokenId = participant.token_id;
      list.appendChild(sheet);
    }
    if (isGm) {
      const roll = actionMenuItem("initiative/participant/roll", combatUi(state).initiative.icon, "Rolar iniciativa");
      roll.dataset.participantId = participant.id;
      list.appendChild(roll);
      const setTurn = actionMenuItem("turn/set", "ph-flag", "Definir como turno");
      setTurn.dataset.turnIndex = String(participant.turn_index ?? (state.participants || []).indexOf(participant));
      list.appendChild(setTurn);
      const remove = actionMenuItem("participants/remove", "ph-x", "Remover", { danger: true });
      remove.dataset.participantId = participant.id;
      list.appendChild(remove);
    }

    if (!list.children.length) {
      const empty = el("span", "gw-combat-menu-item gw-combat-menu-item--empty", "Sem ações");
      list.appendChild(empty);
    }
    menu.appendChild(list);
    actions.appendChild(menu);
    return actions;
  }

  function metric(label, value, className = "") {
    const node = el("span", `gw-combat-metric${className ? ` ${className}` : ""}`);
    node.appendChild(el("span", "gw-combat-metric__label", label));
    node.appendChild(el("strong", "gw-combat-metric__value", value));
    return node;
  }

  function hpResource(participant) {
    const resources = participant?.resources;
    if (!resources || typeof resources !== "object") return null;
    return resources.hp || resources.health || null;
  }

  function hpClass(hp) {
    if (!hp || hp.percent == null) return "";
    if (hp.percent <= 25) return "is-critical";
    if (hp.percent <= 50) return "is-wounded";
    return "is-healthy";
  }

  function hpBar(participant) {
    const hp = hpResource(participant);
    if (!hp) return null;
    const percent = hp.percent == null ? 0 : Math.max(0, Math.min(100, Number(hp.percent) || 0));
    const wrap = el("div", `gw-combat-hp ${hpClass(hp)}`);
    const label = el("span", "gw-combat-hp__label", hp.label || "HP");
    const value = el("span", "gw-combat-hp__value", `${hp.value ?? "—"}/${hp.max ?? "—"}`);
    const track = el("span", "gw-combat-hp__track");
    const fill = el("span", "gw-combat-hp__fill");
    fill.style.width = `${percent}%`;
    track.appendChild(fill);
    wrap.append(label, track, value);
    return wrap;
  }

  function initiativeLabel(state) {
    return combatUi(state).initiative.scoreLabel || state?.config?.initiative?.label || state?.config?.initiativeRoll?.label || state?.config?.turnOrder?.label || "Iniciativa";
  }

  function combatStats(state) {
    const participants = Array.isArray(state?.participants) ? state.participants : [];
    return {
      total: participants.length,
      waiting: participants.filter((p) => participantStatus(p) === "waiting").length,
      acted: participants.filter((p) => participantStatus(p) === "acted").length,
      withInitiative: participants.filter((p) => p.initiative_label && p.initiative_label !== "—").length,
    };
  }

  function renderHud(hud, state) {
    const isGm = hud.dataset.isGm === "true";
    hud.innerHTML = "";
    const active = !!state?.is_active;
    hud.classList.toggle("is-active", active);
    hud.appendChild(el("div", "gw-combat-hud__label", hud.dataset.combatLabel || "Combate"));
    const roundText = active
      ? `${turnSummary(state)} · ${currentLabel(state)}`
      : (hud.dataset.combatInactiveLabel || "Fora de combate");
    hud.appendChild(el("div", "gw-combat-hud__round", roundText));
    if (!isGm) return;
    const actions = el("div", "gw-combat-hud__actions");
    const start = el("button", "gw-combat-hud__btn", active ? (hud.dataset.combatEndLabel || "Encerrar") : (hud.dataset.combatStartLabel || "Iniciar"));
    start.type = "button";
    start.dataset.combatAction = active ? "end" : "start";
    actions.appendChild(start);
    const next = el("button", "gw-combat-hud__btn gw-combat-hud__btn--primary", "Próximo turno");
    next.type = "button";
    next.dataset.combatAction = "turn/next";
    next.disabled = !active;
    actions.appendChild(next);
    hud.appendChild(actions);
  }

  function renderHero(state) {
    const active = !!state?.is_active;
    const participants = Array.isArray(state?.participants) ? state.participants : [];
    const current = state?.current || participants.find((p) => p.is_current) || {};
    const upcoming = nextParticipant(state) || {};
    const hero = el("section", "gw-combat-hero" + (active ? " is-active" : ""));

    const avatar = participantPortrait(current, "gw-combat-hero__portrait");
    hero.appendChild(avatar);

    const body = el("div", "gw-combat-hero__body");
    body.appendChild(el("span", "gw-combat-hero__eyebrow", active ? turnSummary(state) : "Fora de combate"));
    body.appendChild(el("strong", "gw-combat-hero__name", active ? (current.name || "Sem participante ativo") : "Combate não iniciado"));
    const sub = active
      ? `${statusLabel("next", state)}: ${upcoming.name || "—"}`
      : "Inicie o combate e adicione tokens para montar a ordem.";
    body.appendChild(el("span", "gw-combat-hero__sub", sub));
    hero.appendChild(body);

    const score = el("div", "gw-combat-hero__score");
    score.appendChild(el("span", "gw-combat-hero__score-label", initiativeLabel(state)));
    score.appendChild(el("strong", "gw-combat-hero__score-value", active ? (current.initiative_label || "—") : "—"));
    hero.appendChild(score);
    return hero;
  }

  function filterButton(panel, filter, label, count) {
    const active = (panel.dataset.combatFilter || "all") === filter;
    const btn = el("button", `gw-combat-filter${active ? " is-active" : ""}`);
    btn.type = "button";
    btn.dataset.combatFilter = filter;
    btn.textContent = count == null ? label : `${label} ${count}`;
    return btn;
  }

  function renderSearchAndFilters(panel, state) {
    const participants = Array.isArray(state?.participants) ? state.participants : [];
    const counts = {
      all: participants.length,
      current: participants.filter((p) => participantStatus(p) === "current").length,
      waiting: participants.filter((p) => participantStatus(p) === "waiting" || participantStatus(p) === "next").length,
      acted: participants.filter((p) => participantStatus(p) === "acted").length,
    };
    const wrap = el("section", "gw-combat-controls");
    const search = el("label", "gw-combat-search");
    search.innerHTML = '<i class="ph ph-magnifying-glass" aria-hidden="true"></i>';
    const input = document.createElement("input");
    input.type = "search";
    input.placeholder = "Buscar participante";
    input.autocomplete = "off";
    input.value = panel.dataset.combatSearch || "";
    input.dataset.combatSearch = "true";
    search.appendChild(input);
    wrap.appendChild(search);

    const filters = el("div", "gw-combat-filters");
    filters.appendChild(filterButton(panel, "all", "Todos", counts.all));
    filters.appendChild(filterButton(panel, "waiting", statusLabel("waiting", state), counts.waiting));
    filters.appendChild(filterButton(panel, "acted", "Agiram", counts.acted));
    filters.appendChild(filterButton(panel, "current", "Atual", counts.current));
    wrap.appendChild(filters);
    return wrap;
  }

  function matchesPanelFilter(panel, participant) {
    const filter = panel.dataset.combatFilter || "all";
    const search = String(panel.dataset.combatSearch || "").trim().toLowerCase();
    const status = participantStatus(participant);
    if (filter === "current" && status !== "current") return false;
    if (filter === "waiting" && status !== "waiting" && status !== "next") return false;
    if (filter === "acted" && status !== "acted") return false;
    if (search && !String(participant.name || "").toLowerCase().includes(search)) return false;
    return true;
  }

  function participantRow(participant, state, isGm) {
    const status = participantStatus(participant);
    const row = el("article", `gw-combat-participant is-${status}`);
    if (participant.is_current) row.classList.add("is-current");
    if (participant.is_next || participantId(participant) === nextParticipantId(state)) row.classList.add("is-next");
    if (participant.has_acted) row.classList.add("has-acted");
    if (participant.turn_status === "waiting") row.classList.add("is-waiting");
    row.dataset.participantId = participantId(participant);
    row.dataset.tokenId = participant.token_id || "";
    row.dataset.actorId = participant.actor_id || "";

    const order = el("span", "gw-combat-participant__order", participant.turn_position || "—");
    row.appendChild(order);

    row.appendChild(participantPortrait(participant));

    const main = el("div", "gw-combat-participant__main");
    const top = el("div", "gw-combat-participant__topline");
    const name = el("span", "gw-combat-participant__name", participant.name || "???");
    top.appendChild(name);
    const badge = el("span", `gw-combat-participant__badge is-${status}`, statusLabel(status, state));
    top.appendChild(badge);
    main.appendChild(top);

    const metaParts = [];
    if (participant.token_id) metaParts.push("Token");
    if (participant.initiative_data?.kind === "card") metaParts.push("Carta");
    if (participant.conditions_count) metaParts.push(`${participant.conditions_count} condição${participant.conditions_count === 1 ? "" : "ões"}`);
    if (participant.effects_count) metaParts.push(`${participant.effects_count} efeito${participant.effects_count === 1 ? "" : "s"}`);
    const pluginMeta = combatHook(state, "participantMeta", { participant, state, isGm });
    if (Array.isArray(pluginMeta)) {
      pluginMeta.map((item) => String(item || "").trim()).filter(Boolean).forEach((item) => metaParts.push(item));
    } else if (pluginMeta) {
      metaParts.push(String(pluginMeta).trim());
    }
    if (metaParts.length) {
      main.appendChild(el("span", "gw-combat-participant__meta", metaParts.join(" · ")));
    }
    const hp = hpBar(participant);
    if (hp) main.appendChild(hp);
    row.appendChild(main);

    const score = el("span", "gw-combat-participant__score", participant.initiative_label || "—");
    score.title = initiativeLabel(state);
    row.appendChild(score);

    row.appendChild(participantActionsMenu(participant, state, isGm));
    return row;
  }

  function renderToolbar(panel, state, active, isGm) {
    const selectedCount = Number(panel.dataset.selectedTokenCount || 0);
    const toolbar = el("div", "gw-combat-toolbar");
    toolbar.appendChild(iconButton(active ? "end" : "start", active ? "ph-stop" : "ph-play", active ? "Encerrar combate" : "Iniciar combate"));
    toolbar.appendChild(iconButton("participants/add-selected", "ph-plus-circle", selectedCount ? `Adicionar ${selectedCount} token(s) selecionado(s)` : "Adicionar tokens selecionados", { disabled: !isGm || selectedCount < 1 }));
    toolbar.appendChild(iconButton("turn/previous", "ph-caret-left", "Turno anterior", { disabled: !isGm || !active }));
    toolbar.appendChild(iconButton("turn/next", "ph-caret-right", "Próximo turno", { primary: true, disabled: !isGm || !active }));
    toolbar.appendChild(iconButton("round/next", "ph-arrow-clockwise", "Próxima rodada", { disabled: !isGm || !active }));
    return toolbar;
  }

  function renderInitiativeActions(state, active, isGm) {
    const ui = combatUi(state).initiative;
    const wrap = el("section", "gw-combat-initiative-actions");
    wrap.appendChild(textActionButton(
      "initiative/roll",
      ui.icon,
      ui.rollAllLabel || "Rolar todas",
      { sublabel: ui.rollSubtitle || "", disabled: !isGm || !active, primary: true },
    ));
    wrap.appendChild(textActionButton(
      "initiative/roll-monsters",
      ui.monsterIcon,
      ui.rollMonstersLabel || "Só monstros",
      { sublabel: ui.monsterSubtitle || "", disabled: !isGm || !active },
    ));
    return wrap;
  }

  function renderMetrics(state) {
    const stats = combatStats(state);
    const wrap = el("section", "gw-combat-metrics");
    wrap.appendChild(metric("Participantes", String(stats.total)));
    wrap.appendChild(metric("Iniciativas", `${stats.withInitiative}/${stats.total || 0}`));
    wrap.appendChild(metric("Aguardando", String(stats.waiting), "is-waiting"));
    wrap.appendChild(metric("Já agiram", String(stats.acted), "is-acted"));
    return wrap;
  }

  function renderPanel(panel, state) {
    const target = panel.querySelector("[data-combat-state]");
    if (!target) return;
    const isGm = panel.dataset.isGm === "true";
    combatHook(state, "beforeRender", { panel, state, isGm });
    target.innerHTML = "";
    const active = !!state?.is_active;
    applyCombatUi(target, state);

    target.appendChild(renderHero(state));
    if (isGm) {
      target.appendChild(renderInitiativeActions(state, active, isGm));
      target.appendChild(renderToolbar(panel, state, active, isGm));
    }
    target.appendChild(renderMetrics(state));
    target.appendChild(renderSearchAndFilters(panel, state));

    const list = el("div", "gw-combat-participant-list");
    const participants = Array.isArray(state?.participants) ? state.participants : [];
    const visible = participants.filter((participant) => matchesPanelFilter(panel, participant));
    if (!participants.length) {
      const empty = el("div", "tool-empty gw-combat-empty");
      empty.innerHTML = '<i class="ph ph-sword" aria-hidden="true"></i>';
      empty.appendChild(el("p", null, active ? "Nenhum participante. Selecione tokens e use + para adicionar." : "Nenhum combate ativo."));
      list.appendChild(empty);
    } else if (!visible.length) {
      const empty = el("div", "tool-empty gw-combat-empty");
      empty.innerHTML = '<i class="ph ph-funnel" aria-hidden="true"></i>';
      empty.appendChild(el("p", null, "Nenhum participante corresponde ao filtro."));
      list.appendChild(empty);
    } else {
      visible.forEach((participant) => list.appendChild(participantRow(participant, state, isGm)));
    }
    target.appendChild(list);

    const footer = el("div", "gw-combat-footer");
    if (active) {
      footer.appendChild(el("span", "gw-combat-footer__round", turnSummary(state)));
      footer.appendChild(el("span", "gw-combat-footer__turn", `${initiativeLabel(state)} · Atual: ${currentLabel(state)}`));
    } else {
      footer.appendChild(el("span", "gw-combat-footer__round", "Fora de combate"));
      footer.appendChild(el("span", "gw-combat-footer__turn", isGm ? "Use ▶ para iniciar." : "Aguardando GM."));
    }
    target.appendChild(footer);
    combatHook(state, "afterRender", { panel, state, target, isGm });
  }

  window.GravewrightCombatPanel = { renderHud, renderPanel };
})();
