





(function () {
  const FI = (window.GravewrightItemSheetInternals = window.GravewrightItemSheetInternals || {});

  const contexts = new WeakMap(); 

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

  function buildChildren(parent, children, rc) {
    (children || []).forEach((child) => {
      const node = buildNode(child, rc);
      if (node) parent.appendChild(node);
    });
  }

  function labelled(labelText, control) {
    const wrap = el("label", "actor-field");
    wrap.appendChild(el("span", "actor-field-label", labelText || ""));
    wrap.appendChild(control);
    return wrap;
  }

  function bindInput(input, path, kind) {
    input.dataset.bindPath = path || "";
    input.dataset.bindKind = kind;
  }


  function modifierTargets(node) {
    return Array.isArray(node.targets) ? node.targets.filter((target) => target && typeof target === "object") : [];
  }

  function modifierTargetById(targets, id) {
    return targets.find((target) => target.id === id) || targets[0] || null;
  }

  function modifierOperationById(target, id) {
    const operations = Array.isArray(target?.operations) ? target.operations : [];
    return operations.find((operation) => operation.id === id) || operations[0] || null;
  }

  function modifierValueType(operation) {
    return operation?.valueType || (operation?.id === "add_dice" ? "dice" : "number");
  }

  function buildOptions(select, options, value) {
    options.forEach((opt) => {
      const option = el("option", null, opt.label || opt.id || opt.value || "");
      option.value = opt.id || opt.value || "";
      select.appendChild(option);
    });
    select.value = value || options[0]?.id || options[0]?.value || "";
  }

  function buildModifierBuilder(node, rc) {
    const targets = modifierTargets(node);
    const path = node.path || "sheet.modifiers";
    const list = getPath(rc.ctx, path);
    const modifiers = Array.isArray(list) ? list : [];
    const wrap = el("section", "gw-modifier-builder");
    wrap.dataset.modifierBuilder = "1";
    wrap.dataset.modifierPath = path;
    wrap.dataset.targets = JSON.stringify(targets);
    if (node.label) wrap.appendChild(el("h4", "gw-modifier-builder__title", node.label));

    const body = el("div", "gw-modifier-builder__rows");
    modifiers.forEach((modifier, index) => {
      const row = el("div", "gw-modifier-row");
      row.dataset.index = String(index);

      const target = modifierTargetById(targets, modifier?.target);
      const operation = modifierOperationById(target, modifier?.operation);

      const targetSelect = el("select", "actor-input gw-modifier-row__target");
      targetSelect.disabled = !rc.canEdit;
      targetSelect.dataset.modifierField = "target";
      buildOptions(targetSelect, targets, modifier?.target);
      row.appendChild(targetSelect);

      const operations = Array.isArray(target?.operations) ? target.operations : [];
      const opSelect = el("select", "actor-input gw-modifier-row__operation");
      opSelect.disabled = !rc.canEdit;
      opSelect.dataset.modifierField = "operation";
      buildOptions(opSelect, operations, modifier?.operation);
      row.appendChild(opSelect);

      const valueType = modifierValueType(operation);
      const value = el("input", "actor-input gw-modifier-row__value");
      value.dataset.modifierField = "value";
      value.disabled = !rc.canEdit || valueType === "none";
      value.placeholder = valueType === "none" ? "—" : valueType;
      value.type = valueType === "number" ? "number" : "text";
      value.value = modifier?.value ?? "";
      row.appendChild(value);

      const label = el("input", "actor-input gw-modifier-row__label");
      label.dataset.modifierField = "label";
      label.disabled = !rc.canEdit;
      label.placeholder = "Label";
      label.value = modifier?.label ?? "";
      row.appendChild(label);

      const remove = el("button", "gw-modifier-row__remove", "remove");
      remove.type = "button";
      remove.disabled = !rc.canEdit;
      remove.dataset.modifierAction = "remove";
      row.appendChild(remove);

      body.appendChild(row);
    });
    wrap.appendChild(body);

    const add = el("button", "gw-modifier-builder__add", "+ Add modifier");
    add.type = "button";
    add.disabled = !rc.canEdit || !targets.length;
    add.dataset.modifierAction = "add";
    wrap.appendChild(add);

    if (!modifiers.length) wrap.appendChild(el("p", "gw-modifier-builder__empty", "No active modifiers."));
    return wrap;
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
          const tabLabel = tab.label || tab.id || `Tab ${index + 1}`;
          const btn = el("button", "actor-tab-btn", tabLabel);
          btn.type = "button";
          btn.title = tabLabel;
          btn.setAttribute("aria-label", tabLabel);
          const panel = el("div", "actor-tab-panel");
          if (index !== 0) panel.hidden = true;
          else btn.classList.add("is-active");
          buildChildren(panel, tab.children, rc);
          btn.addEventListener("click", () => {
            bar.querySelectorAll(".actor-tab-btn").forEach((b) => b.classList.remove("is-active"));
            panels.querySelectorAll(".actor-tab-panel").forEach((p) => (p.hidden = true));
            btn.classList.add("is-active");
            panel.hidden = false;
          });
          bar.appendChild(btn);
          panels.appendChild(panel);
        });
        container.appendChild(bar);
        container.appendChild(panels);
        return container;
      }
      case "section": {
        const section = el("section", "actor-section");
        if (node.label) section.appendChild(el("h3", "actor-section-title", node.label));
        buildChildren(section, node.children, rc);
        return section;
      }
      case "row": {
        const row = el("div", "actor-row");
        buildChildren(row, node.children, rc);
        return row;
      }
      case "column": {
        const col = el("div", "actor-column");
        buildChildren(col, node.children, rc);
        return col;
      }
      case "divider":
        return el("hr", "actor-divider");
      case "spacer":
        return el("div", "actor-spacer");

      case "textField":
      case "numberField": {
        const input = el("input", "actor-input");
        input.type = node.type === "numberField" ? "number" : "text";
        input.value = getPath(ctx, node.path) ?? "";
        input.disabled = !editable;
        bindInput(input, node.path, node.type === "numberField" ? "number" : "text");
        return labelled(node.label, input);
      }
      case "textArea": {
        const input = el("textarea", "actor-input actor-textarea");
        input.value = getPath(ctx, node.path) ?? "";
        input.disabled = !editable;
        bindInput(input, node.path, "text");
        return labelled(node.label, input);
      }
      case "checkboxField": {
        const input = el("input", "actor-checkbox");
        input.type = "checkbox";
        input.checked = !!getPath(ctx, node.path);
        input.disabled = !editable;
        bindInput(input, node.path, "bool");
        const wrap = el("label", "actor-field actor-field--check");
        wrap.appendChild(input);
        wrap.appendChild(el("span", "actor-field-label", node.label || ""));
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
        return labelled(node.label, select);
      }
      case "resourceField": {
        const wrap = el("div", "actor-field actor-resource");
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
        const wrap = el("div", "actor-field");
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
        const wrap = el("div", "actor-field actor-field--readonly");
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
      case "modifierBuilder":
        return buildModifierBuilder(node, rc);


      case "itemList": {
        const wrap = el("div", "actor-itemlist");
        if (node.label) wrap.appendChild(el("h4", "actor-itemlist-title", node.label));
        const items = getPath(ctx, node.path);
        if (Array.isArray(items) && items.length) {
          const table = el("table", "actor-itemlist-table");
          const head = el("tr");
          (node.columns || []).forEach((c) => head.appendChild(el("th", null, c.label || "")));
          table.appendChild(head);
          items.forEach((item) => {
            const tr = el("tr");
            (node.columns || []).forEach((c) => tr.appendChild(el("td", null, getPath(item, c.path) ?? "")));
            table.appendChild(tr);
          });
          wrap.appendChild(table);
        } else {
          wrap.appendChild(el("p", "actor-itemlist-empty", node.emptyText || ""));
        }
        return wrap;
      }

      case "rollButton":
      case "actionButton": {
        const btn = el("button", "actor-action-btn" + (node.type === "rollButton" ? " actor-roll-btn" : ""));
        btn.type = "button";
        btn.textContent = node.label || (node.type === "rollButton" ? "Roll" : "Action");
        btn.dataset.action = node.action || "";
        return btn;
      }
      case "incrementButton":
      case "decrementButton": {
        const btn = el("button", "actor-step-btn");
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
    return { core: { name: bundle.item?.name }, sheet: bundle.data || {} };
  }

  function render(root, bundle) {
    const rc = { ctx: buildContext(bundle), canEdit: !!bundle.can_edit };
    root.innerHTML = "";
    const layout = bundle.layout;
    if (!layout || !layout.body) {
      root.appendChild(el("p", "actor-sheet-empty", "No sheet layout for this system."));
      return;
    }
    const body = buildNode(layout.body, rc);
    if (body) root.appendChild(body);
  }

  async function refresh(root) {
    const meta = contexts.get(root);
    if (!meta) return;
    const res = await fetch(`/game/item/${encodeURIComponent(meta.itemId)}/sheet-bundle`, {
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
  FI.render = render;
  FI.refresh = refresh;
  FI.modifierTargetById = modifierTargetById;
  FI.modifierOperationById = modifierOperationById;
  FI.modifierValueType = modifierValueType;
  FI.buildOptions = buildOptions;
})();
