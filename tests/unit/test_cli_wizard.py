from __future__ import annotations

import builtins

from app.cli import _no_intent_flags, build_parser
import app.cli.wizard as wizard
from app.engine.sdk.package_manifest_validator import validate_manifest
from app.cli.scaffold import build_manifest


def _script(checkbox_answers: dict, choose_answer=None):
    """Patch the wizard widgets with scripted answers keyed by a title substring."""

    def fake_checkbox(title, options, *, preselected=None):
        for needle, answer in checkbox_answers.items():
            if needle in title:
                return answer
        return list(preselected or [])

    def fake_choose(title, options, *, default=0):
        return choose_answer if choose_answer is not None else options[default][0]

    return fake_checkbox, fake_choose


def _ruleset_script(actor_types, item_types, mechanic, *, create_items="yes",
                    biography="yes", notes="yes", sheet_mode="html"):
    def fake_checkbox(title, options, *, preselected=None):
        if "actor sheet types" in title:
            return actor_types
        if "item sheet types" in title:
            return item_types
        return list(preselected or [])

    def fake_choose(title, options, *, default=0):
        if "start your ruleset" in title:
            return "scratch"
        if "build the sheets" in title:
            return sheet_mode
        if "Create item sheet types" in title:
            return create_items
        if "core mechanic" in title:
            return mechanic
        if "Biography tab" in title:
            return biography
        if "Notes tab" in title:
            return notes
        return options[default][0]

    return fake_checkbox, fake_choose


def test_wizard_builds_ruleset_intent(monkeypatch):
    cb, ch = _ruleset_script(["character", "npc"], ["weapon", "spell"], "d20-attribute-modifier-skill")
    monkeypatch.setattr(wizard, "_checkbox", cb)
    monkeypatch.setattr(wizard, "_choose", ch)

    result = wizard.run_new_wizard("ruleset", default_name="Sexto Elemento RPG Oficial")
    assert result is not None
    i = result.intent
    assert i.actor_types == ("character", "npc")
    assert i.item_types == ("weapon", "spell")
    assert i.mechanic == "d20-attribute-modifier-skill"
    assert i.has_sheets and i.html_sheets
    assert i.wants_biography and i.wants_notes
    assert i.wants_effects is True


def test_wizard_collects_fields_for_each_item_type(monkeypatch):
    _cb, ch = _ruleset_script(["character"], ["equipment"], "none")
    def checkbox(title, options, *, preselected=None):
        if "actor sheet types" in title:
            return ["character"]
        if "item sheet types" in title:
            return ["equipment"]
        if "fields should equipment" in title:
            return ["weight", "cost", "damage", "description"]
        return list(preselected or [])
    monkeypatch.setattr(wizard, "_checkbox", checkbox)
    monkeypatch.setattr(wizard, "_choose", ch)

    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    assert result.intent.item_fields == (
        ("equipment", ("weight", "cost", "damage", "description")),
    )


def test_item_decision_tree_only_asks_for_selected_fields(monkeypatch):
    prompts = []
    answers = iter(["2.5", "75", "2d8 + 3"])
    monkeypatch.setattr(wizard, "_interactive", lambda: True)
    monkeypatch.setattr(
        wizard, "_ask_text",
        lambda label, default=None: prompts.append(label) or next(answers),
    )
    monkeypatch.setattr(wizard, "_choose", lambda title, options, *, default=0: "yes")

    config = wizard._configure_item("equipment", ["weight", "cost", "damage", "description"])

    assert config == (
        ("weight.default", "2.5"),
        ("cost.default", "75"),
        ("damage.default", "2d8 + 3"),
        ("damage.roll", "yes"),
    )
    assert prompts == ["Starting weight", "Starting cost", "Starting damage formula"]


def test_armor_decision_tree_configures_armor_and_equipped(monkeypatch):
    monkeypatch.setattr(wizard, "_interactive", lambda: True)
    monkeypatch.setattr(wizard, "_ask_text", lambda label, default=None: "4")
    monkeypatch.setattr(wizard, "_choose", lambda title, options, *, default=0: "no")

    config = wizard._configure_item("armor", ["armor", "equipped"])

    assert config == (("armor.default", "4"), ("equipped.default", "no"))


