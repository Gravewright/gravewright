/** Shared editor vocabulary; native objects remain authoritative for current state. */
import { shaderProperties, validateShaderValue } from './shader-control.js';
export const blueprintStates = Object.freeze(['closed', 'open', 'locked']);
const leverStates = Object.freeze(['off', 'on']);
const regionStates = Object.freeze(['empty', 'occupied']);
export const blueprintWritableStates = Object.freeze([...blueprintStates, ...leverStates]);
export const blueprintAllStates = Object.freeze([...blueprintWritableStates, ...regionStates]);
/** States owned by this element; cross-element actions may use blueprintAllStates. */
export function blueprintStatesFor(kind = 'door') {
    if (kind === 'door') return blueprintStates;
    if (kind === 'lever' || kind === 'torch') return leverStates;
    if (kind === 'region') return regionStates;
    throw new Error('Unsupported blueprint version or object type.');
}
/** New event entry points only start execution; state decisions belong to nodes. */
export function blueprintVerbEventsFor(kind = 'door') {
    blueprintStatesFor(kind);
    if (kind === 'door') return ['interact', 'destroy'];
    const presence = ['presence:enter', 'presence:exit', 'destroy'];
    return kind === 'region' ? presence : ['interact', ...presence];
}
export function blueprintEventsFor(kind = 'door', blueprint = null) {
    return [...blueprintVerbEventsFor(kind),
        ...(blueprint?.version === 2 ? Object.keys(blueprint.graphs || {}).filter(isBlueprintSignalEvent) : [])];
}
/** Presentation names for supported event identifiers. */
export function blueprintEventMetadata(event, kind = 'door') {
    blueprintStatesFor(kind);
    const definitions = {
        interact: { label: 'On interaction', code: 'onInteract' },
        destroy: { label: 'On destroy', code: 'onDestroy' },
        'presence:enter': { label: 'On area enter', code: 'onAreaEnter' },
        'presence:exit': { label: 'On area exit', code: 'onAreaExited' },
    };
    if (Object.hasOwn(definitions, event)) return { event, ...definitions[event] };
    if (isBlueprintSignalEvent(event)) return { event, label: 'On signal', code: 'onSignal', name: event.slice(7) };
    return null;
}
/** Labels share event vocabulary; authored signal names remain unchanged. */
export function blueprintEventLabel(event, t, kind = 'door') {
    const metadata = blueprintEventMetadata(event, kind);
    if (metadata) return `${t(metadata.label)}${metadata.name ? ` · ${metadata.name}` : ''}`;
    return event;
}
/** Opening an event alone creates no authored actions or execution path. */
export function isMeaningfulBlueprintGraph(graph) {
    return Boolean(Array.isArray(graph?.nodes) && graph.nodes.some(node => node.type !== 'event') || Array.isArray(graph?.edges) && graph.edges.length > 0);
}
/** An authored generic interaction owns the gesture only when execution is wired. */
export function hasBlueprintEventPath(blueprint, event) {
    const graph = blueprint?.graphs?.[event], root = graph?.nodes?.find(node => node.type === 'event');
    return Boolean(root && graph.edges?.some(edge => edge.from === root.id && edge.output === 'next' && edge.kind !== 'data'));
}
/** Match the server's locked-door interaction guard without granting lock writes. */
export function canInteractWithBlueprintDoor(door, gm = false) {
    if (!door || door.kind !== 'door') return false;
    if (gm) return true;
    if (door.interactionEnabled === false) return false;
    if ((door.door_state ?? door.state) !== 'locked') return true;
    return door.blueprintInteraction === true || door.blueprint?.version === 2 && hasBlueprintEventPath(door.blueprint, 'interact');
}
export const blueprintAppearances = Object.freeze(['inherit', 'hidden', 'asset']);
export const blueprintProperties = Object.freeze(['state', 'previous']);
export const variableTypes = Object.freeze(['boolean', 'number', 'text']);
export const variableScopes = Object.freeze(['element', 'scene']);
export const variableOperators = Object.freeze(['eq', 'ne', 'lt', 'lte', 'gt', 'gte']);
export const timerActions = Object.freeze(['start', 'stop', 'restart']);
export const switchCaseIds = Object.freeze(['case1', 'case2', 'case3', 'case4']);
export const randomBranchIds = Object.freeze(['branch1', 'branch2', 'branch3', 'branch4']);
export const groupMemberTypes = Object.freeze(['element', 'light', 'sound']);
export const audienceScopes = Object.freeze(['trigger', 'players', 'users']);
export function validateAudience(audience) {
    if (!audience || !audienceScopes.includes(audience.scope)
        || !exactFields(audience, audience.scope === 'users' ? ['scope', 'userIds'] : ['scope'])
        || audience.scope === 'users' && !identifierList(audience.userIds, 64)) throw new Error('Invalid blueprint audience.');
    return audience;
}
export const eventContextTypes = Object.freeze({ event: 'text', sourceId: 'text', userId: 'text', userName: 'text', tokenId: 'text', actorId: 'text',
    presence: 'text', count: 'number', hasToken: 'boolean', state: 'state', previous: 'state' });
export const eventContextProperties = Object.freeze(Object.keys(eventContextTypes));
// Require the actual end; JavaScript's $ also accepts a final line break.
const namePattern = /^[A-Za-z][A-Za-z0-9_.-]{0,63}(?![\s\S])/;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![\s\S])/i;
const validUuid = value => typeof value === 'string' && uuidPattern.test(value);
function identifierList(value, maximum) {
    return Array.isArray(value) && value.length >= 1 && value.length <= maximum && Array.from(value).every(validUuid)
        && new Set(value.map(id => id.toLowerCase())).size === value.length;
}
export function isBlueprintSignalEvent(event) { return typeof event === 'string' && event.startsWith('signal:') && namePattern.test(event.slice(7)); }
export function typedDefault(valueType) { return valueType === 'number' ? 0 : valueType === 'text' ? '' : false; }
function typedValue(valueType, value) {
    return valueType === 'boolean' ? typeof value === 'boolean'
        : valueType === 'number' ? Number.isFinite(value) && Math.abs(value) <= 1000000
            : valueType === 'text' && typeof value === 'string' && value.length <= 512 && Array.from(value).length <= 256;
}
/** Optional private simulation memory; never written to a scene or project. */
export function validateVariableSnapshot(variables = {}) {
    if (!variables || typeof variables !== 'object' || Array.isArray(variables)
        || Object.keys(variables).some(scope => !variableScopes.includes(scope))) throw new Error('Invalid blueprint variable snapshot.');
    for (const scope of variableScopes) {
        if (!Object.hasOwn(variables, scope)) continue;
        const rows = variables[scope];
        if (!rows || typeof rows !== 'object' || Array.isArray(rows) || Object.keys(rows).length > 64) throw new Error('Invalid blueprint variable snapshot.');
        for (const [name, row] of Object.entries(rows)) {
            if (!namePattern.test(name) || !exactFields(row, ['type', 'value']) || !variableTypes.includes(row.type)
                || !typedValue(row.type, row.value)) throw new Error('Invalid blueprint variable snapshot.');
        }
    }
    return variables;
}
/** Private preview metadata mirrors trusted trigger fields, never a writable payload. */
export function validateEventContextSnapshot(value = {}) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(key => !Object.hasOwn(eventContextTypes, key)))
        throw new Error('Invalid blueprint event context.');
    for (const [key, actual] of Object.entries(value)) {
        const type = eventContextTypes[key];
        if (type === 'state' ? !blueprintAllStates.includes(actual) : !typedValue(type, actual)
            || key === 'count' && (!Number.isInteger(actual) || actual < 0)) throw new Error('Invalid blueprint event context.');
    }
    return value;
}

