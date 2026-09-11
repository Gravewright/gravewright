import { fieldBounds } from "./pdf-geometry.js";
import { text as gwText } from "./text.js";
import { loadPdfjs, } from "./pdfjs-loader.js";
import { autoMapFields, readCanonical, writeCanonical, } from "./mapping.js";
import { normalizePdfCharacterData } from "../sheet-shape.js";
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
    let viewerDoc;
    let loadingTask;
    function releasePdf() {
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
        if (!spec || !actor.value || !canEditNow.value)
            return;
        const target = event.target;
        const raw = spec.type === "boolean"
            ? target.checked
            : spec.type === "number"
                ? target.value === ""
                    ? 0
                    : Number(target.value)
                : target.value;
        writeCanonical(actor.value, spec.path, raw);
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
        fieldIndex.clear();
        for (let number = 1; number <= doc.numPages; number += 1) {
            const page = await doc.getPage(number);
            const annotations = await page.getAnnotations({ intent: "display" });
            for (const annotation of annotations) {
                if (!annotation.fieldName || annotation.subtype !== "Widget")
                    continue;
                if (!fieldIndex.has(annotation.fieldName)) {
                    fieldIndex.set(annotation.fieldName, {
                        page: number,
                        rect: annotation.rect,
                        fieldType: annotation.fieldType ?? "Tx",
                        readOnly: Boolean(annotation.readOnly),
                    });
                }
            }
        }
        return [...fieldIndex.keys()];
    }
    function fieldTypeOf(name) {
        return fieldIndex.get(name)?.fieldType ?? "Tx";
    }
    function computeFields(source, templateFields) {
        if (!actor.value)
            return;
        const barChoices = actor.value.data.token.bars;
        Object.keys(fields).forEach((key) => delete fields[key]);
        let next;
        if (!openFieldNames.value.length && templateFields && viewerMissing.value) {
            next = templateFields;
        }
        else {
            next = autoMapFields(openFieldNames.value, mapping.value?.templates.generic?.fields, fieldTypeOf, barChoices);
        }
        Object.assign(fields, next);
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
            positions[name] = fieldBounds(viewport, info.rect, offsetTop);
        }
    }
    async function render() {
        try {
            await renderPages();
        }
        catch {
            if (!disposed)
                statusText.value = gwText("Could not render the page.");
        }
    }
    async function renderPages() {
        if (!viewerDoc || !pageHost.value || !actor.value)
            return;
        const generation = ++renderGeneration;
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
            const canvas = document.createElement("canvas");
            canvas.className = "pdf-sheet__canvas";
            const ratio = window.devicePixelRatio || 1;
            canvas.width = Math.floor(viewport.width * ratio);
            canvas.height = Math.floor(viewport.height * ratio);
            canvas.style.width = `${viewport.width}px`;
            canvas.style.height = `${viewport.height}px`;
            pageHost.value.append(canvas);
            try {
                await page.render({
                    canvas,
                    viewport,
                    transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0],
                }).promise;
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
            offsetTop += viewport.height;
        }
        pageLabel.value = `${actor.value.data.pdf.page} / ${viewerDoc.numPages}`;
    }
    async function openSource() {
        const generation = ++sourceGeneration;
        ++renderGeneration;
        const source = resolveSource();
        currentSource.value = source;
        viewerMissing.value = false;
        statusText.value = "";
        openFieldNames.value = [];
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
            openFieldNames.value = await indexFields(viewerDoc);
            if (disposed || generation !== sourceGeneration)
                return;
            computeFields(source, templateFields);
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
            if (templateFields)
                Object.assign(fields, templateFields);
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
        if (file.size > 10_000_000) {
            saveError.value = gwText("The PDF must be no larger than 10 MB.");
            return;
        }
        try {
            const body = await props.block.host.call("asset.upload", { file });
            if (disposed)
                return;
            campaignAssets.value = [...campaignAssets.value, body];
            await chooseSource("asset", body.id);
        }
        catch {
            saveError.value = gwText("Could not upload the PDF.");
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
                saving,
                pending: saveQueued,
            };
        },
        value: fieldValue,
        call(name, ...args) {
            const methods = {
                save,
                prevPage,
                nextPage,
                zoomBy,
                fitPage,
                toggleSpread,
                download,
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
                result.finally(options.repaint);
            return result;
        },
        destroy() {
            disposed = true;
            ++sourceGeneration;
            ++renderGeneration;
            sourceAbort.abort();
            window.removeEventListener("beforeunload", leaving);
            clearTimeout(saveTimer);
            if (saveQueued)
                void save();
            saveQueued = false;
            releasePdf();
        },
    };
}