def test_wizard_collects_fields_for_each_actor_type(monkeypatch):
    _cb, ch = _ruleset_script(["character"], [], "none", create_items="no")
    def checkbox(title, options, *, preselected=None):
        if "actor sheet types" in title:
            return ["character"]
        if "fields should character" in title:
            return ["health", "health-max", "mana", "description"]
        return list(preselected or [])
    monkeypatch.setattr(wizard, "_checkbox", checkbox)
    monkeypatch.setattr(wizard, "_choose", ch)

    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    assert result.intent.actor_fields == (
        ("character", ("health", "health-max", "mana", "description")),
    )


def test_wizard_biography_and_notes_questions(monkeypatch):
    cb, ch = _ruleset_script(["character"], [], "none", create_items="no",
                             biography="yes", notes="no")
    monkeypatch.setattr(wizard, "_checkbox", cb)
    monkeypatch.setattr(wizard, "_choose", ch)
    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    assert result.intent.wants_biography is True
    assert result.intent.wants_notes is False


def test_wizard_defaults_to_declarative_beginner_mode(monkeypatch):
    cb, ch = _ruleset_script(
        ["character"], [], "none", create_items="no", sheet_mode="declarative"
    )
    monkeypatch.setattr(wizard, "_checkbox", cb)
    monkeypatch.setattr(wizard, "_choose", ch)
    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    assert result.intent.has_sheets is True
    assert result.intent.html_sheets is False


def test_wizard_without_item_sheets(monkeypatch):
    cb, ch = _ruleset_script(["character"], [], "none", create_items="no")
    monkeypatch.setattr(wizard, "_checkbox", cb)
    monkeypatch.setattr(wizard, "_choose", ch)

    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    assert result.intent.item_types == ()
    assert result.intent.wants_effects is True


def test_wizard_custom_actor_type_normalized(monkeypatch):
    def fake_checkbox(title, options, *, preselected=None):
        if "actor sheet types" in title:
            return ["character", "custom"]
        return []

    def fake_choose(title, options, *, default=0):
        if "start your ruleset" in title:
            return "scratch"
        if "Create item sheet types" in title:
            return "no"
        return options[default][0]

    monkeypatch.setattr(wizard, "_checkbox", fake_checkbox)
    monkeypatch.setattr(wizard, "_choose", fake_choose)
    monkeypatch.setattr(builtins, "input", lambda _p="": "Star Ship, MECHA")

    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    assert result.intent.actor_types == ("character", "star-ship", "mecha")


def test_wizard_intent_validates(monkeypatch):
    cb, ch = _ruleset_script(["character"], ["item"], "dice-pool-successes")
    monkeypatch.setattr(wizard, "_checkbox", cb)
    monkeypatch.setattr(wizard, "_choose", ch)

    result = wizard.run_new_wizard("ruleset", default_name="My RPG")
    manifest = build_manifest(
        package_id="my-rpg", name="My RPG", version="0.1.0", kind="ruleset", intent=result.intent
    )
    assert validate_manifest(manifest).ok


def test_wizard_cancel_returns_none(monkeypatch):
    monkeypatch.setattr(wizard, "_choose", lambda *a, **k: None)
    assert wizard.run_new_wizard("ruleset", default_name="My RPG") is None


def _template_choose(template_id, *, sheet_mode="declarative"):
    def fake_choose(title, options, *, default=0):
        if "start your ruleset" in title:
            return "template"
        if "template fits" in title:
            return template_id
        if "build the sheets" in title:
            return sheet_mode
        return options[default][0]

    return fake_choose


def test_wizard_template_path_builds_full_intent(monkeypatch):
    monkeypatch.setattr(wizard, "_choose", _template_choose("fantasy-d20"))
    result = wizard.run_new_wizard("ruleset", default_name="Heroes")
    assert result is not None
    i = result.intent
    assert i.actor_types == ("character", "npc", "monster")
    assert i.item_types == ("weapon", "armor", "spell", "consumable")
    assert i.mechanic == "d20-attribute-modifier-skill"
    assert i.html_sheets is False
    assert i.wants_effects and i.wants_biography


def test_wizard_template_html_mode_override(monkeypatch):
    monkeypatch.setattr(wizard, "_choose", _template_choose("pbta", sheet_mode="html"))
    result = wizard.run_new_wizard("ruleset", default_name="Hack")
    assert result.intent.mechanic == "2d6-pbta"
    assert result.intent.html_sheets is True


def test_every_template_produces_a_valid_manifest():
    from app.cli.templates import RULESET_TEMPLATES
    from dataclasses import replace

    for template in RULESET_TEMPLATES:
        for html in (False, True):
            intent = replace(template.intent, html_sheets=html)
            manifest = build_manifest(
                package_id=template.id,
                name=template.label,
                version="0.1.0",
                kind=template.kind,
                intent=intent,
            )
            assert validate_manifest(manifest).ok, (template.id, html)


