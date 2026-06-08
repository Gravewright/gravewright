







(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  
  
  function sanitizeHtml(value) {
    const input = value == null ? "" : String(value);
    if (window.DOMPurify && typeof window.DOMPurify.sanitize === "function") {
      return window.DOMPurify.sanitize(input);
    }
    return escapeHtml(input);
  }

  
  
  function trustedTemplate(html) {
    return html == null ? "" : String(html);
  }

  Core.sanitization = { escapeHtml, sanitizeHtml, trustedTemplate };
})();
