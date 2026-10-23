import { pdfController } from "./controller.js";
import { createManualEditor } from './manual-editor.js';
import { createFieldActionsEditor } from './field-actions-editor.js';
import { createMappingLibrary } from './mapping-library.js';
import { createPdfDiagnostics } from './diagnostics.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { registerEscapeClose } from '/static/gravewright_web/escape.js';
import {
  Editor,
  StarterKit,
  Link,
} from "/static/gravewright_journals/vendor/editor.js";
const show = (el, on) => el.toggleAttribute("hidden", !on);
export function mountSheet({ root: el, window: hostWindow, campaign, actorId, token, gm, setTitle, lifecycle: extensionLifecycle }) {
  const translator = createTranslator(), text = (key, params) => translator.t(key, params);
  el.append(document.getElementById('system-sheet-body').content.cloneNode(true));
  const snapshot = token?.linkMode === 'snapshot';
  let closed = false,
    queued = false,
    controller, manualEditor, fieldActionsEditor, mappingLibrary, diagnostics, unregisterEscape,
    notes = [],
    tab = "ficha",
    fieldsKey = "",
    sourcesKey = "",
    barsKey = "", rollsKey = "";
  const interactions = new AbortController();
  const render = () => {
    if (closed || queued) return;
    queued = true;
    queueMicrotask(() => {
      queued = false;
      if (!closed && controller) paint();
    });
  };
  async function upload(kind, file) {
    const form = new FormData();
    form.set("file", file);
    form.set("kind", kind);
    if (kind !== "pdf") form.set("actorId", actorId);
    const response = await fetch(`/api/containers/${campaign}/actor-upload`, {
      method: "POST",
      body: form,
      headers: {
        "X-CSRF-Token": decodeURIComponent(
          document.cookie.match(/(?:^|; )gravewright-csrf=([^;]*)/)?.[1] || "",
        ),
      },
    });
    const value = await response.json();
    if (!response.ok) throw Error(value.message);
    return value;
  }
  const assets = {
    url: (p) =>
      p.startsWith("vendor/")
        ? "/static/gravewright_journals/" + p
        : "/static/gravewright_pdf_system/" + p,
    json: async (p) => {
      const r = await fetch(assets.url(p));
      if (!r.ok) throw Error("Could not load the PDF template.");
      return r.json();
    },
    bytes: async (p) => {
      const r = await fetch(assets.url(p));
      if (!r.ok) throw Error("Could not load the PDF template.");
      return r.arrayBuffer();
    },
  };
  const props = {
    actorId,
    tokenId: snapshot ? token.id : undefined,
    block: {
      context: { role: gm ? "gm" : "player" },
      assets,
      host: {
        async call(name, args) {
          if (name === "asset.list") {
            const r = await fetch(`/api/containers/${campaign}/actors`);
            if (!r.ok) throw Error("Could not load templates.");
            return { items: (await r.json()).templates };
          }
          if (name === "asset.download") {
            const r = await fetch(`/game/actors/asset/${args.id}`);
            if (!r.ok) throw Error("PDF not available.");
            return { blob: await r.blob() };
          }
          if (name === "asset.upload") return upload("pdf", args.file);
          if (name === "actor.image.upload")
            return upload(args.kind, args.file);
          throw Error("Unknown sheet operation.");
        },
      },
    },
  };
  controller = pdfController(el.querySelector(".pdf-sheet__page-host"), {
    props,
    repaint: render,
    async read() {
      const r = await fetch(
        `/api/containers/${campaign}/actors/${actorId}/sheet` +
          (token ? "?tokenId=" + token.id : ""),
        { cache: "no-store" },
      );
      if (!r.ok) throw Error("Character sheet unavailable.");
      const value = await r.json();
      // Switching systems does not convert existing document data. A PDF
      // provider cannot interpret a foreign sheet as its own schema.
      if (['pdf', 'fields', 'token', 'bars'].some(key => !value.data?.[key] || typeof value.data[key] !== 'object' || Array.isArray(value.data[key])))
        throw Error("Character sheet unavailable.");
      return value;
    },
    save: (value) =>
      window.gravewrightRealtime.resourceCommand("actors", "sheet.save", {
        actorId,
        tokenId: snapshot ? token.id : undefined,
        name: value.name,
        data: value.data,
        version: value.version,
        sheetVersion: value.sheetVersion,
      }),
    roll: (payload, { requestId }) => window.gravewrightRealtime.roll(payload, {
      requestId, mapId: token?.mapId || window.gravewrightMaps?.current?.id,
    }),
  });
  function destroy() {
    closed = true;
    unregisterEscape?.();
    interactions.abort();
    fieldActionsEditor.destroy();
    mappingLibrary.destroy(); diagnostics.destroy();
    manualEditor.destroy();
    controller.destroy();
    notes.forEach(editor => editor.destroy());
  }
  el.onclick = async (e) => {
    const t = e.target.closest(".pdf-sheet__tabs > [data-tab]")?.dataset.tab;
    if (t) {
      try {
        await extensionLifecycle('gravewright:sheet-flush');
        await controller.call('flush');
        await controller.call('refreshActor');
        if(t === 'ficha') await extensionLifecycle('gravewright:sheet-refresh');
      } catch(error) { const alert=el.querySelector('.pdf-sheet__error');show(alert,true);alert.querySelector('span').textContent=error.message;return; }
      tab = t;
      paint();
    }
    const name = e.target.closest("[data-pdf]")?.dataset.pdf;
    if (name)
      controller.call(
        name === "in" || name === "out" ? "zoomBy" : name,
        ...(name === "in" ? [1.2] : name === "out" ? [1 / 1.2] : []),
      );
  };
  manualEditor = createManualEditor({ root: el, controller, t: text,
    onConfigure: id => {
      const name = Object.keys(controller.view.fields).find(name => controller.view.fields[name].manualId === id);
      if (name && controller.view.canConfigureFieldActions) void configure(name);
    },
  });
  fieldActionsEditor = createFieldActionsEditor({ root: el, hostWindow, controller, t: text });
  mappingLibrary = createMappingLibrary({ root: el, controller, campaign, t: text });
  diagnostics = createPdfDiagnostics({ root: el, controller, t: text, onSelect: async name => {
    await controller.call('showField', name);
    el.querySelectorAll('[data-pdf-field]').forEach(input => {
      if (input.dataset.pdfField === name) { input.scrollIntoView({ block: 'center' }); input.focus(); }
    });
  } });
  el.querySelector('[data-pdf-library-open]').addEventListener('click', () => void mappingLibrary.open());
  el.querySelector('[data-pdf-diagnostics-open]').addEventListener('click', () => diagnostics.open());
  async function rollField(name) {
    const alert = el.querySelector('.pdf-sheet__error');
    try { await controller.call('rollField', name); }
    catch (failure) {
      if (closed) return;
      show(alert, true);
      alert.querySelector('span').textContent = text(failure.message || 'Could not roll this field. Try again.');
    }
  }
  function fieldNameFrom(target) {
    const input = target.closest('[data-pdf-field]');
    if (input) return input.dataset.pdfField;
    const box = target.closest('[data-pdf-map-field]');
    return box && Object.keys(controller.view.fields).find(name => controller.view.fields[name].manualId === box.dataset.pdfMapField);
  }
  async function configure(name) {
    try { await fieldActionsEditor.open(name); }
    catch (failure) {
      if (closed) return;
      const alert = el.querySelector('.pdf-sheet__error');
      show(alert, true); alert.querySelector('span').textContent = text(failure.message);
    }
  }
  el.addEventListener('dblclick', event => {
    const name = fieldNameFrom(event.target);
    if (!name) return;
    if (controller.view.canConfigureFieldActions) {
      event.preventDefault(); event.stopPropagation(); void configure(name);
    } else if (controller.view.canEdit && controller.view.fieldActions[name]) {
      event.preventDefault(); event.stopPropagation(); void rollField(name);
    }
  }, { signal: interactions.signal });
  el.addEventListener('keydown', event => {
    const name = fieldNameFrom(event.target);
    if (!name) return;
    if (event.key === 'F2' && controller.view.canConfigureFieldActions) {
      event.preventDefault(); event.stopPropagation(); void configure(name);
    } else if (event.key === 'Enter' && event.altKey && controller.view.fieldActions[name] && controller.view.canEdit) {
      event.preventDefault(); event.stopPropagation(); void rollField(name);
    }
  }, { signal: interactions.signal });
  unregisterEscape = registerEscapeClose(hostWindow, () => {
    if (!manualEditor.cancelGesture()) hostWindow.querySelector('[data-window="close"]')?.click();
  });
  for (const input of el.querySelectorAll("[data-upload]"))
    input.onchange = (e) =>
      controller.call(
        input.dataset.upload === "pdf" ? "uploadPdf" : "uploadImage",
        ...(input.dataset.upload === "pdf" ? [e] : [input.dataset.upload, e]),
      );
  for (const input of el.querySelectorAll("[data-field]"))
    input.oninput = () => {
      const a = controller.view.actor;
      if (!a?.canEdit) return;
      const key = input.dataset.field;
      if (key === "name") a.name = input.value;
      else if (key === "size") a.data.token.size = Number(input.value);
      else a.data.pdf.textColor = input.value;
      controller.call("scheduleSave");
      paint();
    };
  function paint() {
    const v = controller.view,
      a = v.actor;
    manualEditor.paint(v);
    const loading = el.querySelector(".pdf-sheet__loading");
    show(loading, v.loading || !a);
    loading.textContent = v.loading
      ? "Opening character sheet…"
      : v.error || "Character sheet unavailable.";
    show(el.querySelector(".pdf-sheet__tabs"), !!a);
    for (const p of el.querySelectorAll(".pdf-sheet > [data-panel]"))
      show(p, !!a && p.dataset.panel === tab);
    if (!a) return;
    const mappingLabel = el.querySelector('[data-pdf-map-toggle-label]');
    mappingLabel.textContent = text(v.mappingEditing ? 'Finish mapping' : 'Map fields');
    show(el.querySelector('[data-pdf-unmapped]'), gm && v.canMap && !v.mappingEditing && !v.nativeFieldCount && !v.manualFields.length);
    show(el.querySelector('[data-pdf-actions-hint]'), v.canConfigureFieldActions && !!v.openFieldNames.length);
    show(el.querySelector('[data-pdf-library-open]'), v.canConfigureFieldActions);
    show(el.querySelector('[data-pdf-diagnostics-open]'), v.canConfigureFieldActions);
    const filledButton = el.querySelector('[data-pdf=downloadFilled]');
    filledButton.disabled = !v.pages || v.exporting;
    hostWindow.dataset.canEdit = String(a.canEdit);
    setTitle(a.name);
    el.querySelector(".pdf-sheet").style.setProperty(
      "--pdf-field-text",
      a.data.pdf.textColor,
    );
    const alert = el.querySelector(".pdf-sheet__error");
    show(alert, !!(v.saveError || v.actionError));
    alert.querySelector("span").textContent = v.saveError || v.actionError;
    show(alert.querySelector('button'), !!v.saveError);
    for (const b of el.querySelectorAll(".pdf-sheet__tabs > [data-tab]")) {
      b.classList.toggle("pdf-sheet__tab--active", b.dataset.tab === tab);
      b.setAttribute("aria-selected", String(b.dataset.tab === tab));
    }
    el.querySelector(".pdf-sheet__page").textContent = v.pageLabel;
    el.querySelector(".pdf-sheet__status").textContent = v.statusText;
    el.querySelector("[data-pdf=prevPage]").disabled =
      !v.pages || a.data.pdf.page <= 1;
    el.querySelector("[data-pdf=nextPage]").disabled =
      !v.pages || a.data.pdf.page >= v.pages;
    el.querySelector("[data-pdf=toggleSpread]").classList.toggle(
      "pdf-sheet__btn--active",
      a.data.pdf.spread,
    );
    const picker = el.querySelector(".pdf-sheet__picker");
    show(picker, v.pickerOpen);
    const toggle = el.querySelector("[data-pdf=togglePicker]");
    show(toggle, a.canEdit);
    toggle.setAttribute("aria-expanded", String(v.pickerOpen));
    const choices = Object.entries(v.mapping?.templates || {})
      .map(([id, t]) => ({ id, name: t.label, kind: "template" }))
      .concat(v.campaignAssets.map((a) => ({ ...a, kind: "asset" })));
    const key = JSON.stringify(choices);
    if (key !== sourcesKey) {
      sourcesKey = key;
      const host = el.querySelector("[data-pdf-sources]");
      host.replaceChildren();
      for (const c of choices) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "pdf-sheet__picker-option";
        b.textContent = c.name;
        b.onclick = () => controller.call("chooseSource", c.kind, c.id);
        host.append(b);
      }
    }
    el.querySelector(".pdf-sheet__stage").dataset.viewerMissing = String(
      v.viewerMissing,
    );
    show(el.querySelector(".pdf-sheet__empty"), !v.currentSource);
    show(el.querySelector(".pdf-sheet__doc"), !!v.currentSource);
    const fkey = JSON.stringify([
      v.fields,
      v.positions,
      v.viewerMissing,
      a.canEdit,
    ]);
    if (fkey !== fieldsKey) {
      fieldsKey = fkey;
      const host = el.querySelector(".pdf-sheet__fields");
      host.replaceChildren();
      for (const [name, spec] of Object.entries(v.fields)) {
        const pos = v.positions[name];
        if (pos?.hidden) continue;
        const input = document.createElement(spec.multiline ? 'textarea' : 'input');
        input.className =
          "pdf-sheet__field" +
          (spec.type === "boolean" ? " pdf-sheet__field--checkbox" : "");
        if (!spec.multiline) input.type =
          spec.type === "boolean"
            ? "checkbox"
            : spec.type === "number"
              ? "number"
              : "text";
        input.title = spec.label || name;
        input.setAttribute("aria-label", spec.label || name);
        input.dataset.pdfField = name;
        if (spec.manualId) {
          input.dataset.manualField = spec.manualId;
          input.setAttribute('translate', 'no');
          if (spec.type !== 'boolean' && spec.type !== 'number') input.maxLength = 20000;
        }
        if (spec.type === 'number') {
          input.step = 'any';
          if (spec.manualId) { input.min = '-1000000'; input.max = '1000000'; }
        }
        const readonly = !a.canEdit || spec.calculated || v.fieldIndex.get(name)?.readOnly;
        input.readOnly = readonly;
        if (spec.calculated) input.dataset.pdfCalculated = '';
        input.disabled = input.type === "checkbox" && readonly;
        if (v.viewerMissing) input.placeholder = spec.label || name;
        else
          for (const k of ["left", "top", "width", "height"])
            input.style[k] = (pos?.[k] || 0) + "px";
        const value = controller.value(name);
        if (input.type === "checkbox") input.checked = !!value;
        else input.value = value;
        input.oninput = (e) => controller.call("onFieldInput", name, e);
        host.append(input);
      }
    }
    for (const input of el.querySelectorAll('.pdf-sheet__fields [data-pdf-field]')) {
      if (input.ownerDocument.activeElement === input || input.getAttribute('aria-invalid') === 'true') continue;
      const value = controller.value(input.dataset.pdfField);
      if (input.type === 'checkbox') input.checked = !!value;
      else input.value = value;
    }
    const rollNames = Object.keys(v.fieldActions).filter(name => v.fields[name] && !v.positions[name]?.hidden);
    const rollKey = JSON.stringify(rollNames.map(name => [name, v.fieldActions[name], v.fields[name]?.label]));
    const rolls = el.querySelector('[data-pdf-rolls]');
    show(rolls, a.canEdit && !!rollNames.length);
    if (rollKey !== rollsKey) {
      rollsKey = rollKey;
      rolls.replaceChildren();
      for (const name of rollNames) {
        const label = v.fieldActions[name].label || v.fields[name].label || name;
        const button = el.ownerDocument.createElement('button');
        button.type = 'button';
        button.dataset.pdfRollField = name;
        button.setAttribute('translate', 'no');
        button.textContent = label;
        button.title = translator.t('Roll {0}', [label]);
        button.setAttribute('aria-label', translator.t('Roll {0}', [label]));
        button.onclick = () => void rollField(name);
        rolls.append(button);
      }
    }
    for (const button of rolls.querySelectorAll('button')) button.disabled = v.rolling || !a.canEdit;
    for (const input of el.querySelectorAll("[data-field]")) {
      input.disabled = !a.canEdit;
      if (input.ownerDocument.activeElement !== input)
        input.value =
          input.dataset.field === "name"
            ? a.name
            : input.dataset.field === "size"
              ? a.data.token.size
              : a.data.pdf.textColor;
    }
    for (const img of el.querySelectorAll("[data-image]")) {
      const src = a[img.dataset.image === "token" ? "tokenUrl" : "portraitUrl"];
      show(img, !!src);
      if (src && img.getAttribute("src") !== src) img.src = src;
    }
    for (const input of el.querySelectorAll(
      "[data-upload]:not([data-upload=pdf])",
    ))
      input.disabled = !a.canEdit || snapshot;
    for (const action of el.querySelectorAll("[data-image-action]"))
      show(action, a.canEdit && !snapshot);
    show(el.querySelector("[data-no-fields]"), !v.openFieldNames.length);
    show(el.querySelector("[data-bar-choices]"), !!v.openFieldNames.length);
    const barNames = v.openFieldNames.filter(name => !v.fields[name]?.manualId
      || !v.fields[name].multiline && v.fields[name].type !== 'boolean');
    const bkey = JSON.stringify(barNames.map(name => [name, v.fields[name]?.label]));
    for (const select of el.querySelectorAll("[data-bar]")) {
      if (bkey !== barsKey) {
        select.replaceChildren(
          new Option(text("— none —"), ""),
          ...barNames.map((n) => new Option(v.fields[n]?.label || n, n)),
        );
        select.onchange = (e) =>
          controller.call("onBarChoice", select.dataset.bar, e);
      }
      select.disabled = !a.canEdit;
      select.value = a.data.token.bars[select.dataset.bar] || "";
    }
    barsKey = bkey;
    if (!notes.length)
      for (const host of el.querySelectorAll("[data-note]")) {
        const key = host.dataset.note,
          value = a.data[key],
          doc =
            typeof value === "object"
              ? value
              : {
                  type: "doc",
                  content: String(value)
                    .split("\n")
                    .map((text) => ({
                      type: "paragraph",
                      content: text ? [{ type: "text", text }] : [],
                    })),
                };
        host.className = "pdf-sheet__rich-text";
        const surface = document.createElement("div");
        const editor = new Editor({
          element: surface,
          extensions: [StarterKit, Link.configure({ openOnClick: false })],
          content: doc,
          editable: a.canEdit,
          editorProps: {
            attributes: { "aria-label": host.getAttribute("aria-label") },
          },
          onUpdate: ({ editor }) =>
            controller.call("setNote", key, editor.getJSON()),
        });
        if (a.canEdit) {
          const nav = document.createElement("nav");
          for (const [label, method] of [
            ["Bold", "toggleBold"],
            ["Italic", "toggleItalic"],
            ["List", "toggleBulletList"],
            ["Undo", "undo"],
            ["Redo", "redo"],
          ]) {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = label;
            button.onclick = () => editor.chain().focus()[method]().run();
            nav.append(button);
          }
          host.append(nav);
        }
        host.append(surface);
        notes.push(editor);
      }
  }
  return {
    destroy,
    flush: () => controller.call("flush"),
    get dirty() {
      return (
        controller.view.pending ||
        controller.view.saving ||
        !!controller.view.saveError
      );
    },
  };
}
