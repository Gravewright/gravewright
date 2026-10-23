import { mountModal } from '/static/gravewright_table/modal.js';
import { mappingDiagnostics } from './controller.js';

export function createPdfDiagnostics({ root, controller, t, onSelect }) {
    let active;
    return {
        open() {
            if (!controller.view.canConfigureFieldActions) return;
            active?.close(true);
            const document = root.ownerDocument, modal = document.createElement('section');
            modal.className = 'table-form-modal pdf-diagnostics'; modal.dataset.pdfDiagnostics = '';
            const form = document.createElement('form'), header = document.createElement('header');
            const title = document.createElement('strong'); title.textContent = t('PDF mapping diagnostics');
            const close = document.createElement('button'); close.type = 'button'; close.textContent = t('Close');
            close.dataset.pdfDiagnosticsClose = '';
            close.addEventListener('click', () => modal.close()); header.append(title, close);
            modal.setAttribute('aria-label', title.textContent);
            const body = document.createElement('div'); body.className = 'table-form-modal__body';
            const issues = mappingDiagnostics(controller.view);
            if (!issues.length) {
                const p = document.createElement('p'); p.textContent = t('No mapping problems found.'); body.append(p);
            }
            for (const issue of issues) {
                const row = document.createElement('div'), p = document.createElement('p');
                if (issue.field) {
                    const label = document.createElement('strong');
                    label.setAttribute('translate', 'no');
                    label.textContent = controller.view.fields[issue.field]?.label
                        || controller.view.referenceFields.find(binding => binding.field === issue.field)?.name || issue.field;
                    row.append(label);
                }
                p.textContent = t(issue.message, issue.params); row.append(p);
                if (controller.view.fields[issue.field]) {
                    const button = document.createElement('button'); button.type = 'button'; button.textContent = t('Go to field');
                    button.addEventListener('click', () => { modal.close(); void onSelect(issue.field); }); row.append(button);
                }
                body.append(row);
            }
            form.append(header, body); modal.append(form);
            modal.addEventListener('submit', event => event.preventDefault());
            modal.addEventListener('close', () => { if (active === modal) active = undefined; }, { once: true });
            active = mountModal(modal, { nested: true });
        },
        destroy() { active?.close(true); active = undefined; },
    };
}
