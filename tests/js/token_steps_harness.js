/*
 * Cobertura de comportamento do movimento por setas (static/js/map/input/map-token-steps.js).
 *
 * Carrega o arquivo real sobre dependências mínimas, para exercitar o passo de
 * verdade: colisão, gravação adiada e histórico. Sai != 0 na primeira falha.
 */
const fs = require("fs");
const path = require("path");

const SCRIPT = path.resolve(__dirname, "../../static/js/map/input/map-token-steps.js");

function buildWorld({
    token = { token_id: "t1", grid_x: 5, grid_y: 5, width_cells: 1, height_cells: 1 },
    selected = ["t1"],
    controllable = true,
    blocked = () => false,
    tile = 70,
} = {}) {
    const canvas = { dataset: { roomId: "campaign-1" } };
    const store = new Map([[token.token_id, { ...token }]]);
    const commands = [];
    const historyEntries = [];
    const timers = new Map();
    let nextTimer = 1;
    let dirty = 0;
    let invalidated = 0;
    const blockCalls = [];

    const sandbox = {
        window: {
            setTimeout: (fn, ms) => { const id = nextTimer++; timers.set(id, { fn, ms }); return id; },
            clearTimeout: (id) => timers.delete(id),
            GravewrightRealtime: {
                sendCommand: (command, payload) => commands.push({ command, payload }),
            },
            GravewrightLighting: {
                blocksMovement: (_canvas, from, to) => {
                    blockCalls.push({ from, to });
                    return blocked(from, to);
                },
                invalidateFor: () => { invalidated += 1; },
            },
        },
    };

    new Function("window", "Object", fs.readFileSync(SCRIPT, "utf8"))(sandbox.window, Object);

    const steps = sandbox.window.GravewrightMapTokenSteps.createTokenSteps({
        canControlToken: () => controllable,
        clampGridPosition: (gx, gy) => ({
            grid_x: Math.max(0, Math.min(20, gx)),
            grid_y: Math.max(0, Math.min(12, gy)),
        }),
        history: { push: (entry) => historyEntries.push(entry) },
        markDirty: () => { dirty += 1; },
        sceneDataFor: () => ({ id: "scene-1", scaledTileSize: tile }),
        selectedSet: () => new Set(selected),
        tokenStoreFor: () => store,
    });

    return {
        steps, canvas, store, commands, historyEntries, blockCalls,
        press: (key) => steps.step(canvas, key),
        cell: () => {
            const t = store.get(token.token_id);
            return { x: t.grid_x, y: t.grid_y };
        },
        settle: () => {
            const pending = [...timers.values()];
            timers.clear();
            pending.forEach(({ fn }) => fn());
        },
        counts: () => ({ dirty, invalidated }),
    };
}

const failures = [];
function check(name, condition, detail = "") {
    if (condition) return console.log(`ok   ${name}`);
    failures.push(name);
    console.log(`FAIL ${name}${detail ? ` :: ${detail}` : ""}`);
}

{
    const world = buildWorld();
    world.press("ArrowRight");
    check("seta move uma celula", world.cell().x === 6 && world.cell().y === 5, JSON.stringify(world.cell()));
    world.press("ArrowDown");
    check("segunda seta acumula", world.cell().x === 6 && world.cell().y === 6);
    check("o passo e local: nada foi enviado ainda", world.commands.length === 0);
    check("o tabuleiro redesenhou a cada passo", world.counts().dirty === 2);
    check("a visao foi invalidada a cada passo", world.counts().invalidated === 2);
}

{
    // "liberar ao soltar": segurar a seta vira uma escrita, nao uma por passo
    const world = buildWorld();
    ["ArrowRight", "ArrowRight", "ArrowRight", "ArrowDown"].forEach((k) => world.press(k));
    check("nada enviado enquanto anda", world.commands.length === 0);
    world.settle();
    check("uma unica escrita ao parar", world.commands.length === 1, JSON.stringify(world.commands));
    const payload = world.commands[0].payload;
    check("a escrita leva a posicao final",
        payload.grid_x === 8 && payload.grid_y === 6, JSON.stringify(payload));
    check("comando certo", world.commands[0].command === "token.move");
}

{
    // parede barra: a celula nao muda e nada e agendado
    const world = buildWorld({ blocked: () => true });
    world.press("ArrowRight");
    check("passo bloqueado nao move", world.cell().x === 5 && world.cell().y === 5);
    world.settle();
    check("passo bloqueado nao grava", world.commands.length === 0);
    check("mesmo bloqueado, a tecla e consumida", world.press("ArrowRight") === true);
}

{
    // a colisao recebe o centro do token, nao o canto
    const world = buildWorld();
    world.press("ArrowRight");
    const call = world.blockCalls[0];
    check("colisao usa o centro da celula de origem",
        call.from.x === 5.5 * 70 && call.from.y === 5.5 * 70, JSON.stringify(call.from));
    check("colisao usa o centro da celula de destino",
        call.to.x === 6.5 * 70 && call.to.y === 5.5 * 70, JSON.stringify(call.to));
}

{
    // so anda quem o jogador controla
    const world = buildWorld({ controllable: false });
    check("token sem controle nao anda pelas setas", world.press("ArrowRight") === false);
    check("e a celula fica onde estava", world.cell().x === 5);
}

{
    // com varios selecionados o arrasto continua sendo o caminho
    const world = buildWorld({ selected: ["t1", "t2"] });
    check("selecao multipla nao anda pelas setas", world.press("ArrowRight") === false);
}

{
    // a borda da cena para o passo sem gravar nada
    const world = buildWorld({ token: { token_id: "t1", grid_x: 0, grid_y: 5, width_cells: 1, height_cells: 1 } });
    check("borda consome a tecla", world.press("ArrowLeft") === true);
    check("borda nao move", world.cell().x === 0);
    world.settle();
    check("borda nao grava", world.commands.length === 0);
}

{
    // desfazer um trajeto inteiro volta ao ponto de partida, nao um passo
    const world = buildWorld();
    ["ArrowRight", "ArrowRight", "ArrowUp"].forEach((k) => world.press(k));
    world.settle();
    check("um trajeto vira uma entrada de historico", world.historyEntries.length === 1);
    world.commands.length = 0;
    world.historyEntries[0].undo();
    check("desfazer volta a origem do trajeto",
        world.commands[0].payload.grid_x === 5 && world.commands[0].payload.grid_y === 5,
        JSON.stringify(world.commands[0].payload));
}

{
    const world = buildWorld();
    check("teclas nao-seta nao sao tratadas",
        !world.steps.handles("Delete") && !world.steps.handles("a"));
    check("as quatro setas sao tratadas",
        ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].every((k) => world.steps.handles(k)));
}

if (failures.length) {
    console.error(`\n${failures.length} verificacao(oes) falharam: ${failures.join(", ")}`);
    process.exit(1);
}
console.log("\ntodas as verificacoes de movimento passaram");
