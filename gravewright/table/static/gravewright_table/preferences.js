import { renderingPreferences } from '/static/gravewright_maps/render-profile.js';

const table = document.querySelector('#table-workspace');
if (table) {
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
    window.addEventListener('pagehide', event => { if (!event.persisted) stop(); });
}

if(table?.dataset.rendererDebug==='true'){
    let last=0;
    window.addEventListener('gravewright:map-viewport',()=>{
        if(performance.now()-last<1000)return;
        last=performance.now();
        console.debug('[Gravewright renderer]',window.gravewrightMaps?.board?.streamingStats());
    });
}
