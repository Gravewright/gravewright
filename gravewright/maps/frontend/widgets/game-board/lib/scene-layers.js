import { transformedPoint } from '../../../features/selection/model/objects.js';
import { arrowHead } from '../../../features/drawing/model/drawing.js';
import { Container, Graphics, Sprite, Texture, Text } from "pixi.js";
import { effectQuality } from "../../../shared/rendering/effect-quality.js";
import { renderingPreferences } from "../../../shared/rendering/render-profile.js";
import { SceneLightMap } from "./scene-light-map.js";
import { effectLights } from "../model/effect-lighting.js";
import { AnimatedLight, LightTexturePool } from "./animated-light.js";
import { particlesOf } from "../../../features/effects/model/particle-profiles.js";
import { mountShaders } from "./scene-shaders.js";
import { SceneRenderKey } from "../model/scene-render-key.js";
import { SceneImageArt } from "../model/scene-image-art.js";
import { surfaceArtRows, loadSurfaceArt } from "../model/scene-surface-art.js";
import { sceneDarkness } from "../model/scene-darkness.js";
import { createVisibilityContext, visibilityPolygon } from "../model/visibility-polygon.js";
import { VisibilityJobs } from "../model/visibility-jobs.js";
import { doorArt } from "../model/door-art.js";
import { imageComponentKeys, imageComponentTransform } from '../../../features/images/model/image-components.js';
import { isGMImage, imageMarkerVisible } from '../../../features/images/model/image-layer.js';
/** All GPU, animation and image resources here belong to a single mounted block. */
export class SceneLayers {
    board;
    #layers = [];
    #abort = new AbortController();
    #imageLoads = new Map();
    #bitmapLoads = new Map();
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
    #lightTextures;
    #lightPolygons = [];
    #visibilityJobs;
    #visionPolygons = [];
    #visionIdentity = '';
    #visionFrame = 0;
    #pendingVision;
    #shaders;
    #bitmaps = new Set();
    #generation = 0;
    #closed = false;
    #imageSprites = new Map();
    #imageArt;
    #surfaceArt;
    #surfaceRows = new Map();
    #surfaceSprites = new Map();
    #zoneLayer;
    #zoneKey = '';
    #sceneIdentity = '';
    #gm = false;
    #selectionNodes = new Map();
    #componentOrigins = new Map();
    #selectionPreview;
    registerSelection(key, node) { this.#selectionNodes.set(key, { node, x: node.x, y: node.y, angle: node.angle,
        scaleX: node.scale.x, scaleY: node.scale.y }); if (this.#selectionPreview || this.#imagePreview)
        this.previewSelection(this.#selectionPreview); }
    previewSelection(value) { this.#selectionPreview = value; const keys = new Set(value?.objects.map(o => o.key));
        for (const image of this.#imagePlacements) if (keys.has(`image:${image.id}`))
            for (const key of imageComponentKeys(image)) keys.add(key);
        for (const [key, base] of this.#selectionNodes) {
        const p = value && keys.has(key) ? transformedPoint(base, value.center, value.dx, value.dy, value.angle) : base;
        base.node.position.set(p.x, p.y);
        base.node.angle = base.angle + (value && keys.has(key) ? value.angle : 0);
        base.node.scale.set(base.scaleX, base.scaleY);
    }
        const image = this.#imagePreview, original = image && this.#imagePlacements.find(row => row.id === image.id);
        if (original) {
            const sprite = this.#imageSprites.get(image.id);
            if (sprite) { sprite.position.set(image.x, image.y); sprite.angle = image.rotation; sprite.scale.set(image.scale); }
            for (const key of imageComponentKeys(original)) {
                const base = this.#selectionNodes.get(key);
                const next = base && imageComponentTransform(original, image, base, this.#componentOrigins.get(key));
                if (next) { base.node.position.set(next.x, next.y); base.node.angle = next.angle;
                    base.node.scale.set(next.scaleX, next.scaleY); }
            }
        }
        this.board.invalidate?.(); }
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
        this.board.invalidate?.();
    }
    #imagePreview;
    #imagePlacements = [];
    #imageRows = new Map();
    #imageLayer;
    #gmImageLayer;
    #editingLayer = 'game';
    setEditingLayer(layer) {
        if (layer === this.#editingLayer) return;
        this.#editingLayer = layer;
        for (const row of this.#imagePlacements) {
            const sprite = this.#imageSprites.get(row.id);
            if (sprite) sprite.visible = imageMarkerVisible(row, layer, this.#gm);
        }
        this.board.invalidate?.();
    }
    syncImages(images) {
        this.#imagePlacements = images;
        this.#imageRows = new Map(images.map(row => [row.id, row]));
        this.#imageArt.sync(images.filter(row => row.empty !== true && !row.surface && !row.surfacePlane?.group));
        this.syncImageTransforms();
    }
    syncSurfaces(images, width, height) {
        const rows = surfaceArtRows(images, width, height);
        this.#surfaceRows = new Map(rows.map(row => [row.id, row]));
        this.#surfaceArt.sync(rows);
    }
    syncImageTransforms() {
        for (const row of this.#imagePlacements) this.syncImageTransform(row);
        this.previewImage(this.#imagePreview);
    }
    syncImageTransform(row) {
        const sprite = this.#imageSprites.get(row.id);
        if (!sprite) return;
        const hidden = isGMImage(row);
        const layer = hidden ? this.#gmImageLayer : this.#imageLayer;
        if (layer && sprite.parent !== layer) layer.addChild(sprite);
        sprite.alpha = hidden ? .55 : 1;
        sprite.visible = imageMarkerVisible(row, this.#editingLayer, this.#gm);
        sprite.zIndex = row.z_index;
        sprite.position.set(row.x, row.y);
        sprite.angle = row.rotation;
        sprite.scale.set(row.scale);
        this.#selectionNodes.set(`image:${row.id}`, {node:sprite,x:row.x,y:row.y,angle:row.rotation,
            scaleX:row.scale,scaleY:row.scale});
    }
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
        this.previewSelection(this.#selectionPreview);
    }
    constructor(board) {
        this.board = board;
        this.#imageArt = new SceneImageArt({
            load: async (url, signal) => {
                const response = await fetch(url, { signal, credentials: 'same-origin' });
                if (!response.ok) return;
                const bitmap = await createImageBitmap(await response.blob());
                if (signal.aborted) { bitmap.close(); return; }
                return { texture: Texture.from(bitmap), bitmap, bytes: bitmap.width * bitmap.height * 4 };
            },
            apply: (id, { texture }) => {
                let sprite = this.#imageSprites.get(id);
                if (sprite) sprite.texture = texture;
                else {
                    sprite = new Sprite(texture);
                    sprite.anchor.set(.5);
                    this.#imageSprites.set(id, sprite);
                    this.#imageLayer.addChild(sprite);
                }
                const row = this.#imageRows.get(id);
                if (row) this.syncImageTransform(row);
                if (this.#selectionPreview || this.#imagePreview) this.previewSelection(this.#selectionPreview);
                this.board.invalidate?.();
            },
            remove: id => {
                const sprite = this.#imageSprites.get(id);
                if (sprite) { sprite.parent?.removeChild(sprite); sprite.destroy(); }
                this.#imageSprites.delete(id);
                this.#selectionNodes.delete(`image:${id}`);
            },
            release: ({ texture, bitmap }) => { texture.destroy(true); bitmap.close(); },
        });
        this.#surfaceArt = new SceneImageArt({
            load: (source, signal) => this.surfaceArt(source, signal),
            apply: (id, { texture }) => {
                const row = this.#surfaceRows.get(id);
                if (!row) return;
                let sprite = this.#surfaceSprites.get(id);
                if (sprite) sprite.texture = texture;
                else {
                    sprite = new Sprite(texture);
                    this.#surfaceSprites.set(id, sprite);
                    this.#imageLayer.addChild(sprite);
                }
                if (row.placementId) {
                    sprite.anchor.set(.5);
                    this.#imageSprites.set(row.placementId, sprite);
                    const placement = this.#imageRows.get(row.placementId);
                    if (placement) this.syncImageTransform(placement);
                    if (this.#selectionPreview || this.#imagePreview) this.previewSelection(this.#selectionPreview);
                } else {
                    sprite.position.set(row.bounds.left, row.bounds.top);
                    sprite.zIndex = row.order;
                }
                this.board.invalidate?.();
            },
            remove: id => {
                const sprite = this.#surfaceSprites.get(id);
                if (!sprite) return;
                this.#surfaceSprites.delete(id);
                for (const [placementId, image] of this.#imageSprites) if (image === sprite) {
                    this.#imageSprites.delete(placementId);
                    this.#selectionNodes.delete(`image:${placementId}`);
                }
                sprite.parent?.removeChild(sprite);
                sprite.destroy();
            },
            release: ({ texture, canvas }) => {
                texture.destroy(true);
                canvas.width = canvas.height = 1;
            },
        });
    }
    layer(id, order) {
        const layer = this.board.createLayer(`native:${id}`, order);
        this.#layers.push(layer);
        return layer.native().container;
    }
    clear(preserveImageArt = false) {
        this.#generation++;
        this.#imageArt.reset(preserveImageArt);
        this.#surfaceArt.reset(preserveImageArt);
        this.#surfaceRows.clear();
        this.#abort.abort();
        this.#abort = new AbortController();
        this.#imageLoads.clear();
        this.#bitmapLoads.clear();
        this.#imageSprites.clear();
        this.#cardNodes.clear();
        this.#selectionNodes.clear();
        this.#componentOrigins.clear();
        this.#staticKey = '';
        this.#zoneLayer = undefined;
        this.#zoneKey = '';
        this.#visionKey = '';
        this.#lightState = undefined;
        this.#lightPolygons = [];
        cancelAnimationFrame(this.#visionFrame);
        this.#visionFrame = 0;
        this.#pendingVision = undefined;
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
        this.#lightTextures?.dispose();
        this.#lightTextures = undefined;
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
        const sceneIdentity = JSON.stringify([state.containerId, state.blockId, state.sceneId, gm]);
        this.#gm = gm;
        const staticKey = this.#keys.static(state, cell, width, height, gm, profile);
        const visionKey = this.#keys.vision(state);
        if (staticKey === this.#staticKey && this.#lightState) {
            if (state.images !== this.#imagePlacements) this.syncImages(state.images);
            this.zones(state, gm);
            this.fog(state, cell, width, height, gm);
            if (visionKey !== this.#visionKey) {
                this.queueVision({ ...this.#lightState, vision: state.vision, previewTokenVision: state.previewTokenVision }, cell, width, height, gm);
                this.#visionKey = visionKey;
            }
            this.board.invalidate?.();
            return;
        }
        this.clear(sceneIdentity === this.#sceneIdentity);
        this.#sceneIdentity = sceneIdentity;
        this.#componentOrigins = new Map([['light', state.lights], ['particle', state.particles], ['shader', state.shaders]]
            .flatMap(([kind, rows]) => rows.map(row => [`${kind}:${row.id}`, row])));
        this.#staticKey = staticKey;
        this.#visionKey = visionKey;
        const visit = this.#generation;
        const quality = effectQuality(profile);
        const lightState = { ...state, lights: effectLights(state, cell, width, height) };
        this.#lightState = lightState;
        const lightWalls = state.walls.filter(w => w.blocks_light !== 0 && w.light_behavior !== 'pass')
            .map(w => ({ ...w, blocks_sight: w.blocks_light, vision_behavior: w.light_behavior }));
        const lightContext = createVisibilityContext(lightWalls);
        for (const light of lightState.lights) {
            if (!light.enabled) continue;
            const radius = light.dim_radius === 0 ? Math.hypot(width, height) * 2 : Math.max(light.dim_radius, light.bright_radius) * cell;
            if (radius > 0) this.#lightPolygons.push({ light, radius, polygon: visibilityPolygon(light, radius, lightWalls, lightContext) });
        }
        const lightTextures = this.#lightTextures = new LightTexturePool();
        const ambient = Math.max(.08, 1 - sceneDarkness(state.lighting));
        const readLight = state.particles.some(e => (e.light_response ?? 0) > 0) && quality.particles > 0;
        const needsShaders = quality.shaders && state.shaders.some(s => s.enabled);
        const lightMap = this.#lightMap = new SceneLightMap(width, height, quality.lightMap, ambient, {
            renderToTexture: this.board.renderToTexture?.bind(this.board), textures: lightTextures,
            sampleOnly: !needsShaders,
        });
        const stamps = [];
        const needsLightMap = readLight || needsShaders;
        const imageLayer = this.layer("images", 150);
        imageLayer.sortableChildren = true;
        this.#imageLayer = imageLayer;
        this.#gmImageLayer = this.layer('gm-image-layer', 155);
        this.#gmImageLayer.sortableChildren = true;
        this.#imagePlacements = state.images;
        for (const placement of [...state.images].sort((a, b) => a.z_index - b.z_index)) {
            if (placement.empty === true) {
                if (gm) {
                    const marker = new Graphics();
                    const width = placement.natural_width, height = placement.natural_height;
                    const arm = Math.min(width, height) * .16;
                    marker.rect(-width / 2, -height / 2, width, height)
                        .fill({ color: 0xc8a35f, alpha: .06 })
                        .stroke({ color: 0xc8a35f, alpha: .65, width: 1.5 });
                    marker.moveTo(-arm, 0).lineTo(arm, 0).moveTo(0, -arm).lineTo(0, arm)
                        .stroke({ color: 0xc8a35f, alpha: .8, width: 1.5 });
                    this.#imageSprites.set(placement.id, marker);
                    imageLayer.addChild(marker);
                }
                continue;
            }
        }
        this.syncImages(this.#imagePlacements);
        this.syncSurfaces(this.#imagePlacements, width, height);
        const doorImages = state.walls.map(doorArt).filter(Boolean);
        if (doorImages.length) {
            const doors = this.layer('door-art', 170);
            for (const art of doorImages) {
                void this.image(art.src, visit).then(texture => {
                    if (!texture || this.#closed || visit !== this.#generation) return;
                    const sprite = new Sprite(texture);
                    sprite.anchor.set(0, .5);
                    sprite.position.set(art.x, art.y);
                    sprite.width = art.width;
                    sprite.height = art.height;
                    sprite.angle = art.angle;
                    doors.addChild(sprite);
                    this.board.invalidate?.();
                }).catch(() => { });
            }
        }
        const drawings = this.layer("drawings", 185);
        for (const row of state.drawings?.rows ?? []) {
            const a = row.points[0], b = row.points.at(-1);
            if (row.kind === 'text') {
                const text = new Text({ text: row.text, style: { fontFamily: 'sans-serif', fontSize: row.fontSize, fill: row.color } });
                text.position.set(a.x, a.y);
                text.angle = row.rotation ?? 0;
                text.alpha = row.opacity * (gm && row.audience === 'gm' ? .55 : 1);
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
            g.alpha = row.opacity * (gm && row.audience === 'gm' ? .55 : 1);
            g.pivot.set(a.x, a.y);
            g.position.set(a.x, a.y);
            g.angle = row.rotation ?? 0;
            drawings.addChild(g);
            this.registerSelection(`drawing:${row.id}`, g);
        }
        this.zones(state, gm);
        this.darkness(lightState, cell, width, height, gm);
        const lights = this.layer("lights", 240);
        const animatedLights = [];
        for (const { light, radius, polygon } of this.#lightPolygons) {
            const mask = new Graphics().poly(polygon.flatMap(p => [p.x, p.y])).fill("white");
            const animated = new AnimatedLight(light, radius, lightTextures, quality.fps ? performance.now() : 0);
            stamps.push({ light, x: light.x, y: light.y, radius, polygon });
            animated.node.mask = mask;
            const group = new Container();
            group.addChild(mask, animated.node);
            lights.addChild(group);
            this.registerSelection(`light:${light.id}`, group);
            animatedLights.push(animated);
        }
        if (needsLightMap) lightMap.update(stamps, readLight, quality.fps ? performance.now() : 0);
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
                    if (!texture || this.#closed || visit !== this.#generation)
                        return;
                    const sprite = new Sprite(texture);
                    sprite.anchor.set(.5);
                    sprite.width = 56;
                    sprite.height = 80;
                    node.addChild(sprite);
                    this.board.invalidate?.();
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
        const movingLights = animatedLights.some(light => light.animated);
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
                for (const light of animatedLights) if (light.animated) light.update(now);
                if (needsLightMap) lightMap.update(stamps, readLight, now);
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
            this.board.invalidate?.();
            if (quality.fps && (movingLights || particles.length || state.shaders.some(s => s.enabled)))
                this.#frame = requestAnimationFrame(tick);
        };
        if (animatedLights.length || particles.length || state.shaders.some(s => s.enabled))
            tick();
        this.board.invalidate?.();
    }
    clearVision() {
        cancelAnimationFrame(this.#visionFrame);
        this.#visionFrame = 0;
        this.#pendingVision = undefined;
        this.#visibilityJobs?.dispose();
        this.#visibilityJobs = undefined;
        this.#visionPolygons = [];
        this.#visionIdentity = '';
        this.#visionLayer?.dispose();
        this.#visionLayer = undefined;
        this.#visionTexture?.destroy(true);
        this.#visionTexture = undefined;
        this.#visionSprite = undefined;
        this.#visionCanvas = undefined;
    }
    queueVision(state, cell, width, height, gm) {
        if (sceneDarkness(state.lighting) === 0) { this.clearVision(); return; }
        // Revoke old observers before yielding; a worker may finish before RAF.
        const identity = this.visionIdentity(state, gm);
        if (identity !== this.#visionIdentity) {
            this.#visionIdentity = identity;
            this.#visionPolygons = [];
            this.#visibilityJobs?.cancel();
            this.paintDarkness(state, cell, width, height, gm, []);
        }
        if (identity === 'gm') {
            // The GM veil depends only on static scene inputs. Drop a queued
            // preview as well, so it cannot replace the unrestricted view.
            cancelAnimationFrame(this.#visionFrame);
            this.#visionFrame = 0;
            this.#pendingVision = undefined;
            return;
        }
        this.#pendingVision = [state, cell, width, height, gm];
        if (this.#visionFrame) return;
        this.#visionFrame = requestAnimationFrame(() => {
            this.#visionFrame = 0;
            const pending = this.#pendingVision;
            this.#pendingVision = undefined;
            if (!this.#closed && pending) this.darkness(...pending);
        });
    }
    visionIdentity(state, gm) {
        if (gm && !state.previewTokenVision) return 'gm';
        return JSON.stringify(state.vision.map(source => [source.sourceId ?? [source.x, source.y],
            source.radius, source.elevation, source.angle, source.rotation]));
    }
    darkness(state, cell, width, height, gm) {
        const darkness = sceneDarkness(state.lighting);
        if (darkness === 0) {
            this.clearVision();
            return;
        }
        const limited = !gm || !!state.previewTokenVision;
        if (!limited) {
            this.#visionIdentity = 'gm';
            this.#visibilityJobs?.cancel();
            this.paintDarkness(state, cell, width, height, gm, []);
            return;
        }
        // Keep the last completed frame only for the same observers and wall
        // revision. A selection, range, elevation or scene change closes it.
        const identity = this.visionIdentity(state, gm);
        const changed = identity !== this.#visionIdentity;
        if (changed) {
            this.#visionIdentity = identity;
            this.#visionPolygons = [];
            this.#visibilityJobs?.cancel();
        }
        this.#visibilityJobs ??= new VisibilityJobs(state.walls);
        const generation = this.#generation;
        let complete = false;
        this.#visibilityJobs.request(state.vision, Math.hypot(width, height) * 2, polygons => {
            if (this.#closed || generation !== this.#generation || identity !== this.#visionIdentity) return;
            complete = true;
            this.#visionPolygons = polygons;
            this.paintDarkness(state, cell, width, height, gm, polygons);
            this.board.invalidate?.();
        });
        // An unchanged observer already has a veil. Retain that texture until
        // the worker completes instead of repainting the same pixels each RAF.
        if (!complete && changed) this.paintDarkness(state, cell, width, height, gm, this.#visionPolygons);
    }
    paintDarkness(state, cell, width, height, gm, polygons) {
        const darkness = sceneDarkness(state.lighting);
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
        for (const { light, radius, polygon } of limited ? [] : this.#lightPolygons) {
            ctx.save();
            ctx.beginPath();
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
            for (const polygon of polygons) {
                ctx.beginPath();
                for (let i = 0; i < polygon.length; i += 2)
                    if (i === 0) ctx.moveTo(polygon[i], polygon[i + 1]);
                    else ctx.lineTo(polygon[i], polygon[i + 1]);
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
    image(url, visit) {
        // Sharing one decoded texture per URL avoids duplicate fetches and GPU uploads.
        let pending = this.#imageLoads.get(url);
        if (!pending) {
            pending = (async () => {
                const bitmap = await this.bitmap(url, visit);
                if (!bitmap || this.#closed || visit !== this.#generation) return;
                const texture = Texture.from(bitmap);
                this.#textures.add(texture);
                return texture;
            })();
            this.#imageLoads.set(url, pending);
        }
        return pending;
    }
    bitmap(url, visit) {
        let pending = this.#bitmapLoads.get(url);
        if (!pending) {
            pending = (async () => {
                const response = await fetch(url, { signal: this.#abort.signal, credentials: 'same-origin' });
                if (!response.ok) return;
                const bitmap = await createImageBitmap(await response.blob());
                if (this.#closed || visit !== this.#generation) { bitmap.close(); return; }
                this.#bitmaps.add(bitmap); return bitmap;
            })();
            this.#bitmapLoads.set(url, pending);
        }
        return pending;
    }
    async surfaceArt(source, signal) {
        const resource = await loadSurfaceArt(source, signal);
        return { ...resource, texture: Texture.from(resource.canvas) };
    }
    zones(state, gm) {
        const key = this.#keys.zones(state);
        if (key === this.#zoneKey) return;
        this.#zoneKey = key;
        const zones = this.#zoneLayer ??= this.layer('zones', 180);
        for (const child of zones.removeChildren()) child.destroy();
        for (const id of this.#selectionNodes.keys()) if (id.startsWith('zone:')) this.#selectionNodes.delete(id);
        for (const zone of state.zones.filter(z => z.enabled || gm && z.region)) {
            const g = zone.geometry, shape = new Graphics();
            if (g.shape === 'circle') shape.circle(g.x ?? 0, g.y ?? 0, g.radius ?? 1);
            else if (g.shape === 'rect') shape.rect(g.x ?? 0, g.y ?? 0, g.width ?? 1, g.height ?? 1);
            else shape.poly((g.points ?? []).flatMap(p => [p.x, p.y]));
            const color = zone.region && !zone.enabled ? '#7d8a94' : zone.region?.state === 'occupied' ? '#79d4b6' : '#c9a44c';
            shape.fill({ color, alpha: zone.enabled ? .18 : .05 }).stroke({ color, width: 2, alpha: zone.enabled ? 1 : .45 });
            zones.addChild(shape);
            this.registerSelection(`zone:${zone.id}`, shape);
        }
        this.board.invalidate?.();
    }
}
