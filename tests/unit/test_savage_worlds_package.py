"""The promises this ruleset makes to the engine that loads it, and to Pinnacle.

A ruleset is data, so nothing about it fails loudly at runtime: a formula that
does not parse just rolls zero, and a label with no translation renders as its
own dotted name. These pin the parts that would otherwise rot in silence,
including the permission notice the package is published under.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from app.engine.effects.active_effects import apply_stat_modifiers, effect_modifiers
from app.engine.rules.condition_effects import sync_condition_effects
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.formula_engine import evaluate
from app.engine.sheets.sheet_action_service import _roll_targets
from app.engine.sheets.sheet_ir_validator import validate_sheet_ir

PACKAGE = Path(__file__).resolve().parents[2] / "data/packages/rulesets/savage-worlds"
KEY_RE = re.compile(r"^savage-worlds\.[a-z0-9.]+$")

# The wording Pinnacle provided. It is a licence condition, not decoration.
NOTICE = (
    "This game references the Savage Worlds game system, available from Pinnacle "
    "Entertainment Group at www.peginc.com. Savage Worlds and all associated logos "
    "and trademarks are copyrights of Pinnacle Entertainment Group. Used with "
    "permission. Pinnacle makes no representation or warranty as to the quality, "
    "viability, or suitability for purpose of this product."
)


def _json(relative: str) -> dict:
    return json.loads((PACKAGE / relative).read_text(encoding="utf-8"))


HELPERS = _json("rules/formulas.gw.json")["helpers"]
ACTIONS = _json("rules/actions.gw.json")["actions"]
# Uma ação `chat` leva o item à mesa sem rolar nada: tudo que se afirma sobre
# fórmulas é sobre as rolagens.
ROLLS = {a: v for a, v in ACTIONS.items() if v.get("type") == "roll"}
DERIVED = _json("rules/derived.gw.json")["derived"]

# A Wild Card mid-fight: hurt, tired, armoured, holding a d8 skill.
SHEET = {
    "attributes": {
        "agility": {"sides": 8, "modifier": 1},
        "smarts": {"sides": 6, "modifier": 0},
        "spirit": {"sides": 6, "modifier": 0},
        "strength": {"sides": 10, "modifier": 0},
        "vigor": {"sides": 8, "modifier": 2},
    },
    "stats": {
        "parry": {"value": 0, "modifier": 0, "fightingSides": 10, "fightingModifier": 0, "shield": 1},
        "toughness": {"value": 0, "modifier": 0, "armor": 2},
        "pace": {"value": 6, "running": 6},
        "size": 0,
        "load": {"value": 0, "max": 0},
    },
    "wounds": {"value": 2, "max": 3},
    "fatigue": {"value": 1, "max": 2},
    "wildDie": {"sides": 6, "enabled": True},
    "penalty": {"wounds": 0, "fatigue": 0, "total": 0},
    "bars": {"bar_1": {"value": 0, "max": 3}, "bar_2": {"value": 0, "max": 2}},
}

# A forma real de um item numa ficha (ver ``DropEntry.as_dict``): o que o schema
# do item declara vive sob ``data``. Uma fixture achatada dava por boas fórmulas
# que, em jogo, liam campo nenhum.
ITEM = {
    "id": "itm_1",
    "type": "skill",
    "name": "Lutar",
    "img": "",
    "data": {"die": {"sides": 8, "modifier": 1}, "damage": "acing(6) + 2"},
}


def sheet_for(actor_type: str) -> dict:
    return apply_derived(
        actor_type=actor_type,
        data=json.loads(json.dumps(SHEET)),
        derived_rules=DERIVED,
        helpers=HELPERS,
        core={"name": "Aria"},
    )


def resolve(formula: str, context: dict) -> str:
    """A formula that is nothing but a path is replaced by the field's text."""
    if formula.startswith("@") and " " not in formula:
        cursor = context
        for segment in formula[1:].split("."):
            cursor = cursor.get(segment) if isinstance(cursor, dict) else None
        if isinstance(cursor, str) and cursor:
            return cursor
    return formula


# --- the licence ------------------------------------------------------------


