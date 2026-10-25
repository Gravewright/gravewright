"""Real-engine rehearsals leave campaign state, files and delivery untouched."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.audio.models import Playback
from gravewright.journals.services import JournalError
from gravewright.maps import blueprint_testing, services
from gravewright.maps.models import (AutomationDelay, AutomationRun, MapAsset, MapBuilderProject,
                                     Receipt, Scene, SceneObject, SceneState, Tile)
from gravewright.tokens.models import Token

from . import test_builder_blueprints as fixtures
from .test_blueprint_references import data, execution, node
from .test_blueprint_world import audience, chain


EVENT = "interact"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BlueprintTestingTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = chain()
        self.actor = Actor.objects.create(campaign=self.campaign, name="Rehearsal hero", data={})

    def snapshot(self):
        models = (Scene, SceneObject, SceneState, MapAsset, MapBuilderProject, Token, Playback,
                  AutomationDelay, AutomationRun, Receipt, Tile)
        return {model._meta.label: list(model.objects.order_by("pk").values()) for model in models}

    def payload(self, **extra):
        return {"request_id": str(uuid.uuid4()), "event": EVENT,
                "expected_version": self.door_object.version, **extra}

    def draft(self, document=None, **extra):
        return {"request_id": str(uuid.uuid4()), "document": deepcopy(document or self.doc),
                "elementId": self.doc["doors"][0]["id"], "event": EVENT, **extra}

    def rehearse(self, payload, *, user=None, owner=None, scene=None):
        return blueprint_testing.run(self.campaign.pk, (user or self.gm).pk, (scene or self.scene).pk,
                                     (owner or self.door_object).pk, payload)

    def test_scene_runs_real_effects_and_returns_predictions_but_rolls_back_everything(self):
        self.generated()
        raw = chain(node("state", "state", targetState="open"),
            node("lamp", "light", targetId=str(self.light_object.pk), enabled=True),
            node("sound", "sound", trackId=str(self.sound.pk), volume=.3),
            node("variable", "setVariable", scope="scene", name="Alarm", valueType="boolean", value=True),
            node("message", "showMessage", text="Never delivered", audience=audience("players")),
            node("timer", "timer", name="Alarm", action="restart", seconds=1),
            node("wait", "delay", seconds=1),
            node("later", "light", targetId=str(self.light_object.pk), enabled=False))
        before, files = self.snapshot(), self.files()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = self.rehearse(self.payload(blueprint=raw))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["run"]["stateAfter"], "open")
        self.assertTrue(next(row for row in result["changes"]["elements"]
                             if row["id"] == str(self.light_object.pk))["after"]["data"]["enabled"])
        self.assertIn("Alarm", result["changes"]["sceneVariables"]["after"])
        self.assertEqual(result["changes"]["audio"]["after"]["data"]["ambient"][0]["status"], "playing")
        self.assertEqual({row["after"]["kind"] for row in result["scheduled"]}, {"delay", "timer"})
        self.assertEqual(set(result["warnings"]), {"timing-not-advanced", "presentation-not-delivered"})
        send.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.files(), files)

    def test_chosen_event_is_exact_and_does_not_force_its_named_state(self):
        self.doc["doors"][0]["blueprint"] = chain(node("lamp", "light", targetId=self.light_id, enabled=True), event="signal:Open")
        self.generated()
        result = self.rehearse(self.payload(event="signal:Open"))
        self.assertEqual([entry["event"] for entry in result["run"]["events"]], ["signal:Open"])
        self.assertEqual(result["run"]["stateAfter"], "closed")
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_failure_reports_trace_and_no_partial_effect_prediction_or_persisted_effect(self):
        self.generated()
        raw = chain(node("lamp", "light", targetId=str(self.light_object.pk), enabled=True),
                    node("outside", "cameraFocus", focusX=1000, focusY=0, audience=audience()))
        before = self.snapshot()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = self.rehearse(self.payload(blueprint=raw))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["message"], "Camera focus is outside the map.")
        self.assertEqual(result["changes"]["elements"], [])
        self.assertEqual(result["scheduled"], [])
        self.assertEqual([step["id"] for step in result["run"]["events"][0]["steps"]], ["event", "lamp", "outside"])
        self.assertEqual(self.snapshot(), before)
        send.assert_not_called()

    def test_authorization_scene_owner_token_and_revision_are_checked_before_test(self):
        self.generated()
        before = self.snapshot()
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises((services.MapError, JournalError)):
                self.rehearse(self.payload(), user=user)
        with self.assertRaises(services.MapError) as failure:
            self.rehearse(self.payload(expected_version=self.door_object.version + 1))
        self.assertEqual(failure.exception.code, "conflict")
        foreign_scene = Scene.objects.create(campaign=self.other, name="Other", width=512, height=512)
        foreign_actor = Actor.objects.create(campaign=self.other, name="Other actor", data={})
        token = Token.objects.create(scene=foreign_scene, actor=foreign_actor)
        with self.assertRaisesMessage(services.MapError, "test token"):
            self.rehearse(self.payload(tokenId=str(token.pk)))
        with self.assertRaisesMessage(services.MapError, "Scene not found"):
            self.rehearse(self.payload(), scene=foreign_scene)
        foreign_scene.delete()
        self.assertEqual(self.snapshot(), before)

    def test_payload_rejects_untrusted_context_and_missing_event(self):
        self.generated()
        for extra in ({"context": {"userId": str(self.player.pk)}}, {"actorId": str(self.actor.pk)},
                      {"expected_version": True}, {"blueprint": None}):
            with self.subTest(extra=extra), self.assertRaises(services.MapError):
                self.rehearse(self.payload(**extra))
        with self.assertRaisesMessage(services.MapError, "event defined"):
            self.rehearse(self.payload(event="signal:absent"))

    def test_named_timer_cancellation_is_only_predicted_and_existing_deadline_is_preserved(self):
        self.doc["doors"][0]["blueprint"] = chain(node("timer", "timer", name="Clock", action="start", seconds=60))
        self.generated()
        self.command(target="closed")
        wait = AutomationDelay.objects.get(scene=self.scene, status="pending")
        self.door_object.refresh_from_db()
        before = self.snapshot()
        result = self.rehearse(self.payload(blueprint=chain(node("timer", "timer", name="Clock", action="stop"))))
        self.assertEqual(result["scheduled"][0]["before"]["status"], "pending")
        self.assertEqual(result["scheduled"][0]["after"]["status"], "cancelled")
        self.assertEqual(self.snapshot(), before)
        wait.refresh_from_db()
        self.assertEqual(wait.status, "pending")

    def test_scene_token_identity_is_read_from_server_and_never_persistently_moved(self):
        self.generated()
        token = Token.objects.create(scene=self.scene, actor=self.actor, grid_x=1, grid_y=1)
        raw = chain(node("identity", "setVariable", scope="element", name="Trigger", valueType="text", value=""))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("token", "eventContext", property="tokenId"))
        graph["edges"].append(data("token", "value", "identity", "value"))
        before = self.snapshot()
        result = self.rehearse(self.payload(blueprint=raw, tokenId=str(token.pk)))
        self.assertTrue(result["ok"], result)
        context = result["run"]["context"]
        self.assertEqual((context["tokenId"], context["actorId"], context["userId"], context["sourceId"]),
                         (str(token.pk), str(self.actor.pk), str(self.gm.pk), str(self.door_object.pk)))
        owner = next(row for row in result["changes"]["elements"] if row["id"] == str(self.door_object.pk))
        self.assertEqual(owner["after"]["data"]["automationVariables"]["Trigger"]["value"], str(token.pk))
        self.assertEqual(self.snapshot(), before)

    def test_cross_element_signal_uses_the_normal_queue_and_rolls_back_both_owners(self):
        self.generated()
        raw = chain(node("change", "state", targetState="open"), event="signal:Open")
        other = SceneObject.objects.create(scene=self.scene, kind="walls", data={**deepcopy(self.door_object.data),
            "x1": 300, "x2": 350, "blueprint": raw})
        trigger = chain(node("signal", "emitEvent", scope="element", name="Open"))
        graph = trigger["graphs"][EVENT]
        graph["nodes"].append(node("target", "reference", targetId=str(other.pk)))
        graph["edges"].append(data("target", "door", "signal", "target"))
        before = self.snapshot()
        result = self.rehearse(self.payload(blueprint=trigger))
        self.assertTrue(result["ok"], result)
        predicted = next(row for row in result["changes"]["elements"] if row["id"] == str(other.pk))
        self.assertEqual(predicted["after"]["data"]["door_state"], "open")
        self.assertIn("signal:Open", [entry["event"] for entry in result["run"]["events"]])
        self.assertEqual(self.snapshot(), before)

    def test_paused_scene_is_rehearsed_explicitly_without_changing_pause_flag(self):
        self.doc["doors"][0]["blueprint"] = chain(node("open", "state", targetState="open"),
            node("lamp", "light", targetId=self.light_id, enabled=True))
        self.generated()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        before = self.snapshot()
        result = self.rehearse(self.payload())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["run"]["stateAfter"], "open")
        self.assertEqual([event["event"] for event in result["run"]["events"]], ["interact"])
        self.assertEqual([step["id"] for step in result["run"]["events"][0]["steps"]], ["event", "open", "lamp"])
        self.assertTrue(result["runs"])
        lamp = next(row for row in result["changes"]["elements"] if row["id"] == str(self.light_object.pk))
        self.assertTrue(lamp["after"]["data"]["enabled"])
        self.assertIn("automation-paused", result["warnings"])
        self.assertEqual(self.snapshot(), before)
        self.scene.refresh_from_db()
        self.assertIs(self.scene.settings["automationPaused"], True)
        self.command("open")
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertFalse(self.light_object.data["enabled"])
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "paused")

    def test_paused_destroy_rehearsal_predicts_actions_and_removal_without_enabling_live_destroy(self):
        self.doc["doors"][0]["blueprint"] = chain(node("lamp", "light", targetId=self.light_id, enabled=True), event="destroy")
        self.generated()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        before = self.snapshot()
        result = self.rehearse(self.payload(event="destroy"))
        self.assertTrue(result["ok"], result)
        self.assertIn("automation-paused", result["warnings"])
        self.assertEqual([event["event"] for event in result["run"]["events"]], ["destroy"])
        self.assertTrue(result["runs"])
        removed = next(row for row in result["changes"]["elements"] if row["id"] == str(self.door_object.pk))
        self.assertIsNone(removed["after"])
        lamp = next(row for row in result["changes"]["elements"] if row["id"] == str(self.light_object.pk))
        self.assertTrue(lamp["after"]["data"]["enabled"])
        self.assertEqual(self.snapshot(), before)
        self.scene.refresh_from_db()
        self.assertIs(self.scene.settings["automationPaused"], True)
        self.command(action="delete")
        self.assertFalse(SceneObject.objects.filter(pk=self.door_object.pk).exists())
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_failed_paused_rehearsal_restores_pause_for_the_next_live_command(self):
        self.doc["doors"][0]["blueprint"] = chain(node("open", "state", targetState="open"))
        self.generated()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        raw = chain(node("open", "state", targetState="open"),
            node("lamp", "light", targetId=str(self.light_object.pk), enabled=True),
            node("sound", "sound", trackId=str(self.sound.pk), volume=.3))
        before = self.snapshot()
        with patch("gravewright.audio.services.play_effects", side_effect=RuntimeError("Synthetic audio failure")):
            with self.assertRaisesMessage(RuntimeError, "Synthetic audio failure"):
                self.rehearse(self.payload(blueprint=raw))
        self.assertEqual(self.snapshot(), before)
        self.scene.refresh_from_db()
        self.assertIs(self.scene.settings["automationPaused"], True)
        self.command("open")
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertFalse(self.light_object.data["enabled"])
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "paused")

    def test_draft_position_is_bounded_and_rehearsal_still_rolls_back(self):
        before = self.snapshot()
        result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk,
            self.draft(actorId=str(self.actor.pk), position={"x": 1.5, "y": 1.5}))
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.snapshot(), before)
        for position in ({"x": -1, "y": 1}, {"x": True, "y": 1}, {"x": 10000, "y": 1}, []):
            with self.subTest(position=position), self.assertRaises(services.MapError):
                blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft(position=position))
            self.assertEqual(self.snapshot(), before)

    def test_draft_executes_current_unsaved_source_and_binds_native_resources_without_files(self):
        self.doc["doors"][0]["blueprint"] = chain(node("lamp", "light", targetId=self.light_id, enabled=True),
            node("variable", "setVariable", scope="element", name="Draft", valueType="number", value=42))
        before, files, document = self.snapshot(), self.files(), deepcopy(self.doc)
        with patch("gravewright.maps.builder_render.render", side_effect=AssertionError("must not render")), \
                patch("django.core.files.storage.default_storage.save", side_effect=AssertionError("must not write")), \
                patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["mode"], "draft")
        lamp = next(row for row in result["changes"]["elements"] if row["sourceId"] == self.light_id)
        self.assertTrue(lamp["after"]["data"]["enabled"])
        self.assertEqual(result["sourceIds"][lamp["id"]], self.light_id)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.doc, document)
        self.assertEqual(self.files(), files)
        send.assert_not_called()

    def test_dynamic_draft_targets_are_metadata_only_and_support_real_visual_actions(self):
        floor = self.doc["floors"][0]
        floor["dynamic"] = True
        raw = chain(node("visible", "setVisibility", visible=False),
                    node("material", "setAppearance", assetId=str(self.floor.pk)))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("target", "reference", targetId=floor["id"]))
        graph["edges"].extend(data("target", "door", action, "target") for action in ("visible", "material"))
        self.doc["doors"][0]["blueprint"] = raw
        before, files = self.snapshot(), self.files()
        with patch("django.core.files.storage.default_storage.save", side_effect=AssertionError("must not write")):
            result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft())
        self.assertTrue(result["ok"], result)
        prediction = next(row for row in result["changes"]["elements"] if row["sourceId"] == floor["id"])
        self.assertEqual(prediction["after"]["data"]["layer"], "gm-image-layer")
        self.assertEqual(prediction["after"]["data"]["surface"]["materialId"], str(self.floor.pk))
        self.assertEqual(prediction["after"]["data"]["src"], "")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.files(), files)

    def test_draft_teleport_uses_campaign_actor_or_skips_missing_token_and_continues(self):
        source, destination = str(uuid.uuid4()), str(uuid.uuid4())
        self.doc["regions"] = [{"id": key, "layerId": self.doc["layers"][0]["id"], "name": name,
            "x": x, "y": 5, "width": 2, "height": 2, "enabled": True}
            for key, name, x in ((source, "Departure", 1), (destination, "Arrival", 5))]
        raw = chain(node("portal", "teleport", destinationId=destination),
                    node("lamp", "light", targetId=self.light_id, enabled=True), event="presence:enter", kind="region")
        self.doc["regions"][0]["blueprint"] = raw
        before = self.snapshot()
        payload = self.draft(elementId=source, event="presence:enter")
        without = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, payload)
        self.assertTrue(without["ok"], without)
        self.assertIn("missing-test-token", without["warnings"])
        self.assertEqual(without["changes"]["tokens"], [])
        self.assertTrue(any(row["sourceId"] == self.light_id for row in without["changes"]["elements"]))
        with_actor = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, {**payload, "actorId": str(self.actor.pk)})
        self.assertTrue(with_actor["ok"], with_actor)
        self.assertEqual(with_actor["changes"]["tokens"][0]["after"]["grid_x"], 5)
        self.assertNotIn("missing-test-token", with_actor["warnings"])
        # The run ends while the token is still inside; the presence pass after the
        # teleport empties the departure region, and the test reports that end state.
        self.assertEqual(with_actor["run"]["stateAfter"], "occupied")
        self.assertEqual(with_actor["state"], {"before": "occupied", "after": "empty"})
        self.assertEqual(with_actor["testTokenId"], with_actor["changes"]["tokens"][0]["id"])
        self.assertNotIn("testTokenId", without)
        self.assertEqual(self.snapshot(), before)

    def test_draft_rejects_foreign_actor_and_player_without_creating_a_scene(self):
        actor = Actor.objects.create(campaign=self.other, name="Foreign", data={})
        before = self.snapshot()
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises((services.MapError, JournalError)):
                blueprint_testing.run_draft(self.campaign.pk, user.pk, self.draft())
        with self.assertRaisesMessage(services.MapError, "test actor"):
            blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft(actorId=str(actor.pk)))
        self.assertEqual(self.snapshot(), before)

    def test_same_request_random_is_reproducible_and_tests_do_not_consume_gate_memory(self):
        raw = chain(node("once", "once"))
        graph = raw["graphs"][EVENT]
        graph["nodes"].extend([node("pick", "random", weights=[1, 1]),
                              node("left", "setVariable", scope="scene", name="Choice", valueType="number", value=1),
                              node("right", "setVariable", scope="scene", name="Choice", valueType="number", value=2)])
        graph["edges"].extend([execution("once", "pick", "true"), execution("pick", "left", "branch1"),
                               execution("pick", "right", "branch2")])
        self.doc["doors"][0]["blueprint"] = raw
        payload = self.draft()
        first = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, payload)
        second = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, payload)
        self.assertTrue(first["ok"], first)
        self.assertEqual(first["changes"]["sceneVariables"], second["changes"]["sceneVariables"])
        self.assertFalse(Scene.objects.exists())

