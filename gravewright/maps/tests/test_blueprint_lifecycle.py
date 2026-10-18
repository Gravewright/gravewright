"""Explicit destruction is transactional gameplay, not an ORM deletion signal."""

from copy import deepcopy
from datetime import timedelta
import uuid
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.journals.services import JournalError
from gravewright.maps import blueprint_testing, builder_services, services
from gravewright.maps.blueprint_delays import process_due_delays
from gravewright.maps.blueprints import clean_blueprint, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject, Receipt, SceneObject
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from . import test_levers as lever_fixtures
from . import test_regions as region_fixtures
from . import test_torches as torch_fixtures
from . import test_blueprint_testing as testing_fixtures
from .test_blueprint_events import EventFixture, definition, graph, set_value
from .test_levers import data, execution, node


def destruction(light_id, kind="door"):
    return definition(kind, destroy=graph("destroy", node("lamp", "light", targetId=light_id, enabled=True),
        node("flag", "setVariable", scope="scene", name="Destroyed", valueType="boolean", value=True)))


def delete(owner, fixture, *, version=None, request_id=None, user=None):
    key = {"walls": "wall_id", "images": "placement_id", "zones": "zone_id"}[owner.kind]
    return services.command(fixture.campaign.pk, (user or fixture.gm).pk, "objects", {
        "mapId": str(fixture.scene.pk), "area": owner.kind, "action": "delete",
        "data": {key: str(owner.pk), "expected_version": owner.version if version is None else version}},
        request_id or uuid.uuid4())


