



(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const whenBlockEditorReady = FI.whenBlockEditorReady;
  const readJsonScript = FI.readJsonScript;
  const blockControllers = FI.blockControllers;

  function renderMarkdownIn(root) {
    if (!window.marked || !window.DOMPurify) {
      window.GravewrightJournalEditorAssets?.loadMarkdown?.()
        .then(() => renderMarkdownIn(root))
        .catch(() => {});
      return;
    }







    const purify = window.DOMPurify;
    const canSanitize = !!purify && typeof purify.sanitize === "function";

    root.querySelectorAll("[data-journal-markdown]").forEach((el) => {
      if (el.dataset.rendered) return;
      const raw = el.textContent || "";
      if (!canSanitize) {
        el.textContent = raw;
        el.dataset.rendered = "1";
        return;
      }
      el.innerHTML = purify.sanitize(window.marked.parse(raw.trim()), {
        ADD_ATTR: ["target", "rel"],
      });
      el.querySelectorAll("a[href]").forEach((a) => {
        a.target = "_blank";
        a.rel = "noopener noreferrer";
      });
      el.dataset.rendered = "1";
    });
  }

  function mountDocReadersIn(root) {
    whenBlockEditorReady(() => {
      root.querySelectorAll("[data-journal-doc-reader]").forEach((host) => {
        if (blockControllers.has(host)) return;
        const doc = readJsonScript(host, "[data-journal-doc]");
        const mountEl = document.createElement("div");
        host.textContent = "";
        host.appendChild(mountEl);
        blockControllers.set(host, window.GWBlockEditor.mount(mountEl, { editable: false, doc }));
      });
    });
  }

  FI.renderMarkdownIn = renderMarkdownIn;
  FI.mountDocReadersIn = mountDocReadersIn;
})();
