import { validateBlueprint } from './blueprint-model.js';

export const templateBindingTypes = Object.freeze(['asset', 'element', 'light', 'sound', 'handout', 'user', 'clock', 'clue', 'mindmap', 'mindmapTopic']);
const fields = (value, required, optional = []) => value && typeof value === 'object' && !Array.isArray(value)
    && required.every(key => Object.hasOwn(value, key)) && Object.keys(value).every(key => [...required, ...optional].includes(key));
const identifier = /^[A-Za-z][A-Za-z0-9_-]{0,63}(?![\s\S])/;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![\s\S])/i;
const fail = message => { throw new Error(message || 'Invalid blueprint template.'); };
const text = (value, limit, empty = false) => typeof value === 'string' && !value.includes('\0')
    && value.isWellFormed() && Array.from(value).length <= limit && (empty || !!value.trim());
const scalarType = value => typeof value === 'boolean' ? 'boolean' : typeof value === 'number' ? 'number' : typeof value === 'string' ? 'text' : null;
const validScalar = (type, value) => scalarType(value) === type && (type === 'number' ? Number.isFinite(value) : type !== 'text' || text(value, 2000, true));
const at = (value, path) => { for (const part of path.slice(0, -1)) value = value[part]; return [value, path.at(-1)]; };
const catalogs = { asset: 'assets', element: 'elements', light: 'lights', sound: 'sounds', handout: 'handouts', user: 'users', clock: 'clocks', clue: 'clues', mindmap: 'mindmaps' };
const resourcesFor = (catalog, type) => type === 'asset' ? catalog.materials || catalog.assets || []
    : type === 'mindmapTopic' ? (catalog.mindmaps || []).flatMap(map => map.nodes || []) : catalog[catalogs[type]] || [];

/** Exact reference fields only; authored UUID-like strings never become bindings. */
function* resourceSlots(blueprint) {
    for (const appearance of Object.values(blueprint.states || {})) if (appearance?.appearance === 'asset') yield [appearance, 'assetId', 'asset'];
    for (const graph of Object.values(blueprint.graphs || {})) for (const node of graph.nodes || []) {
        const slot = { reference: ['targetId', 'element'], lightReference: ['targetId', 'light'], soundReference: ['trackId', 'sound'],
            light: ['targetId', 'light'], sound: ['trackId', 'sound'], soundControl: ['trackId', 'sound'], clockControl: ['clockId', 'clock'], clueControl: ['clueId', 'clue'],
            openMindMap: ['mindMapId', 'mindmap'], mindMapNode: ['mindMapId', 'mindmap'],
            showHandout: ['journalId', 'handout'], setQuestStatus: ['journalId', 'handout'], teleport: ['destinationId', 'element'], setAppearance: ['assetId', 'asset'] }[node.type];
        if (slot) yield [node, ...slot];
        if (['openMindMap', 'mindMapNode'].includes(node.type) && node.nodeId !== null) yield [node, 'nodeId', 'mindmapTopic'];
        if (node.type === 'sprite' && node.appearance === 'asset') yield [node, 'assetId', 'asset'];
        if (node.type === 'elementGroup') {
            if (!['element', 'light', 'sound'].includes(node.memberType) || !Array.isArray(node.targetIds)) fail();
            for (let index = 0; index < node.targetIds.length; index++) yield [node.targetIds, index, node.memberType];
        }
        if (node.audience?.scope === 'users') {
            if (!Array.isArray(node.audience.userIds)) fail();
            for (let index = 0; index < node.audience.userIds.length; index++) yield [node.audience.userIds, index, 'user'];
        }
    }
}