def test_the_permission_notice_is_present_verbatim():
    """Granted by Pinnacle in writing, on the condition it appears as given."""
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    flattened = " ".join(readme.replace(">", " ").split())
    assert NOTICE in flattened, "o aviso de permissão precisa aparecer literalmente"


def test_the_only_image_is_the_official_logo():
    """Compatibility only: no artwork travels with this package but the logo."""
    suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}
    images = sorted(p.name for p in PACKAGE.rglob("*") if p.suffix.lower() in suffixes)
    assert images == ["SW_LOGO_FP_2018.png"], f"imagens inesperadas: {images}"


def test_the_stylesheet_never_reaches_for_a_file():
    css = (PACKAGE / "assets/savage-worlds.css").read_text(encoding="utf-8")
    assert "url(" not in css, "o visual da ficha é CSS puro, sem arquivo externo"


def test_no_content_ships_with_the_ruleset():
    manifest = _json("manifest.json")
    assert "contentPacks" not in manifest["provides"], "este pacote não traz conteúdo"
    assert manifest["name"] == "Savage Worlds Compatibility Package for Gravewright"
    assert manifest["version"] == "1.1.1"


def test_character_sheet_opens_at_the_reference_dimensions():
    source = (PACKAGE / "scripts/character-sheet.js").read_text(encoding="utf-8")
    assert 'actorType === "character" ? 859 : null' in source
    assert 'actorType === "character" ? 741 : null' in source


def test_combat_tracker_uses_selected_sdk_deck_and_public_card_url():
    manifest = _json("manifest.json")
    source = (PACKAGE / "scripts/character-sheet.js").read_text(encoding="utf-8")
    definitions = {setting["key"]: setting for setting in manifest["settings"]}

    assert definitions["initiative_deck_id"]["scope"] == "campaign"
    assert 'sdk.settings.get("initiative_deck_id"' in source
    assert 'sdk.settings.set("initiative_deck_id"' in source
    assert "sdk.cards.state()" in source
    assert "sdk.cards.draw(deck.id" in source
    assert "sdk.combat.setInitiativeOrder" in source
    assert "initiativeCardsByCampaign.set" in source
    assert "confirmedInitiativeStateByCampaign.set" in source
    assert "restoreConfirmedInitiativeOrder(payload)" in source
    assert "if (!assigned.size)" in source
    assert "card.front_asset_url" in source
    assert 'fetch("/game/' not in source
    assert "events.subscribe" in manifest["capabilities"]
    assert 'sdk.events.on("combat.updated"' in source
    assert "function shouldDealForObservedState" in source
    assert "afterAction:" not in source
    assert "automateInitiativeTurn" not in source
    after_render = source.split("afterRender:", 1)[1].split("},", 1)[0]
    assert "dealInitiative" not in after_render
    assert "previousTurnHadJoker" in source
    assert source.index("if (previousTurnHadJoker") < source.index("const dealt = []")


