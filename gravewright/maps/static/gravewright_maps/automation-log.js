// GM-only floating window listing recent object blueprint runs in the current scene.
// The server records each run; this window reads them over HTTP and reloads when
// the table socket reports a new run for the scene being viewed.
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { registerEscapeClose } from '/static/gravewright_web/escape.js';
import { openSceneNetwork } from './builder/scene-network.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { mountSceneControls } from './scene-controls.js';
import { openPlaytest } from './builder/playtest.js';
import { hasBlueprintEventPath } from './builder/blueprint-model.js';
import { createRunFormatter, STEP_NAMES } from './builder/run-format.js';

const root = document.querySelector('#table-workspace');
const template = document.querySelector('#automation-log-window');
if (root?.dataset.role === 'gm' && template) {
    const translator = createTranslator(), t = (key, params) => translator.t(key, params);
    const formatter = createRunFormatter({ t, elements: () => doors });
    const { label: doorLabel, stateName, stepText, eventTitle } = formatter;
    const typeNames = STEP_NAMES;
    const outcomeNames = { completed: 'Completed', blocked: 'Blocked by the lock', failed: 'Failed',
        waiting: 'Waiting', cancelled: 'Cancelled', paused: 'Automation is paused.' };
    const scalar = value => typeof value === 'boolean' ? t(value ? 'True' : 'False') : typeof value === 'string' ? JSON.stringify(value) : String(value);
    const scopeName = value => t(value === 'scene' ? 'Scene' : 'This element');
    let panel, panelAbort, controls, childModal, unregisterEscape, sceneId = null, runs = [], doors = [], paused = false, view = 'runs', filter = 'all', request = 0, failed = false, notice = '';
    let variables = { scene: {}, elements: {} };
    let memory = { elements: {} };
    let delays = [];
    let controlsRefreshTimer;
    function refreshControlsSoon() {
        clearTimeout(controlsRefreshTimer);
        if (panel && view === 'doors') controlsRefreshTimer = setTimeout(() => {
            controlsRefreshTimer = undefined; if (panel && view === 'doors') void controls?.refresh();
        }, 120);
    }

    function element(tag, attrs = {}, text) {
        const node = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function locate(row) {
        window.gravewrightMaps?.board?.ping({ x: row.point.x, y: row.point.y }, true);
    }
    function locateButton(row) {
        const where = element('button', { type: 'button', class: 'automation-log__locate', 'data-automation-locate': '', 'aria-label': t('Show element on the map'), title: t('Show element on the map') });
        const glyph = document.querySelector('#automation-log-locate')?.content.firstElementChild;
        if (glyph) where.append(glyph.cloneNode(true)); else where.textContent = '⌖';
        where.addEventListener('click', () => locate(row));
        return where;
    }
    // GM controls reuse the authorized map command channel; the log reloads on success.
    async function command(area, action, data) {
        notice = '';
        try {
            await window.gravewrightRealtime.mapCommand('objects', { mapId: sceneId, area, action, data });
        } catch (error) {
            notice = t(error?.message || 'Could not load the automation log.');
        }
        await load();
    }
    function renderDoors(list) {
        list.replaceChildren(...doors.filter(door => door.automated).map(door => {
            const item = element('li', { class: 'automation-log__run automation-log__door', 'data-automation-door': door.id });
            const head = element('div', { class: 'automation-log__head' });
            const name = element('strong', { translate: 'no' }, doorLabel(door.id));
            head.append(name, element('span', { class: 'automation-log__door-state' }, stateName(door.state, door.id)));
            if (door.kind === 'region') head.append(element('span', {}, t('Tokens inside: {0}', { 0: door.count ?? 0 })));
            const spacer = element('span', { class: 'automation-log__spacer' });
            head.append(spacer, locateButton(door));
            const actions = element('div', { class: 'automation-log__actions' });
            if (door.kind !== 'region') {
                const interact = element('button', { type: 'button', 'data-automation-interact': '' }, t('Run interaction'));
                interact.disabled = paused || !(door.blueprint?.version === 2 && hasBlueprintEventPath(door.blueprint, 'interact'))
                    && !door.events.includes('interact') && !door.events.includes(`interact:${door.state}`);
                interact.title = interact.disabled ? t(paused ? 'Automation is paused.' : 'This state has no interaction graph.') : '';
                interact.addEventListener('click', () => ['lever', 'torch'].includes(door.kind)
                    ? command('images', 'interact', { image_id: door.id })
                    : command('walls', 'door', { wall_id: door.id, door_state: door.state }));
                actions.append(interact);
            }
            if (door.sprite) {
                const clear = element('button', { type: 'button', 'data-automation-clear-sprite': '' }, t('Clear live image'));
                clear.addEventListener('click', () => command('automation', 'clear-sprite', { wall_id: door.id }));
                actions.append(clear);
            }
            item.append(head, actions);
            return item;
        }));
    }
    function renderVariables(list) {
        const variableScene = sceneId;
        const rows = Object.entries(variables.scene || {}).map(([name, entry]) => ({ scope: 'scene', name, entry }));
        for (const [elementId, store] of Object.entries(variables.elements || {}))
            for (const [name, entry] of Object.entries(store)) rows.push({ scope: 'element', elementId, name, entry });
        list.replaceChildren(...rows.map(({ scope, elementId, name, entry }) => {
            const row = element('li', { class: 'automation-log__run automation-log__variable', 'data-automation-variable-name': name,
                'data-automation-variable-scope': scope, ...(elementId ? { 'data-automation-variable-element': elementId } : {}) });
            const head = element('div', { class: 'automation-log__head' });
            head.append(element('strong', { translate: 'no' }, name), element('span', { class: 'automation-log__spacer' }));
            const reset = element('button', { type: 'button', class: 'automation-log__reset', 'data-automation-reset-variable': '', 'aria-label': `${t('Reset variable')}: ${name}` }, t('Reset variable'));
            reset.addEventListener('click', async () => {
                if (variableScene !== sceneId) return;
                reset.disabled = true;
                await command('automation', 'reset-variable', { scope, name, ...(elementId ? { elementId } : {}), expected: structuredClone(entry) });
            });
            head.append(reset);
            row.append(head, element('span', { class: 'automation-log__hint' }, `${scope === 'scene' ? scopeName(scope) : doorLabel(elementId)} · ${t({ boolean: 'True or False', number: 'Number', text: 'Text' }[entry.type])}`),
                element('code', { class: 'automation-log__variable-value', translate: 'no' }, scalar(entry.value)));
            return row;
        }));
        return rows.length;
    }
    function renderMemory(list) {
        const memoryScene = sceneId, rows = [];
        for (const [elementId, events] of Object.entries(memory.elements || {}))
            for (const [event, nodes] of Object.entries(events))
                for (const [nodeId, entry] of Object.entries(nodes)) rows.push({ elementId, event, nodeId, entry });
        list.replaceChildren(...rows.map(({ elementId, event, nodeId, entry }) => {
            const row = element('li', { class: 'automation-log__run automation-log__variable', 'data-automation-memory-node': nodeId,
                'data-automation-memory-event': event, 'data-automation-memory-element': elementId });
            const head = element('div', { class: 'automation-log__head' });
            head.append(element('strong', {}, t(typeNames[entry.type])), element('span', { class: 'automation-log__spacer' }));
            const reset = element('button', { type: 'button', class: 'automation-log__reset', 'data-automation-reset-memory': '',
                'aria-label': `${t('Reset node')}: ${t(typeNames[entry.type])}` }, t('Reset node'));
            reset.addEventListener('click', async () => {
                if (memoryScene !== sceneId) return;
                reset.disabled = true;
                await command('automation', 'reset-memory', { elementId, event, nodeId, expected: structuredClone(entry) });
            });
            head.append(reset);
            const value = entry.type === 'counter' ? t('Count: {0}', { 0: entry.value }) : entry.type === 'once' ? t('Already used')
                : t('Ready at {0}', { 0: new Date(entry.value).toLocaleString(translator.locale) });
            row.append(head, element('span', { class: 'automation-log__hint' }, eventTitle({ event, doorId: elementId })),
                element('span', { 'data-automation-memory-value': '' }, value), element('code', { class: 'automation-log__memory-id', translate: 'no', title: nodeId }, nodeId));
            return row;
        }));
        return rows.length;
    }
    function renderDelays(list) {
        const delayScene = sceneId;
        list.replaceChildren(...delays.map(wait => {
            const timer = wait.kind === 'timer';
            const row = element('li', { class: 'automation-log__run automation-log__run--waiting', 'data-automation-delay-id': wait.id });
            if (timer) row.setAttribute('data-automation-timer-name', wait.name);
            const head = element('div', { class: 'automation-log__head' });
            head.append(element('strong', { translate: 'no' }, timer ? `${t('Timer')}: ${wait.name}` : doorLabel(wait.elementId)), element('span', { class: 'automation-log__spacer' }));
            if (timer) {
                const restart = element('button', { type: 'button', class: 'automation-log__reset', 'data-automation-restart-timer': '' }, t('Restart timer'));
                restart.addEventListener('click', async () => {
                    if (delayScene !== sceneId) return;
                    restart.disabled = true;
                    await command('automation', 'restart-timer', { delayId: wait.id, expectedDueAt: wait.dueAt });
                });
                head.append(restart);
            }
            const cancel = element('button', { type: 'button', class: 'automation-log__reset', 'data-automation-cancel-delay': '' }, t(timer ? 'Stop timer' : 'Cancel wait'));
            cancel.addEventListener('click', async () => {
                if (delayScene !== sceneId) return;
                cancel.disabled = true;
                await command('automation', 'cancel-delay', { delayId: wait.id, expectedDueAt: wait.dueAt });
            });
            head.append(cancel);
            const when = element('time', { datetime: wait.dueAt, 'data-automation-delay-due': '' }, new Date(wait.dueAt).toLocaleString(translator.locale));
            const due = element('span');
            due.append(`${t(timer ? 'Expires at' : 'Resume at')}: `, when);
            row.append(head, element('span', { class: 'automation-log__hint' }, eventTitle({ event: wait.event, ...(timer ? { doorId: wait.elementId } : {}) })),
                due, element('span', { class: 'automation-log__hint' }, t('Wait {0} seconds', { 0: wait.seconds })),
                element('span', { translate: 'no' }, wait.actor?.name || ''));
            return row;
        }));
    }
    function render() {
        if (!panel) return;
        const list = panel.querySelector('[data-automation-runs]'), status = panel.querySelector('[data-automation-status]');
        const doorList = panel.querySelector('[data-automation-controls]'), pause = panel.querySelector('[data-automation-pause]');
        const variableList = panel.querySelector('[data-automation-variables]'), variableCount = renderVariables(variableList);
        const memoryList = panel.querySelector('[data-automation-memory]'), memoryCount = renderMemory(memoryList);
        const delayList = panel.querySelector('[data-automation-delays]');
        renderDelays(delayList);
        const note = panel.querySelector('[data-automation-paused-note]');
        for (const button of panel.querySelectorAll('[data-automation-filter]')) button.setAttribute('aria-pressed', String(button.dataset.automationFilter === filter));
        for (const button of panel.querySelectorAll('[data-automation-view]')) button.setAttribute('aria-pressed', String(button.dataset.automationView === view));
        panel.querySelector('.automation-log__filters').hidden = view !== 'runs';
        list.hidden = view !== 'runs'; doorList.hidden = view !== 'doors';
        variableList.hidden = view !== 'variables';
        memoryList.hidden = view !== 'memory';
        delayList.hidden = view !== 'delays';
        pause.setAttribute('aria-pressed', String(paused)); pause.disabled = !sceneId || failed;
        pause.textContent = t(paused ? 'Resume automation' : 'Pause automation');
        note.hidden = !paused; note.textContent = t('Automation is paused: elements change state without running their graphs.');
        const shown = runs.filter(run => filter === 'all' || run.outcome !== 'completed');
        status.textContent = notice || (!sceneId ? t('Open a scene to see its automation.')
            : failed ? t('Could not load the automation log.')
            : view === 'doors' ? ''
            : view === 'variables' ? (variableCount ? '' : t('No stored variables in this scene.'))
            : view === 'memory' ? (memoryCount ? '' : t('No persistent nodes have run in this scene.'))
            : view === 'delays' ? (delays.length ? '' : t('No events are waiting in this scene.'))
            : !runs.length ? t('No automation has run in this scene yet.')
            : !shown.length ? t('No problems in the recent runs.') : '');
        status.hidden = !status.textContent;
        status.classList.toggle('is-error', failed || !!notice);
        list.replaceChildren(...shown.map(run => {
            const item = element('li', { class: `automation-log__run automation-log__run--${run.outcome}`, 'data-automation-run': run.id });
            const head = element('div', { class: 'automation-log__head' });
            const time = new Date(run.createdAt);
            head.append(element('span', { class: 'automation-log__outcome' }, t(outcomeNames[run.outcome] || run.outcome)),
                element('time', { datetime: run.createdAt }, time.toLocaleTimeString(translator.locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' })));
            head.append(locateButton(run));
            const summary = element('p', { class: 'automation-log__summary' });
            summary.append(element('strong', { translate: 'no' }, run.actor?.name || ''));
            if (run.stateBefore != null && run.stateAfter != null) summary.append(` · ${stateName(run.stateBefore, run.doorId)} → ${stateName(run.stateAfter, run.doorId)}`);
            item.append(head, summary);
            if (run.timerName) item.append(element('p', { class: 'automation-log__hint', 'data-automation-timer-run': '' }, `${t('Timer')}: ${run.timerName}`));
            if (run.context?.tokenId) {
                const context = element('p', { class: 'automation-log__context', 'data-automation-presence-context': '' });
                context.append(`${t('Instigating token')}: `, element('span', { translate: 'no' }, run.context.tokenId));
                if (typeof run.context.count === 'number') context.append(` · ${t('Tokens inside: {0}', { 0: run.context.count })}`);
                item.append(context);
            }
            if (run.message) item.append(element('p', { class: 'automation-log__message', role: 'note' }, t(run.message)));
            for (const entry of run.events || []) {
                const block = element('div', { class: 'automation-log__event' });
                block.append(element('span', { class: 'automation-log__event-title' }, eventTitle(entry)));
                if (entry.message) block.append(element('p', { class: 'automation-log__message', role: 'note' }, t(entry.message)));
                const steps = element('ol', { class: 'automation-log__steps' });
                for (const step of entry.steps.filter(row => row.type !== 'event'))
                    steps.append(element('li', { class: `automation-log__step automation-log__step--${step.type}${step.missing ? ' is-missing' : ''}`, 'data-step-type': step.type }, stepText(step)));
                if (!steps.children.length && !entry.message) steps.append(element('li', { class: 'automation-log__step automation-log__step--empty' }, t('No connected nodes ran.')));
                block.append(steps); item.append(block);
            }
            if (!(run.events || []).length && run.outcome === 'failed') item.append(element('p', { class: 'automation-log__hint' }, t('Refused before any graph ran.')));
            return item;
        }));
    }
    async function load() {
        const scene = sceneId, ticket = ++request;
        if (!panel || !scene) { runs = []; doors = []; variables = { scene: {}, elements: {} }; memory = { elements: {} }; delays = []; paused = false; failed = false; render(); return; }
        try {
            const response = await fetch(`/api/maps/${encodeURIComponent(scene)}/automation`, { headers: { Accept: 'application/json' }, credentials: 'same-origin', signal: panelAbort?.signal });
            if (!response.ok) throw new Error(String(response.status));
            const body = await response.json();
            if (ticket !== request || scene !== sceneId) return;
            runs = Array.isArray(body.runs) ? body.runs : []; doors = Array.isArray(body.doors) ? body.doors : [];
            variables = body.variables || { scene: {}, elements: {} };
            memory = body.memory || { elements: {} };
            delays = Array.isArray(body.delays) ? body.delays : [];
            paused = body.paused === true; failed = false;
        } catch {
            if (ticket !== request) return;
            runs = []; doors = []; variables = { scene: {}, elements: {} }; memory = { elements: {} }; delays = []; failed = true;
        }
        render();
    }
    function translateStatic() {
        if (!panel) return;
        panel.querySelector('#automation-log-title').textContent = t('Automation');
        panel.setAttribute('aria-label', t('Automation'));
        panel.querySelector('[data-automation-close]').setAttribute('aria-label', t('Close'));
        const minimize = panel.querySelector('[data-automation-minimize]');
        minimize.setAttribute('aria-label', t(panel.hasAttribute('data-window-minimized') ? 'Restore' : 'Minimize'));
        panel.querySelector('.automation-log__filters').setAttribute('aria-label', t('Show'));
        panel.querySelector('[data-automation-filter=all]').textContent = t('All runs');
        panel.querySelector('[data-automation-filter=problems]').textContent = t('Problems');
        panel.querySelector('.automation-log__views').setAttribute('aria-label', t('View'));
        panel.querySelector('[data-automation-view=runs]').textContent = t('Runs');
        panel.querySelector('[data-automation-view=doors]').textContent = t('Elements');
        panel.querySelector('[data-automation-view=variables]').textContent = t('Variables');
        panel.querySelector('[data-automation-view=memory]').textContent = t('Node memory');
        panel.querySelector('[data-automation-view=delays]').textContent = t('Waiting');
        panel.querySelector('[data-automation-network]').textContent = t('Scene network');
        panel.querySelector('[data-automation-network]').disabled = !sceneId;
    }
    function close() {
        if (!panel) return;
        clearTimeout(controlsRefreshTimer);
        panelAbort?.abort(); panelAbort = null;
        childModal?.close(true); childModal = null; controls?.destroy(); controls = null;
        unregisterEscape?.(); unregisterEscape = null;
        panel.remove(); panel = null; request++;
        document.querySelector('[data-dock-tool=automation]')?.setAttribute('aria-pressed', 'false');
    }
    function open() {
        panel = template.content.firstElementChild.cloneNode(true);
        const lifetime = panelAbort = new AbortController();
        const http = new HttpClient(undefined, () => lifetime.signal);
        controls = mountSceneControls(panel.querySelector('[data-automation-controls]'), {
            t, getSceneId: () => sceneId,
            load: (scene, signal) => http.get(`/api/maps/${encodeURIComponent(scene)}/automation/network`, { signal }),
            control: (action, owner, value, signal) => http.post(`/api/maps/${encodeURIComponent(sceneId)}/automation/control/${encodeURIComponent(owner.id)}`,
                { request_id: crypto.randomUUID(), expected_version: owner.version, action, ...(value === undefined ? {} : { value }) }, { signal }),
            locate,
            edit: owner => openNetwork(owner.id),
            onTest: async owner => {
                const scene = sceneId, originalPanel = panel;
                const catalog = await http.get(`/api/maps/${encodeURIComponent(scene)}/automation/network`);
                if (scene !== sceneId || !panel || panel !== originalPanel) return;
                childModal = openPlaytest({ elements: catalog.elements, tokens: catalog.tokens, initialElement: owner.id, t,
                    execute: (owner, event, token, requestId, signal) => http.post(`/api/maps/${encodeURIComponent(scene)}/automation/test/${encodeURIComponent(owner.id)}`,
                        { request_id: requestId, expected_version: owner.version, event, ...(token ? { tokenId: token } : {}) }, { signal }),
                    onClose: () => { childModal = null; },
                });
                return childModal;
            }, onChange: () => void load(),
        });
        panel.querySelector('[data-automation-close]').addEventListener('click', close);
        panel.querySelector('[data-automation-minimize]').addEventListener('click', () => {
            panel.classList.toggle('gw-window--minimized', panel.toggleAttribute('data-window-minimized')); translateStatic();
        });
        for (const button of panel.querySelectorAll('[data-automation-filter]'))
            button.addEventListener('click', () => { filter = button.dataset.automationFilter; render(); });
        for (const button of panel.querySelectorAll('[data-automation-view]'))
            button.addEventListener('click', () => { view = button.dataset.automationView; notice = ''; render(); if (view === 'doors') void controls.refresh(); });
        panel.querySelector('[data-automation-pause]').addEventListener('click', () => command('automation', 'pause', { paused: !paused }));
        panel.querySelector('[data-automation-network]').addEventListener('click', () => openNetwork());
        function openNetwork(initialElementId) {
            if (!sceneId) return;
            const scene = sceneId;
            childModal = openSceneNetwork({ campaignId: root.dataset.tableId, t, initialElementId, editInitially: Boolean(initialElementId),
                load: signal => http.get(`/api/maps/${encodeURIComponent(scene)}/automation/network`, { signal }),
                save: (owner, blueprint, requestId, signal) => http.post(`/api/maps/${encodeURIComponent(scene)}/automation/network/${encodeURIComponent(owner.id)}`,
                    { request_id: requestId, expected_version: owner.version, expected_project_version: owner.projectVersion, blueprint }, { signal })
                    .catch(error => { if (error.status === 409) error.code = 'conflict'; throw error; }),
                locate: owner => { if (window.gravewrightMaps?.current?.id === scene) locate(owner); },
                onClose: () => { childModal = null; if (view === 'doors') void controls?.refresh(); },
            });
            return childModal;
        }
        root.append(panel);
        unregisterEscape = registerEscapeClose(panel, close);
        document.querySelector('[data-dock-tool=automation]')?.setAttribute('aria-pressed', 'true');
        translateStatic(); render(); void load(); if (view === 'doors') void controls.refresh();
        panel.querySelector('[data-automation-filter]')?.focus({ preventScroll: true });
    }
    // Capture the dock click so the wall tool controller does not treat it as a drawing tool.
    document.addEventListener('click', event => {
        const button = event.target.closest?.('[data-dock-tool=automation]');
        if (!button) return;
        event.preventDefault(); event.stopImmediatePropagation();
        if (panel) close(); else open();
    }, true);
    window.addEventListener('gravewright:api-event', ({ detail }) => {
        if (detail?.type === 'maps.automation' && panel && detail.payload?.sceneId === sceneId) void load();
        if (detail?.type === 'maps.layers' && detail.payload?.sceneId === sceneId) refreshControlsSoon();
    });
    window.addEventListener('gravewright:module-scene', () => {
        childModal?.close(true); childModal = null;
        sceneId = window.gravewrightMaps?.current?.id || null; void load(); if (view === 'doors') void controls?.refresh();
    });
    window.addEventListener('gravewright:connected', () => { void load(); refreshControlsSoon(); });
    window.addEventListener('gravewright:i18n-catalog', () => { translateStatic(); render(); controls?.translate(); });
    window.addEventListener('pagehide', close);
    sceneId = window.gravewrightMaps?.current?.id || null;
}
