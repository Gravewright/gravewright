/** Ready-to-edit interactive objects use the existing generic mechanism contract. */
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, validateAudience, isMeaningfulBlueprintGraph } from './blueprint-model.js';

export const interactiveObjectPresets = Object.freeze([
    { id: 'switch', name: 'Interactive switch', description: 'Toggle a switch and optionally open or close a linked door.', group: 'Mechanisms', door: 'optional' },
    { id: 'chest', name: 'Chest', description: 'Open and close a chest. Show a message the first time it opens.', group: 'Objects', message: 'The chest is open.' },
    { id: 'secret-passage', name: 'Secret passage', description: 'Toggle a linked door from an interactive object.', group: 'Mechanisms', door: 'required' },
    { id: 'book', name: 'Readable book', description: 'Open a journal handout for the chosen players.', group: 'Journal and quests', handout: true },
    { id: 'altar', name: 'Altar', description: 'Show a message on interaction, with a five-second cooldown.', group: 'Objects', message: 'The altar responds to your touch.' },
    { id: 'trap', name: 'Warning trap', description: 'Warn players when a token enters the armed object. Interact to arm or disarm it.', group: 'Mechanisms', message: 'A trap has been triggered!', initialState: 'on' },
    { id: 'bell', name: 'Bell', description: 'Ring a bell and notify the chosen players, with a short cooldown.', group: 'Objects', message: 'The bell rings.' },
    { id: 'pressure-plate', name: 'Pressure plate', description: 'Open a linked door on area entry and close it when the last token leaves. Interaction also opens it.', group: 'Mechanisms', door: 'required' },
    { id: 'dice-request', name: 'Dice challenge', description: 'Ask the chosen players to roll dice in a modal when they interact.', group: 'Dice', roll: true },
    { id: 'quest-start', name: 'Quest giver', description: 'Mark a quest as active and open its journal entry for the chosen players.', group: 'Journal and quests', quest: 'active' },
    { id: 'quest-complete', name: 'Quest completion', description: 'Mark a quest as completed and open its journal entry for the chosen players.', group: 'Journal and quests', quest: 'completed' },
    { id: 'entrance-sign', name: 'Entrance sign', description: 'Show a welcome message once when a token enters. Interaction reads it again.', group: 'Objects', message: 'You have entered a new area.' },
    { id: 'timed-switch', name: 'Timed switch', description: 'Activate an object and optionally open a door, then reset them after a delay.', group: 'Mechanisms', door: 'optional', delay: true },
    { id: 'door-button', name: 'Door button', description: 'Open a linked door when the button is pressed.', group: 'Mechanisms', door: 'required' },
].map(row => Object.freeze(row)));
/** The inspector and context menu share this catalog rather than duplicating it. */
export const interactiveObjectBehaviorOptions = Object.freeze(interactiveObjectPresets.map(preset => Object.freeze({ value: `preset:${preset.id}`, label: preset.name })));
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![\s\S])/i;