/** Allowlisted scalar fields; topology, identity, events and scopes stay authored. */
export function templateParameterOptions(blueprint) {
    const options = [];
    for (const [event, graph] of Object.entries(blueprint.graphs || {})) for (const [index, node] of graph.nodes.entries()) {
        const names = { light: ['enabled'], sound: ['volume'], soundControl: ['volume'], clockControl: node.action === 'reset' ? [] : ['amount'], flame: ['enabled'], setInteraction: ['enabled'],
            clueControl: ['advance', 'reduce', 'set'].includes(node.action) ? ['amount'] : [],
            setRegion: ['enabled'], setVisibility: ['visible'], counter: ['target'], cooldown: ['seconds'], delay: ['seconds'],
            timer: node.action === 'stop' ? [] : ['seconds'], move: ['dx', 'dy'], rotate: ['degrees'], getVariable: ['default'],
            setVariable: ['value'], compareValue: ['expected'], switch: ['value'], showMessage: ['text'],
            requestRoll: ['expression', 'label', 'visibility'], setQuestStatus: ['status'], cameraFocus: ['focusX', 'focusY'] }[node.type] || [];
        const tails = names.map(name => [name]);
        if (node.type === 'switch') tails.push(...node.cases.map((_, position) => ['cases', position, 'value']));
        if (node.type === 'random') tails.push(...node.weights.map((_, position) => ['weights', position]));
        for (const tail of tails) {
            let value = node; for (const part of tail) value = value[part];
            const type = scalarType(value);
            if (type) options.push({ id: `parameter${options.length + 1}`, label: `${event} · ${node.id} · ${tail.join('.')}`,
                path: ['graphs', event, 'nodes', index, ...tail], type, default: structuredClone(value) });
        }
    }
    return options;
}

function referenceCatalog(blueprint) {
    const result = { assets: [], lights: [], sounds: [], clocks: [], clues: [] };
    for (const [parent, key, type] of resourceSlots(blueprint)) if (['asset', 'light', 'sound', 'clock', 'clue'].includes(type)) result[catalogs[type]].push({ id: parent[key] });
    return result;
}

/** Capture a library snapshot, replacing every resource UUID with a typed slot. */
export function captureTemplate(blueprint, { ownerId, catalog = {}, expose = [] } = {}) {
    const draft = structuredClone(blueprint);
    validateBlueprint(draft, catalog);
    const available = templateParameterOptions(draft), parameters = [];
    for (const requested of expose) {
        const option = available.find(row => JSON.stringify(row.path) === JSON.stringify(requested.path || requested));
        if (!option) fail('Invalid blueprint template parameter.');
        parameters.push({ ...option, ...(requested.label ? { label: requested.label } : {}) });
    }
    const bindings = [], seen = new Map();
    for (const [parent, key, type] of resourceSlots(draft)) {
        const resource = parent[key];
        if (typeof resource !== 'string' || !uuid.test(resource)) fail('Invalid blueprint template binding.');
        const identity = `${type}:${resource.toLowerCase()}`;
        if (!seen.has(identity)) {
            const self = type === 'element' && typeof ownerId === 'string' && resource.toLowerCase() === ownerId.toLowerCase();
            const row = { id: `binding${bindings.length + 1}`, type, label: self ? 'Self' : `${type} ${bindings.length + 1}`, ...(self ? { self: true } : {}) };
            bindings.push(row); seen.set(identity, row.id);
        }
        parent[key] = { binding: seen.get(identity) };
    }
    return validateTemplateDefinition({ version: 1, blueprint: draft, bindings, parameters });
}

/** Validate placeholder locations and default combinations against the real model. */
export function validateTemplateDefinition(raw) {
    if (!fields(raw, ['version', 'blueprint', 'bindings', 'parameters']) || raw.version !== 1
        || !Array.isArray(raw.bindings) || raw.bindings.length > 256 || !Array.isArray(raw.parameters) || raw.parameters.length > 64) fail();
    const definition = structuredClone(raw), temporary = structuredClone(raw.blueprint), bindings = new Map(), used = new Set();
    for (const [index, row] of definition.bindings.entries()) {
        if (!fields(row, ['id', 'type', 'label'], ['self']) || typeof row.id !== 'string' || !identifier.test(row.id)
            || bindings.has(row.id) || !templateBindingTypes.includes(row.type) || !text(row.label, 120)
            || Object.hasOwn(row, 'self') && (row.self !== true || row.type !== 'element')) fail('Invalid blueprint template binding.');
        bindings.set(row.id, { ...row, temporary: `ffffffff-ffff-4fff-8fff-${String(index + 1).padStart(12, '0')}` });
    }
    for (const [parent, key, type] of resourceSlots(temporary)) {
        const marker = parent[key], row = fields(marker, ['binding']) && bindings.get(marker.binding);
        if (!row || row.type !== type) fail('Invalid blueprint template binding.');
        used.add(row.id); parent[key] = row.temporary;
    }
    if (used.size !== bindings.size) fail('Unused blueprint template binding.');
    validateBlueprint(temporary, referenceCatalog(temporary));
    const options = new Map(templateParameterOptions(temporary).map(row => [JSON.stringify(row.path), row]));
    const identities = new Set(bindings.keys()), paths = new Set();
    for (const row of definition.parameters) {
        if (!fields(row, ['id', 'label', 'path', 'type', 'default']) || typeof row.id !== 'string' || !identifier.test(row.id)
            || identities.has(row.id) || !text(row.label, 120) || !Array.isArray(row.path)) fail('Invalid blueprint template parameter.');
        const path = JSON.stringify(row.path), option = options.get(path);
        if (!option || paths.has(path) || row.type !== option.type || !validScalar(row.type, row.default) || row.default !== option.default) fail('Invalid blueprint template parameter.');
        identities.add(row.id); paths.add(path);
    }
    return definition;
}

