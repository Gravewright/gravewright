import { text as gwText } from '../../../shared/config/i18n/text.js';
import { normalizeShaderSource } from '../model/shader-source.js';
import { shaderPrompt } from '../model/shader-prompt.js';

export function shaderInstructions(description) {
    return shaderPrompt.replace('<describe appearance, motion, density, and lighting behavior here>', () => description.trim());
}

export function shaderSource(value) {
    const source = normalizeShaderSource(value);
    const code = source.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, '');
    if (!source) throw new Error(gwText('Paste the GLSL code returned by your AI. The field is empty.'));
    if (source.length > 32000) throw new Error(gwText('The shader exceeds the limit of 32,000 characters. Ask your AI for a shorter version.'));
    if (!/\bvoid\s+main\s*\(\s*(?:void\s*)?\)/.test(code)) {
        throw new Error(gwText('The pasted code does not contain void main(). Copy the complete shader, including its main function.'));
    }

    return source;
}

export function openShaderPrompt(onInsert, onClose) {
    const previousFocus = document.activeElement;
    const dialog = document.createElement('dialog');
    dialog.className = 'shader-prompt-dialog';
    dialog.setAttribute('aria-labelledby', 'shader-prompt-title');
    document.body.append(dialog);
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
        window.removeEventListener('keydown', modalEscape, true);
        dialog.close();
        dialog.remove();
        if (previousFocus?.isConnected) previousFocus.focus();
        onClose();
    }
    function modalEscape(event) {
        if (event.key !== 'Escape' || disposed) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        close();
    }
    window.addEventListener('keydown', modalEscape, true);
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    dialog.addEventListener('keydown', event => event.stopPropagation());
    dialog.addEventListener('click', event => event.stopPropagation());
    function render(step) {
        dialog.replaceChildren();
        element('h2', step === 1 ? 'Describe your shader' : 'Paste the AI-generated code').id = 'shader-prompt-title';
        const hint = element('p', step === 1
            ? 'Describe the appearance, colors and movement you want. We will add the technical instructions and copy everything for your AI.'
            : 'Instructions copied! Paste them into your favorite AI. Then copy its complete GLSL response and paste it below. Insert into editor will place the code in the GLSL code field; save it there when you are ready.');
        hint.id = 'shader-prompt-hint';
        const label = element('label', step === 1 ? 'Desired effect' : 'GLSL returned by the AI');
        label.htmlFor = 'shader-prompt-input';
        const input = element('textarea');
        input.id = 'shader-prompt-input';
        input.setAttribute('aria-describedby', hint.id);
        input.rows = 8;
        input.maxLength = step === 1 ? 4000 : 40000;
        input.spellcheck = step === 1;
        input.value = step === 1 ? description : response;
        input.placeholder = gwText(step === 1 ? 'Example: slow violet mist with a few glowing sparks.' : 'Paste the complete shader code here.');
        const error = element('p');
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
    dialog.showModal();
    dialog.querySelector('textarea').focus();
    return close;
}
