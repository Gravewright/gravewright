import { Texture } from 'pixi.js';
/** Reused, bounded atlas. Visibility masks are calculated once per scene update. */
export class SceneLightMap {
    ambient;
    canvas = document.createElement('canvas');
    texture;
    context;
    scale;
    #pixels;
    constructor(width, height, edge, ambient) {
        this.ambient = ambient;
        this.scale = Math.min(1, edge / Math.max(width, height));
        this.canvas.width = Math.max(1, Math.ceil(width * this.scale));
        this.canvas.height = Math.max(1, Math.ceil(height * this.scale));
        this.context = this.canvas.getContext('2d', { willReadFrequently: true });
        this.texture = Texture.from(this.canvas);
    }
    update(stamps, readPixels) {
        const ctx = this.context;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalCompositeOperation = 'source-over';
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        ctx.scale(this.scale, this.scale);
        for (const s of stamps) {
            ctx.save();
            ctx.beginPath();
            s.polygon.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
            ctx.closePath();
            ctx.clip();
            ctx.globalCompositeOperation = 'lighter';
            ctx.drawImage(s.canvas, s.x - s.radius, s.y - s.radius, s.radius * 2, s.radius * 2);
            ctx.restore();
        }
        this.#pixels = readPixels ? ctx.getImageData(0, 0, this.canvas.width, this.canvas.height).data : undefined;
        this.texture.source.update();
    }
    tint(color, x, y, response) {
        const base = parseInt(color.slice(1), 16), pixels = this.#pixels;
        if (!pixels || response <= 0)
            return base;
        const px = Math.max(0, Math.min(this.canvas.width - 1, Math.floor(x * this.scale))), py = Math.max(0, Math.min(this.canvas.height - 1, Math.floor(y * this.scale))), index = (py * this.canvas.width + px) * 4;
        let output = 0;
        for (let c = 0; c < 3; c++) {
            const shift = 16 - c * 8, channel = (base >> shift & 255) / 255;
            const illumination = Math.min(1.5, this.ambient + (pixels[index + c] ?? 0) / 255 * (pixels[index + 3] ?? 0) / 255);
            const value = Math.pow(Math.pow(channel, 2.2) * ((1 - response) + response * illumination), 1 / 2.2);
            output |= Math.min(255, Math.round(value * 255)) << shift;
        }
        return output;
    }
    dispose() { this.#pixels = undefined; this.texture.destroy(true); this.canvas.width = this.canvas.height = 1; }
}
