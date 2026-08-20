/* Acoes do painel de cenas, no mesmo contrato de atores e itens: mutar e depois
 * repintar a arvore pelo fragmento do servidor, sem recarregar a pagina. */
(() => {
  "use strict";

  const FI = (window.GravewrightScenesInternals = window.GravewrightScenesInternals || {});

  function csrf() {
    return typeof window.csrfToken === "function" ? window.csrfToken() : "";
  }

  function panelFor(roomId) {
    return document.querySelector(`[data-scene-panel][data-room-id="${CSS.escape(roomId)}"]`) || null;
  }

  function treeHostFor(roomId) {
    return panelFor(roomId)?.querySelector("[data-scene-tree-host]") || null;
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json", "x-csrftoken": csrf() },
      body: JSON.stringify(payload || {}),
    });
  }

  function postForm(url, fields) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "text/html",
        "X-Requested-With": "fetch",
      },
      body: new URLSearchParams({ ...fields, _csrf_token: csrf() }).toString(),
    });
  }

  async function refreshPanel(roomId) {
    const host = treeHostFor(roomId);
    if (!host) return;
    try {
      const response = await fetch(`/game/scenes/panel/${encodeURIComponent(roomId)}`, {
        credentials: "same-origin",
        headers: { Accept: "text/html" },
      });
      if (!response.ok) return;
      host.innerHTML = await response.text();
      // A arvore generica guarda o que estava aberto em localStorage, entao
      // basta reidratar: nao ha estado de expansao para carregar na mao.
      document.dispatchEvent(new CustomEvent("vtt:scene-panel-refreshed", { detail: { host, roomId } }));
      const panel = panelFor(roomId);
      if (panel?.querySelector("[data-scene-search]")?.value) {
        window.GravewrightScenesTree?.applySearch?.(panel);
      }
    } catch { /* Um refresh perdido nao pode derrubar a acao que ja foi gravada. */ }
  }

  Object.assign(FI, { panelFor, treeHostFor, postJson, postForm, refreshPanel });

  window.GravewrightScenes = {
    refreshPanel,
    async moveScene(sceneId, groupId, roomId) {
      const response = await postJson("/game/scenes/move", { scene_id: sceneId, group_id: groupId || "" });
      if (response.ok) await refreshPanel(roomId);
      return response.ok;
    },
    async activate(sceneId, roomId) {
      const response = await postForm("/game/scenes/activate", { campaign_id: roomId, scene_id: sceneId });
      if (response.ok) await refreshPanel(roomId);
      return response.ok;
    },
    async deleteFolder(folderId, roomId) {
      const response = await postForm("/game/scene-folder/delete", {
        folder_id: folderId, campaign_id: roomId,
      });
      if (response.ok) await refreshPanel(roomId);
      return response.ok;
    },
    async remove(sceneId, roomId) {
      const response = await postForm("/game/scenes/delete", { campaign_id: roomId, scene_id: sceneId });
      if (response.ok) await refreshPanel(roomId);
      return response.ok;
    },
  };
})();