/** Resolve to an independent copy; normal project Save enforces server ownership. */
export function resolveTemplate(raw, { ownerId, bindings = {}, parameters = {}, catalog = {} } = {}) {
    const definition = validateTemplateDefinition(raw), resolved = new Map();
    if (!fields(bindings, definition.bindings.filter(row => !row.self).map(row => row.id))
        || !fields(parameters, [], definition.parameters.map(row => row.id))) fail('Resolve every blueprint template binding.');
    for (const row of definition.bindings) {
        const value = row.self ? ownerId : bindings[row.id];
        if (typeof value !== 'string' || !uuid.test(value)) fail('Invalid blueprint template binding value.');
        if (!row.self && !resourcesFor(catalog, row.type).some(resource => resource.id.toLowerCase() === value.toLowerCase()))
            fail('Choose a current resource for each binding.');
        resolved.set(row.id, value);
    }
    const blueprint = structuredClone(definition.blueprint);
    for (const [parent, key] of resourceSlots(blueprint)) parent[key] = resolved.get(parent[key].binding);
    for (const row of definition.parameters) {
        const value = Object.hasOwn(parameters, row.id) ? parameters[row.id] : row.default;
        if (!validScalar(row.type, value)) fail('Invalid blueprint template parameter value.');
        const [parent, key] = at(blueprint, row.path); parent[key] = value;
    }
    validateBlueprint(blueprint, catalog);
    return blueprint;
}

