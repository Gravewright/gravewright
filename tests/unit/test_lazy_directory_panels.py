from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_initial_game_html_omits_directory_tree_fragments() -> None:
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")

    for partial in ("_actors_panel.html", "_items_panel.html", "_journals_panel.html", "_scenes_panel.html"):
        assert f'include "pages/game/{partial}"' not in template
    for kind in ("actors", "items", "journals", "scenes"):
        assert f'data-lazy-directory-kind="{kind}"' in template


def test_directory_hydration_is_tied_to_panel_opening() -> None:
    loader = (ROOT / "static/js/ui/lazy-directory-panels.js").read_text(encoding="utf-8")

    assert 'document.addEventListener("vtt:modal-opened"' in loader
    assert 'host.dataset.directoryLoaded === "true"' in loader
    assert "refreshJournalPanel" in loader
    assert "GravewrightScenes?.refreshPanel" in loader


def test_realtime_refreshes_do_not_hydrate_never_opened_directories() -> None:
    sources = [
        ROOT / "static/js/actors/actors-panel.js",
        ROOT / "static/js/items/items-panel.js",
        ROOT / "static/js/journals/journals-panel.js",
    ]

    for source in sources:
        assert 'dataset.directoryLoaded === "true"' in source.read_text(encoding="utf-8")
