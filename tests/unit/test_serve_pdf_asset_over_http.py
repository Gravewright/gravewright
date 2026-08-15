"""Servir um PDF da biblioteca precisa funcionar pela HTTP de verdade.

Toda a cadeia foi testada em pedaços: upload valida, o banco guarda, o serviço de
leitura resolve o caminho, e mesmo assim a ficha não abria o arquivo. O pedaço
que ninguém exercitava era o último: a resposta HTTP em si, com os cabeçalhos que
o navegador realmente recebe.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from litestar.testing import TestClient

from main import app
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user

ROOT = Path(__file__).resolve().parents[2]
PDF_BYTES = (ROOT / "data/packages/rulesets/gravewright-pdf-system/assets/sheets/blank-a4.pdf").read_bytes()


@pytest.fixture
def client():
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as test_client:
        yield test_client


def _upload_pdf(client, campaign_id: str, name: str = "ficha.pdf"):
    return client.post(
        "/game/assets/upload",
        data={"campaign_id": campaign_id},
        files={"file": (name, PDF_BYTES, "application/pdf")},
    )


def test_uploading_and_serving_a_pdf_round_trips(client):
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    login(client, gm)

    upload = _upload_pdf(client, campaign_id)
    assert upload.status_code == 201, upload.text

    asset = upload.json()["asset"]
    assert asset["kind"] == "pdf"
    assert asset["content_type"] == "application/pdf"

    served = client.get(asset["src"])
    assert served.status_code == 200, served.text
    assert served.headers["content-type"].startswith("application/pdf")
    # O byte-a-byte é o que prova que o arquivo chega inteiro ao renderizador.
    assert served.content == PDF_BYTES


def test_the_pdf_is_served_as_an_attachment_but_still_readable(client):
    """Inline abriria o visualizador nativo do navegador, que executa o JavaScript
    embutido no PDF. Como anexo, `fetch` continua lendo os bytes: que é como o
    pdf.js trabalha."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    login(client, gm)

    src = _upload_pdf(client, campaign_id).json()["asset"]["src"]
    served = client.get(src)

    assert served.status_code == 200
    assert "attachment" in served.headers.get("content-disposition", "")
    assert len(served.content) == len(PDF_BYTES)


def test_an_image_is_still_served_inline(client):
    """A troca para anexo não pode valer para imagem: a cena usa <img src>, que
    não carrega um anexo."""
    from io import BytesIO

    from PIL import Image

    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    login(client, gm)

    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")

    upload = client.post(
        "/game/assets/upload",
        data={"campaign_id": campaign_id},
        files={"file": ("mapa.png", buffer.getvalue(), "image/png")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["asset"]["kind"] == "image"

    served = client.get(upload.json()["asset"]["src"])
    assert served.status_code == 200
    assert "inline" in served.headers.get("content-disposition", "")


def test_the_library_state_lists_the_uploaded_pdf(client):
    """É desta lista que o seletor da ficha se alimenta."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    login(client, gm)

    _upload_pdf(client, campaign_id, name="savage-worlds.pdf")

    state = client.get(f"/game/assets/state/{campaign_id}")
    assert state.status_code == 200, state.text

    pdfs = [asset for asset in state.json()["assets"] if asset["kind"] == "pdf"]
    assert len(pdfs) == 1
    assert pdfs[0]["filename"].endswith(".pdf")
    assert pdfs[0]["src"].startswith("/game/assets/file/")


def test_a_stranger_cannot_read_the_pdf(client):
    """O arquivo é da campanha; a rota decide por papel, não por posse da URL."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    login(client, gm)
    src = _upload_pdf(client, campaign_id).json()["asset"]["src"]

    outsider = seed_user(name="Outsider")
    login(client, outsider)

    denied = client.get(src)
    assert denied.status_code in (403, 404), denied.status_code
