/*
 * O pdf.js vendorizado funciona num motor sem as APIs mais novas?
 *
 * O build MODERNO do pdf.js 6.x usa APIs de ponta sem checar se existem:
 *
 *   Map.prototype.getOrInsertComputed  — proposta recente; Firefox tem, Chrome não
 *   Uint8Array.prototype.toHex         — Chrome 140+
 *   Uint8Array.fromBase64 / toBase64   — Chrome 140+
 *
 * Onde isso dói: `getOrInsertComputed` está no caminho que resolve recursos de
 * FORMULÁRIO, e `toHex` no de DESCRIPTOGRAFIA — exatamente por onde passa uma
 * ficha de RPG preenchível, que ainda por cima costuma vir protegida por senha de
 * dono. Com o build moderno o documento nem abre num navegador um pouco atrás.
 *
 * Por isso o pacote traz o build LEGACY, que carrega os próprios polyfills. Este
 * harness prova isso: o Node 24 não tem nenhuma das três APIs, então serve de
 * espelho de um navegador atrasado. Se alguém trocar o vendor pelo build moderno,
 * este teste falha na hora, em vez de a ficha falhar na mão de quem joga.
 */
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const ROOT = path.resolve(__dirname, "../..");
const PACKAGE = path.join(ROOT, "data/packages/rulesets/gravewright-pdf-system");
const VENDOR = path.join(PACKAGE, "vendor");
const SHEET = path.join(PACKAGE, "assets/sheets/blank-a4.pdf");

let checks = 0;
let failures = 0;

function check(label, condition, detail) {
  checks += 1;
  if (condition) return;
  failures += 1;
  console.error(`FALHOU: ${label}${detail === undefined ? "" : ` — ${detail}`}`);
}

// --- ambiente mínimo de navegador -------------------------------------------
globalThis.DOMMatrix = class {};
globalThis.Path2D = class {};
globalThis.ImageData = class {};
globalThis.btoa ||= (text) => Buffer.from(text, "binary").toString("base64");
globalThis.atob ||= (text) => Buffer.from(text, "base64").toString("binary");

async function main() {
  // --- o Node reproduz mesmo a lacuna que queremos cobrir? ------------------
  const faltando = {
    "Map.getOrInsertComputed": typeof Map.prototype.getOrInsertComputed !== "function",
    "Uint8Array.toHex": typeof Uint8Array.prototype.toHex !== "function",
    "Uint8Array.fromBase64": typeof Uint8Array.fromBase64 !== "function",
  };
  const ausentes = Object.entries(faltando).filter(([, ausente]) => ausente);
  check(
    "o ambiente do teste espelha um navegador sem as APIs novas",
    ausentes.length > 0,
    "este Node já tem tudo; o harness deixaria de provar o preenchimento",
  );

  // --- o pdf.js precisa se virar sozinho ------------------------------------
  const pdfjs = await import(pathToFileURL(path.join(VENDOR, "pdf.mjs")).href);

  check(
    "o build vendorizado instala Map.getOrInsertComputed",
    typeof Map.prototype.getOrInsertComputed === "function",
    "é o build moderno? ele assume a API pronta e falha em Chrome",
  );
  check(
    "o build vendorizado instala Uint8Array.toHex",
    typeof Uint8Array.prototype.toHex === "function",
  );
  check(
    "o build vendorizado instala Uint8Array.fromBase64",
    typeof Uint8Array.fromBase64 === "function",
  );

  // O worker roda em contexto separado e não herda nada da página: precisa
  // carregar os próprios polyfills, senão só a página funciona.
  const worker = fs.readFileSync(path.join(VENDOR, "pdf.worker.mjs"), "utf8");
  check(
    "o worker vendorizado também traz os polyfills",
    /getOrInsertComputed\s*[:=(]/.test(worker) && worker.includes("core-js"),
    "worker sem polyfill quebra assim que o documento é aberto de verdade",
  );

  // --- o visualizador só pode chamar o que a biblioteca REAL tem -------------
  // O dublê do pdf_viewer_harness é escrito por mim; se ele oferecer um método
  // que a biblioteca não tem, o harness passa a provar a minha suposição em vez
  // do código. Foi assim que `convertToViewportRectangle` — removido no pdf.js 6
  // — sobreviveu a uma suíte verde e só apareceu no navegador.
  function apisUsadas(fonte, alvo) {
    const encontrado = new Set();
    const padrao = new RegExp(String.raw`\b${alvo}\.(\w+)\(`, "g");
    let m;
    while ((m = padrao.exec(fonte)) !== null) encontrado.add(m[1]);
    return [...encontrado];
  }

  const viewerSource = fs.readFileSync(path.join(PACKAGE, "scripts/pdf-viewer.js"), "utf8");

  // --- o teste que importa: o pdf.js abre a ficha ---------------------------
  pdfjs.GlobalWorkerOptions.workerSrc = pathToFileURL(path.join(VENDOR, "pdf.worker.mjs")).href;

  const data = new Uint8Array(fs.readFileSync(SHEET));
  let doc = null;
  try {
    doc = await pdfjs.getDocument({ data, isEvalSupported: false }).promise;
  } catch (error) {
    check("o pdf.js abre o PDF do pacote", false, `${error.name}: ${error.message}`);
  }

  if (doc) {
    check("o documento tem páginas", doc.numPages >= 1, doc.numPages);

    const page = await doc.getPage(1);
    const viewport = page.getViewport({ scale: 1 });

    for (const metodo of apisUsadas(viewerSource, "viewport")) {
      check(
        `viewport.${metodo}() existe na biblioteca real`,
        typeof viewport[metodo] === "function",
        "o visualizador chama um método que o pdf.js não tem",
      );
    }
    for (const metodo of apisUsadas(viewerSource, "page")) {
      check(`page.${metodo}() existe na biblioteca real`, typeof page[metodo] === "function");
    }
    for (const metodo of apisUsadas(viewerSource, "lib")) {
      check(`pdfjs.${metodo}() existe na biblioteca real`, typeof pdfjs[metodo] === "function");
    }
    check(
      "a página é A4",
      Math.round(viewport.width) === 595 && Math.round(viewport.height) === 842,
      `${viewport.width.toFixed(0)} x ${viewport.height.toFixed(0)}`,
    );

    // O template de fábrica é só um aviso: não tem campo nenhum de propósito.
    // Quem traz campos é o PDF que o GM envia.
    const anns = await page.getAnnotations({ intent: "display" });
    const campos = anns.filter((a) => a.fieldName && a.subtype === "Widget");
    check("o template de fábrica não finge ter campos", campos.length === 0, `${campos.length}`);

    // E o aviso precisa estar legível: um PDF que abre em branco não ensina nada.
    const texto = (await page.getTextContent()).items.map((i) => i.str).join(" ");
    for (const trecho of ["biblioteca de assets", "asset library", "Enviar ficha PDF"]) {
      check(`o aviso menciona "${trecho}"`, texto.includes(trecho));
    }

    await doc.cleanup?.();
  }

  console.log(`${checks - failures}/${checks} verificações passaram`);
  if (failures) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
