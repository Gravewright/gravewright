(() => {
  "use strict";
  const overlay = document.querySelector("[data-command-palette]");
  if (!overlay) return;
  const dialog = overlay.querySelector("[data-command-palette-dialog]");
  const input = overlay.querySelector("[data-command-palette-input]");
  const results = overlay.querySelector("[data-command-palette-results]");
  const status = overlay.querySelector("[data-command-palette-status]");
  const labels = JSON.parse(document.querySelector("#command-palette-labels")?.textContent || "{}");
  let entries = [], selected = -1, timer = 0, requestSequence = 0, previousFocus = null;
  const campaignId = () => document.querySelector('input[name="selected-room"]:checked')?.value || "";
  const setStatus = (text) => { status.textContent = text || ""; };

  function select(index) {
    if (!entries.length) { selected = -1; input.removeAttribute("aria-activedescendant"); return; }
    selected = (index + entries.length) % entries.length;
    results.querySelectorAll('[role="option"]').forEach((option, i) => {
      const active = i === selected;
      option.classList.toggle("is-selected", active);
      option.setAttribute("aria-selected", String(active));
      if (active) { input.setAttribute("aria-activedescendant", option.id); option.scrollIntoView({ block: "nearest" }); }
    });
  }

  function render(items) {
    entries = items; selected = -1; results.replaceChildren();
    items.forEach((entry, index) => {
      const option = document.createElement("button");
      option.type = "button"; option.id = `command-result-${index}`;
      option.className = "command-palette-result"; option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      const icon = document.createElement("i"); icon.className = `ph ${entry.icon || "ph-file"}`; icon.setAttribute("aria-hidden", "true");
      const copy = document.createElement("span"); copy.className = "command-palette-result-copy";
      const title = document.createElement("strong"); title.textContent = entry.title;
      const detail = document.createElement("small");
      detail.textContent = [labels.types?.[entry.type] || entry.type, entry.subtitle, entry.snippet].filter(Boolean).join(" · ");
      copy.append(title, detail); option.append(icon, copy);
      option.addEventListener("click", () => openEntry(entry));
      option.addEventListener("mousemove", () => select(index)); results.appendChild(option);
    });
    if (items.length) select(0); setStatus(items.length ? "" : labels.empty);
  }

  async function search() {
    const query = input.value.trim();
    if (query.length < 2) { render([]); setStatus(labels.hint); return; }
    const sequence = ++requestSequence; setStatus(labels.loading);
    const response = await window.GravewrightCore.http.getJson(`/game/search?campaign_id=${encodeURIComponent(campaignId())}&q=${encodeURIComponent(query)}`);
    if (sequence !== requestSequence) return;
    if (!response.ok || response.data?.ok === false) { render([]); setStatus(labels.error); return; }
    render(response.data.results || []);
  }

  function open() {
    previousFocus = document.activeElement; overlay.hidden = false;
    document.body.classList.add("command-palette-open"); input.value = "";
    render([]); setStatus(labels.hint); window.setTimeout(() => input.focus(), 0);
  }
  function close() {
    overlay.hidden = true; document.body.classList.remove("command-palette-open"); previousFocus?.focus?.();
  }
  function openModal(id) {
    const trigger = document.createElement("button"); trigger.type = "button";
    trigger.dataset.modalOpen = id; trigger.hidden = true; document.body.appendChild(trigger);
    trigger.click(); trigger.remove();
  }
  function openEntry(entry) {
    const target = entry.target || {}; close();
    if (target.action === "open_actor") document.dispatchEvent(new CustomEvent("vtt:open-actor-sheet", { detail: { actorId: target.id } }));
    else if (target.action === "open_item") document.dispatchEvent(new CustomEvent("vtt:open-item-sheet", { detail: { itemId: target.id } }));
    else if (target.action === "open_journal") document.dispatchEvent(new CustomEvent("vtt:open-journal", { detail: { journalId: target.id } }));
    else if (target.action === "open_scene_manager") { openModal(`scene-manager-${campaignId()}`); window.setTimeout(() => document.querySelector(`[data-scene-edit="${CSS.escape(target.id)}"]`)?.focus(), 0); }
    else if (target.action === "focus_scene") document.querySelector(`.room-workspace[data-room-id="${CSS.escape(campaignId())}"] [data-map-canvas]`)?.focus();
    else if (target.action === "open_compendium") {
      openModal(`panel-content-${campaignId()}`);
      window.setTimeout(() => { const summary = [...document.querySelectorAll(".content-pack-summary")].find((node) => node.textContent.trim() === entry.title); if (summary) { summary.parentElement.open = true; summary.focus(); } }, 100);
    }
  }

  document.addEventListener("click", (event) => { if (event.target.closest("[data-command-palette-open]")) open(); if (event.target === overlay) close(); });
  input.addEventListener("input", () => { window.clearTimeout(timer); timer = window.setTimeout(search, 180); });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); overlay.hidden ? open() : close(); return; }
    if (overlay.hidden) return;
    if (event.key === "Escape") { event.preventDefault(); close(); }
    else if (event.key === "ArrowDown") { event.preventDefault(); select(selected + 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); select(selected - 1); }
    else if (event.key === "Enter" && selected >= 0) { event.preventDefault(); openEntry(entries[selected]); }
    else if (event.key === "Tab") {
      const focusables = [...dialog.querySelectorAll("input, button:not([disabled])")];
      if (!focusables.length) return; const index = focusables.indexOf(document.activeElement);
      const next = event.shiftKey ? index - 1 : index + 1;
      if (next < 0 || next >= focusables.length) { event.preventDefault(); focusables[(next + focusables.length) % focusables.length].focus(); }
    }
  });
})();
