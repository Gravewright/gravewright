/*
 * Cobertura de colisão do arrasto de token (static/js/map/drag/map-token-drag.js).
 *
 * O arrasto é o caminho pelo qual a mesa realmente anda com o token, e ele não
 * consultava as paredes: só o passo por setas consultava. Este harness carrega o
 * arquivo real sobre dependências mínimas e exercita a regra dos dois lados -
 * jogador barrado, mestre livre: inclusive no arrasto de grupo. Sai != 0 na
 * primeira falha.
 */
const fs = require("fs");
const path = require("path");

const SCRIPT = path.resolve(__dirname, "../../static/js/map/drag/map-token-drag.js");

const TILE = 50;

function buildWorld({ isGm = false, wallX = 300 } = {}) {
    const tokens = new Map([
        ["t1", { token_id: "t1", grid_x: 4, grid_y: 4, width_cells: 1, height_cells: 1 }],
        ["t2", { token_id: "t2", grid_x: 4, grid_y: 6, width_cells: 1, height_cells: 1 }],
    ]);
    const sent = [];
    const win = {
        GravewrightLighting: {
            // Parede vertical em ``wallX``: cruzar é sair de um lado e chegar no outro.
            blocksMovement: (_canvas, from, to) =>
                (from.x < wallX && to.x > wallX) || (from.x > wallX && to.x < wallX),
        },
        GravewrightRealtime: { sendCommand: (command, payload) => sent.push({ command, payload }) },
    };
    const documentStub = { body: { dataset: {} } };

    new Function("window", "document", fs.readFileSync(SCRIPT, "utf8"))(win, documentStub);

    const canvas = {
        dataset: { roomId: "campaign-1" },
        setPointerCapture() {},
        releasePointerCapture() {},
    };
    let selected = new Set(["t1"]);

    const controller = win.GravewrightMapTokenDrag.createTokenDragController({
        canControlToken: () => true,
        clampGridPosition: (gx, gy) => ({
            grid_x: Math.max(0, Math.min(40, gx)),
            grid_y: Math.max(0, Math.min(40, gy)),
        }),
        effectiveIsGm: () => isGm,
        history: { push: () => {} },
        isSelected: (_canvas, id) => selected.has(id),
        markDirty: () => {},
        sceneDataFor: () => ({ id: "scene-1", scaledTileSize: TILE, width: 2000, height: 2000 }),
        screenToWorldXY: (x, y) => ({ worldX: x, worldY: y }),
        selectToken: () => {},
        selectedSet: () => selected,
        snapDragToGrid: (worldX, worldY) => ({
            grid_x: Math.round(worldX / TILE),
            grid_y: Math.round(worldY / TILE),
        }),
        stateFor: () => ({}),
        tokenStoreFor: () => tokens,
    });

    return {
        controller,
        canvas,
        tokens,
        sent,
        select: (ids) => { selected = new Set(ids); },
    };
}

let failures = 0;
function check(label, condition) {
    console.log(`${condition ? "ok  " : "FAIL"}   ${label}`);
    if (!condition) failures += 1;
}

// O jogador anda até a parede e para nela.
{
    const world = buildWorld({ isGm: false });
    world.controller.start(world.canvas, { pointerId: 1, clientX: 200, clientY: 200 }, world.tokens.get("t1"));

    world.controller.update({ pointerId: 1, clientX: 250, clientY: 200 });
    check("jogador anda ate a parede", world.controller.active().currentGridX === 5);

    world.controller.update({ pointerId: 1, clientX: 400, clientY: 200 });
    check("jogador nao atravessa a parede", world.controller.active().currentGridX === 5);
    check("o desenho volta para a celula permitida", world.controller.active().currentWorldX === 5 * TILE);

    world.controller.stop({ pointerId: 1 });
    check("grava a celula permitida, nao a do ponteiro", world.tokens.get("t1").grid_x === 5);
}

// O mestre atravessa: é ele quem põe o monstro na sala trancada.
{
    const world = buildWorld({ isGm: true });
    world.controller.start(world.canvas, { pointerId: 2, clientX: 200, clientY: 200 }, world.tokens.get("t1"));
    world.controller.update({ pointerId: 2, clientX: 400, clientY: 200 });
    check("mestre atravessa a parede", world.controller.active().currentGridX === 8);
    world.controller.stop({ pointerId: 2 });
    check("mestre grava do outro lado", world.tokens.get("t1").grid_x === 8);
}

// Sem parede no caminho, o arrasto continua como sempre foi.
{
    const world = buildWorld({ isGm: false, wallX: 5000 });
    world.controller.start(world.canvas, { pointerId: 3, clientX: 200, clientY: 200 }, world.tokens.get("t1"));
    world.controller.update({ pointerId: 3, clientX: 400, clientY: 350 });
    check("mapa livre nao barra o arrasto", world.controller.active().currentGridX === 8);
    world.controller.stop({ pointerId: 3 });
    check("mapa livre grava o destino", world.tokens.get("t1").grid_x === 8);
    check("arrasto envia a trajetoria validada", world.sent[0].payload.movement_path.at(-1).grid_x === 8);
}

// Arrasto de grupo: um barrado trava a formação inteira.
{
    const world = buildWorld({ isGm: false });
    world.select(["t1", "t2"]);
    world.controller.start(world.canvas, { pointerId: 4, clientX: 200, clientY: 200 }, world.tokens.get("t1"));

    world.controller.update({ pointerId: 4, clientX: 250, clientY: 200 });
    check("grupo anda ate a parede", world.controller.active().currentGridX === 5);

    world.controller.update({ pointerId: 4, clientX: 400, clientY: 200 });
    check("grupo inteiro trava na parede", world.controller.active().currentGridX === 5);

    world.controller.stop({ pointerId: 4 });
    check("companheiro do grupo nao atravessa", world.tokens.get("t2").grid_x === 5);
}

console.log(
    failures
        ? `\n${failures} verificacao(oes) de arrasto falharam`
        : "\ntodas as verificacoes de arrasto passaram",
);
process.exit(failures ? 1 : 0);
