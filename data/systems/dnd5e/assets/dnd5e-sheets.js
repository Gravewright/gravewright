








(function () {
  const GW = window.GravewrightSheets;
  if (!GW || typeof GW.registerSystem !== "function") return;
  const h = GW.helpers;

  

  function skillKeyFromPath(path) {
    const match = String(path || "").match(/^sheet\.skills\.([^.]+)\./);
    return match ? match[1] : "";
  }

  function monsterSkillRows(children, ctx) {
    return (children || []).map((skill) => {
      const key = skillKeyFromPath(skill.profPath || skill.expertPath || skill.modPath);
      return {
        key,
        label: skill.label || key,
        ability: skill.ability || "",
        mod: h.formatMod(h.getPath(ctx, skill.modPath)),
        profPath: skill.profPath || "",
        expertPath: skill.expertPath || "",
        prof: !!h.getPath(ctx, skill.profPath),
        expert: !!h.getPath(ctx, skill.expertPath),
        interaction: h.normalizeInteraction(skill.interaction, skill.rollAction, skill.rollLabel || skill.label),
      };
    }).filter((skill) => skill.key);
  }

  function renderMonsterSkillSummaryRow(skill) {
    const trigger = h.el("button", "actor-monster-skill-summary");
    trigger.type = "button";
    trigger.appendChild(h.el("span", "actor-monster-skill-name", skill.label));
    if (skill.ability) trigger.appendChild(h.el("span", "actor-monster-skill-ability", skill.ability));
    trigger.appendChild(h.el("span", "actor-monster-skill-mod", skill.mod));
    if (skill.expert) trigger.appendChild(h.el("span", "actor-monster-skill-badge", "Esp."));
    if (skill.interaction) h.bindInteraction(trigger, skill.interaction);
    else trigger.disabled = true;
    return trigger;
  }

  function openMonsterSkillsModal(section, children, rc) {
    h.closeFloatingSheetMenus();
    const root = section.closest("[data-actor-sheet-root]");
    if (!root) return;
    const skills = monsterSkillRows(children, rc.ctx);
    const overlay = h.el("div", "gw-roll-modal gw-skills-modal");
    const dialog = h.el("div", "gw-roll-dialog gw-skills-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.appendChild(h.el("div", "gw-roll-dialog__title", "Perícias do Monstro"));

    const grid = h.el("div", "gw-skills-grid");
    skills.forEach((skill) => {
      const row = h.el("div", "gw-skill-option");
      row.dataset.skillKey = skill.key;
      const label = h.el("div", "gw-skill-option__label");
      label.appendChild(h.el("strong", null, skill.label));
      const meta = h.nonEmptyParts([skill.ability, skill.mod]).join(" · ");
      if (meta) label.appendChild(h.el("span", null, meta));

      const prof = h.el("label", "gw-skill-option__check");
      const profInput = h.el("input", null);
      profInput.type = "checkbox";
      profInput.checked = skill.prof;
      profInput.disabled = !rc.canEdit;
      profInput.dataset.skillProf = "1";
      prof.appendChild(profInput);
      prof.appendChild(h.el("span", null, "Prof."));

      const expert = h.el("label", "gw-skill-option__check");
      const expertInput = h.el("input", null);
      expertInput.type = "checkbox";
      expertInput.checked = skill.expert;
      expertInput.disabled = !rc.canEdit;
      expertInput.dataset.skillExpert = "1";
      expert.appendChild(expertInput);
      expert.appendChild(h.el("span", null, "Esp."));

      row.appendChild(label);
      row.appendChild(prof);
      row.appendChild(expert);
      grid.appendChild(row);
    });
    dialog.appendChild(grid);

    const actions = h.el("div", "gw-roll-dialog__actions");
    const cancel = h.el("button", "gw-roll-dialog__btn", rc.canEdit ? "Cancelar" : "Fechar");
    cancel.type = "button";
    cancel.addEventListener("click", h.closeFloatingSheetMenus);
    actions.appendChild(cancel);
    if (rc.canEdit) {
      const save = h.el("button", "gw-roll-dialog__btn gw-roll-dialog__btn--primary");
      save.type = "button";
      save.appendChild(h.phIcon("check"));
      save.appendChild(h.el("span", null, "Salvar"));
      save.addEventListener("click", async () => {
        const patch = {};
        dialog.querySelectorAll("[data-skill-key]").forEach((row) => {
          const key = row.dataset.skillKey;
          patch[`skills.${key}.prof`] = !!row.querySelector("[data-skill-prof]")?.checked;
          patch[`skills.${key}.expert`] = !!row.querySelector("[data-skill-expert]")?.checked;
        });
        const meta = h.getContext(root);
        if (meta && await h.postJSON("/game/actor/sheet-data/patch", {
          csrf_token: meta.csrf,
          actor_id: meta.actorId,
          patch,
        })) {
          h.closeFloatingSheetMenus();
          h.refresh(root);
        }
      });
      actions.appendChild(save);
    }
    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) h.closeFloatingSheetMenus();
    });
    document.body.appendChild(overlay);
    (dialog.querySelector("input:not(:disabled), button") || dialog).focus();
  }

  function renderMonsterSkillsSection(node, rc) {
    const section = h.el("section", "actor-section actor-section--skills actor-section--monster-skills");
    const title = h.el("h3", "actor-section-title actor-section-title--button");
    const open = h.el("button", "actor-monster-skills-open");
    open.type = "button";
    open.appendChild(h.el("span", null, node.label || "Perícias"));
    open.appendChild(h.phIcon("list-checks", "actor-monster-skills-open__icon"));
    open.addEventListener("click", (event) => {
      event.stopPropagation();
      openMonsterSkillsModal(section, node.children || [], rc);
    });
    title.appendChild(open);
    section.appendChild(title);

    const selected = monsterSkillRows(node.children, rc.ctx).filter((skill) => skill.prof || skill.expert);
    const list = h.el("div", "actor-monster-skills-summary");
    if (selected.length) {
      selected.forEach((skill) => list.appendChild(renderMonsterSkillSummaryRow(skill)));
    } else {
      list.appendChild(h.el("p", "actor-monster-skills-empty", "Nenhuma perícia marcada."));
    }
    section.appendChild(list);
    return section;
  }

  

  function renderMonsterIdentity(main, bundle) {
    const d = bundle.data || {};
    const editable = !!bundle.can_edit;
    const sizes = {
      tiny: "Minúsculo",
      small: "Pequeno",
      medium: "Médio",
      large: "Grande",
      huge: "Enorme",
      gargantuan: "Imenso",
    };
    const sizeOptions = Object.entries(sizes).map(([value, label]) => ({ value, label }));
    const hp = d.hp || {};
    const meta = h.el("div", "ash-meta ash-meta--monster");
    const typeLine = h.el("div", "ash-meta-line");
    typeLine.appendChild(h.phIcon("cube", "ash-meta-icon"));
    typeLine.appendChild(h.headerSelect("sheet.size", d.size, sizeOptions, editable));
    typeLine.appendChild(h.el("span", "ash-meta-sep", "ND"));
    const cr = h.headerInput("sheet.cr", "text", d.cr, editable, "0");
    cr.classList.add("ash-meta-input--lvl");
    typeLine.appendChild(cr);
    typeLine.appendChild(h.el("span", "ash-meta-divider", "·"));
    typeLine.appendChild(h.headerInput("sheet.type", "text", d.type, editable, "Tipo"));
    meta.appendChild(typeLine);

    const detailLine = h.el("div", "ash-meta-line");
    detailLine.appendChild(h.phIcon("footprints", "ash-meta-icon"));
    detailLine.appendChild(h.headerInput("sheet.speed", "text", d.speed, editable, "Deslocamento"));
    detailLine.appendChild(h.el("span", "ash-meta-divider", "·"));
    detailLine.appendChild(h.headerInput("sheet.alignment", "text", d.alignment, editable, "Alinhamento"));
    meta.appendChild(detailLine);
    main.appendChild(meta);

    const ids = h.el("div", "ash-identity ash-identity--monster");
    ids.appendChild(h.headerIdentityCell("ND", h.headerInput("sheet.cr", "text", d.cr, editable, "0"), "challenge"));
    ids.appendChild(h.headerIdentityCell("Prof.", h.headerInput("sheet.prof", "number", d.prof, editable, "2"), "proficiency"));
    ids.appendChild(h.headerIdentityCell("Dados de Vida", h.headerInput("sheet.hp.formula", "text", hp.formula, editable, "—"), "hitdice"));
    main.appendChild(ids);
  }

  function renderCharacterIdentity(main, bundle) {
    const d = bundle.data || {};
    const editable = !!bundle.can_edit;
    const meta = h.el("div", "ash-meta");
    const classLine = h.el("div", "ash-meta-line");
    classLine.appendChild(h.phIcon("graduation-cap", "ash-meta-icon"));
    classLine.appendChild(h.headerInput("sheet.class", "text", d.class, editable, "Classe"));
    classLine.appendChild(h.el("span", "ash-meta-sep", "Nível"));
    const lvl = h.headerInput("sheet.level", "number", d.level, editable, "1");
    lvl.classList.add("ash-meta-input--lvl");
    classLine.appendChild(lvl);
    classLine.appendChild(h.el("span", "ash-meta-divider", "·"));
    classLine.appendChild(h.headerInput("sheet.background", "text", d.background, editable, "Antecedente"));
    meta.appendChild(classLine);

    const raceLine = h.el("div", "ash-meta-line");
    raceLine.appendChild(h.phIcon("person", "ash-meta-icon"));
    raceLine.appendChild(h.headerInput("sheet.race", "text", d.race, editable, "Raça"));
    raceLine.appendChild(h.el("span", "ash-meta-divider", "·"));
    raceLine.appendChild(h.headerInput("sheet.alignment", "text", d.alignment, editable, "Alinhamento"));
    meta.appendChild(raceLine);
    main.appendChild(meta);

    const ids = h.el("div", "ash-identity");
    ids.appendChild(h.headerIdentityCell("Inspiração", h.headerInput("sheet.inspiration", "number", d.inspiration, editable, "0"), "inspiration"));
    ids.appendChild(h.headerIdentityCell("Bônus de Proficiência", h.el("span", "ash-id-readonly", h.formatMod(d.prof)), "proficiency"));
    ids.appendChild(h.headerIdentityCell("Pontos de Experiência", h.headerInput("sheet.xp", "number", d.xp, editable, "0"), "experience"));
    main.appendChild(ids);
  }

  

  GW.registerSystem("dnd5e", {
    renderSection(node, variant, rc) {
      if (rc.actorType === "monster" && variant === "skills") {
        return renderMonsterSkillsSection(node, rc);
      }
      return null;
    },
    renderHeaderIdentity(main, bundle) {
      const isMonster = bundle.actor && bundle.actor.type === "monster";
      if (isMonster) renderMonsterIdentity(main, bundle);
      else renderCharacterIdentity(main, bundle);
    },
    autoFitWidth(actorType) {
      if (actorType === "monster") return 900;
      if (actorType === "character") return 820;
      return null;
    },
  });
})();
