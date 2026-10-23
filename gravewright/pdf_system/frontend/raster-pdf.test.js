import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rasterPdf } from './raster-pdf.js';

test('flattened PDF byte offsets, page resources and binary image lengths remain exact', () => {
    const jpeg = new Uint8Array([255, 216, 128, 0, 10, 255, 217]);
    const page = { width: 595, height: 842, pixelWidth: 1190, pixelHeight: 1684, jpeg };
    const bytes = rasterPdf([page, { ...page, width: 842, height: 595 }]);
    const source = new TextDecoder('latin1').decode(bytes);
    assert.match(source, /\/Count 2/);
    assert.match(source, /\/MediaBox \[0 0 842 595\]/);
    assert.match(source, /\/Filter \/DCTDecode \/Length 7/);
    const start = Number(source.match(/startxref\n(\d+)/)[1]);
    assert.equal(new TextDecoder().decode(bytes.slice(start, start + 4)), 'xref');
    const xref = new TextDecoder().decode(bytes.slice(start)).split('\n').slice(3, 11);
    xref.forEach((entry, i) => {
        assert.equal(new TextEncoder().encode(entry + '\n').length, 20);
        const offset = Number(entry.slice(0, 10));
        assert.equal(new TextDecoder().decode(bytes.slice(offset, offset + `${i + 1} 0 obj`.length)), `${i + 1} 0 obj`);
    });
    assert.doesNotMatch(source, /\/JavaScript|\/OpenAction|\/EmbeddedFile/);
});

test('filled PDF export rejects empty, excessive or malformed pages', () => {
    for (const pages of [[], Array(101).fill({}), [{}], [{ width: NaN }]])
        assert.throws(() => rasterPdf(pages));
});
