"""The scene network edits the existing native/source rule atomically."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.journals.models import Journal
from gravewright.maps import blueprint_network, builder_services, objects, services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import MapAsset, MapBuilderProject, Receipt, Scene, SceneObject

from . import test_builder_blueprints as fixtures
from .test_blueprint_references import node
from .test_blueprint_world import audience, chain


EVENT = "interact"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BlueprintNetworkTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = chain()
        self.region_id = str(uuid.uuid4())
        self.doc["regions"] = [{"id": self.region_id, "layerId": self.doc["layers"][0]["id"], "name": "Travelers",
            "x": 5, "y": 5, "width": 2, "height": 2, "enabled": True, "blueprint": default_blueprint("region")}]
        self.generated()

    def project(self):
        return MapBuilderProject.objects.get(pk=self.project_id)

    def payload(self, raw=None, *, owner=None, rid=None, owned=True):
        row = owner or SceneObject.objects.get(pk=self.door_object.pk)
        return {"request_id": str(rid or uuid.uuid4()), "expected_version": row.version,
                "expected_project_version": self.project().version if owned else None,
                "blueprint": chain(node("message", "showMessage", text="Updated", audience=audience())) if raw is None else raw}

    def write(self, payload, *, user=None, row=None, scene=None):
        return blueprint_network.save(self.campaign.pk, (user or self.gm).pk, (scene or self.scene).pk,
                                      (row or self.door_object).pk, payload)

    def test_gm_catalog_is_private_and_does_not_offer_internal_surface_planes(self):
        from gravewright.maps.extra_objects import image
        picture = SceneObject.objects.create(scene=self.scene, kind="images", data=image(self.scene, {
            "asset_id": str(self.floor.pk), "x": 1, "y": 2}))
        internal = SceneObject.objects.create(scene=self.scene, kind="images", data={**picture.data,
            "surfacePlane": {"group": None, "order": 0, "operation": "paint"}})
        generated_asset = MapAsset.objects.create(campaign=self.campaign, generated_for=self.scene,
            name="Private mask", file=self.floor.file.name, width=16, height=16)
        result = blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)
        indexed = {row["id"]: row for row in result["elements"]}
        self.assertEqual(indexed[str(picture.pk)]["kind"], "image")
        self.assertFalse(indexed[str(picture.pk)]["editable"])
        self.assertIsNone(indexed[str(picture.pk)]["state"])
        self.assertNotIn(str(internal.pk), indexed)
        self.assertTrue(indexed[str(self.door_object.pk)]["editable"])
        self.assertEqual(indexed[str(self.door_object.pk)]["projectId"], str(self.project_id))
        self.assertNotIn(str(generated_asset.pk), {asset["id"] for asset in result["assets"]})
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises(services.MapError):
                blueprint_network.state(self.campaign.pk, user.pk, self.scene.pk)

    def test_write_rejects_player_streamer_foreign_scene_and_foreign_owner(self):
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises(services.MapError):
                self.write(self.payload(), user=user)
        foreign = Scene.objects.create(campaign=self.other, name="Foreign", width=512, height=512)
        foreign_row = SceneObject.objects.create(scene=foreign, kind="walls", data=objects.wall({
            "x1": 0, "y1": 0, "x2": 100, "y2": 0, "kind": "door"}))
        for scene, row in ((foreign, foreign_row), (self.scene, foreign_row)):
            with self.subTest(scene=scene.pk), self.assertRaises(services.MapError):
                self.write(self.payload(), scene=scene, row=row)
        self.assertFalse(Receipt.objects.filter(result__response__elementId=str(foreign_row.pk)).exists())

    def test_native_light_and_effect_catalog_keeps_scene_ownership_versions_and_private_drafts(self):
        from gravewright.maps.extra_objects import effect
        particle = SceneObject.objects.create(scene=self.scene, kind="particles", version=4,
            data=effect("particles", {"kind": "smoke", "x": 10, "y": 20, "enabled": False}))
        shader = SceneObject.objects.create(scene=self.scene, kind="shaders", version=3,
            data=effect("shaders", {"name": "Authored shader", "source": "void main() { finalColor = vec4(1.0); }", "x": 30, "y": 40}))
        foreign = Scene.objects.create(campaign=self.other, name="Foreign", width=512, height=512)
        hidden = SceneObject.objects.create(scene=foreign, kind="particles", data=particle.data)
        before = deepcopy(self.project().document)
        result = blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)
        lights = {row["id"]: row for row in result["lights"]}
        self.assertEqual(lights[str(self.light_object.pk)]["nativeKind"], "lights")
        self.assertEqual(lights[str(self.light_object.pk)]["version"], self.light_object.version)
        self.assertEqual(lights[str(self.light_object.pk)]["nativeData"], self.light_object.data)
        effects = {row["id"]: row for row in result["effects"]}
        self.assertEqual(set(effects), {str(particle.pk), str(shader.pk)})
        self.assertNotIn(str(hidden.pk), effects)
        self.assertEqual(effects[str(particle.pk)]["version"], 4)
        self.assertFalse(effects[str(particle.pk)]["nativeData"]["enabled"])
        self.assertEqual(effects[str(shader.pk)]["point"], {"x": 30, "y": 40})
        effects[str(shader.pk)]["nativeData"]["source"] = "Only a local draft"
        shader.refresh_from_db()
        self.assertNotEqual(shader.data["source"], "Only a local draft")
        self.assertEqual(self.project().document, before)

    def test_native_and_source_graph_save_once_and_retry_checks_the_exact_payload(self):
        payload = self.payload()
        original_version = self.project().version
        result = self.write(payload)
        self.door_object.refresh_from_db()
        project = self.project()
        self.assertEqual(self.door_object.data["blueprint"], payload["blueprint"])
        self.assertEqual(project.document["doors"][0]["blueprint"], payload["blueprint"])
        self.assertEqual(project.version, original_version + 1)
        adopted = next(row for row in project.generation["objects"] if row["id"] == str(self.door_object.pk))
        self.assertEqual(adopted["data"]["blueprint"], payload["blueprint"])
        self.assertEqual(self.write(payload), result)
        self.assertEqual(self.project().version, project.version)
        changed = deepcopy(payload)
        changed["blueprint"]["graphs"][EVENT]["nodes"][1]["text"] = "Different logical operation"
        with self.assertRaises(services.MapError) as error:
            self.write(changed)
        self.assertEqual(error.exception.code, "conflict")
        self.assertEqual(Receipt.objects.filter(request_id=payload["request_id"]).count(), 1)

    def test_native_and_project_cas_reject_stale_editors_without_force_writes(self):
        stale = self.payload()
        self.write(self.payload())
        with self.assertRaisesMessage(services.MapError, "object changed"):
            self.write(stale)
        fresh = self.payload()
        project = self.project()
        project.version += 1
        project.save(update_fields=["version"])
        with self.assertRaisesMessage(services.MapError, "project changed"):
            self.write(fresh)
        self.assertFalse(Receipt.objects.filter(request_id=stale["request_id"]).exists())
        self.assertFalse(Receipt.objects.filter(request_id=fresh["request_id"]).exists())

    def test_source_failure_rolls_back_native_revision_receipt_and_notifications(self):
        before_native, before_source = deepcopy(self.door_object.data), deepcopy(self.project().document)
        payload = self.payload()
        version = self.door_object.version
        with patch("gravewright.maps.builder_services.clean_document", side_effect=services.MapError("Synthetic source failure")), \
                patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, "Synthetic source failure"):
                self.write(payload)
        self.door_object.refresh_from_db()
        self.assertEqual((self.door_object.data, self.door_object.version), (before_native, version))
        self.assertEqual(self.project().document, before_source)
        self.assertFalse(Receipt.objects.filter(request_id=payload["request_id"]).exists())
        self.assertFalse(send.called)
        self.write(payload)
        self.assertEqual(self.project().document["doors"][0]["blueprint"], payload["blueprint"])

    def test_only_typed_references_are_mapped_back_to_source_ids(self):
        project = self.project()
        region = self.scene.elements.get(kind="zones")
        mapping = {}
        for original in (self.door_object, self.light_object, region):
            replacement = SceneObject.objects.create(scene=self.scene, kind=original.kind, data=deepcopy(original.data))
            for record in project.generation["objects"]:
                if record["id"] == str(original.pk):
                    mapping[str(replacement.pk)] = record["sourceId"]
                    record["id"] = str(replacement.pk)
            original.delete()
            if original.kind == "walls":
                self.door_object = replacement
            elif original.kind == "lights":
                self.light_object = replacement
            else:
                region = replacement
        project.save(update_fields=["generation"])
        authored = "Keep " + str(self.door_object.pk)
        journal = Journal.objects.create(campaign=self.campaign, title="Handout", visibility="shared")
        raw = chain()
        raw["graphs"][EVENT]["nodes"].extend([
            node("ref", "reference", targetId=str(region.pk)),
            node("light", "lightReference", targetId=str(self.light_object.pk)),
            node("group", "elementGroup", name=authored, memberType="element", targetIds=[str(self.door_object.pk), str(region.pk)]),
            node("typedText", "getVariable", scope="element", name="Text", valueType="text", default=authored),
            node("message", "showMessage", text=authored, audience=audience("users", userIds=[str(self.player.pk)])),
            node("handout", "showHandout", journalId=str(journal.pk), audience=audience()),
            node("portal", "teleport", destinationId=str(region.pk))])
        self.write(self.payload(raw))
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["blueprint"], raw)
        nodes = self.project().document["doors"][0]["blueprint"]["graphs"][EVENT]["nodes"]
        self.assertEqual(nodes[1]["targetId"], mapping[str(region.pk)])
        self.assertEqual(nodes[2]["targetId"], mapping[str(self.light_object.pk)])
        self.assertEqual(nodes[3]["targetIds"], [mapping[str(self.door_object.pk)], mapping[str(region.pk)]])
        self.assertEqual((nodes[3]["name"], nodes[4]["default"], nodes[5]["text"]), (authored, authored, authored))
        self.assertEqual(nodes[5]["audience"]["userIds"], [str(self.player.pk)])
        self.assertEqual(nodes[6]["journalId"], str(journal.pk))
        self.assertEqual(nodes[7]["destinationId"], mapping[str(region.pk)])

    def test_editing_rules_does_not_adopt_prior_manual_geometry_conflicts(self):
        self.door_object.data["x1"] += 5
        self.door_object.version += 1
        self.door_object.save(update_fields=["data", "version"])
        self.write(self.payload())
        with self.assertRaisesMessage(services.MapError, "changed"):
            self.update_scene()

    def test_unowned_native_lever_and_torch_apply_the_new_graph(self):
        from gravewright.maps.extra_objects import image
        for kind in ("lever", "torch"):
            raw = image(self.scene, {"asset_id": str(self.floor.pk), "x": 30, "y": 40, "rotation": 0})
            raw[kind] = {"state": "off", "baseAssetId": str(self.floor.pk), "baseLayer": "map", "width": 16, "height": 16}
            if kind == "torch":
                raw[kind].update(lit=True, baseRotation=0, components={"lights": {"id": str(self.light_object.pk), "enabled": False}})
            raw["blueprint"] = default_blueprint(kind)
            row = SceneObject.objects.create(scene=self.scene, kind="images", data=raw)
            blueprint = chain(node("message", "showMessage", text="New " + kind, audience=audience()), event="interact", kind=kind)
            payload = self.payload(blueprint, owner=row, owned=False)
            version = self.project().version
            result = self.write(payload, row=row)
            row.refresh_from_db()
            self.assertEqual(row.data["blueprint"], blueprint)
            self.assertEqual(row.data[kind]["state"], "off")
            self.assertEqual((row.data["x"], row.data["y"], row.data["rotation"]), (30, 40, 0))
            self.assertIsNone(result["projectVersion"])
            self.assertEqual(self.project().version, version)

    def test_region_graph_edit_keeps_derived_occupancy_and_updates_its_source(self):
        region = self.scene.elements.get(kind="zones")
        raw = chain(node("message", "showMessage", text="Entered", audience=audience()), event="presence:enter", kind="region")
        result = self.write(self.payload(raw, owner=region), row=region)
        region.refresh_from_db()
        self.assertEqual(region.data["blueprint"], raw)
        self.assertEqual(region.data["region"]["state"], "empty")
        self.assertEqual(region.data["region"]["occupants"], [])
        self.assertEqual(self.project().document["regions"][0]["blueprint"], raw)
        self.assertEqual(result["version"], region.version)

    def test_http_gm_editor_is_nostore_and_rejects_invalid_and_null_graphs(self):
        url = f"/api/maps/{self.scene.pk}/automation/network"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        for raw in (None, [], {"version": 2}):
            payload = self.payload()
            payload["blueprint"] = raw
            response = self.client.post(f"{url}/{self.door_object.pk}", payload, content_type="application/json")
            self.assertIn(response.status_code, (400, 403))
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(url).status_code, 404)
