/** Measure wall artwork once, retaining only its visible bounds between renders. */
export function createWallArtCache({ onReady, onError }) {
    const entries = new Map();
    let disposed = false;
    return {
        get(asset) {
            const cached = entries.get(asset.id);
            if (cached?.url === asset.url) return cached;
            cached?.cancel?.();
            const image = new Image();
            const entry = { url: asset.url, status: 'pending', cancel: () => {
                image.onload = image.onerror = null; image.removeAttribute('src');
            } };
            entries.set(asset.id, entry);
            image.onload = () => {
                if (disposed) return;
                const canvas = document.createElement('canvas');
                try {
                    const width = image.naturalWidth, height = image.naturalHeight;
                    if (!width || !height || width * height > 40_000_000) throw new Error('Invalid wall image dimensions.');
                    canvas.width = width; canvas.height = height;
                    const context = canvas.getContext('2d', { willReadFrequently: true });
                    context.drawImage(image, 0, 0);
                    const pixels = context.getImageData(0, 0, width, height).data;
                    let left = width, top = height, right = -1, bottom = -1;
                    // Match the server's alpha threshold, excluding invisible export noise.
                    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
                        if (pixels[(y * width + x) * 4 + 3] < 8) continue;
                        left = Math.min(left, x); right = Math.max(right, x);
                        top = Math.min(top, y); bottom = Math.max(bottom, y);
                    }
                    Object.assign(entry, { status: 'ready', width, height,
                        bounds: right < left ? { x: 0, y: 0, width, height }
                            : { x: left, y: top, width: right - left + 1, height: bottom - top + 1 } });
                } catch (error) {
                    entry.status = 'error'; onError(asset, error);
                } finally {
                    canvas.width = canvas.height = 0;
                    entry.cancel(); delete entry.cancel;
                }
                onReady(asset.id);
            };
            image.onerror = error => {
                if (disposed) return;
                entry.status = 'error'; entry.cancel(); delete entry.cancel;
                onError(asset, error); onReady(asset.id);
            };
            image.src = asset.url;
            return entry;
        },
        dispose() {
            disposed = true;
            for (const entry of entries.values()) entry.cancel?.();
            entries.clear();
        },
    };
}
