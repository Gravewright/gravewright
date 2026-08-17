(() => {
  const PACKAGE = "gravewright-pdf-system";
  const assetUrl = (relative) => `/sdk/packages/${PACKAGE}/asset/${String(relative || "").replace(/^\/+/, "")}`;
  let loader = null;
  let active = null;

  function ensureViewer() {
    if (window.GravewrightPdfViewer) return Promise.resolve(window.GravewrightPdfViewer);
    if (!loader) loader = new Promise((resolve, reject) => {
      if (!document.querySelector('[data-journal-pdf-viewer-style]')) {
        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = assetUrl("styles/pdf-sheet.css");
        style.dataset.journalPdfViewerStyle = "true";
        document.head.appendChild(style);
      }
      const script = document.createElement("script");
      script.src = assetUrl("scripts/pdf-viewer.js");
      script.onload = () => window.GravewrightPdfViewer ? resolve(window.GravewrightPdfViewer) : reject(new Error("pdf viewer unavailable"));
      script.onerror = () => reject(new Error("pdf viewer unavailable"));
      document.head.appendChild(script);
    });
    return loader;
  }

  function shell(container) {
    container.classList.add("journal-pdf-inline");
    if (!container.querySelector("[data-journal-pdf-host]")) {
      container.innerHTML = `<header class="journal-pdf-inline-bar">
        <strong data-journal-pdf-title></strong><span data-journal-pdf-page></span>
        <button type="button" data-journal-pdf-prev aria-label="Página anterior"><i class="ph ph-caret-left"></i></button>
        <button type="button" data-journal-pdf-next aria-label="Próxima página"><i class="ph ph-caret-right"></i></button>
        <button type="button" data-journal-pdf-zoom-out aria-label="Reduzir zoom">-</button>
        <button type="button" data-journal-pdf-zoom-in aria-label="Aumentar zoom">+</button>
        <label class="journal-pdf-search"><span class="sr-only">Buscar no PDF</span><input type="search" data-journal-pdf-search placeholder="Buscar"><button type="button" data-journal-pdf-search-run aria-label="Buscar"><i class="ph ph-magnifying-glass"></i></button></label>
      </header><div class="journal-pdf-inline-host" data-journal-pdf-host></div>`;
    }
    return container;
  }

  async function searchPdf(container) {
    if (active !== container) return;
    const query = container.querySelector("[data-journal-pdf-search]")?.value || "";
    const matches = await window.GravewrightPdfViewer?.search?.(query) || [];
    if (matches[0]) await window.GravewrightPdfViewer.goToPage(matches[0].page);
    else if (query) window.GravewrightToasts?.showToast?.("Nenhum resultado encontrado");
  }

  async function mount(container, documentId) {
    if (!container || !documentId) return;
    container.dataset.documentId = documentId;
    const response = await fetch(`/game/journal/pdf/${encodeURIComponent(documentId)}`, {
      credentials: "same-origin", headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error_key || "pdf unavailable");
    const { document: pdf } = await response.json();
    const inline = shell(container);
    inline.querySelector("[data-journal-pdf-title]").textContent = pdf.filename || "PDF";
    inline.querySelector("[data-journal-pdf-page]").textContent = "";
    const viewer = await ensureViewer();
    active = inline;
    await viewer.open({
      host: inline.querySelector("[data-journal-pdf-host]"), url: pdf.url, assetUrl, page: 1, zoom: 1,
      onPageChange: ({ page, pages }) => {
        if (active === inline) inline.querySelector("[data-journal-pdf-page]").textContent = `${page} / ${pages}`;
      },
    });
    inline.dataset.pdfMounted = "true";
  }

  function activate(container) {
    if (!container?.dataset.documentId) return;
    if (active === container && container.dataset.pdfMounted === "true") return;
    void mount(container, container.dataset.documentId).catch((error) => {
      window.GravewrightToasts?.showToast?.(String(error?.message || error));
    });
  }

  document.addEventListener("click", (event) => {
    const control = event.target.closest?.("[data-journal-pdf-prev], [data-journal-pdf-next], [data-journal-pdf-zoom-out], [data-journal-pdf-zoom-in], [data-journal-pdf-search-run]");
    if (control) {
      const container = control.closest("[data-journal-pdf-inline]");
      if (active !== container) activate(container);
      else if (control.matches("[data-journal-pdf-prev]")) void window.GravewrightPdfViewer?.prevPage?.();
      else if (control.matches("[data-journal-pdf-next]")) void window.GravewrightPdfViewer?.nextPage?.();
      else if (control.matches("[data-journal-pdf-zoom-out]")) void window.GravewrightPdfViewer?.zoomBy?.(0.8);
      else if (control.matches("[data-journal-pdf-zoom-in]")) void window.GravewrightPdfViewer?.zoomBy?.(1.25);
      else void searchPdf(container);
      return;
    }
    const pageTarget = event.target.closest?.("[data-journal-section-link], [data-journal-page-target]");
    if (pageTarget) requestAnimationFrame(() => {
      const modal = pageTarget.closest("[data-journal-modal]") || document;
      const visible = Array.from(modal.querySelectorAll("[data-journal-pdf-inline]")).find((item) => !item.closest("[hidden]"));
      if (visible) activate(visible);
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || !event.target.matches("[data-journal-pdf-search]")) return;
    event.preventDefault();
    void searchPdf(event.target.closest("[data-journal-pdf-inline]"));
  });

  function mountVisible() {
    document.querySelectorAll("[data-journal-pdf-inline][data-document-id]").forEach((container) => {
      if (!container.closest("[hidden]")) activate(container);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountVisible, { once: true });
  else mountVisible();

  window.GravewrightJournalPdfViewer = { mount, activate };
})();
