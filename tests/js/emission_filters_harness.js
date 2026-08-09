/*
 * Fonte de luz e efeito de cena são coisas diferentes, e o código precisa manter
 * a separação.
 *
 * Luz anima de dois jeitos e só: chama irregular (tocha) e respiração (pulso).
 * Fumaça, brasa, poeira e mote arcano viraram emissores de partícula — não
 * iluminam nada, e por isso moram na camada de composição, longe do foco.
 *
 * Este harness existe porque "todas as luzes iguais" sobreviveu a várias rodadas
 * de asserção de texto: o código tinha animação por tipo e a tela mostrava um
 * disco pulsando. Aqui os presets reais são exercitados e comparados entre si.
 *
 * Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const LIGHTING = path.resolve(__dirname, "../../static/js/lighting/dynamic-lighting.js");
const LAYER = path.resolve(__dirname, "../../static/js/board/pixi/pixi-lighting-layer.js");
const LAYERS = path.resolve(__dirname, "../../static/js/board/pixi/pixi-board-layers.js");

const LIGHTS = ["torch", "pulse"];
const KINDS = ["smoke", "ember", "dust", "arcane"];

function loadLighting() {
    // O laço de animação começa na carga; sem estes o arquivo nem sobe.
    const win = { requestAnimationFrame() {}, setInterval() {}, clearInterval() {} };
    const doc = {
        readyState: "complete",
        addEventListener() {},
        querySelector: () => null,
        querySelectorAll: () => [],
        body: { dataset: {} },
    };
    new Function("window", "document", "fetch", "CSS", "console", "performance",
        fs.readFileSync(LIGHTING, "utf8"))(
        win, doc, async () => ({ ok: true, json: async () => ({}) }),
        { escape: (s) => s }, { log() {}, warn() {}, error() {} }, { now: () => 0 },
    );
    return win.GravewrightLighting;
}

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

const lighting = loadLighting();
const source = fs.readFileSync(LIGHTING, "utf8");

const light = (animation) => ({
    id: `light-${animation}`, animation, color: "#ffd8a8", x: 500, y: 500, dim: 200, bright: 90,
});
const profileAt = (animation, now) => lighting.emissionProfile(light(animation), now);

// --- as duas luzes que sobraram se movem de jeitos diferentes ---------------
{
    const travel = (name) => {
        let most = 0;
        for (let now = 0; now < 6000; now += 50) {
            const { offset } = profileAt(name, now);
            most = Math.max(most, Math.hypot(offset.x, offset.y));
        }
        return most;
    };
    const torch = profileAt("torch", 777);
    const pulse = profileAt("pulse", 777);

    check("a tocha passeia", travel("torch") > 0, `${travel("torch").toFixed(1)} px`);
    // O pulso é movimento puramente matemático, e é essa ausência de tremor que o
    // distingue da chama.
    check("o pulso nao sai do lugar", travel("pulse") === 0);
    check("a tocha gira, o pulso nao", torch.spin !== 0 && pulse.spin === 0);
    check("a tocha tem lobulos; o pulso e circulo limpo",
        torch.lobes > 0 && pulse.lobes === 0, `${torch.lobes} x ${pulse.lobes}`);
    check("a tocha e feita de mais de uma fonte",
        torch.sources.length > pulse.sources.length);
}

// --- nenhuma luz solta partícula --------------------------------------------
{
    // Foi a separação inteira desta rodada. Se soltar partícula voltar a ser coisa
    // de foco, o editor de luz volta a encher de controle que não acende nada.
    const emissions = source.slice(
        source.indexOf("const EMISSIONS = {"),
        source.indexOf("const LIGHT_DEFAULTS = {"),
    );
    check("o preset de luz nao declara particula", !emissions.includes("particles:"));
    check("e so tocha e pulso restaram",
        LIGHTS.every((name) => emissions.includes(`${name}: {`))
        && !["candle", "fire", "arcane", "smoke"].some((n) => emissions.includes(`${n}: {`)));
}

// --- os emissores ------------------------------------------------------------
{
    const emitter = (kind, extra) => Object.assign(
        { id: `e-${kind}`, kind, x: 500, y: 500, scale: 3, density: 0.6, enabled: 1 },
        extra || {},
    );
    const at = (kind, now, extra) => lighting.particleCloud(emitter(kind, extra), now, 50);

    KINDS.forEach((kind) => {
        check(`${kind} solta particula`, at(kind, 0).length > 0, `${at(kind, 0).length}`);
    });

    // Determinismo: é o que permite testar, e o que faz a nuvem sobreviver a pausa
    // e a queda de quadros sem acumular lixo.
    check("o mesmo instante devolve a mesma nuvem",
        JSON.stringify(at("smoke", 1234)) === JSON.stringify(at("smoke", 1234)));

    // Densidade é o botão de desempenho do mestre: baixa sem perder a composição.
    check("densidade baixa solta menos",
        at("smoke", 0, { density: 0.1 }).length < at("smoke", 0, { density: 1 }).length,
        `${at("smoke", 0, { density: 0.1 }).length} < ${at("smoke", 0, { density: 1 }).length}`);
    check("emissor desligado nao solta nada", at("smoke", 0, { enabled: 0 }).length === 0);

    const byAge = (kind) => [...at(kind, 777)].sort((a, b) => a.age - b.age);
    const climb = (kind) => {
        const sorted = byAge(kind);
        return sorted[0].y - sorted[sorted.length - 1].y;
    };
    check("fumaca sobe", climb("smoke") > 0, `${climb("smoke").toFixed(0)} px`);
    check("brasa sobe", climb("ember") > 0, `${climb("ember").toFixed(0)} px`);
    // Poeira que sobe vira fumaça: ela paira e vai de lado, que é o que a luz de
    // uma fresta mostra num salão parado.
    check("poeira paira em vez de subir", climb("dust") < climb("smoke") / 4,
        `${climb("dust").toFixed(0)} contra ${climb("smoke").toFixed(0)}`);
    check("mote arcano orbita", Math.abs(climb("arcane")) < 60, `${climb("arcane").toFixed(0)} px`);

    // Nasce e morre transparente: sem isso ela aparece e some de estalo.
    const alphas = [];
    for (let now = 0; now < 6200; now += 300) alphas.push(at("smoke", now)[0].alpha);
    check("a nuvem acende e apaga em vez de piscar",
        Math.min(...alphas) < 0.1 && Math.max(...alphas) > 0.2,
        `${Math.min(...alphas).toFixed(2)} .. ${Math.max(...alphas).toFixed(2)}`);

    const spread = (scale) => Math.max(
        ...at("smoke", 777, { scale }).map((p) => Math.hypot(p.x - 500, p.y - 500)));
    check("escala maior espalha mais longe", spread(6) > spread(2),
        `${spread(2).toFixed(0)} -> ${spread(6).toFixed(0)} px`);
}

// --- e ficam sob a escuridão -------------------------------------------------
{
    const layers = fs.readFileSync(LAYERS, "utf8");
    const block = layers.slice(layers.indexOf("board.lightingLayer.addChild("));
    const cloudAt = block.indexOf("lightingParticleGfx");
    const darknessAt = block.indexOf("lightingSprite");
    check("a nuvem entra antes da folha de escuridao",
        cloudAt >= 0 && cloudAt < darknessAt,
        "emissor nao ilumina: o escuro tem de engoli-lo como engole o mapa");

    // Sem máscara própria — a oclusão vem da ordem das camadas, que é mais barata
    // e nunca sai de sincronia com a escuridão.
    const pixi = fs.readFileSync(LAYER, "utf8");
    const method = pixi.slice(pixi.indexOf("_renderParticleClouds(board, lighting"));
    check("e sem mascara propria", !method.slice(0, 1200).includes("mask"));
}

console.log(
    failures
        ? `\n${failures} verificacao(oes) de emissao falharam`
        : "\ntodas as verificacoes de emissao passaram",
);
process.exit(failures ? 1 : 0);
