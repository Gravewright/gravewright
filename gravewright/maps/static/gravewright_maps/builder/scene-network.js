import { mountModal } from '/static/gravewright_table/modal.js';
import { openBlueprintEditor } from './blueprint-editor.js';
import { sceneNetwork, networkPage } from './network-model.js';

/** Browse relationships and edit the existing owner; never instantiate another rule. */
export function openSceneNetwork({ load, save, discard, campaignId, t, pick, locate, onClose, initialElementId, editInitially = false }) {
    if (!document.querySelector('link[data-scene-network-css]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet';
        link.href = new URL('./scene-network.css', import.meta.url).href; link.dataset.sceneNetworkCss = '';
        document.head.append(link);
    }
    const abort = new AbortController(), { signal } = abort;
    const make = (tag, attrs = {}, text) => {
        const element = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
        if (text !== undefined) element.textContent = text;
        return element;
    };
    const listen = (element, name, handler, options = {}) => element.addEventListener(name, handler, { signal, ...options });
    const button = (text, attrs, handler) => {
        const element = make('button', { type: 'button', ...attrs }, t(text)); listen(element, 'click', handler); return element;
    };
    const modal = make('section', { class: 'table-form-modal scene-network', 'data-scene-network': '', role: 'dialog', 'aria-label': t('Scene network') });
    const header = make('header'), title = make('strong', {}, t('Scene network'));
    header.append(title, button('Close', { 'data-network-close': '' }, () => modal.close()));
    const body = make('div', { class: 'scene-network__body' }), toolbar = make('div', { class: 'scene-network__toolbar' });
    const search = make('input', { type: 'search', maxlength: '240', placeholder: t('Search elements and events'), 'aria-label': t('Search elements and events'), 'data-network-search': '' });
    const issues = make('input', { type: 'checkbox', 'data-network-problems': '' }), issuesLabel = make('label', { class: 'scene-network__check' });
    issuesLabel.append(issues, make('span', {}, t('Missing targets')));
    const refreshButton = button('Refresh', { 'data-network-refresh': '' }, () => void refresh());
    toolbar.append(search, issuesLabel, refreshButton);
    const status = make('p', { class: 'scene-network__status', role: 'status' });
    const alert = make('p', { role: 'alert', hidden: '' });
    const layout = make('div', { class: 'scene-network__layout' });
    const canvas = make('div', { class: 'scene-network__canvas', tabindex: '0', role: 'region', 'aria-label': t('Behavior relationships'), 'data-network-canvas': '' });
    const stage = make('div', { class: 'scene-network__stage' }), plane = make('div', { class: 'scene-network__plane' });
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'scene-network__wires'); svg.setAttribute('aria-hidden', 'true');
    const cards = make('div', { class: 'scene-network__cards' }); plane.append(svg, cards); stage.append(plane); canvas.append(stage);
    const inspector = make('aside', { class: 'scene-network__inspector', 'data-network-inspector': '' });
    layout.append(canvas, inspector); body.append(toolbar, status, alert, layout);
    const footer = make('footer'), pages = make('span', { 'data-network-page-status': '' });
    const previous = button('Previous page', { 'data-network-previous': '' }, () => { page--; render(); });
    const next = button('Next page', { 'data-network-next': '' }, () => { page++; render(); });
    const zoomOut = button('Zoom out', { 'data-network-zoom-out': '' }, () => resizeZoom(zoom - .15));
    const zoomIn = button('Zoom in', { 'data-network-zoom-in': '' }, () => resizeZoom(zoom + .15));
    footer.append(previous, pages, next, zoomOut, zoomIn);
    modal.append(header, body, footer);
    let catalog = { elements: [] }, network = { nodes: [], edges: [] }, selected = initialElementId, page = 0, zoom = 1;
    let disposed = false, loading = false, child, request = 0, saving = false, width = 0, height = 0, drag, initialOpened = false;
    const kindName = node => t(node.empty === true ? 'Empty Object' : ({ door: 'Door', lever: 'Lever', torch: 'Torch', region: 'Region', image: 'Object' })[node.kind]
        || ({ light: 'Light',shader:'Shader', sound: 'Sound', asset: 'Image', handout: 'Handout', user: 'User', clock: 'Clock', clue: 'Clue', mindmap: 'Mind map' })[node.resource] || 'Element');
    const label = node => node.missing ? t('Missing target') : node.name || `${kindName(node)} ${node.ordinal || ''}`.trim();
    function resizeZoom(value) {
        const previousZoom = zoom; zoom = Math.max(.4, Math.min(1.5, value));
        const center = { x: (canvas.scrollLeft + canvas.clientWidth / 2) / previousZoom, y: (canvas.scrollTop + canvas.clientHeight / 2) / previousZoom };
        plane.style.transform = `scale(${zoom})`; stage.style.width = `${width * zoom}px`; stage.style.height = `${height * zoom}px`;
        canvas.scrollLeft = center.x * zoom - canvas.clientWidth / 2; canvas.scrollTop = center.y * zoom - canvas.clientHeight / 2;
    }
    function reveal(id) {
        selected = id; search.value = ''; issues.checked = false;
        page = Math.max(0, Math.floor(network.nodes.findIndex(node => node.id === id) / 40));
        render(); cards.querySelector(`[data-network-element="${CSS.escape(id)}"] button`)?.focus();
    }
    function inspect() {
        inspector.replaceChildren();
        const node = network.nodes.find(node => node.id === selected);
        if (!node) { inspector.append(make('p', {}, t('Choose an element to inspect its existing rules.'))); return; }
        inspector.append(make('strong', { translate: 'no' }, label(node)), make('span', {}, kindName(node)), make('code', {}, node.resourceId));
        if (node.missing) inspector.append(make('p', {}, t('This target no longer exists; repair its reference in the owning behavior.')));
        if (node.editable) {
            inspector.append(button('Edit behavior', { 'data-network-edit': node.id }, () => edit(node)));
            const events = make('div', { class: 'scene-network__events' });
            for (const event of node.events) events.append(button(event, { 'data-network-edit-event': event }, () => edit(node, event)));
            inspector.append(events);
        }
        if (locate && node.point && !node.missing) inspector.append(button('Show element on the map', { 'data-network-locate': node.id }, () => locate(node)));
        const related = network.edges.filter(edge => edge.from === node.id || edge.to === node.id);
        if (related.length) inspector.append(make('strong', {}, t('Connections')));
        for (const edge of related) {
            const target = network.nodes.find(row => row.id === (edge.from === node.id ? edge.to : edge.from));
            if (!target) continue;
            const line = button('Show element', { class: 'scene-network__related', 'data-network-related': target.id }, () => reveal(target.id));
            line.textContent = `${edge.from === node.id ? '→' : '←'} ${label(target)}`;
            line.title = edge.events.join('\n'); inspector.append(line);
        }
    }
    function render() {
        const result = networkPage(network, { query: search.value, problems: issues.checked, page }); page = result.page;
        cards.replaceChildren(); svg.replaceChildren();
        const columns = Math.max(1, Math.min(4, Math.floor((canvas.clientWidth || 900) / 300)));
        width = columns * 300 + 32; height = Math.max(280, Math.ceil(result.nodes.length / columns) * 184 + 32);
        plane.style.width = `${width}px`; plane.style.height = `${height}px`;
        svg.setAttribute('width', width); svg.setAttribute('height', height);
        const positions = new Map();
        result.nodes.forEach((node, index) => {
            const position = { x: 16 + index % columns * 300, y: 16 + Math.floor(index / columns) * 184 };
            positions.set(node.id, position);
            const card = make('article', { class: `scene-network__node${node.missing ? ' is-missing' : ''}${selected === node.id ? ' is-selected' : ''}`,
                'data-network-element': node.id, style: `left:${position.x}px;top:${position.y}px` });
            const select = button('Inspect element', { 'aria-label': `${t('Inspect element')}: ${label(node)}` }, () => { selected = node.id; render(); });
            select.replaceChildren(make('strong', { translate: 'no' }, label(node)));
            card.append(select, make('span', {}, kindName(node)), make('span', {}, t('{0} event graphs', { 0: node.events.length })));
            if (node.editable) card.append(button('Edit behavior', { 'data-network-open': node.id }, () => edit(node)));
            cards.append(card);
        });
        for (const edge of result.edges) {
            const from = positions.get(edge.from), to = positions.get(edge.to), path = document.createElementNS(svg.namespaceURI, 'path');
            const x1 = from.x + 132, y1 = from.y + 152, x2 = to.x + 132, y2 = to.y;
            path.setAttribute('d', edge.from === edge.to ? `M${x1},${y1} C${x1 + 160},${y1 + 90} ${x2 + 160},${y2 - 90} ${x2},${y2}`
                : `M${x1},${y1} C${x1},${y1 + 48} ${x2},${y2 - 48} ${x2},${y2}`);
            path.dataset.networkEdge = edge.kind;
            if (selected === edge.from || selected === edge.to) path.classList.add('is-selected'); svg.append(path);
        }
        status.textContent = loading ? t('Loading scene network...') : t('{0} elements · {1} connections', { 0: network.nodes.length, 1: network.edges.length });
        if (!result.total && !loading) status.textContent = t('No matching elements.');
        pages.textContent = t('Page {0} of {1}', { 0: page + 1, 1: result.pages });
        previous.disabled = page === 0 || loading; next.disabled = page + 1 >= result.pages || loading;
        inspect(); resizeZoom(zoom);
    }
    async function refresh() {
        const token = ++request; loading = true; refreshButton.disabled = true; alert.hidden = true;
        try {
            const result = await load(signal);
            if (disposed || token !== request) return;
            catalog = result; network = sceneNetwork(catalog); render();
        } catch (error) {
            if (disposed || signal.aborted || token !== request) return;
            alert.textContent = t(error.message || 'Could not load scene network.'); alert.hidden = false;
        } finally {
            if (!disposed && token === request) {
                loading = false; refreshButton.disabled = false; render();
                if (editInitially && !initialOpened && alert.hidden) {
                    const node = network.nodes.find(node => node.id === initialElementId);
                    if (node?.editable) { initialOpened = true; edit(node); }
                }
            }
        }
    }
    function edit(node, initialEvent) {
        if (child || loading || disposed || !node.editable) return;
        const owner = catalog.elements.find(row => row.id === node.resourceId); if (!owner) return;
        const current = { ...owner, name: label(node) }, sourceCatalog = catalog;
        const elements = catalog.elements.map(row => ({ ...row, name: row.name || label(network.nodes.find(node => node.id === row.id) || row) }));
        const assets = (catalog.assets || []).filter(asset => !asset.role || asset.role === (owner.kind === 'door' ? 'door' : 'decoration'));
        let pendingMutation;
        modal.suspend();
        child = openBlueprintEditor({ ...sourceCatalog, assets, materials: catalog.materials || catalog.assets, elements,
            campaignId, initialEvent, nested: true, element: current, t, pick,
            onSave: async blueprint => {
                const signature = JSON.stringify(blueprint);
                if (!pendingMutation || pendingMutation.signature !== signature)
                    pendingMutation = { id: crypto.randomUUID(), signature, owner: structuredClone(current) };
                saving = true;
                try {
                    const result = await save(pendingMutation.owner, blueprint, pendingMutation.id, signal);
                    // Advance optimistic revisions only from a confirmed write, never from a conflict refresh.
                    if (result?.version !== undefined) current.version = result.version;
                    if (result && Object.hasOwn(result, 'projectVersion')) current.projectVersion = result.projectVersion;
                    current.blueprint = structuredClone(blueprint);
                    pendingMutation = null;
                    await refresh();
                }
                catch (error) { if (error.code === 'conflict') await refresh(); throw error; }
                finally { saving = false; }
            },
            onClose: () => { child = null; if (!disposed) { modal.resume(); render(); } },
            onDiscard: blueprint => discard?.(current, blueprint),
        });
    }
    listen(search, 'input', () => { page = 0; render(); }); listen(issues, 'change', () => { page = 0; render(); });
    listen(canvas, 'pointerdown', event => {
        if (event.button !== 1 && (event.button !== 0 || event.target.closest('article,button'))) return;
        event.preventDefault(); drag = { id: event.pointerId, x: event.clientX, y: event.clientY, left: canvas.scrollLeft, top: canvas.scrollTop };
        canvas.setPointerCapture(event.pointerId);
    });
    listen(canvas, 'pointermove', event => { if (drag?.id === event.pointerId) { canvas.scrollLeft = drag.left - event.clientX + drag.x; canvas.scrollTop = drag.top - event.clientY + drag.y; } });
    for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) listen(canvas, event, () => { drag = null; });
    listen(canvas, 'wheel', event => { if (event.ctrlKey || event.metaKey) { event.preventDefault(); resizeZoom(zoom + (event.deltaY > 0 ? -.1 : .1)); } }, { passive: false });
    listen(window, 'resize', render);
    listen(modal, 'gravewright:sheet-flush', event => {
        // Closing the network must also wait for its nested behavior's latest write.
        child?.dispatchEvent(new CustomEvent('gravewright:sheet-flush', { detail: event.detail }));
    });
    modal.addEventListener('close', () => { disposed = true; child?.close(true); abort.abort(); onClose?.(); }, { once: true });
    mountModal(modal, { canClose: () => !saving }); render(); void refresh();
    return modal;
}
