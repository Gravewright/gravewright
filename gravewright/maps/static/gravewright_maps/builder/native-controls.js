import { lightPresets, particlePresets, shaderPresets, createLight, createParticle, createShader } from './native-effects.js';

export const isNativeKind = kind => ['lights', 'particles', 'shaders'].includes(kind);
export const nativeFactory = (tool, preset, x = 0, y = 0) => tool === 'light' ? createLight(preset, x, y)
    : tool === 'particle' ? createParticle(preset, x, y) : createShader(preset, x, y);
export const nativeCatalog = tool => tool === 'light' ? lightPresets : tool === 'particle' ? particlePresets : shaderPresets;
const particleNames = { smoke: 'Smoke', ember: 'Embers', dust: 'Dust', arcane: 'Arcane', rain: 'Rain', snow: 'Snow',
    firefly: 'Fireflies', leaves: 'Leaves', bubbles: 'Bubbles', ash: 'Ash', blood: 'Blood', runes: 'Runes' };
export const presetName = (tool, preset, t) => t(tool === 'particle' ? particleNames[preset.id || preset.kind] || preset.name : preset.name);
const animations = [['none', 'Steady'], ['torch', 'Torch'], ['pulse', 'Pulse'], ['candle', 'Candle'], ['fire', 'Fire'], ['arcane', 'Arcane'], ['smoke', 'Smoke']];

/** Native catalogs supply data; these cards only choose a placement brush. */
export function renderNativeLibrary(container, { role, effectTool, search, choices, t, choose, signal }) {
    const tools = role === 'light' ? ['light'] : ['particle', 'shader'].includes(effectTool) ? [effectTool] : ['particle', 'shader'];
    let count = 0;
    for (const tool of tools) {
        const group = document.createElement('section'); group.className = 'map-builder__native-group';
        const heading = document.createElement('h3'); heading.textContent = t({ light: 'Lights', particle: 'Particles', shader: 'Shaders' }[tool]);
        const cards = document.createElement('div'); cards.className = 'map-builder__native-cards';
        for (const preset of nativeCatalog(tool)) {
            const id = preset.id || preset.kind, name = presetName(tool, preset, t);
            if (search && !`${name} ${preset.description || ''} ${preset.category || ''}`.toLocaleLowerCase().includes(search)) continue;
            const card = document.createElement('button'); card.type = 'button';
            card.className = 'map-builder__asset map-builder__native-preset';
            card.setAttribute(`data-builder-${tool}-preset`, id);
            card.setAttribute('aria-pressed', String(choices[tool] === id));
            card.title = preset.description ? `${name}: ${t(preset.description)}` : name;
            const sample = document.createElement('span'); sample.className = `map-builder__native-swatch map-builder__native-swatch--${tool}`;
            sample.style.setProperty('--native-color', preset.color || '#ffc977'); sample.setAttribute('aria-hidden', 'true');
            sample.textContent = tool === 'light' ? '☀' : tool === 'particle' ? '✦' : '◈';
            const label = document.createElement('span'); label.textContent = name;
            card.append(sample, label); card.addEventListener('click', () => choose(tool, id), { signal });
            cards.append(card); count++;
        }
        if (cards.childElementCount) { group.append(heading, cards); container.append(group); }
    }
    return count;
}

/** Every setting maps to an existing native resource property. */
export function renderNativeProperties(container, { kind, item, t, signal, change }) {
    const field = (label, key, type, attrs = {}, options) => {
        const wrapper = document.createElement('label'); wrapper.textContent = t(label);
        const input = document.createElement(options ? 'select' : type === 'textarea' ? 'textarea' : 'input');
        if (!options && type !== 'textarea') input.type = type;
        input.setAttribute('data-builder-property', key);
        for (const [name, value] of Object.entries(attrs)) input.setAttribute(name, value);
        if (options) for (const [value, text] of options) input.append(new Option(t(text), value));
        if (type === 'checkbox') { input.checked = item[key] !== false; wrapper.className = 'map-builder__check'; wrapper.prepend(input); }
        else { input.value = item[key] ?? (key === 'elevation' ? 0 : ''); wrapper.append(input); }
        input.addEventListener('change', () => {
            if (input.disabled || !input.checkValidity()) return;
            change({ [key]: type === 'checkbox' ? input.checked : type === 'number' ? Number(input.value) : input.value });
        }, { signal });
        container.append(wrapper); return input;
    };
    const number = (label, key, min, max, step = 'any') => field(label, key, 'number', { min, max, step, required: '' });
    if (kind === 'lights') {
        field('Animation', 'animation', 'text', {}, animations);
        number('Angle', 'angle', 5, 360); number('Rotation', 'rotation', 0, 359.999);
        number('Elevation', 'elevation', -1e6, 1e6);
    } else {
        if (kind === 'particles') field('Particle profile', 'kind', 'text', {}, particlePresets.map(preset => [preset.id || preset.kind, presetName('particle', preset, t)]));
        else {
            number('Radius (cells, 0 = whole scene)', 'radius', 0, 1e6);
            number('Intensity', 'intensity', 0, 1); number('Opacity', 'opacity', 0, 1); number('Speed', 'speed', 0, 8);
            field('Blend mode', 'blend_mode', 'text', {}, [['normal', 'Normal'], ['add', 'Add'], ['screen', 'Screen'], ['multiply', 'Multiply']]);
        }
        number('Scale', 'scale', .1, 20); if (kind === 'particles') number('Density', 'density', 0, 1);
        number('Rotation', 'rotation', 0, 359.999);
        number('Respond to light', 'light_response', 0, 1); number('Emit light', 'light_emission', 0, 2);
    }
    field(kind === 'lights' ? 'Light color' : 'Color', 'color', 'color');
    field('Enabled', 'enabled', 'checkbox');
    if (kind === 'shaders') {
        const details = document.createElement('details'), title = document.createElement('summary');
        details.className = 'map-builder__shader-source'; title.textContent = t('Shader source'); details.append(title);
        const fields = document.createElement('div'); details.append(fields); container.append(details);
        const original = container; container = fields;
        field('Shader source', 'source', 'textarea', { maxlength: 32000, rows: 8, required: '', translate: 'no', spellcheck: 'false' });
        container = original;
    }
}
