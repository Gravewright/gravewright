/*
 * "Sem limite" como pergunta, não como zero escondido.
 *
 * Alcance de luz, de visão e de shader guardam zero para dizer "ilimitado". Como
 * armazenamento é cômodo; como botão é o contrário do que a régua promete -
 * arrastar para o mínimo devia dar o MENOR alcance, e dava o maior.
 *
 * O que este harness cobra é o comportamento do par régua+checkbox, incluindo o
 * caso que faz a correção valer alguma coisa: desmarcar não pode devolver a
 * pessoa a zero, que é exatamente o lugar de onde ela quis sair.
 *
 * Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const SCRIPT = path.resolve(__dirname, "../../static/js/lighting/limit-toggle.js");

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

function buildPanel({ value = 0, fallback = 8 } = {}) {
    const range = { value: String(value), disabled: false, dataset: { limitDefault: String(fallback) } };
    const check = { checked: false, type: "checkbox" };
    const panel = {
        querySelector: (selector) => {
            if (selector.includes("data-limit-target")) return range;
            if (selector.includes("data-limit-for")) return check;
            return null;
        },
    };
    return { panel, range, check };
}

const win = {};
new Function("window", fs.readFileSync(SCRIPT, "utf8"))(win);
const limits = win.GravewrightLimits;

// --- abrir o painel ---------------------------------------------------------
{
    const zero = buildPanel({ value: 0 });
    limits.paint(zero.panel, "radius");
    check("quem gravou zero reabre com 'sem limite' marcado", zero.check.checked === true);
    // Régua que não decide mais nada não deve aceitar arrasto: ela mentiria sobre
    // o que está valendo.
    check("e com a regua fora de acao", zero.range.disabled === true);

    const limitado = buildPanel({ value: 12 });
    limits.paint(limitado.panel, "radius");
    check("com alcance, o checkbox fica solto", limitado.check.checked === false);
    check("e a regua responde", limitado.range.disabled === false);
}

// --- marcar e desmarcar -----------------------------------------------------
{
    const world = buildPanel({ value: 12 });
    limits.paint(world.panel, "radius");
    world.check.checked = true;
    const semLimite = limits.next(world.panel, "radius");
    check("marcar manda zero para o servidor", semLimite === 0, `${semLimite}`);
    check("e a regua acompanha", world.range.value === "0" && world.range.disabled === true);

    world.check.checked = false;
    const voltou = limits.next(world.panel, "radius");
    // O ponto inteiro da correcao: sem isto, desmarcar devolve zero: que e
    // "ilimitado" de novo. O checkbox nao teria como ser desmarcado.
    check("desmarcar volta num valor util, nao em zero", voltou === 8, `${voltou}`);
    check("e a regua volta a responder", world.range.disabled === false);
}

// --- o valor escrito na tela ------------------------------------------------
{
    const world = buildPanel({ value: 0 });
    check("zero le como infinito", limits.text(world.panel, "radius", 0) === limits.UNLIMITED);
    check("e qualquer outro numero fica como esta", limits.text(world.panel, "radius", 5) === null);

    // Campo sem checkbox nenhum nao muda de leitura: intensidade zero e intensidade
    // zero mesmo, e trocar por "infinito" seria mentir.
    const semControle = { querySelector: () => null };
    check("campo sem 'sem limite' nao ganha infinito",
        limits.text(semControle, "intensity", 0) === null);
}

console.log(
    failures
        ? `\n${failures} verificacao(oes) de limite falharam`
        : "\ntodas as verificacoes de limite passaram",
);
process.exit(failures ? 1 : 0);
