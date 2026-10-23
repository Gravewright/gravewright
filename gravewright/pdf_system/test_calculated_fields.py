"""Authoritative, bounded calculations and references stay inside the PDF system."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps.services import MapError

from .calculated_fields import normalize_calculated_fields, normalize_field_bindings
from .field_actions import normalize_field_actions
from .formulas import calculate_formula, compile_formula, expand_formula, field_references, numeric_value
from .schema import defaults, normalize


def binding(field, **changes):
    return {"source": "template:generic", "field": field, "path": "sheet.fields." + field,
            "type": "number", "name": field, **changes}


def calculated(field="Total", formula="@{Score} + 2", **changes):
    return {"source": "template:generic", "field": field, "formula": formula, **changes}


def sheet():
    data = defaults()
    data["pdf"].update(fieldBindings=[binding("Score"), binding("Total"), binding("Double")],
                       calculatedFields=[calculated()])
    data["fields"] = {"Score": 3, "Total": 999}
    return data


class FieldReferenceTests(SimpleTestCase):
    def test_references_are_names_not_paths_and_support_escaped_braces(self):
        self.assertEqual(field_references(r"@{A.b [0]} + @{close\}brace} + @{back\\slash} + @value"),
                         ["A.b [0]", "close}brace", "back\\slash"])
        self.assertEqual(expand_formula("1d20 + @{Score} + @value", lambda field: "-3", value=2), "1d20 + (-3) + (2)")
        self.assertEqual(expand_formula("@{Score}", lambda field: 1e-7), "(0.0000001)")
        self.assertEqual(expand_formula("@{Score}", lambda field: False), "(0)")

    def test_references_cannot_inject_syntax_and_numeric_coercion_is_bounded(self):
        for raw in ("1d20", "0x10", "1e3", {}, [], float("inf"), 1000001, 10 ** 1000):
            with self.subTest(raw=type(raw)), self.assertRaises(MapError):
                expand_formula("@{Score} + 1", lambda field: raw)
        for raw, expected in ((None, 0), ("", 0), (" ", 0), (True, 1), (False, 0), ("-3.5", -3.5)):
            with self.subTest(raw=raw):
                self.assertEqual(numeric_value(raw), expected)
        for formula in ("@{", "@{}", "@{ }", r"@{bad\q}", "@other", "@value.foo"):
            with self.subTest(formula=formula), self.assertRaises(MapError):
                compile_formula(formula)

    def test_native_dice_remain_available_only_in_roll_formulas_without_rng_in_validation(self):
        with patch("gravewright.dice.grammar.runtime.secure_sample", side_effect=AssertionError("No RNG")):
            compile_formula("2d20kh1 + @{Score} + @value")
            for formula in ("1d6", "@value + 2", "1d6 + @{Score}"):
                with self.subTest(formula=formula), self.assertRaises(MapError):
                    compile_formula(formula, dice=False, allow_value=False)
            self.assertEqual(calculate_formula("floor((@{Score} - 10) / 2)", lambda field: "15"), 2)

    def test_deterministic_operators_match_native_numeric_behavior(self):
        cases = {"floor(-1.2)": -2, "ceil(-1.2)": -1, "round(-1.5)": -1,
                 "round(1.5)": 2, "abs(-3)": 3, "min(2, 3)": 2,
                 "max(2, 3)": 3, "clamp(20, 0, 10)": 10, "1 < 2": 1,
                 "2 == 3": 0, "-3 + 2 * 4 / 2": 1,
                 "@{Score} * 2 + @{Score}": 9}
        for formula, expected in cases.items():
            with self.subTest(formula=formula):
                self.assertEqual(calculate_formula(formula, lambda field: 3), expected)
        for formula in ("1 / 0", "clamp(1, 3, 2)", "1000000 * 2", "max(1 < 2, 3)", "unknown(2)"):
            with self.subTest(formula=formula), self.assertRaises(MapError):
                calculate_formula(formula, lambda field: 1)


class FieldBindingTests(SimpleTestCase):
    def test_allowed_addresses_and_original_names_are_preserved(self):
        rows = [binding("Score"), binding("HP", path="sheet.bars.bar_1.value"),
                binding("AC", path="sheet.ac"), binding("Init", path="sheet.init"),
                binding("Name.with punctuation", path="sheet.fields.Safe_name", type="string", readOnly=True)]
        pdf = {"fieldBindings": rows}
        normalize_field_bindings(pdf)
        self.assertEqual(pdf["fieldBindings"], rows)

    def test_bindings_are_gm_only_and_omission_preserves_them(self):
        previous = {"pdf": {"fieldBindings": [binding("Score")]}}
        pdf = {}
        normalize_field_bindings(pdf, previous, gm=False)
        self.assertEqual(pdf["fieldBindings"], previous["pdf"]["fieldBindings"])
        for rows in ([], [binding("Score", path="sheet.fields.Other")], [binding("Other")]):
            with self.subTest(rows=rows), self.assertRaises(MapError) as error:
                normalize_field_bindings({"fieldBindings": rows}, previous, gm=False)
            self.assertEqual(error.exception.code, "forbidden")

    def test_binding_paths_and_shapes_reject_private_data_and_prototype_segments(self):
        paths = [None, [], "core.name", "sheet.notes", "sheet.pdf.asset", "sheet.token.size",
                 "sheet.fields.a.b", "sheet.fields.__proto__", "sheet.fields.constructor", "sheet.fields.prototype",
                 "sheet.effects", "sheet.bars.bar_3.value"]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(MapError):
                normalize_field_bindings({"fieldBindings": [binding("Score", path=path)]})
        for row in (binding("Score", unknown=True), binding("Score", readOnly=1),
                    binding("Score", type="object"), binding("Score", path="sheet.init", type="string")):
            with self.subTest(row=row), self.assertRaises(MapError):
                normalize_field_bindings({"fieldBindings": [row]})
        for rows in (None, {}, [binding("Score"), binding("Score")], [binding(str(i)) for i in range(1025)]):
            with self.subTest(rows_type=type(rows)), self.assertRaises(MapError):
                normalize_field_bindings({"fieldBindings": rows})


class CalculatedFieldTests(SimpleTestCase):
    def test_calculated_values_are_authoritative_and_chains_use_dependency_order(self):
        data = sheet()
        data["pdf"]["calculatedFields"] = [calculated("Double", "@{Total} * 2"), calculated()]
        data["fields"]["Double"] = -999
        self.assertEqual(normalize_calculated_fields(data), [])
        self.assertEqual(data["fields"]["Total"], 5)
        self.assertEqual(data["fields"]["Double"], 10)

    def test_player_can_fill_inputs_but_cannot_change_formula_configuration(self):
        previous = sheet()
        normalize_calculated_fields(previous)
        data = deepcopy(previous)
        data["fields"].update(Score=8, Total=999)
        del data["pdf"]["calculatedFields"]
        normalize_calculated_fields(data, previous, gm=False)
        self.assertEqual(data["fields"]["Total"], 10)
        data["pdf"]["calculatedFields"][0]["formula"] = "1"
        with self.assertRaises(MapError) as error:
            normalize_calculated_fields(data, previous, gm=False)
        self.assertEqual(error.exception.code, "forbidden")

    def test_missing_references_cycles_self_and_address_aliases_are_rejected(self):
        variants = [[calculated(formula="@{Missing}")], [calculated(formula="@{Total}")],
                    [calculated(formula="@{Double}"), calculated("Double", "@{Total}")]]
        for rows in variants:
            data = sheet()
            data["pdf"]["calculatedFields"] = rows
            with self.subTest(rows=rows), self.assertRaises(MapError):
                normalize_calculated_fields(data)
        data = sheet()
        data["pdf"]["fieldBindings"].append(binding("Alias", path="sheet.fields.Total"))
        data["pdf"]["calculatedFields"] = [calculated(formula="@{Alias}")]
        with self.assertRaises(MapError):
            normalize_calculated_fields(data)
        data = sheet()
        data["pdf"]["fieldBindings"][2]["path"] = "sheet.fields.Total"
        data["pdf"]["calculatedFields"] = [calculated(), calculated("Double", "1")]
        with self.assertRaises(MapError):
            normalize_calculated_fields(data)

    def test_calculation_definition_limits_and_exact_record_shape_are_validated(self):
        for rows in (None, {}, [calculated(unknown=True)], [calculated(), calculated()],
                     [calculated(str(i), "1") for i in range(257)]):
            data = sheet()
            data["pdf"]["calculatedFields"] = rows
            with self.subTest(rows_type=type(rows)), self.assertRaises(MapError):
                normalize_calculated_fields(data)

    def test_failed_input_preserves_previous_server_value_instead_of_submitted_output(self):
        previous = sheet()
        normalize_calculated_fields(previous)
        for invalid in ("Authored words", "1d20", {}):
            data = deepcopy(previous)
            data["fields"].update(Score=invalid, Total=999)
            with self.subTest(invalid=invalid):
                errors = normalize_calculated_fields(data, previous, gm=False)
                self.assertEqual(data["fields"]["Total"], 5)
                self.assertEqual(errors[0]["field"], "Total")
        data = sheet()
        data["pdf"]["calculatedFields"] = [calculated(formula="10 / @{Score}")]
        data["fields"]["Score"] = 0
        self.assertTrue(normalize_calculated_fields(data))
        self.assertEqual(data["fields"]["Total"], 0)

    def test_source_switch_does_not_recompute_archived_fields_sharing_value_addresses(self):
        data = sheet()
        data["pdf"]["fieldBindings"] += [binding("Score", source="template:other"), binding("Total", source="template:other")]
        data["pdf"]["calculatedFields"] += [calculated(formula="@{Score} * 100", source="template:other")]
        normalize_calculated_fields(data)
        self.assertEqual(data["fields"]["Total"], 5)

    def test_manual_fields_and_legacy_bar_overrides_are_resolved_without_pdf_parsing(self):
        data = sheet()
        field_id = str(uuid4())
        key = "manual_" + field_id.replace("-", "")
        data["pdf"]["manualFields"] = [{"id": field_id, "source": "template:generic", "name": "Modifier", "type": "number"}]
        data["pdf"]["calculatedFields"] = [calculated(formula="@{" + key + "} + 2")]
        data["token"]["bars"]["bar1Value"] = key
        data["bars"]["bar_1"]["value"] = 8
        normalize_calculated_fields(data)
        self.assertEqual(data["fields"]["Total"], 10)
        data["token"]["bars"]["bar2Value"] = "Total"
        normalize_calculated_fields(data)
        self.assertEqual(data["bars"]["bar_2"]["value"], 10)

    def test_string_targets_are_written_as_numbers_in_text_and_read_only_targets_fail(self):
        data = sheet()
        data["pdf"]["fieldBindings"][1]["type"] = "string"
        normalize_calculated_fields(data)
        self.assertEqual(data["fields"]["Total"], "5")
        for change in ({"readOnly": True}, {"type": "boolean"}):
            data = sheet()
            data["pdf"]["fieldBindings"][1].update(change)
            with self.subTest(change=change), self.assertRaises(MapError):
                normalize_calculated_fields(data)

    def test_roll_references_require_registered_same_source_fields(self):
        data = sheet()
        data["pdf"]["fieldActions"] = [{"source": "template:generic", "field": "Total",
                                         "roll": {"formula": "1d20 + @{Score}", "label": "Check"}}]
        normalize_field_actions(data["pdf"])
        data["pdf"]["fieldActions"][0]["roll"]["formula"] = "1d20 + @{Missing}"
        with self.assertRaises(MapError):
            normalize_field_actions(data["pdf"])


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class CalculatedFieldPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from gravewright.accounts.models import User
        from gravewright.actors.models import Actor
        from gravewright.campaigns.models import Campaign, Membership
        from gravewright.maps.models import Broadcast, Scene
        from gravewright.tokens.models import Token

        cls.gm = User.objects.create(email="pdf-calc-gm@example.test", name="GM", role="owner")
        cls.player = User.objects.create(email="pdf-calc-player@example.test", name="Player")
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="PDF calculations")
        Membership.objects.create(campaign=cls.campaign, user=cls.gm, role="gm")
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role="player")
        cls.actor = Actor.objects.create(campaign=cls.campaign, name="Hero", data=normalize(sheet()),
                                        permissions={str(cls.player.pk): "owner"})
        scene = Scene.objects.create(campaign=cls.campaign, name="Map", width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=scene)
        cls.token = Token.objects.create(scene=scene, actor=cls.actor, linked=False, snapshot=deepcopy(cls.actor.data))

    def view(self, user, snapshot=False):
        from gravewright.actors.services import sheet as read_sheet
        return read_sheet(self.campaign.pk, user.pk, self.actor.pk, self.token.pk if snapshot else None)

    def save(self, user, view):
        from gravewright.actors.services import command
        return command(self.campaign.pk, user.pk, "sheet.save", {**view, "actorId": str(self.actor.pk)}, uuid4())

    def test_player_output_tampering_is_overwritten_for_actor_and_snapshot(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                view = self.view(self.player, snapshot)
                view["data"]["fields"].update(Score=8, Total=999)
                self.save(self.player, view)
                self.assertEqual(self.view(self.gm, snapshot)["data"]["fields"]["Total"], 10)

    def test_non_numeric_input_still_saves_but_preserves_last_server_output(self):
        view = self.view(self.player)
        view["data"]["fields"].update(Score="Authored words", Total=999)
        self.save(self.player, view)
        saved = self.view(self.gm)["data"]["fields"]
        self.assertEqual(saved["Score"], "Authored words")
        self.assertEqual(saved["Total"], 5)

    def test_binding_and_formula_changes_remain_gm_only_through_sheet_service(self):
        for key, value in (("calculatedFields", []), ("fieldBindings", [])):
            with self.subTest(key=key):
                view = self.view(self.player)
                view["data"]["pdf"][key] = value
                with self.assertRaises(MapError) as error:
                    self.save(self.player, view)
                self.assertEqual(error.exception.code, "forbidden")
        view = self.view(self.gm)
        view["data"]["pdf"]["calculatedFields"][0]["formula"] = "@{Score} * 3"
        self.save(self.gm, view)
        self.assertEqual(self.view(self.gm)["data"]["fields"]["Total"], 9)
