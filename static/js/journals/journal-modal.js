





(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const csrfToken = FI.csrfToken;
  const boardPost = FI.boardPost;
  const applyJournalFolderColors = FI.applyJournalFolderColors;
  const editors = FI.editors;
  const initRichTextIn = FI.initRichTextIn;
  const renderMarkdownIn = FI.renderMarkdownIn;
  const mountBlockEditorsIn = FI.mountBlockEditorsIn;
  const mountDocReadersIn = FI.mountDocReadersIn;
  const destroyBlockEditorsIn = FI.destroyBlockEditorsIn;
  const initQuestEditors = FI.initQuestEditors;
  const initImageUpload = FI.initImageUpload;
  const flushEditors = FI.flushEditors;
  const autosaveJournal = FI.autosaveJournal;
  const scheduleAutosave = FI.scheduleAutosave;
  const initPanel = FI.initPanel;

  const initialized = new WeakSet();

  const EMPTY_JOURNAL_DOC = {
    format: "gw-journal-doc-v1", version: 1,
    doc: { type: "doc", content: [] },
  };

  function sectionId() {
    return `section_${globalThis.crypto?.randomUUID?.().replaceAll("-", "").slice(0, 12) || Date.now().toString(36)}`;
  }

  function sectionCard(id, isGm, kind = "text") {
    const card = document.createElement("article");
    card.className = "journal-section-card";
    card.dataset.journalSection = "";
    card.dataset.sectionId = id;
    card.dataset.sectionKind = kind;
    card.draggable = true;
    card.innerHTML = `
      <header>
        <i class="ph ph-dots-six-vertical journal-section-grip" data-section-drag-handle aria-hidden="true"></i>
        <button type="button" class="journal-section-collapse" data-journal-section-collapse aria-expanded="true" aria-label="Recolher seção">
          <i class="ph ph-caret-down" aria-hidden="true"></i>
        </button>
        <input type="text" data-section-title maxlength="120" placeholder="Nova página" aria-label="Nome da página">
        <input type="text" data-section-category maxlength="80" placeholder="Sem capítulo" aria-label="Capítulo">
        <select data-section-kind aria-label="Tipo">
          <option value="text" ${kind === "text" ? "selected" : ""}>Texto</option>
          <option value="image" ${kind === "image" ? "selected" : ""}>Imagem</option>
          <option value="pdf" ${kind === "pdf" ? "selected" : ""}>PDF</option>
        </select>
        <select data-section-audience aria-label="Audiência">
          <option value="public">Mesa</option><option value="gm">Só mestre</option>
        </select>
        <button type="button" class="journal-mini-action is-danger" data-journal-section-remove aria-label="Remover seção">
          <i class="ph ph-trash" aria-hidden="true"></i>
        </button>
      </header>
      <div class="journal-block-field" data-journal-block-field>
        <div class="journal-block-editor-host" data-journal-block-editor data-is-gm="${isGm ? "true" : "false"}">
          <script type="application/json" data-journal-doc>${JSON.stringify(EMPTY_JOURNAL_DOC)}</script>
        </div>
        <input type="hidden" name="section_doc_${id}" data-journal-doc-input>
      </div>
      <div class="journal-page-asset" data-page-asset>
        <input type="hidden" data-page-src>
        <button type="button" data-page-asset-upload><i class="ph ph-upload-simple"></i> Enviar arquivo</button>
        <img data-page-image-preview alt="">
        <iframe data-page-pdf-preview title="Documento PDF"></iframe>
      </div>`;
    return card;
  }

  function syncJournalSections(scope) {
    const editor = scope.querySelector?.("[data-journal-sections-editor]")
      || scope.closest?.("[data-journal-sections-editor]");
    if (!editor) return;
    const sections = Array.from(editor.querySelectorAll("[data-journal-section]")).map((card, index) => {
      const docInput = card.querySelector("[data-journal-doc-input]");
      let content = EMPTY_JOURNAL_DOC;
      try { content = JSON.parse(docInput?.value || "{}"); } catch { }
      const kind = card.querySelector("[data-section-kind]")?.value || card.dataset.sectionKind || "text";
      card.dataset.sectionKind = kind;
      return {
        id: card.dataset.sectionId,
        title: card.querySelector("[data-section-title]")?.value.trim() || "Nova página",
        category: card.querySelector("[data-section-category]")?.value.trim() || "",
        kind,
        src: card.querySelector("[data-page-src]")?.value || "",
        level: 1,
        audience: card.querySelector("[data-section-audience]")?.value || "public",
        sortOrder: (index + 1) * 10,
        content,
      };
    });
    const output = editor.querySelector("[data-journal-sections-json]");
    if (output) output.value = JSON.stringify(sections);
  }

  function initDiarySections(modal) {
    const editor = modal.querySelector("[data-journal-sections-editor]");
    if (!editor) return;
    const form = editor.closest("[data-journal-editor]");
    const list = editor.querySelector("[data-journal-sections-list]");
    let dragCard = null;
    let dragFromHandle = false;

    editor.addEventListener("pointerdown", (event) => {
      dragFromHandle = !!event.target.closest("[data-section-drag-handle]");
    });
    const interactionRoot = editor.closest("[data-journal-diary-workspace]") || editor;
    interactionRoot.addEventListener("click", (event) => {
      const collapse = event.target.closest("[data-journal-section-collapse]");
      if (collapse) {
        const card = collapse.closest("[data-journal-section]");
        const collapsed = card.classList.toggle("is-collapsed");
        collapse.setAttribute("aria-expanded", String(!collapsed));
        return;
      }
      if (event.target.closest("[data-journal-section-add]")) {
        const add = event.target.closest("[data-journal-section-add]");
        const kind = add.dataset.journalAddKind || "text";
        const card = sectionCard(sectionId(), editor.dataset.isGm === "true", kind);
        list.appendChild(card);
        mountBlockEditorsIn(card);
        card.querySelector("[data-section-title]")?.focus();
        editor.dispatchEvent(new CustomEvent("journal:section-added", { detail: { card } }));
        scheduleAutosave(form);
        return;
      }
      const remove = event.target.closest("[data-journal-section-remove]");
      if (remove) {
        remove.closest("[data-journal-section]")?.remove();
        scheduleAutosave(form);
      }
    });
    editor.addEventListener("dragstart", (event) => {
      const card = event.target.closest("[data-journal-section]");
      if (!card || !dragFromHandle) { event.preventDefault(); return; }
      dragCard = card;
      card.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
    });
    editor.addEventListener("dragover", (event) => {
      if (!dragCard) return;
      const target = event.target.closest("[data-journal-section]");
      if (!target || target === dragCard) return;
      event.preventDefault();
      const rect = target.getBoundingClientRect();
      list.insertBefore(dragCard, event.clientY < rect.top + rect.height / 2 ? target : target.nextSibling);
    });
    editor.addEventListener("dragend", () => {
      dragCard?.classList.remove("is-dragging");
      dragCard = null;
      dragFromHandle = false;
      scheduleAutosave(form);
    });
    syncJournalSections(form);
  }

  function initNotebookNavigation(modal) {
    modal.addEventListener("click", (event) => {
      const link = event.target.closest("[data-journal-section-link]");
      if (!link) return;
      modal.querySelectorAll("[data-journal-section-link]").forEach((item) => {
        item.classList.toggle("is-active", item === link);
      });
      const notebook = link.closest("[data-journal-notebook]");
      if (notebook && modal.dataset.journalType === "diary") {
        notebook.querySelectorAll(".journal-notebook-section").forEach((page) => {
          page.hidden = page.id !== link.dataset.journalSectionLink;
        });
      } else {
        modal.querySelector(`#${CSS.escape(link.dataset.journalSectionLink)}`)
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
    if (modal.dataset.journalType === "diary") {
      const notebook = modal.querySelector("[data-journal-notebook]");
      const firstLink = notebook?.querySelector("[data-journal-section-link]");
      firstLink?.classList.add("is-active");
      notebook?.querySelectorAll(".journal-notebook-section").forEach((page, index) => { page.hidden = index !== 0; });
    }
  }

  // A quest is edited in four parts, reached from the rail on its left: the
  // player-visible content, the objectives, the rewards, and the GM's half.
  function initQuestWorkspace(modal) {
    const workspace = modal.querySelector("[data-quest-workspace]");
    if (!workspace) return;
    const tabs = Array.from(workspace.querySelectorAll("[data-quest-tab]"));
    const panels = Array.from(workspace.querySelectorAll("[data-quest-panel]"));
    if (!tabs.length) return;

    const titleProxy = workspace.querySelector("[data-quest-title-input]");
    const titleInput = modal.querySelector('[data-journal-editor-chrome] input[name="title"]');
    titleProxy?.addEventListener("input", () => {
      if (!titleInput) return;
      titleInput.value = titleProxy.value;
      titleInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    const activate = (name) => {
      tabs.forEach((tab) => {
        const active = tab.dataset.questTab === name;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-pressed", String(active));
      });
      panels.forEach((panel) => { panel.hidden = panel.dataset.questPanel !== name; });
    };

    // The rail carries how many objectives and rewards the quest already has,
    // so the master does not have to open a part to find it empty.
    const counts = () => {
      workspace.querySelectorAll("[data-quest-count]").forEach((slot) => {
        const rows = workspace.querySelector(`[data-${slot.dataset.questCount}-rows]`);
        const total = rows ? rows.querySelectorAll(".journal-list-row").length : 0;
        slot.textContent = total ? String(total) : "";
      });
    };

    workspace.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-quest-tab]");
      if (tab) activate(tab.dataset.questTab);
      else if (event.target.closest("[data-objective-add], [data-reward-add], [data-row-remove]")) counts();
    });
    workspace.addEventListener("input", counts);

    activate("content");
    counts();
  }

  function initDiaryWorkspace(modal) {
    const workspace = modal.querySelector("[data-journal-diary-workspace]");
    if (!workspace) return;
    const tabs = Array.from(workspace.querySelectorAll("[data-journal-diary-tab]"));
    const panes = Array.from(workspace.querySelectorAll("[data-journal-diary-pane]"));
    if (!tabs.length) return;
    const activate = (name) => {
      workspace.classList.toggle("is-gm-active", name === "gm");
      tabs.forEach((tab) => {
        const active = tab.dataset.journalDiaryTab === name;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-pressed", String(active));
      });
      panes.forEach((pane) => { pane.hidden = pane.dataset.journalDiaryPane !== name; });
    };
    workspace.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-journal-diary-tab]");
      // The GM control is a toggle, not a tab strip: pressing it again returns
      // to the pages, since there is no longer a rail to switch back from.
      if (tab) activate(tab.classList.contains("is-active") ? "content" : tab.dataset.journalDiaryTab);
    });
    activate("content");
  }

  function initDiaryPager(modal) {
    const main = modal.querySelector(".journal-diary-main");
    const workspace = main?.closest("[data-journal-diary-workspace]");
    const base = main?.querySelector("[data-journal-base-page]");
    const sections = main?.querySelector("[data-journal-sections-editor]");
    const list = main?.querySelector("[data-journal-sections-list]");
    const index = main?.querySelector("[data-journal-index-drawer]") || workspace?.querySelector("[data-journal-index-drawer]");
    const indexList = index?.querySelector("[data-journal-index-list]");
    const position = main?.querySelector("[data-journal-page-position]");
    const currentTitle = main?.querySelector("[data-journal-current-page-title]");
    const currentChapter = main?.querySelector("[data-journal-current-chapter]");
    const range = main?.querySelector("[data-journal-page-range]");
    if (!main || !workspace || !base || !sections || !list || !index || !indexList) return;
    // The contents manager is a real workspace column. Keeping it outside the
    // page prevents it from obscuring the journal while pages are managed.
    if (index.parentElement === main) workspace.insertBefore(index, main);
    const setIndexOpen = (open) => {
      index.hidden = !open;
      workspace.classList.toggle("is-index-open", open);
      main.querySelector("[data-journal-index-toggle]")?.setAttribute("aria-expanded", String(open));
    };
    const form = main.closest("[data-journal-editor]");
    let current = "cover";
    let indexReordering = false;

    const titleInput = modal.querySelector('[data-journal-editor-chrome] input[name="title"]');
    const journalTitle = () => titleInput?.value.trim()
      || modal.querySelector(".sheet-modal-name")?.textContent.trim()
      || "";

    const pages = () => [
      // The opening page is the journal itself: it wears the journal's name and
      // belongs to no chapter, so the toolbar must not invent one for it.
      { id: "cover", title: journalTitle(), node: base },
      ...Array.from(list.querySelectorAll("[data-journal-section]")).map((node, number) => ({
        id: node.dataset.sectionId,
        title: node.querySelector("[data-section-title]")?.value.trim() || `Página ${number + 2}`,
        category: node.querySelector("[data-section-category]")?.value.trim() || "",
        kind: node.querySelector("[data-section-kind]")?.value || node.dataset.sectionKind || "text",
        audience: node.querySelector("[data-section-audience]")?.value || "public",
        node,
      })),
    ];

    let kindFilter = "all";
    let gmOnly = false;
    const isGm = sections.dataset.isGm === "true";

    // The opening page has no row in the list; the home control stands for it.
    const heading = workspace.querySelector("[data-journal-heading]");
    const cardOf = (pageId) => list.querySelector(`[data-section-id="${CSS.escape(pageId || "")}"]`);
    const cardsInChapter = (chapter) => Array.from(list.querySelectorAll("[data-journal-section]")).filter((card) => {
      const value = card.querySelector("[data-section-category]")?.value.trim() || "";
      return chapter === "Sem capítulo" ? !value : value === chapter;
    });

    // Page settings are written straight onto the section card the index mirrors;
    // dispatching `change` lets the card's own listeners (kind → layout) react.
    const setPageField = (pageId, selector, value) => {
      const field = cardOf(pageId)?.querySelector(selector);
      if (!field) return;
      field.value = value;
      field.dispatchEvent(new Event("change", { bubbles: true }));
      scheduleAutosave(form);
      renderIndex();
    };

    const removePage = (pageId) => {
      const card = cardOf(pageId);
      if (!card) return;
      card.remove();
      scheduleAutosave(form);
      // Falls through to the empty state when that was the last page.
      openFirstPage();
    };

    const composer = workspace.querySelector("[data-journal-chapter-composer]");
    const composerInput = composer?.querySelector("[data-journal-chapter-name]");
    const toggleChapterComposer = (open) => {
      if (!composer) return;
      composer.hidden = !open;
      if (open) composerInput?.focus();
      else if (composerInput) composerInput.value = "";
    };
    // A chapter is a page carrying its name: the same shape the index groups by.
    const createChapter = () => {
      const name = composerInput?.value.trim();
      if (!name) return;
      const card = sectionCard(sectionId(), isGm, "text");
      card.querySelector("[data-section-category]").value = name.slice(0, 80);
      list.appendChild(card);
      mountBlockEditorsIn(card);
      sections.dispatchEvent(new CustomEvent("journal:section-added", { detail: { card } }));
      scheduleAutosave(form);
      toggleChapterComposer(false);
    };
    const renderIndex = () => {
      const allPages = pages();
      const chapters = new Map();
      allPages.forEach((page) => {
        if (page.id === "cover") return;
        const chapter = page.category || "Sem capítulo";
        if (!chapters.has(chapter)) chapters.set(chapter, []);
        chapters.get(chapter).push(page);
      });
      // The opening page has no row of its own: it is the journal, so the
      // heading above the list is what opens it.
      heading?.classList.toggle("is-active", current === "cover");
      const entries = new Map();
      allPages.forEach((page) => {
        if (page.id === "cover") return;
        const entry = document.createElement("div");
        entry.className = "journal-index-entry";
        entry.dataset.indexPageId = page.id;
        entry.dataset.pageKind = page.kind || "text";
        entry.classList.toggle("is-active", page.id === current);
        entry.draggable = true;
        const icons = { text: "ph-file-text", image: "ph-image", pdf: "ph-file-pdf" };
        // Page settings live in the right-click menu, so the row stays a row.
        entry.innerHTML = `
          <i class="ph ph-dots-six-vertical journal-index-grip" data-index-drag-handle aria-hidden="true"></i>
          <button type="button" class="journal-index-open" aria-label="Abrir página"><i class="ph ${icons[page.kind] || icons.text} journal-index-kind"></i><strong></strong>${page.audience === "gm" ? '<i class="ph ph-lock-key journal-index-lock"></i>' : ""}</button>`;
        entry.querySelector("strong").textContent = page.title;
        entry.querySelector(".journal-index-open").dataset.journalPageTarget = page.id;
        entries.set(page.id, entry);
      });
      const groups = Array.from(chapters, ([chapter, chapterPages]) => {
        const group = document.createElement("section");
        group.className = "journal-chapter-group";
        group.dataset.chapter = chapter;
        // An unnamed chapter has no header to show; its pages open the list.
        group.innerHTML = chapter
          ? `<header><button type="button" data-chapter-collapse aria-expanded="true"><i class="ph ph-caret-down"></i><strong></strong><span>${chapterPages.length}</span></button></header><div data-chapter-pages></div>`
          : `<div data-chapter-pages></div>`;
        if (chapter) group.querySelector("strong").textContent = chapter;
        group.querySelector("[data-chapter-pages]").append(...chapterPages.map((page) => entries.get(page.id)));
        return group;
      });
      indexList.replaceChildren(...groups);
      const chapterOptions = workspace.querySelector("[data-journal-chapter-options]");
      if (chapterOptions) {
        chapterOptions.replaceChildren(...Array.from(chapters.keys()).filter((name) => name && name !== "Sem capítulo").map((name) => {
          const option = document.createElement("option"); option.value = name; return option;
        }));
      }
      const query = workspace.querySelector("[data-journal-page-search]")?.value.trim().toLocaleLowerCase() || "";
      let visible = 0;
      indexList.querySelectorAll("[data-index-page-id]").forEach((entry) => {
        const page = allPages.find((item) => item.id === entry.dataset.indexPageId);
        const haystack = `${page?.title || ""} ${page?.category || ""}`.toLocaleLowerCase();
        const matchesSearch = !query || haystack.includes(query);
        const matchesKind = kindFilter === "all" || entry.dataset.pageKind === kindFilter;
        entry.hidden = !(matchesSearch && matchesKind && (!gmOnly || page?.audience === "gm"));
        if (!entry.hidden) visible += 1;
      });
      indexList.querySelectorAll(".journal-chapter-group").forEach((group) => {
        group.hidden = !group.querySelector("[data-index-page-id]:not([hidden])");
      });
      const empty = workspace.querySelector("[data-journal-index-empty]");
      if (empty) {
        empty.hidden = visible > 0;
        // A journal with no pages yet is not a search that found nothing.
        empty.textContent = allPages.length > 1
          ? "Nenhuma página corresponde à busca."
          : "Nenhuma página ainda.";
      }
    };

    const emptyState = main.querySelector("[data-journal-page-empty]");
    const toolbar = main.querySelector("[data-journal-page-toolbar]");

    // Nothing to open: the column carries the invitation to start writing
    // instead of an editor for a page that does not exist.
    const showEmptyState = () => {
      current = null;
      pages().forEach((page) => { page.node.hidden = true; });
      if (emptyState) emptyState.hidden = false;
      if (toolbar) toolbar.hidden = true;
      heading?.classList.remove("is-active");
      renderIndex();
    };

    const activate = (id) => {
      const all = pages();
      const selected = all.find((page) => page.id === id) || all[0];
      current = selected.id;
      if (emptyState) emptyState.hidden = true;
      if (toolbar) toolbar.hidden = false;
      workspace.classList.add("is-page-open");
      all.forEach((page) => { page.node.hidden = page !== selected; });
      sections.classList.toggle("is-showing-section", selected.node !== base);
      const pageNumber = all.indexOf(selected) + 1;
      if (position) position.textContent = `Página ${pageNumber} de ${all.length} · ${Math.round((pageNumber / all.length) * 100)}%`;
      if (currentTitle) currentTitle.textContent = selected.title;
      if (currentChapter) currentChapter.textContent = selected.id === "cover" ? "" : (selected.category || "Sem capítulo");
      if (range) { range.max = String(all.length); range.value = String(pageNumber); }
      // The pager buttons sit in the browser footer, next to the create action.
      const previous = workspace.querySelector("[data-journal-page-previous]");
      const next = workspace.querySelector("[data-journal-page-next]");
      if (previous) previous.disabled = pageNumber === 1;
      if (next) next.disabled = pageNumber === all.length;
      renderIndex();
    };

    const move = (amount) => {
      const all = pages();
      const target = all[all.findIndex((page) => page.id === current) + amount];
      if (target) activate(target.id);
    };
    workspace.addEventListener("click", (event) => {
      const collapseBrowser = event.target.closest("[data-journal-browser-collapse]");
      if (collapseBrowser) {
        workspace.classList.toggle("is-browser-collapsed");
        collapseBrowser.setAttribute("aria-expanded", String(!workspace.classList.contains("is-browser-collapsed")));
        return;
      }
      const filterToggle = event.target.closest("[data-journal-filter-toggle]");
      if (filterToggle) {
        const filters = workspace.querySelector("[data-journal-page-filters]");
        if (filters) filters.hidden = !filters.hidden;
        return;
      }
      const kindButton = event.target.closest("[data-journal-kind-filter]");
      if (kindButton) {
        kindFilter = kindButton.dataset.journalKindFilter;
        workspace.querySelectorAll("[data-journal-kind-filter]").forEach((button) => button.classList.toggle("is-active", button === kindButton));
        renderIndex();
        return;
      }
      const audienceButton = event.target.closest("[data-journal-audience-filter]");
      if (audienceButton) {
        gmOnly = audienceButton.classList.toggle("is-active");
        renderIndex();
        return;
      }
      const chapterToggle = event.target.closest("[data-chapter-collapse]");
      if (chapterToggle) {
        const group = chapterToggle.closest(".journal-chapter-group");
        const collapsed = group?.classList.toggle("is-collapsed");
        chapterToggle.setAttribute("aria-expanded", String(!collapsed));
        return;
      }
      if (event.target.closest("[data-journal-chapter-add]")) {
        // Naming happens inline; a window.prompt() drops the master out of the
        // game window and cannot be styled with the rest of the journal.
        toggleChapterComposer(composer?.hidden !== false);
        return;
      }
      if (event.target.closest("[data-journal-chapter-confirm]")) {
        createChapter();
        return;
      }
      if (event.target.closest("[data-journal-browser-show]")) {
        // Brings the list back from either state that hides it: collapsed on a
        // wide window, or pushed off-screen by the page on a narrow one.
        workspace.classList.remove("is-page-open", "is-browser-collapsed");
        workspace.querySelector("[data-journal-browser-collapse]")?.setAttribute("aria-expanded", "true");
        return;
      }
      if (event.target.closest("[data-journal-index-toggle]")) {
        setIndexOpen(index.hidden);
      } else if (event.target.closest("[data-journal-index-close]")) {
        setIndexOpen(false);
      } else if (event.target.closest("[data-journal-page-previous]")) move(-1);
      else if (event.target.closest("[data-journal-page-next]")) move(1);
      else if (event.target.closest("[data-page-asset-upload]")) {
        const card = event.target.closest("[data-journal-section]");
        const kind = card?.querySelector("[data-section-kind]")?.value || "image";
        const picker = document.createElement("input");
        picker.type = "file";
        picker.accept = kind === "pdf" ? "application/pdf" : "image/png,image/jpeg,image/webp";
        picker.addEventListener("change", async () => {
          const file = picker.files?.[0];
          if (!file || !card) return;
          const result = await FI.uploadJournalImage?.(modal.dataset.journalId || "", file);
          if (!result?.src) return;
          card.querySelector("[data-page-src]").value = result.src;
          const image = card.querySelector("[data-page-image-preview]");
          const pdf = card.querySelector("[data-page-pdf-preview]");
          if (image) image.src = result.src;
          if (pdf) pdf.src = result.src;
          scheduleAutosave(form, true);
        });
        picker.click();
      }
      else {
        const target = event.target.closest("[data-journal-page-target]");
        if (target) {
          activate(target.dataset.journalPageTarget);
          if (window.matchMedia("(max-width: 760px)").matches) setIndexOpen(false);
        }
      }
    });
    workspace.addEventListener("keydown", (event) => {
      if (event.target.matches("[data-journal-chapter-name]")) {
        if (event.key === "Enter") { event.preventDefault(); createChapter(); }
        else if (event.key === "Escape") { event.preventDefault(); toggleChapterComposer(false); }
        return;
      }
    });
    workspace.addEventListener("input", (event) => {
      if (event.target.matches("[data-journal-page-search]")) {
        renderIndex();
      } else if (event.target.matches("[data-journal-page-range]")) {
        const target = pages()[Number(event.target.value) - 1];
        if (target) activate(target.id);
      } else if (event.target.matches("[data-section-title]")) {
        if (event.target.closest("[data-journal-section]")?.dataset.sectionId === current) {
          currentTitle.textContent = event.target.value || "Sem título";
        }
        renderIndex();
      } else if (event.target.matches("[data-section-category]")) {
        const card = event.target.closest("[data-journal-section]");
        if (card?.dataset.sectionId === current && currentChapter) currentChapter.textContent = event.target.value.trim() || "Sem capítulo";
        renderIndex();
      } else if (event.target.matches("[data-section-kind]")) {
        const card = event.target.closest("[data-journal-section]");
        if (card) card.dataset.sectionKind = event.target.value;
        renderIndex();
      }
    });
    workspace.addEventListener("change", (event) => {
      if (event.target.matches("[data-section-kind]")) {
        const card = event.target.closest("[data-journal-section]");
        if (card) card.dataset.sectionKind = event.target.value;
        renderIndex();
      }
    });

    /* ---- Page context menu ------------------------------------------------
     * Renaming and filing a page happen in place on the index row; the rest of
     * the page's settings hang off the right-click menu the rest of the game
     * already uses (#ctx-menu), so the row itself stays a single line. */

    const startInlineEdit = (pageId, selector, { fallback = "", placeholder = "" } = {}) => {
      const entry = indexList.querySelector(`[data-index-page-id="${CSS.escape(pageId)}"]`);
      const field = cardOf(pageId)?.querySelector(selector);
      if (!entry || !field) return;
      const input = document.createElement("input");
      input.type = "text";
      input.className = "journal-index-rename";
      input.maxLength = selector.includes("category") ? 80 : 120;
      input.value = field.value;
      input.placeholder = placeholder;
      // Filing a page offers the chapters that already exist.
      const chapterOptions = workspace.querySelector("[data-journal-chapter-options]");
      if (selector.includes("category") && chapterOptions) input.setAttribute("list", chapterOptions.id);
      entry.classList.add("is-renaming");
      entry.appendChild(input);
      input.focus();
      input.select();
      let settled = false;
      const finish = (commit) => {
        if (settled) return;
        settled = true;
        if (commit) {
          field.value = input.value.trim() || fallback;
          field.dispatchEvent(new Event("input", { bubbles: true }));
          scheduleAutosave(form);
        }
        entry.classList.remove("is-renaming");
        renderIndex();
      };
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") { event.preventDefault(); finish(true); }
        else if (event.key === "Escape") { event.preventDefault(); finish(false); }
      });
      input.addEventListener("blur", () => finish(true));
    };

    const choice = (pageId, selector, currentValue, options) => options.map(([value, text]) => ({
      text,
      small: true,
      checked: currentValue === value,
      action: () => setPageField(pageId, selector, value),
    }));

    // Renaming a chapter is renaming the label its pages carry: there is no
    // chapter record of its own to edit.
    const renameChapter = (chapter) => {
      const header = indexList.querySelector(`.journal-chapter-group[data-chapter="${CSS.escape(chapter)}"] > header`);
      if (!header) return;
      const input = document.createElement("input");
      input.type = "text";
      input.className = "journal-index-rename";
      input.maxLength = 80;
      input.value = chapter === "Sem capítulo" ? "" : chapter;
      input.placeholder = "Nome do capítulo";
      header.replaceChildren(input);
      input.focus();
      input.select();
      let settled = false;
      const finish = (commit) => {
        if (settled) return;
        settled = true;
        if (commit) {
          const name = input.value.trim().slice(0, 80);
          cardsInChapter(chapter).forEach((card) => {
            const field = card.querySelector("[data-section-category]");
            if (field) field.value = name;
          });
          scheduleAutosave(form);
        }
        renderIndex();
      };
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") { event.preventDefault(); finish(true); }
        else if (event.key === "Escape") { event.preventDefault(); finish(false); }
      });
      input.addEventListener("blur", () => finish(true));
    };

    const addPageToChapter = (chapter) => {
      const card = sectionCard(sectionId(), isGm, "text");
      card.querySelector("[data-section-category]").value = chapter === "Sem capítulo" ? "" : chapter;
      list.appendChild(card);
      mountBlockEditorsIn(card);
      sections.dispatchEvent(new CustomEvent("journal:section-added", { detail: { card } }));
      scheduleAutosave(form);
    };

    const openPageMenu = (event, pageId) => {
      const menu = window.GravewrightContextMenuInternals;
      const page = pages().find((item) => item.id === pageId);
      const items = [
        { text: "Abrir", action: () => activate(pageId) },
        { text: "Renomear página", action: () => startInlineEdit(pageId, "[data-section-title]", { fallback: "Nova página" }) },
        { text: "Definir capítulo", action: () => startInlineEdit(pageId, "[data-section-category]", { placeholder: "Sem capítulo" }) },
      ];
      if (isGm) {
        items.push(
          { type: "sep" },
          { type: "label", text: "Audiência" },
          ...choice(pageId, "[data-section-audience]", page?.audience || "public",
            [["public", "Mesa"], ["gm", "Só mestre"]]),
        );
      }
      items.push({ type: "sep" }, {
        text: "Excluir página",
        danger: true,
        action: () => menu.showMenu(event.clientX, event.clientY, [{
          text: "Confirmar exclusão",
          danger: true,
          action: () => removePage(pageId),
        }]),
      });
      menu.showMenu(event.clientX, event.clientY, items);
    };

    const openChapterMenu = (event, chapter) => {
      const menu = window.GravewrightContextMenuInternals;
      const items = [{ text: "Nova página neste capítulo", action: () => addPageToChapter(chapter) }];
      if (chapter !== "Sem capítulo") {
        items.push(
          { text: "Renomear capítulo", action: () => renameChapter(chapter) },
          { type: "sep" },
          {
            text: "Desfazer capítulo",
            danger: true,
            action: () => menu.showMenu(event.clientX, event.clientY, [{
              // Only the label goes: the pages move to "Sem capítulo".
              text: "Confirmar: as páginas ficam sem capítulo",
              danger: true,
              action: () => {
                cardsInChapter(chapter).forEach((card) => {
                  const field = card.querySelector("[data-section-category]");
                  if (field) field.value = "";
                });
                scheduleAutosave(form);
                renderIndex();
              },
            }]),
          },
        );
      }
      menu.showMenu(event.clientX, event.clientY, items);
    };

    indexList.addEventListener("contextmenu", (event) => {
      if (!window.GravewrightContextMenuInternals?.showMenu) return;
      const entry = event.target.closest("[data-index-page-id]");
      if (entry) {
        event.preventDefault();
        openPageMenu(event, entry.dataset.indexPageId);
        return;
      }
      const group = event.target.closest(".journal-chapter-group");
      if (group) {
        event.preventDefault();
        openChapterMenu(event, group.dataset.chapter);
      }
    });

    let draggedIndexId = null;
    let indexDragFromHandle = false;
    indexList.addEventListener("pointerdown", (event) => {
      indexDragFromHandle = !!event.target.closest("[data-index-drag-handle]");
    });
    indexList.addEventListener("dragstart", (event) => {
      const entry = event.target.closest("[data-index-page-id]");
      if (!entry?.draggable || !indexDragFromHandle) { event.preventDefault(); return; }
      draggedIndexId = entry.dataset.indexPageId;
      indexReordering = true;
      entry.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
    });
    indexList.addEventListener("dragover", (event) => {
      if (!draggedIndexId) return;
      const targetEntry = event.target.closest("[data-index-page-id]");
      if (!targetEntry || targetEntry.dataset.indexPageId === "cover" || targetEntry.dataset.indexPageId === draggedIndexId) return;
      const draggedCard = list.querySelector(`[data-section-id="${CSS.escape(draggedIndexId)}"]`);
      const targetCard = list.querySelector(`[data-section-id="${CSS.escape(targetEntry.dataset.indexPageId)}"]`);
      if (!draggedCard || !targetCard) return;
      event.preventDefault();
      const rect = targetEntry.getBoundingClientRect();
      list.insertBefore(draggedCard, event.clientY < rect.top + rect.height / 2 ? targetCard : targetCard.nextSibling);
    });
    indexList.addEventListener("dragend", () => {
      draggedIndexId = null;
      indexDragFromHandle = false;
      indexReordering = false;
      indexList.querySelector(".is-dragging")?.classList.remove("is-dragging");
      scheduleAutosave(form);
      renderIndex();
    });
    sections.addEventListener("journal:section-added", (event) => {
      const card = event.detail.card;
      // A page created while a chapter is open belongs to that chapter. The
      // chapter menu and the chapter composer file their own pages, so an
      // existing value is left alone.
      const field = card.querySelector("[data-section-category]");
      if (field && !field.value.trim()) {
        const open = pages().find((page) => page.id === current);
        if (open?.category) field.value = open.category;
      }
      activate(card.dataset.sectionId);
    });
    new MutationObserver(() => {
      if (indexReordering) return;
      if (pages().some((page) => page.id === current)) activate(current);
      else openFirstPage();
    })
      .observe(list, { childList: true });
    // Renaming the journal renames the page the toolbar is showing.
    titleInput?.addEventListener("input", () => {
      if (current === "cover" && currentTitle) currentTitle.textContent = journalTitle();
    });

    // The diary opens on its first page: the first of the first chapter, since
    // the index groups pages in list order. The opening page stays one click
    // away, on the home control.
    const openFirstPage = () => {
      const first = pages().find((page) => page.id !== "cover");
      if (first) activate(first.id);
      else showEmptyState();
    };

    openFirstPage();
  }

  FI.syncJournalSections = syncJournalSections;



  function initBoardAdmin(modal) {
    const admin = modal.querySelector("[data-board-admin]");
    if (!admin) return;
    const boardId = admin.dataset.boardId;

    const refresh = () => reloadJournalModal(boardId, "editor");

    admin.querySelector("[data-board-add-quest]")?.addEventListener("click", async () => {
      const select = admin.querySelector("[data-board-quest-select]");
      const questId = select?.value;
      if (!questId) return;
      if (await boardPost("/game/journal/board/add", { board_id: boardId, quest_id: questId })) refresh();
    });

    admin.addEventListener("change", async (event) => {
      const statusSelect = event.target.closest("[data-board-quest-status]");
      if (!statusSelect) return;
      const entry = statusSelect.closest("[data-board-entry]");
      if (!entry) return;
      statusSelect.disabled = true;
      const changed = await boardPost("/game/journal/quest/status", {
        journal_id: entry.dataset.boardEntry,
        status: statusSelect.value,
      });
      if (changed) refresh();
      else statusSelect.disabled = false;
    });

    admin.addEventListener("click", async (event) => {
      const filterButton = event.target.closest("[data-board-status-filter]");
      if (filterButton) {
        const active = filterButton.getAttribute("aria-pressed") !== "true";
        filterButton.setAttribute("aria-pressed", String(active));
        filterButton.classList.toggle("is-active", active);
        const enabled = new Set(
          Array.from(admin.querySelectorAll('[data-board-status-filter][aria-pressed="true"]'))
            .map((button) => button.dataset.boardStatusFilter),
        );
        admin.querySelectorAll("[data-board-entry]").forEach((row) => {
          row.hidden = !enabled.has(row.dataset.boardStatus);
        });
        return;
      }

      const entry = event.target.closest("[data-board-entry]");
      if (!entry) return;
      const questId = entry.dataset.boardEntry;

      if (event.target.closest("[data-board-remove]")) {
        if (await boardPost("/game/journal/board/remove", { board_id: boardId, quest_id: questId })) refresh();
        return;
      }
      const pinBtn = event.target.closest("[data-board-pin]");
      if (pinBtn) {
        if (await boardPost("/game/journal/board/pin", { board_id: boardId, quest_id: questId, pinned: pinBtn.dataset.boardPin }))
          refresh();
        return;
      }
      const moveBtn = event.target.closest("[data-board-move]");
      if (moveBtn) {
        const list = admin.querySelector("[data-board-entries]");
        const rows = Array.from(list.querySelectorAll("[data-board-entry]"));
        const index = rows.indexOf(entry);
        const target = moveBtn.dataset.boardMove === "up" ? index - 1 : index + 1;
        if (target < 0 || target >= rows.length) return;
        const ordered = rows.map((r) => r.dataset.boardEntry);
        [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
        const params = new URLSearchParams({ csrf_token: csrfToken(), board_id: boardId });
        ordered.forEach((id) => params.append("quest_ids", id));
        const res = await fetch("/game/journal/board/reorder", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
          body: params,
          credentials: "same-origin",
        });
        if (res.ok) refresh();
      }
    });
  }



  function setJournalView(modal, view) {
    modal.dataset.journalMode = view;
    modal.querySelectorAll("[data-journal-view]").forEach((el) => {
      el.hidden = el.dataset.journalView !== view;
    });
    modal.querySelectorAll("[data-journal-reader-chrome]").forEach((el) => { el.hidden = view === "editor"; });
    modal.querySelectorAll("[data-journal-editor-chrome]").forEach((el) => { el.hidden = view !== "editor"; });
    modal.querySelectorAll("[data-journal-edit-toggle]").forEach((button) => {
      const isEditor = view === "editor";
      const label = button.querySelector("[data-journal-toggle-label]");
      if (label) label.textContent = isEditor ? button.dataset.labelBack : button.dataset.labelEdit;
      const icon = button.querySelector("i");
      if (icon) {
        icon.classList.toggle("ph-pencil-simple", !isEditor);
        icon.classList.toggle("ph-arrow-left", isEditor);
      }
    });
    if (view === "editor") {

      modal.querySelectorAll("[data-journal-editor] [data-journal-rich-text]").forEach((t) => {
        editors.get(t)?.codemirror.refresh();
      });
    }
  }

  function initJournalModal(modal) {
    if (initialized.has(modal)) return;
    initialized.add(modal);
    const diaryEditor = modal.dataset.journalType === "diary" && modal.querySelector("[data-journal-editor]");
    modal.dataset.journalMode = diaryEditor ? "editor" : (modal.querySelector('[data-journal-view="editor"]:not([hidden])')
      ? "editor" : "reader");
    setJournalView(modal, modal.dataset.journalMode);
    initRichTextIn(modal);
    renderMarkdownIn(modal);
    mountBlockEditorsIn(modal);
    mountDocReadersIn(modal);
    initQuestEditors(modal);
    initImageUpload(modal);
    initBoardAdmin(modal);
    initDiarySections(modal);
    initQuestWorkspace(modal);
    initDiaryWorkspace(modal);
    initDiaryPager(modal);
    initNotebookNavigation(modal);
    syncCreateTypeFields(modal);

    const editForm = modal.querySelector("[data-journal-editor]");
    if (editForm) {
      editForm.addEventListener("input", () => scheduleAutosave(editForm));
      editForm.addEventListener("change", () => scheduleAutosave(editForm));
      editForm.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
          event.preventDefault();
          scheduleAutosave(editForm, true);
        }
      });
      const windowTitle = modal.querySelector('[data-journal-editor-chrome] input[name="title"]');
      windowTitle?.addEventListener("input", () => scheduleAutosave(editForm));
      windowTitle?.addEventListener("change", () => scheduleAutosave(editForm));
    }


    modal.addEventListener("click", async (event) => {
      if (event.target.closest("[data-modal-close]") && editForm && isEditorVisible(modal)) {
        scheduleAutosave(editForm, true);
      }
      if (event.target.closest("[data-journal-edit-toggle]")) {
        if (isEditorVisible(modal)) {
          if (editForm) scheduleAutosave(editForm, true);
          setJournalView(modal, "reader");
        } else {
          setJournalView(modal, "editor");
        }
      }
    });

    modal.addEventListener("submit", (event) => {
      const form = event.target.closest("form");
      if (form) flushEditors(form);

      if (form && form.matches("[data-journal-editor]")) {
        event.preventDefault();
        scheduleAutosave(editForm, true);
      }
    });
  }

  async function reloadJournalModal(journalId, keepView) {
    const modal = document.querySelector(`[data-modal-id="journal-${CSS.escape(journalId)}"]`);
    if (!modal) return;
    try {
      const res = await fetch(`/game/journal/modal/${encodeURIComponent(journalId)}`, {
        credentials: "same-origin",
        headers: { Accept: "text/html" },
      });
      if (!res.ok) return;
      const html = (await res.text()).trim();
      const template = document.createElement("template");
      template.innerHTML = html;
      const next = template.content.querySelector("[data-modal-window]");
      if (!next) return;
      next.hidden = false;
      destroyBlockEditorsIn(modal);
      modal.replaceWith(next);
      initJournalModal(next);

      if (keepView === "editor" && next.querySelector("[data-journal-editor]")) {
        setJournalView(next, "editor");
      }
    } catch {

    }
  }

  function isEditorVisible(modal) {
    return !!modal.querySelector('[data-journal-view="editor"]:not([hidden])');
  }

  function reloadOpenQuestBoardsForCampaign(campaignId, keepEditor = true) {
    if (!campaignId) return;
    document
      .querySelectorAll(
        `[data-journal-type="quest_board"][data-journal-campaign="${CSS.escape(campaignId)}"]`,
      )
      .forEach((modal) => {
        const boardId = modal.dataset.journalId;
        if (boardId) reloadJournalModal(boardId, keepEditor && isEditorVisible(modal) ? "editor" : undefined);
      });
  }

  function syncCreateTypeFields(modal) {
    const typeSelect = modal.querySelector("[data-journal-create-type]");
    if (!typeSelect) return;
    const update = () => {
      modal.querySelectorAll("[data-journal-type-fields]").forEach((block) => {
        const visible = block.dataset.journalTypeFields === typeSelect.value;
        block.hidden = !visible;
        if (visible) {

          block.querySelectorAll("[data-journal-rich-text]").forEach((textarea) => {
            const editor = editors.get(textarea);
            if (editor) editor.codemirror.refresh();
          });
        }
      });
      const form = modal.querySelector("[data-journal-create-form]");
      if (form) form.dataset.journalType = typeSelect.value;
      const submit = modal.querySelector("[data-journal-create-submit]");
      const label = submit?.querySelector("span");
      if (submit && label) {
        const key = typeSelect.value === "quest_board" ? "labelQuestBoard"
          : typeSelect.value === "quest" ? "labelQuest" : "labelDiary";
        label.textContent = submit.dataset[key] || label.textContent;
      }
    };
    typeSelect.addEventListener("change", update);
    update();
  }



  const JOURNAL_EVENTS = new Set([
    "journal.updated",
    "quest.status_changed",
    "quest.objective_updated",
    "quest_board.updated",
  ]);

  document.addEventListener("vtt:transport-event", (event) => {
    const envelope = event.detail || {};
    const payload = envelope.payload || {};
    const journalId = payload.journal_id;
    if (!journalId) return;

    if (envelope.event === "journal.deleted") {
      const modal = document.querySelector(`[data-modal-id="journal-${CSS.escape(journalId)}"]`);
      modal?.querySelector("[data-modal-close]")?.click();
      modal?.remove();
      if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
      return;
    }

    if (envelope.event === "journal.created" && payload.type === "quest") {
      reloadOpenQuestBoardsForCampaign(payload.room_id);
      return;
    }

    if (JOURNAL_EVENTS.has(envelope.event)) {
      const modal = document.querySelector(`[data-modal-id="journal-${CSS.escape(journalId)}"]`);
      if (!modal) {
        if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
        return;
      }



      const editorForm = modal.querySelector("[data-journal-editor]");
      if (editorForm && !editorForm.hidden) {
        if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
        return;
      }
      reloadJournalModal(journalId);
      if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
    }
  });



  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-journal-panel]").forEach(initPanel);
    document.querySelectorAll("[data-journal-modal]").forEach((body) => {
      const modal = body.closest("[data-modal-window]");
      if (modal) initJournalModal(modal);
    });
    applyJournalFolderColors(document);
  });

  document.addEventListener("vtt:journal-modal-mounted", (event) => {
    const modal = event.detail?.modal;
    if (modal) initJournalModal(modal);
  });

  FI.openJournalEditor = (modal) => {
    if (modal?.querySelector("[data-journal-editor]")) setJournalView(modal, "editor");
  };
})();
