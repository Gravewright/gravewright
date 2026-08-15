/*
 * Exercita o adaptador de renderização do Gravewright PDF System.
 *
 * O que importa provar aqui não é o pdf.js (não é nosso), e sim a ponte: que os
 * inputs da ficha pousam exatamente sobre os retângulos que o PDF declara, que
 * campo de outra página some, e que a inversão de eixo do PDF é respeitada. Um
 * erro de um destes deixa a ficha bonita e os campos no lugar errado, o tipo de
 * defeito que nenhuma leitura de arquivo pega.
 *
 * O resolvedor de asset é injetável (open({assetUrl})), então apontamos o
 * import() para um pdf.js falso em disco e rodamos o caminho real.
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const { pathToFileURL } = require("url");

const ROOT = path.resolve(__dirname, "../..");
const PACKAGE = path.join(ROOT, "data/packages/rulesets/gravewright-pdf-system");

let checks = 0;
let failures = 0;

function check(label, condition, detail) {
  checks += 1;
  if (condition) return;
  failures += 1;
  console.error(`FALHOU: ${label}${detail === undefined ? "" : `: ${detail}`}`);
}

function near(a, b, tolerance = 1e-6) {
  return Math.abs(a - b) <= tolerance;
}

// --- DOM mínimo -------------------------------------------------------------

function makeElement(tag) {
  return {
    tagName: tag,
    style: {},
    dataset: {},
    className: "",
    children: [],
    width: 0,
    height: 0,
    readOnly: false,
    parentElement: null,
    append(...nodes) {
      for (const node of nodes) {
        node.parentElement = this;
        this.children.push(node);
      }
    },
    replaceChildren() {
      this.children = [];
    },
    getContext: () => ({}),
    click() {
      this.clicked = true;
    },
    remove() {
      if (!this.parentElement) return;
      const at = this.parentElement.children.indexOf(this);
      if (at >= 0) this.parentElement.children.splice(at, 1);
    },
  };
}

global.window = { devicePixelRatio: 1 };
global.document = {
  createElement: makeElement,
  body: makeElement("body"),
};

// --- pdf.js falso -----------------------------------------------------------
// Uma página A4 (595x842) com dois campos, e uma segunda página com um terceiro.
// Retângulos em coordenadas de PDF: origem embaixo à esquerda.

const PAGES = [
  [
    { fieldName: "CharacterName", subtype: "Widget", rect: [50, 750, 300, 780], fieldType: "Tx" },
    { fieldName: "HP", subtype: "Widget", rect: [400, 700, 460, 730], fieldType: "Tx", readOnly: true },
    // ruído que o indexador precisa ignorar
    { subtype: "Link", rect: [0, 0, 10, 10] },
    { fieldName: "Nota", subtype: "Popup", rect: [0, 0, 10, 10] },
  ],
  [{ fieldName: "Notes", subtype: "Widget", rect: [50, 100, 545, 400], fieldType: "Tx" }],
];

const fakeLibrary = `
const PAGES = ${JSON.stringify(PAGES)};
export const GlobalWorkerOptions = { workerSrc: "" };
export function getDocument({ url }) {
  const doc = {
    url,
    numPages: PAGES.length,
    destroyed: false,
    destroy() { this.destroyed = true; },
    async getPage(number) {
      return {
        async getAnnotations({ intent }) {
          if (intent !== "display") throw new Error("intent inesperado: " + intent);
          return PAGES[number - 1];
        },
        getViewport({ scale }) {
          return {
            width: 595 * scale,
            height: 842 * scale,
            scale,
            // A MESMA superficie do pdf.js 6: um ponto por vez. Um duble que
            // oferece mais do que a biblioteca real transforma o harness em prova
            // da minha suposicao, nao do codigo: foi assim que
            // convertToViewportRectangle (que nao existe mais) passou batido.
            convertToViewportPoint(x, y) {
              return [x * scale, (842 - y) * scale];
            },
          };
        },
        render() {
          return { promise: Promise.resolve() };
        },
      };
    },
  };
  globalThis.__lastDoc = doc;
  return { promise: Promise.resolve(doc) };
}
`;

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "gw-pdf-"));
const fakePath = path.join(tempDir, "fake-pdf.mjs");
fs.writeFileSync(fakePath, fakeLibrary, "utf8");

const requested = [];
const assetUrl = (relative) => {
  requested.push(relative);
  if (relative === "vendor/pdf.mjs") return pathToFileURL(fakePath).href;
  return `/sdk/packages/gravewright-pdf-system/asset/${relative}`;
};

// --- carrega o adaptador ----------------------------------------------------

const source = fs.readFileSync(path.join(PACKAGE, "scripts/pdf-viewer.js"), "utf8");
(0, eval)(source);
const viewer = global.window.GravewrightPdfViewer;

check("o adaptador se publica em window.GravewrightPdfViewer", Boolean(viewer));

async function main() {
  // Antes de abrir, nada pode explodir: a ficha chama estes handlers pelos botões
  // da barra mesmo com o documento ainda não carregado.
  check("viewState responde antes de abrir", viewer.viewState().page === 1);
  check("fieldNames vazio antes de abrir", viewer.fieldNames().length === 0);
  await viewer.nextPage();
  await viewer.prevPage();
  await viewer.zoomBy(2);
  await viewer.fitPage();
  viewer.download("x");
  viewer.close();
  check("controles são inertes sem documento", true);

  const host = makeElement("div");
  host.clientHeight = 421;
  const stage = makeElement("div");
  stage.clientHeight = 421;
  stage.append(host);

  const pageChanges = [];
  const opened = await viewer.open({
    host,
    url: "/sdk/packages/gravewright-pdf-system/asset/assets/sheets/blank-a4.pdf",
    page: 1,
    zoom: 1,
    spread: false,
    assetUrl,
    onPageChange: (info) => pageChanges.push(info),
  });

  check("o runtime do pdf.js vem do resolvedor de asset", requested.includes("vendor/pdf.mjs"));
  check(
    "o worker recebe caminho explícito de asset do pacote",
    requested.includes("vendor/pdf.worker.mjs"),
    requested.join(", "),
  );
  check("abre relatando o total de páginas", opened.pages === 2, opened.pages);
  check(
    "indexa só campos de formulário, ignorando Link e Popup",
    JSON.stringify(opened.fields) === JSON.stringify(["CharacterName", "HP", "Notes"]),
    JSON.stringify(opened.fields),
  );
  check("avisa a página inicial", pageChanges.length === 1 && pageChanges[0].pages === 2);

  // --- posicionamento -------------------------------------------------------
  const name = makeElement("input");
  const hp = makeElement("input");
  const notes = makeElement("input");
  const ghost = makeElement("input");

  check("placeField aceita campo existente", viewer.placeField(name, "CharacterName") === true);
  viewer.placeField(hp, "HP");
  viewer.placeField(notes, "Notes");
  check("placeField recusa campo que o PDF não tem", viewer.placeField(ghost, "NaoExiste") === false);
  check("campo inexistente fica escondido", ghost.style.display === "none");
  check("campo somente-leitura do PDF trava o input", hp.readOnly === true);
  check("campo comum não vira somente-leitura", name.readOnly === false);

  // Os inputs são registrados DEPOIS do open(), porque num PDF enviado os nomes
  // dos campos vêm do arquivo. Antes do refresh eles ainda não têm posição: este
  // é o estado em que a ficha ficava presa: tudo empilhado na origem.
  check(
    "recém-registrado, o input ainda não tem posição",
    !name.style.left,
    `left=${name.style.left}`,
  );

  await viewer.refresh();

  // rect [50, 750, 300, 780] em zoom 1 → x=50, y=842-780=62, w=250, h=30
  check("posição X vem do retângulo do PDF", name.style.left === "50px", name.style.left);
  check("o eixo Y é invertido (origem do PDF é embaixo)", name.style.top === "62px", name.style.top);
  check("largura do campo", name.style.width === "250px", name.style.width);
  check("altura do campo", name.style.height === "30px", name.style.height);
  check("campo de outra página some", notes.style.display === "none", notes.style.display);
  check("campo da página visível aparece", name.style.display === "");

  // --- zoom -----------------------------------------------------------------
  await viewer.zoomBy(2);
  check("zoom escala a posição", name.style.left === "100px", name.style.left);
  check("zoom escala o tamanho", name.style.width === "500px", name.style.width);
  check("zoom é registrado no estado", near(viewer.viewState().zoom, 2), viewer.viewState().zoom);

  await viewer.zoomBy(1000);
  check("zoom tem teto", viewer.viewState().zoom <= 8, viewer.viewState().zoom);
  await viewer.zoomBy(1 / 100000);
  check("zoom tem piso", viewer.viewState().zoom >= 0.1, viewer.viewState().zoom);

  await viewer.fitPage();
  check("fitPage cabe a página na altura disponível", near(viewer.viewState().zoom, 0.5), viewer.viewState().zoom);

  // --- navegação ------------------------------------------------------------
  await viewer.nextPage();
  check("avança de página", viewer.viewState().page === 2);
  check("o campo da página 2 aparece", notes.style.display === "");
  check("o campo da página 1 some", name.style.display === "none");

  await viewer.nextPage();
  check("não passa da última página", viewer.viewState().page === 2);
  await viewer.prevPage();
  check("volta de página", viewer.viewState().page === 1);
  await viewer.prevPage();
  check("não passa da primeira página", viewer.viewState().page === 1);

  // --- página dupla ---------------------------------------------------------
  const spread = await viewer.toggleSpread();
  check("toggleSpread devolve o novo estado", spread === true);
  check("página dupla desenha dois canvases", host.children.length === 2, host.children.length);
  check("com as duas páginas à vista, ambos os campos aparecem",
    name.style.display === "" && notes.style.display === "");

  // A segunda página é desenhada abaixo da primeira: o campo dela precisa do
  // deslocamento, senão fica sobreposto ao topo.
  const zoom = viewer.viewState().zoom;
  const expectedTop = (842 - 400) * zoom + 842 * zoom;
  check(
    "campo da segunda página é deslocado pela altura da primeira",
    near(parseFloat(notes.style.top), expectedTop, 0.5),
    `${notes.style.top} vs ${expectedTop}px`,
  );

  await viewer.toggleSpread();
  check("volta para página única", host.children.length === 1);

  // --- download e fechamento ------------------------------------------------
  viewer.download("Aria");
  check("o download é do template, não de uma cópia preenchida",
    !global.document.body.children.length, "o link não pode ficar preso no DOM");

  const doc = globalThis.__lastDoc;
  viewer.close();
  check("fechar libera o documento do pdf.js", doc.destroyed === true);
  check("fechar limpa o palco", host.children.length === 0);
  check("fechar esquece os campos", viewer.fieldNames().length === 0);

  fs.rmSync(tempDir, { recursive: true, force: true });

  console.log(`${checks - failures}/${checks} verificações passaram`);
  if (failures) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
