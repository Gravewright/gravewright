/*
 * Shader de cena, dos dois lados.
 *
 * Um shader e a unica coisa da mesa que uma pessoa escreve e OUTRA executa — na
 * GPU dela, a cada quadro. As duas garantias que fazem isso ser aceitavel sao
 * comportamento, nao texto no codigo, e por isso estao aqui:
 *
 *   1. quem nao compila e desligado, e a cena continua desenhando;
 *   2. quem olha pode desligar todos, sem depender do mestre.
 *
 * Mais a regra de composicao combinada: shader e o efeito do modo
 * cinematografico; no modo leve o efeito da cena sao as particulas.
 *
 * Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const LIGHTING = path.resolve(__dirname, "../../static/js/lighting/dynamic-lighting.js");
const EFFECTS = path.resolve(__dirname, "../../static/js/board/pixi/pixi-shader-effects.js");

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

const SHADERS = [
    { id: "s1", name: "nevoa", source: "void main(){ finalColor = vec4(uColor, 1.0); }", intensity: 0.5, scale: 2, speed: 1, color: "#8fb6ff", enabled: 1, x: 400, y: 300, radius: 4 },
    { id: "s2", name: "desligado", source: "void main(){}", intensity: 1, scale: 1, speed: 1, color: "#ff0000", enabled: 0, x: 900, y: 900, radius: 0 },
];

// --- parte 1: o estado de render decide quem chega ate a GPU -----------------

// O arquivo real usa `new CustomEvent(...)` como global.
global.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init?.detail; } };

class El {
    constructor(tag, parent = null) {
        this.tag = tag; this.dataset = {}; this.parent = parent; this.children = [];
        this.listeners = []; this.classList = { contains: () => true };
        if (parent) parent.children.push(this);
    }
    addEventListener(type, fn, capture = false) {
        this.listeners.push({ type, fn, capture: capture === true || capture?.capture === true });
    }
    matches(selector) {
        const parsed = /^\[([a-z-]+)(?:="([^"]*)")?\]$/.exec(selector);
        if (!parsed) return false;
        const key = parsed[1].replace(/^data-/, "").replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        if (!(key in this.dataset)) return false;
        return parsed[2] === undefined || this.dataset[key] === parsed[2];
    }
    closest(selector) {
        for (let node = this; node; node = node.parent) if (node.matches(selector)) return node;
        return null;
    }
    querySelector() { return null; }
    setPointerCapture() {}
    releasePointerCapture() {}
    path() {
        const chain = [];
        for (let node = this; node; node = node.parent) chain.unshift(node);
        return chain;
    }
}

function buildWorld({ shadersEnabled = true, mode = "cinematic", isGm = true, layer = "game", tool = "select", shaders = SHADERS, emitters = [] } = {}) {
    let visionMode = mode;
    const listeners = [];
    const posts = [];
    const live = shaders.map((s) => ({ ...s }));

    const root = new El("body");
    const surface = new El("div", root);
    surface.dataset.mapViewport = "";
    surface.dataset.lightingGm = isGm ? "true" : "false";
    const canvas = new El("canvas", surface);
    canvas.dataset.mapCanvas = "";
    canvas.dataset.roomId = "campaign-1";

    const tools = { activeTool: tool, activeLayer: layer, activeSubTool: "", isLayerVisible: () => true };
    const sandbox = {
        window: {
            GravewrightTools: tools,
            GravewrightMap: {
                redraw() {},
                sceneDataFor: () => ({ id: "scene-1", width: 2000, height: 2000, scaledTileSize: 70, darkness: 0.9 }),
                tokenStoreFor: () => new Map(),
                isPlayerView: () => false,
                screenToWorldXY: (x, y) => ({ worldX: x, worldY: y }),
                worldFromScreen: (_canvas, x, y) => ({ worldX: x, worldY: y }),
                stateFor: () => ({ zoom: 1 }),
            },
            GravewrightVisionMode: { current: () => visionMode, isClassic: () => visionMode === "classic" },
            GravewrightShaderPreference: { enabled: () => shadersEnabled },
            GravewrightToasts: { showToast() {} },
            requestAnimationFrame() {},
            csrfToken: () => "csrf",
        },
        document: {
            readyState: "complete",
            body: { dataset: { currentUserId: "user-gm" } },
            addEventListener: (type, fn) => listeners.push({ type, fn }),
            dispatchEvent: (event) => listeners.filter((l) => l.type === event.type).forEach((l) => l.fn(event)),
            querySelector: (selector) => (selector === "[data-map-canvas]" ? canvas : null),
            querySelectorAll: (selector) => (selector === "[data-map-canvas]" ? [canvas] : []),
        },
        fetch: async (url, options = {}) => {
            if ((options.method || "GET") !== "POST") {
                if (url.includes("/game/shaders/")) {
                    return { ok: true, json: async () => ({ shaders: live.map((s) => ({ ...s })) }) };
                }
                return { ok: true, json: async () => ({ walls: [], lights: [], emitters: emitters.map((e) => ({ ...e })) }) };
            }
            const body = JSON.parse(options.body);
            posts.push({ url, body });
            if (url.endsWith("/game/shaders")) {
                const shader = {
                    id: `N${live.length + 1}`, name: "", source: "void main(){ finalColor = texture(uTexture, vTextureCoord); }",
                    x: body.x, y: body.y, radius: 0, rotation: 0,
                    intensity: 0.6, scale: 1, speed: 1, color: "#8fb6ff", enabled: 1,
                };
                live.push(shader);
                return { ok: true, json: async () => ({ shader: { ...shader, scene_id: "scene-1" } }) };
            }
            if (url.endsWith("/game/shaders/update")) {
                const shader = live.find((s) => s.id === body.shader_id);
                if (shader) Object.assign(shader, body);
                return { ok: true, json: async () => ({ shader: { ...shader, scene_id: "scene-1" } }) };
            }
            return { ok: true, json: async () => ({}) };
        },
    };

    new Function("window", "document", "fetch", "CSS", "console", "performance",
        fs.readFileSync(LIGHTING, "utf8"))(
        sandbox.window, sandbox.document, sandbox.fetch,
        { escape: (s) => s }, { log() {}, warn() {}, error() {} }, { now: () => 1000 },
    );

    const dispatch = (type, props = {}) => {
        const target = props.target || canvas;
        const event = {
            type, target, button: 0, clientX: 0, clientY: 0, pointerId: 1,
            preventDefault() {}, stopPropagation() {},
            composedPath: () => target.path(),
            ...props,
        };
        surface.listeners.filter((l) => l.type === type).forEach((l) => l.fn(event));
        listeners.filter((l) => l.type === type).forEach((l) => l.fn(event));
        return event;
    };

    const emitted = [];
    const original = sandbox.document.dispatchEvent;
    sandbox.document.dispatchEvent = (event) => { emitted.push(event); return original(event); };

    return {
        dispatch, posts, tools, emitted,
        state: () => sandbox.window.GravewrightLighting.stateForCanvas(canvas),
        setMode: (next) => { visionMode = next; },
        setLayer: (next) => {
            tools.activeLayer = next;
            listeners.filter((l) => l.type === "tool:active-layer").forEach((l) => l.fn({ detail: { layer: next } }));
        },
        settle: async () => { for (let i = 0; i < 12; i += 1) await Promise.resolve(); },
    };
}

async function stateChecks() {
    const world = buildWorld();
    await world.settle();
    const cinematic = world.state();
    check("o cinematografico recebe o shader da cena", cinematic.shaders.length === 1,
        `${cinematic.shaders.length} de ${SHADERS.length}`);
    check("shader desligado nao viaja", !cinematic.shaders.some((s) => s.id === "s2"));

    // Modo leve nao tem passe de filtro; o efeito dele sao as particulas, e e por
    // isso que elas continuam sendo desenhadas la.
    world.setMode("classic");
    check("o modo leve nao recebe shader nenhum", world.state().shaders.length === 0);

    const off = buildWorld({ shadersEnabled: false });
    await off.settle();
    check("a chave de quem olha desliga todos", off.state().shaders.length === 0,
        "shader roda na GPU de quem nao escreveu; sair nao pode depender do mestre");
}

// --- a origem: ver, pegar e mover -------------------------------------------

async function originChecks() {
    {
        const world = buildWorld({ layer: "effects" });
        await world.settle();
        const state = world.state();
        // Sem marcador a origem e invisivel — o shader desenha na tela inteira, e
        // nao ha nada no mapa que revele de onde ele sai.
        check("a camada de efeitos mostra a origem", state.editingShaders === true);
        check("inclusive a do shader desligado", state.shaderMarkers.length === 2,
            "e como se volta a ligar um que se apagou sem querer");
        const marker = state.shaderMarkers.find((s) => s.id === "s1");
        check("o marcador sabe onde fica", marker.x === 400 && marker.y === 300);
        // Raio em celulas vira mundo aqui, onde o tamanho da celula e conhecido.
        check("e o alcance vira medida de mundo", marker.radiusWorld === 4 * 70,
            `${marker.radiusWorld}`);

        world.setLayer("game");
        check("mas some quando o mestre volta a jogar", world.state().editingShaders === false);
    }

    {
        const world = buildWorld({ layer: "effects" });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 400, clientY: 300 });
        check("clicar na origem seleciona", world.state().shaderMarkers[0].selected === true);

        world.dispatch("pointermove", { clientX: 640, clientY: 500 });
        const arrastando = world.state();
        // Enquanto arrasta, so a tela se mexe: gravar a cada pixel geraria uma
        // requisicao por quadro, e um refresh no meio traria a posicao velha.
        check("arrastar move a origem na tela", arrastando.shaderMarkers[0].x === 640
            && arrastando.shaderMarkers[0].y === 500);
        check("e o shader ativo acompanha", arrastando.shaders[0].x === 640);
        check("sem falar com o servidor ainda", world.posts.length === 0);

        world.dispatch("pointerup", { clientX: 640, clientY: 500 });
        await world.settle();
        const gravado = world.posts.find((p) => p.url.endsWith("/game/shaders/update"));
        check("soltar grava a posicao", gravado?.body.x === 640 && gravado?.body.y === 500,
            JSON.stringify(gravado?.body));
    }

    {
        // Origem de shader e emissor no MESMO ponto. Sao vizinhos de camada, e o
        // shader e o mais raro dos dois: perder o clique para uma nuvem por cima
        // dele tira a unica forma que existe de move-lo.
        const world = buildWorld({
            layer: "effects",
            emitters: [{ id: "E1", x: 400, y: 300, kind: "smoke", scale: 3, density: 0.6, color: "#9aa3ad", enabled: 1 }],
        });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 400, clientY: 300 });
        world.dispatch("pointermove", { clientX: 500, clientY: 400 });
        const state = world.state();
        check("com nuvem em cima, o clique ainda pega a origem",
            state.shaderMarkers.find((s) => s.id === "s1").x === 500);
        check("e a nuvem fica onde estava", state.particleClouds[0].x === 400);
    }

    {
        // Clique parado nao e arraste. Sem isto, selecionar viraria uma escrita.
        const world = buildWorld({ layer: "effects" });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 400, clientY: 300 });
        world.dispatch("pointerup", { clientX: 400, clientY: 300 });
        await world.settle();
        check("so selecionar nao grava nada", world.posts.length === 0);
    }

    {
        // Camada errada nao pega: na de jogo o clique e do tabuleiro.
        const world = buildWorld({ layer: "game" });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 400, clientY: 300 });
        world.dispatch("pointermove", { clientX: 700, clientY: 700 });
        check("fora da camada de efeitos a origem nao se move",
            world.state().shaders[0].x === 400);
    }

    {
        // Jogador nao move o shader do mestre.
        const world = buildWorld({ layer: "effects", isGm: false });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 400, clientY: 300 });
        world.dispatch("pointermove", { clientX: 700, clientY: 700 });
        world.dispatch("pointerup", { clientX: 700, clientY: 700 });
        await world.settle();
        check("jogador nao arrasta origem alheia",
            world.posts.length === 0 && world.state().shaders[0].x === 400);
    }
}

// --- o fluxo da ferramenta ---------------------------------------------------
//
// Escolhe na barra, pinga no mapa, o editor abre naquele shader, cola o codigo,
// salva. O caminho anterior — criar pelo editor, achar na lista, so entao
// escrever — cobrava tres passos antes da primeira linha de GLSL.

async function toolFlowChecks() {
    {
        const world = buildWorld({ layer: "effects", tool: "shader", shaders: [] });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 520, clientY: 360 });
        await world.settle();

        const criado = world.posts.find((p) => p.url.endsWith("/game/shaders"));
        check("pingar no mapa cria o shader", Boolean(criado), JSON.stringify(world.posts.map((p) => p.url)));
        check("no ponto em que se clicou", criado?.body.x === 520 && criado?.body.y === 360,
            JSON.stringify(criado?.body));
        check("sem pedir nome", !("name" in (criado?.body || {})));

        const abriu = world.emitted.find((e) => e.type === "lighting:edit-shader");
        check("e o editor abre ja naquele shader", Boolean(abriu?.detail?.shaderId),
            "o clique ja disse qual e: obrigar a acha-lo numa lista e refazer o trabalho");
        check("o shader entra no estado", world.state().shaders.length === 1);
    }

    {
        // Clicar de novo em cima de um que existe abre aquele. Empilhar dois no
        // mesmo ponto seria pagar dois passes de tela pelo mesmo desenho.
        const world = buildWorld({ layer: "effects", tool: "shader" });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 400, clientY: 300 });
        await world.settle();
        check("clicar sobre um que existe nao cria outro",
            !world.posts.some((p) => p.url.endsWith("/game/shaders")));
        const abriu = world.emitted.filter((e) => e.type === "lighting:edit-shader").pop();
        check("abre o que ja estava ali", abriu?.detail?.shaderId === "s1");
    }

    {
        // Fora da camada de Efeitos a ferramenta nao age: o clique e do tabuleiro.
        const world = buildWorld({ layer: "game", tool: "shader", shaders: [] });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 520, clientY: 360 });
        await world.settle();
        check("a camada errada nao cria shader",
            !world.posts.some((p) => p.url.endsWith("/game/shaders")));
    }

    {
        const world = buildWorld({ layer: "effects", tool: "shader", isGm: false, shaders: [] });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 520, clientY: 360 });
        await world.settle();
        check("jogador nao cria shader", world.posts.length === 0);
    }
}

// --- parte 2: compilar, falhar e sobreviver ---------------------------------

function loadEffects({ failOn = null } = {}) {
    const dispatched = [];
    const built = [];
    const gl = {
        FRAGMENT_SHADER: 1, COMPILE_STATUS: 2,
        createShader: () => ({ src: "" }),
        shaderSource: (handle, src) => { handle.src = src; },
        compileShader: (handle) => { handle.ok = !(failOn && handle.src.includes(failOn)); },
        getShaderParameter: (handle) => handle.ok,
        getShaderInfoLog: () => "ERROR: 0:14: 'finalColour' : undeclared identifier",
        deleteShader() {},
    };

    class Sprite {
        constructor(texture) {
            this.texture = texture;
            this.width = 0; this.height = 0;
            this.visible = true; this.destroyed = false;
            this.mask = null; this.filters = null;
            this.anchorValue = null;
            this.position = { x: 0, y: 0, set: (x, y) => { this.position.x = x; this.position.y = y; } };
            this.anchor = { set: (v) => { this.anchorValue = v; } };
        }
        destroy() { this.destroyed = true; }
    }

    class Mesh extends Sprite {
        constructor(options) {
            super(null);
            this.geometry = options.geometry;
            this.shader = options.shader;
            this.isMesh = true;
        }
    }

    // Graphics de mentira que guarda o que foi desenhado: e o desenho, e nao a
    // existencia do objeto, que diz se a parede recortou alguma coisa.
    class Graphics {
        constructor() {
            this.visible = true; this.destroyed = false;
            this.shapes = [];
            this.position = { x: 0, y: 0, set: (x, y) => { this.position.x = x; this.position.y = y; } };
        }
        clear() { this.shapes = []; return this; }
        poly(points) { this.shapes.push({ kind: "poly", points }); return this; }
        circle(x, y, r) { this.shapes.push({ kind: "circle", x, y, r }); return this; }
        fill(value) {
            const last = this.shapes[this.shapes.length - 1];
            if (last) last.fill = value;
            return this;
        }
        stroke(value) {
            const last = this.shapes[this.shapes.length - 1];
            if (last) last.stroke = value;
            return this;
        }
        destroy() { this.destroyed = true; }
    }

    const PIXI = {
        defaultFilterVert: "vert",
        // `from` so e usada para o pixel preto de fallback; devolver um objeto
        // com `source` e o que permite conferir QUAL textura foi ligada.
        Texture: { WHITE: "white", from: () => ({ source: "preto" }) },
        Sprite,
        Mesh,
        MeshGeometry: class { constructor(options) { Object.assign(this, options); } },
        Graphics,
        FillGradient: class { constructor(o) { Object.assign(this, o); } },
        RenderTexture: { create: (o) => ({ ...o, source: `rt-${o.width}x${o.height}` }) },
        Container: class {
            constructor() { this.children = []; this.visible = true; this.destroyed = false; this.mask = null; }
            addChild(...n) { this.children.push(...n); }
            removeChildren() { this.children = []; }
            destroy() { this.destroyed = true; }
        },
        GlProgram: { from: ({ fragment }) => ({ fragment }) },
        UniformGroup: class { constructor(u) { this.uniforms = Object.fromEntries(Object.entries(u).map(([k, v]) => [k, v.value])); } },
        Filter: class { constructor(o) { Object.assign(this, o); built.push(this); } },
        Shader: class { constructor(o) { Object.assign(this, o); built.push(this); } },
    };
    ["DarkenBlend", "LightenBlend", "OverlayBlend", "HardLightBlend", "SoftLightBlend",
     "ColorDodgeBlend", "ColorBurnBlend", "DifferenceBlend", "ExclusionBlend", "SubtractBlend"]
        .forEach((name) => { PIXI[name] = class { destroy() { this.destroyed = true; } }; });

    const children = [];
    const effectsLayer = { addChild: (...nodes) => children.push(...nodes) };
    const rendered = [];
    const win = { GravewrightShaderEffects: null, PIXI };
    const doc = {
        readyState: "complete",
        addEventListener() {},
        dispatchEvent: (event) => dispatched.push(event),
        createElement: () => ({
            width: 0, height: 0,
            getContext: () => ({
                createRadialGradient: () => ({ addColorStop() {} }),
                fillRect() {}, set fillStyle(_v) {},
            }),
        }),
    };
    new Function("window", "document", "PIXI", "CustomEvent", "performance", "console",
        fs.readFileSync(EFFECTS, "utf8"))(
        win, doc, PIXI,
        class { constructor(type, init) { this.type = type; this.detail = init?.detail; } },
        { now: () => 5000 }, { log() {}, warn() {}, error() {} },
    );
    return {
        api: win.GravewrightShaderEffects, gl, dispatched, built, children,
        rendered,
        board: { app: { renderer: { gl, render: (call) => rendered.push(call) } }, effectsLayer },
        // Sprites vivos na camada, na ordem em que entraram.
        sprites: () => children.filter((node) => node.isMesh && !node.destroyed),
        masks: () => children.filter((node) => node instanceof Graphics && !node.destroyed),
    };
}

function effectChecks() {
    const CAM = { offsetX: 0, offsetY: 0, zoom: 1 };
    const draw = (world, shaders, camera = CAM, now = 5000, light = null) =>
        world.api.render(world.board, shaders, now, 800, 600, camera, light);

    {
        const world = loadEffects();
        const desenhados = draw(world, [SHADERS[0]]);
        check("shader valido desenha", desenhados === 1);
        check("num quadro proprio na camada de efeitos", world.sprites().length === 1);

        const fragment = world.built[0].glProgram.fragment;
        check("o preambulo entra antes do texto de quem escreveu",
            fragment.startsWith("#version 300 es") && fragment.includes("finalColor = vec4(uColor, 1.0)"));

        // A regra desta rodada: o texto de quem escreve chega INTEIRO a GPU. Nao ha
        // renomeacao de `main`, nao ha embrulho, nao ha nada acrescentado depois.
        // Enquanto havia, o GLSL deixava de ser da pessoa — e era o preco de tentar
        // conter o efeito lendo texto.
        check("o texto do mestre entra inteiro", fragment.includes(SHADERS[0].source));
        check("a opacidade e aplicada no mesmo passe",
            fragment.includes("gwUserMain(); finalColor *= gwUOpacity")
            && (fragment.match(/void main\s*\(/g) || []).length === 2);

        ["uTime", "uIntensity", "uOpacity", "uScale", "uSpeed", "uColor", "uResolution",
         "uOrigin", "uRadius", "uRotation", "uCamera", "uAspect", "uTexture", "vTextureCoord",
         "gwWorld", "gwRotated", "gwScreen", "gwScreenUV", "gwLight", "gwFeature", "gwPattern",
         // Os do proprio Pixi: sem eles nao ha como saber que pedaco do quadro
         // chegou, e a conta de mundo volta a escorregar com o zoom.
         "uFrameOrigin"]
            .forEach((name) => check(`o preambulo oferece ${name}`, fragment.includes(name)));

        const u = world.built[0].resources.shaderUniforms.uniforms;
        // Segundos, nao milissegundos: um float de GPU perde precisao, e com o
        // relogio cru a animacao congela depois de horas de sessao aberta.
        check("uTime chega em segundos", u.gwUTime === 5, `${u.gwUTime}`);
        check("a cor vira 0..1", u.gwUColor.every((c) => c >= 0 && c <= 1) && u.gwUColor[2] === 1,
            JSON.stringify(u.gwUColor));
    }

    // --- o desenho acompanha o alcance --------------------------------------
    //
    // Com tamanho fixo no mundo, um circulo pequeno mostrava um pedaco chapado de
    // um padrao gigante: a nevoa virava mancha, e diminuir o alcance parecia
    // quebrar o efeito. A lei abaixo e lida do proprio preambulo, e nao repetida
    // aqui — se a constante mudar la, esta verificacao muda junto.
    {
        const world = loadEffects();
        const lei = /gwURadius > 0\.0 \? gwURadius \* ([0-9.]+) : ([0-9.]+)/.exec(world.api.PREAMBLE);
        check("o tamanho do desenho esta amarrado ao alcance", Boolean(lei), "gwFeature nao encontrado");
        check("gwPattern nasce no ponto clicado",
            world.api.PREAMBLE.includes("(gwRotated(uv) - gwUOrigin) / gwFeature()"));

        const feature = (radius, scale) =>
            Math.max((radius > 0 ? radius * Number(lei[1]) : Number(lei[2])) * scale, 1);
        // "Quantas voltas de padrao cabem no diametro" e o que a pessoa enxerga.
        const voltas = (radius) => (radius * 2) / feature(radius, 1);

        check("circulo pequeno mostra tanto padrao quanto o grande",
            Math.abs(voltas(70) - voltas(4000)) < 1e-9,
            `${voltas(70).toFixed(2)} contra ${voltas(4000).toFixed(2)}`);
        // Poucas voltas viram mancha; muitas viram chuvisco. Entre duas e seis o
        // desenho ainda le como forma.
        check("e a quantidade e legivel", voltas(280) > 2 && voltas(280) < 6, `${voltas(280).toFixed(2)}`);

        // Escala MAIOR tem de dar desenho MAIOR. Antes o exemplo dividia o mundo
        // por uma constante e multiplicava por uScale, entao a regua "Escala"
        // encolhia o padrao ao ser aumentada — o contrario do que ela promete.
        check("aumentar a escala aumenta o desenho", feature(280, 4) > feature(280, 1),
            `${feature(280, 1)} -> ${feature(280, 4)}`);

        // Sem alcance nao ha raio a que se amarrar: vale uma medida de sala.
        check("cena inteira cai numa medida de sala",
            feature(0, 1) > 200 && feature(0, 1) < 900, `${feature(0, 1)}`);
    }

    // --- a contencao, que agora e do QUADRO e nao do texto -------------------
    {
        const world = loadEffects();
        const shader = { ...SHADERS[0], x: 250, y: 150, radiusWorld: 100 };
        const cam = { offsetX: 100, offsetY: 50, zoom: 2 };
        draw(world, [shader], cam);

        const sprite = world.sprites()[0];
        const mask = world.masks()[0];
        const raio = 100 * 2;
        const centro = { x: 250 * 2 + 100, y: 150 * 2 + 50 };
        check("o quadro tem o tamanho do alcance",
            sprite.width === raio * 2 && sprite.height === raio * 2,
            `${sprite.width}x${sprite.height}`);
        check("e fica centrado na origem",
            sprite.position.x === centro.x - raio && sprite.position.y === centro.y - raio,
            `${sprite.position.x},${sprite.position.y}`);
        // ISTO e a garantia: fora do quadro nao existe pixel para pintar, entao
        // nenhuma conta no GLSL alcanca o resto do mapa.
        check("com mascara por cima", sprite.mask === mask && mask.visible === true);
        const forma = mask.shapes[0];
        check("sem parede em volta, a forma e o proprio alcance",
            forma?.kind === "circle" && forma.r === raio, JSON.stringify(forma?.kind));
        check("e o degrade se apaga na borda do alcance",
            forma?.fill?.outerRadius === raio && forma.fill.type === "radial");

        const u = world.built[0].resources.shaderUniforms.uniforms;
        // A camera vai CRUA. Ela ja foi corrigida pelo canto do quadro, e essa
        // correcao so valia enquanto o quadro coubesse inteiro na tela — foi o que
        // trouxe o zoom de volta.
        check("a camera vai crua para o shader",
            u.gwUCamera[0] === cam.offsetX && u.gwUCamera[1] === cam.offsetY && u.gwUCamera[2] === cam.zoom,
            JSON.stringify(u.gwUCamera));
        check("e a tela vai junto", u.gwUScreen[0] === 800 && u.gwUScreen[1] === 600);

        // Conferencia da conta que o shader faz, com o que o PIXI entrega. O filtro
        // recorta a entrada no viewport, entao a conta e exercitada nos dois casos:
        // quadro inteiro na tela, e quadro cortado pela borda.
        const gwWorld = (uv, inputSize, outputFrame) => [
            (uv[0] * inputSize[0] + outputFrame[0] - u.gwUCamera[0]) / u.gwUCamera[2],
            (uv[1] * inputSize[1] + outputFrame[1] - u.gwUCamera[1]) / u.gwUCamera[2],
        ];

        // 1) quadro inteiro visivel: a entrada e o proprio quadro.
        const meio = gwWorld([0.5, 0.5], [sprite.width, sprite.height],
            [sprite.position.x, sprite.position.y]);
        check("o centro do quadro e a origem em mundo",
            Math.abs(meio[0] - 250) < 1e-9 && Math.abs(meio[1] - 150) < 1e-9, JSON.stringify(meio));

        // 2) quadro cortado: o Pixi entrega so o pedaco na tela, com outro tamanho
        // e outro canto. A MESMA origem tem de sair, senao o desenho escorrega
        // conforme o zoom — que era o defeito.
        const corte = { size: [sprite.width / 3, sprite.height / 4], at: [0, 0] };
        const uvDaOrigem = [
            (250 * cam.zoom + cam.offsetX - corte.at[0]) / corte.size[0],
            (150 * cam.zoom + cam.offsetY - corte.at[1]) / corte.size[1],
        ];
        const mesmo = gwWorld(uvDaOrigem, corte.size, corte.at);
        check("e continua sendo, mesmo com o quadro cortado na borda da tela",
            Math.abs(mesmo[0] - 250) < 1e-9 && Math.abs(mesmo[1] - 150) < 1e-9, JSON.stringify(mesmo));
    }

    {
        // Sem alcance o quadro e a tela inteira — e ai nao ha mascara, senao os
        // cantos do que se pediu inteiro sairiam recortados.
        const world = loadEffects();
        draw(world, [{ ...SHADERS[0], x: 100, y: 100, radiusWorld: 0 }]);
        const sprite = world.sprites()[0];
        check("sem alcance o quadro e a tela", sprite.width === 800 && sprite.height === 600);
        check("comecando no canto", sprite.position.x === 0 && sprite.position.y === 0);
        check("e sem mascara", sprite.mask === null && world.masks()[0].visible === false);
    }

    {
        // Zoom foi um defeito serio desta feature: origem e alcance viajavam
        // convertidos para tela, e cada mexida de camera reescrevia os dois.
        const world = loadEffects();
        const shader = { ...SHADERS[0], x: 900, y: 700, radiusWorld: 280 };
        draw(world, [shader], { offsetX: -100, offsetY: -50, zoom: 0.5 });
        const u = world.built[0].resources.shaderUniforms.uniforms;
        const origemLonge = [...u.gwUOrigin], raioLonge = u.gwURadius;
        draw(world, [shader], { offsetX: 320, offsetY: 240, zoom: 3 });

        check("a origem nao muda com o zoom",
            u.gwUOrigin[0] === origemLonge[0] && u.gwUOrigin[1] === origemLonge[1],
            `${JSON.stringify(origemLonge)} -> ${JSON.stringify(u.gwUOrigin)}`);
        check("e ela e o ponto de mundo, nao um ponto de tela",
            u.gwUOrigin[0] === 900 && u.gwUOrigin[1] === 700, JSON.stringify(u.gwUOrigin));
        check("o alcance tambem nao muda com o zoom", u.gwURadius === raioLonge && u.gwURadius === 280,
            `${raioLonge} -> ${u.gwURadius}`);

        // Grau e coisa de painel; a GPU quer radiano.
        draw(world, [{ ...shader, rotation: 90 }]);
        check("a rotacao chega em radianos", Math.abs(u.gwURotation - Math.PI / 2) < 1e-9, `${u.gwURotation}`);
    }

    // --- parede -------------------------------------------------------------
    //
    // A fumaca atravessava muro e aparecia em sala fechada, o que faz o efeito
    // parecer adesivo em vez de estar na cena. A oclusao nao entrou como uniform
    // para o shader multiplicar: ela e a FORMA da mascara, entao vale para
    // qualquer shader ja escrito, sem tocar em GLSL nenhum.
    {
        const world = loadEffects();
        const visivel = [{ x: 900, y: 700 }, { x: 1100, y: 700 }, { x: 1100, y: 900 }, { x: 900, y: 900 }];
        const shader = {
            ...SHADERS[0], x: 900, y: 700, radiusWorld: 280,
            occlusion: visivel, occlusionStamp: "geo-1",
        };
        const cam = { offsetX: 0, offsetY: 0, zoom: 1 };
        draw(world, [shader], cam);

        const forma = world.masks()[0].shapes[0];
        check("com parede em volta, a mascara vira o poligono", forma?.kind === "poly");
        check("com os vertices em tela", forma.points.length === visivel.length * 2);
        check("e o degrade continua ancorado na origem",
            forma.fill?.start?.x === 900 && forma.fill?.outerRadius === 280);

        // Repintar um poligono de dezenas de vertices a cada quadro com a cena
        // parada e desperdicio puro.
        const antes = world.masks()[0].shapes;
        draw(world, [shader], cam);
        check("cena parada nao repinta a mascara", world.masks()[0].shapes === antes);

        // Porta abrindo muda a geometria, e ai a forma TEM de ser refeita — e o
        // que faz a fumaca aparecer pelo vao.
        draw(world, [{ ...shader, occlusionStamp: "geo-2", occlusion: [...visivel, { x: 800, y: 800 }] }], cam);
        check("geometria nova repinta", world.masks()[0].shapes !== antes
            && world.masks()[0].shapes[0].points.length === (visivel.length + 1) * 2);

        // Mover a camera tambem: a mascara vive em tela, e o poligono em mundo.
        const depois = world.masks()[0].shapes;
        draw(world, [{ ...shader, occlusionStamp: "geo-2", occlusion: [...visivel, { x: 800, y: 800 }] }],
            { offsetX: 120, offsetY: 0, zoom: 1 });
        check("e mexer a camera tambem", world.masks()[0].shapes !== depois);
    }

    {
        // Cena inteira nao e ocluida, de proposito: chuva nao para na parede de um
        // mapa em corte, e seria o caso mais caro de calcular.
        const world = loadEffects();
        draw(world, [{ ...SHADERS[0], x: 900, y: 700, radiusWorld: 0, occlusion: [{ x: 1, y: 1 }, { x: 2, y: 2 }, { x: 3, y: 3 }] }]);
        check("efeito de cena inteira ignora parede",
            world.sprites()[0].mask === null && world.masks()[0].shapes.length === 0);
    }

    // --- a luz da cena chega ao shader --------------------------------------
    //
    // Oclusao coube na mascara porque parede e recorte. Cor nao e: uma nevoa perto
    // da tocha nao fica menor, fica dourada. Entao esta parte volta a ser uniform,
    // e o que ela precisa garantir e que a textura CERTA esta ligada em cada quadro.
    {
        const world = loadEffects();
        const shader = { ...SHADERS[0], x: 300, y: 200, radiusWorld: 120 };
        const luz = { source: "buffer-de-luz" };
        draw(world, [shader], { offsetX: 40, offsetY: 20, zoom: 1 }, 5000, luz);

        const filtro = world.built[0];
        check("o buffer de luz e ligado ao filtro",
            filtro.resources.gwULightBuffer === "buffer-de-luz");

        const u = filtro.resources.shaderUniforms.uniforms;
        const sprite = world.sprites()[0];
        // O tamanho da tela e o que leva do espaco do pedaco para o do buffer.
        // Errar isto faz a luz aparecer deslocada do foco.
        check("a tela vai ao shader", u.gwUScreen[0] === 800 && u.gwUScreen[1] === 600);

        // Conferencia da conta de gwScreenUV, com o pedaco que o Pixi entrega.
        const screenUV = (uv, inputSize, outputFrame) => [
            (uv[0] * inputSize[0] + outputFrame[0]) / u.gwUScreen[0],
            (uv[1] * inputSize[1] + outputFrame[1]) / u.gwUScreen[1],
        ];
        const meio = screenUV([0.5, 0.5], [sprite.width, sprite.height],
            [sprite.position.x, sprite.position.y]);
        check("e o centro do quadro cai no centro do efeito em tela",
            Math.abs(meio[0] - (300 + 40) / 800) < 1e-9
            && Math.abs(meio[1] - (200 + 20) / 600) < 1e-9, JSON.stringify(meio));
    }

    {
        // Sem buffer, o shader tem de ver PRETO. Branco faria toda cena sem foco
        // nenhum parecer iluminada, e deixar o anterior pendurado faria a luz de
        // uma cena vazar para a seguinte.
        const world = loadEffects();
        draw(world, [SHADERS[0]], CAM, 5000, { source: "primeiro" });
        draw(world, [SHADERS[0]], CAM, 5100, null);
        check("sem buffer o shader recebe preto",
            world.built[0].resources.gwULightBuffer === "preto",
            String(world.built[0].resources.gwULightBuffer));
    }

    // --- composicao e opacidade ---------------------------------------------
    {
        const world = loadEffects();
        const shader = { ...SHADERS[0], opacity: 0.35, blend_mode: "multiply" };
        draw(world, [shader]);
        const sprite = world.sprites()[0];
        const uniforms = world.built[0].resources.shaderUniforms.uniforms;
        check("a opacidade chega ao mesmo passe", uniforms.gwUOpacity === 0.35, `${uniforms.gwUOpacity}`);
        check("o sprite composto nao tem filtro", !sprite.filters);
        check("o modo fica na malha do shader", sprite.blendMode === "multiply", sprite.blendMode);
        check("a malha usa Shader, nao Filter", sprite.shader === world.built[0]);
    }

    // --- falhas -------------------------------------------------------------
    {
        const world = loadEffects({ failOn: "finalColor" });
        check("shader que nao compila nao desenha", draw(world, [SHADERS[0]]) === 0);
        check("e ninguem monta um filtro quebrado", world.built.length === 0);
        check("nem sobra quadro na camada", world.sprites().length === 0);
        check("o erro e avisado uma vez", world.dispatched.length === 1
            && world.dispatched[0].type === "vtt:shader-error");
        // A GPU numera a partir do arquivo inteiro; quem escreveu so viu o final.
        const message = world.dispatched[0].detail.error;
        check("a linha e corrigida pelo tamanho do preambulo", /linha 1\b/.test(message), message);
        check("e o erro fica consultavel pelo editor", world.api.errorFor("s1") === message);
    }

    {
        // Um quebrado no meio de bons nao pode levar os outros junto.
        const world = loadEffects({ failOn: "QUEBRADO" });
        const bad = { ...SHADERS[0], id: "s9", source: "void main(){ QUEBRADO }" };
        check("o vizinho quebrado nao derruba o que compila", draw(world, [SHADERS[0], bad]) === 1);
    }

    {
        // Orcamento: cada quadro de efeito custa por quadro de tela, e a cena nao
        // pode ser afundada por uma lista que ninguem revisou — porque ninguem
        // revisa mais.
        const world = loadEffects();
        const many = Array.from({ length: 9 }, (_, i) => ({ ...SHADERS[0], id: `m${i}` }));
        check("o orcamento limita quantos rodam por quadro", draw(world, many) === world.api.MAX_ACTIVE);
    }

    {
        // Editar o texto tem de recompilar: sem isso o mestre salva e continua
        // vendo a versao antiga ate recarregar a pagina.
        const world = loadEffects();
        draw(world, [SHADERS[0]]);
        const antes = world.built.length;
        draw(world, [{ ...SHADERS[0] }]);
        check("o mesmo texto reaproveita o programa", world.built.length === antes);
        draw(world, [{ ...SHADERS[0], source: "void main(){ finalColor = vec4(1.0); }" }]);
        check("texto editado compila de novo", world.built.length === antes + 1);
    }

    {
        // Shader apagado, desligado ou de outra cena leva o quadro junto — senao
        // ele fica aceso na tela para sempre.
        const world = loadEffects();
        draw(world, [SHADERS[0]]);
        const sprite = world.sprites()[0];
        draw(world, []);
        check("sumir da lista destroi o quadro", sprite.destroyed === true);
        check("e a camada fica limpa", world.sprites().length === 0);
    }
}

(async () => {
    await stateChecks();
    await originChecks();
    await toolFlowChecks();
    effectChecks();
    console.log(
        failures
            ? `\n${failures} verificacao(oes) de shader falharam`
            : "\ntodas as verificacoes de shader passaram",
    );
    process.exit(failures ? 1 : 0);
})();
