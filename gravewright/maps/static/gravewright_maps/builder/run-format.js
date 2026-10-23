import { blueprintEventLabel } from './blueprint-model.js';

/** Readable automation traces and rehearsal changes, shared by the run log and the test panel. */
export const STATE_NAMES = { closed: 'Closed', open: 'Opened', locked: 'Locked', off: 'Deactivated', on: 'Activated', empty: 'Empty', occupied: 'Occupied' };
export const STEP_NAMES = { event: 'Event', light: 'Set light', sound: 'Play sound', state: 'Change state', interact: 'Interact with object', condition: 'Check state',
    sprite: 'Change sprite', sequence: 'Sequence', property: 'Get property', compare: 'Compare state',
    reference: 'Element reference', reveal: 'Reveal', barrier: 'Set barrier', soundControl: 'Control sound', flame: 'Set flame',
    all: 'All conditions', any: 'Any condition', getVariable: 'Get variable', setVariable: 'Set variable', compareValue: 'Compare value', emitEvent: 'Emit event',
    counter: 'Counter', once: 'Once', cooldown: 'Cooldown', delay: 'Delay', timer: 'Timer', switch: 'Switch', random: 'Random',
    elementGroup: 'Element group', lightReference: 'Light reference', soundReference: 'Sound reference', eventContext: 'Event context',
    move: 'Move object', rotate: 'Rotate object', setInteraction: 'Set interaction', setRegion: 'Set region',
    setVisibility: 'Set visibility', setAppearance: 'Set appearance', showMessage: 'Show message',
    showHandout: 'Show handout', requestRoll: 'Request dice roll', setQuestStatus: 'Set quest status', cameraFocus: 'Focus camera', teleport: 'Teleport token', clockControl: 'Control clock', clueControl: 'Control clue' };
const CHANNEL_NAMES = { movement: 'Movement', vision: 'Vision', light: 'Light', sound: 'Sound' };
const MODE_NAMES = { block: 'Block', pass: 'Pass', attenuate: 'Attenuate' };
const APPEARANCE_NAMES = { inherit: 'Native appearance', hidden: 'Hidden image', asset: 'Use image' };
const NATIVE_KIND_NAMES = { walls: 'Door', images: 'Object', lights: 'Light', zones: 'Region', particles: 'Particles', shaders: 'Shader' };
const HIDDEN_LAYERS = ['gm', 'gm-image-layer'];

/**
 * `elements` returns the current catalog ({ id, kind, name }); `resolve` maps a
 * native ID to its catalog ID; `fallbackName` and `tokenName` name what the
 * catalog does not list, such as plain regions in a live scene or test tokens.
 */
