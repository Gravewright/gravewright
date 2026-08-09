"""Coerência do pacote Gravewright PDF System.

A ideia do sistema é que o PDF seja a aparência da ficha e o mapeamento
transforme cada campo num caminho de dado — é isso que deixa a barra de HP do
token ler o mesmo número que o jogador digitou no papel. Um mapeamento que
aponta para um caminho fora do schema, ou para um arquivo que o manifest não
declara, quebra essa ponte em silêncio: a ficha abre e nada persiste.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_manifest_validator import validate_manifest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "data/packages/rulesets/gravewright-pdf-system"


def _json(relative: str) -> dict:
    return json.loads((PACKAGE / relative).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest_raw() -> dict:
    return _json("manifest.json")


def test_manifest_is_valid_sdk_1(manifest_raw):
    result = validate_manifest(manifest_raw)
    assert not result.errors, list(result.errors)
    assert not result.warnings, list(result.warnings)
    assert manifest_raw["sdkVersion"] == "1"
    assert manifest_raw["kind"] == "ruleset"
    assert manifest_raw["id"] == "gravewright-pdf-system"
    assert manifest_raw["version"] == "0.1.0"


def test_every_declared_file_exists(manifest_raw):
    manifest = PackageManifest.from_dict(manifest_raw)
    missing = [path for path in manifest.referenced_paths() if not (PACKAGE / path).is_file()]
    assert not missing, missing


def test_the_pdf_template_is_declared_so_it_can_be_served(manifest_raw):
    """O mapeamento aponta o arquivo, mas quem autoriza servir é o manifest.

    Sem a declaração em provides.assets o PDF volta 404 e a ficha abre vazia —
    e nada no mapeamento acusaria isso.
    """
    manifest = PackageManifest.from_dict(manifest_raw)
    servable = set(manifest.referenced_paths())

    for name, template in _json("mappings/pdf-fields.gw.json")["templates"].items():
        assert template["file"] in servable, f"template '{name}' não é servível: {template['file']}"
        assert (PACKAGE / template["file"]).is_file()


def test_the_bundled_template_is_a_structurally_valid_pdf():
    """PDF real usa CR, LF ou CRLF conforme o gerador. Exigir só LF fazia o teste
    recusar arquivos legítimos — e foi o que aconteceu ao trocar o template por um
    PDF de verdade."""
    import re

    data = (PACKAGE / "assets/sheets/blank-a4.pdf").read_bytes()
    assert data.startswith(b"%PDF-")
    assert data.rstrip().endswith(b"%%EOF")

    # Um PDF linearizado traz dois startxref: o primeiro aponta para 0 por
    # convenção, e o autoritativo é o último. Pegar o primeiro leva de volta ao
    # cabeçalho do arquivo e parece corrupção.
    matches = re.findall(rb"startxref[\r\n]+(\d+)", data)
    assert matches, "sem startxref não há como localizar a tabela de referência"
    start = int(matches[-1])

    # PDF 1.5+ pode usar xref stream (um objeto) em vez da tabela clássica.
    target = data[start : start + 32]
    assert target.startswith(b"xref") or re.match(rb"\d+\s+\d+\s+obj", target), (
        f"startxref aponta para bytes que não são xref nem objeto: {target[:16]!r}"
    )


def test_mapped_paths_land_where_the_schema_allows():
    """Cada campo grava num caminho; se o schema não tiver esse caminho, o
    servidor sanitiza a escrita e o valor some sem erro visível."""
    schema = _json("schemas/actors/character.schema.json")
    root_properties = set(schema["properties"])

    for name, template in _json("mappings/pdf-fields.gw.json")["templates"].items():
        for field, spec in template["fields"].items():
            path = spec["path"]
            assert spec["type"] in {"string", "number", "boolean"}, (name, field)

            head, _, rest = path.partition(".")
            assert head in {"core", "sheet"}, f"{field}: raiz desconhecida em '{path}'"
            if head != "sheet":
                continue
            branch = rest.split(".")[0]
            assert branch in root_properties, (
                f"{field}: '{path}' não existe no schema (propriedades: {sorted(root_properties)})"
            )


def test_token_bars_read_the_same_paths_the_pdf_writes():
    """A ponte inteira em um teste: o campo 'HP' do PDF e a barra do token
    precisam apontar para o mesmo lugar, senão o token nunca reflete a ficha."""
    fields = _json("mappings/pdf-fields.gw.json")["templates"]["generic"]["fields"]
    token = _json("mappings/token.gw.json")["character"]

    assert fields["HP"]["path"] == token["bars"]["bar_1"]["value"]
    assert fields["HPMax"]["path"] == token["bars"]["bar_1"]["max"]
    assert fields["Initiative"]["path"] == token["initiative"]
    assert fields["AC"]["path"] == token["defense"]


def test_every_label_key_used_has_a_translation():
    en = _json("locales/en.json")
    pt = _json("locales/pt-BR.json")
    assert set(en) == set(pt), set(en).symmetric_difference(pt)

    import re

    # O template rotula botões por data-pdf-title (o controlador traduz); o
    # controlador chama t("ui.x"). Nenhum dos dois pode citar chave inexistente.
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    used = {f"gravewright-pdf-system.ui.{name}" for name in re.findall(r'data-pdf-title="(\w+)"', template)}
    used |= {
        f"gravewright-pdf-system.{key}"
        for key in re.findall(r'(?<![\w.])t\("([\w.]+)"', controller)
    }

    missing = sorted(used - set(en))
    assert not missing, f"chaves usadas na ficha sem tradução: {missing}"
    assert used, "o teste precisa achar alguma chave, senão não guarda nada"

    # data-text é caminho de DADO no host, não chave de tradução. Usá-lo para
    # rótulo renderiza vazio — foi assim que o aviso de 'sem template' sumiu.
    for key in re.findall(r'data-text="([^"]+)"', template):
        assert not key.startswith("gravewright-pdf-system."), (
            f"data-text='{key}' é caminho de dado, não chave de i18n"
        )

    manifest_keys = {
        key
        for setting in _json("manifest.json")["settings"]
        for key in (setting["labelKey"], setting["hintKey"])
    }
    assert not manifest_keys - set(en), sorted(manifest_keys - set(en))


def test_the_pdfjs_runtime_is_lazy_not_an_entrypoint(manifest_raw):
    """pdf.mjs + worker somam ~3 MB. Como entrypoint eles entrariam no
    carregamento da página de jogo de todo mundo, inclusive de quem nunca abre
    uma ficha PDF. Precisam ser asset declarado e importados sob demanda."""
    scripts = manifest_raw["entrypoints"]["game"]["scripts"]
    assert not [s for s in scripts if s.startswith("vendor/")], scripts

    vendor = {entry["path"] for entry in manifest_raw["provides"]["assets"]["vendor"]}
    assert vendor == {"vendor/pdf.mjs", "vendor/pdf.worker.mjs"}

    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")
    assert 'await import(asset("vendor/pdf.mjs"))' in viewer, "importação sob demanda"
    assert "if (pdfjs) return pdfjs" in viewer, "importa uma vez só"

    # o worker precisa do caminho explícito: o default do pdf.js é um irmão da
    # página ("./pdf.worker.mjs"), que não existe aqui
    assert 'workerSrc = asset("vendor/pdf.worker.mjs")' in viewer


def test_field_positions_come_from_the_pdf_not_from_the_mapping():
    """O mapeamento fala só de nomes de campo. Se as coordenadas tivessem de ser
    escritas à mão, cada PDF novo viraria um trabalho de régua."""
    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")
    assert "page.getAnnotations(" in viewer
    assert "annotation.fieldName" in viewer
    assert 'annotation.subtype !== "Widget"' in viewer, "só campos de formulário"
    # O pdf.js 6 só expõe convertToViewportPoint; convertToViewportRectangle foi
    # removido. Os dois cantos passam pelo viewport, que aplica a inversão do eixo
    # Y, a escala e a rotação.
    assert viewer.count("viewport.convertToViewportPoint(field.rect") == 2, "PDF tem origem embaixo"

    mapping = _json("mappings/pdf-fields.gw.json")
    for name, template in mapping["templates"].items():
        for field, spec in template["fields"].items():
            assert set(spec) <= {"path", "type"}, (
                f"{name}.{field}: mapeamento não deve carregar coordenadas ({sorted(spec)})"
            )


def test_the_sheet_survives_without_a_pdf_renderer():
    """Não há renderizador de PDF instalado no projeto. O sistema é de dados, e
    precisa continuar gravando mesmo sem página desenhada."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    styles = (PACKAGE / "styles/pdf-sheet.css").read_text(encoding="utf-8")

    assert "window.GravewrightPdfViewer || null" in controller, "o renderizador é opcional"
    assert 'stage.dataset.viewerMissing = "true"' in controller
    assert '[data-viewer-missing="true"]' in styles, "sem renderizador os campos empilham"
    # o controlador nunca pode assumir que o visualizador existe
    assert "viewer?.close" in controller

    # campo que o PDF não tem some, em vez de flutuar num canto qualquer
    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")
    place = viewer.split("placeField(input, fieldName) {", 1)[1].split("},", 1)[0]
    assert 'input.style.display = "none"' in place and "return false" in place