/** Return an independent Blueprint and its authored initial state; no object is mutated. */
export function createInteractiveObjectPreset(id, { doorId = '', journalId = '', text, audience = { scope: 'trigger' },
    expression = '1d20', label = '', visibility = 'public', seconds = 5,
    includeSound = false, trackId = '', volume = .7, includeImage = false, assetId = '', t = value => value } = {}) {
    const preset = interactiveObjectPresets.find(row => row.id === id);
    if (!preset) throw new Error('Choose an interactive object.');
    if ((preset.door === 'required' || doorId) && !uuid.test(doorId)) throw new Error('Choose a controlled door first.');
    if ((preset.handout || preset.quest) && !uuid.test(journalId)) throw new Error(preset.quest ? 'Choose a quest first.' : 'Choose a journal handout first.');
    if (includeSound && !uuid.test(trackId)) throw new Error('Choose a sound from this campaign.');
    if (includeImage && !uuid.test(assetId)) throw new Error('Choose an image for each configured state.');
    validateAudience(audience);
    const blueprint = defaultBlueprint('lever'), graph = eventGraph('interact');
    const add = (target, node, x, y) => { target.nodes.push({ ...node, x, y }); return node.id; };
    const link = (target, from, output, to, input) => connectNodes(target, from, output, to, input ? { input } : {});
    const message = target => add(target, { id: 'message', type: 'showMessage', text: text ?? t(preset.message), audience: structuredClone(audience) }, 1320, 60);
    const sound = (target, from, output = 'next') => {
        if (!includeSound) return;
        const effect = add(target, { id: 'sound', type: 'sound', trackId, volume }, 1640, 60); link(target, from, output, effect);
    };
    const activate = target => add(target, { id: 'activate', type: 'state', targetState: 'on' }, 680, 60);
    const openDoor = (target, from, state = 'open', x = 1000, y = 60) => {
        if (!doorId) return from;
        if (!target.nodes.some(node => node.id === 'door')) add(target, { id: 'door', type: 'reference', targetId: doorId }, 680, 700);
        const name = state === 'open' ? 'open' : 'close';
        add(target, { id: name, type: 'state', targetState: state }, x, y); link(target, from, 'next', name); link(target, 'door', 'door', name, 'target');
        return name;
    };
    function toggle() {
        add(graph, { id: 'check', type: 'condition', state: 'off' }, 360, 60);
        add(graph, { id: 'activate', type: 'state', targetState: 'on' }, 680, 60);
        add(graph, { id: 'deactivate', type: 'state', targetState: 'off' }, 680, 380);
        link(graph, 'event', 'next', 'check'); link(graph, 'check', 'true', 'activate'); link(graph, 'check', 'false', 'deactivate');
        const opened = openDoor(graph, 'activate'); openDoor(graph, 'deactivate', 'closed', 1000, 380);
        if (['switch', 'secret-passage'].includes(id)) sound(graph, opened);
    }
    if (['switch', 'secret-passage', 'chest', 'trap'].includes(id)) toggle();
    if (id === 'chest') {
        add(graph, { id: 'firstOpen', type: 'once' }, 1000, 60);
        link(graph, 'activate', 'next', 'firstOpen'); link(graph, 'firstOpen', 'true', message(graph)); sound(graph, 'message');
    } else if (preset.handout || preset.quest) {
        const entry = preset.quest ? add(graph, { id: 'quest', type: 'setQuestStatus', journalId, status: preset.quest }, 360, 380) : 'event';
        if (preset.quest) link(graph, 'event', 'next', entry);
        add(graph, { id: 'read', type: 'showHandout', journalId, audience: structuredClone(audience) }, 360, 60);
        activate(graph); link(graph, entry, 'next', 'read'); link(graph, 'read', 'next', 'activate'); sound(graph, 'activate');
    } else if (['altar', 'bell', 'dice-request'].includes(id)) {
        add(graph, { id: 'cooldown', type: 'cooldown', seconds: id === 'bell' ? 2 : 5 }, 360, 60);
        activate(graph); link(graph, 'event', 'next', 'cooldown'); link(graph, 'cooldown', 'true', 'activate');
        if (preset.roll) {
            add(graph, { id: 'roll', type: 'requestRoll', expression, label, visibility, audience: structuredClone(audience) }, 1000, 60);
            link(graph, 'activate', 'next', 'roll'); sound(graph, 'roll');
        } else { link(graph, 'activate', 'next', message(graph)); sound(graph, 'message'); }
    } else if (id === 'trap') {
        const enter = eventGraph('presence:enter');
        add(enter, { id: 'armed', type: 'condition', state: 'on' }, 360, 60);
        add(enter, { id: 'cooldown', type: 'cooldown', seconds: 5 }, 680, 60);
        link(enter, 'event', 'next', 'armed'); link(enter, 'armed', 'true', 'cooldown'); link(enter, 'cooldown', 'true', message(enter)); sound(enter, 'message');
        blueprint.graphs['presence:enter'] = enter;
    } else if (['pressure-plate', 'door-button'].includes(id)) {
        activate(graph); link(graph, 'event', 'next', 'activate'); sound(graph, openDoor(graph, 'activate'));
        if (id === 'pressure-plate') {
            blueprint.graphs['presence:enter'] = { nodes: graph.nodes.map(node => ({ ...node, ...(node.type === 'event' ? { event: 'presence:enter' } : {}) })), edges: structuredClone(graph.edges) };
            const exit = eventGraph('presence:exit');
            add(exit, { id: 'count', type: 'eventContext', property: 'count' }, 360, 380);
            add(exit, { id: 'empty', type: 'compareValue', valueType: 'number', operator: 'eq', expected: 0 }, 680, 380);
            add(exit, { id: 'lastExit', type: 'condition', state: 'on' }, 680, 60);
            add(exit, { id: 'deactivate', type: 'state', targetState: 'off' }, 1000, 60);
            link(exit, 'count', 'value', 'empty', 'value'); link(exit, 'empty', 'result', 'lastExit', 'test');
            link(exit, 'event', 'next', 'lastExit'); link(exit, 'lastExit', 'true', 'deactivate');
            openDoor(exit, 'deactivate', 'closed', 1320, 60); blueprint.graphs['presence:exit'] = exit;
        }
    } else if (id === 'entrance-sign') {
        activate(graph); link(graph, 'event', 'next', 'activate'); link(graph, 'activate', 'next', message(graph)); sound(graph, 'message');
        const enter = eventGraph('presence:enter');
        add(enter, { id: 'firstEntry', type: 'once' }, 360, 60); activate(enter);
        link(enter, 'event', 'next', 'firstEntry'); link(enter, 'firstEntry', 'true', 'activate'); link(enter, 'activate', 'next', message(enter)); sound(enter, 'message');
        blueprint.graphs['presence:enter'] = enter;
    } else if (id === 'timed-switch') {
        add(graph, { id: 'check', type: 'condition', state: 'off' }, 360, 60); activate(graph);
        link(graph, 'event', 'next', 'check'); link(graph, 'check', 'true', 'activate');
        const opened = openDoor(graph, 'activate'); sound(graph, opened);
        add(graph, { id: 'resetDelay', type: 'delay', seconds }, 1960, 60);
        add(graph, { id: 'deactivate', type: 'state', targetState: 'off' }, 2280, 60);
        link(graph, includeSound ? 'sound' : opened, 'next', 'resetDelay'); link(graph, 'resetDelay', 'next', 'deactivate');
        openDoor(graph, 'deactivate', 'closed', 2600, 60);
    }
    if (includeImage) blueprint.states.on = { appearance: 'asset', assetId };
    blueprint.graphs.interact = graph;
    validateBlueprint(blueprint, { assets: includeImage ? [{ id: assetId }] : [], sounds: includeSound ? [{ id: trackId }] : [] });
    return { blueprint, initialState: preset.initialState || 'off', name: t(preset.name) };
}

