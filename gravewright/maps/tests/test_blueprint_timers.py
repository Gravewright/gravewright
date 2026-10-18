"""Named timers run fresh bounded events without suspending their source graph."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import threading
import uuid
from unittest.mock import patch

from django.db import IntegrityError, OperationalError, close_old_connections, connection, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.campaigns.models import Membership
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprint_delays import pending_delays, process_due_delays
from gravewright.maps.blueprints import clean_blueprint, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject, Receipt, SceneObject
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from . import test_blueprint_delays as delay_fixtures
from .test_blueprint_references import blueprint, data, execution, node


EVENT = "interact"
NAME = "DoorTimeout"
SIGNAL = "signal:" + NAME


def timed(action="start", *, seconds=3, name=NAME):
    timer = node("timer", "timer", name=name, action=action)
    if action != "stop":
        timer["seconds"] = seconds
    return blueprint({EVENT: ([timer, node("immediate", "setVariable", scope="element", name="Immediate",
        valueType="boolean", value=True)], [execution("event", "timer"), execution("timer", "immediate")]),
        SIGNAL: ([node("read", "getVariable", scope="scene", name="Stage", valueType="number", default=0),
            node("copy", "setVariable", scope="element", name="Copy", valueType="number", value=0),
            node("open", "state", targetState="open")], [execution("event", "copy"),
            execution("copy", "open"), data("read", "value", "copy", "value")])})


class TimerContractTests(SimpleTestCase):
    def test_actions_duration_names_and_version_are_strict(self):
        for action in ("start", "restart", "stop"):
            raw = timed(action)
            self.assertEqual(clean_blueprint(raw), raw)
        for action in ("", "repeat", True, [], None):
            raw = timed()
            raw["graphs"][EVENT]["nodes"][1]["action"] = action
            with self.subTest(action=action), self.assertRaises(MapError):
                clean_blueprint(raw)
        for value in (.0999, 86400.1, True, "3", float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(seconds=value), self.assertRaises(MapError):
                clean_blueprint(timed(seconds=value))
        for value in (.1, 86400, .1001):
            self.assertEqual(clean_blueprint(timed(seconds=value))["graphs"][EVENT]["nodes"][1]["seconds"], value)
        for value in ("", "Door timeout", "9Door", "á", "A" * 65):
            with self.subTest(name=value), self.assertRaises(MapError):
                clean_blueprint(timed(name=value))
        for action in ("start", "restart"):
            raw = timed(action)
            del raw["graphs"][EVENT]["nodes"][1]["seconds"]
            with self.assertRaises(MapError):
                clean_blueprint(raw)
        raw = timed("stop")
        raw["graphs"][EVENT]["nodes"][1]["seconds"] = 1
        with self.assertRaises(MapError):
            clean_blueprint(raw)
        raw = timed()
        raw["version"] = 1
        with self.assertRaises(MapError):
            clean_blueprint(raw)

    def test_timer_is_an_action_and_next_executes_immediately_without_mutation(self):
        raw = timed()
        before = deepcopy(raw)
        result = evaluate_graph(raw, EVENT, "closed")
        self.assertEqual([action["id"] for action in result["actions"]], ["timer", "immediate"])
        self.assertEqual(result["trace"], ["event", "timer", "immediate"])
        self.assertNotIn("delay", result)
        self.assertEqual(raw, before)

    def test_missing_listener_is_valid_and_stop_has_no_duration(self):
        raw = timed("stop")
        del raw["graphs"][SIGNAL]
        result = evaluate_graph(raw, EVENT, "closed")
        self.assertEqual(result["actions"][0]["action"], "stop")
        self.assertNotIn("seconds", result["actions"][0])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class TimerRuntimeTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene
    edit_source = delay_fixtures.DelayRuntimeTests.edit_source
    cancel = delay_fixtures.DelayRuntimeTests.cancel
    due = delay_fixtures.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = timed()

    def start(self, *, user=None, request_id=None):
        self.generated()
        self.command("closed", user=user, request_id=request_id)
        return AutomationDelay.objects.get(status="pending")

    def restart(self, row, *, user=None, expected=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects", {
            "mapId": str(self.scene.pk), "area": "automation", "action": "restart-timer", "data": {
                "delayId": str(row.pk), "expectedDueAt": expected or row.due_at.isoformat()}}, request_id or uuid.uuid4())

    def test_next_is_immediate_and_expiry_uses_live_variables_without_replaying(self):
        request_id = uuid.uuid4()
        row = self.start(user=self.player, request_id=request_id)
        self.assertEqual(row.kind, "timer")
        self.assertEqual(row.name, NAME)
        self.assertEqual(row.event, SIGNAL)
        self.assertNotIn("continuation", row.data)
        self.door_object.refresh_from_db()
        self.assertTrue(self.door_object.data["automationVariables"]["Immediate"]["value"])
        self.assertNotIn("Copy", self.door_object.data["automationVariables"])
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.scene.settings["automationVariables"] = {"Stage": {"type": "number", "value": 7}}
        self.scene.save(update_fields=["settings"])
        self.assertEqual(process_due_delays(now=row.due_at - timedelta(milliseconds=1))["processed"], 0)
        self.assertEqual(self.due(row)["completed"], 1)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["automationVariables"]["Copy"]["value"], 7)
        self.assertEqual(self.door_object.data["door_state"], "open")
        run = AutomationRun.objects.filter(data__delayId=str(row.pk)).get()
        self.assertEqual(run.data["timerName"], NAME)
        self.assertEqual(run.data["events"][0]["event"], SIGNAL)
        self.assertEqual(self.due(row)["processed"], 0)
        self.assertTrue(Receipt.objects.filter(request_id=row.pk).exists())
        self.command("closed", user=self.player, request_id=request_id)
        self.assertEqual(AutomationDelay.objects.count(), 1)

    def test_start_preserves_deadline_identity_actor_and_budget(self):
        row = self.start(user=self.player)
        original = {key: deepcopy(getattr(row, key)) for key in ("due_at", "user_id", "role", "data", "chain_id")}
        self.command("closed")
        row.refresh_from_db()
        self.assertEqual(AutomationDelay.objects.count(), 1)
        for key, value in original.items():
            self.assertEqual(getattr(row, key), value)

    def test_sequential_start_stop_start_and_emit_observe_timer_action_order(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].extend([node("send", "emitEvent", scope="element", name="StopNow"),
                              node("second", "timer", name="Second", action="start", seconds=1)])
        graph["edges"] = [execution("event", "timer"), execution("timer", "second"), execution("second", "send")]
        raw["graphs"].update(blueprint({"signal:StopNow": (
            [node("stop", "timer", name=NAME, action="stop"), node("again", "timer", name=NAME, action="start", seconds=8)],
            [execution("event", "stop"), execution("stop", "again")])})["graphs"])
        self.generated()
        self.command("closed")
        rows = list(AutomationDelay.objects.order_by("created_at"))
        self.assertEqual(len(rows), 3)
        self.assertEqual([(row.name, row.status, row.seconds) for row in rows],
                         [(NAME, "cancelled", 3), ("Second", "pending", 1), (NAME, "pending", 8)])

    def test_restart_node_replaces_only_its_name_and_uses_current_authority(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("second", "timer", name="Second", action="start", seconds=10))
        graph["edges"].append(execution("timer", "second"))
        graph["nodes"].extend([node("mode", "condition", state="open"),
                               node("restart", "timer", name=NAME, action="restart", seconds=4)])
        graph["edges"].remove(execution("event", "timer"))
        graph["edges"].extend([execution("event", "mode"), execution("mode", "timer", "false"),
                               execution("mode", "restart", "true")])
        self.generated()
        self.command("closed", user=self.player)
        old = AutomationDelay.objects.get(name=NAME)
        other = AutomationDelay.objects.get(name="Second")
        self.door_object.refresh_from_db()
        self.door_object.data["door_state"] = "open"
        self.door_object.save(update_fields=["data"])
        self.command("open")
        replacement = AutomationDelay.objects.get(name=NAME, status="pending")
        old.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(old.status, "cancelled")
        self.assertNotEqual(replacement.pk, old.pk)
        self.assertEqual(replacement.user_id, self.gm.pk)
        self.assertEqual(replacement.seconds, 4)
        self.assertEqual(other.status, "pending")

    def test_gm_restart_is_cas_idempotent_and_preserves_original_player_authority(self):
        row = self.start(user=self.player)
        for user in (self.player, self.streamer):
            with self.assertRaises(Exception):
                self.restart(row, user=user)
        with self.assertRaisesMessage(MapError, "timer changed") as raised:
            self.restart(row, expected="2000-01-01T00:00:00+00:00")
        self.assertEqual(raised.exception.code, "conflict")
        request_id = uuid.uuid4()
        future = row.due_at + timedelta(seconds=5)
        with patch("gravewright.maps.blueprint_delays.timezone.now", return_value=future):
            result = self.restart(row, request_id=request_id)
        self.assertEqual(self.restart(row, request_id=request_id), result)
        replacement = AutomationDelay.objects.get(status="pending")
        self.assertNotEqual(replacement.pk, row.pk)
        self.assertEqual(replacement.due_at, future + timedelta(seconds=row.seconds))
        for key in ("user_id", "role", "chain_id", "request_id", "seconds", "data"):
            self.assertEqual(getattr(replacement, key), getattr(row, key))
        with self.assertRaisesMessage(MapError, "timer changed"):
            self.restart(row)
        Membership.objects.filter(campaign=self.campaign, user=self.player).update(role="gm")
        self.door_object.refresh_from_db()
        self.door_object.data["door_state"] = "locked"
        self.door_object.save(update_fields=["data"])
        self.assertEqual(self.due(replacement)["failed"], 1)
        self.door_object.refresh_from_db()
        self.assertNotIn("Copy", self.door_object.data["automationVariables"])

    def test_gm_cancel_never_fires_and_missing_listener_completes_without_effects(self):
        row = self.start()
        self.cancel(row)
        self.assertEqual(self.due(row)["processed"], 0)
        self.door_object.refresh_from_db()
        self.assertNotIn("Copy", self.door_object.data["automationVariables"])
        changed = deepcopy(self.door_object.data["blueprint"])
        del changed["graphs"][SIGNAL]
        self.command("closed", action="update", blueprint=changed, version=self.door_object.version)
        self.command("closed")
        replacement = AutomationDelay.objects.get(status="pending")
        self.assertEqual(self.due(replacement)["completed"], 1)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")

    def test_pause_defers_expiry_and_reads_do_not_claim_or_leak_jobs(self):
        row = self.start(user=self.player)
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.assertEqual(self.due(row)["processed"], 0)
        self.client.force_login(self.gm)
        response = self.client.get(f"/api/maps/{self.scene.pk}/automation")
        self.assertEqual(response.status_code, 200)
        projected = response.json()["delays"][0]
        self.assertEqual(projected["kind"], "timer")
        self.assertEqual(projected["name"], NAME)
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/api/maps/{self.scene.pk}/automation").status_code, 404)
            public = json.dumps(objects.layer_state(self.scene, Membership.objects.get(campaign=self.campaign, user=user)))
            self.assertNotIn(str(row.pk), public)
            self.assertNotIn("DoorTimeout", public)
        self.scene.settings.pop("automationPaused")
        self.scene.save(update_fields=["settings"])
        self.assertEqual(self.due(row)["completed"], 1)

    def test_layout_update_preserves_deadline_and_behavior_edit_cancels(self):
        row = self.start()
        self.edit_source(lambda value: value["graphs"][EVENT]["nodes"][1].update(x=450, y=200))
        self.update_scene()
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.edit_source(lambda value: value["graphs"][EVENT]["nodes"][1].update(seconds=4))
        self.update_scene()
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelled")
        self.assertEqual(self.due(row)["processed"], 0)

    def test_deleted_target_cancels_and_copies_archives_do_not_copy_pending_jobs(self):
        row = self.start()
        self.door_object.refresh_from_db()
        target = SceneObject.objects.create(scene=self.scene, kind="walls", data=self.door_object.data)
        changed = deepcopy(self.door_object.data["blueprint"])
        changed["graphs"][SIGNAL]["nodes"].append(node("target", "reference", targetId=str(target.pk)))
        changed["graphs"][SIGNAL]["edges"].append(data("target", "door", "open", "target"))
        self.command("closed", action="update", blueprint=changed, version=self.door_object.version)
        self.command("closed")
        pending = AutomationDelay.objects.get(status="pending")
        target.delete()
        self.assertEqual(self.due(pending)["cancelled"], 1)
        self.door_object.refresh_from_db()
        result = objects.apply(self.scene, self.membership, "wall-selection", "paste", {"walls": [self.door_object.data]})
        self.assertEqual(len(result["walls"]), 1)
        self.assertEqual(AutomationDelay.objects.count(), 2)
        from gravewright.administration.archives import options, records
        self.assertNotIn("gravewright_maps.automationdelay", {r["model"] for r in records(self.campaign, options())})
        self.door_object.delete()
        self.assertEqual(AutomationDelay.objects.count(), 0)

    def test_inherited_time_and_element_budgets_bound_self_rearming_timers(self):
        raw = self.doc["doors"][0]["blueprint"]
        raw["graphs"][SIGNAL] = blueprint({SIGNAL: (
            [node("again", "timer", name=NAME, action="start", seconds=.1)], [execution("event", "again")])})["graphs"][SIGNAL]
        row = self.start()
        for unused in range(3):
            self.assertEqual(self.due(row)["completed"], 1)
            replacement = AutomationDelay.objects.get(status="pending")
            self.assertEqual(replacement.chain_id, row.chain_id)
            self.assertEqual(replacement.data["budget"]["delays"], row.data["budget"]["delays"] + 1)
            row = replacement
        self.assertEqual(self.due(row)["failed"], 1)
        self.assertFalse(AutomationDelay.objects.filter(status="pending").exists())
        row.refresh_from_db()
        self.assertIn("repeating chain", row.message)

    def test_timer_and_delay_share_capacity_and_failure_rolls_back_prior_effects(self):
        row = self.start()
        clones = []
        fields = ("scene_id", "element_id", "user_id", "chain_id", "request_id", "role", "event",
                  "node_id", "graph_hash", "seconds", "due_at", "data")
        for unused in range(63):
            clones.append(AutomationDelay(**{field: deepcopy(getattr(row, field)) for field in fields}))
        AutomationDelay.objects.bulk_create(clones)
        self.door_object.refresh_from_db()
        changed = deepcopy(self.door_object.data["blueprint"])
        changed["graphs"][EVENT]["nodes"][1]["name"] = "Second"
        # Bypass an authored edit only to retain the full private-capacity fixture.
        self.door_object.data["blueprint"] = changed
        self.door_object.data.pop("automationVariables", None)
        self.door_object.save(update_fields=["data"])
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "Too many pending"):
            self.command("closed", request_id=request_id)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.door_object.refresh_from_db()
        self.assertNotIn("automationVariables", self.door_object.data)
        self.assertEqual(AutomationDelay.objects.filter(status="pending").count(), 64)

    def test_restart_rolls_back_when_a_later_effect_fails(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].extend([node("mode", "condition", state="open"),
            node("replace", "timer", name=NAME, action="restart", seconds=6),
            node("light", "light", targetId=self.light_id, enabled=True)])
        graph["edges"].remove(execution("event", "timer"))
        graph["edges"].extend([execution("event", "mode"), execution("mode", "timer", "false"),
            execution("mode", "replace", "true"), execution("replace", "light")])
        row = self.start()
        self.door_object.refresh_from_db()
        self.door_object.data["door_state"] = "open"
        self.door_object.save(update_fields=["data"])
        with override_settings(DYNAMIC_LIGHTING_ENABLED=False), self.assertRaisesMessage(MapError, "lighting is disabled"):
            self.command("open")
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")
        self.assertEqual(AutomationDelay.objects.count(), 1)

    def test_scene_access_loss_cancels_and_records_the_named_timer(self):
        row = self.start(user=self.player)
        self.scene.visibility = "gm"
        self.scene.save(update_fields=["visibility"])
        self.assertEqual(self.due(row)["cancelled"], 1)
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelled")
        run = AutomationRun.objects.get(data__delayId=str(row.pk))
        self.assertEqual(run.data["timerName"], NAME)

    def test_time_resumption_limit_applies_even_before_the_normal_event_limit(self):
        row = self.start()
        row.data["budget"]["delays"] = 32
        row.save(update_fields=["data"])
        self.assertEqual(self.due(row)["failed"], 1)
        row.refresh_from_db()
        self.assertIn("continuation limit", row.message)
        self.door_object.refresh_from_db()
        self.assertNotIn("Copy", self.door_object.data["automationVariables"])

    def test_database_enforces_one_pending_name_per_element(self):
        row = self.start()
        fields = ("scene_id", "element_id", "user_id", "chain_id", "request_id", "role", "kind", "name", "event",
                  "node_id", "graph_hash", "seconds", "due_at", "data")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AutomationDelay.objects.create(**{field: deepcopy(getattr(row, field)) for field in fields})

    def test_timer_names_are_authored_text_during_archive_reference_rewriting(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        authored = "Timer." + str(self.alternate.pk)
        self.doc["doors"][0]["blueprint"] = timed(name=authored)
        self.start()
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Imported timers")
        source = MapBuilderProject.objects.get(campaign=restored)
        self.assertEqual(source.document["doors"][0]["blueprint"]["graphs"][EVENT]["nodes"][1]["name"], authored)
        native = SceneObject.objects.get(scene=source.scene, kind="walls", data__kind="door")
        self.assertEqual(native.data["blueprint"]["graphs"][EVENT]["nodes"][1]["name"], authored)
        self.assertFalse(AutomationDelay.objects.filter(scene__campaign=restored).exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TimerConcurrencyTests(TransactionTestCase):
    def test_racing_workers_commit_one_fresh_timer_event(self):
        if connection.vendor != "sqlite":
            self.skipTest("SQLite contention scenario; other engines serialize at the campaign lock.")
        from gravewright.accounts.models import User
        from gravewright.campaigns.models import Campaign
        from gravewright.maps.models import Scene

        gm = User.objects.create_user("timer-concurrency@example.test", "synthetic-password", name="GM")
        campaign = Campaign.objects.create(owner=gm, name="Timer workers")
        Membership.objects.create(campaign=campaign, user=gm, role="gm")
        scene = Scene.objects.create(campaign=campaign, name="Concurrent", width=100, height=100)
        raw = timed(seconds=.1)
        raw["graphs"][SIGNAL] = blueprint({SIGNAL: (
            [node("count", "counter", target=2)], [execution("event", "count")])})["graphs"][SIGNAL]
        obj = SceneObject.objects.create(scene=scene, kind="walls", data={"kind": "door", "door_state": "closed",
            "x1": 0, "y1": 0, "x2": 64, "y2": 0, "blueprint": raw})
        services.command(campaign.pk, gm.pk, "objects", {"mapId": str(scene.pk), "area": "walls", "action": "door",
            "data": {"wall_id": str(obj.pk), "door_state": "closed"}}, uuid.uuid4())
        job = AutomationDelay.objects.get(status="pending")
        barrier = threading.Barrier(2)

        def run():
            close_old_connections()
            try:
                barrier.wait(timeout=3)
                try:
                    return process_due_delays(now=job.due_at + timedelta(seconds=1))
                except OperationalError as error:
                    if "locked" not in str(error):
                        raise
                    return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda unused: run(), range(2)))
        self.assertTrue(any(result is not None for result in results))
        process_due_delays(now=job.due_at + timedelta(seconds=1))
        obj.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(obj.data["automationMemory"][SIGNAL]["count"]["value"], 1)
        self.assertEqual(Receipt.objects.filter(request_id=job.pk).count(), 1)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TimerMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_and_resumes_an_existing_delay_checkpoint(self):
        from django.db.migrations.executor import MigrationExecutor
        from gravewright.accounts.models import User
        from gravewright.campaigns.models import Campaign
        from gravewright.maps.blueprint_delays import semantic_hash
        from gravewright.maps.models import Scene

        previous = ("gravewright_maps", "0011_automationdelay")
        current = ("gravewright_maps", "0012_automationdelay_timer")
        executor = MigrationExecutor(connection)
        latest = [target for target in executor.loader.graph.leaf_nodes() if target[0] == "gravewright_maps"]
        executor.migrate([previous])
        try:
            old_model = executor.loader.project_state([previous]).apps.get_model("gravewright_maps", "AutomationDelay")
            gm = User.objects.create_user("timer-migration@example.test", "synthetic-password", name="GM")
            campaign = Campaign.objects.create(owner=gm, name="Timer migration")
            Membership.objects.create(campaign=campaign, user=gm, role="gm")
            scene = Scene.objects.create(campaign=campaign, name="Existing wait", width=100, height=100)
            raw = delay_fixtures.waiting()
            historical_data = objects.wall({"x1": 0, "y1": 0, "x2": 100, "y2": 0, "kind": "door"})
            historical_data["blueprint"] = raw
            obj = SceneObject.objects.create(scene=scene, kind="walls", data=historical_data)
            first = evaluate_graph(raw, EVENT, "closed")
            job = old_model.objects.create(scene_id=scene.pk, element_id=obj.pk, user_id=gm.pk, role="gm",
                chain_id=uuid.uuid4(), request_id=uuid.uuid4(), event=EVENT, node_id="wait", seconds=3,
                graph_hash=semantic_hash(raw), due_at=timezone.now() - timedelta(seconds=1), data={
                    "continuation": first["delay"]["continuation"],
                    "budget": {"operations": 1, "actions": 1, "delays": 0, "perElement": {str(obj.pk): 1}}})
            before = old_model.objects.values().get(pk=job.pk)
            executor = MigrationExecutor(connection)
            executor.migrate([current])
            upgraded = AutomationDelay.objects.get(pk=job.pk)
            self.assertEqual(upgraded.kind, "delay")
            self.assertEqual(upgraded.name, "")
            after = AutomationDelay.objects.values().get(pk=job.pk)
            self.assertEqual({key: after[key] for key in before}, before)
            # Resume with the current host only after all of its schema exists.
            # The intermediate 0012 assertions above still verify that upgrade.
            MigrationExecutor(connection).migrate(latest)
            self.assertEqual(process_due_delays()["completed"], 1)
            obj.refresh_from_db()
            self.assertEqual(obj.data["automationVariables"]["After"]["value"], 2)
        finally:
            MigrationExecutor(connection).migrate(latest)
