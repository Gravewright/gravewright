/* Arvore do painel de cenas.
 *
 * Mesma maquina de atores, itens e diarios: busca, colapso e a persistencia do
 * que estava aberto saem de graca do diretorio generico. A unica diferenca e
 * que grupo de cena nao aninha -- scene_groups nao tem parent_id --, entao a
 * arvore tem um nivel so, o que o modulo generico ja atende.
 */
(() => {
  "use strict";

  const tree = window.GravewrightDirectoryTree?.create({
    type: "scenes",
    panelSelector: "[data-scene-panel]",
    hostSelector: "[data-scene-tree-host]",
    searchSelector: "[data-scene-search]",
    collapseSelector: "[data-scene-collapse-all]",
    toggleSelector: "[data-scene-folder-collapse]",
    folderClass: "scene-folder",
    entrySelector: "[data-scene-card]",
  });
  if (!tree) return;

  function hydrate(scope) {
    tree.applyColors(scope || document);
    document.querySelectorAll("[data-scene-panel]").forEach(tree.restore);
  }

  document.addEventListener("DOMContentLoaded", () => hydrate(document));

  // O painel e trocado inteiro quando um formulario de cena volta do servidor;
  // sem reidratar, os grupos perdem cor e voltam todos fechados.
  document.addEventListener("vtt:scene-panel-refreshed", (event) => hydrate(event.detail?.host || document));

  window.GravewrightScenesTree = { hydrate, applySearch: tree.applySearch };
})();
