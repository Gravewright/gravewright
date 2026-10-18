"""Presence filters retain authoritative identities and quiet configuration edits."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.maps import builder_services, objects, regions, services
from gravewright.maps.models import AutomationRun, MapBuilderProject, Receipt, Scene
from gravewright.maps.blueprints import default_blueprint
from gravewright.tokens.models import Token

from . import test_regions as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class RegionFilterTests(TestCase):
    asset = fixtures.RegionTests.asset
    post = fixtures.RegionTests.post
    save = fixtures.RegionTests.save
    generate = fixtures.RegionTests.generate
    files = fixtures.RegionTests.files
    generated = fixtures.RegionTests.generated
    update_scene = fixtures.RegionTests.update_scene
    setUp = fixtures.RegionTests.setUp
    region = fixtures.RegionTests.region
    token_command = fixtures.RegionTests.token_command
    place = fixtures.RegionTests.place
    move = fixtures.RegionTests.move
    edit = fixtures.RegionTests.edit
    door_state = fixtures.RegionTests.door_state

    def filters(self, **values):
        return {"tokenIds": [], "actorIds": [], "dispositions": [], "visibility": "any", **values}

    def set_region_graph(self, *, target=None, enabled=False, light=False):
        event = "presence:enter"
        graph = {"nodes": [fixtures.node("event", "event", event=event),
                           fixtures.node("set", "setRegion", enabled=enabled),
                           fixtures.node("count", "eventContext", property="count"),
                           fixtures.node("compare", "compareValue", valueType="number", operator="eq", expected=1),
                           fixtures.node("check", "condition", state="occupied")],
                 "edges": [fixtures.execution("event", "check"), fixtures.execution("check", "set", "true"),
                           fixtures.data("count", "value", "compare", "value"),
                           fixtures.data("compare", "result", "check", "test")]}
        if target:
            graph["nodes"].append(fixtures.node("target", "reference", targetId=target))
            graph["edges"].append(fixtures.data("target", "door", "set", "target"))
        if light:
            graph["nodes"].append(fixtures.node("light", "light", targetId=self.light_id, enabled=True))
            graph["edges"].append(fixtures.execution("set", "light"))
        blueprint = default_blueprint("region")
        blueprint["graphs"] = {event: graph}
        return blueprint

    def test_source_native_projection_and_legacy_omission(self):
        original = deepcopy(self.doc)
        self.assertEqual(builder_services.clean_document(original, self.membership), original)
        self.doc["regions"][0]["filters"] = self.filters(actorIds=[str(self.actor.pk)], dispositions=["neutral"])
        self.generated()
        self.assertEqual(self.region().data["region"]["filters"], self.doc["regions"][0]["filters"])
        token = self.place(2, 1)
        projection = objects.layer_state(self.scene, self.membership)["zones"][0]["region"]
        self.assertEqual(projection["filters"], self.doc["regions"][0]["filters"])
        self.assertEqual(projection["count"], 1)
        self.assertNotIn("occupants", projection)
        self.assertNotIn(str(token.pk), str(projection))
        from gravewright.journals.services import member
        for user in (self.player, self.streamer):
            self.assertEqual(objects.layer_state(self.scene, member(self.campaign.pk, user.pk))["zones"], [])

    def test_filter_defaults_strict_validation_and_inert_missing_ids(self):
        missing = str(uuid.uuid4())
        self.assertEqual(regions.clean_filters({}), self.filters())
        self.assertEqual(regions.clean_filters({"actorIds": [missing]}, campaign_id=self.campaign.pk),
                         self.filters(actorIds=[missing]))
        bad = [None, [], True, {"unknown": True}, {"tokenIds": "one"}, {"actorIds": [False]},
               {"tokenIds": [missing, missing]}, {"actorIds": ["not-a-uuid"]},
               {"actorIds": [str(uuid.uuid4()) for _ in range(65)]},
               {"dispositions": ["PC"]}, {"dispositions": ["friendly", "friendly"]},
               {"visibility": "players"}, {"visibility": False}]
        for value in bad:
            with self.subTest(filters=value), self.assertRaises(services.MapError):
                regions.clean_filters(value, campaign_id=self.campaign.pk)
        self.doc["regions"][0]["filters"] = self.filters(actorIds=[missing])
        self.generated()
        self.place(2, 1)
        self.assertEqual(self.region().data["region"]["occupants"], [])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_known_foreign_actors_tokens_and_native_foreign_scene_are_rejected(self):
        self.generated()
        foreign_actor = Actor.objects.create(campaign=self.other, name="Foreign", data={})
        foreign_scene = Scene.objects.create(campaign=self.other, name="Foreign", width=512, height=512)
        foreign = Token.objects.create(scene=foreign_scene, actor=foreign_actor)
        for key, value in (("actorIds", foreign_actor.pk), ("tokenIds", foreign.pk)):
            with self.subTest(key=key), self.assertRaisesMessage(services.MapError, "this campaign and scene"):
                regions.clean_filters({key: [str(value)]}, campaign_id=self.campaign.pk)
        local_scene = Scene.objects.create(campaign=self.campaign, name="Other placement", width=512, height=512)
        local = Token.objects.create(scene=local_scene, actor=self.actor)
        regions.clean_filters({"tokenIds": [str(local.pk)]}, campaign_id=self.campaign.pk)
        with self.assertRaisesMessage(services.MapError, "this campaign and scene"):
            self.edit(region={"filters": {"tokenIds": [str(local.pk)]}})

    def test_criteria_are_and_with_or_inside_each_nonempty_list(self):
        self.generated()
        one, two = self.place(), self.place()
        second_actor = Actor.objects.create(campaign=self.campaign, name="Second", data={})
        third = Token.objects.create(scene=self.scene, actor=second_actor, disposition="friendly", grid_y=1)
        self.edit(region={"filters": self.filters(tokenIds=[str(one.pk), str(third.pk)],
            actorIds=[str(self.actor.pk)], dispositions=["neutral", "friendly"], visibility="visible")})
        self.move(two, 2)
        self.move(third, 2)
        self.assertEqual(self.region().data["region"]["occupants"], [])
        one.refresh_from_db()
        self.move(one, 2)
        self.assertEqual(self.region().data["region"]["occupants"], [str(one.pk)])
        self.assertEqual(self.door_state(), "open")

    def test_actor_filter_accepts_multiple_placements_but_token_filter_excludes_duplicates(self):
        self.doc["regions"][0]["filters"] = self.filters(actorIds=[str(self.actor.pk)])
        self.doc["regions"][0].update(width=3, height=3)
        self.generated()
        one = self.place(2, 1)
        result = self.token_command("duplicate", {"tokenIds": [str(one.pk)]})
        two = self.scene.tokens.get(pk=result["createdIds"][0])
        self.assertEqual(len(self.region().data["region"]["occupants"]), 2)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.edit(region={"filters": self.filters(tokenIds=[str(one.pk)])})
        self.assertEqual(self.region().data["region"]["occupants"], [str(one.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.move(two, 0)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)

    def test_hidden_filter_changes_rebaseline_silently_and_future_moves_obey_it(self):
        self.doc["regions"][0]["filters"] = self.filters(visibility="visible")
        self.generated()
        token = self.place(2, 1)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.token_command("hidden", {"tokenIds": [str(token.pk)], "hidden": True})
        self.assertEqual(self.region().data["region"]["occupants"], [])
        self.assertEqual(self.region().data["region"]["state"], "empty")
        self.assertEqual(self.door_state(), "open")
        token.refresh_from_db()
        self.move(token, 0)
        self.move(token, 2)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.token_command("hidden", {"tokenIds": [str(token.pk)], "hidden": False})
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        token.refresh_from_db()
        self.move(token, 0)
        self.assertEqual(self.door_state(), "closed")

    def test_disposition_metadata_rebaselines_and_unknown_is_an_explicit_core_value(self):
        self.doc["regions"][0]["filters"] = self.filters(dispositions=["friendly", "unknown"])
        self.generated()
        token = self.place(2, 1)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.token_command("configure", {"tokenIds": [str(token.pk)], "expectedVersion": token.version,
                                          "values": {"disposition": "unknown"}})
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        token.refresh_from_db()
        self.move(token, 0)
        self.move(token, 2)
        self.assertEqual(self.door_state(), "open")
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.token_command("configure", {"tokenIds": [str(token.pk)], "expectedVersion": token.version,
                                          "values": {"disposition": "hostile"}})
        self.assertEqual(self.region().data["region"]["occupants"], [])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.assertEqual(self.door_state(), "open")

    def test_excluded_path_crossing_does_not_fire_and_filter_edit_is_quiet(self):
        self.doc["regions"][0]["filters"] = self.filters(dispositions=["hostile"])
        self.generated()
        token = self.place()
        self.move(token, 5)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.edit(region={"filters": {}})
        self.move(token, 0)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 2)

    def test_authenticated_context_ignores_payload_identity_and_counts_filtered_occupants(self):
        self.doc["regions"][0]["filters"] = self.filters(actorIds=[str(self.actor.pk)])
        self.generated()
        token = self.place()
        self.token_command("move", {"id": str(token.pk), "expectedVersion": token.version, "gridX": 2, "gridY": 1,
            "context": {"userId": str(self.gm.pk), "actorId": str(uuid.uuid4()), "count": 99}}, user=self.player)
        context = AutomationRun.objects.filter(scene=self.scene).latest("created_at").data["context"]
        self.assertEqual(context, {"userId": str(self.player.pk), "userName": self.player.name,
            "sourceId": str(self.region().pk), "tokenId": str(token.pk), "actorId": str(self.actor.pk),
            "presence": "enter", "count": 1})

    def test_filters_and_identity_references_survive_linked_update_and_archive_remapping(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.doc["regions"][0]["filters"] = self.filters(actorIds=[str(self.actor.pk)])
        self.generated()
        token = self.place(2, 1)
        # A native filter edit becomes authored in this source through an explicit update.
        self.doc["regions"][0]["filters"]["tokenIds"] = [str(token.pk)]
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.update_scene()
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Filtered presence clone")
        project = MapBuilderProject.objects.get(campaign=restored)
        imported = project.scene.tokens.get()
        expected = self.filters(actorIds=[str(imported.actor_id)], tokenIds=[str(imported.pk)])
        self.assertEqual(project.document["regions"][0]["filters"], expected)
        self.assertEqual(project.scene.elements.get(kind="zones").data["region"]["filters"], expected)
        self.assertEqual(builder_services.clean_document(project.document, restored.memberships.get(user=self.gm)), project.document)

    def test_name_patch_retains_filters_and_filter_patch_retains_name(self):
        self.doc["regions"][0]["filters"] = self.filters(visibility="hidden")
        self.generated()
        self.edit(region={"name": "Renamed"})
        self.assertEqual(self.region().data["region"]["filters"]["visibility"], "hidden")
        self.edit(region={"filters": {"visibility": "visible"}})
        self.assertEqual(self.region().data["region"]["name"], "Renamed")

    def test_runtime_self_disable_keeps_empty_baseline_and_prevents_future_presence_events(self):
        blueprint = self.set_region_graph()
        blueprint["graphs"]["presence:enter"]["nodes"].append(
            fixtures.node("light", "light", targetId=self.light_id, enabled=True))
        self.doc["regions"][0]["blueprint"] = blueprint
        self.generated()
        token = self.place()
        self.move(token, 2)
        region = self.region()
        self.assertFalse(region.data["enabled"])
        self.assertEqual(region.data["region"]["occupants"], [])
        self.assertEqual(region.data["region"]["state"], "empty")
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        run = AutomationRun.objects.get(scene=self.scene)
        self.assertEqual([entry["event"] for entry in run.data["events"]], ["presence:enter"])
        self.assertIn("set", [step["id"] for entry in run.data["events"] for step in entry["steps"]])
        self.assertNotIn("light", [step["id"] for entry in run.data["events"] for step in entry["steps"]],
                         "an event executes only its connected actions")
        self.move(token, 0)
        self.move(token, 2)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.assertEqual(self.region().data["region"]["occupants"], [])
        self.assertEqual(self.region().data["region"]["state"], "empty")
        self.assertFalse(regions.presence_suppressed(region))

    def test_runtime_disable_later_region_prevents_prefetched_presence_and_stale_writeback(self):
        other = deepcopy(self.doc["regions"][0])
        other.update(id=str(uuid.uuid4()), name="Later plate")
        self.doc["regions"].append(other)
        self.doc["regions"][0]["blueprint"] = self.set_region_graph(target=other["id"])
        self.generated()
        token = self.place()
        self.move(token, 2)
        first, second = list(self.scene.elements.filter(kind="zones").order_by("created_at", "id"))
        self.assertTrue(first.data["enabled"])
        self.assertFalse(second.data["enabled"])
        self.assertEqual(first.data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(second.data["region"]["occupants"], [])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene, door_id=second.pk).exists())
        self.assertEqual(self.door_state(), "closed")

    def test_runtime_enable_later_region_establishes_current_occupancy_without_enter_event(self):
        other = deepcopy(self.doc["regions"][0])
        other.update(id=str(uuid.uuid4()), name="Initially disabled", enabled=False)
        self.doc["regions"].append(other)
        self.doc["regions"][0]["blueprint"] = self.set_region_graph(target=other["id"], enabled=True)
        self.generated()
        token = self.place()
        self.move(token, 2)
        second = self.scene.elements.filter(kind="zones").order_by("created_at", "id").last()
        self.assertTrue(second.data["enabled"])
        self.assertEqual(second.data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(second.data["region"]["state"], "occupied")
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene, door_id=second.pk).exists())
        self.assertEqual(self.door_state(), "closed")
        self.move(token, 0)
        self.assertTrue(AutomationRun.objects.filter(scene=self.scene, door_id=second.pk).exists())

    def test_group_disable_then_enable_suppresses_remaining_events_without_a_loop_or_retry_effect(self):
        other = deepcopy(self.doc["regions"][0])
        other.update(id=str(uuid.uuid4()), name="Group plate")
        self.doc["regions"].append(other)
        blueprint = default_blueprint("region")
        blueprint["graphs"] = {"presence:enter": {
            "nodes": [fixtures.node("event", "event", event="presence:enter"),
                      fixtures.node("group", "elementGroup", name="Plates", memberType="element", targetIds=[self.region_id, other["id"]]),
                      fixtures.node("disable", "setRegion", enabled=False), fixtures.node("enable", "setRegion", enabled=True),
                      fixtures.node("count", "eventContext", property="count"),
                      fixtures.node("compare", "compareValue", valueType="number", operator="eq", expected=1),
                      fixtures.node("check", "condition", state="occupied")],
            "edges": [fixtures.execution("event", "check"), fixtures.execution("check", "disable", "true"),
                      fixtures.data("count", "value", "compare", "value"),
                      fixtures.data("compare", "result", "check", "test"), fixtures.execution("disable", "enable"),
                      fixtures.data("group", "targets", "disable", "target"), fixtures.data("group", "targets", "enable", "target")]}}
        self.doc["regions"][0]["blueprint"] = blueprint
        self.generated()
        token = self.place()
        request_id, version = uuid.uuid4(), token.version
        self.move(token, 2, rid=request_id)
        rows = list(self.scene.elements.filter(kind="zones"))
        self.assertTrue(all(row.data["enabled"] for row in rows))
        self.assertTrue(all(row.data["region"]["occupants"] == [str(token.pk)] for row in rows))
        self.assertTrue(all(row.data["region"]["state"] == "occupied" for row in rows))
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.token_command("move", {"id": str(token.pk), "expectedVersion": version, "gridX": 2, "gridY": 1}, rid=request_id)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)

    def test_failing_later_action_rolls_back_runtime_baseline_and_clears_suppression_for_retry(self):
        other = deepcopy(self.doc["regions"][0])
        other.update(id=str(uuid.uuid4()), name="Rollback plate")
        self.doc["regions"].append(other)
        self.doc["regions"][0]["blueprint"] = self.set_region_graph(target=other["id"], light=True)
        self.generated()
        token = self.place()
        request_id = uuid.uuid4()
        with override_settings(DYNAMIC_LIGHTING_ENABLED=False), self.assertRaisesMessage(services.MapError, "Dynamic lighting is disabled"):
            self.move(token, 2, rid=request_id)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 0)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.assertTrue(all(row.data["enabled"] for row in self.scene.elements.filter(kind="zones")))
        self.assertTrue(all(not regions.presence_suppressed(row) for row in self.scene.elements.filter(kind="zones")))
        self.move(token, 2, rid=request_id)
        second = self.scene.elements.filter(kind="zones").order_by("created_at", "id").last()
        self.assertFalse(second.data["enabled"])
        self.assertEqual(second.data["region"]["occupants"], [])

    def test_source_update_preserves_runtime_presence_until_authored_enabled_changes(self):
        self.doc["regions"][0]["blueprint"] = self.set_region_graph()
        self.generated()
        token = self.place()
        self.move(token, 2)
        region_id = self.region().pk
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.update_scene()
        self.assertEqual(self.region().pk, region_id)
        self.assertFalse(self.region().data["enabled"])
        self.doc["regions"][0]["enabled"] = False
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update_scene()
        self.doc["regions"][0]["enabled"] = True
        self.assertEqual(self.save(expected_version=2).status_code, 200)
        self.update_scene()
        self.assertTrue(self.region().data["enabled"])
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)

    def test_source_layer_change_wins_and_quietly_rebaselines_runtime_presence(self):
        self.doc["regions"][0]["blueprint"] = self.set_region_graph()
        self.generated()
        token = self.place()
        self.move(token, 2)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.doc["layers"][0]["visible"] = False
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update_scene()
        self.doc["layers"][0]["visible"] = True
        self.assertEqual(self.save(expected_version=2).status_code, 200)
        self.update_scene()
        self.assertTrue(self.region().data["enabled"])
        self.assertEqual(self.region().data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)

    def test_combined_source_flag_and_layer_change_is_not_hidden_by_equal_effective_value(self):
        self.doc["layers"][0]["visible"] = False
        self.generated()
        row = self.region()
        regions.set_enabled(self.scene, row, True)
        row.version += 1
        row.save(update_fields=["data", "version"])
        self.doc["regions"][0]["enabled"] = False
        self.doc["layers"][0]["visible"] = True
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update_scene()
        self.assertFalse(self.region().data["enabled"])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

