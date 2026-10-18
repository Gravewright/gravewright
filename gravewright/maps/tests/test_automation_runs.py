"""GM-only log of door blueprint runs: completed, blocked and failed attempts."""

from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings

from gravewright.journals.services import JournalError, member
from gravewright.maps import services
from gravewright.maps.blueprint_runtime import RUN_HISTORY, record_run
from gravewright.maps.models import AutomationRun

from . import test_builder_blueprints as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class AutomationRunTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.generated()
        self.url = f"/api/maps/{self.scene.pk}/automation"

    def runs(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["runs"]

    def test_completed_run_lists_steps_once_per_operation_and_notifies_after_commit(self):
        request_id = uuid.uuid4()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.command("open", request_id=request_id)
        self.assertIn({"type": "room.automation", "sceneId": str(self.scene.pk)},
                      [call.args[1] for call in send.call_args_list])
        self.command("open", request_id=request_id)
        run, = self.runs()
        self.assertEqual(run["outcome"], "completed")
        self.assertEqual(run["doorId"], str(self.door_object.pk))
        self.assertEqual((run["stateBefore"], run["stateAfter"], run["requested"]), ("closed", "open", "open"))
        self.assertEqual(run["actor"], {"name": "GM", "role": "gm"})
        data = self.door_object.data
        self.assertEqual(run["point"], {"x": round((data["x1"] + data["x2"]) / 2, 2),
                                        "y": round((data["y1"] + data["y2"]) / 2, 2)})
        self.assertEqual([event["event"] for event in run["events"]], ["interact"])
        entry = run["events"][-1]
        self.assertNotIn("previous", entry, "The base event does not synthesize a state transition.")
        self.assertEqual(entry["steps"], [
            {"id": "event", "type": "event"},
            {"id": "locked", "type": "condition", "result": False},
            {"id": "open", "type": "condition", "result": False},
            {"id": "open-state", "type": "state", "state": "open"},
            {"id": "open-light", "type": "light", "enabled": True},
            {"id": "open-sound", "type": "sound", "sound": "Door click", "volume": .35},
        ])

    def test_locked_interaction_and_refused_locked_or_secret_door_are_logged_for_the_gm(self):
        self.command("locked", action="update", version=self.door_object.version)
        self.command("open", user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "locked")
        completed = self.runs()[0]
        self.assertEqual((completed["outcome"], completed["actor"]["role"]), ("completed", "player"))
        self.assertEqual(completed["events"][0]["event"], "interact")
        self.assertEqual(completed["events"][0]["steps"][1], {"id": "locked", "type": "condition", "result": True})
        self.door_object.data["blueprint"]["graphs"]["interact"]["edges"] = []
        self.door_object.save(update_fields=["data"])
        with self.assertRaisesMessage(services.MapError, "cannot be operated"):
            self.command("open", user=self.player)
        refused = self.runs()[0]
        self.assertEqual((refused["outcome"], refused["actor"]["role"], refused["events"]), ("failed", "player", []))
        self.door_object.refresh_from_db()
        self.command(action="update", version=self.door_object.version, target="closed",
                     presentation="secret", discovered=False)
        with self.assertRaisesMessage(services.MapError, "cannot be operated"):
            self.command("open", user=self.player)
        refused = self.runs()[0]
        self.assertEqual(refused["outcome"], "failed")
        self.assertEqual(refused["events"], [])
        self.assertEqual(refused["message"], "This door cannot be operated.")

    @override_settings(DYNAMIC_LIGHTING_ENABLED=False)
    def test_failed_effect_keeps_partial_trace_without_persisting_effects(self):
        self.light_object.refresh_from_db()
        light_version = self.light_object.version
        with self.assertRaisesMessage(services.MapError, "Dynamic lighting is disabled"):
            self.command("open")
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual(self.light_object.version, light_version)
        failed = self.runs()[0]
        self.assertEqual((failed["outcome"], failed["stateAfter"]), ("failed", "closed"))
        self.assertEqual(failed["events"][-1]["event"], "interact")
        self.assertEqual(failed["message"], "Dynamic lighting is disabled.")

    def test_only_game_masters_read_the_log_and_each_scene_keeps_recent_runs(self):
        self.command("open")
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.gm)
        who = member(self.campaign.pk, self.gm.pk)
        for index in range(RUN_HISTORY + 2):
            record_run(self.scene, who, self.door_object, "completed",
                       {"requested": "open", "stateBefore": "open", "stateAfter": "open", "events": [], "index": index})
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), RUN_HISTORY)
        runs = self.runs()
        self.assertEqual(len(runs), RUN_HISTORY)
        self.assertEqual(runs[0]["index"], RUN_HISTORY + 1, "newest first")

    def automation(self, action, user=None, **data):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects",
            {"mapId": str(self.scene.pk), "area": "automation", "action": action, "data": data}, uuid.uuid4())

    def state(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_paused_scene_preserves_blueprint_state_and_logs_paused_runs(self):
        self.light_object.refresh_from_db()
        light_version = self.light_object.version
        self.assertEqual(self.automation("pause", paused=True), {"automationPaused": True})
        self.assertIs(self.state()["paused"], True)
        self.command("open")
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual(self.light_object.version, light_version, "graphs do not run while paused")
        run = self.runs()[0]
        self.assertEqual((run["outcome"], run["stateBefore"], run["stateAfter"], run["events"]),
                         ("paused", "closed", "closed", []))
        # Paused locked doors lose their interaction exception for players.
        self.command("locked", action="update", version=self.door_object.version)
        with self.assertRaisesMessage(services.MapError, "cannot be operated"):
            self.command("open", user=self.player)
        self.automation("pause", paused=False)
        self.assertIs(self.state()["paused"], False)
        self.command("open", user=self.player)
        self.assertEqual(self.runs()[0]["outcome"], "completed")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "locked")
        self.scene.refresh_from_db()
        self.assertNotIn("automationPaused", self.scene.settings)

    def test_gm_lists_doors_triggers_interaction_and_clears_live_sprite(self):
        doors = self.state()["doors"]
        self.assertEqual([door["id"] for door in doors], [str(self.door_object.pk)])
        self.assertEqual(doors[0]["events"], ["interact"])
        self.assertIs(doors[0]["sprite"], False)
        self.door_object.data["sprite"] = {"appearance": "hidden"}
        self.door_object.save(update_fields=["data"])
        self.assertIs(self.state()["doors"][0]["sprite"], True)
        result = self.automation("clear-sprite", wall_id=str(self.door_object.pk))
        self.assertEqual(result, {"wallId": str(self.door_object.pk), "sprite": False})
        self.door_object.refresh_from_db()
        self.assertNotIn("sprite", self.door_object.data)
        # Requesting the current state runs only the interaction graph.
        self.command("locked", action="update", version=self.door_object.version)
        self.command("locked")
        self.assertEqual([event["event"] for event in self.runs()[0]["events"]], ["interact"])
        for action, data in (("pause", {"paused": "yes"}), ("clear-sprite", {"wall_id": str(self.light_object.pk)}), ("other", {})):
            with self.subTest(action=action), self.assertRaises(services.MapError):
                self.automation(action, **data)
        for user in (self.player, self.streamer):
            # Players fail the GM check; streamers are already read-only.
            with self.subTest(user=user.name), self.assertRaises((services.MapError, JournalError)):
                self.automation("pause", user=user, paused=True)
