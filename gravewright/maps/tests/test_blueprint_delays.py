"""Durable waits preserve event order, authority, receipts and transaction safety."""

from copy import deepcopy
from datetime import timedelta
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

from django.db import OperationalError, close_old_connections, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.campaigns.models import Membership
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprint_delays import pending_delays, process_due_delays, semantic_hash
from gravewright.maps.blueprints import clean_blueprint, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject, Receipt, Scene, SceneObject
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from .test_blueprint_references import blueprint, data, execution, node


EVENT = "interact"


def waiting(*, seconds=3):
    return blueprint({EVENT: ([node("before", "setVariable", scope="element", name="Before",
        valueType="number", value=1), node("wait", "delay", seconds=seconds),
        node("after", "setVariable", scope="element", name="After", valueType="number", value=2)],
        [execution("event", "before"), execution("before", "wait"), execution("wait", "after")])})


class DelayContractTests(SimpleTestCase):
    def test_duration_is_bounded_strict_and_v2_only(self):
        for value in (.0999, 86400.1, True, "3", float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(seconds=value), self.assertRaises(MapError):
                clean_blueprint(waiting(seconds=value))
        for value in (.1, 86400, .1001):
            self.assertEqual(clean_blueprint(waiting(seconds=value))["graphs"][EVENT]["nodes"][2]["seconds"], value)
        raw = waiting()
        raw["version"] = 1
        with self.assertRaises(MapError):
            clean_blueprint(raw)

    def test_wait_stops_entire_remaining_event_and_resume_never_replays(self):
        raw = waiting()
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("sibling", "reveal"))
        graph["edges"].append(execution("event", "sibling"))
        initial = evaluate_graph(raw, EVENT, "closed")
        self.assertEqual(initial["trace"], ["event", "before", "wait"])
        self.assertEqual([item["id"] for item in initial["actions"]], ["before"])
        resumed = evaluate_graph(raw, EVENT, "open", continuation=initial["delay"]["continuation"])
        self.assertEqual(resumed["trace"], ["after", "sibling"])
        self.assertNotIn("delay", resumed)

    def test_sequence_reconvergence_and_multiple_waits_share_original_visited_set(self):
        raw = blueprint({EVENT: ([node("seq", "sequence"), node("first", "delay", seconds=1),
            node("second", "delay", seconds=2), node("shared", "reveal")],
            [execution("event", "seq"), execution("seq", "first", "then1"),
             execution("seq", "shared", "then2"), execution("first", "second"),
             execution("second", "shared")])})
        first = evaluate_graph(raw, EVENT, "closed")
        second = evaluate_graph(raw, EVENT, "closed", continuation=first["delay"]["continuation"])
        self.assertEqual(second["trace"], ["second"])
        final = evaluate_graph(raw, EVENT, "closed", continuation=second["delay"]["continuation"])
        self.assertEqual(final["trace"], ["shared"])

    def test_snapshot_variables_and_state_survive_wait_but_gate_memory_is_live(self):
        raw = blueprint({EVENT: ([node("read", "getVariable", scope="scene", name="Stage",
            valueType="number", default=0), node("before", "setVariable", scope="element", name="Copy",
            valueType="number", value=0), node("wait", "delay", seconds=1), node("gate", "counter", target=3),
            node("after", "setVariable", scope="element", name="Copy", valueType="number", value=0)],
            [execution("event", "before"), execution("before", "wait"), execution("wait", "gate"),
             execution("gate", "after", "true"), data("read", "value", "before", "value"),
             data("read", "value", "after", "value")])})
        values = {"scene": {"Stage": {"type": "number", "value": 7}}}
        first = evaluate_graph(raw, EVENT, "closed", variables=values)
        checkpoint = deepcopy(first["delay"]["continuation"])
        values["scene"]["Stage"]["value"] = 99
        second = evaluate_graph(raw, EVENT, "open", variables=values, continuation=checkpoint,
            memory={EVENT: {"gate": {"type": "counter", "value": 2}}})
        self.assertEqual(second["actions"][0]["value"], 7)
        self.assertEqual(second["memory"][EVENT]["gate"]["value"], 3)
        self.assertEqual(checkpoint, first["delay"]["continuation"])
        self.assertNotIn("read", second["trace"])

    def test_unread_values_use_original_event_snapshot_after_wait(self):
        raw = blueprint({EVENT: ([node("wait", "delay", seconds=1), node("check", "condition", state="closed"),
            node("yes", "reveal"), node("no", "state", targetState="open")],
            [execution("event", "wait"), execution("wait", "check"),
             execution("check", "yes", "true"), execution("check", "no", "false")])})
        first = evaluate_graph(raw, EVENT, "closed")
        second = evaluate_graph(raw, EVENT, "open", continuation=first["delay"]["continuation"])
        self.assertEqual([item["id"] for item in second["actions"]], ["yes"])

    def test_malformed_checkpoint_is_rejected_and_empty_wait_still_suspends(self):
        raw = waiting()
        first = evaluate_graph(raw, EVENT, "closed")
        for key, value in (("pending", ["missing"]), ("visited", ["missing"]),
                           ("values", {"wait": True}), ("decisions", {"wait": True}), ("doors", [])):
            broken = deepcopy(first["delay"]["continuation"])
            broken[key] = value
            with self.subTest(key=key), self.assertRaises(MapError):
                evaluate_graph(raw, EVENT, "closed", continuation=broken)
        graph = raw["graphs"][EVENT]
        graph["edges"].pop()
        self.assertEqual(evaluate_graph(raw, EVENT, "closed")["delay"]["continuation"]["pending"], [])

    def test_semantic_hash_ignores_layout_but_tracks_parameters_and_connections(self):
        raw = waiting()
        changed = deepcopy(raw)
        changed["graphs"][EVENT]["nodes"][1].update(x=200, y=800)
        self.assertEqual(semantic_hash(raw), semantic_hash(changed))
        changed["graphs"][EVENT]["nodes"][2]["seconds"] = 4
        self.assertNotEqual(semantic_hash(raw), semantic_hash(changed))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class DelayRuntimeTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = blueprint({EVENT: (
            [node("on", "light", targetId=self.light_id, enabled=True), node("wait", "delay", seconds=3),
             node("off", "light", targetId=self.light_id, enabled=False), node("open", "state", targetState="open")],
            [execution("event", "on"), execution("on", "wait"), execution("wait", "off"), execution("off", "open")])})

    def start(self, user=None, request_id=None):
        self.generated()
        self.command("closed", user=user, request_id=request_id)
        return AutomationDelay.objects.get(status="pending")

    def due(self, row=None):
        row = row or AutomationDelay.objects.get(status="pending")
        return process_due_delays(now=row.due_at + timedelta(seconds=1))

    def cancel(self, row, *, user=None, expected=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects", {
            "mapId": str(self.scene.pk), "area": "automation", "action": "cancel-delay", "data": {
                "delayId": str(row.pk), "expectedDueAt": expected or row.due_at.isoformat()}}, request_id or uuid.uuid4())

    def edit_source(self, change):
        source = MapBuilderProject.objects.get(pk=self.project_id)
        changed = deepcopy(source.document)
        change(changed["doors"][0]["blueprint"])
        return builder_services.save(self.campaign.pk, self.gm.pk, self.project_id, {
            "request_id": str(uuid.uuid4()), "expected_version": source.version,
            "folder_id": str(self.folder.pk), "document": changed})

    def test_due_worker_completes_once_without_any_client_and_uses_request_receipt(self):
        request_id = uuid.uuid4()
        row = self.start(user=self.player, request_id=request_id)
        self.assertEqual(row.request_id, request_id)
        self.assertEqual(process_due_delays(now=row.due_at - timedelta(milliseconds=1))["processed"], 0)
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(self.due(row)["completed"], 1)
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertFalse(self.light_object.data["enabled"])
        version = self.door_object.version
        self.assertEqual(self.due(row)["processed"], 0)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.version, version)
        self.assertTrue(Receipt.objects.filter(request_id=row.pk).exists())

    def test_original_receipt_retry_does_not_enqueue_again(self):
        request_id = uuid.uuid4()
        row = self.start(request_id=request_id)
        self.command("closed", request_id=request_id)
        self.assertEqual(AutomationDelay.objects.filter(status="pending").count(), 1)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.assertEqual(AutomationRun.objects.get().outcome, "waiting")
        self.due(row)
        self.command("closed", request_id=request_id)
        self.assertEqual(AutomationDelay.objects.count(), 1)

    def test_pause_keeps_overdue_checkpoint_then_resume_runs_it(self):
        row = self.start()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.assertEqual(self.due(row)["processed"], 0)
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.scene.settings.pop("automationPaused")
        self.scene.save(update_fields=["settings"])
        self.assertEqual(self.due(row)["completed"], 1)

    def test_cancel_is_gm_only_compare_and_swap_and_receipt_idempotent(self):
        row = self.start()
        for user in (self.player, self.streamer):
            with self.assertRaises(Exception):
                self.cancel(row, user=user)
        with self.assertRaisesMessage(MapError, "delay changed") as raised:
            self.cancel(row, expected="2000-01-01T00:00:00+00:00")
        self.assertEqual(raised.exception.code, "conflict")
        request_id = uuid.uuid4()
        self.assertEqual(self.cancel(row, request_id=request_id), {"delays": []})
        self.assertEqual(self.cancel(row, request_id=request_id), {"delays": []})
        self.assertEqual(self.due(row)["processed"], 0)
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])

    def test_pending_projection_is_gm_only_and_reads_have_no_side_effects(self):
        row = self.start(user=self.player)
        row.due_at = timezone.now() - timedelta(seconds=1)
        row.save(update_fields=["due_at"])
        self.client.force_login(self.gm)
        result = self.client.get(f"/api/maps/{self.scene.pk}/automation")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["delays"], pending_delays(self.scene))
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/api/maps/{self.scene.pk}/automation").status_code, 404)
            public = json.dumps(objects.layer_state(self.scene, Membership.objects.get(campaign=self.campaign, user=user)))
            self.assertNotIn(str(row.pk), public)
            self.assertNotIn("continuation", public)

    def test_locked_root_rolls_back_every_continuation_effect_but_keeps_prior_effects(self):
        row = self.start(user=self.player)
        self.door_object.refresh_from_db()
        self.door_object.data["door_state"] = "locked"
        self.door_object.save(update_fields=["data"])
        self.assertEqual(self.due(row)["failed"], 1)
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        row.refresh_from_db()
        self.assertEqual(row.status, "failed")
        self.assertFalse(Receipt.objects.filter(request_id=row.pk).exists())

    def test_player_promotion_cannot_grant_gm_authority_to_saved_checkpoint(self):
        row = self.start(user=self.player)
        Membership.objects.filter(campaign=self.campaign, user=self.player).update(role="gm")
        self.door_object.refresh_from_db()
        self.door_object.data["door_state"] = "locked"
        self.door_object.save(update_fields=["data"])
        self.assertEqual(self.due(row)["failed"], 1)

    def test_gm_demotion_and_removed_membership_cancel_pending_work(self):
        row = self.start()
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role="player")
        self.assertEqual(self.due(row)["cancelled"], 1)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role="gm")
        self.command("closed", user=self.player)
        row = AutomationDelay.objects.get(status="pending")
        Membership.objects.filter(campaign=self.campaign, user=self.player).delete()
        self.assertEqual(self.due(row)["cancelled"], 1)

    def test_current_scene_access_is_rechecked_but_unviewed_gm_scene_runs(self):
        row = self.start(user=self.player)
        self.scene.visibility = "gm"
        self.scene.save(update_fields=["visibility"])
        self.assertEqual(self.due(row)["cancelled"], 1)
        self.command("closed")
        self.assertEqual(self.due()["completed"], 1)

    def test_linked_layout_edits_keep_wait_and_semantic_edits_cancel_it(self):
        row = self.start()
        self.edit_source(lambda value: value["graphs"][EVENT]["nodes"][2].update(x=400, y=500))
        self.update_scene()
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.edit_source(lambda value: value["graphs"][EVENT]["nodes"][2].update(seconds=4))
        self.update_scene()
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelled")
        self.assertEqual(self.due(row)["processed"], 0)

    def test_native_semantic_edit_cancels_and_deletion_cascades_without_copying_jobs(self):
        row = self.start()
        self.door_object.refresh_from_db()
        changed = deepcopy(self.door_object.data["blueprint"])
        changed["graphs"][EVENT]["nodes"][2]["seconds"] = 7
        self.command("closed", action="update", blueprint=changed, version=self.door_object.version)
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelled")
        self.command("closed")
        self.door_object.refresh_from_db()
        result = objects.apply(self.scene, self.membership, "wall-selection", "paste", {"walls": [self.door_object.data]})
        self.assertEqual(len(result["walls"]), 1)
        self.assertEqual(AutomationDelay.objects.filter(status="pending").count(), 1)
        self.door_object.delete()
        self.assertEqual(AutomationDelay.objects.count(), 0)

    def test_source_update_conflicts_still_protect_unrelated_manual_edits(self):
        self.start()
        self.door_object.refresh_from_db()
        self.door_object.data["x1"] += 5
        self.door_object.save(update_fields=["data"])
        with self.assertRaisesMessage(MapError, "changed"):
            self.update_scene()

    def test_pending_waits_are_not_campaign_archive_content(self):
        self.start()
        from gravewright.administration.archives import options, records
        content = records(self.campaign, options())
        self.assertNotIn("gravewright_maps.automationdelay", {row["model"] for row in content})

    def test_chain_budgets_survive_waits_and_failure_does_not_replay_pre_wait_nodes(self):
        row = self.start()
        row.data["budget"]["actions"] = 1024
        row.save(update_fields=["data"])
        self.assertEqual(self.due(row)["failed"], 1)
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        row.refresh_from_db()
        self.assertIn("too many actions", row.message)

    def test_six_serial_waits_continue_the_same_element_operation(self):
        graph = self.doc["doors"][0]["blueprint"]["graphs"][EVENT]
        graph["edges"][2] = execution("wait", "wait2")
        for index in range(2, 7):
            graph["nodes"].append(node("wait" + str(index), "delay", seconds=.1))
            graph["edges"].append(execution("wait" + str(index), "wait" + str(index + 1) if index < 6 else "off"))
        first = self.start()
        for index in range(6):
            row = AutomationDelay.objects.get(status="pending")
            self.assertEqual(row.data["budget"]["operations"], 1)
            self.assertEqual(row.data["budget"]["perElement"][str(self.door_object.pk)], 1)
            self.assertEqual(self.due(row)["completed"], 1)
        self.assertEqual(AutomationDelay.objects.filter(chain_id=first.chain_id).count(), 6)
        self.assertFalse(AutomationDelay.objects.filter(status="pending").exists())
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_cancelled_runs_explain_gm_and_semantic_cancellation(self):
        row = self.start(user=self.player)
        self.cancel(row)
        run = AutomationRun.objects.filter(scene=self.scene, outcome="cancelled").get()
        self.assertEqual(run.data["delayId"], str(row.pk))
        self.assertEqual(run.data["actor"]["name"], self.player.name)
        self.assertEqual(run.data["message"], "Cancelled by the GM.")
        self.command("closed")
        row = AutomationDelay.objects.get(status="pending")
        self.edit_source(lambda value: value["graphs"].clear())
        self.update_scene()
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene, outcome="cancelled").count(), 2)
        self.assertTrue(AutomationRun.objects.filter(data__delayId=str(row.pk)).exists())

    def test_deleted_required_light_cancels_at_due_without_partial_effects(self):
        row = self.start()
        self.light_object.delete()
        self.assertEqual(self.due(row)["cancelled"], 1)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        row.refresh_from_db()
        self.assertIn("target is missing", row.message)

    def test_deleted_light_used_only_before_wait_cancels_with_a_clear_diagnostic(self):
        self.doc["doors"][0]["blueprint"] = blueprint({EVENT: (
            [node("on", "light", targetId=self.light_id, enabled=True), node("wait", "delay", seconds=3),
             node("after", "setVariable", scope="element", name="After", valueType="boolean", value=True)],
            [execution("event", "on"), execution("on", "wait"), execution("wait", "after")])})
        row = self.start()
        self.light_object.delete()
        self.assertEqual(self.due(row)["cancelled"], 1)
        self.door_object.refresh_from_db()
        self.assertNotIn("After", self.door_object.data.get("automationVariables", {}))
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelled")
        self.assertIn("target is missing", row.message)

    def test_deleted_required_element_cancels_instead_of_silently_skipping_action(self):
        self.generated()
        target = SceneObject.objects.create(scene=self.scene, kind="walls", data=self.door_object.data)
        changed = deepcopy(self.door_object.data["blueprint"])
        graph = changed["graphs"][EVENT]
        graph["nodes"].append(node("ref", "reference", targetId=str(target.pk)))
        graph["edges"].append(data("ref", "door", "open", "target"))
        self.command("closed", action="update", blueprint=changed, version=self.door_object.version)
        self.command("closed")
        row = AutomationDelay.objects.get(status="pending")
        target.delete()
        self.assertEqual(self.due(row)["cancelled"], 1)
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])

    def test_multiple_waits_retain_one_chain_and_finish_in_order(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("second", "delay", seconds=.1))
        graph["edges"][-1] = execution("off", "second")
        graph["edges"].append(execution("second", "open"))
        first = self.start()
        self.assertEqual(self.due(first)["completed"], 1)
        second = AutomationDelay.objects.get(status="pending")
        self.assertEqual(second.chain_id, first.chain_id)
        self.assertEqual(second.request_id, first.request_id)
        self.assertEqual(second.data["budget"]["delays"], 1)
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual(self.due(second)["completed"], 1)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_independent_signal_event_runs_while_original_event_waits(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("send", "emitEvent", scope="element", name="Immediate"))
        graph["edges"][0] = execution("event", "send")
        graph["edges"].append(execution("send", "on"))
        raw["graphs"].update(blueprint({"signal:Immediate": (
            [node("mark", "setVariable", scope="element", name="Independent", valueType="boolean", value=True)],
            [execution("event", "mark")])})["graphs"])
        self.start()
        self.door_object.refresh_from_db()
        self.assertTrue(self.door_object.data["automationVariables"]["Independent"]["value"])
        self.assertEqual(AutomationDelay.objects.filter(status="pending").count(), 1)

    def test_pending_capacity_rolls_back_all_prior_effects_of_rejected_schedule(self):
        row = self.start()
        clones = []
        fields = ("scene_id", "element_id", "user_id", "chain_id", "request_id", "role", "event",
                  "node_id", "graph_hash", "seconds", "due_at", "data")
        for unused in range(63):
            clones.append(AutomationDelay(**{field: deepcopy(getattr(row, field)) for field in fields}))
        AutomationDelay.objects.bulk_create(clones)
        self.light_object.refresh_from_db()
        self.light_object.data["enabled"] = False
        self.light_object.save(update_fields=["data"])
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "Too many pending"):
            self.command("closed", request_id=request_id)
        self.assertEqual(AutomationDelay.objects.filter(status="pending").count(), 64)
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        # The dedicated continuation limit remains enforced independently.
        row.data["budget"]["delays"] = 32
        row.save(update_fields=["data"])
        self.assertEqual(process_due_delays(limit=1, now=row.due_at + timedelta(seconds=1))["failed"], 1)

    def test_campaign_capacity_counts_other_scenes_and_terminal_history_is_bounded(self):
        from gravewright.maps.blueprint_delays import _finish
        row = self.start()
        other = Scene.objects.create(campaign=self.campaign, name="Other", width=100, height=100)
        target = SceneObject.objects.create(scene=other, kind="walls", data=self.door_object.data)
        fields = ("user_id", "chain_id", "request_id", "role", "event", "node_id", "graph_hash", "seconds", "due_at", "data")
        clones = [AutomationDelay(scene=other, element=target,
            **{field: deepcopy(getattr(row, field)) for field in fields}) for unused in range(255)]
        AutomationDelay.objects.bulk_create(clones)
        with self.assertRaisesMessage(MapError, "Too many pending"):
            self.command("closed")
        self.assertEqual(AutomationDelay.objects.filter(status="pending").count(), 256)
        for pending in AutomationDelay.objects.filter(scene=other):
            _finish(pending, "cancelled")
        self.assertEqual(AutomationDelay.objects.filter(scene=other).count(), 50)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DelayConcurrencyTests(TransactionTestCase):
    def test_sqlite_racing_workers_commit_one_continuation(self):
        if connection.vendor != "sqlite":
            self.skipTest("SQLite contention scenario; row-locking engines serialize at the campaign lock.")
        from gravewright.accounts.models import User
        from gravewright.campaigns.models import Campaign
        from gravewright.maps import blueprint_delays

        gm = User.objects.create_user("delay-concurrency@example.test", "synthetic-password", name="GM")
        campaign = Campaign.objects.create(owner=gm, name="Delay workers")
        Membership.objects.create(campaign=campaign, user=gm, role="gm")
        scene = Scene.objects.create(campaign=campaign, name="Concurrent", width=100, height=100)
        raw = blueprint({EVENT: ([node("wait", "delay", seconds=.1), node("count", "counter", target=2)],
            [execution("event", "wait"), execution("wait", "count")])})
        obj = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall({
            "x1": 0, "y1": 0, "x2": 100, "y2": 0, "kind": "door", "blueprint": raw},
            campaign_id=campaign.pk, scene_id=scene.pk))
        services.command(campaign.pk, gm.pk, "objects", {"mapId": str(scene.pk), "area": "walls",
            "action": "door", "data": {"wall_id": str(obj.pk), "door_state": "closed"}}, uuid.uuid4())
        job = AutomationDelay.objects.get(status="pending")
        barrier = threading.Barrier(2)
        def work():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return process_due_delays(now=job.due_at + timedelta(seconds=1))
            except OperationalError as error:
                self.assertIn("locked", str(error).lower())
                return "retry"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda unused: work(), range(2)))
        process_due_delays(now=job.due_at + timedelta(seconds=1))
        obj.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(obj.data["automationMemory"][EVENT]["count"]["value"], 1)
        self.assertEqual(AutomationRun.objects.filter(scene=scene, outcome="completed").count(), 1)
        self.assertEqual(Receipt.objects.filter(request_id=job.pk).count(), 1)
        self.assertTrue(any(isinstance(result, dict) and result["completed"] == 1 for result in results))
