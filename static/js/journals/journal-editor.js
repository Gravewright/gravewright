




(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const csrfToken = FI.csrfToken;

  const editors = new WeakMap();
  const blockControllers = new WeakMap(); 
  const autosaveTimers = new WeakMap();

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  

  function initRichTextIn(root) {
    if (!window.EasyMDE) return;
    root.querySelectorAll("[data-journal-rich-text]").forEach((textarea) => {
      if (editors.has(textarea)) return;
      const editor = new window.EasyMDE({
        element: textarea,
        spellChecker: false,
        status: false,
        minHeight: "150px",
        toolbar: [
          "bold", "italic", "heading",
          "|", "quote", "unordered-list", "ordered-list",
          "|", "link", "image",
          "|", "preview", "side-by-side", "guide",
        ],
      });
      editors.set(textarea, editor);
      
      editor.codemirror.on("blur", () => {
        const form = textarea.closest("[data-journal-editor]");
        if (form) {
          editor.codemirror.save();
          scheduleAutosave(form, true);
        }
      });
    });
  }

  

  function readJsonScript(host, selector) {
    const tag = host.querySelector(selector);
    if (!tag) return null;
    try {
      return JSON.parse(tag.textContent || "null");
    } catch {
      return null;
    }
  }

  function whenBlockEditorReady(cb) {
    if (window.GWBlockEditor) cb();
    else document.addEventListener("gw:block-editor-ready", () => cb(), { once: true });
  }

  function modalLabels(host) {
    const tag = host.closest("[data-modal-window]")?.querySelector("[data-journal-editor-labels]");
    try {
      return JSON.parse(tag?.textContent || "{}");
    } catch {
      return {};
    }
  }

  async function uploadJournalImage(journalId, file, errorMessage) {
    const body = new FormData();
    body.append("csrf_token", csrfToken());
    body.append("journal_id", journalId);
    body.append("file", file);
    const res = await fetch("/game/journal/asset", {
      method: "POST",
      body,
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      if (errorMessage) window.GravewrightToasts?.showToast(errorMessage);
      throw new Error("upload failed");
    }
    return res.json();
  }


  function initImageUpload(modal) {
    const journalId = modal.dataset.journalId || "";
    if (!journalId) return;
    modal.querySelectorAll("[data-image-upload]").forEach((btn) => {
      if (btn.dataset.imageUploadBound) return;
      btn.dataset.imageUploadBound = "1";
      const field = btn.closest("[data-image-field]");
      const input = field?.querySelector("[data-image-src]");
      if (!input) return;
      btn.addEventListener("click", () => {
        const picker = document.createElement("input");
        picker.type = "file";
        picker.accept = "image/png,image/jpeg,image/webp";
        picker.addEventListener("change", async () => {
          const file = picker.files?.[0];
          if (!file) return;
          btn.disabled = true;
          try {
            const result = await uploadJournalImage(journalId, file, btn.dataset.errorLabel);
            if (result?.src) {
              input.value = result.src;
              input.dispatchEvent(new Event("change", { bubbles: true }));
            }
          } catch {

          } finally {
            btn.disabled = false;
          }
        });
        picker.click();
      });
    });
  }

  function mountBlockEditorsIn(root) {
    whenBlockEditorReady(() => {
      root.querySelectorAll("[data-journal-block-editor]").forEach((host) => {
        if (blockControllers.has(host)) return;
        const form = host.closest("[data-journal-editor]");
        
        const field = host.closest("[data-journal-block-field]") || host.parentElement;
        const input = field?.querySelector("[data-journal-doc-input]");
        const doc = readJsonScript(host, "[data-journal-doc]");
        let labels = modalLabels(host);
        if (host.dataset.labels) {
          try { labels = JSON.parse(host.dataset.labels); } catch {  }
        }

        
        
        const mountEl = document.createElement("div");
        host.textContent = "";
        host.appendChild(mountEl);

        let suppressAutosave = true;
        const writeInput = (d) => { if (input) input.value = JSON.stringify(d); };
        const journalId = host.closest("[data-modal-window]")?.dataset.journalId || "";

        const controller = window.GWBlockEditor.mount(mountEl, {
          editable: true,
          isGm: host.dataset.isGm === "true",
          labels,
          doc,
          uploadImage: journalId
            ? (file) => uploadJournalImage(journalId, file, labels.upload_error)
            : null,
          onChange: (d) => {
            writeInput(d);
            if (form && !suppressAutosave) scheduleAutosave(form);
          },
        });
        blockControllers.set(host, controller);

        writeInput(controller.getDoc());
        suppressAutosave = false;
      });
    });
  }

  function flushBlockEditors(scope) {
    scope.querySelectorAll("[data-journal-block-editor]").forEach((host) => {
      const controller = blockControllers.get(host);
      const field = host.closest("[data-journal-block-field]") || host.parentElement;
      const input = field?.querySelector("[data-journal-doc-input]");
      if (controller && input) input.value = JSON.stringify(controller.getDoc());
    });
  }

  function destroyBlockEditorsIn(root) {
    root.querySelectorAll("[data-journal-block-editor], [data-journal-doc-reader]").forEach((host) => {
      const controller = blockControllers.get(host);
      if (!controller) return;
      try { controller.destroy(); } catch {  }
      blockControllers.delete(host);
    });
  }

  

  function readJson(textarea) {
    try {
      const value = JSON.parse(textarea.value || "[]");
      return Array.isArray(value) ? value : [];
    } catch {
      return [];
    }
  }

  function checkboxField(field, label, checked) {
    return `<label class="journal-list-check"><input type="checkbox" data-field="${field}" ${checked ? "checked" : ""}/> ${escapeHtml(label)}</label>`;
  }

  function renderObjectiveRow(editor, obj) {
    const ds = editor.dataset;
    return `<div class="journal-list-row" draggable="false">
      <input type="text" class="journal-list-text" data-field="text" value="${escapeHtml(obj.text)}" placeholder="${escapeHtml(ds.placeholder || "")}" />
      ${checkboxField("completed", ds.labelCompleted || "Done", obj.completed)}
      ${checkboxField("optional", ds.labelOptional || "Optional", obj.optional)}
      ${checkboxField("visibleToPlayers", ds.labelVisible || "Visible", obj.visibleToPlayers)}
      <button type="button" class="journal-list-remove" data-row-remove title="${escapeHtml(ds.labelRemove || "Remove")}"><i class="ph ph-trash" aria-hidden="true"></i></button>
    </div>`;
  }

  function renderRewardRow(editor, reward) {
    const ds = editor.dataset;
    return `<div class="journal-list-row" draggable="false">
      <input type="text" class="journal-list-text" data-field="text" value="${escapeHtml(reward.text)}" placeholder="${escapeHtml(ds.placeholder || "")}" />
      ${checkboxField("visibleToPlayers", ds.labelVisible || "Visible", reward.visibleToPlayers)}
      <button type="button" class="journal-list-remove" data-row-remove title="${escapeHtml(ds.labelRemove || "Remove")}"><i class="ph ph-trash" aria-hidden="true"></i></button>
    </div>`;
  }

  function initListEditor(modal, config) {
    const editor = modal.querySelector(config.editorSelector);
    if (!editor) return;
    const rowsEl = editor.querySelector(config.rowsSelector);
    const jsonEl = editor.querySelector(config.jsonSelector);
    if (!rowsEl || !jsonEl) return;

    const items = readJson(jsonEl);

    const sync = () => {
      const collected = [];
      rowsEl.querySelectorAll(".journal-list-row").forEach((row) => {
        const item = {};
        row.querySelectorAll("[data-field]").forEach((field) => {
          if (field.type === "checkbox") item[field.dataset.field] = field.checked;
          else item[field.dataset.field] = field.value;
        });
        if ((item.text || "").trim()) collected.push(item);
      });
      jsonEl.value = JSON.stringify(collected);
    };

    const append = (item) => {
      rowsEl.insertAdjacentHTML("beforeend", config.render(editor, item));
    };

    items.forEach(append);

    editor.querySelector(config.addSelector)?.addEventListener("click", () => {
      append(config.empty());
    });

    rowsEl.addEventListener("click", (event) => {
      const removeBtn = event.target.closest("[data-row-remove]");
      if (removeBtn) {
        removeBtn.closest(".journal-list-row")?.remove();
        sync();
      }
    });
    rowsEl.addEventListener("input", sync);
    rowsEl.addEventListener("change", sync);

    
    const form = editor.closest("form");
    form?.addEventListener("submit", sync);
  }

  function initQuestEditors(modal) {
    initListEditor(modal, {
      editorSelector: "[data-objectives-editor]",
      rowsSelector: "[data-objectives-rows]",
      jsonSelector: "[data-objectives-json]",
      addSelector: "[data-objective-add]",
      render: renderObjectiveRow,
      empty: () => ({ text: "", completed: false, optional: false, visibleToPlayers: true }),
    });
    initListEditor(modal, {
      editorSelector: "[data-rewards-editor]",
      rowsSelector: "[data-rewards-rows]",
      jsonSelector: "[data-rewards-json]",
      addSelector: "[data-reward-add]",
      render: renderRewardRow,
      empty: () => ({ text: "", visibleToPlayers: true }),
    });
  }

  

  function flushEditors(scope) {
    scope.querySelectorAll("[data-journal-rich-text]").forEach((textarea) => {
      const editor = editors.get(textarea);
      if (editor) editor.codemirror.save();
    });
    flushBlockEditors(scope);
  }

  async function autosaveJournal(form) {
    if (!form) return;
    flushEditors(form);
    const hint = form.querySelector("[data-journal-autosave-hint]");
    try {
      const res = await fetch(form.action, {
        method: "POST",
        body: new URLSearchParams(new FormData(form)),
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });
      if (!res.ok) return;
      const data = await res.json().catch(() => ({}));
      const modal = form.closest("[data-modal-window]");
      if (modal && data.version) modal.dataset.journalVersion = data.version;
      if (hint) {
        hint.textContent = hint.dataset.savedLabel || "Saved";
        hint.classList.add("is-visible");
      }
    } catch {
      
    }
  }

  function scheduleAutosave(form, immediate) {
    if (!form) return;
    clearTimeout(autosaveTimers.get(form));
    if (immediate) {
      autosaveJournal(form);
    } else {
      autosaveTimers.set(form, setTimeout(() => autosaveJournal(form), 700));
    }
  }

  FI.editors = editors;
  FI.blockControllers = blockControllers;
  FI.readJsonScript = readJsonScript;
  FI.whenBlockEditorReady = whenBlockEditorReady;
  FI.initRichTextIn = initRichTextIn;
  FI.mountBlockEditorsIn = mountBlockEditorsIn;
  FI.destroyBlockEditorsIn = destroyBlockEditorsIn;
  FI.initQuestEditors = initQuestEditors;
  FI.initImageUpload = initImageUpload;
  FI.flushEditors = flushEditors;
  FI.autosaveJournal = autosaveJournal;
  FI.scheduleAutosave = scheduleAutosave;
})();
