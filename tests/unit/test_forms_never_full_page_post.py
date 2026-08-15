"""Nenhuma mutação em /game ou /inside pode recarregar a página.

O usuário mexe num controle e a página inteira recarrega: perde rolagem, perde
modais abertos, perde estado de painel. Todo POST tem de ser interceptado por
JavaScript.

Este teste casa cada ``<form method="post">`` dos templates contra os seletores
realmente registrados nos ``addEventListener("submit", ...)`` do JS, para que um
formulário novo sem dono seja acusado na hora de escrevê-lo, e não em produção.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Formulários que navegam de propósito, com o motivo.
DELIBERATE_NAVIGATION = {
    "/logout": "encerrar sessão é navegação real",
}


def _submit_selectors() -> tuple[set[str], set[str], bool]:
    """Atributos e classes interceptados, e se existe um handler genérico."""
    attrs: set[str] = set()
    classes: set[str] = set()
    generic = False

    for path in (ROOT / "static/js").rglob("*.js"):
        source = path.read_text(encoding="utf-8")
        for block in re.split(r'addEventListener\(\s*"submit"', source)[1:]:
            head = block[:400]
            for selector in re.findall(r'closest\(\s*"([^"]+)"', head):
                if selector.strip() == "form":
                    generic = True
                    continue
                attrs.update(re.findall(r"\[([a-z-]+)\]", selector))
                classes.update(re.findall(r"\.([a-zA-Z0-9_-]+)", selector))
            # shouldHandleForm/matches também definem cobertura
            for selector in re.findall(r'matches\(\s*"([^"]+)"', head):
                attrs.update(re.findall(r"\[([a-z-]+)\]", selector))
                classes.update(re.findall(r"\.([a-zA-Z0-9_-]+)", selector))

        # Nem todo dono usa delegação: alguns módulos resolvem o elemento por
        # querySelector e ligam o submit nele direto (ex.: inside-join-code.js).
        if re.search(r"\bform\??\.addEventListener\(\s*\"submit\"", source):
            for selector in re.findall(r'querySelector\(\s*"\[([a-z-]+)\]"', source):
                attrs.add(selector)
    return attrs, classes, generic


def _post_forms(page: str):
    root = ROOT / "templates/pages" / page
    for path in sorted(root.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"<form\b[^>]*>", text, re.S):
            tag = " ".join(match.group(0).split())
            if 'method="post"' not in tag.lower():
                continue
            line = text[: match.start()].count("\n") + 1
            action = (re.search(r'action="([^"]+)"', tag) or [None, ""])[1]
            yield f"{path.relative_to(root)}:{line}", action, tag


def test_every_game_form_is_intercepted_by_javascript():
    """/game não tem handler genérico: cada formulário precisa do seu."""
    attrs, classes, _ = _submit_selectors()
    orphans = []

    for where, action, tag in _post_forms("game"):
        if action in DELIBERATE_NAVIGATION:
            continue
        covered = any(a in tag for a in attrs) or any(
            re.search(rf'class="[^"]*\b{re.escape(c)}\b', tag) for c in classes
        )
        if not covered:
            orphans.append(f"{where} -> {action}")

    assert not orphans, (
        "formulários de /game sem interceptador de submit (dariam refresh): " + str(orphans)
    )


def test_inside_relies_on_its_generic_handler_and_names_every_exception():
    """/inside intercepta qualquer POST; os opt-outs precisam ter dono."""
    attrs, classes, generic = _submit_selectors()
    assert generic, "inside-ajax.js perdeu o handler genérico de formulário"

    source = (ROOT / "static/js/inside/inside-ajax.js").read_text(encoding="utf-8")
    guard = source.split("function shouldHandleForm", 1)[1].split("}", 1)[0]
    opted_out = set(re.findall(r"\.([a-zA-Z0-9_-]+-form)", guard))
    assert opted_out, "o guard deixou de nomear exceções"

    # cada opt-out tem de ser tratado por outro handler: por delegação (classe)
    # ou por um listener ligado direto no elemento (atributo data-*)
    inside_forms = {
        tag: where
        for where, _action, tag in _post_forms("inside")
    }
    unowned = []
    for opted in sorted(opted_out):
        if opted in classes:
            continue
        tag = next((t for t in inside_forms if re.search(rf'\b{re.escape(opted)}\b', t)), None)
        if tag and any(a in tag for a in attrs):
            continue
        unowned.append(opted)
    assert not unowned, f"opt-outs de /inside sem dono: {unowned}"

    assert "/logout" in guard, "sair da sessão continua sendo navegação real"


def test_the_ruleset_selector_answers_json():
    """Era o último POST tradicional do /game: trocar o sistema recarregava a
    página e devolvia a mensagem por query string."""
    route = (ROOT / "app/actions/sdk/campaign_packages.py").read_text(encoding="utf-8")
    handler = route.split('@post("/sdk/campaigns/ruleset"', 1)[1].split("@get", 1)[0]
    assert 'wants_json = "application/json" in request.headers.get("accept", "")' in handler
    assert '{"ok": True' in handler and '{"ok": False' in handler
    assert "Redirect(" in handler, "quem chega sem JavaScript ainda precisa do redirect"

    script = (ROOT / "static/js/game/system-ruleset-form.js").read_text(encoding="utf-8")
    assert 'closest(".system-inline-form")' in script and "event.preventDefault()" in script
    assert "window.location.reload()" in script, (
        "trocar o ruleset troca o sistema de fichas: o markup já renderizado fica velho"
    )
