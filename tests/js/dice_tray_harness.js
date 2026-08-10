/*
 * Exercita a bandeja de dados.
 *
 * O que precisa ser provado aqui é a EXPRESSÃO: a bandeja monta texto que o
 * servidor vai avaliar, e um erro de notação só apareceria como "rolagem
 * inválida" na cara de quem joga.
 *
 * A armadilha específica: no xdice, `Ln`/`Hn` DESCARTAM os n menores/maiores —
 * não "mantêm". Vantagem em d20 é `2d20L1`. Quem vem do Foundry escreve `kh1`,
 * que aqui é sintaxe inválida. E `L` tem de vir antes de `H`.
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const SCRIPT = path.join(ROOT, "static/js/dice/dice-tray.js");
const SAVAGE_SCRIPT = path.join(ROOT, "data/packages/rulesets/savage-worlds/scripts/dice-tray.js");

let checks = 0;
let failures = 0;

function check(label, condition, detail) {
  checks += 1;
  if (condition) return;
  failures += 1;
  console.error(`FALHOU: ${label}${detail === undefined ? "" : ` — ${detail}`}`);
}

// --- DOM mínimo -------------------------------------------------------------

function makeElement(tag = "div") {
  const el = {
    tagName: tag.toUpperCase(),
    dataset: {},
    style: {},
    children: [],
    innerHTML: "",
    value: "",
    hidden: false,
    textContent: "",
    parentElement: null,
    querySelector: (sel) => el.__find(sel),
    querySelectorAll: () => [],
    closest: () => null,
    append(...nodes) {
      for (const n of nodes) {
        n.parentElement = el;
        el.children.push(n);
      }
    },
    __slots: {},
    __find(sel) {
      const chave = String(sel).replace(/[[\]]/g, "");
      return el.__slots[chave] || null;
    },
  };
  return el;
}

const root = makeElement("div");
root.dataset.roomId = "sala-1";
for (const slot of [
  "data-dice-pool", "data-dice-term-options", "data-dice-formula", "data-dice-name",
  "data-dice-modifier-value", "data-dice-history", "data-dice-status", "data-dice-bonus",
]) {
  root.__slots[slot] = makeElement(
    slot === "data-dice-formula" || slot === "data-dice-name" ? "input" : "div",
  );
}

global.document = {
  body: { dataset: {} },
  readyState: "complete",
  activeElement: null,
  addEventListener() {},
  querySelectorAll: (sel) => (String(sel).includes("dice-tray") ? [root] : []),
};
// localStorage de mentira: o histórico da bandeja é persistido nele, e é aqui
// que se prova que ele sobrevive a um reload.
const storage = new Map();
global.window = {
  localStorage: {
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
  },
};

const enviados = [];
global.fetch = async (url, init) => {
  enviados.push({ url, body: String(init.body) });
  return { ok: true, json: async () => ({}) };
};
global.window.csrfToken = () => "token-de-teste";

// --- carrega ----------------------------------------------------------------

(0, eval)(fs.readFileSync(SCRIPT, "utf8"));
const api = global.window.GravewrightDiceTray;
(0, eval)(fs.readFileSync(SAVAGE_SCRIPT, "utf8"));
check("a bandeja se publica em window.GravewrightDiceTray", Boolean(api));

const tray = api.trays.get("sala-1");
check("uma bandeja foi montada para a sala", Boolean(tray));

async function main() {
  // --- composição da expressão ------------------------------------------------
  
  const expressao = () => tray.expressao();
  
  tray.limpar();
  tray.adicionar("20");
  check("um dado vira 1dN", expressao() === "1d20", expressao());
  
  tray.adicionar("20");
  check("clicar de novo soma ao mesmo termo", expressao() === "2d20", expressao());
  
  // Vantagem: rolar dois e DESCARTAR o menor. É o L do xdice, não kh.
  tray.ajustarTermo("descartarMenores", 1);
  check("descartar o menor usa L", expressao() === "2d20L1", expressao());
  check("nada de kh: seria inválido no servidor", !expressao().includes("kh"));
  
  // Com dados suficientes dá para combinar os dois, como no 6D6L1H2 da doc.
  tray.limpar();
  tray.adicionar("6");
  for (let i = 0; i < 5; i += 1) tray.ajustarTermo("quantidade", 1);
  tray.ajustarTermo("descartarMenores", 1);
  tray.ajustarTermo("descartarMaiores", 1);
  tray.ajustarTermo("descartarMaiores", 1);
  check("combina descarte dos dois lados", expressao() === "6d6L1H2", expressao());
  check(
    "L vem antes de H, como o xdice exige",
    expressao().indexOf("L") < expressao().indexOf("H"),
    expressao(),
  );
  
  // Não dá para descartar tudo: sobraria nada para somar.
  tray.limpar();
  tray.adicionar("6");
  tray.ajustarTermo("descartarMenores", 1);
  check("um dado só não pode ter descarte", expressao() === "1d6", expressao());
  
  tray.ajustarTermo("quantidade", 1);
  tray.ajustarTermo("descartarMenores", 1);
  check("com dois dados, descartar um é permitido", expressao() === "2d6L1", expressao());
  tray.ajustarTermo("descartarMenores", 1);
  check("mas não os dois", expressao() === "2d6L1", expressao());
  
  // Explosão e vários termos
  tray.limpar();
  tray.adicionar("6");
  tray.ajustarTermo("explode", 0);
  check("explodir vira !", expressao() === "1d6!", expressao());
  
  tray.limpar();
  tray.adicionar("6");
  tray.adicionar("8");
  check("termos diferentes se somam", expressao() === "1d6+1d8", expressao());
  
  tray.modificador = 3;
  check("modificador positivo", expressao() === "1d6+1d8+3", expressao());
  tray.modificador = -2;
  check("modificador negativo usa sinal, não +-", expressao() === "1d6+1d8-2", expressao());
  tray.modificador = 0;
  check("modificador zero não aparece", expressao() === "1d6+1d8", expressao());
  
  // Dados especiais
  tray.limpar();
  tray.adicionar("%");
  check("d% é notação do xdice", expressao() === "1d%", expressao());
  tray.limpar();
  tray.adicionar("F");
  check("dF para fudge", expressao() === "1dF", expressao());
  
  // --- dado dadoExtra (Savage Worlds) -------------------------------------------
  // Rola o dado de atributo E um d6 dadoExtra, e vale o MELHOR. Os dois explodem.
  tray.limpar();
  tray.adicionar("8");
  root.__slots["data-dice-bonus"].checked = true;
  check("dadoExtra vira max(atributo, d6)", expressao() === "max(1d8!,1d6!)", expressao());
  check("o d6 dadoExtra explode", expressao().includes("1d6!"));
  check("o dado de atributo também explode", expressao().includes("1d8!"), expressao());

  tray.modificador = 2;
  check(
    "o modificador soma FORA do max, não dentro de um dos lados",
    expressao() === "max(1d8!,1d6!)+2",
    expressao(),
  );

  root.__slots["data-dice-bonus"].checked = false;
  check("desligar volta ao normal, sem explosão forçada", expressao() === "1d8+2", expressao());

  // Limpar a bandeja também desliga o dadoExtra: senão a próxima rolagem sai
  // dadoExtra sem ninguém ter pedido.
  root.__slots["data-dice-bonus"].checked = true;
  tray.limpar();
  tray.adicionar("20");
  check("limpar desliga o dadoExtra", expressao() === "1d20", expressao());

  // --- fórmula escrita à mão ---------------------------------------------------
  
  tray.limpar();
  tray.adicionar("20");
  tray.formulaManual = "4d6L1";
  check("texto escrito ganha dos botões", expressao() === "4d6L1", expressao());
  tray.adicionar("6");
  check("mexer nos botões devolve o controle a eles", expressao() !== "4d6L1", expressao());
  
  // --- envio -------------------------------------------------------------------
  
  tray.limpar();
  tray.adicionar("20");
  tray.modificador = 5;
  enviados.length = 0;
  
  await tray.rolar(false);
  check("rolar envia uma requisição", enviados.length === 1);
  check("vai para o chat, não para uma rota nova", enviados[0]?.url === "/game/chat", enviados[0]?.url);
  check(
    "usa o comando /roll, que já persiste e vira cartão",
    decodeURIComponent((enviados[0]?.body || "").replace(/\+/g, "%20")).includes("message=/roll 1d20+5"),
    enviados[0]?.body,
  );
  check("manda o csrf junto", (enviados[0]?.body || "").includes("csrf_token=token-de-teste"));
  
  await tray.rolar(true);
  check(
    "rolagem para o GM usa /gmroll",
    decodeURIComponent((enviados[1]?.body || "").replace(/\+/g, "%20")).includes("message=/gmroll 1d20+5"),
    enviados[1]?.body,
  );
  
  // --- histórico ----------------------------------------------------------------
  
  check(
    "a expressão rolada entra no histórico",
    tray.historico[0]?.expressao === "1d20+5",
    JSON.stringify(tray.historico),
  );
  await tray.rolar(false);
  check(
    "rolar a mesma coisa não duplica o histórico",
    tray.historico.length === 1,
    JSON.stringify(tray.historico),
  );

  // O nome é só rótulo: não pode vazar para a expressão que vai ao servidor.
  tray.nome = "Ataque com espada";
  enviados.length = 0;
  await tray.rolar(false);
  const mensagemNomeada = decodeURIComponent((enviados[0]?.body || "").replace(/\+/g, "%20"));
  check(
    "nomear não muda a expressão enviada",
    mensagemNomeada.includes("message=/roll 1d20+5 #"),
    enviados[0]?.body,
  );
  check(
    "o nome vai como rótulo depois do #, para o chat e o toast",
    mensagemNomeada.includes("# Ataque com espada"),
    enviados[0]?.body,
  );
  check(
    "o nome fica na entrada do histórico",
    tray.historico[0]?.nome === "Ataque com espada" && tray.historico[0]?.expressao === "1d20+5",
    JSON.stringify(tray.historico),
  );
  check(
    "a mesma fórmula com e sem nome são atalhos diferentes",
    tray.historico.length === 2,
    JSON.stringify(tray.historico),
  );

  // Rolar sem nome nenhum continua valendo: o campo nunca trava a rolagem.
  tray.nome = "";
  tray.limpar();
  tray.adicionar("6");
  enviados.length = 0;
  await tray.rolar(false);
  check("sem nome a rolagem sai igual", enviados.length === 1, enviados[0]?.body);
  check("e entra no histórico sem rótulo", tray.historico[0]?.nome === "", JSON.stringify(tray.historico));

  tray.limpar();
  tray.usar(tray.historico.findIndex((e) => e.nome === "Ataque com espada"));
  check("reusar do histórico preenche a fórmula", expressao() === "1d20+5", expressao());
  check("e devolve o nome junto", tray.nome === "Ataque com espada", tray.nome);

  const antes = tray.historico.length;
  tray.esquecer(0);
  check("dá para tirar uma entrada do histórico", tray.historico.length === antes - 1);

  // Reload: o histórico é da pessoa, não da sessão.
  const salvo = JSON.stringify(tray.historico);
  api.trays.delete("sala-1");
  api.montar();
  const recarregada = api.trays.get("sala-1");
  check(
    "o histórico volta depois de recarregar a página",
    JSON.stringify(recarregada.historico) === salvo,
    JSON.stringify(recarregada.historico),
  );
  check("a bandeja recarregada é outra instância", recarregada !== tray);

  // Bandeja vazia não manda nada: um POST com expressão vazia só viraria erro.
  tray.limpar();
  enviados.length = 0;
  await tray.rolar(false);
  check("bandeja vazia não envia", enviados.length === 0);
  

}

main()
  .then(() => {
    console.log(`${checks - failures}/${checks} verificações passaram`);
    if (failures) process.exit(1);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
