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
import { VisibilityJobs } from "../model/visibility-jobs.js";
import { LightPolygons, lightWalls } from "../model/light-polygons.js";
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
    #last;
    #geometry = [];
    #profile;
    #quality;
    #started = 0;
    #effectRun = 0;
    #doorRun = 0;
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
    #lightPolygons;
    #lightRows = [];
    #lightWalls = [];
    #lightKey = '';
    #lightMapKey = '';
    #readLight = false;
    #needsLightMap = false;
    #shadersEnabled = false;
    #animatedLights = [];
    #stamps = [];
    #particles = [];
    #dotTexture;
    #doorLayer;
    #drawingLayer;
    #cardLayer;
    #lightLayer;
    #shaderLayer;
    #particleLayer;
    #markers = new Map();
    #lightNodes = new Map();
    #drawingEntries = new Map();
    #cardEntries = new Map();
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
    /**
     * Keep surface identities current with every image snapshot: a standalone
     * transform revokes the old coverage identity but reuses the same decoded
     * pixels, so its sprite is carried over to the new identity instead of
     * being destroyed. A later material change then still has its previous
     * finish to show while the replacement loads.
     */
    syncSurfaces(images, width, height) {
        const rows = surfaceArtRows(images, width, height);
        this.#surfaceRows = new Map(rows.map(row => [row.id, row]));
        const recycled = this.#recycledSurfaces = new Map();
        try { this.#surfaceArt.sync(rows); }
        finally {
            this.#recycledSurfaces = undefined;
            for (const [placementId, sprite] of recycled) {
                if (this.#imageSprites.get(placementId) === sprite) {
                    this.#imageSprites.delete(placementId);
                    this.#selectionNodes.delete(`image:${placementId}`);
                }
                sprite.parent?.removeChild(sprite);
                sprite.destroy();
            }
        }
    }
    #recycledSurfaces;
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
                const recycled = row.placementId && this.#recycledSurfaces?.get(row.placementId);
                if (!sprite && recycled) {
                    this.#recycledSurfaces.delete(row.placementId);
                    this.#surfaceSprites.set(id, sprite = recycled);
                }
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
                // During a snapshot sync the same placement may reappear under a new identity.
                const placementId = this.#recycledSurfaces && [...this.#imageSprites].find(([, image]) => image === sprite)?.[0];
                if (placementId !== undefined && placementId !== null && this.#recycledSurfaces) {
                    this.#recycledSurfaces.set(placementId, sprite);
                    return;
                }
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
    #dropSelection(prefix, retained) {
        for (const key of [...this.#selectionNodes.keys()])
            if (key.startsWith(prefix) && !retained?.has(key)) this.#selectionNodes.delete(key);
    }
    clear(preserveImageArt = false) {
        this.#generation++;
        this.#effectRun++;
        this.#imageArt.reset(preserveImageArt);
        this.#surfaceArt.reset(preserveImageArt);
        this.#surfaceRows.clear();
        this.#abort.abort();
        this.#abort = new AbortController();
        this.#imageLoads.clear();
        this.#bitmapLoads.clear();
        this.#imageSprites.clear();
        this.#markers.clear();
        this.#cardNodes.clear();
        this.#cardEntries.clear();
        this.#drawingEntries.clear();
        this.#selectionNodes.clear();
        this.#componentOrigins.clear();
        this.#last = undefined;
        this.#zoneLayer = undefined;
        this.#zoneKey = '';
        this.#visionKey = '';
        this.#lightState = undefined;
        this.#lightPolygons?.dispose();
        this.#lightPolygons = undefined;
        this.#lightRows = [];
        this.#lightWalls = [];
        this.#lightKey = '';
        this.#lightMapKey = '';
        this.#animatedLights = [];
        this.#lightNodes.clear();
        this.#stamps = [];
        this.#particles = [];
        this.#dotTexture = undefined;
        this.#imageLayer = this.#gmImageLayer = this.#doorLayer = this.#drawingLayer = this.#cardLayer = undefined;
        this.#lightLayer = this.#shaderLayer = this.#particleLayer = undefined;
        cancelAnimationFrame(this.#visionFrame);
        this.#visionFrame = 0;
        this.#pendingVision = undefined;
        this.clearVision();
        this.clearFog();
        cancelAnimationFrame(this.#frame);
        this.#frame = 0;
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
    /**
     * Each part of the scene has its own key. Only a different scene, role,
     * geometry or quality profile remounts everything; a drawing, a card or a
     * door refreshes the layers that actually read it.
     */
    render(state, cell, width, height, gm) {
        if (this.#closed)
            return;
        const profile = renderingPreferences.current().name;
        const keys = this.#keys.layers(state, cell, width, height, gm, profile);
        this.#gm = gm;
        let last = this.#last;
        if (keys.base !== last?.base) {
            const sceneIdentity = JSON.stringify([state.containerId, state.blockId, state.sceneId, gm]);
            this.clear(sceneIdentity === this.#sceneIdentity);
            this.#sceneIdentity = sceneIdentity;
            this.#mount(profile);
            last = undefined;
        }
        this.#last = keys;
        this.#geometry = [cell, width, height];
        const changed = {};
        for (const name of Object.keys(keys)) changed[name] = keys[name] !== last?.[name];
        if (changed.images) this.syncImageLayers(state.images, width, height, gm);
        else if (state.images !== this.#imagePlacements) {
            this.syncImages(state.images);
            this.syncSurfaces(state.images, width, height);
        }
        if (changed.walls) this.syncDoors(state.walls);
        if (changed.drawings) this.syncDrawings(state.drawings, gm);
        if (changed.cards) this.syncCards(state.cards);
        this.zones(state, gm);
        const effects = changed.walls || changed.lights || changed.particles || changed.shaders || changed.lighting;
        if (effects) this.syncEffects(state, cell, width, height, changed);
        this.fog(state, cell, width, height, gm);
        const visionKey = this.#keys.vision(state);
        const limited = !gm || !!state.previewTokenVision;
        if (last && changed.walls) {
            // A wall revision closes the last restricted vision frame, as a remount did.
            // The GM's unrestricted veil does not depend on observers.
            if (limited) this.#visionIdentity = '';
            this.#visibilityJobs?.setWalls(state.walls);
        }
        // The GM's unrestricted veil follows the light polygons. While the worker
        // still owes some, keep the current veil; the answer repaints it once.
        const awaitingLights = last && !limited && !changed.lighting && this.#lightPolygons.pending
            && this.#visionIdentity === 'gm' && visionKey === this.#visionKey;
        if (awaitingLights) { /* #lightRowsReady paints the veil. */ }
        else if (!last || changed.walls || changed.lighting || effects && !limited) {
            this.#visionKey = visionKey;
            this.darkness({ ...this.#lightState, vision: state.vision, previewTokenVision: state.previewTokenVision },
                cell, width, height, gm);
        }
        else if (visionKey !== this.#visionKey) {
            this.queueVision({ ...this.#lightState, vision: state.vision, previewTokenVision: state.previewTokenVision }, cell, width, height, gm);
            this.#visionKey = visionKey;
        }
        this.board.invalidate?.();
    }
    /** Mounted layers and resources shared by every part of one scene. */
    #mount(profile) {
        this.#profile = profile;
        this.#quality = effectQuality(profile);
        this.#started = performance.now();
        this.#lightTextures = new LightTexturePool();
        this.#lightPolygons = new LightPolygons({ onUpdate: rows => this.#lightRowsReady(rows) });
        this.#imageLayer = this.layer("images", 150);
        this.#imageLayer.sortableChildren = true;
        this.#gmImageLayer = this.layer('gm-image-layer', 155);
        this.#gmImageLayer.sortableChildren = true;
        this.#doorLayer = this.layer('door-art', 170);
        this.#drawingLayer = this.layer("drawings", 185);
        this.#cardLayer = this.layer("cards", 210);
        this.#lightLayer = this.layer("lights", 240);
        this.#shaderLayer = this.layer("shaders", 245);
        this.#particleLayer = this.layer("particles", 250);
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255,255,255,1)');
        gradient.addColorStop(.35, 'rgba(255,255,255,.75)');
        gradient.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);
        this.#dotTexture = Texture.from(canvas);
        this.#textures.add(this.#dotTexture);
    }
    /**
     * Membership, surfaces or placeholders changed: rebind the image art from
     * retained resources, as a remount did, without touching any other layer.
     */
    syncImageLayers(images, width, height, gm) {
        this.#imageArt.reset(true);
        this.#surfaceArt.reset(true);
        this.#surfaceRows.clear();
        for (const marker of this.#markers.values()) marker.destroy();
        this.#markers.clear();
        this.#imageSprites.clear();
        this.#dropSelection('image:');
        for (const placement of [...images].sort((a, b) => a.z_index - b.z_index)) {
            if (placement.empty !== true || !gm) continue;
            const marker = new Graphics();
            const width = placement.natural_width, height = placement.natural_height;
            const arm = Math.min(width, height) * .16;
            marker.rect(-width / 2, -height / 2, width, height)
                .fill({ color: 0xc8a35f, alpha: .06 })
                .stroke({ color: 0xc8a35f, alpha: .65, width: 1.5 });
            marker.moveTo(-arm, 0).lineTo(arm, 0).moveTo(0, -arm).lineTo(0, arm)
                .stroke({ color: 0xc8a35f, alpha: .8, width: 1.5 });
            this.#markers.set(placement.id, marker);
            this.#imageSprites.set(placement.id, marker);
            this.#imageLayer.addChild(marker);
        }
        this.#imagePlacements = images;
        this.syncImages(images);
        this.syncSurfaces(images, width, height);
    }
    syncDoors(walls) {
        const layer = this.#doorLayer, visit = this.#generation, run = ++this.#doorRun;
        // Door textures stay cached by URL, so the replacement lands before the next frame.
        for (const child of layer.removeChildren()) child.destroy();
        for (const art of walls.map(doorArt).filter(Boolean)) {
            void this.image(art.src, visit).then(texture => {
                if (!texture || this.#closed || visit !== this.#generation || run !== this.#doorRun) return;
                const sprite = new Sprite(texture);
                sprite.anchor.set(0, .5);
                sprite.position.set(art.x, art.y);
                sprite.width = art.width;
                sprite.height = art.height;
                sprite.angle = art.angle;
                layer.addChild(sprite);
                this.board.invalidate?.();
            }).catch(() => { });
        }
    }
    /** Rebuild only the drawings whose rows changed; collaborative strokes add one node each. */
    syncDrawings(drawings, gm) {
        const layer = this.#drawingLayer, previous = this.#drawingEntries, next = new Map();
        for (const [index, row] of (drawings?.rows ?? []).entries()) {
            const id = next.has(row.id) ? `${row.id}#${index}` : row.id;
            const key = this.#keys.part(row);
            let entry = previous.get(id);
            if (entry?.key === key) previous.delete(id);
            else {
                entry = { key, node: this.drawing(row, gm) };
                layer.addChild(entry.node);
                // A retained node keeps its registration; a live selection preview may have moved it.
                this.registerSelection(`drawing:${row.id}`, entry.node);
            }
            entry.node.zIndex = index;
            next.set(id, entry);
        }
        for (const { node } of previous.values()) node.destroy();
        this.#drawingEntries = next;
        this.#dropSelection('drawing:', new Set([...next.keys()].map(id => `drawing:${String(id).replace(/#\d+$/, '')}`)));
    }
    drawing(row, gm) {
        const a = row.points[0], b = row.points.at(-1);
        if (row.kind === 'text') {
            const text = new Text({ text: row.text, style: { fontFamily: 'sans-serif', fontSize: row.fontSize, fill: row.color } });
            text.position.set(a.x, a.y);
            text.angle = row.rotation ?? 0;
            text.alpha = row.opacity * (gm && row.audience === 'gm' ? .55 : 1);
            return text;
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
        return g;
    }
    /** Moving or turning a card updates its node; only a different face rebuilds it. */
    syncCards(cards) {
        const layer = this.#cardLayer, previous = this.#cardEntries, next = new Map(), visit = this.#generation;
        this.#cardRows = cards;
        this.#cardNodes = new Map();
        for (const [index, card] of [...cards].sort((a, b) => (a.z_index ?? 0) - (b.z_index ?? 0)).entries()) {
            const id = next.has(card.id) ? `${card.id}#${index}` : card.id;
            const { x: _x, y: _y, rotation: _rotation, scale: _scale, z_index: _z, ...face } = card;
            const key = JSON.stringify(face);
            let entry = previous.get(id);
            if (entry?.key === key) previous.delete(id);
            else {
                entry = { key, node: this.card(card, visit) };
                layer.addChild(entry.node);
            }
            const node = entry.node;
            node.position.set(card.x, card.y);
            node.angle = card.rotation;
            node.scale.set(card.scale || 1);
            node.zIndex = index;
            next.set(id, entry);
            this.#cardNodes.set(card.id, node);
            this.registerSelection(`card:${card.id}`, node);
        }
        for (const { node } of previous.values()) node.destroy({ children: true });
        this.#cardEntries = next;
        this.#dropSelection('card:', new Set(cards.map(card => `card:${card.id}`)));
    }
    card(card, visit) {
        const node = new Container();
        node.addChild(new Graphics().roundRect(-28, -40, 56, 80, 5).fill("#332d29").stroke({ color: "#c9a44c", width: 2 }));
        if (card.card?.src)
            void this.image(card.card.src, visit).then(texture => {
                if (!texture || this.#closed || visit !== this.#generation || node.destroyed)
                    return;
                const sprite = new Sprite(texture);
                sprite.anchor.set(.5);
                sprite.width = 56;
                sprite.height = 80;
                node.addChild(sprite);
                this.board.invalidate?.();
            }).catch(() => { });
        return node;
    }
    /**
     * Lights, the light buffer, particles and shaders. Light polygons come from
     * a per-light cache, so a door recalculates only the lights it can reach.
     */
    syncEffects(state, cell, width, height, changed) {
        const quality = this.#quality;
        const lights = effectLights(state, cell, width, height);
        this.#lightState = { ...state, lights };
        this.#componentOrigins = new Map([['light', state.lights], ['particle', state.particles], ['shader', state.shaders]]
            .flatMap(([kind, rows]) => rows.map(row => [`${kind}:${row.id}`, row])));
        const ambient = Math.max(.08, 1 - sceneDarkness(state.lighting));
        const readLight = state.particles.some(e => (e.light_response ?? 0) > 0) && quality.particles > 0;
        this.#shadersEnabled = state.shaders.some(s => s.enabled);
        const needsShaders = quality.shaders && this.#shadersEnabled;
        const lightMapKey = JSON.stringify([ambient, readLight, needsShaders]);
        let shaders = changed.shaders || changed.walls || changed.lighting;
        const lightMapReplaced = lightMapKey !== this.#lightMapKey;
        if (lightMapReplaced) {
            // Shaders own bindings to the light buffer; detach them before freeing its source.
            this.#unmountShaders();
            this.#lightMap?.dispose();
            this.#lightMap = new SceneLightMap(width, height, quality.lightMap, ambient, {
                renderToTexture: this.board.renderToTexture?.bind(this.board), textures: this.#lightTextures,
                sampleOnly: !needsShaders,
            });
            this.#lightMapKey = lightMapKey;
            shaders = true;
        }
        this.#readLight = readLight;
        this.#needsLightMap = readLight || needsShaders;
        if (changed.walls) this.#lightWalls = lightWalls(state.walls);
        const lightKey = JSON.stringify(lights);
        if (changed.walls || lightKey !== this.#lightKey) {
            this.#lightKey = lightKey;
            this.mountLights(this.#lightPolygons.update(lights, this.#lightWalls, cell, width, height));
        }
        else if (lightMapReplaced) this.#updateLightMap(quality.fps ? performance.now() : 0);
        if (changed.particles) this.mountParticles(state.particles, cell);
        if (shaders) {
            this.#unmountShaders();
            this.#shaders = mountShaders(this.#shaderLayer, state, cell, width, height, this.#lightMap.texture, ambient,
                this.#profile, (key, node) => this.registerSelection(key, node));
        }
        this.#startEffects();
    }
    #unmountShaders() {
        this.#shaders?.dispose();
        this.#shaders = undefined;
        if (this.#shaderLayer) for (const child of this.#shaderLayer.removeChildren()) child.destroy({ children: true });
        this.#dropSelection('shader:');
    }
    #updateLightMap(now) {
        if (this.#needsLightMap && this.#lightMap) this.#lightMap.update(this.#stamps, this.#readLight, now);
    }
    /** Lights keep their nodes and light-buffer stamps unless the light or its polygon changed. */
    mountLights(rows) {
        const layer = this.#lightLayer, now = this.#quality.fps ? performance.now() : 0;
        const previous = this.#lightNodes, next = new Map();
        this.#lightRows = rows;
        this.#animatedLights = [];
        const stamps = [];
        for (const { light, radius, polygon } of rows) {
            const key = JSON.stringify([light, radius]);
            let entry = previous.get(light.id);
            if (entry?.key === key && entry.polygon === polygon && !next.has(light.id)) previous.delete(light.id);
            else {
                const mask = new Graphics().poly(Array.from(polygon)).fill("white");
                const animated = new AnimatedLight(light, radius, this.#lightTextures, now);
                animated.node.mask = mask;
                const group = new Container();
                group.addChild(mask, animated.node);
                entry = { key, polygon, group, animated, stamp: { light, x: light.x, y: light.y, radius, polygon } };
                this.registerSelection(`light:${light.id}`, group);
            }
            next.set(light.id, entry);
            stamps.push(entry.stamp);
            this.#animatedLights.push(entry.animated);
        }
        for (const { group } of previous.values()) group.destroy({ children: true });
        layer.removeChildren();
        for (const { group } of next.values()) layer.addChild(group);
        this.#lightNodes = next;
        this.#dropSelection('light:', new Set([...next.keys()].map(id => `light:${id}`)));
        this.#stamps = stamps;
        this.#updateLightMap(now);
    }
    /** A worker answer for lights whose polygons were missing or stale. */
    #lightRowsReady(rows) {
        if (this.#closed || !this.#lightLayer) return;
        this.mountLights(rows);
        this.#startEffects();
        // Only the GM's unrestricted veil cuts light polygons; a token preview or a
        // player's veil follows vision alone. The stored state may predate a preview toggle.
        const state = this.#lightState;
        if (state && this.#visionIdentity === 'gm' && sceneDarkness(state.lighting) > 0)
            this.paintDarkness({ ...state, previewTokenVision: false }, ...this.#geometry, this.#gm, []);
        this.board.invalidate?.();
    }
    mountParticles(rows, cell) {
        const layer = this.#particleLayer, quality = this.#quality;
        for (const child of layer.removeChildren()) child.destroy({ children: true });
        this.#dropSelection('particle:');
        this.#particles = [];
        let remaining = quality.particleLimit;
        for (const e of rows) {
            if (!e.enabled || !quality.particles)
                continue;
            if (remaining <= 0)
                break;
            const emitter = { ...e, density: e.density * quality.particles };
            const samples = particlesOf(emitter, 0, cell).slice(0, remaining);
            remaining -= samples.length;
            const group = new Container();
            layer.addChild(group);
            this.registerSelection(`particle:${e.id}`, group);
            this.#particles.push({ emitter, cell, dots: samples.map(() => { const dot = new Sprite(this.#dotTexture); dot.anchor.set(.5); group.addChild(dot); return dot; }) });
        }
    }
    /** One animation loop for the mounted effects; a resync replaces it without restarting the clock. */
    #startEffects() {
        cancelAnimationFrame(this.#frame);
        this.#frame = 0;
        const run = ++this.#effectRun, quality = this.#quality;
        if (!this.#animatedLights.length && !this.#particles.length && !this.#shadersEnabled)
            return;
        const movingLights = this.#animatedLights.some(light => light.animated);
        let lastLightFrame = 0, lastFrame = 0;
        const tick = () => {
            if (this.#closed || run !== this.#effectRun)
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
            const time = quality.fps ? (clock - this.#started) / 1000 : 0;
            this.#shaders?.tick(time);
            const now = performance.now();
            if (movingLights && quality.lightFps && now - lastLightFrame >= 1000 / quality.lightFps) {
                lastLightFrame = now;
                for (const light of this.#animatedLights) if (light.animated) light.update(now);
                this.#updateLightMap(now);
            }
            const lightMap = this.#lightMap;
            for (const { emitter, cell, dots } of this.#particles) {
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
            if (quality.fps && (movingLights || this.#particles.length || this.#shadersEnabled))
                this.#frame = requestAnimationFrame(tick);
        };
        tick();
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
        for (const { light, radius, polygon } of limited ? [] : this.#lightRows) {
            ctx.save();
            ctx.beginPath();
            for (let i = 0; i < polygon.length; i += 2)
                if (i === 0) ctx.moveTo(polygon[i], polygon[i + 1]);
                else ctx.lineTo(polygon[i], polygon[i + 1]);
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
