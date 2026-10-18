"""Pressure plates use private, transactional, multi-token presence."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint
from gravewright.maps.models import AutomationRun, MapBuilderProject, Receipt, SceneObject
from gravewright.tokens import services as tokens

from . import test_builder_blueprints as fixtures
from .test_levers import data, execution, node


def target_graph(event, target, state, *, count=None):
    graph = {"nodes": [node("event", "event", event=event), node("target", "reference", targetId=target),
                      node("state", "state", targetState=state)],
            "edges": [execution("event", "state"), data("target", "door", "state", "target")]}
    if count is not None:
        graph["nodes"].extend([node("count", "eventContext", property="count"),
            node("compare", "compareValue", valueType="number", operator="eq", expected=count),
            node("check", "condition", state="occupied")])
        graph["edges"][0:1] = [execution("event", "check"), execution("check", "state", "true"),
            data("count", "value", "compare", "value"), data("compare", "result", "check", "test")]
    return graph


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class RegionTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0].pop("blueprint")
        self.region_id = str(uuid.uuid4())
        blueprint = default_blueprint("region")
        blueprint["graphs"] = {event: target_graph(event, self.doc["doors"][0]["id"], target, count=count)
            for event, target, count in (("presence:enter", "open", 1), ("presence:exit", "closed", 0))}
        self.doc["regions"] = [{"id": self.region_id, "layerId": self.doc["layers"][0]["id"],
            "name": "Pressure plate", "x": 2, "y": 1, "width": 2, "height": 1,
            "enabled": True, "blueprint": blueprint}]
        self.actor = Actor.objects.create(campaign=self.campaign, name="Hero", data={},
                                          permissions={str(self.player.pk): "owner"})

    def region(self):
        return self.scene.elements.get(kind="zones", data__region__isnull=False)

    def token_command(self, action, values, *, user=None, rid=None):
        return tokens.command(self.campaign.pk, (user or self.gm).pk, action,
                              {"mapId": str(self.scene.pk), **values}, rid or uuid.uuid4())

    def place(self, x=0, y=1):
        result = self.token_command("place", {"actorId": str(self.actor.pk), "gridX": x, "gridY": y})
        return self.scene.tokens.get(pk=result["createdIds"][0])

    def move(self, token, x, y=1, *, user=None, rid=None, path=None):
        result = self.token_command("move", {"id": str(token.pk), "gridX": x, "gridY": y,
            "expectedVersion": token.version, **({"path": path} if path is not None else {})}, user=user, rid=rid)
        token.refresh_from_db()
        return result

    def door_state(self):
        self.door_object.refresh_from_db()
        return self.door_object.data["door_state"]

    def edit(self, **values):
        row = self.region()
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "zones", "action": "update",
            "data": {"id": str(row.pk), "expected_version": row.version, "patch": values}}, uuid.uuid4())

    def test_source_native_identity_and_read_only_occupancy(self):
        self.generated()
        row = self.region()
        self.assertEqual(row.data["geometry"], {"shape": "rect", "x": 128, "y": 64, "width": 128, "height": 64})
        self.assertEqual(row.data["region"], {"name": "Pressure plate", "state": "empty", "occupants": []})
        self.assertEqual(row.data["audience"], {"kind": "gm"})
        self.assertEqual(row.data["blueprint"]["graphs"]["presence:enter"]["nodes"][1]["targetId"], str(self.door_object.pk))
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document, self.doc)
        with self.assertRaisesMessage(services.MapError, "Invalid presence region"):
            self.edit(region={"name": "Forged", "state": "occupied"})

    def test_first_token_opens_last_token_closes_and_retry_never_repeats(self):
        self.generated()
        one, two = self.place(), self.place(0, 2)
        one.refresh_from_db()
        rid = uuid.uuid4()
        original_version = one.version
        self.move(one, 2, user=self.player, rid=rid)
        self.assertEqual(self.door_state(), "open")
        first_count = AutomationRun.objects.filter(scene=self.scene).count()
        self.token_command("move", {"id": str(one.pk), "gridX": 2, "gridY": 1,
            "expectedVersion": original_version}, user=self.player, rid=rid)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), first_count)
        self.move(two, 3)
        self.assertEqual(len(self.region().data["region"]["occupants"]), 2)
        self.move(one, 0, user=self.player)
        self.assertEqual(self.door_state(), "open")
        self.assertEqual(self.region().data["region"]["state"], "occupied")
        self.move(two, 0)
        self.assertEqual(self.door_state(), "closed")
        events = [event for run in AutomationRun.objects.filter(scene=self.scene) for event in run.data["events"]]
        self.assertEqual(sum(event["event"] == "presence:enter" for event in events), 2)
        self.assertEqual(sum(event["event"] == "presence:exit" for event in events), 2)
        self.assertEqual(sum(any(step["type"] == "state" for step in event["steps"]) for event in events), 2,
                         "all presence events start, while explicit count checks act only for the first and last token")

    def test_per_token_events_include_private_context_and_do_not_repeat_for_internal_move(self):
        self.doc["regions"][0]["blueprint"]["graphs"]["presence:enter"] = {
            "nodes": [node("event", "event", event="presence:enter"), node("sound", "sound", trackId=str(self.sound.pk), volume=.3)],
            "edges": [execution("event", "sound")]}
        self.generated()
        one, two = self.place(), self.place()
        one.refresh_from_db()
        self.move(one, 2)
        self.move(two, 3)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.move(two, 2.5)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        runs = list(AutomationRun.objects.filter(scene=self.scene))
        self.assertEqual({run.data["context"]["tokenId"] for run in runs}, {str(one.pk), str(two.pk)})
        self.assertEqual(sum(any(event["event"] == "presence:enter" for event in run.data["events"]) for run in runs), 2)
        gm = objects.layer_state(self.scene, self.membership)["zones"][0]
        self.assertEqual(gm["region"], {"name": "Pressure plate", "state": "occupied", "count": 2})
        self.assertNotIn("occupants", gm["region"])

    def test_committed_path_crossing_enters_and_leaves_but_detour_does_not(self):
        self.generated()
        token = self.place()
        self.move(token, 5, path=[[0, 0], [5, 0]])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.move(token, 0)
        self.assertEqual(self.region().data["region"]["state"], "empty")
        self.assertEqual(self.door_state(), "closed")
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 2)

    def test_blocked_movement_and_preview_have_no_presence_effects(self):
        self.generated()
        token = self.place()
        SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({"x1": 64, "y1": 0, "x2": 64, "y2": 128}))
        with self.assertRaisesMessage(services.MapError, "blocked"):
            self.move(token, 2, user=self.player)
        self.assertEqual(token.grid_x, 0)
        self.assertEqual(self.door_state(), "closed")
        tokens.preview(self.campaign.pk, self.gm.pk, self.scene.pk,
            [{"id": str(token.pk), "gridX": 2, "gridY": 1, "expectedVersion": token.version}], {})
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_place_duplicate_remove_and_elevation_use_final_membership(self):
        self.doc["regions"][0].update(width=3, height=3, vertical={"bottom": 0, "top": 1})
        self.generated()
        token = self.place(2, 1)
        self.assertEqual(self.door_state(), "open")
        result = self.token_command("duplicate", {"tokenIds": [str(token.pk)]})
        clone = self.scene.tokens.get(pk=result["createdIds"][0])
        self.assertEqual(len(self.region().data["region"]["occupants"]), 2)
        self.token_command("remove", {"tokenIds": [str(token.pk)]})
        self.assertEqual(self.door_state(), "open")
        self.token_command("configure", {"tokenIds": [str(clone.pk)], "expectedVersion": clone.version,
                                          "values": {"elevation": 2}})
        self.assertEqual(self.door_state(), "closed")
        self.assertEqual(self.region().data["region"]["occupants"], [])

    def test_edits_reload_and_linked_update_baseline_without_synthetic_events(self):
        self.generated()
        token = self.place(2, 1)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.update_scene()
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.edit(region={"name": "Renamed"}, enabled=False)
        self.assertEqual(self.region().data["region"]["state"], "empty")
        self.move(token, 3)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.edit(enabled=True)
        self.assertEqual(self.region().data["region"]["state"], "occupied")
        self.move(token, 0)
        self.assertEqual(self.door_state(), "closed")

    def test_private_regions_hidden_tokens_and_authorization(self):
        from gravewright.journals.services import member
        self.generated()
        token = self.place(2, 1)
        self.token_command("hidden", {"tokenIds": [str(token.pk)], "hidden": True})
        self.assertEqual(len(self.region().data["region"]["occupants"]), 1)
        for user in (self.player, self.streamer):
            self.assertEqual(objects.layer_state(self.scene, member(self.campaign.pk, user.pk))["zones"], [])
        with self.assertRaisesMessage(services.MapError, "Only the GM"):
            services.command(self.campaign.pk, self.player.pk, "objects", {"mapId": str(self.scene.pk),
                "area": "zones", "action": "delete", "data": {"id": str(self.region().pk), "expected_version": self.region().version}}, uuid.uuid4())

    def test_failing_graph_rolls_back_move_occupancy_effects_and_receipt(self):
        self.doc["regions"][0]["blueprint"]["graphs"]["presence:enter"] = {
            "nodes": [node("event", "event", event="presence:enter"), node("light", "light", targetId=self.light_id, enabled=True)],
            "edges": [execution("event", "light")]}
        self.generated()
        token, rid = self.place(), uuid.uuid4()
        with override_settings(DYNAMIC_LIGHTING_ENABLED=False):
            with self.assertRaisesMessage(services.MapError, "Dynamic lighting is disabled"):
                self.move(token, 2, user=self.player, rid=rid)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 0)
        self.assertEqual(self.door_state(), "closed")
        self.assertEqual(self.region().data["region"]["occupants"], [])
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())

    def test_region_states_are_readable_but_cannot_be_forged_by_state_nodes(self):
        blueprint = default_blueprint("region")
        blueprint["graphs"]["presence:enter"] = {"nodes": [node("event", "event", event="presence:enter"),
            node("state", "state", targetState="occupied")], "edges": [execution("event", "state")]}
        with self.assertRaisesMessage(services.MapError, "Invalid blueprint door state"):
            clean_blueprint(blueprint)
        self.doc["regions"][0]["blueprint"]["states"]["occupied"] = {"appearance": "hidden"}
        self.assertEqual(self.save().status_code, 400)

    def test_native_region_create_is_private_and_bounds_presence_work(self):
        self.generated()
        token = self.place(2, 1)
        result = services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "zones", "action": "create", "data": {"geometry": self.region().data["geometry"],
            "audience": {"kind": "campaign"}, "region": {"name": "Native plate"}}}, uuid.uuid4())
        self.assertEqual(result["audience"], {"kind": "gm"})
        self.assertEqual(result["region"]["count"], 1)
        self.assertNotIn(str(token.pk), str(result))
        with patch("gravewright.maps.regions.MAX_PRESENCE_EVENTS", 0):
            with self.assertRaisesMessage(services.MapError, "too many presence regions"):
                self.move(token, 0)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 2)

    def test_source_regions_reject_invalid_geometry_elevation_ownership_and_budgets(self):
        original = deepcopy(self.doc)
        mutations = [lambda row: row.update(x=7, width=2),
                     lambda row: row.update(height=0),
                     lambda row: row.update(vertical={"bottom": 3, "top": 1}),
                     lambda row: row.update(vertical={"bottom": float("inf"), "top": None}),
                     lambda row: row.update(name="x" * 121),
                     lambda row: row.update(layerId=str(uuid.uuid4())),
                     lambda row: row["blueprint"].update(version=1),
                     lambda row: row.update(state="occupied"),
                     lambda row: row.update(occupants=[str(uuid.uuid4())])]
        for mutate in mutations:
            self.doc = deepcopy(original)
            mutate(self.doc["regions"][0])
            with self.subTest(region=self.doc["regions"][0]):
                with self.assertRaises(services.MapError):
                    builder_services.clean_document(self.doc, self.membership)
        self.doc = deepcopy(original)
        self.doc["regions"] = [{**deepcopy(original["regions"][0]), "id": str(uuid.uuid4())} for _ in range(129)]
        with self.assertRaisesMessage(services.MapError, "too many presence regions"):
            builder_services.clean_document(self.doc, self.membership)

    def test_player_trigger_obeys_locked_door_policy_and_explicit_authorization(self):
        self.doc["doors"][0]["state"] = "locked"
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        self.assertEqual(self.door_state(), "locked")
        self.assertTrue(any(event["event"] == "refused" for event in
                            AutomationRun.objects.latest("created_at").data["events"]))
        self.move(token, 0, user=self.player)
        blueprint = deepcopy(self.region().data["blueprint"])
        blueprint["graphs"]["presence:enter"]["nodes"][2]["players"] = True
        self.edit(blueprint=blueprint)
        self.move(token, 2, user=self.player)
        self.assertEqual(self.door_state(), "open")

    def test_archive_without_audio_removes_region_source_and_native_dependencies(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.doc["regions"][0]["blueprint"]["graphs"]["presence:enter"] = {
            "nodes": [node("event", "event", event="presence:enter"), node("sound", "sound", trackId=str(self.sound.pk), volume=.3)],
            "edges": [execution("event", "sound")]}
        self.generated()
        restored = import_campaign(export_campaign(self.campaign, {"audio": False}), self.gm, "Silent regions")
        source = MapBuilderProject.objects.get(campaign=restored)
        authored = source.document["regions"][0]["blueprint"]["graphs"]["presence:enter"]
        native = source.scene.elements.get(kind="zones").data["blueprint"]["graphs"]["presence:enter"]
        self.assertEqual([item["type"] for item in authored["nodes"]], ["event"])
        self.assertEqual([item["type"] for item in native["nodes"]], ["event"])

    def test_actor_deletion_releases_cascaded_tokens_once_and_replays_safely(self):
        from gravewright.actors import services as actors
        self.generated()
        self.place(2, 1)
        self.place(3, 1)
        rid = uuid.uuid4()
        actors.command(self.campaign.pk, self.gm.pk, "actor.delete", {"id": str(self.actor.pk)}, rid)
        self.assertFalse(self.scene.tokens.exists())
        self.assertEqual(self.region().data["region"]["occupants"], [])
        self.assertEqual(self.door_state(), "closed")
        count = AutomationRun.objects.filter(scene=self.scene).count()
        actors.command(self.campaign.pk, self.gm.pk, "actor.delete", {"id": str(self.actor.pk)}, rid)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)

    def test_recursive_actor_folder_deletion_releases_presence(self):
        from gravewright.actors import services as actors
        from gravewright.actors.models import Folder
        self.generated()
        parent = Folder.objects.create(campaign=self.campaign, name="Actors")
        child = Folder.objects.create(campaign=self.campaign, parent=parent, name="Inside")
        self.actor.folder = child
        self.actor.save(update_fields=["folder"])
        self.place(2, 1)
        actors.command(self.campaign.pk, self.gm.pk, "folder.delete", {"id": str(parent.pk), "recursive": True}, uuid.uuid4())
        self.assertFalse(self.scene.tokens.exists())
        self.assertEqual(self.door_state(), "closed")

    def test_scene_grid_configuration_rebaselines_without_entry_or_exit(self):
        self.generated()
        token = self.place()
        services.command(self.campaign.pk, self.gm.pk, "update", {"mapId": str(self.scene.pk),
            "version": self.scene.version, "settings": {"gridOffsetX": 128}}, uuid.uuid4())
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(self.region().data["region"]["state"], "occupied")
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.move(token, 3)
        self.assertEqual(self.region().data["region"]["state"], "empty")

    def test_token_size_edit_rebaselines_without_running_presence(self):
        from gravewright.actors import services as actors
        from gravewright.pdf_system.schema import normalize
        self.generated()
        self.actor.data = normalize({})
        self.actor.save(update_fields=["data"])
        token = self.place(1, 1)
        values = deepcopy(self.actor.data)
        values["token"]["size"] = 2
        actors.command(self.campaign.pk, self.gm.pk, "sheet.save", {"actorId": str(self.actor.pk),
            "sheetVersion": self.actor.sheet_version, "version": self.actor.version,
            "data": values, "name": self.actor.name}, uuid.uuid4())
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_linked_update_counts_regions_authored_directly_in_the_game(self):
        self.generated()
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "zones", "action": "create", "data": {"geometry": self.region().data["geometry"],
            "region": {"name": "External region"}}}, uuid.uuid4())
        self.doc["regions"].append({**deepcopy(self.doc["regions"][0]), "id": str(uuid.uuid4()), "name": "New source region"})
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        with patch("gravewright.maps.regions.MAX_REGIONS", 2):
            with self.assertRaisesMessage(services.MapError, "too many presence regions"):
                self.update_scene()
        self.assertEqual(self.scene.elements.filter(kind="zones").count(), 2)

    def test_converting_an_existing_zone_cannot_bypass_region_limit(self):
        self.generated()
        result = services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "zones", "action": "create", "data": {"geometry": self.region().data["geometry"]}}, uuid.uuid4())
        with patch("gravewright.maps.regions.MAX_REGIONS", 1):
            with self.assertRaisesMessage(services.MapError, "too many presence regions"):
                services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
                    "area": "zones", "action": "update", "data": {"id": result["id"],
                    "expected_version": result["version"], "patch": {"region": {"name": "Converted"}}}}, uuid.uuid4())
        self.assertNotIn("region", self.scene.elements.get(pk=result["id"]).data)

    def test_overlapping_regions_each_transition_independently_and_archive_preserves_ledger(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        second = deepcopy(self.doc["regions"][0])
        second.update(id=str(uuid.uuid4()), name="Second plate")
        self.doc["regions"].append(second)
        self.generated()
        token = self.place(2, 1)
        rows = list(self.scene.elements.filter(kind="zones"))
        self.assertTrue(all(row.data["region"]["occupants"] == [str(token.pk)] for row in rows))
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 2)
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Region clone")
        source = MapBuilderProject.objects.get(campaign=restored)
        restored_token = source.scene.tokens.get()
        self.assertTrue(all(row.data["region"]["occupants"] == [str(restored_token.pk)]
                            for row in source.scene.elements.filter(kind="zones")))
