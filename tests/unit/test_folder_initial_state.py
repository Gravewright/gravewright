from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_every_tab_folder_starts_collapsed() -> None:
    for template_name in ("_actors_panel.html", "_items_panel.html", "_journals_panel.html"):
        template = (ROOT / "templates/pages/game" / template_name).read_text(encoding="utf-8")
        folder_declaration = template.split("<div class=\"sheet-folder-body", 1)[0]

        assert "data-open" not in folder_declaration
        assert '<div class="sheet-folder-body" hidden>' in template


def test_panel_refresh_preserves_only_explicitly_open_folders() -> None:
    scripts = (
        ROOT / "static/js/actors/actors-api.js",
        ROOT / "static/js/items/items-api.js",
        ROOT / "static/js/journals/journal-api.js",
    )

    for script_path in scripts:
        script = script_path.read_text(encoding="utf-8")
        assert "[data-open]" in script
        assert "expanded" in script
        assert "setFolderOpen(f, true)" in script or "setJournalFolderOpen(f, true)" in script


def test_directory_drag_ux_is_shared_by_all_three_directories() -> None:
    page = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    helper = (ROOT / "static/js/ui/directory-drag.js").read_text(encoding="utf-8")

    assert "directory-drag.js" in page
    assert "source.contains(targetFolder)" in helper
    assert 'sourceParentId !== targetFolderId' in helper
    assert "setTimeout" in helper
    assert "setOpen(folder, true)" in helper

    for script_name in (
        "static/js/actors/actors-drag.js",
        "static/js/items/items-drag.js",
        "static/js/journals/journals-panel.js",
    ):
        script = (ROOT / script_name).read_text(encoding="utf-8")
        assert "GravewrightDirectoryDrag?.start" in script
        assert "GravewrightDirectoryDrag?.canDrop" in script
        assert "GravewrightDirectoryDrag?.end" in script

    actors_drag = (ROOT / "static/js/actors/actors-drag.js").read_text(encoding="utf-8")
    items_drag = (ROOT / "static/js/items/items-drag.js").read_text(encoding="utf-8")
    journals_drag = (ROOT / "static/js/journals/journals-panel.js").read_text(encoding="utf-8")
    assert 'event.target.closest("[data-actor-panel]")' in actors_drag
    assert 'event.target.closest("[data-item-panel]")' in items_drag
    assert 'e.target.closest("[data-journal-panel]")' in journals_drag
    assert "visual: Boolean(folderEl)" in actors_drag
    assert "visual: Boolean(folderEl)" in items_drag
    assert "visual: Boolean(folder)" in journals_drag


def test_folder_drag_requires_the_visible_handle() -> None:
    for script_name in (
        "static/js/actors/actors-drag.js",
        "static/js/items/items-drag.js",
        "static/js/journals/journals-panel.js",
    ):
        script = (ROOT / script_name).read_text(encoding="utf-8")
        assert 'closest(".sheet-folder-drag-handle")' in script
        assert "folderDragFromHandle" in script


def test_folder_context_menu_uses_combined_name_and_color_editor() -> None:
    page = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    editor = (ROOT / "static/js/ui/context-menu/folder-editor.js").read_text(encoding="utf-8")

    assert "folder-editor.js" in page
    assert 'name="name"' in editor
    assert 'name="color"' in editor
    assert '${basePath}/rename' in editor
    assert '${basePath}/color' in editor
    assert '"/game/journal/folder"' in editor

    for script_name in (
        "static/js/ui/context-menu/actor-context-menu.js",
        "static/js/ui/context-menu/item-context-menu.js",
        "static/js/ui/context-menu/journal-context-menu.js",
    ):
        script = (ROOT / script_name).read_text(encoding="utf-8")
        assert "openFolderEditor" in script
        assert 'window.prompt(label("ctxActorFolderRename")' not in script
        assert '["#b9995d", "#8ea8ff"' not in script


