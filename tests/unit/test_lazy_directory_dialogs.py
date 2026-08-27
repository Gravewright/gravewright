from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_directory_dialogs_are_disabled_in_initial_game_render() -> None:
    game = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")

    assert game.count("eager_directory_dialogs|default(false)") == 5


def test_directory_dialog_bundle_contains_all_supported_modal_ids() -> None:
    fragment = (ROOT / "templates/pages/game/_directory_dialogs.html").read_text(encoding="utf-8")

    for modal_id in (
        "actor-create-", "actor-folder-create-", "item-create-",
        "item-folder-create-", "journal-folder-create-",
    ):
        assert modal_id in fragment


def test_modal_manager_fetches_missing_directory_dialog_bundle() -> None:
    manager = (ROOT / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")
    remote = (ROOT / "static/js/ui/modals/modal-remote.js").read_text(encoding="utf-8")

    assert "modalRemote.ensureDirectoryDialogs" in manager
    assert "/game/directory-dialogs/" in remote
    assert 'template.content.querySelectorAll("[data-modal-window]")' in remote


def test_scene_creation_dialogs_are_a_separate_lazy_bundle() -> None:
    game = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    fragment = (ROOT / "templates/pages/game/_scene_create_dialogs.html").read_text(encoding="utf-8")
    manager = (ROOT / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")
    remote = (ROOT / "static/js/ui/modals/modal-remote.js").read_text(encoding="utf-8")

    assert game.count("eager_scene_create_dialogs|default(false)") == 2
    assert "scene-create-{{ room.id }}" in fragment
    assert "scene-group-create-{{ room.id }}" in fragment
    assert "data-upload-progress-form" in fragment
    assert "data-upload-progress" in fragment
    assert "ensureSceneCreateDialogs" in manager
    assert "/game/scenes/create-dialogs/" in remote
