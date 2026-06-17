



(function () {
  const FI = (window.GravewrightItemSheetInternals = window.GravewrightItemSheetInternals || {});
  const contexts = FI.contexts;
  const csrfOf = FI.csrfOf;
  const getPath = FI.getPath;
  const postJSON = FI.postJSON;
  const render = FI.render;
  const refresh = FI.refresh;
  const modifierTargetById = FI.modifierTargetById;
  const modifierOperationById = FI.modifierOperationById;
  const modifierValueType = FI.modifierValueType;
  const buildOptions = FI.buildOptions;

  function coerce(kind, raw, checked) {
    if (kind === "bool") return !!checked;
    if (kind === "number") {
      const n = Number(raw);
      return Number.isFinite(n) ? n : 0;
    }
    return raw;
  }

  function writePath(root, path, value) {
    const meta = contexts.get(root);
    if (!meta) return Promise.resolve(null);
    if (path === "core.name") {
      return postJSON("/game/item/update-core", {
        csrf_token: meta.csrf, item_id: meta.itemId, name: String(value),
      });
    }
    const dataPath = path.startsWith("sheet.") ? path.slice("sheet.".length) : path;
    return postJSON("/game/item/sheet-data/patch", {
      csrf_token: meta.csrf, item_id: meta.itemId, patch: { [dataPath]: value },
    });
  }


  function modifierValueFor(operation, raw) {
    const type = modifierValueType(operation);
    if (type === "none") return undefined;
    if (type === "number") {
      const n = Number(raw);
      return Number.isFinite(n) ? n : 0;
    }
    return String(raw || "").trim();
  }

  function readModifierBuilder(builder) {
    const targets = JSON.parse(builder.dataset.targets || "[]");
    const rows = Array.from(builder.querySelectorAll(".gw-modifier-row"));
    return rows.map((row, index) => {
      const targetId = row.querySelector('[data-modifier-field="target"]')?.value || targets[0]?.id || "";
      const target = modifierTargetById(targets, targetId);
      const operationId = row.querySelector('[data-modifier-field="operation"]')?.value || target?.operations?.[0]?.id || "";
      const operation = modifierOperationById(target, operationId);
      const rawValue = row.querySelector('[data-modifier-field="value"]')?.value ?? "";
      const label = row.querySelector('[data-modifier-field="label"]')?.value || target?.label || "Modifier";
      const result = {
        id: row.dataset.modifierId || `mod_${Date.now()}_${index}`,
        target: targetId,
        operation: operationId,
        label,
      };
      const value = modifierValueFor(operation, rawValue);
      if (value !== undefined && value !== "") result.value = value;
      return result;
    });
  }

  function defaultModifier(builder) {
    const targets = JSON.parse(builder.dataset.targets || "[]");
    const target = targets[0] || { id: "roll.check", label: "Check", operations: [] };
    const operation = (Array.isArray(target.operations) ? target.operations[0] : null) || { id: "add", valueType: "number" };
    return {
      id: `mod_${Date.now()}`,
      target: target.id,
      operation: operation.id,
      label: target.label || "Modifier",
      ...(modifierValueType(operation) === "none" ? {} : { value: modifierValueType(operation) === "number" ? 0 : "" }),
    };
  }

  async function persistModifierBuilder(root, builder, nextList) {
    const path = builder.dataset.modifierPath || "sheet.modifiers";
    return writePath(root, path, nextList);
  }

  function wire(root) {
    root.addEventListener("change", async (event) => {
      const modifierField = event.target.closest("[data-modifier-field]");
      if (modifierField && root.contains(modifierField)) {
        const builder = modifierField.closest("[data-modifier-builder]");
        if (!builder) return;
        if (modifierField.dataset.modifierField === "target") {
          const targets = JSON.parse(builder.dataset.targets || "[]");
          const row = modifierField.closest(".gw-modifier-row");
          const target = modifierTargetById(targets, modifierField.value);
          const op = row?.querySelector('[data-modifier-field="operation"]');
          if (op) {
            op.innerHTML = "";
            buildOptions(op, Array.isArray(target?.operations) ? target.operations : [], "");
          }
        }
        if (await persistModifierBuilder(root, builder, readModifierBuilder(builder))) refresh(root);
        return;
      }

      const input = event.target.closest("[data-bind-path]");
      if (!input || !root.contains(input)) return;
      const value = coerce(input.dataset.bindKind, input.value, input.checked);
      if (await writePath(root, input.dataset.bindPath, value)) refresh(root);
    });

    root.addEventListener("click", async (event) => {
      const meta = contexts.get(root);
      if (!meta) return;

      const modifierAction = event.target.closest("[data-modifier-action]");
      if (modifierAction && root.contains(modifierAction)) {
        const builder = modifierAction.closest("[data-modifier-builder]");
        if (!builder) return;
        let nextList = readModifierBuilder(builder);
        if (modifierAction.dataset.modifierAction === "add") {
          nextList = [...nextList, defaultModifier(builder)];
        } else if (modifierAction.dataset.modifierAction === "remove") {
          const row = modifierAction.closest(".gw-modifier-row");
          const index = Number(row?.dataset.index);
          nextList = nextList.filter((_, i) => i !== index);
        }
        if (await persistModifierBuilder(root, builder, nextList)) refresh(root);
        return;
      }

      const step = event.target.closest("[data-step-path]");
      if (step && root.contains(step)) {
        const res = await fetch(`/game/item/${encodeURIComponent(meta.itemId)}/sheet-bundle`, {
          credentials: "same-origin", headers: { Accept: "application/json" },
        });
        if (!res.ok) return;
        const bundle = await res.json();
        const path = step.dataset.stepPath;
        const current = Number(getPath({ core: {}, sheet: bundle.data }, path)) || 0;
        const next = current + Number(step.dataset.stepBy || 0);
        if (await writePath(root, path, next)) refresh(root);
      }
    });
  }

  function mount(modal) {
    const root = modal.querySelector("[data-item-sheet-root]");
    const script = modal.querySelector("[data-item-bundle]");
    if (!root || !script) return;
    let bundle;
    try {
      bundle = JSON.parse(script.textContent || "{}");
    } catch {
      return;
    }
    contexts.set(root, {
      itemId: root.dataset.itemId,
      csrf: csrfOf(root),
      canEdit: !!bundle.can_edit,
    });
    const isHtmlSheet = bundle.sheet && bundle.sheet.mode === "html";
    if (!isHtmlSheet && !root.dataset.wired) {
      wire(root);
      root.dataset.wired = "1";
    }
    render(root, bundle);
  }

  FI.mount = mount;
  FI.writePath = writePath;
})();
