"""Authored element names survive scene delivery without changing references."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.campaigns.models import Membership
from gravewright.maps import blueprint_network, blueprint_runtime, builder_services, objects, services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import Broadcast, MapBuilderProject, Receipt, SceneObject

from . import test_builder_effects as effects
from . import test_builder_projects as projects
from .test_blueprint_references import data, execution, node


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BuilderElementNameTests(TestCase):
    asset = projects.BuilderProjectTests.asset
    post = projects.BuilderProjectTests.post
    save = projects.BuilderProjectTests.save
    generate = projects.BuilderProjectTests.generate
    files = projects.BuilderProjectTests.files
    generated = effects.BuilderEffectTests.generated
    update = effects.BuilderEffectTests.update

    def setUp(self):
        effects.BuilderEffectTests.setUp(self)
        layer = self.doc["layers"][0]
        layer.update(visible=True, locked=False)
        self.doc["regions"] = [{"id": str(uuid.uuid4()), "layerId": layer["id"], "name": "Entry area",
                                "x": 5, "y": 5, "width": 1, "height": 1, "enabled": True}]
        self.doc["decorations"].append({"id": str(uuid.uuid4()), "layerId": layer["id"], "assetId": None,
            "empty": True, "name": "Invisible controller", "x": 6, "y": 6, "width": 1, "height": 1,
            "rotation": 0, "lever": {"state": "off"}})
        for kind in ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders", "regions"):
            for index, row in enumerate(self.doc[kind]):
                row["name"] = f"{kind} authored {index} — 雪"
        controller = self.doc["decorations"][-1]
        controller["blueprint"] = default_blueprint("lever")
        controller["blueprint"]["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"),
                      node("ref", "reference", targetId=self.doc["doors"][0]["id"]),
                      node("act", "state", targetState="open")],
            "edges": [execution("event", "act"), data("ref", "door", "act", "target")]}

    def sources(self, document=None):
        doc = self.doc if document is None else document
        return {row["id"]: row for kind in ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders", "regions")
                for row in doc[kind]}

    def test_names_roundtrip_with_unicode_and_existing_unnamed_rows_stay_unnamed(self):
        document = deepcopy(self.doc)
        for row in self.sources(document).values():
            row["name"] = "  The entry <gate> & 雪  "
        response = self.save(document=document)
        self.assertEqual(response.status_code, 200, response.content)
        saved = self.client.get(self.url).json()["project"]["document"]
        self.assertEqual({row["name"] for row in self.sources(saved).values()}, {"The entry <gate> & 雪"})
        self.assertEqual(set(self.sources(saved)), set(self.sources(document)))
        for kind in ("floors", "walls", "doors", "lights", "particles"):
            document[kind][0].pop("name")
        document["decorations"][0].pop("name")
        saved = builder_services.clean_document(document, self.membership)
        for kind in ("floors", "walls", "doors", "lights", "particles"):
            self.assertNotIn("name", saved[kind][0])
        self.assertNotIn("name", saved["decorations"][0])

    def test_name_validation_preserves_saved_document_receipts_and_revisions(self):
        self.assertEqual(self.save().status_code, 200)
        original = MapBuilderProject.objects.get(pk=self.project_id)
        for kind in ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders", "regions"):
            for value in (None, False, 4, [], {}, "", "   ", "bad\x00name", "x" * 121):
                document = deepcopy(self.doc)
                document[kind][0]["name"] = value
                with self.subTest(kind=kind, value=value):
                    result = self.save(document=document, expected_version=1)
                    self.assertEqual(result.status_code, 400, result.content)
        current = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual((current.document, current.version), (original.document, original.version))
        self.assertEqual(Receipt.objects.count(), 1)
        document = deepcopy(self.doc)
        for row in self.sources(document).values():
            row["name"] = "雪" * 120
        self.assertEqual(self.save(document=document, expected_version=1).status_code, 200)

    def test_generation_and_linked_rename_keep_native_ids_targets_and_live_state(self):
        self.generated()
        original_ids = set(self.scene.elements.values_list("pk", flat=True))
        door_id = uuid.uuid5(self.scene.pk, self.doc["doors"][0]["id"])
        controller_id = uuid.uuid5(self.scene.pk, self.doc["decorations"][-1]["id"])
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "images", "action": "interact", "data": {"image_id": str(controller_id)}}, uuid.uuid4())
        self.assertEqual(self.scene.elements.get(pk=door_id).data["door_state"], "open")
        renamed = deepcopy(self.doc)
        for row in self.sources(renamed).values():
            row["name"] += " renamed"
        result = self.update(renamed)
        self.assertEqual(result["scene"]["id"], str(self.scene.pk))
        self.assertEqual(set(self.scene.elements.values_list("pk", flat=True)), original_ids)
        self.assertEqual(self.scene.elements.get(pk=door_id).data["door_state"], "open")
        for source_id, source in self.sources(renamed).items():
            row = self.scene.elements.filter(pk=uuid.uuid5(self.scene.pk, source_id)).first()
            if row is None:  # Static floors are baked into the background.
                continue
            self.assertEqual(row.data.get("region", {}).get("name", row.data.get("name")), source["name"])
        for row in self.scene.elements.filter(kind="walls", data__kind="wall"):
            self.assertEqual(row.data["name"], renamed["walls"][0]["name"])
        graph = self.scene.elements.get(pk=controller_id).data["blueprint"]["graphs"]["interact"]
        self.assertEqual(next(row for row in graph["nodes"] if row["id"] == "ref")["targetId"], str(door_id))
        catalog = blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)
        self.assertEqual(next(row for row in catalog["elements"] if row["id"] == str(door_id))["name"], renamed["doors"][0]["name"])
        summaries = blueprint_runtime.automation_doors(self.scene)
        self.assertEqual(next(row for row in summaries if row["id"] == str(controller_id))["name"], renamed["decorations"][-1]["name"])
        for key, kind in (("lights", "lights"), ("effects", "particles")):
            native_id = str(uuid.uuid5(self.scene.pk, renamed[kind][0]["id"]))
            self.assertEqual(next(row for row in catalog[key] if row["id"] == native_id)["name"], renamed[kind][0]["name"])

    def test_unrelated_native_edits_keep_names_and_invalid_native_rename_is_atomic(self):
        self.generated()
        for row in list(self.scene.elements.all()):
            original = deepcopy(row.data)
            if row.kind == "zones":
                payload = {"zone_id": str(row.pk), "expected_version": row.version, "patch": {"enabled": False}}
            else:
                idkey = {"walls": "wall_id", "lights": "light_id", "images": "placement_id",
                         "particles": "emitter_id", "shaders": "shader_id"}[row.kind]
                payload = {idkey: str(row.pk), "version": row.version}
            services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
                "area": row.kind, "action": "update", "data": payload}, uuid.uuid4())
            row.refresh_from_db()
            if row.kind == "zones":
                self.assertEqual(row.data["region"]["name"], original["region"]["name"])
            else:
                self.assertEqual(row.data["name"], original["name"])
                before = deepcopy(row.data)
                receipts = Receipt.objects.count()
                with self.assertRaises(services.MapError):
                    services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
                        "area": row.kind, "action": "update", "data": {**payload, "version": row.version, "name": "bad\x00name"}}, uuid.uuid4())
                row.refresh_from_db()
                self.assertEqual(row.data, before)
                self.assertEqual(Receipt.objects.count(), receipts)

    def test_named_dynamic_surfaces_are_available_to_native_references(self):
        self.doc["floors"][0]["dynamic"] = True
        self.doc["walls"][0]["dynamic"] = True
        self.generated()
        for kind in ("floors", "walls"):
            source = self.doc[kind][0]
            row = self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, source["id"]))
            self.assertEqual(row.data["name"], source["name"])
            self.assertEqual(row.data["surface"]["kind"], kind[:-1])
            native = objects.entry(row)
            self.assertEqual(native["name"], source["name"])
        names = {row["name"] for row in blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)["elements"]}
        self.assertIn(self.doc["floors"][0]["name"], names)
        self.assertIn(self.doc["walls"][0]["name"], names)

    def test_resetting_an_optional_name_updates_existing_scene_without_replacing_it(self):
        self.generated()
        source = self.doc["decorations"][0]
        native_id = uuid.uuid5(self.scene.pk, source["id"])
        document = deepcopy(self.doc)
        document["decorations"][0].pop("name")
        self.update(document)
        row = SceneObject.objects.get(pk=native_id)
        self.assertNotIn("name", row.data)
        self.assertEqual(row.scene_id, self.scene.pk)

    def test_undiscovered_secret_names_are_private_until_revealed_to_players_and_streamers(self):
        self.doc["doors"][0].update(name="Hidden treasury entrance", presentation="secret", discovered=False)
        self.generated()
        self.scene.visibility = "players"
        self.scene.save(update_fields=["visibility"])
        Broadcast.objects.update_or_create(campaign=self.campaign, defaults={"scene": self.scene})
        door = self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, self.doc["doors"][0]["id"]))
        viewers = [Membership.objects.get(campaign=self.campaign, user=user) for user in (self.player, self.streamer)]
        for presentation in ("secret", "invisible"):
            door.data.update(presentation=presentation, discovered=False)
            door.save(update_fields=["data"])
            authored = deepcopy(door.data)
            gm = next(row for row in objects.layer_state(self.scene, self.membership)["walls"] if row["id"] == str(door.pk))
            self.assertEqual((gm["name"], gm["kind"]), (door.data["name"], "door"))
            for viewer in viewers:
                with self.subTest(presentation=presentation, role=viewer.role):
                    state = objects.layer_state(self.scene, viewer)
                    hidden = next(row for row in state["walls"] if row["id"] == str(door.pk))
                    self.assertNotIn("name", hidden)
                    self.assertNotIn(door.data["name"], str(state))
                    self.assertEqual(hidden["kind"], "wall")
                    self.assertEqual(hidden["x1"], authored["x1"])
            door.refresh_from_db()
            self.assertEqual(door.data, authored)
            door.data["discovered"] = True
            door.save(update_fields=["data"])
            for viewer in viewers:
                revealed = next(row for row in objects.layer_state(self.scene, viewer)["walls"] if row["id"] == str(door.pk))
                self.assertEqual((revealed["name"], revealed["kind"]), (door.data["name"], "door"))
        door.data.update(presentation="normal", discovered=False)
        door.save(update_fields=["data"])
        for viewer in viewers:
            public = next(row for row in objects.layer_state(self.scene, viewer)["walls"] if row["id"] == str(door.pk))
            self.assertEqual(public["name"], door.data["name"])