def test_vendor_carries_only_what_is_declared(manifest_raw):
    """Uma distribuição do pdf.js vem com 7 MB de source maps e um bundle de
    sandbox que só serve para executar JavaScript embutido no PDF — coisa que este
    sistema não faz. Arquivo não declarado não é servível, então seria peso morto
    no repositório e 404 no devtools."""
    vendor_dir = PACKAGE / "vendor"
    on_disk = {entry.name for entry in vendor_dir.iterdir()}
    # "vendor" é código de terceiro; o que é nosso vive em provides.assets.runtime
    declared = {
        entry["path"].split("/")[-1]
        for entry in manifest_raw["provides"]["assets"]["vendor"]
    }
    assert on_disk == declared, f"vendor fora do manifest: {sorted(on_disk ^ declared)}"

    for name in on_disk:
        text = (vendor_dir / name).read_text(encoding="utf-8", errors="ignore")
        assert "sourceMappingURL" not in text, f"{name} aponta para um .map que não existe"


def test_the_viewer_asks_the_sdk_where_assets_live():
    """Se o visualizador remontasse a URL de asset por conta própria, seriam duas
    montagens para manter em acordo com a rota. Ele recebe o resolvedor do SDK."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")
    sdk = (ROOT / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")

    assert "const asset = sdk.package.assetUrl;" in controller, "o controlador pega o resolvedor do SDK"
    assert "assetUrl: asset," in controller, "e o repassa ao visualizador"
    assert "if (assetUrl) asset = assetUrl;" in viewer, "o visualizador adota o resolvedor recebido"
    assert "assetUrl: (relativePath) =>" in sdk, "o SDK precisa expor package.assetUrl"


def test_a_fresh_sheet_resolves_a_template(manifest_raw):
    """Sem template resolvido a ficha não desenha nada e não cria campo algum —
    abre inerte, sem erro nenhum no console. Com a configuração em branco era
    exatamente isso que acontecia numa instalação nova."""
    templates = _json("mappings/pdf-fields.gw.json")["templates"]
    default = next(s for s in manifest_raw["settings"] if s["key"] == "defaultTemplate")["default"]

    assert default, "o padrão em branco deixa toda ficha nova inerte"
    assert default in templates, f"padrão '{default}' não existe no mapeamento ({sorted(templates)})"

    # Cinto e suspensório: mesmo que alguém apague a configuração, um sistema com
    # um único template cai nele em vez de abrir vazio.
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    assert "available.length === 1 ? available[0] : \"\"" in controller


def test_the_template_picker_is_never_a_dead_end():
    """O aviso de 'nenhum template' manda usar o botão PDF. Se o botão recusar
    quando só há um template, não há saída — que era o caso. E ciclar no clique
    também não mostrava o que existe."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    picker = controller.split("async function chooseTemplate", 1)[1].split(
        "function closePicker", 1
    )[0]

    assert "if (ids.length < 2)" not in picker, "recusar com um template fecha a única saída"
    assert "Object.entries(mapping?.templates" in picker, "lista os templates do pacote"
    assert "await uploadedPdfs()" in picker, "e os PDFs que o GM enviou"
    assert "data-pdf-picker" in template, "o template precisa hospedar a lista"

    # As duas origens são exclusivas: gravar uma tem de limpar a outra, senão um
    # envio antigo continua ganhando do template recém-escolhido.
    assert 'change(ctx, "system.pdf.asset"' in picker
    assert 'change(ctx, "system.pdf.template"' in picker

    # A lista some junto com a ficha, e o ouvinte de clique-fora vai junto: um
    # listener preso ao document depois da ficha fechada é vazamento.
    assert 'document.addEventListener("click", onOutside, true)' in picker
    closer = controller.split("function closePicker", 1)[1]
    assert "document.removeEventListener" in closer
    assert "closePicker(ctx);" in controller.split("unmount(ctx) {", 1)[1][:120]


