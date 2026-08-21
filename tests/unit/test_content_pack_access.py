"""Acesso ao compêndio, pack a pack.

Era tudo-ou-nada e só do GM, o que tornava impossível o caso normal de mesa:
liberar o pack de magias e manter o de monstros fechado. O acesso passou a ser
propriedade de cada pack, por papel, com os mesmos três níveis que ator, item e
diário já usam.

Estes testes guardam sobretudo o que *não* pode acontecer, porque é aí que um
modelo de permissão falha em silêncio.
"""

from __future__ import annotations

import json

from litestar.testing import TestClient

from app.engine.content.content_pack_access import ContentPackAccessService
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
from main import app
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user

PACOTE = "pack-of-things"
MAGIAS = "spells"
MONSTROS = "monsters"


def _install(user_id: str) -> None:
    InstalledPackageRepository().upsert(
        package_id=PACOTE, kind="ruleset", name="Coisas", version="1", status="enabled",
        package_dir=f"rulesets/{PACOTE}",
        manifest_json=json.dumps({"capabilities": ["content.packs"], "provides": {}}),
        compatibility_status="compatible", validation_errors_json="[]",
        installed_by_user_id=user_id, last_validation_status="valid",
    )


def _mesa(db_unused=None):
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    player = seed_user(name="Player")
    seed_member(campaign, player, "player")
    streamer = seed_user(name="Streamer")
    seed_member(campaign, streamer, "streamer")
    _install(gm)
    return gm, player, streamer, campaign


def test_absent_row_means_no_access(db):
    """A ausência de linha é o padrão, e o padrão é fechado.

    É o que faz a migração ser silenciosa: antes nenhum jogador via compêndio,
    e depois dela nenhum vê, até o mestre abrir um pack de propósito.
    """
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()

    assert acesso.level_for(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player) == "none"
    assert not acesso.can_read(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player)
    assert not acesso.reaches_any_pack(campaign_id=campaign, user_id=player)


def test_the_gm_owns_every_pack_without_a_row(db):
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()
    assert acesso.level_for(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=gm) == "owner"
    assert acesso.can_import(campaign_id=campaign, package_id=PACOTE, pack_id=MONSTROS, user_id=gm)
    assert acesso.reaches_any_pack(campaign_id=campaign, user_id=gm)


def test_access_is_per_pack_not_per_campaign(db):
    """O caso que motivou tudo: magias liberado, monstros fechado."""
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()
    assert acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                            role="player", level="read", user_id=gm)

    assert acesso.can_read(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player)
    assert not acesso.can_read(campaign_id=campaign, package_id=PACOTE, pack_id=MONSTROS, user_id=player)
    assert acesso.reaches_any_pack(campaign_id=campaign, user_id=player), "um pack já basta para a aba"


def test_read_lets_you_consult_but_never_import(db):
    """`owner` num pack quer dizer "pode alterar o mundo" -- aqui, importar para
    a campanha. Quem só lê consulta e não traz nada para a mesa."""
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()
    acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                     role="player", level="read", user_id=gm)

    assert acesso.can_read(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player)
    assert not acesso.can_import(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player)

    acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                     role="player", level="owner", user_id=gm)
    assert acesso.can_import(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player)


def test_the_streamer_stays_out_even_if_a_row_says_otherwise(db):
    """O streamer observa a mesa; compêndio é material de quem joga.

    A exclusão é por decisão de produto, não por falta de linha -- então nem uma
    linha gravada no papel dele pode abrir a porta.
    """
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()
    acesso.ownership.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                               role="streamer", level="owner")

    assert acesso.level_for(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=streamer) == "none"
    assert not acesso.reaches_any_pack(campaign_id=campaign, user_id=streamer)


def test_only_the_gm_grants_and_never_over_gm_or_streamer(db):
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()

    assert not acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                                role="player", level="owner", user_id=player), "jogador não concede"
    assert not acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                                role="gm", level="none", user_id=gm), "o mestre não se rebaixa"
    assert not acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                                role="streamer", level="read", user_id=gm)


