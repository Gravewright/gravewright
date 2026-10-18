"""Base events start a graph whose explicit state and visual actions stay ordered."""

import uuid

from django.test import TestCase, override_settings

from gravewright.maps.models import AutomationRun

from . import test_levers as fixtures
from .test_blueprint_events import EventFixture, definition, graph, toggle
from .test_levers import execution, node


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class StateAppearanceTests(EventFixture, TestCase):
    lever = fixtures.LeverTests.lever
    interact = fixtures.LeverTests.interact

    def setUp(self):
        fixtures.LeverTests.setUp(self)
        self.other_art = self.asset("explicit-off.png", "#8844cc")
        self.doc["assets"].append({"assetId": str(self.other_art.pk), "role": "decoration"})
        blueprint = definition("lever")
        blueprint["graphs"] = {"interact": {
            "nodes": [node("event", "event", event="interact"), node("check", "condition", state="off"),
                node("on", "state", targetState="on"), node("off", "state", targetState="off"),
                node("onArt", "sprite", appearance="asset", assetId=str(self.handle_on.pk)),
                node("offArt", "sprite", appearance="asset", assetId=str(self.other_art.pk))],
            "edges": [execution("event", "check"), execution("check", "on", "true"), execution("on", "onArt"),
                execution("check", "off", "false"), execution("off", "offArt")]}}
        self.doc["decorations"][0]["blueprint"] = blueprint

    def test_one_interaction_graph_chooses_state_and_sprite_without_replaying_a_retry(self):
        self.generated()
        rid = uuid.uuid4()
        first = self.interact(user=self.player, request_id=rid)
        self.assertEqual(self.interact(user=self.player, request_id=rid), first)
        owner = self.lever()
        self.assertEqual(owner.data["lever"]["state"], "on")
        self.assertEqual(owner.data["asset_id"], str(self.handle_on.pk))
        self.assertEqual(owner.data["sprite"], {"appearance": "asset", "assetId": str(self.handle_on.pk)})
        self.interact(user=self.player)
        owner = self.lever()
        self.assertEqual(owner.data["lever"]["state"], "off")
        self.assertEqual(owner.data["asset_id"], str(self.other_art.pk))
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 2)

    def test_state_action_does_not_reset_a_later_explicit_sprite(self):
        event = "interact"
        blueprint = definition("lever", **{event: graph(event, node("state", "state", targetState="on"),
            node("sprite", "sprite", appearance="asset", assetId=str(self.handle_on.pk)))})
        blueprint["states"]["on"] = {"appearance": "asset", "assetId": str(self.other_art.pk)}
        self.doc["decorations"][0]["blueprint"] = blueprint
        self.generated()
        self.interact(user=self.player)
        owner = self.lever()
        self.assertEqual(owner.data["lever"]["state"], "on")
        self.assertEqual(owner.data["sprite"]["assetId"], str(self.handle_on.pk))
        self.assertEqual(owner.data["asset_id"], str(self.handle_on.pk))

    def test_retired_state_event_never_runs_or_toggles_the_mechanism(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", **{"interact:off": graph("interact:off",
            node("on", "state", targetState="on"), node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk)))})
        self.generated()
        self.interact(user=self.player)
        owner = self.lever()
        self.assertEqual(owner.data["lever"]["state"], "off")
        self.assertEqual(owner.data["asset_id"], str(self.handle_off.pk))
        self.assertNotIn("sprite", owner.data)