def test_every_declared_setting_is_actually_used(manifest_raw):
    """Configuração que aparece na UI e não faz nada é pior que configuração
    ausente: o GM mexe e conclui que o sistema está quebrado."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    unused = [
        setting["key"]
        for setting in manifest_raw["settings"]
        if f'settings.get("{setting["key"]}"' not in controller
    ]
    assert not unused, f"configurações declaradas e nunca lidas: {unused}"


def test_a_template_whose_mapping_does_not_match_the_pdf_still_shows_fields():
    """Trocar o arquivo de um template sem atualizar o mapeamento é fácil de
    fazer. Sem defesa, a ficha abre com a página desenhada e nenhum campo: todo
    input aponta para um nome que o PDF não tem, e o visualizador esconde todos."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    build = controller.split("async function build", 1)[1].split("function rebuild", 1)[0]

    assert "const real = new Set(opened.fields)" in build
    assert "!Object.keys(fields).some((name) => real.has(name))" in build, (
        "a defesa só vale quando NENHUM campo mapeado existe no arquivo"
    )
    # cair no auto-mapeamento é o mesmo caminho do PDF enviado, não um segundo
    assert build.count("autoMapFields(\n") == 2


def test_writing_a_value_updates_the_local_data_before_notifying():
    """O host, ao ligar um data-bind, faz duas coisas: setPath(ctx.data, ...) e
    depois ctx.onChange(...). Chamar só a segunda deixa ctx.data com o valor
    antigo — e qualquer releitura logo em seguida vê o que acabou de ser
    substituído. Foi assim que escolher um PDF enviado não trocava nada: o
    remonte relia o id anterior e caía de volta no template do pacote."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")

    helper = controller.split("function change(ctx, path, value)", 1)[1].split("}", 1)[0]
    assert "writePath(ctx.data, path, value)" in helper
    assert "ctx.onChange?.(path, value)" in helper
    assert helper.index("writePath") < helper.index("ctx.onChange"), (
        "atualizar o dado local tem de vir antes de avisar"
    )

    # Fora do helper não pode sobrar ninguém avisando sem gravar.
    outside = controller.replace(helper, "")
    assert outside.count("ctx.onChange?.(") == 0, (
        "toda escrita passa por change(); um ctx.onChange solto reintroduz o bug"
    )


def test_switching_pdf_resets_the_remembered_page():
    """A página lembrada era do arquivo anterior: abrir a página 7 de um PDF com
    2 páginas não faz sentido."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    picker = controller.split("async function chooseTemplate", 1)[1].split("function closePicker", 1)[0]
    assert 'change(ctx, "system.pdf.page", 1)' in picker


