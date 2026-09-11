// JournalPdf.vue behavior with the original local PDF.js renderer.
export async function pdfView(host, assetId, title, clone, ticket) {
    const section = clone('pdf');
    host.append(section);
    section.setAttribute('aria-label', title);
    section.querySelector('strong').textContent = title;
    const canvasHost = section.querySelector('.journal-pdf__canvas'), error = section.querySelector('[role=alert]');
    let document, loading, task, closed = false, generation = 0, page = 1, zoom = 1, matches = [], match = 0;
    const fail = text => { error.hidden = false; error.textContent = text; };
    async function render() { const current = ++generation; task?.cancel(); if (!document)
        return; try {
        const p = await document.getPage(page);
        if (closed || current !== generation)
            return;
        const viewport = p.getViewport({ scale: zoom });
        const ratio = Math.min(window.devicePixelRatio || 1, 2);
        const canvas = host.ownerDocument.createElement('canvas');
        canvas.width = Math.floor(viewport.width * ratio);
        canvas.height = Math.floor(viewport.height * ratio);
        canvas.style.width = viewport.width + 'px';
        canvas.style.height = viewport.height + 'px';
        canvasHost.replaceChildren(canvas);
        section.querySelector('[data-pdf-count]').textContent = `${page} / ${document.numPages}`;
        section.querySelector('[data-pdf=prev]').disabled = page <= 1;
        section.querySelector('[data-pdf=next]').disabled = page >= document.numPages;
        task = p.render({ canvasContext: canvas.getContext('2d'), viewport, transform: [ratio, 0, 0, ratio, 0, 0] });
        await task.promise;
    }
    catch (e) {
        if (!closed && e.name !== 'RenderingCancelledException')
            fail('Could not render this page.');
    } }
    section.addEventListener('click', e => { const action = e.target.closest('[data-pdf]')?.dataset.pdf; if (!action || !document)
        return; if (action === 'prev')
        page = Math.max(1, page - 1); if (action === 'next')
        page = Math.min(document.numPages, page + 1); if (action === 'out')
        zoom = Math.max(.1, zoom * .8); if (action === 'in')
        zoom = Math.min(8, zoom * 1.25); if (action === 'match' && matches.length) {
        match = (match + 1) % matches.length;
        page = matches[match];
        section.querySelector('[data-pdf=match]').textContent = `${match + 1}/${matches.length}`;
    } void render(); });
    section.querySelector('form').addEventListener('submit', async (e) => { e.preventDefault(); if (!document)
        return; const needle = section.querySelector('input').value.trim().toLowerCase(); matches = []; match = 0; error.hidden = true; if (!needle)
        return; for (let i = 1; i <= document.numPages; i++) {
        const p = await document.getPage(i);
        if (closed)
            return;
        const text = await p.getTextContent();
        if (closed)
            return;
        if (text.items.map(i => i.str || '').join(' ').toLowerCase().includes(needle))
            matches.push(i);
    } const button = section.querySelector('[data-pdf=match]'); button.hidden = !matches.length; button.textContent = `1/${matches.length}`; if (matches.length) {
        page = matches[0];
        void render();
    }
    else
        fail('No results found.'); });
    import('./vendor/pdf.mjs').then(async (lib) => { if (closed)
        return; lib.GlobalWorkerOptions.workerSrc = '/static/gravewright_journals/vendor/pdf.worker.mjs'; loading = lib.getDocument({ url: ticket ? `/game/handouts/presentation/${encodeURIComponent(ticket)}/asset/${assetId}` : `/game/journal/asset/${assetId}`, isEvalSupported: false }); document = await loading.promise; if (closed) {
        await document.destroy();
        return;
    } await render(); }).catch(() => { if (!closed)
        fail('Could not open the PDF.'); });
    return () => { closed = true; generation++; task?.cancel(); void loading?.destroy(); };
}
