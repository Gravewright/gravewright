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
from dataclasses import dataclass

from app.cli.scaffold import MECHANICS, Intent, _slugify, mechanic_ids

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


def _run_ruleset(default_name: str | None) -> WizardResult | None:
    _wizard_step(1, 5, "Ruleset name")
    name = default_name or _ask_text("Ruleset name")
    if not name:
        return None
    print(f"  package id: {_slugify(name)}")

    _wizard_step(2, 5, "Authoring mode")
    sheet_mode = _choose(
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
    if sheet_mode is None:
        return None

    _wizard_step(3, 5, "Document types")
    actor_types = _select_types(
        "Which actor sheet types should this ruleset have?",
        ACTOR_SHEET_OPTIONS,
        preselected=["character"],
    )
    if actor_types is None:
        return None
    if not actor_types:
        actor_types = ["character"]

    item_types: list[str] = []
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

    effects = _choose(
        "Include Active Effects?",
        [
            ("yes", "Yes - conditions, bonuses, penalties and periodic effects"),
            ("no", "No - omit the effect type and actor Effects tab"),
        ],
    )
    if effects is None:
        return None

    _wizard_step(4, 5, "Core mechanic")
    mechanic = _choose(
        "Which core mechanic does the system use?",
        [(mid, f"{mid}  —  {MECHANICS[mid]['label']}") for mid in mechanic_ids()],
    )
    if mechanic is None:
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
        item_types=tuple(item_types),
        mechanic=mechanic,
        wants_biography=biography == "yes",
        wants_notes=notes == "yes",
        wants_effects=effects == "yes",
        html_sheets=sheet_mode == "html",
    )
    _clear_screen()
    return WizardResult(name=name, intent=intent)


def _run_simple(kind: str, default_name: str | None) -> WizardResult | None:
    """Wizard for non-ruleset kinds (feature/asset checkboxes only)."""
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