def test_fields_are_positioned_after_they_are_created():
    """Os inputs nascem DEPOIS do open(): num PDF enviado os nomes dos campos vêm
    do arquivo, então é preciso abrir para saber o que criar. Só que quem
    posiciona é o render(), que já rodou com a lista vazia. Sem uma segunda
    passada, os campos ficam sem left/top e empilham todos na origem — o que
    aparece como uma barra única no canto da ficha, com só o último clicável."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")

    assert "refresh: () => render()" in viewer, "o visualizador precisa reposicionar sob demanda"

    build = controller.split("async function build", 1)[1].split("function rebuild", 1)[0]
    assert "await active?.refresh?.()" in build
    assert build.index("buildFields(ctx, fields, active)") < build.index("active?.refresh?.()")


def test_checkboxes_are_checkboxes():
    """Uma ficha de Savage Worlds traz 125 campos Btn. Como caixa de texto, eles
    pedem que a pessoa digite onde deveria marcar."""
    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")

    assert "fieldType: (name) =>" in viewer, "o tipo vem do PDF, não do palpite"
    assert 'viewer?.fieldType?.(name) === "Btn" ? "boolean" : "string"' in controller
    assert 'spec.type === "boolean" ? "checkbox"' in controller

    # readOnly não trava checkbox; sem disabled, quem não pode editar ainda marca.
    assert 'if (input.type === "checkbox") input.disabled = !canEdit;' in controller


def test_two_field_names_never_share_a_data_path():
    """"HP atual" e "HP-atual" viram o mesmo segmento seguro. Sem desempate, os
    dois gravariam no mesmo caminho e um apagaria o outro sem aviso."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    mapper = controller.split("function autoMapFields", 1)[1].split("\n      }", 1)[0]

    assert "const usados = new Map()" in mapper
    assert "if (repetido) segmento = `${segmento}_${repetido + 1}`" in mapper


