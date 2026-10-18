/** Small builder adapter; the GPU engine is loaded only for visible effects. */
export { lightPresets, particlePresets, particleDefaults, shaderPresets, createLight, createParticle, createShader } from '../builder-catalog.js';
import { nativeEffectState, hasNativeEffects } from './native-effects-model.js';

let rendererModule;
export function mountNativeEffects({ host, svg, onError = () => {} }) {
    let preview, projected, visible = true, disposed = false, generation = 0, failed = false, contentKey = '', failedKey = '';
    const abort = new AbortController();
    function stop() { generation++; preview?.dispose(); preview = undefined; host.dataset.renderState = 'idle'; }
    async function render() {
        if (disposed || !projected || !visible || document.hidden || !hasNativeEffects(projected)) { stop(); return; }
        if (failed) return;
        if (preview) { preview.update(projected); return; }
        const visit = ++generation;
        host.dataset.renderState = 'loading';
        try {
            rendererModule ??= import('../builder-native.js');
            const module = await rendererModule;
            if (disposed || visit !== generation) return;
            preview = module.mountNativePreview({ host, svg, onError: cause => {
                failed = true; failedKey = contentKey; stop(); host.dataset.renderState = 'failed'; onError(cause);
            } });
            preview.update(projected);
        } catch (cause) {
            if (disposed || visit !== generation) return;
            rendererModule = undefined;
            failed = true; failedKey = contentKey; stop(); host.dataset.renderState = 'failed'; onError(cause);
        }
    }
    document.addEventListener('visibilitychange', () => { void render(); }, { signal: abort.signal });
    return {
        update(value, { visible: next = visible } = {}) {
            if (disposed) return;
            projected = nativeEffectState(value); visible = next;
            contentKey = JSON.stringify(projected);
            if (failed && contentKey !== failedKey) failed = false;
            void render();
        },
        setVisible(next) { if (!disposed && visible !== next) { visible = next; void render(); } },
        dispose() { if (!disposed) { disposed = true; abort.abort(); stop(); } },
    };
}
