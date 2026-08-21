/* Menu de botao direito do cartao de cena.
 *
 * Ativar, navegar, configurar e remover moravam como quatro icones dentro do
 * cartao. Numa arvore estreita eles disputavam espaco com o nome -- que e o
 * unico dado que o mestre le ao varrer a lista --, entao passaram para ca.
 * Remover veio junto, do rodape do dialogo de configurar: apagar uma cena e
 * uma acao sobre a cena, nao um campo do formulario dela.
 */
(() => {
  "use strict";

  function label(name, fallback) {
    return document.body?.dataset?.[name] || fallback;
  }

  function navigateTo(roomId, sceneId) {
    void window.GravewrightSceneNavigation?.navigate?.(sceneId, roomId, { local: true });
  }

  function openEditModal(sceneId) {
    // O modal de configurar e carregado sob demanda por modal-manager; o
    // gatilho dele e o data-scene-edit, entao emprestamos um botao invisivel
    // em vez de duplicar aqui o carregamento.
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.dataset.sceneEdit = sceneId;
    trigger.style.display = "none";
    document.body.appendChild(trigger);
    trigger.click();
    trigger.remove();
  }

  /* Menu da pasta: criar cena ja dentro dela, renomear/recolorir e apagar.
     Apagar solta as cenas para a raiz -- nunca as remove, porque uma cena leva
     junto o mapa, os tiles e os chunks. */
  function openFolderMenu(event, folder, panel) {
    const menu = window.GravewrightContextMenu;
    if (!menu) return;
    const folderId = folder.dataset.folderId || "";
    const roomId = panel.dataset.roomId || "";
    if (!folderId || panel.dataset.isGm !== "true") return;

    event.preventDefault();
    event.stopPropagation();
    menu.show(event.clientX, event.clientY, [
      {
        label: label("sceneMenuNewInFolder", "New scene here"),
        icon: "ph-map-trifold",
        onClick: () => openCreateModal(roomId, folderId),
      },
      { separator: true },
      {
        label: label("ctxFolderEdit", "Edit folder"),
        icon: "ph-pencil-simple",
        onClick: () => window.GravewrightContextMenuInternals?.openFolderEditor?.({
          kind: "scene", folderId, campaignId: roomId,
          name: folder.dataset.folderName || "", color: folder.dataset.folderColor || "",
        }),
      },
      { separator: true },
      {
        label: label("sceneMenuFolderDelete", "Delete folder"),
        icon: "ph-trash",
        danger: true,
        onClick: async () => {
          const prompt = label("sceneMenuFolderDeleteConfirm", "Delete this folder? Its scenes are kept.");
          if (!(await window.GravewrightCore.dialog.confirm(prompt, { variant: "danger" }))) return;
          await window.GravewrightScenes?.deleteFolder(folderId, roomId);
        },
      },
    ]);
  }

  function openCreateModal(roomId, groupId) {
    const modalId = `scene-create-${roomId}`;
    const form = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"] .scene-upload-form`);
    // O dialogo de nova cena ja tem o seletor de grupo; abrir pela pasta so o
    // deixa pre-escolhido, em vez de duplicar o formulario.
    const select = form?.querySelector('select[name="group_id"]');
    if (select) select.value = groupId || "";
    window.GravewrightModals?.open?.(modalId);
  }

  document.addEventListener("contextmenu", (event) => {
    const panel = event.target.closest("[data-scene-panel]");
    if (!panel) return;

    const folderHeader = event.target.closest(".scene-folder > .sheet-folder-header");
    if (folderHeader) {
      openFolderMenu(event, folderHeader.closest(".scene-folder"), panel);
      return;
    }

    const card = event.target.closest(".scene-card[data-scene-id]");
    if (!card) return;
    const menu = window.GravewrightContextMenu;
    if (!menu) return;

    const sceneId = card.dataset.sceneId;
    const roomId = card.dataset.roomId || "";
    const isActive = card.dataset.sceneActive === "true";
    const isGm = panel.dataset.isGm === "true";

    event.preventDefault();
    event.stopPropagation();

    // Mesma ordem das outras tres abas: primeiro a acao inofensiva de olhar,
    // depois a acao do dominio, depois o dialogo de ajuste, e so entao apagar.
    // Ativar estava no primeiro slot -- onde ator, item e diario tem "Abrir" --
    // e a memoria muscular das outras abas jogaria a cena na mesa sem querer.
    const items = [];
    items.push({
      label: label("sceneMenuNavigate", "Navigate"),
      icon: "ph-eye",
      onClick: () => navigateTo(roomId, sceneId),
    });
    if (isGm) {
      items.push({
        label: label("sceneMenuActivate", "Activate"),
        icon: "ph-play",
        onClick: () => { if (!isActive) void window.GravewrightScenes?.activate(sceneId, roomId); },
      });
    }
    items.push({
      label: label("sceneMenuConfigure", "Configure"),
      icon: "ph-sliders-horizontal",
      onClick: () => openEditModal(sceneId),
    });
    if (isGm) {
      items.push({ separator: true });
      items.push({
        label: label("sceneMenuRemove", "Remove scene"),
        icon: "ph-trash",
        danger: true,
        onClick: async () => {
          const prompt = label("sceneMenuRemoveConfirm", "Remove this scene?");
          if (!(await window.GravewrightCore.dialog.confirm(prompt, { variant: "danger" }))) return;
          await window.GravewrightScenes?.remove(sceneId, roomId);
        },
      });
    }

    menu.show(event.clientX, event.clientY, items);
  });
})();
