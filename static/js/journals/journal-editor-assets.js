(() => {
  const script = document.currentScript;
  const version = encodeURIComponent(script?.dataset?.assetVersion || "dev");
  const loadedStyles = new Set();
  const pending = new Map();

  function stylesheet(path) {
    if (loadedStyles.has(path) || document.querySelector(`link[href^="${path}"]`)) {
      return;
    }
    loadedStyles.add(path);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${path}?v=${version}`;
    document.head.appendChild(link);
  }

  function classic(path, globalName) {
    if (globalName && window[globalName]) return Promise.resolve(window[globalName]);
    if (pending.has(path)) return pending.get(path);
    const promise = new Promise((resolve, reject) => {
      const element = document.createElement("script");
      element.src = `${path}?v=${version}`;
      element.async = true;
      element.onload = () => resolve(globalName ? window[globalName] : true);
      element.onerror = () => reject(new Error(`Could not load ${path}`));
      document.head.appendChild(element);
    });
    pending.set(path, promise);
    return promise;
  }

  function module(path) {
    if (window.GWBlockEditor) return Promise.resolve(window.GWBlockEditor);
    if (pending.has(path)) return pending.get(path);
    const promise = import(`${path}?v=${version}`).then(() => window.GWBlockEditor);
    pending.set(path, promise);
    return promise;
  }

  window.GravewrightJournalEditorAssets = Object.freeze({
    loadBlockEditor() {
      return module("/static/js/journals/block-editor.js");
    },
    loadEasyMDE() {
      stylesheet("/static/vendor/easymde/easymde.min.css");
      return classic("/static/vendor/easymde/easymde.min.js", "EasyMDE");
    },
    loadMarkdown() {
      return classic("/static/vendor/marked.min.js", "marked")
        .then(() => classic("/static/vendor/purify.min.js", "DOMPurify"));
    },
  });
})();
