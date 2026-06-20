"""Interactive guided wizard for ``grave <kind> new``.

Instead of remembering intent flags, an author can answer a few selection
questions and the wizard builds the same :class:`~app.cli.scaffold.Intent` the
flags would. Selection uses ``questionary`` (prompt_toolkit) when it is
installed — the ``dev`` extra ships it — which renders scrollable, resize-safe
checkbox/select prompts. When it is absent the wizard degrades to a plain
numbered text menu.

The wizard only runs on an interactive terminal. Callers fall back to the
flag-driven path otherwise.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace

from app.cli.scaffold import (
    MECHANICS, Intent, _slugify, actor_field_options, default_actor_field_ids,
    default_item_field_ids, item_field_options, mechanic_ids,
)
from app.cli.templates import Template, get_template, templates_for_kind

try:
    import questionary

    _QUESTIONARY = True
except ImportError:  # pragma: no cover - the dev extra ships questionary
    _QUESTIONARY = False


_WIZARD_STYLE = (
    questionary.Style(
        [
            ("qmark", "fg:#c09a5a bold"),
            ("question", "bold"),
            ("answer", "fg:#c09a5a bold"),
            ("pointer", "fg:#c09a5a bold"),
            ("highlighted", "fg:#c09a5a bold"),
            ("selected", "fg:#6fddb4"),
            ("instruction", "fg:#777777"),
        ]
    )
    if _QUESTIONARY
    else None
)


@dataclass
class WizardResult:
    name: str
    intent: Intent


def _split_ids(raw: str) -> list[str]:
    """Split a comma-separated string into ids (slugify handles spaces within one)."""
    return [token.strip() for token in raw.split(",") if token.strip()]


# --- selection widgets ------------------------------------------------------
#
# ``questionary`` handles arrow-key navigation, scrolling for long lists, and
# terminal resize, so the prompt never miscounts lines and "breaks the screen".
# A numbered text fallback keeps the wizard usable without the dev extra.


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _wizard_heading(
    title: str,
    subtitle: str = "",
    *,
    step: tuple[int, int, str] | None = None,
) -> None:
    if not _interactive():
        return
    try:
        from rich.console import Console
        from rich.panel import Panel

        body = f"[bold]{title}[/bold]"
        if subtitle:
            body += f"\n[dim]{subtitle}[/dim]"
        if step:
            number, total, step_title = step
            body += f"\n[bold yellow]Step {number} of {total} - {step_title}[/bold yellow]"
        Console().print(Panel.fit(body, border_style="yellow", padding=(0, 2)))
    except ImportError:  # pragma: no cover
        print(title)
        if subtitle:
            print(subtitle)
        if step:
            number, total, step_title = step
            print(f"Step {number} of {total} - {step_title}")


def _clear_screen() -> None:
    if not _interactive():
        return
    try:
        from rich.console import Console

        Console().clear()
    except ImportError:  # pragma: no cover
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def _wizard_step(number: int, total: int, title: str) -> None:
    _clear_screen()
    _wizard_heading(
        "Create a ruleset",
        "Choose the data model, sheets and game mechanics",
        step=(number, total, title),
    )


def _wizard_intro(kind: str) -> None:
    """A friendly welcome banner shown before the first question."""
    if not _interactive():
        return
    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(
            Panel.fit(
                f"[bold]Let's build a {kind}.[/bold]\n"
                "[dim]Start from a ready-made template and tweak it, or answer a\n"
                "few questions to design it from scratch. Press Ctrl+C to cancel\n"
                "at any time.[/dim]",
                title="Gravewright",
                border_style="yellow",
                padding=(0, 2),
            )
        )
    except ImportError:  # pragma: no cover
        print(f"Let's build a {kind}. Ctrl+C to cancel at any time.")


def _format_types(label: str, ids) -> str:
    values = [str(i) for i in (ids or ())]
    return f"{label}: {', '.join(values) if values else '(none)'}"


def _render_intent_summary(
    name: str, kind: str, intent: Intent, *, template: Template | None = None
) -> None:
    """Show what will be generated so the author can confirm before writing.

    Display-only: the CLI still asks for the final create confirmation. Skipped
    on non-interactive runs so scripted/automated paths stay silent.
    """
    if not _interactive():
        return

    mechanic_label = MECHANICS.get(intent.mechanic, {}).get("label", intent.mechanic)
    sections = [
        label
        for label, on in (
            ("Biography", intent.wants_biography),
            ("Notes", intent.wants_notes),
            ("Active Effects", intent.wants_effects),
        )
        if on
    ]
    mode = "HTML templates (full control)" if intent.html_sheets else "Declarative"
    rows = [
        ("Name", name),
        ("Package id", _slugify(name)),
        ("Actor types", ", ".join(intent.actor_types or ()) or "(none)"),
        ("Item types", ", ".join(intent.item_types or ()) or "(none)"),
        ("Core mechanic", mechanic_label),
        ("Sheet sections", ", ".join(sections) or "(none)"),
        ("Authoring mode", mode),
    ]

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        if template is not None:
            console.print(
                Panel.fit(
                    f"[bold]{template.label}[/bold]\n[dim]{template.description}[/dim]",
                    title="Template",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )
        table = Table(
            title="You're about to create",
            title_justify="left",
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("", style="dim", no_wrap=True)
        table.add_column("", style="bold")
        for key, value in rows:
            table.add_row(key, value)
        console.print(table)
    except ImportError:  # pragma: no cover
        if template is not None:
            print(f"Template: {template.label}")
            print(f"  {template.description}")
        print("You're about to create:")
        for key, value in rows:
            print(f"  {key}: {value}")


def _checkbox(
    title: str, options: list[tuple[str, str]], *, preselected: list[str] | None = None
) -> list[str] | None:
    pre = set(preselected or [])
    if _QUESTIONARY and _interactive():
        choices = [
            questionary.Choice(title=label, value=key, checked=key in pre)
            for key, label in options
        ]
        return questionary.checkbox(title, choices=choices, style=_WIZARD_STYLE).ask()
    return _text_checkbox(title, options, pre)


def _choose(title: str, options: list[tuple[str, str]], *, default: int = 0) -> str | None:
    if _QUESTIONARY and _interactive():
        choices = [questionary.Choice(title=label, value=key) for key, label in options]
        index = max(0, min(default, len(choices) - 1))
        return questionary.select(
            title, choices=choices, default=choices[index], style=_WIZARD_STYLE
        ).ask()
    return _text_choose(title, options, default)


def _text_checkbox(
    title: str, options: list[tuple[str, str]], preselected: set[str]
) -> list[str] | None:
    """Numbered fallback when questionary is unavailable."""
    selected = set(preselected)
    print(title)
    for i, (key, label) in enumerate(options, 1):
        box = "x" if key in selected else " "
        print(f"  [{box}] {i}. {label}")
    raw = input("> numbers to toggle (e.g. 2 3), Enter to confirm: ").strip()
    if raw.lower() in {"q", "quit"}:
        return None
    for token in raw.replace(",", " ").split():
        if token.isdigit() and 1 <= int(token) <= len(options):
            selected ^= {options[int(token) - 1][0]}
    return [key for key, _ in options if key in selected]


def _text_choose(title: str, options: list[tuple[str, str]], default: int) -> str | None:
    print(title)
    for i, (_key, label) in enumerate(options, 1):
        marker = " (default)" if i - 1 == default else ""
        print(f"  {i}. {label}{marker}")
    raw = input(f"> choose [1-{len(options)}], Enter for default: ").strip()
    if raw.lower() in {"q", "quit"}:
        return None
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1][0]
    return options[default][0]


def _ask_text(label: str, default: str | None = None) -> str | None:
    suffix = f" [{default}]" if default else ""
    try:
        entered = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return None
    return entered or default


# --- the wizard ------------------------------------------------------------


# Common sheet types offered in the wizard. Ids are the generated, normalized
# English type ids; "custom" lets the author enter their own.
ACTOR_SHEET_OPTIONS = (
    "character", "monster", "npc", "companion", "familiar", "mount", "vehicle",
    "starship", "mecha", "drone", "robot", "spirit", "summon", "faction",
    "organization", "settlement", "kingdom", "domain", "crew", "squad", "army",
    "base", "location", "hazard", "trap",
    # extended
    "deity", "swarm", "construct", "undead", "elemental", "dragon", "beast",
    "plant", "guild", "party", "planet", "station", "colony", "fleet", "horde",
)
ITEM_SHEET_OPTIONS = (
    "item", "weapon", "armor", "shield", "gear", "equipment", "consumable",
    "spell", "power", "ability", "skill", "feat", "talent", "trait", "ancestry",
    "heritage", "background", "class", "subclass", "profession", "path",
    "technique", "ritual", "condition", "injury", "cyberware", "implant",
    "augmentation", "module", "vehicle-module", "starship-module", "mecha-module",
    "treasure", "loot",
    # extended
    "potion", "scroll", "wand", "rod", "staff", "ammunition", "currency", "tool",
    "kit", "poison", "drug", "artifact", "relic", "rune", "enchantment",
    "mutation", "perk", "flaw", "maneuver", "stance", "invocation", "cantrip",
    "prayer", "blessing", "curse", "contract", "container", "clothing",
    "jewelry", "material", "software", "program", "gadget", "grenade",
    "explosive", "food", "vehicle",
)


def _select_types(title: str, options: tuple[str, ...], preselected: list[str]) -> list[str] | None:
    """Multi-select common type ids plus a ``custom`` entry for free-form ids."""
    chosen = _checkbox(
        title,
        [(opt, opt) for opt in options] + [("custom", "custom (type your own)")],
        preselected=preselected,
    )
    if chosen is None:
        return None
    ids = [c for c in chosen if c != "custom"]
    if "custom" in chosen:
        raw = _ask_text("Custom type ids (comma-separated)")
        if raw:
            ids.extend(_split_ids(raw))
    # Normalize + de-duplicate, preserving order.
    out: list[str] = []
    for tid in ids:
        slug = _slugify(tid)
        if slug and slug not in out:
            out.append(slug)
    return out


def _ask_ids(label: str, defaults: tuple[str, ...]) -> tuple[str, ...] | None:
    raw = _ask_text(label, ", ".join(defaults))
    if raw is None:
        return None
    values = []
    for value in _split_ids(raw):
        slug = _slugify(value)
        if slug and slug not in values:
            values.append(slug)
    return tuple(values)


def _configure_mechanic(mechanic: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, str], ...]] | None:
    """Ask the questions relevant to one mechanic preset."""
    if not _interactive() or mechanic == "none":
        return (), (), ()
    attrs: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    config: list[tuple[str, str]] = []
    attribute_defaults = {
        "d20-attribute-modifier-skill": _DND_ATTRIBUTE_DEFAULTS,
        "d20-attribute-modifier": _DND_ATTRIBUTE_DEFAULTS,
        "d20-roll-under": _DND_ATTRIBUTE_DEFAULTS,
        "dice-pool-successes": ("strength", "agility", "mind"),
        "dice-pool-count-hits": ("strength", "agility", "mind"),
        "exploding-dice": ("strength", "agility", "mind"),
        "step-dice": ("strength", "agility", "mind", "spirit"),
        "fudge-fate": ("careful", "clever", "flashy", "forceful", "quick", "sneaky"),
        "2d6-pbta": ("cool", "hard", "hot", "sharp", "weird"),
        "2d20": ("agility", "brawn", "coordination", "insight"),
        "year-zero-d6-pool": ("strength", "agility", "wits", "empathy"),
        "custom": ("resource",),
    }
    if mechanic in attribute_defaults:
        label = "Approaches (comma-separated)" if mechanic == "fudge-fate" else "Attributes (comma-separated)"
        attrs = _ask_ids(label, attribute_defaults[mechanic])
        if attrs is None:
            return None
    skill_defaults = {
        "d20-attribute-modifier-skill": ("athletics", "perception", "stealth"),
        "d100-percentile": ("perception", "investigation", "medicine"),
        "2d20": ("athletics", "survival", "technology"),
    }
    if mechanic in skill_defaults:
        skills = _ask_ids("Skills (comma-separated)", skill_defaults[mechanic])
        if skills is None:
            return None
    questions = {
        "d20-roll-under": [("default", "Starting attribute value", "12")],
        "d100-percentile": [("default", "Starting skill percentage", "50")],
        "dice-pool-successes": [("default", "Starting pool size", "3"), ("target", "Success result on d6", "6")],
        "dice-pool-count-hits": [("default", "Starting pool size", "6"), ("target", "Hit result on d6", "5")],
        "year-zero-d6-pool": [("default", "Starting attribute dice", "3"), ("target", "Success result on d6", "6")],
        "exploding-dice": [("sides", "Default die sides", "6"), ("threshold", "Explosion threshold", "6")],
        "step-dice": [("default", "Default step die sides", "6")],
        "cards": [("deck-size", "Number of cards in the deck", "52")],
        "custom": [("formula", "Roll formula", "1d20 + @sheet.resource")],
    }
    for key, label, default in questions.get(mechanic, []):
        value = _ask_text(label, default)
        if value is None:
            return None
        config.append((key, value))
    return attrs, skills, tuple(config)


def _configure_item(item_type: str, fields: list[str]) -> tuple[tuple[str, str], ...] | None:
    """Follow the conditional configuration tree for one selected item type."""
    if not _interactive():
        return ()
    config: list[tuple[str, str]] = []
    defaults = {
        "weight": "0", "cost": "0", "quantity": "1", "damage": "1d6",
        "attack-bonus": "0", "damage-type": "physical", "armor": "1",
        "level": "0", "effect": "",
    }
    labels = {
        "weight": "Starting weight", "cost": "Starting cost",
        "quantity": "Starting quantity", "damage": "Starting damage formula",
        "attack-bonus": "Starting attack bonus", "damage-type": "Default damage type",
        "armor": "Starting armor value", "level": "Starting level",
        "effect": "Default effect text",
    }
    for field_id in fields:
        if field_id in defaults:
            value = _ask_text(labels[field_id], defaults[field_id])
            if value is None:
                return None
            config.append((f"{field_id}.default", value))
        if field_id == "damage":
            roll = _choose(
                "Create an executable damage roll for this item type?",
                [("yes", "Yes - add a Roll damage action"), ("no", "No - store damage only")],
            )
            if roll is None:
                return None
            config.append(("damage.roll", roll))
        elif field_id == "equipped":
            equipped = _choose(
                "Should newly created items start equipped?",
                [("no", "No"), ("yes", "Yes")],
            )
            if equipped is None:
                return None
            config.append(("equipped.default", equipped))
    return tuple(config)


_DND_ATTRIBUTE_DEFAULTS = (
    "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma",
)


def _ask_authoring_mode() -> str | None:
    """The shared declarative-vs-HTML sheet authoring question."""
    return _choose(
        "How do you want to build the sheets?",
        [
            (
                "declarative",
                "Declarative (recommended to start) - configure fields without HTML/JavaScript",
            ),
            (
                "html",
                "HTML (full control) - customize markup, CSS and advanced behavior",
            ),
        ],
    )


def _run_ruleset(default_name: str | None) -> WizardResult | None:
    """Top-level ruleset wizard: offer a template or the from-scratch path."""
    _wizard_intro("ruleset")
    start = _choose(
        "How would you like to start your ruleset?",
        [
            (
                "template",
                "Start from a template - a ready-made system you can tweak (recommended)",
            ),
            (
                "scratch",
                "Build from scratch - answer a few quick questions",
            ),
        ],
    )
    if start is None:
        return None
    if start == "template":
        return _run_ruleset_from_template(default_name)
    return _run_ruleset_scratch(default_name)


def _run_ruleset_from_template(default_name: str | None) -> WizardResult | None:
    """Pick a ready-made template, choose an authoring mode, then confirm."""
    templates = templates_for_kind("ruleset")
    choice = _choose(
        "Which template fits your game best?",
        [(t.id, f"{t.label}  -  {t.tagline}") for t in templates],
    )
    if choice is None:
        return None
    template = get_template(choice)
    if template is None:  # pragma: no cover - choices come from the catalog
        return None

    mode = _ask_authoring_mode()
    if mode is None:
        return None

    name = default_name or _ask_text("Ruleset name", template.name_suggestion)
    if not name:
        return None

    intent = replace(template.intent, html_sheets=mode == "html")
    _clear_screen()
    _render_intent_summary(name, "ruleset", intent, template=template)
    return WizardResult(name=name, intent=intent)


def _run_ruleset_scratch(default_name: str | None) -> WizardResult | None:
    _wizard_step(1, 5, "Ruleset name")
    name = default_name or _ask_text("Ruleset name")
    if not name:
        return None
    print(f"  package id: {_slugify(name)}")

    _wizard_step(2, 5, "Core mechanic")
    mechanic = _choose(
        "Which core mechanic does the system use?",
        [(mid, f"{mid}  —  {MECHANICS[mid]['label']}") for mid in mechanic_ids()],
    )
    if mechanic is None:
        return None
    mechanic_setup = _configure_mechanic(mechanic)
    if mechanic_setup is None:
        return None
    mechanic_attributes, mechanic_skills, mechanic_config = mechanic_setup

    _wizard_step(3, 5, "Authoring mode")
    sheet_mode = _ask_authoring_mode()
    if sheet_mode is None:
        return None

    _wizard_step(4, 5, "Document types")
    actor_types = _select_types(
        "Which actor sheet types should this ruleset have?",
        ACTOR_SHEET_OPTIONS,
        preselected=["character"],
    )
    if actor_types is None:
        return None
    if not actor_types:
        actor_types = ["character"]
    actor_fields: list[tuple[str, tuple[str, ...]]] = []
    for actor_type in actor_types:
        selected = _checkbox(
            f"Which fields should {actor_type} have?",
            actor_field_options(actor_type),
            preselected=default_actor_field_ids(actor_type),
        )
        if selected is None:
            return None
        actor_fields.append((actor_type, tuple(selected)))

    item_types: list[str] = []
    item_fields: list[tuple[str, tuple[str, ...]]] = []
    item_config: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    create_items = _choose(
        "Create item sheet types?",
        [("no", "No"), ("yes", "Yes")],
    )
    if create_items is None:
        return None
    if create_items == "yes":
        chosen_items = _select_types(
            "Which item sheet types should this ruleset have?",
            ITEM_SHEET_OPTIONS,
            preselected=["item"],
        )
        if chosen_items is None:
            return None
        item_types = chosen_items
        for item_type in item_types:
            selected = _checkbox(
                f"Which fields should {item_type} have?",
                item_field_options(item_type),
                preselected=default_item_field_ids(item_type),
            )
            if selected is None:
                return None
            item_fields.append((item_type, tuple(selected)))
            configured = _configure_item(item_type, selected)
            if configured is None:
                return None
            item_config.append((item_type, configured))

    effects = _choose(
        "Include Active Effects?",
        [
            ("yes", "Yes - conditions, bonuses, penalties and periodic effects"),
            ("no", "No - omit the effect type and actor Effects tab"),
        ],
    )
    if effects is None:
        return None

    _wizard_step(5, 5, "Sheet sections")
    biography = _choose(
        "Create a Biography tab? (text-only fields)",
        [("no", "No"), ("yes", "Yes")],
        default=1,
    )
    if biography is None:
        return None

    notes = _choose(
        "Create a Notes tab? (text-only fields)",
        [("no", "No"), ("yes", "Yes")],
        default=1,
    )
    if notes is None:
        return None

    intent = Intent(
        has_sheets=True,
        actor_types=tuple(actor_types),
        actor_fields=tuple(actor_fields),
        item_types=tuple(item_types),
        item_fields=tuple(item_fields),
        item_config=tuple(item_config),
        mechanic=mechanic,
        mechanic_attributes=mechanic_attributes,
        mechanic_skills=mechanic_skills,
        mechanic_config=mechanic_config,
        wants_biography=biography == "yes",
        wants_notes=notes == "yes",
        wants_effects=effects == "yes",
        html_sheets=sheet_mode == "html",
    )
    _clear_screen()
    _render_intent_summary(name, "ruleset", intent)
    return WizardResult(name=name, intent=intent)


def _run_simple(kind: str, default_name: str | None) -> WizardResult | None:
    """Wizard for non-ruleset kinds (feature/asset checkboxes only)."""
    _wizard_intro(kind)
    name = default_name or _ask_text("Package name")
    if not name:
        return None
    print(f"  package id: {_slugify(name)}")

    fields: dict[str, bool] = {}

    if kind == "assets":
        cats = _checkbox(
            "Which asset categories?",
            [
                ("images", "images"),
                ("maps", "maps"),
                ("audio", "audio"),
                ("icons", "icons"),
            ],
            preselected=["images"],
        )
        if cats is None:
            return None
        fields = {
            "has_images": "images" in cats,
            "has_maps": "maps" in cats,
            "has_audio": "audio" in cats,
            "has_icons": "icons" in cats,
        }
        locales = _checkbox("Include:", [("locales", "translations")])
        if locales is None:
            return None
        fields["wants_locales"] = "locales" in locales
    elif kind == "addon":
        feats = _checkbox(
            "What does the addon do?",
            [
                ("js", "JavaScript (in-game UI/logic)"),
                ("sheet_runtime", "Extend sheets at runtime"),
                ("combat_runtime", "Combat logic"),
                ("scene_tools", "Scene tools"),
                ("scene_overlays", "Scene overlays"),
                ("tokens", "Extend tokens"),
                ("content", "Content (compendiums)"),
                ("settings", "Settings"),
                ("locales", "Translations"),
            ],
        )
        if feats is None:
            return None
        fields = {
            "uses_js": "js" in feats,
            "uses_sheet_runtime": "sheet_runtime" in feats,
            "uses_combat_runtime": "combat_runtime" in feats,
            "uses_scene_tools": "scene_tools" in feats,
            "uses_scene_overlays": "scene_overlays" in feats,
            "uses_token_extensions": "tokens" in feats,
            "wants_content": "content" in feats,
            "wants_settings": "settings" in feats,
            "wants_locales": "locales" in feats,
        }
    else:  # theme, library, content
        feats = _checkbox(
            "Include:",
            [
                ("js", "JavaScript"),
                ("settings", "Settings"),
                ("locales", "Translations"),
            ],
        )
        if feats is None:
            return None
        fields = {
            "uses_js": "js" in feats,
            "wants_settings": "settings" in feats,
            "wants_locales": "locales" in feats,
        }

    return WizardResult(name=name, intent=Intent(**fields))


def run_new_wizard(kind: str, *, default_name: str | None = None) -> WizardResult | None:
    """Drive the guided wizard for ``kind``; ``None`` means the user cancelled."""
    try:
        if kind == "ruleset":
            return _run_ruleset(default_name)
        return _run_simple(kind, default_name)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        return None
