"""Safe native formula validation and persistence of GM-only PDF field actions."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps.services import MapError

from .schema import normalize


def action(**changes):
    return {"source": "template:generic", "field": "Strength modifier",
            "roll": {"formula": "1d20 + @value", "label": "Strength test"}, **changes}


class FieldActionSchemaTests(SimpleTestCase):
    def test_existing_sheet_shape_remains_unchanged(self):
        self.assertNotIn("fieldActions", normalize({})["pdf"])

    def test_native_and_manual_names_have_distinct_source_bound_actions(self):
        definitions = [action(), action(source="asset:" + str(uuid4())),
                       action(field="manual_" + uuid4().hex)]
        raw = {"pdf": {"fieldActions": definitions}}
        original = deepcopy(raw)
        self.assertEqual(normalize(raw)["pdf"]["fieldActions"], definitions)
        self.assertEqual(raw, original)
        self.assertNotIn("manualFields", normalize(raw)["pdf"])

    def test_all_native_formula_features_use_the_existing_parser_without_rolling(self):
        formulas = ["1d20 + @value", "2d20kh1 + @value", "2d20kl1 + @value",
                    "3d6 + @value * 2", "4d6kh3", "4dF", "5d6 >= 5",
                    "floor(@value / 2)", "ceil(@value / 2)", "round(@value / 2)",
                    "abs(@value)", "min(1, @value)", "max(1, @value)",
                    "clamp(@value, 0, 10)", "@value + @value", "1 + 2"]
        with patch("gravewright.dice.engine.evaluate", side_effect=AssertionError("Must not roll")), \
                patch("gravewright.dice.grammar.runtime.secure_sample", side_effect=AssertionError("No RNG")):
            for formula in formulas:
                with self.subTest(formula=formula):
                    row = action(roll={"formula": formula, "label": ""})
                    self.assertEqual(normalize({"pdf": {"fieldActions": [row]}})
                                     ["pdf"]["fieldActions"], [row])

    def test_gm_can_change_remove_and_omit_actions_without_touching_field_values(self):
        previous = normalize({"pdf": {"fieldActions": [action()]}, "fields": {"Strength_modifier": 3}})
        edited = deepcopy(previous)
        edited["pdf"]["fieldActions"][0]["roll"] = {"formula": "2d20kh1 + @value", "label": "Advantage"}
        self.assertEqual(normalize(edited, previous)["pdf"]["fieldActions"], edited["pdf"]["fieldActions"])
        edited["pdf"]["fieldActions"] = []
        self.assertEqual(normalize(edited, previous)["fields"], {"Strength_modifier": 3})
        self.assertEqual(normalize({"pdf": {"template": "another"}}, previous)
                         ["pdf"]["fieldActions"], [action()])

    def test_player_can_fill_fields_and_retain_or_omit_existing_action_definitions(self):
        previous = normalize({"pdf": {"fieldActions": [action()]}})
        for include in (False, True):
            raw = {"fields": {"Strength_modifier": 5}}
            if include:
                raw["pdf"] = {"fieldActions": [action()]}
            with self.subTest(include=include):
                saved = normalize(raw, previous, gm=False)
                self.assertEqual(saved["pdf"]["fieldActions"], [action()])
                self.assertEqual(saved["fields"]["Strength_modifier"], 5)

    def test_player_cannot_create_change_duplicate_or_remove_configuration(self):
        previous = normalize({"pdf": {"fieldActions": [action()]}})
        variants = [[], [action(), action(field="Another field")],
                    [action(source="template:another")], [action(field="Changed field")],
                    [action(roll={"formula": "1d6", "label": "Strength test"})],
                    [action(roll={"formula": "1d20 + @value", "label": "Changed label"})]]
        for actions in variants:
            with self.subTest(actions=actions), self.assertRaises(MapError) as caught:
                normalize({"pdf": {"fieldActions": actions}}, previous, gm=False)
            self.assertEqual(caught.exception.code, "forbidden")
        with self.assertRaises(MapError) as caught:
            normalize({"pdf": {"fieldActions": [action()]}}, gm=False)
        self.assertEqual(caught.exception.code, "forbidden")

    def test_legacy_player_bar_mapping_permissions_are_unchanged(self):
        previous = normalize({"pdf": {"fieldActions": [action()]}})
        saved = normalize({"token": {"bars": {"bar1Value": "Strength modifier"}}}, previous, gm=False)
        self.assertEqual(saved["token"]["bars"]["bar1Value"], "Strength modifier")
        self.assertEqual(saved["pdf"]["fieldActions"], [action()])

    def test_actions_have_bounded_counts_and_exact_shapes(self):
        largest = [action(field=f"Native field {i}") for i in range(256)]
        self.assertEqual(len(normalize({"pdf": {"fieldActions": largest}})["pdf"]["fieldActions"]), 256)
        for actions in (None, True, {}, "list", [None], largest + [action()],
                        [{**action(), "unknown": True}], [{"source": "template:generic", "field": "Name"}],
                        [action(roll={"formula": "1d20"})], [action(roll=None)],
                        [action(roll={"formula": "1d20", "label": "", "visibility": "gm"})]):
            with self.subTest(actions_type=type(actions)), self.assertRaises(MapError):
                normalize({"pdf": {"fieldActions": actions}})

    def test_arbitrary_native_names_are_preserved_and_bounded(self):
        for name in ("Character.Statistics[0].Strength", "Nome / Ação ☺", " Name with spaces ", "x" * 512):
            with self.subTest(name=name):
                row = action(field=name)
                self.assertEqual(normalize({"pdf": {"fieldActions": [row]}})["pdf"]["fieldActions"], [row])
        for name in (None, 3, [], "", "  ", "x" * 513, "Name\x00hidden"):
            with self.subTest(name=name), self.assertRaises(MapError):
                normalize({"pdf": {"fieldActions": [action(field=name)]}})

    def test_sources_are_canonical_without_granting_asset_access(self):
        source = "asset:" + str(uuid4())
        row = action(source=source.upper().replace("ASSET:", "asset:"))
        self.assertEqual(normalize({"pdf": {"fieldActions": [row]}})
                         ["pdf"]["fieldActions"][0]["source"], source)
        for source in (None, [], "generic", "asset:bad", "template:", "template:../private", "template:" + "x" * 121):
            with self.subTest(source=source), self.assertRaises(MapError):
                normalize({"pdf": {"fieldActions": [action(source=source)]}})

    def test_duplicate_source_field_pairs_are_rejected_including_canonical_aliases(self):
        source = "asset:" + str(uuid4())
        for rows in ([action(), action()],
                     [action(source=source), action(source=source.upper().replace("ASSET:", "asset:"))]):
            with self.subTest(rows=rows), self.assertRaises(MapError):
                normalize({"pdf": {"fieldActions": rows}})
        self.assertEqual(len(normalize({"pdf": {"fieldActions": [action(field="HP"), action(field="hp")]}})
                             ["pdf"]["fieldActions"]), 2)

    def test_invalid_formula_syntax_placeholders_functions_and_complexity_are_rejected(self):
        formulas = [None, 12, True, {}, "", "  ", "1" * 513, "1d20 +",
                    "1d20 + @sheet.fields.Strength", "1d20 + @value2", "@value.__proto__",
                    "__import__('os')", "unknown(1)", "max(1 < 2, 3)", "min(1)",
                    "100d6", "1d1001", "99d6 + 99d6 + 99d6", "+".join(["1d6"] * 33),
                    "(" * 33 + "1" + ")" * 33]
        for formula in formulas:
            with self.subTest(formula=formula), self.assertRaises(MapError):
                normalize({"pdf": {"fieldActions": [action(roll={"formula": formula, "label": ""})]}})

    def test_labels_match_the_native_chat_roll_limit(self):
        for label in ("", "A" * 48, "Ação da personagem"):
            with self.subTest(label=label):
                row = action(roll={"formula": "1d20", "label": label})
                self.assertEqual(normalize({"pdf": {"fieldActions": [row]}})["pdf"]["fieldActions"], [row])
        for label in (None, [], 2, "A" * 49, "label\x00hidden"):
            with self.subTest(label=label), self.assertRaises(MapError):
                normalize({"pdf": {"fieldActions": [action(roll={"formula": "1d20", "label": label})]}})


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class FieldActionPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from gravewright.accounts.models import User
        from gravewright.actors.models import Actor
        from gravewright.campaigns.models import Campaign, Membership
        from gravewright.maps.models import Broadcast, Scene
        from gravewright.tokens.models import Token

        cls.gm = User.objects.create(email="pdf-action-gm@example.test", name="GM", role="owner")
        cls.player = User.objects.create(email="pdf-action-player@example.test", name="Player")
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="PDF actions")
        Membership.objects.create(campaign=cls.campaign, user=cls.gm, role="gm")
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role="player")
        cls.actor = Actor.objects.create(campaign=cls.campaign, name="Hero", data=normalize({}),
                                        permissions={str(cls.player.pk): "owner"})
        scene = Scene.objects.create(campaign=cls.campaign, name="Map", width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=scene)
        cls.token = Token.objects.create(scene=scene, actor=cls.actor, linked=False, snapshot=deepcopy(cls.actor.data))

    def view(self, user, snapshot=False):
        from gravewright.actors.services import sheet
        return sheet(self.campaign.pk, user.pk, self.actor.pk, self.token.pk if snapshot else None)

    def save(self, user, view, request_id=None):
        from gravewright.actors.services import command
        return command(self.campaign.pk, user.pk, "sheet.save", {**view, "actorId": str(self.actor.pk)}, request_id or uuid4())

    def test_gm_actions_round_trip_and_players_fill_values_for_actor_and_snapshot(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                gm_view = self.view(self.gm, snapshot)
                gm_view["data"]["pdf"]["fieldActions"] = [action()]
                self.save(self.gm, gm_view)
                player_view = self.view(self.player, snapshot)
                del player_view["data"]["pdf"]["fieldActions"]
                player_view["data"]["fields"]["Strength_modifier"] = 3
                self.save(self.player, player_view)
                saved = self.view(self.gm, snapshot)["data"]
                self.assertEqual(saved["pdf"]["fieldActions"], [action()])
                self.assertEqual(saved["fields"]["Strength_modifier"], 3)

    def test_player_creation_and_removal_are_atomic_for_actor_and_snapshot(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                player_view = self.view(self.player, snapshot)
                player_view["data"]["pdf"]["fieldActions"] = [action()]
                with self.assertRaises(MapError) as caught:
                    self.save(self.player, player_view)
                self.assertEqual(caught.exception.code, "forbidden")
                self.assertNotIn("fieldActions", self.view(self.gm, snapshot)["data"]["pdf"])
                gm_view = self.view(self.gm, snapshot)
                gm_view["data"]["pdf"]["fieldActions"] = [action()]
                self.save(self.gm, gm_view)
                player_view = self.view(self.player, snapshot)
                player_view["data"]["pdf"]["fieldActions"] = []
                with self.assertRaises(MapError):
                    self.save(self.player, player_view)
                self.assertEqual(self.view(self.gm, snapshot)["data"]["pdf"]["fieldActions"], [action()])

    def test_invalid_formula_rejects_candidate_without_corrupting_stored_sheet(self):
        view = self.view(self.gm)
        original = deepcopy(view["data"])
        view["data"]["pdf"]["fieldActions"] = [action(roll={"formula": "bad(@value)", "label": ""})]
        view["data"]["fields"]["Strength_modifier"] = 99
        with self.assertRaises(MapError):
            self.save(self.gm, view)
        self.assertEqual(self.view(self.gm)["data"], original)

    def test_action_saves_reuse_receipts_and_reject_stale_revisions(self):
        view = self.view(self.gm)
        view["data"]["pdf"]["fieldActions"] = [action()]
        request_id = uuid4()
        first = self.save(self.gm, view, request_id)
        self.assertEqual(self.save(self.gm, view, request_id), first)
        with self.assertRaises(MapError) as caught:
            self.save(self.gm, view)
        self.assertEqual(caught.exception.code, "conflict")