def test_initiative_deals_once_per_round_not_on_next_player():
    harness = PACKAGE.parents[3] / "tests/js/savage_initiative_trigger_harness.js"
    result = subprocess.run(["node", str(harness)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {
        "initialBlank": True,
        "initialPopulated": False,
        "add": True,
        "nextPlayer": False,
        "reorderedRows": False,
        "wrappedRound": True,
        "repaint": False,
        "inactive": False,
    }


# --- the dice ---------------------------------------------------------------


@pytest.mark.parametrize("action_id", sorted(ROLLS))
def test_every_action_formula_evaluates(action_id):
    """A formula the engine cannot parse silently totals zero."""
    context = {"core": {"name": "Aria"}, "sheet": sheet_for("character"), "item": ITEM}
    formula = resolve(ROLLS[action_id]["formula"], context)
    for _ in range(20):
        evaluate(formula, context=context, helpers=HELPERS)


def test_an_item_roll_reads_the_item_it_was_given():
    """``@item.x`` resolves against the stored instance, whose own fields sit
    under ``data``. Reaching one level too high returns nothing, ``acing(0)``
    is out of bounds, and the engine rejects the whole formula: the button
    reports no error and simply does nothing."""
    context = {"core": {}, "sheet": sheet_for("character"), "item": ITEM}

    for action_id in ("roll.skill", "roll.attack", "roll.power"):
        formula = ACTIONS[action_id]["formula"]
        assert "@item.data." in formula, f"{action_id} não lê a instância real"
        totals = {evaluate(formula, context=context, helpers=HELPERS).int_total for _ in range(80)}
        assert max(totals) > 2, f"{action_id} rolou como se o dado não existisse"


def test_a_damage_expression_is_read_off_the_item():
    """Damage is the item's whole expression, substituted before evaluation."""
    context = {"core": {}, "sheet": sheet_for("character"), "item": ITEM}
    formula = resolve(ACTIONS["roll.damage"]["formula"], context)
    assert formula == "acing(6) + 2", "a expressão do item não foi substituída"
    assert evaluate(formula, context=context, helpers=HELPERS).int_total >= 3


def test_an_extra_never_rolls_a_die_it_does_not_have():
    """``if`` evaluates both branches, so the Extra rolls are their own actions.
    A sheet with no wildDie must not reach for one."""
    sheet = sheet_for("extra")
    sheet.pop("wildDie", None)
    context = {"core": {"name": "Bran"}, "sheet": sheet, "item": ITEM}

    extras = [a for a in ACTIONS if a.endswith(".extra")]
    assert extras, "o teste precisa achar as ações de Extra"
    for action_id in extras:
        evaluate(resolve(ACTIONS[action_id]["formula"], context), context=context, helpers=HELPERS)


def test_a_skill_die_saved_by_an_html_select_still_rolls():
    context = {"core": {}, "sheet": sheet_for("character"), "item": json.loads(json.dumps(ITEM))}
    context["item"]["data"]["die"] = {"sides": "10", "modifier": "1"}
    formula = resolve(ACTIONS["roll.skill"]["formula"], context)

    result = evaluate(formula, context=context, helpers=HELPERS)

    assert any(group["notation"].startswith("1d10") for group in result.groups)


CARDS = _json("mappings/chat-cards.gw.json")["cards"]


def test_the_face_of_the_card_shows_results_and_never_a_formula():
    """The card reads as an answer, not as a sum being worked out. Notation and
    the assembled expression belong behind the breakdown, and two dice groups
    joined with '+' would read as a sum when only the better of the two counts."""
    for name, card in CARDS.items():
        values = {str(line.get("value", "")) for line in card["lines"]}
        forbidden = {
            "@roll.displayFormula",
            "@roll.formula",
            "@roll.expression",
            "@roll.baseFormula",
            "@roll.finalFormula",
            "@roll.resolvedFormula",
            "@roll.dice",
        }
        assert not (values & forbidden), f"{name} mostraria fórmula na face: {values & forbidden}"


def test_a_card_line_asks_for_a_value_the_renderer_reads():
    """``lines[].value`` is the contract; a card that writes ``fields[].path``
    validates as JSON, renders a title and a total, and silently drops every
    line it meant to show."""
    for name, card in CARDS.items():
        assert "fields" not in card, f"{name} usa a chave que o renderizador ignora"
        for line in card["lines"]:
            assert "value" in line, f"{name}: linha sem `value`"
            assert "path" not in line, f"{name}: `path` não é lido em linha de cartão"


def test_only_the_rolls_measured_against_a_target_declare_one():
    """A trait roll is read against 4 and gains a raise every 4 over it. Damage
    is read against the target's Toughness, which the card cannot know: giving
    it a target of 4 would print a confident lie."""
    assert CARDS["trait"]["outcome"] == {"target": 4, "step": 4}
    assert CARDS["attack"]["outcome"] == {"target": 4, "step": 4}
    assert "outcome" not in CARDS["damage"]


def test_every_wild_die_roll_has_an_extra_counterpart():
    for action_id, action in list(ROLLS.items()):
        if action_id.endswith(".extra"):
            continue
        if "@sheet.wildDie" in action["formula"]:
            assert f"{action_id}.extra" in ROLLS, f"{action_id} sem versão de Extra"


def test_the_wild_die_keeps_the_better_of_the_two():
    """A d12 Wild Die beside a d4 trait must lift the ceiling of the result."""
    context = {"core": {}, "sheet": sheet_for("character"), "item": ITEM}
    context["sheet"]["attributes"]["agility"] = {"sides": 4, "modifier": 0}
    context["sheet"]["wildDie"] = {"sides": 12, "enabled": True}
    context["sheet"]["penalty"]["total"] = 0

    formula = ACTIONS["roll.trait.agility"]["formula"]
    best = max(evaluate(formula, context=context, helpers=HELPERS).int_total for _ in range(200))
    assert best > 4, "o Wild Die não está entrando na conta"


def test_a_trait_die_can_ace_past_its_own_faces():
    totals = {evaluate("acing(4)", helpers=HELPERS).int_total for _ in range(400)}
    assert max(totals) > 4, "o dado não está explodindo"


# --- the derived sheet ------------------------------------------------------


def test_wound_and_fatigue_penalties_apply_and_cap():
    assert sheet_for("character")["penalty"]["total"] == 3  # 2 ferimentos + 1 fadiga

    battered = json.loads(json.dumps(SHEET))
    battered["wounds"]["value"] = 9
    battered["fatigue"]["value"] = 7
    capped = apply_derived(
        actor_type="character",
        data=battered,
        derived_rules=DERIVED,
        helpers=HELPERS,
        core={"name": "Aria"},
    )
    assert capped["penalty"]["total"] == 5, "a penalidade não pode crescer sem limite"


def test_parry_and_toughness_are_half_the_die_plus_two():
    sheet = sheet_for("character")
    # Vigor d8+2 -> 2 + (4 + 1) + 2 de armadura
    assert sheet["stats"]["toughness"]["value"] == 9
    # Lutar d10 -> 2 + metade do dado + 1 de escudo. O escudo soma no Aparar,
    # senão o campo existiria na ficha sem mudar número nenhum.
    assert sheet["stats"]["parry"]["value"] == 8


def test_token_bars_count_what_is_left_not_what_was_taken():
    """A full bar is an unhurt character: it drains as the hits land."""
    sheet = sheet_for("character")
    assert sheet["bars"]["bar_1"] == {"value": 1, "max": 3}  # 2 de 3 ferimentos
    assert sheet["bars"]["bar_2"] == {"value": 1, "max": 2}  # 1 de 2 de fadiga


SHEET_HTML = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
SHEET_JS = (PACKAGE / "scripts/character-sheet.js").read_text(encoding="utf-8")


def _schema_has(schema: dict, dotted: str) -> bool:
    cursor = schema
    for segment in dotted.split("."):
        properties = cursor.get("properties") if isinstance(cursor, dict) else None
        if not isinstance(properties, dict) or segment not in properties:
            return False
        cursor = properties[segment]
    return True


def test_every_field_the_html_sheet_binds_exists_in_the_schema():
    """A bind is a silent contract: a path the schema does not define reads back
    empty and its writes are dropped by ``sanitize_write``. Nothing errors: the
    field simply never keeps what you type."""
    schema = _json("schemas/character.schema.json")
    bound = set(re.findall(r'data-(?:bind|text)="system\.([A-Za-z0-9_.]+)"', SHEET_HTML))
    assert bound, "o teste precisa achar os binds da ficha"

    missing = sorted(path for path in bound if not _schema_has(schema, path))
    assert not missing, f"a ficha grava onde o schema não tem campo: {missing}"


def test_the_controller_and_the_template_agree_on_their_hooks():
    """The controller draws the wound track, the penalty and the derived notes
    into placeholders the template declares. A renamed hook leaves a blank spot
    on a working sheet: no error anywhere."""
    hooks = set(re.findall(r"\[(data-sw-[a-z-]+)=", SHEET_JS))
    assert hooks, "o teste precisa achar os ganchos do controlador"

    missing = sorted(hook for hook in hooks if hook not in SHEET_HTML)
    assert not missing, f"o controlador procura o que o template não tem: {missing}"


def test_the_html_sheet_never_edits_a_derived_field():
    """``readOnly`` paths are rejected on write. Rendering one as an input is an
    invitation to type a number the server throws away.

    A ``type="hidden"`` bind is not that invitation: nobody can type into it and
    it fires no change event, so it only ever reads. That is how a derived value
    stays available in the DOM without claiming a place on the sheet.
    """
    schema = _json("schemas/character.schema.json")
    written = {
        tag.group(1)
        for tag in re.finditer(r'<[^>]*data-bind="system\.([A-Za-z0-9_.]+)"[^>]*>', SHEET_HTML)
        if 'type="hidden"' not in tag.group(0)
    }

    def is_read_only(dotted: str) -> bool:
        cursor: object = schema
        for segment in dotted.split("."):
            properties = cursor.get("properties") if isinstance(cursor, dict) else None
            if not isinstance(properties, dict) or segment not in properties:
                return False
            cursor = properties[segment]
        return isinstance(cursor, dict) and cursor.get("readOnly") is True

    offenders = sorted(path for path in written if is_read_only(path))
    assert not offenders, f"campo derivado editável na ficha: {offenders}"


def _drop_zones() -> list[dict]:
    """As zonas que o manifesto declara para a ficha HTML do Wild Card."""
    character = next(
        a for a in _json("manifest.json")["provides"]["actorTypes"] if a["id"] == "character"
    )
    return character["sheet"]["dropZones"]


@pytest.mark.parametrize(
    "item_type",
    [entry["id"] for entry in _json("manifest.json")["provides"]["itemTypes"]],
)
def test_every_item_type_lands_in_a_list_the_sheet_draws(item_type):
    """Solto em qualquer ponto da ficha, um item vai para a lista do seu tipo.

    Quem roteia é o servidor, pelo tipo, contra estas zonas: igual ao que uma
    ficha declarativa faz com os ``dropZone`` do layout. O ponto onde a pessoa
    soltou não entra na conta: a aba de destino está quase sempre escondida
    durante o arrasto. Um tipo que ninguém reivindica cai na coleção genérica,
    que ficha nenhuma desenha: gravado e invisível para sempre.
    """
    claimed = {
        accepted.split(".")[-1] for zone in _drop_zones() for accepted in zone["accepts"]
    }
    assert item_type in claimed, f"nada aceita '{item_type}': sumiria na lista genérica"


def test_every_drop_zone_points_at_a_list_the_sheet_reads():
    """Rotear para uma coleção que o template não desenha guarda o item onde
    ninguém o vê, o mesmo sintoma de não ter zona nenhuma."""
    drawn = set(re.findall(r'data-item-list="system\.([A-Za-z0-9_]+)"', SHEET_HTML))
    drawn |= set(re.findall(r'data-sw-skill-rows', SHEET_HTML)) and {"skills"}

    for zone in _drop_zones():
        assert zone["list"] in drawn, f"a ficha não desenha 'system.{zone['list']}'"


def test_no_two_zones_claim_the_same_item_type():
    """A primeira zona que aceita o tipo ganha. Duas reivindicando o mesmo tipo
    tornam o destino uma questão de ordem no manifesto."""
    seen: dict[str, str] = {}
    for zone in _drop_zones():
        for accepted in zone["accepts"]:
            assert accepted not in seen, f"'{accepted}' em {seen.get(accepted)} e {zone['list']}"
            seen[accepted] = zone["list"]


def test_the_declared_conditions_are_the_flags_the_sheet_stores():
    """The HUD pill is produced by reading ``sheet.conditions.<id>`` for each
    declared condition. A declared id with no flag behind it never lights up;
    a flag nobody declared never reaches the token."""
    declared = {entry["id"] for entry in _json("rules/conditions.gw.json")["conditions"]}
    for name in ("character.schema.json", "extra.schema.json"):
        flags = set(_json(f"schemas/{name}")["properties"]["conditions"]["properties"])
        assert declared == flags, f"{name}: {declared ^ flags}"


CONDITIONS = _json("rules/conditions.gw.json")["conditions"]


def _sheet_with(**flags) -> dict:
    """The derived sheet with those conditions ticked and turned into effects."""
    data = json.loads(json.dumps(SHEET))
    data["wounds"]["value"] = 0
    data["fatigue"]["value"] = 0
    data["conditions"] = flags
    derived = apply_derived(
        actor_type="character",
        data=data,
        derived_rules=DERIVED,
        helpers=HELPERS,
        core={"name": "Aria"},
    )
    sync_condition_effects(derived, CONDITIONS, _json("locales/pt-BR.json"))
    return apply_stat_modifiers(derived)


def test_a_condition_that_costs_something_says_so_in_the_numbers():
    """Prone and Defending are not labels: SWADE gives each a number, and it
    arrives the same way a dropped effect's would: as a modifier, not as a term
    welded into the derived formula."""
    clean = _sheet_with()
    assert _sheet_with(defending=True)["stats"]["parry"]["value"] == clean["stats"]["parry"]["value"] + 4
    assert _sheet_with(prone=True)["stats"]["parry"]["value"] == clean["stats"]["parry"]["value"] - 2
    assert _sheet_with(encumbered=True)["stats"]["pace"]["value"] == clean["stats"]["pace"]["value"] - 2


def test_a_condition_reaches_the_roll_it_is_supposed_to_reach():
    """Distracted costs a trait roll −2 and a damage roll nothing. The two are
    told apart by the action's intent, so damage must not declare ``check``."""
    distracted = _sheet_with(distracted=True)

    trait = ACTIONS["roll.trait.agility"]
    _, on_trait = effect_modifiers(distracted, _roll_targets("roll.trait.agility", trait))
    assert [m["label"] for m in on_trait] == ["Distraído"]

    damage = ACTIONS["roll.damage"]
    _, on_damage = effect_modifiers(distracted, _roll_targets("roll.damage", damage))
    assert on_damage == [], "dano não é teste de traço"


def test_aiming_and_prone_only_touch_the_attack():
    aiming = _sheet_with(aiming=True)
    attack = ACTIONS["roll.attack"]
    _, on_attack = effect_modifiers(aiming, _roll_targets("roll.attack", attack))
    assert [m["operation"] for m in on_attack] == ["add"]

    _, on_trait = effect_modifiers(
        aiming, _roll_targets("roll.trait.smarts", ACTIONS["roll.trait.smarts"])
    )
    assert on_trait == [], "mirar não ajuda a pensar"


def test_the_token_mapping_reads_the_paths_the_sheet_writes():
    mapping = _json("mappings/token.gw.json")
    sheet = sheet_for("character")
    for actor_type in ("character", "extra"):
        for slot, bar in mapping[actor_type]["bars"].items():
            cursor: object = {"sheet": sheet}
            for segment in bar["value"].split("."):
                cursor = cursor[segment]  # type: ignore[index]
            assert isinstance(cursor, (int, float)), f"{actor_type}/{slot} não resolve"


# --- the sheets -------------------------------------------------------------


@pytest.mark.parametrize("layout", sorted(PACKAGE.glob("layouts/**/*.json")), ids=lambda p: p.name)
def test_every_layout_passes_the_sheet_validator(layout):
    assert validate_sheet_ir(json.loads(layout.read_text(encoding="utf-8"))) == []


ITEM_RENDERER = (
    Path(__file__).resolve().parents[2] / "static/js/sheets/items/item-sheet-renderer.js"
)


def _node_types(payload) -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            kind = node.get("type")
            if isinstance(kind, str):
                found.add(kind)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return found


@pytest.mark.parametrize(
    "layout", sorted(PACKAGE.glob("layouts/items/*.json")), ids=lambda p: p.name
)
def test_the_item_renderer_draws_every_node_the_layout_asks_for(layout):
    """The renderer answers an unknown ``type`` with nothing: no error, no node,
    just a field that never reaches the screen. A layout built on a type it does
    not handle looks empty, and the validator would still call it valid."""
    handled = set(re.findall(r'case "([A-Za-z]+)":', ITEM_RENDERER.read_text(encoding="utf-8")))
    assert handled, "o teste precisa achar os tipos que o renderizador trata"

    asked = _node_types(json.loads(layout.read_text(encoding="utf-8")))
    assert asked <= handled, f"o renderizador ignora: {sorted(asked - handled)}"


def _actions_in(payload) -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            value = node.get("action")
            if isinstance(value, str) and value.startswith("roll."):
                found.add(value)
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def test_every_layout_action_exists():
    """A button wired to a missing action does nothing, and says nothing."""
    referenced: set[str] = set()
    for layout in PACKAGE.glob("layouts/**/*.json"):
        referenced |= _actions_in(json.loads(layout.read_text(encoding="utf-8")))

    assert referenced, "o teste precisa achar ações nos layouts"
    missing = referenced - set(ACTIONS)
    assert not missing, f"ações inexistentes: {sorted(missing)}"


def test_the_wild_die_roll_is_written_as_max_of_two_dice():
    """The rule is 'keep the better of the two', so the formula says so out loud:
    two dice side by side inside a max(). ``acing`` only names the explosion."""
    formula = ACTIONS["roll.trait.agility"]["formula"]
    assert formula.startswith("max(acing("), formula
    assert formula.count("acing(") == 2, "os dois dados são rolados de verdade"


@pytest.mark.parametrize("action_id", sorted(ROLLS))
def test_a_formula_leaves_room_for_the_dialog_to_append(action_id):
    """The engine caps an expression at 200 characters, and the roll options are
    appended to it as text. A formula that fills the budget on its own would
    reject the very modifiers its dialog asked the player for.

    The room measured here is a full dialog: two segmented penalties, a typed
    modifier and four extra dice. The engine accepts up to eight dice of up to
    ``99d999``, so a player determined to overflow it still can: that ceiling
    belongs to the engine, which should truncate rather than refuse the roll.
    """
    budget = 200 - len(" - 4") * 2 - len(" + 999") - len(" + 2d10") * 4
    assert len(ROLLS[action_id]["formula"]) <= budget, "sobra pouco para o diálogo"


@pytest.mark.parametrize("action_id", sorted(ACTIONS))
def test_every_dialog_field_reaches_the_roll(action_id):
    """A field the roll does nothing with is collected from the player and then
    dropped on the floor: no error, the answer just never counts.

    There are two ways an answer counts: a transform that folds it into the
    formula, or ``actionField``: the field that decides *which* action runs, so
    that one control can offer a Spirit test and an unshake without the sheet
    needing a separate button for each.
    """
    action = ACTIONS[action_id]
    dialog = action.get("dialog") or {}
    asked = {
        field["id"]
        for field in dialog.get("fields", [])
        if field["type"] not in {"separator", "hint", "visibility"}
    }
    wired = {
        transform["when"].split(".", 1)[1].split(" ", 1)[0]
        for transform in action.get("transforms", [])
        if str(transform.get("when", "")).startswith("input.")
    }
    if dialog.get("actionField"):
        wired.add(str(dialog["actionField"]))
    assert asked <= wired, f"{action_id} pede sem usar: {sorted(asked - wired)}"


@pytest.mark.parametrize("action_id", sorted(ROLLS))
def test_an_action_swapping_option_points_at_an_action_that_exists(action_id):
    """``actionField`` lets an option redirect the roll. A typo there fires an
    action id nobody declared, and the button reports nothing at all."""
    dialog = ROLLS[action_id].get("dialog") or {}
    field_id = dialog.get("actionField")
    if not field_id:
        return
    field = next((f for f in dialog["fields"] if f.get("id") == field_id), None)
    assert field is not None, f"{action_id}: actionField aponta para campo inexistente"
    for option in field.get("options", []):
        target = option.get("action")
        if target:
            assert target in ACTIONS, f"{action_id} -> {target} não existe"


def test_only_the_wild_card_sheet_rolls_the_wild_die():
    wild_rolls = {a for a, v in ROLLS.items() if "@sheet.wildDie" in v["formula"]}
    character = _actions_in(_json("layouts/character.sheet.gw.json"))
    extra = _actions_in(_json("layouts/extra.sheet.gw.json"))

    assert character & wild_rolls, "o Wild Card não rola o Wild Die"
    assert not (extra & wild_rolls), "o Extra não deveria rolá-lo"


def test_html_skill_buttons_choose_the_action_for_each_actor_type():
    controller = (PACKAGE / "scripts" / "character-sheet.js").read_text(encoding="utf-8")
    assert 'ctx.sheetType === "extra" ? "roll.skill.extra" : "roll.skill"' in controller
    assert 'ctx.sheetType === "extra" ? "roll.unskilled.extra" : "roll.unskilled"' in controller
    assert "ctx.onItemAction?.(item.id, actionId" in controller


def test_unskilled_click_does_not_immediately_close_its_roll_dialog():
    """O listener global fecha diálogos ao receber cliques fora deles. Como a
    linha sem perícia é criada pelo controller e não possui ``data-action``, o
    clique precisa parar nela, igual ao clique das perícias treinadas."""
    controller = (PACKAGE / "scripts" / "character-sheet.js").read_text(encoding="utf-8")
    unskilled = controller.split("function unskilledRow", 1)[1].split(
        "\n  window.GravewrightSDK.register", 1
    )[0]

    assert 'addEventListener("click", (event) =>' in unskilled
    assert "event.preventDefault();" in unskilled
    assert "event.stopPropagation();" in unskilled
    assert "ctx.onAction?.(actionId, { event, element: name });" in unskilled


def _tabs(layout: dict) -> list[dict]:
    for child in layout["body"]["children"]:
        if child.get("type") == "tabs":
            return child["tabs"]
    raise AssertionError("a ficha precisa ter abas")


def test_the_identity_header_sits_outside_the_tabs():
    """Name and rank never scroll away, the way the system's own sheet reads."""
    body = _json("layouts/character.sheet.gw.json")["body"]
    first = body["children"][0]
    assert first["type"] == "section" and first["variant"] == "header"
    assert body["children"][1]["type"] == "tabs"


def test_the_summary_tab_is_two_columns_not_a_stack():
    """The complaint that started this: everything in one endless column."""
    summary = _tabs(_json("layouts/character.sheet.gw.json"))[0]
    grids = [c for c in summary["children"] if c.get("type") == "grid"]
    assert grids, "o resumo precisa de um grid, não de uma pilha"
    columns = [c for c in grids[0]["children"] if c.get("type") == "column"]
    assert len(columns) == 2, "duas colunas: o que você é, e o que você faz"


def test_the_quick_rolls_have_their_own_tab():
    """They used to hang off the bottom of the first tab as a stray block."""
    ids = [tab["id"] for tab in _tabs(_json("layouts/character.sheet.gw.json"))]
    assert "actions" in ids
    summary = _tabs(_json("layouts/character.sheet.gw.json"))[0]
    assert "rollButton" not in json.dumps(summary), "o resumo não é lugar de botão solto"


def test_the_first_tab_carries_what_a_fight_needs():
    """Parry, Toughness, wounds and fatigue without changing tabs."""
    main = _tabs(_json("layouts/character.sheet.gw.json"))[0]
    flat = json.dumps(main)
    for path in (
        "sheet.stats.parry.value",
        "sheet.stats.toughness.value",
        "sheet.wounds.value",
        "sheet.fatigue.value",
        "sheet.bennies.value",
    ):
        assert path in flat, f"{path} deveria estar na primeira aba"


# --- the catalogue ----------------------------------------------------------


def _keys_in(node) -> set[str]:
    if isinstance(node, dict):
        return set().union(*(_keys_in(v) for v in node.values())) if node else set()
    if isinstance(node, list):
        return set().union(*(_keys_in(v) for v in node)) if node else set()
    if isinstance(node, str) and KEY_RE.match(node):
        return {node}
    return set()


@pytest.mark.parametrize("locale", ["en", "pt-BR"])
def test_every_referenced_label_has_a_translation(locale):
    catalog = _json(f"locales/{locale}.json")
    used: set[str] = set()
    for path in PACKAGE.rglob("*.json"):
        if path.parent.name == "locales":
            continue
        used |= _keys_in(json.loads(path.read_text(encoding="utf-8")))

    # A ficha HTML também carrega chaves: em `data-sw-i18n` e nas ações que as
    # linhas de item declaram. Varrer só os JSON dava por órfã uma tradução que
    # a ficha usa, e por traduzida uma chave que ela inventou.
    for path in [*PACKAGE.rglob("*.html"), *PACKAGE.rglob("*.js")]:
        used |= set(re.findall(r"savage-worlds\.[a-z0-9.]+", path.read_text(encoding="utf-8")))

    assert used, "o teste precisa achar chaves"
    assert not (used - set(catalog)), f"sem tradução: {sorted(used - set(catalog))}"
    assert not (set(catalog) - used), f"tradução órfã: {sorted(set(catalog) - used)}"
