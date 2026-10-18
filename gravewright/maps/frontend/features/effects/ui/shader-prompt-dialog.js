import { text as gwText } from '../../../shared/config/i18n/text.js';
import { normalizeShaderSource, shaderSource } from '../model/shader-source.js';
import { shaderPrompt } from '../model/shader-prompt.js';
import { mountModal } from '/static/gravewright_table/modal.js';

export function shaderInstructions(description) {
    return shaderPrompt.replace('<describe appearance, motion, density, and lighting behavior here>', () => description.trim());
}

export function openShaderPrompt(onInsert, onClose, { nested = false } = {}) {
    const previousFocus = document.activeElement;
    const dialog = document.createElement('section');
    dialog.className = 'table-modal-window shader-prompt-dialog';
    dialog.setAttribute('aria-labelledby', 'shader-prompt-title');
    let description = '', response = '', disposed = false;
    function element(tag, text, parent = dialog) {
        const node = document.createElement(tag);
        if (text) node.textContent = gwText(text);
        parent.append(node);
        return node;
    }
    function close() {
        if (disposed) return;
        disposed = true;
        dialog.close();
        if (previousFocus?.isConnected) previousFocus.focus();
        onClose();
    }
    dialog.addEventListener('close', close);
    dialog.addEventListener('keydown', event => event.stopPropagation());
    dialog.addEventListener('click', event => event.stopPropagation());
    function render(step) {
        dialog.replaceChildren();
        const header = element('header');
        element('strong', step === 1 ? 'Describe your shader' : 'Paste the AI-generated code', header).id = 'shader-prompt-title';
        const dismiss = element('button', '\u00d7', header);
        dismiss.type = 'button'; dismiss.dataset.close = ''; dismiss.setAttribute('aria-label', gwText('Close')); dismiss.onclick = close;
        const body = element('div'); body.className = 'table-modal-body';
        const hint = element('p', step === 1
            ? 'Describe the appearance, colors and movement you want. We will add the technical instructions and copy everything for your AI.'
            : 'Instructions copied! Paste them into your favorite AI. Then copy its complete GLSL response and paste it below. Insert into editor will place the code in the GLSL code field; save it there when you are ready.', body);
        hint.id = 'shader-prompt-hint';
        const label = element('label', step === 1 ? 'Desired effect' : 'GLSL returned by the AI', body);
        label.htmlFor = 'shader-prompt-input';
        const input = element('textarea', '', body);
        input.id = 'shader-prompt-input';
        input.setAttribute('aria-describedby', hint.id);
        input.rows = 8;
        input.maxLength = step === 1 ? 4000 : 40000;
        input.spellcheck = step === 1;
        input.value = step === 1 ? description : response;
        input.placeholder = gwText(step === 1 ? 'Example: slow violet mist with a few glowing sparks.' : 'Paste the complete shader code here.');
        const error = element('p', '', body);
        error.className = 'shader-prompt-dialog__error';
        error.setAttribute('role', 'alert');
        const actions = element('footer');
        const cancel = element('button', 'Cancel', actions);
        cancel.type = 'button'; cancel.onclick = close;
        if (step === 2) {
            const back = element('button', 'Back', actions);
            back.type = 'button'; back.onclick = () => { response = input.value; render(1); };
        }
        const confirm = element('button', step === 1 ? 'Copy instructions and continue' : 'Insert into editor', actions);
        confirm.type = 'button'; confirm.className = 'shader-prompt-dialog__confirm';
        confirm.disabled = !input.value.trim();
        input.oninput = () => { confirm.disabled = !input.value.trim(); error.textContent = ''; };
        confirm.onclick = async () => {
            error.textContent = '';
            if (step === 1) {
                description = input.value.trim();
                if (!description) return;
                confirm.disabled = true;
                try {
                    await navigator.clipboard.writeText(shaderInstructions(description));
                    if (!disposed) render(2);
                } catch {
                    if (!disposed) {
                        error.textContent = gwText('Could not copy the instructions. Allow clipboard access in your browser and try again.');
                        confirm.disabled = false;
                    }
                }
            } else {
                try {
                    input.value = normalizeShaderSource(input.value);
                    onInsert(shaderSource(input.value));
                    close();
                }
                catch (failure) { error.textContent = failure.message; }
            }
        };
        input.focus();
    }
    render(1);
    mountModal(dialog, { nested });
    dialog.querySelector('textarea').focus();
    return close;
}
