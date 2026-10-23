import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filledPdf } from '../static/gravewright_pdf_system/filled-pdf.js';

const jpeg = new Uint8Array([255, 216, 1, 2, 255, 217]);
const lib = { AnnotationMode: { ENABLE_FORMS: 2 } };

function trackedSignal() {
    const controller = new AbortController(), listeners = new Set();
    const signal = {
        throwIfAborted: () => controller.signal.throwIfAborted(),
        addEventListener(type, callback, options) {
            if (type === 'abort') listeners.add(callback);
            controller.signal.addEventListener(type, callback, options);
        },
        removeEventListener(type, callback, options) {
            if (type === 'abort') listeners.delete(callback);
            controller.signal.removeEventListener(type, callback, options);
        },
    };
    return { controller, signal, listeners };
}

function canvasDocument({ encode } = {}) {
    const canvases = [];
    const document = {
        createElement(tag) {
            assert.equal(tag, 'canvas');
            const calls = { rects: [], text: [], encodes: [] };
            const context = {
                save() {}, restore() {}, beginPath() {}, clip() {}, stroke() {},
                rect(...bounds) { calls.rects.push(bounds); },
                fillText(text, x, y) { calls.text.push({ text, x, y, color: this.fillStyle }); },
                measureText(text) { return { width: Array.from(text).length * 5 }; },
                strokeRect() {}, moveTo() {}, lineTo() {},
            };
            const canvas = {
                width: 0, height: 0, calls,
                getContext(kind) { assert.equal(kind, '2d'); return context; },
                toBlob(callback, type, quality) {
                    calls.encodes.push([type, quality]);
                    callback(encode ? encode(canvas) : new Blob([jpeg], { type: 'image/jpeg' }));
                },
            };
            canvases.push(canvas);
            return canvas;
        },
    };
    return { document, canvases };
}

function page({ rotation = 0, annotations = [], render, getAnnotations = true } = {}) {
    const renders = [], annotationReads = [];
    const value = {
        renders, annotationReads,
        getViewport({ scale }) {
            const width = (rotation === 90 ? 300 : 200) * scale;
            const height = (rotation === 90 ? 200 : 300) * scale;
            return { width, height, rotation,
                convertToViewportPoint(x, y) {
                    return rotation === 90
                        ? [y * scale, x * scale]
                        : [x * scale, height - y * scale];
                } };
        },
        render(options) {
            renders.push(options);
            return render ? render(options) : { promise: Promise.resolve(), cancel() {} };
        },
    };
    if (getAnnotations) value.getAnnotations = async options => {
        annotationReads.push(options);
        return typeof annotations === 'function' ? annotations() : annotations;
    };
    return value;
}

function documentWithPages(pages) {
    const reads = [];
    return { reads, numPages: pages.length, async getPage(number) { reads.push(number); return pages[number - 1]; } };
}

