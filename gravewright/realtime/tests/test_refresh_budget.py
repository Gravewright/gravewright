"""Notification cost budgets: SQL, frames and bytes delivered to one recipient per change.

SQL and frame counts are deterministic and act as ceilings. Byte sizes vary slightly
with timestamps and revisions, so they are recorded as a range. Set
GRAVEWRIGHT_REALTIME_BENCHMARK_OUTPUT to an explicit JSON file under an
installation-local test directory to record 20 repetitions with median and
95th-percentile handler times (observations only).
"""

import json
import os
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter
from unittest.mock import patch
import uuid

from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings

from gravewright.maps.models import SceneObject
from gravewright.realtime import dispatch, metrics
# Import the module, not the class: an imported TestCase would run again here.
from gravewright.realtime.tests import test_scene_update_priority as priority

MODULES = ("items", "combat", "cards", "audio", "compendiums")
SCENARIOS = (("tokens", "move"), ("audio", "play"), ("maps", "objects"), ("actors", "sheet.save"))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"])
class RefreshBudgetTests(TransactionTestCase):
    setUp = priority.SceneUpdatePriorityTests.setUp
    consumer = priority.SceneUpdatePriorityTests.consumer

    def subscribed(self, user):
        # The audit configuration: every resource module and both directories.
        consumer = self.consumer(user)
        consumer.actors_subscribed = consumer.journals_subscribed = True
        consumer.table_modules = {name: str(self.scene.pk) for name in MODULES}
        return consumer

    def events(self, resource, action):
        sent = []
        with patch.object(dispatch, "send", side_effect=lambda _campaign, event: sent.append(event)), \
                patch("gravewright.table.events.resource_changed.send_robust", return_value=[]):
            # Outside a transaction, on_commit callbacks run immediately.
            dispatch.changed(self.campaign.pk, self.gm.pk, resource, action, uuid.uuid4())
        return sent

    async def deliver(self, user, resource, action, warm=False):
        events = await db(self.events)(resource, action)
        consumer = self.subscribed(user)
        if warm:
            # Steady state: this socket already holds the current projections. The
            # measured envelope is a new commit (a newer revision) without data changes.
            for event in events:
                await getattr(consumer, event["type"].replace(".", "_"))(event)
            consumer.emit.reset_mock()
            events = await db(self.events)(resource, action)
        sql = 0
        started = perf_counter()
        for event in events:
            with metrics.handler("delivery") as measured:
                await getattr(consumer, event["type"].replace(".", "_"))(event)
            sql += measured.sql_count
        elapsed = (perf_counter() - started) * 1000
        frames = consumer.emit.await_args_list
        return {
            "events": len(events),
            "sql": sql,
            "frames": len(frames),
            "bytes": sum(len(json.dumps({"type": call.args[0], "payload": call.args[1]}).encode())
                         for call in frames),
            "ms": elapsed,
        }

    async def add_images(self, count):
        await db(SceneObject.objects.bulk_create)([
            SceneObject(scene=self.scene, kind="images",
                        data={"name": f"Synthetic image {index}", "layer": "image-layer"})
            for index in range(count)])

    async def measure_all(self):
        output = os.environ.get("GRAVEWRIGHT_REALTIME_BENCHMARK_OUTPUT")
        repetitions = 20 if output else 1
        results = {}
        for images in (2, 102):
            if images == 102:
                await self.add_images(100)
            for role, user in (("gm", self.gm), ("player", self.player)):
                for resource, action in SCENARIOS:
                    samples = [await self.deliver(user, resource, action) for _ in range(repetitions)]
                    first = samples[0]
                    # Deterministic counts must not vary between repetitions.
                    for sample in samples[1:]:
                        self.assertEqual({k: sample[k] for k in ("events", "sql", "frames")},
                                         {k: first[k] for k in ("events", "sql", "frames")})
                    times = [sample["ms"] for sample in samples]
                    sizes = [sample["bytes"] for sample in samples]
                    results[f"{role}:{resource}/{action}:{images}"] = {
                        **{k: first[k] for k in ("events", "sql", "frames")},
                        "bytesMin": min(sizes), "bytesMax": max(sizes),
                        "medianMs": round(median(times), 3),
                        "p95Ms": round(quantiles(times, n=20)[-1], 3) if len(times) > 1 else round(times[0], 3),
                        "repetitions": repetitions,
                    }
            for role, user in (("gm", self.gm), ("player", self.player)):
                for resource, action in SCENARIOS:
                    warm = await self.deliver(user, resource, action, warm=True)
                    results[f"{role}:{resource}/{action}:{images}:warm"] = {
                        key: warm[key] for key in ("events", "sql", "frames", "bytes")}
        if output:
            Path(output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        return results

    async def test_notification_budgets(self):
        results = await self.measure_all()
        # (SQL, frames) measured on 2026-11-09 before any transport change; the GM
        # values match the realtime audit. Kept to show each ceiling stays below them.
        baseline = {
            "gm:tokens/move": (32, 6), "gm:audio/play": (108, 24),
            "gm:maps/objects": (25, 4), "gm:actors/sheet.save": (55, 12),
            "player:tokens/move": (45, 6), "player:audio/play": (133, 24),
            "player:maps/objects": (35, 4), "player:actors/sheet.save": (74, 12),
        }
        # Ceilings with one envelope per commit and narrowed dependencies.
        ceilings = {
            "gm:tokens/move": (24, 6), "gm:audio/play": (11, 2),
            "gm:maps/objects": (21, 4), "gm:actors/sheet.save": (32, 10),
            "player:tokens/move": (37, 6), "player:audio/play": (13, 2),
            "player:maps/objects": (31, 4), "player:actors/sheet.save": (48, 10),
        }
        for key, (sql, frames) in ceilings.items():
            self.assertLessEqual((sql, frames), baseline[key])
            for images in (2, 102):
                with self.subTest(scenario=key, images=images):
                    row = results[f"{key}:{images}"]
                    self.assertLessEqual(row["sql"], sql)
                    self.assertLessEqual(row["frames"], frames)
        for key, row in results.items():
            if key.endswith(":2:warm"):
                with self.subTest(scenario=key):
                    # Unchanged projections are not sent again (only hints and time-based
                    # audio state remain), so the size no longer depends on the scene.
                    larger = results[key.replace(":2:warm", ":102:warm")]
                    self.assertLessEqual(abs(row["bytes"] - larger["bytes"]), 8)
                    self.assertLess(larger["bytes"], 1024)
        for resource, action in SCENARIOS:
            for role in ("gm", "player"):
                with self.subTest(scenario=f"{role}:{resource}/{action}"):
                    # Query cost depends on subscriptions, not on the scene's size.
                    self.assertEqual(results[f"{role}:{resource}/{action}:2"]["sql"],
                                     results[f"{role}:{resource}/{action}:102"]["sql"])
