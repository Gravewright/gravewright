import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { mountModal } from '/static/gravewright_table/modal.js';

const root = document.querySelector('#table-workspace');
if (root && !root.dataset.detachedChat?.includes('true')) {
    const abort = new AbortController(), { signal } = abort;
    const translator = createTranslator(), t = key => translator.t(key);
    const preference = root.querySelector('[data-automation-camera-preference]');
    const storageKey = `gravewright.automation.camera.${root.dataset.profileId}`;
    const seen = new Set();
    let followCamera = false, modal, messages, closeButton, title;
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
    function showMessage(text) {
        if (!modal) {
            modal = make('section', 'table-form-modal automation-presentation');
            modal.dataset.automationPresentation = ''; modal.setAttribute('aria-label', t('Message'));
            const header = make('header'); title = make('strong', '', t('Message'));
            closeButton = make('button', '', t('Close')); closeButton.type = 'button';
            closeButton.dataset.presentationClose = ''; closeButton.addEventListener('click', () => modal.close());
            messages = make('div', 'automation-presentation__messages'); messages.setAttribute('aria-live', 'polite');
            header.append(title, closeButton); modal.append(header, messages);
            modal.addEventListener('close', () => { modal = messages = closeButton = title = null; }, { once: true });
            mountModal(modal, { nested: true });
        }
        const message = make('p', '', text); message.translate = false;
        messages.append(message);
        while (messages.children.length > 20) messages.firstElementChild.remove();
        message.scrollIntoView({ block: 'nearest' });
    }
    window.addEventListener('gravewright:api-event', ({ detail }) => {
        if (detail?.type !== 'automation.presentation') return;
        const value = detail.payload;
        if (!value || value.tableId !== root.dataset.tableId || typeof value.id !== 'string' || seen.has(value.id)
            || typeof value.sceneId !== 'string' || !['message', 'handout', 'camera'].includes(value.type)) return;
        // Repeated socket delivery must never reopen a window or repeat a camera motion.
        seen.add(value.id); if (seen.size > 256) seen.delete(seen.values().next().value);
        if (value.type === 'message' && typeof value.text === 'string' && [...value.text].length <= 2000) showMessage(value.text);
        if (value.type === 'handout' && typeof value.journalId === 'string') window.gravewrightJournals?.open(value.journalId);
        if (value.type === 'camera' && followCamera && window.gravewrightMaps?.current?.id === value.sceneId
            && Number.isFinite(value.x) && Number.isFinite(value.y)) window.gravewrightMaps?.board?.ping({ x: value.x, y: value.y }, true);
    }, { signal });
    window.addEventListener('gravewright:i18n-catalog', () => {
        if (!modal) return;
        modal.setAttribute('aria-label', t('Message')); title.textContent = t('Message'); closeButton.textContent = t('Close');
    }, { signal });
    window.addEventListener('pagehide', event => { if (!event.persisted) { modal?.close(true); abort.abort(); } }, { signal });
}