/** Mount the object catalog. Await onApply(result); thrown errors keep it open. */
export async function openInteractiveObjectCatalog({ element, doors = [], handouts = [], users = [], sounds = [], assets = [], materials = assets,
    initialPreset, preserveState = false, t = value => value, signal: parentSignal, onApply }) {
    const { mountModal } = await import('/static/gravewright_table/modal.js');
    if (parentSignal?.aborted) return null;
    if (!document.querySelector('link[data-blueprint-templates]')) {
        const stylesheet = document.createElement('link'); stylesheet.rel = 'stylesheet';
        stylesheet.href = new URL('./blueprint-templates.css', import.meta.url).href;
        stylesheet.dataset.blueprintTemplates = ''; document.head.append(stylesheet);
    }
    if (!document.querySelector('link[data-interactive-presets]')) {
        const stylesheet = document.createElement('link'); stylesheet.rel = 'stylesheet';
        stylesheet.href = new URL('./interactive-presets.css', import.meta.url).href;
        stylesheet.dataset.interactivePresets = ''; document.head.append(stylesheet);
    }
    const abort = new AbortController(), { signal } = abort;
    const make = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className;
        if (text !== undefined) node.textContent = text; return node; };
    const button = (label, action, className) => { const node = make('button', className, t(label)); node.type = 'button';
        node.addEventListener('click', action, { signal }); return node; };
    const modal = make('section', 'table-form-modal blueprint-templates interactive-presets'); modal.dataset.interactiveObjectCatalog = '';
    const header = make('header'), title = make('strong', '', t('Interactive object catalog'));
    const titleId = `object-catalog-${crypto.randomUUID()}`; title.id = titleId; modal.setAttribute('aria-labelledby', titleId);
    header.append(title, button('Close', () => modal.close()));
    const body = make('div', 'blueprint-templates__body'), panes = make('div', 'blueprint-templates__panes');
    const sidebar = make('div', 'interactive-presets__sidebar'), list = make('div', 'blueprint-templates__list'), content = make('div', 'blueprint-templates__content');
    const status = make('p', 'blueprint-templates__status'); status.setAttribute('role', 'alert');
    const search = make('input'); search.type = 'search'; search.dataset.interactivePresetSearch = '';
    search.placeholder = t('Search ready-made models'); search.setAttribute('aria-label', t('Search ready-made models'));
    const emptyList = make('p', 'blueprint-templates__hint', t('No matching models.')); emptyList.hidden = true;
    sidebar.append(search, list, emptyList);
    body.append(make('p', 'blueprint-templates__hint', t('Choose an object, apply its behavior, then customize its nodes.')), status, panes);
    panes.append(sidebar, content); modal.append(header, body);
    let chosen = interactiveObjectPresets.find(preset => preset.id === initialPreset) || interactiveObjectPresets[0], busy = false, remember = () => {};
    const cards = new Map(), groups = new Map(), values = new Map();
    // State artwork uses the owner's image catalog; generic surface materials
    // are valid only for Set appearance nodes and cannot become lever states.
    const images = assets;
    for (const preset of interactiveObjectPresets) {
        if (!groups.has(preset.group)) { const group = make('div', 'interactive-presets__group');
            group.append(make('h4', '', t(preset.group))); groups.set(preset.group, group); list.append(group); }
        const card = button(preset.name, () => { remember(); chosen = preset; render(); }, 'blueprint-templates__item');
        card.dataset.interactivePreset = preset.id; card.title = t(preset.description); cards.set(preset.id, card); groups.get(preset.group).append(card);
    }
    search.addEventListener('input', () => {
        const query = search.value.trim().toLocaleLowerCase(); let matches = 0;
        for (const preset of interactiveObjectPresets) {
            const card = cards.get(preset.id); card.hidden = ![preset.name, preset.description, preset.group].some(value => t(value).toLocaleLowerCase().includes(query));
            if (!card.hidden) matches++;
        }
        for (const group of groups.values()) group.hidden = ![...group.querySelectorAll('button')].some(card => !card.hidden);
        emptyList.hidden = matches > 0;
    }, { signal });
    function field(label, control) { const row = make('label', '', t(label)); row.append(control); return row; }
    function checkbox(label, key) { const input = make('input'); input.type = 'checkbox'; input.dataset[key] = '';
        const row = field(label, input); row.className = 'interactive-presets__checkbox'; return [input, row]; }
    function render() {
        status.textContent = ''; content.replaceChildren(); const saved = values.get(chosen.id) || {};
        for (const [id, card] of cards) card.setAttribute('aria-pressed', String(id === chosen.id));
        content.append(make('h3', '', t(chosen.name)), make('p', 'blueprint-templates__hint', t(chosen.description)));
        if (preserveState && chosen.initialState === 'on') {
            const hint = make('p', 'blueprint-templates__hint', t('This object keeps its current state. Interact to arm the trap, or choose its initial state in object properties.'));
            hint.dataset.interactivePreserveState = ''; content.append(hint);
        }
        const form = make('form', 'blueprint-templates__content'); form.dataset.interactivePresetForm = '';
        const door = make('select'); door.dataset.interactivePresetDoor = ''; door.append(new Option(t('Choose a door'), ''));
        for (const entry of doors) door.append(new Option(entry.name || t('Door'), entry.id)); door.value = saved.doorId || '';
        if (chosen.door) { door.required = chosen.door === 'required'; form.append(field('Controlled door', door));
            if (!doors.length) form.append(make('p', 'blueprint-templates__hint', t('No doors are available. Add a door to this map first.'))); }
        const journal = make('select'); journal.dataset.interactivePresetJournal = ''; journal.required = true;
        journal.append(new Option(t(chosen.quest ? 'Choose a quest' : 'Choose a journal handout'), ''));
        const journals = chosen.quest ? handouts.filter(entry => entry.type === 'quest') : handouts;
        for (const entry of journals) journal.append(new Option(entry.name || entry.title || entry.id, entry.id)); journal.value = saved.journalId || '';
        if (chosen.handout || chosen.quest) {
            form.append(field(chosen.quest ? 'Quest' : 'Journal handout', journal));
            if (!journals.length) form.append(make('p', 'blueprint-templates__hint', t(chosen.quest ? 'No quests are available. Add a quest in the journal first.' : 'No journal entries are available. Add an entry in the journal first.')));
        }
        const text = make('textarea'); text.dataset.interactivePresetMessage = ''; text.maxLength = 2000; text.required = true; text.translate = false;
        if (chosen.message) { text.value = saved.text ?? t(chosen.message); form.append(field('Message', text)); }
        const expression = make('input'); expression.dataset.interactivePresetExpression = ''; expression.required = true; expression.maxLength = 512; expression.value = saved.expression ?? '1d20';
        const rollLabel = make('input'); rollLabel.dataset.interactivePresetRollLabel = ''; rollLabel.maxLength = 48; rollLabel.value = saved.label ?? '';
        const visibility = make('select'); visibility.dataset.interactivePresetVisibility = '';
        visibility.append(new Option(t('Public'), 'public'), new Option(t('GM only'), 'gm')); visibility.value = saved.visibility || 'public';
        if (chosen.roll) form.append(field('Dice expression', expression), field('Roll title', rollLabel), field('Roll visibility', visibility));
        const seconds = make('input'); seconds.type = 'number'; seconds.min = '.1'; seconds.max = '86400'; seconds.step = 'any'; seconds.value = String(saved.seconds ?? 5); seconds.required = true;
        seconds.dataset.interactivePresetDelay = ''; if (chosen.delay) form.append(field('Delay (seconds)', seconds));
        const audience = make('select'); audience.dataset.interactivePresetAudience = '';
        audience.append(new Option(t('Triggering player'), 'trigger'), new Option(t('All players'), 'players'), new Option(t('One player'), 'user'));
        audience.value = saved.scope || (['trap', 'bell', 'entrance-sign'].includes(chosen.id) ? 'players' : 'trigger');
        const player = make('select'); player.dataset.interactivePresetPlayer = ''; player.append(new Option(t('Choose a player'), ''));
        for (const entry of users.filter(row => row.role === 'player')) player.append(new Option(entry.name || entry.username || entry.id, entry.id)); player.value = saved.playerId || '';
        const playerField = field('Player', player);
        const updateAudience = () => { playerField.hidden = audience.value !== 'user'; player.required = !playerField.hidden; };
        audience.addEventListener('change', updateAudience, { signal }); updateAudience();
        if (chosen.message || chosen.handout || chosen.quest || chosen.roll) form.append(field('Audience', audience), playerField);
        const [includeSound, soundToggle] = checkbox('Add a sound when activated', 'interactivePresetIncludeSound'); includeSound.checked = saved.includeSound === true;
        const track = make('select'); track.dataset.interactivePresetSound = ''; track.append(new Option(t('Choose a sound'), ''));
        for (const entry of sounds) track.append(new Option(entry.name || entry.id, entry.id)); track.value = saved.trackId || '';
        const volume = make('input'); volume.type = 'number'; volume.min = '0'; volume.max = '1'; volume.step = '.05'; volume.value = String(saved.volume ?? .7); volume.dataset.interactivePresetVolume = '';
        const soundFields = make('div', 'interactive-presets__options'); soundFields.append(field('Sound', track), field('Volume', volume));
        const updateSound = () => { track.disabled = volume.disabled = !includeSound.checked; track.required = volume.required = includeSound.checked; };
        includeSound.addEventListener('change', updateSound, { signal }); updateSound(); form.append(soundToggle, soundFields);
        if (!sounds.length) form.append(make('p', 'blueprint-templates__hint', t('No sounds are available. Add a sound to the campaign first.')));
        const [includeImage, imageToggle] = checkbox('Use an active image', 'interactivePresetIncludeImage');
        includeImage.checked = !element?.empty && saved.includeImage === true; includeImage.disabled = element?.empty === true;
        const image = make('select'); image.dataset.interactivePresetImage = ''; image.append(new Option(t('Choose an image'), ''));
        for (const entry of images) image.append(new Option(entry.name || entry.id, entry.id)); image.value = saved.assetId || '';
        const updateImage = () => { image.disabled = !includeImage.checked || includeImage.disabled; image.required = includeImage.checked && !includeImage.disabled; };
        includeImage.addEventListener('change', updateImage, { signal }); updateImage(); form.append(imageToggle, field('Active image', image));
        form.append(make('p', 'blueprint-templates__hint', t(element?.empty ? 'Empty Objects cannot receive images.' : 'The original image is kept for the inactive state.')));
        if (!images.length && !element?.empty) form.append(make('p', 'blueprint-templates__hint', t('No object images are available. Add an object image to this project first.')));
        const actions = make('div', 'blueprint-templates__actions');
        actions.append(button('Apply object preset', () => form.requestSubmit(), 'blueprint-templates__primary'));
        content.append(form, make('p', 'blueprint-templates__hint', t('Applying a preset replaces this object’s Blueprint.')), actions);
        remember = () => values.set(chosen.id, { doorId: door.value, journalId: journal.value, text: text.value, expression: expression.value,
            label: rollLabel.value, visibility: visibility.value, seconds: Number(seconds.value), scope: audience.value, playerId: player.value,
            includeSound: includeSound.checked, trackId: track.value, volume: Number(volume.value), includeImage: includeImage.checked, assetId: image.value });
        form.addEventListener('submit', event => {
            event.preventDefault(); if (busy || !form.reportValidity()) return; remember();
            try {
                const result = createInteractiveObjectPreset(chosen.id, { ...values.get(chosen.id), doorId: chosen.door ? door.value : '', journalId: journal.value,
                    text: chosen.message ? text.value : undefined, audience: audience.value === 'user' ? { scope: 'users', userIds: [player.value] } : { scope: audience.value }, t });
                const authored = Object.values(element?.blueprint?.graphs || {}).some(isMeaningfulBlueprintGraph)
                    || Object.values(element?.blueprint?.states || {}).some(state => state.appearance !== 'inherit');
                if (authored) confirm(result); else void apply(result);
            } catch (error) { status.textContent = t(error.message); }
        }, { signal });
    }
    async function apply(result) {
        if (busy || signal.aborted) return;
        busy = true;
        const controls = new Map([...modal.querySelectorAll('button,input,select,textarea')].map(control => [control, control.disabled]));
        for (const control of controls.keys()) control.disabled = true;
        try { await onApply(result); if (!signal.aborted) modal.close(true); }
        catch (error) { if (!signal.aborted) status.textContent = t(error.message || 'Could not apply the object preset.'); }
        finally { busy = false; if (!signal.aborted) for (const [control, disabled] of controls) control.disabled = disabled; }
    }
    function confirm(result) {
        content.replaceChildren(make('h3', '', t('Replace this object’s behavior?')),
            make('p', 'blueprint-templates__hint', t('Its current states and nodes will be replaced. You can undo this change.')));
        const actions = make('div', 'blueprint-templates__actions');
        actions.append(button('Cancel', render), button('Replace and apply', () => void apply(result), 'blueprint-templates__primary'));
        content.append(actions); actions.querySelector('button').focus();
    }
    modal.addEventListener('close', () => abort.abort(), { once: true });
    parentSignal?.addEventListener('abort', () => modal.close(true), { signal, once: true });
    render(); return mountModal(modal, { nested: true, canClose: () => !busy });
}
