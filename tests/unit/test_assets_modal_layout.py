"""A modal de assets é uma grade com pastas, busca e filtro: não uma lista.

A lista em linha única servia quando só havia imagem. Com ficha em PDF na mesma
pasta, ela deixou de servir por dois motivos: a miniatura de 48px não ajuda a
escolher uma imagem, e não havia como separar os tipos.

A aba "Biblioteca" existia só para hospedar um botão. Ela morreu, e o botão
virou "Assets". O painel de GM que o hospedava também morreu depois, e Assets
passou a viver no cartão de gerenciamento das Configurações.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates/pages/game/index.html"
SCRIPT = ROOT / "static/js/assets/asset-library.js"
STYLES = ROOT / "static/css/game.css"


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_the_library_tab_is_gone():
    html = _template()
    assert "panel-library-" not in html, "o painel intermediário não existe mais"
    assert "show_library_panel" not in html, "a flag que o gatilhava também sai"
    assert 'data-panel-toggle="panel-library-' not in html, "nem o botão do dock"


def test_the_gm_panel_is_gone_and_assets_lives_in_settings():
    """O painel da coroa foi desmontado: Cenas e Compêndios subiram ao rail,
    Decks e Assets desceram para Configurações, e Jogadores era só um atalho
    que já abria a própria aba de Configurações."""
    html = _template()
    assert 'data-modal-id="panel-gm-' not in html, "o painel de GM não existe mais"
    assert 'data-panel-toggle="panel-gm-' not in html, "nem o botão da coroa"

    gerenciamento = html.split('data-settings-section="management"', 1)[1].split("</section>", 1)[0]
    assert 'data-modal-open="library-images-' in gerenciamento, "Assets abre a modal"
    assert "game.assets.title" in gerenciamento
    assert 'data-modal-open="panel-cards-' in gerenciamento, "Decks veio junto"


def test_nobody_gains_or_loses_access_in_the_move():
    """Assets e Decks eram de gm+assistente+streamer. Mudar de casa não pode
    mexer nisso: a condição viajou junto com o botão."""
    html = _template()

    gerenciamento = html.split('data-settings-section="management"', 1)[1].split("</section>", 1)[0]
    for acao in ('data-modal-open="library-images-', 'data-modal-open="panel-cards-'):
        antes = gerenciamento.split(acao, 1)[0].rsplit("{% if", 1)[1]
        assert "assistant_gm" in antes and "is_streamer" in antes, acao

    # A modal em si mantém o público de sempre
    modal = html.split('class="game-modal-window library-images-modal"', 1)[0].rsplit("{% if", 1)[1]
    assert "assistant_gm" in modal


def test_the_modal_offers_folders_search_and_a_type_filter():
    html = _template()
    corpo = html.split("asset-panel-body", 1)[1].split("</article>", 1)[0]

    assert "data-asset-search" in corpo, "buscar por nome"
    assert "data-scene-asset-folder-list" in corpo, "pastas em coluna, não em barra"
    assert "data-asset-summary" in corpo, "quantos itens e quanto pesam"

    assert 'class="asset-kinds"' in corpo
    assert 'data-asset-kind="image"' not in corpo, "tipos ausentes não devem produzir filtro vazio"
    script = SCRIPT.read_text(encoding="utf-8")
    assert "renderKinds()" in script and "counts.has(kind)" in script


def test_package_import_starts_hidden_and_uses_active_asset_packages():
    html = _template()
    button = html.split("data-asset-package-open", 1)[0].rsplit("<button", 1)[1] + html.split("data-asset-package-open", 1)[1].split(">", 1)[0]
    assert "hidden" in button, "não pode piscar para campanhas sem addon de assets"
    script = SCRIPT.read_text(encoding="utf-8")
    assert "/game/assets/packages/" in script
    assert "button.hidden = this.assetPackages.length === 0" in script


def test_the_three_filters_narrow_the_same_set():
    """Pasta, tipo e busca são recortes independentes. Se cada um filtrasse por
    conta própria, o rodapé contaria um conjunto e a grade mostraria outro."""
    script = SCRIPT.read_text(encoding="utf-8")
    visiveis = script.split("visibleAssets() {", 1)[1].split("\n    }", 1)[0]

    assert "folder_id" in visiveis and "this.kind" in visiveis and "this.search" in visiveis

    for metodo in ("renderGrid", "renderSummary"):
        corpo = script.split(f"{metodo}() {{", 1)[1].split("\n    }", 1)[0]
        assert "this.visibleAssets()" in corpo, f"{metodo} precisa usar o mesmo recorte"


def test_typing_in_the_search_does_not_rebuild_the_folder_rail():
    """Refazer as pastas a cada tecla rouba o foco do campo de busca."""
    script = SCRIPT.read_text(encoding="utf-8")
    handler = script.split("[data-asset-search]", 1)[1].split("});", 1)[0]

    assert "controller.renderGrid()" in handler
    assert "renderFolders" not in handler, "a lista de pastas não muda com a busca"


def test_the_empty_state_explains_which_filter_hid_everything():
    """"Nada aqui" com um filtro ligado manda a pessoa procurar o arquivo que ela
    mesma escondeu."""
    script = SCRIPT.read_text(encoding="utf-8")
    vazio = script.split("emptyMessage() {", 1)[1].split("\n    }", 1)[0]

    assert "assetLabelNoMatch" in vazio, "busca sem resultado"
    assert "assetLabelNoKind" in vazio, "filtro de tipo sem resultado"
    assert "assetLabelEmptyFolder" in vazio, "pasta realmente vazia"

    html = _template()
    for rotulo in ("no-match", "no-kind", "show"):
        assert f'data-asset-label-{rotulo}=' in html, f"rótulo {rotulo} não chega ao cliente"


def test_the_grid_replaced_the_row_list_everywhere():
    """CSS de uma estrutura que não existe mais é ruído para quem for mexer."""
    assert ".asset-row" not in STYLES.read_text(encoding="utf-8")
    assert "asset-row" not in SCRIPT.read_text(encoding="utf-8")
    assert "asset-row" not in _template()

    styles = STYLES.read_text(encoding="utf-8")
    assert ".asset-card__thumb" in styles and "aspect-ratio" in styles, (
        "a miniatura grande é o motivo de existir a grade"
    )
