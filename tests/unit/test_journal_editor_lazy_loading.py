from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_game_does_not_eagerly_load_heavy_journal_editors() -> None:
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")

    assert '<script type="module" src="/static/js/journals/block-editor.js' not in template
    assert '<script defer src="/static/vendor/easymde/easymde.min.js' not in template
    assert '<script defer src="/static/vendor/marked.min.js' not in template
    assert '<script defer src="/static/vendor/purify.min.js' not in template
    assert '<link rel="stylesheet" href="/static/vendor/easymde/easymde.min.css' not in template
    assert "/static/js/journals/journal-editor-assets.js" in template


def test_journal_assets_are_loaded_on_first_matching_editor() -> None:
    loader = (ROOT / "static/js/journals/journal-editor-assets.js").read_text(encoding="utf-8")
    editor = (ROOT / "static/js/journals/journal-editor.js").read_text(encoding="utf-8")
    preview = (ROOT / "static/js/journals/journal-preview.js").read_text(encoding="utf-8")

    assert 'module("/static/js/journals/block-editor.js")' in loader
    assert 'classic("/static/vendor/easymde/easymde.min.js", "EasyMDE")' in loader
    assert 'classic("/static/vendor/marked.min.js", "marked")' in loader
    assert "loadBlockEditor" in editor
    assert "loadEasyMDE" in editor
    assert "loadMarkdown" in preview


def test_hidden_journal_modals_do_not_trigger_editor_loading_at_boot() -> None:
    modal = (ROOT / "static/js/journals/journal-modal.js").read_text(encoding="utf-8")
    docking = (ROOT / "static/js/ui/modals/modal-docking.js").read_text(encoding="utf-8")

    assert "if (modal && (!modal.hidden || detached)) initJournalModal(modal);" in modal
    assert 'document.addEventListener("vtt:modal-opened"' in modal
    assert 'new CustomEvent("vtt:modal-opened"' in docking
