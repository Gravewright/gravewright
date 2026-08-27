from jinja2 import ChainableUndefined, Environment, FileSystemLoader


def _render_detached(modal_id: str) -> str:
    environment = Environment(
        loader=FileSystemLoader("templates"),
        undefined=ChainableUndefined,
    )
    environment.globals.update(t=lambda key: key, csrf_token=lambda: "token")
    template = environment.get_template("pages/game/index.html")
    return template.render(
        locale="pt-BR",
        app_name="Gravewright",
        asset_version="test",
        rooms=[],
        active_room_id="",
        system_styles=[],
        system_scripts=[],
        game_client_context_json="{}",
        sdk_client_manifests_json="[]",
        user={"id": "user-1"},
        detached_modal=modal_id,
        dynamic_lighting_enabled=False,
        command_palette_enabled=False,
        campaign_join_code_enabled=False,
        targeted_handouts_enabled=False,
        lobby_ready_check_enabled=False,
    )


def test_detached_actor_loads_only_the_sheet_runtime():
    html = _render_detached("actor-actor-1")

    assert "actor-sheet-controller.js" in html
    assert "item-sheet-controller.js" in html  # embedded actor items
    assert "journal-modal.js" not in html
    _assert_table_runtimes_are_absent(html)


def test_detached_journal_loads_only_the_journal_runtime():
    html = _render_detached("journal-journal-1")

    assert "journal-modal.js" in html
    assert "actor-sheet-controller.js" not in html
    assert "item-sheet-controller.js" not in html
    _assert_table_runtimes_are_absent(html)


def test_detached_item_loads_only_the_item_runtime():
    html = _render_detached("item-item-1")

    assert "item-sheet-controller.js" in html
    assert "actor-sheet-controller.js" not in html
    assert "journal-modal.js" not in html
    _assert_table_runtimes_are_absent(html)


def _assert_table_runtimes_are_absent(html: str) -> None:
    assert 'class="game-modal-layer"' in html
    assert "core-audio-runtime.js" not in html
    assert "native-sound-ui.js" not in html
    assert "pixi.min.js" not in html
    assert "data-map-canvas" not in html
    assert "chat-controller.js" not in html