/** Campaign library modal. Applying hands its owner a single, detached draft. */
export async function openTemplateLibrary({ campaignId, blueprint, ownerId, catalog = {}, t = text => text, onApply }) {
    const { mountModal } = await import('/static/gravewright_table/modal.js');
    if (!document.querySelector('link[data-blueprint-templates]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = new URL('./blueprint-templates.css', import.meta.url).href;
        link.dataset.blueprintTemplates = ''; document.head.append(link);
    }
    const abort = new AbortController(), { signal } = abort;
    const modal = document.createElement('section'); modal.className = 'table-form-modal blueprint-templates';
    const make = (tag, className, content) => { const element = document.createElement(tag); if (className) element.className = className;
        if (content !== undefined) element.textContent = content; return element; };
    const button = (label, action, className) => { const element = make('button', className, t(label)); element.type = 'button';
        element.addEventListener('click', action, { signal }); return element; };
    const header = make('header'), title = make('strong', '', t('Blueprint templates'));
    header.append(title, button('Close', () => modal.close()));
    const body = make('div', 'blueprint-templates__body'), status = make('p', 'blueprint-templates__status'); status.setAttribute('role', 'status');
    const hint = make('p', 'blueprint-templates__hint', t('Applying creates an independent copy. Later template changes do not change existing elements.'));
    const toolbar = make('div', 'blueprint-templates__toolbar'), panes = make('div', 'blueprint-templates__panes');
    const list = make('div', 'blueprint-templates__list'), content = make('div', 'blueprint-templates__content'); panes.append(list, content);
    body.append(hint, toolbar, status, panes); modal.append(header, body);
    let selected, busy = false, rows = [], requestSequence = 0, pendingMutation, csrf;
    const base = `/api/containers/${encodeURIComponent(campaignId)}/map-builder/templates`;
    async function request(url, options = {}) {
        if (options.body && !csrf) {
            const endpoint = document.querySelector('meta[name="gravewright-csrf-url"]')?.content || '/__gravewright/csrf';
            const response = await fetch(endpoint, { signal, credentials: 'same-origin', cache: 'no-store' });
            if (!response.ok) throw new Error(t('The template operation failed.'));
            csrf = await response.json();
        }
        const response = await fetch(url, { ...options, signal, credentials: 'same-origin', cache: 'no-store', headers: {
            'Content-Type': 'application/json', ...(options.body ? { [csrf.header]: csrf.token } : {}), ...options.headers } });
        let result; try { result = await response.json(); } catch { throw new Error(t('The template library could not be loaded.')); }
        if (!response.ok) { const error = new Error(result.error || t('The template operation failed.')); error.code = result.code; throw error; }
        return result;
    }
    const report = error => { if (!signal.aborted) status.textContent = t(error.message); };
    async function run(operation) {
        if (busy) return; busy = true; status.textContent = '';
        const prior = new Map([...modal.querySelectorAll('button,input,select,textarea')].map(control => [control, control.disabled]));
        for (const control of prior.keys()) control.disabled = true;
        try { await operation(); } catch (error) {
            if (error.code === 'conflict' && !signal.aborted) {
                try {
                    await refresh();
                    if (selected && rows.some(row => row.id === selected.id)) selected = (await request(`${base}/${selected.id}`)).template;
                } catch { /* Keep the authored form and its old revision for an explicit refresh. */ }
            }
            report(error);
        }
        finally { busy = false; if (!signal.aborted) for (const [control, disabled] of prior) if (control.isConnected) control.disabled = disabled; }
    }
    function field(label, input, authored = false) {
        const name = authored ? label : t(label), wrapper = make('label', '', name);
        if (authored) wrapper.translate = false;
        input.setAttribute('aria-label', name); wrapper.append(input); return wrapper;
    }
    function input(value, { type = 'text', limit } = {}) { const element = make('input'); element.type = type;
        if (type === 'checkbox') element.checked = value; else element.value = value;
        if (limit) element.maxLength = limit; return element; }
    function renderList() {
        list.replaceChildren();
        if (!rows.length) list.append(make('p', 'blueprint-templates__hint', t('No templates in this campaign.')));
        for (const row of rows) {
            const item = button(row.name, () => load(row.id), 'blueprint-templates__item'); item.textContent = row.name;
            item.translate = false;
            item.setAttribute('aria-pressed', String(selected?.id === row.id)); list.append(item);
        }
    }
    async function refresh() { rows = (await request(base)).templates; renderList(); }
    async function load(id) {
        if (busy) return;
        const sequence = ++requestSequence;
        try { const result = await request(`${base}/${id}`); if (signal.aborted || sequence !== requestSequence) return;
            selected = result.template; pendingMutation = null; renderList(); showApply(); } catch (error) { report(error); }
    }
    function mutation(method, id, payload) {
        const identity = JSON.stringify([method, id, payload]);
        if (!pendingMutation || pendingMutation.identity !== identity) pendingMutation = { identity, requestId: crypto.randomUUID() };
        return request(`${base}/${id}`, { method, body: JSON.stringify({ ...payload, request_id: pendingMutation.requestId }) });
    }
    function showApply() {
        content.replaceChildren();
        if (!selected) return;
        const row = selected, definition = row.definition;
        const heading = make('h3', '', row.name), description = make('p', 'blueprint-templates__hint', row.description);
        heading.translate = description.translate = false;
        content.append(heading, description);
        if (definition.blueprint.kind !== blueprint.kind) content.append(make('p', '', t('Choose a template for this element type.')));
        const bindings = new Map(), parameters = new Map();
        for (const binding of definition.bindings) {
            if (binding.self) { const hint = make('p', 'blueprint-templates__hint', `${binding.label}: ${t('This element')}`);
                hint.translate = false; content.append(hint); continue; }
            const select = make('select'); select.required = true; select.append(new Option(t('Choose a resource'), ''));
            for (const resource of resourcesFor(catalog, binding.type)) select.append(new Option(resource.name || resource.title || resource.id, resource.id));
            bindings.set(binding.id, select); content.append(field(binding.label, select, true));
        }
        for (const parameter of definition.parameters) {
            const control = parameter.type === 'text' ? make('textarea')
                : input(parameter.default, { type: parameter.type === 'boolean' ? 'checkbox' : 'number' });
            if (parameter.type === 'text') { control.value = parameter.default; control.maxLength = 4000; control.translate = false; }
            if (parameter.type === 'number') control.step = 'any';
            parameters.set(parameter.id, { parameter, control }); content.append(field(parameter.label, control, true));
        }
        const actions = make('div', 'blueprint-templates__actions');
        const apply = button('Apply independent copy', () => run(async () => {
            if (definition.blueprint.kind !== blueprint.kind) throw new Error('Choose a template for this element type.');
            const values = Object.fromEntries([...parameters].map(([id, { parameter, control }]) => [id, parameter.type === 'boolean' ? control.checked
                : parameter.type === 'number' ? (control.value.trim() ? Number(control.value) : NaN) : control.value]));
            const resolved = resolveTemplate(definition, { ownerId, catalog, bindings: Object.fromEntries([...bindings].map(([id, control]) => [id, control.value])), parameters: values });
            await onApply(resolved); modal.close(true);
        }), 'blueprint-templates__primary');
        apply.disabled = definition.blueprint.kind !== blueprint.kind || typeof onApply !== 'function';
        actions.append(apply, button('Edit template', () => showSave(row)), button('Delete template', () => confirmDelete(row)));
        content.append(actions);
    }
    function confirmDelete(row) {
        const heading = make('h3', '', row.name); heading.translate = false;
        content.replaceChildren(heading, make('p', '', t('Delete this template? Existing copies will remain unchanged.')));
        const actions = make('div', 'blueprint-templates__actions');
        actions.append(button('Cancel', showApply), button('Delete template', () => run(async () => {
            await mutation('DELETE', row.id, { expected_version: row.version }); selected = null; content.replaceChildren(); await refresh();
        }))); content.append(actions);
    }
    function showSave(existing = null) {
        requestSequence++; pendingMutation = null; content.replaceChildren();
        let definition;
        try { definition = existing ? structuredClone(existing.definition) : captureTemplate(blueprint, { ownerId, catalog }); }
        catch (error) { report(error); return; }
        const name = input(existing?.name || '', { limit: 120 }); name.required = true;
        const description = make('textarea'); description.value = existing?.description || ''; description.maxLength = 2000;
        content.append(make('h3', '', t(existing ? 'Edit template' : 'Save current behavior as template')), field('Template name', name), field('Description', description));
        const bindingControls = new Map();
        for (const binding of definition.bindings) {
            const control = input(binding.label, { limit: 120 }); control.required = true;
            const typeName = { asset: 'Image', element: 'Element', light: 'Light', sound: 'Sound', handout: 'Handout', user: 'User', clock: 'Clock', clue: 'Clue', mindmap: 'Mind map', mindmapTopic: 'Topic' }[binding.type];
            content.append(field(binding.self ? 'This element' : `${t('Binding')} · ${t(typeName)}`, control)); bindingControls.set(binding.id, control);
        }
        const source = structuredClone(definition.blueprint);
        // Only scalar fields are inspected here; resource placeholders are untouched.
        const parameterControls = [];
        content.append(make('h3', '', t('Exposed parameters')));
        for (const option of templateParameterOptions(source)) {
            const previous = definition.parameters.find(row => JSON.stringify(row.path) === JSON.stringify(option.path));
            const checkbox = input(!!previous, { type: 'checkbox' }), label = input(previous?.label || option.label, { limit: 120 });
            const wrapper = make('div', 'blueprint-templates__parameter'); wrapper.append(field('Expose', checkbox), field(option.label, label, true)); content.append(wrapper);
            parameterControls.push({ option, checkbox, label });
        }
        const saveId = existing?.id || crypto.randomUUID(), actions = make('div', 'blueprint-templates__actions');
        actions.append(button('Cancel', showApply), button('Save template', () => run(async () => {
            if (!name.value.trim()) throw new Error('Enter a template name.');
            for (const binding of definition.bindings) binding.label = bindingControls.get(binding.id).value;
            definition.parameters = parameterControls.filter(row => row.checkbox.checked).map(({ option, label }) => ({ ...option, label: label.value }));
            const result = await mutation('POST', saveId, { expected_version: existing?.version || 0, name: name.value, description: description.value,
                definition: validateTemplateDefinition(definition) });
            selected = result.template; pendingMutation = null; await refresh(); showApply();
        }), 'blueprint-templates__primary')); content.append(actions); name.focus();
    }
    toolbar.append(button('Save current behavior as template', () => showSave()), button('Refresh', () => run(async () => {
        await refresh();
        if (selected && rows.some(row => row.id === selected.id)) { selected = (await request(`${base}/${selected.id}`)).template; showApply(); }
        else { selected = null; content.replaceChildren(); }
    })));
    modal.addEventListener('close', () => { requestSequence++; abort.abort(); modal.remove(); }, { once: true });
    mountModal(modal, { nested: true, canClose: () => !busy });
    await run(refresh);
    return modal;
}
