import { HttpClient } from "/static/gravewright_modules/http-client.js";
const http = new HttpClient();
const text = (root, selector, value) => {
  const el = root.querySelector(selector);
  if (el) el.textContent = value ?? "";
};
const show = (root, selector, visible) => root.querySelector(selector)?.toggleAttribute("hidden", !visible);
function summary(root, values) {
  root.replaceChildren();
  for (const [key, value] of Object.entries(values)) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = typeof value === "object" ? JSON.stringify(value) : String(value);
    root.append(dt, dd);
  }
}
async function run(root, work) {
  if (root.dataset.busy === "true") return;
  root.dataset.busy = "true";
  root.setAttribute("aria-busy", "true");
  show(root, "[role=alert]", false);
  const disabled = [...root.querySelectorAll("button,input,select")].map((el) => [el, el.disabled]);
  disabled.forEach(([el]) => el.disabled = true);
  try {
    await work();
  } catch (error) {
    text(root, "[role=alert]", error.status === 403 ? "Only the installation owner or campaign GM can perform this action." : error.status === 409 ? "The state changed. Refresh before trying again." : error.status === 413 ? "The archive exceeds the 256 MB upload limit." : error.message || "The operation failed. Check the file or connection and try again.");
    show(root, "[role=alert]", true);
  } finally {
    root.dataset.busy = "false";
    root.setAttribute("aria-busy", "false");
    disabled.forEach(([el, value]) => el.disabled = value);
  }
}
function modules(root) {
  let installed = [], releases = [], ready = false;
  const installedOnly = root.dataset.moduleCatalog === "installed";
  function render() {
    const q = root.querySelector("input").value.trim().toLowerCase();
    const rows = (installedOnly ? installed : releases).filter((r) => `${r.id} ${r.name ?? ""} ${r.version}`.toLowerCase().includes(q));
    const grid = root.querySelector(".module-catalog__grid");
    grid.replaceChildren();
    for (const row of rows) {
      const local = installed.find((r) => r.id === row.id && r.version === row.version), card = root.querySelector("template").content.firstElementChild.cloneNode(true);
      text(card, "h3", local?.name ?? row.id);
      text(card, "[data-version]", `${row.id} \xB7 ${row.version}`);
      text(card, "[data-description]", local?.description ?? "");
      text(card, "[data-status]", local?.revoked ? "Revoked" : local ? "Installed" : "");
      show(card, "[data-action=install]", !local);
      card.querySelector("button").onclick = () => run(root, async () => {
        await http.post("/api/marketplace/install", { id: row.id, version: row.version }, { timeoutMs: null });
        await refresh();
        text(root, "[role=status]", `${row.id} ${row.version} installed. Open a table's Settings \u2192 Extensions to activate it.`);
        show(root, "[role=status]", true);
      });
      grid.append(card);
    }
    text(root, ".module-catalog__empty", q ? "No modules match your search." : installedOnly ? "No modules installed yet. Open Marketplace to find a package." : "No compatible modules are available in this catalog yet.");
    show(root, ".module-catalog__empty", !rows.length && (installedOnly || ready));
  }
  async function refresh() {
    const [status, packages] = await Promise.all([http.get("/api/marketplace/status"), http.get("/api/module-packages")]);
    installed = packages;
    ready = status.catalogConfigured && status.trustedKeysConfigured;
    show(root, ".module-catalog__setup", !installedOnly && !ready);
    show(root, "[data-setup=catalog]", !status.catalogConfigured);
    show(root, "[data-setup=keys]", !status.trustedKeysConfigured);
    if (!installedOnly && ready) {
      releases = await http.get("/api/marketplace", { timeoutMs: 6e4 });
      installed = await http.get("/api/module-packages");
    }
    render();
  }
  root.querySelector("input").oninput = render;
  root.querySelector("[data-action=refresh]").onclick = () => run(root, refresh);
  void run(root, refresh);
}
function administration(root) {
  let report, preview;
  function updates(value) {
    summary(root.querySelector("[data-update-summary]"), { "Installed version": value.currentVersionLabel ?? value.currentVersion, "Installation": value.installFormat, "Status": value.status, ...value.availableVersion ? { "Published version": value.availableVersionLabel ?? value.availableVersion } : {}, ...value.checkedAt ? { "Last check": new Date(value.checkedAt * 1e3).toLocaleString() } : {} });
    root.querySelector("[name=channel]").value = value.channel;
    show(root, "[data-channel-risk]", value.channel !== "stable");
    show(root, "[data-source-update]", value.installFormat === "source");
    show(root, "[data-container-update]", value.installFormat === "container");
    text(root, "[data-release-notes]", value.releaseNotes);
    const link = root.querySelector("[data-release]");
    let valid = false;
    try {
      const u = new URL(value.releaseUrl);
      valid = u.protocol === "https:" && u.hostname === "github.com" && !u.username && !u.password;
      if (valid) link.href = u.href;
    } catch {
    }
    link.hidden = !valid;
    show(root, "[data-artifact]", !!value.artifact && value.installFormat === "win64");
    if (value.artifact) {
      text(root, "[data-artifact-name]", value.artifact.name);
      text(root, "[data-artifact-hash]", value.artifact.sha256);
      root.querySelector("[data-artifact-link]").href = value.artifact.url;
    }
  }
  async function refresh() {
    updates((await http.get("/api/admin/status")).updates);
  }
  function events() {
    const area = root.querySelector("[data-events]");
    area.replaceChildren();
    const q = root.querySelector("[data-event-search]").value.toLowerCase();
    for (const e of report?.recent_events ?? []) {
      if (!`${e.event} ${JSON.stringify(e.fields)}`.toLowerCase().includes(q)) continue;
      const article = document.createElement("article");
      article.className = "administration__event";
      const strong = document.createElement("strong"), time = document.createElement("time"), pre = document.createElement("pre");
      strong.textContent = e.event;
      time.textContent = new Date(e.ts * 1e3).toLocaleString();
      pre.textContent = JSON.stringify(e.fields, null, 2);
      article.append(strong, time, pre);
      area.append(article);
    }
  }
  async function diagnostics() {
    report = await http.get("/api/admin/diagnostics");
    const area = root.querySelector("[data-metrics]");
    area.replaceChildren();
    for (const [group, values] of Object.entries(report.metrics)) {
      const section = document.createElement("section"), h = document.createElement("h3"), dl = document.createElement("dl");
      h.textContent = group;
      dl.className = "administration__summary";
      summary(dl, values);
      section.append(h, dl);
      area.append(section);
    }
    events();
  }
  root.querySelector("[data-event-search]").oninput = events;
  root.querySelectorAll("[data-tab]").forEach((button) => button.onclick = () => {
    root.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("administration__tab--active", b === button));
    root.querySelectorAll("[data-content]").forEach((el) => el.hidden = el.dataset.content !== button.dataset.tab);
    if (button.dataset.tab === "diagnostics") void run(root, diagnostics);
  });
  root.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (action === "refresh") void run(root, refresh);
    if (action === "diagnostics") void run(root, diagnostics);
    if (action === "check-updates") void run(root, async () => updates(await http.post("/api/admin/updates/check", {}, { timeoutMs: null })));
    if (action === "export-diagnostics" && report) {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
      a.download = "gravewright-diagnostics.json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1e3);
    }
  });
  root.addEventListener("submit", (event) => {
    const form = event.target.closest("form");
    if (!form) return;
    event.preventDefault();
    const data = new FormData(form);
    void run(root, async () => {
      if (form.dataset.form === "channel") {
        updates(await http.post("/api/admin/updates/channel", { channel: data.get("channel") }));
        return;
      }
      if (form.dataset.form === "import") {
        const file = data.get("archive");
        if (file.size > 256 * 1024 * 1024) throw Error("Choose a ZIP smaller than 256 MB.");
        const progress = form.querySelector("progress");
        progress.hidden = false;
        await http.upload("/api/admin/campaigns/import", data, (p) => progress.value = p);
        location.assign("/inside");
        return;
      }
      if (form.dataset.form === "clone") {
        const options = Object.fromEntries(["scenes", "actors", "items", "journals", "settings"].map((k) => [k, data.has(k)]));
        const result = await http.post(`/api/admin/campaigns/${data.get("source")}/clone/${preview ? "create" : "preview"}`, { title: data.get("title"), options }, { timeoutMs: null });
        if (preview) {
          location.assign("/inside");
          return;
        }
        preview = result.summary;
        summary(form.querySelector("[data-preview]"), preview);
        show(form, "[data-preview]", true);
        text(form, "button", "Create copy");
      }
    });
  });
  const clone = root.querySelector("[data-form=clone]");
  clone.onchange = (event) => {
    preview = void 0;
    show(clone, "[data-preview]", false);
    text(clone, "button", "Preview copy");
    if (event.target.name === "source") clone.querySelector("[name=title]").value = `${event.target.selectedOptions[0].textContent} \u2014 copy`;
  };
  void run(root, refresh);
}
function initialize() {
  for (const [selector, start] of [["[data-module-catalog]", modules], ["[data-administration]", administration]]) document.querySelectorAll(selector).forEach((root) => {
    if (root.dataset.initialized) return;
    root.dataset.initialized = "true";
    start(root);
  });
}
new MutationObserver(initialize).observe(document.body, { subtree: true, childList: true });
initialize();
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-backup]");
  if (button) openBackups(button.dataset.backup, button.dataset.backupName);
});
function openBackups(id, name) {
  const scrim = document.createElement("div");
  scrim.className = "campaign-backups-scrim";
  Object.assign(scrim.style, { position: "fixed", inset: 0, zIndex: 1e3, display: "grid", placeItems: "center", background: "#0009" });
  scrim.innerHTML = `<div class="campaign-backups" role="dialog" aria-modal="true" aria-labelledby="backup-title"><header><h2 id="backup-title"></h2><button type="button" data-close>Close</button></header><p>Snapshots restore this campaign's native state on this host. Account sessions and JavaScript module packages/settings are separate.</p><a data-export download>Export portable campaign ZIP</a><p>Exports transfer native campaign content and supported assets; they do not include accounts, invitations or chat history.</p><form data-create><label>Snapshot name<input name="name" required minlength="2" maxlength="120" value="Before the next session" /></label><button>Create snapshot</button></form><p role="alert" hidden></p><p data-empty>No snapshots yet.</p><div data-snapshots></div><form data-confirm hidden><h3></h3><p data-warning></p><details><summary>Restoration details</summary><pre></pre></details><label><span data-prompt></span><input name="confirm" required autocomplete="off" /></label><button>Confirm</button><button type="button" data-cancel>Cancel</button></form></div>`;
  const root = scrim.firstElementChild, base = `/api/containers/${id}`;
  let confirmation;
  document.body.append(scrim);
  text(root, "h2", `Copies \xB7 ${name}`);
  root.querySelector("[data-export]").href = base + "/export";
  const close = () => {
    if (root.dataset.busy !== "true") {
      scrim.remove();
      document.querySelector(`[data-backup="${id}"]`)?.focus();
    }
  };
  root.querySelector("[data-close]").onclick = close;
  scrim.onkeydown = (e) => {
    if (e.key === "Escape") close();
  };
  async function refresh() {
    const { snapshots } = await http.get(base + "/snapshots");
    const list = root.querySelector("[data-snapshots]");
    list.replaceChildren();
    show(root, "[data-empty]", !snapshots.length);
    for (const item of snapshots) {
      const article = document.createElement("article"), copy = document.createElement("div"), strong = document.createElement("strong"), small = document.createElement("small");
      strong.textContent = item.name;
      small.textContent = new Date(item.createdAt).toLocaleString();
      copy.append(strong, small);
      article.append(copy);
      for (const action of ["restore", "delete"]) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = action === "restore" ? "Restore" : "Delete";
        b.onclick = () => run(root, async () => {
          let preview;
          if (action === "restore") preview = (await http.post(`${base}/snapshots/${item.id}/preview`, {})).preview;
          confirmation = { ...item, action };
          const form = root.querySelector("[data-confirm]");
          text(form, "h3", `${b.textContent} ${item.name}`);
          text(form, "[data-warning]", action === "restore" ? "This replaces the current native campaign state. All participants must leave the table first." : "This permanently removes this snapshot.");
          text(form, "pre", JSON.stringify(preview, null, 2));
          show(form, "details", !!preview);
          text(form, "[data-prompt]", `Type ${action.toUpperCase()}`);
          form.querySelector("input").value = "";
          show(root, "[data-confirm]", true);
        });
        article.append(b);
      }
      list.append(article);
    }
  }
  root.querySelector("[data-create]").onsubmit = (e) => {
    e.preventDefault();
    const name2 = new FormData(e.target).get("name");
    void run(root, async () => {
      await http.post(base + "/snapshots", { name: name2 }, { timeoutMs: null });
      await refresh();
    });
  };
  root.querySelector("[data-cancel]").onclick = () => show(root, "[data-confirm]", false);
  root.querySelector("[data-confirm]").onsubmit = (e) => {
    e.preventDefault();
    const confirm = new FormData(e.target).get("confirm");
    if (confirm !== confirmation.action.toUpperCase()) {
      text(root, "[role=alert]", "Type the confirmation exactly as shown.");
      show(root, "[role=alert]", true);
      return;
    }
    void run(root, async () => {
      await http.post(`${base}/snapshots/${confirmation.id}/${confirmation.action}`, { confirm }, { timeoutMs: null });
      show(root, "[data-confirm]", false);
      await refresh();
    });
  };
  void run(root, refresh);
}
