/*
 * Cobertura numérica do halo lobulado (static/js/board/pixi/pixi-lighting-layer.js).
 *
 * Existe porque a versão anterior estava certa no código e invisível na tela: a
 * mordida do lóbulo era multiplicada por `distância ao quadrado`, o que a punha no
 * ponto em que a queda quadrática já tinha levado o alfa a quase zero. Nenhuma
 * asserção de texto pega isso: só a conta pega. Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const SCRIPT = path.resolve(__dirname, "../../static/js/board/pixi/pixi-lighting-layer.js");

const win = { GravewrightBoardInternals: { PixiBoardRenderer: { prototype: {} } } };
new Function("window", "document", "PIXI", fs.readFileSync(SCRIPT, "utf8"))(win, {}, {});
const profile = win.GravewrightBoardInternals.flameProfile;

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

// O ângulo do pico e do vale de um perfil, varrendo a volta inteira.
function extremes(count, bite, distance) {
    let peak = { alpha: -Infinity }, notch = { alpha: Infinity };
    for (let i = 0; i < 720; i += 1) {
        const angle = -Math.PI + (i / 720) * Math.PI * 2;
        const alpha = profile(count, bite, distance, angle);
        if (alpha > peak.alpha) peak = { alpha, angle };
        if (alpha < notch.alpha) notch = { alpha, angle };
    }
    return { peak, notch };
}

// --- o entalhe precisa aparecer onde o halo ainda tem brilho ----------------
{
    // Meio do raio: é onde o halo tem corpo e onde o olho lê a silhueta.
    const { peak, notch } = extremes(6, 0.26, 0.5);
    const ratio = peak.alpha / Math.max(1e-6, notch.alpha);
    check("tocha: pico e vale se separam no meio do raio", ratio >= 1.8,
        `pico ${peak.alpha.toFixed(3)} vale ${notch.alpha.toFixed(3)} razao ${ratio.toFixed(2)}x`);
    check("e o brilho ali ainda é visível", peak.alpha > 0.15, peak.alpha.toFixed(3));
}

// --- silhuetas diferentes produzem contrastes diferentes ---------------------
{
    const torch = extremes(6, 0.26, 0.5);
    const beacon = extremes(1, 0.55, 0.5);
    const beaconRatio = beacon.peak.alpha / Math.max(1e-6, beacon.notch.alpha);
    const torchRatio = torch.peak.alpha / Math.max(1e-6, torch.notch.alpha);
    check("farol corta mais fundo que tocha", beaconRatio > torchRatio,
        `farol ${beaconRatio.toFixed(2)}x tocha ${torchRatio.toFixed(2)}x`);
}

// --- contagem de lóbulos: quantos picos a volta tem -------------------------
function peaks(count, bite, distance) {
    const samples = [];
    for (let i = 0; i < 720; i += 1) {
        const angle = -Math.PI + (i / 720) * Math.PI * 2;
        samples.push(profile(count, bite, distance, angle));
    }
    let found = 0;
    for (let i = 0; i < samples.length; i += 1) {
        const previous = samples[(i - 1 + samples.length) % samples.length];
        const next = samples[(i + 1) % samples.length];
        if (samples[i] > previous && samples[i] >= next) found += 1;
    }
    return found;
}

for (const [name, count, bite] of [
    ["farol", 1, 0.55], ["arcana", 3, 0.3], ["fogueira", 4, 0.34],
    ["tocha", 6, 0.26], ["vela", 9, 0.16],
]) {
    check(`${name} desenha ${count} lobulo(s)`, peaks(count, bite, 0.5) === count,
        `contou ${peaks(count, bite, 0.5)}`);
}

// --- o miolo fica inteiro ----------------------------------------------------
{
    const { peak, notch } = extremes(6, 0.26, 0.05);
    check("nenhum buraco girando no meio da luz", peak.alpha - notch.alpha < 0.02,
        `variacao ${(peak.alpha - notch.alpha).toFixed(4)}`);
    check("e o centro e opaco", profile(6, 0.26, 0, 0) > 0.95);
}

// --- o entalhe so encurta, nunca estica -------------------------------------
{
    // A mascara do poligono corta o que passa do raio; um lobulo para fora seria
    // metade do efeito invisivel.
    let overflows = 0;
    for (let d = 0.05; d < 1; d += 0.05) {
        const smooth = (1 - d) * (1 - d);
        const { peak } = extremes(6, 0.26, d);
        if (peak.alpha > smooth + 1e-9) overflows += 1;
    }
    check("nenhum ponto brilha mais que o halo liso", overflows === 0, `${overflows} pontos`);
}

// --- sem lobulo, o perfil e o halo liso de sempre ---------------------------
{
    const same = [0.1, 0.4, 0.7, 0.95].every(
        (d) => Math.abs(profile(0, 0, d, 1.2) - (1 - d) * (1 - d)) < 1e-9,
    );
    check("pulso e classico caem no halo liso", same);
}

console.log(
    failures
        ? `\n${failures} verificacao(oes) do halo falharam`
        : "\ntodas as verificacoes do halo passaram",
);
process.exit(failures ? 1 : 0);
