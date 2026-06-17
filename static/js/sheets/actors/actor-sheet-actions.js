





(function () {
  const FI = (window.GravewrightActorSheetInternals = window.GravewrightActorSheetInternals || {});
  const contexts = FI.contexts;
  const el = FI.el;
  const phIcon = FI.phIcon;
  const labelled = FI.labelled;
  const postJSON = FI.postJSON;

  function closeFloatingSheetMenus() {
    document.querySelectorAll(".gw-action-menu, .gw-roll-modal").forEach((node) => node.remove());
  }

  async function executeSheetAction(root, actionId, options = {}) {
    const meta = contexts.get(root);
    if (!meta || !actionId) return null;
    const body = {
      csrf_token: meta.csrf,
      actor_id: meta.actorId,
      action_id: actionId,
    };
    if (meta.tokenId) body.token_id = meta.tokenId;
    if (options.rollOptions) body.rollOptions = options.rollOptions;
    if (options.targetActorId) body.target_actor_id = options.targetActorId;
    if (options.targetTokenId) body.target_token_id = options.targetTokenId;
    return postJSON("/game/actor/action", body);
  }

  async function executeItemAction(root, itemId, actionId, options = {}) {
    const meta = contexts.get(root);
    if (!meta || !itemId || !actionId) return null;
    const body = {
      csrf_token: meta.csrf,
      actor_id: meta.actorId,
      item_instance_id: itemId,
      action_id: actionId,
    };
    if (meta.tokenId) body.token_id = meta.tokenId;
    if (options.rollOptions) body.rollOptions = options.rollOptions;
    if (options.targetActorId) body.target_actor_id = options.targetActorId;
    if (options.targetTokenId) body.target_token_id = options.targetTokenId;
    return postJSON("/game/actor/item/action", body);
  }

  function positionFloating(node, anchor) {
    const rect = anchor.getBoundingClientRect();
    node.style.left = `${Math.max(8, rect.left)}px`;
    node.style.top = `${Math.max(8, rect.bottom + 6)}px`;
  }

  function openActionMenu(root, anchor, interaction, context = {}) {
    closeFloatingSheetMenus();
    if (!interaction || typeof interaction !== "object") return;
    if (interaction.type === "action") {
      if (interaction.dialog === "roll" || (interaction.dialog && typeof interaction.dialog === "object")) openRollDialog(root, anchor, interaction, context);
      else if (context.itemId) void executeItemAction(root, context.itemId, interaction.action);
      else void executeSheetAction(root, interaction.action);
      return;
    }
    if (interaction.type !== "actionMenu" || !Array.isArray(interaction.items)) return;

    const menu = el("div", "gw-action-menu");
    menu.setAttribute("role", "menu");
    if (interaction.title) menu.appendChild(el("div", "gw-action-menu__title", interaction.title));
    interaction.items.forEach((item) => {
      if (!item || typeof item !== "object") return;
      const btn = el("button", "gw-action-menu__item");
      btn.type = "button";
      if (item.icon) btn.appendChild(el("span", "gw-action-menu__icon", iconText(item.icon)));
      btn.appendChild(el("span", "gw-action-menu__label", item.label || item.action || item.command || "Action"));
      btn.addEventListener("click", () => {
        if (item.dialog === "roll" || (item.dialog && typeof item.dialog === "object")) openRollDialog(root, anchor, item, context);
        else if (item.action && context.itemId) void executeItemAction(root, context.itemId, item.action);
        else if (item.action) void executeSheetAction(root, item.action);
        else closeFloatingSheetMenus();
      });
      menu.appendChild(btn);
    });
    document.body.appendChild(menu);
    positionFloating(menu, anchor);
  }

  function iconText(icon) {
    return { d20: "🎲", dice: "🎲", shield: "🛡", sword: "⚔", edit: "✎" }[String(icon)] || String(icon).slice(0, 2);
  }

  function dialogSchema(item) {
    if (item?.dialog && typeof item.dialog === "object" && Array.isArray(item.dialog.fields)) return item.dialog;
    return {
      type: "roll",
      fields: [
        { id: "mode", type: "segmented", label: "Mode", default: "normal", options: [
          { value: "normal", label: "Normal" },
          { value: "advantage", label: "Advantage" },
          { value: "disadvantage", label: "Disadvantage" },
        ] },
        { id: "extraDice", type: "diceList", label: "Extra Dice", placeholder: "1d6, 1d4" },
        { id: "extraModifier", type: "number", label: "Modifier", default: 0 },
        { id: "visibility", type: "visibility", label: "Visibility", default: "public" },
      ],
    };
  }

  
  
  
  
  function buildSegmented(field) {
    const wrap = el("div", "gw-segmented");
    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.dataset.rollFieldId = field.id;
    hidden.dataset.rollFieldType = "segmented";
    const options = field.options || [];
    const first = typeof options[0] === "object" ? options[0]?.value : options[0];
    hidden.value = field.default ?? first ?? "";
    const optionActions = {};
    options.forEach((opt) => {
      const value = typeof opt === "object" ? opt.value : opt;
      const label = typeof opt === "object" ? (opt.label || opt.value) : opt;
      if (opt && typeof opt === "object" && opt.action) optionActions[value] = opt.action;
      const btn = el("button", "gw-segmented__btn", label);
      btn.type = "button";
      if (String(value) === String(hidden.value)) btn.classList.add("is-active");
      btn.addEventListener("click", () => {
        hidden.value = value;
        wrap.querySelectorAll(".gw-segmented__btn").forEach((b) => b.classList.toggle("is-active", b === btn));
      });
      wrap.appendChild(btn);
    });
    if (Object.keys(optionActions).length) hidden.dataset.optionActions = JSON.stringify(optionActions);
    wrap.appendChild(hidden);
    return wrap;
  }

  function buildRollDialogField(field) {
    const id = String(field?.id || "");
    if (!id) return null;
    const type = String(field.type || "text");
    let control;
    if (type === "segmented" || type === "radio") {
      control = buildSegmented({ ...field, id });
    } else if (type === "select" || type === "visibility") {
      control = el("select", "gw-roll-dialog__input");
      const options = type === "visibility"
        ? (field.options || [{ value: "public", label: "Public" }, { value: "gm", label: "GM" }])
        : (field.options || []);
      options.forEach((opt) => {
        const value = typeof opt === "object" ? opt.value : opt;
        const label = typeof opt === "object" ? opt.label || opt.value : opt;
        const node = el("option", null, label);
        node.value = value;
        control.appendChild(node);
      });
      control.value = field.default ?? (control.options[0]?.value || "");
    } else if (type === "boolean") {
      control = el("input", "gw-roll-dialog__check");
      control.type = "checkbox";
      control.checked = !!field.default;
    } else {
      control = el("input", "gw-roll-dialog__input");
      control.type = type === "number" ? "number" : "text";
      control.value = field.default ?? "";
      if (field.placeholder) control.placeholder = field.placeholder;
    }
    
    if (type !== "segmented" && type !== "radio") {
      control.dataset.rollFieldId = id;
      control.dataset.rollFieldType = type;
    }
    return labelled(field.label || id, control);
  }

  function collectRollOptions(dialog) {
    const rollOptions = {};
    dialog.querySelectorAll("[data-roll-field-id]").forEach((field) => {
      const id = field.dataset.rollFieldId;
      const type = field.dataset.rollFieldType;
      if (type === "boolean") rollOptions[id] = !!field.checked;
      else if (type === "number") rollOptions[id] = Number(field.value || 0);
      else if (type === "diceList") rollOptions[id] = field.value.split(/[,+ ]+/).map((x) => x.trim()).filter(Boolean);
      else rollOptions[id] = field.value;
    });
    return rollOptions;
  }

  
  
  function resolveDialogAction(dialog, schema, fallback) {
    if (!schema?.actionField) return fallback;
    const field = dialog.querySelector(`[data-roll-field-id="${CSS.escape(String(schema.actionField))}"]`);
    if (!field || !field.dataset.optionActions) return fallback;
    try {
      const map = JSON.parse(field.dataset.optionActions);
      return map[field.value] || fallback;
    } catch {
      return fallback;
    }
  }

  
  
  
  function damageTargets(root) {
    const out = [];
    const seenActors = new Set();
    const meta = contexts.get(root) || {};
    const roomTokens = window.GravewrightStatusZones?.tokensForRoom?.(meta.roomId) || [];
    roomTokens.forEach((token) => {
      if (!token?.token_id || !token.actor_id) return;
      if (token.hidden) return;
      const card = document.querySelector(`[data-actor-card="${CSS.escape(token.actor_id)}"]`);
      const canEdit = card?.dataset.canEdit === "true" || document.querySelector(`[data-map-canvas][data-room-id="${CSS.escape(meta.roomId || "")}"]`)?.dataset.isGm === "true";
      if (!canEdit) return;
      out.push({ tokenId: token.token_id, actorId: token.actor_id, name: token.name || token.actor_id });
      seenActors.add(token.actor_id);
    });
    document.querySelectorAll('[data-actor-card][data-can-edit="true"]').forEach((card) => {
      const id = card.getAttribute("data-actor-card");
      if (!id || seenActors.has(id)) return;
      const name = (card.querySelector(".actor-card-info strong")?.textContent || id || "").trim();
      out.push({ actorId: id, name });
    });
    return out;
  }

  
  function buildTargetField(root, schema) {
    if (!schema || schema.intent !== "damage") return null;
    const targets = damageTargets(root);
    if (!targets.length) return null;
    const wrap = el("label", "gw-roll-dialog__field");
    wrap.appendChild(el("span", "gw-roll-dialog__label", "Target"));
    const select = el("select", "gw-roll-dialog__input");
    select.dataset.rollTarget = "1";
    select.appendChild(el("option", null, "No target (roll only)")).value = "";
    targets.forEach((target) => {
      const option = el("option", null, target.name);
      option.value = target.tokenId || target.actorId || "";
      if (target.tokenId) option.dataset.targetTokenId = target.tokenId;
      if (target.actorId) option.dataset.targetActorId = target.actorId;
      select.appendChild(option);
    });
    wrap.appendChild(select);
    return wrap;
  }

  function toastApplied(applied, systemId) {
    if (!applied || !window.GravewrightToasts) return;
    const L = window.GravewrightSheets?.getLabels?.(systemId) || {};
    const verb = applied.mode === "heal" ? (L.healed || "healed") : (L.tookDamage || "took");
    const type = applied.damageType ? ` ${applied.damageType}` : "";
    let msg = `${applied.targetName} ${verb} ${applied.amount}${type} (HP ${applied.valueAfter})`;
    if (applied.mode !== "heal" && applied.rawAmount != null && applied.rawAmount !== applied.amount) {
      msg += ` — ${L.reducedFrom || "reduced from"} ${applied.rawAmount}`;
    }
    window.GravewrightToasts.showToast(msg, { duration: 5000 });
  }

  function openRollDialog(root, anchor, item, context = {}) {
    closeFloatingSheetMenus();
    if (!item?.action) return;
    const schema = dialogSchema(item);
    const overlay = el("div", "gw-roll-modal");
    const dialog = el("div", "gw-roll-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.appendChild(el("div", "gw-roll-dialog__title", schema.title || item.title || item.label || "Roll"));

    (schema.fields || []).forEach((field) => {
      if (field?.type === "hint") {
        dialog.appendChild(el("p", "gw-roll-dialog__hint", field.text || field.label || ""));
        return;
      }
      if (field?.type === "separator") {
        dialog.appendChild(el("hr", "gw-roll-dialog__separator"));
        return;
      }
      const node = buildRollDialogField(field);
      if (node) dialog.appendChild(node);
    });

    const targetField = buildTargetField(root, schema);
    if (targetField) dialog.appendChild(targetField);

    const actions = el("div", "gw-roll-dialog__actions");
    const cancel = el("button", "gw-roll-dialog__btn", "Cancel");
    cancel.type = "button";
    cancel.addEventListener("click", closeFloatingSheetMenus);
    const roll = el("button", "gw-roll-dialog__btn gw-roll-dialog__btn--primary");
    roll.type = "button";
    roll.appendChild(phIcon("dice-five"));
    roll.appendChild(el("span", null, "Roll"));
    roll.addEventListener("click", async () => {
      const rollOptions = collectRollOptions(dialog);
      const action = resolveDialogAction(dialog, schema, item.action);
      const targetSelect = dialog.querySelector("[data-roll-target]");
      const targetOption = targetSelect?.selectedOptions?.[0];
      const options = { rollOptions };
      if (targetOption?.dataset.targetTokenId) options.targetTokenId = targetOption.dataset.targetTokenId;
      else if (targetOption?.dataset.targetActorId) options.targetActorId = targetOption.dataset.targetActorId;
      const meta = contexts.get(root) || {};
      const result = context.itemId
        ? await executeItemAction(root, context.itemId, action, options)
        : await executeSheetAction(root, action, options);
      if (result?.applied) toastApplied(result.applied, meta.systemId);
      closeFloatingSheetMenus();
    });
    actions.appendChild(cancel);
    actions.appendChild(roll);
    dialog.appendChild(actions);

    overlay.appendChild(dialog);
    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) closeFloatingSheetMenus();
    });
    document.body.appendChild(overlay);
    (dialog.querySelector(".gw-segmented__btn, input, select, button") || roll).focus();
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeFloatingSheetMenus();
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest(".gw-action-menu, .gw-roll-dialog, [data-interaction]")) return;
    closeFloatingSheetMenus();
  });

  FI.closeFloatingSheetMenus = closeFloatingSheetMenus;
  FI.executeSheetAction = executeSheetAction;
  FI.executeItemAction = executeItemAction;
  FI.openActionMenu = openActionMenu;
  FI.openRollDialog = openRollDialog;
})();
