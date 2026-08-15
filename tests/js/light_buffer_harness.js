/*
 * O buffer de luz que o shader recebe.
 *
 * Ele não é a soma dos focos: é a iluminação RESULTANTE, ambiente mais focos, já
 * recortada nas paredes. A diferença importa: sem o ambiente, um mapa de dia sem
 * foco nenhum entregava preto, e um efeito que responde à luz sumia justamente
 * onde tudo está iluminado.
 *
 * Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const SCRIPT = path.resolve(__dirname, "../../static/js/board/pixi/pixi-light-buffer.js");

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

function load() {
    const rendered = [];

    class Node {
        constructor(kind) {
            this.kind = kind;
            this.visible = true;
            this.children = [];
            this.shapes = [];
            this.mask = null;
            this.tint = 0xffffff;
            this.alpha = 1;
            this.width = 0;
            this.height = 0;
            this.blendMode = "normal";
            this.position = { x: 0, y: 0, set: (x, y) => { this.position.x = x; this.position.y = y; } };
            this.anchor = { set() {} };
        }
        addChild(...nodes) { this.children.push(...nodes); }
        removeChildren() { this.children = []; }
        clear() { this.shapes = []; return this; }
        rect(x, y, w, h) { this.shapes.push({ kind: "rect", x, y, w, h }); return this; }
        poly(points) { this.shapes.push({ kind: "poly", points }); return this; }
        fill(value) {
            const last = this.shapes[this.shapes.length - 1];
            if (last) last.fill = value;
            return this;
        }
    }

    const PIXI = {
        Container: class { constructor() { this.children = []; } addChild(...n) { this.children.push(...n); } removeChildren() { this.children = []; } },
        Graphics: class extends Node { constructor() { super("graphics"); } },
        Sprite: class extends Node { constructor(texture) { super("sprite"); this.texture = texture; } },
        RenderTexture: { create: (o) => ({ ...o, destroy() {} }) },
    };

    const win = {
        PIXI,
        GravewrightBoardInternals: { falloff: () => "queda-radial" },
    };
    new Function("window", "PIXI", fs.readFileSync(SCRIPT, "utf8"))(win, PIXI);

    return {
        api: win.GravewrightLightBuffer,
        rendered,
        board: { app: { renderer: { render: (call) => rendered.push(call) } } },
    };
}

const CAM = { offsetX: 0, offsetY: 0, zoom: 1 };
const tocha = (extra = {}) => ({
    id: "L1", x: 400, y: 300, dim: 200, color: "#ff9a3c", alpha: 1,
    polygon: [{ x: 300, y: 200 }, { x: 500, y: 200 }, { x: 500, y: 400 }, { x: 300, y: 400 }],
    ...extra,
});
// `darkness` e o que se PINTA (atenuado para o mestre); `sceneDarkness` e o da
// cena. Os dois convivem no estado de proposito, e o buffer tem de ler o segundo.
const state = (extra = {}) => ({
    lights: [], darkness: 1, sceneDarkness: 1, geometryStamp: "g1", ...extra,
});

// --- ambiente ---------------------------------------------------------------
{
    const world = load();
    world.api.build(world.board, state({ darkness: 0, sceneDarkness: 0 }), 800, 600, CAM);
    const call = world.rendered[0];
    const fundo = call.container.children[0];
    // "Sem luz" e uma cor que o modulo DESENHA, e nao a que ele encontra: `clear`
    // usa o fundo do renderer, e o fundo do tabuleiro nao e preto, o buffer saia
    // claro de ponta a ponta e o preview virava uma folha branca sobre o mapa.
    check("o buffer comeca preto por conta propria",
        fundo.shapes[0]?.kind === "rect" && fundo.shapes[0].fill.color === 0x000000
        && fundo.shapes[0].fill.alpha === 1, JSON.stringify(fundo.shapes[0]?.fill));
    check("e a limpeza tambem vai explicita",
        JSON.stringify(call.clearColor) === "[0,0,0,1]", JSON.stringify(call.clearColor));

    // Cena sem escuridao e cena inteiramente iluminada. Entregar preto aqui fazia
    // o efeito sumir justamente onde tudo esta claro.
    const luz = (mundo) => mundo.rendered[0].container.children[0].shapes[1];
    check("cena sem escuridao entrega luz cheia", luz(world)?.fill.alpha === 1,
        JSON.stringify(luz(world)?.fill));

    const escuro = load();
    escuro.api.build(escuro.board, state({ darkness: 1, sceneDarkness: 1 }), 800, 600, CAM);
    const semFundo = escuro.rendered[0].container.children[0];
    check("escuridao total nao pinta ambiente nenhum", semFundo.shapes.length === 1,
        "so o preto de base");

    const meio = load();
    meio.api.build(meio.board, state({ darkness: 0.75, sceneDarkness: 0.75 }), 800, 600, CAM);
    check("e meia escuridao entrega o que sobra",
        Math.abs(luz(meio).fill.alpha - 0.25) < 1e-9, JSON.stringify(luz(meio)?.fill));
}

// --- a escuridão que vale é a da cena ---------------------------------------
{
    // O mestre nao ve a escuridao cheia: ela e atenuada para ele nao ficar sem o
    // proprio mapa. Ler ESSA escuridao aqui dizia que uma sala preta estava quase
    // clara, e o buffer saia branco de ponta a ponta: que foi o defeito na mesa.
    const world = load();
    world.api.build(world.board, state({ darkness: 0.315, sceneDarkness: 0.9 }), 800, 600, CAM);
    const ambiente = world.rendered[0].container.children[0].shapes[1];
    check("sala escura entrega pouca luz, mesmo com a previa do mestre clara",
        Math.abs(ambiente.fill.alpha - 0.1) < 1e-9,
        `${ambiente.fill.alpha}: com a previa do GM daria 0.685`);

    // E a previa do mestre mudando sozinha nao pode reescrever a textura: ela nao
    // muda a iluminacao da cena, so como ela e mostrada a ele.
    const antes = world.rendered.length;
    world.api.build(world.board, state({ darkness: 0.9, sceneDarkness: 0.9 }), 800, 600, CAM);
    check("e a previa do mestre nao redesenha o buffer", world.rendered.length === antes);
}

// --- focos ------------------------------------------------------------------
{
    const world = load();
    world.api.build(world.board, state({ lights: [tocha()] }), 800, 600, CAM);
    const filhos = world.rendered[0].container.children;
    const sprite = filhos.find((node) => node.kind === "sprite");

    check("o foco entra somando", sprite.blendMode === "add",
        "duas tochas na mesma sala somam, como somam na tela");
    check("com a cor dele", sprite.tint === 0xff9a3c);
    check("e o tamanho do alcance", sprite.width === 200 * 2 * world.api.SCALE);

    // A oclusao: o MESMO poligono da tela. Sem isto, a luz que o shader recebe
    // atravessaria parede enquanto a luz que a pessoa ve para nela.
    check("recortado pelo poligono da propria luz",
        sprite.mask?.shapes[0]?.kind === "poly" && sprite.mask.shapes[0].points.length === 8);

    const semParede = load();
    semParede.api.build(semParede.board, state({ lights: [tocha({ polygon: [] })] }), 800, 600, CAM);
    const solto = semParede.rendered[0].container.children.find((n) => n.kind === "sprite");
    check("alcance livre dispensa recorte", solto.mask === null,
        "a queda radial ja limita sozinha");
}

// --- escala e orcamento -----------------------------------------------------
{
    const world = load();
    world.api.build(world.board, state({ lights: [tocha()] }), 800, 600, CAM);
    const alvo = world.rendered[0].target;
    // Meia resolucao: nevoa e brilho nao tem detalhe fino, e o custo cai a um
    // quarto: que e o que mantem isto honesto no PC velho.
    check("a textura e de meia resolucao", alvo.width === 400 && alvo.height === 300,
        `${alvo.width}x${alvo.height}`);

    const muitas = load();
    const lista = Array.from({ length: 40 }, (_, i) => tocha({ id: `L${i}` }));
    muitas.api.build(muitas.board, state({ lights: lista }), 800, 600, CAM);
    const sprites = muitas.rendered[0].container.children.filter((n) => n.kind === "sprite");
    check("o orcamento limita quantos focos entram", sprites.length === muitas.api.MAX_LIGHTS,
        `${sprites.length}`);

    const apagada = load();
    apagada.api.build(apagada.board, state({ lights: [tocha({ alpha: 0 })] }), 800, 600, CAM);
    check("foco apagado nao entra",
        !apagada.rendered[0].container.children.some((n) => n.kind === "sprite"));
}

// --- a cena parada não redesenha --------------------------------------------
{
    const world = load();
    const cena = state({ lights: [tocha()] });
    world.api.build(world.board, cena, 800, 600, CAM);
    world.api.build(world.board, cena, 800, 600, CAM);
    check("cena parada nao redesenha a textura", world.rendered.length === 1,
        `${world.rendered.length} renderizacoes`);

    world.api.build(world.board, state({ lights: [tocha({ x: 600 })] }), 800, 600, CAM);
    check("foco que se move redesenha", world.rendered.length === 2);

    world.api.build(world.board, state({ lights: [tocha({ x: 600 })], geometryStamp: "g2" }), 800, 600, CAM);
    check("parede que muda redesenha", world.rendered.length === 3,
        "porta abrindo tem de mudar a luz que o shader recebe");

    world.api.build(world.board, state({ lights: [tocha({ x: 600 })], geometryStamp: "g2", sceneDarkness: 0.5 }), 800, 600, CAM);
    check("e mexer na escuridao da cena tambem", world.rendered.length === 4);
}

console.log(
    failures
        ? `\n${failures} verificacao(oes) do buffer de luz falharam`
        : "\ntodas as verificacoes do buffer de luz passaram",
);
process.exit(failures ? 1 : 0);
