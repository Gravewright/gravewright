/** A non-modal disclosure: existing panel buttons keep their actions and shortcuts. */
export function mountDockMenu(table) {
    const toggle = table.querySelector('[data-dock-menu-toggle]');
    const panel = table.querySelector('[data-dock-overflow]');
    if (!toggle || !panel) return () => {};
    const abort = new AbortController(), { signal } = abort;
    const buttons = () => [...panel.querySelectorAll('button')].filter(button =>
        !button.disabled && button.getAttribute('aria-disabled') !== 'true' && !button.hidden && button.getClientRects().length);
    function close(restore = false) {
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        if (restore) toggle.focus();
    }
    toggle.addEventListener('click', () => {
        if (!panel.hidden) return close();
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        buttons()[0]?.focus();
    }, { signal });
    panel.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (button && !button.disabled && button.getAttribute('aria-disabled') !== 'true') {
            // Do not steal focus from the window opened by the selected action.
            close();
            if (panel.contains(document.activeElement)) toggle.focus();
        }
    }, { signal });
    document.addEventListener('pointerdown', event => {
        if (!panel.hidden && !panel.contains(event.target) && !toggle.contains(event.target)) close();
    }, { capture: true, signal });
    document.addEventListener('focusin', event => {
        if (!panel.hidden && !panel.contains(event.target) && !toggle.contains(event.target)) close();
    }, { signal });
    window.addEventListener('keydown', event => {
        if (panel.hidden || event.defaultPrevented) return;
        if (event.key === 'Escape') {
            event.preventDefault(); event.stopImmediatePropagation(); close(true);
        } else if (panel.contains(event.target) && ['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
            const choices = buttons(), index = choices.indexOf(document.activeElement);
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? choices.length - 1
                : (index + (event.key === 'ArrowDown' ? 1 : -1) + choices.length) % choices.length;
            event.preventDefault(); choices[next]?.focus();
        }
    }, { capture: true, signal });
    return () => { abort.abort(); close(); };
}
