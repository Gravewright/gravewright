"""GM live controls share native authority, revisions and transactional receipts."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.journals.services import JournalError
from gravewright.maps import blueprint_controls, objects, services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import AutomationRun, MapAsset, MapBuilderProject, Receipt, Scene, SceneObject
from gravewright.tokens.models import Token

from . import test_torches as fixtures
from .test_blueprint_references import node
from .test_blueprint_world import chain


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class SceneControlTests(TestCase):
    asset = fixtures.TorchTests.asset
    post = fixtures.TorchTests.post
    save = fixtures.TorchTests.save
    generate = fixtures.TorchTests.generate
    files = fixtures.TorchTests.files
    generated = fixtures.TorchTests.generated
    update_scene = fixtures.TorchTests.update_scene
    torch = fixtures.TorchTests.torch
    children = fixtures.TorchTests.children

    def setUp(self):
        fixtures.TorchTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = chain(event="interact")
        self.region_id = str(uuid.uuid4())
        self.doc["regions"] = [{"id": self.region_id, "layerId": self.doc["layers"][0]["id"],
            "name": "Controlled region", "x": 1, "y": 5, "width": 2, "height": 2,
            "enabled": True, "blueprint": default_blueprint("region")}]
        self.doc["floors"][0]["dynamic"] = True
        self.doc["walls"][0]["dynamic"] = True
        self.generated()

    def region(self):
        return self.scene.elements.get(kind="zones", data__region__isnull=False)

    def payload(self, action, value=None, *, row=None, request_id=None):
        row = row or SceneObject.objects.get(pk=self.door_object.pk)
        return {"request_id": str(request_id or uuid.uuid4()), "expected_version": row.version, "action": action,
                **({} if action == "interact" else {"value": value})}

    def control(self, action, value=None, *, row=None, payload=None, user=None, scene=None):
        row = row or SceneObject.objects.get(pk=self.door_object.pk)
        return blueprint_controls.control(self.campaign.pk, (user or self.gm).pk, (scene or self.scene).pk,
                                          row.pk, payload or self.payload(action, value, row=row))

    def test_gm_control_is_revision_checked_and_retries_use_exact_payload_receipt(self):
        payload = self.payload("state", "open")
        first = self.control("state", payload=payload)
        self.assertEqual(self.control("state", payload=payload), first)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual(self.door_object.version, first["version"])
        self.assertEqual(Receipt.objects.filter(request_id=payload["request_id"]).count(), 1)
        with self.assertRaises(services.MapError) as error:
            self.control("state", payload={**payload, "value": "closed"})
        self.assertEqual(error.exception.code, "conflict")
        with self.assertRaises(services.MapError) as error:
            self.control("state", payload={**payload, "request_id": str(uuid.uuid4()), "value": "closed"})
        self.assertEqual(error.exception.code, "conflict")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_players_streamers_and_foreign_scene_elements_are_rejected(self):
        before = deepcopy(self.door_object.data)
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises((services.MapError, JournalError)):
                self.control("state", "open", user=user)
        foreign_scene = Scene.objects.create(campaign=self.other, name="Foreign", width=512, height=512)
        foreign = SceneObject.objects.create(scene=foreign_scene, kind="walls", data=deepcopy(before))
        with self.assertRaises(services.MapError):
            self.control("state", "open", row=foreign)
        with self.assertRaises(services.MapError):
            self.control("state", "open", row=foreign, scene=foreign_scene)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data, before)

    def test_payload_shapes_are_strict_and_do_not_create_receipts(self):
        payload = self.payload("state", "open")
        for change in ({"expected_version": True}, {"expected_version": 0}, {"action": "unknown"},
                       {"action": "interact"}, {"extra": "untrusted"}, {"value": "off"}):
            candidate = {**payload, **change, "request_id": str(uuid.uuid4())}
            with self.subTest(change=change), self.assertRaises(services.MapError):
                self.control("state", payload=candidate)
            self.assertFalse(Receipt.objects.filter(request_id=candidate["request_id"]).exists())
        missing = self.payload("state", "open")
        missing.pop("value")
        with self.assertRaises(services.MapError):
            self.control("state", payload=missing)

    def test_interaction_gate_blocks_players_but_gm_override_uses_native_graphs(self):
        self.control("interaction", False)
        self.door_object.refresh_from_db()
        self.assertFalse(self.door_object.data["interactionEnabled"])
        with self.assertRaisesMessage(services.MapError, "interaction is disabled"):
            services.command(self.campaign.pk, self.player.pk, "objects", {"mapId": str(self.scene.pk),
                "area": "walls", "action": "door", "data": {"wall_id": str(self.door_object.pk), "door_state": "open"}}, uuid.uuid4())
        self.control("state", "open")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_explicit_door_state_does_not_start_interaction_or_named_signal_graphs(self):
        raw = chain(node("stay", "state", targetState="closed"),
                    node("mark", "setVariable", scope="scene", name="Interacted", valueType="boolean", value=True),
                    event="interact")
        raw["graphs"].update(chain(node("signal", "setVariable", scope="scene", name="Signaled", valueType="boolean", value=True),
                                   node("lamp", "light", targetId=str(self.light_object.pk), enabled=False),
                                   event="signal:Effects")["graphs"])
        self.door_object.data["blueprint"] = raw
        self.door_object.save(update_fields=["data"])
        self.control("state", "open")
        self.door_object.refresh_from_db()
        self.scene.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertNotIn("Signaled", self.scene.settings.get("automationVariables", {}))
        self.assertNotIn("Interacted", self.scene.settings.get("automationVariables", {}))
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).latest("created_at").data["events"], [])
        self.control("state", "closed")
        self.control("interact")
        self.door_object.refresh_from_db()
        self.scene.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertIn("Interacted", self.scene.settings["automationVariables"])
        self.assertNotIn("Signaled", self.scene.settings["automationVariables"])
        self.assertEqual([entry["event"] for entry in AutomationRun.objects.filter(scene=self.scene).latest("created_at").data["events"]],
                         ["interact"])

    def test_explicit_mechanism_state_and_native_interaction_are_distinct(self):
        torch = self.torch()
        raw = chain(node("stay", "state", targetState="off"), event="interact", kind="torch")
        torch.data["blueprint"] = raw
        torch.save(update_fields=["data"])
        self.control("state", "on", row=torch)
        torch.refresh_from_db()
        self.assertEqual(torch.data["torch"]["state"], "on")
        self.control("state", "off", row=torch)
        torch.refresh_from_db()
        self.control("interact", row=torch)
        torch.refresh_from_db()
        self.assertEqual(torch.data["torch"]["state"], "off")

    def test_authored_interaction_turns_torch_and_flame_is_independent_without_graph_events(self):
        torch = self.torch()
        self.control("interact", row=torch)
        torch.refresh_from_db()
        self.assertEqual(torch.data["torch"]["state"], "on")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        runs = AutomationRun.objects.filter(scene=self.scene).count()
        self.control("flame", False, row=torch)
        torch.refresh_from_db()
        self.assertFalse(torch.data["torch"]["lit"])
        self.assertEqual(torch.data["torch"]["state"], "on")
        self.assertTrue(all(not row.data["enabled"] for row in self.children(torch).values()))
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), runs)

    def test_hiding_and_restoring_torch_gates_all_owned_components(self):
        torch = self.torch()
        self.control("visibility", False, row=torch)
        torch.refresh_from_db()
        self.assertEqual(torch.data["layer"], "gm-image-layer")
        self.assertTrue(all(not row.data["enabled"] for row in self.children(torch).values()))
        self.control("appearance", None, row=torch)
        torch.refresh_from_db()
        self.assertEqual(torch.data["layer"], "map")
        children = self.children(torch)
        self.assertTrue(children["lights"].data["enabled"])
        self.assertTrue(children["particles"].data["enabled"])
        self.assertFalse(children["shaders"].data["enabled"])

    def test_dynamic_material_restore_preserves_generated_art_mask_and_barriers(self):
        barriers = list(self.scene.elements.filter(kind="walls").values("id", "data", "version"))
        files = self.files()
        for surface in self.scene.elements.filter(kind="images", data__surface__isnull=False):
            with self.subTest(kind=surface.data["surface"]["kind"]):
                base, mask = surface.data["asset_id"], surface.data["surface"]["maskId"]
                self.control("appearance", str(self.floor.pk), row=surface)
                surface.refresh_from_db()
                self.assertEqual(surface.data["surface"]["materialId"], str(self.floor.pk))
                self.control("visibility", False, row=surface)
                surface.refresh_from_db()
                self.assertEqual(surface.data["layer"], "gm-image-layer")
                self.control("appearance", None, row=surface)
                surface.refresh_from_db()
                self.assertNotIn("materialId", surface.data["surface"])
                self.assertNotIn("materialCrop", surface.data["surface"])
                self.assertEqual((surface.data["asset_id"], surface.data["surface"]["maskId"]), (base, mask))
        self.assertEqual(list(self.scene.elements.filter(kind="walls").values("id", "data", "version")), barriers)
        self.assertEqual(self.files(), files)

    def test_assets_are_campaign_owned_and_generated_masks_cannot_become_materials(self):
        surface = self.scene.elements.filter(kind="images", data__surface__isnull=False).first()
        before = deepcopy(surface.data)
        generated = MapAsset.objects.filter(generated_for=self.scene).first()
        for target in (self.foreign_asset, generated):
            with self.subTest(asset=target.pk), self.assertRaisesMessage(services.MapError, "image from this campaign"):
                self.control("appearance", str(target.pk), row=surface)
        surface.refresh_from_db()
        self.assertEqual(surface.data, before)

    def test_region_control_rebaselines_without_running_presence_graphs(self):
        region = self.region()
        actor = Actor.objects.create(campaign=self.campaign, name="Occupant", data={})
        token = Token.objects.create(scene=self.scene, actor=actor, grid_x=1, grid_y=5)
        previous_runs = AutomationRun.objects.filter(scene=self.scene).count()
        self.control("region", False, row=region)
        region.refresh_from_db()
        self.assertFalse(region.data["enabled"])
        self.control("region", True, row=region)
        region.refresh_from_db()
        self.assertTrue(region.data["enabled"])
        self.assertEqual(region.data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(region.data["region"]["state"], "occupied")
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), previous_runs)

    def test_door_artwork_controls_restore_state_appearance_without_touching_collision(self):
        before = {key: deepcopy(value) for key, value in self.door_object.data.items() if key != "sprite"}
        self.control("appearance", str(self.floor.pk))
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["sprite"], {"appearance": "asset", "assetId": str(self.floor.pk)})
        self.control("appearance", None)
        self.door_object.refresh_from_db()
        self.assertNotIn("sprite", self.door_object.data)
        self.assertEqual(self.door_object.data, before)

    def test_unsupported_controls_reject_without_changing_owner(self):
        region = self.region()
        light = self.children()["lights"]
        before = list(self.scene.elements.values("id", "data", "version"))
        for row, action, value in ((region, "state", "open"), (region, "interaction", True),
                                  (light, "visibility", False), (light, "appearance", None),
                                  (self.door_object, "flame", True), (self.door_object, "region", False)):
            with self.subTest(row=row.pk, action=action), self.assertRaises(services.MapError):
                self.control(action, value, row=row)
        self.assertEqual(list(self.scene.elements.values("id", "data", "version")), before)

    def test_authored_project_is_preserved_and_runtime_controls_survive_explicit_update(self):
        project = MapBuilderProject.objects.get(pk=self.project_id)
        document, version = deepcopy(project.document), project.version
        self.control("state", "open")
        self.control("interaction", False)
        torch = self.torch()
        self.control("flame", False, row=torch)
        region = self.region()
        self.control("region", False, row=region)
        surface = self.scene.elements.filter(kind="images", data__surface__kind="floor").get()
        self.control("appearance", str(self.floor.pk), row=surface)
        surface.refresh_from_db()
        self.control("visibility", False, row=surface)
        project.refresh_from_db()
        self.assertEqual((project.document, project.version), (document, version))
        self.update_scene()
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertFalse(self.door_object.data["interactionEnabled"])
        self.assertFalse(self.torch().data["torch"]["lit"])
        self.assertFalse(self.region().data["enabled"])
        surface.refresh_from_db()
        self.assertEqual(surface.data["surface"]["materialId"], str(self.floor.pk))
        self.assertEqual(surface.data["layer"], "gm-image-layer")
        project.refresh_from_db()
        self.assertEqual(project.document, document)

    def test_receipt_failure_rolls_back_native_source_children_and_notifications(self):
        before = list(self.scene.elements.values("id", "data", "version"))
        project = MapBuilderProject.objects.get(pk=self.project_id)
        manifest = deepcopy(project.generation)
        payload = self.payload("visibility", False, row=self.torch())
        with patch("gravewright.maps.blueprint_controls.record", side_effect=services.MapError("Synthetic receipt failure")), \
                patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, "Synthetic receipt failure"):
                self.control("visibility", row=self.torch(), payload=payload)
        self.assertEqual(list(self.scene.elements.values("id", "data", "version")), before)
        project.refresh_from_db()
        self.assertEqual(project.generation, manifest)
        self.assertFalse(Receipt.objects.filter(request_id=payload["request_id"]).exists())
        send.assert_not_called()