class LifecycleContractTests(SimpleTestCase):
    def test_destroy_supports_all_intelligent_kinds_and_normalizes_historical_door_containers(self):
        for kind, state in (("door", "closed"), ("lever", "off"), ("torch", "off"), ("region", "empty")):
            raw = definition(kind, destroy=graph("destroy", set_value("Done")))
            self.assertEqual(clean_blueprint(raw), raw)
            self.assertEqual(evaluate_graph(raw, "destroy", state)["actions"][0]["id"], "Done")
        raw = definition(destroy=graph("destroy"))
        raw["version"] = 1
        self.assertEqual(clean_blueprint(raw), definition(destroy=graph("destroy")))
        for event in ("create", "onDestroy", "onAreaEnter", "onAreaExited"):
            with self.subTest(event=event), self.assertRaises(MapError):
                clean_blueprint(definition("region", **{event: graph(event)}))
        raw = definition("region", **{"presence:enter": graph("presence:enter"), "presence:exit": graph("presence:exit")})
        self.assertEqual(clean_blueprint(raw), raw)

    def test_destroy_memory_and_template_parameters_use_the_normal_cleaner(self):
        from gravewright.maps import blueprint_templates as templates
        raw = definition(destroy={"nodes": [node("event", "event", event="destroy"), node("once", "once"),
            node("wait", "delay", seconds=1)], "edges": [execution("event", "once"), execution("once", "wait", "true")]})
        first = evaluate_graph(raw, "destroy", "closed")
        second = evaluate_graph(raw, "destroy", "closed", memory=first["memory"])
        self.assertNotIn("delay", second)
        saved = {"version": 1, "blueprint": raw, "bindings": [], "parameters": []}
        self.assertEqual(templates.clean_definition(saved), saved)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class DestructionTests(EventFixture, TestCase):
    snapshot = testing_fixtures.BlueprintTestingTests.snapshot

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = destruction(self.light_id)

    def test_explicit_delete_runs_before_removal_and_receipt_retry_never_replays(self):
        self.generated()
        owner_id, rid = self.door_object.pk, uuid.uuid4()
        first = delete(self.door_object, self, request_id=rid)
        self.assertEqual(delete(self.door_object, self, request_id=rid), first)
        self.assertFalse(SceneObject.objects.filter(pk=owner_id).exists())
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(self.light_object.version, 2)
        self.scene.refresh_from_db()
        self.assertTrue(self.scene.settings["automationVariables"]["Destroyed"]["value"])
        runs = AutomationRun.objects.filter(scene=self.scene)
        self.assertEqual(runs.count(), 1)
        self.assertEqual(runs.get().door_id, owner_id)
        self.assertEqual(runs.get().data["events"][0]["event"], "destroy")

    def test_permission_and_stale_revision_fail_before_any_hook_or_receipt(self):
        self.generated()
        before = self.snapshot()
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises((MapError, JournalError)):
                delete(self.door_object, self, user=user)
        for version in (self.door_object.version + 1, True):
            with self.subTest(version=version), self.assertRaises(MapError) as error:
                delete(self.door_object, self, version=version)
            self.assertEqual(error.exception.code, "conflict")
        self.assertEqual(self.snapshot(), before)

    def test_pause_removes_natively_without_executing_hook(self):
        self.generated()
        self.scene.settings = {**self.scene.settings, "automationPaused": True}
        self.scene.save(update_fields=["settings"])
        delete(self.door_object, self)
        self.assertFalse(SceneObject.objects.filter(pk=self.door_object.pk).exists())
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_configuration_generation_and_source_update_do_not_destroy(self):
        self.generated()
        self.command("closed", action="update", version=self.door_object.version)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.update_scene()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        builder_services.detail(self.campaign.pk, self.gm.pk, source.pk)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.assertTrue(SceneObject.objects.filter(pk=self.door_object.pk).exists())
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_asset_cleanup_and_direct_orm_removal_do_not_execute_gameplay_hooks(self):
        self.generated()
        response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.door.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.scene.elements.filter(kind="walls").delete()
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_source_update_removes_an_owned_door_without_executing_destroy(self):
        self.generated()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        changed = deepcopy(source.document)
        changed["doors"] = []
        builder_services.save(self.campaign.pk, self.gm.pk, source.pk, {
            "request_id": str(uuid.uuid4()), "expected_version": source.version,
            "folder_id": str(self.folder.pk), "document": changed})
        self.update_scene()
        self.assertFalse(self.scene.elements.filter(pk=self.door_object.pk).exists())
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_bulk_hooks_run_before_any_owner_is_removed_and_duplicates_execute_once(self):
        self.generated()
        target = SceneObject.objects.create(scene=self.scene, kind="walls", data=deepcopy(self.door_object.data))
        self.door_object.data["blueprint"] = definition(destroy={"nodes": [node("event", "event", event="destroy"),
            node("target", "reference", targetId=str(target.pk)), node("state", "state", targetState="open")],
            "edges": [execution("event", "state"), data("target", "door", "state", "target")]})
        self.door_object.save(update_fields=["data"])
        target.data["blueprint"] = definition(destroy={"nodes": [node("event", "event", event="destroy"),
            node("check", "condition", state="open"), node("flag", "setVariable", scope="scene", name="SawTarget",
                valueType="boolean", value=True)],
            "edges": [execution("event", "check"), execution("check", "flag", "true")]})
        target.save(update_fields=["data"])
        ids = [str(target.pk), str(self.door_object.pk), str(target.pk)]
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "wall-selection", "action": "delete", "data": {"wall_ids": ids}}, uuid.uuid4())
        self.assertFalse(self.scene.elements.filter(pk__in=ids).exists())
        self.scene.refresh_from_db()
        self.assertTrue(self.scene.settings["automationVariables"]["SawTarget"]["value"])
        events = [event for run in AutomationRun.objects.filter(scene=self.scene) for event in run.data["events"]]
        self.assertEqual(sum(event["event"] == "destroy" for event in events), 2)

    def test_late_failing_bulk_hook_rolls_back_all_earlier_effects_and_deletions(self):
        self.generated()
        bad = SceneObject.objects.create(scene=self.scene, kind="walls", data=deepcopy(self.door_object.data))
        bad.data["blueprint"] = definition(destroy=graph("destroy", node("emit", "emitEvent", scope="element", name="Loop")),
            **{"signal:Loop": graph("signal:Loop", node("again", "emitEvent", scope="element", name="Loop"))})
        bad.save(update_fields=["data"])
        rid = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "repeating chain"):
            services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
                "area": "wall-selection", "action": "delete", "data": {
                    "wall_ids": [str(self.door_object.pk), str(bad.pk)]}}, rid)
        self.assertEqual(self.scene.elements.filter(pk__in=[bad.pk, self.door_object.pk]).count(), 2)
        self.scene.refresh_from_db()
        self.assertNotIn("Destroyed", self.scene.settings.get("automationVariables", {}))
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())
        failed = AutomationRun.objects.get(scene=self.scene)
        self.assertEqual((failed.outcome, failed.door_id), ("failed", bad.pk))

    def test_clear_commands_execute_destroy_handlers_and_enforce_active_limit_before_effects(self):
        self.generated()
        originals = [str(row.pk) for row in self.scene.elements.filter(kind="walls")]
        for area in ("walls", "wall-selection"):
            owner = SceneObject.objects.create(scene=self.scene, kind="walls", data=deepcopy(self.door_object.data))
            services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
                "area": area, "action": "clear", "data": {}}, uuid.uuid4())
            self.assertFalse(self.scene.elements.filter(pk=owner.pk).exists())
        self.assertFalse(self.scene.elements.filter(pk__in=originals).exists())
        SceneObject.objects.bulk_create([SceneObject(scene=self.scene, kind="walls", data=deepcopy(self.door_object.data))
                                        for _ in range(33)])
        count = AutomationRun.objects.filter(scene=self.scene).count()
        with self.assertRaisesMessage(MapError, "at most 32"):
            services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
                "area": "walls", "action": "clear", "data": {}}, uuid.uuid4())
        self.assertEqual(self.scene.elements.filter(kind="walls").count(), 33)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)

    def test_destroy_cancels_owned_timer_and_delay_and_preserves_diagnostic_history(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact", node("existing", "timer", name="Existing", action="start", seconds=2)),
            "destroy": graph("destroy", node("new", "timer", name="New", action="start", seconds=2),
                             node("wait", "delay", seconds=1), set_value("Never"))}
        self.generated()
        self.command("closed")
        self.assertEqual(AutomationDelay.objects.filter(scene=self.scene, status="pending").count(), 1)
        due = AutomationDelay.objects.get(scene=self.scene).due_at + timedelta(seconds=5)
        delete(self.door_object, self)
        self.assertFalse(AutomationDelay.objects.filter(scene=self.scene).exists())
        self.assertEqual(process_due_delays(now=due)["processed"], 0)
        cancelled = AutomationRun.objects.filter(scene=self.scene, outcome="cancelled")
        self.assertEqual(cancelled.count(), 3)
        self.assertEqual({row.data["message"] for row in cancelled}, {"The owning element was destroyed."})

    def test_rehearsal_removes_owner_under_rollback_with_timing_warning_and_no_delivery(self):
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact",
            node("existing", "timer", name="Existing", action="start", seconds=2))
        self.doc["doors"][0]["blueprint"]["graphs"]["destroy"] = graph("destroy",
            node("lamp", "light", targetId=self.light_id, enabled=True),
            node("wait", "delay", seconds=1), set_value("Never"))
        self.generated()
        self.command("closed")
        self.door_object.refresh_from_db()
        before = self.snapshot()
        payload = {"request_id": str(uuid.uuid4()), "event": "destroy", "expected_version": self.door_object.version}
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, self.door_object.pk, payload)
        self.assertTrue(result["ok"], result)
        removed = next(row for row in result["changes"]["elements"] if row["id"] == str(self.door_object.pk))
        self.assertIsNone(removed["after"])
        self.assertIsNotNone(removed["before"])
        self.assertIn("destruction-timing-cancelled", result["warnings"])
        self.assertEqual(len(result["scheduled"]), 1)
        self.assertIsNone(result["scheduled"][0]["after"])
        send.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_draft_rehearsal_maps_the_removed_source_owner_and_leaves_no_ephemeral_scene(self):
        before = self.snapshot()
        result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, {
            "request_id": str(uuid.uuid4()), "document": deepcopy(self.doc), "elementId": self.doc["doors"][0]["id"],
            "event": "destroy"})
        self.assertTrue(result["ok"], result)
        removed = [row for row in result["changes"]["elements"] if row["after"] is None]
        self.assertEqual([row["sourceId"] for row in removed], [self.doc["doors"][0]["id"]])
        self.assertEqual(self.snapshot(), before)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class MechanismDestructionTests(EventFixture, TestCase):
    lever = lever_fixtures.LeverTests.lever

    def setUp(self):
        lever_fixtures.LeverTests.setUp(self)
        self.doc["decorations"][0]["blueprint"] = destruction(self.light_id, "lever")

    def test_image_delete_and_clear_execute_owner_hook_and_retry_has_no_extra_effect(self):
        self.generated()
        owner = self.lever()
        rid = uuid.uuid4()
        result = delete(owner, self, request_id=rid)
        self.assertEqual(delete(owner, self, request_id=rid), result)
        self.assertFalse(self.scene.elements.filter(pk=owner.pk).exists())
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        copy = SceneObject.objects.create(scene=self.scene, kind="images", data=deepcopy(owner.data))
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "images", "action": "clear", "data": {}}, uuid.uuid4())
        self.assertFalse(self.scene.elements.filter(pk=copy.pk).exists())
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 2)

    def test_normal_image_cleanup_does_not_add_a_database_read_for_each_image(self):
        from gravewright.maps.blueprint_lifecycle import destroy_objects
        self.generated()
        appearance = deepcopy(self.lever().data)
        appearance.pop("lever")
        appearance.pop("blueprint")
        counts = []
        for size in (1, 40):
            rows = SceneObject.objects.bulk_create([SceneObject(scene=self.scene, kind="images", data=deepcopy(appearance))
                                                   for _ in range(size)])
            with CaptureQueriesContext(connection) as queries:
                destroy_objects(self.scene, self.membership, rows)
            counts.append(len(queries))
            self.assertFalse(SceneObject.objects.filter(pk__in=[row.pk for row in rows]).exists())
        self.assertLessEqual(counts[1], counts[0] + 1, counts)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class TorchDestructionTests(EventFixture, TestCase):
    torch = torch_fixtures.TorchTests.torch
    children = torch_fixtures.TorchTests.children
    snapshot = testing_fixtures.BlueprintTestingTests.snapshot

    def setUp(self):
        torch_fixtures.TorchTests.setUp(self)
        self.doc["decorations"][0]["blueprint"] = definition("torch", destroy=graph("destroy",
            node("flag", "setVariable", scope="scene", name="TorchGone", valueType="boolean", value=True)))

    def test_torch_owner_hook_runs_once_and_components_are_removed_without_extra_hooks(self):
        self.generated()
        owner = self.torch()
        ids = [owner.pk, *(row.pk for row in self.children(owner).values())]
        delete(owner, self)
        self.assertFalse(self.scene.elements.filter(pk__in=ids).exists())
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)

    def test_torch_destruction_rehearsal_reports_every_component_removed_without_touching_storage(self):
        self.generated()
        owner = self.torch()
        ids = {str(owner.pk), *(str(row.pk) for row in self.children(owner).values())}
        before, files = self.snapshot(), self.files()
        result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, owner.pk,
            {"request_id": str(uuid.uuid4()), "event": "destroy", "expected_version": owner.version})
        self.assertTrue(result["ok"], result)
        self.assertEqual({row["id"] for row in result["changes"]["elements"] if row["after"] is None}, ids)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.files(), files)

    def test_asset_cleanup_removes_the_entire_group_without_destroy_gameplay(self):
        self.generated()
        owner = self.torch()
        ids = [owner.pk, *(row.pk for row in self.children(owner).values())]
        response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.art.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(self.scene.elements.filter(pk__in=ids).exists())
        self.scene.refresh_from_db()
        self.assertNotIn("TorchGone", self.scene.settings.get("automationVariables", {}))
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class RegionDestructionTests(EventFixture, TestCase):
    region = region_fixtures.RegionTests.region

    def setUp(self):
        region_fixtures.RegionTests.setUp(self)
        self.doc["regions"][0]["blueprint"] = destruction(self.light_id, "region")

    def test_region_delete_checks_revision_and_executes_its_destroy_hook(self):
        self.generated()
        owner = self.region()
        with self.assertRaises(MapError):
            delete(owner, self, version=owner.version + 1)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        delete(owner, self)
        self.assertFalse(self.scene.elements.filter(pk=owner.pk).exists())
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).data["events"][0]["event"], "destroy")
