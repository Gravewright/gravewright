from __future__ import annotations

from litestar.router import Router

from app.actions.game.ban_member import ban_member
from app.actions.game.manage_actor_folders import actors_panel_fragment
from app.actions.game.manage_actor_folders import create_actor_folder
from app.actions.game.manage_actor_folders import delete_actor_folder
from app.actions.game.manage_actor_folders import move_actor
from app.actions.game.manage_actor_folders import move_actor_folder
from app.actions.game.manage_actor_folders import rename_actor_folder
from app.actions.game.manage_actor_folders import set_actor_folder_color
from app.actions.game.manage_actor_folders import toggle_actor_owner
from app.actions.game.invite_to_campaign import invite_to_campaign
from app.actions.game.leave import leave_game
from app.actions.game.manage_scenes import activate_scene
from app.actions.game.manage_scenes import create_scene_group
from app.actions.game.manage_scenes import delete_scene
from app.actions.game.manage_scenes import scene_edit_modal
from app.actions.game.manage_scenes import update_scene
from app.actions.game.manage_scenes import update_scene_start_point
from app.actions.game.manage_scenes import upload_scene_map
from app.actions.game.manage_actors import create_actor
from app.actions.game.manage_actors import delete_actor as delete_actor_core
from app.actions.game.manage_actors import drop_on_actor
from app.actions.game.manage_actors import execute_action
from app.actions.game.manage_actors import execute_item_action
from app.actions.game.manage_actors import get_content_pack
from app.actions.game.manage_actors import import_content_entry
from app.actions.game.manage_actors import list_content_packs
from app.actions.game.manage_actors import get_sheet_bundle
from app.actions.game.manage_actors import get_sheet_data
from app.actions.game.manage_actors import get_token_sheet_bundle
from app.actions.game.manage_actors import patch_item_instance
from app.actions.game.manage_actors import patch_sheet_data
from app.actions.game.manage_actors import patch_token_sheet_data
from app.actions.game.manage_actors import remove_item_instance
from app.actions.game.manage_actors import roll_actor_formula
from app.actions.game.manage_actors import set_sheet_data
from app.actions.game.manage_actors import serve_actor_image
from app.actions.game.manage_actors import show_actor_sheet_modal
from app.actions.game.manage_actors import show_token_sheet_modal
from app.actions.game.manage_actors import update_actor_core
from app.actions.game.manage_actors import upload_actor_image
from app.actions.game.manage_combat import add_combat_participants
from app.actions.game.manage_combat import end_combat
from app.actions.game.manage_combat import get_combat_state
from app.actions.game.manage_combat import next_combat_round
from app.actions.game.manage_combat import next_combat_round_v1
from app.actions.game.manage_combat import next_combat_turn
from app.actions.game.manage_combat import previous_combat_turn
from app.actions.game.manage_combat import remove_combat_participant
from app.actions.game.manage_combat import roll_combat_initiative
from app.actions.game.manage_combat import roll_combat_monster_initiative
from app.actions.game.manage_combat import roll_combat_participant_initiative
from app.actions.game.manage_combat import set_combat_turn
from app.actions.game.manage_combat import start_combat
from app.actions.game.manage_item_folders import create_item_folder
from app.actions.game.manage_item_folders import delete_item_folder
from app.actions.game.manage_item_folders import items_panel_fragment
from app.actions.game.manage_item_folders import move_item
from app.actions.game.manage_item_folders import move_item_folder
from app.actions.game.manage_item_folders import rename_item_folder
from app.actions.game.manage_item_folders import set_item_folder_color
from app.actions.game.manage_item_folders import toggle_item_owner
from app.actions.game.manage_items import create_item
from app.actions.game.manage_items import delete_item
from app.actions.game.manage_items import get_item_sheet_bundle
from app.actions.game.manage_items import get_item_sheet_data
from app.actions.game.manage_items import import_item_content
from app.actions.game.manage_items import patch_item_sheet_data
from app.actions.game.manage_items import set_item_sheet_data
from app.actions.game.manage_items import show_item_sheet_modal
from app.actions.game.manage_items import update_item_core
from app.actions.game.manage_journals import board_add_quest
from app.actions.game.manage_journals import board_pin_quest
from app.actions.game.manage_journals import board_remove_quest
from app.actions.game.manage_journals import board_reorder
from app.actions.game.manage_journals import create_journal
from app.actions.game.manage_journals import create_journal_folder
from app.actions.game.manage_journals import journals_panel_fragment
from app.actions.game.manage_journals import delete_journal
from app.actions.game.manage_journals import move_journal
from app.actions.game.manage_journals import move_journal_folder
from app.actions.game.manage_journals import serve_journal_asset
from app.actions.game.manage_journals import set_quest_status
from app.actions.game.manage_journals import show_journal_create_modal
from app.actions.game.manage_journals import show_journal_modal
from app.actions.game.manage_journals import toggle_journal_owner
from app.actions.game.manage_journals import toggle_quest_objective
from app.actions.game.manage_journals import update_journal
from app.actions.game.manage_module_content import get_module_content_pack
from app.actions.game.manage_module_content import import_module_content_entry
from app.actions.game.manage_module_content import list_module_content_packs
from app.actions.game.manage_journals import upload_journal_asset
from app.actions.game.resource_permissions import show_resource_permissions
from app.actions.game.resource_permissions import update_resource_permissions
from app.actions.game.send_chat_message import clear_chat_messages
from app.actions.game.send_chat_message import delete_chat_message
from app.actions.game.send_chat_message import send_chat_message
from app.actions.game.serve_scene_image import serve_scene_image
from app.actions.game.serve_scene_tile import serve_scene_tile
from app.actions.game.module_settings import update_module_setting
from app.actions.game.scene_manifest import get_scene_manifest
from app.actions.game.scene_tokens import get_scene_tokens
from app.actions.game.scene_tokens import update_token_hp
from app.actions.game.show_game import show_game
from app.actions.game.show_permissions_popup import show_permissions_popup
from app.actions.game.streamer_link import consume_streamer_link
from app.actions.game.streamer_link import generate_streamer_link
from app.actions.game.streamer_link import revoke_streamer_link
from app.actions.game.update_permissions import update_campaign_permissions
from app.actions.game.update_layout_preference import update_layout_preference
from app.actions.game.update_table_settings import update_table_settings
from app.actions.game.websocket import game_websocket
from app.helpers.auth import require_user


                                                                                 
                                                                                   
                                                                
_protected_handlers = [
    show_game,
    get_scene_manifest,
    get_scene_tokens,
    update_token_hp,
    serve_scene_image,
    serve_scene_tile,
    update_module_setting,
    leave_game,
    create_scene_group,
    activate_scene,
    update_scene,
    delete_scene,
    scene_edit_modal,
    update_scene_start_point,
    upload_scene_map,
    create_actor,
    update_actor_core,
    upload_actor_image,
    serve_actor_image,
    get_combat_state,
    start_combat,
    add_combat_participants,
    remove_combat_participant,
    roll_combat_initiative,
    roll_combat_monster_initiative,
    roll_combat_participant_initiative,
    next_combat_turn,
    previous_combat_turn,
    set_combat_turn,
    next_combat_round_v1,
    next_combat_round,
    end_combat,
    delete_actor_core,
    get_sheet_data,
    get_sheet_bundle,
    get_token_sheet_bundle,
    patch_sheet_data,
    patch_token_sheet_data,
    set_sheet_data,
    execute_action,
    execute_item_action,
    patch_item_instance,
    remove_item_instance,
    roll_actor_formula,
    show_actor_sheet_modal,
    show_token_sheet_modal,
    list_content_packs,
    get_content_pack,
    drop_on_actor,
    import_content_entry,
    create_journal,
    update_journal,
    list_module_content_packs,
    get_module_content_pack,
    import_module_content_entry,
    delete_journal,
    set_quest_status,
    toggle_quest_objective,
    board_add_quest,
    board_remove_quest,
    board_reorder,
    board_pin_quest,
    create_journal_folder,
    journals_panel_fragment,
    show_journal_modal,
    show_journal_create_modal,
    toggle_journal_owner,
    upload_journal_asset,
    serve_journal_asset,
    move_journal,
    move_journal_folder,
    invite_to_campaign,
    update_campaign_permissions,
    update_layout_preference,
    update_table_settings,
    send_chat_message,
    delete_chat_message,
    clear_chat_messages,
    actors_panel_fragment,
    create_actor_folder,
    rename_actor_folder,
    set_actor_folder_color,
    delete_actor_folder,
    move_actor_folder,
    move_actor,
    toggle_actor_owner,
    create_item,
    update_item_core,
    delete_item,
    show_item_sheet_modal,
    get_item_sheet_bundle,
    get_item_sheet_data,
    patch_item_sheet_data,
    set_item_sheet_data,
    import_item_content,
    items_panel_fragment,
    toggle_item_owner,
    move_item,
    create_item_folder,
    rename_item_folder,
    set_item_folder_color,
    delete_item_folder,
    move_item_folder,
    show_resource_permissions,
    update_resource_permissions,
    show_permissions_popup,
    ban_member,
    generate_streamer_link,
    revoke_streamer_link,
]


route_handlers = [
    Router(path="/", route_handlers=_protected_handlers, guards=[require_user]),
                                                                               
                                                
    consume_streamer_link,
    game_websocket,
]
