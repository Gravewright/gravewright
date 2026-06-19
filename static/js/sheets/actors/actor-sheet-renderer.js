











(function () {
  const FI = (window.GravewrightActorSheetInternals = window.GravewrightActorSheetInternals || {});

  const contexts = new WeakMap(); 

  
  
  
  
  
  
  const systemPlugins = {};

  const DEFAULT_SHEET_LABELS = {
    actorName: "Name",
    levelPrefix: "Level",
    equipped: "Equipped",
    spellCirclePrefix: "Circle",
    prepared: "Prepared",
    active: "Active",
    inactive: "Inactive",
    qtyPrefix: "Qty",
    portrait: "Portrait",
    token: "Token",
    uploadPortrait: "Upload portrait",
    uploadToken: "Upload token",
    cancel: "Cancel",
    roll: "Roll",
    rollDialogTitle: "Roll",
    healed: "healed",
    tookDamage: "took",
    reducedFrom: "reduced from",
  };

  function sheetLabels(systemId) {
    const plugin = systemId && systemPlugins[systemId];
    if (plugin && plugin.labels && typeof plugin.labels === "object") {
      return { ...DEFAULT_SHEET_LABELS, ...plugin.labels };
    }
    return DEFAULT_SHEET_LABELS;
  }

  const sheetHelpers = {
    el: (...a) => el(...a),
    phIcon: (...a) => phIcon(...a),
    getPath: (...a) => getPath(...a),
    formatMod: (...a) => formatMod(...a),
    cssIdent: (...a) => cssIdent(...a),
    nonEmptyParts: (...a) => nonEmptyParts(...a),
    normalizeInteraction: (...a) => normalizeInteraction(...a),
    bindInteraction: (...a) => bindInteraction(...a),
    headerInput: (...a) => headerInput(...a),
    headerSelect: (...a) => headerSelect(...a),
    headerIdentityCell: (...a) => headerIdentityCell(...a),
    closeFloatingSheetMenus: (...a) => FI.closeFloatingSheetMenus(...a),
    postJSON: (...a) => postJSON(...a),
    refresh: (...a) => refresh(...a),
    getContext: (root) => contexts.get(root),
    getLabels: (systemId) => sheetLabels(systemId),
  };
  window.GravewrightSheets = {
    helpers: sheetHelpers,
    registerSystem(id, plugin) {
      if (id && plugin && typeof plugin === "object") systemPlugins[String(id)] = plugin;
    },
    getLabels(systemId) { return sheetLabels(systemId); },
  };

  function csrfOf(root) {
    return root.dataset.csrf || window.csrfToken();
  }

  function getPath(ctx, path) {
    let cursor = ctx;
    for (const seg of String(path || "").split(".")) {
      if (cursor && typeof cursor === "object") cursor = cursor[seg];
      else return undefined;
    }
    return cursor;
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    return res.ok ? res.json().catch(() => ({})) : null;
  }

  

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function phIcon(name, className) {
    const i = document.createElement("i");
    i.className = `ph ph-${name}${className ? ` ${className}` : ""}`;
    i.setAttribute("aria-hidden", "true");
    return i;
  }

  function buildChildren(parent, children, rc) {
    (children || []).forEach((child) => {
      const node = buildNode(child, rc);
      if (node) parent.appendChild(node);
    });
  }

  function variantClass(base, variant, extra = "") {
    const suffix = cssIdent(variant);
    return `${base}${suffix ? ` ${base}--${suffix}` : ""}${extra ? ` ${extra}` : ""}`;
  }

  function labelled(labelText, control, variant) {
    const wrap = el("label", variantClass("actor-field", variant));
    wrap.appendChild(el("span", "actor-field-label", labelText || ""));
    wrap.appendChild(control);
    return wrap;
  }

  function cssIdent(value) {
    return String(value || "")
      .trim()
      .replace(/[^a-zA-Z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function formatMod(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return value ?? "—";
    return n > 0 ? `+${n}` : String(n);
  }

  
  
  

  function bindInput(input, path, kind) {
    input.dataset.bindPath = path || "";
    input.dataset.bindKind = kind;
  }

  function normalizeInteraction(interaction, fallbackAction, fallbackLabel) {
    if (interaction && typeof interaction === "object") return interaction;
    if (fallbackAction) return {
      type: "action",
      action: fallbackAction,
      title: fallbackLabel || "Action",
      label: fallbackLabel || "Roll",
    };
    return null;
  }

  function bindInteraction(node, interaction, context) {
    if (!interaction) return;
    node.dataset.interaction = JSON.stringify(interaction);
    if (context?.itemId) node.dataset.itemId = context.itemId;
  }

  function itemTemplateValue(item, value, fallbackPath = "") {
    if (typeof value === "string" && value) {
      if (value.startsWith("@item.")) return getPath(item, value.slice("@item.".length));
      if (value.startsWith("item.")) return getPath(item, value.slice("item.".length));
      return getPath(item, value) ?? value;
    }
    if (fallbackPath) return getPath(item, fallbackPath);
    return undefined;
  }

  function nonEmptyParts(parts) {
    return parts.map((part) => part == null || part === "" ? "" : String(part)).filter(Boolean);
  }

  function setRollDialogDataset(btn, dialog) {
    if (!dialog) return;
    btn.dataset.rollDialog = "1";
    if (dialog && typeof dialog === "object") btn.dataset.rollDialogSchema = JSON.stringify(dialog);
  }

  function buildItemActionButton(action, item, editable) {
    const btn = el("button", "actor-item-action-btn", action.label || "•");
    btn.type = "button";
    btn.disabled = !editable || !item?.id;
    btn.dataset.itemId = item?.id || "";
    setRollDialogDataset(btn, action.dialog);
    if (action.type === "itemAction") {
      btn.dataset.itemAction = action.action || "";
    } else if (action.type === "removeAction") {
      btn.dataset.itemRemove = "1";
    } else if (action.type === "openEmbeddedItemAction") {
      btn.dataset.itemEdit = "1";
      
      
      
      
      btn.disabled = true;
    }
    return btn;
  }

  function buildItemActions(rowActions, item, editable) {
    const actions = el("div", "actor-item-row-actions");
    (rowActions || []).forEach((action) => {
      if (!action || typeof action !== "object") return;
      actions.appendChild(buildItemActionButton(action, item, editable));
    });
    return actions;
  }

  function itemRowIcon(type) {
    return {
      weaponRow: "sword",
      spellRow: "magic-wand",
      featureRow: "sparkle",
      inventoryRow: "backpack",
      effectRow: "circles-three",
    }[type] || "diamond";
  }

  function buildItemRow(row, item, editable, rc) {
    const L = sheetLabels(rc?.systemId);
    const rowType = cssIdent(row?.type || "inventoryRow");
    const card = el("article", `actor-item-row actor-item-row--${rowType}`);
    if (item?.id) card.dataset.itemInstanceId = item.id;

    card.appendChild(phIcon(itemRowIcon(String(row?.type || "inventoryRow")), "actor-item-row-icon"));
    const main = el("div", "actor-item-row-main");
    const title = itemTemplateValue(item, row?.title, "name") || "Item";
    main.appendChild(el("strong", "actor-item-row-title", title));

    const type = String(row?.type || "inventoryRow");
    let metaParts = [];
    if (type === "weaponRow") {
      metaParts = nonEmptyParts([
        itemTemplateValue(item, row?.attackLabel, "data.attackBonus"),
        itemTemplateValue(item, row?.damageLabel, "data.damage"),
        itemTemplateValue(item, row?.damageTypeLabel, "data.damage_type") || itemTemplateValue(item, row?.damageTypeLabel, "data.damageType"),
        item?.equipped ? L.equipped : "",
      ]);
    } else if (type === "spellRow") {
      const level = itemTemplateValue(item, row?.levelPath, "level") ?? itemTemplateValue(item, row?.levelPath, "data.level");
      metaParts = nonEmptyParts([
        level !== undefined && level !== "" ? `${L.spellCirclePrefix} ${level}` : "",
        itemTemplateValue(item, row?.schoolPath, "school") || itemTemplateValue(item, row?.schoolPath, "data.school"),
        item?.prepared ? L.prepared : "",
      ]);
    } else if (type === "featureRow") {
      metaParts = nonEmptyParts([
        itemTemplateValue(item, row?.sourcePath, "data.source"),
        itemTemplateValue(item, row?.usesPath, "data.uses"),
        itemTemplateValue(item, row?.typePath, "type"),
      ]);
    } else if (type === "effectRow") {
      const remaining = itemTemplateValue(item, row?.durationPath, "duration.remaining");
      const duration = remaining !== undefined && remaining !== "" ? `${remaining}r` : itemTemplateValue(item, row?.durationLabel, "duration.type");
      metaParts = nonEmptyParts([
        itemTemplateValue(item, row?.categoryPath, "data.category"),
        duration,
        item?.enabled === false ? L.inactive : L.active,
      ]);
    } else {
      const qty = itemTemplateValue(item, row?.quantityPath, "quantity");
      metaParts = nonEmptyParts([
        qty ? `${L.qtyPrefix} ${qty}` : "",
        itemTemplateValue(item, row?.typePath, "type"),
        itemTemplateValue(item, row?.damageLabel, "data.damage"),
        item?.equipped ? L.equipped : "",
      ]);
    }

    const customSubtitle = itemTemplateValue(item, row?.subtitle);
    const subtitle = customSubtitle || metaParts.join(" · ");
    if (subtitle) main.appendChild(el("span", "actor-item-row-subtitle", subtitle));

    card.appendChild(main);
    const actions = buildItemActions(row?.actions, item, editable);
    if (actions.childElementCount) card.appendChild(actions);
    return card;
  }

  function isSpecializedItemRow(row) {
    return ["weaponRow", "spellRow", "featureRow", "inventoryRow", "effectRow"].includes(String(row?.type || ""));
  }

  function buildNode(node, rc) {
    if (!node || typeof node !== "object") return null;
    const ctx = rc.ctx;
    const editable = rc.canEdit;

    switch (node.type) {
      case "tabs": {
        const container = el("div", "actor-tabs");
        const bar = el("div", "actor-tab-bar");
        const panels = el("div", "actor-tab-panels");
        (node.tabs || []).forEach((tab, index) => {
          const tabId = cssIdent(tab.id);
          const tabLabel = tab.label || tab.id || `Tab ${index + 1}`;
          const btn = el("button", `actor-tab-btn${tabId ? ` actor-tab-btn--${tabId}` : ""}`);
          if (tab.icon) btn.appendChild(phIcon(tab.icon, "actor-tab-icon"));
          btn.appendChild(el("span", "actor-tab-label", tabLabel));
          btn.type = "button";
          btn.title = tabLabel;
          btn.setAttribute("aria-label", tabLabel);
          const panel = el("div", `actor-tab-panel${tabId ? ` actor-tab-panel--${tabId}` : ""}`);
          if (index !== 0) panel.hidden = true;
          else btn.classList.add("is-active");
          buildChildren(panel, tab.children, rc);
          btn.addEventListener("click", () => {
            bar.querySelectorAll(".actor-tab-btn").forEach((b) => b.classList.remove("is-active"));
            panels.querySelectorAll(".actor-tab-panel").forEach((p) => (p.hidden = true));
            btn.classList.add("is-active");
            panel.hidden = false;
            document.dispatchEvent(new CustomEvent("vtt:modal-content-updated", {
              detail: { modal: container.closest("[data-modal-window]") },
            }));
          });
          bar.appendChild(btn);
          panels.appendChild(panel);
        });
        container.appendChild(bar);
        container.appendChild(panels);
        return container;
      }
      case "section": {
        const variant = cssIdent(node.variant);
        const sectionPlugin = systemPlugins[rc.systemId];
        if (sectionPlugin && typeof sectionPlugin.renderSection === "function") {
          const custom = sectionPlugin.renderSection(node, variant, rc, sheetHelpers);
          if (custom) return custom;
        }
        const section = el("section", `actor-section${variant ? ` actor-section--${variant}` : ""}`);
        if (node.label) section.appendChild(el("h3", "actor-section-title", node.label));
        buildChildren(section, node.children, rc);
        return section;
      }
      case "row": {
        const variant = cssIdent(node.variant);
        const row = el("div", `actor-row${variant ? ` actor-row--${variant}` : ""}`);
        buildChildren(row, node.children, rc);
        return row;
      }
      case "grid": {
        const variant = cssIdent(node.variant);
        const grid = el("div", `actor-grid${variant ? ` actor-grid--${variant}` : ""}`);
        if (node.columns) grid.style.setProperty("--gw-grid-columns", String(node.columns));
        buildChildren(grid, node.children, rc);
        return grid;
      }
      case "column": {
        const variant = cssIdent(node.variant);
        const col = el("div", `actor-column${variant ? ` actor-column--${variant}` : ""}`);
        buildChildren(col, node.children, rc);
        return col;
      }
      case "divider":
        return el("hr", "actor-divider");
      case "spacer":
        return el("div", "actor-spacer");

      case "abilityCard": {
        const variant = cssIdent(node.variant);
        const card = el("div", `actor-ability-card${variant ? ` actor-ability-card--${variant}` : ""}`);
        if (node.abbr) card.appendChild(el("span", "actor-ability-card-abbr", node.abbr));
        card.appendChild(el("span", "actor-ability-card-label", node.label || ""));

        const score = el("input", "actor-ability-card-score");
        score.type = "number";
        score.value = getPath(ctx, node.scorePath) ?? 0;
        score.disabled = !editable;
        bindInput(score, node.scorePath, "number");
        card.appendChild(score);

        const modText = formatMod(getPath(ctx, node.modPath));
        const interaction = normalizeInteraction(node.interaction, node.rollAction, node.rollLabel || node.label);
        if (interaction) {
          const mod = el("button", "actor-ability-card-mod actor-ability-card-roll", modText);
          mod.type = "button";
          mod.title = interaction.title || node.rollLabel || "Actions";
          bindInteraction(mod, interaction);
          card.appendChild(mod);
        } else {
          card.appendChild(el("span", "actor-ability-card-mod", modText));
        }
        return card;
      }

      case "rollableStat": {
        
        
        
        
        const variant = cssIdent(node.variant);
        const row = el("div", `actor-rollable-row${variant ? ` actor-rollable-row--${variant}` : ""}`);

        const toggle = (path, cls, title) => {
          const input = el("input", `actor-prof-dot ${cls}`);
          input.type = "checkbox";
          input.checked = !!getPath(ctx, path);
          input.disabled = !editable;
          input.title = title;
          bindInput(input, path, "bool");
          return input;
        };
        if (node.profPath || node.expertPath) {
          const dots = el("div", "actor-rollable-toggles");
          if (node.profPath) dots.appendChild(toggle(node.profPath, "actor-prof-dot--prof", "Proficiency"));
          if (node.expertPath) dots.appendChild(toggle(node.expertPath, "actor-prof-dot--expert", "Expertise"));
          row.appendChild(dots);
        }

        const interaction = normalizeInteraction(node.interaction, node.rollAction, node.rollLabel || node.label);
        const trigger = el("button", "actor-rollable");
        trigger.type = "button";
        trigger.title = (interaction && (interaction.title || node.rollLabel)) || `Roll ${node.label || ""}`.trim();
        if (interaction) bindInteraction(trigger, interaction);
        else trigger.disabled = true;

        if (node.icon) trigger.appendChild(phIcon(node.icon, "actor-rollable-icon"));
        trigger.appendChild(el("span", "actor-rollable-name", node.label || ""));
        if (node.ability) trigger.appendChild(el("span", "actor-rollable-ability", node.ability));

        const hasMod = node.modPath != null;
        if (hasMod) {
          trigger.appendChild(el("span", "actor-rollable-mod", formatMod(getPath(ctx, node.modPath))));
        }
        if (variant === "action") trigger.appendChild(phIcon("dice-five", "actor-rollable-die"));
        row.appendChild(trigger);
        return row;
      }

      case "combatStat": {
        const variant = cssIdent(node.variant);
        const stat = el("div", `actor-combat-stat${variant ? ` actor-combat-stat--${variant}` : ""}`);
        if (node.icon) stat.appendChild(phIcon(node.icon, "actor-combat-stat-icon"));
        stat.appendChild(el("span", "actor-combat-stat-abbr", node.abbr || node.label || ""));
        if (node.label && node.abbr) stat.appendChild(el("span", "actor-combat-stat-label", node.label));
        const raw = getPath(ctx, node.valuePath);
        const valueText = node.signed ? formatMod(raw) : (raw ?? "—");
        const interaction = normalizeInteraction(node.interaction, node.rollAction, node.rollLabel || node.label);
        if (interaction) {
          const btn = el("button", "actor-combat-stat-value actor-combat-stat-roll", valueText);
          btn.type = "button";
          btn.title = interaction.title || node.rollLabel || "Actions";
          bindInteraction(btn, interaction);
          stat.appendChild(btn);
        } else if (node.readonly) {
          stat.appendChild(el("span", "actor-combat-stat-value actor-combat-stat-value--readonly", valueText));
        } else {
          const kind = node.kind === "text" ? "text" : "number";
          const input = el("input", "actor-combat-stat-value");
          input.type = kind === "text" ? "text" : "number";
          input.value = raw ?? (kind === "text" ? "" : 0);
          input.disabled = !editable;
          bindInput(input, node.valuePath, kind);
          stat.appendChild(input);
        }
        return stat;
      }

      case "resourceBox": {
        const variant = cssIdent(node.variant);
        const box = el("div", `actor-resource-box${variant ? ` actor-resource-box--${variant}` : ""}`);
        const boxHead = el("div", "actor-resource-box-head");
        if (node.icon) boxHead.appendChild(phIcon(node.icon, "actor-resource-box-icon"));
        boxHead.appendChild(el("span", "actor-resource-box-label", node.label || ""));
        box.appendChild(boxHead);
        const values = el("div", "actor-resource-box-values");
        const value = el("input", "actor-resource-box-value");
        value.type = "number";
        value.value = getPath(ctx, node.valuePath) ?? 0;
        value.disabled = !editable;
        bindInput(value, node.valuePath, "number");
        const sep = el("span", "actor-resource-box-sep", "/");
        const max = el("input", "actor-resource-box-max");
        max.type = "number";
        max.value = getPath(ctx, node.maxPath) ?? 0;
        max.disabled = !editable;
        bindInput(max, node.maxPath, "number");
        values.appendChild(value);
        values.appendChild(sep);
        values.appendChild(max);
        box.appendChild(values);
        box.appendChild(buildBar(getPath(ctx, node.valuePath), getPath(ctx, node.maxPath)));
        if (node.controls !== false) {
          const controls = el("div", "actor-resource-box-controls");
          const minus = el("button", "actor-resource-box-step", "−");
          minus.type = "button";
          minus.dataset.stepPath = node.valuePath || "";
          minus.dataset.stepBy = "-1";
          minus.disabled = !editable;
          const plus = el("button", "actor-resource-box-step", "+");
          plus.type = "button";
          plus.dataset.stepPath = node.valuePath || "";
          plus.dataset.stepBy = "1";
          plus.disabled = !editable;
          controls.appendChild(minus);
          controls.appendChild(plus);
          box.appendChild(controls);
        }
        return box;
      }

      case "textField":
      case "numberField": {
        const input = el("input", "actor-input");
        input.type = node.type === "numberField" ? "number" : "text";
        input.value = getPath(ctx, node.path) ?? "";
        input.disabled = !editable;
        bindInput(input, node.path, node.type === "numberField" ? "number" : "text");
        return labelled(node.label, input, node.variant);
      }
      case "textArea": {
        const input = el("textarea", "actor-input actor-textarea");
        input.value = getPath(ctx, node.path) ?? "";
        input.disabled = !editable;
        bindInput(input, node.path, "text");
        return labelled(node.label, input, node.variant);
      }
      case "checkboxField": {
        const input = el("input", "actor-checkbox");
        input.type = "checkbox";
        input.checked = !!getPath(ctx, node.path);
        input.disabled = !editable;
        bindInput(input, node.path, "bool");
        const wrap = el("label", variantClass("actor-field", node.variant, "actor-field--check"));
        wrap.appendChild(input);
        wrap.appendChild(el("span", "actor-field-label", node.label || ""));
        return wrap;
      }
      case "checkboxTrack": {
        const current = Math.max(0, Number(getPath(ctx, node.path)) || 0);
        const max = Math.max(1, Number(node.max) || 3);
        const wrap = el("div", variantClass("actor-field", node.variant, "actor-field--check-track"));
        wrap.appendChild(el("span", "actor-field-label", node.label || ""));
        const track = el("div", "actor-check-track");
        track.dataset.checkTrackPath = node.path || "";
        for (let index = 1; index <= max; index += 1) {
          const label = el("label", "actor-check-track__box");
          const input = el("input", null);
          input.type = "checkbox";
          input.checked = index <= current;
          input.disabled = !editable;
          input.dataset.checkTrackValue = String(index);
          label.appendChild(input);
          label.appendChild(el("span", null, String(index)));
          track.appendChild(label);
        }
        wrap.appendChild(track);
        return wrap;
      }
      case "selectField": {
        const select = el("select", "actor-input");
        (node.options || []).forEach((opt) => {
          const value = typeof opt === "object" ? opt.value : opt;
          const text = typeof opt === "object" ? opt.label || opt.value : opt;
          const o = el("option", null, text);
          o.value = value;
          select.appendChild(o);
        });
        select.value = getPath(ctx, node.path) ?? "";
        select.disabled = !editable;
        bindInput(select, node.path, "text");
        return labelled(node.label, select, node.variant);
      }
      case "resourceField": {
        const wrap = el("div", variantClass("actor-field", node.variant, "actor-resource"));
        wrap.appendChild(el("span", "actor-field-label", node.label || ""));
        const pair = el("div", "actor-resource-pair");
        const value = el("input", "actor-input actor-resource-value");
        value.type = "number";
        value.value = getPath(ctx, node.valuePath) ?? 0;
        value.disabled = !editable;
        bindInput(value, node.valuePath, "number");
        const sep = el("span", "actor-resource-sep", "/");
        const max = el("input", "actor-input actor-resource-max");
        max.type = "number";
        max.value = getPath(ctx, node.maxPath) ?? 0;
        max.disabled = !editable;
        bindInput(max, node.maxPath, "number");
        pair.appendChild(value);
        pair.appendChild(sep);
        pair.appendChild(max);
        wrap.appendChild(pair);
        wrap.appendChild(buildBar(getPath(ctx, node.valuePath), getPath(ctx, node.maxPath)));
        return wrap;
      }
      case "imageField": {
        const wrap = el("div", variantClass("actor-field", node.variant));
        wrap.appendChild(el("span", "actor-field-label", node.label || ""));
        const src = getPath(ctx, node.path);
        if (src) {
          const img = el("img", "actor-image");
          img.src = src;
          img.alt = node.label || "";
          wrap.appendChild(img);
        }
        return wrap;
      }
      case "readonlyField": {
        const wrap = el("div", variantClass("actor-field", node.variant, "actor-field--readonly"));
        wrap.appendChild(el("span", "actor-field-label", node.label || ""));
        wrap.appendChild(el("span", "actor-readonly-value", getPath(ctx, node.path) ?? "—"));
        return wrap;
      }
      case "text":
        return el("p", "actor-text", node.value ?? getPath(ctx, node.path) ?? "");
      case "badge":
        return el("span", "actor-badge", node.value ?? getPath(ctx, node.path) ?? "");
      case "resourceBar":
        return buildBar(getPath(ctx, node.valuePath), getPath(ctx, node.maxPath));

      case "itemList": {
        const wrap = el("div", variantClass("actor-itemlist", node.variant));
        if (node.label) wrap.appendChild(el("h4", "actor-itemlist-title", node.label));
        const items = getPath(ctx, node.path);
        const rowActions = (node.row && Array.isArray(node.row.actions)) ? node.row.actions : [];
        if (Array.isArray(items) && items.length) {
          if (isSpecializedItemRow(node.row)) {
            const list = el("div", `actor-item-row-list actor-item-row-list--${cssIdent(node.row.type)}`);
            items.forEach((item) => list.appendChild(buildItemRow(node.row, item, editable, rc)));
            wrap.appendChild(list);
          } else {
            const table = el("table", "actor-itemlist-table");
            const head = el("tr");
            (node.columns || []).forEach((c) => head.appendChild(el("th", null, c.label || "")));
            if (rowActions.length) head.appendChild(el("th", "actor-itemlist-actions-head", ""));
            table.appendChild(head);
            items.forEach((item) => {
              const tr = el("tr");
              if (item && item.id) tr.dataset.itemInstanceId = item.id;
              (node.columns || []).forEach((c) => tr.appendChild(el("td", null, getPath(item, c.path) ?? "")));
              if (rowActions.length) {
                const actionsCell = el("td", "actor-itemlist-actions");
                rowActions.forEach((a) => {
                  if (!a || typeof a !== "object") return;
                  actionsCell.appendChild(buildItemActionButton(a, item, editable));
                });
                tr.appendChild(actionsCell);
              }
              table.appendChild(tr);
            });
            wrap.appendChild(table);
          }
        } else {
          wrap.appendChild(el("p", "actor-itemlist-empty", node.emptyText || ""));
        }
        
        
        
        return wrap;
      }
      case "dropZone":
        return null;

      case "rollButton":
      case "actionButton": {
        const btn = el("button", variantClass("actor-action-btn", node.variant, node.type === "rollButton" ? "actor-roll-btn" : ""));
        btn.type = "button";
        btn.textContent = node.label || (node.type === "rollButton" ? "Roll" : "Action");
        btn.dataset.action = node.action || "";
        return btn;
      }
      case "incrementButton":
      case "decrementButton": {
        const btn = el("button", variantClass("actor-step-btn", node.variant));
        btn.type = "button";
        btn.textContent = node.label || (node.type === "incrementButton" ? "+" : "−");
        btn.dataset.stepPath = node.path || "";
        btn.dataset.stepBy = String((node.type === "incrementButton" ? 1 : -1) * (node.step || 1));
        btn.disabled = !editable;
        return btn;
      }
      default:
        return null;
    }
  }

  function buildBar(value, max) {
    const v = Number(value) || 0;
    const m = Number(max) || 0;
    const bar = el("div", "actor-bar");
    const fill = el("div", "actor-bar-fill");
    fill.style.width = m > 0 ? `${Math.max(0, Math.min(100, (v / m) * 100))}%` : "0%";
    bar.appendChild(fill);
    return bar;
  }

  

  function buildContext(bundle) {
    return { core: { name: bundle.actor?.name }, sheet: bundle.data || {} };
  }

  

  async function uploadActorImage(root, kind, file) {
    const meta = contexts.get(root);
    if (!meta || !file) return;
    const form = new FormData();
    form.append("image", file);
    
    const res = await fetch(`/game/actor/${encodeURIComponent(meta.actorId)}/image/${kind}`, {
      method: "POST",
      body: form,
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (res.ok) {
      refresh(root);
    } else if (window.GravewrightToasts) {
      window.GravewrightToasts.showToast("Failed to upload image.");
    }
  }

  function imageFrame(root, kind, url, canEdit, systemId) {
    const L = sheetLabels(systemId);
    const frame = el("div", `ash-frame ash-frame--${kind}${url ? "" : " is-empty"}`);
    if (url) {
      const img = el("img", "ash-frame-img");
      img.src = url;
      img.alt = "";
      frame.appendChild(img);
    } else {
      frame.appendChild(el("span", "ash-frame-placeholder", kind === "portrait" ? L.portrait : L.token));
    }
    if (canEdit) {
      frame.classList.add("is-editable");
      frame.tabIndex = 0;
      frame.setAttribute("role", "button");
      const input = el("input", "ash-frame-input");
      input.type = "file";
      input.accept = "image/png,image/jpeg,image/webp";
      input.hidden = true;
      const trigger = el("button", "ash-frame-upload");
      trigger.type = "button";
      trigger.title = kind === "portrait" ? L.uploadPortrait : L.uploadToken;
      trigger.innerHTML = '<i class="ph ph-upload-simple" aria-hidden="true"></i>';
      trigger.addEventListener("click", () => input.click());
      frame.addEventListener("click", (event) => {
        if (!trigger.contains(event.target) && event.target !== input) input.click();
      });
      frame.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        input.click();
      });
      input.addEventListener("change", () => {
        uploadActorImage(root, kind, input.files && input.files[0]);
        input.value = "";
      });
      frame.appendChild(trigger);
      frame.appendChild(input);
    }
    return frame;
  }

  function headerSubtitle(bundle) {
    const d = bundle.data || {};
    const systemId = cssIdent(bundle.actor?.system_id);
    const L = sheetLabels(systemId);
    const parts = [];
    if (d.race) parts.push(d.race);
    if (d.class) parts.push(d.class);
    if (d.level != null && d.level !== "") parts.push(`${L.levelPrefix} ${d.level}`);
    if (parts.length) return parts.join(" · ");
    return bundle.actor && bundle.actor.type ? bundle.actor.type : "";
  }

  
  
  function headerInput(path, kind, value, editable, placeholder) {
    const input = el("input", "ash-meta-input");
    input.type = kind === "number" ? "number" : "text";
    input.value = value ?? "";
    if (placeholder) input.placeholder = placeholder;
    input.disabled = !editable;
    bindInput(input, path, kind);
    return input;
  }

  function headerDisplay(value, placeholder) {
    const input = el("input", "ash-meta-input");
    input.type = "text";
    input.value = value ?? "";
    if (placeholder) input.placeholder = placeholder;
    input.readOnly = true;
    input.tabIndex = -1;
    return input;
  }

  function headerSelect(path, value, options, editable) {
    const select = el("select", "ash-meta-input");
    (options || []).forEach((opt) => {
      const option = el("option", null, opt.label ?? opt.value);
      option.value = opt.value;
      if (String(value ?? "") === String(opt.value)) option.selected = true;
      select.appendChild(option);
    });
    select.disabled = !editable;
    bindInput(select, path, "text");
    return select;
  }

  function headerIdentityCell(label, valueNode, variant) {
    const cell = el("div", `ash-id-cell${variant ? ` ash-id-cell--${variant}` : ""}`);
    cell.appendChild(el("span", "ash-id-label", label));
    cell.appendChild(valueNode);
    return cell;
  }

  
  
  
  function renderHeaderIdentity(main, bundle) {
    const systemId = cssIdent(bundle.actor?.system_id);
    const plugin = systemPlugins[systemId];
    if (plugin && typeof plugin.renderHeaderIdentity === "function") {
      plugin.renderHeaderIdentity(main, bundle, sheetHelpers);
      return;
    }
    const subtitle = headerSubtitle(bundle);
    if (subtitle) main.appendChild(subtitle);
  }

  function renderSheetHeader(root, bundle, systemId) {
    const canEdit = !!bundle.can_edit;
    const L = sheetLabels(systemId);
    const header = el("div", "actor-sheet-header");

    header.appendChild(imageFrame(root, "portrait", bundle.portrait_url, canEdit, systemId));

    const main = el("div", "ash-main");

    const titleRow = el("div", "ash-title-row");
    const nameInput = el("input", "ash-name-input");
    nameInput.type = "text";
    nameInput.value = (bundle.actor && bundle.actor.name) || "";
    nameInput.placeholder = L.actorName;
    nameInput.dataset.bindPath = "core.name";
    nameInput.dataset.bindKind = "text";
    nameInput.disabled = !canEdit;
    titleRow.appendChild(nameInput);
    titleRow.appendChild(imageFrame(root, "token", bundle.token_url || bundle.portrait_url, canEdit, systemId));
    main.appendChild(titleRow);

    renderHeaderIdentity(main, bundle);

    header.appendChild(main);
    root.appendChild(header);
  }

  function render(root, bundle) {
    const systemId = cssIdent(bundle.actor?.system_id);
    const actorType = cssIdent(bundle.actor?.type);
    [...root.classList].forEach((name) => {
      if (name.startsWith("actor-sheet--")) root.classList.remove(name);
    });
    if (systemId) root.classList.add(`actor-sheet--${systemId}`);
    if (actorType) root.classList.add(`actor-sheet--${actorType}`);

    const modal = root.closest(".actor-sheet-modal");
    if (modal) {
      [...modal.classList].forEach((name) => {
        if (name.startsWith("actor-sheet-modal--")) modal.classList.remove(name);
      });
      if (systemId) modal.classList.add(`actor-sheet-modal--${systemId}`);
      if (actorType) modal.classList.add(`actor-sheet-modal--${actorType}`);
      const widthPlugin = systemPlugins[systemId];
      const fit = widthPlugin && typeof widthPlugin.autoFitWidth === "function" ? widthPlugin.autoFitWidth(actorType) : null;
      if (fit) modal.dataset.autoFitWidth = String(fit);
      else delete modal.dataset.autoFitWidth;
    }


    if (bundle.sheet && bundle.sheet.mode === "html") {
      renderHtmlSheet(root, bundle);
      return;
    }

    const rc = { ctx: buildContext(bundle), canEdit: !!bundle.can_edit, systemId, actorType };
    root.innerHTML = "";
    renderSheetHeader(root, bundle, systemId);
    const layout = bundle.layout;
    if (!layout || !layout.body) {
      root.appendChild(el("p", "actor-sheet-empty", "No sheet layout for this system."));
      return;
    }
    const body = buildNode(layout.body, rc);
    if (body) root.appendChild(body);
  }



  function htmlSheetData(bundle) {
    const data = bundle.data || {};
    return {
      actor: { id: bundle.actor?.id, name: bundle.actor?.name, type: bundle.actor?.type, ...data },
      system: data,
      canEdit: !!bundle.can_edit,
    };
  }



  function writeHtmlSheetPath(root, path, value) {
    const writePath = FI.writePath;
    if (typeof writePath !== "function") return;
    let target = String(path || "");
    if (target === "actor.name" || target === "core.name") target = "core.name";
    else if (target.startsWith("system.")) target = "sheet." + target.slice("system.".length);
    else if (target.startsWith("actor.")) target = "sheet." + target.slice("actor.".length);
    writePath(root, target, value);
  }




  async function renderHtmlSheet(root, bundle) {
    const HTML = window.GravewrightHTMLSheets;
    const packageId = bundle.actor?.system_id || "";
    const sheetType = bundle.actor?.type || "";
    const sheet = bundle.sheet || {};
    if (!HTML || !packageId || !sheet.template) {
      root.innerHTML = "";
      root.appendChild(el("p", "actor-sheet-empty", "No sheet layout for this system."));
      return;
    }

    HTML.unmount(root);
    let html;
    try {
      const url = `/sdk/packages/${encodeURIComponent(packageId)}/asset/${sheet.template}`;
      // The template asset URL has no version query, so never serve a stale
      // cached copy after the package's sheet is regenerated.
      const res = await fetch(url, { credentials: "same-origin", cache: "no-store", headers: { Accept: "text/html" } });
      if (!res.ok) throw new Error(`template ${res.status}`);
      html = await res.text();
    } catch (_err) {
      root.innerHTML = "";
      root.appendChild(el("p", "actor-sheet-empty", "Failed to load sheet template."));
      return;
    }


    root.innerHTML = html;
    HTML.mount(packageId, sheetType, root, htmlSheetData(bundle), {
      onChange: (path, value) => writeHtmlSheetPath(root, path, value),
      // data-action buttons execute the ruleset's own rules/actions entry
      // server-side (e.g. a roll preset), exactly like a declarative sheet.
      onAction: (name) => FI.executeSheetAction?.(root, name),
      onItemChange: async (itemId, path, value) => {
        const meta = contexts.get(root);
        if (!meta || !itemId || !path) return;
        await postJSON("/game/actor/item/patch", {
          csrf_token: meta.csrf,
          actor_id: meta.actorId,
          item_instance_id: itemId,
          patch: { [path]: value },
        });
      },
      onItemAction: (itemId, name) => FI.executeItemAction?.(root, itemId, name),
    });
  }

  async function refresh(root) {
    const meta = contexts.get(root);
    if (!meta) return;
    const bundleUrl = meta.tokenId
      ? `/game/token/${encodeURIComponent(meta.tokenId)}/sheet-bundle`
      : `/game/actor/${encodeURIComponent(meta.actorId)}/sheet-bundle`;
    const res = await fetch(bundleUrl, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return;
    render(root, await res.json());
  }

  FI.contexts = contexts;
  FI.csrfOf = csrfOf;
  FI.getPath = getPath;
  FI.postJSON = postJSON;
  FI.el = el;
  FI.phIcon = phIcon;
  FI.labelled = labelled;
  FI.formatMod = formatMod;
  FI.cssIdent = cssIdent;
  FI.render = render;
  FI.refresh = refresh;
})();
