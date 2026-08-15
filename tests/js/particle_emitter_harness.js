/*
 * Colocar, ver e apagar um emissor de partícula.
 *
 * Existe porque a primeira versão criava o emissor no servidor e ele ficava
 * invisível e inalcançável na mesa, por dois motivos que nenhuma asserção de
 * texto pegaria: o clique era barrado antes de chegar à ferramenta (a porta
 * checava a camada da iluminação, e partícula mora na de composição), e não havia
 * marcador desenhado: a nuvem fica sob a escuridão, então numa sala escura não
 * havia nada para ver nem onde clicar.
 *
 * Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

// O arquivo real usa `new CustomEvent(...)` como global.
global.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init?.detail; } };

const SCRIPT = path.resolve(__dirname, "../../static/js/lighting/dynamic-lighting.js");

class El {
    constructor(tag, parent = null) {
        this.tag = tag;
        this.dataset = {};
        this.parent = parent;
        this.children = [];
        this.listeners = [];
        this.classList = { contains: () => true };
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

function buildWorld({ isGm = true, layer = "effects", tool = "particles", subTool = "smoke", zoom = 1 } = {}) {
    let scale = zoom;
    let visionMode = "cinematic";
    const root = new El("body");
    const workspace = new El("article", root);
    const surface = new El("div", workspace);
    surface.dataset.mapViewport = "";
    surface.dataset.lightingGm = isGm ? "true" : "false";
    const canvas = new El("canvas", surface);
    canvas.dataset.mapCanvas = "";
    canvas.dataset.roomId = "campaign-1";

    const posts = [];
    const emitters = [];
    const tools = { activeTool: tool, activeSubTool: subTool, activeLayer: layer, isLayerVisible: () => true };
    const documentListeners = [];

    const sandbox = {
        window: {
            GravewrightTools: tools,
            GravewrightMap: {
                redraw() {},
                sceneDataFor: () => ({ id: "scene-1", width: 2000, height: 2000, scaledTileSize: 70, darkness: 0.9 }),
                tokenStoreFor: () => new Map(),
                isPlayerView: () => false,
                screenToWorldXY: (x, y) => ({ worldX: x, worldY: y }),
                // O controlador converte o clique por aqui; sem o stub, `world()`
                // devolve null e nenhuma ferramenta chega a agir.
                // A tela vira mundo dividindo pelo zoom, como no app: e por isso
                // que a tolerancia de clique tem de ser corrigida por ele.
                worldFromScreen: (_canvas, x, y) => ({ worldX: x / scale, worldY: y / scale }),
                stateFor: () => ({ zoom: scale }),
                activeCanvas: () => canvas,
                history: { push() {} },
            },
            GravewrightVisionMode: { current: () => visionMode, isClassic: () => visionMode === "classic" },
            GravewrightToasts: { showToast() {} },
            requestAnimationFrame() {},
            csrfToken: () => "csrf",
        },
        document: {
            readyState: "complete",
            body: { dataset: { currentUserId: "user-gm" } },
            addEventListener: (type, fn) => documentListeners.push({ type, fn }),
            dispatchEvent: (event) => documentListeners
                .filter((l) => l.type === event.type).forEach((l) => l.fn(event)),
            querySelector: (selector) => (selector === "[data-map-canvas]" ? canvas : null),
            querySelectorAll: (selector) => (selector === "[data-map-canvas]" ? [canvas] : []),
        },
        fetch: async (url, options = {}) => {
            if ((options.method || "GET") !== "POST") {
                if (url.includes("/game/particles/")) {
                    return { ok: true, json: async () => ({ emitters: emitters.map((e) => ({ ...e })) }) };
                }
                return { ok: true, json: async () => ({ walls: [], lights: [] }) };
            }
            const body = JSON.parse(options.body);
            posts.push({ url, body });
            if (url.endsWith("/game/particles")) {
                const emitter = {
                    id: `E${posts.length}`, x: body.x, y: body.y, kind: body.kind,
                    scale: body.scale, density: body.density, color: body.color, enabled: 1,
                };
                emitters.push(emitter);
                return { ok: true, json: async () => ({ emitter: { ...emitter } }) };
            }
            if (url.endsWith("/game/particles/delete-many")) {
                const gone = new Set(body.emitter_ids || []);
                for (let i = emitters.length - 1; i >= 0; i -= 1) {
                    if (gone.has(emitters[i].id)) emitters.splice(i, 1);
                }
                return { ok: true, json: async () => ({ emitter_ids: [...gone], scene_id: "scene-1" }) };
            }
            if (url.endsWith("/game/particles/delete")) {
                const at = emitters.findIndex((e) => e.id === body.emitter_id);
                if (at >= 0) emitters.splice(at, 1);
                return { ok: true, json: async () => ({ emitter_id: body.emitter_id, scene_id: "scene-1" }) };
            }
            return { ok: true, json: async () => ({}) };
        },
    };

    new Function("window", "document", "fetch", "CSS", "console", "performance",
        fs.readFileSync(SCRIPT, "utf8"))(
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
        documentListeners.filter((l) => l.type === type).forEach((l) => l.fn(event));
        return event;
    };

    return {
        dispatch, posts, canvas, tools,
        setLayer: (next) => {
            tools.activeLayer = next;
            documentListeners.filter((l) => l.type === "tool:active-layer")
                .forEach((l) => l.fn({ detail: { layer: next } }));
        },
        setZoom: (next) => { scale = next; },
        setVisionMode: (mode) => { visionMode = mode; },
        onDocument: (type, fn) => documentListeners.push({ type, fn }),
        state: () => sandbox.window.GravewrightLighting.stateForCanvas(canvas),
        settle: async () => { for (let i = 0; i < 12; i += 1) await Promise.resolve(); },
    };
}

let failures = 0;
function check(label, condition, detail = "") {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}${detail ? `  (${detail})` : ""}`);
    if (!condition) failures += 1;
}

(async () => {
    // --- colocar na camada de composição ------------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();

        const created = world.posts.find((p) => p.url.endsWith("/game/particles"));
        check("clicar na composicao cria o emissor", Boolean(created),
            JSON.stringify(world.posts.map((p) => p.url)));
        check("com o tipo escolhido no dock", created?.body.kind === "smoke");
        check("o emissor entra no estado", world.state().particleClouds.length === 1);
    }

    // --- o ponto de origem precisa ser visível -------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();

        const state = world.state();
        // Sem isto o emissor existe e é invisível: a nuvem fica sob a escuridão.
        check("o marcador aparece enquanto se compoe a cena", state.editingParticles === true);
        const cloud = state.particleClouds[0];
        check("e o marcador sabe onde e de que tipo",
            Number.isFinite(cloud.x) && Number.isFinite(cloud.y) && cloud.kind === "smoke");

        world.setLayer("game");
        check("mas some quando o mestre volta a jogar", world.state().editingParticles === false);
    }

    // --- a camada errada não cria -------------------------------------------
    {
        const world = buildWorld({ layer: "lighting" });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();
        check("a ferramenta de particula nao age na camada de iluminacao",
            !world.posts.some((p) => p.url.endsWith("/game/particles")));
    }

    // --- jogador não coloca --------------------------------------------------
    {
        const world = buildWorld({ isGm: false });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();
        check("jogador nao coloca emissor",
            !world.posts.some((p) => p.url.endsWith("/game/particles")));
    }

    // --- selecionar e apagar -------------------------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();
        check("o emissor nasce selecionado", world.state().particleClouds[0].selected === true);

        world.dispatch("keydown", { key: "Delete", target: { closest: () => null } });
        await world.settle();
        // Um pedido para a selecao inteira, mesmo com um item so: apagar em laco
        // enchia a mesa de avisos e a cena sumia aos pedacos na tela dos outros.
        check("Delete na camada de efeitos apaga o emissor",
            world.posts.some((p) => p.url.endsWith("/game/particles/delete-many")),
            "sem isto ele so sairia da cena pelo banco");
        check("e ele some do estado", world.state().particleClouds.length === 0);
    }

    // --- mover -----------------------------------------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();

        // Pegar e arrastar comeca no mesmo clique que seleciona: pedir um segundo
        // clique para mover e atrito puro.
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        world.dispatch("pointermove", { clientX: 480, clientY: 360 });
        const dragging = world.state().particleClouds[0];
        check("a nuvem acompanha o ponteiro durante o arraste",
            Math.round(dragging.x) === 480 && Math.round(dragging.y) === 360,
            `${Math.round(dragging.x)},${Math.round(dragging.y)}`);

        world.dispatch("pointerup", { clientX: 480, clientY: 360 });
        await world.settle();
        const moved = world.posts.filter((p) => p.url.endsWith("/game/particles/update"));
        check("e a posicao nova e gravada ao soltar",
            moved.length === 1 && moved[0].body.x === 480 && moved[0].body.y === 360,
            JSON.stringify(moved.map((p) => p.body)));
    }

    // --- clique parado não é arraste --------------------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();

        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        world.dispatch("pointerup", { clientX: 300, clientY: 300 });
        await world.settle();
        check("selecionar sem mover nao grava nada",
            !world.posts.some((p) => p.url.endsWith("/game/particles/update")),
            "sem a folga, cada toque viraria uma gravacao");
    }

    // --- multisselecao: mouse e teclado ------------------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        world.dispatch("pointerdown", { clientX: 600, clientY: 300 });
        await world.settle();
        world.tools.activeTool = "select";
        world.dispatch("pointerdown", { clientX: 250, clientY: 250 });
        world.dispatch("pointermove", { clientX: 650, clientY: 350 });
        world.dispatch("pointerup", { clientX: 650, clientY: 350 });
        check("a caixa seleciona varios efeitos", world.state().picked.emitter.size === 2);

        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        world.dispatch("pointermove", { clientX: 350, clientY: 340 });
        world.dispatch("pointerup", { clientX: 350, clientY: 340 });
        await world.settle();
        let clouds = world.state().particleClouds;
        check("arrastar um efeito move toda a selecao",
            clouds[0].x === 350 && clouds[0].y === 340
            && clouds[1].x === 650 && clouds[1].y === 340,
            JSON.stringify(clouds));

        world.dispatch("keydown", { key: "ArrowRight", target: { closest: () => null } });
        await world.settle();
        clouds = world.state().particleClouds;
        check("seta move todos os efeitos selecionados",
            clouds[0].x === 385 && clouds[1].x === 685,
            JSON.stringify(clouds));
    }

    // --- duplo clique abre o painel ---------------------------------------------
    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();

        let asked = null;
        world.onDocument("lighting:edit-emitter", (event) => { asked = event.detail; });
        world.dispatch("dblclick", { clientX: 300, clientY: 300 });
        check("duplo clique pede o painel do emissor", Boolean(asked?.emitterId));
    }

    // --- todo emissor precisa ser clicavel, em qualquer zoom -------------------
    {
        for (const zoom of [0.4, 1, 2.5]) {
            const world = buildWorld({ zoom });
            await world.settle();

            // Uma fileira de emissores, longe um do outro.
            const spots = [[200, 200], [600, 240], [1000, 700], [420, 900], [1400, 300]];
            for (const [x, y] of spots) {
                world.dispatch("pointerdown", { clientX: x * zoom, clientY: y * zoom });
                world.dispatch("pointerup", { clientX: x * zoom, clientY: y * zoom });
                await world.settle();
            }
            check(`zoom ${zoom}: os ${spots.length} emissores foram criados`,
                world.state().particleClouds.length === spots.length,
                `${world.state().particleClouds.length}`);
            world.tools.activeTool = "select";

            // E cada um responde ao clique no proprio ponto.
            const unreachable = [];
            for (const [x, y] of spots) {
                world.dispatch("pointerdown", { clientX: 1900 * zoom, clientY: 1900 * zoom });
                world.dispatch("pointerup", { clientX: 1900 * zoom, clientY: 1900 * zoom });
                world.dispatch("pointerdown", { clientX: x * zoom, clientY: y * zoom });
                world.dispatch("pointerup", { clientX: x * zoom, clientY: y * zoom });
                await world.settle();
                const picked = world.state().particleClouds.find((c) => c.selected);
                if (!picked || Math.round(picked.x) !== x || Math.round(picked.y) !== y) {
                    unreachable.push(`${x},${y}`);
                }
            }
            check(`zoom ${zoom}: todos sao selecionaveis`, unreachable.length === 0,
                unreachable.length ? `sem resposta em ${unreachable.join(" ")}` : "");
        }
    }

    // --- aglomerado: cada um tem de responder no proprio ponto -----------------
    {
        // O aglomerado nao nasce de cliques seguidos: a tolerancia faz o segundo
        // clique SELECIONAR o vizinho em vez de criar. Ele nasce de colocar com o
        // mapa aproximado e depois trabalhar afastado: a tolerancia e em pixels de
        // tela, entao afastar junta tudo dentro dela. E o caso da mesa.
        const world = buildWorld({ zoom: 4 });
        await world.settle();

        const spots = [[500, 500], [508, 500], [516, 500], [508, 508]];
        for (const [x, y] of spots) {
            world.dispatch("pointerdown", { clientX: x * 4, clientY: y * 4 });
            world.dispatch("pointerup", { clientX: x * 4, clientY: y * 4 });
            await world.settle();
        }
        check("aproximado, os quatro cabem", world.state().particleClouds.length === 4,
            `${world.state().particleClouds.length}`);
        world.tools.activeTool = "select";

        // Agora afastado: os quatro caem dentro da mesma tolerancia.
        world.setZoom(0.5);
        const unreachable = [];
        for (const [x, y] of spots) {
            world.dispatch("pointerdown", { clientX: 1900 * 0.5, clientY: 1900 * 0.5 });
            world.dispatch("pointerup", { clientX: 1900 * 0.5, clientY: 1900 * 0.5 });
            world.dispatch("pointerdown", { clientX: x * 0.5, clientY: y * 0.5 });
            world.dispatch("pointerup", { clientX: x * 0.5, clientY: y * 0.5 });
            await world.settle();
            const picked = world.state().particleClouds.find((c) => c.selected);
            if (!picked || Math.round(picked.x) !== x || Math.round(picked.y) !== y) {
                unreachable.push(
                    `${x},${y} -> ${picked ? `${Math.round(picked.x)},${Math.round(picked.y)}` : "nenhum"}`,
                );
            }
        }
        check("afastado, cada um ainda responde no proprio ponto",
            unreachable.length === 0,
            unreachable.length ? `pegou o vizinho em ${unreachable.join(" | ")}` : "");
    }

    // --- partícula é o efeito do modo LEVE ---------------------------------------
    {
        // A regra: cinematográfico desenha o efeito por shader, clássico o desenha
        // por partícula. Suprimir partícula no clássico deixava o modo leve sem
        // efeito nenhum, o oposto da intenção.
        const world = buildWorld();
        world.setVisionMode("classic");
        await world.settle();
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        await world.settle();

        const cloud = world.state().particleClouds[0];
        check("no modo classico a nuvem existe", cloud.particles.length > 0,
            `${cloud.particles.length} particulas`);

        world.setVisionMode("cinematic");
        check("e no cinematografico tambem, ate o shader chegar",
            world.state().particleClouds[0].particles.length > 0);
    }

    console.log(
        failures
            ? `\n${failures} verificacao(oes) de emissor falharam`
            : "\ntodas as verificacoes de emissor passaram",
    );
    process.exit(failures ? 1 : 0);
})();
