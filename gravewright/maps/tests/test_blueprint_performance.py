"""Committed event paths reuse only transaction-local, validated work."""

from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch
import uuid

from django.db import connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.actors.models import Actor
from gravewright.maps import blueprint_runtime, regions, services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import AutomationRun, SceneObject

from . import test_blueprint_action_matrix as fixtures
from . import test_levers as lever_fixtures
from . import test_regions as token_fixtures
from .test_levers import data, execution, node


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class EventPerformanceTests(TestCase):
    asset = fixtures.ActionTargetMatrixTests.asset
    post = fixtures.ActionTargetMatrixTests.post
    save = fixtures.ActionTargetMatrixTests.save
    generate = fixtures.ActionTargetMatrixTests.generate
    files = fixtures.ActionTargetMatrixTests.files
    handler = staticmethod(fixtures.ActionTargetMatrixTests.handler)
    token_command = token_fixtures.RegionTests.token_command
    place = token_fixtures.RegionTests.place
    move = token_fixtures.RegionTests.move

    def setUp(self):
        fixtures.ActionTargetMatrixTests.setUp(self)
        self.actor = Actor.objects.create(campaign=self.campaign, name="Performance visitor", data={},
            permissions={str(self.player.pk): "owner"})

    def graph(self, event, *, following=None):
        actions = [node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk)),
                   node("light", "light", targetId=str(self.light_object.pk), enabled=True),
                   node("state", "state", targetState="on")]
        references = []
        if following is not None:
            actions.append(node("interact", "interact"))
            references = [node("target", "reference", targetId=str(following.pk))]
        values = [node("event", "event", event=event), *actions]
        edges = [execution(a["id"], b["id"]) for a, b in zip(values, values[1:])]
        if following is not None:
            edges.append(data("target", "door", "interact", "target"))
        return {"nodes": [*values, *references], "edges": edges}

    def author(self, row, graphs):
        blueprint = default_blueprint("lever")
        blueprint["graphs"] = graphs
        services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "update",
            "data": {"placement_id": str(row.pk), "blueprint": blueprint}}, uuid.uuid4())
        row.refresh_from_db()

    def sample(self, label, command, verify, *, repetitions=5):
        output = os.environ.get("GRAVEWRIGHT_EVENT_BENCHMARK_OUTPUT")
        repetitions = repetitions if output else 1
        samples, queries = [], []
        for _ in range(repetitions):
            with transaction.atomic():
                try:
                    with CaptureQueriesContext(connection) as captured:
                        start = perf_counter()
                        command()
                        samples.append((perf_counter() - start) * 1000)
                    queries.append([query["sql"] for query in captured.captured_queries])
                    verify()
                finally:
                    transaction.set_rollback(True)
        if output:
            path = Path(output)
            results = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            results[label] = {"repetitions": repetitions, "medianMs": round(median(samples), 3),
                              "queryCounts": [len(rows) for rows in queries], "sql": queries[0]}
            path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        self.assertTrue(all(len(rows) == len(queries[0]) for rows in queries))
        return queries[0]

    def test_committed_eight_object_chain_reuses_validation_inventory(self):
        chain = [self.targets["lever"]]
        for index in range(7):
            values = deepcopy(chain[0].data)
            values.update(name=f"Chain link {index + 2}", x=96 + index * 64, y=400)
            chain.append(SceneObject.objects.create(scene=self.scene, kind="images", data=values))
        for index, row in enumerate(chain):
            following = chain[index + 1] if index + 1 < len(chain) else None
            self.author(row, {"interact": self.graph("interact", following=following)})

        def command():
            services.command(self.campaign.pk, self.gm.pk, "objects", {
                "mapId": str(self.scene.pk), "area": "images", "action": "interact",
                "data": {"image_id": str(chain[0].pk)}}, uuid.uuid4())

        def verify():
            for row in chain:
                row.refresh_from_db()
                self.assertEqual(row.data["lever"]["state"], "on")
                self.assertEqual(row.data["asset_id"], str(self.handle_on.pk))
            self.light_object.refresh_from_db()
            self.assertTrue(self.light_object.data["enabled"])
            run = AutomationRun.objects.filter(scene=self.scene).latest("created_at")
            self.assertEqual(len([event for event in run.data["events"] if event["event"] == "interact"]), 8)

        queries = self.sample("eightObjectChain", command, verify)
        self.assert_inventory_queries(queries)

    def assert_inventory_queries(self, queries):
        reads = Counter(query.split(" FROM ")[1].split(" WHERE ")[0]
                        for query in queries if query.startswith("SELECT ") and " FROM " in query)
        self.assertEqual(reads['"gravewright_maps_mapasset"'], 2,
                         "One ownership inventory and one shared fitted appearance lookup.")
        self.assertEqual(reads['"gravewright_audio_track"'], 1,
                         "Names and owned sound IDs share one inventory.")
        declarations = [query for query in queries if 'AS "data__blueprint"' in query]
        self.assertEqual(len(declarations), 1,
                         "Scene variable declarations load once for the whole command.")

    def test_committed_overlapping_areas_reuse_token_paths(self):
        template = self.targets["lever"]
        listeners = []
        for index in range(16):
            values = deepcopy(template.data)
            values.update(name=f"Area {index + 1}", x=192, y=96)
            values["lever"].update(width=128, height=64)
            listener = SceneObject.objects.create(scene=self.scene, kind="images", data=values)
            self.author(listener, {"presence:enter": self.graph("presence:enter"),
                                   "presence:exit": self.graph("presence:exit")})
            listeners.append(listener)
        token = self.place(x=0, y=1)
        original_version = token.version

        def command():
            token.version = original_version
            self.move(token, 2, user=self.player)

        def verify():
            for row in listeners:
                row.refresh_from_db()
                self.assertEqual(row.data["areaPresence"]["occupants"], [str(token.pk)])
                self.assertEqual(row.data["lever"]["state"], "on")
                self.assertEqual(row.data["asset_id"], str(self.handle_on.pk))
            events = [event for run in AutomationRun.objects.filter(scene=self.scene)
                      for event in run.data["events"] if event["event"] == "presence:enter"]
            self.assertEqual(len(events), 16)

        with patch("gravewright.maps.regions.token_point", wraps=regions.token_point) as point:
            queries = self.sample("sixteenAreaEntry", command, verify, repetitions=3)
        self.assertEqual(point.call_count, 2 * (3 if os.environ.get("GRAVEWRIGHT_EVENT_BENCHMARK_OUTPUT") else 1),
                         "The accepted start/end are projected once, regardless of listeners.")
        self.assert_inventory_queries(queries)

    def interact(self, row):
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "interact",
            "data": {"image_id": str(row.pk)}}, uuid.uuid4())

    def test_next_command_reads_updated_asset_metadata(self):
        owner = self.targets["lever"]
        self.author(owner, {"interact": self.graph("interact")})
        self.interact(owner)
        owner.refresh_from_db()
        self.assertEqual(owner.data["natural_width"], self.handle_on.width)
        lever_fixtures.LeverTests.replace_asset_pixels(self, self.handle_on, (80, 40))
        self.interact(owner)
        owner.refresh_from_db()
        self.assertEqual((owner.data["natural_width"], owner.data["natural_height"]), (80, 40))
        self.assertIsNone(blueprint_runtime._event_resources.get())

    def test_next_command_rechecks_resource_ownership_and_failure_clears_inventory(self):
        owner = self.targets["lever"]
        self.author(owner, {"interact": self.graph("interact")})
        self.interact(owner)
        before = list(self.scene.elements.order_by("pk").values("id", "data", "version"))
        self.handle_on.campaign = self.other
        self.handle_on.save(update_fields=["campaign"])
        with self.assertRaisesMessage(services.MapError, "Blueprint asset not found."):
            self.interact(owner)
        self.assertEqual(list(self.scene.elements.order_by("pk").values("id", "data", "version")), before)
        self.assertIsNone(blueprint_runtime._event_resources.get())
        self.handle_on.campaign = self.campaign
        self.handle_on.save(update_fields=["campaign"])
        self.interact(owner)
        self.assertIsNone(blueprint_runtime._event_resources.get())

    def test_presence_batch_keeps_every_run_but_notifies_the_log_once_after_commit(self):
        listeners = []
        for index in range(2):
            values = deepcopy(self.targets["lever"].data)
            values.update(name=f"Notification area {index + 1}", x=192, y=96)
            values["lever"].update(width=128, height=64)
            row = SceneObject.objects.create(scene=self.scene, kind="images", data=values)
            self.author(row, {"presence:enter": self.graph("presence:enter")})
            listeners.append(row)
        token = self.place(x=0, y=1)
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.move(token, 2, user=self.player)
                self.assertFalse(send.called, "Nothing is pushed before the successful commit.")
            notifications = [call.args[1] for call in send.call_args_list
                             if call.args[1].get("type") == "room.automation"]
        self.assertEqual(notifications, [{"type": "room.automation", "sceneId": str(self.scene.pk)}])
        self.assertEqual(set(AutomationRun.objects.filter(scene=self.scene).values_list("door_id", flat=True)),
                         {row.pk for row in listeners} | {self.targets["region"].pk})