def test_add_subfolder_reuses_create_folder_modal() -> None:
    page = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    editor = (ROOT / "static/js/ui/context-menu/folder-editor.js").read_text(encoding="utf-8")
    assert page.count('type="hidden" name="parent_id"') >= 2
    assert "openFolderCreateModal" in editor
    assert "prepareCreateForm" in editor

    for kind in ("actor", "item", "journal"):
        context_menu = (ROOT / f"static/js/ui/context-menu/{kind}-context-menu.js").read_text(encoding="utf-8")
        panel_name = "journals/journals-panel.js" if kind == "journal" else f"{kind}s/{kind}s-panel.js"
        panel = (ROOT / f"static/js/{panel_name}").read_text(encoding="utf-8")
        assert "openFolderCreateModal" in context_menu
        assert "parentId: folderId" in context_menu
        assert "parent_id: parentId" in panel


def test_context_menus_do_not_offer_resource_movement() -> None:
    forbidden = (
        "ctxActorMoveToFolder",
        "ctxActorMoveToRoot",
        "ctxActorFolderMoveRoot",
        'moveActor(actorId, ""',
        'moveItem(itemId, ""',
        'folder/move",',
    )
    for script_name in (
        "static/js/ui/context-menu/actor-context-menu.js",
        "static/js/ui/context-menu/item-context-menu.js",
        "static/js/ui/context-menu/journal-context-menu.js",
    ):
        script = (ROOT / script_name).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in script


def test_actor_folder_context_menu_can_create_actor_in_folder() -> None:
    page = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    editor = (ROOT / "static/js/ui/context-menu/folder-editor.js").read_text(encoding="utf-8")
    menu = (ROOT / "static/js/ui/context-menu/actor-context-menu.js").read_text(encoding="utf-8")
    panel = (ROOT / "static/js/actors/actors-panel.js").read_text(encoding="utf-8")

    assert 'type="hidden" name="folder_id"' in page
    assert "openActorCreateModal" in editor
    assert "prepareActorCreateForm" in editor
    assert "FI.openActorCreateModal?.({ campaignId, folderId })" in menu
    assert "folder_id: folderId" in panel


def test_folder_context_modals_open_by_the_right_panel_and_remain_draggable() -> None:
    editor = (ROOT / "static/js/ui/context-menu/folder-editor.js").read_text(encoding="utf-8")
    assert 'document.querySelector(".game-modal-layer")' in editor
    assert "openNearRight" in editor
    assert "panelRect.left - layerRect.left - modal.offsetWidth" in editor
    assert "modals?.setPosition(modal, x, y)" in editor
    assert 'data-modal-drag-handle' in editor
    assert 'game-modal-drag-grip' in editor


def test_folder_hover_uses_its_own_color_without_increasing_intensity() -> None:
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    assert "var(--folder-color, var(--accent)) 4%" in css
    assert "var(--folder-color, var(--accent)) 7%" in css


def test_journal_directory_does_not_draw_an_extra_frame_around_entries() -> None:
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    journal_directory_rule = css.split(".journal-directory {", 1)[1].split("}", 1)[0]
    assert "border: 0" in journal_directory_rule
    assert "background: transparent" in journal_directory_rule


def test_actor_and_journal_directories_use_item_spacing() -> None:
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    actor_panel_rule = css.split(".actor-panel-body {", 1)[1].split("}", 1)[0]
    journal_panel_rule = css.split(".journal-panel-body {", 1)[1].split("}", 1)[0]
    journal_list_rule = css.split(".journal-list {", 1)[1].split("}", 1)[0]
    assert "padding: 8px" in actor_panel_rule
    assert "padding: 8px" in journal_panel_rule
    assert "gap: 0" in actor_panel_rule
    assert "gap: 0" in journal_panel_rule
    assert "gap: 2px" in journal_list_rule
    assert "padding: 0" in journal_list_rule
    assert ".journal-tree-host" in css


