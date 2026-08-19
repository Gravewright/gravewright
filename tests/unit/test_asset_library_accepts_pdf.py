"""A biblioteca de assets aceita PDF, e só PDF de verdade.

Fichas em PDF entram pela mesma biblioteca das imagens: é onde o GM já procura
arquivo. Mas o caminho de validação é outro: não há nada para o Pillow decodificar,
então a única prova de que o arquivo é um PDF é a assinatura no começo dele. Sem
essa checagem, qualquer arquivo renomeado para `.pdf` entraria na biblioteca e
sairia servido como `application/pdf`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.assets.asset_library_service import ALLOWED_CONTENT_TYPES
from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.assets.asset_library_service import PDF_CONTENT_TYPE
from app.infrastructure.storage.local_asset_storage import SAFE_EXTENSIONS

ROOT = Path(__file__).resolve().parents[2]
VALID_PDF = (ROOT / "data/packages/rulesets/gravewright-pdf-system/assets/sheets/blank-a4.pdf").read_bytes()


class _StubAssets:
    def __init__(self) -> None:
        self.created: list[dict] = []

    def create(self, **kwargs):
        row = {"id": f"asset-{len(self.created)}", **kwargs}
        self.created.append(row)
        return row

    def update_storage_path(self, *, asset_id: str, storage_path: str) -> None:
        for row in self.created:
            if row["id"] == asset_id:
                row["storage_path"] = storage_path


class _StubStorage:
    def __init__(self) -> None:
        self.written: list[str] = []

    def write_image(self, *, campaign_id, asset_id, filename, data):
        # Espelha a barreira real: extensão fora da lista nunca chega ao disco.
        extension = Path(filename).suffix.lower()
        if extension not in SAFE_EXTENSIONS:
            raise ValueError("filename extension is invalid")
        path = f"data/assets/{campaign_id}/{asset_id}{extension}"
        self.written.append(path)
        return path


@pytest.fixture
def service() -> AssetLibraryService:
    return AssetLibraryService(assets=_StubAssets(), storage=_StubStorage())


def test_a_real_pdf_is_stored_without_going_through_the_image_decoder(service):
    result = service.create_asset(
        campaign_id="c1",
        user_id="u1",
        filename="ficha.pdf",
        content_type=PDF_CONTENT_TYPE,
        data=VALID_PDF,
    )

    assert result.success, result.error_key
    asset = result.payload["asset"]
    assert asset["content_type"] == PDF_CONTENT_TYPE
    # PDF não tem dimensão em pixels; as colunas são anuláveis justamente por isso.
    assert asset["width"] is None and asset["height"] is None
    assert asset["storage_path"].endswith(".pdf")
    # decoded fica None: quem monta camada de cena precisa saber que não há
    # dimensão, em vez de receber um objeto pela metade.
    assert result.payload["decoded"] is None


def test_a_renamed_file_is_refused_even_with_the_right_content_type(service):
    result = service.create_asset(
        campaign_id="c1",
        user_id="u1",
        filename="malicioso.pdf",
        content_type=PDF_CONTENT_TYPE,
        data=b"MZ\x90\x00 isto e um executavel",
    )

    assert not result.success
    assert result.error_key == "game.assets.errors.unsupported_type"


def test_the_pdf_extension_alone_is_not_enough(service):
    """Content-type e extensão vêm do navegador. Combinar os dois ainda é palavra
    do cliente: por isso a assinatura é conferida sempre."""
    result = service.create_asset(
        campaign_id="c1",
        user_id="u1",
        filename="ficha.pdf",
        content_type="image/png",
        data=VALID_PDF,
    )
    assert not result.success


def test_images_still_go_through_the_decoder(service):
    """O caminho novo não pode afrouxar o antigo: PNG inválido continua recusado."""
    result = service.create_asset(
        campaign_id="c1",
        user_id="u1",
        filename="mapa.png",
        content_type="image/png",
        data=b"nao sou um png",
    )
    assert not result.success
    assert result.error_key == "game.assets.errors.invalid_image"


def test_pdf_is_not_in_the_image_content_types():
    """Se PDF entrasse em ALLOWED_CONTENT_TYPES, cairia no ramo das imagens e
    seria rejeitado pelo decodificador: silenciosamente, como 'imagem inválida'."""
    assert PDF_CONTENT_TYPE not in ALLOWED_CONTENT_TYPES


def test_a_pdf_is_presented_with_its_kind(service):
    created = service.create_asset(
        campaign_id="c1",
        user_id="u1",
        filename="ficha.pdf",
        content_type=PDF_CONTENT_TYPE,
        data=VALID_PDF,
    )
    presented = service._present_asset(created.payload["asset"])

    assert presented["kind"] == "pdf", "o cliente filtra por kind, não por content_type"
    assert presented["src"].startswith("/game/assets/file/")


def test_storage_refuses_extensions_outside_the_safe_list():
    """A lista de extensões graváveis é a última barreira antes do arquivo existir."""
    assert ".pdf" in SAFE_EXTENSIONS
    for dangerous in (".exe", ".js", ".html", ".svg", ".php"):
        assert dangerous not in SAFE_EXTENSIONS, dangerous


def test_a_pdf_cannot_become_a_scene_image():
    """A camada de cena precisa de largura e altura. Sem guarda, o asset seria
    criado e só então faltaria o decoded: linha órfã no banco mais um 500."""
    from app.engine.scenes.scene_image_service import SceneImageService

    source = Path(ROOT / "app/engine/scenes/scene_image_service.py").read_text(encoding="utf-8")
    guard = source.split("def upload", 1)[1].split("create_asset", 1)[0]
    assert 'content_type.startswith("image/")' in guard, (
        "a guarda precisa vir antes de criar o asset"
    )
    assert SceneImageService is not None


def test_image_and_pdf_have_separate_upload_buttons():
    """Um diálogo só, aceitando imagem e ficha ao mesmo tempo, faz o GM caçar um
    PDF no meio de uma lista de imagens, e esconde que dá para enviar ficha."""
    import re

    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    strip = template.split("asset-bar__uploads", 1)[1].split("</header>", 1)[0]

    kinds = set(re.findall(r'data-scene-asset-upload="([\w-]+)"', strip))
    assert kinds == {"image", "ambient-audio", "effect-audio", "pdf"}, (
        f"botões de upload encontrados: {sorted(kinds)}"
    )

    inputs = re.findall(
        r'accept="([^"]+)"[^>]*data-scene-asset-upload-input="([\w-]+)"', strip
    )
    assert inputs, "cada botão precisa do seu próprio seletor de arquivo"
    accepts = {kind: value for value, kind in inputs}
    assert "application/pdf" not in accepts["image"], "o seletor de imagem não pode listar PDF"
    assert accepts["ambient-audio"] == accepts["effect-audio"]
    assert accepts["ambient-audio"].startswith("audio/"), (
        "os fluxos artísticos devem aceitar o mesmo tipo físico de asset de áudio"
    )
    assert accepts["pdf"] == "application/pdf", "o seletor de ficha só aceita PDF"

    # O handler precisa escolher o input pelo tipo; sem isso os dois botões abrem
    # o mesmo diálogo e a separação é só visual.
    script = (ROOT / "static/js/assets/asset-library.js").read_text(encoding="utf-8")
    assert 'data-scene-asset-upload-input="${kind}"' in script


def test_the_library_still_accepts_both_kinds_after_the_split():
    """Separar os botões não pode fechar a porta do outro lado: o upload em si
    continua aceitando os dois, inclusive por arrastar-e-soltar."""
    script = (ROOT / "static/js/assets/asset-library.js").read_text(encoding="utf-8")
    accepted = script.split("async uploadFiles", 1)[1].split("}", 1)[0]
    assert "IMAGE_MIME_PREFIX" in accepted and "PDF_MIME" in accepted


def test_the_route_body_limit_is_above_the_pdf_cap():
    """O Litestar corta o corpo antes de qualquer handler rodar. Se o limite da
    rota ficar abaixo do nosso teto, o cliente recebe 413 sem chave de erro: a
    validação nunca chega a dizer 'grande demais'. O padrão do Litestar (10 MB
    decimais) é mais baixo até que MAX_ASSET_BYTES (10 MiB), então a faixa entre
    os dois já falhava assim antes de existir PDF."""
    import main
    from app.engine.assets.asset_library_service import MAX_ASSET_BYTES, MAX_PDF_BYTES

    limits = [
        handler.request_max_body_size
        for route in main.app.routes
        if route.path == "/game/assets/upload"
        for handler in route.route_handlers
        if isinstance(getattr(handler, "request_max_body_size", None), int)
    ]
    assert limits, "a rota de upload precisa declarar o próprio limite de corpo"
    assert max(limits) > MAX_PDF_BYTES, "sem folga, o multipart estoura antes do arquivo"
    assert MAX_PDF_BYTES > MAX_ASSET_BYTES, "ficha em PDF é maior que imagem de cena"


def test_the_client_refuses_oversized_files_before_uploading():
    """Mandar 30 MB pela rede para receber 413 no fim é esperar à toa."""
    script = (ROOT / "static/js/assets/asset-library.js").read_text(encoding="utf-8")
    assert "MAX_PDF_BYTES = 25 * 1024 * 1024" in script
    assert "MAX_IMAGE_BYTES = 10 * 1024 * 1024" in script
    assert "file.size > cap" in script


def test_upload_failures_are_never_silent():
    """``.catch(() => {})`` fazia o arquivo simplesmente não aparecer, com o
    motivo só no console."""
    script = (ROOT / "static/js/assets/asset-library.js").read_text(encoding="utf-8")
    body = script.split("async uploadFiles", 1)[1].split("await this.refresh()", 1)[0]

    assert ".catch(() => {})" not in body, "erro de upload não pode ser engolido"
    assert "reportUploadFailure" in body

    # 413 não traz corpo JSON: sem o status, a mensagem viraria um genérico
    upload = script.split("async upload(roomId", 1)[1].split("return data;", 1)[0]
    assert "String(response.status)" in upload
