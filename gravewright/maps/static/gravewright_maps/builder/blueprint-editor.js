import { mountModal } from '/static/gravewright_table/modal.js';
import { openTemplateLibrary } from './blueprint-templates.js';
import { createAutosave } from './autosave.js';
import { defaultBlueprint, eventGraph, blueprintStatesFor, blueprintAllStates, blueprintWritableStates, blueprintVerbEventsFor, blueprintEventMetadata, dataInputs, dataOutputs, isPureNode,
    blueprintContract, connectNodes, validateBlueprint, simulateGraph, blueprintAppearance, upgradeBlueprint, elementInstanceNode,
    variableTypes, variableScopes, variableOperators, typedDefault, isBlueprintSignalEvent, controlNodeTypes, timerActions,
    executionOutputs, switchCaseIds, randomBranchIds, groupMemberTypes, eventContextProperties, eventContextTypes,
    acceptsDataType } from './blueprint-model.js';

// Saved node coordinates start at ORIGIN so cards can be placed around the event.
const ORIGIN = { x: 320, y: 160 }, PLANE = 5400, MAX_POSITION = 4700, PAD = 1200;
const MIN_ZOOM = .35, MAX_ZOOM = 1.5, ZOOM_STEP = .15, HISTORY_LIMIT = 100;
const SVG = 'http://www.w3.org/2000/svg';
const catalog = [
    { type: 'state', group: 'Actions', description: 'Change a door, lever or torch mechanism to one of its native states.' },
    { type: 'interact', group: 'Actions', description: 'Run the target object\'s On interaction behavior, including its connected image, light and sound actions.' },
    { type: 'flame', group: 'Actions', description: 'Light or extinguish a torch without moving its mechanism.', missing: 'Add a torch to this map first.' },
    { type: 'sound', group: 'Actions', description: 'Play a campaign sound at a chosen volume.', missing: 'Add a sound to this campaign first.' },
    { type: 'light', group: 'Actions', description: 'Turn a light from this project on or off.', missing: 'Add a light to this project first.' },
    { type: 'sprite', group: 'Actions', description: "Change this element's image, or the image of the elements connected to Target." },
    { type: 'reveal', group: 'Actions', description: 'Reveal a secret or invisible door: this one, or the door connected to Target.' },
    { type: 'barrier', group: 'Actions', description: 'Block or let through movement, vision, light or sound at this door or the door connected to Target.' },
    { type: 'soundControl', group: 'Actions', description: 'Stop a playing campaign sound or change its volume.', missing: 'Add a sound to this campaign first.' },
    { type: 'condition', group: 'Logic', description: 'Compare the state at the start of the event and continue on True or False.' },
    { type: 'switch', group: 'Logic', description: 'Choose one matching case by value, or continue through Default.', aliases: 'switch' },
    { type: 'random', group: 'Logic', description: 'Choose one branch using its weight. Zero disables a branch.', aliases: 'random' },
    { type: 'all', group: 'Logic', description: 'Returns True when all connected conditions are true.', aliases: 'all and' },
    { type: 'any', group: 'Logic', description: 'Returns True when at least one connected condition is true.', aliases: 'any or' },
    { type: 'setVariable', group: 'Actions', description: 'Store a typed value for this element or the scene.', aliases: 'setVariable' },
    { type: 'emitEvent', group: 'Actions', description: 'Queue a named signal for an element or matching listeners in this scene.', aliases: 'emitEvent' },
    { type: 'sequence', group: 'Logic', description: 'Run up to four branches one after another, in order.' },
    { type: 'counter', group: 'Logic', description: 'Count activations and continue through Reached when the target is met.', aliases: 'counter' },
    { type: 'once', group: 'Logic', description: 'Continue through First time only once, until the GM resets this node.', aliases: 'once' },
    { type: 'cooldown', group: 'Logic', description: 'Allow one activation, then block this path until the cooldown ends.', aliases: 'cooldown' },
    { type: 'delay', group: 'Logic', description: 'Wait, then resume the rest of this event on the server.', aliases: 'delay wait' },
    { type: 'timer', group: 'Logic', description: 'Start, stop or restart a named timer. Its event runs when the timer expires.', aliases: 'timer' },
    { type: 'property', group: 'Values', description: 'Read the element state, or the state it just left.' },
    { type: 'compare', group: 'Values', description: 'Check whether a state equals the chosen one; outputs True or False.' },
    { type: 'getVariable', group: 'Values', description: 'Read a stored variable, or its default when no value exists.', aliases: 'getVariable' },
    { type: 'compareValue', group: 'Logic', description: 'Compare Boolean, number or text values and output True or False.', aliases: 'compareValue' },
    { type: 'reference', group: 'Values', description: 'Choose a live object, door, lever, torch or region for a compatible Target.', missing: 'Add another object to this map first.' },
    { type: 'elementGroup', group: 'Values', description: 'Choose an ordered group of elements, lights or sounds for compatible actions.', aliases: 'group elementGroup' },
    { type: 'lightReference', group: 'Values', description: 'Reference a light for a compatible Target input.', missing: 'Add a light to this project first.', aliases: 'lightReference' },
    { type: 'soundReference', group: 'Values', description: 'Reference a campaign sound for a compatible Target input.', missing: 'Add a sound to this campaign first.', aliases: 'soundReference' },
    { type: 'eventContext', group: 'Values', description: 'Read who triggered this event, its token or its current event state.', aliases: 'eventContext context' },
    { type: 'move', group: 'Actions', description: 'Move live objects by an offset in grid cells.', aliases: 'move' },
    { type: 'rotate', group: 'Actions', description: 'Rotate live objects around their own centers.', aliases: 'rotate' },
    { type: 'setInteraction', group: 'Actions', description: 'Allow or block direct player interaction. The GM can still operate the mechanism.', aliases: 'setInteraction' },
    { type: 'setRegion', group: 'Actions', description: 'Enable or disable presence triggers without generating entry or exit events.', aliases: 'setRegion' },
    { type: 'setVisibility', group: 'Actions', description: 'Show or hide live artwork while preserving its collision barriers.', aliases: 'setVisibility visibility' },
    { type: 'setAppearance', group: 'Actions', description: 'Change a dynamic surface material or native object image.', missing: 'Add an image to this project first.', aliases: 'setAppearance material' },
    { type: 'showMessage', group: 'Actions', description: 'Show a plain text message to an authorized audience.', aliases: 'showMessage' },
    { type: 'showHandout', group: 'Actions', description: 'Open a handout only for recipients who can already read it.', missing: 'Create a handout in this campaign first.', aliases: 'showHandout' },
    { type: 'cameraFocus', group: 'Actions', description: 'Request camera focus from recipients who allow it.', aliases: 'cameraFocus' },
    { type: 'teleport', group: 'Actions', description: 'Transport the triggering token to an available place in a region of this scene.', missing: 'Add a presence region to this map first.', aliases: 'teleport' },
];
const groups = ['Actions', 'Logic', 'Values'];
let clipboard = null;
// A substring of the name or description ranks first; otherwise the query letters
// must appear in order within the node name, so long descriptions cannot match
// scattered letters.
function fuzzy(query, name, text) {
    if (!query) return 1;
    const at = text.indexOf(query);
    if (at >= 0) return 1000 - at;
    let score = 0, last = -1;
    for (const char of query) {
        const index = name.indexOf(char, last + 1);
        if (index < 0) return 0;
        score += index === last + 1 ? 5 : 1; last = index;
    }
    return score;
}
// Execution sockets read as circles; typed value sockets as diamonds in their type color.
const typeNames = { state: 'State', boolean: 'True or False', number: 'Number', text: 'Text', door: 'Element', element: 'Element',
    elementset: 'Element group', light: 'Light', lightset: 'Light group', sound: 'Sound', soundset: 'Sound group' };

