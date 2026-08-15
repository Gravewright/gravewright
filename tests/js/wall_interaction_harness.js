/*
 * Cobertura de comportamento para o desenho de paredes (static/js/lighting/dynamic-lighting.js).
 *
 * O arquivo real e carregado sobre um DOM minimo que replica a propagacao em fase
 * de captura, para que a sequencia de ponteiros seja exercitada de verdade em vez
 * de conferida por busca de texto. Sai com codigo != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

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
    setPointerCapture(id) { this.captured = id; }
    releasePointerCapture(id) {
        if (this.captured !== id) throw new Error("pointer nao capturado");
        this.captured = null;
    }
    path() {
        const chain = [];
        for (let node = this; node; node = node.parent) chain.unshift(node);
        return chain;
    }
}

function buildWorld({
    sceneId = "scene-1", isGm = true, activeTool = "wall", activeLayer = "walls",
    darkness = 0, userId = "user-gm", tokens = [], playerView = false, walls = [],
} = {}) {
    const root = new El("body");
    const workspace = new El("article", root);
    const surface = new El("div", workspace);
    surface.dataset.mapViewport = "";
    surface.dataset.lightingGm = isGm ? "true" : "false";
    const canvas = new El("canvas", surface);
    canvas.dataset.mapCanvas = "";
    canvas.dataset.roomId = "campaign-1";
    if (sceneId) canvas.dataset.sceneId = sceneId;

    const documentListeners = [];
    const posts = [];
    const gets = [];
    const warnings = [];
    const tools = { activeTool, activeLayer, activeSubTool: "torch", isLayerVisible: () => true };
    const serverWalls = new Map();
    const serverLights = new Map();
    const tokenStore = new Map(tokens.map((token) => [token.token_id, token]));
    let currentSceneId = sceneId;
    let currentDarkness = darkness;
    let currentDrag = null;

    const bucket = (store, id) => {
        if (!store.has(id)) store.set(id, []);
        return store.get(id);
    };
    const wallsOf = (id) => bucket(serverWalls, id);
    const lightsOf = (id) => bucket(serverLights, id);
    const snapshot = (id) => wallsOf(id).map((wall) => ({ ...wall }));
    const lightSnapshot = (id) => lightsOf(id).map((light) => ({ ...light }));
    // Paredes pre-existentes: um jogador nunca poderia desenha-las, entao cenarios
    // de operacao em jogo comecam com a geometria ja no "servidor".
    if (sceneId) walls.forEach((wall, index) => wallsOf(sceneId).push({
        id: `seed${index + 1}`, kind: "wall", door_state: "closed", ...wall,
    }));

    function dispatch(type, props = {}) {
        const event = {
            type, target: canvas, button: 0, pointerId: 1, clientX: 0, clientY: 0,
            shiftKey: false, altKey: false, ctrlKey: false,
            defaultPrevented: false, propagationStopped: false,
            preventDefault() { this.defaultPrevented = true; },
            stopPropagation() { this.propagationStopped = true; },
            ...props,
        };
        const chain = canvas.path();
        for (const node of chain) {
            for (const listener of node.listeners) {
                if (listener.type !== type || !listener.capture) continue;
                listener.fn(event);
                if (event.propagationStopped) return event;
            }
        }
        for (const node of [...chain].reverse()) {
            for (const listener of node.listeners) {
                if (listener.type !== type || listener.capture) continue;
                listener.fn(event);
                if (event.propagationStopped) return event;
            }
        }
        for (const listener of documentListeners) if (listener.type === type) listener.fn(event);
        return event;
    }

    const sandbox = {
        CSS: { escape: String },
        console: { warn: (...args) => warnings.push(args.join(" ")), error: () => {}, debug: () => {} },
        window: {
            // No-op de proposito: o laco de animacao dos focos se reagenda via rAF e
            // executar o callback aqui recursaria sem fim.
            requestAnimationFrame: () => 0,
            csrfToken: () => "token",
            GravewrightTools: tools,
            GravewrightToasts: { showToast: () => {} },
            GravewrightMap: {
                redraw: () => {},
                sceneDataFor: () => (currentSceneId
                    ? { id: currentSceneId, width: 1672, height: 941, scaledTileSize: 70, darkness: currentDarkness }
                    : null),
                stateFor: () => ({ offsetX: 0, offsetY: 0, zoom: 1 }),
                worldFromScreen: (_c, x, y) => ({ worldX: x, worldY: y, zoom: 1 }),
                tokenStoreFor: () => tokenStore,
                activeTokenDrag: () => currentDrag,
                activeCanvas: () => canvas,
                history: { push: () => {} },
                isPlayerView: () => playerView,
            },
        },
        performance: { now: () => 0 },
        document: {
            readyState: "complete",
            body: { dataset: { currentUserId: userId } },
            addEventListener: (type, fn) => documentListeners.push({ type, fn }),
            querySelectorAll: (selector) => (selector === "[data-map-canvas]" ? [canvas] : []),
            querySelector: () => null,
        },
        fetch: async (url, options = {}) => {
            const method = options.method || "GET";
            if (method !== "POST") {
                gets.push(url);
                if (url.includes("/game/lights/")) {
                    const id = decodeURIComponent(url.split("/game/lights/")[1].split("?")[0]);
                    return { ok: true, json: async () => ({ lights: lightSnapshot(id) }) };
                }
                const id = decodeURIComponent(url.split("/game/walls/")[1].split("?")[0]);
                return { ok: true, json: async () => ({ walls: snapshot(id) }) };
            }
            const body = JSON.parse(options.body);
            posts.push({ url, body });
            if (url.endsWith("/game/lights")) {
                const light = {
                    id: `L${posts.length}`, x: body.x, y: body.y,
                    bright_radius: body.bright_radius, dim_radius: body.dim_radius,
                    color: body.color, intensity: body.intensity,
                    animation: body.animation, enabled: 1,
                    // O servidor de verdade completa estes; sem eles aqui, o facho
                    // do farol nunca seria exercitado pelo harness.
                    angle: body.angle ?? 360, rotation: body.rotation ?? 0,
                };
                lightsOf(body.scene_id).push(light);
                return { ok: true, json: async () => ({ light: { ...light } }) };
            }
            if (url.endsWith("/game/lights/update")) {
                const light = [...serverLights.values()].flat().find((l) => l.id === body.light_id);
                if (light) Object.assign(light, { x: body.x ?? light.x, y: body.y ?? light.y });
                return { ok: true, json: async () => ({ light: { ...light } }) };
            }
            if (url.endsWith("/game/lights/delete")) {
                serverLights.forEach((list, key) => serverLights.set(key, list.filter((l) => l.id !== body.light_id)));
                return { ok: true, json: async () => ({ light_id: body.light_id }) };
            }
            if (url.endsWith("/game/lights/delete-many")) {
                const gone = new Set(body.light_ids || []);
                serverLights.forEach((list, key) => serverLights.set(key, list.filter((l) => !gone.has(l.id))));
                return { ok: true, json: async () => ({ light_ids: [...gone], scene_id: "scene-1" }) };
            }
            if (url.endsWith("/game/walls/split")) {
                const wall = wallsOf("scene-1").find((w) => w.id === body.wall_id);
                if (wall) {
                    const antigo = { x2: wall.x2, y2: wall.y2 };
                    wall.x2 = body.x; wall.y2 = body.y;
                    wallsOf("scene-1").push({
                        ...wall, id: `S${wallsOf("scene-1").length + 1}`,
                        x1: body.x, y1: body.y, x2: antigo.x2, y2: antigo.y2,
                    });
                }
                return { ok: true, json: async () => ({ walls: snapshot("scene-1"), scene_id: "scene-1" }) };
            }
            if (url.endsWith("/game/walls/delete-many")) {
                const gone = new Set(body.wall_ids || []);
                serverWalls.forEach((list, key) => serverWalls.set(key, list.filter((w) => !gone.has(w.id))));
                return { ok: true, json: async () => ({ wall_ids: [...gone], scene_id: "scene-1" }) };
            }
            if (url.endsWith("/game/walls/move-many")) {
                const ids = new Set(body.wall_ids || []);
                wallsOf(body.scene_id).forEach((wall) => {
                    if (!ids.has(wall.id)) return;
                    wall.x1 += body.dx; wall.y1 += body.dy;
                    wall.x2 += body.dx; wall.y2 += body.dy;
                });
                return { ok: true, json: async () => ({ walls: snapshot(body.scene_id) }) };
            }
            if (url.endsWith("/door-state")) {
                const wall = [...serverWalls.values()].flat().find((w) => w.id === body.wall_id);
                if (wall) wall.door_state = body.door_state;
                return { ok: true, json: async () => ({ wall: { ...wall } }) };
            }
            if (url.endsWith("/move-node")) {
                const at = (x, y) => Math.hypot(x - body.from_x, y - body.from_y) <= 1;
                wallsOf(body.scene_id).forEach((wall) => {
                    if (at(wall.x1, wall.y1)) { wall.x1 = body.to_x; wall.y1 = body.to_y; }
                    if (at(wall.x2, wall.y2)) { wall.x2 = body.to_x; wall.y2 = body.to_y; }
                });
                return { ok: true, json: async () => ({ walls: snapshot(body.scene_id) }) };
            }
            const wall = {
                id: `w${posts.length}`, kind: body.kind, door_state: "closed",
                x1: body.x1, y1: body.y1, x2: body.x2, y2: body.y2,
            };
            wallsOf(body.scene_id).push(wall);
            return { ok: true, json: async () => ({ wall: { ...wall } }) };
        },
    };

    new Function("window", "document", "fetch", "CSS", "console", "performance", fs.readFileSync(SCRIPT, "utf8"))(
        sandbox.window, sandbox.document, sandbox.fetch, sandbox.CSS, sandbox.console, sandbox.performance,
    );

    return {
        dispatch, posts, gets, warnings, canvas,
        setTool: (nextTool) => { tools.activeTool = nextTool; },
        setSubTool: (nextSub) => { tools.activeSubTool = nextSub; },
        setLayer: (nextLayer) => {
            tools.activeLayer = nextLayer;
            documentListeners.filter((l) => l.type === "tool:active-layer")
                .forEach((l) => l.fn({ detail: { layer: nextLayer } }));
        },
        setDarkness: (value) => { currentDarkness = value; },
        previewVision: (tokenId) => {
            documentListeners.filter((l) => l.type === "token:vision-preview")
                .forEach((l) => l.fn({ detail: { tokenId } }));
        },
        selectToken: (tokenId) => {
            documentListeners.filter((l) => l.type === "vtt:token-selection-changed")
                .forEach((l) => l.fn({ detail: { tokenId } }));
        },
        moveToken: (tokenId, gridX, gridY) => {
            const token = tokenStore.get(tokenId);
            if (token) { token.grid_x = gridX; token.grid_y = gridY; }
            documentListeners.filter((l) => l.type === "vtt:transport-event")
                .forEach((l) => l.fn({ detail: { event: "tokens.moved", payload: {} } }));
        },
        setScene: (nextId) => {
            currentSceneId = nextId;
            if (nextId) canvas.dataset.sceneId = nextId;
            else delete canvas.dataset.sceneId;
        },
        // Arrasto em curso: o store so recebe a posicao no fim, entao a visao
        // precisa ler daqui para acompanhar ao vivo.
        dragToken: (tokenId, gridX, gridY) => {
            currentDrag = { canvas, tokenId, currentGridX: gridX, currentGridY: gridY };
        },
        dropToken: () => { currentDrag = null; },
        blocksMovement: (from, to) =>
            sandbox.window.GravewrightLighting.blocksMovement(canvas, from, to),
        state: () => sandbox.window.GravewrightLighting.stateForCanvas(canvas),
        settle: async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); },
    };
}

const failures = [];
function check(name, condition, detail = "") {
    if (condition) return console.log(`ok   ${name}`);
    failures.push(name);
    console.log(`FAIL ${name}${detail ? ` :: ${detail}` : ""}`);
}

async function clickAt(world, x, y, props = {}) {
    world.dispatch("pointerdown", { clientX: x, clientY: y, ...props });
    world.dispatch("pointerup", { clientX: x, clientY: y, ...props });
    await world.settle();
}

(async () => {
    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200);
        check("primeiro clique ancora sem criar parede", world.posts.length === 0 && !!world.state().start);
        world.dispatch("pointermove", { clientX: 400, clientY: 205 });
        await clickAt(world, 400, 205);
        check("segundo clique crava a parede", world.posts.length === 1, JSON.stringify(world.posts));
        check("angulo livre: coordenadas nao sao encaixadas na grade",
            world.posts[0] && world.posts[0].body.x1 === 200 && world.posts[0].body.y1 === 200
            && world.posts[0].body.x2 === 400 && world.posts[0].body.y2 === 205,
            JSON.stringify(world.posts[0]?.body));
    }

    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200, { shiftKey: true });
        await clickAt(world, 400, 205, { shiftKey: true });
        check("Shift encaixa na meia-celula",
            world.posts.length === 1 && world.posts[0].body.x1 === 210 && world.posts[0].body.y1 === 210
            && world.posts[0].body.x2 === 385 && world.posts[0].body.y2 === 210,
            JSON.stringify(world.posts[0]?.body));
    }

    {
        const world = buildWorld();
        await world.settle();
        world.dispatch("pointerdown", { clientX: 100, clientY: 100 });
        world.dispatch("pointermove", { clientX: 300, clientY: 100 });
        world.dispatch("pointerup", { clientX: 300, clientY: 100 });
        await world.settle();
        check("arrastar e soltar crava a parede", world.posts.length === 1, JSON.stringify(world.posts));
    }

    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200);
        await clickAt(world, 400, 200);
        const anchor = world.state().start;
        check("parede encadeia por padrao", !!anchor && anchor.x === 400 && anchor.y === 200, JSON.stringify(anchor));
        await clickAt(world, 400, 400);
        check("segmento encadeado sai do endpoint anterior",
            world.posts.length === 2 && world.posts[1].body.x1 === 400 && world.posts[1].body.y1 === 200,
            JSON.stringify(world.posts[1]?.body));
    }

    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200);
        await clickAt(world, 400, 200, { altKey: true });
        check("Alt encerra a corrente", world.posts.length === 1 && world.state().start === null);
    }

    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 203, 197);
        await clickAt(world, 411, 202);
        check("angulo livre preserva o pixel exato",
            world.posts.length === 1 && world.posts[0].body.x1 === 203 && world.posts[0].body.y1 === 197,
            JSON.stringify(world.posts[0]?.body));
    }

    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200);
        await clickAt(world, 400, 200);
        await clickAt(world, 400, 400);
        // fecha o circuito: clique perto do primeiro ponto deve grudar nele
        await clickAt(world, 208, 206);
        const last = world.posts[world.posts.length - 1];
        check("ima de extremidade fecha o circuito exatamente",
            world.posts.length === 3 && last.body.x2 === 200 && last.body.y2 === 200,
            JSON.stringify(last?.body));
    }

    {
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200);
        world.dispatch("pointerdown", { button: 2, clientX: 300, clientY: 300 });
        check("botao direito cancela o desenho", world.state().start === null);
    }

    {
        const world = buildWorld({ sceneId: null });
        await world.settle();
        await clickAt(world, 200, 200);
        check("sem cena ativa: nem ancora o primeiro ponto e avisa no console",
            world.state().start === null && world.warnings.some((w) => w.includes("sem cena ativa")),
            JSON.stringify(world.warnings));
        await clickAt(world, 400, 200);
        check("sem cena ativa: nao cria parede", world.posts.length === 0, JSON.stringify(world.posts));
    }

    {
        // cena ativada depois do carregamento da pagina (ativacao via modal/realtime)
        const world = buildWorld({ sceneId: null });
        await world.settle();
        world.setScene("scene-9");
        world.state();
        await world.settle();
        check("cena ativada depois carrega as paredes",
            world.gets.some((url) => url.includes("/game/walls/scene-9")), JSON.stringify(world.gets));
        await clickAt(world, 200, 200);
        await clickAt(world, 400, 200);
        check("cena ativada depois volta a criar paredes", world.posts.length === 1, JSON.stringify(world.posts));
    }

    {
        // trocar de cena nao pode manter paredes nem desenho da cena anterior
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 200, 200);
        await clickAt(world, 400, 200);
        check("parede criada na cena original", world.state().walls.length === 1);
        await clickAt(world, 400, 400);
        world.setScene("scene-2");
        const state = world.state();
        await world.settle();
        check("troca de cena limpa paredes e cancela o desenho",
            state.walls.length === 0 && state.start === null,
            JSON.stringify({ walls: state.walls.length, start: state.start }));
        check("troca de cena busca as paredes da nova cena",
            world.gets.some((url) => url.includes("/game/walls/scene-2")), JSON.stringify(world.gets));
    }

    {
        const world = buildWorld({ activeTool: "select" });
        await world.settle();
        await clickAt(world, 200, 200);
        check("ferramenta select nao ancora parede", world.state().start === null && world.posts.length === 0);
    }

    {
        // select arrasta o vertice compartilhado por duas paredes encadeadas
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 100, 100);
        await clickAt(world, 300, 100);
        await clickAt(world, 300, 300, { altKey: true });
        check("duas paredes soldadas no vertice", world.state().walls.length === 2);

        world.setTool("select");
        world.dispatch("pointerdown", { clientX: 300, clientY: 100 });
        world.dispatch("pointermove", { clientX: 340, clientY: 160 });
        const preview = world.state().walls;
        check("arrasto do no move as duas pontas soldadas no preview",
            preview[0].x2 === 340 && preview[0].y2 === 160
            && preview[1].x1 === 340 && preview[1].y1 === 160,
            JSON.stringify(preview));
        check("arrasto do no nao mexe nas outras pontas",
            preview[0].x1 === 100 && preview[0].y1 === 100
            && preview[1].x2 === 300 && preview[1].y2 === 300,
            JSON.stringify(preview));

        world.dispatch("pointerup", { clientX: 340, clientY: 160 });
        await world.settle();
        const move = world.posts[world.posts.length - 1];
        check("soltar persiste via move-node",
            move.url.endsWith("/game/walls/move-node")
            && move.body.from_x === 300 && move.body.from_y === 100
            && move.body.to_x === 340 && move.body.to_y === 160,
            JSON.stringify(move));
        const walls = world.state().walls;
        check("estado final vem do servidor",
            walls[0].x2 === 340 && walls[0].y2 === 160 && walls[1].x1 === 340 && walls[1].y1 === 160,
            JSON.stringify(walls));
    }

    {
        // porta selecionada percorre fechada -> aberta -> trancada -> fechada
        const world = buildWorld({ activeTool: "door" });
        await world.settle();
        await clickAt(world, 100, 100);
        await clickAt(world, 300, 100, { altKey: true });
        check("porta nasce fechada", world.state().walls[0].door_state === "closed");

        world.setTool("select");
        await clickAt(world, 200, 100);
        check("primeiro clique so seleciona a porta",
            world.state().selected === "w1" && world.state().walls[0].door_state === "closed");

        const states = [];
        for (let i = 0; i < 4; i++) {
            await clickAt(world, 200, 100);
            states.push(world.state().walls[0].door_state);
        }
        check("clique repetido cicla os tres estados e volta ao inicio",
            states.join(">") === "open>locked>closed>open", states.join(">"));
        const last = world.posts[world.posts.length - 1];
        check("cada passo persiste o estado explicito",
            last.url.endsWith("/game/walls/door-state") && last.body.door_state === "open",
            JSON.stringify(last));
    }

    {
        // clicar no corpo da parede continua selecionando, nao arrasta no
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 100, 100);
        await clickAt(world, 300, 100, { altKey: true });
        world.setTool("select");
        await clickAt(world, 200, 100);
        check("select no corpo da parede seleciona o segmento",
            world.state().selected === "w1" && world.posts.length === 1,
            JSON.stringify({ selected: world.state().selected, posts: world.posts.length }));
    }

    {
        const world = buildWorld({ activeTool: "select", walls: [
            { x1: 100, y1: 100, x2: 300, y2: 100 },
            { x1: 100, y1: 200, x2: 300, y2: 200 },
        ] });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 50, clientY: 50 });
        world.dispatch("pointermove", { clientX: 350, clientY: 250 });
        world.dispatch("pointerup", { clientX: 350, clientY: 250 });
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        world.dispatch("pointermove", { clientX: 225, clientY: 130 });
        world.dispatch("pointerup", { clientX: 225, clientY: 130 });
        await world.settle();
        const walls = world.state().walls;
        check("arrasto pelo mouse move toda a selecao de paredes",
            walls[0].x1 === 125 && walls[0].y1 === 130
            && walls[1].x1 === 125 && walls[1].y1 === 230,
            JSON.stringify(walls));
        const move = world.posts[world.posts.length - 1];
        check("arrasto em lote persiste em uma operacao",
            move?.url.endsWith("/game/walls/move-many")
            && move.body.wall_ids.length === 2 && move.body.dx === 25 && move.body.dy === 30,
            JSON.stringify(move));
        world.dispatch("keydown", { key: "ArrowRight" });
        await world.settle();
        const afterKey = world.state().walls;
        check("seta move toda a selecao de paredes",
            afterKey[0].x1 === 160 && afterKey[1].x1 === 160,
            JSON.stringify(afterKey));
    }

    {
        // no arrastado nao pode se auto-imantar de volta para a origem
        const world = buildWorld();
        await world.settle();
        await clickAt(world, 100, 100);
        await clickAt(world, 300, 100, { altKey: true });
        world.setTool("select");
        world.dispatch("pointerdown", { clientX: 300, clientY: 100 });
        world.dispatch("pointermove", { clientX: 305, clientY: 104 });
        const preview = world.state().walls;
        check("movimento curto nao gruda de volta na origem",
            preview[0].x2 === 305 && preview[0].y2 === 104, JSON.stringify(preview));
        world.dispatch("pointerup", { clientX: 305, clientY: 104 });
        await world.settle();
    }

    {
        const world = buildWorld({ isGm: false });
        await world.settle();
        await clickAt(world, 200, 200);
        await clickAt(world, 400, 200);
        check("jogador nao desenha parede", world.posts.length === 0 && world.state().start === null);
    }

    // --- porta operada em jogo ---------------------------------------------

    const DOOR_SEED = [{ kind: "door", x1: 100, y1: 100, x2: 300, y2: 100 }];

    async function worldWithDoor(options = {}) {
        const world = buildWorld({ activeTool: "select", walls: DOOR_SEED, ...options });
        await world.settle();
        world.setLayer("game");
        return world;
    }

    {
        const world = await worldWithDoor();
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        await world.settle();
        check("clique em jogo abre a porta destrancada", world.state().walls[0].door_state === "open");
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        await world.settle();
        check("clique de novo fecha", world.state().walls[0].door_state === "closed");
        const last = world.posts[world.posts.length - 1];
        check("operacao em jogo usa door-state explicito",
            last.url.endsWith("/game/walls/door-state") && last.body.door_state === "closed", JSON.stringify(last));
    }

    {
        const world = await worldWithDoor({ isGm: false, userId: "player-1" });
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        await world.settle();
        check("jogador tambem abre porta destrancada", world.state().walls[0].door_state === "open");
    }

    {
        // botao direito do GM so tranca e destranca; abrir e fechar e do esquerdo
        const world = await worldWithDoor();
        const states = [];
        for (let i = 0; i < 4; i++) {
            world.dispatch("pointerdown", { button: 2, clientX: 200, clientY: 100 });
            await world.settle();
            states.push(world.state().walls[0].door_state);
        }
        check("botao direito alterna so a tranca",
            states.join(">") === "locked>closed>locked>closed", states.join(">"));
    }

    {
        // trancar uma porta aberta tambem a fecha: nao existe trancada e aberta
        const world = await worldWithDoor();
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        await world.settle();
        check("porta aberta pelo esquerdo", world.state().walls[0].door_state === "open");
        world.dispatch("pointerdown", { button: 2, clientX: 200, clientY: 100 });
        await world.settle();
        check("trancar fecha a porta junto", world.state().walls[0].door_state === "locked");
    }

    {
        // esquerdo continua sendo so abre/fecha, e a tranca o barra
        const world = await worldWithDoor({
            walls: [{ kind: "door", door_state: "locked", x1: 100, y1: 100, x2: 300, y2: 100 }],
        });
        const before = world.posts.length;
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        await world.settle();
        check("porta trancada nao cede ao clique esquerdo",
            world.state().walls[0].door_state === "locked" && world.posts.length === before);

        world.dispatch("pointerdown", { button: 2, clientX: 200, clientY: 100 });
        await world.settle();
        check("GM destranca com o botao direito", world.state().walls[0].door_state === "closed");
        world.dispatch("pointerdown", { clientX: 200, clientY: 100 });
        await world.settle();
        check("destrancada, o esquerdo volta a abrir", world.state().walls[0].door_state === "open");
    }

    {
        const world = await worldWithDoor({
            isGm: false, userId: "player-1",
            walls: [{ kind: "door", door_state: "locked", x1: 100, y1: 100, x2: 300, y2: 100 }],
        });
        const event = world.dispatch("pointerdown", { button: 2, clientX: 200, clientY: 100 });
        await world.settle();
        check("jogador nao cicla com o botao direito",
            world.state().walls[0].door_state === "locked" && world.posts.length === 0,
            JSON.stringify(world.posts));
        // e o evento segue livre: o menu de contexto do jogador nao pode ser engolido
        check("botao direito do jogador nao e consumido",
            !event.defaultPrevented && !event.propagationStopped);
    }

    {
        const world = await worldWithDoor();
        const before = world.posts.length;
        world.dispatch("pointerdown", { clientX: 900, clientY: 900 });
        await world.settle();
        check("clique longe da porta nao dispara nada", world.posts.length === before);
    }

    {
        // porta de (100,100) a (300,100): a extremidade tambem opera, nao so o meio
        const world = await worldWithDoor();
        world.dispatch("pointerdown", { clientX: 110, clientY: 100 });
        await world.settle();
        check("clique na ponta da porta opera", world.state().walls[0].door_state === "open");

        world.dispatch("pointerdown", { button: 2, clientX: 290, clientY: 104 });
        await world.settle();
        check("botao direito na outra ponta tranca", world.state().walls[0].door_state === "locked");
    }

    {
        // fora da tolerancia continua sem pegar, para nao roubar cliques do tabuleiro
        const world = await worldWithDoor();
        const before = world.posts.length;
        world.dispatch("pointerdown", { clientX: 200, clientY: 140 });
        await world.settle();
        check("longe da linha da porta nao opera", world.posts.length === before);
    }

    // --- focos de luz -------------------------------------------------------

    {
        const world = buildWorld({ activeTool: "light", activeLayer: "lighting" });
        await world.settle();
        await clickAt(world, 300, 300);
        const created = world.posts[world.posts.length - 1];
        check("ferramenta de luz cria foco com a animacao do sub-tool",
            created.url.endsWith("/game/lights") && created.body.animation === "torch"
            && created.body.x === 300 && created.body.y === 300,
            JSON.stringify(created));
        check("foco entra no estado renderizado", world.state().lights.length === 1);

        world.setSubTool("pulse");
        await clickAt(world, 600, 300);
        check("sub-tool troca a animacao do proximo foco",
            world.posts[world.posts.length - 1].body.animation === "pulse");
    }

    {
        const world = buildWorld({ activeTool: "light", activeLayer: "lighting" });
        await world.settle();
        await clickAt(world, 300, 300);
        world.setTool("select");
        world.dispatch("pointerdown", { clientX: 300, clientY: 300 });
        world.dispatch("pointermove", { clientX: 420, clientY: 360 });
        const dragged = world.state().lights[0];
        check("arrastar o foco atualiza o preview", dragged.x === 420 && dragged.y === 360);
        world.dispatch("pointerup", { clientX: 420, clientY: 360 });
        await world.settle();
        const moved = world.posts[world.posts.length - 1];
        check("soltar persiste a posicao do foco",
            moved.url.endsWith("/game/lights/update") && moved.body.x === 420 && moved.body.y === 360,
            JSON.stringify(moved));
    }

    {
        const world = buildWorld({ activeTool: "light", activeLayer: "lighting" });
        await world.settle();
        await clickAt(world, 300, 300);
        world.dispatch("keydown", { key: "Delete", target: { closest: () => null } });
        await world.settle();
        const deleted = world.posts.find((p) => p.url.endsWith("/game/lights/delete-many"));
        // Um pedido, mesmo para um item so: apagar em laco enchia a mesa de avisos
        // de tempo real e a cena sumia aos pedacos na tela dos outros.
        check("Delete remove o foco selecionado", deleted?.body.light_ids?.length === 1,
            JSON.stringify(world.posts));
        check("foco some do estado", world.state().lights.length === 0);
    }

    {
        const world = buildWorld({ activeTool: "light", activeLayer: "lighting", darkness: 0.9 });
        await world.settle();
        await clickAt(world, 300, 300);
        const light = world.state().lights[0];
        check("foco com raio produz poligono fechado", light.polygon.length >= 3);
        // O raio vem do proprio foco: cada emissao nasce com o seu, entao cravar
        // um numero aqui amarraria o teste ao preset da tocha.
        const reach = world.state().lights[0].dim;
        check("poligono do foco respeita o raio escuro",
            light.polygon.every((p) => Math.hypot(p.x - 300, p.y - 300) <= reach + 1),
            JSON.stringify(light.polygon.slice(0, 3)));
        // Amostras radiais fora da faixa de atan2 fazem o contorno enrolar duas vezes
        // e o foco se desenha como varias luzes empilhadas.
        check("angulos do foco ficam todos na faixa de atan2",
            light.polygon.every((p) => p.angle >= -Math.PI - 1e-6 && p.angle <= Math.PI + 1e-6),
            JSON.stringify(light.polygon.map((p) => p.angle).filter((a) => a > Math.PI).slice(0, 4)));
        // Uma volta so: a diferenca angular acumulada nao pode passar de 2PI.
        const span = light.polygon[light.polygon.length - 1].angle - light.polygon[0].angle;
        check("contorno do foco da exatamente uma volta",
            span <= Math.PI * 2 + 1e-6, String(span));
    }

    {
        // parede atravessada na frente do foco tem de cortar o alcance dele
        const world = buildWorld({
            activeTool: "light", activeLayer: "lighting", darkness: 0.9,
            walls: [{ x1: 400, y1: 0, x2: 400, y2: 941 }],
        });
        await world.settle();
        await clickAt(world, 300, 300);
        const light = world.state().lights[0];
        // parede atravessa a cena de ponta a ponta: nao ha como contornar as pontas
        const beyond = light.polygon.filter((p) => p.x > 401);
        check("parede corta o foco", beyond.length === 0, JSON.stringify(beyond.slice(0, 3)));
        // e o lado livre continua alcancando o raio cheio
        const reachesLeft = light.polygon.some((p) => p.x < 300 - 4 * 70 + 5);
        check("o lado sem parede mantem o alcance", reachesLeft);
    }

    {
        // porta aberta deixa a luz passar; fechada e trancada barram
        const seed = (door_state) => buildWorld({
            activeTool: "light", activeLayer: "lighting", darkness: 0.9,
            walls: [{ kind: "door", door_state, x1: 400, y1: 0, x2: 400, y2: 941 }],
        });
        for (const [state, blocks] of [["open", false], ["closed", true], ["locked", true]]) {
            const world = seed(state);
            await world.settle();
            await clickAt(world, 300, 300);
            const beyond = world.state().lights[0].polygon.filter((p) => p.x > 401);
            check(`porta ${state} ${blocks ? "barra" : "deixa passar"} a luz`,
                blocks ? beyond.length === 0 : beyond.length > 0,
                `${state}: ${beyond.length} pontos alem`);
        }
    }

    // --- escuridao e visao por jogador --------------------------------------

    const playerToken = (id, userIds, extra = {}) => ({
        token_id: id, grid_x: 2, grid_y: 2, width_cells: 1, height_cells: 1,
        controlled_by_user_ids: userIds, vision_enabled: true, vision_range: 0, ...extra,
    });

    {
        const world = buildWorld({
            isGm: false, userId: "player-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"]), playerToken("t2", ["player-2"], { grid_x: 10 })],
        });
        await world.settle();
        const state = world.state();
        check("jogador enxerga a partir do proprio token", state.visionPolygons.length === 1);
        check("escuridao chega cheia ao jogador", state.darkness === 0.8);
    }

    {
        const world = buildWorld({
            isGm: true, userId: "gm-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"])],
        });
        await world.settle();
        const state = world.state();
        check("GM sem selecao nao tem a visao recortada", state.visionPolygons.length === 0);
        check("GM ve a escuridao so como previa atenuada",
            state.darkness > 0 && state.darkness < 0.8, String(state.darkness));

        // selecionar um token e como o GM confere o que aquele token enxerga
        world.selectToken("t1");
        const seeing = world.state();
        check("GM selecionando token assume a visao dele", seeing.visionPolygons.length === 1);
        check("e recebe a escuridao cheia para conferir de verdade", seeing.darkness === 0.8,
            String(seeing.darkness));

        world.selectToken("");
        check("desselecionar devolve a visao livre do GM",
            world.state().visionPolygons.length === 0);
    }

    {
        // token sem visao nao serve de janela: o GM continua enxergando tudo
        const world = buildWorld({
            isGm: true, userId: "gm-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"], { vision_enabled: false })],
        });
        await world.settle();
        world.selectToken("t1");
        const state = world.state();
        check("token cego nao recorta a visao do GM", state.visionPolygons.length === 0);
        check("e a escuridao volta a ser previa", state.darkness < 0.8, String(state.darkness));
    }

    {
        // o alcance do token selecionado limita o que o GM ve
        const world = buildWorld({
            isGm: true, userId: "gm-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"], { vision_range: 3 })],
        });
        await world.settle();
        world.selectToken("t1");
        const polygon = world.state().visionPolygons[0];
        const origin = { x: 2.5 * 70, y: 2.5 * 70 };
        check("GM ve limitado pelo alcance do token",
            polygon.every((p) => Math.hypot(p.x - origin.x, p.y - origin.y) <= 3 * 70 + 1),
            JSON.stringify(polygon.slice(0, 2)));
    }

    {
        const world = buildWorld({
            isGm: true, playerView: true, userId: "gm-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"])],
        });
        await world.settle();
        const state = world.state();
        check("GM em visao de jogador recebe a escuridao cheia", state.darkness === 0.8);
        check("GM em visao de jogador enxerga pelos tokens de jogador", state.visionPolygons.length === 1);
    }

    {
        const world = buildWorld({
            isGm: false, userId: "player-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"], { vision_range: 3 })],
        });
        await world.settle();
        const polygon = world.state().visionPolygons[0];
        const origin = { x: 2.5 * 70, y: 2.5 * 70 };
        check("alcance de visao limita o poligono",
            polygon.every((p) => Math.hypot(p.x - origin.x, p.y - origin.y) <= 3 * 70 + 1),
            JSON.stringify(polygon.slice(0, 3)));
    }

    {
        const world = buildWorld({
            isGm: false, userId: "player-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"], { vision_enabled: false })],
        });
        await world.settle();
        check("token sem visao nao enxerga nada", world.state().visionPolygons.length === 0);
    }

    {
        // O GM nao tem a visao recortada e a cena pode estar com escuridao 0: sem a
        // previa, mexer no alcance nao muda nada na tela.
        const world = buildWorld({
            isGm: true, userId: "gm-1", darkness: 0,
            tokens: [playerToken("t1", ["player-1"], { vision_range: 4 })],
        });
        await world.settle();
        check("sem previa nao ha nada desenhado", world.state().visionPreview === null);

        world.previewVision("t1");
        const preview = world.state().visionPreview;
        check("previa existe mesmo com escuridao 0 e sendo GM", preview !== null);
        check("previa carrega o alcance do token", preview && preview.radius === 4 * 70,
            JSON.stringify(preview && preview.radius));
        check("previa tem poligono desenhavel", preview && preview.polygon.length >= 3);

        world.previewVision("");
        check("fechar o painel apaga a previa", world.state().visionPreview === null);
    }

    {
        // token com visao desligada ainda precisa de previa: e como se religa
        const world = buildWorld({
            isGm: true, userId: "gm-1", darkness: 0.8,
            tokens: [playerToken("t1", ["player-1"], { vision_enabled: false, vision_range: 2 })],
        });
        await world.settle();
        world.previewVision("t1");
        check("previa aparece mesmo com a visao desligada", world.state().visionPreview !== null);
    }

    {
        // selecionar o token alheio nao pode emprestar a visao dele
        const world = buildWorld({
            isGm: false, userId: "player-1", darkness: 0.8,
            tokens: [playerToken("t2", ["player-2"], { grid_x: 12, grid_y: 12 })],
        });
        await world.settle();
        check("jogador sem token proprio nao enxerga", world.state().visionPolygons.length === 0);

        world.selectToken("t2");
        check("selecionar token de outro jogador nao da visao", world.state().visionPolygons.length === 0);
    }

    {
        // com varios tokens proprios, selecionar um foca a visao nele
        const world = buildWorld({
            isGm: false, userId: "player-1", darkness: 0.8,
            tokens: [
                playerToken("t1", ["player-1"]),
                playerToken("t3", ["player-1"], { grid_x: 9, grid_y: 9 }),
            ],
        });
        await world.settle();
        check("sem selecao o jogador soma os proprios tokens", world.state().visionPolygons.length === 2);
        world.selectToken("t3");
        check("com selecao propria a visao foca nela", world.state().visionPolygons.length === 1);
        world.selectToken("t2");
        check("selecao inexistente cai de volta para todos os proprios",
            world.state().visionPolygons.length === 2);
    }

    {
        // O marcador e o unico indicador de estado e o alvo do clique: escondido no
        // escuro, a porta ficava inoperavel. Longe da visao do jogador, continua la.
        const world = buildWorld({
            isGm: false, userId: "player-1", darkness: 0.9,
            tokens: [playerToken("t1", ["player-1"])],
            walls: [{ kind: "door", x1: 900, y1: 900, x2: 900, y2: 700 }],
        });
        await world.settle();
        world.setLayer("game");
        check("porta distante segue visivel no escuro", world.state().doors.length === 1,
            JSON.stringify(world.state().doors.length));
    }

    // --- indice de paredes por chunk ----------------------------------------

    {
        // Um alcance finito so pode pagar pelas paredes perto dele. O corte tem de
        // ser conservador: a forma resultante nao muda, so o custo.
        const grid = [];
        for (let i = 0; i < 600; i++) {
            const x = 40 + (i % 20) * 72, y = 40 + Math.floor(i / 20) * 60;
            grid.push({ x1: x, y1: y, x2: x + 60, y2: y });
        }
        const near = { token_id: "t1", grid_x: 3, grid_y: 3, width_cells: 1, height_cells: 1,
            controlled_by_user_ids: ["p1"], vision_enabled: true, vision_range: 3 };

        const world = buildWorld({ isGm: false, userId: "p1", darkness: 0.9, tokens: [near], walls: grid });
        await world.settle();
        const polygon = world.state().visionPolygons[0];
        const origin = { x: 3.5 * 70, y: 3.5 * 70 };
        check("visao com alcance fecha dentro do raio",
            polygon.length >= 3 && polygon.every((p) => Math.hypot(p.x - origin.x, p.y - origin.y) <= 3 * 70 + 1));

        // o corte nao pode custar mais que o mapa inteiro: dobrar as paredes
        // distantes tem de deixar o tempo praticamente igual
        const timed = async (walls) => {
            const w = buildWorld({ isGm: false, userId: "p1", darkness: 0.9, tokens: [near], walls });
            await w.settle();
            const N = 10, t0 = process.hrtime.bigint();
            for (let i = 0; i < N; i++) { w.moveToken("t1", 3 + (i % 2), 3); w.state(); }
            return Number(process.hrtime.bigint() - t0) / 1e6 / N;
        };
        const small = await timed(grid.slice(0, 150));
        const large = await timed(grid);
        check("custo nao acompanha o tamanho do mapa",
            large < small * 3, `150 paredes: ${small.toFixed(1)}ms, 600: ${large.toFixed(1)}ms`);
    }

    {
        // parede vizinha nao pode ser descartada pelo corte
        const world = buildWorld({
            isGm: false, userId: "p1", darkness: 0.9,
            tokens: [{ token_id: "t1", grid_x: 2, grid_y: 2, width_cells: 1, height_cells: 1,
                controlled_by_user_ids: ["p1"], vision_enabled: true, vision_range: 4 }],
            walls: [{ x1: 300, y1: 0, x2: 300, y2: 941 }],
        });
        await world.settle();
        const polygon = world.state().visionPolygons[0];
        check("parede dentro do alcance continua bloqueando",
            polygon.every((p) => p.x <= 301), JSON.stringify(polygon.filter((p) => p.x > 301).slice(0, 3)));
    }

    // --- sondagem progressiva da visao sem alcance ---------------------------

    const room = (x, y, w, h) => [
        { x1: x, y1: y, x2: x + w, y2: y },
        { x1: x + w, y1: y, x2: x + w, y2: y + h },
        { x1: x + w, y1: y + h, x2: x, y2: y + h },
        { x1: x, y1: y + h, x2: x, y2: y },
    ];
    const freeToken = (extra = {}) => ({
        token_id: "t1", grid_x: 4, grid_y: 4, width_cells: 1, height_cells: 1,
        controlled_by_user_ids: ["p1"], vision_enabled: true, vision_range: 0, ...extra,
    });

    {
        // Sala fechada: a sondagem fecha cedo e nao pode vazar para fora dela.
        const walls = [...room(200, 200, 280, 280), ...room(900, 600, 300, 200)];
        const world = buildWorld({ isGm: false, userId: "p1", darkness: 0.9,
            tokens: [freeToken()], walls });
        await world.settle();
        const polygon = world.state().visionPolygons[0];
        check("visao sem alcance fecha na sala",
            polygon.every((p) => p.x >= 199 && p.x <= 481 && p.y >= 199 && p.y <= 481),
            JSON.stringify(polygon.filter((p) => p.x > 481 || p.y > 481).slice(0, 3)));
    }

    {
        // Risco real da sondagem: parar cedo demais e ignorar parede distante. O token
        // fica em campo aberto, com a unica parede alem do primeiro raio sondado.
        const world = buildWorld({ isGm: false, userId: "p1", darkness: 0.9,
            tokens: [freeToken({ grid_x: 1, grid_y: 6 })],
            walls: [{ x1: 1200, y1: 0, x2: 1200, y2: 941 }] });
        await world.settle();
        const polygon = world.state().visionPolygons[0];
        check("parede alem do primeiro raio sondado ainda bloqueia",
            polygon.every((p) => p.x <= 1201),
            JSON.stringify(polygon.filter((p) => p.x > 1201).slice(0, 3)));
        check("e o resto da visao alcanca a borda da cena",
            polygon.some((p) => p.y <= 1 || p.y >= 940));
    }

    {
        // Campo totalmente aberto: sem parede, a visao vai ate os limites da cena.
        const world = buildWorld({ isGm: false, userId: "p1", darkness: 0.9,
            tokens: [freeToken()], walls: [] });
        await world.settle();
        const polygon = world.state().visionPolygons[0];
        const corners = [[0, 0], [1672, 0], [0, 941], [1672, 941]];
        check("campo aberto enxerga os quatro cantos da cena",
            corners.every(([cx, cy]) => polygon.some((p) => Math.hypot(p.x - cx, p.y - cy) < 2)),
            JSON.stringify(polygon.length));
    }

    {
        // O palpite aprendido nao pode contaminar o resultado quando o token muda de
        // contexto: sair da sala para o aberto tem de expandir de volta.
        const walls = [...room(200, 200, 280, 280)];
        const world = buildWorld({ isGm: false, userId: "p1", darkness: 0.9,
            tokens: [freeToken()], walls });
        await world.settle();
        check("dentro da sala, fecha na sala",
            world.state().visionPolygons[0].every((p) => p.x <= 481));
        world.moveToken("t1", 16, 10);
        const outside = world.state().visionPolygons[0];
        check("ao sair da sala, a visao volta a se expandir",
            outside.some((p) => p.x > 1000 || p.y > 800), JSON.stringify(outside.length));
    }

    // --- visao acompanhando o movimento --------------------------------------

    {
        // O store so recebe a posicao ao soltar. Sem ler o arrasto em curso, a visao
        // ficava parada na celula antiga e so "acendia" no fim do movimento.
        //
        // Celulas longe da borda de proposito: perto dela o circulo e cortado pela
        // cena e o centro da caixa deixa de coincidir com a origem.
        const world = buildWorld({
            isGm: false, userId: "p1", darkness: 0.9,
            tokens: [{ token_id: "t1", grid_x: 6, grid_y: 6, width_cells: 1, height_cells: 1,
                controlled_by_user_ids: ["p1"], vision_enabled: true, vision_range: 3 }],
        });
        await world.settle();
        const centre = (polygon) => {
            const xs = polygon.map((p) => p.x), ys = polygon.map((p) => p.y);
            return { x: (Math.min(...xs) + Math.max(...xs)) / 2, y: (Math.min(...ys) + Math.max(...ys)) / 2 };
        };

        const parada = centre(world.state().visionPolygons[0]);
        check("visao parte da celula do token",
            Math.abs(parada.x - 6.5 * 70) < 2, JSON.stringify(parada));

        world.dragToken("t1", 12, 6);
        const arrastando = centre(world.state().visionPolygons[0]);
        check("visao acompanha durante o arrasto, sem esperar soltar",
            Math.abs(arrastando.x - 12.5 * 70) < 2, JSON.stringify(arrastando));

        world.dropToken();
        const solta = centre(world.state().visionPolygons[0]);
        check("ao soltar volta a seguir o store", Math.abs(solta.x - 6.5 * 70) < 2,
            JSON.stringify(solta));
    }

    {
        // arrasto de outro canvas nao pode mexer nesta visao
        const world = buildWorld({
            isGm: false, userId: "p1", darkness: 0.9,
            tokens: [{ token_id: "t1", grid_x: 2, grid_y: 2, width_cells: 1, height_cells: 1,
                controlled_by_user_ids: ["p1"], vision_enabled: true, vision_range: 3 }],
        });
        await world.settle();
        const before = world.state().visionPolygons[0].length;
        world.dragToken("outro-token", 12, 8);
        check("arrastar outro token nao move a visao deste",
            world.state().visionPolygons[0].length === before);
    }

    // --- colisao de movimento ------------------------------------------------

    {
        // parede vertical em x=300, de y=0 a y=400
        const world = buildWorld({
            walls: [{ x1: 300, y1: 0, x2: 300, y2: 400 }],
        });
        await world.settle();
        const blocks = (ax, ay, bx, by) =>
            world.blocksMovement({ x: ax, y: ay }, { x: bx, y: by });

        check("passo atravessando a parede e barrado", blocks(250, 200, 350, 200));
        check("passo do mesmo lado passa", !blocks(100, 200, 250, 200));
        check("passo do outro lado passa", !blocks(350, 200, 500, 200));
        check("passo paralelo rente a parede passa", !blocks(300, 100, 300, 300));
        // a parede acaba em y=400: contornar por baixo e legitimo
        check("contornar a ponta da parede passa", !blocks(250, 500, 350, 500));
        check("passo na diagonal atravessando e barrado", blocks(250, 150, 350, 250));
    }

    {
        // porta: so deixa passar aberta
        for (const [state, blocked] of [["open", false], ["closed", true], ["locked", true]]) {
            const world = buildWorld({
                walls: [{ kind: "door", door_state: state, x1: 300, y1: 0, x2: 300, y2: 400 }],
            });
            await world.settle();
            check(`porta ${state} ${blocked ? "barra" : "deixa"} o movimento`,
                world.blocksMovement({ x: 250, y: 200 }, { x: 350, y: 200 }) === blocked);
        }
    }

    {
        // sem paredes nada barra, e sem cena tambem nao
        const world = buildWorld({ walls: [] });
        await world.settle();
        check("mapa sem paredes nao barra nada",
            !world.blocksMovement({ x: 0, y: 0 }, { x: 1600, y: 900 }));
    }

    if (failures.length) {
        console.error(`\n${failures.length} verificacao(oes) falharam: ${failures.join(", ")}`);
        process.exit(1);
    }
    
    // --- selecao multipla ----------------------------------------------------
    //
    // Montar cena era clicar item por item para apagar. A caixa e o Shift existem
    // para isso, e o que eles precisam garantir e comportamento, nao presenca de
    // codigo: quem entra na selecao, quem fica de fora, e quantas requisicoes
    // saem no fim.

    const paredes = [
        { id: "W1", kind: "wall", x1: 100, y1: 100, x2: 200, y2: 100, door_state: "closed" },
        { id: "W2", kind: "wall", x1: 100, y1: 200, x2: 200, y2: 200, door_state: "closed" },
        { id: "W3", kind: "wall", x1: 700, y1: 700, x2: 800, y2: 700, door_state: "closed" },
    ];

    {
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: paredes });
        await world.settle();

        // Caixa cobrindo as duas primeiras, longe da terceira.
        world.dispatch("pointerdown", { clientX: 50, clientY: 50 });
        world.dispatch("pointermove", { clientX: 260, clientY: 260 });
        const durante = world.state();
        check("a caixa aparece enquanto se arrasta", Boolean(durante.marquee));
        world.dispatch("pointerup", { clientX: 260, clientY: 260 });

        const escolhidas = world.state().picked.wall;
        check("a caixa pega tudo o que cobriu", escolhidas.has("W1") && escolhidas.has("W2"),
            [...escolhidas].join(","));
        check("e nao o que ficou de fora", !escolhidas.has("W3"));
        check("e some ao soltar", !world.state().marquee);
    }

    {
        // Meia parede dentro da caixa nao entra: seria "apaguei sem querer o que
        // estava so encostando".
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: paredes });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 50, clientY: 50 });
        world.dispatch("pointermove", { clientX: 150, clientY: 150 });
        world.dispatch("pointerup", { clientX: 150, clientY: 150 });
        check("parede so encostando fica de fora", world.state().picked.wall.size === 0);
    }

    {
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: paredes });
        await world.settle();
        // Clique simples escolhe um; a caixa e o segundo modo, para selecionar varios.
        world.dispatch("pointerdown", { clientX: 150, clientY: 100 });
        world.dispatch("pointerup", { clientX: 150, clientY: 100 });
        check("clique simples escolhe uma", world.state().picked.wall.size === 1);
        world.dispatch("pointerdown", { clientX: 150, clientY: 200 });
        world.dispatch("pointerup", { clientX: 150, clientY: 200 });
        check("outro clique comum troca a selecao", world.state().picked.wall.size === 1
            && world.state().picked.wall.has("W2"));
    }

    {
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: paredes });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 50, clientY: 50 });
        world.dispatch("pointermove", { clientX: 260, clientY: 260 });
        world.dispatch("pointerup", { clientX: 260, clientY: 260 });
        world.dispatch("keydown", { key: "Delete", target: { closest: () => null } });
        await world.settle();

        const lotes = world.posts.filter((p) => p.url.endsWith("/game/walls/delete-many"));
        // UMA requisicao para a selecao inteira. Em laco, trinta paredes eram
        // trinta pedidos e trinta avisos, e a cena sumia aos pedacos para os outros.
        check("apagar a selecao e um pedido so", lotes.length === 1, `${lotes.length}`);
        check("com os dois ids dentro", (lotes[0]?.body.wall_ids || []).length === 2,
            JSON.stringify(lotes[0]?.body));
        check("e a cena fica so com a de fora", world.state().walls.length === 1);
    }

    {
        // Clique parado no vazio nao e caixa: sem o piso, cada clique varreria uma
        // caixa de zero por zero.
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: paredes });
        await world.settle();
        world.dispatch("pointerdown", { clientX: 150, clientY: 100 });
        world.dispatch("pointerup", { clientX: 150, clientY: 100 });
        const antes = world.state().picked.wall.size;
        world.dispatch("pointerdown", { clientX: 600, clientY: 600 });
        world.dispatch("pointerup", { clientX: 600, clientY: 601 });
        check("clique no vazio limpa a selecao sem varrer nada",
            antes === 1 && world.state().picked.wall.size === 0);
    }

    // --- duplo clique parte a parede ----------------------------------------
    {
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: [paredes[0]] });
        await world.settle();
        world.dispatch("dblclick", { clientX: 150, clientY: 100 });
        await world.settle();
        const pedido = world.posts.find((p) => p.url.endsWith("/game/walls/split"));
        check("duplo clique na parede pede a divisao", Boolean(pedido), JSON.stringify(world.posts));
        check("no ponto em que se clicou", pedido?.body.x === 150 && pedido?.body.y === 100);
        check("e a cena passa a ter duas", world.state().walls.length === 2);
    }

    {
        // Em cima de um no ja existente nao divide: nasceria um no colado no outro.
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: [paredes[0]] });
        await world.settle();
        world.dispatch("dblclick", { clientX: 100, clientY: 100 });
        await world.settle();
        check("duplo clique no no nao divide",
            !world.posts.some((p) => p.url.endsWith("/game/walls/split")));
    }

    {
        const porta = {
            id: "D1", kind: "door", x1: 100, y1: 100, x2: 200, y2: 100,
            door_state: "closed",
        };
        const world = buildWorld({ activeTool: "select", activeLayer: "walls", walls: [porta] });
        await world.settle();
        world.dispatch("dblclick", { clientX: 150, clientY: 100 });
        await world.settle();
        check("duplo clique na porta nao insere no",
            !world.posts.some((p) => p.url.endsWith("/game/walls/split")));
        check("e a porta permanece um unico segmento", world.state().walls.length === 1);
    }

console.log("\ntodas as verificacoes de interacao passaram");
})();
