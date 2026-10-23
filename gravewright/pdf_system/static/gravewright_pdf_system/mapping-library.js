/** Campaign mapping templates contain layout metadata, never documents or character values. */
export function createMappingLibrary({ root, controller, campaign, t }) {
  let active, destroyed = false, generation = 0;
  const base = `/api/containers/${campaign}/pdf-mappings`;
  async function request(url, payload, signal) {
    const response = await fetch(url, {
      method: payload ? "POST" : "GET", cache: "no-store", signal,
      headers: payload ? { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(
        root.ownerDocument.cookie.match(/(?:^|; )gravewright-csrf=([^;]*)/)?.[1] || "") } : {},
      ...(payload ? { body: JSON.stringify({ ...payload, requestId: crypto.randomUUID() }) } : {}),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Could not load the PDF mapping library.");
    return result;
  }
  async function open() {
    if (destroyed || !controller.view.canConfigureFieldActions) return null;
    if (active) { active.modal.focus(); return active.modal; }
    const pending = ++generation;
    const { mountModal } = await import("/static/gravewright_table/modal.js");
    if (destroyed || pending !== generation) return null;
    const document = root.ownerDocument;
    if (!document.querySelector("link[data-pdf-mapping-library-style]")) {
      const style = document.createElement("link");
      style.rel = "stylesheet"; style.href = new URL("./mapping-library.css", import.meta.url).href;
      style.dataset.pdfMappingLibraryStyle = ""; document.head.append(style);
    }
    const abort = new AbortController(), { signal } = abort;
    let busy = false, locked = false, items = [], selected = "";
    const node = (tag, attributes = {}, text) => {
      const element = document.createElement(tag);
      for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
      if (text !== undefined) element.textContent = text;
      return element;
    };
    const button = (key, text) => node("button", { type: "button", [`data-pdf-library-${key}`]: "" }, t(text));
    const modal = node("section", { class: "table-form-modal pdf-mapping-library", "data-pdf-mapping-library": "" });
    const form = node("form"), header = node("header");
    const title = node("strong", { id: `pdf-library-${crypto.randomUUID()}` }, t("PDF mapping library"));
    modal.setAttribute("aria-labelledby", title.id);
    const close = button("close", "Close"); header.append(title, close);
    const body = node("div", { class: "table-form-modal__body" });
    body.append(node("p", { class: "pdf-mapping-library__hint" }, t("Reuse fields, token bindings and formulas without copying PDFs or character values.")));
    const name = node("input", { type: "text", maxlength: "120", "data-pdf-library-name": "", translate: "no" });
    const nameLabel = node("label"); nameLabel.append(node("span", {}, t("Template name")), name);
    const list = node("select", { size: "5", "data-pdf-library-list": "", "aria-label": t("Saved mapping templates") });
    const empty = node("p", { class: "pdf-mapping-library__hint" }, t("No mapping templates saved yet."));
    const actions = node("div", { class: "pdf-mapping-library__actions" });
    const save = button("create", "Save current mapping"), update = button("update", "Replace selected template");
    const apply = button("apply", "Apply to this sheet"), remove = button("delete", "Delete selected template");
    const exportCurrent = button("export-current", "Export current mapping"), exportSelected = button("export", "Export selected template");
    const importButton = button("import", "Import mapping JSON");
    const upload = node("input", { type: "file", accept: ".json,application/json", hidden: "", "data-pdf-library-file": "" });
    actions.append(save, update, apply, exportCurrent, exportSelected, importButton, remove, upload);
    const several = node("details", { class: "pdf-mapping-library__several" });
    several.append(node("summary", {}, t("Apply to several characters")));
    const targets = node("div", { class: "pdf-mapping-library__targets", "data-pdf-library-targets": "" });
    const applySeveral = button("apply-many", "Apply to selected characters");
    several.append(node("p", { class: "pdf-mapping-library__hint" }, t("Character names, values and PDFs are preserved. Token snapshots keep their own layouts.")), targets, applySeveral);
    const status = node("p", { role: "status", hidden: "", "data-pdf-library-status": "" });
    const issue = node("p", { role: "alert", hidden: "", "data-pdf-library-error": "" });
    const footer = node("footer"), done = button("done", "Done"); footer.append(done);
    body.append(nameLabel, list, empty, actions, several, status, issue);
    form.append(header, body, footer); modal.append(form);
    const current = () => items.find((item) => item.id === selected);
    function refreshControls() {
      for (const control of modal.querySelectorAll("input,select,button")) control.disabled = busy;
      close.disabled = busy && locked;
      done.disabled = busy && locked;
      if (!busy) {
        for (const control of [update, apply, remove, exportSelected, applySeveral]) control.disabled = !current();
      }
      modal.setAttribute("aria-busy", String(busy));
    }
    async function work(callback, mutation = false) {
      if (busy || destroyed || signal.aborted) return;
      busy = true; locked = mutation; issue.hidden = true; status.hidden = true; refreshControls();
      try { await callback(); }
      catch (error) {
        if (!destroyed && !signal.aborted) { issue.textContent = t(error.message || "Could not load the PDF mapping library."); issue.hidden = false; }
      } finally {
        busy = false; locked = false;
        if (!destroyed && !signal.aborted) refreshControls();
      }
    }
    async function reload() {
      const result = await request(base, null, signal);
      if (signal.aborted) return;
      items = result.items;
      if (!items.some((item) => item.id === selected)) selected = "";
      list.replaceChildren(...items.map((item) => node("option", { value: item.id, translate: "no" }, item.name)));
      list.value = selected; empty.hidden = !!items.length;
    }
    function download(bundle, filename) {
      const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" }));
      const link = node("a", { href: url, download: filename }); document.body.append(link); link.click(); link.remove();
      document.defaultView.setTimeout(() => URL.revokeObjectURL(url), 0);
    }
    function chosenName() {
      if (!name.value.trim() || name.value.length > 120) throw new Error("Use a template name with 1 to 120 characters.");
      return name.value.trim();
    }
    list.addEventListener("change", () => {
      selected = list.value; name.value = current()?.name || ""; refreshControls();
    }, { signal });
    save.addEventListener("click", () => work(async () => {
      const result = await request(base, { action: "create", name: chosenName(), bundle: controller.call("exportMappingBundle") }, signal);
      selected = result.id; await reload();
    }, true), { signal });
    update.addEventListener("click", () => work(async () => {
      const item = current();
      await request(base, { action: "update", id: item.id, revision: item.revision, name: chosenName(), bundle: controller.call("exportMappingBundle") }, signal);
      await reload();
    }, true), { signal });
    apply.addEventListener("click", () => work(async () => {
      await controller.call("applyMappingBundle", current().bundle);
      status.textContent = t("Mapping applied."); status.hidden = false;
    }, true), { signal });
    remove.addEventListener("click", () => work(async () => {
      const item = current(); await request(base, { action: "delete", id: item.id, revision: item.revision }, signal);
      selected = ""; await reload();
    }, true), { signal });
    exportCurrent.addEventListener("click", () => work(async () => download(controller.call("exportMappingBundle"), "pdf-mapping.json")), { signal });
    exportSelected.addEventListener("click", () => {
      if (!busy && current()) download(current().bundle, "pdf-mapping.json");
    }, { signal });
    importButton.addEventListener("click", () => { if (!busy) upload.click(); }, { signal });
    upload.addEventListener("change", () => work(async () => {
      const file = upload.files?.[0]; upload.value = "";
      if (!file) return;
      if (file.size > 1_000_000) throw new Error("Use a mapping JSON file no larger than 1 MB.");
      const bundle = await file.text();
      const result = await request(base, { action: "import", name: name.value.trim() || file.name.replace(/\.json$/i, "").slice(0, 120), bundle }, signal);
      selected = result.id; name.value = result.name; await reload();
    }, true), { signal });
    let targetsLoaded = false;
    several.addEventListener("toggle", () => {
      if (!several.open || targetsLoaded) return;
      work(async () => {
        const result = await request(`/api/containers/${campaign}/actors`, null, signal);
        if (signal.aborted) return;
        for (const actor of result.actors) {
          const label = node("label");
          const input = node("input", { type: "checkbox", value: actor.id, "data-pdf-library-target": "" });
          label.append(input, node("span", { translate: "no" }, actor.name)); targets.append(label);
        }
        targetsLoaded = true;
      });
    }, { signal });
    applySeveral.addEventListener("click", () => work(async () => {
      const chosen = [...targets.querySelectorAll("input:checked")];
      if (!chosen.length || chosen.length > 100) throw new Error("Choose between 1 and 100 characters for this mapping.");
      await controller.call("flush");
      const prepared = [];
      for (const input of chosen) {
        const sheet = await request(`/api/containers/${campaign}/actors/${input.value}/sheet`, null, signal);
        prepared.push({ actorId: input.value, version: sheet.version, sheetVersion: sheet.sheetVersion,
          source: sheet.data.pdf.asset ? `asset:${sheet.data.pdf.asset}` : `template:${sheet.data.pdf.template || "generic"}` });
      }
      const item = current();
      await request(base, { action: "apply", id: item.id, revision: item.revision, targets: prepared }, signal);
      await controller.call("refreshActor");
      status.textContent = t("Mapping applied."); status.hidden = false;
    }, true), { signal });
    for (const control of [close, done]) control.addEventListener("click", () => { if (!busy || !locked) modal.close(); }, { signal });
    form.addEventListener("submit", (event) => event.preventDefault(), { signal });
    modal.addEventListener("close", () => { abort.abort(); if (active?.modal === modal) active = undefined; }, { once: true });
    active = { modal, abort };
    mountModal(modal, { nested: true, canClose: () => !busy || !locked });
    await work(reload);
    return modal;
  }
  return { open, destroy() { destroyed = true; ++generation; active?.modal.close(true); active?.abort.abort(); active = undefined; } };
}
