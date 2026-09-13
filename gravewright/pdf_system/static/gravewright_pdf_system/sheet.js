import { pdfController } from "./controller.js";
import {
  Editor,
  StarterKit,
  Link,
} from "/static/gravewright_journals/vendor/editor.js";
const show = (el, on) => el.toggleAttribute("hidden", !on);
export function openSheet(campaign, actorId, token, gm, onClose = () => {}) {
  const el = document
    .getElementById("pdf-sheet-window")
    .content.firstElementChild.cloneNode(true);
  const snapshot = token?.linkMode === "snapshot";
  if (token) {
    el.classList.remove("actor-directory__sheet");
    el.classList.add("token-sheet");
    el.querySelector("header").className = "gw-window__header";
    el.querySelector(".gw-window__grip").remove();
    const heading = document.createElement("strong"),
      small = document.createElement("small");
    small.textContent = snapshot ? "Independent copy" : "Linked to actor";
    heading.append(document.createTextNode(""), small);
    el.querySelector(".actor-directory__sheet-heading").replaceWith(heading);
  }
  if(token){el.dataset.tokenId=token.id;el.dataset.sceneId=token.mapId;}
  document.body.append(el);
  let closed = false,
    queued = false,
    controller,
    notes = [],
    tab = "ficha",
    fieldsKey = "",
    sourcesKey = "",
    barsKey = "";
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
      return r.json();
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
  });
  async function extensionLifecycle(name) {
    const tasks = [];
    el.dispatchEvent(new CustomEvent(name, { detail: { waitUntil: task => tasks.push(task) } }));
    await Promise.all(tasks);
  }
  async function close(force = false) {
    if (!force) {
      try { await extensionLifecycle('gravewright:sheet-flush'); await controller.call('flush'); }
      catch (error) { const alert=el.querySelector('.pdf-sheet__error');show(alert,true);alert.querySelector('span').textContent=error.message;return; }
    }
    if (closed) return;
    closed = true;
    controller.destroy();
    notes.forEach((e) => e.destroy());
    el.remove();
    window.removeEventListener("gravewright:access-revoked", revoke);
    onClose();
  }
  const revoke = () => close(true);
  window.addEventListener("gravewright:access-revoked", revoke);
  el.onclick = async (e) => {
    const w = e.target.closest("[data-window]")?.dataset.window;
    if (w === "close") return close();
    if (w === "maximize")
      el.classList.toggle(
        token ? "token-sheet--maximized" : "actor-directory__sheet--maximized",
      );
    if (w === "minimize") {
      el.classList.toggle("gw-window--minimized");
      show(
        el.querySelector(".gw-window__body"),
        !el.classList.contains("gw-window--minimized"),
      );
    }
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
    const loading = el.querySelector(".pdf-sheet__loading");
    show(loading, v.loading || !a);
    loading.textContent = v.loading
      ? "Opening character sheet…"
      : v.error || "Character sheet unavailable.";
    show(el.querySelector(".pdf-sheet__tabs"), !!a);
    for (const p of el.querySelectorAll(".pdf-sheet > [data-panel]"))
      show(p, !!a && p.dataset.panel === tab);
    if (!a) return;
    el.dataset.actorId = actorId;
    el.dataset.canEdit = String(a.canEdit);
    el.setAttribute("aria-label", token ? "Ficha: " + a.name : a.name);
    if (token)
      el.querySelector("header strong").firstChild.textContent = a.name + " ";
    else el.querySelector("header strong").textContent = a.name;
    el.querySelector(".pdf-sheet").style.setProperty(
      "--pdf-field-text",
      a.data.pdf.textColor,
    );
    const alert = el.querySelector(".pdf-sheet__error");
    show(alert, !!v.saveError);
    alert.querySelector("span").textContent = v.saveError;
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
        const input = document.createElement("input");
        input.className =
          "pdf-sheet__field" +
          (spec.type === "boolean" ? " pdf-sheet__field--checkbox" : "");
        input.type =
          spec.type === "boolean"
            ? "checkbox"
            : spec.type === "number"
              ? "number"
              : "text";
        input.title = name;
        input.setAttribute("aria-label", name);
        const readonly = !a.canEdit || v.fieldIndex.get(name)?.readOnly;
        input.readOnly = readonly;
        input.disabled = input.type === "checkbox" && readonly;
        if (v.viewerMissing) input.placeholder = name;
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
    for (const input of el.querySelectorAll("[data-field]")) {
      input.disabled = !a.canEdit;
      if (document.activeElement !== input)
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
    const bkey = JSON.stringify(v.openFieldNames);
    for (const select of el.querySelectorAll("[data-bar]")) {
      if (bkey !== barsKey) {
        select.replaceChildren(
          new Option("— none —", ""),
          ...v.openFieldNames.map((n) => new Option(n, n)),
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
    close,
    element: el,
    get dirty() {
      return (
        controller.view.pending ||
        controller.view.saving ||
        !!controller.view.saveError
      );
    },
  };
}
