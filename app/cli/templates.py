"""Ready-made ruleset scaffolds (``templates``) for ``grave ruleset new``.

A *template* is a curated, complete :class:`~app.cli.scaffold.Intent` for a
recognizable family of tabletop systems — "classic d20 fantasy", "Powered by the
Apocalypse", "percentile horror", and so on. Instead of answering a dozen
questions about a system they may not have designed yet, an author picks a
template that already declares sensible actor/item types, a core dice mechanic,
and the right sheet sections, then edits the generated files.

Templates are the fast, beginner-friendly entry point; the from-scratch wizard
and the raw ``--flags`` remain available for full control. Both the interactive
wizard and the non-interactive ``--template <id>`` CLI flag resolve names here,
so this module is the single source of truth.

Every template targets *declarative* sheets by default (the simpler authoring
mode). Callers may flip to HTML templates with :func:`dataclasses.replace`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.cli.scaffold import Intent

# The classic six-ability spread shared by the d20-family templates.
_ABILITIES = (
    "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma",
)


@dataclass(frozen=True)
class Template:
    """A named, ready-to-build package preset.

    ``tagline`` is the one-line hook shown in the picker; ``description`` is the
    longer blurb shown in the preview before creation.
    """

    id: str
    label: str
    tagline: str
    description: str
    kind: str
    name_suggestion: str
    intent: Intent


# Order here is the presentation order in the wizard and ``--list-templates``.
# "blank" is first so the minimal path is always one keystroke away; the rest are
# roughly ordered most-popular-first.
RULESET_TEMPLATES: tuple[Template, ...] = (
    Template(
        id="blank",
        label="Blank slate",
        tagline="One character sheet, no dice mechanic — total freedom.",
        description=(
            "A single character actor type with the common fields and nothing "
            "else. Pick this when you want to design the system yourself."
        ),
        kind="ruleset",
        name_suggestion="My Ruleset",
        intent=Intent(
            has_sheets=True,
            actor_types=("character",),
            item_types=(),
            mechanic="none",
        ),
    ),
    Template(
        id="fantasy-d20",
        label="Classic d20 fantasy",
        tagline="Six abilities + skills, weapons, armor, spells and effects (D&D-like).",
        description=(
            "Characters, NPCs and monsters with the six classic abilities and a "
            "few skills. Weapon, armor, spell and consumable items, plus active "
            "effects and Biography/Notes tabs. Rolls are d20 + ability modifier "
            "+ skill."
        ),
        kind="ruleset",
        name_suggestion="My d20 Fantasy",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc", "monster"),
            item_types=("weapon", "armor", "spell", "consumable"),
            mechanic="d20-attribute-modifier-skill",
            mechanic_attributes=_ABILITIES,
            mechanic_skills=("athletics", "perception", "stealth", "arcana"),
            wants_biography=True,
            wants_notes=True,
            wants_effects=True,
        ),
    ),
    Template(
        id="osr-roll-under",
        label="Old-school roll-under",
        tagline="Roll under your ability on a d20 — lean, lethal, classic.",
        description=(
            "Characters and monsters with the six classic abilities, weapon, "
            "armor and spell items, and active effects. Tests succeed when you "
            "roll under the relevant ability on a d20."
        ),
        kind="ruleset",
        name_suggestion="My OSR Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "monster"),
            item_types=("weapon", "armor", "spell"),
            mechanic="d20-roll-under",
            mechanic_attributes=_ABILITIES,
            mechanic_config=(("default", "12"),),
            wants_effects=True,
        ),
    ),
    Template(
        id="pbta",
        label="Powered by the Apocalypse",
        tagline="2d6 + stat moves, narrative-first, no inventory grind.",
        description=(
            "Player characters and NPCs driven by the five PbtA stats "
            "(cool/hard/hot/sharp/weird). Moves resolve on 2d6 + stat. No item "
            "types — fiction first — with a Biography tab for playbooks."
        ),
        kind="ruleset",
        name_suggestion="My PbtA Hack",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc"),
            item_types=(),
            mechanic="2d6-pbta",
            mechanic_attributes=("cool", "hard", "hot", "sharp", "weird"),
            wants_biography=True,
        ),
    ),
    Template(
        id="forged-dark",
        label="Forged in the Dark",
        tagline="d6 dice pools, crews and abilities — heist-and-consequence play.",
        description=(
            "Characters, NPCs and a shared crew sheet. Abilities and gear as "
            "items, active effects, and action rolls built from d6 dice pools "
            "that count successes."
        ),
        kind="ruleset",
        name_suggestion="My Forged Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc", "crew"),
            item_types=("ability", "gear"),
            mechanic="dice-pool-successes",
            mechanic_attributes=("insight", "prowess", "resolve"),
            mechanic_config=(("default", "2"), ("target", "6")),
            wants_effects=True,
        ),
    ),
    Template(
        id="cosmic-horror",
        label="Percentile horror",
        tagline="d100 roll-under skills for fragile investigators (CoC-like).",
        description=(
            "Investigators, NPCs and monsters resolving skills on a d100 "
            "roll-under. Weapon and spell items, with Biography and Notes tabs "
            "for the long, doomed paper trail."
        ),
        kind="ruleset",
        name_suggestion="My Horror Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc", "monster"),
            item_types=("weapon", "spell"),
            mechanic="d100-percentile",
            mechanic_skills=("perception", "investigation", "medicine", "occult"),
            mechanic_config=(("default", "45"),),
            wants_biography=True,
            wants_notes=True,
        ),
    ),
    Template(
        id="fate-core",
        label="Fate / Fudge",
        tagline="4dF approaches and aspects — pure narrative engine.",
        description=(
            "Characters and NPCs using the six Fate approaches and 4dF rolls. "
            "Active effects stand in for aspects and stunts, with a Biography "
            "tab for high concept and trouble."
        ),
        kind="ruleset",
        name_suggestion="My Fate Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc"),
            item_types=(),
            mechanic="fudge-fate",
            mechanic_attributes=(
                "careful", "clever", "flashy", "forceful", "quick", "sneaky",
            ),
            wants_biography=True,
            wants_effects=True,
        ),
    ),
    Template(
        id="year-zero",
        label="Year Zero survival",
        tagline="d6 attribute pools, gear that matters, gritty survival.",
        description=(
            "Characters, NPCs and monsters with the four Year Zero attributes. "
            "Weapon, armor and gear items plus active effects. Rolls gather a "
            "pool of d6s and count sixes."
        ),
        kind="ruleset",
        name_suggestion="My Survival Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc", "monster"),
            item_types=("weapon", "armor", "gear"),
            mechanic="year-zero-d6-pool",
            mechanic_attributes=("strength", "agility", "wits", "empathy"),
            wants_effects=True,
        ),
    ),
    Template(
        id="action-2d20",
        label="2d20 action",
        tagline="Attribute + skill on 2d20 — momentum-fueled cinematic play.",
        description=(
            "Characters and NPCs testing attribute + skill on 2d20. Weapon and "
            "talent items, plus active effects for momentum and complications."
        ),
        kind="ruleset",
        name_suggestion="My 2d20 Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc"),
            item_types=("weapon", "talent"),
            mechanic="2d20",
            mechanic_attributes=("agility", "brawn", "coordination", "insight"),
            mechanic_skills=("athletics", "survival", "technology"),
            wants_effects=True,
        ),
    ),
    Template(
        id="card-narrative",
        label="Card-driven narrative",
        tagline="Draw from a deck instead of rolling dice — storytelling games.",
        description=(
            "Characters and NPCs that resolve actions by drawing from a 52-card "
            "deck. A Biography tab keeps the story front and centre; add your "
            "own suits and meanings in the generated action."
        ),
        kind="ruleset",
        name_suggestion="My Card Game",
        intent=Intent(
            has_sheets=True,
            actor_types=("character", "npc"),
            item_types=(),
            mechanic="cards",
            mechanic_config=(("deck-size", "52"),),
            wants_biography=True,
        ),
    ),
)


_BY_ID: dict[str, Template] = {t.id: t for t in RULESET_TEMPLATES}


def templates_for_kind(kind: str) -> list[Template]:
    """Templates available for ``kind`` (only ``ruleset`` ships presets today)."""
    return [t for t in RULESET_TEMPLATES if t.kind == kind]


def template_ids(kind: str | None = None) -> list[str]:
    """All template ids, optionally filtered to ``kind``."""
    items = templates_for_kind(kind) if kind else list(RULESET_TEMPLATES)
    return [t.id for t in items]


def get_template(template_id: str) -> Template | None:
    """Return the template with ``template_id``, or ``None`` when unknown."""
    return _BY_ID.get(template_id)
