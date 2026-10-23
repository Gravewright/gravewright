import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { mountModal } from '/static/gravewright_table/modal.js';

const root = document.querySelector('#table-workspace');
if (root && !root.dataset.detachedChat?.includes('true')) {
    const abort = new AbortController(), { signal } = abort;
    const translator = createTranslator(), t = key => translator.t(key);
    const preference = root.querySelector('[data-automation-camera-preference]');
    const storageKey = `gravewright.automation.camera.${root.dataset.profileId}`;
    const seen = new Set(), rollViews = new Map();
    let followCamera = false, modal, messages, closeButton, title;
    let modalAbort;
    function readPreference() {
        try { followCamera = localStorage.getItem(storageKey) === 'true'; } catch { followCamera = false; }
        if (preference) preference.checked = followCamera;
    }
    readPreference();
    preference?.addEventListener('change', () => {
        followCamera = preference.checked;
        try { localStorage.setItem(storageKey, String(followCamera)); } catch {}
    }, { signal });
    window.addEventListener('storage', event => { if (event.key === storageKey || event.key === null) readPreference(); }, { signal });
    const make = (tag, className, text) => {
        const element = document.createElement(tag); if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    };
    function refreshLabels() {
        if (!modal) return;
        const heading = t(rollViews.size ? 'Dice roll request' : 'Message');
        modal.setAttribute('aria-label', heading); title.textContent = heading; closeButton.textContent = t('Close');
        for (const view of rollViews.values()) view.refresh();
    }
    function ensureModal() {
        if (!modal) {
            modalAbort = new AbortController();
            modal = make('section', 'table-form-modal automation-presentation');
            modal.dataset.automationPresentation = ''; modal.setAttribute('aria-label', t('Message'));
            const header = make('header'); title = make('strong', '', t('Message'));
            closeButton = make('button', '', t('Close')); closeButton.type = 'button';
            closeButton.dataset.presentationClose = ''; closeButton.addEventListener('click', () => modal.close(), { signal: modalAbort.signal });
            messages = make('div', 'automation-presentation__messages'); messages.setAttribute('aria-live', 'polite');
            header.append(title, closeButton); modal.append(header, messages);
            modal.addEventListener('close', () => {
                modalAbort.abort(); rollViews.clear(); modal = messages = closeButton = title = null;
            }, { once: true });
            mountModal(modal, { nested: true });
        }
    }
    function appendEntry(entry) {
        messages.append(entry);
        while (messages.children.length > 20) {
            const first = messages.firstElementChild;
            rollViews.get(first)?.dispose(); rollViews.delete(first); first.remove();
        }
        refreshLabels();
        entry.scrollIntoView({ block: 'nearest' });
    }
    function showMessage(text) {
        ensureModal();
        const message = make('p', '', text); message.translate = false;
        appendEntry(message);
    }
    function showRoll(value) {
        const opening = !modal;
        ensureModal();
        const card = make('form', 'automation-presentation__roll'); card.dataset.presentationRoll = value.id;
        const heading = make('strong', '', value.label || ''); heading.translate = false; heading.hidden = !value.label;
        const expression = make('code', '', value.expression); expression.translate = false;
        const audience = make('span', 'automation-presentation__audience');
        const submit = make('button'); submit.type = 'submit'; submit.dataset.presentationRollSubmit = '';
        const result = make('p', 'automation-presentation__result'); result.setAttribute('role', 'status'); result.hidden = true;
        const error = make('p'); error.setAttribute('role', 'alert'); error.hidden = true;
        const actions = make('div', 'automation-presentation__actions'); actions.append(audience, submit);
        card.append(heading, expression, actions, result, error);
        let busy = false, done = false, disposed = false;
        const refresh = () => {
            audience.textContent = t(value.visibility === 'gm' ? 'To GM' : 'Public');
            submit.textContent = t(busy ? 'Rolling…' : 'Roll'); submit.disabled = busy || done;
            if (done) result.textContent = t('Roll sent to chat.');
        };
        const submitRoll = async event => {
            event.preventDefault();
            if (busy || done || disposed) return;
            busy = true; error.hidden = true; error.textContent = ''; card.setAttribute('aria-busy', 'true'); refresh();
            try {
                if (!window.gravewrightRealtime?.roll) throw new Error('Connect to the table before rolling.');
                // The event identifies one logical roll per recipient, including retries
                // and another tab receiving the same presentation. Keep its scene fixed.
                await window.gravewrightRealtime.roll({ expression: value.expression, label: value.label || '', visibility: value.visibility },
                    { requestId: value.id, mapId: value.sceneId });
                if (disposed || !card.isConnected) return;
                done = true; result.hidden = false;
            } catch (failure) {
                if (disposed || !card.isConnected) return;
                error.textContent = t(failure?.message || 'The roll could not be submitted.'); error.hidden = false;
            } finally {
                if (!disposed && card.isConnected) {
                    busy = false; card.setAttribute('aria-busy', 'false'); refresh();
                    if (done && document.activeElement === submit) closeButton?.focus();
                }
            }
        };
        const modalSignal = modalAbort.signal;
        const dispose = () => {
            disposed = true; card.removeEventListener('submit', submitRoll); modalSignal.removeEventListener('abort', dispose);
        };
        card.addEventListener('submit', submitRoll);
        modalSignal.addEventListener('abort', dispose, { once: true });
        rollViews.set(card, { refresh, dispose });
        appendEntry(card);
        if (opening) submit.focus();
    }
    window.addEventListener('gravewright:api-event', ({ detail }) => {
        if (detail?.type !== 'automation.presentation') return;
        const value = detail.payload;
        if (!value || value.tableId !== root.dataset.tableId || typeof value.id !== 'string' || seen.has(value.id)
            || typeof value.sceneId !== 'string' || !['message', 'handout', 'camera', 'roll', 'mindmap'].includes(value.type)) return;
        // Repeated socket delivery must never reopen a window or repeat a camera motion.
        seen.add(value.id); if (seen.size > 256) seen.delete(seen.values().next().value);
        if (value.type === 'message' && typeof value.text === 'string' && [...value.text].length <= 2000) showMessage(value.text);
        if (value.type === 'roll' && root.dataset.role !== 'streamer' && typeof value.expression === 'string'
            && value.expression.trim() && [...value.expression].length <= 512
            && (value.label === undefined || typeof value.label === 'string' && [...value.label].length <= 48)
            && ['public', 'gm'].includes(value.visibility)) showRoll(value);
        if (value.type === 'handout' && typeof value.journalId === 'string') window.gravewrightJournals?.open(value.journalId);
        if (value.type === 'mindmap' && typeof value.mindMapId === 'string'
            && (value.nodeId === null || value.nodeId === undefined || typeof value.nodeId === 'string'))
            window.gravewrightMindMaps?.open(value.mindMapId, value.nodeId);
        if (value.type === 'camera' && followCamera && window.gravewrightMaps?.current?.id === value.sceneId
            && Number.isFinite(value.x) && Number.isFinite(value.y)) window.gravewrightMaps?.board?.ping({ x: value.x, y: value.y }, true);
    }, { signal });
    const stopTranslation = translator.onChange(refreshLabels);
    signal.addEventListener('abort', stopTranslation, { once: true });
    window.addEventListener('pagehide', event => { if (!event.persisted) { modal?.close(true); abort.abort(); } }, { signal });
}