export function createRunFormatter({ t, elements, resolve = id => id, fallbackName = () => undefined, tokenName = () => undefined }) {
    const find = id => elements().find(row => row.id === resolve(id) || row.id === id);
    // Keep numbering within each element kind so a lever never renumbers doors.
    const label = id => {
        const row = find(id);
        if (!row) return fallbackName(id) || t('Missing element');
        if (row.name) return row.name;
        const kind = row.kind || 'door', peers = elements().filter(value => (value.kind || 'door') === kind);
        if (kind === 'region' || kind === 'image') return t(kind === 'region' ? 'Region' : 'Object');
        return `${t(kind === 'torch' ? 'Torch' : kind === 'lever' ? 'Lever' : 'Door')} ${peers.indexOf(row) + 1}`;
    };
    const stateName = (value, id) => t(find(id)?.kind === 'torch' ? ({ off: 'Normal', on: 'Turned' }[value] || value) : STATE_NAMES[value] || value);
    const bool = value => t(value ? 'True' : 'False');
    const scalar = value => typeof value === 'boolean' ? bool(value) : typeof value === 'string' ? JSON.stringify(value) : String(value);
    const scopeName = value => t(value === 'scene' ? 'Scene' : 'This element');
    const choiceName = (type, output) => output === 'default' ? t('Default')
        : t(type === 'switch' ? 'Case {0}' : 'Branch {0}', { 0: output.replace(/\D/g, '') });
    const token = id => tokenName(id) || t('Token');

    function stepText(step) {
        const name = t(STEP_NAMES[step.type] || step.type);
        const detail = {
            state: () => stateName(step.state, step.doorId),
            sound: () => `${step.sound || t('Sound')} · ${Math.round(step.volume * 100)}%`,
            light: () => t(step.enabled ? 'Enabled' : 'Disabled'),
            flame: () => t(step.enabled ? 'Lit' : 'Unlit'),
            sprite: () => t(APPEARANCE_NAMES[step.appearance] || step.appearance),
            condition: () => bool(step.result),
            counter: () => `${step.value} / ${step.target} · ${t(step.result ? 'Reached' : 'Below target')}`,
            once: () => t(step.result ? 'First time' : 'Already used'),
            cooldown: () => t(step.result ? 'Ready' : 'Cooling down'),
            delay: () => t('Wait {0} seconds', { 0: step.seconds }),
            timer: () => `${t({ start: 'Start timer', stop: 'Stop timer', restart: 'Restart timer' }[step.action])} · ${step.name}`
                + (step.action === 'stop' ? '' : ` · ${t('Wait {0} seconds', { 0: step.seconds })}`),
            switch: () => `${scalar(step.value)} → ${choiceName(step.type, step.output)}`,
            random: () => `${choiceName(step.type, step.output)} · ${t('Weight')}: ${step.weight}/${step.total}`,
            compare: () => bool(step.value),
            all: () => bool(step.value),
            any: () => bool(step.value),
            compareValue: () => bool(step.value),
            getVariable: () => `${scopeName(step.scope)} · ${step.name} = ${scalar(step.value)}`,
            setVariable: () => `${scopeName(step.scope)} · ${step.name} = ${scalar(step.value)}`,
            emitEvent: () => `${step.name} · ${step.scope === 'scene' ? scopeName('scene') : step.doorId ? label(step.doorId) : t('This element')}`,
            property: () => step.value ? stateName(step.value, step.doorId) : t('Missing element'),
            reference: () => label(step.doorId),
            elementGroup: () => `${step.name} · ${t({ element: 'Elements', light: 'Lights', sound: 'Sounds' }[step.memberType])}: ${step.count}`,
            lightReference: () => t('Light'),
            soundReference: () => step.sound || t('Sound'),
            eventContext: () => `${t({ event: 'Event', sourceId: 'Triggering element ID', userId: 'Triggering user ID', userName: 'Triggering user name',
                tokenId: 'Triggering token ID', actorId: 'Triggering actor ID', presence: 'Presence transition', count: 'Occupancy count',
                hasToken: 'Has triggering token', state: 'Current state', previous: 'Previous state' }[step.property])}: ${scalar(step.value)}`,
            move: () => `${step.dx}, ${step.dy} · ${t('Cells')}`,
            rotate: () => `${step.degrees}°`,
            setInteraction: () => t(step.enabled ? 'Enabled' : 'Disabled'),
            setRegion: () => t(step.enabled ? 'Enabled' : 'Disabled'),
            setVisibility: () => t(step.visible ? 'Visible' : 'Hidden'),
            setAppearance: () => t('Image'),
            showMessage: () => step.text || t('Message'),
            showHandout: () => t('Handout'),
            requestRoll: () => `${step.expression || ''}${step.label ? ` · ${step.label}` : ''}`,
            setQuestStatus: () => t({ draft: 'Draft', available: 'Available', active: 'Active', completed: 'Completed', failed: 'Failed', archived: 'Archived' }[step.status] || step.status),
            clockControl: () => `${t({ advance: 'Advance clock', reduce: 'Reduce clock', set: 'Set clock value', reset: 'Reset clock' }[step.action])}`
                + (Number.isInteger(step.before) && Number.isInteger(step.value) ? ` · ${step.before} → ${step.value}` : ''),
            clueControl: () => `${t({ advance: 'Advance clue', reduce: 'Reduce clue', set: 'Set clue progress', reset: 'Reset clue', reveal: 'Reveal clue', hide: 'Hide clue' }[step.action])}`
                + (Number.isInteger(step.before) && Number.isInteger(step.value) ? ` · ${step.before} → ${step.value}` : '')
                + (['gm', 'players'].includes(step.visibility) ? ` · ${t(step.beforeVisibility === 'gm' ? 'GM only' : 'Visible to players')} → ${t(step.visibility === 'gm' ? 'GM only' : 'Visible to players')}` : ''),
            cameraFocus: () => `${step.focusX}, ${step.focusY} · ${t('Cells')}`,
            teleport: () => step.skipped ? t('Skipped')
                : `${token(step.tokenId)} → ${label(step.destinationId)} (${step.gridX}, ${step.gridY})`,
            reveal: () => step.doorId ? label(step.doorId) : t('This element'),
            barrier: () => `${t(CHANNEL_NAMES[step.channel])}: ${t(MODE_NAMES[step.mode])}`,
            soundControl: () => `${step.sound || t('Sound')} · ${step.action === 'stop' ? t('Stop') : `${Math.round(step.volume * 100)}%`}`,
        }[step.type];
        let text = detail ? `${name}: ${detail()}` : name;
        if (['state', 'barrier', 'flame'].includes(step.type) && step.doorId) text += ` · ${label(step.doorId)}`;
        if (step.targetIds?.length && !step.doorId) text += ` · ${t('Targets')}: ${step.targetIds.length}`;
        if (step.players) text += ` · ${t('Players may lock or unlock')}`;
        if (step.unsupported) text += ` · ${t('Unsupported action for this element')}`;
        if (step.unsupportedIds?.length) text += ` · ${t('Unsupported targets')}: ${step.unsupportedIds.map(id => find(id) ? label(id) : t('Element')).join(', ')}`;
        return step.missing ? `${text} · ${t('Missing target')}` : text;
    }

    function eventTitle(entry) {
        const phase = entry.event.split(':')[0];
        const door = entry.doorId ? `${label(entry.doorId)} · ` : '';
        if (phase === 'refused') return `${door}${t('Skipped')}`;
        const title = `${door}${blueprintEventLabel(entry.event, t, find(entry.doorId)?.kind || 'door')}`;
        return phase !== 'presence' && phase !== 'signal' && entry.previous
            ? `${title} · ${t('Previous state')}: ${stateName(entry.previous, entry.doorId)}` : title;
    }

    /** Stores hold { type, value } per name; list each name whose value changed. */
    function variableChanges(before = {}, after = {}, prefix = t('Variables')) {
        return [...new Set([...Object.keys(before || {}), ...Object.keys(after || {})])]
            .filter(name => JSON.stringify(before?.[name]) !== JSON.stringify(after?.[name]))
            .map(name => `${prefix} · ${name} = ${after?.[name] === undefined ? '—' : scalar(after[name].value)}`);
    }

    /** Summarize one rehearsal element change: known fields as facts, the rest as technical details. */
    function describeChange(change) {
        const title = find(change.sourceId || change.id) ? label(change.sourceId || change.id)
            : change.after?.data?.name || change.before?.data?.name || t(NATIVE_KIND_NAMES[change.kind] || 'Element');
        if (change.after === null) return { title, removed: true, facts: [], details: [] };
        const after = change.after?.data || {}, before = change.before?.data || {};
        const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
        const facts = [], details = [], handled = new Set(['src', 'blueprint', 'name']);
        const transition = (from, to, id) => `${stateName(from, id)} → ${stateName(to, id)}`;
        const occupancy = (from = {}, to = {}) => {
            const was = from.occupants || [], now = to.occupants || [];
            const parts = [];
            if (from.state !== to.state && to.state) parts.push(transition(from.state, to.state, change.id));
            const entered = now.filter(id => !was.includes(id)), left = was.filter(id => !now.includes(id));
            if (entered.length) parts.push(`${t('Entered area')}: ${entered.map(token).join(', ')}`);
            if (left.length) parts.push(`${t('Left area')}: ${left.map(token).join(', ')}`);
            if (parts.length) facts.push(parts.join(' · '));
        };
        const check = (keys, write) => {
            const changed = keys.filter(key => !same(after[key], before[key]));
            for (const key of keys) handled.add(key);
            if (changed.length) write(changed);
        };
        check(['door_state'], () => facts.push(transition(before.door_state, after.door_state, change.id)));
        if (!same(after.lever?.state, before.lever?.state)) facts.push(transition(before.lever?.state, after.lever?.state, change.id));
        if (!same(after.torch?.state, before.torch?.state)) facts.push(transition(before.torch?.state, after.torch?.state, change.id));
        if (!same(after.torch?.lit, before.torch?.lit)) facts.push(t(after.torch?.lit ? 'Lit' : 'Unlit'));
        if (!same(after.region, before.region)) occupancy(before.region, after.region);
        if (!same(after.areaPresence, before.areaPresence)) occupancy(before.areaPresence, after.areaPresence);
        check(['enabled'], () => facts.push(t(after.enabled ? 'Enabled' : 'Disabled')));
        check(['interactionEnabled'], () => facts.push(`${t('Set interaction')}: ${t(after.interactionEnabled === false ? 'Disabled' : 'Enabled')}`));
        check(['discovered'], () => after.discovered && facts.push(t('Reveal')));
        check(['layer'], () => facts.push(t(HIDDEN_LAYERS.includes(after.layer) ? 'Hidden' : 'Visible')));
        check(['x', 'y', 'x1', 'y1', 'x2', 'y2', 'geometry'], () => facts.push(t('Moved')));
        check(['rotation'], () => facts.push(`${t('Rotated')}: ${Math.round(((after.rotation || 0) - (before.rotation || 0)) * 100) / 100}°`));
        check(['sprite', 'asset_id'], () => facts.push(t('Appearance changed')));
        for (const channel of Object.keys(CHANNEL_NAMES)) check([`${channel}_behavior`], () =>
            facts.push(`${t(CHANNEL_NAMES[channel])}: ${t(MODE_NAMES[after[`${channel}_behavior`]] || after[`${channel}_behavior`])}`));
        check(['automationVariables'], () => facts.push(...variableChanges(before.automationVariables, after.automationVariables)));
        for (const key of ['lever', 'torch', 'region', 'areaPresence']) handled.add(key);
        for (const key of new Set([...Object.keys(after), ...Object.keys(before)])) {
            if (!handled.has(key) && !same(after[key], before[key])) details.push([key, JSON.stringify(after[key] ?? null)]);
        }
        // Internal bookkeeping inside known objects stays inspectable without leading the summary.
        for (const key of ['lever', 'torch', 'region', 'areaPresence']) if (!same(after[key], before[key])) details.push([key, JSON.stringify(after[key] ?? null)]);
        return { title, removed: false, facts, details };
    }

    return { label, tokenLabel: token, stateName, stepText, eventTitle, describeChange, variableChanges };
}
