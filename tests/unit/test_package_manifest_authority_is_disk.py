"""Quem manda no manifest é o disco, não o retrato guardado na instalação.

``installed_packages.manifest_json`` é uma cópia tirada na hora de instalar. Se
alguma camada ler essa cópia em vez do arquivo em disco, editar o manifest passa a
exigir reinstalar o pacote — e, pior, o servidor fica dividido: uma parte enxerga a
capability nova e outra não. Foi exatamente assim que ``sdk.assets.list`` passou na
validação do manifest e mesmo assim explodiu no navegador com

    Package "x" attempted to use sdk.assets.list but does not declare
    capability "assets.library".

``PackageInstallService.get_manifest`` é o único lugar que decide isso.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.engine.sdk.package_install_service import PackageInstallService

ROOT = Path(__file__).resolve().parents[2]
SDK_DIR = ROOT / "app/engine/sdk"


def test_only_the_install_service_reads_the_stored_snapshot():
    """Qualquer serviço que abra ``manifest_json`` está reimplementando a regra —
    e nada garante que a reimplemente na mesma direção.

    Este teste já existiu varrendo só ``app/engine/sdk``, e por isso deixou passar
    quatro serviços fora dessa pasta: o registry de regras (mapeamento de token),
    o schema das fichas (que sanitiza as escritas), o layout e os content packs.
    O sintoma foi caro de achar — token sem imagem no tabuleiro e campo novo
    sumindo na gravação, ambos sem erro nenhum. A varredura agora é o app inteiro.
    """
    # O doctor é a exceção legítima: o trabalho dele é justamente comparar o
    # retrato com o disco para acusar a defasagem. O repositório é quem grava.
    allowed = {
        "package_install_service.py",
        "package_doctor_service.py",
        "installed_package_repository.py",
    }

    offenders: list[str] = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        if path.name in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        code = re.sub(r"#.*", "", source)
        if 'record["manifest_json"]' in code or "row['manifest_json']" in code:
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "estes leem o retrato guardado em vez de perguntar ao PackageInstallService: "
        f"{offenders}"
    )


def test_the_services_a_package_edit_must_reach():
    """Os quatro que quebraram na prática, nomeados: um manifest editado precisa
    chegar a todos eles sem reinstalar o pacote."""
    for relativo in (
        "app/engine/rules/rules_registry.py",
        "app/engine/sheets/schema_service.py",
        "app/engine/sheets/system_layout_service.py",
        "app/engine/content/content_pack_service.py",
    ):
        source = (ROOT / relativo).read_text(encoding="utf-8")
        assert "self.install.get_manifest(" in source, f"{relativo} não usa a autoridade comum"


def test_the_install_service_prefers_disk_over_the_snapshot():
    source = (SDK_DIR / "package_install_service.py").read_text(encoding="utf-8")
    body = source.split("def get_manifest", 1)[1].split("def ", 1)[0]

    disk_at = body.index("package_registry.load_by_package_id")
    snapshot_at = body.index('record["manifest_json"]')
    assert disk_at < snapshot_at, "o disco tem de ser consultado primeiro"


def test_the_client_manifest_capabilities_come_from_disk(monkeypatch, tmp_path):
    """O teste que faltava: a lista de capabilities que chega ao navegador precisa
    refletir o manifest em disco, mesmo com um retrato antigo no banco."""
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_asset_service import PackageAssetService

    package_id = "gravewright-pdf-system"
    on_disk = json.loads(
        (ROOT / "data/packages/rulesets" / package_id / "manifest.json").read_text(encoding="utf-8")
    )

    # retrato desatualizado: sem a capability que o disco declara
    stale = {**on_disk, "capabilities": ["actors.register"]}
    record = {
        "id": package_id,
        "status": "enabled",
        "package_dir": f"rulesets/{package_id}",
        "manifest_json": json.dumps(stale),
    }

    service = PackageAssetService()
    # O repositório é a fonte que install.get e install.get_manifest compartilham;
    # trocar só o get deixaria get_manifest olhando o banco de verdade.
    monkeypatch.setattr(
        service.install.installed, "get", lambda pid: record if pid == package_id else None
    )
    monkeypatch.setattr(service, "_ordered_active_package_ids", lambda campaign_id: [package_id])
    monkeypatch.setattr(service.settings, "definitions", lambda pid: [])
    monkeypatch.setattr(service.settings, "effective_values", lambda pid, cid, uid: {})
    monkeypatch.setattr(service.locales, "get_locale", lambda pid, locale: {})

    assert package_registry.load_by_package_id(package_id) is not None, "pacote precisa estar em disco"

    manifests = service.list_client_manifests("campanha", user_id="u1")
    assert manifests, "o pacote habilitado precisa chegar ao cliente"

    capabilities = set(manifests[0]["capabilities"])
    assert capabilities == set(on_disk["capabilities"]), (
        "as capabilities entregues ao navegador vieram do retrato, não do disco"
    )
    assert "assets.library" in capabilities


def test_install_service_get_manifest_is_the_shared_entry_point():
    service = PackageInstallService()
    assert hasattr(service, "get_manifest")


def test_package_asset_urls_change_when_the_file_changes(tmp_path):
    """A versão do manifest não muda quando só um script muda. Sem outro sinal, o
    navegador reusa o ``?v=0.1.0`` em cache e o autor depura código que não está
    mais rodando — foi o que aconteceu ao editar o controlador da ficha PDF."""
    from app.engine.sdk.package_asset_service import PackageAssetService

    script = tmp_path / "app.js"
    script.write_text("// v1", encoding="utf-8")

    first = PackageAssetService._asset_url("pkg", "app.js", "1.0.0", tmp_path)
    assert first.startswith("/sdk/packages/pkg/asset/app.js?v=1.0.0-"), first

    import os

    stat = script.stat()
    os.utime(script, (stat.st_atime, stat.st_mtime + 60))
    second = PackageAssetService._asset_url("pkg", "app.js", "1.0.0", tmp_path)

    assert first != second, "editar o arquivo tem de mudar a URL, sem subir a versão"

    # Arquivo inexistente ainda produz URL utilizável: a rota é quem decide 404.
    missing = PackageAssetService._asset_url("pkg", "sumiu.js", "1.0.0", tmp_path)
    assert missing.endswith("?v=1.0.0")
