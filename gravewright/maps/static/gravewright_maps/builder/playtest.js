import { mountModal } from '/static/gravewright_table/modal.js';
import { blueprintEventLabel, blueprintVerbEventsFor, isBlueprintSignalEvent } from './blueprint-model.js';

/** Every run rehearses the current configuration through the server, then discards it. */
export function openPlaytest({ elements, actors = [], tokens = [], draft = false, initialElement, t, execute, preview, onClose }) {
    if (!document.querySelector('link[data-playtest-css]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet'; link.dataset.playtestCss = '';
        link.href = new URL('./playtest.css', import.meta.url).href; document.head.append(link);
    }
    const abort = new AbortController(), signal = abort.signal;
    const make = (tag, attrs = {}, text) => {
        const node = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const button = (text, attrs, handler) => {
        const node = make('button', { type: 'button', ...attrs }, t(text)); node.addEventListener('click', handler, { signal }); return node;
    };
    const modal = make('section', { class: 'table-form-modal playtest', 'data-playtest': '', 'aria-label': t('Test behavior') });
    const head = make('header'); head.append(make('strong', {}, t('Test behavior')), button('Close', { 'data-playtest-close': '' }, () => modal.close()));
    const body = make('div', { class: 'playtest__body' }), form = make('form', { class: 'playtest__form' });
    function select(label, key) {
        const row = make('label'), node = make('select', { [`data-playtest-${key}`]: '' }); row.append(make('span', {}, t(label)), node); form.append(row); return node;
    }
    const supportedEvents = owner => Object.keys(owner.blueprint?.graphs || {})
        .filter(event => blueprintVerbEventsFor(owner.kind).includes(event) || isBlueprintSignalEvent(event));
    const owners = elements.filter(owner => supportedEvents(owner).length);
    const ownerSelect = select('Element', 'element'), eventSelect = select('Event', 'event');
    const contextSelect = select(draft ? 'Test actor' : 'Test token', draft ? 'actor' : 'token');
    const kindNames = { door: 'Door', lever: 'Lever', torch: 'Torch', region: 'Region', image: 'Object' };
    const stateNames = { closed: 'Closed', open: 'Opened', locked: 'Locked', on: 'Activated', off: 'Deactivated', empty: 'Empty', occupied: 'Occupied' };
    const stepNames = { event: 'Event', state: 'Change state', interact: 'Interact with object', light: 'Set light', sound: 'Play sound', sprite: 'Change sprite',
        condition: 'Check state', sequence: 'Sequence', reference: 'Element reference', property: 'Get property', compare: 'Compare state',
        reveal: 'Reveal', barrier: 'Set barrier', flame: 'Set flame', soundControl: 'Control sound', all: 'All conditions', any: 'Any condition',
        getVariable: 'Get variable', setVariable: 'Set variable', compareValue: 'Compare value', emitEvent: 'Emit event', counter: 'Counter',
        once: 'Once', cooldown: 'Cooldown', delay: 'Delay', timer: 'Timer', switch: 'Switch', random: 'Random', elementGroup: 'Element group',
        lightReference: 'Light reference', soundReference: 'Sound reference', eventContext: 'Event context', move: 'Move object', rotate: 'Rotate object',
        setInteraction: 'Set interaction', setRegion: 'Set region', setVisibility: 'Set visibility', setAppearance: 'Set appearance',
        showMessage: 'Show message', showHandout: 'Show handout', cameraFocus: 'Focus camera', teleport: 'Teleport token' };
    for (const [index, owner] of owners.entries()) ownerSelect.append(make('option', { value: owner.id, translate: 'no' },
        owner.name || `${t(owner.empty ? 'Empty Object' : kindNames[owner.kind] || 'Element')} ${index + 1}`));
    if (owners.some(owner => owner.id === initialElement)) ownerSelect.value = initialElement;
    contextSelect.append(make('option', { value: '' }, t('No triggering token')));
    for (const entry of draft ? actors : tokens) contextSelect.append(make('option', { value: entry.id, translate: 'no' }, entry.name || entry.id));
    const note = make('p', { class: 'playtest__hint' }, t('Each test starts from the current configuration. Nothing is saved or sent to players.'));
    const eventNote = make('p', { class: 'playtest__hint' }, t('Events only start the sequence. Use logic nodes for comparisons and actions to change the element.'));
    const status = make('p', { role: 'status', 'data-playtest-status': '' });
    const layout = make('div', { class: 'playtest__layout' }), map = make('div', { class: 'playtest__map', 'data-playtest-map': '' });
    const results = make('div', { class: 'playtest__results', 'data-playtest-results': '', 'aria-live': 'polite' });
    layout.append(map, results); body.append(note, eventNote, form, status, layout);
    const footer = make('footer'), run = button('Run test', { 'data-playtest-run': '', class: 'button button--primary' }, () => void perform());
    const reset = button('Reset test', { 'data-playtest-reset': '' }, () => { requestId = undefined; results.replaceChildren(); status.textContent = ''; draw(null); });
    footer.append(reset, run); modal.append(head, body, footer);
    let busy = false, disposed = false, requestId, previousPayload, disposePreview;
    function draw(result) {
        disposePreview?.(); disposePreview = undefined; map.replaceChildren(); map.hidden = !preview;
        if (preview) disposePreview = preview(map, result);
    }
    function events() {
        const owner = owners.find(entry => entry.id === ownerSelect.value);
        const selected = eventSelect.value;
        eventSelect.replaceChildren(...(owner ? supportedEvents(owner) : []).map(event => {
            return make('option', { value: event }, blueprintEventLabel(event, t, owner.kind));
        }));
        if ([...eventSelect.options].some(option => option.value === selected)) eventSelect.value = selected;
        run.disabled = !eventSelect.options.length || busy;
    }
    function line(label, value) {
        const row = make('p'); row.append(make('strong', {}, `${t(label)}: `), make('span', { translate: 'no' }, String(value))); results.append(row);
    }
    function report(result) {
        results.replaceChildren();
        if (result.run) line('State', `${t(stateNames[result.run.stateBefore] || result.run.stateBefore)} → ${t(stateNames[result.run.stateAfter] || result.run.stateAfter)}`);
        if (result.error) results.append(make('p', { role: 'alert' }, t(result.error.message)));
        const warnings = {
            'timing-not-advanced': 'Timers and waits are scheduled in this test; time does not advance.',
            'presentation-not-delivered': 'Messages, handouts and camera changes are listed without sending them to players.',
            'missing-test-token': 'Teleport was skipped. Choose a test actor or token to test its destination.',
            'automation-paused': 'Automation is paused.',
            'destruction-timing-cancelled': 'Timers and waits owned by the destroyed element are cancelled.',
        };
        for (const code of result.warnings || []) results.append(make('p', { class: 'playtest__warning' }, t(warnings[code] || code)));
        for (const change of result.changes?.elements || []) {
            const data = change.after?.data || {}, before = change.before?.data || {};
            const label = owners.find(owner => owner.id === (change.sourceId || change.id))?.name || t(({ walls: 'Door', images: 'Object', lights: 'Light', zones: 'Region' })[change.kind] || 'Element');
            const block = make('details', { 'data-playtest-change': change.id, open: '' }); block.append(make('summary', { translate: 'no' }, label));
            if (change.after === null) {
                block.setAttribute('data-playtest-removed', ''); block.append(make('p', {}, t('Removed for this test')));
                results.append(block); continue;
            }
            const values = make('dl');
            for (const key of Object.keys(data)) if (JSON.stringify(data[key]) !== JSON.stringify(before[key]) && !['src', 'blueprint'].includes(key)) {
                values.append(make('dt', { translate: 'no' }, key), make('dd', { translate: 'no' }, JSON.stringify(data[key])));
            }
            block.append(values); results.append(block);
        }
        for (const change of result.changes?.tokens || []) line('Token destination', `${change.after?.grid_x}, ${change.after?.grid_y}`);
        if (JSON.stringify(result.changes?.sceneVariables?.before) !== JSON.stringify(result.changes?.sceneVariables?.after)) line('Variables', JSON.stringify(result.changes.sceneVariables.after));
        if (JSON.stringify(result.changes?.audio?.before) !== JSON.stringify(result.changes?.audio?.after)) line('Sound', t('Playback would change'));
        for (const job of result.scheduled || []) {
            const row = job.after || job.before || {};
            line(job.after === null ? 'Cancelled' : 'Waiting', `${row.name || row.kind || ''}: ${row.seconds ?? 0}s`);
        }
        const trace = result.ok === false && result.run
            ? [result.run, ...(result.runs || []).filter(entry => entry.elementId !== result.elementId)]
            : result.runs?.length ? result.runs : result.run ? [result.run] : [];
        for (const entry of trace) for (const event of entry.events || []) {
            const block = make('details', { 'data-playtest-trace': '', open: '' }); block.append(make('summary', { translate: 'no' }, event.event));
            const steps = make('ol');
            for (const step of event.steps || []) {
                const row = make('li', { 'data-step-type': step.type });
                row.append(make('strong', {}, t(stepNames[step.type] || step.type)));
                if (step.unsupportedIds?.length) {
                    const names = step.unsupportedIds.map(id => elements.find(element => element.id === (result.sourceIds?.[id] || id))?.name || t('Element'));
                    row.append(make('span', { 'data-playtest-unsupported-targets': '' }, ` · ${t('Unsupported targets')}: ${names.join(', ')}`));
                }
                for (const [key, value] of Object.entries(step)) if (!['type', 'id', 'nodeId', 'unsupportedIds'].includes(key)) row.append(make('span', { translate: 'no' }, ` · ${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`));
                steps.append(row);
            }
            block.append(steps); results.append(block);
        }
        if (!results.children.length) results.append(make('p', {}, t('No changes were predicted.')));
    }
    async function perform() {
        if (busy || !ownerSelect.value || !eventSelect.value) return;
        const owner = owners.find(entry => entry.id === ownerSelect.value), payload = JSON.stringify([owner.id, eventSelect.value, contextSelect.value]);
        if (payload !== previousPayload || !requestId) { requestId = crypto.randomUUID(); previousPayload = payload; }
        busy = true; run.disabled = true; reset.disabled = true;
        for (const input of form.elements) input.disabled = true;
        status.textContent = t('Running test...'); modal.setAttribute('aria-busy', 'true');
        try {
            const result = await execute(owner, eventSelect.value, contextSelect.value || null, requestId, signal);
            if (disposed) return;
            requestId = undefined; status.textContent = t(result.ok ? 'Test completed. All changes were discarded.' : 'Test failed. All changes were discarded.');
            report(result); draw(result);
        } catch (error) {
            if (disposed || error.name === 'AbortError') return;
            status.textContent = t(error.status === 409 ? 'The object changed. Close this test and refresh the scene.' : error.message || 'Could not run the test.');
            results.replaceChildren(); draw(null);
        } finally {
            if (!disposed) { busy = false; reset.disabled = false; for (const input of form.elements) input.disabled = false; events(); modal.setAttribute('aria-busy', 'false'); }
        }
    }
    ownerSelect.addEventListener('change', events, { signal });
    form.addEventListener('submit', event => { event.preventDefault(); void perform(); }, { signal });
    modal.addEventListener('close', () => { disposed = true; abort.abort(); disposePreview?.(); onClose?.(); }, { once: true });
    events(); draw(null);
    if (!owners.length) status.textContent = t('Add a behavior to an element before testing.');
    return mountModal(modal, { nested: true });
}
