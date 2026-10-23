import { rasterPdf, fieldBounds } from './controller.js';

function linesFor(context, text, width, multiline) {
    if (!multiline) return [text.replace(/[\r\n]+/g, ' ')];
    const result = [];
    for (const paragraph of text.split(/\r?\n/)) {
        let line = '';
        for (const character of paragraph) {
            if (line && context.measureText(line + character).width > width) { result.push(line); line = ''; }
            line += character;
        }
        result.push(line);
    }
    return result;
}

function paintValue(context, rect, value, spec, color) {
    const { left, top, width, height } = rect;
    context.save();
    context.beginPath(); context.rect(left, top, width, height); context.clip();
    context.fillStyle = color;
    if (spec.type === 'boolean') {
        context.strokeStyle = color; context.lineWidth = Math.max(1, Math.min(width, height) / 18);
        context.strokeRect(left + 1, top + 1, Math.max(0, width - 2), Math.max(0, height - 2));
        if (value) {
            context.strokeStyle = color; context.lineWidth = Math.max(1, Math.min(width, height) / 10);
            context.beginPath(); context.moveTo(left + width * .2, top + height * .5);
            context.lineTo(left + width * .42, top + height * .75);
            context.lineTo(left + width * .82, top + height * .2); context.stroke();
        }
    } else {
        const text = String(value ?? '');
        if (text.length > 20000) throw new Error('A PDF field contains too much text to export.');
        const inset = Math.min(4, width / 10), available = Math.max(1, width - 2 * inset);
        let size = Math.min(24, height * .72), lines = [];
        for (; size >= 8; size -= 1) {
            context.font = `${size}px sans-serif`;
            lines = linesFor(context, text, available, spec.multiline);
            if (lines.every(line => context.measureText(line).width <= available)
                && lines.length * size * 1.15 <= height) break;
        }
        if (text && size < 8) throw new Error('A PDF field is too small for its text. Enlarge it before exporting.');
        context.textBaseline = 'top';
        lines.forEach((line, i) => context.fillText(line, left + inset, top + i * size * 1.15 + Math.max(0, (height - lines.length * size * 1.15) / 2)));
    }
    context.restore();
}

/** Render into disposable canvases; the viewer and original file stay untouched. */
export async function filledPdf({ doc, lib, fields, fieldIndex, value, color, document, signal, onProgress }) {
    if (!doc || doc.numPages > 100) throw new Error('Export between 1 and 100 PDF pages.');
    const pages = [];
    let pixels = 0, bytes = 0;
    for (let number = 1; number <= doc.numPages; number++) {
        signal.throwIfAborted();
        onProgress?.(number, doc.numPages);
        const page = await doc.getPage(number), viewport = page.getViewport({ scale: 2 });
        const pixelWidth = Math.ceil(viewport.width), pixelHeight = Math.ceil(viewport.height);
        pixels += pixelWidth * pixelHeight;
        if (pixelWidth > 16384 || pixelHeight > 16384 || pixelWidth * pixelHeight > 16_000_000 || pixels > 128_000_000)
            throw new Error('This PDF is too large to export as a filled copy.');
        const canvas = document.createElement('canvas');
        canvas.width = pixelWidth; canvas.height = pixelHeight;
        const context = canvas.getContext('2d');
        let task;
        const cancel = () => task?.cancel();
        signal.addEventListener('abort', cancel, { once: true });
        try {
            task = page.render({ canvas, viewport, annotationMode: lib.AnnotationMode.ENABLE_FORMS, background: 'rgb(255,255,255)' });
            await task.promise;
            signal.throwIfAborted();
            const nativeRects = new Map();
            for (const annotation of await page.getAnnotations({ intent: 'display' })) {
                if (annotation.subtype !== 'Widget' || !annotation.fieldName || !Object.hasOwn(fields, annotation.fieldName)) continue;
                const rectangles = nativeRects.get(annotation.fieldName) || [];
                rectangles.push(annotation.rect);
                nativeRects.set(annotation.fieldName, rectangles);
            }
            signal.throwIfAborted();
            for (const [name, spec] of Object.entries(fields)) {
                const info = fieldIndex.get(name);
                if (!info) continue;
                const rectangles = info.manual
                    ? (info.page === number ? [[info.manual.x * viewport.width, info.manual.y * viewport.height,
                        info.manual.width * viewport.width, info.manual.height * viewport.height]] : [])
                    : (nativeRects.get(name) || (info.page === number ? [info.rect] : [])).map(rect => {
                        const r = fieldBounds(viewport, rect);
                        return [r.left, r.top, r.width, r.height];
                    });
                for (const bounds of rectangles)
                    paintValue(context, { left: bounds[0], top: bounds[1], width: bounds[2], height: bounds[3] }, value(name), spec, color);
            }
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .94));
            if (!blob) throw new Error('Could not encode a filled PDF page.');
            bytes += blob.size;
            if (bytes > 90_000_000) throw new Error('The filled PDF is too large to export.');
            pages.push({ width: viewport.width / 2, height: viewport.height / 2, pixelWidth, pixelHeight,
                jpeg: new Uint8Array(await blob.arrayBuffer()) });
        } finally {
            signal.removeEventListener('abort', cancel);
            canvas.width = canvas.height = 0;
        }
    }
    signal.throwIfAborted();
    return rasterPdf(pages);
}
