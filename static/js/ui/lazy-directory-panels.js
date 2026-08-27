(() => {
  const loading = new WeakMap();

  function refreshFor(kind) {
    if (kind === "actors") return window.GravewrightActorsInternals?.refreshPanel;
    if (kind === "items") return window.GravewrightItemsInternals?.refreshPanel;
    if (kind === "journals") return window.GravewrightJournalsInternals?.refreshJournalPanel;
    if (kind === "scenes") return window.GravewrightScenes?.refreshPanel;
    return null;
  }

  async function hydrate(host) {
    if (!host || host.dataset.directoryLoaded === "true") return true;
    if (loading.has(host)) return loading.get(host);
    const refresh = refreshFor(host.dataset.lazyDirectoryKind);
    const roomId = host.dataset.lazyDirectoryRoom || "";
    if (!refresh || !roomId) return false;
    host.setAttribute("aria-busy", "true");
    const promise = Promise.resolve(refresh(roomId))
      .then((loaded) => {
        if (loaded) host.dataset.directoryLoaded = "true";
        return Boolean(loaded);
      })
      .catch(() => false)
      .finally(() => {
        host.removeAttribute("aria-busy");
        loading.delete(host);
      });
    loading.set(host, promise);
    return promise;
  }

  document.addEventListener("vtt:modal-opened", (event) => {
    event.detail?.modal?.querySelectorAll?.("[data-lazy-directory-kind]").forEach(hydrate);
  });

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-modal-window]:not([hidden]) [data-lazy-directory-kind]")
      .forEach(hydrate);
  });

  window.GravewrightLazyDirectories = { hydrate };
})();