def test_the_field_layer_shares_the_canvas_coordinate_system():
    """As coordenadas de cada campo vêm do canvas (convertToViewportRectangle).
    Se a camada de campos se alinhar ao palco, e o canvas for centralizado dentro
    dele, todo campo sai deslocado na horizontal — e desgruda ao rolar, porque o
    palco é que rola."""
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    styles = (PACKAGE / "styles/pdf-sheet.css").read_text(encoding="utf-8")

    doc = template.split('class="pdf-sheet-doc"', 1)
    assert len(doc) == 2, "falta o referencial comum"
    bloco = doc[1].split("</div>\n  </section>", 1)[0]
    assert "data-pdf-page-host" in bloco and "data-pdf-fields" in bloco, (
        "página e campos precisam viver dentro do mesmo referencial"
    )

    assert ".pdf-sheet-doc { position: relative;" in styles
    # Centralizar o canvas TAMBÉM o deslocaria dentro do próprio referencial.
    canvas = styles.split(".pdf-sheet-canvas {", 1)[1].split("}", 1)[0]
    assert "margin: 0 auto" not in canvas, "quem centraliza é o .pdf-sheet-doc"


def test_the_bar_slots_write_where_the_token_mapping_reads():
    """A escolha "este campo é o PV" só chega ao token se gravar no caminho que
    token.gw.json lê. Dois lugares, um acordo: se separarem, a barra fica parada
    sem nada acusar."""
    import re

    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    bloco = controller.split("const BAR_SLOTS = [", 1)[1].split("];", 1)[0]
    slots = dict(re.findall(r'key: "(\w+)", path: "([\w.]+)"', bloco))
    assert slots, "o teste precisa achar os slots"

    token = _json("mappings/token.gw.json")["character"]
    assert slots["bar1Value"] == token["bars"]["bar_1"]["value"]
    assert slots["bar1Max"] == token["bars"]["bar_1"]["max"]
    assert slots["bar2Value"] == token["bars"]["bar_2"]["value"]
    assert slots["bar2Max"] == token["bars"]["bar_2"]["max"]
    assert slots["initiative"] == token["initiative"]
    assert slots["defense"] == token["defense"]

    # O campo escolhido grava DIRETO no caminho canônico. Espelhar de
    # sheet.fields.X para sheet.bars.bar_1.value seria uma segunda escrita, e
    # duas escritas divergem.
    mapper = controller.split("function autoMapFields", 1)[1].split("\n      }", 1)[0]
    assert "paraBarra.get(name)" in mapper
    assert 'fields[name] = { path: daBarra, type: "number" }' in mapper


def test_the_sheet_has_the_three_tabs_the_host_can_wire():
    """O host liga abas por [role=tablist] com filhos [data-tab] e painéis irmãos
    [data-tab-panel]. Fora dessa forma, as abas não fazem nada."""
    import re

    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    assert 'role="tablist"' in template

    tabs = re.findall(r'data-tab="(\w+)"', template)
    panels = re.findall(r'data-tab-panel="(\w+)"', template)
    assert tabs == panels == ["ficha", "token", "notas"], (tabs, panels)

    # A lista e os painéis precisam ser irmãos: o host procura os painéis entre os
    # filhos do PAI da tablist.
    corpo = template.split('<div class="pdf-sheet" data-pdf-sheet>', 1)[1]
    assert corpo.index('role="tablist"') < corpo.index('data-tab-panel="ficha"')