def test_modal_auto_fit_does_not_add_a_global_empty_height() -> None:
    manager = (ROOT / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")
    layout = (ROOT / "static/js/ui/modals/modal-layout.js").read_text(encoding="utf-8")
    assert "DEFAULT_FIT_HEIGHT" not in manager
    assert 'modal.classList.contains("dialog-modal") ? 0 : minWindowHeight' in layout
    assert "explicitMinFitHeight ?? contentHeightFloor" in layout
    assert 'dataNumber(modal, "autoFitMinHeight") || defaultFitHeight' not in layout


def test_diary_notebook_has_distinct_sections_and_drag_reordering() -> None:
    template = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    assert "journal-notebook-rail" in template
    assert "data-journal-sections-editor" in template
    assert "data-section-audience" in template
    assert "data-section-drag-handle" in template
    assert "syncJournalSections" in script
    assert 'event.target.closest("[data-section-drag-handle]")' in script


def test_journal_workspace_is_wide_readable_and_sections_can_collapse() -> None:
    template = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    assert "data-journal-section-collapse" in template
    assert 'card.classList.toggle("is-collapsed")' in script
    assert "width: min(920px" in css
    assert ".game-modal-window.journal-modal--readonly" in css
    assert "data-auto-fit-width=" in template
    assert ".journal-modal--create" in css
    assert "grid-template-columns: 220px minmax(0, 1fr)" in css


def test_modal_geometry_is_scoped_per_user_and_clamped_to_the_viewport() -> None:
    manager = (ROOT / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")
    layout = (ROOT / "static/js/ui/modals/modal-layout.js").read_text(encoding="utf-8")
    assert 'document.body.dataset.currentUserId || "anonymous"' in manager
    assert 'gravewright.game.window.${windowOwner}.' in manager
    assert "const restoredWidth =" in layout
    assert "const restoredHeight =" in layout
    assert "modal.style.width = `${restoredWidth}px`" in layout
    assert "modal.style.height = `${restoredHeight}px`" in layout


def test_create_and_permission_modals_open_next_to_their_resource_panel() -> None:
    manager = (ROOT / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")
    assert "function positionModalNearPanel" in manager
    assert "panelRect.left - layerRect.left - modal.offsetWidth - margin" in manager
    assert 'const createMatch = modalId.match(/^(actor|item)-create-(.+)$/)' in manager
    assert "positionModalNearPanel(modalId, resourceType" in manager
    assert 'positionModalNearPanel(modalId, "journal", { campaignId })' in manager


def test_player_sees_interface_settings_once_per_table() -> None:
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/game/settings-navigation.js").read_text(encoding="utf-8")
    assert 'data-member-role="{{ room.member_role }}"' in template
    assert "function openPlayerFirstVisit" in script
    assert 'settingsPanel.dataset.memberRole !== "player"' in script
    assert 'fetch("/game/player-onboarding/claim"' in script
    assert "localStorage" not in script
    assert "if (payload.show === true)" in script
    assert "window.GravewrightModalInternals?.open?.(modalId)" in script


def test_journal_editor_regions_cannot_shrink_and_overlap() -> None:
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    assert ".journal-modal .journal-editor-form > *" in css
    assert ".journal-modal .journal-content-field--blocks .journal-block-field" in css
    assert "flex: 0 0 auto" in css
    assert "journal-editorial-workspace-3" in template


def test_diary_editor_separates_gm_area_into_private_tab() -> None:
    modal = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    assert "{% if is_gm %}" in modal
    assert 'data-journal-diary-tab="gm"' in modal
    assert 'data-journal-diary-pane="gm" hidden' in modal
    assert 'data-journal-diary-pane="content"' in modal
    assert "initDiaryWorkspace(modal)" in script
    assert ".journal-modal .journal-diary-tabs" in css


def test_diary_opens_in_pages_without_a_legacy_cover_field() -> None:
    modal = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    assert "This diary has no cover" in modal
    assert 'name="diary_image_src"' not in modal


def test_diary_uses_editorial_navigation_for_reader_and_editor() -> None:
    modal = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    assert "data-journal-index-toggle" not in modal
    assert "data-journal-page-previous" not in modal
    assert "data-journal-page-next" not in modal
    assert "data-journal-page-position" not in modal
    assert "data-journal-page-range" not in modal
    assert "data-journal-current-page-title" in modal
    assert "initDiaryPager(modal)" in script
    assert 'pane.hidden = pane.dataset.journalDiaryPane !== name' in script
    assert 'page.node.hidden = page !== selected' in script
    assert ".journal-modal .journal-index-drawer" in css
    assert "Editorial journal: unified reader/editor workspace" in css
    assert "grid-template-columns: 46px 252px minmax(0, 1fr)" in css
    assert "journal-diary-workspace--editorial" in modal
    assert "journal-reader--editorial" in modal
    assert "data-journal-page-search" in modal
    assert "entry.dataset.indexPageId = page.id" in script
    assert "entry.querySelector(\"strong\").textContent = page.title" in script


def test_kindle_goto_inserts_only_text_image_and_pdf_pages() -> None:
    modal = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    for kind in ("text", "image", "pdf"):
        assert f'data-journal-add-kind="{kind}"' in modal
    for kind in ("page", "chapter", "section", "subsection"):
        assert f'data-journal-add-kind="{kind}"' not in modal
    assert "data-journal-insert-heading" not in modal
    assert "card.dataset.sectionKind = kind" in script
    assert "data-section-kind" in modal
    assert 'entry.dataset.pageKind = page.kind || "text"' in script
    assert "data-page-asset-upload" in modal
    assert "window.GravewrightJournalPdfViewer?.mount" in script
    assert ".journal-modal .journal-page-asset" in css


def test_text_page_hierarchy_is_provided_by_slash_rich_text_commands() -> None:
    editor = (ROOT / "static/js/journals/block-editor.js").read_text(encoding="utf-8")
    assert 'id: "h1"' in editor
    assert 'id: "h2"' in editor
    assert 'id: "h3"' in editor
    assert 'setNode("heading", { level: 2 })' in editor


def test_journal_editor_uses_single_window_header_and_manageable_index() -> None:
    modal = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    assert 'data-journal-editor-chrome hidden' in modal
    assert 'form="journal-editor-form-{{ journal.id }}"' in modal
    assert '<header class="journal-editor-head">' not in modal
    assert "entry.dataset.pageKind" in script
    assert "journal-index-open" in script
    assert "data-index-drag-handle" in script
    assert ".journal-modal .journal-index-entry" in css
    assert "journal-index-manage" not in script


def test_journal_interaction_uses_ordered_autosave_instead_of_save_button() -> None:
    create = (ROOT / "templates/pages/game/_journal_create_modal.html").read_text(encoding="utf-8")
    modal = (ROOT / "templates/pages/game/_journal_modal.html").read_text(encoding="utf-8")
    editor = (ROOT / "static/js/journals/journal-editor.js").read_text(encoding="utf-8")
    interaction = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    assert 't("game.journal.save")' not in create
    assert 'ph-floppy-disk' not in create
    assert 'data-journal-create-submit' in create
    assert 't("game.journal.create_type." ~ default_type)' in create
    assert "data-saving-label" in modal and 'aria-live="polite"' in modal
    assert "autosaveQueues" in editor
    assert "previous.catch(() => false).then(() => performAutosave(form))" in editor
    assert "setTimeout(() => autosaveJournal(form), 700)" in editor
    assert 'event.key.toLowerCase() === "s"' in interaction


def test_journal_create_uses_context_defaults_without_folder_or_visibility_selectors() -> None:
    create = (ROOT / "templates/pages/game/_journal_create_modal.html").read_text(encoding="utf-8")
    assert 'type="hidden" name="folder_id" value="{{ default_folder_id or \'\' }}"' in create
    assert 'type="hidden" name="visibility" value="private"' in create
    assert '<select name="folder_id">' not in create
    assert '<select name="visibility">' not in create
