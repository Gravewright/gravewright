"""Toda mutação em /game que muda estado compartilhado precisa avisar a sala.

O GM mexia em algo, via mudar na própria tela, e os jogadores continuavam com o
estado antigo até recarregar a página. O silêncio era invisível: nada acusava.

Este teste percorre os handlers ``@post`` de ``app/actions/game`` e resolve, de
forma transitiva, se cada um alcança o transporte — direto ou por um helper. O
que for silencioso de propósito precisa estar listado abaixo com o motivo, então
uma rota nova nasce acusada e a decisão fica escrita.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIONS = ROOT / "app/actions/game"

_TRANSPORT = re.compile(r"transport|to_room|to_user|broadcast|announce|emit|notify", re.I)

# rota -> por que não anuncia
DELIBERATELY_SILENT = {
    "/campaigns/invitations": "o convidado ainda não está na sala",
    "/game/onboarding/preference": "preferência por usuário",
    "/game/preferences/layout": "preferência por usuário",
    "/game/preferences/vision": "preferência por usuário; só muda como a tela é pintada",
    "/game/streamer-link": "painel só do GM",
    "/game/streamer-link/revoke": "painel só do GM",
    "/game/scenes/group": "organização do gerenciador de cenas, só o GM vê",
    "/game/cards/assets/upload": "asset solto; o baralho anuncia ao ser usado",
    "/game/journal/asset": "asset solto; o diário anuncia ao ser aberto",
    "/game/scenes/start-point": "afeta o enquadramento inicial de quem ainda vai entrar",
    "/campaigns/permissions": (
        "a interface do jogador é renderizada no servidor pelas permissões; "
        "aplicar em tempo real exigiria recarregar a página dele"
    ),
}


def _names_used(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            found.add(func.id if isinstance(func, ast.Name) else getattr(func, "attr", ""))
        elif isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
    return found


def _silent_post_routes() -> list[tuple[str, str]]:
    silent: list[tuple[str, str]] = []
    for path in sorted(ACTIONS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        used = {name: _names_used(node) for name, node in functions.items()}

        def reaches_transport(name: str, seen: set[str] | None = None) -> bool:
            seen = seen or set()
            if name in seen:
                return False
            seen.add(name)
            return any(
                _TRANSPORT.search(other) or (other in functions and reaches_transport(other, seen))
                for other in used.get(name, ())
            )

        for name, node in functions.items():
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if getattr(decorator.func, "id", "") != "post" or not decorator.args:
                    continue
                route = getattr(decorator.args[0], "value", "")
                if route and not reaches_transport(name):
                    silent.append((route, path.name))
    return silent


def test_every_shared_state_route_reaches_the_room():
    silent = _silent_post_routes()
    undocumented = [f"{route}  ({module})" for route, module in silent
                    if route not in DELIBERATELY_SILENT]

    assert not undocumented, (
        "rotas que mudam estado sem avisar a sala — emita um evento ou registre o "
        "motivo em DELIBERATELY_SILENT: " + str(undocumented)
    )


def test_the_silent_list_has_no_leftovers():
    """Uma rota que passou a anunciar não pode continuar na lista de exceções."""
    silent_routes = {route for route, _module in _silent_post_routes()}
    stale = sorted(set(DELIBERATELY_SILENT) - silent_routes)
    assert not stale, f"já anunciam, remova de DELIBERATELY_SILENT: {stale}"