def test_setting_none_clears_the_row_instead_of_storing_the_default(db):
    gm, player, streamer, campaign = _mesa()
    acesso = ContentPackAccessService()
    acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                     role="player", level="read", user_id=gm)
    assert len(acesso.ownership.list_for_campaign(campaign_id=campaign)) == 1

    acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                     role="player", level="none", user_id=gm)
    assert acesso.ownership.list_for_campaign(campaign_id=campaign) == [], (
        "ausência já significa none; guardar o padrão só acumula lixo"
    )


def test_the_pack_endpoints_refuse_a_reader_without_access(db):
    """Os dois endpoints de leitura não checavam NADA -- nem campanha, nem papel.

    Qualquer usuário logado lia qualquer pack de qualquer sistema instalado, o
    que faria do ownership pura decoração na tela.
    """
    gm, player, streamer, campaign = _mesa()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        assert client.get(f"/game/content/packs/{PACOTE}").status_code == 403, "sem campanha, sem pack"
        sem_acesso = client.get(
            f"/game/content/pack/{PACOTE}/{MAGIAS}", params={"campaign_id": campaign}
        )
        assert sem_acesso.status_code == 403
        assert sem_acesso.json()["error_key"] == "permissions.errors.denied"


def test_importing_requires_owner_on_the_server_not_just_a_hidden_button(db):
    gm, player, streamer, campaign = _mesa()
    ContentPackAccessService().set_level(
        campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
        role="player", level="read", user_id=gm,
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        for rota in ("/game/content/import", "/game/item/content/import"):
            resposta = client.post(rota, json={
                "campaign_id": campaign, "package_id": PACOTE,
                "pack_id": MAGIAS, "entry_id": "qualquer",
            })
            assert resposta.status_code == 403, rota
            assert resposta.json()["error_key"] == "permissions.errors.denied"


def test_the_listing_carries_the_level_only_for_who_grants(db, monkeypatch):
    """O nível viaja junto da lista de packs para o mestre encher o seletor sem
    uma segunda ida ao servidor. Para quem não concede, ele nem aparece: seria
    contar ao jogador como a permissão dele está configurada."""
    from app.engine.content.content_pack_service import ContentPackService

    gm, player, streamer, campaign = _mesa()
    monkeypatch.setattr(
        ContentPackService, "list_packs",
        lambda self, system_id: [{"id": MAGIAS, "type": "spell_pack", "label": "Magias"},
                                 {"id": MONSTROS, "type": "actor_pack", "label": "Monstros"}],
    )
    acesso = ContentPackAccessService()
    acesso.set_level(campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
                     role="player", level="read", user_id=gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        visao_gm = client.get(f"/game/content/packs/{PACOTE}", params={"campaign_id": campaign}).json()
    assert visao_gm["can_grant"] is True
    niveis = {p["id"]: p["player_access"] for p in visao_gm["packs"]}
    assert niveis == {MAGIAS: "read", MONSTROS: "none"}, "o mestre vê os dois, com o nível de cada"

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        visao_jogador = client.get(f"/game/content/packs/{PACOTE}", params={"campaign_id": campaign}).json()
    assert visao_jogador["can_grant"] is False
    assert [p["id"] for p in visao_jogador["packs"]] == [MAGIAS], "monstros nem é listado"
    assert "player_access" not in visao_jogador["packs"][0]


def test_only_the_gm_can_move_the_selector(db):
    gm, player, streamer, campaign = _mesa()
    corpo = {"campaign_id": campaign, "package_id": PACOTE, "pack_id": MAGIAS,
             "role": "player", "level": "owner"}

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        assert client.post("/game/content/pack-access", json=corpo).status_code == 403

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert client.post("/game/content/pack-access", json=corpo).status_code == 200

    assert ContentPackAccessService().can_import(
        campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS, user_id=player
    ), "o que o seletor gravou vale de verdade"


def test_an_entry_opens_the_real_sheet_read_only(db, monkeypatch):
    """O leitor não é uma tela nova: é a ficha do mundo com can_edit falso.

    Manter duas telas para a mesma coisa é o que faz uma delas envelhecer -- por
    isso o preview reusa o mesmo miolo de build_bundle, e o que muda é só o que
    não vem de um ator persistido: id, retrato, resumo e permissão.
    """
    from app.engine.sdk.package_content_service import PackageContentService

    gm, player, streamer, campaign = _mesa()
    entrada = {"id": "goblin", "type": "npc", "name": "Goblin", "data": {"hp": 7}}
    monkeypatch.setattr(
        PackageContentService, "get_pack",
        lambda self, package_id, pack_id: {"id": pack_id, "type": "actor_pack", "entries": [entrada]},
    )
    ContentPackAccessService().set_level(
        campaign_id=campaign, package_id=PACOTE, pack_id=MONSTROS,
        role="player", level="read", user_id=gm,
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        resposta = client.get(
            f"/game/content/pack/{PACOTE}/{MONSTROS}/entry/goblin/sheet",
            params={"campaign_id": campaign},
        )
    assert resposta.status_code == 200
    corpo = resposta.text
    assert "Goblin" in corpo
    # O id do modal é próprio do compêndio: sem ele o preview nasceria como
    # "actor-" e colidiria com qualquer outro aberto.
    assert f'data-modal-id="compendium-{PACOTE}-{MONSTROS}-goblin"' in corpo
    assert '"can_edit":false' in corpo.replace(" ", ""), "compêndio é fonte, nunca editável daqui"


def test_the_reader_refuses_an_entry_the_reader_cannot_reach(db, monkeypatch):
    from app.engine.sdk.package_content_service import PackageContentService

    gm, player, streamer, campaign = _mesa()
    monkeypatch.setattr(
        PackageContentService, "get_pack",
        lambda self, package_id, pack_id: {"id": pack_id, "type": "actor_pack",
                                           "entries": [{"id": "x", "type": "npc", "name": "X", "data": {}}]},
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        negado = client.get(
            f"/game/content/pack/{PACOTE}/{MONSTROS}/entry/x/sheet",
            params={"campaign_id": campaign}, follow_redirects=False,
        )
    assert negado.status_code in (302, 303, 307, 308), "sem acesso, nem a ficha"


def test_a_package_appears_for_a_player_who_reaches_one_pack_inside_it(db, monkeypatch):
    """A aba do jogador aparecia, mas o pacote não: `list_active_packages` era
    gm-only, e o compêndio abria vazio mesmo com um pack liberado.

    O pacote só entra se houver ao menos um pack legível dentro -- senão o
    jogador abriria um pacote para encontrar nada, que é o mesmo problema um
    nível abaixo.
    """
    from app.engine.sdk.package_content_service import PackageContentService
    from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository

    gm, player, streamer, campaign = _mesa()
    servico = PackageContentService()
    monkeypatch.setattr(
        PackageContentService, "list_packs",
        lambda self, package_id: [{"id": MAGIAS}, {"id": MONSTROS}],
    )
    monkeypatch.setattr(
        type(servico.install), "list_for_tab",
        lambda self: [{"id": PACOTE, "name": "Coisas", "status": "enabled",
                       "capabilities": ["content.packs"]}],
    )
    CampaignPackageRepository().activate(
        campaign_id=campaign, package_id=PACOTE, activation_role="content",
        enabled_by_user_id=gm,
    )

    assert servico.list_active_packages(campaign_id=campaign, user_id=gm), "o mestre sempre vê"
    assert servico.list_active_packages(campaign_id=campaign, user_id=player) == [], (
        "sem pack liberado, o pacote não aparece"
    )

    ContentPackAccessService().set_level(
        campaign_id=campaign, package_id=PACOTE, pack_id=MAGIAS,
        role="player", level="read", user_id=gm,
    )
    assert [p["id"] for p in servico.list_active_packages(campaign_id=campaign, user_id=player)] == [PACOTE]
    assert servico.list_active_packages(campaign_id=campaign, user_id=streamer) == [], "streamer fora"


def test_an_item_pack_entry_opens_the_item_sheet_not_the_actor_sheet(db, monkeypatch):
    """O tipo do PACK decide a ficha.

    Mandar tudo para a ficha de ator desenhava um arco curto com classe, raça e
    pontos de experiência -- e sem layout nenhum, porque não existe ficha de ator
    do tipo "weapon".
    """
    from app.engine.sdk.package_content_service import PackageContentService

    gm, player, streamer, campaign = _mesa()
    arma = {"id": "arco", "type": "weapon", "name": "Arco Curto", "data": {}}
    monkeypatch.setattr(
        PackageContentService, "get_pack",
        lambda self, package_id, pack_id: {"id": pack_id, "type": "item_pack", "entries": [arma]},
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        corpo = client.get(
            f"/game/content/pack/{PACOTE}/{MAGIAS}/entry/arco/sheet",
            params={"campaign_id": campaign},
        ).text

    assert "Arco Curto" in corpo
    assert "item-sheet-modal" in corpo, "tem de ser a casca de item"
    assert "actor-sheet-modal" not in corpo, "e não a de ator"
    assert f'data-modal-id="compendium-{PACOTE}-{MAGIAS}-arco"' in corpo


def test_the_preview_modal_id_never_starts_with_a_routed_prefix(db):
    """Um id começando com "actor-" ou "item-" faz ensureModalReady tentar
    buscá-lo em /game/actor/sheet/modal/... -- e o modal simplesmente não abre.

    Esse era o motivo de o botão não exibir nada.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    gerente = (raiz / "static/js/ui/modals/modal-manager.js").read_text(encoding="utf-8")
    prefixos = [linha.split('prefix: "')[1].split('"')[0]
                for linha in gerente.splitlines() if 'prefix: "' in linha]
    assert prefixos, "o registro de prefixos sumiu; este teste precisa ser revisto"
    for prefixo in prefixos:
        assert not "compendium-".startswith(prefixo), (
            f'o id de preview colide com o prefixo roteado "{prefixo}"'
        )


def test_the_preview_uses_the_campaign_system_not_the_content_package(db, monkeypatch):
    """O `system_id` da rota é o PACOTE DE CONTEÚDO; o layout da ficha vem do
    SISTEMA da campanha, e os dois podem ser pacotes diferentes.

    Usar o pacote fazia a ficha abrir sem layout nenhum. O import já resolvia
    isso com _entry_system_id; ler tem de seguir a mesma regra, senão a leitura
    mostra algo diferente do que a importação cria.
    """
    from app.engine.sdk.package_content_service import PackageContentService
    from app.engine.sheets.item_sheet_service import ItemSheetService
    from app.persistence.repositories.campaign_repository import CampaignRepository

    gm, player, streamer, campaign = _mesa()
    _install(gm)
    CampaignRepository().update_system(
        campaign_id=campaign, changed_by_user_id=gm, next_system_id="dnd5e"
    )
    monkeypatch.setattr(
        PackageContentService, "get_pack",
        lambda self, package_id, pack_id: {
            "id": pack_id, "type": "item_pack",
            "entries": [{"id": "arco", "type": "weapon", "name": "Arco", "data": {}}],
        },
    )
    vistos: list[str] = []
    original = ItemSheetService.build_preview_bundle
    monkeypatch.setattr(
        ItemSheetService, "build_preview_bundle",
        lambda self, **kw: (vistos.append(kw["system_id"]), original(self, **kw))[1],
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        client.get(f"/game/content/pack/{PACOTE}/{MAGIAS}/entry/arco/sheet",
                   params={"campaign_id": campaign})

    assert vistos == ["dnd5e"], f"devia usar o sistema da campanha, usou {vistos}"


def test_the_preview_announces_both_sheet_mounts():
    """A entrada volta como ficha de ator OU de item, e só o servidor sabe qual.

    Anunciar só o mount de ator deixava a ficha de item montada pela metade: o
    modal abria com a casca certa e o corpo no placeholder, porque o controlador
    de item nunca era acordado. Cada mount() desiste sozinho quando não acha o
    próprio bundle, então anunciar os dois é seguro.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    remoto = (raiz / "static/js/ui/modals/modal-remote.js").read_text(encoding="utf-8")
    trecho = remoto.split("ensureCompendiumEntryModal", 1)[1].split("async function", 1)[0]
    assert "vtt:actor-sheet-modal-mounted" in trecho
    assert "vtt:item-sheet-modal-mounted" in trecho

    for arquivo, marcador in (
        ("static/js/sheets/actors/actor-sheet-controller.js", "[data-actor-bundle]"),
        ("static/js/sheets/items/item-sheet-controller.js", "[data-item-bundle]"),
    ):
        corpo = (raiz / arquivo).read_text(encoding="utf-8")
        montagem = corpo.split("function mount(modal)", 1)[1][:400]
        assert marcador in montagem and "if (!root || !script) return;" in montagem, (
            f"{arquivo}: o mount precisa desistir sem o próprio bundle"
        )
