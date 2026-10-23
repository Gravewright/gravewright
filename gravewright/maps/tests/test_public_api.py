"""Public map capabilities keep native authority, scope, revisions and retries."""
import base64
from copy import deepcopy
from datetime import timedelta
from io import BytesIO
import json
from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from api import Context, map_builder, map_blueprints, universal_vtt
from gravewright.campaigns.models import StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps import (blueprint_controls, blueprint_network, blueprint_templates,
                              blueprint_testing, builder_import, builder_services,
                              public, services, universal_vtt as interchange)
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import (AutomationRun, BlueprintTemplate, Broadcast, MapBuilderProject,
                                    Receipt, Scene, SceneNavigation, SceneObject, Tile)
from . import test_builder_projects as fixtures
from .test_builder_blueprints import graph


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class PublicMapApiTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="c" * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))

    def invoke(self, domain, method, payload=None, *, user=None, request_id=None, scene_id=None):
        return public.invoke(self.campaign.pk, (user or self.gm).pk, domain, method,
                             payload or {}, request_id or uuid.uuid4(), scene_id)

    def save_project(self, **overrides):
        return self.invoke("mapBuilder", "save", {
            "projectId": str(self.project_id), "expectedVersion": 0,
            "folderId": str(self.folder.pk), "document": self.doc, **overrides,
        })["project"]

    def generated(self, *, blueprint=False):
        if blueprint:
            self.doc["schemaVersion"] = 3
            layer_id = str(uuid.uuid4())
            self.doc["layers"] = [{"id": layer_id, "name": "Room", "visible": True, "locked": False}]
            for kind in ("floors", "walls", "doors"):
                for row in self.doc[kind]:
                    row["layerId"] = layer_id
            self.doc["floors"][0]["rotation"] = 0
            self.doc.update(decorations=[], lights=[])
            raw = default_blueprint()
            raw["graphs"]["interact"] = graph("interact", {"type": "state", "targetState": "open"})
            self.doc["doors"][0]["blueprint"] = raw
        source = self.save_project()
        result = self.invoke("mapBuilder", "generate", {
            "projectId": source["id"], "expectedVersion": source["version"],
        })
        self.scene = Scene.objects.get(pk=result["scene"]["id"])
        self.door_object = self.scene.elements.get(kind="walls", data__kind="door")
        return result["project"]

    def template_payload(self, **overrides):
        return {"templateId": str(uuid.uuid4()), "expectedVersion": 0, "name": "Reusable door",
                "description": "Synthetic reusable rule", "definition": {
                    "version": 1, "blueprint": default_blueprint(), "bindings": [], "parameters": [],
                }, **overrides}

    def raw_uvtt(self):
        with Image.new("RGB", (32, 32), "#112233") as image, BytesIO() as output:
            image.save(output, "PNG")
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
        return json.dumps({"format": .2, "resolution": {"map_origin": {"x": 0, "y": 0},
                           "map_size": {"x": 1, "y": 1}, "pixels_per_grid": 32},
                           "line_of_sight": [], "objects_line_of_sight": [], "portals": [],
                           "lights": [], "environment": {"baked_lighting": False,
                           "ambient_light": "ffffffff"}, "image": encoded}).encode()

    def test_facades_are_explicit_authorized_service_aliases(self):
        for name in ("catalog", "detail", "save", "generate", "update", "sync"):
            self.assertIs(getattr(map_builder, name), getattr(builder_services, name))
        self.assertIs(map_builder.adopt, builder_import.adopt)
        expected = {"template_catalog": blueprint_templates.catalog, "template_detail": blueprint_templates.detail,
                    "template_mutate": blueprint_templates.mutate, "network_state": blueprint_network.state,
                    "network_save": blueprint_network.save, "rehearse": blueprint_testing.run,
                    "rehearse_draft": blueprint_testing.run_draft, "control": blueprint_controls.control}
        for name, operation in expected.items():
            self.assertIs(getattr(map_blueprints, name), operation)
        self.assertEqual(set(map_blueprints.__all__), expected.keys())
        self.assertIs(universal_vtt.import_map, interchange.import_map)
        self.assertIs(universal_vtt.export_map, interchange.export_map)
        self.assertNotIn("parse", universal_vtt.__all__)

    def test_save_read_catalog_keep_campaign_scope_and_context_metadata(self):
        source = self.save_project(sceneId=str(uuid.uuid4()))
        self.assertEqual(source["document"], self.doc)
        self.assertEqual(self.invoke("mapBuilder", "read", {"projectId": source["id"]})["project"], source)
        catalog = self.invoke("mapBuilder", "state", {"mapId": str(uuid.uuid4())})
        self.assertEqual([row["id"] for row in catalog["projects"]], [source["id"]])
        self.assertNotIn(str(self.foreign_asset.pk), {row["id"] for row in catalog["assets"]})
        with self.assertRaises(services.MapError):
            map_builder.detail(self.other.pk, self.gm.pk, source["id"])
        self.assertEqual(map_builder.catalog(self.other.pk, self.gm.pk)["projects"], [])

    def test_every_capability_rechecks_live_gm_permission(self):
        self.generated()
        operations = (("mapBuilder", "state", {}), ("mapBuilder", "read", {"projectId": str(self.project_id)}),
                      ("blueprints", "templates", {}), ("blueprints", "state", {"sceneId": str(self.scene.pk)}),
                      ("maps", "exportUniversalVtt", {"sceneId": str(self.scene.pk)}),
                      ("maps", "navigate", {"mapId": str(self.scene.pk)}))
        for user in (self.player, self.streamer):
            for domain, method, payload in operations:
                with self.subTest(user=user.pk, method=method), self.assertRaises((services.MapError, JournalError)):
                    self.invoke(domain, method, payload, user=user)
        context = Context(self.campaign.pk, self.gm.pk)
        self.membership.delete()
        with self.assertRaises(JournalError):
            map_builder.catalog(context.campaign_id, context.user_id)
        with self.assertRaises(JournalError):
            self.invoke("blueprints", "templates")

    def test_save_retries_retain_fingerprint_and_reject_stale_or_changed_operations(self):
        rid = uuid.uuid4()
        payload = {"projectId": str(self.project_id), "expectedVersion": 0,
                   "folderId": str(self.folder.pk), "document": self.doc}
        saved = self.invoke("mapBuilder", "save", payload, request_id=rid)
        self.assertEqual(self.invoke("mapBuilder", "save", payload, request_id=rid), saved)
        changed = deepcopy(payload)
        changed["document"]["name"] = "A different operation"
        for attempted, request_id in ((changed, rid), (payload, uuid.uuid4())):
            with self.subTest(retry=request_id == rid), self.assertRaises(services.MapError) as failure:
                self.invoke("mapBuilder", "save", attempted, request_id=request_id)
            self.assertEqual(failure.exception.code, "conflict")
        self.assertEqual(MapBuilderProject.objects.get().document, self.doc)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_generate_is_private_and_delivery_waits_for_commit_and_replay_is_silent(self):
        source = self.save_project()
        rid = uuid.uuid4()
        payload = {"projectId": source["id"], "expectedVersion": 1}
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.invoke("mapBuilder", "generate", payload, request_id=rid)
                self.assertFalse(send.called)
            self.assertTrue(send.called)
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.invoke("mapBuilder", "generate", payload, request_id=rid), result)
            self.assertFalse(send.called)
        self.assertEqual(Scene.objects.get(pk=result["scene"]["id"]).visibility, "gm")
        self.assertFalse(Broadcast.objects.exists())
        self.assertEqual(Scene.objects.count(), 1)

    def test_update_and_sync_reject_project_retargeting_and_stale_scene_versions(self):
        source = self.generated()
        unrelated = Scene.objects.create(campaign=self.campaign, name="Another scene", width=32, height=32)
        payload = {"projectId": source["id"], "expectedVersion": source["version"],
                   "expectedSceneVersion": self.scene.version}
        for method in ("update", "sync"):
            with self.subTest(method=method), self.assertRaises(services.MapError) as failure:
                self.invoke("mapBuilder", method, payload, scene_id=unrelated.pk)
            self.assertEqual(failure.exception.code, "conflict")
            with self.assertRaises(services.MapError):
                self.invoke("mapBuilder", method, {**payload, "expectedSceneVersion": 999})
        result = self.invoke("mapBuilder", "sync", payload, scene_id=self.scene.pk)
        self.assertFalse(result["synchronized"])
        result = self.invoke("mapBuilder", "update", payload, scene_id=self.scene.pk)
        self.assertEqual(result["scene"]["id"], str(self.scene.pk))

    def test_update_and_sync_recheck_scene_identity_after_concurrent_project_regeneration(self):
        for method in ("update", "sync"):
            with self.subTest(method=method):
                self.project_id = uuid.uuid4()
                source = self.generated()
                mounted_scene = self.scene.pk
                original = getattr(map_builder, method)
                concurrent = {}

                def regenerate_then_call(*args):
                    generated = map_builder.generate(self.campaign.pk, self.gm.pk, self.project_id, {
                        "request_id": str(uuid.uuid4()), "expected_version": source["version"],
                    })
                    concurrent["scene"] = generated["scene"]
                    return original(*args)

                rid = uuid.uuid4()
                with patch.object(map_builder, method, side_effect=regenerate_then_call):
                    with self.assertRaises(services.MapError) as failure:
                        self.invoke("mapBuilder", method, {"projectId": source["id"],
                            "expectedVersion": source["version"], "expectedSceneVersion": self.scene.version},
                            request_id=rid, scene_id=mounted_scene)
                self.assertEqual(failure.exception.code, "conflict")
                replacement = Scene.objects.get(pk=concurrent["scene"]["id"])
                self.assertNotEqual(replacement.pk, mounted_scene)
                self.assertEqual(replacement.version, concurrent["scene"]["version"])
                self.assertFalse(Receipt.objects.filter(request_id=rid).exists())

    def test_adopt_uses_scene_revision_and_preserves_existing_native_identity(self):
        self.generated()
        before = self.door_object.pk
        version = self.scene.version
        with self.assertRaises(services.MapError):
            self.invoke("mapBuilder", "adopt", {"sceneId": str(self.scene.pk), "expectedSceneVersion": version + 1})
        rid = uuid.uuid4()
        payload = {"sceneId": str(self.scene.pk), "expectedSceneVersion": version}
        result = self.invoke("mapBuilder", "adopt", payload, request_id=rid)
        self.assertEqual(self.invoke("mapBuilder", "adopt", payload, request_id=rid), result)
        self.assertEqual(self.scene.elements.get(pk=before).pk, before)
        self.assertEqual(result["project"]["sceneId"], str(self.scene.pk))

    def test_template_library_create_read_update_delete_and_cross_campaign_rejection(self):
        payload = self.template_payload()
        rid = uuid.uuid4()
        first = self.invoke("blueprints", "saveTemplate", payload, request_id=rid)["template"]
        self.assertEqual(self.invoke("blueprints", "saveTemplate", payload, request_id=rid)["template"], first)
        self.assertEqual(self.invoke("blueprints", "readTemplate", {"templateId": first["id"]})["template"], first)
        self.assertEqual(self.invoke("blueprints", "templates")["templates"][0]["id"], first["id"])
        with self.assertRaises(services.MapError):
            map_blueprints.template_detail(self.other.pk, self.gm.pk, first["id"])
        updated = self.invoke("blueprints", "saveTemplate", {**payload, "expectedVersion": 1, "name": "Renamed"})["template"]
        self.assertEqual(updated["version"], 2)
        with self.assertRaises(services.MapError):
            self.invoke("blueprints", "deleteTemplate", {"templateId": first["id"], "expectedVersion": 1})
        self.invoke("blueprints", "deleteTemplate", {"templateId": first["id"], "expectedVersion": 2})
        self.assertFalse(BlueprintTemplate.objects.exists())

    def test_network_update_keeps_source_and_native_rule_in_sync(self):
        source = self.generated(blueprint=True)
        network = self.invoke("blueprints", "state", scene_id=self.scene.pk)
        self.assertIn(str(self.door_object.pk), {row["id"] for row in network["elements"]})
        raw = default_blueprint()
        payload = {"elementId": str(self.door_object.pk), "expectedVersion": self.door_object.version,
                   "expectedProjectVersion": source["version"], "blueprint": raw}
        rid = uuid.uuid4()
        result = self.invoke("blueprints", "save", payload, request_id=rid, scene_id=self.scene.pk)
        self.assertEqual(self.invoke("blueprints", "save", payload, request_id=rid, scene_id=self.scene.pk), result)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["blueprint"], raw)
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).document["doors"][0]["blueprint"], raw)
        with self.assertRaises(services.MapError):
            self.invoke("blueprints", "save", payload, scene_id=self.scene.pk)

    def test_live_control_uses_native_receipts_without_repeating_toggle(self):
        self.generated(blueprint=True)
        rid = uuid.uuid4()
        payload = {"sceneId": str(self.scene.pk), "elementId": str(self.door_object.pk),
                   "expectedVersion": self.door_object.version, "action": "state", "value": "open"}
        result = self.invoke("blueprints", "control", payload, request_id=rid)
        self.assertEqual(self.invoke("blueprints", "control", payload, request_id=rid), result)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual(Receipt.objects.filter(request_id=rid).count(), 1)

    def test_scene_and_draft_rehearsals_roll_back_changes_files_receipts_and_notifications(self):
        self.generated(blueprint=True)
        counts = (Scene.objects.count(), SceneObject.objects.count(), Tile.objects.count(), Receipt.objects.count())
        files = self.files()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            scene_result = self.invoke("blueprints", "test", {"sceneId": str(self.scene.pk),
                "elementId": str(self.door_object.pk), "expectedVersion": self.door_object.version, "event": "interact"})
            draft_result = self.invoke("blueprints", "testDraft", {"document": self.doc,
                "elementId": self.doc["doors"][0]["id"], "event": "interact"})
        self.assertTrue(scene_result["ok"], scene_result)
        self.assertTrue(draft_result["ok"], draft_result)
        self.assertEqual(scene_result["run"]["stateAfter"], "open")
        self.assertEqual(draft_result["run"]["stateAfter"], "open")
        self.assertEqual(counts, (Scene.objects.count(), SceneObject.objects.count(), Tile.objects.count(), Receipt.objects.count()))
        self.assertFalse(AutomationRun.objects.exists())
        self.assertEqual(self.files(), files)
        send.assert_not_called()
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")

    def test_python_uvtt_import_can_create_editable_project_and_json_export_keeps_original(self):
        rid, raw = uuid.uuid4(), self.raw_uvtt()
        imported = universal_vtt.import_map(self.campaign.pk, self.gm.pk, raw,
            name="Synthetic portable room", request_id=rid, builder_editable=True)
        self.assertTrue(imported["builderEditable"])
        self.assertEqual(universal_vtt.import_map(self.campaign.pk, self.gm.pk, raw,
            name="Synthetic portable room", request_id=rid, builder_editable=True), imported)
        scene = Scene.objects.get(pk=imported["scene"]["id"])
        original = list(scene.tiles.values("file", "byte_size"))
        exported = self.invoke("maps", "exportUniversalVtt", {"sceneId": str(scene.pk)})
        self.assertEqual(exported["document"]["format"], .2)
        self.assertTrue(exported["document"]["image"])
        self.assertEqual(list(scene.tiles.values("file", "byte_size")), original)
        self.assertEqual(Scene.objects.count(), 1)
        with self.assertRaises(services.MapError):
            public.invoke(self.other.pk, self.gm.pk, "maps", "exportUniversalVtt", {"sceneId": str(scene.pk)}, uuid.uuid4())
        with self.assertRaises(services.MapError):
            universal_vtt.import_map(self.campaign.pk, self.player.pk, raw, name="Forbidden", request_id=uuid.uuid4())

    def test_navigation_is_private_and_can_resume_following_broadcast(self):
        self.generated()
        rid = uuid.uuid4()
        result = self.invoke("maps", "navigate", {"mapId": str(self.scene.pk)}, request_id=rid)
        self.assertEqual(self.invoke("maps", "navigate", {"mapId": str(self.scene.pk)}, request_id=rid), result)
        self.assertEqual(SceneNavigation.objects.get(membership=self.membership).scene_id, self.scene.pk)
        self.assertFalse(Broadcast.objects.exists())
        self.invoke("maps", "navigate", {"mapId": None})
        self.assertIsNone(SceneNavigation.objects.get(membership=self.membership).scene_id)

    def test_adapter_rejects_identity_injection_scene_conflicts_and_unregistered_capabilities(self):
        source = self.save_project()
        for payload in ({"projectId": source["id"], "userId": str(self.gm.pk)},
                        {"projectId": source["id"], "request_id": str(uuid.uuid4())}):
            with self.subTest(payload=payload), self.assertRaises(services.MapError):
                self.invoke("mapBuilder", "read", payload)
        for domain, method in (("mapBuilder", "__dict__"), ("blueprints", "resolve_definition"),
                               ("maps", "importUniversalVtt"), ("__import__", "state")):
            with self.subTest(domain=domain, method=method), self.assertRaises(services.MapError):
                self.invoke(domain, method)
        with self.assertRaises(services.MapError) as failure:
            self.invoke("mapBuilder", "state", {"sceneId": str(uuid.uuid4())}, scene_id=uuid.uuid4())
        self.assertEqual(failure.exception.code, "conflict")
