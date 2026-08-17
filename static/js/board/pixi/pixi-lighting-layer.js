(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;



    const WALL_COLOR = 0x6366f1;
    const DOOR_COLORS = { closed: 0xf59e0b, open: 0x22c55e, locked: 0xef4444 };
    const LIGHT_MARKER = 0xfde047;


    const EMITTER_COLORS = { smoke: 0x9aa3ad, ember: 0xff9040, dust: 0xd8cdb4, arcane: 0xc9a6ff,
        rain: 0x9bc9e8, snow: 0xedf7ff, firefly: 0xffe46b, leaves: 0xa87035,
        bubbles: 0x8de8ff, ash: 0x77736e, blood: 0xa10f20, runes: 0x69a7ff };
    const colorFor = (wall) => wall.kind === "door"
        ? DOOR_COLORS[wall.door_state] ?? DOOR_COLORS.closed
        : WALL_COLOR;
    const hexToInt = (hex) => {
        const parsed = parseInt(String(hex || "").replace("#", ""), 16);
        return Number.isFinite(parsed) ? parsed : 0xffd8a8;
    };




    function desaturate(color, keep) {
        const r = (color >> 16) & 0xff;
        const g = (color >> 8) & 0xff;
        const b = color & 0xff;
        const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        const mix = (channel) => Math.round(luma + (channel - luma) * keep);
        return (mix(r) << 16) | (mix(g) << 8) | mix(b);
    }





    const FALLOFF_SIZE = 256;
    let falloffTexture = null;

    function falloff() {
        if (falloffTexture) return falloffTexture;
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = FALLOFF_SIZE;
        const ctx = canvas.getContext("2d");
        const half = FALLOFF_SIZE / 2;
        const gradient = ctx.createRadialGradient(half, half, 0, half, half, half);


        for (let i = 0; i <= 16; i += 1) {
            const t = i / 16;
            gradient.addColorStop(t, `rgba(255,255,255,${(1 - t) * (1 - t)})`);
        }
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, FALLOFF_SIZE, FALLOFF_SIZE);
        falloffTexture = PIXI.Texture.from(canvas);
        return falloffTexture;
    }














    const flameTextures = new Map();













    function flameProfile(count, bite, distance, angle) {
        if (distance >= 1) return 0;
        if (!count || !bite) return (1 - distance) * (1 - distance);









        const wave = Math.sin(angle * count + 0.6 * Math.sin(angle * count));
        const shape = 0.5 + 0.5 * wave;



        const guard = Math.min(1, distance / 0.25);
        const shrink = bite * shape * guard;
        const reach = Math.min(1, distance / Math.max(0.05, 1 - shrink));
        return (1 - reach) * (1 - reach);
    }

    function flameFalloff(lobes, depth) {
        const count = Math.max(0, Math.round(lobes || 0));
        const bite = Math.max(0, Math.min(0.8, depth || 0));
        if (!count || !bite) return falloff();

        const key = `${count}:${bite.toFixed(2)}`;
        const cached = flameTextures.get(key);
        if (cached) return cached;

        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = FALLOFF_SIZE;
        const ctx = canvas.getContext("2d");
        const image = ctx.createImageData(FALLOFF_SIZE, FALLOFF_SIZE);
        const half = FALLOFF_SIZE / 2;

        for (let y = 0; y < FALLOFF_SIZE; y += 1) {
            for (let x = 0; x < FALLOFF_SIZE; x += 1) {
                const dx = (x - half) / half;
                const dy = (y - half) / half;
                const alpha = flameProfile(count, bite, Math.hypot(dx, dy), Math.atan2(dy, dx));
                if (alpha <= 0) continue;
                const offset = (y * FALLOFF_SIZE + x) * 4;
                image.data[offset] = 255;
                image.data[offset + 1] = 255;
                image.data[offset + 2] = 255;
                image.data[offset + 3] = Math.round(Math.max(0, Math.min(1, alpha)) * 255);
            }
        }
        ctx.putImageData(image, 0, 0);
        const texture = PIXI.Texture.from(canvas);
        flameTextures.set(key, texture);
        return texture;
    }





    window.GravewrightBoardInternals.falloff = falloff;
    window.GravewrightBoardInternals.flameProfile = flameProfile;
    window.GravewrightBoardInternals.emissionEffect = emissionEffect;
    window.GravewrightBoardInternals.driveFilter = driveFilter;




























    const effectBank = new Map();

    function filters() {
        return (typeof PIXI !== "undefined" && PIXI.filters) || null;
    }

    function emissionEffect(light) {
        const animation = light.animation;



        if (animation !== "arcane" && animation !== "smoke") return null;

        const key = `${light.id}:${animation}`;
        if (effectBank.has(key)) return effectBank.get(key);

        const F = filters();
        let built = null;
        try {
            if (F && animation === "arcane" && F.TwistFilter) {
                built = { kind: "twist", filter: new F.TwistFilter({ radius: 200, angle: 2, padding: 20 }) };
            } else if (F && animation === "smoke" && F.MotionBlurFilter) {


                built = { kind: "motion", filter: new F.MotionBlurFilter({ velocity: { x: 0, y: 6 }, kernelSize: 9 }) };
            }
        } catch (_err) {
            built = null;
        }
        effectBank.set(key, built);
        return built;
    }



    function pruneEffects(lights) {
        if (effectBank.size <= 32) return;
        const alive = new Set((lights || []).map((light) => `${light.id}:${light.animation}`));
        effectBank.forEach((entry, key) => {
            if (alive.has(key)) return;
            try { entry?.filter?.destroy?.(); } catch (_err) {                    }
            effectBank.delete(key);
        });
    }



    function driveFilter(entry, light, seconds, centre, radius) {
        const { kind, filter } = entry;
        const phase = light.spin || 0;
        if (kind === "zoom") {


            const jitter = radius * 0.08;
            filter.center = {
                x: centre.x + Math.cos(phase * 3) * jitter,
                y: centre.y + Math.sin(phase * 2.3) * jitter,
            };


            filter.strength = entry.base * (light.wobble ?? 1);
            return;
        }
        if (kind === "bloom") {
            filter.bloomScale = 0.6 + 1.2 * (light.wobble ?? 1);
            return;
        }
        if (kind === "twist") {
            filter.offset = { x: centre.x, y: centre.y };
            filter.radius = radius;
            filter.angle = Math.sin(seconds * 0.6 + phase) * 3.2;
            return;
        }
        if (kind === "motion") {

            filter.velocity = {
                x: Math.sin(seconds * 0.35 + phase) * 3,
                y: -6 - Math.sin(seconds * 0.5 + phase) * 2,
            };
        }
    }




    let dotTexture = null;

    function particleDot() {
        if (dotTexture) return dotTexture;
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 64;
        const ctx = canvas.getContext("2d");
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, "rgba(255,255,255,1)");
        gradient.addColorStop(0.35, "rgba(255,255,255,0.75)");
        gradient.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);
        dotTexture = PIXI.Texture.from(canvas);
        return dotTexture;
    }






































    const VEIL_START = 0.55;
    const VEIL_MAX = 0.15;



    const HALO_SATURATION = 0.7;


    const VEIL_LOBES = 5;
    const VEIL_LOBE_DEPTH = 0.35;


    const VEIL_SPIN = 0.015;
    const VEIL_BREATH_HZ = 0.08;
    const VEIL_BREATH_DEPTH = 0.12;
    const VEIL_SIZE = 512;
    let veilTexture = null;




    function veil() {
        if (veilTexture) return veilTexture;
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = VEIL_SIZE;
        const ctx = canvas.getContext("2d");
        const image = ctx.createImageData(VEIL_SIZE, VEIL_SIZE);
        const half = VEIL_SIZE / 2;

        for (let y = 0; y < VEIL_SIZE; y += 1) {
            for (let x = 0; x < VEIL_SIZE; x += 1) {
                const dx = (x - half) / half;
                const dy = (y - half) / half;
                const distance = Math.hypot(dx, dy);
                const offset = (y * VEIL_SIZE + x) * 4;
                if (distance >= 1 || distance <= VEIL_START) continue;



                const t = (distance - VEIL_START) / (1 - VEIL_START);
                const eased = t * t * (3 - 2 * t);


                const angle = Math.atan2(dy, dx);
                const lobes = 0.5 * (Math.sin(angle * VEIL_LOBES) + Math.sin(angle * (VEIL_LOBES * 2 + 1) + 1.7));
                const shaped = Math.max(0, Math.min(1, eased * (1 + VEIL_LOBE_DEPTH * lobes)));

                image.data[offset + 3] = Math.round(shaped * 255);
            }
        }
        ctx.putImageData(image, 0, 0);
        veilTexture = PIXI.Texture.from(canvas);
        return veilTexture;
    }



    const DOOR_ICONS = {
        closed: "/static/icons/closed-door.png",
        open: "/static/icons/open-door.png",
        locked: "/static/icons/locked-door.png",
    };
    const DOOR_ICON_PX = 34;
    const doorTextures = new Map();

    function doorTexture(state) {
        const url = DOOR_ICONS[state] || DOOR_ICONS.closed;
        if (doorTextures.has(url)) return doorTextures.get(url);
        doorTextures.set(url, null);
        PIXI.Assets.load(url)
            .then((texture) => {
                doorTextures.set(url, texture);
                window.GravewrightMap?.redraw?.();
            })
            .catch(() => doorTextures.set(url, undefined));
        return null;
    }

    Object.assign(proto, {
        _applySceneShaders(board, lighting, cssW, cssH) {
            const effects = window.GravewrightShaderEffects;
            if (!effects || !board.effectsLayer) return;
            const shaders = lighting?.shaders || [];
            if (!shaders.length) { effects.clear(); return; }





            const light = window.GravewrightLightBuffer?.build?.(board, lighting, cssW, cssH, this.camera) || null;
            const drawn = effects.render(board, shaders, performance.now(), cssW, cssH, this.camera, light);
            effects.requestNextFrame?.(shaders, drawn, this.deps.requestRender);
        },

        _renderLighting(board, cssW, cssH) {
            const wallsGfx = board.lightingWallsGfx;
            wallsGfx.clear();
            this._resetDoorPool(board);
            this._resetGlowPool(board);

            const lighting = window.GravewrightLighting?.stateForCanvas?.(this.active);







            this._applySceneShaders(board, lighting, cssW, cssH);
            if (!lighting?.visible || !this.scene) {
                board.lightingLayer.visible = false;
                return;
            }
            board.lightingLayer.visible = true;

            const cam = this.camera;
            const screen = (x, y) => ({
                x: x * cam.zoom + cam.offsetX,
                y: y * cam.zoom + cam.offsetY,
            });
            const flatten = (polygon) => {
                const flat = [];
                polygon.forEach((point) => {
                    const p = screen(point.x, point.y);
                    flat.push(p.x, p.y);
                });
                return flat;
            };

            // Lighting state is scene-wide. Submit only sources that can affect
            // this viewport; offscreen masks and halos are pure GPU overhead.
            const visibleLights = (lighting.lights || []).filter((light) => {
                const centre = screen(light.x, light.y);
                const radius = Math.max(0, Number(light.dim) || 0) * cam.zoom;
                return centre.x + radius >= 0 && centre.y + radius >= 0
                    && centre.x - radius <= cssW && centre.y - radius <= cssH;
            });
            board.visibleLightingSources = visibleLights.length;







            this._renderParticleClouds(board, lighting, screen, cam);




            const classic = lighting.mode === "classic";

            const litAreas = [
                ...lighting.visionPolygons,
                ...visibleLights.map((light) => light.polygon),
            ].filter((polygon) => polygon && polygon.length >= 3);



            if (lighting.darkness > 0) {
                const dpr = window.devicePixelRatio || 1;
                const rt = this._ensureLightingRT(board, cssW, cssH, dpr);



                const key = [



                    lighting.mode,
                    cam.offsetX, cam.offsetY, cam.zoom, cssW, cssH, dpr, lighting.darkness,




                    lighting.geometryStamp,



                    visibleLights.map((l) => [
                        l.id, Math.round(l.x), Math.round(l.y), Math.round(l.dim),
                        l.intensity.toFixed(2), l.angle, l.rotation,
                    ].join("/")).join("|"),
                    (lighting.visionRims || []).map((rim) => Math.round(rim.radius)).join("|"),


                    litAreas.length,






                    visibleLights.map((l) => `${Math.round(l.dim)}/${l.intensity.toFixed(2)}`).join("|"),
                ].join(":");
                if (board.lightingKey !== key) {
                    board.lightingKey = key;
                    this._composeDarkness(board, rt, cssW, cssH, lighting,
                        litAreas.map(flatten), visibleLights, screen, flatten, cam);
                }
                board.lightingSprite.texture = rt;
                board.lightingSprite.position.set(0, 0);
                board.lightingSprite.width = cssW;
                board.lightingSprite.height = cssH;
                board.lightingSprite.visible = true;
            } else {
                board.lightingSprite.visible = false;
            }











            const seconds = performance.now() / 1000;

            let veilSlot = 0;
            if (!classic && lighting.darkness > 0) {
                (lighting.visionRims || []).forEach((rim, index) => {
                    const polygon = lighting.visionPolygons?.[index];
                    if (!polygon || polygon.length < 3) return;



                    if (!rim || !(rim.radius > 0)) return;

                    const phase = index * 1.7;
                    const { sprite, mask } = this._acquireVeil(board, veilSlot);
                    veilSlot += 1;
                    mask.poly(flatten(polygon)).fill({ color: 0xffffff, alpha: 1 });
                    const centre = screen(rim.x, rim.y);
                    sprite.texture = veil();
                    sprite.tint = 0x000000;
                    sprite.blendMode = "normal";
                    sprite.rotation = (seconds * VEIL_SPIN + phase) * Math.PI * 2;
                    sprite.position.set(centre.x, centre.y);


                    sprite.width = sprite.height = rim.radius * cam.zoom * 2;
                    const breath = 1 + VEIL_BREATH_DEPTH
                        * Math.sin((seconds * VEIL_BREATH_HZ + phase) * Math.PI * 2);
                    sprite.alpha = VEIL_MAX * lighting.darkness * breath;
                });
            }







            let glowSlot = 0;
            pruneEffects(visibleLights);
            if (!classic) visibleLights.forEach((light) => {
                if (!light.polygon || light.polygon.length < 3 || light.alpha <= 0 || !(light.dim > 0)) return;
                const centre = screen(light.x, light.y);
                const flat = flatten(light.polygon);







                const texture = flameFalloff(light.lobes, light.lobeDepth);
                const effect = emissionEffect(light);
                const tint = desaturate(hexToInt(light.tint || light.color), HALO_SATURATION);



                const drift = light.offset || { x: 0, y: 0 };
                const origin = {
                    x: centre.x + drift.x * cam.zoom,
                    y: centre.y + drift.y * cam.zoom,
                };

                const entry = this._acquireGlow(board, glowSlot);
                glowSlot += 1;
                entry.mask.poly(flat).fill({ color: 0xffffff, alpha: 1 });

                (light.sources || []).forEach((source, layer) => {
                    const radius = source.radius * (source.wobble ?? 1);
                    if (!(radius > 0)) return;
                    const sprite = this._glowSprite(entry, layer);


                    sprite.texture = source.core ? falloff() : texture;
                    sprite.tint = tint;


                    sprite.blendMode = "add";
                    sprite.position.set(
                        origin.x + (source.offsetX || 0) * cam.zoom,
                        origin.y + (source.offsetY || 0) * cam.zoom,
                    );


                    sprite.rotation = source.core ? 0 : (light.spin || 0) * (layer % 2 ? -1.6 : 1);
                    sprite.width = sprite.height = radius * cam.zoom * 2;
                    sprite.alpha = source.weight * light.alpha;
                });




                if (effect) {
                    driveFilter(effect, light, seconds, origin, (light.dim || 0) * cam.zoom);
                    entry.container.filters = [effect.filter];
                }
            });




            const preview = lighting.visionPreview;
            if (preview) {
                if (preview.polygon?.length >= 3) {
                    wallsGfx.poly(flatten(preview.polygon))
                        .fill({ color: 0x38bdf8, alpha: 0.14 })
                        .stroke({ color: 0x38bdf8, width: 2, alpha: 0.85 });
                }
                const centre = screen(preview.x, preview.y);
                wallsGfx.circle(centre.x, centre.y, 5)
                    .fill({ color: 0x38bdf8, alpha: 1 });

                if (preview.radius > 0) {
                    wallsGfx.circle(centre.x, centre.y, preview.radius * cam.zoom)
                        .stroke({ color: 0x38bdf8, width: 1.5, alpha: 0.5 });
                }
            }





            if (lighting.editingParticles) {
                (lighting.particleClouds || []).forEach((cloud) => {
                    const at = screen(cloud.x, cloud.y);
                    const tint = EMITTER_COLORS[cloud.kind] ?? 0xffffff;
                    const selected = cloud.selected;
                    wallsGfx.circle(at.x, at.y, selected ? 9 : 7)
                        .fill({ color: tint, alpha: 0.85 })
                        .stroke({ color: selected ? 0xffffff : 0x0b0f14, width: selected ? 3 : 2, alpha: 1 });


                    wallsGfx.circle(at.x, at.y, selected ? 15 : 13)
                        .stroke({ color: tint, width: 1.5, alpha: 0.55 });
                });
            }









            if (lighting.editingShaders) {
                (lighting.shaderMarkers || []).forEach((shader) => {
                    const centre = screen(shader.x, shader.y);
                    const tint = hexToInt(shader.color);
                    if (shader.radiusWorld > 0) {


                        wallsGfx.circle(centre.x, centre.y, shader.radiusWorld * this.camera.zoom)
                            .stroke({ color: tint, width: 1, alpha: shader.selected ? 0.55 : 0.28 });
                        if (shader.resizeHandle) {
                            wallsGfx.circle(centre.x + shader.radiusWorld * this.camera.zoom, centre.y, 6)
                                .fill({ color: 0x0b0f19, alpha: 0.9 })
                                .stroke({ color: tint, width: 2, alpha: 0.9 });
                        }
                    }
                    wallsGfx.circle(centre.x, centre.y, shader.selected ? 9 : 7)
                        .fill({ color: tint, alpha: shader.enabled ? 0.85 : 0.25 })
                        .stroke({ color: shader.selected ? 0xffffff : tint, width: shader.selected ? 3 : 2, alpha: 1 });


                    const arm = shader.selected ? 5 : 4;
                    wallsGfx.poly([
                        centre.x, centre.y - arm, centre.x + arm, centre.y,
                        centre.x, centre.y + arm, centre.x - arm, centre.y,
                    ]).fill({ color: 0x0b0f19, alpha: 0.8 });
                });
            }

            if (lighting.editingLights) {
                visibleLights.forEach((light) => {
                    const centre = screen(light.x, light.y);
                    const selected = lighting.picked?.light?.has(light.id);
                    wallsGfx.circle(centre.x, centre.y, selected ? 9 : 7)
                        .fill({ color: hexToInt(light.color), alpha: 0.85 })
                        .stroke({ color: selected ? 0xffffff : LIGHT_MARKER, width: selected ? 3 : 2, alpha: 1 });


                    if (light.animation !== "none") {
                        wallsGfx.circle(centre.x, centre.y, 11 + 4 * light.alpha)
                            .stroke({ color: LIGHT_MARKER, width: 1.5, alpha: 0.35 + 0.45 * light.alpha });
                    }
                });
            }

            if (lighting.marquee) {
                const a = screen(lighting.marquee.from.x, lighting.marquee.from.y);
                const b = screen(lighting.marquee.to.x, lighting.marquee.to.y);
                const broadSelection = lighting.marquee.to.x >= lighting.marquee.from.x;
                const color = broadSelection ? 0x4ce2a5 : 0x93c5fd;
                wallsGfx.rect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y))
                    .fill({ color, alpha: broadSelection ? 0.24 : 0.12 })
                    .stroke({ color, width: broadSelection ? 2 : 1, alpha: 0.9 });
            }

            if (!lighting.editing) {
                lighting.doors.forEach((door, index) => {
                    const a = screen(door.x1, door.y1);
                    const b = screen(door.x2, door.y2);
                    this._drawDoorMarker(board, wallsGfx, index, (a.x + b.x) / 2, (a.y + b.y) / 2, door, colorFor(door));
                });
                return;
            }

            const dragged = lighting.draggingNode
                ? screen(lighting.draggingNode.x, lighting.draggingNode.y)
                : null;
            let doorIndex = 0;
            lighting.walls.forEach((wall) => {
                const a = screen(wall.x1, wall.y1);
                const b = screen(wall.x2, wall.y2);
                const selected = lighting.picked?.wall?.has(wall.id);
                const isDoor = wall.kind === "door";
                const state = isDoor ? wall.door_state : null;
                const color = colorFor(wall);
                wallsGfx.moveTo(a.x, a.y).lineTo(b.x, b.y).stroke({
                    color,

                    alpha: state === "open" ? 0.45 : 1,
                    width: selected ? 7 : isDoor ? 6 : 4,
                });
                if (isDoor) {
                    this._drawDoorMarker(board, wallsGfx, doorIndex, (a.x + b.x) / 2, (a.y + b.y) / 2, wall, color);
                    doorIndex += 1;
                }



                const dot = lighting.nodesGrabbable ? 6 : selected ? 5 : 3.5;
                [a, b].forEach((point) => {
                    const dragging = dragged
                        && Math.hypot(point.x - dragged.x, point.y - dragged.y) < 0.5;
                    wallsGfx.circle(point.x, point.y, dragging ? dot + 2 : dot)
                        .fill({ color: dragging ? 0xfde047 : selected ? 0xffffff : 0x0b0f14, alpha: 1 })
                        .stroke({
                            color: dragging ? 0xfde047 : lighting.nodesGrabbable ? 0x38bdf8 : selected ? 0xffffff : color,
                            width: lighting.nodesGrabbable ? 2 : 1.5,
                            alpha: 1,
                        });
                });
            });



            if (lighting.start && lighting.preview) {
                const a = screen(lighting.start.x, lighting.start.y);
                const b = screen(lighting.preview.x, lighting.preview.y);
                wallsGfx.moveTo(a.x, a.y).lineTo(b.x, b.y).stroke({
                    color: 0xfde047,
                    alpha: 0.95,
                    width: 3,
                });


                wallsGfx.circle(a.x, a.y, 4).fill({ color: 0xfde047, alpha: 1 });
                wallsGfx.circle(b.x, b.y, 7).stroke({ color: 0xfde047, width: 2, alpha: 1 });
            }
        },

        _ensureLightingRT(board, cssW, cssH, dpr) {
            if (board.lightingRT && board.lightingRTW === cssW && board.lightingRTH === cssH && board.lightingRTDpr === dpr) {
                return board.lightingRT;
            }
            if (board.lightingRT) board.lightingRT.destroy(true);
            board.lightingRT = PIXI.RenderTexture.create({
                width: Math.max(1, cssW),
                height: Math.max(1, cssH),
                resolution: dpr,
            });
            board.lightingRTW = cssW;
            board.lightingRTH = cssH;
            board.lightingRTDpr = dpr;
            board.lightingKey = "";
            return board.lightingRT;
        },

        _acquireLightingGfx(board) {
            let gfx = board.lightingGfxPool[board.lightingPoolIndex];
            if (!gfx) {
                gfx = new PIXI.Graphics();
                board.lightingGfxPool[board.lightingPoolIndex] = gfx;
            }
            board.lightingPoolIndex += 1;
            board.lightingScene.addChild(gfx);
            return gfx;
        },

        _acquireDarknessGlow(board, index) {
            let entry = board.lightingDarkGlowPool[index];
            if (!entry) {
                const sprite = new PIXI.Sprite();
                sprite.anchor.set(0.5);
                const mask = new PIXI.Graphics();
                sprite.mask = mask;
                entry = { sprite, mask };
                board.lightingDarkGlowPool[index] = entry;
            }
            entry.sprite.visible = true;
            entry.mask.clear();
            board.lightingScene.addChild(entry.mask, entry.sprite);
            return entry;
        },

        _composeDarkness(board, rt, cssW, cssH, lighting, litAreas, lights, screen, flatten, cam) {
            board.lightingScene.removeChildren();
            board.lightingScene.filters = null;
            board.lightingPoolIndex = 0;
            board.lightingGfxPool.forEach((gfx) => {
                gfx.clear();
                gfx.blendMode = "normal";




                gfx.filters = null;
            });
            board.lightingDarkGlowPool.forEach(({ sprite, mask }) => {
                sprite.visible = false;
                mask.clear();
            });

            this._acquireLightingGfx(board)
                .rect(0, 0, cssW, cssH)
                .fill({ color: 0x000000, alpha: lighting.darkness });




            if (litAreas.length) {
                const eraser = this._acquireLightingGfx(board);
                eraser.blendMode = "erase";
                litAreas.forEach((flat) => eraser.poly(flat).fill({ color: 0x000000, alpha: 1 }));
            }




            board.app.renderer.render({ container: board.lightingScene, target: rt, clear: true });
        },





        _veilPool(board) {
            if (!board.lightingVeilPool) board.lightingVeilPool = [];
            return board.lightingVeilPool;
        },

        _resetGlowPool(board) {
            board.lightingGlowGfx.removeChildren();



            (board.lightingGlowPool || []).forEach(({ mask, container, sprites }) => {
                container.visible = false;
                container.filters = null;
                mask.clear();
                (sprites || []).forEach((sprite) => { sprite.visible = false; });
            });
            this._veilPool(board).forEach(({ sprite, mask }) => {
                sprite.visible = false;
                mask.clear();
            });
        },

        _renderParticleClouds(board, lighting, screen, cam) {
            const layer = board.lightingParticleGfx;
            if (!layer) return;
            const pool = board.lightingParticlePool || (board.lightingParticlePool = []);
            pool.forEach((sprite) => { sprite.visible = false; });

            let slot = 0;
            (lighting.particleClouds || []).forEach((cloud) => {
                cloud.particles.forEach((particle) => {
                    if (!(particle.alpha > 0) || !(particle.size > 0)) return;
                    let sprite = pool[slot];
                    if (!sprite) {
                        sprite = new PIXI.Sprite(particleDot());
                        sprite.anchor.set(0.5);
                        pool[slot] = sprite;
                        layer.addChild(sprite);
                    }
                    slot += 1;
                    sprite.visible = true;
                    sprite.texture = particleDot();
                    sprite.tint = hexToInt(particle.tint);
                    sprite.blendMode = particle.blend || "normal";
                    const at = screen(particle.x, particle.y);
                    sprite.position.set(at.x, at.y);
                    sprite.rotation = particle.rotation || 0;
                    const diameter = particle.size * cam.zoom * 2;
                    sprite.width = diameter * (particle.aspect || 1);
                    sprite.height = diameter;
                    sprite.alpha = particle.alpha;
                });
            });
        },

        _acquireVeil(board, index) {
            const pool = this._veilPool(board);
            let entry = pool[index];
            if (!entry) {
                const sprite = new PIXI.Sprite();
                sprite.anchor.set(0.5);
                const mask = new PIXI.Graphics();
                sprite.mask = mask;
                entry = { sprite, mask };
                pool[index] = entry;
            }
            entry.sprite.visible = true;
            entry.mask.clear();

            board.lightingGlowGfx.addChild(entry.mask, entry.sprite);
            return entry;
        },




        _acquireGlow(board, index) {
            let entry = board.lightingGlowPool[index];
            if (!entry) {




                const container = new PIXI.Container();
                const mask = new PIXI.Graphics();
                container.mask = mask;
                entry = { container, mask, sprites: [] };
                board.lightingGlowPool[index] = entry;
            }
            entry.container.visible = true;
            entry.container.filters = null;
            entry.mask.clear();
            entry.sprites.forEach((sprite) => { sprite.visible = false; });
            board.lightingGlowGfx.addChild(entry.mask, entry.container);
            return entry;
        },




        _glowSprite(entry, index) {
            let sprite = entry.sprites[index];
            if (!sprite) {
                sprite = new PIXI.Sprite();
                sprite.anchor.set(0.5);
                entry.sprites[index] = sprite;
                entry.container.addChild(sprite);
            }
            sprite.visible = true;
            return sprite;
        },

        _resetDoorPool(board) {
            board.lightingDoorLayer.removeChildren();
            board.lightingDoorPool.forEach((sprite) => { sprite.visible = false; });
        },

        _acquireDoorSprite(board, index) {
            let sprite = board.lightingDoorPool[index];
            if (!sprite) {
                sprite = new PIXI.Sprite();
                sprite.anchor.set(0.5);
                board.lightingDoorPool[index] = sprite;
            }
            sprite.visible = true;
            board.lightingDoorLayer.addChild(sprite);
            return sprite;
        },

        _drawDoorMarker(board, gfx, index, mx, my, door, color) {


            gfx.circle(mx, my, DOOR_ICON_PX / 2 + 2).fill({ color: 0x0b0f14, alpha: 0.6 });

            const texture = doorTexture(door.door_state);
            if (texture) {
                const sprite = this._acquireDoorSprite(board, index);
                sprite.texture = texture;
                sprite.position.set(mx, my);
                const scale = DOOR_ICON_PX / Math.max(texture.width, texture.height);
                sprite.scale.set(scale);

                gfx.circle(mx, my, DOOR_ICON_PX / 2 + 2).stroke({ color, width: 2, alpha: 1 });
                return;
            }


            const locked = door.door_state === "locked";
            gfx.circle(mx, my, 9)
                .fill({ color: locked ? color : 0x111827, alpha: 1 })
                .stroke({ color, width: 2, alpha: 1 });
            if (locked) {
                gfx.moveTo(mx - 3.5, my).lineTo(mx + 3.5, my)
                    .stroke({ color: 0x111827, width: 2.5, alpha: 1 });
            }
        },
    });
})();
