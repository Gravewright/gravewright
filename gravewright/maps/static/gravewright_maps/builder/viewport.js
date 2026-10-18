/** A cell-space camera independent of the live table and its subscriptions. */
export function mountViewport(root, handlers = {}) {
    const viewport = root.querySelector('[data-builder-viewport]');
    const svg = root.querySelector('[data-builder-canvas]');
    const output = root.querySelector('[data-builder-zoom-level]');
    const abort = new AbortController(), { signal } = abort;
    let width = 40, height = 30, cellSize = 70, scale = 1, fitted = true;
    let center = { x: 20, y: 15 }, drag, space = false;
    function draw() {
        const bounds = viewport.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        const w = bounds.width / scale, h = bounds.height / scale;
        svg.setAttribute('viewBox', `${center.x - w / 2} ${center.y - h / 2} ${w} ${h}`);
        output.value = `${Math.round(scale / cellSize * 100)}%`;
    }
    function point(event) {
        const bounds = viewport.getBoundingClientRect();
        return { x: center.x + (event.clientX - bounds.left - bounds.width / 2) / scale,
            y: center.y + (event.clientY - bounds.top - bounds.height / 2) / scale };
    }
    function fit() {
        const bounds = viewport.getBoundingClientRect();
        scale = Math.max(.1, Math.min(Math.max(1, bounds.width - 48) / width, Math.max(1, bounds.height - 48) / height));
        fitted = true; center = { x: width / 2, y: height / 2 }; draw();
    }
    function changeZoom(factor, x, y) {
        const bounds = viewport.getBoundingClientRect();
        const next = Math.max(cellSize * .001, Math.min(cellSize * 8, scale * factor));
        const offsetX = (x ?? bounds.width / 2) - bounds.width / 2;
        const offsetY = (y ?? bounds.height / 2) - bounds.height / 2;
        center.x += offsetX * (1 / scale - 1 / next); center.y += offsetY * (1 / scale - 1 / next);
        scale = next; fitted = false; draw();
    }
    function stop(event, cancel = false) {
        if (!drag || (event?.pointerId !== undefined && event.pointerId !== drag.id)) return;
        const previous = drag; drag = undefined;
        if (viewport.hasPointerCapture(previous.id)) viewport.releasePointerCapture(previous.id);
        viewport.classList.remove('is-panning');
        if (!previous.pan) {
            if (cancel) handlers.cancel?.();
            else handlers.end?.(point(event), event);
        }
    }
    root.querySelector('[data-builder-fit]').addEventListener('click', fit, { signal });
    for (const button of root.querySelectorAll('[data-builder-zoom]')) button.addEventListener('click', () => changeZoom(button.dataset.builderZoom === 'in' ? 1.25 : .8), { signal });
    viewport.addEventListener('wheel', event => {
        event.preventDefault();
        const bounds = viewport.getBoundingClientRect();
        changeZoom(Math.exp(-Math.max(-200, Math.min(200, event.deltaY)) * .002), event.clientX - bounds.left, event.clientY - bounds.top);
    }, { signal, passive: false });
    viewport.addEventListener('contextmenu', event => event.preventDefault(), { signal });
    viewport.addEventListener('pointerdown', event => {
        if (![0, 1].includes(event.button) || drag) return;
        const pan = event.button === 1 || space || handlers.isPan?.();
        if (!pan && handlers.start?.(point(event), event) === false) return;
        event.preventDefault();
        drag = { id: event.pointerId, x: event.clientX, y: event.clientY, pan };
        viewport.setPointerCapture(event.pointerId);
        viewport.classList.toggle('is-panning', pan); viewport.focus({ preventScroll: true });
    }, { signal });
    viewport.addEventListener('pointermove', event => {
        if (!drag || drag.id !== event.pointerId) return;
        if (drag.pan) {
            center.x -= (event.clientX - drag.x) / scale; center.y -= (event.clientY - drag.y) / scale;
            fitted = false; drag.x = event.clientX; drag.y = event.clientY; draw();
        } else handlers.move?.(point(event), event);
    }, { signal });
    viewport.addEventListener('pointerup', event => stop(event), { signal });
    for (const name of ['pointercancel', 'lostpointercapture']) viewport.addEventListener(name, event => stop(event, true), { signal });
    root.addEventListener('keydown', event => {
        if (event.target.closest('input,select,textarea,button,a,summary') || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.code === 'Space') { space = true; event.preventDefault(); return; }
        if (event.key === '0' || event.key === 'Home') fit();
        else if (event.key === '+' || event.key === '=') changeZoom(1.25);
        else if (event.key === '-') changeZoom(.8);
        else if (event.key === 'Escape') stop(undefined, true);
        else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
            const step = 40 / scale;
            center.x += event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0;
            center.y += event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0;
            fitted = false; draw();
        } else return;
        event.preventDefault();
    }, { signal });
    addEventListener('keyup', event => { if (event.code === 'Space') space = false; }, { signal });
    addEventListener('blur', () => { space = false; stop(undefined, true); }, { signal });
    const observer = new ResizeObserver(() => { if (fitted) fit(); else draw(); });
    observer.observe(viewport); fit();
    return {
        get scale() { return scale; },
        resize(columns, rows, pixelsPerCell, reset = true) {
            const changed = width !== columns || height !== rows || cellSize !== pixelsPerCell;
            width = columns; height = rows; cellSize = pixelsPerCell;
            if (reset || changed) fit(); else draw();
        },
        cancel() { stop(undefined, true); },
        dispose() { stop(undefined, true); observer.disconnect(); abort.abort(); },
    };
}
