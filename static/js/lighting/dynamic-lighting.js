(() => {
    const controllers = new Map();


    const BUILD = "lights-vision-1";
    const DRAG_THRESHOLD_PX = 6;
    const SNAP_DIVISIONS = 2;
    const ENDPOINT_SNAP_PX = 12;
    const NODE_GRAB_PX = 10;
    const NODE_EPSILON = 1;
    const DOOR_GRAB_PX = 14;
    const LIGHT_GRAB_PX = 12;


    const ANIMATION_INTERVAL_MS = 40;

    const RADIAL_SAMPLES = 64;



    const WALL_CHUNK_TILES = 2;


    const PROBE_START_TILES = 12;

    const GM_DARKNESS_PREVIEW = 0.35;

    const DOOR_CYCLE = { closed: "open", open: "locked", locked: "closed" };
    let activeLayer = "game";






    const EDIT_LAYERS = { wall: "walls", door: "walls", light: "lighting", particles: "effects", shader: "effects" };
    let selectedTokenId = "";
    let componentClipboard = null;



    let visionPreviewTokenId = "";
    let tracing = false;
    const trace = (step, detail) => { if (tracing) console.log(`[paredes] ${step}`, detail ?? ""); };
    const csrf = () => typeof window.csrfToken === "function" ? window.csrfToken() : "";
    const redraw = () => window.GravewrightMap?.redraw?.();
    const toast = (message) => window.GravewrightToasts?.showToast?.(message);
    const currentUserId = () => document.body?.dataset?.currentUserId || "";

    async function post(url, body) {
        if (document.body?.dataset?.streamerMode === "true") {
            return localPost(url, body);
        }
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { Accept: "application/json", "Content-Type": "application/json", "x-csrftoken": csrf() },
            body: JSON.stringify(body),
        });
        const data = await response.json().catch(() => ({}));




        if (!response.ok) {
            throw new Error(data.error_key || `lighting.errors.http_${response.status}`);
        }
        return data;
    }

    function localPost(url, body) {
        const controller = [...controllers.values()].find((item) => item.roomId === body.campaign_id);
        if (!controller) throw new Error("lighting.errors.not_found");
        const id = (prefix) => `streamer-${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const withoutMeta = (value) => Object.fromEntries(
            Object.entries(value).filter(([key]) => !["campaign_id", "scene_id"].includes(key)),
        );
        const update = (items, itemId, patch) => {
            const item = items.find((candidate) => candidate.id === itemId);
            if (item) Object.assign(item, withoutMeta(patch));
            return item || null;
        };
        const remove = (items, ids) => items.filter((item) => !ids.includes(item.id));

        if (url === "/game/walls") return { wall: { id: id("wall"), ...withoutMeta(body), door_state: "closed" } };
        if (url === "/game/walls/door-state") return { wall: update(controller.walls, body.wall_id, { door_state: body.door_state }) };
        if (url === "/game/walls/move-node") return {};
        if (url === "/game/walls/move-endpoint") {
            const wall = controller.walls.find((item) => item.id === body.wall_id);
            if (wall && [1, 2].includes(Number(body.endpoint))) {
                wall[`x${body.endpoint}`] = body.to_x;
                wall[`y${body.endpoint}`] = body.to_y;
            }
            return { wall, walls: controller.walls };
        }
        if (url === "/game/walls/move-many") {
            const wanted = new Set(body.wall_ids || []);
            controller.walls = controller.walls.map((wall) => wanted.has(wall.id) ? {
                ...wall, x1: wall.x1 + body.dx, y1: wall.y1 + body.dy,
                x2: wall.x2 + body.dx, y2: wall.y2 + body.dy,
            } : wall);
            return { walls: controller.walls };
        }
        if (url === "/game/walls/split") {
            const wall = controller.walls.find((item) => item.id === body.wall_id);
            if (!wall) throw new Error("lighting.errors.not_found");
            const halves = [
                { ...wall, id: id("wall"), x2: body.x, y2: body.y },
                { ...wall, id: id("wall"), x1: body.x, y1: body.y },
            ];
            controller.walls = controller.walls.filter((item) => item.id !== wall.id).concat(halves);
            return { walls: controller.walls };
        }
        if (url === "/game/walls/delete-many") { controller.walls = remove(controller.walls, body.wall_ids || []); return {}; }

        if (url === "/game/lights") return { light: { id: id("light"), enabled: 1, ...withoutMeta(body) } };
        if (url === "/game/lights/update") return { light: update(controller.lights, body.light_id, body) };
        if (url === "/game/lights/delete") { controller.lights = remove(controller.lights, [body.light_id]); return {}; }
        if (url === "/game/lights/delete-many") { controller.lights = remove(controller.lights, body.light_ids || []); return {}; }

        if (url === "/game/particles") return { emitter: { id: id("emitter"), enabled: 1, ...withoutMeta(body) } };
        if (url === "/game/particles/update") return { emitter: update(controller.emitters, body.emitter_id, body) };
        if (url === "/game/particles/delete") { controller.emitters = remove(controller.emitters, [body.emitter_id]); return {}; }
        if (url === "/game/particles/delete-many") { controller.emitters = remove(controller.emitters, body.emitter_ids || []); return {}; }

        if (url === "/game/shaders") return { shader: { id: id("shader"), enabled: 1, name: "Shader", source: "", radius: 0, ...withoutMeta(body) } };
        if (url === "/game/shaders/update") return { shader: update(controller.shaders, body.shader_id, body) };
        if (url === "/game/shaders/delete") { controller.shaders = remove(controller.shaders, [body.shader_id]); return {}; }
        if (url === "/game/shaders/delete-many") { controller.shaders = remove(controller.shaders, body.shader_ids || []); return {}; }
        throw new Error("lighting.errors.invalid");
    }

    function rayHit(origin, angle, segment, max = 100000) {
        const dx = Math.cos(angle), dy = Math.sin(angle);
        const sx = segment.x2 - segment.x1, sy = segment.y2 - segment.y1;
        const den = dx * sy - dy * sx;
        if (Math.abs(den) < 1e-9) return null;
        const qx = segment.x1 - origin.x, qy = segment.y1 - origin.y;
        const t = (qx * sy - qy * sx) / den, u = (qx * dy - qy * dx) / den;
        return t >= 0 && t <= max && u >= 0 && u <= 1
            ? { x: origin.x + dx * t, y: origin.y + dy * t, distance: t }
            : null;
    }




    function coneOf(source) {
        const angle = Number(source?.angle);
        if (!Number.isFinite(angle) || angle <= 0 || angle >= 360) return null;
        return {
            centre: (Number(source.rotation) || 0) * Math.PI / 180,
            half: (angle / 2) * Math.PI / 180,
        };
    }




    function withinCone(angle, centre, half) {
        if (half >= Math.PI) return true;
        let delta = angle - centre;
        while (delta <= -Math.PI) delta += Math.PI * 2;
        while (delta > Math.PI) delta -= Math.PI * 2;
        return Math.abs(delta) <= half;
    }







    function visibilityPolygon(origin, segments, width, height, radius = 0, arc = true, cone = null) {
        const bounds = [
            { x1: 0, y1: 0, x2: width, y2: 0 }, { x1: width, y1: 0, x2: width, y2: height },
            { x1: width, y1: height, x2: 0, y2: height }, { x1: 0, y1: height, x2: 0, y2: 0 },
        ];
        const all = [...segments, ...bounds], angles = [], epsilon = 0.00001;
        all.forEach((segment) => [
            { x: segment.x1, y: segment.y1 }, { x: segment.x2, y: segment.y2 },
        ].forEach((point) => {
            const angle = Math.atan2(point.y - origin.y, point.x - origin.x);
            angles.push(angle - epsilon, angle, angle + epsilon);
        }));






        const reach = radius > 0 ? radius : 100000;
        if (radius > 0 && arc) {
            for (let i = 0; i < RADIAL_SAMPLES; i += 1) {
                angles.push(-Math.PI + (i / RADIAL_SAMPLES) * Math.PI * 2);
            }
        }





        let apex = null;
        if (cone) {
            const inside = angles.filter((angle) => withinCone(angle, cone.centre, cone.half));
            angles.length = 0;
            angles.push(...inside, cone.centre - cone.half, cone.centre + cone.half);
            apex = { x: origin.x, y: origin.y, angle: cone.centre - cone.half - epsilon };
        }

        const points = angles.map((angle) => {
            let best = { x: origin.x + Math.cos(angle) * reach, y: origin.y + Math.sin(angle) * reach, distance: reach };
            all.forEach((segment) => {
                const hit = rayHit(origin, angle, segment, reach);
                if (hit && hit.distance < best.distance) best = hit;
            });
            return { ...best, angle };
        }).sort((a, b) => a.angle - b.angle);



        return apex ? [apex, ...points] : points;
    }

    function pointInPolygon(point, polygon) {
        if (!polygon || polygon.length < 3) return false;
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
            const a = polygon[j], b = polygon[i];
            if (pointSegmentDistance(point, { x1: a.x, y1: a.y, x2: b.x, y2: b.y }) < 0.01) {
                return true;
            }
            const crosses = ((a.y > point.y) !== (b.y > point.y))
                && point.x < ((b.x - a.x) * (point.y - a.y)) / (b.y - a.y) + a.x;
            if (crosses) inside = !inside;
        }
        return inside;
    }

    function snapToGrid(point, scene) {
        const step = (scene?.scaledTileSize || 0) / SNAP_DIVISIONS;
        if (!(step > 0)) return point;
        return { x: Math.round(point.x / step) * step, y: Math.round(point.y / step) * step };
    }

    function nearestEndpoint(point, walls, tolerance, exclude = null) {
        let best = null, bestDistance = tolerance;
        walls.forEach((wall) => [
            { x: wall.x1, y: wall.y1 }, { x: wall.x2, y: wall.y2 },
        ].forEach((endpoint) => {
            if (exclude && sameNode(endpoint.x, endpoint.y, exclude)) return;
            const distance = Math.hypot(point.x - endpoint.x, point.y - endpoint.y);
            if (distance <= bestDistance) { best = endpoint; bestDistance = distance; }
        }));
        return best;
    }




    function segmentsCross(ax, ay, bx, by, cx, cy, dx, dy) {
        const side = (px, py, qx, qy, rx, ry) =>
            Math.sign((qx - px) * (ry - py) - (qy - py) * (rx - px));
        const d1 = side(ax, ay, bx, by, cx, cy);
        const d2 = side(ax, ay, bx, by, dx, dy);
        const d3 = side(cx, cy, dx, dy, ax, ay);
        const d4 = side(cx, cy, dx, dy, bx, by);
        return d1 !== d2 && d3 !== d4;
    }

    const sameNode = (x, y, node) => Math.hypot(x - node.x, y - node.y) <= NODE_EPSILON;
    const midpoint = (wall) => ({ x: (wall.x1 + wall.x2) / 2, y: (wall.y1 + wall.y2) / 2 });



    function moveNode(walls, from, to) {
        return walls.map((wall) => {
            const head = sameNode(wall.x1, wall.y1, from), tail = sameNode(wall.x2, wall.y2, from);
            if (!head && !tail) return wall;
            return {
                ...wall,
                ...(head ? { x1: to.x, y1: to.y } : null),
                ...(tail ? { x2: to.x, y2: to.y } : null),
            };
        });
    }

    function moveEndpoint(walls, wallId, endpoint, to) {
        return walls.map((wall) => wall.id !== wallId ? wall : {
            ...wall, [`x${endpoint}`]: to.x, [`y${endpoint}`]: to.y,
        });
    }

    function pointSegmentDistance(point, wall) {
        const dx = wall.x2 - wall.x1, dy = wall.y2 - wall.y1;
        const length2 = dx * dx + dy * dy;
        const t = length2 ? Math.max(0, Math.min(1, ((point.x - wall.x1) * dx + (point.y - wall.y1) * dy) / length2)) : 0;
        return Math.hypot(point.x - (wall.x1 + t * dx), point.y - (wall.y1 + t * dy));
    }


    function phaseOf(id) {
        let hash = 0;
        for (let i = 0; i < id.length; i += 1) hash = (hash * 31 + id.charCodeAt(i)) % 9973;
        return (hash / 9973) * Math.PI * 2;
    }






    const OCTAVES = [
        { period: 1300, weight: 0.5 },
        { period: 620, weight: 0.32 },
        { period: 350, weight: 0.18 },
    ];














    const FLICKER_PULSE = 0.1;
    const FLICKER_TORCH = 0.08;



    const SHAPE_CALM = 0.12;
    const SHAPE_LIVE = 0.3;




    function flame(now, phase, scale) {
        let value = 0;
        OCTAVES.forEach(({ period, weight }, index) => {
            value += weight * Math.sin((now * 2 * Math.PI) / (period * scale) + phase * (index + 1));
        });
        return 0.5 + 0.5 * value;
    }


    function breath(now, phase, period) {
        const wave = 0.5 + 0.5 * Math.sin((now * 2 * Math.PI) / period + phase);
        return wave * wave * (3 - 2 * wave);
    }



    const SPIN_SLOW = 0.02;
    const SPIN_FLAME = 0.05;
























    const EMISSIONS = {
        torch: {
            flicker: FLICKER_TORCH, shapeDepth: SHAPE_LIVE, spin: SPIN_FLAME,
            lobes: 6, lobeDepth: 0.26, jitter: 0.05,
            sources: [{ scale: 1, phase: 0, weight: 0.5 }, { scale: 0.62, phase: 2.1, weight: 0.4 }],
            brightness: (now, phase) => flame(now, phase, 1),
            shape: (now, phase) => flame(now, phase * 1.3 + 0.9, 0.7),
        },


        pulse: {
            flicker: FLICKER_PULSE, shapeDepth: SHAPE_LIVE, spin: 0,
            lobes: 0, lobeDepth: 0, jitter: 0,
            sources: [{ scale: 1, phase: 0, weight: 0.55 }],
            brightness: (now, phase) => breath(now, phase, 2800),
            shape: (now, phase) => breath(now, phase, 2800),
        },
    };


    const LIGHT_DEFAULTS = {
        none: { bright_radius: 2, dim_radius: 4, intensity: 0.85, color: "#ffd8a8", angle: 360 },
        torch: { bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#ff9a3c", angle: 360 },
        pulse: { bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#55aaff", angle: 360 },
    };










    const PARTICLE_KINDS = {
        smoke: {
            count: 22, life: 6200, rise: 2.4, spread: 0.5, drift: 0.55,
            size: 0.4, grow: 2.4, alpha: 0.28, blend: "normal", color: "#9aa3ad",
        },
        ember: {
            count: 26, life: 2300, rise: 2.2, spread: 0.42, drift: 0.3,
            size: 0.08, grow: 0.4, alpha: 0.95, blend: "add", color: "#ff9040",
        },


        dust: {
            count: 30, life: 8000, rise: 0.25, spread: 0.9, drift: 0.9,
            size: 0.05, grow: 0.1, alpha: 0.35, blend: "normal", color: "#d8cdb4",
        },
        arcane: {
            count: 16, life: 4200, rise: 0, orbit: 0.62, spread: 1, drift: 0,
            size: 0.07, grow: 0.2, alpha: 0.8, blend: "add", color: "#c9a6ff",
        },
        rain: {
            count: 46, life: 1350, rise: -3.8, spread: 0.95, drift: 0.08, wind: 0.7,
            size: 0.16, grow: 0, aspect: 0.12, alpha: 0.62, blend: "screen", color: "#9bc9e8", rotation: -0.18,
        },
        snow: {
            count: 38, life: 7200, rise: -0.75, spread: 1.1, drift: 0.85, wind: 0.22,
            size: 0.07, grow: 0.25, alpha: 0.8, blend: "normal", color: "#edf7ff",
        },
        firefly: {
            count: 18, life: 5600, rise: 0, orbit: 0.38, spread: 1, drift: 0.35,
            size: 0.055, grow: 0.15, alpha: 0.95, pulse: 3.5, blend: "add", color: "#ffe46b",
        },
        leaves: {
            count: 24, life: 6800, rise: -0.9, spread: 1.15, drift: 1.1, wind: 0.5,
            size: 0.12, grow: 0.05, aspect: 0.55, spin: 8, alpha: 0.72, blend: "normal", color: "#a87035",
        },
        bubbles: {
            count: 22, life: 5200, rise: 1.5, spread: 0.7, drift: 0.7,
            size: 0.08, grow: 0.65, alpha: 0.48, blend: "screen", color: "#8de8ff",
        },
        ash: {
            count: 34, life: 9000, rise: -0.35, spread: 1.25, drift: 1.0, wind: 0.35,
            size: 0.045, grow: 0.1, aspect: 0.65, spin: 5, alpha: 0.5, blend: "normal", color: "#77736e",
        },
        blood: {
            count: 28, life: 1800, burst: true, spread: 1.2, gravity: 1.9, wind: 0.08,
            size: 0.07, grow: 0.35, aspect: 0.5, spin: 7, alpha: 0.9, blend: "normal", color: "#a10f20",
        },
        runes: {
            count: 12, life: 6400, rise: 0, orbit: 0.42, spread: 0.82, drift: 0,
            size: 0.11, grow: 0, aspect: 0.35, spin: -2, pulse: 2.2, alpha: 0.9, blend: "add", color: "#69a7ff",
        },
    };

    const PARTICLE_DEFAULTS = {
        smoke: { scale: 3, density: 0.6, color: "#9aa3ad" },
        ember: { scale: 2, density: 0.5, color: "#ff9040" },
        dust: { scale: 6, density: 0.45, color: "#d8cdb4" },
        arcane: { scale: 2.5, density: 0.6, color: "#c9a6ff" },
        rain: { scale: 8, density: 0.7, color: "#9bc9e8" },
        snow: { scale: 8, density: 0.65, color: "#edf7ff" },
        firefly: { scale: 5, density: 0.55, color: "#ffe46b" },
        leaves: { scale: 7, density: 0.55, color: "#a87035" },
        bubbles: { scale: 4, density: 0.6, color: "#8de8ff" },
        ash: { scale: 8, density: 0.6, color: "#77736e" },
        blood: { scale: 3, density: 0.7, color: "#a10f20" },
        runes: { scale: 3, density: 0.65, color: "#69a7ff" },
    };









    function particlesOf(emitter, now, cellSize) {
        const spec = PARTICLE_KINDS[emitter.kind];
        if (!spec || !(cellSize > 0)) return [];
        if (emitter.enabled === false || emitter.enabled === 0) return [];

        const scale = Math.max(0.5, Number(emitter.scale) || 1);
        const density = Math.max(0, Math.min(1, Number(emitter.density ?? 0.6)));
        const count = Math.max(1, Math.round(spec.count * density));
        const seed = phaseOf(emitter.id || "");
        const reach = cellSize * scale;

        const out = [];
        for (let index = 0; index < count; index += 1) {


            const own = (index * 0.6180339887 + seed) % 1;
            const age = ((now / spec.life + own) % 1 + 1) % 1;

            const around = own * Math.PI * 2;
            const sway = Math.sin(now / 900 + around * 3) * spec.drift;
            const orbit = spec.orbit || 0;
            const radial = spec.burst
                ? { x: Math.cos(around) * spec.spread * age,
                    y: Math.sin(around) * spec.spread * age + (spec.gravity || 0) * age * age }
                : orbit
                ? { x: Math.cos(around + now / 1000 * orbit) * spec.spread,
                    y: Math.sin(around + now / 1000 * orbit) * spec.spread * 0.6 }
                : { x: Math.sin(around) * spec.spread * (0.35 + age) + sway * age,
                    y: -spec.rise * age };
            radial.x += (spec.wind || 0) * age;


            const fade = Math.sin(age * Math.PI);
            out.push({
                age,
                x: emitter.x + radial.x * reach,
                y: emitter.y + radial.y * reach,
                size: spec.size * (1 + spec.grow * age) * reach,
                alpha: spec.alpha * fade * (spec.pulse ? 0.55 + 0.45 * Math.sin(now / 1000 * spec.pulse + around * 5) : 1),
                tint: emitter.color || spec.color,
                blend: spec.blend,
                aspect: spec.aspect || 1,
                rotation: spec.rotation ?? (around + age * (spec.spin || (orbit ? 2 : 0.8))),
            });
        }
        return out;
    }



    function jitterOf(light, now, radius) {
        const emission = EMISSIONS[light.animation];
        if (!emission?.jitter) return { x: 0, y: 0 };
        const phase = phaseOf(light.id || "");
        const reach = radius * emission.jitter;



        return {
            x: Math.sin(now / 340 + phase) * reach,
            y: Math.sin(now / 470 + phase * 2) * reach,
        };
    }

    function lerpHex(from, to, amount) {
        const parse = (hex) => {
            const value = parseInt(String(hex || "").replace("#", ""), 16);
            return Number.isFinite(value) ? value : 0xffd8a8;
        };
        const a = parse(from), b = parse(to);
        const mix = (shift) => {
            const channel = Math.round(
                ((a >> shift) & 0xff) + (((b >> shift) & 0xff) - ((a >> shift) & 0xff)) * amount,
            );
            return Math.max(0, Math.min(255, channel));
        };
        return `#${((mix(16) << 16) | (mix(8) << 8) | mix(0)).toString(16).padStart(6, "0")}`;
    }


    function tintOf(light, now) {
        const emission = EMISSIONS[light.animation];
        const base = light.color || "#ffd8a8";
        if (!emission?.color2) return base;
        const phase = phaseOf(light.id || "");
        return lerpHex(base, emission.color2, 0.5 + 0.5 * Math.sin(now / 2600 + phase));
    }


    function sourcesOf(light, now, dim, bright) {
        const emission = EMISSIONS[light.animation];
        const layers = emission?.sources || [{ scale: 1, phase: 0, weight: 0.5 }];
        const phase = phaseOf(light.id || "");
        return layers.map((layer, index) => {
            const localPhase = phase + layer.phase;
            return {
                radius: dim * layer.scale,
                weight: layer.weight,

                wobble: emission
                    ? 1 + emission.shapeDepth * (emission.shape(now, localPhase) - 0.5) * 2
                    : 1,




                offsetX: emission ? Math.sin(now / (380 + index * 47) + localPhase) * dim * 0.025 : 0,
                offsetY: emission ? Math.sin(now / (530 + index * 61) + localPhase * 1.7) * dim * 0.018 : 0,
            };
        }).concat(bright > 0

            ? [{ radius: bright, weight: 0.45, core: true, wobble: 1, offsetX: 0, offsetY: 0 }]
            : []);
    }



    function animationFactor(light, now) {
        const emission = EMISSIONS[light.animation];
        if (!emission) return 1;
        const phase = phaseOf(light.id || "");
        return (1 - emission.flicker) + emission.flicker * emission.brightness(now, phase);
    }


    function shapeFactor(light, now) {
        const emission = EMISSIONS[light.animation];
        if (!emission) return 1;
        const phase = phaseOf(light.id || "");
        return 1 + emission.shapeDepth * (emission.shape(now, phase) - 0.5) * 2;
    }

    function spinAngle(light, now) {
        const emission = EMISSIONS[light.animation];
        if (!emission?.spin) return 0;
        return (now / 1000) * emission.spin * Math.PI * 2 + phaseOf(light.id || "");
    }


    function lobesOf(light) {
        const emission = EMISSIONS[light.animation];
        return { lobes: emission?.lobes || 0, depth: emission?.lobeDepth || 0 };
    }

    class LightingController {
        constructor(canvas) {
            this.canvas = canvas;
            this.roomId = canvas.dataset.roomId;
            this.isGm = canvas.closest("[data-map-viewport]")?.dataset.lightingGm === "true";
            this.isStreamer = document.body?.dataset?.streamerMode === "true";
            this.walls = [];
            this.lights = [];



            this.emitters = [];


            this.shaders = [];
            this.shaderPreviewCanonical = new Map();
            this.shaderPreviewFrame = null;
            this.shaderPreviewPending = new Map();
            this.transientShaderPreview = null;







            this.picks = { wall: new Set(), light: new Set(), emitter: new Set(), shader: new Set() };
            this.marquee = null;
            this.selectedShader = "";
            this.shaderDrag = null;
            this.shaderResize = null;
            this.start = null;
            this.preview = null;
            this.selected = "";
            this.selectedLight = "";
            this.selectedEmitter = "";
            this.componentDrag = null;
            this.drawingPointerId = null;
            this.downClient = null;
            this.nodeDrag = null;
            this.lightDrag = null;
            this.emitterDrag = null;
            this.sceneId = "";


            this.geometryStamp = 0;
            this.polygonCache = new Map();
            this.probeReach = new Map();
            this.wallIndex = null;
            this.visibleDoorIds = new Set();
            this.bind();
            this.syncScene();
        }

        scene() { return window.GravewrightMap?.sceneDataFor?.(this.canvas) || null; }




        syncScene() {
            const sceneId = this.scene()?.id || "";
            if (sceneId === this.sceneId) return;
            this.sceneId = sceneId;
            this.walls = [];
            this.lights = [];
            this.selected = "";
            this.selectedLight = "";
            this.cancelDrawing();
            this.invalidateGeometry();
            if (sceneId) void this.refresh(sceneId);
        }

        invalidateGeometry() {
            this.geometryStamp += 1;
            this.polygonCache.clear();
            this.wallIndex = null;
        }

        state() { return window.GravewrightMap?.stateFor?.(this.canvas); }
        world(event) {
            const point = window.GravewrightMap?.worldFromScreen?.(this.canvas, event.clientX, event.clientY);
            if (!point) return null;
            return { x: point.worldX, y: point.worldY };
        }



        target(event, exclude = null) {
            const point = this.world(event);
            if (!point) return point;
            const zoom = Math.max(0.001, this.state()?.zoom || 1);
            const magnet = nearestEndpoint(point, this.walls, ENDPOINT_SNAP_PX / zoom, exclude);
            if (magnet) return magnet;
            return event.shiftKey ? snapToGrid(point, this.scene()) : point;
        }

        zoom() { return Math.max(0.001, this.state()?.zoom || 1); }

        nodeAt(point, kind = null) {
            const walls = kind ? this.walls.filter((wall) => wall.kind === kind) : this.walls;
            return nearestEndpoint(point, walls, NODE_GRAB_PX / this.zoom());
        }

        endpointAt(point, kind = null) {
            const tolerance = NODE_GRAB_PX / this.zoom();
            const allowed = this.walls.filter((wall) => !kind || wall.kind === kind);
            const selected = allowed.filter((wall) => this.picked("wall", wall.id));
            const candidates = selected.length ? selected : allowed.slice().reverse();
            let best = null, bestDistance = tolerance;
            candidates.forEach((wall) => [1, 2].forEach((endpoint) => {
                const x = wall[`x${endpoint}`], y = wall[`y${endpoint}`];
                const distance = Math.hypot(point.x - x, point.y - y);
                if (distance < bestDistance) {
                    best = { x, y, wallId: wall.id, endpoint };
                    bestDistance = distance;
                }
            }));
            return best;
        }



        doorAt(point) {
            const tolerance = DOOR_GRAB_PX / this.zoom();
            let best = null, bestDistance = tolerance;
            this.walls.forEach((wall) => {
                if (wall.kind !== "door") return;
                if (activeLayer !== EDIT_LAYERS.door && this.visibleDoorIds.size && !this.visibleDoorIds.has(wall.id)) return;
                const centre = midpoint(wall);
                const distance = Math.min(
                    Math.hypot(point.x - centre.x, point.y - centre.y),
                    pointSegmentDistance(point, wall),
                );
                if (distance <= bestDistance) { best = wall; bestDistance = distance; }
            });
            return best;
        }

        lightAt(point) {
            const tolerance = LIGHT_GRAB_PX / this.zoom();
            let best = null, bestDistance = tolerance;
            this.lights.forEach((light) => {
                const distance = Math.hypot(point.x - light.x, point.y - light.y);
                if (distance <= bestDistance) { best = light; bestDistance = distance; }
            });
            return best;
        }



        renderWalls() {
            if (!this.nodeDrag) return this.walls;
            return this.nodeDrag.detached
                ? moveEndpoint(this.walls, this.nodeDrag.wallId, this.nodeDrag.endpoint, this.nodeDrag.to)
                : moveNode(this.walls, this.nodeDrag.from, this.nodeDrag.to);
        }

        renderLights() {
            const drag = this.lightDrag;
            if (!drag) return this.lights;
            return this.lights.map((light) => light.id === drag.id ? { ...light, x: drag.to.x, y: drag.to.y } : light);
        }

        blockers(walls, channel = "vision") {
            return walls.filter((wall) => (wall.kind !== "door" || wall.door_state !== "open")
                && (wall.behavior?.[channel] || "block") === "block");
        }




        blocksMovement(from, to) {
            return this.blockers(this.walls, "movement").some((wall) => segmentsCross(
                from.x, from.y, to.x, to.y,
                wall.x1, wall.y1, wall.x2, wall.y2,
            ));
        }



        wallIndexFor(blockers, scene) {
            if (this.wallIndex && this.wallIndex.stamp === this.geometryStamp) return this.wallIndex;
            const size = Math.max(1, (scene.scaledTileSize || 50) * WALL_CHUNK_TILES);
            const buckets = new Map();
            blockers.forEach((wall) => {
                const cx0 = Math.floor(Math.min(wall.x1, wall.x2) / size);
                const cx1 = Math.floor(Math.max(wall.x1, wall.x2) / size);
                const cy0 = Math.floor(Math.min(wall.y1, wall.y2) / size);
                const cy1 = Math.floor(Math.max(wall.y1, wall.y2) / size);
                for (let cx = cx0; cx <= cx1; cx += 1) {
                    for (let cy = cy0; cy <= cy1; cy += 1) {
                        const key = `${cx}:${cy}`;
                        const bucket = buckets.get(key);
                        if (bucket) bucket.push(wall);
                        else buckets.set(key, [wall]);
                    }
                }
            });
            this.wallIndex = { stamp: this.geometryStamp, size, buckets, total: blockers.length };
            return this.wallIndex;
        }



        blockersNear(blockers, scene, origin, radius) {
            if (!(radius > 0)) return blockers;
            const { size, buckets } = this.wallIndexFor(blockers, scene);
            const cx0 = Math.floor((origin.x - radius) / size), cx1 = Math.floor((origin.x + radius) / size);
            const cy0 = Math.floor((origin.y - radius) / size), cy1 = Math.floor((origin.y + radius) / size);
            const seen = new Set();
            const near = [];
            for (let cx = cx0; cx <= cx1; cx += 1) {
                for (let cy = cy0; cy <= cy1; cy += 1) {
                    const bucket = buckets.get(`${cx}:${cy}`);
                    if (!bucket) continue;
                    bucket.forEach((wall) => {
                        if (seen.has(wall)) return;
                        seen.add(wall);
                        near.push(wall);
                    });
                }
            }
            return near;
        }





        unboundedPolygon(origin, blockers, scene, key = "") {
            const diagonal = Math.hypot(scene.width, scene.height);
            const step = Math.max(1, (scene.scaledTileSize || 50) * PROBE_START_TILES);




            const first = Math.min(diagonal, this.probeReach.get(key) || step);
            for (let reach = first; ; reach *= 2) {
                const capped = Math.min(reach, diagonal);
                const exhausted = capped >= diagonal;
                const near = exhausted ? blockers : this.blockersNear(blockers, scene, origin, capped);
                const polygon = visibilityPolygon(origin, near, scene.width, scene.height, capped, false);

                const open = polygon.some((point) => point.distance >= capped - 1e-6);
                if (!open || exhausted) {
                    if (key) {
                        const reached = polygon.reduce((max, point) => Math.max(max, point.distance), 0);
                        this.probeReach.set(key, Math.min(capped, Math.max(step, reached * 1.5)));
                    }
                    return polygon;
                }
            }
        }

        cachedPolygon(key, origin, blockers, scene, radius) {


            const cone = coneOf(origin);
            const shape = cone ? `${Math.round(cone.centre * 180 / Math.PI)}/${Math.round(cone.half * 180 / Math.PI)}` : "o";
            const cacheKey = `${key}:${this.geometryStamp}:${Math.round(origin.x)}:${Math.round(origin.y)}:${Math.round(radius)}:${shape}`;
            const cached = this.polygonCache.get(cacheKey);
            if (cached) return cached;
            const polygon = radius > 0
                ? visibilityPolygon(origin, this.blockersNear(blockers, scene, origin, radius), scene.width, scene.height, radius, true, cone)
                : this.unboundedPolygon(origin, blockers, scene, key);
            this.polygonCache.set(cacheKey, polygon);
            return polygon;
        }

        controlsToken(token) {
            const userId = currentUserId();
            return Boolean(userId) && (token.controlled_by_user_ids || []).includes(userId);
        }






        visionSources({ all: everyone = false } = {}) {
            const store = window.GravewrightMap?.tokenStoreFor?.(this.canvas);
            const scene = this.scene();
            if (!store || !scene) return [];
            const size = scene.scaledTileSize || 50;
            const all = [...store.values()].filter((token) => everyone || token.vision_enabled !== false);
            let chosen;
            if (everyone) {
                chosen = all;
            } else if (this.isStreamer) {
                chosen = all;
            } else if (this.isGm) {

                const selected = selectedTokenId ? all.find((token) => token.token_id === selectedTokenId) : null;
                chosen = selected ? [selected] : all.filter((token) => (token.controlled_by_user_ids || []).length > 0);
            } else {
                const owned = all.filter((token) => this.controlsToken(token));
                const selected = selectedTokenId ? owned.find((token) => token.token_id === selectedTokenId) : null;
                chosen = selected ? [selected] : owned;
            }


            const drag = window.GravewrightMap?.activeTokenDrag?.();
            const dragged = drag && drag.canvas === this.canvas ? drag : null;
            const liveCell = (token) => {
                if (!dragged) return { x: token.grid_x, y: token.grid_y };
                if (dragged.positions?.[token.token_id]) {
                    const pos = dragged.positions[token.token_id];
                    return { x: pos.gridX, y: pos.gridY };
                }
                if (dragged.tokenId === token.token_id) {
                    return { x: dragged.currentGridX, y: dragged.currentGridY };
                }
                return { x: token.grid_x, y: token.grid_y };
            };

            return chosen.map((token) => ({
                id: token.token_id,
                x: (liveCell(token).x + (token.width_cells || 1) / 2) * size,
                y: (liveCell(token).y + (token.height_cells || 1) / 2) * size,
                radius: Math.max(0, (token.vision_range || 0) * size),
            }));
        }

        pixiState() {
            this.syncScene();
            const scene = this.scene();



            const mode = window.GravewrightVisionMode?.current?.() || "cinematic";
            const classic = mode === "classic";
            const shown = (layer) => window.GravewrightTools?.isLayerVisible?.(layer, this.roomId) !== false;



            const lightingVisible = shown(EDIT_LAYERS.light);
            const effectsVisible = shown(EDIT_LAYERS.particles);
            const wallsVisible = shown(EDIT_LAYERS.wall);
            const visible = lightingVisible || effectsVisible || wallsVisible;
            const walls = this.renderWalls();
            const lights = this.renderLights();

            const editing = this.isGm && activeLayer === EDIT_LAYERS.wall && wallsVisible;
            const editingLights = this.isGm && activeLayer === EDIT_LAYERS.light && lightingVisible;
            if (!scene) {
                return { mode, visible, editing, editingLights, editingParticles: false, editingShaders: false, shaders: [], shaderMarkers: [], darkness: 0, sceneDarkness: 0, geometryStamp: this.geometryStamp, particleClouds: [], walls, lights: [], visionPolygons: [], visionRims: [], visionPreview: null, doors: [], selected: this.selected, selectedLight: this.selectedLight, picked: this.picks, marquee: null, start: this.start, preview: this.preview, nodesGrabbable: false, draggingNode: null };
            }

            const playerView = Boolean(window.GravewrightMap?.isPlayerView?.());
            const sources = this.visionSources();


            const previewingToken = this.isGm && Boolean(selectedTokenId)
                && sources.length === 1 && sources[0].id === selectedTokenId;
            const visionLimited = !this.isGm || playerView || previewingToken;

            const darkness = lightingVisible
                ? (scene.darkness || 0) * (visionLimited ? 1 : GM_DARKNESS_PREVIEW)
                : 0;






            const sceneDarkness = scene.darkness || 0;
            const visionBlockers = this.blockers(walls, "vision");
            const lightBlockers = this.blockers(walls, "light");
            const size = scene.scaledTileSize || 50;
            const now = performance.now();

            const litPolygons = (lightingVisible ? lights : [])
                .filter((light) => light.enabled !== false && light.enabled !== 0).map((light) => {
                const dim = Math.max(0, (light.dim_radius || 0) * size);

                const bright = Math.max(0, Math.min(dim, (light.bright_radius || 0) * size));
                return {
                    id: light.id,
                    x: light.x,
                    y: light.y,
                    color: light.color || "#ffd8a8",



                    intensity: Math.max(0, Math.min(1, light.intensity ?? 1)),



                    angle: Number(light.angle ?? 360),
                    rotation: Number(light.rotation ?? 0),
                    alpha: Math.max(0, Math.min(1, (light.intensity ?? 1)
                        * (classic ? 1 : animationFactor(light, now)))),
                    bright,
                    dim,



                    animation: classic ? "none" : (light.animation || "none"),




                    wobble: classic ? 1 : shapeFactor(light, now),
                    spin: classic ? 0 : spinAngle(light, now),



                    offset: classic ? { x: 0, y: 0 } : jitterOf(light, now, bright || dim),

                    tint: classic ? (light.color || "#ffd8a8") : tintOf(light, now),



                    sources: classic
                        ? [{ radius: dim, weight: 0.5, wobble: 1 }].concat(
                            bright > 0 ? [{ radius: bright, weight: 0.45, core: true, wobble: 1 }] : [])
                        : sourcesOf(light, now, dim, bright),
                    ...(classic ? { lobes: 0, lobeDepth: 0 } : (() => {
                        const shape = lobesOf(light);
                        return { lobes: shape.lobes, lobeDepth: shape.depth };
                    })()),
                    polygon: dim > 0 ? this.cachedPolygon(`light-${light.id}`, light, lightBlockers, scene, dim) : [],
                };
            });

            const visionPolygons = visionLimited
                ? sources.map((source) => this.cachedPolygon(`vision-${source.id}`, source, visionBlockers, scene, source.radius))
                : [];
            const renderedVisionPolygons = lightingVisible ? visionPolygons : [];

            const doorVisionPolygons = visionLimited
                ? visionPolygons
                : sources.map((source) => this.cachedPolygon(`vision-${source.id}`, source, visionBlockers, scene, source.radius));








            const visionRims = lightingVisible && visionLimited
                ? sources.map((source) => ({ x: source.x, y: source.y, radius: source.radius }))
                : [];



            const preview = visionPreviewTokenId
                ? this.visionSources({ all: true }).find((source) => source.id === visionPreviewTokenId)
                : null;
            const visionPreview = preview
                ? { ...preview, polygon: this.cachedPolygon(`preview-${preview.id}`, preview, visionBlockers, scene, preview.radius) }
                : null;



            const doors = walls.filter((wall) => wallsVisible && wall.kind === "door" && (
                editing || doorVisionPolygons.some((polygon) => pointInPolygon(midpoint(wall), polygon))
            ));
            this.visibleDoorIds = new Set(doors.map((door) => door.id));

            return {
                mode,
                visible,
                editing,
                darkness,
                sceneDarkness: lightingVisible ? sceneDarkness : 0,





                geometryStamp: this.geometryStamp,






                editingParticles: this.isGm && activeLayer === EDIT_LAYERS.particles
                    && effectsVisible,
                editingLights,







                shaders: (effectsVisible && !classic
                    && window.GravewrightShaderPreference?.enabled?.() !== false
                    ? [...(this.shaders || []), ...(this.transientShaderPreview ? [this.transientShaderPreview] : [])] : [])
                    .filter((shader) => shader.enabled && shader.source)
                    .map((shader) => {


                        const dragging = this.shaderDrag?.id === shader.id ? this.shaderDrag.to : null;
                        const x = dragging?.x ?? shader.x;
                        const y = dragging?.y ?? shader.y;


                        const radiusWorld = Number(shader.radius || 0) * size;
                        return {
                            ...shader,
                            x, y, radiusWorld,











                            occlusionStamp: this.geometryStamp,
                            occlusion: radiusWorld > 0
                                ? this.cachedPolygon(`shader-${shader.id}`, { x, y }, lightBlockers, scene, radiusWorld)
                                : null,
                        };
                    }),


                editingShaders: this.isGm && activeLayer === EDIT_LAYERS.particles
                    && shown(EDIT_LAYERS.particles),
                shaderMarkers: (this.isGm && activeLayer === EDIT_LAYERS.particles
                    ? (this.shaders || []) : []).map((shader) => {
                        const dragging = this.shaderDrag?.id === shader.id ? this.shaderDrag.to : null;
                        return {
                            id: shader.id,
                            name: shader.name || "",
                            x: dragging?.x ?? shader.x,
                            y: dragging?.y ?? shader.y,
                            radiusWorld: Number(shader.radius || 0) * size,
                            color: shader.color,
                            enabled: Boolean(shader.enabled),
                            selected: this.picked("shader", shader.id),
                            resizeHandle: this.picked("shader", shader.id) && Number(shader.radius || 0) > 0,
                        };
                    }),
                particleClouds: (effectsVisible ? (this.emitters || []) : []).map((emitter) => {



                    const dragging = this.emitterDrag?.id === emitter.id ? this.emitterDrag.to : null;
                    const live = { ...emitter, x: dragging?.x ?? emitter.x, y: dragging?.y ?? emitter.y };
                    return {
                    id: emitter.id,
                    selected: this.picked("emitter", emitter.id),
                    x: live.x,
                    y: live.y,
                    kind: emitter.kind,





                    particles: particlesOf(live, now, size),
                    };
                }),
                walls,
                lights: litPolygons,
                visionPolygons: renderedVisionPolygons,
                visionRims,
                visionPreview,
                doors,
                selected: this.selected,
                selectedLight: this.selectedLight,


                picked: this.picks,
                marquee: this.marquee,
                start: this.start,
                preview: this.preview,
                nodesGrabbable: editing && ["select", "wall", "door"].includes(window.GravewrightTools?.activeTool),
                draggingNode: this.nodeDrag ? this.nodeDrag.to : null,
            };
        }

        animated() {

            if (window.GravewrightVisionMode?.isClassic?.()) return false;
            const scene = this.scene();
            if (!scene) return false;

            const layerVisible =
                window.GravewrightTools?.isLayerVisible?.("lighting", this.roomId) !== false;




            const flames = layerVisible && this.lights.some(
                (light) => light.enabled !== false && light.animation && light.animation !== "none",
            );


            const veil = scene.darkness > 0
                && this.visionSources().some((source) => source.radius > 0);



            const clouds = layerVisible
                && (this.emitters || []).some((emitter) => emitter.enabled !== false);

            return flames || veil || clouds;
        }

        async refresh(sceneId = this.scene()?.id || "") {
            if (!sceneId) {
                (this.shaders || []).forEach((shader) => window.GravewrightShaderEffects?.invalidate?.(shader.id));
                this.walls = [];
                this.lights = [];
                this.emitters = [];
                this.shaders = [];
                this.invalidateGeometry();
                redraw();
                return;
            }
            const query = `?campaign_id=${encodeURIComponent(this.roomId)}`;


            const load = async (path) => {
                try {
                    const response = await fetch(`${path}/${encodeURIComponent(sceneId)}${query}`, { credentials: "same-origin", headers: { Accept: "application/json" } });
                    if (!response.ok) {
                        console.warn(`Iluminacao: ${path} respondeu ${response.status}`);
                        return null;
                    }
                    return await response.json();
                } catch (error) {
                    console.warn(`Iluminacao: ${path} falhou`, error);
                    return null;
                }
            };
            const [wallData, lightData, particleData, shaderData] = await Promise.all([
                load("/game/walls"), load("/game/lights"), load("/game/particles"), load("/game/shaders"),
            ]);
            if (this.sceneId !== sceneId) return;
            if (wallData) this.walls = wallData.walls || [];
            if (lightData) this.lights = lightData.lights || [];
            if (particleData) this.emitters = particleData.emitters || [];
            if (shaderData) {
                const nextShaders = shaderData.shaders || [];
                const nextById = new Map(nextShaders.map((shader) => [shader.id, shader]));
                (this.shaders || []).forEach((shader) => {
                    const next = nextById.get(shader.id);
                    if (!next || String(next.source || "") !== String(shader.source || "")) {
                        window.GravewrightShaderEffects?.invalidate?.(shader.id);
                    }
                });
                this.shaders = nextShaders;
            }
            this.invalidateGeometry();
            redraw();
        }

        hit(point, kind = null) {
            const tolerance = 10 / this.zoom();
            return this.walls.slice().reverse().find((wall) =>
                (!kind || wall.kind === kind) && pointSegmentDistance(point, wall) <= tolerance) || null;
        }

        diagnostics() {
            return {
                build: BUILD,
                roomId: this.roomId,
                isGm: this.isGm,
                activeLayer,
                activeTool: window.GravewrightTools?.activeTool,
                sceneId: this.scene()?.id || null,
                trackedSceneId: this.sceneId || null,
                darkness: this.scene()?.darkness ?? null,
                boundTo: this.canvas.closest("[data-map-viewport]") ? "viewport" : "NAO LIGADO",
                start: this.start,
                preview: this.preview,
                walls: this.walls.length,
                lights: this.lights.length,
                visionSources: this.visionSources().length,

                registered: controllers.get(this.canvas) === this,
                layerVisible: window.GravewrightTools?.isLayerVisible?.("lighting", this.roomId) !== false,
                doors: this.walls.filter((wall) => wall.kind === "door").length,
                doorStates: this.walls.filter((wall) => wall.kind === "door").map((wall) => wall.door_state),
            };
        }

        warnNoScene() {
            console.warn("Iluminacao: sem cena ativa para receber paredes", this.diagnostics());
            toast("Não há cena ativa para receber a parede.");
        }

        async create(end, kind, chain = false) {
            const scene = this.scene(), start = this.start;
            if (!scene) {
                this.cancelDrawing();
                this.warnNoScene();
                redraw();
                return;
            }
            if (!start) {
                console.warn("Iluminacao: segmento descartado (ponto inicial ausente)", this.diagnostics());
                return;
            }
            if (Math.hypot(end.x - start.x, end.y - start.y) < 2) {
                console.warn("Iluminacao: segmento descartado (comprimento zero apos encaixe)", { start, end });
                return;
            }
            const temporaryId = `pending-${Date.now()}-${Math.random()}`;
            const temporary = { id: temporaryId, kind, door_state: "closed", x1: start.x, y1: start.y, x2: end.x, y2: end.y };
            this.walls.push(temporary);
            this.start = kind === "wall" && chain ? end : null;
            this.preview = null;
            this.invalidateGeometry();
            redraw();
            try {
                const result = await post("/game/walls", { campaign_id: this.roomId, scene_id: scene.id, kind, x1: start.x, y1: start.y, x2: end.x, y2: end.y });
                if (this.sceneId !== scene.id) return;
                const index = this.walls.findIndex((wall) => wall.id === temporaryId);
                if (index >= 0) this.walls[index] = result.wall;
                else if (result.wall && !this.walls.some((wall) => wall.id === result.wall.id)) this.walls.push(result.wall);
                this.invalidateGeometry();
                redraw();
            } catch (error) {
                if (this.sceneId !== scene.id) return;
                this.walls = this.walls.filter((wall) => wall.id !== temporaryId);
                this.start = start;
                this.preview = end;
                this.invalidateGeometry();
                redraw();
                console.error("Dynamic lighting segment creation failed", error);
                toast("Não foi possível salvar a parede ou porta.");
            }
        }

        async setDoor(door, next) {
            const previous = door.door_state;
            if (next === previous) return;
            door.door_state = next;
            this.invalidateGeometry();
            redraw();
            try {
                const result = await post("/game/walls/door-state", { campaign_id: this.roomId, wall_id: door.id, door_state: next });
                const index = this.walls.findIndex((wall) => wall.id === door.id);
                if (index >= 0 && result.wall) this.walls[index] = result.wall;
                this.invalidateGeometry();
                redraw();
            } catch (error) {
                door.door_state = previous;
                this.invalidateGeometry();
                redraw();
                const locked = String(error.message || "").includes("locked");
                console.error("Dynamic lighting door state change failed", error);
                toast(locked ? "Esta porta está trancada." : "Não foi possível mudar o estado da porta.");
            }
        }

        cycleDoor(door) {
            return this.setDoor(door, DOOR_CYCLE[door.door_state] || "closed");
        }



        operateDoor(door, { lock = false } = {}) {
            if (lock) {
                if (!this.isGm) return;
                return this.setDoor(door, door.door_state === "locked" ? "closed" : "locked");
            }
            if (door.door_state === "locked") {
                toast("Esta porta está trancada.");
                return;
            }
            return this.setDoor(door, door.door_state === "open" ? "closed" : "open");
        }








        emitterAt(point) {
            const tolerance = LIGHT_GRAB_PX / this.zoom();
            let best = null, bestDistance = tolerance;
            (this.emitters || []).forEach((emitter) => {
                const distance = Math.hypot(point.x - emitter.x, point.y - emitter.y);
                if (distance <= bestDistance) { best = emitter; bestDistance = distance; }
            });
            return best;
        }

        async placeEmitter(point) {
            const scene = this.scene();
            if (!scene) return this.warnNoScene();
            const chosen = String(window.GravewrightTools?.activeSubTool || "");
            const kind = PARTICLE_KINDS[chosen] ? chosen : "smoke";
            const preset = PARTICLE_DEFAULTS[kind];

            const temporaryId = `pending-emitter-${Date.now()}`;
            const temporary = { id: temporaryId, x: point.x, y: point.y, kind, enabled: 1, ...preset };
            this.emitters.push(temporary);
            redraw();
            try {
                const result = await post("/game/particles", {
                    campaign_id: this.roomId, scene_id: scene.id,
                    x: point.x, y: point.y, kind,
                    scale: preset.scale, density: preset.density, color: preset.color,
                });
                if (this.sceneId !== scene.id) return;
                const index = this.emitters.findIndex((emitter) => emitter.id === temporaryId);
                if (index >= 0 && result.emitter) this.emitters[index] = result.emitter;
                this.selectedEmitter = result.emitter?.id || "";
                redraw();
            } catch (error) {
                if (this.sceneId !== scene.id) return;
                this.emitters = this.emitters.filter((emitter) => emitter.id !== temporaryId);
                redraw();
                console.error("Scene particle emitter creation failed", error);
                toast("Não foi possível criar o emissor de partículas.");
            }
        }




        get selected() { return this.lastPick("wall"); }
        set selected(id) { this.setPick("wall", id); }
        get selectedLight() { return this.lastPick("light"); }
        set selectedLight(id) { this.setPick("light", id); }
        get selectedEmitter() { return this.lastPick("emitter"); }
        set selectedEmitter(id) { this.setPick("emitter", id); }
        get selectedShader() { return this.lastPick("shader"); }
        set selectedShader(id) { this.setPick("shader", id); }

        lastPick(kind) {
            const set = this.picks?.[kind];
            if (!set || !set.size) return "";


            let last = "";
            set.forEach((id) => { last = id; });
            return last;
        }

        setPick(kind, id) {
            const set = this.picks?.[kind];
            if (!set) return;
            set.clear();
            if (id) set.add(id);
        }


        pick(kind, id, additive) {
            if (!id) return;
            const set = this.picks[kind];
            if (!additive) {
                Object.values(this.picks).forEach((other) => other.clear());
                set.add(id);
                return;
            }
            if (set.has(id)) set.delete(id); else set.add(id);
        }

        picked(kind, id) { return Boolean(this.picks?.[kind]?.has(id)); }
        pickedIds(kind) { return [...(this.picks?.[kind] || [])]; }
        pickCount() { return Object.values(this.picks).reduce((total, set) => total + set.size, 0); }
        clearPicks() { Object.values(this.picks).forEach((set) => set.clear()); }

        scopePicksForTool(tool) {
            if (tool === "select") return;
            const ownedKind = { wall: "wall", door: "wall", light: "light", particles: "emitter", shader: "shader" }[tool];
            Object.entries(this.picks).forEach(([kind, ids]) => {
                if (kind !== ownedKind) ids.clear();
            });
            if (tool === "wall" || tool === "door") {
                const allowed = new Set(this.walls.filter((wall) => wall.kind === tool).map((wall) => wall.id));
                [...this.picks.wall].forEach((id) => { if (!allowed.has(id)) this.picks.wall.delete(id); });
            }
        }




        pickInside(box, additive) {
            const inside = (x, y) => x >= box.x0 && x <= box.x1 && y >= box.y0 && y <= box.y1;
            if (!additive) this.clearPicks();
            if (activeLayer === EDIT_LAYERS.wall) {
                (this.walls || []).forEach((wall) => {


                    if (inside(wall.x1, wall.y1) && inside(wall.x2, wall.y2)) this.picks.wall.add(wall.id);
                });
            }
            if (activeLayer === EDIT_LAYERS.light) {
                (this.lights || []).forEach((light) => {
                    if (inside(light.x, light.y)) this.picks.light.add(light.id);
                });
            }
            if (activeLayer === EDIT_LAYERS.particles) {
                (this.emitters || []).forEach((emitter) => {
                    if (inside(emitter.x, emitter.y)) this.picks.emitter.add(emitter.id);
                });
                (this.shaders || []).forEach((shader) => {
                    if (inside(shader.x, shader.y)) this.picks.shader.add(shader.id);
                });
            }
            return this.pickCount();
        }




        shaderAt(point) {
            const tolerance = LIGHT_GRAB_PX / this.zoom();
            let best = null, bestDistance = tolerance;
            (this.shaders || []).forEach((shader) => {
                const distance = Math.hypot(point.x - shader.x, point.y - shader.y);
                if (distance <= bestDistance) { best = shader; bestDistance = distance; }
            });
            return best;
        }

        shaderResizeAt(point) {
            const size = this.scene()?.scaledTileSize || 50;
            const tolerance = LIGHT_GRAB_PX / this.zoom();
            return (this.shaders || []).find((shader) => {
                if (!this.picked("shader", shader.id) || Number(shader.radius || 0) <= 0) return false;
                return Math.hypot(point.x - (shader.x + Number(shader.radius) * size), point.y - shader.y) <= tolerance;
            }) || null;
        }

        async commitShaderDrag(drag) {
            if (!drag) return;
            const moved = Math.hypot(drag.to.x - drag.from.x, drag.to.y - drag.from.y);


            if (moved < 0.5) { redraw(); return; }
            await this.patchShader(drag.id, { x: drag.to.x, y: drag.to.y }).catch((error) => {
                console.error("Scene shader move failed", error);
            });
        }

        beginComponentDrag(kind, id, event, surface, { owned = false } = {}) {
            if (owned) {
                this.clearPicks();
                this.picks[kind].add(id);
            } else if (!this.picked(kind, id)) this.pick(kind, id, false);
            const items = this.selectedSnapshots();
            if (!items.length) return false;
            const from = this.world(event);
            if (!from) return false;
            this.componentDrag = { pointerId: event.pointerId, from, to: from, items };
            try { surface.setPointerCapture(event.pointerId); } catch {}
            redraw();
            return true;
        }

        previewComponentDrag(point) {
            const drag = this.componentDrag;
            if (!drag || !point) return;
            drag.to = point;
            const dx = point.x - drag.from.x;
            const dy = point.y - drag.from.y;
            drag.items.forEach(({ kind, value }) => {
                const list = { wall: this.walls, light: this.lights, emitter: this.emitters, shader: this.shaders }[kind];
                const item = (list || []).find((candidate) => candidate.id === value.id);
                if (!item) return;
                if (kind === "wall") Object.assign(item, {
                    x1: value.x1 + dx, y1: value.y1 + dy, x2: value.x2 + dx, y2: value.y2 + dy,
                });
                else Object.assign(item, { x: value.x + dx, y: value.y + dy });
            });
            this.invalidateGeometry();
            redraw();
        }

        finishComponentDrag(drag) {
            if (!drag) return;
            const dx = drag.to.x - drag.from.x;
            const dy = drag.to.y - drag.from.y;
            drag.items.forEach(({ kind, value }) => {
                const list = { wall: this.walls, light: this.lights, emitter: this.emitters, shader: this.shaders }[kind];
                const item = (list || []).find((candidate) => candidate.id === value.id);
                if (item) Object.assign(item, value);
            });
            this.invalidateGeometry();
            if (Math.hypot(dx, dy) < 0.5) { redraw(); return; }
            this.moveSelected(dx, dy);
        }

        cancelTransientInteraction() {
            if (this.componentDrag) {
                this.componentDrag.items.forEach(({ kind, value }) => {
                    const list = { wall: this.walls, light: this.lights, emitter: this.emitters, shader: this.shaders }[kind];
                    const item = (list || []).find((candidate) => candidate.id === value.id);
                    if (item) Object.assign(item, value);
                });
            }
            this.componentDrag = null;
            this.marquee = null;
            this.start = null;
            this.preview = null;
            this.drawingPointerId = null;
            this.downClient = null;
            this.nodeDrag = null;
            this.lightDrag = null;
            this.shaderDrag = null;
            this.shaderResize = null;
            this.emitterDrag = null;
            this.transientShaderPreview = null;
            this.invalidateGeometry();
            redraw();
        }

        semanticPreview(presetId, point = null, { creation = false } = {}) {
            if (!presetId) { this.transientShaderPreview = null; redraw(); return; }
            const definition = window.GravewrightTools?.shaderPresetDefinition?.(presetId) || null;
            const parameters = Object.fromEntries(Object.entries(definition?.parameters || {})
                .map(([key, spec]) => [key, spec.default]));
            const scene = this.scene();
            const at = point || { x: Number(scene?.width || 0) / 2, y: Number(scene?.height || 0) / 2 };
            this.transientShaderPreview = {
                id: "__gravewright_shader_preview__", scene_id: scene?.id || "", preset_id: presetId,
                source: `gravewright-preset://${presetId}/v${definition?.schemaVersion || 1}`,
                x: at.x, y: at.y, radius: parameters.radius ?? 8, rotation: parameters.rotation ?? 0,
                opacity: creation ? 0.62 : (parameters.opacity ?? 1), intensity: parameters.intensity ?? 0.8,
                scale: parameters.scale ?? 1, speed: parameters.speed ?? 1,
                color: parameters.color || "#8fb6ff", blend_mode: parameters.blendMode || "normal",
                enabled: true, transient: true, creation,
            };
            redraw();
        }








        async placeShader(point) {
            const scene = this.scene();
            if (!scene) return this.warnNoScene();
            try {
                const presetId = window.GravewrightTools?.selectedShaderPreset;
                if (presetId) {
                    const result = await post("/game/shaders/apply-preset", {
                        campaign_id: this.roomId,
                        scene_id: scene.id,
                        preset_id: presetId,
                        schema_version: window.GravewrightTools?.selectedShaderPresetSchemaVersion || 1,
                        x: point.x,
                        y: point.y,
                    });
                    const instanceId = result.instance?.id || "";
                    await this.refresh(scene.id);
                    if (instanceId) this.selectedShader = instanceId;
                    redraw();
                    return;
                }
                const shader = await this.createShader({ x: point.x, y: point.y });
                if (!shader) return;
                this.selectedShader = shader.id;
                redraw();
            } catch (error) {
                console.error("Scene shader creation failed", error);
                toast("Não foi possível criar o shader.");
            }
        }

        async createShader(values = {}) {
            const scene = this.scene();
            if (!scene) return this.warnNoScene();
            const result = await post("/game/shaders", { campaign_id: this.roomId, scene_id: scene.id, ...values });
            if (result.shader) { this.shaders = [...(this.shaders || []), result.shader]; redraw(); }
            return result.shader || null;
        }

        async patchShader(shaderId, patch) {
            const shader = (this.shaders || []).find((candidate) => candidate.id === shaderId);
            if (!shader) return null;
            const previous = { ...shader };
            const sourceChanged = Object.hasOwn(patch, "source")
                && String(patch.source || "") !== String(shader.source || "");
            Object.assign(shader, patch);
            if (sourceChanged) window.GravewrightShaderEffects?.invalidate?.(shaderId);
            redraw();
            try {
                const result = await post("/game/shaders/update", { campaign_id: this.roomId, shader_id: shaderId, ...patch });
                const index = this.shaders.findIndex((candidate) => candidate.id === shaderId);
                if (index >= 0 && result.shader) {
                    if (String(result.shader.source || "") !== String(this.shaders[index].source || "")) {
                        window.GravewrightShaderEffects?.invalidate?.(shaderId);
                    }
                    this.shaders[index] = result.shader;
                }
                this.shaderPreviewCanonical.delete(shaderId);
                redraw();
                return result.shader || null;
            } catch (error) {


                const index = this.shaders.findIndex((candidate) => candidate.id === shaderId);
                if (index >= 0) {
                    if (String(this.shaders[index].source || "") !== String(previous.source || "")) {
                        window.GravewrightShaderEffects?.invalidate?.(shaderId);
                    }
                    this.shaders[index] = previous;
                }
                redraw();
                throw error;
            }
        }

        previewShader(shaderId, patch) {
            const shader = (this.shaders || []).find((candidate) => candidate.id === shaderId);
            if (!shader || !patch || typeof patch !== "object") return false;
            if (!this.shaderPreviewCanonical.has(shaderId)) {
                this.shaderPreviewCanonical.set(shaderId, { ...shader });
            }
            this.shaderPreviewPending.set(shaderId, { ...(this.shaderPreviewPending.get(shaderId) || {}), ...patch });
            if (this.shaderPreviewFrame !== null) return true;
            this.shaderPreviewFrame = requestAnimationFrame(() => {
                const started = performance.now();
                this.shaderPreviewFrame = null;
                this.shaderPreviewPending.forEach((values, id) => {
                    const live = (this.shaders || []).find((candidate) => candidate.id === id);
                    if (live) Object.assign(live, values);
                });
                this.shaderPreviewPending.clear();
                redraw();
                performance.measure?.("preview_parameter_update_ms", { start: started, end: performance.now() });
            });
            return true;
        }

        restoreShaderPreview(shaderId) {
            const canonical = this.shaderPreviewCanonical.get(shaderId);
            if (!canonical) return false;
            const index = this.shaders.findIndex((candidate) => candidate.id === shaderId);
            if (index >= 0) this.shaders[index] = canonical;
            this.shaderPreviewCanonical.delete(shaderId);
            this.shaderPreviewPending.delete(shaderId);
            redraw();
            return true;
        }

        async commitShaderPreview(shaderId, patch) {
            const shader = (this.shaders || []).find((candidate) => candidate.id === shaderId);
            const canonical = this.shaderPreviewCanonical.get(shaderId) || (shader ? { ...shader } : null);
            if (!shader || !canonical) return null;
            try {
                let result;
                if (shader.preset_id) {
                    const parameters = Object.fromEntries(Object.entries(patch || {}).map(([key, value]) => [
                        key === "blend_mode" ? "blendMode" : key, value,
                    ]));
                    result = await post("/game/shaders/update-preset", {
                        campaign_id: this.roomId, shader_id: shaderId,
                        expected_version: Number(canonical.version || shader.version || 1), parameters,
                    });
                    await this.refresh(shader.scene_id);
                } else {
                    result = await post("/game/shaders/update", {
                        campaign_id: this.roomId, shader_id: shaderId, ...(patch || {}),
                    });
                    const index = this.shaders.findIndex((candidate) => candidate.id === shaderId);
                    if (index >= 0 && result.shader) this.shaders[index] = result.shader;
                }
                this.shaderPreviewCanonical.delete(shaderId);
                redraw();
                return result.instance || result.shader || null;
            } catch (error) {
                this.restoreShaderPreview(shaderId);
                await this.refresh(canonical.scene_id).catch(() => {});
                throw error;
            }
        }

        async deleteShader(shaderId) {
            const before = (this.shaders || []).slice();
            this.shaders = before.filter((shader) => shader.id !== shaderId);
            window.GravewrightShaderEffects?.invalidate?.(shaderId);
            redraw();
            try {
                await post("/game/shaders/delete", { campaign_id: this.roomId, shader_id: shaderId });
            } catch (error) {
                this.shaders = before;
                redraw();
                console.error("Scene shader delete failed", error);
            }
        }

        async patchEmitter(emitterId, patch) {
            const emitter = (this.emitters || []).find((candidate) => candidate.id === emitterId);
            if (!emitter) return;
            const previous = { ...emitter };
            Object.assign(emitter, patch);
            redraw();
            try {
                const result = await post("/game/particles/update", {
                    campaign_id: this.roomId, emitter_id: emitterId, ...patch,
                });
                const index = this.emitters.findIndex((candidate) => candidate.id === emitterId);
                if (index >= 0 && result.emitter) this.emitters[index] = result.emitter;
                redraw();
            } catch (error) {
                const index = this.emitters.findIndex((candidate) => candidate.id === emitterId);
                if (index >= 0) this.emitters[index] = previous;
                redraw();
                console.error("Scene particle emitter update failed", error);
            }
        }

        async deleteEmitter(emitterId) {
            const before = this.emitters.slice();
            this.emitters = this.emitters.filter((emitter) => emitter.id !== emitterId);
            if (this.selectedEmitter === emitterId) this.selectedEmitter = "";
            redraw();
            try {
                await post("/game/particles/delete", { campaign_id: this.roomId, emitter_id: emitterId });
            } catch (error) {
                this.emitters = before;
                redraw();
                console.error("Scene particle emitter delete failed", error);
            }
        }

        async placeLight(point) {
            const scene = this.scene();
            if (!scene) return this.warnNoScene();





            const chosen = String(window.GravewrightTools?.activeSubTool || "");
            const animation = chosen === "none" || EMISSIONS[chosen] ? chosen : "torch";
            const temporaryId = `pending-light-${Date.now()}`;
            const preset = LIGHT_DEFAULTS[animation] || LIGHT_DEFAULTS.none;
            const temporary = {
                id: temporaryId, x: point.x, y: point.y, animation, enabled: 1,
                rotation: 0, ...preset,
            };
            this.lights.push(temporary);
            redraw();
            try {
                const result = await post("/game/lights", {
                    campaign_id: this.roomId, scene_id: scene.id,
                    x: point.x, y: point.y, animation,
                    bright_radius: temporary.bright_radius, dim_radius: temporary.dim_radius,
                    color: temporary.color, intensity: temporary.intensity,
                    angle: temporary.angle, rotation: temporary.rotation,
                });
                if (this.sceneId !== scene.id) return;
                const index = this.lights.findIndex((light) => light.id === temporaryId);
                if (index >= 0 && result.light) this.lights[index] = result.light;
                this.selectedLight = result.light?.id || "";
                redraw();
            } catch (error) {
                if (this.sceneId !== scene.id) return;
                this.lights = this.lights.filter((light) => light.id !== temporaryId);
                redraw();
                console.error("Dynamic lighting source creation failed", error);
                toast("Não foi possível criar o foco de luz.");
            }
        }



        async patchLight(lightId, patch) {
            const light = this.lights.find((candidate) => candidate.id === lightId);
            if (!light) return;
            const previous = { ...light };
            Object.assign(light, patch);
            redraw();
            try {
                const result = await post("/game/lights/update", { campaign_id: this.roomId, light_id: lightId, ...patch });
                const index = this.lights.findIndex((candidate) => candidate.id === lightId);
                if (index >= 0 && result.light) this.lights[index] = result.light;
                redraw();
            } catch (error) {
                const index = this.lights.findIndex((candidate) => candidate.id === lightId);
                if (index >= 0) this.lights[index] = previous;
                redraw();
                console.error("Dynamic lighting source update failed", error);
                toast("Não foi possível atualizar o foco de luz.");
            }
        }

        async deleteLight(lightId) {
            this.lights = this.lights.filter((light) => light.id !== lightId);
            if (this.selectedLight === lightId) this.selectedLight = "";
            redraw();
            try {
                await post("/game/lights/delete", { campaign_id: this.roomId, light_id: lightId });
            } catch (error) {
                console.error("Dynamic lighting source delete failed", error);
            }
            if (!this.isStreamer) await this.refresh();
        }

        async commitEmitter(drag) {
            const emitter = (this.emitters || []).find((candidate) => candidate.id === drag.id);
            if (!emitter) return;


            if (Math.hypot(drag.to.x - drag.from.x, drag.to.y - drag.from.y) < 0.5) { redraw(); return; }
            await this.patchEmitter(drag.id, { x: drag.to.x, y: drag.to.y });
        }

        async commitLight(drag) {
            const light = this.lights.find((candidate) => candidate.id === drag.id);
            if (!light) return;
            if (Math.hypot(drag.to.x - drag.from.x, drag.to.y - drag.from.y) < 0.5) { redraw(); return; }
            const previous = { x: light.x, y: light.y };
            light.x = drag.to.x; light.y = drag.to.y;
            redraw();
            try {
                const result = await post("/game/lights/update", { campaign_id: this.roomId, light_id: light.id, x: drag.to.x, y: drag.to.y });
                const index = this.lights.findIndex((candidate) => candidate.id === light.id);
                if (index >= 0 && result.light) this.lights[index] = result.light;
                redraw();
            } catch (error) {
                light.x = previous.x; light.y = previous.y;
                redraw();
                console.error("Dynamic lighting source move failed", error);
                toast("Não foi possível mover o foco de luz.");
            }
        }

        async commitNode(drag) {
            const scene = this.scene();
            if (!scene) return;
            if (sameNode(drag.to.x, drag.to.y, drag.from)) { redraw(); return; }
            const previous = this.walls;
            this.walls = drag.detached
                ? moveEndpoint(this.walls, drag.wallId, drag.endpoint, drag.to)
                : moveNode(this.walls, drag.from, drag.to);
            this.invalidateGeometry();
            redraw();
            try {
                const result = await post(drag.detached ? "/game/walls/move-endpoint" : "/game/walls/move-node", {
                    campaign_id: this.roomId, scene_id: scene.id,
                    ...(drag.detached ? { wall_id: drag.wallId, endpoint: drag.endpoint } : {
                        from_x: drag.from.x, from_y: drag.from.y,
                    }),
                    to_x: drag.to.x, to_y: drag.to.y,
                });
                if (this.sceneId !== scene.id) return;
                if (result.walls) this.walls = result.walls;
                this.invalidateGeometry();
                redraw();
            } catch (error) {
                if (this.sceneId !== scene.id) return;
                this.walls = previous;
                this.invalidateGeometry();
                redraw();
                console.error("Dynamic lighting node move failed", error);
                toast("Não foi possível mover o nó da parede.");
            }
        }

        cancelDrawing() {
            this.cancelTransientInteraction();
        }


        handlePlayDoor(event) {
            const currentLayer = window.GravewrightTools?.activeLayer || activeLayer;
            if (currentLayer === EDIT_LAYERS.door) return false;
            if (event.button !== 0 && event.button !== 2) return false;

            if (event.button === 2 && !this.isGm) return false;
            const raw = this.world(event);
            const door = raw ? this.doorAt(raw) : null;
            if (!door) return false;
            event.preventDefault(); event.stopPropagation();
            void this.operateDoor(door, { lock: event.button === 2 });
            return true;
        }

        bind() {
            const surface = this.canvas.closest("[data-map-viewport]");
            if (!surface) return;
            surface.addEventListener("pointermove", (event) => {
                if (this.componentDrag) {
                    this.previewComponentDrag(this.world(event));
                    return;
                }
                if (this.marquee) {
                    this.marquee.to = this.world(event) || this.marquee.to;
                    redraw();
                    return;
                }
                if (this.shaderDrag) {
                    this.shaderDrag.to = this.world(event) || this.shaderDrag.to;
                    redraw();
                    return;
                }
                if (this.shaderResize) {
                    const at = this.world(event);
                    const shader = (this.shaders || []).find((candidate) => candidate.id === this.shaderResize.id);
                    if (at && shader) {
                        const size = this.scene()?.scaledTileSize || 50;
                        const radius = Math.max(0, Math.min(120, Math.hypot(at.x - shader.x, at.y - shader.y) / size));
                        this.shaderResize.to = radius;
                        this.previewShader(shader.id, { radius });
                    }
                    return;
                }
                if (window.GravewrightTools?.activeTool === "shader" && window.GravewrightTools?.selectedShaderPreset) {
                    this.semanticPreview(window.GravewrightTools.selectedShaderPreset, this.target(event), { creation: true });
                }
                if (this.emitterDrag) {
                    this.emitterDrag.to = this.world(event) || this.emitterDrag.to;
                    redraw();
                    return;
                }
                if (this.lightDrag) {
                    this.lightDrag.to = this.world(event) || this.lightDrag.to;
                    redraw();
                    return;
                }
                if (this.nodeDrag) {
                    this.nodeDrag.to = this.target(event, this.nodeDrag.from) || this.nodeDrag.to;
                    redraw();
                    return;
                }
                if (!this.start) return;
                this.preview = this.target(event);
                redraw();
            }, true);
            surface.addEventListener("pointerdown", (event) => {
                trace("pointerdown", { button: event.button, isGm: this.isGm, activeLayer, activeTool: window.GravewrightTools?.activeTool, temStart: Boolean(this.start) });
                if (event.target.closest("[data-layer-hud]")) return;
                if (this.handlePlayDoor(event)) return;
                if (!this.isGm) return trace("ignorado: nao e gm");



                const onTool = window.GravewrightTools?.activeTool;
                const layerAllows = onTool === "select"


                    ? Object.values(EDIT_LAYERS).includes(activeLayer)
                    : activeLayer === EDIT_LAYERS[onTool];
                if (!layerAllows) return trace("ignorado: camada", { activeLayer, onTool });
                if (event.button === 2 && (this.start || this.componentDrag || this.nodeDrag || this.lightDrag
                    || this.shaderDrag || this.shaderResize || this.emitterDrag || this.marquee || this.transientShaderPreview)) {
                    event.preventDefault(); event.stopPropagation();
                    this.cancelTransientInteraction();
                    return;
                }
                if (event.button !== 0) return;
                const tool = window.GravewrightTools?.activeTool;
                const raw = this.world(event);
                if (!raw) return;

                if (tool === "light") {
                    event.preventDefault(); event.stopPropagation();
                    const existing = this.lightAt(raw);
                    if (existing) { this.beginComponentDrag("light", existing.id, event, surface, { owned: true }); return; }
                    void this.placeLight(this.target(event));
                    return;
                }

                if (tool === "shader") {
                    event.preventDefault(); event.stopPropagation();
                    const handle = this.shaderResizeAt(raw);
                    if (handle) {
                        this.shaderResize = { id: handle.id, from: Number(handle.radius), to: Number(handle.radius), pointerId: event.pointerId };
                        try { surface.setPointerCapture(event.pointerId); } catch {}
                        return;
                    }
                    const existing = this.shaderAt(raw);



                    if (existing) {
                        this.transientShaderPreview = null;
                        this.beginComponentDrag("shader", existing.id, event, surface, { owned: true });
                        return;
                    }
                    this.transientShaderPreview = null;
                    void this.placeShader(this.target(event));
                    return;
                }

                if (tool === "particles") {
                    const existing = this.emitterAt(raw);
                    event.preventDefault(); event.stopPropagation();
                    if (existing) {
                        this.beginComponentDrag("emitter", existing.id, event, surface, { owned: true });
                        return;
                    }
                    void this.placeEmitter(this.target(event));
                    return;
                }

                if (tool === "select" && activeLayer === EDIT_LAYERS.particles) {



                    const shader = this.shaderAt(raw);
                    if (shader) {
                        event.preventDefault(); event.stopPropagation();
                        this.beginComponentDrag("shader", shader.id, event, surface);
                        return;
                    }
                    const existing = this.emitterAt(raw);
                    if (existing) {
                        event.preventDefault(); event.stopPropagation();
                        this.beginComponentDrag("emitter", existing.id, event, surface);
                        return;
                    }

                }



                if (tool === "select") {
                    const light = activeLayer === EDIT_LAYERS.light ? this.lightAt(raw) : null;
                    if (light) {
                        event.preventDefault(); event.stopPropagation();
                        this.beginComponentDrag("light", light.id, event, surface);
                        return;
                    }
                    const node = activeLayer === EDIT_LAYERS.wall
                        ? (event.shiftKey ? this.endpointAt(raw) : this.nodeAt(raw)) : null;
                    if (node) {
                        event.preventDefault(); event.stopPropagation();
                        this.nodeDrag = { from: { x: node.x, y: node.y }, to: { x: node.x, y: node.y },
                            pointerId: event.pointerId, detached: Boolean(event.shiftKey),
                            wallId: node.wallId, endpoint: node.endpoint };
                        try { surface.setPointerCapture(event.pointerId); } catch {}
                        redraw();
                        return;
                    }
                }
                const wallKind = tool === "wall" || tool === "door" ? tool : null;
                const ownedNode = wallKind && !this.start
                    ? (event.shiftKey ? this.endpointAt(raw, wallKind) : this.nodeAt(raw, wallKind)) : null;
                if (ownedNode) {
                    event.preventDefault(); event.stopPropagation();
                    this.clearPicks();
                    this.nodeDrag = { from: { x: ownedNode.x, y: ownedNode.y }, to: { x: ownedNode.x, y: ownedNode.y },
                        pointerId: event.pointerId, detached: Boolean(event.shiftKey),
                        wallId: ownedNode.wallId, endpoint: ownedNode.endpoint };
                    try { surface.setPointerCapture(event.pointerId); } catch {}
                    redraw();
                    return;
                }
                const hit = this.hit(raw, wallKind && !this.start ? wallKind : null);
                if (tool === "select" && activeLayer === EDIT_LAYERS.wall && hit) {
                    event.preventDefault(); event.stopPropagation();



                    if (hit.kind === "door" && this.picked("wall", hit.id) && this.pickCount() === 1) {
                        void this.cycleDoor(hit);
                    } else {
                        this.beginComponentDrag("wall", hit.id, event, surface);
                    }
                    return;
                }
                if (wallKind && !this.start && hit) {
                    event.preventDefault(); event.stopPropagation();
                    this.beginComponentDrag("wall", hit.id, event, surface, { owned: true });
                    return;
                }
                if (tool === "select") {


                    event.preventDefault(); event.stopPropagation();
                    this.marquee = {
                        from: raw, to: raw, pointerId: event.pointerId, additive: event.shiftKey,
                    };
                    if (!event.shiftKey) this.clearPicks();
                    try { surface.setPointerCapture(event.pointerId); } catch {}
                    redraw();
                    return;
                }
                if (tool !== "wall" && tool !== "door") return trace("ignorado: ferramenta ativa nao e parede/porta", tool);
                event.preventDefault(); event.stopPropagation();


                if (!this.scene()) return this.warnNoScene();
                const point = this.target(event);
                trace("ponto resolvido", point);
                if (!this.start) {
                    this.start = point;
                    this.preview = point;
                    this.drawingPointerId = event.pointerId;
                    this.downClient = { x: event.clientX, y: event.clientY };
                    try { surface.setPointerCapture(event.pointerId); } catch {}
                    redraw();
                    return;
                }

                this.drawingPointerId = null;
                this.downClient = null;
                trace("segundo ponto: cravando", { de: this.start, para: point });
                void this.create(point, tool, !event.altKey);
            }, true);
            surface.addEventListener("pointerup", (event) => {
                if (this.componentDrag && event.pointerId === this.componentDrag.pointerId) {
                    const drag = this.componentDrag;
                    this.componentDrag = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    this.finishComponentDrag(drag);
                    return;
                }
                if (this.marquee && event.pointerId === this.marquee.pointerId) {
                    const box = this.marquee;
                    this.marquee = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    const width = Math.abs(box.to.x - box.from.x);
                    const height = Math.abs(box.to.y - box.from.y);


                    if (width > 2 || height > 2) {
                        const rect = {
                            x0: Math.min(box.from.x, box.to.x), x1: Math.max(box.from.x, box.to.x),
                            y0: Math.min(box.from.y, box.to.y), y1: Math.max(box.from.y, box.to.y),
                        };
                        this.pickInside(rect, box.additive);
                    }
                    redraw();
                    return;
                }
                if (this.shaderDrag && event.pointerId === this.shaderDrag.pointerId) {
                    const drag = this.shaderDrag;
                    this.shaderDrag = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    void this.commitShaderDrag(drag);
                    return;
                }
                if (this.shaderResize && event.pointerId === this.shaderResize.pointerId) {
                    const resize = this.shaderResize;
                    this.shaderResize = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    void this.commitShaderPreview(resize.id, { radius: resize.to }).catch((error) => {
                        console.error("Scene shader resize failed", error);
                    });
                    return;
                }
                if (this.emitterDrag && event.pointerId === this.emitterDrag.pointerId) {
                    const drag = this.emitterDrag;
                    this.emitterDrag = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    void this.commitEmitter(drag);
                    return;
                }
                if (this.lightDrag && event.pointerId === this.lightDrag.pointerId) {
                    const drag = this.lightDrag;
                    this.lightDrag = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    void this.commitLight(drag);
                    return;
                }
                if (this.nodeDrag && event.pointerId === this.nodeDrag.pointerId) {
                    const drag = this.nodeDrag;
                    this.nodeDrag = null;
                    try { surface.releasePointerCapture(event.pointerId); } catch {}
                    event.preventDefault(); event.stopPropagation();
                    const tool = window.GravewrightTools?.activeTool;
                    if ((tool === "wall" || tool === "door") && sameNode(drag.to.x, drag.to.y, drag.from)) {
                        this.start = { ...drag.from };
                        this.preview = { ...drag.from };
                        redraw();
                        return;
                    }
                    void this.commitNode(drag);
                    return;
                }
                if (this.drawingPointerId === null || event.pointerId !== this.drawingPointerId) return;
                this.drawingPointerId = null;
                try { surface.releasePointerCapture(event.pointerId); } catch {}
                const down = this.downClient;
                this.downClient = null;
                if (!this.start) return;
                const tool = window.GravewrightTools?.activeTool;
                if (tool !== "wall" && tool !== "door") return;

                const dragged = down ? Math.hypot(event.clientX - down.x, event.clientY - down.y) >= DRAG_THRESHOLD_PX : false;
                if (!dragged) return;
                const end = this.target(event);
                if (!end) return;
                event.preventDefault(); event.stopPropagation();
                void this.create(end, tool, !event.altKey);
            }, true);

            surface.addEventListener("dblclick", (event) => {
                if (!this.isGm) return;
                if (activeLayer === EDIT_LAYERS.particles) {
                    const at = this.world(event);
                    const activeTool = window.GravewrightTools?.activeTool || "select";
                    const shader = activeTool === "particles" ? null : (at ? this.shaderAt(at) : null);
                    if (shader) {
                        event.preventDefault(); event.stopPropagation();
                        this.selectedShader = shader.id;
                        redraw();
                        document.dispatchEvent(new CustomEvent("lighting:edit-shader", {
                            detail: { canvas: this.canvas, roomId: this.roomId, shaderId: shader.id },
                        }));
                        return;
                    }
                    const emitter = activeTool === "shader" ? null : (at ? this.emitterAt(at) : null);
                    if (!emitter) return;
                    event.preventDefault(); event.stopPropagation();
                    this.selectedEmitter = emitter.id;
                    redraw();
                    document.dispatchEvent(new CustomEvent("lighting:edit-emitter", {
                        detail: { canvas: this.canvas, emitterId: emitter.id, clientX: event.clientX, clientY: event.clientY },
                    }));
                    return;
                }
                if (activeLayer === EDIT_LAYERS.wall) {
                    const at = this.world(event);
                    const wall = at ? this.hit(at) : null;
                    if (!wall) return;

                    // Portas sao segmentos atomicos. A tool de porta usa o
                    // duplo clique para operar a porta selecionada; nenhuma
                    // tool pode transforma-la implicitamente em dois segmentos.
                    if (wall.kind === "door") {
                        if (window.GravewrightTools?.activeTool === "door") {
                            event.preventDefault(); event.stopPropagation();
                            this.selected = wall.id;
                            void this.cycleDoor(wall);
                        }
                        return;
                    }


                    if (this.nodeAt(at)) return;
                    event.preventDefault(); event.stopPropagation();
                    void this.splitWall(wall, at);
                    return;
                }
                if (activeLayer !== EDIT_LAYERS.light) return;
                const raw = this.world(event);
                const light = raw ? this.lightAt(raw) : null;
                if (!light) return;
                event.preventDefault(); event.stopPropagation();
                this.selectedLight = light.id;
                redraw();
                document.dispatchEvent(new CustomEvent("lighting:edit-light", {
                    detail: { canvas: this.canvas, lightId: light.id, clientX: event.clientX, clientY: event.clientY },
                }));
            }, true);
            surface.addEventListener("pointercancel", (event) => {
                if (this.componentDrag && event.pointerId === this.componentDrag.pointerId) {
                    this.cancelTransientInteraction();
                    return;
                }
                if (this.marquee && event.pointerId === this.marquee.pointerId) {
                    this.marquee = null;
                }
                if (this.shaderDrag && event.pointerId === this.shaderDrag.pointerId) {
                    this.shaderDrag = null;
                }
                if (this.shaderResize && event.pointerId === this.shaderResize.pointerId) {
                    this.restoreShaderPreview(this.shaderResize.id);
                    this.shaderResize = null;
                }
                if (this.emitterDrag && event.pointerId === this.emitterDrag.pointerId) {
                    this.emitterDrag = null;
                }
                if (this.lightDrag && event.pointerId === this.lightDrag.pointerId) {
                    this.lightDrag = null;
                    redraw();
                    return;
                }
                if (this.nodeDrag && event.pointerId === this.nodeDrag.pointerId) {
                    this.nodeDrag = null;
                    redraw();
                    return;
                }
                if (event.pointerId !== this.drawingPointerId) return;
                this.drawingPointerId = null;
                this.downClient = null;
            }, true);
        }




        async splitWall(wall, point) {
            try {
                const result = await post("/game/walls/split", {
                    campaign_id: this.roomId, wall_id: wall.id, x: point.x, y: point.y,
                });
                if (result.walls) {
                    this.walls = result.walls;
                    this.invalidateGeometry();
                    redraw();
                }
            } catch (error) {


                const tooClose = String(error.message || "").includes("invalid");
                console.error("Wall split failed", error);
                toast(tooClose ? "Muito perto da ponta da parede." : "Não foi possível dividir a parede.");
            }
        }

        async removeSelected(kind = null, wallKind = null) {
            const snapshots = this.selectedSnapshots().filter((snapshot) =>
                (!kind || snapshot.kind === kind) && (!wallKind || snapshot.value.kind === wallKind));
            const lots = [
                ["light", "/game/lights/delete-many", "light_ids"],
                ["wall", "/game/walls/delete-many", "wall_ids"],
                ["emitter", "/game/particles/delete-many", "emitter_ids"],
                ["shader", "/game/shaders/delete-many", "shader_ids"],
            ].map(([itemKind, url, field]) => [url, field, itemKind,
                kind && itemKind !== kind ? [] : this.pickedIds(itemKind).filter((id) =>
                    !wallKind || itemKind !== "wall" || this.walls.find((wall) => wall.id === id)?.kind === wallKind)])
             .filter(([, , , ids]) => ids.length);
            if (!lots.length) return;
            if (kind) this.picks[kind].clear(); else this.clearPicks();
            redraw();
            try {
                await Promise.all(lots.map(([url, field, , ids]) =>
                    post(url, { campaign_id: this.roomId, [field]: ids })));
            } catch (error) {
                console.error("Bulk delete failed", error);
                toast("Não foi possível apagar a seleção.");
            }
            if (!this.isStreamer) await this.refresh();
            if (snapshots.length) {
                let live = snapshots;
                window.GravewrightMap?.history?.push?.({
                    undo: async () => { live = await this.restoreSnapshots(snapshots, 0); },
                    redo: () => { void this.deleteSnapshots(live); },
                });
            }
        }

        selectedSnapshots() {
            const sources = { wall: this.walls, light: this.lights, emitter: this.emitters, shader: this.shaders };
            return Object.entries(sources).flatMap(([kind, items]) =>
                (items || []).filter((item) => this.picked(kind, item.id)).map((item) => ({ kind, value: { ...item } })));
        }

        copySelected() {
            const items = this.selectedSnapshots();
            if (!items.length) return false;
            componentClipboard = { items, sceneId: this.scene()?.id || "" };
            return true;
        }

        async createSnapshot(snapshot, offset = 0) {
            const scene = this.scene();
            if (!scene) return null;
            const value = snapshot.value || {};
            const shifted = { ...value };
            if (snapshot.kind === "wall") {
                Object.assign(shifted, { x1: value.x1 + offset, y1: value.y1 + offset, x2: value.x2 + offset, y2: value.y2 + offset });
            } else {
                Object.assign(shifted, { x: value.x + offset, y: value.y + offset });
            }
            const specs = {
                wall: ["/game/walls", "wall", ["kind", "x1", "y1", "x2", "y2"]],
                light: ["/game/lights", "light", ["x", "y", "bright_radius", "dim_radius", "color", "intensity", "angle", "rotation", "animation", "enabled"]],
                emitter: ["/game/particles", "emitter", ["x", "y", "kind", "scale", "density", "color", "enabled"]],
                shader: ["/game/shaders", "shader", ["x", "y", "name", "source", "radius", "rotation", "blend_mode", "intensity", "opacity", "scale", "speed", "color", "enabled"]],
            };
            const spec = specs[snapshot.kind];
            if (!spec) return null;
            const payload = { campaign_id: this.roomId, scene_id: scene.id };
            spec[2].forEach((key) => { if (shifted[key] !== undefined) payload[key] = shifted[key]; });
            const result = await post(spec[0], payload);
            const created = result[spec[1]];
            if (!created) return null;
            const listName = { wall: "walls", light: "lights", emitter: "emitters", shader: "shaders" }[snapshot.kind];
            this[listName] = [...(this[listName] || []), created];
            return { kind: snapshot.kind, value: { ...created } };
        }

        async restoreSnapshots(snapshots, offset = 0) {
            const created = (await Promise.all((snapshots || []).map((item) => this.createSnapshot(item, offset)))).filter(Boolean);
            this.clearPicks();
            created.forEach((item) => this.picks[item.kind].add(item.value.id));
            this.invalidateGeometry(); redraw();
            return created;
        }

        async deleteSnapshots(snapshots) {
            const ids = { wall: [], light: [], emitter: [], shader: [] };
            (snapshots || []).forEach((item) => { if (item?.value?.id && ids[item.kind]) ids[item.kind].push(item.value.id); });
            const specs = { wall: ["/game/walls/delete-many", "wall_ids"], light: ["/game/lights/delete-many", "light_ids"], emitter: ["/game/particles/delete-many", "emitter_ids"], shader: ["/game/shaders/delete-many", "shader_ids"] };
            await Promise.all(Object.entries(ids).filter(([, values]) => values.length).map(([kind, values]) =>
                post(specs[kind][0], { campaign_id: this.roomId, [specs[kind][1]]: values })));
            if (!this.isStreamer) await this.refresh();
            this.invalidateGeometry(); redraw();
        }

        async pasteClipboard() {
            if (!componentClipboard?.items?.length) return false;
            let created = await this.restoreSnapshots(componentClipboard.items, 16);
            if (!created.length) return false;
            window.GravewrightMap?.history?.push?.({
                undo: () => { void this.deleteSnapshots(created); },
                redo: async () => { created = await this.restoreSnapshots(componentClipboard.items, 16); },
            });
            return true;
        }

        async applySelectedMove(dx, dy) {
            const scene = this.scene();
            if (!scene || (!dx && !dy)) return false;
            const wallIds = this.pickedIds("wall");
            const jobs = [];
            if (wallIds.length) {
                jobs.push(post("/game/walls/move-many", {
                    campaign_id: this.roomId, scene_id: scene.id, wall_ids: wallIds, dx, dy,
                }).then((result) => { if (result.walls) this.walls = result.walls; }));
            }
            this.pickedIds("light").forEach((id) => {
                const item = this.lights.find((value) => value.id === id);
                if (item) jobs.push(this.patchLight(id, { x: item.x + dx, y: item.y + dy }));
            });
            this.pickedIds("emitter").forEach((id) => {
                const item = this.emitters.find((value) => value.id === id);
                if (item) jobs.push(this.patchEmitter(id, { x: item.x + dx, y: item.y + dy }));
            });
            this.pickedIds("shader").forEach((id) => {
                const item = this.shaders.find((value) => value.id === id);
                if (item) jobs.push(this.patchShader(id, { x: item.x + dx, y: item.y + dy }));
            });
            if (!jobs.length) return false;
            await Promise.all(jobs);
            this.invalidateGeometry(); redraw();
            return true;
        }

        moveSelected(dx, dy) {
            if (!this.pickCount()) return false;
            void this.applySelectedMove(dx, dy);
            window.GravewrightMap?.history?.push?.({
                undo: () => { void this.applySelectedMove(-dx, -dy); },
                redo: () => { void this.applySelectedMove(dx, dy); },
            });
            return true;
        }

    }



    function startAnimationLoop() {
        let last = 0;
        const tick = (now) => {
            if (now - last >= ANIMATION_INTERVAL_MS) {
                last = now;
                if ([...controllers.values()].some((controller) => controller.animated())) redraw();
            }
            window.requestAnimationFrame(tick);
        };
        window.requestAnimationFrame(tick);
    }

    function init() {
        activeLayer = window.GravewrightTools?.activeLayer || "game";
        document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
            const controller = new LightingController(canvas);
            controllers.set(canvas, controller);
        });
        document.addEventListener("tool:active-layer", (event) => {
            activeLayer = event.detail?.layer || "game";
            controllers.forEach((controller) => controller.cancelDrawing());
            redraw();
        });
        document.addEventListener("tool:active-tool", (event) => {
            controllers.forEach((controller) => {
                controller.cancelDrawing();
                controller.transientShaderPreview = null;
                controller.scopePicksForTool(event.detail?.tool || window.GravewrightTools?.activeTool || "select");
            });
            redraw();
        });
        document.addEventListener("tool:shader-preview", (event) => {
            controllers.forEach((controller) => controller.semanticPreview(event.detail?.presetId || null));
        });
        document.addEventListener("tool:layer-state", redraw);
        document.addEventListener("vtt:shaders-toggled", redraw);
        document.addEventListener("vtt:token-selection-changed", (event) => { selectedTokenId = event.detail?.tokenId || ""; redraw(); });
        document.addEventListener("token:vision-preview", (event) => {
            visionPreviewTokenId = event.detail?.tokenId || "";
            controllers.forEach((controller) => controller.invalidateGeometry());
            redraw();
        });
        document.addEventListener("vtt:transport-event", (event) => {
            const name = String(event.detail?.event || "");
            if (name === "scene.walls.updated" || name === "scene.lights.updated"
                || name === "scene.particles.updated" || name === "scene.shaders.updated") {
                [...controllers.values()].find((controller) => controller.roomId === event.detail.payload?.room_id)?.refresh();
            } else if (name.startsWith("token")) {

                controllers.forEach((controller) => controller.invalidateGeometry());
                redraw();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") controllers.forEach((controller) => controller.cancelTransientInteraction());
            const editing = Object.values(EDIT_LAYERS).includes(activeLayer)
                && !event.target.closest("input,textarea,select,[contenteditable]");
            const commandModifier = event.metaKey || event["ctrlKey"];
            const activeController = controllers.get(window.GravewrightMap?.activeCanvas?.());
            if (editing && commandModifier && event.key.toLowerCase() === "c") {
                const copied = activeController?.copySelected();
                if (copied) event.preventDefault();
                return;
            }
            if (editing && commandModifier && event.key.toLowerCase() === "v") {
                event.preventDefault();
                if (activeController?.scene()?.id) void activeController.pasteClipboard();
                return;
            }
            const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
            if (editing && arrows[event.key]) {
                const [x, y] = arrows[event.key];
                const controller = activeController;
                const step = event.shiftKey ? 1 : (controller?.scene()?.scaledTileSize || 50) / SNAP_DIVISIONS;
                if (controller?.moveSelected(x * step, y * step)) event.preventDefault();
                return;
            }
            const erasing = (event.key === "Delete" || event.key === "Backspace")
                && !event.target.closest("input,textarea,select,[contenteditable]");
            if (!erasing) return;






            if (!Object.values(EDIT_LAYERS).includes(activeLayer)) return;
            const toolKinds = { wall: ["wall", "wall"], door: ["wall", "door"], light: ["light"], particles: ["emitter"], shader: ["shader"] };
            const activeTool = window.GravewrightTools?.activeTool || "select";
            controllers.forEach((controller) => void controller.removeSelected(...(toolKinds[activeTool] || [])));
        });
        startAnimationLoop();
    }

    window.GravewrightLighting = {
        build: BUILD,
        stateForCanvas: (canvas) => controllers.get(canvas)?.pixiState() || null,


        blocksMovement: (canvas, from, to) =>
            controllers.get(canvas)?.blocksMovement(from, to) ?? false,

        invalidateFor: (canvas) => controllers.get(canvas)?.invalidateGeometry(),


        invalidateAll: () => controllers.forEach((controller) => controller.invalidateGeometry()),
        lightFor: (canvas, lightId) => controllers.get(canvas)?.lights.find((light) => light.id === lightId) || null,


        particleCloud: (emitter, now = 0, cellSize = 50) => particlesOf(emitter, now, cellSize),
        emitterFor: (canvas, emitterId) => controllers.get(canvas)?.emitters.find((emitter) => emitter.id === emitterId) || null,
        patchEmitter: (canvas, emitterId, patch) => controllers.get(canvas)?.patchEmitter(emitterId, patch),
        deleteEmitter: (canvas, emitterId) => controllers.get(canvas)?.deleteEmitter(emitterId),
        shadersFor: (canvas) => controllers.get(canvas)?.shaders || [],
        createShader: (canvas, values) => controllers.get(canvas)?.createShader(values),
        patchShader: (canvas, shaderId, patch) => controllers.get(canvas)?.patchShader(shaderId, patch),
        previewShader: (canvas, shaderId, patch) => controllers.get(canvas)?.previewShader(shaderId, patch),
        restoreShaderPreview: (canvas, shaderId) => controllers.get(canvas)?.restoreShaderPreview(shaderId),
        commitShaderPreview: (canvas, shaderId, patch) => controllers.get(canvas)?.commitShaderPreview(shaderId, patch),
        deleteShader: (canvas, shaderId) => controllers.get(canvas)?.deleteShader(shaderId),
        patchLight: (canvas, lightId, patch) => controllers.get(canvas)?.patchLight(lightId, patch),
        deleteLight: (canvas, lightId) => controllers.get(canvas)?.deleteLight(lightId),



        emissionProfile: (light, now = 0) => ({
            alpha: animationFactor(light, now),
            wobble: shapeFactor(light, now),
            spin: spinAngle(light, now),
            offset: jitterOf(light, now, light.bright || light.dim || 0),
            tint: tintOf(light, now),
            sources: sourcesOf(light, now, light.dim || 0, light.bright || 0),
            ...lobesOf(light),
        }),
        debug: () => [...controllers.values()].map((controller) => controller.diagnostics()),
        trace: (on = true) => { tracing = Boolean(on); return tracing ? "rastreio ligado" : "rastreio desligado"; },


        sample: (frames = 20) => new Promise((resolve) => {
            const rows = [];
            const step = () => {
                [...controllers.values()].forEach((controller) => {
                    const state = controller.pixiState();
                    rows.push({
                        visible: state.visible, editing: state.editing, editingLights: state.editingLights,
                        doors: state.doors.length, darkness: state.darkness,
                        scene: controller.scene()?.id || null,
                        walls: controller.walls.length,
                    });
                });
                if (rows.length >= frames) {
                    const key = (row) => JSON.stringify(row);
                    const unique = [...new Set(rows.map(key))];
                    resolve({ estavel: unique.length === 1, variantes: unique.map((row) => JSON.parse(row)) });
                    return;
                }
                window.requestAnimationFrame(step);
            };
            window.requestAnimationFrame(step);
        }),
    };
    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init, { once: true }) : init();
})();
