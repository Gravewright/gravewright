import { fieldBounds } from "./pdf-geometry.js";
import { text as gwText } from "./text.js";
import { loadPdfjs, } from "./pdfjs-loader.js";
import { autoMapFields, BAR_SLOTS, readCanonical, writeCanonical, } from "./mapping.js";
import { MAX_MANUAL_FIELDS, sourceKey, manualFieldKey, manualFieldSpec,
    manualFieldsForSource, manualFieldBounds, validManualField } from "./manual-fields.js";
import { normalizePdfCharacterData } from "../sheet-shape.js";
import { actionsForSource, fieldActionCandidate } from './field-actions.js';
import { bindingsForSource, bindingPath, captureFieldBindings, expandFieldFormula,
    recalculateFields } from './formulas.js';
import { captureLayout, restoreLayout, copyLayout, pasteLayout } from './layout-history.js';
export { layoutBounds, moveLayoutFields, alignLayoutFields, distributeLayoutFields, snapLayoutRect } from './layout-editor.js';
export { rasterPdf } from './raster-pdf.js';
export { fieldBounds };
export { fieldReference } from './formulas.js';
export { mappingDiagnostics } from './diagnostics.js';
export function pdfController(host, options) {
    const props = options.props;
    const box = (initial) => {
        let value = initial;
        return {
            get value() {
                return value;
            },
            set value(next) {
                value = next;
                options.repaint();
            },
        };
    };
    const derive = (read) => ({
        get value() {
            return read();
        },
    }), reactive = (v) => v, nextTick = async () => {
        options.repaint();
        await new Promise(requestAnimationFrame);
    };
    const actor = box(null);
    const mapping = box(null);
    const campaignAssets = box([]);
    const loading = box(true);
    const error = box("");
    const saveError = box("");
    const actionError = box('');
    let disposed = false, sourceGeneration = 0, renderGeneration = 0;
    const sourceAbort = new AbortController();
    const activeTab = box("ficha");
    const pageLabel = box("-");
    const statusText = box("");
    const viewerMissing = box(false);
    const fields = reactive(Object.create(null));
    const positions = reactive(Object.create(null));
    const openFieldNames = box([]);
    const pickerOpen = box(false);
    const pageHost = box();
    const isGm = derive(() => props.block.context.role === "gm");
    const canEditNow = derive(() => actor.value?.canEdit === true);
    const currentSource = box(null);
    const mappingEditing = box(false), rendering = box(false), configuring = box(false), rolling = box(false);
    const exporting = box(false);
    const pageFrames = [], renderTasks = new Set();
    const undoLayouts = [], redoLayouts = [];
    let sourceDocument = null, calculationErrors = [];
    let nativeFieldNames = [];
    let viewerDoc;
    let loadingTask;
    let exportAbort;
    function releasePdf() {
        for (const task of renderTasks) task.cancel();
        renderTasks.clear();
        pageFrames.length = 0;
        const task = loadingTask;
        loadingTask = undefined;
        viewerDoc = undefined;
        if (task)
            void task.destroy().catch(() => { });
    }
    const fieldIndex = new Map();
    let saveTimer;
    let saving = false;
    let saveQueued = false;
    function fieldValue(pdfField) {
        const spec = fields[pdfField];
        if (!spec || !actor.value)
            return "";
        const value = readCanonical(actor.value, spec.path);
        if (spec.type === "boolean")
            return Boolean(value);
        if (spec.type === "number")
            return typeof value === "number" ? value : "";
        return typeof value === "string" ? value : "";
    }
    function onFieldInput(pdfField, event) {
        const spec = fields[pdfField];
        if (!spec || spec.calculated || !actor.value || !canEditNow.value)
            return;
        const target = event.target;
        const raw = spec.type === "boolean"
            ? target.checked
            : spec.type === "number"
                ? target.value === ""
                    ? 0
                    : Number(target.value)
                : target.value;
        if (spec.manualId && spec.type === "number") {
            const message = gwText("Use a number between -1000000 and 1000000.");
            if (target.validity?.badInput || !Number.isFinite(raw) || Math.abs(raw) > 1_000_000) {
                target.setCustomValidity(message);
                target.setAttribute('aria-invalid', 'true');
                statusText.value = message;
                return;
            }
            target.setCustomValidity('');
            target.removeAttribute('aria-invalid');
            if (statusText.value === message) statusText.value = '';
        }
        writeCanonical(actor.value, spec.path, raw);
        recalculate();
        scheduleSave();
    }
    function scheduleSave() {
        if (!canEditNow.value || disposed)
            return;
        saveQueued = true;
        if (saveTimer)
            clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            saveTimer = undefined;
            void save();
        }, 400);
    }
    async function save() {
        if (!actor.value || !canEditNow.value)
            return;
        if (saving) {
            saveQueued = true;
            return;
        }
        saving = true;
        saveQueued = false;
        try {
            recalculate();
            const snapshot = JSON.parse(JSON.stringify(actor.value));
            if (props.tokenId)
                snapshot.data.token.name = snapshot.name;
            const result = await options.save(snapshot);
            actor.value.sheetVersion = result.sheetVersion;
            actor.value.version = result.version;
            saveError.value = "";
        }
        catch (reason) {
            saveError.value =
                reason.code === "conflict"
                    ? "This sheet was changed in another window. Your changes remain here. Copy anything you want to preserve before reloading."
                    : "Could not save. Your changes remain here; try again.";
            saveQueued = false;
        }
        finally {
            saving = false;
            if (saveQueued) {
                if (disposed)
                    void save();
                else
                    scheduleSave();
            }
            options.repaint();
        }
    }
    async function flush() {
        clearTimeout(saveTimer);
        while (saving || saveQueued) {
            clearTimeout(saveTimer);
            if (saving) await new Promise(resolve => setTimeout(resolve, 20));
            else await save();
        }
        if (saveError.value) throw new Error(saveError.value);
    }
    async function fetchPdfBytes(kind, id) {
        if (kind === "template")
            return new Uint8Array(await props.block.assets.bytes("assets/blank-a4.pdf"));
        const file = await props.block.host.call("asset.download", { id }, { signal: sourceAbort.signal });
        return new Uint8Array(await file.blob.arrayBuffer());
    }
    function resolveSource() {
        if (!actor.value)
            return null;
        const assetId = actor.value.data.pdf.asset;
        if (assetId)
            return { kind: "asset", id: assetId };
        const templateId = actor.value.data.pdf.template ||
            Object.keys(mapping.value?.templates ?? {})[0] ||
            "";
        if (!templateId || !mapping.value?.templates[templateId])
            return null;
        return { kind: "template", id: templateId };
    }
    async function indexFields(doc) {
        const indexed = new Map();
        indexed.documentPages = [];
        for (let number = 1; number <= doc.numPages; number += 1) {
            const page = await doc.getPage(number);
            const viewport = page.getViewport({ scale: 1 });
            if (indexed.documentPages.length < 1024 && viewport.width <= 32768 && viewport.height <= 32768)
                indexed.documentPages.push({ page: number, width: viewport.width, height: viewport.height, rotation: viewport.rotation });
            const annotations = await page.getAnnotations({ intent: "display" });
            for (const annotation of annotations) {
                if (!annotation.fieldName || annotation.subtype !== "Widget")
                    continue;
                if (!indexed.has(annotation.fieldName)) {
                    indexed.set(annotation.fieldName, {
                        page: number,
                        rect: annotation.rect,
                        fieldType: annotation.fieldType ?? "Tx",
                        readOnly: Boolean(annotation.readOnly),
                    });
                }
            }
        }
        return indexed;
    }
    function fieldTypeOf(name) {
        return fieldIndex.get(name)?.fieldType ?? "Tx";
    }
    function computeFields(source, templateFields) {
        if (!actor.value)
            return;
        const barChoices = actor.value.data.token.bars;
        Object.keys(fields).forEach((key) => delete fields[key]);
        for (const [key, info] of fieldIndex) if (info.manual) fieldIndex.delete(key);
        let next;
        if (!nativeFieldNames.length && templateFields && viewerMissing.value) {
            next = templateFields;
        }
        else {
            next = autoMapFields(nativeFieldNames, mapping.value?.templates.generic?.fields, fieldTypeOf, barChoices);
        }
        Object.assign(fields, next);
        const manual = manualFieldsForSource(actor.value.data.pdf, source);
        for (const field of manual) {
            const key = manualFieldKey(field);
            const slot = ['text', 'number'].includes(field.type)
                && BAR_SLOTS.find(slot => barChoices[slot.key] === key);
            fields[key] = { ...(slot ? { path: slot.path, type: 'number' } : manualFieldSpec(field)),
                label: field.name, manualId: field.id, multiline: field.type === 'multiline' };
            fieldIndex.set(key, { page: field.page, manual: field, readOnly: false,
                fieldType: field.type === 'checkbox' ? 'Btn' : 'Tx' });
        }
        openFieldNames.value = [...nativeFieldNames, ...manual.map(manualFieldKey)];
        for (const entry of actor.value.data.pdf.calculatedFields || [])
            if (entry.source === sourceKey(source) && fields[entry.field]) fields[entry.field].calculated = true;
        recalculate();
        for (const name of Object.keys(positions)) if (!Object.hasOwn(fields, name)) delete positions[name];
    }
    function positionFields(viewport, pageNumber, offsetTop, visiblePages) {
        for (const name of Object.keys(fields)) {
            const info = fieldIndex.get(name);
            if (!info || !visiblePages.has(info.page)) {
                positions[name] = {
                    left: 0,
                    top: 0,
                    width: 0,
                    height: 0,
                    hidden: true,
                };
                continue;
            }
            if (info.page !== pageNumber)
                continue;
            positions[name] = info.manual ? manualFieldBounds(info.manual, viewport, offsetTop)
                : fieldBounds(viewport, info.rect, offsetTop);
        }
    }
    async function render() {
        if (!viewerDoc || !pageHost.value || !actor.value) return;
        const generation = ++renderGeneration;
        for (const task of renderTasks) task.cancel();
        renderTasks.clear(); pageFrames.length = 0; rendering.value = true;
        try {
            await renderPages(generation);
        }
        catch {
            if (!disposed && generation === renderGeneration)
                statusText.value = gwText("Could not render the page.");
        }
        finally {
            if (!disposed && generation === renderGeneration) rendering.value = false;
        }
    }
    async function renderPages(generation) {
        if (!viewerDoc || !pageHost.value || !actor.value)
            return;
        const doc = viewerDoc;
        pageHost.value.replaceChildren();
        const first = Math.max(1, Math.min(doc.numPages, actor.value.data.pdf.page));
        actor.value.data.pdf.page = first;
        const last = actor.value.data.pdf.spread
            ? Math.min(first + 1, viewerDoc.numPages)
            : first;
        const visible = new Set();
        for (let number = first; number <= last; number += 1)
            visible.add(number);
        for (const name of Object.keys(fields))
            if (!visible.has(fieldIndex.get(name)?.page ?? -1))
                positions[name] = {
                    left: 0,
                    top: 0,
                    width: 0,
                    height: 0,
                    hidden: true,
                };
        let offsetTop = 0;
        for (let number = first; number <= last; number += 1) {
            const page = await doc.getPage(number);
            if (disposed || generation !== renderGeneration)
                return;
            const viewport = page.getViewport({ scale: actor.value.data.pdf.zoom });
            const canvas = pageHost.value.ownerDocument.createElement("canvas");
            canvas.className = "pdf-sheet__canvas";
            canvas.dataset.pdfPage = number;
            const ratio = window.devicePixelRatio || 1;
            canvas.width = Math.floor(viewport.width * ratio);
            canvas.height = Math.floor(viewport.height * ratio);
            canvas.style.width = `${viewport.width}px`;
            canvas.style.height = `${viewport.height}px`;
            pageHost.value.append(canvas);
            try {
                const task = page.render({
                    canvas,
                    viewport,
                    transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0],
                });
                renderTasks.add(task);
                try { await task.promise; } finally { renderTasks.delete(task); }
            }
            catch (reason) {
                if (disposed || generation !== renderGeneration)
                    return;
                statusText.value = gwText("Could not render the page.");
                return;
            }
            if (disposed || generation !== renderGeneration)
                return;
            positionFields(viewport, number, offsetTop, visible);
            pageFrames.push({ page: number, viewport, top: offsetTop });
            offsetTop += viewport.height;
        }
        pageLabel.value = `${actor.value.data.pdf.page} / ${viewerDoc.numPages}`;
    }
    async function openSource() {
        const generation = ++sourceGeneration;
        ++renderGeneration;
        const source = resolveSource();
        undoLayouts.length = redoLayouts.length = 0;
        exportAbort?.abort();
        sourceDocument = null;
        mappingEditing.value = false;
        currentSource.value = source;
        viewerMissing.value = false;
        statusText.value = "";
        openFieldNames.value = [];
        nativeFieldNames = [];
        releasePdf();
        Object.keys(fields).forEach((key) => delete fields[key]);
        if (!source)
            return;
        const templateFields = source.kind === "template"
            ? mapping.value?.templates[source.id]?.fields
            : undefined;
        try {
            const lib = await loadPdfjs(props.block.assets.url);
            const bytes = await fetchPdfBytes(source.kind, source.id);
            if (disposed || generation !== sourceGeneration)
                return;
            const task = lib.getDocument({ data: bytes, isEvalSupported: false });
            loadingTask = task;
            const doc = await task.promise;
            if (disposed || generation !== sourceGeneration) {
                await task.destroy();
                return;
            }
            viewerDoc = doc;
            const indexed = await indexFields(viewerDoc);
            if (disposed || generation !== sourceGeneration)
                return;
            fieldIndex.clear();
            for (const [key, value] of indexed) fieldIndex.set(key, value);
            nativeFieldNames = [...indexed.keys()];
            sourceDocument = { source: sourceKey(source), pageCount: doc.numPages,
                fingerprint: String(doc.fingerprints?.[0] || '').slice(0, 128), pages: indexed.documentPages };
            computeFields(source, templateFields);
            if (captureReferenceData()) scheduleSave();
            await nextTick();
            await render();
        }
        catch (reason) {
            // The sheet is data, not the rendered file: without pdf.js (or the
            // network), a template still has its hand-written field mapping, so the
            // fields keep showing — stacked, per the CSS fallback — and keep saving.
            // Only an uploaded PDF has no other source for field names.
            if (disposed || generation !== sourceGeneration)
                return;
            viewerMissing.value = true;
            statusText.value =
                reason instanceof Error
                    ? reason.message
                    : gwText("Could not open the PDF.");
            fieldIndex.clear();
            computeFields(source, templateFields);
        }
    }
    function canMap() {
        return isGm.value && canEditNow.value && !disposed && !viewerMissing.value
            && !rendering.value && Boolean(viewerDoc) && pageFrames.length > 0;
    }
    function updatePositions() {
        if (!currentSource.value || !actor.value) return;
        computeFields(currentSource.value, currentSource.value.kind === 'template'
            ? mapping.value?.templates[currentSource.value.id]?.fields : undefined);
        const visible = new Set(pageFrames.map(frame => frame.page));
        for (const frame of pageFrames) positionFields(frame.viewport, frame.page, frame.top, visible);
        options.repaint();
    }
    function recalculate() {
        if (!actor.value || !currentSource.value) return;
        const result = recalculateFields(actor.value, currentSource.value);
        calculationErrors = result.errors;
        return result;
    }
    function captureReferenceData() {
        if (!actor.value || !isGm.value || !currentSource.value) return false;
        const pdf = actor.value.data.pdf, key = sourceKey(currentSource.value);
        let changed = false;
        const rows = new Map((pdf.fieldBindings || []).filter(row => row.source === key).map(row => [row.field, row]));
        for (const row of captureFieldBindings(currentSource.value, originalFields(), fieldIndex)) rows.set(row.field, row);
        const next = [...(pdf.fieldBindings || []).filter(row => row.source !== key), ...rows.values()];
        if (next.length <= 1024 && JSON.stringify(next) !== JSON.stringify(pdf.fieldBindings || [])) {
            pdf.fieldBindings = next; changed = true;
        }
        if (sourceDocument && !(pdf.sourceMetadata || []).some(row => row.source === key) && (pdf.sourceMetadata || []).length < 64) {
            pdf.sourceMetadata = [...(pdf.sourceMetadata || []), structuredClone(sourceDocument)]; changed = true;
        }
        return changed;
    }
    function layoutChanged(before) {
        captureReferenceData();
        const after = captureLayout(actor.value, currentSource.value);
        if (JSON.stringify(before) !== JSON.stringify(after)) {
            undoLayouts.push(before); if (undoLayouts.length > 50) undoLayouts.shift();
            redoLayouts.length = 0;
        }
        updatePositions(); scheduleSave();
    }
    function addManualField(type, name, page, rectangle) {
        if (!canMap() || !mappingEditing.value || !pageFrames.some(frame => frame.page === page)) return false;
        const definitions = actor.value.data.pdf.manualFields || [];
        if (definitions.length >= MAX_MANUAL_FIELDS) {
            statusText.value = gwText('Use at most 256 manual PDF fields.'); return false;
        }
        const labels = { text: 'Text field', number: 'Number field', checkbox: 'Checkbox', multiline: 'Multiline text' };
        if (!Object.hasOwn(labels, type)) return false;
        const field = { ...rectangle, id: crypto.randomUUID(), source: sourceKey(currentSource.value),
            page, type, name: typeof name === 'string' && name.trim() ? name.trim() : gwText(labels[type]) };
        if (!validManualField(field)) return false;
        const before = captureLayout(actor.value, currentSource.value);
        actor.value.data.pdf.manualFields = [...definitions, field];
        layoutChanged(before);
        return field.id;
    }
    function updateManualField(id, patch) {
        if (!canMap() || !mappingEditing.value || !patch || typeof patch !== 'object'
            || Object.keys(patch).some(key => !['name', 'x', 'y', 'width', 'height'].includes(key))) return false;
        const field = manualFieldsForSource(actor.value.data.pdf, currentSource.value).find(field => field.id === id);
        if (!field) return false;
        const next = { ...field, ...patch };
        if (typeof next.name === 'string') next.name = next.name.trim();
        if (!validManualField(next)) return false;
        const before = captureLayout(actor.value, currentSource.value);
        actor.value.data.pdf.manualFields = actor.value.data.pdf.manualFields.map(field => field.id === id ? next : field);
        layoutChanged(before); return true;
    }
    function removeManualField(id) {
        if (!canMap() || !mappingEditing.value) return false;
        const field = manualFieldsForSource(actor.value.data.pdf, currentSource.value).find(field => field.id === id);
        if (!field) return false;
        const before = captureLayout(actor.value, currentSource.value);
        archiveManualValue(actor.value, field);
        actor.value.data.pdf.manualFields = actor.value.data.pdf.manualFields.filter(field => field.id !== id);
        if (actor.value.data.pdf.fieldActions) {
            const source = sourceKey(currentSource.value), key = manualFieldKey(field);
            actor.value.data.pdf.fieldActions = actor.value.data.pdf.fieldActions.filter(action => action.source !== source || action.field !== key);
        }
        if (actor.value.data.pdf.calculatedFields)
            actor.value.data.pdf.calculatedFields = actor.value.data.pdf.calculatedFields.filter(row => row.source !== sourceKey(currentSource.value) || row.field !== manualFieldKey(field));
        for (const [slot, key] of Object.entries(actor.value.data.token.bars)) {
            if (key === manualFieldKey(field)) actor.value.data.token.bars[slot] = '';
        }
        layoutChanged(before); return true;
    }
    function editManualFields(edits) {
        if (!canMap() || !mappingEditing.value || !Array.isArray(edits) || !edits.length || edits.length > 256) return false;
        const source = sourceKey(currentSource.value), before = captureLayout(actor.value, source);
        const candidate = structuredClone(actor.value), seen = new Set();
        for (const edit of edits) {
            if (!edit || seen.has(edit.id)) return false;
            seen.add(edit.id);
            const field = candidate.data.pdf.manualFields.find(row => row.source === source && row.id === edit.id);
            if (!field) return false;
            if (edit.remove === true) {
                archiveManualValue(candidate, field);
                const key = manualFieldKey(field);
                candidate.data.pdf.manualFields = candidate.data.pdf.manualFields.filter(row => row.id !== field.id);
                for (const list of ['fieldActions', 'calculatedFields'])
                    if (candidate.data.pdf[list]) candidate.data.pdf[list] = candidate.data.pdf[list].filter(row => row.source !== source || row.field !== key);
                for (const slot of BAR_SLOTS) if (candidate.data.token.bars[slot.key] === key) candidate.data.token.bars[slot.key] = '';
            } else {
                if (!edit.changes || Object.keys(edit.changes).some(key => !['x', 'y', 'width', 'height', 'name'].includes(key))) return false;
                const next = { ...field, ...edit.changes };
                if (typeof next.name === 'string') next.name = next.name.trim();
                if (!validManualField(next)) return false;
                Object.assign(field, next);
            }
        }
        actor.value.data = candidate.data;
        layoutChanged(before); return true;
    }
    function archiveManualValue(candidate, field) {
        const key = manualFieldKey(field), current = fieldValue(key);
        const value = field.type === 'number' && current === '' ? 0 : current;
        candidate.data.fields[key] = field.type === 'text' || field.type === 'multiline' ? String(value ?? '') : value;
    }
    function pasteManualFields(clipboard, offset = {}) {
        if (!canMap() || !mappingEditing.value) return false;
        const before = captureLayout(actor.value, currentSource.value);
        const { candidate, ids } = pasteLayout(actor.value, currentSource.value, clipboard,
            { ...offset, page: actor.value.data.pdf.page, pageCount: viewerDoc.numPages });
        actor.value.data = candidate.data;
        layoutChanged(before); return ids;
    }
    function moveLayoutHistory(from, to) {
        if (!canMap() || !mappingEditing.value || !from.length) return false;
        to.push(captureLayout(actor.value, currentSource.value));
        restoreLayout(actor.value, from.pop());
        updatePositions(); scheduleSave(); return true;
    }
    function canConfigureFieldActions() {
        return isGm.value && canEditNow.value && !disposed && !rendering.value
            && !configuring.value && Boolean(currentSource.value)
            && sourceKey(resolveSource()) === sourceKey(currentSource.value);
    }
    function originalFields() {
        const originals = autoMapFields(nativeFieldNames, mapping.value?.templates.generic?.fields, fieldTypeOf, {});
        for (const field of manualFieldsForSource(actor.value.data.pdf, currentSource.value))
            originals[manualFieldKey(field)] = manualFieldSpec(field);
        // Templates can still expose their authored mapping without PDF.js.
        if (viewerMissing.value && currentSource.value?.kind === 'template')
            Object.assign(originals, mapping.value?.templates[currentSource.value.id]?.fields);
        return originals;
    }
    async function configureFieldAction(name, config) {
        if (!canConfigureFieldActions() || !Object.hasOwn(fields, name))
            throw new Error('Only the GM can configure PDF field actions.');
        const source = sourceKey(currentSource.value);
        configuring.value = true;
        try {
            await flush();
            if (disposed || sourceKey(currentSource.value) !== source || !Object.hasOwn(fields, name))
                throw new Error('This field is no longer available. Reopen the character sheet.');
            captureReferenceData();
            const candidate = fieldActionCandidate(actor.value, currentSource.value, name, config, fields, originalFields());
            if (config.calculation !== undefined && typeof config.calculation !== 'string') throw new Error('Invalid calculated PDF field.');
            if (config.calculation !== undefined) {
                const calculations = (candidate.data.pdf.calculatedFields || []).filter(row => row.source !== source || row.field !== name);
                if (config.calculation.trim()) calculations.push({ source, field: name, formula: config.calculation.trim() });
                if (candidate.data.pdf.calculatedFields || config.calculation.trim()) candidate.data.pdf.calculatedFields = calculations;
            }
            recalculateFields(candidate, currentSource.value, { previous: actor.value });
            if (config.bar && fieldIndex.get(name)?.readOnly)
                throw new Error('This field cannot be linked to a token bar.');
            if (props.tokenId) candidate.data.token.name = candidate.name;
            saving = true;
            // Validate and persist before touching local data. A rejected formula
            // must leave the existing sheet and its autosave queue usable.
            const result = await options.save(candidate);
            if (!disposed) {
                undoLayouts.length = redoLayouts.length = 0;
                actor.value.name = candidate.name;
                actor.value.data = candidate.data;
                actor.value.sheetVersion = result.sheetVersion;
                actor.value.version = result.version;
                saveError.value = '';
                updatePositions();
            }
            return true;
        } catch (failure) {
            if (!disposed && failure.code === 'conflict')
                saveError.value = 'This sheet was changed in another window. Your changes remain here. Copy anything you want to preserve before reloading.';
            throw failure;
        } finally {
            saving = false;
            configuring.value = false;
            if (saveQueued && !disposed) scheduleSave();
        }
    }
    async function rollField(name) {
        if (disposed || !canEditNow.value || rolling.value || !Object.hasOwn(fields, name)) return false;
        const source = sourceKey(currentSource.value);
        rolling.value = true;
        actionError.value = '';
        try {
            await flush();
            if (disposed) return false;
            if (sourceKey(currentSource.value) !== source)
                throw new Error('This field is no longer available. Reopen the character sheet.');
            const action = actionsForSource(actor.value.data.pdf, currentSource.value)[name];
            if (!action) return false;
            const bindings = bindingsForSource(actor.value.data.pdf, currentSource.value);
            const expression = expandFieldFormula(action.formula, reference => {
                if (!bindings[reference]) throw new Error('A referenced PDF field is not available.');
                return readCanonical(actor.value, bindingPath(actor.value.data, bindings[reference]));
            }, { value: fieldValue(name) });
            const label = action.label || Array.from(fields[name]?.label || name).slice(0, 48).join('');
            await options.roll({ expression, label, visibility: 'public' }, { requestId: crypto.randomUUID() });
            if (!disposed) statusText.value = gwText('Roll sent to chat.');
            return true;
        } catch (failure) {
            if (!disposed) actionError.value = gwText(failure.message || 'Could not roll this field. Try again.');
            throw failure;
        } finally {
            rolling.value = false;
        }
    }
    async function remapFields() {
        if (!actor.value || !currentSource.value)
            return;
        computeFields(currentSource.value, currentSource.value.kind === "template"
            ? mapping.value?.templates[currentSource.value.id]?.fields
            : undefined);
        await nextTick();
        await render();
    }
    function onBarChoice(slot, event) {
        if (!actor.value || !canEditNow.value)
            return;
        actor.value.data.token.bars[slot] =
            event.target.value || undefined;
        undoLayouts.length = redoLayouts.length = 0;
        scheduleSave();
        void remapFields();
    }
    async function chooseSource(kind, id) {
        if (!actor.value)
            return;
        pickerOpen.value = false;
        if (currentSource.value?.kind === kind && currentSource.value.id === id)
            return;
        actor.value.data.pdf.asset = kind === "asset" ? id : "";
        actor.value.data.pdf.template = kind === "template" ? id : "";
        actor.value.data.pdf.page = 1;
        await save();
        await openSource();
    }
    async function nextPage() {
        if (!actor.value || !viewerDoc)
            return;
        const step = actor.value.data.pdf.spread ? 2 : 1;
        actor.value.data.pdf.page = Math.min(viewerDoc.numPages, actor.value.data.pdf.page + step);
        scheduleSave();
        await render();
    }
    async function prevPage() {
        if (!actor.value || !viewerDoc)
            return;
        const step = actor.value.data.pdf.spread ? 2 : 1;
        actor.value.data.pdf.page = Math.max(1, actor.value.data.pdf.page - step);
        scheduleSave();
        await render();
    }
    async function zoomBy(factor) {
        if (!actor.value)
            return;
        actor.value.data.pdf.zoom = Math.max(0.1, Math.min(8, actor.value.data.pdf.zoom * factor));
        scheduleSave();
        await render();
    }
    async function fitPage() {
        if (!actor.value || !viewerDoc || !pageHost.value)
            return;
        const page = await viewerDoc.getPage(actor.value.data.pdf.page);
        const unscaled = page.getViewport({ scale: 1 });
        const available = pageHost.value.parentElement?.clientHeight || unscaled.height;
        actor.value.data.pdf.zoom = Math.max(0.1, Math.min(8, available / unscaled.height));
        scheduleSave();
        await render();
    }
    async function toggleSpread() {
        if (!actor.value)
            return;
        actor.value.data.pdf.spread = !actor.value.data.pdf.spread;
        scheduleSave();
        await render();
    }
    async function download() {
        if (!currentSource.value)
            return;
        const bytes = await fetchPdfBytes(currentSource.value.kind, currentSource.value.id);
        const url = URL.createObjectURL(new Blob([new Uint8Array(bytes).buffer], { type: "application/pdf" }));
        const link = document.createElement("a");
        link.href = url;
        link.download = `${actor.value?.name || "sheet"}.pdf`;
        document.body.append(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1_000);
    }
    function exportMappingBundle() {
        if (!canConfigureFieldActions()) throw new Error('Only the GM can manage PDF mappings.');
        captureReferenceData();
        const source = sourceKey(currentSource.value), pdf = actor.value.data.pdf;
        const bundle = { format: 'gravewright.pdf-mapping', version: 1, bindings: {} };
        for (const list of ['manualFields', 'fieldActions', 'calculatedFields', 'fieldBindings'])
            bundle[list] = (pdf[list] || []).filter(row => row.source === source).map(row => {
                const { source: ignored, ...definition } = structuredClone(row); return definition;
            });
        for (const slot of BAR_SLOTS) {
            const name = actor.value.data.token.bars[slot.key];
            bundle.bindings[slot.key] = name && fields[name] ? name : '';
        }
        const document = (pdf.sourceMetadata || []).find(row => row.source === source) || sourceDocument;
        if (document) { const { source: ignored, ...metadata } = structuredClone(document); bundle.document = metadata; }
        return bundle;
    }
    async function applyMappingBundle(bundle) {
        if (!canConfigureFieldActions()) throw new Error('Only the GM can manage PDF mappings.');
        if (!bundle || bundle.format !== 'gravewright.pdf-mapping' || bundle.version !== 1)
            throw new Error('Unsupported PDF mapping format or version.');
        const source = sourceKey(currentSource.value);
        configuring.value = true;
        try {
            await flush();
            if (source !== sourceKey(currentSource.value) || disposed) throw new Error('The PDF source changed. Reload the character sheet.');
            const candidate = structuredClone(actor.value), pdf = candidate.data.pdf;
            for (const list of ['manualFields', 'fieldActions', 'calculatedFields', 'fieldBindings']) {
                if (bundle[list] !== undefined && !Array.isArray(bundle[list])) throw new Error('Invalid PDF mapping definitions.');
                const incoming = (bundle[list] || []).map(row => ({ ...structuredClone(row), source }));
                if (list === 'manualFields') {
                    const occupied = new Set((pdf.manualFields || []).filter(row => row.source !== source).map(row => row.id));
                    if (incoming.some(row => occupied.has(row.id))) throw new Error("This mapping's field identifiers are already used by another PDF.");
                }
                pdf[list] = [...(pdf[list] || []).filter(row => row.source !== source), ...incoming];
            }
            candidate.data.token.bars = Object.fromEntries(BAR_SLOTS.map(slot => [slot.key, bundle.bindings?.[slot.key] || '']));
            if (bundle.document) pdf.sourceMetadata = [...(pdf.sourceMetadata || []).filter(row => row.source !== source),
                { ...structuredClone(bundle.document), source, fingerprint: bundle.document.fingerprint || '', pages: bundle.document.pages || [] }];
            recalculateFields(candidate, currentSource.value, { previous: actor.value });
            if (props.tokenId) candidate.data.token.name = candidate.name;
            saving = true;
            const result = await options.save(candidate);
            if (!disposed) {
                actor.value.data = candidate.data;
                actor.value.version = result.version; actor.value.sheetVersion = result.sheetVersion;
                undoLayouts.length = redoLayouts.length = 0;
                saveError.value = '';
                updatePositions();
            }
            return true;
        } catch (failure) {
            if (!disposed && failure.code === 'conflict') saveError.value = 'This sheet was changed in another window. Your changes remain here. Copy anything you want to preserve before reloading.';
            throw failure;
        } finally {
            saving = false; configuring.value = false;
            if (saveQueued && !disposed) scheduleSave();
        }
    }
    async function downloadFilled() {
        if (!actor.value || !viewerDoc || disposed || exporting.value) return false;
        exporting.value = true;
        exportAbort?.abort(); exportAbort = new AbortController();
        const source = sourceKey(currentSource.value), doc = viewerDoc, signal = exportAbort.signal;
        try {
            await flush(); recalculate();
            const [{ filledPdf }, lib] = await Promise.all([
                import('/static/gravewright_pdf_system/filled-pdf.js'), loadPdfjs(props.block.assets.url),
            ]);
            if (disposed || source !== sourceKey(currentSource.value)) return false;
            const snapshotFields = structuredClone(fields), snapshotIndex = new Map(fieldIndex);
            const values = Object.fromEntries(Object.keys(snapshotFields).map(name => [name, fieldValue(name)]));
            const bytes = await filledPdf({ doc, lib, fields: snapshotFields, fieldIndex: snapshotIndex,
                value: name => values[name], color: actor.value.data.pdf.textColor,
                document: pageHost.value.ownerDocument, signal,
                onProgress: (page, total) => { statusText.value = gwText('Preparing PDF page {0} of {1}…', page, total); },
            });
            signal.throwIfAborted();
            const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
            const link = pageHost.value.ownerDocument.createElement('a');
            link.href = url; link.download = `${actor.value.name || 'sheet'}-filled.pdf`;
            link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
            statusText.value = gwText('Filled PDF downloaded.');
            return true;
        } catch (failure) {
            if (signal.aborted || disposed) return false;
            actionError.value = gwText(failure.message || 'Could not export the filled PDF.');
            throw failure;
        } finally { exporting.value = false; }
    }
    async function load() {
        try {
            const [value, config, catalog] = await Promise.all([
                options.read(),
                props.block.assets.json("assets/pdf-fields.gw.json"),
                props.block.host.call("asset.list", {}),
            ]);
            if (disposed)
                return;
            actor.value = { ...value, data: normalizePdfCharacterData(value.data) };
            mapping.value = config;
            campaignAssets.value = catalog.items;
        }
        catch (e) {
            error.value = e.message;
        }
        finally {
            loading.value = false;
        }
        await nextTick();
        await openSource();
    }
    async function uploadPdf(event) {
        const input = event.target;
        const file = input.files?.[0];
        input.value = "";
        if (!file || !isGm.value)
            return;
        try {
            const body = await props.block.host.call("asset.upload", { file });
            if (disposed)
                return;
            campaignAssets.value = [...campaignAssets.value, body];
            await chooseSource("asset", body.id);
        }
        catch (cause) {
            saveError.value = gwText(cause.message || "Could not upload the PDF.");
        }
    }
    function leaving(event) {
        if (saving || saveQueued || saveError.value) {
            event.preventDefault();
        }
    }
    function noteDocument(value) {
        return typeof value === "object" ? value : undefined;
    }
    function setNote(key, value) {
        if (actor.value && canEditNow.value) {
            actor.value.data[key] = value;
            scheduleSave();
        }
    }
    async function uploadImage(kind, event) {
        const input = event.target, file = input.files?.[0];
        input.value = "";
        if (!file || !actor.value || !canEditNow.value)
            return;
        try {
            if (props.tokenId) {
                saveError.value = gwText("Change the image through the original actor’s sheet.");
                return;
            }
            const result = await props.block.host.call("actor.image.upload", {
                id: props.actorId,
                kind,
                file,
            });
            if (!disposed && actor.value)
                actor.value[kind === "token" ? "tokenUrl" : "portraitUrl"] = result.url;
        }
        catch {
            if (!disposed)
                saveError.value = gwText("Could not upload the image.");
        }
    }
    pageHost.value = host;
    window.addEventListener("beforeunload", leaving);
    void load();
    return {
        get view() {
            return {
                actor: actor.value,
                loading: loading.value,
                error: error.value,
                saveError: saveError.value,
                actionError: actionError.value,
                fields,
                positions,
                pageLabel: pageLabel.value,
                statusText: statusText.value,
                viewerMissing: viewerMissing.value,
                currentSource: currentSource.value,
                openFieldNames: openFieldNames.value,
                pickerOpen: pickerOpen.value,
                mapping: mapping.value,
                campaignAssets: campaignAssets.value,
                canEdit: canEditNow.value,
                pages: viewerDoc?.numPages ?? 0,
                fieldIndex,
                mappingEditing: mappingEditing.value,
                canMap: canMap(),
                canConfigureFieldActions: canConfigureFieldActions(),
                fieldActions: actor.value ? actionsForSource(actor.value.data.pdf, currentSource.value) : Object.create(null),
                rolling: rolling.value,
                exporting: exporting.value,
                sourceDocument,
                calculationErrors,
                referenceFields: actor.value ? Object.values(bindingsForSource(actor.value.data.pdf, currentSource.value)) : [],
                calculatedFields: Object.fromEntries((actor.value?.data.pdf.calculatedFields || []).filter(row => row.source === sourceKey(currentSource.value)).map(row => [row.field, row.formula])),
                canUndoManualLayout: !!undoLayouts.length,
                canRedoManualLayout: !!redoLayouts.length,
                manualFields: actor.value ? manualFieldsForSource(actor.value.data.pdf, currentSource.value) : [],
                nativeFieldCount: nativeFieldNames.length,
                pageFrames,
                saving,
                pending: saveQueued,
            };
        },
        value: fieldValue,
        call(name, ...args) {
            const methods = {
                flush,
                async refreshActor() {
                    const previousLayout = actor.value && currentSource.value ? JSON.stringify(captureLayout(actor.value, currentSource.value)) : '';
                    const value = await options.read();
                    if (!disposed) {
                        actor.value = { ...value, data: normalizePdfCharacterData(value.data) };
                        const source = resolveSource();
                        if (source?.kind !== currentSource.value?.kind || source?.id !== currentSource.value?.id) await openSource();
                        else {
                            if (previousLayout !== JSON.stringify(captureLayout(actor.value, currentSource.value))) undoLayouts.length = redoLayouts.length = 0;
                            updatePositions();
                        }
                    }
                },
                toggleMapping() { if (canMap()) mappingEditing.value = !mappingEditing.value; },
                addManualField,
                updateManualField,
                removeManualField,
                editManualFields,
                copyManualFields: ids => copyLayout(actor.value, currentSource.value, ids, fields),
                pasteManualFields,
                undoManualLayout: () => moveLayoutHistory(undoLayouts, redoLayouts),
                redoManualLayout: () => moveLayoutHistory(redoLayouts, undoLayouts),
                configureFieldAction,
                rollField,
                exportMappingBundle,
                applyMappingBundle,
                save,
                prevPage,
                nextPage,
                zoomBy,
                fitPage,
                toggleSpread,
                download,
                downloadFilled,
                async showField(name) {
                    const info = fieldIndex.get(name);
                    if (!info || !actor.value) return false;
                    actor.value.data.pdf.page = info.page;
                    await render(); return true;
                },
                chooseSource,
                onFieldInput,
                onBarChoice,
                uploadPdf,
                uploadImage,
                setNote,
                scheduleSave,
                togglePicker: () => (pickerOpen.value = !pickerOpen.value),
            };
            const result = methods[name](...args);
            options.repaint();
            if (result?.finally)
                result.then(options.repaint, options.repaint);
            return result;
        },
        destroy() {
            disposed = true;
            ++sourceGeneration;
            ++renderGeneration;
            sourceAbort.abort();
            exportAbort?.abort();
            window.removeEventListener("beforeunload", leaving);
            clearTimeout(saveTimer);
            if (saveQueued)
                void save();
            saveQueued = false;
            releasePdf();
        },
    };
}