export const controlNodeTypes = Object.freeze(['counter', 'once', 'cooldown']);
const nodeIdPattern = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;
const memoryEvents = new Set(['door', 'lever', 'torch', 'region'].flatMap(kind => blueprintEventsFor(kind)));
/** Validate private per-element progress without reading inherited properties. */
export function validateBlueprintMemory(memory = {}) {
    if (!memory || typeof memory !== 'object' || Array.isArray(memory) || Object.keys(memory).length > 128) throw new Error('Invalid blueprint control memory.');
    let count = 0;
    for (const [event, rows] of Object.entries(memory)) {
        if (!memoryEvents.has(event) && !isBlueprintSignalEvent(event)
            || !rows || typeof rows !== 'object' || Array.isArray(rows)) throw new Error('Invalid blueprint control memory.');
        for (const [id, row] of Object.entries(rows)) {
            if (++count > 128 || !nodeIdPattern.test(id) || !exactFields(row, ['type', 'value']) || !controlNodeTypes.includes(row.type)
                || (row.type === 'once' ? row.value !== true : !Number.isSafeInteger(row.value) || row.value < 0
                    || row.type === 'counter' && row.value > 1000000)) throw new Error('Invalid blueprint control memory.');
        }
    }
    return memory;
}
/** Copy progress for surviving controls; layout, wires and parameter edits keep it. */
export function reconcileBlueprintMemory(blueprint, memory = {}) {
    supportedBlueprint(blueprint);
    validateBlueprintMemory(memory);
    const result = Object.create(null);
    for (const [event, graph] of Object.entries(blueprint.graphs || {})) {
        if (!Object.hasOwn(memory, event)) continue;
        const rows = memory[event], kept = Object.create(null);
        for (const node of graph.nodes) {
            const row = Object.hasOwn(rows, node.id) ? rows[node.id] : null;
            if (row && controlNodeTypes.includes(node.type) && row.type === node.type) kept[node.id] = structuredClone(row);
        }
        if (Object.keys(kept).length) result[event] = kept;
    }
    return result;
}

function freeze(value) {
    for (const entry of Object.values(value)) if (entry && typeof entry === 'object') freeze(entry);
    return Object.freeze(value);
}
const executionInput = { id: 'input', kind: 'execution', label: 'Input' };
const executionNext = { id: 'next', kind: 'execution', label: 'Next' };
const sequenceOutputs = ['then1', 'then2', 'then3', 'then4'].map((id, index) => ({ id, kind: 'execution', label: String(index + 1) }));
const eventOutput = event => ({ id: event, ...blueprintEventMetadata(event),
    color: { interact: 'green', destroy: 'red', 'presence:enter': 'green', 'presence:exit': 'red' }[event], kind: 'execution' });
const verbOutputs = blueprintVerbEventsFor().map(eventOutput);
const objectOutputs = blueprintVerbEventsFor('lever').map(eventOutput);
const regionOutputs = blueprintVerbEventsFor('region').map(eventOutput);
// Node types added with version 2; version 1 documents keep their original vocabulary.
const versionTwoTypes = ['shaderControl','sequence', 'sprite', 'property', 'compare', 'all', 'any', 'reference', 'reveal', 'barrier', 'soundControl', 'flame',
    'getVariable', 'setVariable', 'compareValue', 'emitEvent', ...controlNodeTypes, 'delay', 'timer', 'switch', 'random',
    'elementGroup', 'lightReference', 'soundReference', 'eventContext', 'move', 'rotate', 'setInteraction', 'setRegion',
    'showMessage', 'showHandout', 'requestRoll', 'setQuestStatus', 'cameraFocus', 'teleport', 'setVisibility', 'setAppearance', 'interact', 'clockControl', 'clueControl', 'openMindMap', 'mindMapNode'];
export const questStatuses = Object.freeze(['draft', 'available', 'active', 'completed', 'failed', 'archived']);
export const barrierChannels = Object.freeze(['movement', 'vision', 'light', 'sound']);
export const soundControls = Object.freeze(['stop', 'volume']);
export const clockControls = Object.freeze(['advance', 'reduce', 'set', 'reset']);
export const clueControls = Object.freeze(['advance', 'reduce', 'set', 'reset', 'reveal', 'hide']);
export const mindMapControls = Object.freeze(['complete', 'reset', 'toggle']);
// A connected Target replaces "Self" with a referenced element. The persisted
// reference output ID remains "door" for existing version-two documents.
const targetInput = { id: 'target', kind: 'value', type: 'element', label: 'Target' };
const elementTargets = { ...targetInput, acceptedTypes: ['element', 'elementset'] };
const lightTargets = { ...targetInput, type: 'light', acceptedTypes: ['light', 'lightset'] };
const soundTargets = { ...targetInput, type: 'sound', acceptedTypes: ['sound', 'soundset'] };
const transformTargets = { ...targetInput, acceptedTypes: ['element', 'elementset', 'light', 'lightset'] };
const booleanInputs = ['a', 'b', 'c', 'd'].map(id => ({ id, kind: 'value', type: 'boolean', label: id.toUpperCase() }));
const booleanOutput = { id: 'result', kind: 'value', type: 'boolean', label: 'Result' };
const controlOutputs = (yes, no) => [{ id: 'true', kind: 'execution', label: yes }, { id: 'false', kind: 'execution', label: no }];

