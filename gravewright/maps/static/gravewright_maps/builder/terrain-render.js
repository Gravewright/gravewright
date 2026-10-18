/** Disposable SVG mask images for bounded terrain strokes, never campaign assets. */
import { terrainBrushMask } from './terrain-brush.js';

export function createTerrainMaskCache() {
    const entries = new Map();
    return {
        get(item, cellSize) {
            const signature = JSON.stringify([item.x, item.y, item.width, item.height, item.brush, cellSize]);
            const cached = entries.get(item.id);
            if (cached?.signature === signature) return cached;
            const mask = terrainBrushMask(item, cellSize), canvas = document.createElement('canvas');
            canvas.width = mask.width; canvas.height = mask.height;
            try {
                const context = canvas.getContext('2d'), pixels = context.createImageData(mask.width, mask.height);
                const color = item.brush.operation === 'erase' ? 0 : 255;
                for (let index = 0; index < mask.alpha.length; index++) {
                    const offset = index * 4;
                    pixels.data[offset] = color; pixels.data[offset + 1] = color; pixels.data[offset + 2] = color;
                    pixels.data[offset + 3] = mask.alpha[index];
                }
                context.putImageData(pixels, 0, 0);
                const value = { signature, url: canvas.toDataURL('image/png'), x: mask.left / cellSize,
                    y: mask.top / cellSize, width: mask.width / cellSize, height: mask.height / cellSize };
                entries.set(item.id, value); return value;
            } finally { canvas.width = canvas.height = 0; }
        },
        prune(floors) {
            const ids = new Set(floors.filter(item => item.brush).map(item => item.id));
            for (const id of entries.keys()) if (!ids.has(id)) entries.delete(id);
        },
        dispose() { entries.clear(); },
    };
}
