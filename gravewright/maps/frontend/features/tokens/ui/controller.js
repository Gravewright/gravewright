import { text as gwText, formatNumber, } from "../../../shared/config/i18n/text.js";
import { suggestTokenRoute } from "../model/token-pathfinding.js";
import { routeMeasurements, routeLengths, routePosition, ROUTE_CELLS_PER_SECOND, MAX_ROUTE_POINTS, } from "../model/token-route.js";
import { interpolateTokens, TOKEN_SETTLE_MS } from "../model/token-motion.js";
import { renderingPreferences } from "../../../shared/rendering/render-profile.js";
import { LONG_PRESS_MS } from "../../../widgets/game-board/model/board-input.js";
import { hitToken, inMarquee, position, movementBlocked, } from "../model/token-interaction.js";
export function tokenController(element, options) {
    const props = { ...options.props }, emit = options.emit, nextTick = () => Promise.resolve();
    const box = (initial) => {
        let value = initial;
        return {
            get value() {
                return value;
            },
            set value(next) {
                value = next;
                options.repaint();
            },
        };
    };
    const derive = (read) => ({
        get value() {
            return read();
        },
    });
    const root = box(), selected = box([]), busy = box(false), error = box(""), context = box(), marquee = box(), sheet = box(), editor = box(), confirm = box(false), clipboard = box([]);
    const displayed = box(props.tokens), destinations = box([]);
    let animation = 0, heldArrow = "", queuedArrow;
    function stopAnimation() {
        cancelAnimationFrame(animation);
        animation = 0;
    }
    function present(rows) {
        displayed.value = rows;
        emit("preview", rows);
    }
    function merged(rows) {
        const changed = new Map(rows.map((t) => [t.id, t]));
        return remoteRows().map((t) => changed.get(t.id) ?? t);
    }
    function animate(rows, immediate = false) {
        stopAnimation();
        const previous = new Map(displayed.value.map((t) => [t.id, t]));
        // Never animate a newly visible token from a hidden/stale position, or cut through a wall.
        const from = rows.map((t) => {
            const old = previous.get(t.id);
            return old &&
                old.hidden === t.hidden &&
                !movementBlocked(old, t, props.walls, props.cell)
                ? old
                : t;
        });
        const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches ||
            renderingPreferences.current().capabilities.motion === "none";
        if (immediate ||
            reduced ||
            !rows.some((t, i) => t.gridX !== from[i].gridX || t.gridY !== from[i].gridY)) {
            present(rows);
            return;
        }
        const start = performance.now();
        const tick = (now) => {
            if (closed)
                return;
            const progress = Math.min(1, (now - start) / TOKEN_SETTLE_MS);
            present(interpolateTokens(from, rows, progress));
            if (progress < 1)
                animation = requestAnimationFrame(tick);
            else
                animation = 0;
        };
        present(interpolateTokens(from, rows, 0));
        animation = requestAnimationFrame(tick);
    }
    const remote = new Map();
    let stream = "", livePositions = [], lastSent = 0;
    const livePaths = new Map();
    let heartbeat;
    function remoteRows(rows = props.tokens) {
        return rows.map((t) => {
            const preview = remote.get(t.id);
            return preview && preview.version === t.version
                ? { ...t, gridX: preview.gridX, gridY: preview.gridY }
                : t;
        });
    }
    function transmit() {
        if (!stream || !livePositions.length || closed)
            return;
        lastSent = performance.now();
        emit("motion", {
            stream,
            phase: "update",
            positions: livePositions.map((p) => ({
                ...p,
                path: livePaths.get(p.id) ?? [],
            })),
        });
        for (const p of livePositions)
            livePaths.set(p.id, [[p.gridX, p.gridY]]);
    }
    function publish(rows) {
        if (!stream)
            return;
        livePositions = rows.map(({ id, gridX, gridY, version }) => ({
            id,
            gridX: Number(gridX.toFixed(4)),
            gridY: Number(gridY.toFixed(4)),
            version,
        }));
        for (const p of livePositions) {
            const path = livePaths.get(p.id) ?? [];
            path.push([p.gridX, p.gridY]);
            livePaths.set(p.id, path.slice(-16));
        }
        if (performance.now() - lastSent >= 100)
            transmit();
    }
    function finishBroadcast(phase) {
        if (heartbeat)
            clearInterval(heartbeat);
        heartbeat = undefined;
        if (stream)
            emit("motion", { stream, phase });
        stream = "";
        livePositions = [];
        livePaths.clear();
    }
    function receiveMotion(value) {
        const packet = value;
        if (closed ||
            !packet ||
            packet.scene_id !== scope.map ||
            typeof packet.stream !== "string" ||
            typeof packet.connection !== "string")
            return;
        const key = packet.connection + ":" + packet.stream;
        if (packet.phase === "update" && Array.isArray(packet.positions)) {
            for (const p of packet.positions) {
                const token = props.tokens.find((t) => t.id === p.id);
                if (token &&
                    p.version === token.version &&
                    Number.isFinite(p.gridX) &&
                    Number.isFinite(p.gridY))
                    remote.set(p.id, {
                        ...p,
                        stream: key,
                        expires: performance.now() + 1500,
                    });
            }
        }
        else if (packet.phase === "cancel") {
            for (const [id, p] of remote)
                if (p.stream === key)
                    remote.delete(id);
        }
        else if (packet.phase === "end") {
            // Keep the last visual point while the confirmed snapshot catches up.
            for (const p of remote.values())
                if (p.stream === key)
                    p.expires = performance.now() + 700;
            emit("refresh");
        }
        else
            return;
        if (drag)
            present(merged(drag.current));
        else if (!busy.value)
            animate(remoteRows());
    }
    const expireRemote = setInterval(() => {
        let changed = false;
        for (const [id, p] of remote)
            if (p.expires <= performance.now()) {
                remote.delete(id);
                changed = true;
            }
        if (changed && !drag && !busy.value)
            animate(remoteRows());
    }, 250);
    const route = box([]), walking = box(false);
    let routeFrame = 0;
    const routeMeasurement = derive(() => routeMeasurements(route.value, props.measureValue));
    function formatDistance(value) {
        return `${formatNumber(value)} ${props.measureUnit || gwText("units")}`;
    }
    const routeLine = derive(() => route.value
        .map((step) => {
        const t = step[0];
        return `${(t.gridX + t.cells / 2) * props.cell},${(t.gridY + (t.heightCells ?? t.cells) / 2) * props.cell}`;
    })
        .join(" "));
    let suggestionKey, suggestionValue, suggestionInputs = [];
    const suggested = derive(() => {
        if (walking.value) return undefined;
        // DOM paint reads this more than once. A* runs only when its inputs change.
        const inputs = [route.value, props.walls, props.cell, props.width, props.height];
        if (inputs.every((value, i) => value === suggestionInputs[i])) return suggestionValue;
        suggestionInputs = inputs;
        const key = JSON.stringify(inputs);
        if (key !== suggestionKey) {
            suggestionKey = key;
            suggestionValue = suggestTokenRoute(route.value, props.walls, props.cell, props.width, props.height);
        }
        return suggestionValue;
    });
    const suggestedMeasurement = derive(() => suggested.value
        ? routeMeasurements(suggested.value, props.measureValue)
        : undefined);
    const suggestedLine = derive(() => suggested.value
        ?.map((step) => {
        const t = step[0];
        return `${(t.gridX + t.cells / 2) * props.cell},${(t.gridY + (t.heightCells ?? t.cells) / 2) * props.cell}`;
    })
        .join(" "));
    const routeEnd = derive(() => route.value.at(-1)?.[0]);
    function useSuggestedRoute() {
        const candidate = suggested.value;
        if (walking.value || busy.value || !candidate)
            return;
        route.value = candidate;
        error.value = "";
    }
    function startBroadcast() {
        finishBroadcast("cancel");
        stream = crypto.randomUUID();
        lastSent = 0;
        heartbeat = setInterval(() => {
            if (performance.now() - lastSent >= 100)
                transmit();
        }, 250);
    }
    function addWaypoint(p, free) {
        if (busy.value || drag)
            return;
        const first = route.value[0] ??
            selection.value
                .filter((t) => t.canControl && !t.locked)
                .map((t) => ({ ...t }));
        if (!first.length) {
            error.value = gwText("Select a token you control.");
            return;
        }
        const previous = route.value.at(-1) ?? first;
        if (route.value.length >= MAX_ROUTE_POINTS + 1) {
            error.value = gwText("The route accepts up to {0} points.", MAX_ROUTE_POINTS);
            return;
        }
        const anchor = previous[0];
        const delta = {
            x: p.x - (anchor.gridX + anchor.cells / 2) * props.cell,
            y: p.y -
                (anchor.gridY + (anchor.heightCells ?? anchor.cells) / 2) * props.cell,
        };
        const next = previous.map((t) => ({
            ...t,
            ...position(t, delta, props.cell, props.width, props.height, props.grid && !free),
        }));
        if (next.every((t, i) => t.gridX === previous[i].gridX && t.gridY === previous[i].gridY))
            return;
        stopAnimation();
        context.value = undefined;
        error.value = "";
        route.value = [...(route.value.length ? route.value : [first]), next];
    }
    function walkRoute() {
        if (walking.value || busy.value || route.value.length < 2)
            return;
        const steps = route.value, first = steps[0], lengths = routeLengths(steps);
        if (first.some((t) => !props.tokens.some((v) => v.id === t.id &&
            v.version === t.version &&
            v.canControl &&
            !v.locked))) {
            cancel();
            error.value = "A rota foi cancelada porque um token mudou.";
            return;
        }
        if (!props.gm &&
            steps
                .slice(1)
                .some((step, i) => step.some((t, j) => movementBlocked(steps[i][j], t, props.walls, props.cell)))) {
            cancel();
            error.value = "A rota foi bloqueada por uma parede.";
            return;
        }
        stopAnimation();
        walking.value = true;
        busy.value = true;
        startBroadcast();
        let previousFrame, distance = 0, passed = 0;
        const tick = (now) => {
            if (closed || !walking.value)
                return;
            // A delayed first frame or a suspended tab must not skip the walk.
            if (previousFrame !== undefined)
                distance +=
                    (Math.min(100, Math.max(0, now - previousFrame)) / 1000) *
                        ROUTE_CELLS_PER_SECOND;
            previousFrame = now;
            const sample = routePosition(steps, lengths, distance);
            // Include crossed corners in the broadcast path, even after a slow frame.
            while (passed < sample.passed) {
                passed++;
                publish(steps[passed]);
            }
            present(merged(sample.tokens));
            publish(sample.tokens);
            if (!sample.done) {
                routeFrame = requestAnimationFrame(tick);
                return;
            }
            routeFrame = 0;
            walking.value = false;
            route.value = [];
            const paths = new Map(first.map((t, i) => [
                t.id,
                steps.map((step) => ({
                    gridX: step[i].gridX,
                    gridY: step[i].gridY,
                })),
            ]));
            transmit();
            saveMoves(first, steps.at(-1), paths, true);
        };
        publish(first);
        routeFrame = requestAnimationFrame(tick);
    }
    const selection = derive(() => props.tokens.filter((t) => selected.value.includes(t.id)));
    const interactive = derive(() => props.tool === "select");
    let closed = false, queue = Promise.resolve(), drag;
    const abort = new AbortController(), reader = { list: () => options.read() }, writer = {
        command: (_a, _b, action, data) => options.command(action, data),
        move: (_a, id, data) => options
            .command("move", { id, ...data })
            .then((r) => r.tokens.find((t) => t.id === id)),
    }, scope = {
        container: props.containerId,
        block: props.blockId,
        map: props.mapId,
    };
    const undo = box([]), redo = box([]);
    let pressTimer;
    function clearPress() {
        if (pressTimer)
            clearTimeout(pressTimer);
        pressTimer = undefined;
    }
    let lastPoint = { x: 0, y: 0 };
    function point(e) {
        const r = root.value.getBoundingClientRect();
        return {
            x: (e.clientX - r.left - props.viewport.x) / props.viewport.scale,
            y: (e.clientY - r.top - props.viewport.y) / props.viewport.scale,
        };
    }
    function stop(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    async function run(operation) {
        queue = queue.then(async () => {
            if (closed)
                return;
            busy.value = true;
            error.value = "";
            try {
                await operation();
            }
            catch (e) {
                if (!closed)
                    error.value = gwText("Could not complete the action. Check permissions or reload the scene state.");
            }
            finally {
                if (!closed) {
                    try {
                        const rows = await reader.list(scope.container, scope.map);
                        if (!closed) {
                            emit("changed", rows);
                            animate(remoteRows(rows));
                            emit("refresh");
                        }
                    }
                    catch {
                        if (!closed)
                            animate(remoteRows());
                    }
                    if (!closed) {
                        finishBroadcast(error.value ? "cancel" : "end");
                        await nextTick();
                        busy.value = false;
                        if (queuedArrow && heldArrow === queuedArrow.key) {
                            const event = queuedArrow;
                            queuedArrow = undefined;
                            keys(event);
                        }
                    }
                }
            }
        });
        return queue;
    }
    function command(action, data = {}, ids = selected.value) {
        const chosen = [...ids];
        context.value = undefined;
        void run(async () => {
            const result = await writer.command(scope.container, scope.map, action, {
                tokenIds: chosen,
                ...data,
            });
            if (closed)
                return;
            emit("changed", result.tokens);
            editor.value = undefined;
            confirm.value = false;
            if (result.createdIds.length)
                selected.value = result.createdIds;
        });
    }
    function down(e) {
        if (!interactive.value)
            return;
        const p = point(e), token = hitToken(p, displayed.value, props.cell);
        if (e.button === 0 && e.ctrlKey && selected.value.length) {
            stop(e);
            addWaypoint(p, e.altKey);
            return;
        }
        if (route.value.length) {
            if (e.button === 0)
                stop(e);
            return;
        }
        if (e.button === 2) {
            if (token && (props.gm || token.canControl))
                stop(e);
            return;
        }
        if (e.button !== 0)
            return;
        if (token) {
            stop(e);
            if (busy.value)
                return;
            if (e.shiftKey) {
                selected.value = selected.value.includes(token.id)
                    ? selected.value.filter((id) => id !== token.id)
                    : [...selected.value, token.id];
                return;
            }
            if (!selected.value.includes(token.id))
                selected.value = [token.id];
            if (!token.canControl || token.locked)
                return;
        }
        else {
            stop(e);
            if (busy.value)
                return;
            marquee.value = { from: p, to: p };
        }
        stopAnimation();
        const original = token
            ? selection.value
                .filter((t) => t.canControl && !t.locked)
                .map((t) => ({ ...t }))
            : [];
        const visualOrigin = original.map((t) => {
            const visual = displayed.value.find((v) => v.id === t.id);
            return {
                ...t,
                gridX: visual?.gridX ?? t.gridX,
                gridY: visual?.gridY ?? t.gridY,
            };
        });
        drag = {
            pointer: e.pointerId,
            from: p,
            original,
            visualOrigin,
            current: visualOrigin,
            paths: new Map(original.map((t, i) => [
                t.id,
                [
                    { gridX: t.gridX, gridY: t.gridY },
                    { gridX: visualOrigin[i].gridX, gridY: visualOrigin[i].gridY },
                ],
            ])),
            moved: false,
            additive: e.shiftKey,
            selection: [...selected.value],
        };
        if (original.length)
            startBroadcast();
        context.value = undefined;
        root.value?.setPointerCapture(e.pointerId);
        clearPress();
        pingShift = e.shiftKey;
        if (!token)
            pressTimer = setTimeout(() => {
                if (!closed && drag)
                    emit("ping", p, pingShift);
            }, LONG_PRESS_MS);
    }
    function move(e) {
        lastPoint = point(e);
        pingShift = e.shiftKey;
        if (drag &&
            Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) *
                props.viewport.scale >
                10)
            clearPress();
        if (!interactive.value)
            return;
        if (!drag) {
            emit("hover", hitToken(lastPoint, props.tokens, props.cell)?.id);
            return;
        }
        if (drag.pointer !== e.pointerId)
            return;
        stop(e);
        if (!drag.original.length) {
            drag.moved =
                Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) *
                    props.viewport.scale >=
                    3;
            marquee.value = { from: drag.from, to: lastPoint };
            selected.value = [
                ...new Set([
                    ...(drag.additive ? drag.selection : []),
                    ...props.tokens
                        .filter((t) => inMarquee(t, drag.from, lastPoint, props.cell) &&
                        (props.gm || t.canControl))
                        .map((t) => t.id),
                ]),
            ];
            return;
        }
        if (!drag.moved &&
            Math.hypot(lastPoint.x - drag.from.x, lastPoint.y - drag.from.y) *
                props.viewport.scale <
                3)
            return;
        const delta = {
            x: lastPoint.x - drag.from.x,
            y: lastPoint.y - drag.from.y,
        }, next = drag.visualOrigin.map((t) => ({
            ...t,
            ...position(t, delta, props.cell, props.width, props.height, false),
        }));
        if (!props.gm &&
            next.some((t, i) => movementBlocked(drag.current[i], t, props.walls, props.cell))) {
            error.value = gwText("Movement blocked by a wall.");
            return;
        }
        if (next.some((t) => (drag.paths.get(t.id)?.length ?? 0) >= 511)) {
            error.value = gwText("Release the token to finish this movement segment.");
            return;
        }
        error.value = "";
        drag.moved = true;
        drag.current = next;
        for (const t of next) {
            const path = drag.paths.get(t.id);
            const last = path[path.length - 1];
            if (last.gridX !== t.gridX || last.gridY !== t.gridY)
                path.push({ gridX: t.gridX, gridY: t.gridY });
        }
        destinations.value =
            props.grid && !e.altKey
                ? next
                    .map((t) => ({
                    ...t,
                    ...position(t, { x: 0, y: 0 }, props.cell, props.width, props.height, true),
                }))
                    .filter((t, i) => props.gm ||
                    !movementBlocked(next[i], t, props.walls, props.cell))
                : [];
        present(merged(next));
        publish(next);
    }
    function up(e) {
        clearPress();
        if (!drag || drag.pointer !== e.pointerId)
            return;
        stop(e);
        const d = drag;
        drag = undefined;
        destinations.value = [];
        marquee.value = undefined;
        if (root.value?.hasPointerCapture(e.pointerId))
            root.value.releasePointerCapture(e.pointerId);
        if (d.original.length && d.moved) {
            const target = d.current.map((t) => {
                const snapped = {
                    ...t,
                    ...position(t, { x: 0, y: 0 }, props.cell, props.width, props.height, props.grid && !e.altKey),
                };
                return !props.gm && movementBlocked(t, snapped, props.walls, props.cell)
                    ? t
                    : snapped;
            });
            for (const t of target) {
                const path = d.paths.get(t.id);
                const last = path.at(-1);
                if (last.gridX !== t.gridX || last.gridY !== t.gridY)
                    path.push({ gridX: t.gridX, gridY: t.gridY });
            }
            publish(target);
            transmit();
            saveMoves(d.original, target, d.paths, true);
        }
        else {
            finishBroadcast("cancel");
            if (!d.original.length && !d.additive && !d.moved)
                selected.value = [];
        }
    }
    function cancel() {
        clearPress();
        stopAnimation();
        finishBroadcast("cancel");
        cancelAnimationFrame(routeFrame);
        routeFrame = 0;
        route.value = [];
        if (walking.value) {
            walking.value = false;
            busy.value = false;
        }
        if (drag && root.value?.hasPointerCapture(drag.pointer))
            root.value.releasePointerCapture(drag.pointer);
        drag = undefined;
        marquee.value = undefined;
        destinations.value = [];
        displayed.value = remoteRows();
        if (!closed)
            present(displayed.value);
        else
            emit("preview", undefined);
    }
    function saveMoves(from, to, paths, record, after) {
        animate(merged(to));
        void run(async () => {
            const accepted = [], starts = [];
            let failed = 0;
            for (const t of to) {
                const old = from.find((v) => v.id === t.id);
                if (old.gridX === t.gridX &&
                    old.gridY === t.gridY &&
                    !(paths.get(t.id) ?? []).some((p) => p.gridX !== old.gridX || p.gridY !== old.gridY))
                    continue;
                try {
                    const result = await writer.move(scope.container, t.id, {
                        gridX: t.gridX,
                        gridY: t.gridY,
                        expectedVersion: old.version,
                        path: paths.get(t.id),
                    });
                    accepted.push(result);
                    starts.push(old);
                }
                catch {
                    failed++;
                }
            }
            if (closed)
                return;
            if (failed)
                error.value = gwText("{0} movement(s) refused: wall, locked token, no control, or a change in another window.", failed);
            if (!failed)
                after?.();
            if (record && accepted.length) {
                undo.value = [
                    ...undo.value.slice(-49),
                    { from: starts, to: accepted, paths },
                ];
                redo.value = [];
            }
        });
    }
    function history(back) {
        if (busy.value)
            return;
        const source = back ? undo : redo, destination = back ? redo : undo;
        const item = source.value.at(-1);
        if (!item)
            return;
        const target = back ? item.from : item.to, from = target
            .map((t) => props.tokens.find((v) => v.id === t.id))
            .filter((t) => !!t);
        const path = new Map([...item.paths].map(([id, points]) => [
            id,
            back ? [...points].reverse() : points,
        ]));
        if (from.length !== target.length) {
            error.value = gwText("A token in this movement is no longer in the scene.");
            return;
        }
        saveMoves(from, target, path, false, () => {
            source.value.pop();
            destination.value.push(item);
        });
    }
    function menu(e) {
        if (!interactive.value)
            return;
        const token = hitToken(point(e), displayed.value, props.cell);
        if (!token || (!props.gm && !token.canControl))
            return;
        stop(e);
        if (!selected.value.includes(token.id))
            selected.value = [token.id];
        context.value = { x: e.clientX, y: e.clientY, token };
    }
    function double(e) {
        if (!interactive.value)
            return;
        const token = hitToken(point(e), displayed.value, props.cell);
        if (token?.canOpenSheet) {
            stop(e);
            cancel();
            sheet.value = { ...token };
        }
    }
    function edit(mode) {
        context.value = undefined;
        editor.value = { mode, tokens: selection.value.map((t) => ({ ...t })) };
    }
    function copy() {
        clipboard.value = selection.value.map((t) => t.id);
        context.value = undefined;
    }
    function paste() {
        if (props.gm && clipboard.value.length)
            command("duplicate", {}, clipboard.value);
    }
    let pingShift = false;
    function keys(e) {
        pingShift = e.shiftKey;
        if (props.externalMixed ||
            !interactive.value ||
            e.defaultPrevented ||
            (e.target instanceof Element &&
                e.target.closest("input,textarea,select,[contenteditable=true],[role=dialog],.directory-context-menu")))
            return;
        const mod = e.ctrlKey || e.metaKey;
        if (e.key === "Escape") {
            cancel();
            context.value = undefined;
            selected.value = [];
            return;
        }
        if (e.key.startsWith("Arrow"))
            heldArrow = e.key;
        if (busy.value || route.value.length) {
            if (!walking.value &&
                !route.value.length &&
                e.key.startsWith("Arrow") &&
                selected.value.length) {
                stop(e);
                queuedArrow = new KeyboardEvent("keydown", { key: e.key });
            }
            return;
        }
        if (mod && e.key.toLowerCase() === "a") {
            stop(e);
            selected.value = props.tokens
                .filter((t) => props.gm || t.canControl)
                .map((t) => t.id);
            return;
        }
        if (mod && e.key.toLowerCase() === "c") {
            stop(e);
            copy();
            return;
        }
        if (mod && e.key.toLowerCase() === "v") {
            stop(e);
            paste();
            return;
        }
        if (mod && ["z", "y"].includes(e.key.toLowerCase())) {
            stop(e);
            history(e.key.toLowerCase() === "z" && !e.shiftKey);
            return;
        }
        if (["Delete", "Backspace"].includes(e.key) &&
            props.gm &&
            selection.value.length) {
            stop(e);
            confirm.value = true;
            return;
        }
        const direction = {
            ArrowUp: { x: 0, y: -props.cell },
            ArrowDown: { x: 0, y: props.cell },
            ArrowLeft: { x: -props.cell, y: 0 },
            ArrowRight: { x: props.cell, y: 0 },
        }[e.key];
        if (!direction || !selection.value.length || drag)
            return;
        stop(e);
        const from = selection.value.filter((t) => t.canControl && !t.locked), to = from.map((t) => ({
            ...t,
            ...position(t, direction, props.cell, props.width, props.height, false),
        }));
        if (!props.gm &&
            to.some((t, i) => movementBlocked(from[i], t, props.walls, props.cell))) {
            error.value = gwText("Movement blocked by a wall.");
            return;
        }
        saveMoves(from, to, new Map(to.map((t, i) => [
            t.id,
            [
                { gridX: from[i].gridX, gridY: from[i].gridY },
                { gridX: t.gridX, gridY: t.gridY },
            ],
        ])), true);
    }
    function keyup(e) {
        pingShift = e.shiftKey;
        if (e.key === "Control" && !e.ctrlKey && route.value.length) {
            walkRoute();
            return;
        }
        if (e.key === heldArrow) {
            heldArrow = "";
            queuedArrow = undefined;
        }
    }
    function blur() {
        heldArrow = "";
        queuedArrow = undefined;
        cancel();
    }
    root.value = element;
    const events = {
        pointerdown: down,
        pointermove: move,
        pointerup: up,
        pointercancel: cancel,
        contextmenu: menu,
        dblclick: double,
    };
    const listeners = Object.entries(events).map(([name, fn]) => {
        const handler = (e) => {
            fn(e);
            options.repaint();
        };
        element.addEventListener(name, handler);
        return [name, handler];
    });
    const key = (e) => {
        keys(e);
        options.repaint();
    };
    window.addEventListener("keydown", key);
    window.addEventListener("keyup", keyup);
    window.addEventListener("blur", blur);
    return {
        get view() {
            return {
                displayed: displayed.value,
                destinations: destinations.value,
                selected: selected.value,
                selection: selection.value,
                context: context.value,
                editor: editor.value,
                sheet: sheet.value,
                confirm: confirm.value,
                clipboard: clipboard.value,
                busy: busy.value,
                error: error.value,
                marquee: marquee.value,
                route: route.value,
                routeLine: routeLine.value,
                routeMeasurement: routeMeasurement.value,
                suggestedLine: suggestedLine.value,
                suggestedMeasurement: suggestedMeasurement.value,
                routeEnd: routeEnd.value,
                walking: walking.value,
                routeBlocked: route.value.slice(1).some((step, i) => step.some((token, j) => movementBlocked(route.value[i][j], token, props.walls, props.cell))),
                undo: undo.value,
                redo: redo.value,
                interactive: interactive.value,
            };
        },
        receiveMotion,
        call(name, ...args) {
            const methods = {
                command,
                edit,
                copy,
                paste,
                select: ids => { selected.value = ids; },
                history,
                cancel,
                useSuggestedRoute,
                closeContext: () => (context.value = undefined),
                closeEditor: () => (editor.value = undefined),
                closeSheet: () => (sheet.value = undefined),
                closeConfirm: () => (confirm.value = false),
                remove: () => {
                    context.value = undefined;
                    confirm.value = true;
                },
                openSheet: (t) => {
                    sheet.value = t;
                    context.value = undefined;
                },
            };
            const result = methods[name](...args);
            options.repaint();
            return result;
        },
        update(next) {
            const oldTool = props.tool;
            Object.assign(props, next);
            if (oldTool !== props.tool)
                cancel();
            if (next.tokens) {
                const rows = props.tokens;
                if (sheet.value) {
                    const fresh = rows.find((t) => t.id === sheet.value.id);
                    if (!fresh?.canOpenSheet ||
                        fresh.linkMode !== sheet.value.linkMode ||
                        (sheet.value.canControl && !fresh.canControl))
                        sheet.value = undefined;
                }
                selected.value = selected.value.filter((id) => rows.some((t) => t.id === id));
                if (drag?.original.some((t) => !rows.some((r) => r.id === t.id &&
                    r.version === t.version &&
                    r.canControl &&
                    !r.locked)))
                    cancel();
                if (route.value.length &&
                    route.value[0].some((t) => !rows.some((r) => r.id === t.id &&
                        r.version === t.version &&
                        r.canControl &&
                        !r.locked)))
                    cancel();
                for (const [id, p] of remote)
                    if (!rows.some((t) => t.id === id && t.version === p.version))
                        remote.delete(id);
                if (!drag && !busy.value)
                    animate(remoteRows());
            }
            if (next.walls &&
                walking.value &&
                route.value.length &&
                !props.gm &&
                route.value
                    .slice(1)
                    .some((step, i) => step.some((t, j) => movementBlocked(route.value[i][j], t, props.walls, props.cell))))
                cancel();
            options.repaint();
        },
        destroy() {
            closed = true;
            abort.abort();
            clearInterval(expireRemote);
            remote.clear();
            cancel();
            for (const [name, fn] of listeners)
                element.removeEventListener(name, fn);
            window.removeEventListener("keydown", key);
            window.removeEventListener("keyup", keyup);
            window.removeEventListener("blur", blur);
        },
    };
}
