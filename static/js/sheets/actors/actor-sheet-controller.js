




(function () {
  const FI = (window.GravewrightActorSheetInternals = window.GravewrightActorSheetInternals || {});
  const contexts = FI.contexts;
  const csrfOf = FI.csrfOf;
  const getPath = FI.getPath;
  const postJSON = FI.postJSON;
  const render = FI.render;
  const refresh = FI.refresh;
  const openActionMenu = FI.openActionMenu;
  const openRollDialog = FI.openRollDialog;
  const executeItemAction = FI.executeItemAction;
  const executeSheetAction = FI.executeSheetAction;

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
    if (meta.tokenId && meta.tokenLinkMode !== "linked") {
      const dataPath = path.startsWith("sheet.") ? path.slice("sheet.".length) : path;
      return postJSON("/game/token/sheet-data/patch", {
        csrf_token: meta.csrf, token_id: meta.tokenId, patch: { [dataPath]: value },
      });
    }
    if (path === "core.name") {
      return postJSON("/game/actor/update-core", {
        csrf_token: meta.csrf, actor_id: meta.actorId, name: String(value),
      });
    }
    const dataPath = path.startsWith("sheet.") ? path.slice("sheet.".length) : path;
    return postJSON("/game/actor/sheet-data/patch", {
      csrf_token: meta.csrf, actor_id: meta.actorId, patch: { [dataPath]: value },
    });
  }

  function wire(root) {
    root.addEventListener("change", async (event) => {
      const trackInput = event.target.closest("[data-check-track-value]");
      if (trackInput && root.contains(trackInput)) {
        const track = trackInput.closest("[data-check-track-path]");
        const path = track?.dataset.checkTrackPath || "";
        const value = Number(trackInput.dataset.checkTrackValue || 0);
        const next = trackInput.checked ? value : Math.max(0, value - 1);
        if (path && await writePath(root, path, next)) refresh(root);
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

      const interaction = event.target.closest("[data-interaction]");
      if (interaction && root.contains(interaction)) {
        try {
          openActionMenu(root, interaction, JSON.parse(interaction.dataset.interaction || "{}"), {
            itemId: interaction.dataset.itemId || "",
          });
        } catch {
          
        }
        return;
      }

      const itemAction = event.target.closest("[data-item-action]");
      if (itemAction && root.contains(itemAction)) {
        if (itemAction.dataset.rollDialog === "1") {
          let dialog = "roll";
          if (itemAction.dataset.rollDialogSchema) {
            try { dialog = JSON.parse(itemAction.dataset.rollDialogSchema); }
            catch { dialog = "roll"; }
          }
          openRollDialog(root, itemAction, {
            action: itemAction.dataset.itemAction,
            label: itemAction.textContent || "Roll",
            dialog,
          }, {
            itemId: itemAction.dataset.itemId,
          });
        } else {
          await executeItemAction(root, itemAction.dataset.itemId, itemAction.dataset.itemAction);
        }
        return;
      }

      const itemRemove = event.target.closest("[data-item-remove]");
      if (itemRemove && root.contains(itemRemove)) {
        if (await postJSON("/game/actor/item/remove", {
          csrf_token: meta.csrf,
          actor_id: meta.actorId,
          item_instance_id: itemRemove.dataset.itemId,
        })) refresh(root);
        return;
      }

      const action = event.target.closest("[data-action]");
      if (action && root.contains(action)) {
        await executeSheetAction(root, action.dataset.action);
        return; 
      }

      const step = event.target.closest("[data-step-path]");
      if (step && root.contains(step)) {
        const bundleUrl = meta.tokenId
          ? `/game/token/${encodeURIComponent(meta.tokenId)}/sheet-bundle`
          : `/game/actor/${encodeURIComponent(meta.actorId)}/sheet-bundle`;
        const res = await fetch(bundleUrl, {
          credentials: "same-origin", headers: { Accept: "application/json" },
        });
        if (!res.ok) return;
        const bundle = await res.json();
        const path = step.dataset.stepPath;
        const dataPath = path.startsWith("sheet.") ? path.slice(6) : path;
        const current = Number(getPath({ core: {}, sheet: bundle.data }, path)) || 0;
        const next = current + Number(step.dataset.stepBy || 0);
        if (await writePath(root, path, next)) refresh(root);
        void dataPath;
      }
    });
  }

  function mount(modal) {
    const root = modal.querySelector("[data-actor-sheet-root]");
    const script = modal.querySelector("[data-actor-bundle]");
    if (!root || !script) return;
    let bundle;
    try {
      bundle = JSON.parse(script.textContent || "{}");
    } catch {
      return;
    }
    contexts.set(root, {
      actorId: root.dataset.actorId,
      tokenId: root.dataset.tokenId || "",
      csrf: csrfOf(root),
      roomId: modal.dataset.actorCampaign || "",
      tokenLinkMode: bundle.actor?.token_link_mode || "",
      canEdit: !!bundle.can_edit,
      systemId: bundle.actor?.system_id || "",
    });
    // HTML-mode sheets handle their own input/action wiring through
    // GravewrightHTMLSheets; the declarative listeners would double-fire on
    // shared data-action attributes, so they are skipped.
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
