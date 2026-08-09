"""Método do SDK devolve o dado, não o envelope do transporte.

``GravewrightCore.http`` responde ``{ok, status, data}``. Nenhum método do SDK
promete isso — a documentação fala em "packs", "rows", "assets". Quando um método
esquece de desembrulhar, o erro nunca aparece: ler o campo errado devolve
``undefined``, que vira lista vazia ou condição falsa. Foi assim duas vezes:

- ``sdk.assets.list`` lia ``state.assets`` do envelope e devolvia ``[]`` sempre —
  a biblioteca da campanha parecia vazia, sem erro nenhum;
- ``sdk.settings.set`` lia ``result.success`` do envelope, então nunca atualizava
  o valor em memória e ``settings.get`` devolvia o antigo até recarregar a página.

Por isso o desembrulho mora num helper só. Este teste guarda essa regra.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "static/js/sdk/gravewright-sdk.js"
DOCS = ROOT / "docs/sdk/reference.md"


def _source() -> str:
    return SDK.read_text(encoding="utf-8")


def test_no_method_returns_the_raw_transport_envelope():
    source = _source()
    raw = re.findall(r"return\s+client\?\.(?:getJson|postJson)\?\.\(", source)
    assert not raw, (
        f"{len(raw)} método(s) devolvem o envelope {{ok,status,data}} direto ao pacote; "
        "passe por unwrap()"
    )


def test_the_unwrap_helper_turns_failure_into_an_exception():
    """Devolver `undefined` num erro é o que torna esta família de bugs invisível."""
    source = _source()
    helper = source.split("async function unwrap(", 1)[1].split("\n    }", 1)[0]

    assert "if (!result?.ok)" in helper
    assert "throw new Error(" in helper, "falha silenciosa vira lista vazia"
    assert "return result.data" in helper


def test_every_http_backed_method_goes_through_unwrap():
    """Um método novo que chame client.getJson/postJson sem unwrap reintroduz o bug."""
    source = _source()
    body = source.split("function buildScopedSdk(pkg)", 1)[1]

    calls = [m.start() for m in re.finditer(r"client\.(?:getJson|postJson)\(", body)]
    assert calls, "o teste precisa achar chamadas, senão não guarda nada"

    for at in calls:
        # unwrap( abre a chamada; procuramos para trás dentro da mesma expressão
        window = body[max(0, at - 220) : at]
        assert "unwrap(" in window, (
            "chamada HTTP fora do unwrap:\n" + body[max(0, at - 220) : at + 80]
        )


def test_assets_list_returns_an_array_of_assets():
    source = _source()
    listing = source.split("async list(options = {})", 1)[1].split("},", 1)[0]

    assert 'unwrap(' in listing and '"sdk.assets.list"' in listing
    assert "Array.isArray(state?.assets)" in listing, "o corpo é {campaign_id, folders, assets}"
    assert "asset.kind === options.kind" in listing, "o filtro por tipo é o que a ficha usa"

    # Campanha ausente tem de doer, não devolver lista vazia como se não houvesse
    # nada enviado.
    assert "throw new Error" in listing


def test_settings_set_updates_the_cached_value_from_the_body():
    source = _source()
    setter = source.split("async set(key, value, options = {})", 1)[1].split("\n                },", 1)[0]

    assert '"sdk.settings.set"' in setter, "passa pelo mesmo desembrulho dos outros"
    assert "body?.success" in setter and "body.value" in setter, "success/value vivem no corpo"

    # Sem tirar comentários, a própria explicação do bug (que cita o campo errado)
    # dispararia o assert.
    code = re.sub(r"//.*", "", setter)
    assert "result.success" not in code, "esse campo não existe no envelope"


def test_the_docs_promise_data_not_an_envelope():
    """Se a documentação mudasse para descrever o envelope, este teste avisaria
    que a decisão foi revertida em vez de deixar as duas versões conviverem."""
    docs = DOCS.read_text(encoding="utf-8")
    for snippet in (
        "const packs = await sdk.content.packs();",
        "const rows = await sdk.storage.sqlite.query(",
        "const sheets = await sdk.assets.list(",
    ):
        assert snippet in docs, f"documentação não promete mais o dado: {snippet}"
