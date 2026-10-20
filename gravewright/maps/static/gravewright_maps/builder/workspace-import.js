/** Asset import/edit modals; workspace persistence owns permanent removal. */
export function createWorkspaceImport({ root, state, t, locale, signal, isBusy, isDisposed,
    beforeOpen, modals, setBusy, api, refreshLibrary, removeAsset, renderLayers, openMapImport, library, commit }) {
    const $ = selector => root.querySelector(selector);
    const { assetInfo, assetName, assetUsedByOtherRole, classify, familyGroups, roleFor } = library;
    function openImport(asset = null) {
        if (isBusy() || state.preview || isDisposed()) return;
        beforeOpen();
        if (modals.current) return;
        const modal = $('[data-builder-import-template]').content.firstElementChild.cloneNode(true);
        const modalForm = modal.querySelector('form'), roleInput = modal.querySelector('[data-builder-import-role]');
        const familyInput = modal.querySelector('[data-builder-import-family]'), filesInput = modal.querySelector('[data-builder-upload]');
        const collectionInput = modal.querySelector('[data-builder-import-collection]'), collections = modal.querySelector('[data-builder-import-collections]');
        const nameInput = modal.querySelector('[data-builder-import-name-input]'), list = modal.querySelector('datalist');
        const remove = modal.querySelector('[data-builder-asset-remove]');
        const alert = modal.querySelector('[role=alert]'), local = new AbortController();
        let working = false, removeModal;
        const completed = new Map();
        const readyMap = modal.querySelector('[data-builder-ready-map]');
        readyMap.hidden = Boolean(asset);
        readyMap.addEventListener('click', () => { modal.close(); openMapImport(); }, { signal: local.signal });
        list.id = 'builder-families-' + crypto.randomUUID(); familyInput.setAttribute('list', list.id);
        collections.id = 'builder-collections-' + crypto.randomUUID(); collectionInput.setAttribute('list', collections.id);
        collections.replaceChildren(...[...new Set(state.document.assets.map(entry => entry.collection).filter(Boolean))]
            .sort((a, b) => a.localeCompare(b, locale())).map(name => new Option(name, name)));
        roleInput.value = asset ? roleFor(asset.id) || state.role : state.role;
        if (asset) {
            remove.hidden = false;
            modal.removeAttribute('data-builder-import-modal'); modal.dataset.builderAssetModal = '';
            modal.querySelector('strong').textContent = t('Edit asset');
            modal.querySelector('[data-builder-import-submit]').textContent = t('Save');
            modal.querySelector('[data-builder-import-files]').hidden = true; filesInput.required = false;
            modal.querySelector('[data-builder-import-name]').hidden = false; nameInput.required = true;
            nameInput.value = assetName(asset); familyInput.value = assetInfo(asset.id)?.family || '';
            collectionInput.value = assetInfo(asset.id)?.collection || '';
        }
        function families() {
            list.replaceChildren(...familyGroups(roleInput.value).map(entry => new Option(entry.name, entry.name)));
            familyInput.setCustomValidity('');
        }
        function close() { if (!working) modal.close(); }
        families();
        roleInput.addEventListener('change', families, { signal: local.signal });
        familyInput.addEventListener('input', () => familyInput.setCustomValidity(''), { signal: local.signal });
        filesInput.addEventListener('change', () => completed.clear(), { signal: local.signal });
        modal.querySelector('[data-builder-import-cancel]').addEventListener('click', close, { signal: local.signal });
        modal.querySelector('[data-builder-import-close]').addEventListener('click', close, { signal: local.signal });
        modal.addEventListener('close', () => { removeModal?.close(true); local.abort(); if (modals.current === modal) modals.current = null; }, { once: true });
        signal.addEventListener('abort', () => modal.close(true), { once: true, signal: local.signal });
        remove.addEventListener('click', () => {
            if (!asset || working || isBusy() || isDisposed() || removeModal) return;
            const confirmation = $('[data-builder-asset-remove-template]').content.firstElementChild.cloneNode(true);
            const issue = confirmation.querySelector('[role=alert]');
            confirmation.querySelector('[data-builder-asset-remove-message]').textContent = t(
                'Remove “{name}” from this campaign? This also removes it from other projects and scenes that use it.', { name: assetName(asset) });
            for (const selector of ['[data-builder-asset-remove-cancel]', '[data-builder-asset-remove-close]']) {
                confirmation.querySelector(selector).addEventListener('click', () => { if (!working) confirmation.close(); }, { signal: local.signal });
            }
            confirmation.addEventListener('close', () => { removeModal = null; }, { once: true });
            confirmation.querySelector('[data-builder-asset-remove-submit]').addEventListener('click', async () => {
                if (working || isBusy() || isDisposed()) return;
                working = true; issue.hidden = true; setBusy(true);
                for (const control of [...modal.querySelectorAll('button,input,select'), ...confirmation.querySelectorAll('button')]) control.disabled = true;
                let removed = false;
                try {
                    await removeAsset(asset);
                    removed = true;
                } catch (cause) {
                    if (cause.name !== 'AbortError' && !isDisposed()) { issue.textContent = cause.message; issue.hidden = false; }
                } finally {
                    working = false;
                    if (!isDisposed()) {
                        setBusy(false);
                        for (const control of [...modal.querySelectorAll('button,input,select'), ...confirmation.querySelectorAll('button')]) control.disabled = false;
                    }
                }
                if (!isDisposed()) {
                    if (removed) { confirmation.close(); modal.close(); $('[data-builder-import]').focus({ preventScroll: true }); }
                    else confirmation.querySelector('[data-builder-asset-remove-submit]').focus({ preventScroll: true });
                }
            }, { signal: local.signal });
            removeModal = modals.mount(confirmation, { nested: true, canClose: () => !working });
            confirmation.querySelector('form').addEventListener('submit', event => event.preventDefault(), { signal: local.signal });
        }, { signal: local.signal });
        modalForm.addEventListener('submit', async event => {
            event.preventDefault();
            if (working || isBusy() || !modalForm.reportValidity()) return;
            const role = roleInput.value, family = familyInput.value.trim(), files = [...filesInput.files];
            const collection = collectionInput.value.trim();
            const conflict = state.document.assets.some(entry => entry.family === family && family && entry.role !== role
                && (!asset || entry.assetId !== asset.id));
            if (conflict) {
                alert.textContent = t('An asset family must contain only one asset type.'); alert.hidden = false;
                familyInput.setCustomValidity(t('An asset family must contain only one asset type.'));
                familyInput.reportValidity(); return;
            }
            if (family.length > 80 || family.includes('\0') || collection.length > 80 || collection.includes('\0')) {
                alert.textContent = t('Invalid map asset metadata.'); alert.hidden = false; return;
            }
            if (asset && assetUsedByOtherRole(asset.id, role)) {
                alert.textContent = t('This asset is already used by another brush. Upload a separate copy to use a different type.'); alert.hidden = false; return;
            }
            if (!asset && files.some(file => file.size > 25 * 1024 * 1024)) {
                alert.textContent = t('Choose an image up to 25 MB.'); alert.hidden = false; return;
            }
            if (!asset && state.document.assets.length + files.length - completed.size > (state.limits.maxAssets || 256)) {
                alert.textContent = t('The map has too many assets.'); alert.hidden = false; return;
            }
            working = true; alert.hidden = true; setBusy(true);
            for (const control of modal.querySelectorAll('button,input,select')) control.disabled = true;
            let imported;
            function metadata(id) {
                classify(id, role, family);
                const entry = assetInfo(id);
                if (family) entry.family = family; else delete entry.family;
                if (collection) entry.collection = collection; else delete entry.collection;
                if (asset) entry.name = nameInput.value.trim();
                commit();
            }
            try {
                if (asset) { metadata(asset.id); imported = asset.id; }
                else {
                    for (const [index, file] of files.entries()) {
                        let id = completed.get(index);
                        if (!id) {
                            const body = new FormData(); body.append('file', file);
                            id = (await api(`/api/containers/${root.dataset.campaignId}/library/upload`, body)).id;
                            completed.set(index, id);
                        }
                        metadata(id); imported = id;
                    }
                    await refreshLibrary();
                }
            } catch (cause) {
                if (cause.name !== 'AbortError' && !isDisposed()) {
                    let message = cause.message;
                    if (completed.size) {
                        try { await refreshLibrary(); }
                        catch (refreshError) { message += '\n' + refreshError.message; }
                    }
                    alert.textContent = message; alert.hidden = false;
                }
                imported = null;
            } finally {
                working = false;
                if (!isDisposed()) {
                    setBusy(false);
                    for (const control of modal.querySelectorAll('button,input,select')) control.disabled = false;
                }
            }
            if (imported && !isDisposed()) {
                state.libraryRole = role; state.libraryFilter = role;
                if (family) library.chooseFamily(family, role); else library.chooseBrushAsset(imported, role);
                library.renderAssets(); renderLayers(); modal.close();
            }
        }, { signal: local.signal });
        modals.current = modals.mount(modal, { canClose: () => !working });
    }
    return { openImport };
}
