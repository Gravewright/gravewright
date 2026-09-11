import { transformedPoint } from '../../../features/selection/model/objects.js';
import { arrowHead } from '../../../features/drawing/model/drawing.js';
import { Container, Graphics, Sprite, Texture, Text } from "pixi.js";
import { effectQuality } from "../../../shared/rendering/effect-quality.js";
import { renderingPreferences } from "../../../shared/rendering/render-profile.js";
import { SceneLightMap } from "./scene-light-map.js";
import { effectLights } from "../model/effect-lighting.js";
import { paintAnimatedLight } from "../../../features/lighting/model/light-profiles.js";
import { particlesOf } from "../../../features/effects/model/particle-profiles.js";
import { mountShaders } from "./scene-shaders.js";
import { SceneRenderKey } from "../model/scene-render-key.js";
import { sceneDarkness } from "../model/scene-darkness.js";
import { visibilityPolygon } from "../model/visibility-polygon.js";
/** All GPU, animation and image resources here belong to a single mounted block. */
export class SceneLayers {
    board;
    #layers = [];
    #abort = new AbortController();
    #textures = new Set();
    #frame = 0;
    #keys = new SceneRenderKey();
    #staticKey = '';
    #visionKey = '';
    #fogLayer;
    #fogTexture;
    #fogCanvas;
    #fogSprite;
    #fogKey = "";
    #visionLayer;
    #visionTexture;
    #visionCanvas;
    #visionSprite;
    #lightState;
    #lightMap;
    #shaders;
    #bitmaps = new Set();
    #generation = 0;
    #closed = false;
    #imageSprites = new Map();
    #selectionNodes = new Map();
    #selectionPreview;
    registerSelection(key, node) { this.#selectionNodes.set(key, { node, x: node.x, y: node.y, angle: node.angle }); if (this.#selectionPreview)
        this.previewSelection(this.#selectionPreview); }
    previewSelection(value) { this.#selectionPreview = value; const keys = new Set(value?.objects.map(o => o.key)); for (const [key, base] of this.#selectionNodes) {
        const p = value && keys.has(key) ? transformedPoint(base, value.center, value.dx, value.dy, value.angle) : base;
        base.node.position.set(p.x, p.y);
        base.node.angle = base.angle + (value && keys.has(key) ? value.angle : 0);
    } }
    #cardNodes = new Map();
    #cardRows = [];
    previewCard(card) {
        for (const row of this.#cardRows) {
            const node = this.#cardNodes.get(row.id), value = card?.id === row.id ? card : row;
            if (node) {
                node.position.set(value.x, value.y);
                node.angle = value.rotation;
            }
        }
    }
    #imagePreview;
    #imagePlacements = [];
    previewImage(image) {
        this.#imagePreview = image;
        for (const placement of this.#imagePlacements) {
            const sprite = this.#imageSprites.get(placement.id);
            const row = image?.id === placement.id ? image : placement;
            if (sprite) {
                sprite.position.set(row.x, row.y);
                sprite.angle = row.rotation;
                sprite.scale.set(row.scale);
            }
        }
    }
    constructor(board) {
        this.board = board;
    }
    layer(id, order) {
        const layer = this.board.createLayer(`native:${id}`, order);
        this.#layers.push(layer);
        return layer.native().container;
    }
    clear() {
        this.#generation++;
        this.#imageSprites.clear();
        this.#cardNodes.clear();
        this.#selectionNodes.clear();
        this.#staticKey = '';
        this.#visionKey = '';
        this.#lightState = undefined;
        this.clearVision();
        this.clearFog();
        cancelAnimationFrame(this.#frame);
        // Shaders own bindings to the light buffer; detach them before freeing its source.
        this.#shaders?.dispose();
        this.#shaders = undefined;
        this.#lightMap?.dispose();
        this.#lightMap = undefined;
        for (const layer of this.#layers.splice(0).reverse())
            layer.dispose();
        for (const texture of this.#textures)
            texture.destroy(true);
        this.#textures.clear();
        for (const bitmap of this.#bitmaps)
            bitmap.close();
        this.#bitmaps.clear();
    }
    dispose() { if (this.#closed)
        return; this.#closed = true; this.#abort.abort(); this.clear(); }
    render(state, cell, width, height, gm) {
        if (this.#closed)
            return;
        const profile = renderingPreferences.current().name;
        const staticKey = this.#keys.static(state, cell, width, height, gm, profile);
        const visionKey = this.#keys.vision(state);
        if (staticKey === this.#staticKey && this.#lightState) {
            this.fog(state, cell, width, height, gm);
            if (visionKey !== this.#visionKey) {
                this.darkness({ ...this.#lightState, vision: state.vision, previewTokenVision: state.previewTokenVision }, cell, width, height, gm);
                this.#visionKey = visionKey;
            }
            return;
        }
        this.clear();
        this.#staticKey = staticKey;
        this.#visionKey = visionKey;
        const visit = this.#generation;
        const quality = effectQuality(profile);
        const lightState = { ...state, lights: effectLights(state, cell, width, height) };
        this.#lightState = lightState;
        const ambient = Math.max(.08, 1 - sceneDarkness(state.lighting));
        const lightMap = this.#lightMap = new SceneLightMap(width, height, quality.lightMap, ambient);
        const stamps = [];
        const readLight = state.particles.some(e => (e.light_response ?? 0) > 0) && quality.particles > 0;
        const imageLayer = this.layer("images", 150);
        imageLayer.sortableChildren = true;
        this.#imagePlacements = state.images;
        for (const placement of [...state.images].sort((a, b) => a.z_index - b.z_index)) {
            if (!placement.src)
                continue;
            void this.image(placement.src, visit).then(texture => {
                if (!texture)
                    return;
                const sprite = new Sprite(texture);
                sprite.position.set(placement.x, placement.y);
                sprite.anchor.set(.5);
                sprite.scale.set(placement.scale);
                sprite.angle = placement.rotation;
                if (placement.layer === "gm")
                    sprite.alpha = .55;
                sprite.zIndex = placement.z_index;
                this.#imageSprites.set(placement.id, sprite);
                this.registerSelection(`image:${placement.id}`, sprite);
                imageLayer.addChild(sprite);
                this.previewImage(this.#imagePreview);
                this.previewSelection(this.#selectionPreview);
            }).catch(() => { });
        }
        const drawings = this.layer("drawings", 185);
        for (const row of state.drawings?.rows ?? []) {
            const a = row.points[0], b = row.points.at(-1);
            if (row.kind === 'text') {
                const text = new Text({ text: row.text, style: { fontFamily: 'sans-serif', fontSize: row.fontSize, fill: row.color } });
                text.position.set(a.x, a.y);
                text.angle = row.rotation ?? 0;
                text.alpha = row.opacity;
                drawings.addChild(text);
                this.registerSelection(`drawing:${row.id}`, text);
                continue;
            }
            const g = new Graphics();
            if (row.kind === 'rect')
                g.rect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y));
            else if (row.kind === 'ellipse')
                g.ellipse((a.x + b.x) / 2, (a.y + b.y) / 2, Math.abs(b.x - a.x) / 2, Math.abs(b.y - a.y) / 2);
            else {
                g.moveTo(a.x, a.y);
                for (const p of row.points.slice(1))
                    g.lineTo(p.x, p.y);
                if (row.points.length === 1)
                    g.lineTo(a.x + .01, a.y);
                if (row.kind === 'arrow')
                    for (const p of arrowHead(row))
                        g.moveTo(b.x, b.y).lineTo(p.x, p.y);
            }
            if (row.fill !== 'none' && ['rect', 'ellipse'].includes(row.kind))
                g.fill(row.fill);
            g.stroke({ color: row.color, width: row.width, cap: 'round', join: 'round' });
            g.alpha = row.opacity;
            g.pivot.set(a.x, a.y);
            g.position.set(a.x, a.y);
            g.angle = row.rotation ?? 0;
            drawings.addChild(g);
            this.registerSelection(`drawing:${row.id}`, g);
        }
        const zones = this.layer("zones", 180);
        for (const zone of state.zones.filter(z => z.enabled)) {
            const g = zone.geometry, shape = new Graphics();
            if (g.shape === "circle")
                shape.circle(g.x ?? 0, g.y ?? 0, g.radius ?? 1);
            else if (g.shape === "rect")
                shape.rect(g.x ?? 0, g.y ?? 0, g.width ?? 1, g.height ?? 1);
            else
                shape.poly((g.points ?? []).flatMap(p => [p.x, p.y]));
            shape.fill({ color: "#c9a44c", alpha: .18 }).stroke({ color: "#c9a44c", width: 2 });
            zones.addChild(shape);
            this.registerSelection(`zone:${zone.id}`, shape);
        }
        this.darkness(lightState, cell, width, height, gm);
        const lights = this.layer("lights", 240);
        const animatedLights = [];
        for (const light of lightState.lights) {
            if (!light.enabled)
                continue;
            const radius = light.dim_radius === 0 ? Math.hypot(width, height) * 2 : Math.max(light.dim_radius, light.bright_radius) * cell;
            const polygon = visibilityPolygon(light, radius, state.walls.filter(w => w.blocks_light !== 0 && w.light_behavior !== "pass").map(w => ({ ...w, blocks_sight: w.blocks_light, vision_behavior: w.light_behavior })));
            if (radius <= 0)
                continue;
            const mask = new Graphics().poly(polygon.flatMap(p => [p.x, p.y])).fill("white");
            const canvas = document.createElement("canvas");
            canvas.width = canvas.height = 256;
            const context = canvas.getContext("2d");
            paintAnimatedLight(context, light, 128, 128, 128, quality.fps ? performance.now() : 0);
            stamps.push({ canvas, x: light.x, y: light.y, radius, polygon });
            const texture = Texture.from(canvas);
            this.#textures.add(texture);
            const glow = new Sprite(texture);
            glow.anchor.set(.5);
            glow.position.set(light.x, light.y);
            glow.width = glow.height = radius * 2;
            glow.alpha = 1;
            glow.blendMode = "add";
            glow.mask = mask;
            const group = new Container();
            group.addChild(mask, glow);
            lights.addChild(group);
            this.registerSelection(`light:${light.id}`, group);
            animatedLights.push({ light, glow, canvas, texture });
        }
        lightMap.update(stamps, readLight);
        const cards = this.layer("cards", 210);
        this.#cardRows = state.cards;
        for (const card of [...state.cards].sort((a, b) => (a.z_index ?? 0) - (b.z_index ?? 0))) {
            const node = new Container();
            node.position.set(card.x, card.y);
            node.angle = card.rotation;
            node.scale.set(card.scale || 1);
            cards.addChild(node);
            this.#cardNodes.set(card.id, node);
            this.registerSelection(`card:${card.id}`, node);
            node.addChild(new Graphics().roundRect(-28, -40, 56, 80, 5).fill("#332d29").stroke({ color: "#c9a44c", width: 2 }));
            if (card.card?.src)
                void this.image(card.card.src, visit).then(texture => {
                    if (!texture)
                        return;
                    const sprite = new Sprite(texture);
                    sprite.anchor.set(.5);
                    sprite.width = 56;
                    sprite.height = 80;
                    node.addChild(sprite);
                }).catch(() => { });
        }
        this.fog(state, cell, width, height, gm);
        const effects = this.layer("particles", 250);
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255,255,255,1)');
        gradient.addColorStop(.35, 'rgba(255,255,255,.75)');
        gradient.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);
        const dotTexture = Texture.from(canvas);
        this.#textures.add(dotTexture);
        const particles = [];
        let remaining = quality.particleLimit;
        for (const e of state.particles) {
            if (!e.enabled || !quality.particles)
                continue;
            if (remaining <= 0)
                break;
            const emitter = { ...e, density: e.density * quality.particles };
            const samples = particlesOf(emitter, 0, cell).slice(0, remaining);
            remaining -= samples.length;
            const group = new Container();
            effects.addChild(group);
            this.registerSelection(`particle:${e.id}`, group);
            particles.push({ emitter, dots: samples.map(() => { const dot = new Sprite(dotTexture); dot.anchor.set(.5); group.addChild(dot); return dot; }) });
        }
        const movingLights = animatedLights.some(({ light }) => light.animation && light.animation !== 'none');
        this.#shaders = mountShaders(this.layer("shaders", 245), state, cell, width, height, lightMap.texture, ambient, profile, (key, node) => this.registerSelection(key, node));
        const started = performance.now();
        let lastLightFrame = 0, lastFrame = 0;
        const tick = () => {
            if (this.#closed || visit !== this.#generation)
                return;
            if (document.hidden) {
                this.#frame = requestAnimationFrame(tick);
                return;
            }
            const clock = performance.now();
            if (quality.fps && clock - lastFrame < 1000 / quality.fps) {
                this.#frame = requestAnimationFrame(tick);
                return;
            }
            lastFrame = clock;
            const time = quality.fps ? (clock - started) / 1000 : 0;
            this.#shaders?.tick(time);
            const now = performance.now();
            if (movingLights && quality.lightFps && now - lastLightFrame >= 1000 / quality.lightFps) {
                lastLightFrame = now;
                for (const { light, canvas, texture } of animatedLights) {
                    if (!light.animation || light.animation === 'none')
                        continue;
                    const ctx = canvas.getContext('2d');
                    ctx.clearRect(0, 0, 256, 256);
                    paintAnimatedLight(ctx, light, 128, 128, 128, now);
                    texture.source.update();
                }
                lightMap.update(stamps, readLight);
            }
            for (const { emitter, dots } of particles) {
                particlesOf(emitter, time * 1000, cell).forEach((particle, index) => {
                    const dot = dots[index];
                    if (!dot)
                        return;
                    dot.position.set(particle.x, particle.y);
                    dot.rotation = particle.rotation;
                    dot.width = particle.size * 2 * particle.aspect;
                    dot.height = particle.size * 2;
                    dot.alpha = particle.alpha;
                    dot.tint = lightMap.tint(particle.tint, particle.x, particle.y, emitter.light_response ?? 0);
                    dot.blendMode = particle.blend;
                });
            }
            if (quality.fps && (movingLights || particles.length || state.shaders.some(s => s.enabled)))
                this.#frame = requestAnimationFrame(tick);
        };
        if (animatedLights.length || particles.length || state.shaders.some(s => s.enabled))
            tick();
    }
    clearVision() {
        this.#visionLayer?.dispose();
        this.#visionLayer = undefined;
        this.#visionTexture?.destroy(true);
        this.#visionTexture = undefined;
        this.#visionSprite = undefined;
        this.#visionCanvas = undefined;
    }
    darkness(state, cell, width, height, gm) {
        const darkness = sceneDarkness(state.lighting);
        if (darkness === 0) {
            this.clearVision();
            return;
        }
        const limited = !gm || !!state.previewTokenVision;
        const scale = Math.min(1, 2048 / Math.max(width, height));
        const canvas = this.#visionCanvas ??= document.createElement("canvas");
        const w = Math.max(1, Math.ceil(width * scale)), h = Math.max(1, Math.ceil(height * scale));
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w;
            canvas.height = h;
        }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, w, h);
        ctx.scale(scale, scale);
        ctx.fillStyle = `rgba(0,0,0,${darkness})`;
        ctx.fillRect(0, 0, width, height);
        for (const light of state.lights.filter(l => l.enabled && !limited)) {
            const radius = light.dim_radius === 0 ? Math.hypot(width, height) * 2 : Math.max(light.dim_radius, light.bright_radius) * cell;
            if (radius <= 0)
                continue;
            ctx.save();
            ctx.beginPath();
            const polygon = visibilityPolygon(light, radius, state.walls.filter(w => w.blocks_light !== 0 && w.light_behavior !== "pass").map(w => ({ ...w, blocks_sight: w.blocks_light, vision_behavior: w.light_behavior })));
            polygon.forEach((p, i) => { if (i === 0)
                ctx.moveTo(p.x, p.y);
            else
                ctx.lineTo(p.x, p.y); });
            ctx.closePath();
            ctx.clip();
            ctx.globalCompositeOperation = "destination-out";
            const gradient = ctx.createRadialGradient(light.x, light.y, Math.min(light.bright_radius * cell, radius * .99), light.x, light.y, radius);
            gradient.addColorStop(0, `rgba(0,0,0,${light.intensity})`);
            gradient.addColorStop(1, "transparent");
            ctx.fillStyle = gradient;
            ctx.fillRect(light.x - radius, light.y - radius, radius * 2, radius * 2);
            ctx.restore();
        }
        if (limited) {
            // Token vision reveals the map through the darkness, as in the legacy.
            // Keep the configured veil outside sight instead of painting a second,
            // always-opaque mask that survives the scene-light switch.
            ctx.save();
            ctx.globalCompositeOperation = "destination-out";
            ctx.fillStyle = "#000";
            for (const source of state.vision) {
                const polygon = visibilityPolygon(source, source.radius > 0 ? source.radius : Math.hypot(width, height) * 2, state.walls);
                ctx.beginPath();
                polygon.forEach((p, i) => { if (i === 0)
                    ctx.moveTo(p.x, p.y);
                else
                    ctx.lineTo(p.x, p.y); });
                ctx.closePath();
                ctx.fill();
            }
            ctx.restore();
        }
        if (!this.#visionTexture) {
            this.#visionTexture = Texture.from(canvas);
            this.#visionLayer = this.board.createLayer('native:vision', 285);
            this.#visionSprite = new Sprite(this.#visionTexture);
            this.#visionLayer.native().container.addChild(this.#visionSprite);
        }
        else
            this.#visionTexture.source.update();
        this.#visionSprite.scale.set(1 / scale);
        this.#visionSprite.alpha = gm && !state.previewTokenVision ? .5 : 1;
    }
    clearFog() {
        this.#fogLayer?.dispose(); this.#fogLayer = undefined;
        this.#fogTexture?.destroy(true); this.#fogTexture = undefined;
        this.#fogCanvas = undefined; this.#fogSprite = undefined; this.#fogKey = "";
    }
    fog(state, cell, width, height, gm) {
        if (!state.fog.enabled || state.lighting.mode !== 'manual') {
            this.clearFog(); return;
        }
        const key = `${cell}:${width}:${height}:${gm}:${this.#keys.part(state.fog)}`;
        if (key === this.#fogKey) return;
        this.#fogKey = key;
        // Bounded texture dimensions even for giant maps; world coordinates stay unchanged.
        const scale = Math.min(1, 2048 / Math.max(width, height));
        const canvas = this.#fogCanvas ??= document.createElement("canvas");
        const w = Math.ceil(width * scale), h = Math.ceil(height * scale);
        if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalCompositeOperation = "source-over";
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.scale(scale, scale);
        if (state.fog.enabled && state.fog.baseline === "hide_all") {
            ctx.fillStyle = "black";
            ctx.fillRect(0, 0, width, height);
        }
        for (const op of state.fog.enabled ? state.fog.ops : []) {
            const geom = op.geom;
            ctx.globalCompositeOperation = op.mode === "reveal" ? "destination-out" : "source-over";
            ctx.beginPath();
            if (op.shape === "circle")
                ctx.arc((geom.center_x_cells ?? 0) * cell, (geom.center_y_cells ?? 0) * cell, Math.max(0, geom.radius_cells ?? 0) * cell, 0, Math.PI * 2);
            else if (op.shape === "square") {
                const size = (geom.size_cells ?? 0) * cell;
                ctx.rect((geom.center_x_cells ?? 0) * cell - size / 2, (geom.center_y_cells ?? 0) * cell - size / 2, size, size);
            }
            else
                for (const [i, point] of (geom.points_cells ?? []).entries()) {
                    const x = (point[0] ?? 0) * cell, y = (point[1] ?? 0) * cell;
                    if (i === 0)
                        ctx.moveTo(x, y);
                    else
                        ctx.lineTo(x, y);
                }
            ctx.closePath();
            ctx.fill();
        }
        if (!this.#fogTexture) {
            this.#fogTexture = Texture.from(canvas);
            this.#fogSprite = new Sprite(this.#fogTexture);
            this.#fogLayer = this.board.createLayer("native:fog", 290);
            this.#fogLayer.native().container.addChild(this.#fogSprite);
        }
        this.#fogTexture.source.update();
        this.#fogSprite.scale.set(1 / scale);
        this.#fogSprite.alpha = gm ? (state.fog.gmOpacity ?? .5) : 1;
    }
    async image(url, visit) {
        const response = await fetch(url, { signal: this.#abort.signal, credentials: "same-origin" });
        if (!response.ok)
            return;
        const bitmap = await createImageBitmap(await response.blob());
        if (this.#closed || visit !== this.#generation) {
            bitmap.close();
            return;
        }
        this.#bitmaps.add(bitmap);
        const texture = Texture.from(bitmap);
        this.#textures.add(texture);
        return texture;
    }
}