def test_the_token_image_reuses_the_host_upload():
    """Upload de imagem tem CSRF, transmissão e atualização dos tokens da cena.
    Um pacote reimplementando isso erraria algum dos três."""
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    assert 'data-actor-image="token"' in template

    renderer = (ROOT / "static/js/sheets/actors/actor-sheet-renderer.js").read_text(encoding="utf-8")
    assert "mountImageSlots(root, bundle)" in renderer, "a ficha HTML precisa receber o quadro"
    slot = renderer.split("function mountImageSlots", 1)[1].split("\n  }", 1)[0]
    assert "imageFrame(root, kind, url, canEdit, systemId)" in slot, "é o mesmo controle da ficha nativa"

    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    assert "/game/actor/" not in controller, "o pacote não fala com rotas do host direto"


def test_biography_history_and_notes_persist_like_any_field():
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    schema = _json("schemas/actors/character.schema.json")["properties"]

    for chave in ("bio", "history", "notes"):
        # Editor de blocos, o mesmo dos diários: o host monta, desmonta e grava no
        # blur. Um <textarea> aqui seria texto plano num projeto que já tem editor.
        assert f'data-rich-editor="system.{chave}"' in template, f"{chave} sem editor"
        assert chave in schema, f"{chave} fora do schema é descartado na escrita"
        # O editor guarda um documento, não uma string.
        assert "object" in schema[chave]["type"], f"{chave} precisa aceitar documento"

    assert "token" in schema and "bars" in schema["token"]["properties"], (
        "a escolha de barra precisa de lugar no schema"
    )


def test_changing_a_bar_source_does_not_reopen_the_pdf():
    """Trocar a origem de uma barra muda só para onde o campo grava. Reconstruir a
    ficha inteira reabriria o documento: ele pisca, a página volta para a primeira,
    e parece que a ficha deu submit."""
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")

    barmap = controller.split("function buildBarMap", 1)[1].split("\n      }", 1)[0]
    assert "remapFields(ctx)" in barmap, "o change do seletor não pode chamar build()"
    assert "build(ctx)" not in barmap.replace("remapFields(ctx)", "")

    remap = controller.split("async function remapFields", 1)[1].split("\n      }", 1)[0]
    assert "viewer.open(" not in remap, "reabrir o documento é o que causa o piscar"
    assert "atual.fieldNames" in remap, "os nomes vêm do documento já aberto"
    assert "buildFields(ctx, fields, atual.viewer)" in remap


def test_field_text_is_dark_because_the_page_is_light():
    """Os campos ficam sobre a página do PDF, que é clara. Herdar a cor do tema
    escuro da modal deixava o texto num cinza quase ilegível."""
    styles = (PACKAGE / "styles/pdf-sheet.css").read_text(encoding="utf-8")
    # ".pdf-sheet-field {" também casa com ".pdf-sheet-fields > .pdf-sheet-field {";
    # o bloco que importa é a regra do próprio campo.
    campo = styles.split("\n.pdf-sheet-field {", 1)[1].split("}", 1)[0]

    assert "color: var(--pdf-field-text, #111111)" in campo, "padrão escuro, com escape"
    assert "color: inherit" not in campo, "herdar traz o cinza do tema"


def test_the_text_colour_is_a_choice_that_costs_one_repaint():
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")
    schema = _json("schemas/actors/character.schema.json")

    assert 'data-bind="system.pdf.textColor"' in template
    assert 'type="color"' in template
    assert schema["properties"]["pdf"]["properties"]["textColor"]["default"] == "#111111"

    # Uma variável no container, não estilo em 124 inputs.
    aplica = controller.split("function applyTextColor", 1)[1].split("\n      }", 1)[0]
    assert 'host.style.setProperty("--pdf-field-text"' in aplica

    # E trocar a cor não pode reconstruir: o host chama update() a cada mudança.
    update = controller.split("update(ctx) {", 1)[1].split("},", 1)[0]
    assert "applyTextColor(ctx)" in update
    assert "build(" not in update, "reconstruir aqui reabriria o PDF a cada ajuste"