def test_wizard_assets_kind(monkeypatch):
    def fake_checkbox(title, options, *, preselected=None):
        if "asset categories" in title:
            return ["maps", "audio"]
        if "Include" in title:
            return ["locales"]
        return list(preselected or [])

    monkeypatch.setattr(wizard, "_checkbox", fake_checkbox)
    monkeypatch.setattr(wizard, "_choose", lambda *a, **k: a[1][0][0])

    result = wizard.run_new_wizard("assets", default_name="Pack")
    i = result.intent
    assert i.has_maps and i.has_audio and not i.has_images
    assert i.wants_locales


def test_text_checkbox_toggles_by_number(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "2 3")
    chosen = wizard._text_checkbox(
        "pick", [("a", "A"), ("b", "B"), ("c", "C")], preselected=set()
    )
    assert chosen == ["b", "c"]


def test_checkbox_falls_back_to_text_when_not_interactive(monkeypatch):
    # questionary needs a tty; without one the wizard uses the numbered fallback.
    monkeypatch.setattr(wizard, "_interactive", lambda: False)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "1")
    chosen = wizard._checkbox("pick", [("a", "A"), ("b", "B")], preselected=[])
    assert chosen == ["a"]


def test_wizard_step_renders_progress_inside_heading(monkeypatch, capsys):
    monkeypatch.setattr(wizard, "_interactive", lambda: True)
    monkeypatch.setattr(wizard, "_clear_screen", lambda: None)

    wizard._wizard_step(2, 5, "Authoring mode")

    out = capsys.readouterr().out
    assert "Create a ruleset" in out
    assert "Choose the data model, sheets and game mechanics" in out
    assert "Step 2 of 5 - Authoring mode" in out


def test_ruleset_name_is_first_step(monkeypatch):
    cb, ch = _ruleset_script(["character"], [], "none", create_items="no")
    steps = []
    monkeypatch.setattr(wizard, "_checkbox", cb)
    monkeypatch.setattr(wizard, "_choose", ch)
    monkeypatch.setattr(wizard, "_wizard_step", lambda *step: steps.append(step))

    result = wizard.run_new_wizard("ruleset", default_name="My RPG")

    assert result is not None
    assert steps == [
        (1, 5, "Ruleset name"),
        (2, 5, "Core mechanic"),
        (3, 5, "Authoring mode"),
        (4, 5, "Document types"),
        (5, 5, "Sheet sections"),
    ]


def test_exploding_dice_configuration_is_guided(monkeypatch):
    answers = iter(["forca, agilidade, mente", "8", "8"])
    monkeypatch.setattr(wizard, "_interactive", lambda: True)
    monkeypatch.setattr(wizard, "_ask_text", lambda label, default=None: next(answers))

    configured = wizard._configure_mechanic("exploding-dice")

    assert configured == (
        ("forca", "agilidade", "mente"),
        (),
        (("sides", "8"), ("threshold", "8")),
    )


def test_d20_skill_configuration_asks_attributes_and_skills(monkeypatch):
    answers = iter(["forca, destreza", "atletismo, furtividade"])
    monkeypatch.setattr(wizard, "_interactive", lambda: True)
    monkeypatch.setattr(wizard, "_ask_text", lambda label, default=None: next(answers))

    configured = wizard._configure_mechanic("d20-attribute-modifier-skill")

    assert configured[:2] == (("forca", "destreza"), ("atletismo", "furtividade"))


def test_wizard_step_clears_previous_step(monkeypatch):
    cleared = []
    monkeypatch.setattr(wizard, "_clear_screen", lambda: cleared.append(True))
    monkeypatch.setattr(wizard, "_wizard_heading", lambda *args, **kwargs: None)

    wizard._wizard_step(1, 5, "Ruleset name")

    assert cleared == [True]


def test_no_intent_flags_detection():
    parser = build_parser()
    bare = parser.parse_args(["ruleset", "new", "my-rpg", "--name", "X"])
    assert _no_intent_flags(bare) is True

    with_flag = parser.parse_args(["ruleset", "new", "my-rpg", "--name", "X", "--items"])
    assert _no_intent_flags(with_flag) is False

    with_sheets = parser.parse_args(["ruleset", "new", "my-rpg", "--name", "X", "--sheets"])
    assert _no_intent_flags(with_sheets) is False
