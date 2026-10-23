import { sourceKey, validManualField } from './manual-fields.js';
import { fieldReferences, expandFieldFormula, bindingsForSource, bindingPath } from './formulas.js';
import { readCanonical } from './mapping.js';

/** Diagnose the active mapping without mutating authored definitions or values. */
export function mappingDiagnostics(view) {
    const source = sourceKey(view.currentSource), pdf = view.actor?.data.pdf;
    if (!pdf || !source) return [];
    const issues = [], names = new Set(Object.keys(view.fields)), bindings = bindingsForSource(pdf, source);
    const issue = (code, field, message, params = {}) => issues.push({ code, field, message, params });
    const actual = view.sourceDocument;
    const expected = (pdf.sourceMetadata || []).find(row => row.source === source);
    if (actual && expected) {
        if (expected.pageCount !== actual.pageCount)
            issue('page-count', '', 'The PDF page count differs from the saved mapping. Check the field positions.');
        const changed = (expected.pages || []).some(page => {
            const current = actual.pages.find(row => row.page === page.page);
            return current && (Math.abs(current.width - page.width) > .5 || Math.abs(current.height - page.height) > .5 || current.rotation !== page.rotation);
        });
        if (changed) issue('page-geometry', '', 'PDF page sizes or rotations differ from the saved mapping. Check the field positions.');
        else if (expected.fingerprint && actual.fingerprint && expected.fingerprint !== actual.fingerprint)
            issue('document-changed', '', 'This PDF differs from the document used to create the mapping.');
    }
    for (const field of (pdf.manualFields || []).filter(row => row.source === source)) {
        if (!validManualField(field)) issue('field-bounds', '', 'A mapped field has invalid page bounds: {0}.', [field.name || field.id]);
        else if (actual && field.page > actual.pageCount)
            issue('field-page', `manual_${field.id.replaceAll('-', '')}`, 'A mapped field refers to a missing PDF page: {0}.', [field.name]);
    }
    for (const [kind, rows] of [['roll', pdf.fieldActions || []], ['calculation', pdf.calculatedFields || []]]) {
        for (const row of rows.filter(row => row.source === source)) {
            if (!names.has(row.field)) issue('orphan-action', row.field, 'An action has no matching PDF field: {0}.', [bindings[row.field]?.name || row.field]);
            const formula = kind === 'roll' ? row.roll.formula : row.formula;
            try {
                for (const reference of fieldReferences(formula, { allowValue: kind === 'roll' }))
                    if (!names.has(reference)) issue('missing-reference', row.field, 'A formula references a field that is no longer on this PDF: {0}.', [bindings[reference]?.name || reference]);
                if (kind === 'roll') expandFieldFormula(formula, reference => {
                    if (!bindings[reference]) throw Error('A referenced PDF field is not available.');
                    return readCanonical(view.actor, bindingPath(view.actor.data, bindings[reference]));
                }, { value: view.fields[row.field] ? readCanonical(view.actor, view.fields[row.field].path) : '' });
            } catch (error) { issue('formula-value', row.field, error.message); }
        }
    }
    for (const error of view.calculationErrors || []) issue('calculation-value', error.field, error.message);
    return issues;
}
