from __future__ import annotations

import re
from pathlib import Path

from litestar.testing import TestClient

from app.engine.actors.actor_service import ActorService
from app.persistence.database import engine_begin
from app.persistence.repositories.token_repository import TokenRepository
from app.domain.roles import PlayerRole
from tests.conftest import (
    TEST_SESSION_CONFIG,
    login,
    seed_actor,
    seed_campaign,
    install_system,
    seed_member,
    seed_scene,
    seed_system,
    seed_user,
)


def test_game_page_renders_for_gm_with_manifest_system(db):
    """The /game page renders end-to-end with the legacy sheet panel removed:
    only the Actor Core path (Actors panel + manifest active system) remains."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-render@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)
    seed_actor(campaign_id, gm_id, name="Aria", data={"hp": {"value": 8, "max": 10}})

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.get("/game")

    assert resp.status_code == 200
    assert "panel-actors-" in resp.text
    assert "dnd5e" in resp.text
                                                    
    assert "panel-sheets-" not in resp.text
                                                                       
    assert "panel-items-" in resp.text
    assert "data-item-panel" in resp.text


def test_area_marker_presets_present_without_active_scene(db):
    """Attaching a system must expose its area-marker presets on the canvas even
    before a map is uploaded — the presets come from the system, not the scene."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-presets-noscene@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.get(f"/game?room={campaign_id}")

    assert resp.status_code == 200

    assert "data-area-marker-presets=" in resp.text
    assert "dnd5e-spell-sphere" in resp.text
    assert "sheets/items/item-sheet-controller.js" in resp.text
    assert "items/items-panel.js" in resp.text
    assert "pixi-board-renderer.js" in resp.text
    assert "canvas-board-renderer.js" not in resp.text
    assert "combat/combat-api.js" in resp.text
    assert resp.text.index("combat/combat-api.js") < resp.text.index("systems/dnd5e/asset/assets/dnd5e-sheets.js")


def test_system_combat_api_v1_hooks_are_exposed():
    api = Path("static/js/combat/combat-api.js").read_text()
    panel = Path("static/js/combat/combat-panel.js").read_text()

    assert "window.GravewrightCombat" in api
    assert "registerSystem" in api
    assert "callHook" in api
    assert "renderSlot" in api
    assert '"beforeRender"' in panel
    assert '"afterRender"' in panel
    assert '"participantMeta"' in panel
    assert '"participantActions"' in panel


def test_detached_remote_modals_are_loaded_before_opening():
    manager = Path("static/js/ui/modals/modal-manager.js").read_text()
    actions = Path("static/js/ui/modals/modal-window-actions.js").read_text()

    assert "async function ensureModalReady(modalId)" in manager
    assert '{ prefix: "actor-", ensure: ensureActorSheetModal }' in manager
    assert '{ prefix: "token-", ensure: ensureTokenSheetModal }' in manager
    assert '{ prefix: "item-", ensure: ensureItemSheetModal }' in manager
    assert '{ prefix: "journal-", ensure: ensureJournalModal }' in manager
    assert '{ prefix: "scene-edit-", ensure: ensureSceneEditModal }' in manager
    assert "ensureModalReady(detachedModalId).then" in manager
    assert 'url.searchParams.set("room", activeRoom)' in actions


def test_vendored_pixijs_includes_canvas_renderer_fallback():
    pixi = Path("static/vendor/pixi.min.js").read_text()

    assert "CanvasRenderer" in pixi
    assert "CanvasRenderer is not yet implemented" not in pixi
    assert "sourceMappingURL=pixi.min.js.map" not in pixi


