import { tileBlobCache } from "../model/tile-blob-cache.js";
// Pixi builds its shader and uniform sync code with `new Function`, which the server's
// Content-Security-Policy forbids (`script-src 'self'`, no `unsafe-eval`). This entry swaps those
// generators for polyfills that do the same work without eval, so the policy stays strict. It must
// be imported before any renderer is created.
import "pixi.js/unsafe-eval";
import { Application, Assets, Container, Graphics, Sprite, Text, Texture } from "pixi.js";
// The whole namespace, because a contributed layer needs the engine's constructors and must not
// bring its own copy of them: a second Pixi shares no classes and no renderer with this one.
import * as engine from "pixi.js";
import { BOARD_STACK } from "../model/board-renderer.js";
import { AssetReferencePool } from "../model/asset-reference-pool.js";
/**
 * The one file that knows the board is drawn by Pixi. Everything above it speaks `BoardRenderer`,
 * so swapping the engine touches nothing else.
 */
/** Pixi over-samples on dense displays for nothing; two device pixels per CSS pixel is the ceiling. */
const MAX_RESOLUTION = 2;
/** The disc behind a piece that has no art, dark enough for the name to read over it. */
const PIECE_GROUND = "#181d23";
// Pixi's worker capability probe fetches a data: PNG. Our connect-src deliberately
// permits only same-origin resources and WebSockets, so that probe violates CSP.
// Skip the worker path before the first Assets load; keep async ImageBitmap decoding.
Assets.setPreferences({ preferWorkers: false });
/** Pixi Assets is process-wide, so references are shared across every board renderer too. */
const pieceAssets = new AssetReferencePool(async (url) => await Assets.load({ src: url, parser: "loadTextures" }), async (url) => await Assets.unload(url));
/** What a piece shows when it has no art: the initials of its name, at most two letters. */
function initials(label) {
    const words = label.trim().split(/\s+/).filter(Boolean);
    if (!words.length)
        return "?";
    return (words.length === 1 ? words[0].slice(0, 2) : words[0][0] + words[1][0]).toUpperCase();
}
export class PixiBoardRenderer {
    #application;
    /** Carries the viewport: everything drawn lives inside it, in map coordinates. */
    #world = new Container();
    #tiles = new Container();
    #grid = new Graphics();
    /** Between ground and marks: pieces stand on the map, and pings still read over them. */
    #figures = new Container();
    /** Above the tiles, so the frame and pings are never buried by a tile that lands late. */
    #marks = new Container();
    #sprites = new Map();
    #spriteUrls = new Map();
    /** The load in flight for a key, so a tile that leaves the viewport stops costing bandwidth. */
    #inFlight = new Map();
    #shapes = new Map();
    #layers = new Map();
    #pieces = new Map();
    #textResolution = 1;
    #wantedPieces = new Map();
    /** The tiles asked for by the most recent `setTiles`; in-flight loads are judged against it. */
    #wanted = new Map();
    #destroyed = false;
    #renderFrame = 0;
    /** Coalesce visual changes; a still scene consumes no render-loop frames. */
    invalidate() {
        if (this.#destroyed || this.#renderFrame) return;
        this.#renderFrame = requestAnimationFrame(() => {
            this.#renderFrame = 0;
            if (!this.#destroyed) this.#application.render();
        });
    }
    constructor(application, label) {
        this.#application = application;
        this.#textResolution = Math.min(MAX_RESOLUTION, application.renderer.resolution);
        // Tiles stack by level rather than by arrival, so a coarse backdrop stays under the finer level
        // replacing it however late either of them lands.
        this.#tiles.sortableChildren = true;
        // The world stacks by declared height, which is what lets a contributed layer sit between the
        // board's own three.
        this.#world.sortableChildren = true;
        this.#tiles.zIndex = BOARD_STACK.tiles;
        this.#grid.zIndex = BOARD_STACK.grid;
        this.#figures.zIndex = BOARD_STACK.figures;
        this.#marks.zIndex = BOARD_STACK.marks;
        this.#world.addChild(this.#tiles, this.#grid, this.#figures, this.#marks);
        application.stage.addChild(this.#world);
        application.canvas.setAttribute("role", "img");
        this.setLabel(label);
        this.invalidate();
    }
    get surface() {
        return { width: this.#application.screen.width, height: this.#application.screen.height };
    }
    viewport() {
        return { x: this.#world.x, y: this.#world.y, scale: this.#world.scale.x };
    }
    /** Internal scene effects reuse the board's GPU without exposing it through the SDK. */
    renderToTexture(container, target) {
        if (this.#destroyed) return;
        this.#application.renderer.render({ container, target, clear: true, clearColor: [0, 0, 0, 0] });
    }
    setViewport(view) {
        this.#world.position.set(view.x, view.y);
        this.#world.scale.set(view.scale);
        // Text textures otherwise keep their original density while the map enlarges them.
        // Reuse each density across a zoom band; panning never regenerates text textures.
        const resolution = Math.min(8, 2 ** Math.ceil(Math.log2(Math.max(1,
            view.scale * this.#application.renderer.resolution))));
        if (resolution !== this.#textResolution) {
            this.#textResolution = resolution;
            for (const piece of this.#pieces.values()) {
                piece.label.resolution = resolution;
                if (piece.art instanceof Text) piece.art.resolution = resolution;
                for (const icon of piece.conditions.children) icon.resolution = resolution;
            }
        }
        this.invalidate();
    }
    /** Invalidate pending revisions without removing the tiles already on screen. */
    cancelTileLoads() {
        for (const { controller } of this.#inFlight.values())
            controller.abort();
        this.#inFlight.clear();
    }
    async setTiles(tiles) {
        if (this.#destroyed)
            return [];
        const wanted = new Map(tiles.map((tile) => [tile.key, tile]));
        this.#wanted = wanted;
        for (const key of [...this.#sprites.keys()])
            if (!wanted.has(key))
                this.#release(key);
        // A new revision reuses the tile key, but must not reuse the previous bytes or request.
        for (const [key, { controller, url }] of this.#inFlight)
            if (wanted.get(key)?.url !== url) {
                controller.abort();
                this.#inFlight.delete(key);
            }
        const pending = [];
        for (const [key, tile] of wanted) {
            const sprite = this.#sprites.get(key);
            if (sprite && this.#spriteUrls.get(key) === tile.url) {
                if (sprite.x !== tile.x || sprite.y !== tile.y || sprite.scale.x !== tile.scale || sprite.zIndex !== tile.depth) {
                    sprite.position.set(tile.x, tile.y);
                    sprite.scale.set(tile.scale);
                    sprite.zIndex = tile.depth;
                    this.invalidate();
                }
                continue;
            }
            if (this.#inFlight.has(key))
                continue;
            pending.push(this.#load(key, tile));
        }
        return (await Promise.all(pending)).filter((key) => key !== undefined);
    }
    async setPieces(pieces) {
        if (this.#destroyed)
            return;
        const wanted = new Map(pieces.map((piece) => [piece.key, piece]));
        this.#wantedPieces = wanted;
        for (const key of [...this.#pieces.keys()])
            if (!wanted.has(key))
                this.#releasePiece(key);
        await Promise.all([...wanted].map(([key, piece]) => this.#showPiece(key, piece)));
    }
    setGrid(grid) {
        this.#grid.clear();
        this.invalidate();
        if (!grid.visible || grid.cellSize <= 0 || grid.opacity <= 0)
            return;
        // Refuse pathological density: below this threshold the lines merge into a fill and cost tens
        // of thousands of segments without conveying a grid.
        const columns = Math.floor(grid.width / grid.cellSize);
        const rows = Math.floor(grid.height / grid.cellSize);
        if (columns + rows > 20_000)
            return;
        for (let x = (grid.offsetX ?? 0) % grid.cellSize; x <= grid.width; x += grid.cellSize)
            this.#grid.moveTo(x, 0).lineTo(x, grid.height);
        for (let y = (grid.offsetY ?? 0) % grid.cellSize; y <= grid.height; y += grid.cellSize)
            this.#grid.moveTo(0, y).lineTo(grid.width, y);
        this.#grid.stroke({ width: Math.max(.5, grid.cellSize / 140), color: grid.color, alpha: grid.opacity });
    }
    createLayer(id, order) {
        const existing = this.#layers.get(id);
        if (existing) {
            existing.layer.setOrder(order);
            return existing.layer;
        }
        const container = new Container();
        container.zIndex = order;
        container.sortableChildren = true;
        this.#world.addChild(container);
        const layer = {
            id,
            setOrder: (next) => { container.zIndex = next; this.invalidate(); },
            setVisible: (visible) => { container.visible = visible; this.invalidate(); },
            clear: () => { container.removeChildren().forEach((child) => child.destroy({ children: true })); this.invalidate(); },
            // Everything above this line is engine-neutral; this is the one door, and it is marked.
            native: () => ({ engine, container }),
            dispose: () => {
                if (this.#layers.get(id)?.container !== container)
                    return;
                this.#layers.delete(id);
                container.removeFromParent();
                container.destroy({ children: true });
                this.invalidate();
            },
        };
        this.#layers.set(id, { layer, container });
        this.invalidate();
        return layer;
    }
    drawShape(id, position, shapes) {
        if (this.#destroyed)
            return;
        let graphics = this.#shapes.get(id);
        if (!graphics) {
            graphics = new Graphics();
            this.#marks.addChild(graphics);
            this.#shapes.set(id, graphics);
        }
        graphics.position.set(position.x, position.y);
        graphics.clear();
        this.invalidate();
        for (const shape of shapes) {
            if (shape.kind === "circle")
                graphics.circle(0, 0, shape.radius);
            else if (shape.kind === "line")
                graphics.moveTo(0, 0).lineTo(shape.to.x, shape.to.y);
            else if (shape.kind === "polygon")
                graphics.poly(shape.points);
            else
                graphics.rect(0, 0, shape.width, shape.height);
            if (shape.stroke)
                graphics.stroke({ width: shape.stroke.width, color: shape.stroke.color, alpha: shape.stroke.alpha ?? 1 });
            if (shape.fill)
                graphics.fill({ color: shape.fill.color, alpha: shape.fill.alpha ?? 1 });
        }
    }
    removeShape(id) {
        const graphics = this.#shapes.get(id);
        if (!graphics)
            return;
        this.#shapes.delete(id);
        graphics.removeFromParent();
        graphics.destroy();
        this.invalidate();
    }
    clear() {
        this.#wanted = new Map();
        this.#wantedPieces = new Map();
        this.cancelTileLoads();
        for (const key of [...this.#sprites.keys()])
            this.#release(key);
        for (const key of [...this.#pieces.keys()])
            this.#releasePiece(key);
        for (const id of [...this.#shapes.keys()])
            this.removeShape(id);
        this.#grid.clear();
    }
    resize() {
        if (!this.#destroyed)
            this.#application.resize();
        this.invalidate();
    }
    setLabel(label) {
        this.#application.canvas.setAttribute("aria-label", label);
    }
    destroy() {
        if (this.#destroyed)
            return;
        this.#destroyed = true;
        cancelAnimationFrame(this.#renderFrame);
        this.#renderFrame = 0;
        this.#wanted = new Map();
        this.cancelTileLoads();
        for (const key of [...this.#sprites.keys()])
            this.#release(key);
        this.#shapes.clear();
        this.#wantedPieces = new Map();
        for (const key of [...this.#pieces.keys()])
            this.#releasePiece(key);
        // A contributed layer cannot outlive the surface it was drawn on.
        for (const { layer } of [...this.#layers.values()])
            layer.dispose();
        // Other boards and previews share Pixi's global pools.
        try {
            if (this.#application.renderer)
                this.#application.destroy({ removeView: true, releaseGlobalResources: false }, { children: true });
        }
        catch { /* Already torn down. */ }
    }
    /**
     * Fetches one tile and puts it on the board, answering with its key when it did not make it.
     *
     * The bytes are fetched directly rather than through the asset cache because only a request we
     * own can be abandoned: a fast pan used to pay for every tile it crossed, since a load already in
     * flight had no way of being told that nobody wanted it any more.
     */
    async #load(key, tile) {
        const controller = new AbortController();
        this.#inFlight.set(key, { controller, url: tile.url });
        const current = () => !this.#destroyed && !controller.signal.aborted
            && this.#inFlight.get(key)?.controller === controller && this.#wanted.get(key)?.url === tile.url;
        let bitmap;
        try {
            let blob = tileBlobCache.take(tile.url);
            if (!blob) {
                const response = await fetch(tile.url, { signal: controller.signal, credentials: "same-origin" });
                if (!response.ok)
                    return current() ? key : undefined;
                blob = await response.blob();
            }
            bitmap = await createImageBitmap(blob);
            // The board may have moved on while this tile was in flight; drop it rather than painting a
            // tile nobody is looking at any more.
            if (!current()) {
                bitmap.close();
                return undefined;
            }
            const sprite = new Sprite(Texture.from(bitmap));
            const placement = this.#wanted.get(key);
            sprite.position.set(placement.x, placement.y);
            sprite.scale.set(placement.scale);
            sprite.zIndex = placement.depth;
            // Keep the previous revision visible until its replacement is fully decoded.
            this.#release(key);
            this.#sprites.set(key, sprite);
            this.#spriteUrls.set(key, tile.url);
            this.#tiles.addChild(sprite);
            this.invalidate();
            return undefined;
        }
        catch {
            bitmap?.close();
            // An abort is this renderer's own doing, not a tile the caller should be told to ask for again.
            return current() ? key : undefined;
        }
        finally {
            if (this.#inFlight.get(key)?.controller === controller)
                this.#inFlight.delete(key);
        }
    }
    /** Ordinary motion reuses a piece; a teleport replaces only its rendered root. */
    async #showPiece(key, piece) {
        const standing = this.#pieces.get(key);
        if (standing && standing.imageUrl === piece.imageUrl &&
            standing.teleportVersion === (piece.teleportVersion ?? 0)) {
            this.#placePiece(standing, piece);
            return;
        }
        // Acquisition retains synchronously, keeping cached art alive when the old root is removed.
        const pendingTexture = piece.imageUrl ? this.#pieceTexture(piece.imageUrl) : undefined;
        if (standing && standing.teleportVersion !== (piece.teleportVersion ?? 0))
            this.#releasePiece(key);
        const texture = pendingTexture ? await pendingTexture : undefined;
        // The board may have moved on while the art loaded: another placement, or a scene change.
        const latest = this.#wantedPieces.get(key);
        if (this.#destroyed || !latest || latest.imageUrl !== piece.imageUrl ||
            (latest.teleportVersion ?? 0) !== (piece.teleportVersion ?? 0)) {
            if (piece.imageUrl && texture)
                pieceAssets.release(piece.imageUrl);
            return;
        }
        // Another update may have finished loading this same image while we awaited it.
        // Reuse that view and release this call's extra asset reference, never orphan a root.
        const loaded = this.#pieces.get(key);
        if (loaded && loaded.imageUrl === latest.imageUrl &&
            loaded.teleportVersion === (latest.teleportVersion ?? 0)) {
            if (piece.imageUrl && texture)
                pieceAssets.release(piece.imageUrl);
            this.#placePiece(loaded, latest);
            return;
        }
        if (loaded)
            this.#releasePiece(key);
        piece = latest;
        const root = new Container();
        const ring = new Graphics();
        const details = new Graphics();
        const conditions = new Container();
        const art = texture ? new Sprite(texture) : new Text({ text: initials(piece.label), resolution: this.#textResolution, style: { fill: piece.accent, fontFamily: "serif", fontSize: 10 } });
        art.anchor.set(.5);
        const label = new Text({ text: piece.label, resolution: this.#textResolution, style: {
            fill: "#f2ecdf", fontFamily: "sans-serif", fontWeight: "600", fontSize: 10,
            align: "center", stroke: { color: PIECE_GROUND, width: 2, join: "round" },
        } });
        label.anchor.set(.5, 0);
        root.addChild(ring, art, details, conditions, label);
        const view = {
            root, ring, details, conditions, art, label,
            teleportVersion: piece.teleportVersion ?? 0,
            ...(piece.imageUrl ? { imageUrl: piece.imageUrl } : {}),
            ...(piece.imageUrl && texture ? { retainedImageUrl: piece.imageUrl } : {}),
        };
        if (texture) {
            // Art arrives as whatever rectangle the sheet uploaded; the disc is what the table sees.
            const mask = new Graphics();
            root.addChild(mask);
            art.mask = mask;
            view.mask = mask;
        }
        this.#pieces.set(key, view);
        this.#figures.addChild(root);
        this.#placePiece(view, piece);
    }
    /** Everything about a piece that is only numbers: where it stands, how big, and what it says. */
    #placePiece(view, piece) {
        const radius = piece.size / 2, radiusY = (piece.height ?? piece.size) / 2;
        view.root.position.set(piece.x, piece.y);
        this.invalidate();
        const { x: _x, y: _y, ...appearance } = piece;
        const key = JSON.stringify(appearance);
        if (view.appearance === key)
            return;
        view.appearance = key;
        view.root.alpha = piece.hidden ? .4 : 1;
        view.art.angle = piece.rotation ?? 0;
        view.ring.clear().ellipse(0, 0, radius, radiusY).fill({ color: PIECE_GROUND, alpha: view.mask ? 0 : .85 });
        view.mask?.clear().ellipse(0, 0, radius, radiusY).fill({ color: "#ffffff" });
        if (view.art instanceof Sprite) {
            const source = Math.max(view.art.texture.width, view.art.texture.height) || 1;
            view.art.scale.set(piece.size / source);
        }
        else {
            view.art.style.fontSize = piece.size * .42;
            view.art.style.fill = piece.accent;
            view.art.text = initials(piece.label);
        }
        view.label.text = piece.label + (piece.hovered && piece.conditions?.length ? '\n' + piece.conditions.slice(0, 4).map(c => c.label).join(', ').slice(0, 100) : '');
        view.label.style.fontSize = piece.size * .24;
        view.label.style.lineHeight = piece.size * .32;
        const topBar = piece.bars?.bar_1?.max > 0;
        const bottomBar = piece.bars?.bar_2?.max > 0;
        const barHeight = 4, barGap = 5;
        view.label.position.set(0, radiusY + Math.max(piece.size * .08,
            bottomBar ? barGap + barHeight + 5 : 0));
        view.label.visible = piece.nameDisplay === 'always'
            || (piece.nameDisplay === 'selected' ? !!piece.selected
                : piece.nameDisplay === 'hover' ? !!piece.hovered : !!piece.selected || !!piece.hovered);
        const details = view.details.clear();
        if (piece.combat?.is_current)
            details.ellipse(0, 0, radius + 6, radiusY + 6).stroke({ width: 3, color: '#e9c46a' });
        if (piece.combat?.defeated) {
            const r = radius * .55;
            details.moveTo(-r, -r).lineTo(r, r).moveTo(r, -r).lineTo(-r, r).stroke({ width: 4, color: '#e77c7c' });
        }
        ['bar_1', 'bar_2'].forEach((slot) => {
            const bar = piece.bars?.[slot];
            if (!(bar?.max > 0))
                return;
            const y = slot === 'bar_1' ? -radiusY - barGap - barHeight : radiusY + barGap;
            const width = piece.size - 8;
            details.rect(-radius + 4, y, width, barHeight).fill({ color: '#000000', alpha: .65 });
            details.rect(-radius + 4, y, width * Math.max(0, Math.min(1, bar.value / bar.max)), barHeight).fill(bar.color || '#79c39a');
        });
        for (const child of view.conditions.removeChildren())
            child.destroy();
        const badges = piece.conditions ?? [];
        const badgeSize = Math.max(13, Math.min(21, piece.size / 3));
        const columns = Math.max(1, Math.floor(piece.size / (badgeSize + 2)));
        badges.slice(0, 8).forEach((condition, index) => {
            const color = condition.kind === 'negative' ? '#ee7777' : condition.kind === 'positive' ? '#79c39a' : '#d6b578';
            const glyph = condition.kind === 'negative' ? '☠' : condition.kind === 'positive' ? '✦' : '◆';
            const x = -radius + badgeSize / 2 + (index % columns) * (badgeSize + 2);
            const y = -radiusY - badgeSize / 2 - 3 - (topBar ? barGap + barHeight + 2 : 0)
                - Math.floor(index / columns) * (badgeSize + 2);
            details.roundRect(x - badgeSize / 2, y - badgeSize / 2, badgeSize, badgeSize, 3).fill('#10151b').stroke({ color, width: 1 });
            const icon = new Text({ text: glyph, resolution: this.#textResolution, style: { fontFamily: 'sans-serif', fontSize: badgeSize * .8, fill: color } });
            icon.anchor.set(.5);
            icon.position.set(x, y);
            view.conditions.addChild(icon);
        });
        if (badges.length > 8) {
            const more = new Text({ text: `+${badges.length - 8}`, resolution: this.#textResolution, style: { fontFamily: 'sans-serif', fontSize: 11, fill: '#f2ecdf', stroke: { color: '#10151b', width: 3 } } });
            more.position.set(radius + 3, -radiusY - 13);
            view.conditions.addChild(more);
        }
    }
    /**
     * Piece art keeps going through the asset cache rather than this renderer's own fetch: it comes
     * from wherever a sheet points at, and the cache already handles what an arbitrary origin needs.
     */
    async #pieceTexture(url) {
        // A piece whose art will not load still belongs on the board, drawn from its name instead.
        return await pieceAssets.acquire(url);
    }
    #releasePiece(key) {
        const view = this.#pieces.get(key);
        if (!view)
            return;
        this.#pieces.delete(key);
        view.root.removeFromParent();
        view.root.destroy({ children: true });
        this.invalidate();
        if (view.retainedImageUrl)
            pieceAssets.release(view.retainedImageUrl);
    }
    #release(key) {
        const sprite = this.#sprites.get(key);
        this.#spriteUrls.delete(key);
        if (!sprite)
            return;
        this.#sprites.delete(key);
        sprite.removeFromParent();
        // The texture is this renderer's to free: it was built from bytes it fetched itself, and no
        // asset cache is holding a second reference to it.
        sprite.destroy({ texture: true, textureSource: true });
        this.invalidate();
    }
}
export const createPixiBoardRenderer = async ({ host, background, label }) => {
    const application = new Application();
    try {
        await application.init({ resizeTo: host, background, antialias: true, autoDensity: true, autoStart: false, resolution: Math.min(devicePixelRatio, MAX_RESOLUTION) });
    }
    catch (error) {
        // A stage that failed halfway through `init` still holds a renderer; leaving it alive would
        // leak a WebGL context on every retry.
        try {
            if (application.renderer)
                application.destroy(false, { children: true });
        }
        catch { /* Never came up. */ }
        throw error;
    }
    host.appendChild(application.canvas);
    return new PixiBoardRenderer(application, label);
};
