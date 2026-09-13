import {
  beginTreeDrag,
  cancelTreeDrag,
  draggedItem,
  registerTreePreview,
} from "./tree-drag.js";
import {
  getPath,
  mergePatch,
} from "/static/gravewright_web/vendor/datastar-1.0.3.js";
import { directoryView } from "/static/gravewright_maps/directory.js";
import { openSheet } from "/static/gravewright_pdf_system/sheet.js";
export const clone = (id) =>
  document.getElementById(id).content.firstElementChild.cloneNode(true);
export const icon = (name) =>
  document
    .querySelector("#actor-icons")
    .content.querySelector(`[data-icon="${name}"]`)
    .firstElementChild.cloneNode(true);
const show = (el, on) => el.toggleAttribute("hidden", !on);
let menu;
export function context(event, items, label = "Directory actions") {
  event.preventDefault();
  event.stopPropagation();
  menu?.remove();
  const el = document.createElement("menu");
  menu = el;
  el.className = "gw-folder-menu directory-context-menu";
  el.setAttribute("role", "menu");
  el.setAttribute("aria-label", label);
  Object.assign(el.style, {
    position: "fixed",
    left: event.clientX + "px",
    top: event.clientY + "px",
    zIndex: 1500,
  });
  for (const item of items) {
    const li = document.createElement("li"),
      b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "menuitem");
    b.disabled = !!item.disabled;
    if (item.danger) b.className = "is-danger";
    b.append(icon(item.icon), document.createTextNode(item.label));
    b.onclick = async (e) => {
      e.stopPropagation();
      el.remove();
      try {
        await item.run();
      } catch (error) {
        window.dispatchEvent(
          new CustomEvent("gravewright:actor-error", { detail: error.message }),
        );
      }
    };
    li.append(b);
    el.append(li);
  }
  el.onkeydown = (e) => {
    const buttons = [...el.querySelectorAll("button:not(:disabled)")],
      i = buttons.indexOf(document.activeElement);
    if (e.key === "Escape") {
      el.remove();
      e.stopPropagation();
    }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
      e.preventDefault();
      buttons[
        e.key === "Home"
          ? 0
          : e.key === "End"
            ? buttons.length - 1
            : (i + (e.key === "ArrowUp" ? -1 : 1) + buttons.length) %
              buttons.length
      ]?.focus();
    }
  };
  document.body.append(el);
  const r = el.getBoundingClientRect();
  el.style.left =
    Math.max(8, Math.min(event.clientX, innerWidth - r.width - 8)) + "px";
  el.style.top =
    Math.max(8, Math.min(event.clientY, innerHeight - r.height - 8)) + "px";
  return el;
}
window.addEventListener("click", () => menu?.remove());
const panel = document.getElementById("actors-panel"),
  workspace = document.getElementById("table-workspace"),
  campaign = workspace.dataset.tableId;
const labels = JSON.parse(
  document.getElementById("map-text")?.textContent || "{}",
);
let state = {
    actors: [],
    actorTypes: [],
    folders: [],
    templates: [],
    players: [],
    is_gm: false,
  },
  sheet,
  dialog,
  deletedTemplate,
  popup;
const command = (action, data) =>
  window.gravewrightRealtime.resourceCommand("actors", action, data);
