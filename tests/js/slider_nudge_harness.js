/*
 * Os botões de − e + das réguas.
 *
 * Arrastar serve para achar a região certa; não serve para o ajuste fino. Numa
 * régua de 0,1 a 20 dentro de um painel estreito, um pixel de mouse vale mais que
 * o passo, e "um pouquinho mais" não tem como ser pedido arrastando.
 *
 * O que este harness cobra é o passo, o arredondamento e os limites: três coisas
 * que uma asserção de "o botão existe" não pegaria.
 *
 * Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const SCRIPT = path.resolve(__dirname, "../../static/js/ui/slider-nudge.js");

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

function load() {
    const listeners = [];
    const doc = {
        readyState: "complete",
        documentElement: {},
        addEventListener: (type, fn) => listeners.push({ type, fn }),
        querySelectorAll: () => [],
        createElement: () => ({ dataset: {}, classList: { add() {} }, setAttribute() {} }),
    };
    const win = {};
    new Function("window", "document", "MutationObserver", "Event",
        fs.readFileSync(SCRIPT, "utf8"))(
        win, doc, function () { return { observe() {} }; },
        class { constructor(type) { this.type = type; } },
    );
    return win.GravewrightSliderNudge;
}

const api = load();

// `input[type=range]` NAO aceita qualquer numero: o navegador encaixa o valor no
// passo declarado. Escrever 8.1 numa regua de passo 1 devolve 8, e foi assim que
// os botoes de rotacao e alcance nasceram mortos, com o harness passando porque o
// duble aceitava o decimal que a plataforma recusa.
function range({ value, step = "0.1", min = "0", max = "20", disabled = false } = {}) {
    const events = [];
    return {
        step, min, max, disabled, events, dataset: {},
        _value: String(value),
        get value() { return this._value; },
        set value(raw) {
            // Le o passo VIGENTE, nao o da criacao: afrouxar o campo tem de mudar
            // o que a plataforma aceita, senao o duble nao reproduz o defeito.
            const size = Number(this.step);
            const base = Number.isFinite(Number(this.min)) ? Number(this.min) : 0;
            const numero = Number(raw);
            const encaixado = Number.isFinite(size) && size > 0
                ? base + Math.round((numero - base) / size) * size
                : numero;
            this._value = String(Number(encaixado.toFixed(6)));
        },
        dispatchEvent(event) { events.push(event.type); },
    };
}

// --- o passo ----------------------------------------------------------------
{
    // Régua grossa: o botão anda fino, senão ele seria só um jeito lento de
    // arrastar.
    check("regua de passo inteiro anda de 0,1 no botao",
        api.stepOf(range({ value: 3, step: "1" })) === 0.1);

    // Régua mais fina que o botão manda: descer para 0,1 numa régua de 0,05 seria
    // perder precisão em vez de ganhar.
    check("regua mais fina mantem o proprio passo",
        api.stepOf(range({ value: 0.5, step: "0.05" })) === 0.05);

    check("sem passo declarado, o fino vale",
        api.stepOf(range({ value: 1, step: "" })) === 0.1);
}

// --- o valor -----------------------------------------------------------------
{
    const input = range({ value: 0.2 });
    api.nudge(input, 1);
    // 0.2 + 0.1 em ponto flutuante é 0.30000000000000004. O que aparece na tela
    // tem de ser o que vai para o servidor.
    check("somar 0,1 nao vaza ponto flutuante", input.value === "0.3", input.value);

    // O caso que quebrou na mesa: regua de passo inteiro. O botao tem de AFROUXAR
    // o passo do campo antes de escrever, senao o navegador encaixa de volta e o
    // clique nao faz nada.
    const grosso = range({ value: 7, step: "1", max: "359" });
    api.prepare(grosso);
    api.nudge(grosso, 1);
    check("e numa regua inteira o botao ainda da o decimal", grosso.value === "7.1", grosso.value);
    check("o passo original fica guardado para a exibicao",
        grosso.dataset?.baseStep === "1", JSON.stringify(grosso.dataset));

    const semPreparo = range({ value: 7, step: "1", max: "359" });
    api.nudge(semPreparo, 1);
    check("sem afrouxar, a plataforma engole o decimal", semPreparo.value === "7",
        "e este era o defeito: rotacao e alcance nao andavam");

    const fino = range({ value: 0.5, step: "0.05", max: "1" });
    api.nudge(fino, -1);
    check("regua fina anda no passo dela", fino.value === "0.45", fino.value);
}

// --- limites -----------------------------------------------------------------
{
    const teto = range({ value: 20, max: "20" });
    check("no teto, o botao nao devolve nada", api.nudge(teto, 1) === null);
    check("e o valor fica onde estava", teto.value === "20");

    const piso = range({ value: 0, min: "0" });
    api.nudge(piso, -1);
    check("no piso, tambem nao passa", piso.value === "0");

    const quase = range({ value: 19.95, max: "20" });
    api.nudge(quase, 1);
    check("e perto do teto ele para NO teto, sem passar", quase.value === "20", quase.value);
}

// --- avisar quem escuta ------------------------------------------------------
{
    const input = range({ value: 1 });
    api.nudge(input, 1);
    // Sem disparar, o botão mexeria na régua e não no que ela controla: o painel
    // inteiro grava ouvindo `input`.
    check("o botao avisa quem escuta a regua",
        input.events.includes("input") && input.events.includes("change"),
        input.events.join(","));

    const desligada = range({ value: 1, disabled: true });
    check("regua desligada nao anda", api.nudge(desligada, 1) === null,
        "com 'sem limite' marcado o numero nao esta valendo");
    check("e nao avisa ninguem", desligada.events.length === 0);
}

console.log(
    failures
        ? `\n${failures} verificacao(oes) dos botoes falharam`
        : "\ntodas as verificacoes dos botoes passaram",
);
process.exit(failures ? 1 : 0);
