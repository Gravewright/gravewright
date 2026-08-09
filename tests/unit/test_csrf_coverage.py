"""Nenhum caminho de escrita pode chegar ao servidor sem prova de CSRF.

O Litestar aceita o token por dois caminhos, e só por esses dois:

  1. o cabeçalho ``x-csrftoken``;
  2. o campo de formulário ``_csrf_token`` — e apenas quando o corpo é
     ``application/x-www-form-urlencoded`` ou ``multipart/form-data``.

Repare no underscore: ``csrf_token`` (sem ele) não é lido por ninguém. O projeto
manda esse nome no corpo JSON de 26 chamadas, o que **não protege nada** — quem
protege ali é o cabeçalho, posto pelo wrapper global de ``window.fetch``.

O modo de falha é ruim: 403 em produção, silencioso em desenvolvimento (onde tudo
já está carregado e autenticado). Por isso as invariantes ficam aqui.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
JS = ROOT / "static/js"
WRAPPER = JS / "csrf.js"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _forms(html: str):
    """Cada <form ...> com o seu corpo, respeitando aninhamento."""
    for match in re.finditer(r"<form\b[^>]*>", html, re.I):
        depth, i = 1, match.end()
        while depth and i < len(html):
            opens = html.find("<form", i)
            closes = html.find("</form", i)
            if closes == -1:
                break
            if opens != -1 and opens < closes:
                depth += 1
                i = opens + 5
            else:
                depth -= 1
                i = closes + 6
        yield match.group(0), html[match.start() : i]


def test_every_post_form_carries_the_token_field():
    """``csrf_input`` do Litestar gera ``name="_csrf_token"``. Um formulário sem
    ele volta 403 — no envio nativo e também quando o JS manda ``new
    FormData(form)``, que é como os uploads deste projeto funcionam."""
    missing: list[str] = []
    total = 0

    for template in sorted(TEMPLATES.rglob("*.html")):
        html = template.read_text(encoding="utf-8", errors="ignore")
        for tag, body in _forms(html):
            if not re.search(r'method=["\']post["\']', tag, re.I):
                continue
            total += 1
            if "csrf_input" not in body:
                missing.append(f"{template.relative_to(ROOT)}: {tag.strip()[:80]}")

    assert total > 20, f"o teste precisa achar formulários, achou {total}"
    assert not missing, "formulários POST sem csrf_input:\n  " + "\n  ".join(missing)


def test_the_global_fetch_wrapper_covers_unsafe_same_origin_requests():
    """É ele que protege as dezenas de fetch espalhados pelo projeto — nenhum
    deles põe o cabeçalho por conta própria."""
    source = WRAPPER.read_text(encoding="utf-8")

    assert "window.fetch = function" in source, "sem o wrapper, cada chamada teria de lembrar"
    assert '"GET", "HEAD", "OPTIONS", "TRACE"' in source, "métodos seguros não levam token"
    assert 'headers.set("x-csrftoken"' in source
    assert "isCrossOrigin" in source, "mandar o token para outra origem é vazamento"
    assert 'credentials = "same-origin"' in source


def test_a_page_that_writes_also_loads_the_wrapper():
    """Página que faz requisição de escrita sem carregar csrf.js dá 403 em tudo."""
    for template in sorted(TEMPLATES.rglob("*.html")):
        html = template.read_text(encoding="utf-8", errors="ignore")
        scripts = [s.split("?")[0] for s in re.findall(r'<script[^>]*src="([^"]+)"', html)]
        if not scripts:
            continue

        own = [s for s in scripts if s.startswith("/static/js/")]
        if not own:
            continue  # só vendor (o fundo animado das telas de login)

        if "/static/js/csrf.js" not in scripts:
            # Sem o wrapper, os scripts da página não podem escrever.
            for script in own:
                path = ROOT / script.lstrip("/")
                if not path.is_file():
                    continue
                code = path.read_text(encoding="utf-8", errors="ignore")
                assert 'method: "POST"' not in code and "method: 'POST'" not in code, (
                    f"{template.relative_to(ROOT)} escreve em {script} sem carregar csrf.js"
                )
            continue

        # Com o wrapper, ele precisa vir ANTES de quem usa fetch: script defer roda
        # na ordem do documento, então basta ser o primeiro dos nossos.
        assert scripts.index("/static/js/csrf.js") == 0, (
            f"{template.relative_to(ROOT)}: csrf.js precisa ser o primeiro script"
        )


def test_requests_that_bypass_fetch_carry_the_token_themselves():
    """``sendBeacon`` não aceita cabeçalho, e ``XMLHttpRequest`` não passa pelo
    wrapper. Quem usa um desses tem de mandar ``_csrf_token`` no corpo."""
    for path in sorted(JS.rglob("*.js")):
        source = path.read_text(encoding="utf-8", errors="ignore")

        if "sendBeacon(" in source:
            assert "_csrf_token" in source, (
                f"{path.relative_to(ROOT)}: sendBeacon não põe cabeçalho; "
                "o corpo precisa ser url-encoded com _csrf_token"
            )
            assert "application/x-www-form-urlencoded" in source, (
                f"{path.relative_to(ROOT)}: o Litestar só lê o campo em corpo de formulário"
            )

        # ``.open(`` sozinho casa com indexedDB.open e afins; o que interessa é o
        # XHR, que é o único que escapa do wrapper de fetch.
        if "new XMLHttpRequest" not in source:
            continue

        for method in re.findall(r"\.open\(\s*([^,]+),", source):
            literal = method.strip().strip("\"'").upper()
            if literal in SAFE_METHODS:
                continue
            # método dinâmico ou de escrita: precisa do cabeçalho, ou de um corpo
            # de formulário que já traga o campo escondido.
            ok = re.search(r'setRequestHeader\(\s*["\']x-csrftoken', source, re.I) or (
                "new FormData(" in source
            )
            assert ok, f"{path.relative_to(ROOT)}: XHR de escrita sem prova de CSRF"


def test_the_json_body_token_is_not_what_protects_these_routes():
    """26 chamadas mandam ``csrf_token`` no corpo JSON e nenhum handler lê. Não é
    bug — mas quem for mexer não pode concluir que é dali que vem a proteção, e
    remover o cabeçalho achando que o corpo cobre."""
    read_on_server = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        code = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'(get|\[)\(?["\']csrf_token["\']', code):
            read_on_server.append(str(path.relative_to(ROOT)))

    assert not read_on_server, (
        "algum handler passou a ler csrf_token do corpo; se isso virar a proteção, "
        f"ela precisa valer para TODAS as rotas, não só estas: {read_on_server}"
    )


def test_the_roll_expression_cannot_escape_the_evaluator():
    """O xdice compila a expressão e passa por ``eval`` com ``__builtins__``
    zerado — o que, sozinho, não é fronteira de segurança em Python. O que
    segura de fato é o parser na frente (acesso a atributo não compila) mais o
    teto de comprimento. Se algum dos dois cair, isto avisa."""
    from app.engine.dice.roll_service import RollService

    roller = RollService()
    for payload in (
        "().__class__",
        "(1).__class__.__mro__[1]",
        "max.__self__",
        "[].__class__.__base__.__subclasses__()",
    ):
        assert roller.evaluate(payload) is None, f"expressão perigosa avaliada: {payload}"

    assert roller.evaluate("1d20+5") is not None, "o caminho legítimo continua valendo"
    assert RollService.MAX_EXPRESSION_LEN <= 120, "o teto limita a superfície do eval"
    assert roller.evaluate("1" + "+1" * 100) is None, "expressão longa é recusada"
