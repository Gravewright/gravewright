"""Image-free controllers stay private while ordinary artwork can return to play."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.campaigns.models import Membership
from gravewright.maps import objects, services
from gravewright.maps.models import MapBuilderProject

from . import test_builder_ready_empty as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class EmptyGmLayerTests(TestCase):
    setUp = fixtures.ReadyEmptyTests.setUp
    asset = fixtures.ReadyEmptyTests.asset
    post = fixtures.ReadyEmptyTests.post
    save = fixtures.ReadyEmptyTests.save
    generate = fixtures.ReadyEmptyTests.generate
    generated = fixtures.ReadyEmptyTests.generated
    files = fixtures.ReadyEmptyTests.files
    edit = fixtures.ReadyEmptyTests.edit
    interact = fixtures.ReadyEmptyTests.interact

    def assert_private(self, row):
        gm = Membership.objects.get(campaign=self.campaign, user=self.gm)
        public = [Membership.objects.get(campaign=self.campaign, user=user)
                  for user in (self.player, self.streamer)]
        for member in public:
            self.assertNotIn(str(row.pk), {entry["id"] for entry in objects.layer_state(self.scene, member)["images"]})
        visible = next(entry for entry in objects.layer_state(self.scene, gm)["images"] if entry["id"] == str(row.pk))
        self.assertEqual(visible["layer"], "gm-image-layer")
        self.assertEqual(visible["lever"]["baseLayer"], "gm-image-layer")

    def test_generated_empty_is_private_and_native_edits_cannot_send_it_to_game(self):
        row = self.generated()
        self.assertEqual((row.data["layer"], row.data["lever"]["baseLayer"]), ("gm-image-layer", "gm-image-layer"))
        self.assert_private(row)
        self.edit(row, layer="map", x=321)
        row.refresh_from_db()
        self.assertEqual((row.data["x"], row.data["layer"], row.data["lever"]["baseLayer"]),
                         (321, "gm-image-layer", "gm-image-layer"))
        self.assert_private(row)
        with self.assertRaises(services.MapError):
            self.edit(row, layer="unknown")

    def test_legacy_empty_is_private_before_any_write_and_player_direct_interaction_is_denied(self):
        row = self.generated()
        row.data["layer"] = row.data["lever"]["baseLayer"] = "map"
        row.save(update_fields=["data"])
        before = deepcopy(row.data)
        self.assert_private(row)
        row.refresh_from_db()
        self.assertEqual(row.data, before, "A read must not rewrite an older scene.")
        with self.assertRaises(services.MapError):
            self.interact(row, self.player)
        row.refresh_from_db()
        self.assertEqual(row.data, before)
        self.interact(row)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual(row.data["layer"], "gm-image-layer")

    def test_legacy_layer_normalization_does_not_conflict_with_linked_scene_updates(self):
        row = self.generated()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        for record in source.generation["objects"]:
            if record["id"] == str(row.pk):
                record["data"]["layer"] = record["data"]["lever"]["baseLayer"] = "map"
        source.save(update_fields=["generation"])
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.scene.refresh_from_db()
        response = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()), "expected_version": 2,
            "expected_scene_version": self.scene.version})
        self.assertEqual(response.status_code, 200, response.content)
        row.refresh_from_db()
        self.assertEqual(row.data["layer"], "gm-image-layer")
        self.assert_private(row)
        self.edit(row, x=row.data["x"] + 20)
        self.scene.refresh_from_db()
        response = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()), "expected_version": 2,
            "expected_scene_version": self.scene.version})
        self.assertEqual(response.status_code, 409, "Native geometry conflicts remain protected.")

    def test_normal_images_and_levers_can_return_from_gm_with_identity_and_rules_intact(self):
        art = self.asset("Layer roundtrip.png", "#bb7722")
        self.doc["assets"].append({"assetId": str(art.pk), "role": "decoration"})
        identifiers = []
        for index, intelligent in enumerate((False, True)):
            identifier = str(uuid.uuid4())
            identifiers.append(identifier)
            image = {"id": identifier, "layerId": self.layer_id, "assetId": str(art.pk),
                     "x": 1 + index, "y": 1, "width": 1, "height": 1, "rotation": 0}
            if intelligent:
                image.update(lever={"state": "off"}, blueprint=deepcopy(self.empty["blueprint"]))
            self.doc["decorations"].append(image)
        self.generated()
        player = Membership.objects.get(campaign=self.campaign, user=self.player)
        for identifier in identifiers:
            row = self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, identifier))
            rules = deepcopy(row.data.get("blueprint"))
            for cycle in range(2):
                with self.subTest(image=identifier, cycle=cycle):
                    self.edit(row, layer="gm-image-layer")
                    row.refresh_from_db()
                    self.assertNotIn(str(row.pk), {entry["id"] for entry in objects.layer_state(self.scene, player)["images"]})
                    self.edit(row, layer="map")
                    row.refresh_from_db()
                    self.assertEqual(row.data["layer"], "map")
                    self.assertIn(str(row.pk), {entry["id"] for entry in objects.layer_state(self.scene, player)["images"]})
                    self.assertEqual(row.data.get("blueprint"), rules)
                    if "lever" in row.data:
                        self.assertEqual(row.data["lever"]["baseLayer"], "map")