def test_streamer_game_page_is_readonly_frontend(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-streamer-render@test.com")
    streamer_id = seed_user(name="Streamer", email="streamer-render@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, streamer_id, PlayerRole.STREAMER.value)
    seed_system(campaign_id, gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, streamer_id)
        resp = client.get(f"/game?room={campaign_id}")

    assert resp.status_code == 200
    assert 'data-current-member-role="streamer"' in resp.text
    assert 'data-streamer-mode="true"' in resp.text
    assert 'data-is-streamer="true"' in resp.text
    assert 'data-is-readonly="true"' in resp.text
    assert 'data-is-gm="true"' in resp.text
    assert 'data-chat-form' not in resp.text
    assert 'data-tool-dock' in resp.text
    assert 'data-tool="hp"' not in resp.text
    assert f'data-modal-id="panel-gm-{campaign_id}"' in resp.text
    assert f'data-modal-id="fog-panel-{campaign_id}"' in resp.text
    assert f'data-modal-id="scene-manager-{campaign_id}"' not in resp.text
    assert 'href="/inside"' not in resp.text
    assert "streamer-readonly-note" in resp.text
    assert "game.streamer.readonly_note" not in resp.text


def test_map_camera_and_streaming_use_css_viewport_before_pixi_initializes():
                                                                                
                                                                            
    controller = Path("static/js/map/map-controller.js").read_text()
    streaming = Path("static/js/map/streaming/map-streaming.js").read_text()
    assert "function viewportSizeFor(canvas)" in controller
    assert "CAMERA_STORAGE_VERSION = 2" in controller
    assert "function cameraIntersectsScene(canvas, scene, camera)" in controller
    assert "CHUNK_STREAM_MAX_RETRIES = 5" in controller
    assert "function scheduleChunkStreamRetry(canvas, scene, layerIds, range)" in controller
    assert "meta.version < knownVersion" in streaming
    assert "debugSnapshot" in controller
    assert "canvas.width / dpr" not in controller
    assert "canvas.height / dpr" not in controller


def test_streamer_frontend_blocks_write_realtime_commands():
    realtime = Path("static/js/realtime/realtime-client.js").read_text()
    fog = Path("static/js/fog/fog-commands.js").read_text()
    measures = Path("static/js/map/measures/map-measure-controller.js").read_text()
    add_to_scene = Path("static/js/map/add-to-scene/map-add-to-scene.js").read_text()
    toolbar = Path("static/js/tools/tools-toolbar.js").read_text()

    assert "STREAMER_ALLOWED_COMMANDS" in realtime
    assert '"viewport.subscribe"' in realtime
    assert '"viewport.update"' in realtime
    assert '"chunk.ack"' in realtime
    assert 'document.body?.dataset?.streamerMode === "true"' in realtime
    assert "FI.appendLocalOp(sceneId, op)" in fog
    assert "applyLocalMeasureCommand" in measures
    assert "placeLocalTokens" in add_to_scene
    assert 'streamerMode() && tool === "hp"' in toolbar


def test_map_streaming_uses_local_cache_for_reopened_viewports():
    streaming = Path("static/js/map/streaming/map-streaming.js").read_text()
    events = Path("static/js/map/events/map-realtime-events.js").read_text()

    assert "gravewright.sceneChunks." in streaming
    assert "gravewright.sceneInfo." in streaming
    assert "function viewportReadyFromCache(runtime, manifest, layerIds, range)" in streaming
    assert "missingVisibleChunkKeys(runtime, layerIds, range).length" in streaming
    assert "runtime.lastViewportKey = viewportKey" in streaming
    assert "handleViewportReady(payload)" in streaming
    assert 'evtName === "scene.viewport.ready") handleViewportReady(payload)' in events


def test_pixi_tiles_load_from_focus_outward_and_scene_runtime_is_cached():
    tile_layer = Path("static/js/board/pixi/pixi-tile-layer.js").read_text()
    renderer = Path("static/js/board/pixi/pixi-board-renderer.js").read_text()
    layers = Path("static/js/board/pixi/pixi-board-layers.js").read_text()
    controller = Path("static/js/map/map-controller.js").read_text()
    streaming = Path("static/js/map/streaming/map-streaming.js").read_text()

    assert "cells.sort((a, b) => a.dist - b.dist)" in tile_layer
    assert "frameSnapshot" not in renderer
    assert "frameSnapshot" not in layers
    assert "captureFrame" not in controller
    assert "captureFrame" not in streaming
    assert "sceneRuntimeCache: new Map()" in streaming
    assert "tokenRuntimeCache: new Map()" in streaming
    assert "function saveSceneRuntime(canvas, sceneId, tileVersion)" in streaming
    assert "function restoreSceneRuntime(canvas, sceneId, tileVersion)" in streaming
    assert "saveSceneRuntime(canvas, previousSceneId, previousTileVersion)" in streaming
    assert "restoreSceneRuntime(canvas, scenePayload.id, nextTileVersion)" in streaming


def test_scene_tokens_snapshot_reflects_actor(db):
    """A scene token linked to an actor projects the actor's name + HP bar."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-render-tokens@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)
    scene = seed_scene(campaign_id)
    actor_id = seed_actor(campaign_id, gm_id, name="Monstro Modelo", data={"hp": {"value": 4, "max": 7}})
    TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.get(f"/game/scenes/{scene['id']}/tokens")

    assert resp.status_code == 200
    tokens = resp.json()["tokens"]
    assert len(tokens) == 1
    assert tokens[0]["name"] == "Monstro Modelo"
    assert tokens[0]["actor_id"] == actor_id
    assert tokens[0]["bars"]["hp"] == {"value": 4, "max": 7, "visibility": "everyone"}


def test_csp_allows_journal_cdn_scripts_and_inline_styles(db):
    """The journal rich-text editor (EasyMDE/marked/DOMPurify) loads from the
    jsDelivr CDN and folder colors use inline styles — the CSP must permit both."""
    from main import app

    with TestClient(app=app) as client:
        resp = client.get("/login")
    csp = resp.headers.get("content-security-policy", "")
    script_src = csp.split("script-src")[1].split(";")[0]
    assert "script-src" in csp and "https://cdn.jsdelivr.net" in script_src
    assert "https://esm.sh" in script_src                                     
    assert "style-src" in csp and "'unsafe-inline'" in csp.split("style-src")[1].split(";")[0]


def test_open_specific_table_activates_the_chosen_room(db):
    """Entering ?room=<my campaign> must activate THAT campaign's workspace,
    even when another table the user belongs to was updated more recently
    (regression: clicking "open" on my table dropped me into a friend's table)."""
    from main import app

    me = seed_user(name="Me", email="me-room@test.com")
    friend = seed_user(name="Friend", email="friend-room@test.com")

    my_campaign = seed_campaign(me, title="My Table")
    friend_campaign = seed_campaign(friend, title="Friend Table")
    seed_member(friend_campaign, me, PlayerRole.ASSISTANT_GM.value)

                                                                         
    with engine_begin() as conn:
        conn.exec_driver_sql(
            "UPDATE campaigns SET updated_at = updated_at + 1000 WHERE id = ?",
            (friend_campaign,),
        )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, me)
                                                                    
        page = client.get(f"/game?room={my_campaign}")
        assert page.status_code == 200
        assert re.search(
            r'room-workspace is-active"\s+data-room-id="' + re.escape(my_campaign) + r'"', page.text
        )
        assert not re.search(
            r'room-workspace is-active"\s+data-room-id="' + re.escape(friend_campaign) + r'"',
            page.text,
        )

                                                                                  
                                                     
        foreign = client.get("/game?room=does-not-exist")
        assert foreign.status_code == 200
        assert re.search(
            r'room-workspace is-active"\s+data-room-id="' + re.escape(friend_campaign) + r'"',
            foreign.text,
        )


def test_create_dialogs_and_no_system_constraint(db):
    """The Actors panel exposes Create Actor / Create Folder dialogs. Without an
    enabled system the GM can still create folders but not actors."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-dialogs@test.com")
    with_system = seed_campaign(gm_id, title="Has System")
    seed_system(with_system, gm_id)
    without_system = seed_campaign(gm_id, title="No System")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        page = client.get(f"/game?room={with_system}")
        assert f'data-modal-id="actor-create-{with_system}"' in page.text
        assert f'data-modal-id="actor-folder-create-{with_system}"' in page.text
        assert f'data-modal-open="actor-create-{with_system}"' in page.text                

        page2 = client.get(f"/game?room={without_system}")
                                                                                    
        assert f'data-modal-id="actor-create-{without_system}"' not in page2.text
        assert f'data-modal-open="actor-create-{without_system}"' not in page2.text
        assert f'data-modal-id="actor-folder-create-{without_system}"' in page2.text
        assert f'data-modal-id="system-onboarding-{without_system}"' in page2.text
        assert "data-system-onboarding-modal" in page2.text
        assert "data-panel-ajax-form" not in re.search(
            rf'<form method="post" action="/campaigns/set-system".*?</form>',
            page2.text,
            re.S,
        ).group(0)

        linked = client.post(
            "/campaigns/set-system",
            data={"campaign_id": without_system, "system_id": "dnd5e"},
            follow_redirects=False,
        )
        assert linked.status_code in {302, 303}

        linked_page = client.get(f"/game?room={without_system}")
        assert f'data-modal-id="actor-create-{without_system}"' in linked_page.text
        assert f'data-modal-open="actor-create-{without_system}"' in linked_page.text
        assert f'data-modal-id="item-create-{without_system}"' in linked_page.text
        assert f'data-modal-open="item-create-{without_system}"' in linked_page.text
        assert f'data-modal-id="system-onboarding-{without_system}"' not in linked_page.text


def test_item_create_dialog_uses_only_active_campaign_system(db):
    """Creating an Item from a campaign should expose only the campaign's
    assigned system item types, even when other systems are enabled globally."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-item-active-system@test.com")
    campaign_id = seed_campaign(gm_id, title="DND Table")
    seed_system(campaign_id, gm_id, package_id="dnd5e")
    install_system(gm_id, package_id="dnd5e")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        page = client.get(f"/game?room={campaign_id}")

    assert page.status_code == 200
    match = re.search(
        rf'data-modal-id="item-create-{re.escape(campaign_id)}".*?</article>',
        page.text,
        re.S,
    )
    assert match is not None
    modal_html = match.group(0)

    assert 'value="dnd5e::weapon"' in modal_html
    assert 'value="dnd5e::spell"' in modal_html
    assert "Dungeons &amp; Dragons 5e —" not in modal_html
    assert "Dungeons & Dragons 5e —" not in modal_html


def test_journal_modal_opens_reader_first_with_edit_toggle(db):
    """Journals open in a read-only view for everyone; editors get an Edit toggle
    and an auto-saving editor (no Save button); viewers get the reader only."""
    from main import app
    from app.engine.journals.journal_service import JournalService

    gm_id = seed_user(name="GM", email="gm-journalui@test.com")
    player_id = seed_user(name="P", email="p-journalui@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Lore",
        visibility="shared",
        content_markdown="# Hello",
    )
    assert created.success
    jid = created.journal_id

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        gm = client.get(f"/game/journal/modal/{jid}")
        assert gm.status_code == 200
        assert "data-journal-reader" in gm.text                         
        assert "data-journal-edit-toggle" in gm.text                     
        assert "data-journal-editor" in gm.text                           
        assert "data-journal-read-toggle" in gm.text                       
        assert "ph-floppy-disk" not in gm.text                  
        assert "journal-meta-grid" not in gm.text                                     
        assert 'name="folder_id"' in gm.text                            
        assert 'name="visibility"' in gm.text

                                                                                 
        client.set_session_data({"user_id": player_id})
        pl = client.get(f"/game/journal/modal/{jid}")
        assert pl.status_code == 200
        assert "data-journal-reader" in pl.text
        assert "data-journal-edit-toggle" not in pl.text
        assert "data-journal-editor" not in pl.text


def test_journals_panel_fragment_and_folder_color(db):
    """The Journals panel refreshes in place via a fragment endpoint, folders carry
    their color, and the create-folder (with color) dialog is on the page."""
    from main import app
    from app.engine.journals.journal_service import JournalService

    gm_id = seed_user(name="GM", email="gm-jfrag@test.com")
    outsider = seed_user(name="Out", email="out-jfrag@test.com")
    campaign_id = seed_campaign(gm_id)
    folder = JournalService().create_folder(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Lore",
        color="#8ea8ff",
    )
    assert folder.success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        frag = client.get(f"/game/journals/panel/{campaign_id}")
        assert frag.status_code == 200
        assert "Lore" in frag.text
        assert 'data-folder-color="#8ea8ff"' in frag.text

                                                                                   
        page = client.get(f"/game?room={campaign_id}")
        assert f'data-modal-id="journal-folder-create-{campaign_id}"' in page.text
        assert "data-journal-folder-create-form" in page.text
        assert "data-journal-tree-host" in page.text

                                                                  
        client.set_session_data({"user_id": outsider})
        denied = client.get(
            f"/game/journals/panel/{campaign_id}",
            follow_redirects=False,
        )
        assert denied.status_code in (302, 303, 307)


def test_quest_board_renders_admin_in_editor_and_cards_in_reader(db):
    """A quest board shows linked quest cards in the reader and the add/remove
    admin only inside the editor view (it must not leak into the reader)."""
    from main import app
    from app.engine.journals.journal_service import JournalService

    gm_id = seed_user(name="GM", email="gm-board@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = JournalService()
    board = svc.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest_board",
        title="Board",
    )
    quest = svc.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="Slay the dragon",
        visibility="shared",
    )
    assert board.success and quest.success
    added = svc.add_quest_to_board(
        board_id=board.journal_id,
        quest_id=quest.journal_id,
        requester_user_id=gm_id,
    )
    assert added.success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        page = client.get(f"/game/journal/modal/{board.journal_id}")
    assert page.status_code == 200
    assert "Slay the dragon" in page.text                                 
    assert "data-board-admin" in page.text                       
                                                                           
    admin_pos = page.text.index("data-board-admin")
    editor_wrapper = page.text.rfind('data-journal-view="editor"', 0, admin_pos)
    assert editor_wrapper != -1


