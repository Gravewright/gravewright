/** Ephemeral peer pointers in scene coordinates, with smooth screen rendering. */
export function mountMapPointers(table, { getScene, send }) {
    const frame = table.querySelector('.game-table__scene-frame');
    if (!frame) return () => {};
    const abort = new AbortController(), { signal } = abort;
    const layer = document.createElement('div');
    layer.className = 'map-pointers'; layer.setAttribute('aria-hidden', 'true'); frame.append(layer);
    const visibility = table.querySelector('[data-map-pointer-visibility]');
    const sharing = table.querySelector('[data-map-pointer-sharing]');
    const preferenceError = table.querySelector('[data-map-pointer-preference-error]');
    const preferenceKey = `gravewright.map-pointers.${table.dataset.profileId}`;
    const peers = new Map();
    let showPointers = true, sharePointer = true;
    let local, sentMap, viewedMap, sending = 0, painting = 0, lastFrame = 0, lastPublished = 0;
    function remove(id) { peers.get(id)?.node.remove(); peers.delete(id); }
    function clear() { for (const id of peers.keys()) remove(id); }
    function canShare() { return sharePointer && table.dataset.role !== 'streamer' && table.dataset.tableLayer === 'game'; }
    function applyPreference(value) {
        showPointers = value?.show !== false; sharePointer = value?.share !== false;
        if (visibility) visibility.checked = showPointers;
        if (sharing) sharing.checked = sharePointer;
        layer.hidden = !showPointers;
        if (!showPointers && painting) { cancelAnimationFrame(painting); painting = 0; }
        if (!canShare()) leave();
        repaint();
    }
    function readPreference() {
        let value;
        try { value = JSON.parse(localStorage.getItem(preferenceKey)); } catch {}
        applyPreference(value);
    }
    function savePreference() {
        if (preferenceError) preferenceError.hidden = true;
        try {
            const value = { show: visibility?.checked ?? showPointers, share: sharing?.checked ?? sharePointer };
            localStorage.setItem(preferenceKey, JSON.stringify(value));
            applyPreference(value);
        } catch {
            if (visibility) visibility.checked = showPointers;
            if (sharing) sharing.checked = sharePointer;
            if (preferenceError) preferenceError.hidden = false;
        }
    }
    function stop() {
        clearTimeout(sending); sending = 0; local = undefined;
    }
    function pause() {
        // Keep the last scene position when another window or tab takes focus.
        // Flush a queued move before suspending publication in the background.
        clearTimeout(sending); sending = 0;
        if (local) publish(true);
        stop();
    }
    function leave() {
        stop();
        if (sentMap) send({ mapId: sentMap, position: null });
        sentMap = undefined;
    }
    function publish(final = false) {
        sending = 0;
        const wait = 100 - (performance.now() - lastPublished);
        if (!final && wait > 0 && local) { sending = setTimeout(publish, wait); return; }
        const { map, board } = getScene();
        if (!local || !canShare() || map?.id !== local.mapId) { leave(); return; }
        const point = board?.worldAt({ x: local.x, y: local.y });
        if (!point || point.x < 0 || point.y < 0 || point.x > map.width || point.y > map.height) { leave(); return; }
        lastPublished = performance.now();
        if (send({ mapId: map.id, position: point })) sentMap = map.id;
    }
    function queue() { if (!sending && local) sending = setTimeout(publish, Math.max(0, 100 - (performance.now() - lastPublished))); }
    function move(event) {
        const { map, board } = getScene();
        if (!canShare() || !map || !board || event.pointerType === 'touch'
            || !event.target.closest('.game-board')
            || event.target.closest('button,input,select,textarea,[role=dialog],.gw-window')) { leave(); return; }
        local = { mapId: map.id, x: event.clientX, y: event.clientY }; queue();
    }
    function paint(now) {
        painting = 0;
        const { map, board } = getScene(), view = board?.viewport();
        const surface = frame.querySelector('.game-board__surface');
        if (!map || !view || !surface) { clear(); return; }
        const bounds = surface.getBoundingClientRect(), origin = frame.getBoundingClientRect();
        const fraction = 1 - Math.exp(-Math.min(64, now - lastFrame) / 70);
        lastFrame = now;
        let moving = false;
        for (const peer of peers.values()) {
            if (peer.mapId !== map.id) { peer.node.hidden = true; continue; }
            const dx = peer.target.x - peer.current.x, dy = peer.target.y - peer.current.y;
            if (Math.hypot(dx, dy) * view.scale < .3) peer.current = { ...peer.target };
            else { peer.current.x += dx * fraction; peer.current.y += dy * fraction; moving = true; }
            const x = view.x + peer.current.x * view.scale, y = view.y + peer.current.y * view.scale;
            peer.node.hidden = x < 0 || y < 0 || x > bounds.width || y > bounds.height;
            peer.node.style.transform = `translate(${bounds.left - origin.left + x}px, ${bounds.top - origin.top + y}px)`;
        }
        if (moving) painting = requestAnimationFrame(paint);
    }
    function repaint() {
        if (!showPointers || painting || !peers.size) return;
        lastFrame = performance.now(); painting = requestAnimationFrame(paint);
    }
    function receive({ detail: packet }) {
        const { map } = getScene();
        if (!packet || packet.userId === table.dataset.profileId || packet.mapId !== map?.id) return;
        if (!packet.position) {
            if (peers.get(packet.userId)?.connectionId === packet.connectionId) remove(packet.userId);
            return;
        }
        if (!Number.isFinite(packet.position.x) || !Number.isFinite(packet.position.y)) return;
        let peer = peers.get(packet.userId);
        if (!peer) {
            const node = document.createElement('span'), dot = document.createElement('span'), label = document.createElement('span');
            node.className = 'map-pointer'; node.dataset.mapPointer = packet.userId; node.hidden = true;
            node.translate = false;
            dot.className = 'map-pointer__dot'; label.className = 'map-pointer__name';
            node.append(dot, label); layer.append(node);
            peer = { node, dot, label, current: { ...packet.position } }; peers.set(packet.userId, peer);
        }
        Object.assign(peer, { mapId: packet.mapId, connectionId: packet.connectionId,
            target: { ...packet.position } });
        peer.label.textContent = packet.name || '';
        peer.dot.style.backgroundColor = /^#[0-9a-f]{6}$/i.test(packet.color) ? packet.color : '#f2c679';
        repaint();
    }
    function sceneChanged() {
        const id = getScene().map?.id;
        if (id !== viewedMap) { leave(); clear(); viewedMap = id; }
        else repaint();
    }
    const timer = setInterval(() => {
        // Departure and disconnect packets own removal. Browser throttling or
        // a brief transport delay must not make a stationary pointer flicker.
        if (local && !sending) publish();
    }, 1000);
    const observer = new MutationObserver(() => { if (!canShare()) leave(); });
    observer.observe(table, { attributes: true, attributeFilter: ['data-table-layer'] });
    function dispose() {
        leave(); clear(); clearInterval(timer); observer.disconnect(); abort.abort();
        if (painting) cancelAnimationFrame(painting);
        layer.remove();
    }
    readPreference();
    visibility?.addEventListener('change', savePreference, { signal });
    sharing?.addEventListener('change', savePreference, { signal });
    window.addEventListener('storage', event => {
        if (event.key === preferenceKey || event.key === null) readPreference();
    }, { signal });
    frame.addEventListener('pointermove', move, { signal, passive: true, capture: true });
    frame.addEventListener('pointerleave', event => { if (event.relatedTarget) leave(); else pause(); }, { signal });
    window.addEventListener('blur', pause, { signal });
    window.addEventListener('resize', () => { pause(); repaint(); }, { signal });
    window.addEventListener('gravewright:map-cursor', receive, { signal });
    window.addEventListener('gravewright:module-scene', sceneChanged, { signal });
    window.addEventListener('gravewright:map-viewport', () => { queue(); repaint(); }, { signal });
    window.addEventListener('gravewright:player-preferences', queue, { signal });
    window.addEventListener('gravewright:connected', () => { clear(); queue(); }, { signal });
    window.addEventListener('gravewright:disconnected', () => { leave(); clear(); }, { signal });
    window.addEventListener('gravewright:presence', ({ detail }) => {
        const present = new Set((detail.members || []).map(member => member.id));
        for (const id of peers.keys()) if (!present.has(id)) remove(id);
    }, { signal });
    document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); }, { signal });
    window.addEventListener('pagehide', event => { if (event.persisted) sceneChanged(); else dispose(); }, { signal });
    return dispose;
}
