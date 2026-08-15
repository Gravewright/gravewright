/*
 * Adaptador de renderização do Gravewright PDF System.
 *
 * Desenha a página com pdf.js e devolve, para cada campo de formulário do PDF,
 * onde ele está na tela. É isso que permite ao mapeamento falar só de NOMES de
 * campo: as coordenadas vêm do próprio arquivo, via getAnnotations().
 *
 * O runtime do pdf.js (3 MB entre módulo e worker) é declarado como asset e
 * importado sob demanda: nunca no carregamento da página de jogo. Quem não abre
 * uma ficha PDF não paga por ele.
 */
(() => {
  const PACKAGE_ID = "gravewright-pdf-system";
  let pdfjs = null;

  // Quem resolve caminho de asset é o SDK (sdk.package.assetUrl), passado no
  // open(). O visualizador carrega antes de qualquer setup() e não tem o sdk em
  // mãos, então guardamos o resolvedor em vez de remontar a URL aqui: duas
  // montagens seriam duas coisas para manter em acordo.
  let asset = (relative) => `/sdk/packages/${PACKAGE_ID}/asset/${relative}`;

  async function library() {
    if (pdfjs) return pdfjs;
    // Build "legacy" do pdf.js: ele traz os próprios polyfills (core-js) para as
    // APIs novas que o build moderno assumia prontas: Map.getOrInsertComputed e
    // Uint8Array.toHex, que ficam justamente nos caminhos de formulário e de
    // descriptografia. É o build certo para um parque de navegadores real.
    pdfjs = await import(asset("vendor/pdf.mjs"));
    // O worker roda em 'self' pela CSP; sem isto o pdf.js procura um irmão
    // "./pdf.worker.mjs" relativo à página, que não existe. O worker legacy
    // também se preenche sozinho, no contexto dele.
    pdfjs.GlobalWorkerOptions.workerSrc = asset("vendor/pdf.worker.mjs");
    return pdfjs;
  }

  const state = {
    doc: null,
    host: null,
    url: "",
    page: 1,
    zoom: 1,
    spread: false,
    // nome do campo -> { page, rect } em coordenadas de PDF
    fields: new Map(),
    // nome do campo -> input da Gravewright, para reposicionar a cada render
    bound: new Map(),
    onPageChange: null,
  };

  function canvasFor(index) {
    const canvas = document.createElement("canvas");
    canvas.className = "pdf-sheet-canvas";
    canvas.dataset.pdfPage = String(index);
    return canvas;
  }

  // Um campo do PDF pode aparecer em qualquer página; guardamos onde, para só
  // mostrar os inputs da página visível.
  async function indexFields(doc) {
    state.fields.clear();
    for (let number = 1; number <= doc.numPages; number += 1) {
      const page = await doc.getPage(number);
      const annotations = await page.getAnnotations({ intent: "display" });
      for (const annotation of annotations) {
        if (!annotation.fieldName || annotation.subtype !== "Widget") continue;
        if (!state.fields.has(annotation.fieldName)) {
          state.fields.set(annotation.fieldName, {
            page: number,
            rect: annotation.rect,
            fieldType: annotation.fieldType || "Tx",
            readOnly: Boolean(annotation.readOnly),
          });
        }
      }
    }
  }

  // Esconder é decisão do conjunto de páginas à vista, não de uma página. Em
  // página dupla, deixar cada página esconder o que não é dela faria a segunda
  // apagar os campos que a primeira acabou de posicionar.
  function hideFieldsOutside(visiblePages) {
    for (const [name, input] of state.bound) {
      const field = state.fields.get(name);
      if (!field || !visiblePages.has(field.page)) input.style.display = "none";
    }
  }

  // Posiciona cada input sobre o retângulo do seu campo. O retângulo do PDF tem
  // origem embaixo à esquerda, então os cantos passam pelo viewport, que aplica a
  // inversão do eixo Y, a escala e a rotação de uma vez.
  //
  // São dois cantos, um de cada vez: o pdf.js 6 só expõe convertToViewportPoint.
  // (convertToViewportRectangle existiu em versões antigas e foi removido.)
  function positionFields(viewport, pageNumber, offsetTop) {
    for (const [name, input] of state.bound) {
      const field = state.fields.get(name);
      if (!field || field.page !== pageNumber) continue;
      const [x1, y1] = viewport.convertToViewportPoint(field.rect[0], field.rect[1]);
      const [x2, y2] = viewport.convertToViewportPoint(field.rect[2], field.rect[3]);
      input.style.display = "";
      input.style.left = `${Math.min(x1, x2)}px`;
      input.style.top = `${Math.min(y1, y2) + offsetTop}px`;
      input.style.width = `${Math.abs(x2 - x1)}px`;
      input.style.height = `${Math.abs(y2 - y1)}px`;
    }
  }

  async function render() {
    if (!state.doc || !state.host) return;
    state.host.replaceChildren();

    const first = state.page;
    const last = state.spread ? Math.min(first + 1, state.doc.numPages) : first;
    let offsetTop = 0;

    const visible = new Set();
    for (let number = first; number <= last; number += 1) visible.add(number);
    hideFieldsOutside(visible);

    for (let number = first; number <= last; number += 1) {
      const page = await state.doc.getPage(number);
      const viewport = page.getViewport({ scale: state.zoom });
      const canvas = canvasFor(number);
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      state.host.append(canvas);

      await page.render({
        canvasContext: canvas.getContext("2d"),
        viewport,
        transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0],
      }).promise;

      positionFields(viewport, number, offsetTop);
      offsetTop += viewport.height;
    }

    state.onPageChange?.({ page: state.page, pages: state.doc.numPages });
  }

  async function fitPage() {
    if (!state.doc || !state.host) return;
    const page = await state.doc.getPage(state.page);
    const unscaled = page.getViewport({ scale: 1 });
    const available = state.host.parentElement?.clientHeight || unscaled.height;
    state.zoom = Math.max(0.1, Math.min(8, available / unscaled.height));
    await render();
  }

  window.GravewrightPdfViewer = {
    async open({ host, url, page = 1, zoom = 1, spread = false, onPageChange = null, assetUrl = null }) {
      if (assetUrl) asset = assetUrl;
      const lib = await library();
      state.host = host;
      state.url = url;
      state.page = page;
      state.zoom = zoom;
      state.spread = spread;
      state.onPageChange = onPageChange;
      state.bound.clear();
      state.doc = await lib.getDocument({ url }).promise;
      await indexFields(state.doc);
      await render();
      return { pages: state.doc.numPages, fields: [...state.fields.keys()] };
    },

    // O controlador cria o input; aqui ele só passa a ser posicionado. Campo que
    // o PDF não tem fica escondido em vez de flutuar num canto qualquer.
    placeField(input, fieldName) {
      state.bound.set(fieldName, input);
      const field = state.fields.get(fieldName);
      if (!field) {
        input.style.display = "none";
        return false;
      }
      if (field.readOnly) input.readOnly = true;
      return true;
    },

    fieldNames: () => [...state.fields.keys()],

    // "Tx" (texto), "Btn" (caixa/botão), "Ch" (lista). Quem cria os inputs precisa
    // disto: uma caixa de seleção renderizada como campo de texto pede que a
    // pessoa digite onde deveria marcar.
    fieldType: (name) => state.fields.get(name)?.fieldType || "Tx",

    // Os inputs só existem DEPOIS do open(): num PDF enviado, os nomes dos campos
    // vêm do arquivo, então o controlador precisa abrir para saber o que criar. Só
    // que quem posiciona é o render(), e ele já rodou com a lista de inputs vazia.
    // Sem esta segunda passada os campos ficam sem left/top e empilham todos na
    // origem, o que aparece como uma única barra no canto da ficha.
    refresh: () => render(),

    async nextPage() {
      if (!state.doc || state.page >= state.doc.numPages) return;
      state.page += state.spread ? 2 : 1;
      state.page = Math.min(state.page, state.doc.numPages);
      await render();
    },
    async prevPage() {
      if (!state.doc || state.page <= 1) return;
      state.page -= state.spread ? 2 : 1;
      state.page = Math.max(1, state.page);
      await render();
    },
    async goToPage(page) {
      if (!state.doc) return null;
      const target = Math.max(1, Math.min(state.doc.numPages, Number(page) || 1));
      state.page = target;
      await render();
      return state.page;
    },
    async goToAnchor(anchor) {
      if (!state.doc || !anchor) return null;
      const destination = await state.doc.getDestination(String(anchor));
      if (!destination) return null;
      const reference = destination[0];
      const index = typeof reference === "number" ? reference : await state.doc.getPageIndex(reference);
      state.page = Math.max(1, Math.min(state.doc.numPages, index + 1));
      await render();
      return state.page;
    },
    async search(query) {
      if (!state.doc) return [];
      const needle = String(query || "").trim().toLocaleLowerCase();
      if (!needle) return [];
      const matches = [];
      for (let number = 1; number <= state.doc.numPages; number += 1) {
        const page = await state.doc.getPage(number);
        const content = await page.getTextContent();
        const text = content.items.map((item) => item.str || "").join(" ");
        if (text.toLocaleLowerCase().includes(needle)) matches.push({ page: number, text });
      }
      return matches;
    },
    async zoomBy(factor) {
      state.zoom = Math.max(0.1, Math.min(8, state.zoom * factor));
      await render();
    },
    fitPage,
    async toggleSpread() {
      state.spread = !state.spread;
      await render();
      return state.spread;
    },
    viewState: () => ({ page: state.page, zoom: state.zoom, spread: state.spread }),
    currentPage: () => state.doc ? state.page : null,

    // Baixa o template, não uma cópia preenchida: os valores são da ficha, e o
    // arquivo continua sendo só a aparência.
    download(name) {
      if (!state.url) return;
      const link = document.createElement("a");
      link.href = state.url;
      link.download = `${name || "sheet"}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
    },

    close() {
      state.doc?.destroy?.();
      state.doc = null;
      state.host?.replaceChildren();
      state.host = null;
      state.bound.clear();
      state.fields.clear();
    },
  };
})();