def test_actor_permissions_post_ajax(db):
    """Saving actor permissions via AJAX returns JSON (no redirect/reload) and
    applies the grant — the panel refreshes from the broadcast, not a page reload."""
    from main import app
    from app.persistence.repositories.actor_repository import ActorRepository

    gm_id = seed_user(name="GM", email="gm-permpost@test.com")
    player_id = seed_user(name="P1", email="p1-permpost@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    seed_system(campaign_id, gm_id)
    actor_id = seed_actor(campaign_id, gm_id, name="NPC")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.post(
            "/game/resource-permissions",
            data={
                "resource_type": "actor",
                "resource_id": actor_id,
                f"access__{player_id}": "owner",
            },
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
    assert ActorRepository().has_owner(actor_id=actor_id, user_id=player_id)


def test_actors_panel_fragment_endpoint(db):
    """The Actors panel fragment (used to refresh in place without a page reload)
    renders for a member and refuses a non-member's campaign."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-frag@test.com")
    outsider = seed_user(name="Outsider", email="outsider-frag@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)
    folder = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="Crew")
    actor_id = seed_actor(campaign_id, gm_id, name="Bilbo")
    ActorService().move_actor(actor_id=actor_id, target_folder_id=folder.folder_id, user_id=gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        ok = client.get(f"/game/actors/panel/{campaign_id}")
        assert ok.status_code == 200
        assert "Crew" in ok.text
        assert f'data-actor-card="{actor_id}"' in ok.text
        assert 'draggable="true"' in ok.text                              

                                                                         
        client.set_session_data({"user_id": outsider})
        denied = client.get(
            f"/game/actors/panel/{campaign_id}",
            follow_redirects=False,
        )
        assert denied.status_code in (302, 303, 307)


def test_actor_folders_render_and_permissions_modal(db):
    """The Actors panel renders the folder tree and the per-actor permissions
    modal endpoint serves the generic resource-permissions form."""
    from main import app

    gm_id = seed_user(name="GM", email="gm-actor-perms@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)
    folder = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="Villains")
    actor_id = seed_actor(campaign_id, gm_id, name="Vecna")
    ActorService().move_actor(actor_id=actor_id, target_folder_id=folder.folder_id, user_id=gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        page = client.get("/game")
        assert page.status_code == 200
        assert "Villains" in page.text
        assert f'data-actor-folder="{folder.folder_id}"' in page.text

        modal = client.get(f"/game/resource-permissions/actor/{actor_id}")
        assert modal.status_code == 200
        assert "data-resource-permissions" not in modal.text                              
        assert f"resource-permissions-actor-{actor_id}" in modal.text


def test_quest_and_board_modals_render_with_block_editor(db):
    """Quest (public description + GM notes/secrets) and board (description) rich
    fields use the gw-journal-doc-v1 block editor; the modal must render."""
    from main import app
    from app.engine.journals.journal_service import JournalService

    gm_id = seed_user(name="GM", email="gm-qbmodal@test.com")
    campaign_id = seed_campaign(gm_id)
    quest = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="Crypt",
        visibility="shared",
        data={"public": {"summary": "s"}},
    )
    board = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest_board",
        title="Board",
        visibility="shared",
    )
    assert quest.success and board.success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        q = client.get(f"/game/journal/modal/{quest.journal_id}")
        assert q.status_code == 200
        assert 'name="public_description_doc"' in q.text
        assert 'name="gm_notes_doc"' in q.text
        assert 'name="gm_secrets_doc"' in q.text
        assert "data-journal-editor-labels" in q.text
        assert "public_description_markdown" not in q.text                        

        b = client.get(f"/game/journal/modal/{board.journal_id}")
        assert b.status_code == 200
        assert 'name="board_description_doc"' in b.text
        assert "board_description_markdown" not in b.text
