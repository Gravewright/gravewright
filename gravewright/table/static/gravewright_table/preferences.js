import { renderingPreferences } from '/static/gravewright_maps/render-profile.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { conditionLayout } from '/static/gravewright_tokens/quick-controls.js';
import { mountShortcuts } from './shortcuts.js';

const table = document.querySelector('#table-workspace');
if (table) {
    const stopShortcuts = mountShortcuts(table);
    const http = new HttpClient();
    const observers = [];
    function whenVisible(root, load) {
        if (!root) return;
        const observer = new IntersectionObserver(entries => {
            if (!entries.some(entry => entry.isIntersecting)) return;
            observer.disconnect();
            void load();
        });
        observers.push(observer);
        observer.observe(root);
    }
    renderingPreferences.activate(table.dataset.profileId);
    const choices = [...table.querySelectorAll('[data-render-choice]')];
    const stop = renderingPreferences.subscribe(profile => {
        for (const button of choices) {
            const selected = button.dataset.renderChoice === profile.name;
            button.setAttribute('aria-checked', String(selected));
            button.classList.toggle('house-menu__profile--on', selected);
        }
    });
    for (const button of choices)
        button.addEventListener('click', () => renderingPreferences.select(button.dataset.renderChoice));
    const language = table.querySelector('[data-table-language]');
    if (language) {
        const selector = language.querySelector('select');
        const error = language.querySelector('[role="alert"]');
        let saved = selector.value;
        language.addEventListener('submit', async event => {
            event.preventDefault();
            const body = new FormData(language);
            selector.disabled = true;
            error.hidden = true;
            try {
                const response = await fetch(language.action, {
                    method: 'POST', headers: { Accept: 'application/json' }, body,
                });
                if (!response.ok) throw new Error('language');
                saved = selector.value;
                window.location.reload();
            } catch {
                selector.value = saved;
                selector.disabled = false;
                error.hidden = false;
            }
        });
        selector.addEventListener('change', () => language.requestSubmit());
    }
    const ping = table.querySelector('[data-table-ping]');
    if (ping) {
        const color = ping.querySelector('input');
        const error = ping.querySelector('[role=alert]');
        let saved = color.value;
        function apply(value) {
            saved = color.value = value.pingColor;
            window.dispatchEvent(new CustomEvent('gravewright:player-preferences', { detail: value }));
        }
        whenVisible(ping, async () => {
            try {
                const value = await http.get('/api/player-preferences');
                apply(value);
                color.disabled = false;
            } catch { error.hidden = false; }
        });
        color.addEventListener('change', async () => {
            color.disabled = true; error.hidden = true;
            try {
                const value = await http.post('/api/player-preferences', { pingColor: color.value });
                apply(value);
            } catch { color.value = saved; error.hidden = false; }
            finally { color.disabled = false; }
        });
    }
    const conditions = [...table.querySelectorAll('[data-condition-choice]')];
    const showConditions = () => {
        for (const button of conditions) button.setAttribute('aria-pressed', String(button.dataset.conditionChoice === conditionLayout()));
    };
    for (const button of conditions) button.addEventListener('click', () => {
        try { localStorage.setItem('gravewright.conditions.anonymous', button.dataset.conditionChoice); } catch {}
        window.dispatchEvent(new CustomEvent('gravewright:condition-layout'));
    });
    showConditions();
    window.addEventListener('gravewright:condition-layout', showConditions);
    window.addEventListener('storage', showConditions);
    const marketplace = table.querySelector('[data-table-marketplace]');
    if (marketplace) {
        const button = marketplace.querySelector('[data-install-marketplace]');
        const error = marketplace.querySelector('[role=alert]');
        const render = state => {
            button.hidden = !!state.configured;
            marketplace.hidden = !!state.configured;
        };
        whenVisible(marketplace, async () => {
            try { render(await http.get('/api/marketplace/default')); }
            catch { error.hidden = false; }
        });
        button.addEventListener('click', async () => {
            button.disabled = true; error.hidden = true;
            try { render(await http.post('/api/marketplace/default')); }
            catch { error.hidden = false; }
            finally { button.disabled = false; }
        });
    }
    window.addEventListener('pagehide', event => {
        if (!event.persisted) {
            stop(); stopShortcuts(); observers.forEach(observer => observer.disconnect());
            window.removeEventListener('gravewright:condition-layout', showConditions);
            window.removeEventListener('storage', showConditions);
        }
    });
}

if(table?.dataset.rendererDebug==='true'){
    let last=0;
    window.addEventListener('gravewright:map-viewport',()=>{
        if(performance.now()-last<1000)return;
        last=performance.now();
        console.debug('[Gravewright renderer]',window.gravewrightMaps?.board?.streamingStats());
    });
}
