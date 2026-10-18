"""Native wall and door editors author barrier rules without touching live scenes."""
from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.maps import builder_services, services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import MapBuilderProject, Scene, SceneObject

from . import test_builder_expansion as expanded
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BuilderNativeWallPropertyTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.doc = expanded.BuilderExpansionTests.expanded(self)
        self.doc["walls"][0].update(
            presentation="window", behavior={"movement": "block", "vision": "pass", "light": "pass", "sound": "attenuate"},
            vertical={"bottom": -1.25, "top": 3.75}, discovered=False)
        self.doc["doors"][0].update(
            presentation="secret", behavior={"movement": "pass", "vision": "block", "light": "block", "sound": "pass"},
            vertical={"bottom": None, "top": None}, discovered=True)

    def generated(self):
        self.assertEqual(self.save().status_code, 200)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        self.scene = Scene.objects.get(pk=response.json()["scene"]["id"])

    def test_door_anchor_roundtrips_generates_and_updates_without_resetting_open_state(self):
        self.doc["doors"][0]["rotationAnchor"] = "start"
        self.generated()
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], self.doc)
        door = self.scene.elements.get(kind="walls", data__kind="door")
        self.assertEqual(door.data["rotationAnchor"], "start")
        door.data["door_state"] = "open"
        door.save(update_fields=["data"])
        self.doc["doors"][0]["rotationAnchor"] = "end"
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update()
        door.refresh_from_db()
        self.assertEqual((door.data["rotationAnchor"], door.data["door_state"]), ("end", "open"))
        self.doc["doors"][0].pop("rotationAnchor")
        self.assertEqual(self.save(expected_version=2).status_code, 200)
        self.update()
        door.refresh_from_db()
        self.assertNotIn("rotationAnchor", door.data)

    def test_invalid_door_anchors_do_not_replace_the_project(self):
        self.assertEqual(self.save().status_code, 200)
        for anchor in (None, True, 0, "left", {}, []):
            candidate = deepcopy(self.doc)
            candidate["doors"][0]["rotationAnchor"] = anchor
            with self.subTest(anchor=anchor):
                response = self.save(expected_version=1, document=candidate)
                self.assertEqual(response.status_code, 400, response.content)
                source = MapBuilderProject.objects.get(pk=self.project_id)
                self.assertEqual((source.version, source.document), (1, self.doc))

    def update(self):
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.scene.refresh_from_db()
        return builder_services.update(self.campaign.pk, self.gm.pk, source.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": source.version,
             "expected_scene_version": self.scene.version})

    def test_settings_roundtrip_and_every_split_span_uses_native_units_and_flags(self):
        self.generated()
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], self.doc)
        walls = self.scene.elements.filter(kind="walls", data__kind="wall")
        self.assertEqual(walls.count(), 2)
        for wall in walls:
            self.assertEqual((wall.data["presentation"], wall.data["vision_behavior"], wall.data["light_behavior"],
                              wall.data["sound_behavior"], wall.data["blocks_light"], wall.data["blocks_sight"]),
                             ("window", "pass", "pass", "attenuate", 0, 0))
            self.assertEqual((wall.data["vertical_bottom"], wall.data["vertical_top"]), (-1.25, 3.75))
            self.assertEqual(wall.data["y1"], 192)
        door = self.scene.elements.get(kind="walls", data__kind="door")
        self.assertEqual((door.data["presentation"], door.data["discovered"], door.data["movement_behavior"]),
                         ("secret", True, "pass"))
        self.assertEqual((door.data["x1"], door.data["x2"], door.data["door_state"]), (192, 256, "closed"))

    def test_omitted_and_partial_properties_keep_the_exact_authored_shape(self):
        for kind in ("walls", "doors"):
            for key in builder_services.WALL_PROPERTY_FIELDS:
                self.doc[kind][0].pop(key)
        self.doc["walls"][0]["behavior"] = {"sound": "attenuate"}
        self.doc["doors"][0]["vertical"] = {"bottom": None}
        self.assertEqual(builder_services.clean_document(self.doc, self.membership), self.doc)
        self.generated()
        wall = self.scene.elements.filter(kind="walls", data__kind="wall").first()
        self.assertEqual((wall.data["movement_behavior"], wall.data["sound_behavior"], wall.data["blocks_light"]),
                         ("block", "attenuate", 1))
        self.assertIsNone(wall.data["vertical_top"])

    def test_invalid_settings_are_rejected_atomically_before_replacing_saved_source(self):
        self.assertEqual(self.save().status_code, 200)
        invalid = [
            ("presentation", "elevation"), ("presentation", None), ("discovered", 1),
            ("behavior", []), ("behavior", None), ("behavior", {"vision": "attenuate"}),
            ("behavior", {"sound": "quiet"}), ("behavior", {"light": True}),
            ("behavior", {"unknown": "pass"}), ("vertical", []),
            ("vertical", {"unknown": 1}), ("vertical", {"bottom": 0}),
            ("vertical", {"bottom": None, "top": 3}), ("vertical", {"bottom": True, "top": 3}),
            ("vertical", {"bottom": 4, "top": 3}), ("vertical", {"bottom": 3, "top": 3}),
            ("vertical", {"bottom": 0, "top": 1_000_001}),
            ("vertical", {"bottom": float("nan"), "top": 3}),
        ]
        for kind in ("walls", "doors"):
            for key, value in invalid:
                changed = deepcopy(self.doc)
                changed[kind][0][key] = value
                with self.subTest(kind=kind, key=key, value=value):
                    response = self.save(expected_version=1, document=changed)
                    self.assertEqual(response.status_code, 400, response.content)
                    source = MapBuilderProject.objects.get(pk=self.project_id)
                    self.assertEqual((source.version, source.document), (1, self.doc))
        self.assertFalse(Scene.objects.exists())

    def test_older_schema_does_not_accept_the_new_optional_properties(self):
        source = deepcopy(self.doc)
        for kind in ("floors", "walls", "doors"):
            for row in source[kind]:
                row.pop("layerId")
        for key in ("layers", "decorations", "lights"):
            source.pop(key)
        source["floors"][0].pop("rotation")
        source["schemaVersion"] = 2
        with self.assertRaises(services.MapError):
            builder_services.clean_document(source, self.membership)

    def test_save_changes_only_source_and_explicit_update_preserves_live_door_and_manual_objects(self):
        self.generated()
        door = self.scene.elements.get(kind="walls", data__kind="door")
        door.data["door_state"] = "open"
        door.save(update_fields=["data"])
        manual = SceneObject.objects.create(scene=self.scene, kind="lights", data={"x": 9, "y": 12})
        before = {str(row.pk): deepcopy(row.data) for row in self.scene.elements.all()}
        self.doc["walls"][0].update(presentation="bars", behavior={"vision": "block"}, vertical={"bottom": 1, "top": 5})
        self.doc["doors"][0].update(presentation="window", behavior={"light": "pass"}, discovered=False)
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.assertEqual({str(row.pk): row.data for row in self.scene.elements.all()}, before)
        self.update()
        wall = self.scene.elements.filter(kind="walls", data__kind="wall").first()
        self.assertEqual((wall.data["presentation"], wall.data["vision_behavior"], wall.data["vertical_top"]),
                         ("bars", "block", 5))
        door.refresh_from_db()
        self.assertEqual((door.data["presentation"], door.data["light_behavior"], door.data["door_state"]),
                         ("window", "pass", "open"))
        manual.refresh_from_db()
        self.assertEqual(manual.data, before[str(manual.pk)])

    def test_manual_wall_configuration_changes_conflict_without_partial_scene_replacement(self):
        self.generated()
        wall = self.scene.elements.filter(kind="walls", data__kind="wall").first()
        wall.data["vertical_top"] = 99
        wall.save(update_fields=["data"])
        before = {str(row.pk): deepcopy(row.data) for row in self.scene.elements.all()}
        before_files = self.files()
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update()
        self.assertEqual({str(row.pk): row.data for row in self.scene.elements.all()}, before)
        self.assertEqual(self.files(), before_files)

    def test_blueprint_runtime_barrier_flags_and_live_door_state_survive_source_updates(self):
        self.doc["doors"][0]["blueprint"] = default_blueprint()
        self.generated()
        door = self.scene.elements.get(kind="walls", data__kind="door")
        door.data.update(door_state="open", movement_behavior="pass", vision_behavior="pass",
                         light_behavior="pass", sound_behavior="attenuate", blocks_light=0, blocks_sight=0)
        door.save(update_fields=["data"])
        self.doc["walls"][0]["vertical"]["top"] = 8
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update()
        door.refresh_from_db()
        self.assertEqual((door.data["door_state"], door.data["vision_behavior"], door.data["light_behavior"],
                          door.data["blocks_light"], door.data["sound_behavior"]),
                         ("open", "pass", "pass", 0, "attenuate"))

    def test_live_discovery_survives_repeated_updates_and_old_manifest_fallback(self):
        self.doc["doors"][0]["discovered"] = False
        self.generated()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        for row in source.generation["objects"]:
            row.pop("sourceDiscovered", None)
        source.save(update_fields=["generation"])
        door = self.scene.elements.get(kind="walls", data__kind="door")
        door.data["discovered"] = True
        door.save(update_fields=["data"])
        for _ in range(2):
            self.update()
            door.refresh_from_db()
            self.assertTrue(door.data["discovered"])
            source.refresh_from_db()
            manifest = next(row for row in source.generation["objects"] if row["sourceId"] == self.doc["doors"][0]["id"])
            self.assertFalse(manifest["sourceDiscovered"])
            self.assertTrue(manifest["data"]["discovered"])

    def test_explicit_authored_discovery_changes_apply_while_other_native_changes_remain_conflicts(self):
        self.generated()
        self.doc["doors"][0]["discovered"] = False
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update()
        door = self.scene.elements.get(kind="walls", data__kind="door")
        self.assertFalse(door.data["discovered"])
        self.doc["doors"][0]["discovered"] = True
        self.assertEqual(self.save(expected_version=2).status_code, 200)
        self.update()
        door.refresh_from_db()
        self.assertTrue(door.data["discovered"])
        door.data["presentation"] = "invisible"
        door.save(update_fields=["data"])
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update()
