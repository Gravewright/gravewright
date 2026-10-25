"""Object area listeners survive native edits, source updates and campaign copies."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.administration.archives import export_campaign, import_campaign, options, records
from gravewright.maps import objects, services
from gravewright.maps.models import AutomationRun, MapBuilderProject
from gravewright.tokens import services as tokens

from . import test_builder_ready_empty as fixtures
from . import test_regions as region_fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class ObjectAreaIntegrationTests(TestCase):
    asset = fixtures.ReadyEmptyTests.asset
    post = fixtures.ReadyEmptyTests.post
    save = fixtures.ReadyEmptyTests.save
    generate = fixtures.ReadyEmptyTests.generate
    files = fixtures.ReadyEmptyTests.files
    generated = fixtures.ReadyEmptyTests.generated
    edit = fixtures.ReadyEmptyTests.edit
    token_command = region_fixtures.RegionTests.token_command
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move

    def setUp(self):
        fixtures.ReadyEmptyTests.setUp(self)
        self.actor = Actor.objects.create(campaign=self.campaign, name="Area visitor", data={},
                                         permissions={str(self.player.pk): "owner"})
        self.empty.update(x=2, y=1, width=2, height=1)
        self.empty["blueprint"]["graphs"] = {
            event: fixtures.graph(event, fixtures.node("state", "state", targetState=state))
            for event, state in (("presence:enter", "on"), ("presence:exit", "off"))}

    def test_native_edit_quietly_rebaselines_and_does_not_expose_or_accept_token_ledger(self):
        row = self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual(row.data["areaPresence"]["occupants"], [str(token.pk)])
        count = AutomationRun.objects.filter(scene=self.scene).count()
        result = self.edit(row, x=384)
        row.refresh_from_db()
        self.assertEqual(row.data["areaPresence"]["occupants"], [])
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.assertNotIn("areaPresence", result["image"])
        for user in (self.gm, self.player):
            state = objects.layer_state(self.scene, services.member(self.campaign.pk, user.pk))
            visible = [entry for entry in state["images"] if entry["id"] == str(row.pk)]
            if user == self.gm:
                self.assertNotIn("areaPresence", visible[0])
            else:
                self.assertEqual(visible, [], "Empty controllers are private to the GM.")
        with self.assertRaisesMessage(services.MapError, "membership cannot be edited"):
            self.edit(row, areaPresence={"occupants": [str(token.pk)]})
        self.move(token, 5)
        self.move(token, 0)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "off")

    def test_empty_circle_native_resize_quietly_updates_membership_and_reset_restores_box(self):
        self.empty["presenceRadius"] = 1
        row = self.generated()
        token = self.place(4, 1)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.edit(row, presenceRadius=128)
        row.refresh_from_db()
        self.assertEqual(row.data["areaPresence"]["occupants"], [str(token.pk)])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.assertEqual(row.data["lever"]["state"], "off")
        self.edit(row, x=200)
        row.refresh_from_db()
        self.assertEqual(row.data["presenceRadius"], 128)
        self.edit(row, presenceRadius=None)
        row.refresh_from_db()
        self.assertNotIn("presenceRadius", row.data)
        self.assertEqual(row.data["areaPresence"]["occupants"], [])

    def test_circle_survives_linked_scene_updates_and_campaign_archive(self):
        self.empty["presenceRadius"] = 2
        row = self.generated()
        self.empty["presenceRadius"] = 3
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.scene.refresh_from_db()
        result = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()), "expected_version": 2,
            "expected_scene_version": self.scene.version})
        self.assertEqual(result.status_code, 200, result.content)
        row.refresh_from_db()
        self.assertEqual(row.data["presenceRadius"], 192)
        clone = import_campaign(export_campaign(self.campaign), self.gm, "Copied circular objects")
        source = MapBuilderProject.objects.get(campaign=clone)
        self.assertEqual(source.document["decorations"][0]["presenceRadius"], 3)
        self.assertEqual(source.scene.elements.get(data__empty=True).data["presenceRadius"], 192)

    def test_adding_listener_around_existing_token_is_quiet_and_exit_still_runs(self):
        blueprint = deepcopy(self.empty["blueprint"])
        self.empty.pop("blueprint")
        row = self.generated()
        token = self.place(2)
        result = self.edit(row, blueprint=blueprint)
        row.refresh_from_db()
        self.assertEqual(row.data["areaPresence"]["occupants"], [str(token.pk)])
        self.assertEqual(row.data["lever"]["state"], "off")
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.assertIn("presence:enter", result["image"]["blueprint"]["graphs"])
        self.move(token, 0)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.move(token, 2)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")

    def test_updating_linked_scene_ignores_live_membership_and_preserves_state(self):
        row = self.generated()
        token = self.place()
        self.move(token, 2)
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.scene.refresh_from_db()
        result = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()), "expected_version": 2,
            "expected_scene_version": self.scene.version})
        self.assertEqual(result.status_code, 200, result.content)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual(row.data["areaPresence"]["occupants"], [str(token.pk)])
        self.assertEqual(self.scene.elements.filter(data__empty=True).count(), 1)
        self.move(token, 0)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "off")

    def test_archive_omits_private_membership_and_keeps_authored_area_graphs(self):
        row = self.generated()
        token = self.place()
        self.move(token, 2)
        other = self.place(3)
        for record in records(self.campaign, options()):
            fields = record["fields"]
            if record["model"] == "gravewright_maps.sceneobject":
                self.assertNotIn("areaPresence", fields["data"])
            if record["model"] == "gravewright_maps.mapbuilderproject":
                self.assertTrue(all("areaPresence" not in item["data"] for item in fields["generation"]["objects"]))
        row.refresh_from_db()
        self.assertEqual(set(row.data["areaPresence"]["occupants"]), {str(token.pk), str(other.pk)},
                         "Export must not alter live state.")
        clone = import_campaign(export_campaign(self.campaign), self.gm, "Copied area objects")
        source = MapBuilderProject.objects.get(campaign=clone)
        copied = source.scene.elements.get(data__empty=True)
        self.assertEqual(set(copied.data["blueprint"]["graphs"]), {"presence:enter", "presence:exit"})
        self.assertEqual(len(copied.data["areaPresence"]["occupants"]), 2)
        self.assertFalse(set(copied.data["areaPresence"]["occupants"]) & {str(token.pk), str(other.pk)})
        self.assertEqual(copied.data["lever"]["state"], "on")
        visitor = source.scene.tokens.first()
        tokens.command(clone.pk, self.gm.pk, "move", {"mapId": str(source.scene.pk),
            "id": str(visitor.pk), "gridX": 0, "gridY": 1, "expectedVersion": visitor.version}, uuid.uuid4())
        run = AutomationRun.objects.filter(scene=source.scene).first()
        self.assertEqual((run.data["context"]["presence"], run.data["context"]["count"]), ("exit", 1))

    def test_combined_listener_limit_is_enforced_when_saving_and_adding_native_region(self):
        self.generated()
        with patch("gravewright.maps.regions.MAX_REGIONS", 1):
            with self.assertRaisesMessage(services.MapError, "too many presence regions"):
                services.command(self.campaign.pk, self.gm.pk, "objects", {
                    "mapId": str(self.scene.pk), "area": "zones", "action": "create",
                    "data": {"geometry": {"shape": "rect", "x": 0, "y": 0, "width": 64, "height": 64},
                             "region": {"name": "Additional area"}}}, uuid.uuid4())
            self.assertFalse(self.scene.elements.filter(kind="zones").exists())
            self.doc["decorations"].append({**deepcopy(self.empty), "id": str(uuid.uuid4()), "x": 5})
            result = self.save(expected_version=1)
            self.assertEqual(result.status_code, 400, result.content)
            self.assertEqual(len(MapBuilderProject.objects.get(pk=self.project_id).document["decorations"]), 1)