function error(message) {
  if (!panel) return;
  const el = panel.querySelector("[role=alert]");
  el.textContent = message;
  show(el, true);
}
function form(id, title, save) {
  dialog?.remove();
  const el = clone(id);
  dialog = el;
  el.setAttribute("aria-label", title);
  el.querySelector("header strong").textContent = title;
  const r = panel.getBoundingClientRect();
  el.style.left = Math.max(13, r.left - 258) + "px";
  el.style.top = Math.max(13, r.top + 51) + "px";
  el.querySelector("header button").onclick = () => el.remove();
  el.onsubmit = async (e) => {
    e.preventDefault();
    const button = el.querySelector("[type=submit]");
    button.disabled = true;
    try {
      await save(el);
      el.remove();
    } catch (cause) {
      const p = el.querySelector("[role=alert]");
      p.textContent = cause.message;
      show(p, true);
    } finally {
      button.disabled = false;
    }
  };
  document.body.append(el);
  el.querySelector("input")?.focus();
  return el;
}
function syncActorTypes() {
  const select = dialog?.querySelector('[name=actorType]');
  if (!select || select.disabled) return;
  const selected = select.value;
  select.replaceChildren(...state.actorTypes.map((type) => new Option(type.label, type.id)));
  if (state.actorTypes.some((type) => type.id === selected)) select.value = selected;
  dialog.querySelector('[type=submit]').disabled = !state.actorTypes.length;
}
function edit(actor, folderId) {
  const el = form(
    "actor-form",
    actor ? labels.editActor : labels.newActor,
    (el) =>
      command(actor ? "actor.update" : "actor.create", {
        id: actor?.id,
        version: actor?.version,
        name: el.elements.name.value,
        actorType: actor?.actorType || el.elements.actorType.value,
        folderId: folderId ?? actor?.folderId,
        data: { pdf: { asset: el.elements.template.value } },
      }),
  );
  el.elements.name.value = actor?.name || "";
  el.elements.actorType.disabled = !!actor;
  syncActorTypes();
  show(el.querySelector("[data-actor-type]"), !actor);
  show(
    el.querySelector("[data-actor-template]"),
    !actor && state.systemId === 'gravewright-pdf-system' && !!state.templates.length,
  );
  show(
    el.querySelector("[data-no-templates]"),
    !actor && state.systemId === 'gravewright-pdf-system' && !state.templates.length,
  );
  el.querySelector("[type=submit] span").textContent = actor
    ? "Save"
    : labels.createActor;
  for (const a of state.templates)
    el.elements.template.append(new Option(a.name, a.id));
}
function folder(existing, parentId) {
  const el = form(
    "map-folder-form",
    existing ? "Edit folder" : labels.createActorFolder,
    (el) =>
      command(existing ? "folder.update" : "folder.create", {
        id: existing?.id,
        parentId: parentId ?? existing?.parentId,
        name: el.elements.label.value,
        color: el.elements.color.value,
      }),
  );
  if (existing) {
    el.elements.label.value = existing.name;
    el.elements.color.value = existing.color;
    el.elements.picker.value = existing.color;
  }
  el.elements.picker.oninput = (e) =>
    (el.elements.color.value = e.target.value);
}
function permissions(actor) {
  const el = form("actor-permissions", "Permissions — " + actor.name, (el) =>
    command("actor.permissions", {
      id: actor.id,
      permissions: Object.fromEntries(
        state.players.map((p) => [
          p.id,
          el.querySelector(`input[name="p-${p.id}"]:checked`).value,
        ]),
      ),
    }),
  );
  for (const p of state.players) {
    const row = clone("actor-permission-row");
    row.querySelector("legend").textContent = p.name;
    for (const input of row.querySelectorAll("input")) {
      input.name = "p-" + p.id;
      input.checked = input.value === (actor.permissions?.[p.id] || "none");
    }
    el.querySelector("[data-permission-rows]").append(row);
  }
  if (!state.players.length) {
    el.querySelector("[data-permission-rows]").textContent =
      "No players in this table.";
    show(el.querySelector("[type=submit]"), false);
  }
}
function open(actor, token) {
  sheet?.close();
  sheet = openSheet(campaign, actor.id, token, state.is_gm, () => {
    sheet = undefined;
  });
}
function remove(actor) {
  const el = clone("journal-confirm");
  el.querySelector("p").textContent = "Remove " + actor.name + "?";
  const b = el.querySelectorAll("button");
  b[0].onclick = async () => {
    try {
      await command("actor.delete", { id: actor.id });
      el.remove();
    } catch (e) {
      error(e.message);
    }
  };
  b[1].onclick = () => el.remove();
  document.body.append(el);
}
function paint() {
  if (!panel) return;
  const search = panel.querySelector("[type=search]").value,
    view = directoryView(state.folders, state.actors, search),
    root = panel.querySelector("[data-actor-tree]");
  root.replaceChildren();
  const draw = (host, parent = null) => {
    host.dataset.actorFolder = parent || "";
    host.dataset.treeDrop = parent || "";
    host.dataset.treeKind = "actor";
    for (const f of state.folders.filter(
      (f) => (f.parentId || null) === parent && view.visibleFolders.has(f.id),
    )) {
      const el = clone("journal-folder");
      el.dataset.actorFolder = f.id;
      el.dataset.treeDrop = f.id;
      el.dataset.treeKind = "actor";
      el.style.setProperty("--folder-color", f.color);
      el.querySelector(".gw-folder__label").textContent = f.name;
      el.querySelector(".gw-folder__count").textContent = view.counts.get(f.id);
      const key = `gravewright.directory.${campaign}.actors.${f.id}`,
        toggle = el.querySelector(".gw-folder__toggle");
      let expanded = !!search;
      try {
        expanded ||= localStorage.getItem(key) === "true";
      } catch {}
      show(el.querySelector(".gw-folder__content"), expanded);
      el.classList.toggle("gw-folder--open", expanded);
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.onclick = () => {
        try {
          localStorage.setItem(key, String(!expanded));
        } catch {}
        paint();
      };
      toggle.draggable = false;
      toggle.onpointerdown = (e) => {
        if (state.is_gm)
          beginTreeDrag(
            e,
            {
              id: f.id,
              label: f.name,
              kind: "actor",
              folder: true,
              icon: "FolderPlus",
            },
            (target) => target !== f.id && target !== (f.parentId ?? null),
            (parentId) =>
              command("folder.update", {
                id: f.id,
                parentId: parentId ?? null,
              }).catch((e) => error(e.message)),
          );
      };
      toggle.ondragstart = (e) => {
        e.dataTransfer.setData(
          "application/x-gravewright-actor",
          JSON.stringify({ folderId: f.id }),
        );
        e.stopPropagation();
      };
      toggle.oncontextmenu = (e) =>
        context(e, [
          { icon: "PencilSimple", label: "Edit folder", run: () => folder(f) },
          {
            icon: "FolderPlus",
            label: "Create folder",
            run: () => folder(null, f.id),
          },
          {
            icon: "Trash",
            label: "Delete folder",
            run: () => command("folder.delete", { id: f.id, recursive: false }),
          },
        ]);
      const b = el.querySelectorAll(".gw-folder__actions button");
      b[0].onclick = () => edit(null, f.id);
      if (b[1]) b[1].onclick = (e) => toggle.oncontextmenu(e);
      if (!state.is_gm) {
        el.querySelector(".gw-folder__actions")?.remove();
        toggle.oncontextmenu = null;
      }
      draw(el.querySelector(".gw-folder__content"), f.id);
      host.append(el);
    }
    const list = document.createElement("div");
    list.className = "actor-directory__list";
    for (const a of state.actors.filter(
      (a) => (a.folderId || null) === parent && view.visibleEntries.has(a.id),
    )) {
      const el = clone("actor-entry");
      el.querySelector("strong").textContent = a.name;
      el.querySelector("small").textContent =
        state.actorTypes.find((type) => type.id === a.actorType)?.label || a.actorType;
      if (a.portraitUrl) {
        const image = document.createElement("img");
        image.src = a.portraitUrl;
        image.alt = "";
        el.querySelector("svg").replaceWith(image);
      }
      el.onclick = () => open(a);
      el.draggable = false;
      el.onpointerdown = (e) => {
        if (state.is_gm)
          beginTreeDrag(
            e,
            {
              id: a.id,
              label: a.name,
              kind: "actor",
              folder: false,
              icon: "User",
            },
            (target) => target !== (a.folderId ?? null),
            (folderId) =>
              command("actor.update", {
                id: a.id,
                version: a.version,
                folderId: folderId ?? null,
              }).catch((e) => error(e.message)),
          );
      };
      el.ondragstart = (e) => {
        e.dataTransfer.setData(
          "application/x-gravewright-actor",
          JSON.stringify({ actorId: a.id }),
        );
      };
      el.oncontextmenu = (e) => {
        if (state.is_gm)
          context(e, [
            { icon: "NotePencil", label: "Open sheet", run: () => open(a) },
            {
              icon: "PencilSimple",
              label: labels.editActor,
              run: () => edit(a),
            },
            {
              icon: "UsersThree",
              label: "Permissions",
              run: () => permissions(a),
            },
            {
              icon: "Trash",
              label: labels.removeActor,
              danger: true,
              run: () => remove(a),
            },
          ]);
      };
      list.append(el);
    }
    host.append(list);
  };
  draw(root);
  show(
    panel.querySelector(".actor-directory__empty"),
    !view.visibleEntries.size,
  );
  const templates = panel.querySelector("[data-templates]");
  templates.replaceChildren();
  const folder = clone("journal-folder");
  folder.querySelector(".gw-folder__label").textContent = "Templates";
  folder.querySelector(".gw-folder__count").textContent =
    state.templates.length;
  folder.querySelector(".gw-folder__actions")?.remove();
  const body = folder.querySelector(".gw-folder__content");
  let expanded = !!search;
  try {
    expanded ||=
      localStorage.getItem(
        `gravewright.directory.${campaign}.actors.__templates__`,
      ) === "true";
  } catch {}
  show(body, expanded);
  folder.classList.toggle("gw-folder--open", expanded);
  folder.querySelector(".gw-folder__toggle").onclick = () => {
    try {
      localStorage.setItem(
        `gravewright.directory.${campaign}.actors.__templates__`,
        String(!expanded),
      );
    } catch {}
    paint();
  };
  for (const a of state.templates.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  )) {
    const row = document.createElement("span");
    row.className = "game-directory__item actor-directory__template";
    const text = document.createElement("span"),
      strong = document.createElement("strong"),
      small = document.createElement("small");
    strong.textContent = a.name;
    small.textContent = "PDF";
    text.append(strong, small);
    row.append(icon("FilePdf"), text);
    if (state.is_gm) {
      const b = document.createElement("button");
      b.className = "actor-directory__template-remove";
      b.setAttribute(
        "aria-label",
        deletedTemplate === a.id
          ? "Confirm remove template"
          : "Remove template",
      );
      b.append(icon("Trash"));
      b.onclick = async () => {
        if (deletedTemplate !== a.id) {
          deletedTemplate = a.id;
          paint();
          return;
        }
        try {
          await command("asset.delete", { id: a.id });
          deletedTemplate = null;
        } catch (e) {
          error(e.message);
        }
      };
      row.append(b);
    }
    body.append(row);
  }
  templates.append(folder);
}
window.gravewrightActors = {
  toggle() {
    mergePatch({ _actorsOpen: !getPath("_actorsOpen") });
  },
  open: (actorId, token) => open({ id: actorId }, token),
};
if (panel) {
  panel.querySelector(".game-directory").dataset.treeScroll = "";
  panel.onclick = (e) => {
    const a = e.target.closest("[data-actor-panel]")?.dataset.actorPanel;
    if (a === "close") mergePatch({ _actorsOpen: false });
    if (a === "minimize") panel.classList.toggle("game-panel--minimized");
    if (a === "detach") {
      if (popup && !popup.closed) {
        popup.focus();
        return;
      }
      popup = window.open("", "actors-directory", "popup,width=377,height=754");
      if (!popup) return;
      for (const css of document.querySelectorAll("link[rel=stylesheet]"))
        popup.document.head.append(css.cloneNode(true));
      const marker = document.createComment("actors-directory");
      panel.replaceWith(marker);
      popup.document.body.append(panel);
      panel.classList.add("game-panel--detached");
      popup.onpagehide = () => {
        marker.replaceWith(panel);
        panel.classList.remove("game-panel--detached");
      };
    }
    if (a === "create") edit();
    if (a === "folder") folder();
    if (a === "upload") panel.querySelector("[data-template-upload]").click();
  };
  panel.querySelector("[type=search]").oninput = paint;
  const input = panel.querySelector("[data-template-upload]");
  if (input)
    input.onchange = async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      const data = new FormData();
      data.set("file", file);
      try {
        const r = await fetch(`/api/containers/${campaign}/actor-upload`, {
          method: "POST",
          body: data,
          headers: {
            "X-CSRF-Token": decodeURIComponent(
              document.cookie.match(/(?:^|; )gravewright-csrf=([^;]*)/)?.[1] ||
                "",
            ),
          },
        });
        if (!r.ok) throw Error((await r.json()).message);
      } catch (e) {
        error(e.message);
      }
    };
  panel.ondragover = (e) => {
    if (
      state.is_gm &&
      e.dataTransfer.types.includes("application/x-gravewright-actor")
    )
      e.preventDefault();
  };
  panel.ondrop = async (e) => {
    const value = e.dataTransfer.getData("application/x-gravewright-actor");
    if (!value) return;
    e.preventDefault();
    try {
      const data = JSON.parse(value),
        folderId =
          e.target.closest("[data-actor-folder]")?.dataset.actorFolder || null;
      if (data.actorId) {
        const actor = state.actors.find((a) => a.id === data.actorId);
        await command("actor.update", {
          id: actor.id,
          version: actor.version,
          folderId,
        });
      } else
        await command("folder.update", {
          id: data.folderId,
          parentId: folderId,
        });
    } catch (cause) {
      error(cause.message);
    }
  };
  window.addEventListener("gravewright:actors.state", (e) => {
    state = e.detail;
    syncActorTypes();
    paint();
    if (sheet && sheet.element.dataset.actorId) {
      const a = state.actors.find(
        (a) => a.id === sheet.element.dataset.actorId,
      );
      if (!a || (sheet.element.dataset.canEdit === "true" && !a.canEdit))
        sheet.close();
    }
  });
  window.addEventListener("gravewright:actor-error", (e) => error(e.detail));
  window.addEventListener("gravewright:connected", () =>
    window.gravewrightRealtime.actorsSubscribe(),
  );
  window.addEventListener("gravewright:modules.updated", () =>
    window.gravewrightRealtime.actorsSubscribe(),
  );
  window.gravewrightRealtime?.actorsSubscribe();
  window.addEventListener("gravewright:access-revoked", () => {
    sheet?.close();
    dialog?.remove();
    menu?.remove();
    state = { ...state, actors: [], templates: [], folders: [] };
    paint();
  });
}

window.addEventListener("pagehide", () => {
  cancelTreeDrag("actor");
  popup?.close();
  sheet?.close();
  dialog?.remove();
  menu?.remove();
});

let dragChip;
window.addEventListener("gravewright:tree-drag", () => {
  queueMicrotask(() => {
    const subject = draggedItem.value;
    if (!subject) {
      dragChip?.remove();
      dragChip = undefined;
      return;
    }
    if (!dragChip) {
      dragChip = document.createElement("div");
      dragChip.className = "gw-tree-preview";
      dragChip.setAttribute("aria-hidden", "true");
      const strong = document.createElement("strong");
      strong.textContent = subject.label;
      const glyph = subject.folder ? "FolderPlus" : "User";
      dragChip.append(icon(glyph), strong);
      document.body.append(dragChip);
      registerTreePreview(dragChip);
    }
  });
});
