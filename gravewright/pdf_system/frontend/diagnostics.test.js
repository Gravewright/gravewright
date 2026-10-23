import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mappingDiagnostics } from './diagnostics.js';

const source = 'template:generic';
function view() {
    return { currentSource: source, actor: { data: { pdf: {}, fields: {} } }, fields: {},
        sourceDocument: { pageCount: 1, fingerprint: 'now', pages: [{ page: 1, width: 595, height: 842, rotation: 0 }] }, calculationErrors: [] };
}
test('mapping diagnostics identify changed document geometry and preserve the input', () => {
    const v = view();
    v.actor.data.pdf.sourceMetadata = [{ source, pageCount: 2, fingerprint: 'before', pages: [{ page: 1, width: 842, height: 595, rotation: 90 }] }];
    const before = structuredClone(v);
    assert.deepEqual(mappingDiagnostics(v).map(row => row.code), ['page-count', 'page-geometry']);
    assert.deepEqual(v, before);
});
test('mapping diagnostics expose missing widgets, archived references and calculation failures', () => {
    const v = view();
    v.actor.data.pdf.fieldActions = [{ source, field: 'missing', roll: { formula: '1d6 + @{archived}', label: '' } }];
    v.actor.data.pdf.fieldBindings = [{ source, field: 'archived', path: 'sheet.fields.old', type: 'number', name: 'Old score' }];
    v.actor.data.fields.old = 4;
    v.calculationErrors = [{ field: 'total', message: 'Invalid PDF field formula.' }];
    assert.deepEqual(mappingDiagnostics(v).map(row => row.code), ['orphan-action', 'missing-reference', 'calculation-value']);
    assert.deepEqual(mappingDiagnostics(view()), []);
});