/** Internal capability vocabulary, limited to the nodes the runtime implements. */
export const blueprintContract = freeze({
    versions: [2], currentVersion: 2,
    limits: { graphNodes: 32, graphEdges: 64, blueprintNodes: 128, coordinate: 5000, signalGraphs: 16, variables: 64, variableNumber: 1000000, variableText: 256 },
    portKinds: { execution: { implemented: true }, value: { implemented: true }, reference: { implemented: false } },
    nodes: {
        shaderControl: {category:'action',label:'Control shader',inputs:[executionInput,{id:'value',kind:'value',type:'boolean',label:'Value'}],outputs:[executionNext]},
        door: { category: 'element', label: 'Door', inputs: [], outputs: verbOutputs },
        lever: { category: 'element', label: 'Lever', inputs: [], outputs: objectOutputs },
        torch: { category: 'element', label: 'Torch', inputs: [], outputs: objectOutputs },
        region: { category: 'element', label: 'Region', inputs: [], outputs: regionOutputs },
        event: { category: 'event', label: 'Event', inputs: [], outputs: [executionNext] },
        light: { category: 'action', label: 'Set light', inputs: [executionInput, lightTargets], outputs: [executionNext] },
        sound: { category: 'action', label: 'Play sound', inputs: [executionInput, soundTargets], outputs: [executionNext] },
        state: { category: 'action', label: 'Set state', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        interact: { category: 'action', label: 'Interact with object', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        flame: { category: 'action', label: 'Set flame', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        sprite: { category: 'action', label: 'Change sprite', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        condition: { category: 'condition', label: 'Condition', inputs: [executionInput, { id: 'test', kind: 'value', type: 'boolean', label: 'Test' }], outputs: [
            { id: 'true', kind: 'execution', label: 'True' }, { id: 'false', kind: 'execution', label: 'False' },
        ] },
        sequence: { category: 'control', label: 'Sequence', inputs: [executionInput], outputs: sequenceOutputs },
        property: { category: 'value', label: 'Get property', inputs: [targetInput], outputs: [{ id: 'value', kind: 'value', type: 'state', label: 'Value' }] },
        compare: { category: 'value', label: 'Compare state', inputs: [{ id: 'value', kind: 'value', type: 'state', label: 'Value' }],
            outputs: [booleanOutput] },
        all: { category: 'value', label: 'All conditions', inputs: booleanInputs, outputs: [booleanOutput] },
        any: { category: 'value', label: 'Any condition', inputs: booleanInputs, outputs: [booleanOutput] },
        reference: { category: 'value', label: 'Element reference', inputs: [], outputs: [{ id: 'door', kind: 'value', type: 'element', label: 'Element' }] },
        reveal: { category: 'action', label: 'Reveal', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        barrier: { category: 'action', label: 'Set barrier', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        soundControl: { category: 'action', label: 'Control sound', inputs: [executionInput, soundTargets], outputs: [executionNext] },
        clockControl: { category: 'action', label: 'Control clock', inputs: [executionInput,
            { id: 'amount', kind: 'value', type: 'number', label: 'Amount' }], outputs: [executionNext] },
        clueControl: { category: 'action', label: 'Control clue', inputs: [executionInput,
            { id: 'amount', kind: 'value', type: 'number', label: 'Amount' }], outputs: [executionNext] },
        getVariable: { category: 'value', label: 'Get variable', inputs: [], outputs: [{ id: 'value', kind: 'value', type: 'boolean', label: 'Value' }] },
        setVariable: { category: 'action', label: 'Set variable', inputs: [executionInput, { id: 'value', kind: 'value', type: 'boolean', label: 'Value' }], outputs: [executionNext] },
        compareValue: { category: 'value', label: 'Compare value', inputs: [{ id: 'value', kind: 'value', type: 'boolean', label: 'Value' }], outputs: [booleanOutput] },
        emitEvent: { category: 'action', label: 'Emit signal', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        counter: { category: 'control', label: 'Counter', inputs: [executionInput], outputs: controlOutputs('Reached', 'Below target') },
        once: { category: 'control', label: 'Once', inputs: [executionInput], outputs: controlOutputs('First time', 'Already used') },
        cooldown: { category: 'control', label: 'Cooldown', inputs: [executionInput], outputs: controlOutputs('Ready', 'Cooling down') },
        delay: { category: 'control', label: 'Delay', inputs: [executionInput], outputs: [executionNext] },
        timer: { category: 'control', label: 'Timer', inputs: [executionInput], outputs: [executionNext] },
        switch: { category: 'control', label: 'Switch', inputs: [executionInput, { id: 'value', kind: 'value', type: 'boolean', label: 'Value' }],
            outputs: [{ id: 'default', kind: 'execution', label: 'Default' }] },
        random: { category: 'control', label: 'Random', inputs: [executionInput], outputs: [] },
        elementGroup: { category: 'value', label: 'Element group', inputs: [], outputs: [{ id: 'targets', kind: 'value', type: 'elementset', label: 'Targets' }] },
        lightReference: { category: 'value', label: 'Light reference', inputs: [], outputs: [{ id: 'light', kind: 'value', type: 'light', label: 'Light' }] },
        soundReference: { category: 'value', label: 'Sound reference', inputs: [], outputs: [{ id: 'sound', kind: 'value', type: 'sound', label: 'Sound' }] },
        eventContext: { category: 'value', label: 'Event context', inputs: [], outputs: [{ id: 'value', kind: 'value', type: 'text', label: 'Value' }] },
        move: { category: 'action', label: 'Move element', inputs: [executionInput, transformTargets], outputs: [executionNext] },
        rotate: { category: 'action', label: 'Rotate element', inputs: [executionInput, transformTargets], outputs: [executionNext] },
        setInteraction: { category: 'action', label: 'Set interaction', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        setRegion: { category: 'action', label: 'Set region', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        showMessage: { category: 'action', label: 'Show message', inputs: [executionInput], outputs: [executionNext] },
        showHandout: { category: 'action', label: 'Show handout', inputs: [executionInput], outputs: [executionNext] },
        requestRoll: { category: 'action', label: 'Request dice roll', inputs: [executionInput], outputs: [executionNext] },
        setQuestStatus: { category: 'action', label: 'Set quest status', inputs: [executionInput], outputs: [executionNext] },
        openMindMap: { category: 'action', label: 'Open mind map', inputs: [executionInput], outputs: [executionNext] },
        mindMapNode: { category: 'action', label: 'Control mind-map topic', inputs: [executionInput], outputs: [executionNext] },
        cameraFocus: { category: 'action', label: 'Focus camera', inputs: [executionInput], outputs: [executionNext] },
        teleport: { category: 'action', label: 'Teleport token', inputs: [executionInput], outputs: [executionNext] },
        setVisibility: { category: 'action', label: 'Set visibility', inputs: [executionInput, elementTargets], outputs: [executionNext] },
        setAppearance: { category: 'action', label: 'Set appearance', inputs: [executionInput, elementTargets], outputs: [executionNext] },
    },
    adapters: {
        door: { rootType: 'door', states: blueprintStates, outputs: verbOutputs },
        lever: { rootType: 'lever', states: leverStates, outputs: objectOutputs },
        torch: { rootType: 'torch', states: leverStates, outputs: objectOutputs },
        region: { rootType: 'region', states: regionStates, outputs: regionOutputs },
    },
});

/** The instance card is a view of the real object, never a second saved object. */
export function elementInstanceNode(element, kind = element?.torch ? 'torch' : element?.lever ? 'lever' : element?.blueprint?.kind || 'door') {
    const adapter = blueprintContract.adapters[kind], state = element?.[kind]?.state ?? element?.state;
    if (!adapter || !element || typeof element.id !== 'string' || !element.id || !adapter.states.includes(state)) throw new Error('Invalid blueprint object.');
    return { id: `object:${element.id}`, type: kind, sourceId: element.id,
        name: element.name || blueprintContract.nodes[kind].label, state, outputs: structuredClone(adapter.outputs) };
}
export function doorInstanceNode(door) { return elementInstanceNode(door, 'door'); }

export function defaultBlueprint(kind = 'door') {
    return { version: 2, kind,
        states: Object.fromEntries(blueprintStatesFor(kind).map(state => [state, { appearance: 'inherit' }])), graphs: {} };
}
function supportedBlueprint(blueprint) {
    if (!blueprint || !blueprintContract.versions.includes(blueprint.version) || !Object.hasOwn(blueprintContract.adapters, blueprint.kind)
        || blueprint.kind !== 'door' && blueprint.version === 1) throw new Error('Unsupported blueprint version or object type.');
}
/** Normalize loaded data, discarding removed event graphs rather than migrating their behavior. */
export function upgradeBlueprint(blueprint) {
    if (!blueprint || ![1, 2].includes(blueprint.version) || !Object.hasOwn(blueprintContract.adapters, blueprint.kind)
        || blueprint.kind !== 'door' && blueprint.version === 1) throw new Error('Unsupported blueprint version or object type.');
    const result = structuredClone(blueprint);
    if (!result.graphs || typeof result.graphs !== 'object' || Array.isArray(result.graphs)) throw new Error('Invalid blueprint event.');
    for (const event of Object.keys(result.graphs)) if (event === 'change' || /^(enter|exit|interact):/.test(event)) delete result.graphs[event];
    for (const event of Object.keys(result.graphs)) if (!blueprintVerbEventsFor(result.kind).includes(event) && !isBlueprintSignalEvent(event)) throw new Error('Invalid blueprint event.');
    for (const graph of Object.values(result.graphs)) {
        if (!Array.isArray(graph?.edges)) throw new Error('Invalid blueprint connection.');
        for (const edge of graph.edges) {
            if (blueprint.version === 2 && !['execution', 'data'].includes(edge.kind) || blueprint.version === 1 && 'kind' in edge) throw new Error('Invalid blueprint connection.');
            edge.kind ||= 'execution';
        }
    }
    result.version = 2;
    return result;
}
export function eventGraph(event) {
    if (!['interact', 'destroy', 'presence:enter', 'presence:exit'].includes(event) && !isBlueprintSignalEvent(event)) throw new Error('Invalid blueprint event.');
    return { nodes: [{ id: 'event', type: 'event', event, x: 40, y: 60 }], edges: [] };
}
/** Execution ports include the stable case/branch identifiers of configured choices. */
export function executionOutputs(node) {
    if (node.type === 'switch') return [...(node.cases || []).map(row => ({ id: row.id, kind: 'execution', label: String(switchCaseIds.indexOf(row.id) + 1) })),
        { id: 'default', kind: 'execution', label: 'Default' }];
    if (node.type === 'random') return (node.weights || []).map((_, index) => ({ id: randomBranchIds[index], kind: 'execution', label: String(index + 1) }));
    return blueprintContract.nodes[node.type]?.outputs.filter(port => port.kind === 'execution') || [];
}
/** Execution output identifiers, in the order they run. */
export function nodeOutputs(node) { return executionOutputs(node).map(port => port.id); }
function valuePorts(node, direction) {
    return (blueprintContract.nodes[node.type]?.[direction] || []).filter(port => port.kind === 'value').map(port => {
        if (node.type==='shaderControl'&&port.id==='value')return {...port,type:shaderProperties[node.property]?.type};
        if (['getVariable', 'setVariable', 'compareValue', 'switch'].includes(node.type) && port.id === 'value') return { ...port, type: node.valueType };
        if (node.type === 'elementGroup') return { ...port, type: `${node.memberType}set` };
        if (node.type === 'eventContext') return { ...port, type: eventContextTypes[node.property] };
        return port;
    });
}
export function dataOutputs(node) { return valuePorts(node, 'outputs'); }
export function dataInputs(node) { return valuePorts(node, 'inputs'); }
export function acceptsDataType(port, type) { return !!port && (port.acceptedTypes || [port.type]).includes(type); }
export function isPureNode(node) { return blueprintContract.nodes[node?.type]?.category === 'value'; }
/** Add an execution edge, or a typed data edge when ``input`` names the target port. */
export function connectNodes(graph, from, output, to, { version = 2, input } = {}) {
    if (!blueprintContract.versions.includes(version)) throw new Error('Unsupported blueprint version or object type.');
    const source = graph.nodes.find(node => node.id === from), target = graph.nodes.find(node => node.id === to);
    if (!source || !target || from === to) throw new Error('Invalid blueprint connection.');
    let edge;
    if (input !== undefined) {
        const produced = dataOutputs(source).find(port => port.id === output), accepted = dataInputs(target).find(port => port.id === input);
        if (version !== 2 || !produced || !acceptsDataType(accepted, produced.type)) throw new Error('Invalid blueprint connection.');
        if (graph.edges.some(item => item.kind === 'data' && item.to === to && item.input === input)) throw new Error('Each input accepts one connection.');
        edge = { from, output, to, input, kind: 'data' };
    } else {
        if (target.type === 'event' || isPureNode(target) || !nodeOutputs(source).includes(output)) throw new Error('Invalid blueprint connection.');
        if (version === 2 && graph.edges.some(item => item.kind !== 'data' && item.from === from && item.output === output && item.to === to)) throw new Error('Duplicate blueprint connection.');
        edge = version === 2 ? { from, output, to, kind: 'execution' } : { from, output, to };
    }
    const edges = version === 2 || input !== undefined ? [...graph.edges, edge]
        : [...graph.edges.filter(item => item.from !== from || item.output !== output), edge];
    if (edges.length > blueprintContract.limits.graphEdges) throw new Error('The blueprint has too many nodes or connections.');
    const visiting = new Set(), visited = new Set();
    function visit(id) {
        if (visiting.has(id)) throw new Error('Blueprint connections cannot contain a cycle.');
        if (visited.has(id)) return;
        visiting.add(id);
        for (const edge of edges) if (edge.from === id) visit(edge.to);
        visiting.delete(id); visited.add(id);
    }
    for (const node of graph.nodes) visit(node.id);
    graph.edges = edges;
}
const nodeFields = {
    shaderControl:['targetId','property','value'],
    event: ['event'], light: ['targetId', 'enabled'], sound: ['trackId', 'volume'], state: ['targetState'], condition: ['state'],
    sequence: [], interact: [], sprite: ['appearance'], property: ['property'], compare: ['state'], all: [], any: [], reference: ['targetId'], reveal: [],
    barrier: ['channel', 'mode'], soundControl: ['trackId', 'action', 'volume'], clockControl: ['clockId', 'action', 'amount'],
    clueControl: ['clueId', 'action', 'amount'], openMindMap: ['mindMapId', 'nodeId', 'audience'], mindMapNode: ['mindMapId', 'nodeId', 'action'], flame: ['enabled'],
    getVariable: ['scope', 'name', 'valueType', 'default'], setVariable: ['scope', 'name', 'valueType', 'value'],
    compareValue: ['valueType', 'operator', 'expected'], emitEvent: ['scope', 'name'],
    counter: ['target'], once: [], cooldown: ['seconds'], delay: ['seconds'], timer: ['name', 'action'],
    switch: ['valueType', 'value', 'cases'], random: ['weights'],
    elementGroup: ['name', 'memberType', 'targetIds'], lightReference: ['targetId'], soundReference: ['trackId'], eventContext: ['property'],
    move: ['dx', 'dy'], rotate: ['degrees'], setInteraction: ['enabled'], setRegion: ['enabled'],
    showMessage: ['text', 'audience'], showHandout: ['journalId', 'audience'], cameraFocus: ['focusX', 'focusY', 'audience'],
    requestRoll: ['expression', 'label', 'visibility', 'audience'], setQuestStatus: ['journalId', 'status'],
    teleport: ['destinationId'], setVisibility: ['visible'], setAppearance: ['assetId'],
};
function exactFields(value, fields) {
    return value && typeof value === 'object' && !Array.isArray(value)
        && Object.keys(value).length === fields.length && fields.every(key => Object.hasOwn(value, key));
}
// Optional fields: an image sprite names its asset; an authorized Change state
// carries ``players: true``, which lets a player-started chain lock or unlock.
function fieldsOf(node) {
    const fields = ['id', 'type', 'x', 'y', ...nodeFields[node.type]];
    if (node.type === 'sprite' && node.appearance === 'asset') fields.push('assetId');
    if (node.type === 'state' && Object.hasOwn(node, 'players')) fields.push('players');
    if (node.type === 'timer' && node.action !== 'stop') fields.push('seconds');
    return fields;
}
function validateGraph(graph, event, version) {
    if (!exactFields(graph, ['nodes', 'edges']) || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)
        || !graph.nodes.length || graph.nodes.length > 32 || graph.edges.length > 64) throw new Error('The blueprint has too many nodes or connections.');
    const events = graph.nodes.filter(node => node?.type === 'event');
    if (events.length !== 1 || events[0].event !== event) throw new Error('Each blueprint graph needs one matching event.');
    const seen = new Set();
    for (const node of graph.nodes) {
        if (!node || !Object.hasOwn(nodeFields, node.type) || version === 1 && versionTwoTypes.includes(node.type) || !exactFields(node, fieldsOf(node))
            || typeof node.id !== 'string' || !nodeIdPattern.test(node.id) || seen.has(node.id)
            || !Number.isFinite(node.x) || !Number.isFinite(node.y) || Math.min(node.x, node.y) < 0 || Math.max(node.x, node.y) > 5000) throw new Error('Invalid blueprint node.');
        seen.add(node.id);
        if(node.type==='shaderControl'){
            if(!validUuid(node.targetId))throw Error('Choose a shader from this map.');
            validateShaderValue(node.property,node.value);
        }
        if (['state', 'condition', 'compare'].includes(node.type)
            && !(node.type === 'state' ? blueprintWritableStates : blueprintAllStates).includes(node.type === 'state' ? node.targetState : node.state)) throw new Error('Invalid blueprint state.');
        if (node.type === 'sprite' && !blueprintAppearances.includes(node.appearance) || node.type === 'property' && !blueprintProperties.includes(node.property)
            || ['reference', 'lightReference'].includes(node.type) && !validUuid(node.targetId)
            || node.type === 'soundReference' && !validUuid(node.trackId)
            || node.type === 'state' && Object.hasOwn(node, 'players') && (node.players !== true || version === 1)
            || node.type === 'flame' && typeof node.enabled !== 'boolean'
            || node.type === 'barrier' && (!barrierChannels.includes(node.channel)
                || !(node.channel === 'sound' ? ['block', 'pass', 'attenuate'] : ['block', 'pass']).includes(node.mode))
            || node.type === 'soundControl' && (!soundControls.includes(node.action) || !Number.isFinite(node.volume) || node.volume < 0 || node.volume > 1)) throw new Error('Invalid blueprint node.');
        if (['getVariable', 'setVariable', 'emitEvent'].includes(node.type)
            && (!variableScopes.includes(node.scope) || typeof node.name !== 'string' || !namePattern.test(node.name))) throw new Error('Invalid blueprint variable or signal name.');
        if (['getVariable', 'setVariable', 'compareValue'].includes(node.type)
            && (!variableTypes.includes(node.valueType) || !typedValue(node.valueType,
                node.type === 'getVariable' ? node.default : node.type === 'setVariable' ? node.value : node.expected))) throw new Error('Invalid blueprint variable value.');
        if (node.type === 'compareValue' && (!variableOperators.includes(node.operator)
            || node.valueType !== 'number' && !['eq', 'ne'].includes(node.operator))) throw new Error('Invalid blueprint comparison.');
        if (node.type === 'counter' && (!Number.isInteger(node.target) || node.target < 1 || node.target > 1000000)
            || ['cooldown', 'delay'].includes(node.type) && (!Number.isFinite(node.seconds) || node.seconds < .1 || node.seconds > 86400)) throw new Error('Invalid blueprint control.');
        if (node.type === 'timer' && (typeof node.name !== 'string' || !namePattern.test(node.name) || !timerActions.includes(node.action)
            || node.action !== 'stop' && (!Number.isFinite(node.seconds) || node.seconds < .1 || node.seconds > 86400))) throw new Error('Invalid blueprint timer.');
        if (node.type === 'clockControl' && (!validUuid(node.clockId) || !clockControls.includes(node.action)
            || !Number.isInteger(node.amount) || node.amount < 0 || node.amount > 24)) throw new Error('Invalid blueprint clock action.');
        if (node.type === 'clueControl' && (!validUuid(node.clueId) || !clueControls.includes(node.action)
            || !Number.isInteger(node.amount) || node.amount < 0 || node.amount > 24)) throw new Error('Invalid blueprint clue action.');
        if (['openMindMap', 'mindMapNode'].includes(node.type) && (!validUuid(node.mindMapId)
            || !(node.type === 'openMindMap' && node.nodeId === null) && !validUuid(node.nodeId)
            || node.type === 'mindMapNode' && !mindMapControls.includes(node.action))) throw new Error('Invalid blueprint mind-map action.');
        if (node.type === 'switch' && (!variableTypes.includes(node.valueType) || !typedValue(node.valueType, node.value)
            || !Array.isArray(node.cases) || node.cases.length < 1 || node.cases.length > 4
            || !Array.from(node.cases).every(row => exactFields(row, ['id', 'value']) && switchCaseIds.includes(row.id) && typedValue(node.valueType, row.value))
            || new Set(node.cases.map(row => row.id)).size !== node.cases.length
            || new Set(node.cases.map(row => row.value)).size !== node.cases.length)) throw new Error('Invalid blueprint switch.');
        if (node.type === 'random' && (!Array.isArray(node.weights) || node.weights.length < 2 || node.weights.length > 4
            || !Array.from(node.weights).every(weight => Number.isInteger(weight) && weight >= 0 && weight <= 1000)
            || node.weights.reduce((total, weight) => total + weight, 0) <= 0)) throw new Error('Invalid blueprint random weights.');
        if (node.type === 'elementGroup' && (typeof node.name !== 'string' || !node.name.trim() || node.name.includes('\0') || Array.from(node.name).length > 80
            || !groupMemberTypes.includes(node.memberType) || !identifierList(node.targetIds, 32))) throw new Error('Invalid blueprint element group.');
        if (node.type === 'eventContext' && !Object.hasOwn(eventContextTypes, node.property)) throw new Error('Invalid blueprint event context.');
        if (node.type === 'move' && ![node.dx, node.dy].every(value => Number.isFinite(value) && Math.abs(value) <= 1000)
            || node.type === 'rotate' && (!Number.isFinite(node.degrees) || Math.abs(node.degrees) > 36000)
            || ['setInteraction', 'setRegion'].includes(node.type) && typeof node.enabled !== 'boolean') throw new Error('Invalid blueprint action.');
        if (['showMessage', 'showHandout', 'requestRoll', 'cameraFocus', 'openMindMap'].includes(node.type)) validateAudience(node.audience);
        if (node.type === 'requestRoll' && (typeof node.expression !== 'string' || !node.expression.trim() || node.expression.includes('\0')
            || Array.from(node.expression).length > 512 || typeof node.label !== 'string' || node.label.includes('\0')
            || Array.from(node.label).length > 48 || !['public', 'gm'].includes(node.visibility))) throw new Error('Invalid blueprint dice request.');
        if (node.type === 'setQuestStatus' && (!validUuid(node.journalId) || !questStatuses.includes(node.status))) throw new Error('Invalid blueprint quest action.');
        if (node.type === 'showMessage' && (typeof node.text !== 'string' || !node.text.trim() || node.text.includes('\0') || Array.from(node.text).length > 2000)
            || node.type === 'showHandout' && !validUuid(node.journalId)
            || node.type === 'teleport' && !validUuid(node.destinationId)
            || node.type === 'cameraFocus' && ![node.focusX, node.focusY].every(value => Number.isFinite(value) && value >= 0 && value <= 1000)
            || node.type === 'setVisibility' && typeof node.visible !== 'boolean'
            || node.type === 'setAppearance' && !validUuid(node.assetId)) throw new Error('Invalid blueprint presentation action.');
    }
    const copy = { nodes: graph.nodes, edges: [] }, occupied = new Set();
    for (const edge of graph.edges) {
        const data = version === 2 && edge?.kind === 'data';
        if (!exactFields(edge, version === 2 ? ['from', 'to', 'output', 'kind', ...(data ? ['input'] : [])] : ['from', 'to', 'output'])
            || version === 2 && !['execution', 'data'].includes(edge.kind)) throw new Error('Invalid blueprint connection.');
        const key = `${edge.from}:${edge.output}`;
        if (version === 1 && occupied.has(key)) throw new Error('Each output accepts one connection.');
        occupied.add(key); connectNodes(copy, edge.from, edge.output, edge.to, { version, ...(data ? { input: edge.input } : {}) });
    }
}
/** Image-less owners can control other artwork, but cannot acquire their own. */
export function validateBlueprintImageTargets(blueprint, element) {
    if (element?.empty !== true) return blueprint;
    const invalid = () => { throw new Error('Empty Objects cannot receive images.'); };
    if (Object.values(blueprint.states || {}).some(state => state.appearance !== 'inherit')) invalid();
    return blueprint;
}
export function validateBlueprint(blueprint, { assets = [], materials = assets, lights = [], shaders = [], sounds = [], clocks, clues, mindmaps, element } = {}) {
    supportedBlueprint(blueprint);
    const states = blueprintStatesFor(blueprint.kind);
    if (!exactFields(blueprint, ['version', 'kind', 'states', 'graphs']) || !exactFields(blueprint.states, states)) throw new Error('Invalid blueprint state.');
    const ids = rows => new Set(rows.map(row => row.id));
    const assetIds = ids(assets), materialIds = ids(materials), lightIds = ids(lights), soundIds = ids(sounds);
    for (const state of states) {
        const appearance = blueprint.states[state];
        if (!appearance || !blueprintAppearances.includes(appearance.appearance)
            || blueprint.kind === 'region' && appearance.appearance !== 'inherit'
            || !exactFields(appearance, appearance.appearance === 'asset' ? ['appearance', 'assetId'] : ['appearance'])
            || appearance.appearance === 'asset' && !assetIds.has(appearance.assetId)) throw new Error('Choose an image for each configured state.');
    }
    if (!blueprint.graphs || typeof blueprint.graphs !== 'object' || Array.isArray(blueprint.graphs)) throw new Error('Invalid blueprint event.');
    let count = 0, signals = 0;
    const declarations = new Map(variableScopes.map(scope => [scope, new Map()]));
    for (const [event, graph] of Object.entries(blueprint.graphs)) {
        if (!blueprintEventsFor(blueprint.kind, blueprint).includes(event) && !(blueprint.version === 2 && isBlueprintSignalEvent(event))) throw new Error('Invalid blueprint event.');
        if (isBlueprintSignalEvent(event) && ++signals > blueprintContract.limits.signalGraphs) throw new Error('The blueprint has too many signals.');
        validateGraph(graph, event, blueprint.version);
        count += graph.nodes.length;
        if (count > 128) throw new Error('The blueprint has too many nodes or connections.');
        for (const node of graph.nodes) {
            if (['getVariable', 'setVariable'].includes(node.type)) {
                const names = declarations.get(node.scope);
                if (names.has(node.name) && names.get(node.name) !== node.valueType) throw new Error('A blueprint variable must keep the same type.');
                names.set(node.name, node.valueType);
                if (names.size > blueprintContract.limits.variables) throw new Error('The blueprint has too many variables.');
            }
            if(node.type==='shaderControl'){
                if(!shaders.some(shader=>shader.id===node.targetId))throw Error('Choose a shader from this map.');
                validateShaderValue(node.property,node.value);
            }
            if (node.type === 'light' && (!lightIds.has(node.targetId) || typeof node.enabled !== 'boolean')) throw new Error('Choose a light from this map.');
            if (['sound', 'soundControl'].includes(node.type) && (!soundIds.has(node.trackId) || !Number.isFinite(node.volume) || node.volume < 0 || node.volume > 1)) throw new Error('Choose a sound from this campaign.');
            if (node.type === 'clockControl' && clocks !== undefined
                && !clocks.some(clock => clock.id.toLowerCase() === node.clockId.toLowerCase())) throw new Error('Choose a clock from this campaign.');
            if (node.type === 'clueControl' && clues !== undefined
                && !clues.some(clue => clue.id.toLowerCase() === node.clueId.toLowerCase())) throw new Error('Choose a clue from this campaign.');
            if (['openMindMap', 'mindMapNode'].includes(node.type) && mindmaps !== undefined) {
                const map = mindmaps.find(row => row.id.toLowerCase() === node.mindMapId.toLowerCase());
                if (!map || node.nodeId !== null && !map.nodes?.some(topic => topic.id.toLowerCase() === node.nodeId.toLowerCase()))
                    throw new Error('Choose a mind map and topic from this campaign.');
            }
            if (node.type === 'sprite' && node.appearance === 'asset' && !assetIds.has(node.assetId) && !materialIds.has(node.assetId)) throw new Error('Choose an image for each Change sprite node.');
            if (node.type === 'setAppearance' && !materialIds.has(node.assetId)) throw new Error('Choose an image for each Set appearance node.');
        }
    }
    return validateBlueprintImageTargets(blueprint, element);
}
/**
 * Mirror the server evaluation: conditions and properties read the state at the
 * start of the event, ``previousState`` is the state left by the transition, and
 * pure nodes join the trace when an executed node first reads them. ``elements``
 * maps element IDs to states for properties and actions with a connected Target.
 * Optional ``context.variables`` contains private typed element/scene snapshots.
 * Writes, signals and timers are queued actions; this single-event preview neither
 * changes that snapshot nor executes receiving graphs. ``context.memory`` is
 * cloned and reconciled for stateful controls; ``now`` is integer UTC milliseconds
 * and defaults to zero so previews are repeatable. Returned memory is private to
 * this preview and can be supplied to its next run. A Delay suspends the remaining
 * event traversal, including later Sequence branches. Its continuation runs on
 * the server; this preview reports the first wait without advancing the clock.
 * Timers continue immediately through Next; expiry emits a fresh signal only on
 * the server and cannot execute a receiving graph in this preview.
 * Switch selects one matching case or Default. Random selects across every
 * authored weight, including disconnected branches; optional ``randomDraw``
 * receives (nodeId, total) and returns an integer in [0, total). Otherwise the
 * preview uses Math.random. Only reached nodes draw, once per event traversal.
 */
export function simulateGraph(blueprint, event, currentState, previousState = currentState, elements = {}, context = {}) {
    supportedBlueprint(blueprint);
    const states = blueprintStatesFor(blueprint.kind);
    if (!blueprintEventsFor(blueprint.kind, blueprint).includes(event) && !(blueprint.version === 2 && isBlueprintSignalEvent(event))) throw new Error('Invalid blueprint event.');
    if (!states.includes(currentState) || !states.includes(previousState)) throw new Error('Invalid blueprint state.');
    const variables = validateVariableSnapshot(context.variables);
    const metadata = validateEventContextSnapshot(context.eventContext);
    const eventContext = { ...Object.fromEntries(eventContextProperties.map(property => [property,
        eventContextTypes[property] === 'number' ? 0 : eventContextTypes[property] === 'boolean' ? false : ''])),
        hasToken: Boolean(metadata.tokenId), presence: event.startsWith('presence:') ? event.slice(9) : '',
        ...metadata, event, state: currentState, previous: previousState };
    const now = context.now === undefined ? 0 : context.now;
    if (!Number.isSafeInteger(now) || now < 0 || now > Number.MAX_SAFE_INTEGER - 86400000) throw new Error('Invalid blueprint simulation time.');
    function storedVariable(node) {
        const rows = Object.hasOwn(variables, node.scope) ? variables[node.scope] : {};
        const row = Object.hasOwn(rows, node.name) ? rows[node.name] : null;
        if (row && row.type !== node.valueType) throw new Error('A blueprint variable must keep the same type.');
        return row;
    }
    const graph = blueprint.graphs[event];
    const trace = [], actions = [];
    let delay;
    const controls = graph?.nodes.some(node => controlNodeTypes.includes(node.type));
    const choices = graph?.nodes.some(node => ['switch', 'random'].includes(node.type));
    const memory = controls || Object.hasOwn(context, 'memory') ? reconcileBlueprintMemory(blueprint, context.memory) : null;
    if (!graph) return { trace, actions, ...(memory ? { memory } : {}) };
    validateGraph(graph, event, blueprint.version);
    const nodes = new Map(graph.nodes.map(node => [node.id, node])), visited = new Set(), values = new Map();
    const decisions = Object.create(null);
    const source = (id, input) => graph.edges.find(edge => edge.kind === 'data' && edge.to === id && edge.input === input)?.from;
    function value(id) {
        if (!values.has(id)) {
            const node = nodes.get(id), from = source(id, 'value'), aim = source(id, 'target');
            if (node.type === 'all' || node.type === 'any') {
                // Read every connected input in port order, even when the first
                // input already decides the result. Incomplete drafts stay false.
                const inputs = dataInputs(node).map(port => source(id, port.id)).filter(Boolean).map(value);
                values.set(id, inputs.length >= 2 && (node.type === 'all'
                    ? inputs.every(result => result === true) : inputs.some(result => result === true)));
            } else if (node.type === 'getVariable') {
                const row = storedVariable(node);
                values.set(id, row ? row.value : node.default);
            } else if (node.type === 'compareValue') {
                const input = from ? value(from) : typedDefault(node.valueType), expected = node.expected;
                values.set(id, node.operator === 'eq' ? input === expected : node.operator === 'ne' ? input !== expected
                    : node.operator === 'lt' ? input < expected : node.operator === 'lte' ? input <= expected
                        : node.operator === 'gt' ? input > expected : input >= expected);
            } else if (node.type === 'elementGroup') values.set(id, structuredClone(node.targetIds));
            else if (node.type === 'eventContext') values.set(id, eventContext[node.property]);
            else values.set(id, ['reference', 'lightReference'].includes(node.type) ? node.targetId : node.type === 'soundReference' ? node.trackId
                : node.type === 'property' ? (aim ? elements[value(aim)] ?? null : node.property === 'state' ? currentState : previousState)
                : (from ? value(from) : currentState) === node.state);
            trace.push(id);
        }
        return values.get(id);
    }
    function visit(node) {
        if (delay || visited.has(node.id)) return;
        visited.add(node.id); trace.push(node.id);
        if (node.type === 'delay') {
            delay = { nodeId: node.id, seconds: node.seconds };
            return;
        }
        if (['light', 'shaderControl', 'sound', 'state', 'interact', 'sprite', 'reveal', 'barrier', 'soundControl', 'flame', 'setVariable', 'emitEvent', 'timer',
            'move', 'rotate', 'setInteraction', 'setRegion', 'showMessage', 'showHandout', 'requestRoll', 'setQuestStatus', 'cameraFocus', 'teleport', 'setVisibility', 'setAppearance', 'clockControl', 'clueControl', 'openMindMap', 'mindMapNode'].includes(node.type)) {
            const action = structuredClone(node), aim = source(node.id, 'target');
            if (aim) action.target = structuredClone(value(aim));
            const input = node.type === 'setVariable' && source(node.id, 'value');
            if (node.type === 'setVariable') {
                storedVariable(node);
                if (input) action.value = value(input);
            }
            if (node.type === 'clockControl' && node.action !== 'reset') {
                const amount = source(node.id, 'amount');
                if (amount) action.amount = value(amount);
                if (!Number.isInteger(action.amount) || action.amount < 0 || action.amount > 24)
                    throw new Error('Clock amount must be an integer from 0 to 24.');
            }
            if (node.type === 'clueControl' && ['advance', 'reduce', 'set'].includes(node.action)) {
                const amount = source(node.id, 'amount');
                if (amount) action.amount = value(amount);
                if (!Number.isInteger(action.amount) || action.amount < 0 || action.amount > 24)
                    throw new Error('Clue amount must be an integer from 0 to 24.');
            }
            if(node.type==='shaderControl'){
                const input=source(node.id,'value');
                if(input)action.value=value(input);
                validateShaderValue(node.property,action.value);
            }
            actions.push(action);
        }
        let outputs;
        if (controlNodeTypes.includes(node.type)) {
            const rows = Object.hasOwn(memory, event) ? memory[event] : (memory[event] = Object.create(null));
            const previous = Object.hasOwn(rows, node.id) ? rows[node.id] : null;
            let passed, next;
            if (node.type === 'counter') {
                next = Math.min(1000000, (previous?.value ?? 0) + 1);
                passed = next >= node.target;
            } else if (node.type === 'once') {
                passed = previous?.value !== true;
                next = true;
            } else {
                passed = !previous || now >= previous.value;
                next = passed ? now + Math.ceil(node.seconds * 1000) : previous.value;
                if (!Number.isSafeInteger(next)) throw new Error('Invalid blueprint simulation time.');
            }
            rows[node.id] = { type: node.type, value: next };
            decisions[node.id] = passed;
            outputs = [String(passed)];
        } else if (node.type === 'switch') {
            const input = source(node.id, 'value'), current = input ? value(input) : node.value;
            decisions[node.id] = node.cases.find(row => row.value === current)?.id ?? 'default';
            outputs = [decisions[node.id]];
        } else if (node.type === 'random') {
            const total = node.weights.reduce((sum, weight) => sum + weight, 0);
            const draw = context.randomDraw === undefined ? Math.floor(Math.random() * total)
                : typeof context.randomDraw === 'function' ? context.randomDraw(node.id, total) : NaN;
            if (!Number.isInteger(draw) || draw < 0 || draw >= total) throw new Error('Invalid blueprint random draw.');
            let accumulated = 0;
            const index = node.weights.findIndex(weight => { accumulated += weight; return draw < accumulated; });
            decisions[node.id] = randomBranchIds[index];
            outputs = [decisions[node.id]];
        } else if (node.type === 'condition') {
            const test = source(node.id, 'test');
            decisions[node.id] = test ? value(test) : node.state === currentState;
            outputs = [String(decisions[node.id])];
        } else outputs = nodeOutputs(node);
        for (const output of outputs) {
            for (const edge of graph.edges.filter(edge => edge.kind !== 'data' && edge.from === node.id && edge.output === output)) visit(nodes.get(edge.to));
        }
    }
    visit(graph.nodes.find(item => item.type === 'event'));
    return { trace, actions, values: Object.fromEntries(values), ...(memory ? { memory } : {}), ...(controls || choices ? { decisions } : {}), ...(delay ? { delay } : {}) };
}
export function blueprintAppearance(element, kind = element?.torch ? 'torch' : element?.lever ? 'lever' : element?.blueprint?.kind || 'door') {
    if (element.empty === true) return { visible: false, assetId: null };
    const current = element[kind]?.state ?? element.state;
    const state = element.blueprint?.states?.[current];
    if (state?.appearance === 'hidden') return { visible: false, assetId: null };
    if (state?.appearance === 'asset') return { visible: true, assetId: state.assetId };
    return { visible: kind !== 'door' || current !== 'open' || element.rotationAnchor !== undefined, assetId: element.assetId };
}
