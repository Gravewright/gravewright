"""Authored roll prompts and quest actions retain campaign and retry boundaries."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.administration.archives import export_campaign, import_campaign
from gravewright.campaigns.models import Membership
from gravewright.journals.models import Access, Journal, Receipt as JournalReceipt
from gravewright.maps import blueprint_testing, services
from gravewright.maps.blueprint_delays import invalid_reason
from gravewright.maps.blueprint_runtime import clean_native_blueprint
from gravewright.maps.blueprints import clean_blueprint, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject

from . import test_builder_blueprints as fixtures
from . import test_blueprint_delays as delay_fixtures
from .test_blueprint_references import node
from .test_blueprint_world import audience, chain


def roll_prompt(**values):
    return node("roll", "requestRoll", **{"expression": "1d20+2", "label": "Inspect the chest",
        "visibility": "public", "audience": audience(), **values})


class InteractionContractTests(SimpleTestCase):
    def test_rolls_and_quest_statuses_evaluate_without_drawing_dice(self):
        actions = [roll_prompt(), node("quest", "setQuestStatus", journalId=str(uuid.uuid4()), status="active")]
        raw = chain(*actions)
        before = deepcopy(raw)
        with patch("gravewright.dice.engine.evaluate", side_effect=AssertionError("Prompts do not roll")):
            self.assertEqual(evaluate_graph(raw, "interact", "closed")["actions"], actions)
        self.assertEqual(raw, before)

    def test_roll_shape_grammar_bounds_and_quest_status_are_validated(self):
        invalid = [roll_prompt(**values) for values in (
            {"expression": ""}, {"expression": "a" * 513}, {"expression": "100d6"},
            {"expression": "eval(1)"}, {"expression": "1d20+"}, {"expression": True},
            {"label": "a" * 49}, {"label": "\0"}, {"visibility": "private"}, {"visibility": False})]
        invalid += [node("quest", "setQuestStatus", journalId=str(uuid.uuid4()), status=value)
                    for value in ("done", "", False, [])]
        invalid += [node("quest", "setQuestStatus", journalId="bad", status="active")]
        for action in invalid:
            with self.subTest(action=action), self.assertRaises(services.MapError):
                clean_blueprint(chain(action))
        for status in ("draft", "available", "active", "completed", "failed", "archived"):
            clean_blueprint(chain(node("quest", "setQuestStatus", journalId=str(uuid.uuid4()), status=status)))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BlueprintInteractionTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    due = delay_fixtures.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.quest = Journal.objects.create(campaign=self.campaign, creator=self.gm, title="Find the map",
                                            type="quest", data={"status": "available"})
        self.second = User.objects.create_user("blueprint-second@example.test", "password-12345", name="Second player")
        Membership.objects.create(campaign=self.campaign, user=self.second, role="player")

    def present(self, action, *, request_id=None):
        self.doc["doors"][0]["blueprint"] = chain(action)
        self.generated()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player, request_id=request_id)
        return [call.args[1] for call in send.call_args_list if call.args[1]["type"] == "room.automation_presentation"]

    def test_roll_prompt_targets_all_players_without_rolling_or_including_streamers(self):
        with patch("gravewright.dice.engine.evaluate", side_effect=AssertionError("Prompts do not roll")):
            events = self.present(roll_prompt(audience=audience("players")))
        self.assertEqual(len(events), 1)
        self.assertEqual(set(events[0]["recipients"]), {str(self.player.pk), str(self.second.pk)})
        self.assertEqual({key: events[0]["payload"][key] for key in ("type", "expression", "label", "visibility")},
                         {"type": "roll", "expression": "1d20+2", "label": "Inspect the chest", "visibility": "public"})
        self.assertEqual(events[0]["payload"]["sceneId"], str(self.scene.pk))
        uuid.UUID(events[0]["payload"]["id"])

    def test_roll_prompt_targets_one_player_and_retry_does_not_prompt_again(self):
        request_id = uuid.uuid4()
        events = self.present(roll_prompt(audience=audience("users", userIds=[str(self.second.pk)]), visibility="gm"),
                              request_id=request_id)
        self.assertEqual(events[0]["recipients"], [str(self.second.pk)])
        self.assertEqual(events[0]["payload"]["visibility"], "gm")
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player, request_id=request_id)
        self.assertFalse(any(call.args[1]["type"] == "room.automation_presentation" for call in send.call_args_list))
        from gravewright.maps.blueprint_world import presentation_for
        self.assertIsNone(presentation_for(self.campaign.pk, self.streamer.pk, events[0]["payload"]))
        self.scene.visibility = "gm"
        self.scene.save(update_fields=["visibility"])
        self.assertIsNone(presentation_for(self.campaign.pk, self.second.pk, events[0]["payload"]))

    def test_player_can_trigger_only_the_authored_quest_change_without_receiving_edit_access(self):
        self.doc["doors"][0]["blueprint"] = chain(node("quest", "setQuestStatus", journalId=str(self.quest.pk), status="active"))
        self.generated()
        request_id = uuid.uuid4()
        with self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player, request_id=request_id)
        self.quest.refresh_from_db()
        self.assertEqual((self.quest.data["status"], self.quest.version), ("active", 2))
        self.assertFalse(Access.objects.filter(journal=self.quest, user=self.player).exists())
        self.assertEqual(JournalReceipt.objects.filter(campaign=self.campaign).count(), 1)
        self.command("closed", user=self.player, request_id=request_id)
        self.command("closed", user=self.player)
        self.quest.refresh_from_db()
        self.assertEqual(self.quest.version, 2)
        self.assertEqual(JournalReceipt.objects.filter(campaign=self.campaign).count(), 1)
        step = AutomationRun.objects.filter(scene=self.scene).latest("created_at").data["events"][0]["steps"][-1]
        self.assertEqual((step["journalId"], step["status"], step["changed"]), (str(self.quest.pk), "active", False))

    def test_foreign_or_nonquest_bindings_cannot_be_saved_or_executed(self):
        foreign = Journal.objects.create(campaign=self.other, creator=self.gm, title="Foreign quest", type="quest")
        diary = Journal.objects.create(campaign=self.campaign, creator=self.gm, title="Diary")
        self.doc["doors"][0]["blueprint"] = chain()
        self.generated()
        for journal in (foreign, diary):
            raw = chain(node("quest", "setQuestStatus", journalId=str(journal.pk), status="active"))
            with self.subTest(journal=journal.pk), self.assertRaisesMessage(services.MapError, "quest from this campaign"):
                clean_native_blueprint(raw, self.campaign.pk, self.scene.pk)
            from gravewright.maps.blueprint_world import set_quest_status
            with self.assertRaisesMessage(services.MapError, "quest from this campaign"):
                set_quest_status(self.scene, self.membership, raw["graphs"]["interact"]["nodes"][-1])

    def test_later_failure_rolls_back_status_receipt_and_notifications(self):
        self.doc["doors"][0]["blueprint"] = chain(
            node("quest", "setQuestStatus", journalId=str(self.quest.pk), status="completed"),
            roll_prompt(), node("outside", "cameraFocus", focusX=1000, focusY=1000, audience=audience()))
        self.generated()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, "outside the map"):
                self.command("closed", user=self.player)
        self.quest.refresh_from_db()
        self.assertEqual((self.quest.data["status"], self.quest.version), ("available", 1))
        self.assertFalse(JournalReceipt.objects.filter(campaign=self.campaign).exists())
        self.assertFalse(any(call.args[1]["type"] in ("room.automation_presentation", "room.journals")
                             for call in send.call_args_list))

    def test_rehearsal_reports_quest_prediction_and_discards_status_and_prompt(self):
        self.doc["doors"][0]["blueprint"] = chain(
            node("quest", "setQuestStatus", journalId=str(self.quest.pk), status="completed"), roll_prompt())
        self.generated()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, self.door_object.pk,
                {"request_id": str(uuid.uuid4()), "event": "interact", "expected_version": self.door_object.version})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["changes"]["journals"], [{"id": str(self.quest.pk),
            "before": {"title": self.quest.title, "status": "available", "version": 1},
            "after": {"title": self.quest.title, "status": "completed", "version": 2}}])
        self.assertIn("presentation-not-delivered", result["warnings"])
        self.quest.refresh_from_db()
        self.assertEqual((self.quest.data["status"], self.quest.version), ("available", 1))
        self.assertFalse(JournalReceipt.objects.filter(campaign=self.campaign).exists())
        send.assert_not_called()

    def test_delayed_quest_change_cancels_when_target_disappears(self):
        self.doc["doors"][0]["blueprint"] = chain(node("wait", "delay", seconds=.1),
            node("quest", "setQuestStatus", journalId=str(self.quest.pk), status="completed"))
        self.generated()
        self.command("closed", user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        self.assertIsNone(invalid_reason(job))
        self.quest.delete()
        self.assertEqual(invalid_reason(job), "A delayed blueprint target is missing.")
        self.assertEqual(self.due(job)["cancelled"], 1)

    def test_archive_remaps_quest_and_roll_audience_but_preserves_authored_label(self):
        self.doc["doors"][0]["blueprint"] = chain(
            node("quest", "setQuestStatus", journalId=str(self.quest.pk), status="completed"),
            roll_prompt(label=str(self.player.pk), audience=audience("users", userIds=[str(self.player.pk)])))
        self.generated()
        for included in (False, True):
            clone = import_campaign(export_campaign(self.campaign, {"journals": included}), self.gm, "Cloned interactions")
            project = MapBuilderProject.objects.get(campaign=clone)
            native = project.scene.elements.get(kind="walls", data__kind="door").data["blueprint"]["graphs"]["interact"]["nodes"]
            copied = project.document["doors"][0]["blueprint"]["graphs"]["interact"]["nodes"]
            self.assertNotEqual(native[1]["journalId"], str(self.quest.pk))
            self.assertEqual(Journal.objects.filter(campaign=clone, pk=native[1]["journalId"], type="quest").exists(), included)
            self.assertEqual(copied[1]["journalId"], native[1]["journalId"])
            self.assertNotEqual(native[2]["audience"]["userIds"], [str(self.player.pk)])
            self.assertEqual(native[2]["label"], str(self.player.pk))