test('filled export paints every repeated native widget and normalized manual fields on rotated pages', async () => {
    const shared = 'Repeated score', manual = 'manual_example';
    const firstRect = [10, 20, 90, 50], secondRect = [100, 100, 180, 130], rotatedRect = [20, 30, 100, 60];
    const first = page({ annotations: [
        { subtype: 'Widget', fieldName: shared, rect: firstRect },
        { subtype: 'Widget', fieldName: shared, rect: secondRect },
        { subtype: 'Widget', fieldName: 'Unmapped document field', rect: firstRect },
        { subtype: 'Text', fieldName: shared, rect: firstRect },
    ] });
    const second = page({ rotation: 90, annotations: [{ subtype: 'Widget', fieldName: shared, rect: rotatedRect }] });
    const doc = documentWithPages([first, second]), drawing = canvasDocument(), lifetime = trackedSignal();
    const fieldIndex = new Map([
        [shared, { page: 1, rect: firstRect }],
        [manual, { page: 2, manual: { x: 0.25, y: 0.5, width: 0.2, height: 0.1 } }],
    ]);
    const values = [], progress = [];
    const bytes = await filledPdf({ doc, lib, fields: { [shared]: { type: 'number' }, [manual]: { type: 'string' } },
        fieldIndex, value(name) { values.push(name); return name === shared ? 42 : 'Note'; },
        color: '#123456', document: drawing.document, signal: lifetime.signal,
        onProgress: (...entry) => progress.push(entry) });

    assert.equal(values.filter(name => name === shared).length, 3);
    assert.equal(values.filter(name => name === manual).length, 1);
    assert.deepEqual(drawing.canvases[0].calls.rects, [[20, 500, 160, 60], [200, 340, 160, 60]]);
    assert.deepEqual(drawing.canvases[1].calls.rects, [[60, 40, 60, 160], [150, 200, 120, 40]]);
    assert.deepEqual(drawing.canvases[0].calls.text.map(entry => entry.text), ['42', '42']);
    assert.deepEqual(drawing.canvases[1].calls.text.map(entry => entry.text), ['42', 'Note']);
    assert.ok(drawing.canvases.flatMap(canvas => canvas.calls.text).every(entry => entry.color === '#123456'));
    assert.deepEqual(progress, [[1, 2], [2, 2]]);
    assert.equal(first.annotationReads.length, 1);
    assert.equal(second.annotationReads.length, 1);
    assert.ok([first, second].every(value => value.renders[0].annotationMode === lib.AnnotationMode.ENABLE_FORMS));
    const pdf = new TextDecoder('latin1').decode(bytes);
    assert.match(pdf, /\/Count 2/);
    assert.match(pdf, /\/MediaBox \[0 0 300 200\]/);
    assert.doesNotMatch(pdf, /\/JavaScript|\/OpenAction|\/AcroForm/);
    assert.ok(drawing.canvases.every(canvas => canvas.width === 0 && canvas.height === 0));
    assert.equal(lifetime.listeners.size, 0);
});

test('indexed native fields remain exportable when the page annotation list omits them', async () => {
    const doc = documentWithPages([page({ annotations: [] })]);
    const drawing = canvasDocument(), lifetime = trackedSignal();
    await filledPdf({ doc, lib, fields: { Score: { type: 'number' } },
        fieldIndex: new Map([['Score', { page: 1, rect: [10, 20, 90, 50] }]]),
        value: () => 7, color: '#111111', document: drawing.document, signal: lifetime.signal });
    assert.deepEqual(drawing.canvases[0].calls.text.map(entry => entry.text), ['7']);
    assert.equal(drawing.canvases[0].width, 0);
    assert.equal(lifetime.listeners.size, 0);
});

test('aborting an active page cancels its render, releases its canvas and stops later pages', async () => {
    let entered, rejectRender, cancelled = 0;
    const rendering = new Promise(resolve => { entered = resolve; });
    const first = page({ render() {
        const promise = new Promise((resolve, reject) => { rejectRender = reject; });
        entered();
        return { promise, cancel() { cancelled++; rejectRender(new DOMException('Rendering aborted', 'AbortError')); } };
    } });
    const doc = documentWithPages([first, page()]), drawing = canvasDocument(), lifetime = trackedSignal();
    const exporting = filledPdf({ doc, lib, fields: {}, fieldIndex: new Map(), value: () => '', color: '#111111',
        document: drawing.document, signal: lifetime.signal });
    await rendering;
    lifetime.controller.abort();
    await assert.rejects(exporting, error => error.name === 'AbortError');
    assert.equal(cancelled, 1);
    assert.deepEqual(doc.reads, [1]);
    assert.equal(drawing.canvases[0].calls.encodes.length, 0);
    assert.equal(drawing.canvases[0].width, 0);
    assert.equal(drawing.canvases[0].height, 0);
    assert.equal(lifetime.listeners.size, 0);
});

test('annotation and image encoding failures release disposable rendering resources', async () => {
    for (const failure of ['annotations', 'encoding']) {
        const first = page({ annotations: failure === 'annotations' ? () => { throw new Error('Broken PDF annotations'); } : [] });
        const drawing = canvasDocument({ encode: failure === 'encoding' ? () => null : undefined });
        const lifetime = trackedSignal();
        await assert.rejects(filledPdf({ doc: documentWithPages([first]), lib, fields: {}, fieldIndex: new Map(),
            value: () => '', color: '#111111', document: drawing.document, signal: lifetime.signal }),
        failure === 'annotations' ? /Broken PDF annotations/ : /Could not encode a filled PDF page/);
        assert.equal(drawing.canvases[0].width, 0);
        assert.equal(drawing.canvases[0].height, 0);
        assert.equal(lifetime.listeners.size, 0);
    }
});
