"""System callbacks cannot grant membership or escape their scene context."""
from copy import deepcopy
from uuid import uuid4

from django.test import TestCase

from api import systems
from gravewright.campaigns import system_api
from gravewright.journals.services import JournalError
from gravewright.maps.services import MapError
from gravewright.table.tests import test_modules as fixtures


class SystemApiTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def provider(self, effect="read", callback=None):
        previous = dict(system_api._providers)
        self.addCleanup(lambda: (system_api._providers.clear(), system_api._providers.update(previous)))
        self.campaign.system = "example.system"
        self.campaign.save(update_fields=["system"])
        callback = callback or (lambda campaign, user, data, request, scene: {"data": data, "sceneId": str(scene) if scene else None})
        with self.assertNumQueries(0):
            systems.register_api("example.system", {"example.operation": {
                "effect": effect, "handler": callback, "description": "Synthetic integration operation."
            }})
        return callback

    def test_registration_is_explicit_and_discovery_contains_no_callbacks(self):
        self.provider()
        result = systems.capabilities(self.campaign.pk, self.player.pk)
        self.assertEqual(result["systemId"], "example.system")
        self.assertEqual(result["operations"], [{"name": "example.operation", "effect": "read",
                                              "description": "Synthetic integration operation."}])
        result["operations"][0]["effect"] = "write"
        self.assertEqual(systems.capabilities(self.campaign.pk, self.player.pk)["operations"][0]["effect"], "read")
        for operation in ({"effect": "admin", "handler": lambda: None}, {"effect": "read", "handler": "__import__"},
                          {"effect": "read", "handler": lambda: None, "extra": True}):
            with self.assertRaises(ValueError):
                systems.register_api("example.system", {"example.operation": operation})

    def test_data_is_copied_and_scene_identity_is_authoritative(self):
        def operation(campaign, user, data, request, scene):
            data["nested"]["value"] = 2
            return {"campaign": str(campaign), "user": str(user), "scene": str(scene)}
        self.provider(callback=operation)
        data = {"nested": {"value": 1}, "mapId": str(self.scene.pk)}
        before = deepcopy(data)
        result = systems.call(self.campaign.pk, self.player.pk, "example.operation", data, scene_id=self.scene.pk)
        self.assertEqual(data, before)
        self.assertEqual(result["scene"], str(self.scene.pk))
        self.assertEqual(result["user"], str(self.player.pk))
        with self.assertRaises(MapError):
            systems.call(self.campaign.pk, self.gm.pk, "example.operation", {"sceneId": str(uuid4())}, scene_id=self.scene.pk)

    def test_operations_never_fall_back_to_another_system_or_removed_member(self):
        self.provider()
        for operation in ("unknown", None):
            with self.assertRaises(MapError):
                systems.call(self.campaign.pk, self.gm.pk, operation, {})
        self.campaign.system = "another.system"
        self.campaign.save(update_fields=["system"])
        self.assertEqual(systems.capabilities(self.campaign.pk, self.gm.pk)["operations"], [])
        with self.assertRaises(MapError):
            systems.call(self.campaign.pk, self.gm.pk, "example.operation", {})
        self.campaign.memberships.filter(user=self.player).delete()
        with self.assertRaises(JournalError):
            systems.capabilities(self.campaign.pk, self.player.pk)

    def test_write_requires_request_uuid_and_streamers_remain_read_only(self):
        self.provider("write")
        with self.assertRaises(JournalError):
            systems.call(self.campaign.pk, self.gm.pk, "example.operation", {})
        request_id = uuid4()
        self.assertEqual(systems.call(self.campaign.pk, self.gm.pk, "example.operation", {}, request_id)["data"], {})
        from gravewright.campaigns.streamer import issue
        from gravewright.campaigns.models import StreamerLink
        issue(self.gm, self.campaign.pk)
        guest = StreamerLink.objects.latest("expires_at").guest
        with self.assertRaises(JournalError):
            systems.call(self.campaign.pk, guest.pk, "example.operation", {}, uuid4())

    def test_payload_size_and_nonfinite_numbers_are_rejected_before_callback(self):
        calls = []
        self.provider(callback=lambda *args: calls.append(args))
        for data in (None, [], {"value": float("nan")}, {"value": "x" * system_api.MAX_PAYLOAD_BYTES}):
            with self.assertRaises(MapError):
                systems.call(self.campaign.pk, self.gm.pk, "example.operation", data)
        self.assertEqual(calls, [])