/** Edit an isolated graph; persist valid authored edits without running its events. */
export function openBlueprintEditor({ element, elements, door, doors = [], assets = [], materials = assets, lights = [], sounds = [], users = [], handouts = [], campaignId, initialEvent, nested = false, autosave = true, linkedScene = false, t, pick, onSave, onDiscard, onClose }) {
    if (!document.querySelector('link[href*="builder/blueprint-editor.css"]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet';
        link.href = new URL('./blueprint-editor.css', import.meta.url).href; document.head.append(link);
    }
    const object = element || door, kind = object.kind || object.blueprint?.kind || (object.torch ? 'torch' : object.lever ? 'lever' : 'door');
    const emptyObject = object.empty === true;
    const ownStates = blueprintStatesFor(kind), initialState = object[kind]?.state || object.state || ownStates[0];
    const abort = new AbortController(), { signal } = abort;
    let draft = upgradeBlueprint(object.blueprint || defaultBlueprint(kind));
    const original = JSON.stringify(draft), instance = elementInstanceNode(object, kind);
    let saver, authoredChange = false, changeQueued = false, inputTimer, confirmedKey = original,
        confirmedBlueprint = structuredClone(object.blueprint);
    const undoStack = [], redoStack = [], pan = { x: 0, y: 0 }, touches = new Map();
    let state = initialState, appearanceState = initialState, trigger = kind === 'region' ? 'presence-enter' : 'verb-interact', signalName = '', pending, disposed = false, saving = false, zoom = 1, boxDrag, lastPointer;
    const authored = Object.keys(draft.graphs).filter(key => draft.graphs[key].nodes.length > 1 || draft.graphs[key].edges.length);
    const startingEvent = initialEvent && draft.graphs[initialEvent] ? initialEvent : authored[0];
    if (startingEvent) {
        const [phase, value] = startingEvent.split(':');
        if (phase === 'signal') { trigger = 'signal'; signalName = value; }
        else if (phase === 'presence') trigger = `presence-${value}`;
        else if (blueprintVerbEventsFor(kind).includes(startingEvent)) trigger = `verb-${startingEvent}`;
    }
    // Selected card ids; the door card's id stands for the entry event node it represents.
    const selection = new Set();
    let frame, wireFrame, wireDrag, wireChoice, wirePreview, panDrag, pinch, renderedEvent, suppressClick = false;
    const stateName = (value, stateKind = kind) => t({ closed: 'Closed', open: 'Opened', locked: 'Locked',
        off: stateKind === 'torch' ? 'Normal' : 'Deactivated', on: stateKind === 'torch' ? 'Turned' : 'Activated', empty: 'Empty', occupied: 'Occupied' }[value] || value);
    const kindName = value => t(emptyObject ? 'Empty Object' : { door: 'Door', lever: 'Lever', torch: 'Torch', region: 'Region' }[value]);
    const triggerName = value => t({ 'verb-interact': 'On interaction',
        'verb-destroy': 'On destroy', 'presence-enter': 'On area enter', 'presence-exit': 'On area exit' }[value] || value);
    const typeName = value => t({ event: 'Event', light: 'Set light', sound: 'Play sound', state: 'Change state', interact: 'Interact with object', condition: 'Check state',
        sprite: 'Change sprite', sequence: 'Sequence', property: 'Get property', compare: 'Compare state',
        reference: 'Element reference', reveal: 'Reveal', barrier: 'Set barrier', soundControl: 'Control sound', flame: 'Set flame',
        all: 'All conditions', any: 'Any condition', getVariable: 'Get variable', setVariable: 'Set variable',
        compareValue: 'Compare value', emitEvent: 'Emit event', counter: 'Counter', once: 'Once', cooldown: 'Cooldown', delay: 'Delay', timer: 'Timer',
        switch: 'Switch', random: 'Random', elementGroup: 'Element group', lightReference: 'Light reference', soundReference: 'Sound reference',
        eventContext: 'Event context', move: 'Move object', rotate: 'Rotate object', setInteraction: 'Set interaction', setRegion: 'Set region',
        showMessage: 'Show message', showHandout: 'Show handout', cameraFocus: 'Focus camera', teleport: 'Teleport token',
        setVisibility: 'Set visibility', setAppearance: 'Set appearance' }[value]);
    const timerActionName = value => t({ start: 'Start timer', stop: 'Stop timer', restart: 'Restart timer' }[value]);
    const choiceName = (type, output) => output === 'default' ? t('Default')
        : t(type === 'switch' ? 'Case {0}' : 'Branch {0}', { 0: output.replace(/\D/g, '') });
    const scopeName = value => t(value === 'scene' ? 'Scene' : 'This element');
    const operatorName = value => t({ eq: 'Equals', ne: 'Does not equal', lt: 'Less than', lte: 'Less than or equal',
        gt: 'Greater than', gte: 'Greater than or equal' }[value]);
    const channelName = value => t({ movement: 'Movement', vision: 'Vision', light: 'Light', sound: 'Sound' }[value]);
    const modeName = value => t({ block: 'Block', pass: 'Pass', attenuate: 'Attenuate' }[value]);
    const otherElements = (elements || doors).filter(row => row.id !== object.id);
    const spriteAssets = [...new Map([...assets, ...materials].map(asset => [asset.id, asset])).values()];
    const elementName = id => otherElements.find(row => row.id === id)?.name;
    const contextName = value => t({ event: 'Event', sourceId: 'Triggering element ID', userId: 'Triggering user ID', userName: 'Triggering user name',
        tokenId: 'Triggering token ID', actorId: 'Triggering actor ID', presence: 'Presence transition', count: 'Occupancy count',
        hasToken: 'Has triggering token', state: 'Current state', previous: 'Previous state' }[value]);
    const memberTypeName = value => t({ element: 'Elements', light: 'Lights', sound: 'Sounds' }[value]);
    const groupMembers = memberType => memberType === 'light' ? lights.map((row, index) => ({ ...row, name: row.name || `${t('Light')} ${index + 1}` }))
        : memberType === 'sound' ? sounds : [object, ...otherElements];
    const targetName = value => {
        const names = (Array.isArray(value) ? value : [value]).map(id => id === object.id ? object.name : elementName(id)
            || groupMembers('light').find(row => row.id === id)?.name || sounds.find(row => row.id === id)?.name || t('Missing element'));
        return names.join(', ') || t('Missing target');
    };
    const appearanceName = value => t({ inherit: 'Native appearance', hidden: 'Hidden image', asset: 'Use image' }[value]);
    const portLabel = port => /^\d+$/.test(port.label) ? port.label : t(port.label);
    const available = type => type === 'setAppearance' ? materials.length > 0
        : type === 'showHandout' ? handouts.length > 0
        : type === 'teleport' ? [object, ...otherElements].some(row => row.kind === 'region')
        : ['light', 'lightReference'].includes(type) ? lights.length > 0 : ['sound', 'soundControl', 'soundReference'].includes(type) ? sounds.length > 0
        : type === 'reference' ? otherElements.length > 0 : true;
    const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
    const event = () => trigger.startsWith('verb-') ? trigger.slice(5) : trigger === 'signal' ? `signal:${signalName}` : `presence:${trigger.slice('presence-'.length)}`;
    const eventName = () => trigger === 'signal' ? `${t('On signal')}: ${signalName}` : triggerName(trigger);
    const shift = () => 0;
    const portName = key => {
        const meta = blueprintEventMetadata(key, kind);
        return `${t(meta.label)}${meta.name ? ` · ${meta.name}` : ''}`;
    };
    function chooseEvent(key) {
        if (key !== event()) selection.clear();
        if (blueprintVerbEventsFor(kind).includes(key) && !key.includes(':')) { trigger = `verb-${key}`; return; }
        const [phase, value] = key.split(':');
        if (phase === 'presence') trigger = `presence-${value}`;
        else if (phase === 'signal') { trigger = 'signal'; signalName = value; }
    }
    const graph = () => draft.graphs[event()] || eventGraph(event());
    const editGraph = () => draft.graphs[event()] ||= eventGraph(event());
    const listen = (element, name, callback, options = {}) => element.addEventListener(name, callback, { signal, ...options });
    function node(tag, attrs = {}, text) {
        const element = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
        if (text !== undefined) element.textContent = text;
        return element;
    }
    function button(label, attrs = {}) { return node('button', { type: 'button', ...attrs }, t(label)); }
    function options(select, rows, value) {
        select.replaceChildren(...rows.map(([id, label]) => new Option(label, id))); select.value = value;
    }
    function field(label, control) { const wrapper = node('label', {}, t(label)); wrapper.append(control); return wrapper; }
    function dot(attrs = { 'data-blueprint-socket-dot': '' }) { return node('span', { ...attrs, 'aria-hidden': 'true' }); }

    const modal = node('section', { class: 'table-form-modal smart-object', 'data-smart-object-modal': '', 'aria-labelledby': 'smart-object-title' });
    const header = node('header'), heading = node('div', { class: 'smart-object__title' });
    heading.append(node('strong', { id: 'smart-object-title' }, t('Smart object')),
        node('span', { class: 'smart-object__subtitle', translate: 'no' }, `${instance.name} · ${stateName(instance.state)}`));
    const close = button('Close', { 'data-blueprint-close': '', 'aria-label': t('Close'), class: 'smart-object__close' }); close.textContent = '×';
    header.append(heading, close);
    const body = node('div', { class: 'table-form-modal__body smart-object__body' });
    const layout = node('div', { class: 'smart-object__layout' });

    const rail = node('nav', { class: 'smart-object__events', 'aria-label': t('Events') });

    const stage = node('section', { class: 'smart-object__stage', 'aria-label': t('Blueprint graph') });
    const tools = node('div', { class: 'smart-object__tools' });
    const add = button('Add node', { 'data-blueprint-add': '', class: 'smart-object__primary' });
    const simulate = button('Simulate', { 'data-blueprint-simulate': '' });
    const undo = button('Undo', { 'data-blueprint-undo': '', title: t('Undo (Ctrl+Z)') });
    const redo = button('Redo', { 'data-blueprint-redo': '', title: t('Redo (Ctrl+Shift+Z)') });
    tools.append(add, simulate, node('span', { class: 'smart-object__tools-gap' }), undo, redo);
    if (campaignId) {
        const templates = button('Templates', { 'data-blueprint-templates': '' });
        listen(templates, 'click', async () => {
            const focused = document.activeElement;
            if (focused?.matches('[data-blueprint-param]') && authoredControl(focused)) focused.dispatchEvent(new Event('change'));
            clearConnection();
            try { await openTemplateLibrary({ campaignId, blueprint: draft, ownerId: object.id,
                catalog: { assets, materials, elements: [object, ...otherElements], lights, sounds, users, handouts }, t,
                onApply: blueprint => {
                    validateBlueprint(blueprint, { assets, materials, lights, sounds, element: object });
                    remember(); draft = structuredClone(blueprint); pending = null; selection.clear();
                    renderSettings(); renderGraph(); fitView();
                } }); } catch (cause) { error(cause); }
        });
        tools.insertBefore(templates, undo);
    }
    const viewport = node('div', { class: 'smart-object__viewport' });
    const canvas = node('div', { class: 'smart-object__canvas', 'data-blueprint-canvas': '', tabindex: '0', 'aria-label': t('Blueprint graph') });
    const surface = node('div', { class: 'smart-object__surface' }), plane = node('div', { class: 'smart-object__plane' });
    plane.style.width = plane.style.height = `${PLANE}px`; plane.style.left = plane.style.top = `${PAD}px`;
    const wires = document.createElementNS(SVG, 'svg');
    wires.classList.add('smart-object__wires'); wires.setAttribute('aria-label', t('Connections'));
    wires.setAttribute('width', PLANE); wires.setAttribute('height', PLANE);
    const nodes = node('div', { class: 'smart-object__nodes' }); plane.append(wires, nodes); surface.append(plane); canvas.append(surface);
    const controls = node('div', { class: 'smart-object__view-controls', role: 'group', 'aria-label': t('Zoom') });
    const zoomOut = button('−', { 'aria-label': t('Zoom out') }), zoomIn = button('+', { 'aria-label': t('Zoom in') });
    const zoomReset = node('button', { type: 'button', 'data-blueprint-zoom-reset': '', 'aria-label': t('Reset zoom'), class: 'smart-object__zoom-level' }, '100%');
    const fit = button('Fit graph', { 'data-blueprint-fit': '' });
    controls.append(zoomOut, zoomReset, zoomIn, fit);
    const guide = node('p', { class: 'smart-object__guide', 'data-blueprint-guide': '', role: 'status' });
    const minimap = document.createElementNS(SVG, 'svg');
    minimap.classList.add('smart-object__minimap'); minimap.setAttribute('data-blueprint-minimap', '');
    minimap.setAttribute('role', 'img'); minimap.setAttribute('aria-label', t('Graph overview'));
    const marquee = node('div', { class: 'smart-object__marquee', 'data-blueprint-marquee': '', hidden: '' });
    viewport.append(canvas, guide, minimap, marquee, controls); stage.append(tools, viewport);

    const inspector = node('aside', { class: 'smart-object__inspector' });
    const appearanceSection = node('section', { class: 'smart-object__panel' }), appearanceTitle = node('h3');
    const preview = node('div', { class: 'smart-object__preview', 'data-blueprint-preview': '' });
    const appearance = node('select', { 'data-blueprint-appearance': '' }), asset = node('select', { 'data-blueprint-asset': '' });
    const assetField = field('Image', asset);
    options(appearance, [['inherit', t('Native appearance')], ['hidden', t('Hidden image')], ['asset', t('Use image')]], 'inherit');
    const appearanceStateSelect = node('select', { 'data-blueprint-appearance-state': '' });
    appearanceSection.append(appearanceTitle, field('State', appearanceStateSelect), preview, field('Appearance in this state', appearance), assetField);
    appearanceSection.hidden = kind === 'region' || emptyObject;
    const simulationSection = node('section', { class: 'smart-object__panel' });
    const traceHint = node('p', { class: 'smart-object__hint' }, t('Simulate to highlight the path this event runs.'));
    const trace = node('ol', { class: 'smart-object__trace', 'data-blueprint-trace': '', 'aria-live': 'polite' });
    const previewState = node('select', { 'data-blueprint-simulation-state': '' }), previewStateField = field('Current state for simulation', previewState);
    const simulationVariables = node('details', { class: 'smart-object__simulation-variables', 'data-blueprint-simulation-variables': '', hidden: '' });
    const simulationValues = node('div'), simulationMemory = { element: Object.create(null), scene: Object.create(null) };
    simulationVariables.append(node('summary', {}, t('Simulation variables')),
        node('p', { class: 'smart-object__hint' }, t('Preview values only. Stored game variables are unchanged.')), simulationValues);
    const simulationGates = node('details', { class: 'smart-object__simulation-variables', 'data-blueprint-simulation-gates': '', hidden: '' });
    const simulationGateValues = node('div'), gatePreviews = new Map();
    simulationGates.append(node('summary', {}, t('Persistent node preview')),
        node('p', { class: 'smart-object__hint' }, t('Choose the state before this event. Simulation does not save game progress.')), simulationGateValues);
    const simulationContextPanel = node('details', { class: 'smart-object__simulation-variables', 'data-blueprint-simulation-context': '', hidden: '' });
    const simulationContextFields = node('div'), simulationContext = Object.create(null);
    simulationContextPanel.append(node('summary', {}, t('Event context preview')),
        node('p', { class: 'smart-object__hint' }, t('Preview values only. In the game, the server supplies the original trigger context.')), simulationContextFields);
    simulationSection.append(node('h3', {}, t('Simulation')), previewStateField, simulationVariables, simulationGates, simulationContextPanel, traceHint, trace);
    inspector.append(appearanceSection, simulationSection);
    layout.append(rail, stage, inspector); body.append(layout);

    const footer = node('footer'), alert = node('p', { role: 'alert', hidden: '' });
    const cancel = button(autosave ? 'Close' : 'Cancel', { 'data-blueprint-cancel': '' });
    const save = button('Save', { 'data-blueprint-save': '', class: 'smart-object__primary' });
    const saveStatus = node('p', { class: 'smart-object__autosave', 'data-blueprint-autosave': '', role: 'status', 'aria-live': 'polite' });
    const retry = button('Retry', { 'data-blueprint-retry': '', hidden: '' });
    const discard = button('Discard unsaved changes', { 'data-blueprint-discard': '', hidden: '' });
    save.hidden = autosave; saveStatus.hidden = !autosave;
    footer.append(saveStatus, alert, retry, discard, cancel, save); modal.append(header, body, footer);

    function error(cause) { alert.textContent = t(cause.message); alert.hidden = false; }
    function clearSimulation() {
        if (!['error', 'conflict', 'blocked'].includes(saver?.state.status)) alert.hidden = true;
        trace.replaceChildren(); traceHint.hidden = false;
        for (const element of plane.querySelectorAll('.is-executed')) element.classList.remove('is-executed');
    }
    // Undo snapshots cover the whole draft so a restored step also restores
    // appearance, parameters and positions together.
    function remember(snapshot = JSON.stringify(draft)) {
        changed();
        if (undoStack.at(-1) === snapshot) return;
        undoStack.push(snapshot); redoStack.length = 0;
        if (undoStack.length > HISTORY_LIMIT) undoStack.shift();
        renderHistory();
    }
    function restore(from, to) {
        if (!from.length) return;
        clearConnection(); pending = null; selection.clear();
        to.push(JSON.stringify(draft)); draft = JSON.parse(from.pop());
        if (trigger === 'signal' && !Object.hasOwn(draft.graphs, event())) chooseEvent(blueprintVerbEventsFor(kind)[0]);
        renderSettings(); renderGraph(); changed();
    }
    function changed() {
        authoredChange = true;
        if (!autosave || disposed || changeQueued) return;
        changeQueued = true;
        // Mutators call remember before changing a field; observe their complete edit.
        queueMicrotask(() => { changeQueued = false; if (!disposed) saver?.schedule(); });
    }
    function normalizedBlueprint() {
        const candidate = structuredClone(draft), originalGraphs = JSON.parse(original).graphs;
        for (const [key, value] of Object.entries(candidate.graphs)) {
            if (!isBlueprintSignalEvent(key) && !Object.hasOwn(originalGraphs, key)
                    && JSON.stringify(value) === JSON.stringify(eventGraph(key))) delete candidate.graphs[key];
        }
        return candidate;
    }
    const authoredControl = control => !control.disabled && (control.matches('[data-blueprint-appearance], [data-blueprint-asset]')
        || control.matches('[data-blueprint-param]') && control.closest('[data-blueprint-node]'));
    const authoredFields = () => [...modal.querySelectorAll('[data-blueprint-param], [data-blueprint-appearance], [data-blueprint-asset]')]
        .filter(authoredControl);
    function fieldsValid(report = false) {
        return authoredFields().every(control => report ? control.reportValidity() : control.checkValidity());
    }
    function saveState(value) {
        const inputPending = inputTimer !== undefined || !fieldsValid();
        const status = inputPending && ['idle', 'saved', 'pending'].includes(value.status)
            ? fieldsValid() ? 'pending' : 'blocked' : value.status;
        saveStatus.dataset.state = status;
        saveStatus.textContent = t({ idle: linkedScene ? 'Edits save to the project. Update the scene to apply them in the game.' : 'Changes save automatically.', pending: 'Saving soon...', saving: 'Saving...',
            saved: linkedScene ? 'Project saved. Update the scene to apply these changes in the game.' : 'All changes saved.', error: 'Could not save changes. Your edits are kept here.',
            conflict: 'This behavior changed elsewhere. Reopen it before continuing.',
            blocked: 'Check the highlighted fields before saving.' }[status] || 'Changes save automatically.');
        retry.hidden = !['error', 'blocked'].includes(status);
        discard.hidden = !['conflict', 'blocked'].includes(status) && !(status === 'error' && !value.retrying);
        if (value.status === 'saving') modal.setAttribute('aria-busy', 'true'); else modal.removeAttribute('aria-busy');
        if (value.error) error(value.error); else alert.hidden = true;
    }
    if (autosave) saver = createAutosave({
        initialKey: JSON.stringify(normalizedBlueprint()),
        read: () => {
            const blueprint = normalizedBlueprint();
            validateBlueprint(blueprint, { assets, materials, lights, sounds, element: object });
            return { key: JSON.stringify(blueprint), payload: blueprint };
        },
        canSave: () => !disposed && inputTimer === undefined && !pending && !wireDrag && !wireChoice
            && !nodes.querySelector('.is-dragging') && fieldsValid(),
        save: async snapshot => {
            try { await onSave(structuredClone(snapshot.payload)); }
            catch (cause) { if (cause.code === 'conflict') cause.conflict = true; throw cause; }
            confirmedBlueprint = structuredClone(snapshot.payload);
            confirmedKey = snapshot.key;
        },
        onState: saveState,
    });
    if (saver) saveState(saver.state);
    listen(window, 'beforeunload', event => {
        if (!autosave || !authoredChange || inputTimer === undefined && fieldsValid()
                && JSON.stringify(normalizedBlueprint()) === confirmedKey) return;
        event.preventDefault(); event.returnValue = '';
    });
    listen(modal, 'input', event => {
        const control = event.target;
        if (!autosave || !authoredControl(control)
                || !control.matches('input[data-blueprint-param]:not([type=checkbox]):not([type=range]), textarea[data-blueprint-param]')) return;
        authoredChange = true;
        clearTimeout(inputTimer);
        // Commit a valid typing pause without requiring focus to leave the field.
        inputTimer = setTimeout(() => {
            inputTimer = undefined;
            if (!disposed && control.isConnected && control.checkValidity()) control.dispatchEvent(new Event('change'));
            if (!disposed) saveState(saver.state);
        }, 300);
        saveState(saver.state);
    });
    function renderHistory() { undo.disabled = !undoStack.length; redo.disabled = !redoStack.length; }
    function renderPreview() {
        const result = blueprintAppearance({ ...object, state: appearanceState, ...(['lever', 'torch'].includes(kind) ? { [kind]: { ...object[kind], state: appearanceState } } : {}), blueprint: draft });
        const image = assets.find(row => row.id === result.assetId);
        preview.replaceChildren(result.visible && image
            ? node('img', { src: image.url, alt: t('State appearance') })
            : node('span', {}, t(result.visible ? (kind !== 'door' ? 'Default appearance' : 'Native door') : 'Hidden image')));
    }
    function renderSettings() {
        const config = draft.states[appearanceState]; appearance.value = config.appearance;
        appearanceTitle.textContent = t('Default appearance by state');
        options(appearanceStateSelect, ownStates.map(value => [value, stateName(value)]), appearanceState);
        options(asset, [['', t('Choose an image')], ...assets.map(row => [row.id, row.name])], config.assetId || '');
        assetField.hidden = config.appearance !== 'asset';
        options(previewState, ownStates.map(value => [value, stateName(value)]), state);
        appearanceSection.hidden = kind === 'region' || emptyObject;
        renderPreview();
    }
    function renderRail() {
        const focused = rail.contains(document.activeElement) && document.activeElement.dataset.blueprintEvent;
        rail.replaceChildren(node('h3', {}, t('Events')), node('p', { class: 'smart-object__hint smart-object__event-help',
            'data-blueprint-event-help': '' }, t('Events only start the sequence. Use logic nodes for comparisons and actions to change the element.')));
        const verbs = node('div', { class: 'smart-object__verb-events' });
        const descriptions = {
            interact: 'Starts when someone interacts.',
            'presence:enter': 'Starts when a token enters the area.',
            'presence:exit': 'Starts when a token leaves the area.',
            destroy: 'Runs before this element is removed from the game. Removing it in the builder does not run this event.',
        };
        for (const key of blueprintVerbEventsFor(kind)) {
            const count = Math.max(0, (draft.graphs[key]?.nodes.length || 1) - 1);
            const item = node('button', { type: 'button', class: 'smart-object__event smart-object__verb-event',
                'data-blueprint-event': key, 'aria-pressed': String(key === event()), title: t(descriptions[key]) });
            const label = node('span', { class: 'smart-object__event-label' });
            label.append(node('strong', {}, portName(key)), node('code', { translate: 'no' }, blueprintEventMetadata(key, kind).code));
            item.append(label, node('span', { class: 'smart-object__badge', 'aria-hidden': 'true' }, String(count)));
            listen(item, 'click', () => { clearConnection(); pending = null; selection.clear(); chooseEvent(key); renderSettings(); renderGraph(); fitView(); });
            verbs.append(item);
        }
        rail.append(verbs, node('p', { class: 'smart-object__hint smart-object__event-help' }, t(descriptions[event()]
            || 'Receives a named signal from Emit event or a timer with the same name.')));
        if (['lever', 'torch'].includes(kind) && event().startsWith('presence:')) rail.append(node('p',
            { class: 'smart-object__hint smart-object__event-help' }, t("The object's size and rotation define its area.")));
        if (event() === 'destroy') rail.append(node('p', { class: 'smart-object__hint smart-object__event-help' },
            t('Timers and waits owned by a destroyed element are cancelled. Send a signal to another element for actions that must continue later.')));
        const signals = Object.keys(draft.graphs).filter(isBlueprintSignalEvent).sort();
        const signalSection = node('section', { class: 'smart-object__signals' });
        const signalHeading = node('h3', {}, t('On signal'));
        signalHeading.append(node('code', { class: 'smart-object__event-code', translate: 'no' }, 'onSignal'));
        signalSection.append(signalHeading);
        for (const key of signals) {
            const row = node('div', { class: 'smart-object__signal-row' });
            const name = key.slice(7), count = Math.max(0, draft.graphs[key].nodes.length - 1);
            const choose = node('button', { type: 'button', class: 'smart-object__event smart-object__signal-event',
                'data-blueprint-event': key, 'aria-pressed': String(key === event()), title: name });
            choose.append(node('span', { translate: 'no' }, name), node('span', { class: 'smart-object__badge', 'aria-hidden': 'true' }, String(count)));
            listen(choose, 'click', () => selectEvent(key));
            const remove = button('×', { 'data-blueprint-signal-remove': name, 'aria-label': t('Delete signal graph'), title: t('Delete signal graph') });
            listen(remove, 'click', () => {
                remember(); delete draft.graphs[key];
                if (event() === key) selectEvent(blueprintVerbEventsFor(kind)[0]);
                else renderGraph();
            });
            row.append(choose, remove); signalSection.append(row);
        }
        const name = node('input', { type: 'text', maxlength: '64', pattern: '[A-Za-z][A-Za-z0-9_.\\-]{0,63}',
            'data-blueprint-signal-name': '', placeholder: 'PuzzleSolved', translate: 'no', autocomplete: 'off', 'aria-label': t('Signal name') });
        const create = button('Add signal', { 'data-blueprint-signal-add': '', disabled: '' });
        listen(name, 'input', () => { create.disabled = !name.value || !name.checkValidity() || signals.length >= 16 || !!draft.graphs[`signal:${name.value}`]; });
        const addSignal = () => {
            if (create.disabled) return;
            const key = `signal:${name.value}`, candidate = structuredClone(draft);
            candidate.graphs[key] = eventGraph(key);
            try { validateBlueprint(candidate, { assets, materials, lights, sounds, element: object }); }
            catch (cause) { error(cause); return; }
            remember(); draft = candidate; selectEvent(key);
        };
        listen(create, 'click', addSignal);
        listen(name, 'keydown', event => { if (event.key === 'Enter') { event.preventDefault(); addSignal(); } });
        name.disabled = signals.length >= 16;
        signalSection.append(field('Signal name', name), create); rail.append(signalSection);
        if (focused) rail.querySelector(`[data-blueprint-event="${CSS.escape(focused)}"]`)?.focus({ preventScroll: true });
    }
    // Choosing another event frames its graph; dragging from an event port keeps
    // the camera so the release point stays under the pointer.
    function selectEvent(nextTrigger) {
        clearConnection(); pending = null; selection.clear();
        chooseEvent(nextTrigger);
        renderSettings(); renderGraph(); fitView();
    }
    function updateGuide() {
        guide.textContent = pending?.reverse ? t('Choose a compatible value output.') : pending ? t('Choose the input of the next node.')
            : t('Drag from a connector to add a node. Drag empty space to pan and scroll to zoom.');
    }

    // Camera: the scaled plane sits inside a padded surface and the canvas scroll
    // offset is the pan. Native scrolling, including focus and scrollIntoView,
    // therefore moves the same camera in every direction.
    function applyView() {
        surface.style.width = `${PLANE * zoom + PAD * 2}px`; surface.style.height = `${PLANE * zoom + PAD * 2}px`;
        plane.style.transform = `scale(${zoom})`;
        canvas.scrollLeft = PAD - pan.x; canvas.scrollTop = PAD - pan.y;
        readPan();
        zoomReset.textContent = `${Math.round(zoom * 100)}%`;
    }
    function readPan() {
        pan.x = PAD - canvas.scrollLeft; pan.y = PAD - canvas.scrollTop;
        canvas.style.backgroundSize = `${20 * zoom}px ${20 * zoom}px`;
        canvas.style.backgroundPosition = `${pan.x}px ${pan.y}px`;
        drawMinimap();
    }
    // Overview of every card and the visible area; clicking or dragging recenters the view.
    function drawMinimap() {
        if (disposed || !minimap.isConnected) return;
        const width = minimap.clientWidth, height = minimap.clientHeight, cards = [...nodes.children];
        if (!width || !height || !cards.length) { minimap.replaceChildren(); return; }
        const view = { left: -pan.x / zoom, top: -pan.y / zoom, right: (canvas.clientWidth - pan.x) / zoom, bottom: (canvas.clientHeight - pan.y) / zoom };
        const boxes = cards.map(card => ({ card, left: card.offsetLeft, top: card.offsetTop, right: card.offsetLeft + card.offsetWidth, bottom: card.offsetTop + card.offsetHeight }));
        const left = Math.min(view.left, ...boxes.map(box => box.left)) - 40, top = Math.min(view.top, ...boxes.map(box => box.top)) - 40;
        const right = Math.max(view.right, ...boxes.map(box => box.right)) + 40, bottom = Math.max(view.bottom, ...boxes.map(box => box.bottom)) + 40;
        const scale = Math.min(width / (right - left), height / (bottom - top));
        const offsetX = (width - (right - left) * scale) / 2, offsetY = (height - (bottom - top) * scale) / 2;
        const rect = (box, attrs) => svg('rect', { x: offsetX + (box.left - left) * scale, y: offsetY + (box.top - top) * scale,
            width: Math.max(2, (box.right - box.left) * scale), height: Math.max(2, (box.bottom - box.top) * scale), ...attrs });
        minimap.replaceChildren(...boxes.map(box => rect(box, { class: selection.has(box.card.dataset.blueprintNode) ? 'is-selected' : '',
            'data-node-type': box.card.dataset.blueprintType })), rect(view, { class: 'smart-object__minimap-view' }));
        Object.assign(minimap.dataset, { left: left - offsetX / scale, top: top - offsetY / scale, scale });
    }
    function minimapPoint(event) {
        const bounds = minimap.getBoundingClientRect(), scale = Number(minimap.dataset.scale) || 1;
        return { x: (event.clientX - bounds.left) / scale + Number(minimap.dataset.left || 0), y: (event.clientY - bounds.top) / scale + Number(minimap.dataset.top || 0) };
    }
    function zoomAt(next, clientX, clientY) {
        next = clamp(next, MIN_ZOOM, MAX_ZOOM);
        if (Math.abs(next - zoom) < 1e-6) return;
        const rect = plane.getBoundingClientRect(), left = rect.left - pan.x, top = rect.top - pan.y;
        const x = (clientX - rect.left) / zoom, y = (clientY - rect.top) / zoom;
        zoom = next; pan.x = clientX - left - x * zoom; pan.y = clientY - top - y * zoom;
        applyView(); scheduleWirePreview();
    }
    function zoomCenter(next) {
        clearConnection();
        const rect = canvas.getBoundingClientRect();
        zoomAt(next, rect.left + rect.width / 2, rect.top + rect.height / 2);
    }
    function fitView() {
        const cards = [...nodes.children];
        if (!cards.length || !canvas.clientWidth) return;
        const left = Math.min(...cards.map(card => card.offsetLeft)), top = Math.min(...cards.map(card => card.offsetTop));
        const right = Math.max(...cards.map(card => card.offsetLeft + card.offsetWidth));
        const bottom = Math.max(...cards.map(card => card.offsetTop + card.offsetHeight)) + 12;
        const width = canvas.clientWidth, height = canvas.clientHeight, padding = 32;
        zoom = clamp(Math.min(1, (width - padding * 2) / (right - left), (height - padding * 2) / (bottom - top)), MIN_ZOOM, MAX_ZOOM);
        pan.x = (width - (right - left) * zoom) / 2 - left * zoom;
        pan.y = (height - (bottom - top) * zoom) / 2 - top * zoom;
        applyView();
    }
    function planePoint(clientX, clientY) {
        const origin = plane.getBoundingClientRect();
        return { x: (clientX - origin.left) / zoom, y: (clientY - origin.top) / zoom };
    }
    function place(card, position, offsetX) {
        card.style.left = `${position.x + ORIGIN.x + offsetX}px`; card.style.top = `${position.y + ORIGIN.y}px`;
    }

    // Connections
    function anchor(element) {
        const rect = (element.querySelector('[data-blueprint-state-dot], [data-blueprint-socket-dot]') || element).getBoundingClientRect();
        return planePoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
    }
    // Every execution port leaves its card to the right and enters from the left.
    function cable(a, b) {
        const bend = clamp(Math.abs(b.x - a.x) * .5, 40, 180);
        return `M ${a.x} ${a.y} C ${a.x + bend} ${a.y} ${b.x - bend} ${b.y} ${b.x} ${b.y}`;
    }
    function svg(tag, attrs) {
        const element = document.createElementNS(SVG, tag);
        for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
        return element;
    }
    function sourceElement(id) {
        return [...nodes.children].find(element => element.dataset.blueprintNode === id || element.dataset.blueprintEventSource === id);
    }
    function outputElement(source) {
        const attribute = source.data ? 'data-blueprint-data-output' : 'data-blueprint-output';
        return sourceElement(source.id)?.querySelector(`[${attribute}="${CSS.escape(source.output)}"]`);
    }
    function inputElement(target) {
        return sourceElement(target.id)?.querySelector(`[data-blueprint-data-input="${CSS.escape(target.input)}"]`);
    }
    function targetPort(target) {
        return dataInputs(graph().nodes.find(item => item.id === target.id)).find(port => port.id === target.input);
    }
    function wireKind(output) { return output.dataset.blueprintStatePort || output.dataset.blueprintEventPort || output.dataset.portType || output.dataset.blueprintOutput; }
    function edgeKey(edge) { return [edge.from, edge.output, edge.to, ...(edge.kind === 'data' ? [edge.input] : [])].join(':'); }
    function drawEdges() {
        frame = null;
        if (disposed) return;
        wires.replaceChildren(); wirePreview = null;
        for (const edge of graph().edges) {
            const data = edge.kind === 'data';
            const source = sourceElement(edge.from);
            const target = [...nodes.children].find(element => element.dataset.blueprintNode === edge.to);
            const output = outputElement({ id: edge.from, output: edge.output, data });
            const input = data ? target?.querySelector(`[data-blueprint-data-input="${CSS.escape(edge.input)}"]`) : target?.querySelector('[data-blueprint-input]');
            if (!source || !input || !output) continue;
            const d = cable(anchor(output), anchor(input));
            const group = svg('g', { 'data-blueprint-edge': edgeKey(edge), 'data-wire-kind': wireKind(output),
                class: data ? 'is-data' : '', tabindex: '0', role: 'button', 'aria-label': t('Remove connection') });
            group.append(svg('path', { class: 'smart-object__wire-hit', d }), svg('path', { class: 'smart-object__wire', d }));
            const remove = () => {
                remember(); editGraph().edges = graph().edges.filter(item => item !== edge); pending = null; renderGraph();
                canvas.focus({ preventScroll: true });
            };
            listen(group, 'click', remove);
            listen(group, 'keydown', event => { if (['Enter', ' ', 'Delete', 'Backspace'].includes(event.key)) { event.preventDefault(); remove(); } });
            wires.append(group);
        }
        drawWirePreview(); drawMinimap();
    }
    function scheduleEdges() { if (frame) cancelAnimationFrame(frame); frame = requestAnimationFrame(drawEdges); }
    function focusOutput(source) { outputElement(source)?.focus({ preventScroll: true }); }
    function focusTarget(target) { inputElement(target)?.focus({ preventScroll: true }); }
    function clearConnection(restoreFocus = false) {
        const connection = wireDrag || wireChoice, pointerId = wireDrag?.pointerId;
        wireDrag = null;
        wireChoice?.element.remove(); wireChoice = null;
        wirePreview?.remove(); wirePreview = null;
        if (wireFrame) cancelAnimationFrame(wireFrame);
        wireFrame = null;
        if (pointerId !== undefined && canvas.hasPointerCapture(pointerId)) canvas.releasePointerCapture(pointerId);
        if (restoreFocus && connection) {
            if (connection.source) focusOutput(connection.source);
            else if (connection.target) focusTarget(connection.target);
            else connection.returnFocus?.focus({ preventScroll: true });
        }
    }
    function drawWirePreview() {
        wireFrame = null;
        const connection = wireDrag || wireChoice;
        if (disposed || !connection || !connection.source && !connection.target || wireDrag && !wireDrag.moved) return;
        const pin = connection.target ? inputElement(connection.target) : outputElement(connection.source);
        if (!pin) return;
        if (!wirePreview) {
            wirePreview = svg('path', { 'data-blueprint-wire-preview': '', 'aria-hidden': 'true' });
            wires.append(wirePreview);
        }
        wirePreview.dataset.wireKind = wireKind(pin);
        const cursor = planePoint(connection.clientX, connection.clientY), point = anchor(pin);
        wirePreview.setAttribute('d', connection.target ? cable(cursor, point) : cable(point, cursor));
    }
    function scheduleWirePreview() { if (!wireFrame) wireFrame = requestAnimationFrame(drawWirePreview); }
    // Click-to-connect: an execution output pairs with an Input, a value output with a typed value input.
    function connect(id, input) {
        if (!pending) return;
        if (!pending.data !== (input === undefined)) { error(new Error('Invalid blueprint connection.')); return; }
        try { commitConnection({ ...pending, event: event() }, id, null, input); pending = null; renderGraph(); }
        catch (cause) { error(cause); }
    }
    function newAction(type, position) {
        if (!catalog.some(entry => entry.type === type) || !available(type)) return;
        return { id: 'node_' + crypto.randomUUID(), type, ...position,
            ...({ light: { targetId: lights[0]?.id, enabled: true }, sound: { trackId: sounds[0]?.id, volume: .7 },
                state: { targetState: ['door', 'region'].includes(kind) ? 'open' : 'on' }, interact: {}, condition: { state }, sequence: {}, all: {}, any: {}, flame: { enabled: true },
                sprite: spriteAssets[0] ? { appearance: 'asset', assetId: spriteAssets[0].id } : { appearance: 'hidden' },
                property: { property: 'state' }, compare: { state },
                getVariable: { scope: 'element', name: 'variable', valueType: 'boolean', default: false },
                setVariable: { scope: 'element', name: 'variable', valueType: 'boolean', value: false },
                compareValue: { valueType: 'boolean', operator: 'eq', expected: false },
                counter: { target: 3 }, once: {}, cooldown: { seconds: 5 }, delay: { seconds: 3 },
                timer: { name: 'TimerFinished', action: 'start', seconds: 3 },
                switch: { valueType: 'number', value: 0, cases: [{ id: 'case1', value: 1 }, { id: 'case2', value: 2 }] },
                random: { weights: [1, 1] },
                elementGroup: { name: t('Element group'), memberType: 'element', targetIds: [object.id] },
                lightReference: { targetId: lights[0]?.id }, soundReference: { trackId: sounds[0]?.id },
                eventContext: { property: 'userName' }, move: { dx: 1, dy: 0 }, rotate: { degrees: 90 },
                setInteraction: { enabled: true }, setRegion: { enabled: true },
                setVisibility: { visible: true }, setAppearance: { assetId: materials[0]?.id },
                showMessage: { text: t('Message'), audience: { scope: 'trigger' } },
                showHandout: { journalId: handouts[0]?.id, audience: { scope: 'trigger' } },
                cameraFocus: { focusX: 0, focusY: 0, audience: { scope: 'trigger' } },
                teleport: { destinationId: [...otherElements, object].find(row => row.kind === 'region')?.id },
                emitEvent: { scope: 'element', name: 'PuzzleSolved' },
                reference: { targetId: otherElements[0]?.id }, reveal: {}, barrier: { channel: 'movement', mode: 'pass' },
                soundControl: { trackId: sounds[0]?.id, action: 'stop', volume: .5 } }[type]) };
    }
    function commitConnection(source, targetId, action, input) {
        // Validate a complete candidate before adding either a node or an edge to the draft.
        const candidate = structuredClone(draft), value = candidate.graphs[source.event] ||= eventGraph(source.event);
        if (action) value.nodes.push(action);
        if (source.id) connectNodes(value, source.id, source.output, targetId, { version: candidate.version, ...(input === undefined ? {} : { input }) });
        validateBlueprint(candidate, { assets, materials, lights, sounds, element: object });
        remember(); draft.graphs = candidate.graphs;
    }
    function nextPosition(value) {
        const index = value.nodes.length - 1, preferred = { x: 360 + index % 3 * 280, y: 60 + Math.floor(index / 3) * 300 };
        const candidates = [preferred];
        for (const columns of [[0, 1, 2], Array.from({ length: 13 }, (_, index) => index + 3)]) {
            for (let row = 0; row < 14; row++) for (const column of columns) candidates.push({ x: 360 + column * 280, y: 60 + row * 300 });
        }
        return candidates.find(candidate => value.nodes.every(item => {
            const width = item.type === 'event' ? 280 : 230;
            return candidate.x >= item.x + width + 24 || item.x >= candidate.x + 230 + 24
                || candidate.y >= item.y + 260 + 24 || item.y >= candidate.y + 260 + 24;
        })) || preferred;
    }

    // A created node keeps its drop point unless it would cover another card;
    // then it moves down (and finally right) in small steps until it is clear.
    function settle(id) {
        const card = nodes.querySelector(`[data-blueprint-node="${CSS.escape(id)}"]`), item = graph().nodes.find(row => row.id === id);
        if (!card?.isConnected || !item || !card.offsetWidth || !card.offsetHeight) return;
        const others = [...nodes.children].filter(element => element !== card).map(element =>
            ({ left: element.offsetLeft, top: element.offsetTop, right: element.offsetLeft + element.offsetWidth, bottom: element.offsetTop + element.offsetHeight }));
        const gap = 16, width = card.offsetWidth, height = card.offsetHeight;
        const free = (x, y) => others.every(box => x + width + gap <= box.left || box.right + gap <= x || y + height + gap <= box.top || box.bottom + gap <= y);
        const origin = { left: card.offsetLeft, top: card.offsetTop };
        if (free(origin.left, origin.top)) return;
        for (let column = 0; column < 8; column++) for (let row = 1; row <= 40; row++) {
            const left = origin.left + column * 120, top = origin.top + row * 20;
            const x = left - ORIGIN.x - shift(), y = top - ORIGIN.y;
            if (x < 0 || y < 0 || x > MAX_POSITION || y > MAX_POSITION || !free(left, top)) continue;
            item.x = Math.round(x); item.y = Math.round(y); place(card, item, shift()); scheduleEdges(); return;
        }
    }
    function settleChoiceNeighbors() {
        // The initial draft renders before the modal is mounted. Detached cards
        // have no layout measurements and must never change saved coordinates.
        if (!nodes.isConnected) return;
        const overlaps = (first, second) => first && second
            && first.offsetLeft < second.offsetLeft + second.offsetWidth + 16
            && second.offsetLeft < first.offsetLeft + first.offsetWidth + 16
            && first.offsetTop < second.offsetTop + second.offsetHeight + 16
            && second.offsetTop < first.offsetTop + first.offsetHeight + 16;
        for (const item of graph().nodes.filter(row => ['switch', 'random', 'elementGroup', 'eventContext', 'move', 'rotate', 'setInteraction', 'setRegion',
            'setVisibility', 'setAppearance', 'showMessage', 'showHandout', 'cameraFocus', 'teleport'].includes(row.type))) {
            const card = sourceElement(item.id);
            // Choice fields and translated hints can grow after their neighbors
            // were placed. Keep the edited card still and make room below it.
            for (const other of graph().nodes) {
                if (other.id !== item.id && other.type !== 'event' && overlaps(card, sourceElement(other.id))) settle(other.id);
            }
        }
    }
    // Node chooser: a searchable list placed where a wire was released, or
    // beside the toolbar for unconnected nodes.
    function openPicker(connection, { position, focusSearch = true } = {}) {
        if (!position) {
            const point = planePoint(connection.clientX, connection.clientY);
            position = { x: Math.round(clamp(point.x - ORIGIN.x - shift(), 0, MAX_POSITION)),
                y: Math.round(clamp(point.y - ORIGIN.y, 0, MAX_POSITION)) };
        }
        const picker = node('section', { class: 'smart-object__node-picker', 'data-blueprint-node-picker': '',
            role: 'dialog', 'aria-modal': 'false', 'aria-label': t('Choose a node') });
        const search = node('input', { type: 'search', 'data-blueprint-picker-search': '', placeholder: t('Search nodes'),
            'aria-label': t('Search nodes'), autocomplete: 'off', spellcheck: 'false' });
        const list = node('div', { class: 'smart-object__picker-list' }), empty = node('p', { class: 'smart-object__hint', hidden: '' }, t('No matching nodes.'));
        picker.append(node('strong', {}, t('Choose a node')), search, list, empty);
        const choices = [], source = connection.source, target = connection.target;
        const accepted = target && targetPort(target);
        const producer = type => ({ type, valueType: variableTypes.includes(accepted?.type) ? accepted.type : 'boolean',
            property: Object.keys(eventContextTypes).find(key => acceptsDataType(accepted, eventContextTypes[key])) || 'userName',
            memberType: groupMemberTypes.find(type => acceptsDataType(accepted, `${type}set`)) || 'element' });
        // Offer compatible consumers for output drags and producers for input drags.
        const inputFor = entry => {
            if (target) {
                const port = dataOutputs(producer(entry.type)).find(port => acceptsDataType(accepted, port.type));
                return port && { output: port.id };
            }
            if (!source) return {};
            const ports = source.data ? dataInputs({ type: entry.type,
                valueType: variableTypes.includes(source.type) ? source.type : 'boolean' }) : blueprintContract.nodes[entry.type].inputs;
            const port = source.data ? ports.find(item => acceptsDataType(item, source.type))
                : ports.find(item => item.kind === 'execution');
            return port && (source.data ? { input: port.id } : {});
        };
        for (const group of groups) {
            const entries = catalog.filter(row => row.group === group && inputFor(row));
            if (!entries.length) continue;
            const section = node('div', { class: 'smart-object__picker-group', role: 'group', 'aria-label': t(group) });
            section.append(node('span', { class: 'smart-object__picker-heading', 'aria-hidden': 'true' }, t(group)));
            for (const entry of entries) {
                const enabled = available(entry.type)
                    && (!target || entry.type !== 'elementGroup' || groupMembers(producer(entry.type).memberType).length > 0);
                const choice = node('button', { type: 'button', 'data-blueprint-pick-type': entry.type, class: `smart-object__pick smart-object__pick--${entry.type}` });
                choice.append(node('span', { class: 'smart-object__pick-name' }, typeName(entry.type)),
                    node('span', { class: 'smart-object__pick-description' }, t(enabled ? entry.description : entry.missing || entry.description)));
                choice.disabled = !enabled;
                listen(choice, 'click', () => {
                    try {
                        const action = newAction(entry.type, position);
                        if (!action) return;
                        if (target) {
                            const suggested = producer(entry.type);
                            if (action.type === 'getVariable') { action.valueType = suggested.valueType; action.default = typedDefault(action.valueType); }
                            if (action.type === 'eventContext') action.property = suggested.property;
                            if (action.type === 'elementGroup') {
                                action.memberType = suggested.memberType;
                                action.targetIds = groupMembers(action.memberType).slice(0, 1).map(row => row.id);
                            }
                        }
                        if (source?.data && ['setVariable', 'compareValue', 'switch'].includes(action.type) && variableTypes.includes(source.type)) {
                            action.valueType = source.type;
                            action[action.type === 'compareValue' ? 'expected' : 'value'] = typedDefault(source.type);
                            if (action.type === 'switch') action.cases = action.cases.map((row, index) => ({ ...row,
                                value: source.type === 'boolean' ? !!index : source.type === 'number' ? index + 1 : String(index + 1) }));
                        }
                        if (['getVariable', 'setVariable'].includes(action.type)) {
                            const declarations = Object.values(draft.graphs).flatMap(graph => graph.nodes)
                                .filter(node => ['getVariable', 'setVariable'].includes(node.type) && node.scope === action.scope);
                            if (declarations.some(node => node.name === action.name && node.valueType !== action.valueType)) {
                                const names = new Set(declarations.map(node => node.name));
                                let suffix = 2;
                                while (names.has(`variable${suffix}`)) suffix++;
                                action.name = `variable${suffix}`;
                            }
                        }
                        if (target) commitConnection({ id: action.id, output: inputFor(entry).output, data: true, event: target.event }, target.id, action, target.input);
                        else commitConnection(source || { event: event() }, action.id, action, inputFor(entry).input);
                        clearConnection(); pending = null; selection.clear(); selection.add(action.id); renderGraph(); settle(action.id);
                        nodes.querySelector(`[data-blueprint-drag="${action.id}"]`)?.focus({ preventScroll: true });
                    } catch (cause) { error(cause); }
                });
                section.append(choice); choices.push({ choice, section, name: typeName(entry.type).toLocaleLowerCase(), text: `${typeName(entry.type)} ${t(entry.description)} ${entry.aliases || ''}`.toLocaleLowerCase() });
            }
            list.append(section);
        }
        const cancelPick = button('Cancel', { 'data-blueprint-picker-cancel': '', class: 'smart-object__picker-cancel' });
        listen(cancelPick, 'click', () => clearConnection(true)); picker.append(cancelPick);
        const enabledChoices = () => choices.filter(({ choice }) => !choice.disabled && !choice.hidden).map(({ choice }) => choice);
        listen(search, 'input', () => {
            const query = search.value.trim().toLocaleLowerCase();
            for (const row of choices) { row.score = fuzzy(query, row.name, row.text); row.choice.hidden = !row.score; }
            choices.sort((a, b) => b.score - a.score);
            for (const row of choices) row.section.append(row.choice);
            for (const section of list.children) section.hidden = ![...section.querySelectorAll('button')].some(choice => !choice.hidden);
            empty.hidden = choices.some(({ choice }) => !choice.hidden);
        });
        listen(search, 'keydown', key => {
            if (key.key === 'Enter') { key.preventDefault(); enabledChoices()[0]?.click(); }
            if (key.key === 'ArrowDown') { key.preventDefault(); enabledChoices()[0]?.focus({ preventScroll: true }); }
        });
        listen(picker, 'keydown', key => {
            if (['ArrowDown', 'ArrowUp'].includes(key.key) && key.target.matches('[data-blueprint-pick-type]')) {
                const rows = enabledChoices(), index = rows.indexOf(key.target);
                key.preventDefault();
                if (key.key === 'ArrowUp' && index === 0) search.focus({ preventScroll: true });
                else rows[clamp(index + (key.key === 'ArrowDown' ? 1 : -1), 0, rows.length - 1)].focus({ preventScroll: true });
            }
            if (key.key !== 'Tab') return;
            const items = [...picker.querySelectorAll('input, button:not(:disabled)')].filter(item => !item.hidden && item.getClientRects().length);
            const index = items.indexOf(document.activeElement);
            key.preventDefault(); key.stopPropagation();
            items[(index + (key.shiftKey ? items.length - 1 : 1)) % items.length].focus({ preventScroll: true });
        });
        wireChoice = { ...connection, element: picker }; modal.append(picker);
        const bounds = modal.getBoundingClientRect(), rect = picker.getBoundingClientRect();
        picker.style.left = `${Math.max(bounds.left + 8, Math.min(connection.clientX, bounds.right - rect.width - 8))}px`;
        picker.style.top = `${Math.max(8, Math.min(connection.clientY, innerHeight - rect.height - 8))}px`;
        (focusSearch ? search : list.querySelector('button:not(:disabled)') || search).focus({ preventScroll: true });
        drawWirePreview();
    }
    function chooseFromKeyboard(source) {
        clearConnection(); pending = null;
        const card = sourceElement(source.id).getBoundingClientRect(), bounds = canvas.getBoundingClientRect();
        openPicker({ source,
            clientX: clamp(card.right + 48, bounds.left + 12, bounds.right - 12),
            clientY: clamp(card.top + 48, bounds.top + 12, bounds.bottom - 12) });
    }
    function chooseForInput(target) {
        clearConnection(); pending = null;
        const card = sourceElement(target.id).getBoundingClientRect(), bounds = canvas.getBoundingClientRect();
        openPicker({ target,
            clientX: clamp(card.left - 48, bounds.left + 12, bounds.right - 12),
            clientY: clamp(card.top + 48, bounds.top + 12, bounds.bottom - 12) });
    }
    function eventSource() { return { id: graph().nodes.find(item => item.type === 'event').id, output: 'next', event: event() }; }
    function pinSource(pin) {
        const id = pin.closest('[data-blueprint-node]').dataset.blueprintNode;
        return pin.hasAttribute('data-blueprint-data-output')
            ? { id, output: pin.dataset.blueprintDataOutput, event: event(), data: true, type: pin.dataset.portType }
            : { id, output: pin.dataset.blueprintOutput, event: event() };
    }
    function pendingFrom(source) {
        return { id: source.id, output: source.output, ...(source.data ? { data: true, type: source.type } : {}) };
    }
    function pinTarget(pin) {
        return { id: pin.closest('[data-blueprint-node]').dataset.blueprintNode,
            input: pin.dataset.blueprintDataInput, type: pin.dataset.portType, event: event() };
    }
    function connectOutput(source) {
        if (!pending?.reverse) return false;
        try {
            if (!source.data) throw new Error('Invalid blueprint connection.');
            commitConnection(source, pending.id, null, pending.input);
            pending = null; renderGraph();
        } catch (cause) { error(cause); }
        return true;
    }
    // Drop a dragged wire on an input; execution and value wires each need their own kind of input.
    function dropOn(source, input) {
        const id = input.closest('[data-blueprint-node]').dataset.blueprintNode, port = input.dataset.blueprintDataInput;
        if (!source.data !== (port === undefined)) throw new Error('Invalid blueprint connection.');
        commitConnection(source, id, null, port);
    }

    modal.addEventListener('pointerdown', event => {
        suppressClick = false;
        if (wireChoice && !wireChoice.element.contains(event.target)) clearConnection();
    }, { signal, capture: true });
    modal.addEventListener('click', event => {
        if (!suppressClick || event.detail === 0) return;
        suppressClick = false; event.preventDefault(); event.stopImmediatePropagation();
    }, { signal, capture: true });
    listen(canvas, 'pointerdown', pointer => {
        if (pointer.pointerType === 'touch') touches.set(pointer.pointerId, { x: pointer.clientX, y: pointer.clientY });
        if (touches.size === 2 && !wireDrag) {
            // A second finger turns the gesture into a pinch around its midpoint.
            const [a, b] = [...touches.values()];
            panDrag = null; canvas.classList.remove('is-panning');
            pinch = { distance: Math.hypot(a.x - b.x, a.y - b.y) || 1, zoom };
            canvas.setPointerCapture(pointer.pointerId); return;
        }
        const pin = pointer.target.closest('[data-blueprint-event-port], [data-blueprint-output], [data-blueprint-data-output], [data-blueprint-data-input]');
        const blank = !pointer.target.closest('[data-blueprint-node], [data-blueprint-edge]');
        if (pointer.button === 0 && !pin && blank && pointer.shiftKey) {
            pointer.preventDefault(); canvas.focus({ preventScroll: true });
            boxDrag = { id: pointer.pointerId, x: pointer.clientX, y: pointer.clientY, base: new Set(selection) };
            canvas.setPointerCapture(pointer.pointerId); return;
        }
        if (pointer.button === 1 || pointer.button === 0 && !pin && blank) {
            pointer.preventDefault(); canvas.focus({ preventScroll: true });
            panDrag = { id: pointer.pointerId, x: pointer.clientX, y: pointer.clientY, moved: false, middle: pointer.button === 1 };
            canvas.setPointerCapture(pointer.pointerId); canvas.classList.add('is-panning'); return;
        }
        if (pointer.button !== 0 || !pin || !canvas.contains(pin)) return;
        pointer.preventDefault(); pointer.stopPropagation();
        const focused = document.activeElement;
        if (focused?.matches('[data-blueprint-param]') && authoredControl(focused)) {
            if (!focused.reportValidity()) return;
            focused.dispatchEvent(new Event('change'));
        }
        const prior = pending;
        clearConnection(); pending = null;
        let source, target, clickPending = true;
        if (pin.hasAttribute('data-blueprint-event-port')) {
            clickPending = event() === pin.dataset.blueprintEventPort;
            chooseEvent(pin.dataset.blueprintEventPort); renderSettings(); renderGraph();
            source = eventSource();
        } else if (pin.hasAttribute('data-blueprint-data-input')) target = pinTarget(pin);
        else source = pinSource(pin);
        wireDrag = { source, target, prior: pin.hasAttribute('data-blueprint-event-port') ? null : prior,
            pointerId: pointer.pointerId, startX: pointer.clientX, startY: pointer.clientY,
            clientX: pointer.clientX, clientY: pointer.clientY, moved: false, clickPending, touch: pointer.pointerType === 'touch' };
        canvas.setPointerCapture(pointer.pointerId);
    });
    function boxRect(event) {
        return { left: Math.min(boxDrag.x, event.clientX), top: Math.min(boxDrag.y, event.clientY),
            right: Math.max(boxDrag.x, event.clientX), bottom: Math.max(boxDrag.y, event.clientY) };
    }
    function selectInBox(event) {
        const box = boxRect(event), frame = viewport.getBoundingClientRect();
        Object.assign(marquee.style, { left: `${box.left - frame.left}px`, top: `${box.top - frame.top}px`,
            width: `${box.right - box.left}px`, height: `${box.bottom - box.top}px` });
        marquee.hidden = false;
        selection.clear();
        for (const id of boxDrag.base) selection.add(id);
        for (const card of nodes.children) {
            const rect = card.getBoundingClientRect();
            if (rect.left < box.right && rect.right > box.left && rect.top < box.bottom && rect.bottom > box.top) selection.add(card.dataset.blueprintNode);
        }
        paintSelection();
    }
    listen(canvas, 'pointermove', event => {
        lastPointer = { clientX: event.clientX, clientY: event.clientY };
        if (boxDrag?.id === event.pointerId) { selectInBox(event); return; }
        if (touches.has(event.pointerId)) touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (pinch && touches.size === 2) {
            const [a, b] = [...touches.values()];
            zoomAt(pinch.zoom * Math.hypot(a.x - b.x, a.y - b.y) / pinch.distance, (a.x + b.x) / 2, (a.y + b.y) / 2);
            return;
        }
        if (panDrag?.id === event.pointerId) {
            panDrag.moved ||= Math.hypot(event.clientX - panDrag.x, event.clientY - panDrag.y) >= 3;
            pan.x += event.clientX - panDrag.x; pan.y += event.clientY - panDrag.y;
            panDrag.x = event.clientX; panDrag.y = event.clientY; applyView(); return;
        }
        if (!wireDrag || event.pointerId !== wireDrag.pointerId) return;
        event.preventDefault(); wireDrag.clientX = event.clientX; wireDrag.clientY = event.clientY;
        wireDrag.moved ||= Math.hypot(event.clientX - wireDrag.startX, event.clientY - wireDrag.startY) >= 4;
        scheduleWirePreview();
    });
    function endPan(event) {
        if (boxDrag?.id === event.pointerId) {
            if (event.type === 'pointerup') selectInBox(event);
            boxDrag = null; marquee.hidden = true;
            if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
            return true;
        }
        touches.delete(event.pointerId);
        if (pinch) { if (touches.size < 2) pinch = null; return true; }
        if (panDrag?.id !== event.pointerId) return false;
        const previous = panDrag; panDrag = null; canvas.classList.remove('is-panning');
        if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
        if (!previous.moved && !previous.middle && event.type === 'pointerup') {
            // A click on empty space clears the selection and a pending click connection.
            const changed = selection.size || pending; selection.clear(); pending = null;
            if (changed) renderGraph();
        }
        return true;
    }
    listen(canvas, 'pointerup', event => {
        if (endPan(event) || !wireDrag || event.pointerId !== wireDrag.pointerId) return;
        event.preventDefault(); suppressClick = true;
        const connection = { ...wireDrag, clientX: event.clientX, clientY: event.clientY };
        clearConnection();
        if (!connection.moved) {
            if (connection.target) {
                if (connection.prior && !connection.prior.reverse) {
                    pending = connection.prior; connect(connection.target.id, connection.target.input);
                } else chooseForInput(connection.target);
                return;
            }
            if (connection.prior?.reverse) {
                pending = connection.prior; connectOutput(connection.source); return;
            }
            pending = connection.clickPending ? pendingFrom(connection.source) : null;
            renderGraph();
            if (!connection.clickPending) fitView();
            focusOutput(connection.source); return;
        }
        const target = document.elementFromPoint(event.clientX, event.clientY);
        if (!target || !canvas.contains(target)) return;
        const input = target.closest(connection.target ? '[data-blueprint-data-output]' : '[data-blueprint-input], [data-blueprint-data-input]');
        if (input && connection.target) {
            try { commitConnection(pinSource(input), connection.target.id, null, connection.target.input); renderGraph(); }
            catch (cause) { error(cause); }
        } else if (input) {
            try { dropOn(connection.source, input); renderGraph(); }
            catch (cause) { error(cause); }
        } else if (!target.closest('[data-blueprint-node], [data-blueprint-edge]')) openPicker(connection, { focusSearch: !connection.touch });
    });
    for (const name of ['pointercancel', 'lostpointercapture']) listen(canvas, name, event => {
        if (endPan(event)) return;
        if (wireDrag?.pointerId === event.pointerId) clearConnection();
    });
    listen(canvas, 'dblclick', event => {
        if (event.target.closest('[data-blueprint-node], [data-blueprint-edge]')) return;
        clearConnection(); pending = null;
        openPicker({ source: null, clientX: event.clientX, clientY: event.clientY, returnFocus: canvas });
    });
    listen(canvas, 'wheel', event => {
        event.preventDefault();
        if (wireChoice) clearConnection();
        zoomAt(zoom * Math.exp(-clamp(event.deltaY, -200, 200) * .002), event.clientX, event.clientY);
    }, { passive: false });
    listen(canvas, 'contextmenu', event => { if (!event.target.closest('input, select, textarea')) event.preventDefault(); });
    listen(canvas, 'keydown', key => {
        const input = key.target.closest('[data-blueprint-data-input]');
        if (input && key.key === 'Enter' && key.shiftKey) {
            key.preventDefault(); key.stopPropagation(); clearConnection();
            const target = pinTarget(input);
            pending = { ...target, reverse: true, data: true }; renderGraph(); focusTarget(target); return;
        }
        const pin = key.target.closest('[data-blueprint-event-port], [data-blueprint-output], [data-blueprint-data-output]');
        if (pin && key.key === 'Enter' && key.shiftKey) {
            key.preventDefault(); key.stopPropagation(); clearConnection();
            if (pin.hasAttribute('data-blueprint-event-port')) {
                chooseEvent(pin.dataset.blueprintEventPort); renderSettings();
                pending = { id: graph().nodes.find(item => item.type === 'event').id, output: 'next' };
            } else pending = pendingFrom(pinSource(pin));
            const source = { ...pending }; renderGraph(); focusOutput(source); return;
        }
        if (key.target !== canvas || key.ctrlKey || key.metaKey || key.altKey) return;
        if (['Delete', 'Backspace'].includes(key.key) && deletable().length) {
            key.preventDefault(); deleteNodes(deletable()); return;
        }
        const offsets = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] };
        if (key.key === '0' || key.key === 'Home' || key.key === '.') fitView();
        else if (key.key === '+' || key.key === '=') zoomCenter(zoom + ZOOM_STEP);
        else if (key.key === '-') zoomCenter(zoom - ZOOM_STEP);
        else if (offsets[key.key]) { pan.x += offsets[key.key][0]; pan.y += offsets[key.key][1]; applyView(); }
        else return;
        key.preventDefault();
    });
    listen(canvas, 'scroll', () => { readPan(); scheduleWirePreview(); });
    listen(canvas, 'pointerleave', () => { lastPointer = null; });
    for (const name of ['pointerdown', 'pointermove']) listen(minimap, name, event => {
        if (event.type === 'pointermove' && !(event.buttons & 1)) return;
        event.preventDefault();
        if (event.type === 'pointerdown') minimap.setPointerCapture(event.pointerId);
        const point = minimapPoint(event);
        pan.x = canvas.clientWidth / 2 - point.x * zoom; pan.y = canvas.clientHeight / 2 - point.y * zoom; applyView();
    });
    // Copy keeps the nodes and the connections between them; the event node stays.
    function copySelection() {
        const items = [...selection].map(itemFor).filter(item => item && item.type !== 'event');
        if (!items.length) return null;
        const ids = new Set(items.map(item => item.id));
        const left = Math.min(...items.map(item => item.x)), top = Math.min(...items.map(item => item.y));
        return { left, top, nodes: items.map(item => ({ ...structuredClone(item), x: item.x - left, y: item.y - top })),
            edges: graph().edges.filter(edge => ids.has(edge.from) && ids.has(edge.to)).map(edge => structuredClone(edge)) };
    }
    function paste(data, origin) {
        if (!data?.nodes.length) return;
        const ids = new Map(data.nodes.map(item => [item.id, 'node_' + crypto.randomUUID()]));
        const candidate = structuredClone(draft), value = candidate.graphs[event()] ||= eventGraph(event());
        for (const item of data.nodes) value.nodes.push({ ...structuredClone(item), id: ids.get(item.id),
            x: clamp(Math.round(origin.x + item.x), 0, MAX_POSITION), y: clamp(Math.round(origin.y + item.y), 0, MAX_POSITION) });
        for (const edge of data.edges) value.edges.push({ ...structuredClone(edge), from: ids.get(edge.from), to: ids.get(edge.to) });
        try { validateBlueprint(candidate, { assets, materials, lights, sounds, element: object }); } catch (cause) { error(cause); return; }
        remember(); draft.graphs = candidate.graphs;
        selection.clear(); for (const id of ids.values()) selection.add(id);
        renderGraph(); canvas.focus({ preventScroll: true });
    }
    // Paste at the pointer when it is over the canvas, otherwise beside the copied nodes.
    function pasteOrigin(data) {
        if (!lastPointer) return { x: data.left + 40, y: data.top + 40 };
        const point = planePoint(lastPointer.clientX, lastPointer.clientY);
        return { x: point.x - ORIGIN.x - shift(), y: point.y - ORIGIN.y };
    }
    listen(window, 'blur', () => clearConnection());
    listen(window, 'resize', () => clearConnection());

    function parameter(item, label, key, values) {
        const control = node('select', { 'data-blueprint-param': key }); options(control, values, String(item[key]));
        listen(control, 'change', () => {
            const value = ['enabled', 'visible'].includes(key) ? control.value === 'true' : control.value;
            if (item[key] === value) return;
            remember(); item[key] = value; clearSimulation();
            if (['reference', 'lightReference', 'soundReference'].includes(item.type)) renderGraph();
        });
        return field(label, control);
    }
    const scalarText = value => typeof value === 'boolean' ? t(value ? 'True' : 'False')
        : typeof value === 'string' ? JSON.stringify(value) : String(value);
    function scalarControl(type, value, key, changed, validate = () => '') {
        const control = type === 'boolean' ? node('select', { 'data-blueprint-param': key })
            : node('input', { type: type === 'number' ? 'number' : 'text', 'data-blueprint-param': key,
                ...(type === 'number' ? { min: '-1000000', max: '1000000', step: 'any', required: '', inputmode: 'decimal' } : { maxlength: '512', translate: 'no' }) });
        if (type === 'boolean') options(control, [['false', t('False')], ['true', t('True')]], String(value));
        else control.value = value;
        if (type === 'text') listen(control, 'input', () => control.setCustomValidity(Array.from(control.value).length > 256 ? t('Invalid blueprint variable value.') : ''));
        listen(control, 'change', () => {
            const actual = type === 'boolean' ? control.value === 'true' : type === 'number' ? Number(control.value) : control.value;
            control.setCustomValidity(type === 'text' && Array.from(control.value).length > 256 ? t('Invalid blueprint variable value.') : validate(actual));
            if (!control.reportValidity()) return;
            changed(actual);
        });
        return control;
    }
    function scalarParameter(item, label, key) {
        return field(label, scalarControl(item.valueType, item[key], key, value => {
            if (item[key] === value) return;
            remember(); item[key] = value; clearSimulation();
        }));
    }
    function nameParameter(item) {
        const control = node('input', { type: 'text', required: '', maxlength: '64', pattern: '[A-Za-z][A-Za-z0-9_.\\-]{0,63}',
            'data-blueprint-param': 'name', translate: 'no', value: item.name });
        listen(control, 'change', () => {
            if (!control.reportValidity() || control.value === item.name) return;
            remember(); item.name = control.value; clearSimulation(); renderSimulationVariables();
        });
        return field('Name', control);
    }
    function typedParameter(item) {
        const control = node('select', { 'data-blueprint-param': 'valueType' });
        options(control, variableTypes.map(value => [value, t(typeNames[value])]), item.valueType);
        listen(control, 'change', () => {
            if (item.valueType === control.value) return;
            remember(); item.valueType = control.value;
            item[item.type === 'getVariable' ? 'default' : ['setVariable', 'switch'].includes(item.type) ? 'value' : 'expected'] = typedDefault(item.valueType);
            if (item.type === 'switch') item.cases = item.cases.slice(0, item.valueType === 'boolean' ? 2 : 4).map((row, index) => ({ ...row,
                value: item.valueType === 'boolean' ? !!index : item.valueType === 'number' ? index + 1 : String(index + 1) }));
            if (item.type === 'compareValue' && item.valueType !== 'number' && !['eq', 'ne'].includes(item.operator)) item.operator = 'eq';
            // Changing a value type removes only connections that no longer match.
            const current = editGraph(), byId = new Map(current.nodes.map(row => [row.id, row]));
            current.edges = current.edges.filter(edge => edge.kind !== 'data' || dataOutputs(byId.get(edge.from)).some(output =>
                output.id === edge.output && dataInputs(byId.get(edge.to)).some(input => input.id === edge.input && acceptsDataType(input, output.type))));
            if (item.type === 'switch') current.edges = current.edges.filter(edge => edge.kind === 'data' || edge.from !== item.id
                || executionOutputs(item).some(port => port.id === edge.output));
            pending = null; renderGraph();
            nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-param=valueType]`)?.focus({ preventScroll: true });
        });
        return field('Value type', control);
    }
    function pruneDataConnections() {
        const current = editGraph(), byId = new Map(current.nodes.map(row => [row.id, row]));
        current.edges = current.edges.filter(edge => edge.kind !== 'data' || dataOutputs(byId.get(edge.from)).some(output =>
            output.id === edge.output && dataInputs(byId.get(edge.to)).some(input => input.id === edge.input && acceptsDataType(input, output.type))));
    }
    function scopeParameter(item) {
        const control = node('select', { 'data-blueprint-param': 'scope' });
        options(control, variableScopes.map(value => [value, scopeName(value)]), item.scope);
        listen(control, 'change', () => {
            if (control.value === item.scope) return;
            remember(); item.scope = control.value;
            if (item.type === 'emitEvent' && item.scope === 'scene') editGraph().edges = graph().edges.filter(edge => !(edge.kind === 'data' && edge.to === item.id && edge.input === 'target'));
            pending = null; renderGraph();
            nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-param=scope]`)?.focus({ preventScroll: true });
        });
        return field('Scope', control);
    }
    function renderSimulationVariables() {
        simulationValues.replaceChildren();
        const seen = new Set();
        for (const item of graph().nodes.filter(row => row.type === 'getVariable')) {
            const key = `${item.scope}:${item.name}`;
            if (seen.has(key)) continue;
            seen.add(key);
            const stored = simulationMemory[item.scope][item.name];
            if (stored && stored.type !== item.valueType) delete simulationMemory[item.scope][item.name];
            const value = stored?.type === item.valueType ? stored.value : item.default;
            const control = scalarControl(item.valueType, value, 'simulation-value', value => {
                simulationMemory[item.scope][item.name] = { type: item.valueType, value }; clearSimulation();
            });
            control.setAttribute('data-blueprint-simulation-variable', item.name);
            simulationValues.append(field(`${scopeName(item.scope)} · ${item.name}`, control));
        }
        simulationVariables.hidden = !seen.size;
    }
    function renderSimulationContext() {
        simulationContextFields.replaceChildren();
        const properties = new Set(graph().nodes.filter(item => item.type === 'eventContext').map(item => item.property));
        for (const property of properties) {
            if (['event', 'state', 'previous'].includes(property)) continue;
            const type = eventContextTypes[property], value = simulationContext[property]
                ?? (property === 'hasToken' ? Boolean(simulationContext.tokenId)
                    : property === 'presence' && event().startsWith('presence:') ? event().slice(9) : typedDefault(type));
            const control = scalarControl(type, value, 'simulation-context', value => {
                simulationContext[property] = value; clearSimulation();
                if (property === 'tokenId' && !Object.hasOwn(simulationContext, 'hasToken')) {
                    const flag = simulationContextFields.querySelector('[data-blueprint-context-property=hasToken]');
                    if (flag) flag.value = String(Boolean(value));
                }
            });
            control.dataset.blueprintContextProperty = property;
            if (property === 'count') { control.min = '0'; control.step = '1'; }
            simulationContextFields.append(field(contextName(property), control));
        }
        simulationContextPanel.hidden = !properties.size;
    }
    const gatePreviewKey = item => JSON.stringify([event(), item.id]);
    function gatePreview(item) {
        const preview = gatePreviews.get(gatePreviewKey(item));
        return preview?.type === item.type ? preview.value : item.type === 'once' ? false : 0;
    }
    function renderSimulationGates() {
        simulationGateValues.replaceChildren();
        const counts = {};
        for (const item of graph().nodes.filter(row => controlNodeTypes.includes(row.type))) {
            const value = gatePreview(item), index = counts[item.type] = (counts[item.type] || 0) + 1;
            const control = item.type === 'once' ? node('select') : node('input', {
                type: 'number', min: '0', max: item.type === 'counter' ? '1000000' : '86400',
                step: item.type === 'counter' ? '1' : 'any', required: '', inputmode: 'decimal' });
            control.setAttribute('data-blueprint-simulation-memory', item.id);
            if (item.type === 'once') options(control, [['false', t('False')], ['true', t('True')]], String(value));
            else control.value = value;
            listen(control, 'change', () => {
                if (!control.reportValidity()) return;
                gatePreviews.set(gatePreviewKey(item), { type: item.type, value: item.type === 'once' ? control.value === 'true' : Number(control.value) });
                clearSimulation();
            });
            const label = t(item.type === 'counter' ? 'Count before event' : item.type === 'once' ? 'Already used' : 'Seconds remaining');
            simulationGateValues.append(field(`${typeName(item.type)} ${index} · ${label}`, control));
        }
        simulationGates.hidden = !simulationGateValues.childElementCount;
    }
    function previewMemory(now) {
        const memory = Object.create(null), entries = Object.create(null);
        for (const item of graph().nodes.filter(row => controlNodeTypes.includes(row.type))) {
            const value = gatePreview(item);
            if (item.type === 'counter') entries[item.id] = { type: item.type, value };
            else if (value) entries[item.id] = { type: item.type, value: item.type === 'once' ? true : now + Math.ceil(value * 1000) };
        }
        if (Object.keys(entries).length) memory[event()] = entries;
        return memory;
    }
    // Suspend the modal while the workspace waits for a click on the map.
    function pickButton(item, kind, key) {
        const control = button('Pick on map', { 'data-blueprint-pick-map': kind, class: 'smart-object__pick-map' });
        control.disabled = !pick;
        listen(control, 'click', async () => {
            clearConnection(); modal.suspend?.();
            const id = await pick(kind, ['doors', 'elements'].includes(kind) ? object.id : null);
            if (disposed) return;
            modal.resume?.();
            if (id && id !== item[key]) { remember(); item[key] = id; clearSimulation(); }
            renderGraph();
            nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-pick-map]`)?.focus({ preventScroll: true });
        });
        return control;
    }
    function groupFields(item, content) {
        const name = node('input', { type: 'text', value: item.name, maxlength: '80', required: '', translate: 'no', 'data-blueprint-param': 'name' });
        listen(name, 'change', () => {
            const value = name.value.trim();
            name.setCustomValidity(value && !value.includes('\0') ? '' : t('Enter a group name.'));
            if (!name.reportValidity() || value === item.name) return;
            remember(); item.name = value; clearSimulation();
        });
        const type = node('select', { 'data-blueprint-param': 'memberType' });
        options(type, groupMemberTypes.map(value => [value, memberTypeName(value)]), item.memberType);
        for (const option of type.options) option.disabled = option.value !== item.memberType && !groupMembers(option.value).length;
        listen(type, 'change', () => {
            if (type.value === item.memberType) return;
            remember(); item.memberType = type.value;
            item.targetIds = groupMembers(item.memberType).slice(0, 1).map(row => row.id);
            pruneDataConnections(); pending = null; renderGraph();
            nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-param=memberType]`)?.focus({ preventScroll: true });
        });
        content.append(field('Group name', name), field('Group type', type));
        const members = groupMembers(item.memberType), list = node('ol', { class: 'smart-object__members', 'data-blueprint-members': '' });
        const focusMember = id => nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-member="${CSS.escape(id)}"] button`)?.focus({ preventScroll: true });
        item.targetIds.forEach((id, index) => {
            const known = members.find(row => row.id === id), label = known?.name || t('Missing target');
            const row = node('li', { 'data-blueprint-member': id, ...(known ? {} : { class: 'is-missing' }) });
            row.append(node('span', { translate: 'no', title: id }, `${index + 1}. ${label}`));
            for (const [direction, text, step] of [['up', '↑', -1], ['down', '↓', 1]]) {
                const move = node('button', { type: 'button', [`data-blueprint-member-${direction}`]: id,
                    'aria-label': `${t(direction === 'up' ? 'Move member up' : 'Move member down')}: ${label}`,
                    ...(index + step < 0 || index + step >= item.targetIds.length ? { disabled: '' } : {}) }, text);
                listen(move, 'click', () => {
                    remember(); [item.targetIds[index], item.targetIds[index + step]] = [item.targetIds[index + step], item.targetIds[index]];
                    renderGraph(); focusMember(id);
                }); row.append(move);
            }
            const remove = node('button', { type: 'button', 'data-blueprint-member-remove': id, 'aria-label': `${t('Remove member')}: ${label}`,
                ...(item.targetIds.length === 1 ? { disabled: '' } : {}) }, '×');
            listen(remove, 'click', () => {
                remember(); item.targetIds = item.targetIds.filter(value => value !== id); renderGraph();
                nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-member-choice]`)?.focus({ preventScroll: true });
            }); row.append(remove); list.append(row);
        });
        const choose = node('select', { 'data-blueprint-member-choice': '', 'aria-label': t('Choose a group member') });
        choose.append(new Option(t('Choose a group member'), ''));
        for (const row of members.filter(row => !item.targetIds.includes(row.id))) choose.append(new Option(row.name, row.id));
        const add = button('Add member', { 'data-blueprint-member-add': '', disabled: '' });
        listen(choose, 'change', () => { add.disabled = !choose.value || item.targetIds.length >= 32; });
        const addMember = id => {
            if (!id || item.targetIds.includes(id) || item.targetIds.length >= 32) return;
            remember(); item.targetIds.push(id); renderGraph(); focusMember(id);
        };
        listen(add, 'click', () => addMember(choose.value));
        choose.disabled = item.targetIds.length >= 32 || choose.options.length === 1;
        content.append(list, choose, add);
        if (item.memberType !== 'sound') {
            const map = button('Pick on map', { 'data-blueprint-member-pick': '', ...(pick && item.targetIds.length < 32 ? {} : { disabled: '' }) });
            listen(map, 'click', async () => {
                clearConnection(); modal.suspend?.();
                const id = await pick(item.memberType === 'light' ? 'lights' : 'elements', null);
                if (disposed) return;
                modal.resume?.(); addMember(id);
            }); content.append(map);
        }
        content.append(node('p', { class: 'smart-object__hint' }, t('Members run in the displayed order and share the command limits.')));
    }
    function audienceFields(item, content) {
        const scope = node('select', { 'data-blueprint-param': 'audienceScope' });
        options(scope, [['trigger', t('Triggering user')], ['players', t('Players')], ['users', t('Chosen users')]], item.audience.scope);
        scope.querySelector('option[value=users]').disabled = !users.length && item.audience.scope !== 'users';
        listen(scope, 'change', () => {
            if (scope.value === item.audience.scope) return;
            remember(); item.audience = { scope: scope.value, ...(scope.value === 'users' ? { userIds: [users[0].id] } : {}) }; renderGraph();
        });
        content.append(field('Audience', scope));
        if (item.audience.scope === 'users') {
            const list = node('div', { class: 'smart-object__audience', 'data-blueprint-audience': '' });
            const choices = new Map(users.map(user => [user.id, user]));
            for (const id of item.audience.userIds) if (!choices.has(id)) choices.set(id, { id, name: t('Unavailable: {0}', { 0: id }) });
            const update = () => {
                for (const control of list.querySelectorAll('input')) control.disabled = control.checked && item.audience.userIds.length === 1
                    || !control.checked && item.audience.userIds.length >= 64;
            };
            for (const user of choices.values()) {
                const label = node('label'), control = node('input', { type: 'checkbox', 'data-blueprint-audience-user': user.id });
                control.checked = item.audience.userIds.includes(user.id);
                label.append(control, node('span', { translate: 'no' }, user.name || user.id)); list.append(label);
                listen(control, 'change', () => {
                    remember(); item.audience.userIds = [...list.querySelectorAll('input:checked')].map(input => input.dataset.blueprintAudienceUser);
                    update(); clearSimulation();
                });
            }
            update(); content.append(list);
        }
        content.append(node('p', { class: 'smart-object__hint' }, t('Recipients must have access. Camera requests also respect each person’s preference.')));
    }
    function paintSelection() {
        for (const card of nodes.children) card.classList.toggle('is-selected', selection.has(card.dataset.blueprintNode));
        drawMinimap();
    }
    // A plain click selects one card; Shift, Ctrl or Cmd adds or removes it.
    function pickCard(id, event) {
        if (event?.shiftKey || event?.ctrlKey || event?.metaKey) {
            if (!selection.delete(id)) selection.add(id);
        } else if (!selection.has(id)) { selection.clear(); selection.add(id); }
        paintSelection();
    }
    // Graph node behind a card: the door card moves the entry event node.
    function itemFor(id) {
        const current = graph();
        return id === instance.id ? current.nodes.find(item => item.type === 'event')
            : current.nodes.find(item => item.id === id);
    }
    function deletable() { return [...selection].map(itemFor).filter(item => item && item.type !== 'event').map(item => item.id); }
    function deleteNodes(ids) {
        if (!ids.length) return;
        remember();
        const value = editGraph(), removed = new Set(ids);
        value.nodes = value.nodes.filter(node => !removed.has(node.id));
        value.edges = value.edges.filter(edge => !removed.has(edge.from) && !removed.has(edge.to));
        pending = null; selection.clear(); renderGraph(); canvas.focus({ preventScroll: true });
    }
    function placeAll() {
        const current = graph();
        for (const card of nodes.children) {
            if (card.hasAttribute('data-blueprint-instance')) {
                place(card, current.nodes.find(item => item.type === 'event'), 0);
            } else {
                const item = current.nodes.find(row => row.id === card.dataset.blueprintNode);
                if (item) place(card, item, shift());
            }
        }
        scheduleEdges();
    }
    // Saved positions cannot be negative. Moving nodes past the top or left edge
    // shifts the rest of the graph instead, and the camera follows so nothing
    // jumps on screen. In exit and interaction graphs the fixed door card is not
    // part of the graph, so it is the only card that appears to move.
    function moveItems(entries) {
        const moving = new Set(entries.map(entry => entry.item));
        const others = graph().nodes.filter(item => !moving.has(item));
        const room = axis => MAX_POSITION - Math.max(0, ...others.map(item => item[axis]));
        const low = axis => Math.min(...entries.map(entry => Math.round(entry[axis])));
        const grow = { x: clamp(-low('x'), 0, room('x')), y: clamp(-low('y'), 0, room('y')) };
        for (const item of others) { item.x += grow.x; item.y += grow.y; }
        for (const entry of entries) {
            entry.item.x = clamp(Math.round(entry.x) + grow.x, 0, MAX_POSITION);
            entry.item.y = clamp(Math.round(entry.y) + grow.y, 0, MAX_POSITION);
        }
        if (grow.x || grow.y) { pan.x -= grow.x * zoom; pan.y -= grow.y * zoom; applyView(); }
        return grow;
    }
    function selectedItems(id) {
        if (!selection.has(id)) { selection.clear(); selection.add(id); paintSelection(); }
        return [...selection].map(itemFor).filter(Boolean);
    }
    // Header dragging and arrow keys move the saved event or action position.
    function movable(card, handle, id, offsetX, current) {
        let drag;
        listen(handle, 'pointerdown', event => {
            if (event.button !== 0 || event.target.closest('button')) return;
            event.preventDefault(); event.stopPropagation(); clearConnection();
            if (event.shiftKey || event.ctrlKey || event.metaKey) { pickCard(id, event); return; }
            const before = JSON.stringify(draft);
            editGraph();
            // Dragging a selected card moves the whole selection together.
            const items = selectedItems(id);
            drag = { x: event.clientX, y: event.clientY, id: event.pointerId, before,
                start: items.map(item => ({ item, x: item.x, y: item.y })) };
            handle.setPointerCapture(event.pointerId); card.classList.add('is-dragging');
        });
        listen(handle, 'pointermove', event => {
            if (!drag || drag.id !== event.pointerId) return;
            if (!drag.moved && event.clientX === drag.x && event.clientY === drag.y) return;
            drag.moved = true;
            const dx = (event.clientX - drag.x) / zoom, dy = (event.clientY - drag.y) / zoom;
            const grow = moveItems(drag.start.map(entry => ({ item: entry.item, x: entry.x + dx, y: entry.y + dy })));
            for (const entry of drag.start) { entry.x += grow.x; entry.y += grow.y; }
            if (grow.x || grow.y || drag.start.length > 1) placeAll(); else { place(card, current(), offsetX); scheduleEdges(); }
        });
        for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) listen(handle, name, event => {
            if (drag?.moved && JSON.stringify(draft) !== drag.before) remember(drag.before);
            // A click without movement narrows a group selection to this card.
            if (drag && !drag.moved && event.type === 'pointerup' && selection.size > 1) { selection.clear(); selection.add(id); paintSelection(); }
            drag = null; card.classList.remove('is-dragging');
        });
        listen(handle, 'focus', () => { if (!selection.has(id)) { selection.clear(); selection.add(id); paintSelection(); } });
        listen(handle, 'keydown', event => {
            const offsets = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
            if (['Delete', 'Backspace'].includes(event.key) && deletable().length) {
                event.preventDefault(); deleteNodes(deletable()); return;
            }
            if (!offsets[event.key] || event.ctrlKey || event.metaKey || event.altKey) return;
            event.preventDefault();
            const before = JSON.stringify(draft); editGraph();
            const step = event.shiftKey ? 50 : 10, [dx, dy] = offsets[event.key];
            moveItems(selectedItems(id).map(item => ({ item, x: item.x + dx * step, y: item.y + dy * step })));
            if (JSON.stringify(draft) !== before) remember(before);
            renderGraph();
            nodes.querySelector(`[data-blueprint-drag="${CSS.escape(id)}"]`)?.focus({ preventScroll: true });
        });
    }
    function instanceCard(eventNode) {
        const outputs = elementInstanceNode({ ...object, blueprint: draft }, kind).outputs;
        if (trigger === 'signal') outputs.push({ id: event(), ...blueprintEventMetadata(event(), kind), kind: 'execution' });
        const card = node('article', { class: 'smart-object__node smart-object__node--door',
            'data-blueprint-instance': '', 'data-blueprint-instance-id': instance.sourceId,
            'data-blueprint-node': instance.id, 'data-blueprint-type': kind, 'data-blueprint-event-source': eventNode.id });
        place(card, eventNode, 0);
        const title = node('div', { class: 'smart-object__node-heading' });
        title.append(node('span', { class: 'smart-object__node-kind' }, kindName(kind)), node('strong', { 'data-blueprint-instance-name': '', translate: 'no', title: instance.name }, instance.name));
        const content = node('div', { class: 'smart-object__node-content' });
        content.append(node('span', { 'data-blueprint-instance-state': '' }, `${t('Current state')}: ${stateName(instance.state)}`));
        const ports = node('div', { class: 'smart-object__instance-ports', role: 'group', 'aria-label': t('Events') });
        for (const port of outputs) {
            const active = event() === port.event;
            const pin = node('button', { type: 'button', 'data-blueprint-event-port': port.event,
                class: `smart-object__state-port smart-object__state-port--${port.id.replace(/[^A-Za-z0-9_-]/g, '-')}`, 'aria-pressed': String(active),
                'aria-label': portName(port.event),
                ...(active ? { 'data-blueprint-output': 'next' } : {}) });
            const label = node('span', { class: 'smart-object__port-labels' });
            label.append(node('span', { class: 'smart-object__state-label' }, portName(port.event)));
            if (port.code) label.append(node('code', { class: 'smart-object__event-code', translate: 'no' }, port.code));
            pin.append(label, dot({ 'data-blueprint-state-dot': '' }));
            listen(pin, 'click', click => {
                clearConnection();
                const activate = event() !== port.event; chooseEvent(port.event);
                pending = activate ? null : { id: graph().nodes.find(item => item.type === 'event').id, output: 'next' };
                renderSettings(); renderGraph();
                if (activate) fitView();
                if (click.detail === 0) chooseFromKeyboard(eventSource());
            });
            ports.append(pin);
        }
        card.append(title, content, ports);
        title.setAttribute('data-blueprint-drag', instance.id); title.tabIndex = 0;
        title.setAttribute('aria-label', t('Move node'));
        movable(card, title, instance.id, 0, () => graph().nodes.find(item => item.type === 'event'));
        if (selection.has(instance.id)) card.classList.add('is-selected');
        return card;
    }
    function nodeCard(item) {
        const card = node('article', { class: `smart-object__node smart-object__node--${item.type}`, 'data-blueprint-node': item.id, 'data-blueprint-type': item.type });
        place(card, item, shift());
        if (selection.has(item.id)) card.classList.add('is-selected');
        const title = node('div', { class: 'smart-object__node-heading', 'data-blueprint-drag': item.id, tabindex: '0', 'aria-label': t('Move node') });
        title.append(node('strong', {}, item.type === 'event' ? eventName() : typeName(item.type)));
        if (item.type !== 'event') {
            const remove = button('×', { 'data-blueprint-delete': item.id, 'aria-label': t('Delete node'), class: 'smart-object__node-delete' });
            listen(remove, 'pointerdown', event => event.stopPropagation());
            listen(remove, 'click', () => deleteNodes([item.id])); title.append(remove);
        }
        // Inputs on the left, outputs on the right; value ports carry their type for color and matching.
        const contract = blueprintContract.nodes[item.type], sockets = node('div', { class: 'smart-object__sockets' });
        const inputs = node('div', { class: 'smart-object__inputs' }), outputs = node('div', { class: 'smart-object__outputs' });
        if (contract.inputs.some(port => port.kind === 'execution')) {
            const input = node('button', { type: 'button', 'data-blueprint-input': item.id, class: 'smart-object__socket smart-object__socket--input' });
            input.append(dot(), node('span', {}, t('Input')));
            listen(input, 'click', () => connect(item.id)); inputs.append(input);
        }
        const linked = port => graph().edges.some(edge => edge.kind === 'data' && edge.to === item.id && edge.input === port);
        for (const port of dataInputs(item).filter(port => !(item.type === 'emitEvent' && item.scope === 'scene' && port.id === 'target'))) {
            const input = node('button', { type: 'button', 'data-blueprint-data-input': port.id, 'data-port-type': port.type,
                class: 'smart-object__socket smart-object__socket--input smart-object__socket--data',
                'aria-label': `${t(port.label)} · ${t(typeNames[port.type])}`,
                title: t('Click to choose a value node, or drag to a compatible output.'),
                'aria-pressed': String(pending?.reverse === true && pending.id === item.id && pending.input === port.id) });
            input.append(dot(), node('span', {}, t(port.label)));
            listen(input, 'click', () => {
                if (pending && !pending.reverse) connect(item.id, port.id);
                else chooseForInput(pinTarget(input));
            }); inputs.append(input);
        }
        const pinPressed = (output, data) => String(pending?.id === item.id && pending.output === output && !!pending.data === data);
        for (const port of executionOutputs(item)) {
            const pin = node('button', { type: 'button', 'data-blueprint-output': port.id, class: `smart-object__socket smart-object__socket--output smart-object__socket--${port.id}`,
                'aria-pressed': pinPressed(port.id, false), ...(item.type === 'sequence' ? { 'aria-label': `${typeName('sequence')} ${port.label}` } : {}) });
            pin.append(node('span', {}, ['switch', 'random'].includes(item.type) ? choiceName(item.type, port.id) : portLabel(port)), dot());
            outputs.append(pin);
        }
        for (const port of dataOutputs(item)) {
            const pin = node('button', { type: 'button', 'data-blueprint-data-output': port.id, 'data-port-type': port.type,
                class: 'smart-object__socket smart-object__socket--output smart-object__socket--data', 'aria-pressed': pinPressed(port.id, true),
                'aria-label': `${t(port.label)} · ${t(typeNames[port.type])}` });
            pin.append(node('span', {}, t(port.label)), dot());
            outputs.append(pin);
        }
        for (const pin of outputs.children) listen(pin, 'click', click => {
            const source = pinSource(pin);
            if (connectOutput(source)) return;
            pending = pendingFrom(source); renderGraph();
            if (click.detail === 0) chooseFromKeyboard(source);
        });
        sockets.append(inputs, outputs);
        const content = node('div', { class: 'smart-object__node-content' });
        if (item.type === 'event') {
            const label = node('span', { class: 'smart-object__event-state' });
            label.append(dot({ class: `smart-object__state-mark smart-object__state-mark--${state}` }), node('span', {}, stateName(state)));
            content.append(label);
        }
        if (item.type === 'light') content.append(parameter(item, 'Light', 'targetId', lights.map((light, index) => [light.id, light.name || `${t('Light')} ${index + 1} (${light.x}, ${light.y})`])),
            pickButton(item, 'lights', 'targetId'), parameter(item, 'Enabled', 'enabled', [['true', t('Enabled')], ['false', t('Disabled')]]));
        if (item.type === 'flame') content.append(parameter(item, 'Flame', 'enabled', [['true', t('Lit')], ['false', t('Extinguished')]]));
        if (item.type === 'sound') {
            content.append(parameter(item, 'Sound', 'trackId', sounds.map(sound => [sound.id, sound.name])));
            const volume = node('input', { type: 'number', min: '0', max: '1', step: '.001', value: item.volume, 'data-blueprint-param': 'volume', inputmode: 'decimal' });
            listen(volume, 'change', () => {
                const value = Number(volume.value);
                if (!volume.checkValidity() || value === item.volume) return;
                remember(); item.volume = value; clearSimulation();
            });
            content.append(field('Volume', volume));
        }
        const states = blueprintAllStates.map(value => [value, stateName(value)]);
        if (item.type === 'state') {
            const targetEdge = graph().edges.find(edge => edge.kind === 'data' && edge.to === item.id && edge.input === 'target');
            const reference = targetEdge && graph().nodes.find(node => node.id === targetEdge.from);
            const target = reference && otherElements.find(element => element.id === reference.targetId);
            const targetKind = target?.kind || (target?.torch ? 'torch' : target?.lever ? 'lever' : target ? 'door' : kind);
            const accepted = !targetEdge ? kind === 'region' ? blueprintStatesFor('door') : ownStates
                : target ? ['door', 'lever', 'torch'].includes(targetKind) ? blueprintStatesFor(targetKind) : [] : blueprintWritableStates;
            const choices = accepted.includes(item.targetState) ? accepted : [...accepted, item.targetState];
            // Players may lock or unlock only when the GM explicitly allows it on this action.
            const players = node('select', { 'data-blueprint-param': 'players' });
            options(players, [['false', t('GM rules only')], ['true', t('Players may lock or unlock')]], String(item.players === true));
            listen(players, 'change', () => {
                const value = players.value === 'true';
                if ((item.players === true) === value) return;
                remember(); if (value) item.players = true; else delete item.players; clearSimulation();
            });
            const stateField = parameter(item, 'State', 'targetState', choices.map(value => [value, stateName(value, targetKind)]));
            stateField.querySelector('select').addEventListener('change', () => renderGraph(), { signal });
            content.append(stateField);
            if (!accepted.includes(item.targetState)) content.append(node('p', { class: 'smart-object__hint smart-object__hint--warning' }, t('Choose a state supported by the target element.')));
            if (!targetEdge && kind === 'region') content.append(node('p', { class: 'smart-object__hint' }, t('Connect an Element reference to Target. Region occupancy is determined by tokens.')));
            if (!['off', 'on'].includes(item.targetState)) content.append(field('Locks', players));
            if (targetEdge) content.append(node('p', { class: 'smart-object__hint' },
                t('Changes only the state. Use Interact with object to run the target\'s interaction behavior.')));
        }
        if (item.type === 'interact') content.append(node('p', { class: 'smart-object__hint' },
            t('Explicitly starts On interaction on the target. Its connected actions decide the result.')));
        if (item.type === 'barrier') {
            const channel = parameter(item, 'Blocks', 'channel', ['movement', 'vision', 'light', 'sound'].map(value => [value, channelName(value)]));
            const modes = item.channel === 'sound' ? ['block', 'pass', 'attenuate'] : ['block', 'pass'];
            channel.querySelector('select').addEventListener('change', () => {
                if (item.channel !== 'sound' && item.mode === 'attenuate') item.mode = 'block';
                renderGraph();
            }, { signal });
            content.append(channel, parameter(item, 'Mode', 'mode', modes.map(value => [value, modeName(value)])));
        }
        if (item.type === 'soundControl') {
            const action = parameter(item, 'Action', 'action', [['stop', t('Stop')], ['volume', t('Change volume')]]);
            action.querySelector('select').addEventListener('change', () => renderGraph(), { signal });
            content.append(parameter(item, 'Sound', 'trackId', sounds.map(sound => [sound.id, sound.name])), action);
            if (item.action === 'volume') {
                const volume = node('input', { type: 'number', min: '0', max: '1', step: '.001', value: item.volume, 'data-blueprint-param': 'volume', inputmode: 'decimal' });
                listen(volume, 'change', () => {
                    const value = Number(volume.value);
                    if (!volume.checkValidity() || value === item.volume) return;
                    remember(); item.volume = value; clearSimulation();
                });
                content.append(field('Volume', volume));
            }
        }
        if (item.type === 'condition') {
            const control = parameter(item, 'State', 'state', ownStates.map(value => [value, stateName(value)]));
            if (linked('test')) {
                // A connected Test input decides the branch; the state stays saved for when it is removed.
                control.querySelector('select').disabled = true;
                content.append(control, node('p', { class: 'smart-object__hint' }, t('Uses the Test input.')));
            } else content.append(control);
        }
        if (item.type === 'compare') content.append(parameter(item, 'Equals', 'state', states),
            ...(linked('value') ? [] : [node('p', { class: 'smart-object__hint' }, t('Without an input, compares the current state.'))]));
        if (['counter', 'cooldown', 'delay'].includes(item.type)) {
            const counter = item.type === 'counter', key = counter ? 'target' : 'seconds';
            const control = node('input', { type: 'number', min: counter ? '1' : '.1', max: counter ? '1000000' : '86400',
                step: counter ? '1' : 'any', required: '', value: item[key], 'data-blueprint-param': key, inputmode: counter ? 'numeric' : 'decimal' });
            listen(control, 'change', () => {
                if (!control.reportValidity() || Number(control.value) === item[key]) return;
                remember(); item[key] = Number(control.value); clearSimulation();
            });
            content.append(field(counter ? 'Activation target' : item.type === 'delay' ? 'Wait seconds' : 'Cooldown seconds', control), node('p', { class: 'smart-object__hint' },
                t(counter ? 'Each visit counts once. Reached stays active after the target is met.'
                    : item.type === 'delay' ? 'Pauses the rest of this event. Other elements can keep running.'
                        : 'Blocked attempts do not restart the cooldown.')));
        }
        if (item.type === 'once') content.append(node('p', { class: 'smart-object__hint' }, t('Place this before effects that must run only once. The GM can reset it in Automation.')));
        if (item.type === 'timer') {
            const name = nameParameter(item), mode = node('select', { 'data-blueprint-param': 'action' });
            options(mode, timerActions.map(value => [value, timerActionName(value)]), item.action);
            listen(mode, 'change', () => {
                if (mode.value === item.action) return;
                remember(); item.action = mode.value;
                if (item.action === 'stop') delete item.seconds; else item.seconds ??= 3;
                renderGraph();
                nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-param=action]`)?.focus({ preventScroll: true });
            });
            content.append(name, field('Action', mode));
            if (item.action !== 'stop') {
                const duration = node('input', { type: 'number', min: '.1', max: '86400', step: 'any', required: '',
                    value: item.seconds, 'data-blueprint-param': 'seconds', inputmode: 'decimal' });
                listen(duration, 'change', () => {
                    if (!duration.reportValidity() || Number(duration.value) === item.seconds) return;
                    remember(); item.seconds = Number(duration.value); clearSimulation();
                });
                content.append(field('Timer seconds', duration));
            }
            const hint = node('p', { class: 'smart-object__hint', 'data-blueprint-timer-event': '' });
            const renderHint = () => {
                hint.replaceChildren(`${t('On signal')}: `, node('span', { translate: 'no' }, item.name));
                if (!draft.graphs[`signal:${item.name}`] && item.action !== 'stop') hint.append(` · ${t('Add a matching signal graph to run actions when this timer expires.')}`);
            };
            listen(name.querySelector('input'), 'change', renderHint); renderHint();
            content.append(hint, node('p', { class: 'smart-object__hint' },
                t('Next runs immediately. Start keeps an active timer; Restart replaces it.')));
        }
        if (item.type === 'switch') {
            const fallback = scalarParameter(item, 'Default value', 'value');
            if (linked('value')) fallback.querySelector('input, select').disabled = true;
            content.append(typedParameter(item), fallback);
            if (linked('value')) content.append(node('p', { class: 'smart-object__hint' }, t('Uses the Value input.')));
            const caseControls = new Map();
            const validateCases = () => {
                const rows = item.cases.map(entry => {
                    const control = caseControls.get(entry.id);
                    return { entry, control, value: item.valueType === 'boolean' ? control.value === 'true'
                        : item.valueType === 'number' ? control.valueAsNumber : control.value };
                });
                for (const row of rows) {
                    row.message = item.valueType === 'text' && Array.from(row.value).length > 256 ? t('Invalid blueprint variable value.')
                        : rows.some(other => other !== row && other.value === row.value) ? t('Each case must have a different value.') : '';
                    row.control.setCustomValidity(row.message);
                }
                return rows;
            };
            for (const entry of item.cases) {
                const row = node('div', { class: 'smart-object__choice-row', 'data-blueprint-case': entry.id });
                const value = scalarControl(item.valueType, entry.value, 'caseValue', () => {
                    const rows = validateCases();
                    if (rows.some(row => !row.control.checkValidity()) || rows.every(row => row.entry.value === row.value)) return;
                    // A duplicate can become valid when a sibling changes. Commit
                    // the visible valid group together, including that pending edit.
                    remember();
                    for (const row of rows) row.entry.value = row.value;
                    clearSimulation();
                }, () => validateCases().find(row => row.entry.id === entry.id).message);
                caseControls.set(entry.id, value);
                listen(value, 'input', validateCases);
                const remove = node('button', { type: 'button', class: 'smart-object__choice-remove', 'data-blueprint-remove-case': entry.id,
                    'aria-label': `${t('Remove case')}: ${choiceName(item.type, entry.id)}`, ...(item.cases.length === 1 ? { disabled: '' } : {}) }, '×');
                listen(remove, 'click', () => {
                    remember(); item.cases = item.cases.filter(other => other.id !== entry.id);
                    editGraph().edges = graph().edges.filter(edge => edge.from !== item.id || edge.kind === 'data' || edge.output !== entry.id);
                    pending = null; renderGraph();
                    nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-add-case]`)?.focus({ preventScroll: true });
                });
                row.append(field(choiceName(item.type, entry.id), value), remove); content.append(row);
            }
            const full = item.cases.length >= (item.valueType === 'boolean' ? 2 : switchCaseIds.length);
            const add = node('button', { type: 'button', 'data-blueprint-add-case': '', ...(full ? { disabled: '' } : {}) }, t('Add case'));
            listen(add, 'click', () => {
                const id = switchCaseIds.find(id => !item.cases.some(row => row.id === id));
                if (!id || full) return;
                let value = false;
                if (item.valueType === 'boolean') value = !item.cases.some(row => row.value === false) ? false : true;
                else {
                    let index = 1;
                    while (item.cases.some(row => row.value === (item.valueType === 'number' ? index : String(index)))) index++;
                    value = item.valueType === 'number' ? index : String(index);
                }
                remember(); item.cases.push({ id, value }); renderGraph();
                nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-case="${id}"] [data-blueprint-param=caseValue]`)?.focus({ preventScroll: true });
            });
            content.append(add, node('p', { class: 'smart-object__hint' }, t('One matching case runs. Default runs when no case matches.')));
        }
        if (item.type === 'random') {
            const total = item.weights.reduce((sum, weight) => sum + weight, 0);
            item.weights.forEach((weight, index) => {
                const id = randomBranchIds[index], row = node('div', { class: 'smart-object__choice-row', 'data-blueprint-branch': id });
                const control = node('input', { type: 'number', min: '0', max: '1000', step: '1', required: '', value: weight,
                    'data-blueprint-param': 'weight', inputmode: 'numeric' });
                listen(control, 'change', () => {
                    const value = Number(control.value);
                    control.setCustomValidity(total - weight + value > 0 ? '' : t('At least one branch must have a positive weight.'));
                    if (!control.reportValidity() || value === weight) return;
                    remember(); item.weights[index] = value; renderGraph();
                    nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-branch="${id}"] input`)?.focus({ preventScroll: true });
                });
                row.append(field(`${choiceName(item.type, id)} · ${t('{0}% chance', { 0: Math.round(weight / total * 1000) / 10 })}`, control));
                if (index === item.weights.length - 1) {
                    const remove = node('button', { type: 'button', class: 'smart-object__choice-remove', 'data-blueprint-remove-branch': id,
                        'aria-label': `${t('Remove branch')}: ${choiceName(item.type, id)}`,
                        ...(item.weights.length <= 2 || total === weight ? { disabled: '' } : {}) }, '×');
                    listen(remove, 'click', () => {
                        remember(); item.weights.pop();
                        editGraph().edges = graph().edges.filter(edge => edge.from !== item.id || edge.kind === 'data' || edge.output !== id);
                        pending = null; renderGraph();
                        nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-add-branch]`)?.focus({ preventScroll: true });
                    });
                    row.append(remove);
                }
                content.append(row);
            });
            const add = node('button', { type: 'button', 'data-blueprint-add-branch': '', ...(item.weights.length === randomBranchIds.length ? { disabled: '' } : {}) }, t('Add branch'));
            listen(add, 'click', () => {
                if (item.weights.length >= randomBranchIds.length) return;
                remember(); item.weights.push(1); renderGraph();
                nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-branch="${randomBranchIds[item.weights.length - 1]}"] input`)?.focus({ preventScroll: true });
            });
            content.append(add, node('p', { class: 'smart-object__hint' }, t('Weights are whole numbers from 0 to 1000. Zero disables a branch.')),
                node('p', { class: 'smart-object__hint' }, t('An unconnected chosen branch ends this path without drawing again.')));
        }
        if (item.type === 'elementGroup') groupFields(item, content);
        if (item.type === 'eventContext') {
            const property = node('select', { 'data-blueprint-param': 'property' });
            options(property, eventContextProperties.map(value => [value, contextName(value)]), item.property);
            listen(property, 'change', () => {
                if (property.value === item.property) return;
                remember(); item.property = property.value; pruneDataConnections(); pending = null; renderGraph();
                nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-param=property]`)?.focus({ preventScroll: true });
            });
            content.append(field('Context field', property), node('p', { class: 'smart-object__hint' },
                t('The server supplies the original user and token. Event and state describe the graph currently running.')));
        }
        if (item.type === 'move' || item.type === 'rotate') {
            for (const [key, label, bound] of item.type === 'move' ? [['dx', 'Offset X (cells)', 1000], ['dy', 'Offset Y (cells)', 1000]] : [['degrees', 'Angle (degrees)', 36000]]) {
                const control = node('input', { type: 'number', min: -bound, max: bound, step: 'any', required: '', value: item[key],
                    'data-blueprint-param': key, inputmode: 'decimal' });
                listen(control, 'change', () => {
                    if (!control.reportValidity() || Number(control.value) === item[key]) return;
                    remember(); item[key] = Number(control.value); clearSimulation();
                }); content.append(field(label, control));
            }
            content.append(node('p', { class: 'smart-object__hint' }, t(item.type === 'move'
                ? 'Moves live objects relative to their current position. One cell follows the scene grid.'
                : 'Each target rotates around its center. Regions use multiples of 90 degrees.')),
            node('p', { class: 'smart-object__hint' }, t('Generating or updating from the project restores authored positions.')));
        }
        if (item.type === 'setInteraction') content.append(parameter(item, 'Player interaction', 'enabled', [['true', t('Enabled')], ['false', t('Disabled')]]),
            node('p', { class: 'smart-object__hint' }, t('The GM can still operate and edit. Signals and scheduled events keep running.')));
        if (item.type === 'setRegion') content.append(parameter(item, 'Presence triggers enabled', 'enabled', [['true', t('Enabled')], ['false', t('Disabled')]]),
            node('p', { class: 'smart-object__hint' }, t('Updates occupancy silently. Existing signals, waits and timers keep running.')));
        if (item.type === 'setVisibility') content.append(parameter(item, 'Artwork', 'visible', [['true', t('Visible')], ['false', t('Hidden')]]),
            node('p', { class: 'smart-object__hint' }, t('Hiding artwork does not change movement, vision, light or sound barriers.')));
        if (item.type === 'setAppearance') {
            const choices = materials.map(asset => [asset.id, asset.name]);
            if (!materials.some(asset => asset.id === item.assetId)) choices.unshift([item.assetId, t('Missing image')]);
            content.append(parameter(item, 'Material or image', 'assetId', choices),
                node('p', { class: 'smart-object__hint' }, t('Dynamic surfaces keep their original mask and texture scale.')));
            if (emptyObject) content.append(node('p', { class: 'smart-object__hint' }, t('Empty Objects cannot receive images. Connect another object to Target.')));
        }
        if (item.type === 'showMessage') {
            const text = node('textarea', { rows: '4', maxlength: '4000', required: '', translate: 'no', 'data-blueprint-param': 'text' });
            text.value = item.text;
            const validate = () => text.setCustomValidity(text.value.trim() && !text.value.includes('\0') && Array.from(text.value).length <= 2000 ? '' : t('Use a message with 1 to 2000 characters.'));
            listen(text, 'input', validate);
            listen(text, 'change', () => {
                validate(); if (!text.reportValidity() || text.value === item.text) return;
                remember(); item.text = text.value; clearSimulation();
            }); content.append(field('Message', text));
        }
        if (item.type === 'showHandout') {
            const choices = handouts.map(handout => [handout.id, handout.name]);
            if (!handouts.some(handout => handout.id === item.journalId)) choices.unshift([item.journalId, t('Missing handout')]);
            content.append(parameter(item, 'Handout', 'journalId', choices),
                node('p', { class: 'smart-object__hint' }, t('Opening a handout never grants new reading permissions.')));
        }
        if (item.type === 'cameraFocus') for (const [key, label] of [['focusX', 'Focus X (cells)'], ['focusY', 'Focus Y (cells)']]) {
            const control = node('input', { type: 'number', min: '0', max: '1000', step: 'any', required: '', 'data-blueprint-param': key, value: item[key] });
            listen(control, 'change', () => {
                if (!control.reportValidity() || Number(control.value) === item[key]) return;
                remember(); item[key] = Number(control.value); clearSimulation();
            }); content.append(field(label, control));
        }
        if (['showMessage', 'showHandout', 'cameraFocus'].includes(item.type)) audienceFields(item, content);
        if (item.type === 'teleport') {
            const regions = [object, ...otherElements].filter(element => element.kind === 'region');
            const choices = regions.map(region => [region.id, region.name]);
            if (!regions.some(region => region.id === item.destinationId)) choices.unshift([item.destinationId, t('Missing region')]);
            content.append(parameter(item, 'Destination region', 'destinationId', choices),
                node('p', { class: 'smart-object__hint' }, t('Uses the token from the original presence event. Arrival needs a free place in this scene.')));
        }
        if (['lightReference', 'soundReference'].includes(item.type)) {
            const light = item.type === 'lightReference', rows = light ? groupMembers('light') : sounds, key = light ? 'targetId' : 'trackId';
            const missing = !rows.some(row => row.id === item[key]);
            const choices = rows.map(row => [row.id, row.name]);
            if (missing) choices.unshift([item[key], t('Missing target')]);
            content.append(parameter(item, light ? 'Light' : 'Sound', key, choices));
            if (light) content.append(pickButton(item, 'lights', key));
            if (missing) content.append(node('p', { class: 'smart-object__hint smart-object__hint--warning' }, t('This target no longer exists; actions using it are skipped.')));
        }
        if (['getVariable', 'setVariable'].includes(item.type)) {
            content.append(scopeParameter(item), nameParameter(item), typedParameter(item));
            const constant = scalarParameter(item, item.type === 'getVariable' ? 'Default value' : 'Value', item.type === 'getVariable' ? 'default' : 'value');
            if (item.type === 'setVariable' && linked('value')) {
                constant.querySelector('input, select').disabled = true;
                content.append(constant, node('p', { class: 'smart-object__hint' }, t('Uses the Value input.')));
            } else content.append(constant);
        }
        if (item.type === 'compareValue') content.append(typedParameter(item),
            parameter(item, 'Operator', 'operator', variableOperators.filter(value => item.valueType === 'number' || ['eq', 'ne'].includes(value)).map(value => [value, operatorName(value)])),
            scalarParameter(item, 'Compare to', 'expected'));
        if (item.type === 'emitEvent') content.append(scopeParameter(item), nameParameter(item),
            node('p', { class: 'smart-object__hint' }, t(item.scope === 'scene' ? 'Notify every element listening for this signal in the scene.'
                : linked('target') ? 'Notify the element connected to Target.' : 'Target: this element.')));
        if (['all', 'any'].includes(item.type)) {
            const count = dataInputs(item).filter(port => linked(port.id)).length;
            content.append(node('p', { class: 'smart-object__hint', 'data-blueprint-condition-count': '' }, t('{count} conditions connected', { count })),
                node('p', { class: `smart-object__hint${count < 2 ? ' smart-object__hint--warning' : ''}` },
                    t('Connect at least two conditions. Unconnected inputs are ignored.')));
        }
        if (item.type === 'property') content.append(parameter(item, 'Property', 'property',
            [['state', t('Current state')], ['previous', t('Previous state')]]),
            ...(linked('target') ? [node('p', { class: 'smart-object__hint' }, t('Reads the referenced element; both properties give its current state.'))] : []));
        if (item.type === 'reference') {
            const known = elementName(item.targetId), rows = otherElements.map(row => [row.id, row.name]);
            if (!known) rows.unshift([item.targetId, t('Missing element')]);
            content.append(parameter(item, 'Element', 'targetId', rows), pickButton(item, 'elements', 'targetId'));
            if (!known) { card.classList.add('is-missing'); content.append(node('p', { class: 'smart-object__hint smart-object__hint--warning' }, t('This element no longer exists; actions using it are skipped.'))); }
        }
        if (['light', 'sound', 'soundControl'].includes(item.type) && linked('target')) {
            const fallback = content.querySelector(`[data-blueprint-param="${item.type === 'light' ? 'targetId' : 'trackId'}"]`);
            if (fallback) fallback.disabled = true;
            for (const pick of content.querySelectorAll('[data-blueprint-pick-map]')) pick.disabled = true;
            content.append(node('p', { class: 'smart-object__hint' }, t('Uses the connected Target. Missing references are skipped without using the fallback.')));
        }
        if (['state', 'sprite', 'reveal', 'barrier', 'flame', 'move', 'rotate', 'setInteraction', 'setRegion', 'setVisibility', 'setAppearance'].includes(item.type) && !linked('target'))
            content.append(node('p', { class: 'smart-object__hint' }, t('Target: this element.')));
        if (kind !== 'door' && ['reveal', 'barrier'].includes(item.type) && !linked('target')) content.append(node('p', { class: 'smart-object__hint' }, t('Connect a door to Target; this action applies to doors.')));
        if (kind !== 'torch' && item.type === 'flame' && !linked('target')) content.append(node('p', { class: 'smart-object__hint' }, t('Connect a torch to Target; this action applies to torches.')));
        if (item.type === 'sprite') {
            const mode = node('select', { 'data-blueprint-param': 'appearance' });
            options(mode, ['inherit', 'hidden', 'asset'].map(value => [value, appearanceName(value)]), item.appearance);
            mode.querySelector('option[value=asset]').disabled = !spriteAssets.length && item.appearance !== 'asset';
            listen(mode, 'change', () => {
                if (mode.value === item.appearance) return;
                remember(); item.appearance = mode.value;
                if (mode.value === 'asset') item.assetId ||= spriteAssets[0]?.id; else delete item.assetId;
                renderGraph(); nodes.querySelector(`[data-blueprint-node="${CSS.escape(item.id)}"] [data-blueprint-param=appearance]`)?.focus({ preventScroll: true });
            });
            content.append(field('Appearance', mode));
            if (item.appearance === 'asset') content.append(parameter(item, 'Image', 'assetId', spriteAssets.map(row => [row.id, row.name])));
            if ((emptyObject || kind === 'region') && !linked('target')) content.append(node('p', { class: 'smart-object__hint' },
                t('Connect an object with artwork to Target; this element cannot receive images.')));
        }
        card.append(title, sockets, content);
        listen(card, 'pointerdown', event => { if (!event.target.closest('[data-blueprint-drag]')) pickCard(item.id, event); });
        movable(card, title, item.id, shift(), () => graph().nodes.find(node => node.id === item.id));
        return card;
    }
    function renderGraph() {
        const focused = document.activeElement, focusedCard = renderedEvent === event() ? focused?.closest('[data-blueprint-node]') : null;
        renderedEvent = event();
        const focusAttribute = focusedCard && ['data-blueprint-event-port', 'data-blueprint-output', 'data-blueprint-input', 'data-blueprint-data-output',
            'data-blueprint-data-input', 'data-blueprint-drag', 'data-blueprint-delete']
            .find(attribute => focused.hasAttribute(attribute));
        const focusSelector = focusAttribute && `[data-blueprint-node="${CSS.escape(focusedCard.dataset.blueprintNode)}"] [${focusAttribute}="${CSS.escape(focused.getAttribute(focusAttribute))}"]`;
        clearSimulation(); nodes.replaceChildren(); updateGuide();
        const current = graph();
        nodes.append(instanceCard(current.nodes.find(item => item.type === 'event')));
        for (const item of current.nodes) if (item.type !== 'event') nodes.append(nodeCard(item));
        settleChoiceNeighbors();
        renderRail(); renderHistory(); renderSimulationVariables(); renderSimulationGates(); renderSimulationContext(); scheduleEdges();
        if (focusSelector) (nodes.querySelector(focusSelector) || canvas).focus({ preventScroll: true });
    }

    listen(appearance, 'change', () => {
        remember();
        draft.states[appearanceState] = { appearance: appearance.value };
        if (appearance.value === 'asset' && assets[0]) draft.states[appearanceState].assetId = assets[0].id;
        renderSettings(); clearSimulation();
    });
    listen(asset, 'change', () => { remember(); draft.states[appearanceState].assetId = asset.value; renderPreview(); clearSimulation(); });
    listen(appearanceStateSelect, 'change', () => { appearanceState = appearanceStateSelect.value; renderSettings(); });
    listen(previewState, 'change', () => { state = previewState.value; renderSettings(); renderGraph(); });
    listen(add, 'click', () => {
        clearConnection(); pending = null;
        const rect = add.getBoundingClientRect();
        openPicker({ source: null, clientX: rect.left, clientY: rect.bottom + 4, returnFocus: add },
            { position: nextPosition(draft.graphs[event()] || eventGraph(event())) });
    });
    listen(simulate, 'click', () => {
        try {
            validateBlueprint(draft, { assets, materials, lights, sounds, element: object }); clearSimulation();
            const previous = state;
            const states = Object.fromEntries(otherElements.map(row => [row.id, row.state]));
            const now = Date.now(), current = graph(), result = simulateGraph({ ...draft, graphs: { ...draft.graphs, [event()]: current } }, event(), state, previous, states,
                { variables: simulationMemory, memory: previewMemory(now), eventContext: simulationContext, now });
            const executed = new Set(result.trace), byId = new Map(current.nodes.map(item => [item.id, item]));
            for (const id of result.trace) sourceElement(id)?.classList.add('is-executed');
            const testOf = id => current.edges.find(edge => edge.kind === 'data' && edge.to === id && edge.input === 'test')?.from;
            for (const edge of current.edges) {
                const from = byId.get(edge.from);
                // Highlight a condition's taken branch only; other edges between executed nodes ran.
                const taken = edge.kind === 'data' || ([...controlNodeTypes, 'switch', 'random'].includes(from?.type)
                    ? edge.output === String(result.decisions[from.id])
                    : from?.type !== 'condition' || edge.output === String(testOf(from.id) ? result.values[testOf(from.id)] : from.state === state));
                if (executed.has(edge.from) && executed.has(edge.to) && taken)
                    wires.querySelector(`[data-blueprint-edge="${CSS.escape(edgeKey(edge))}"]`)?.classList.add('is-executed');
            }
            traceHint.hidden = true;
            trace.append(node('li', {}, `${eventName()}: ${stateName(state)}`));
            const actions = new Map(result.actions.map(action => [action.id, action]));
            for (const id of result.trace) {
                const action = actions.get(id), item = byId.get(id);
                if (action) {
                    const detail = action.type === 'sound' ? targetName(action.target ?? action.trackId)
                        : action.type === 'light' ? `${targetName(action.target ?? action.targetId)} · ${t(action.enabled ? 'Enabled' : 'Disabled')}`
                        : action.type === 'flame' ? t(action.enabled ? 'Lit' : 'Extinguished') + (action.target ? ` · ${targetName(action.target)}` : '')
                        : action.type === 'sprite' ? (action.appearance === 'asset' ? spriteAssets.find(row => row.id === action.assetId)?.name : appearanceName(action.appearance))
                        : action.type === 'reveal' ? (action.target ? targetName(action.target) : t('This element'))
                        : action.type === 'barrier' ? `${channelName(action.channel)}: ${modeName(action.mode)}` + (action.target ? ` · ${targetName(action.target)}` : '')
                        : action.type === 'soundControl' ? `${targetName(action.target ?? action.trackId)} · ${action.action === 'stop' ? t('Stop') : `${Math.round(action.volume * 100)}%`}`
                        : action.type === 'move' ? `${action.dx}, ${action.dy} · ${t('Cells')} · ${action.target ? targetName(action.target) : t('This element')}`
                        : action.type === 'rotate' ? `${action.degrees}° · ${action.target ? targetName(action.target) : t('This element')}`
                        : ['setInteraction', 'setRegion'].includes(action.type) ? `${t(action.enabled ? 'Enabled' : 'Disabled')} · ${action.target ? targetName(action.target) : t('This element')}`
                        : action.type === 'setVisibility' ? t(action.visible ? 'Visible' : 'Hidden')
                        : action.type === 'setAppearance' ? materials.find(row => row.id === action.assetId)?.name || t('Missing image')
                        : action.type === 'showMessage' ? action.text
                        : action.type === 'showHandout' ? handouts.find(row => row.id === action.journalId)?.name || t('Missing handout')
                        : action.type === 'cameraFocus' ? `${action.focusX}, ${action.focusY} · ${t('Cells')}`
                        : action.type === 'teleport' ? targetName(action.destinationId)
                        : action.type === 'interact' ? `${t('On interaction')} · ${action.target ? targetName(action.target) : t('This element')}`
                        : action.type === 'setVariable' ? `${scopeName(action.scope)} · ${action.name} = ${scalarText(action.value)}`
                        : action.type === 'emitEvent' ? `${action.name} · ${action.scope === 'scene' ? scopeName('scene') : action.target ? targetName(action.target) : t('This element')}`
                        : action.type === 'timer' ? `${timerActionName(action.action)} · ${action.name}` + (action.action === 'stop' ? '' : ` · ${t('Wait {0} seconds', { 0: action.seconds })}`)
                        : stateName(action.targetState) + (action.target ? ` · ${targetName(action.target)}` : '');
                    trace.append(node('li', { 'data-blueprint-trace-node': action.id }, `${typeName(action.type)}: ${detail}`));
                } else if (['switch', 'random'].includes(item.type)) {
                    const output = result.decisions[id];
                    const source = current.edges.find(edge => edge.kind === 'data' && edge.to === id && edge.input === 'value')?.from;
                    const detail = choiceName(item.type, output) + (item.type === 'switch' ? ` · ${scalarText(source ? result.values[source] : item.value)}` : '');
                    trace.append(node('li', { 'data-blueprint-trace-node': id, 'data-blueprint-trace-choice': output }, `${typeName(item.type)}: ${detail}`));
                } else if (item.type === 'delay') {
                    trace.append(node('li', { 'data-blueprint-trace-node': id, 'data-blueprint-trace-delay': '' },
                        `${typeName(item.type)}: ${t('Wait {0} seconds', { 0: item.seconds })}`));
                } else if (controlNodeTypes.includes(item.type)) {
                    const entry = result.memory?.[event()]?.[id], passed = result.decisions[id];
                    const detail = item.type === 'counter' ? `${entry.value} / ${item.target} · ${t(passed ? 'Reached' : 'Below target')}`
                        : item.type === 'once' ? t(passed ? 'First time' : 'Already used') : t(passed ? 'Ready' : 'Cooling down');
                    trace.append(node('li', { 'data-blueprint-trace-node': id, 'data-blueprint-trace-control': item.type }, `${typeName(item.type)}: ${detail}`));
                } else if (isPureNode(item)) {
                    const value = result.values[id];
                    trace.append(node('li', { 'data-blueprint-trace-value': id, class: 'smart-object__trace-value' },
                        `${typeName(item.type)}: ${typeof value === 'boolean' ? t(value ? 'True' : 'False')
                            : ['getVariable', 'eventContext'].includes(item.type) ? scalarText(value)
                            : ['reference', 'elementGroup', 'lightReference', 'soundReference'].includes(item.type) ? targetName(value)
                            : value ? stateName(value) : t('Missing element')}`));
                }
            }
            guide.textContent = t('Simulation only. The scene has not changed.');
            if (result.delay) trace.append(node('li', { class: 'smart-object__hint' },
                t('Simulation stops at this wait. The server resumes the event when it is due.')));
            if (result.actions.some(action => action.type === 'timer')) trace.append(node('li', { class: 'smart-object__hint' },
                t('Timer actions are previewed only. No timer or expiry event runs in this simulation.')));
            if (event() === 'destroy' && (result.delay || result.actions.some(action => action.type === 'timer'))) trace.append(node('li', { class: 'smart-object__hint' },
                t('Timers and waits owned by a destroyed element are cancelled. Send a signal to another element for actions that must continue later.')));
            if (result.trace.some(id => byId.get(id)?.type === 'random')) trace.append(node('li', { class: 'smart-object__hint' },
                t('Simulation draws locally. The game makes its own choice.')));
            if (result.actions.some(action => action.type === 'emitEvent')) trace.append(node('li', { class: 'smart-object__hint' },
                t('Signals are queued in the game; this preview runs only the selected event.')));
            if (result.actions.some(action => action.type === 'interact')) trace.append(node('li', { class: 'smart-object__hint' },
                t('Target interactions are listed here. Use Test behavior to rehearse their full graphs without changing the game.')));
            if (result.actions.some(action => ['showMessage', 'showHandout', 'cameraFocus', 'teleport'].includes(action.type)))
                trace.append(node('li', { class: 'smart-object__hint' }, t('Presentation and teleport actions are previewed only. No player window, camera or token changes.')));
        } catch (cause) { error(cause); }
    });
    listen(undo, 'click', () => restore(undoStack, redoStack));
    listen(redo, 'click', () => restore(redoStack, undoStack));
    listen(zoomIn, 'click', () => zoomCenter(zoom + ZOOM_STEP)); listen(zoomOut, 'click', () => zoomCenter(zoom - ZOOM_STEP));
    listen(zoomReset, 'click', () => zoomCenter(1));
    listen(fit, 'click', () => { clearConnection(); fitView(); });
    async function apply() {
        if (autosave) {
            try { await flushEdits(); } catch (cause) { error(cause); }
            return;
        }
        if (saving) return;
        try {
            clearConnection();
            for (const input of modal.querySelectorAll('input:not([type=search]),textarea,select')) if (!input.reportValidity()) return;
            const focused = document.activeElement;
            if (focused?.matches('[data-blueprint-param]')) focused.dispatchEvent(new Event('change'));
            const originalGraphs = JSON.parse(original).graphs;
            for (const [key, value] of Object.entries(draft.graphs)) {
                if (!isBlueprintSignalEvent(key) && !Object.hasOwn(originalGraphs, key) && JSON.stringify(value) === JSON.stringify(eventGraph(key))) delete draft.graphs[key];
            }
            validateBlueprint(draft, { assets, materials, lights, sounds, element: object });
            saving = true; body.inert = true; save.disabled = cancel.disabled = close.disabled = true;
            modal.setAttribute('aria-busy', 'true');
            if (JSON.stringify(draft) !== original) await onSave(structuredClone(draft));
            pending = null; saving = false; modal.close();
        }
        catch (cause) { error(cause); }
        finally { saving = false; body.inert = false; modal.removeAttribute('aria-busy'); save.disabled = cancel.disabled = close.disabled = false; }
    }
    async function flushEdits() {
        clearTimeout(inputTimer); inputTimer = undefined;
        clearConnection(); pending = null;
        const focused = document.activeElement;
        if (focused?.matches('[data-blueprint-param]') && authoredControl(focused)) focused.dispatchEvent(new Event('change'));
        if (!fieldsValid(true)) throw new Error('Check the highlighted fields before saving.');
        if (!authoredChange) return;
        saver.schedule();
        await saver.flush();
    }
    listen(modal, 'gravewright:sheet-flush', event => {
        if (!autosave) return;
        event.detail.waitUntil(flushEdits().catch(cause => { error(cause); throw cause; }));
    });
    listen(retry, 'click', () => {
        if (saver.state.status === 'conflict' || !fieldsValid(true)) return;
        saver.retry(); void saver.flush().catch(cause => error(cause));
    });
    listen(discard, 'click', async () => {
        if (discard.hidden) return;
        try {
            await onDiscard?.(structuredClone(confirmedBlueprint));
            saver.dispose();
            modal.close(true);
        } catch (cause) { error(cause); }
    });
    listen(save, 'click', apply); for (const control of [close, cancel]) listen(control, 'click', () => { clearConnection(); pending = null; modal.close(); });
    listen(modal, 'keydown', event => {
        const typing = event.target.closest('input, select, textarea');
        const shortcut = event.ctrlKey || event.metaKey, key = event.key.toLowerCase();
        if (shortcut && key === 's') { event.preventDefault(); event.stopPropagation(); apply(); return; }
        if (shortcut && !typing && (key === 'z' || key === 'y')) {
            event.preventDefault(); event.stopPropagation();
            if (key === 'y' || event.shiftKey) restore(redoStack, undoStack); else restore(undoStack, redoStack);
            return;
        }
        if (shortcut && !typing && !event.altKey && canvas.contains(event.target) && ['a', 'c', 'v', 'd'].includes(key)) {
            event.preventDefault(); event.stopPropagation(); clearConnection();
            if (key === 'a') { selection.clear(); for (const card of nodes.children) selection.add(card.dataset.blueprintNode); paintSelection(); }
            if (key === 'c') clipboard = copySelection() || clipboard;
            if (key === 'v' && clipboard) paste(clipboard, pasteOrigin(clipboard));
            if (key === 'd') { const copy = copySelection(); if (copy) paste(copy, { x: copy.left + 40, y: copy.top + 40 }); }
            return;
        }
        if (event.key === 'Escape' && (wireDrag || wireChoice || pending)) {
            event.preventDefault(); event.stopImmediatePropagation(); clearConnection(true); pending = null; renderGraph();
        }
    });
    modal.addEventListener('close', () => {
        disposed = true; clearTimeout(inputTimer); saver?.dispose(); clearConnection(); abort.abort(); if (frame) cancelAnimationFrame(frame); onClose?.();
    }, { once: true });
    renderSettings(); renderGraph(); applyView();
    mountModal(modal, { nested, canClose: () => {
        if (saving) return false;
        if (wireDrag || wireChoice) { clearConnection(true); pending = null; return false; }
        if (!pending) return true;
        pending = null; renderGraph(); return false;
    } });
    document.fonts.ready.then(() => {
        if (disposed) return;
        fitView(); scheduleEdges();
    });
    return modal;
}
