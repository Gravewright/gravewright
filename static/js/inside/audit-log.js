(() => {
  "use strict";
  const pageSize = 25;







  const labelCache = new WeakMap();

  function labelsFor(panel) {
    if (labelCache.has(panel)) return labelCache.get(panel);
    let labels = { events: {}, fields: {}, results: {}, detailsToggle: "" };
    const tag = panel.querySelector("[data-audit-labels]");
    if (tag) {
      try {
        labels = { ...labels, ...JSON.parse(tag.textContent || "{}") };
      } catch {

      }
    }
    labelCache.set(panel, labels);
    return labels;
  }

  function formatWhen(seconds) {
    const when = new Date(seconds * 1000);
    return when.toLocaleString(undefined, {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatValue(value) {
    if (typeof value === "boolean") return value ? "✓" : "✕";
    return String(value);
  }

  function renderMetadata(labels, metadata) {
    const entries = Object.entries(metadata || {});
    if (!entries.length) return null;
    const wrap = document.createElement("dl");
    wrap.className = "audit-log-fields";
    for (const [key, value] of entries) {
      const term = document.createElement("dt");
      term.textContent = labels.fields[key] || key;
      const def = document.createElement("dd");
      def.textContent = formatValue(value);
      wrap.append(term, def);
    }
    return wrap;
  }

  function render(panel, events, append) {
    const labels = labelsFor(panel);
    const list = panel.querySelector("[data-audit-list]");
    if (!append) list.replaceChildren();
    for (const event of events) {
      const item = document.createElement("article");
      item.className = "audit-log-item";

      const title = document.createElement("strong");
      title.textContent = labels.events[event.event_type] || event.event_type;

      const when = document.createElement("small");
      when.className = "audit-log-when";
      when.textContent = formatWhen(event.created_at);

      const result = document.createElement("span");
      const outcome = String(event.result || "ok");
      result.className = `audit-log-result audit-log-result--${outcome}`;
      result.textContent = labels.results[outcome] || outcome;

      const head = document.createElement("div");
      head.className = "audit-log-head";
      head.append(title, result);
      item.append(head, when);

      const fields = renderMetadata(labels, event.metadata);
      if (fields) item.append(fields);



      const raw = document.createElement("details");
      raw.className = "audit-log-raw";
      const summary = document.createElement("summary");
      summary.textContent = labels.detailsToggle || "…";
      const code = document.createElement("code");
      code.textContent = JSON.stringify(
        {
          event_type: event.event_type,
          subject_type: event.subject_type,
          subject_id: event.subject_id,
          metadata: event.metadata || {},
        },
        null,
        2,
      );
      raw.append(summary, code);
      item.append(raw);

      list.append(item);
    }
    if (!list.children.length) list.textContent = panel.dataset.empty;
  }

  async function load(panel, page = 1) {
    if (panel.dataset.loading === "true") return;
    panel.dataset.loading = "true";
    const campaignId = panel.dataset.campaignId;
    const filter = panel.querySelector("[data-audit-filter]").value;
    const query = new URLSearchParams({ campaign_id: campaignId, page, page_size: pageSize });
    if (filter) query.set("event_type", filter);
    const result = await window.GravewrightCore.http.getJson(`/campaigns/audit?${query}`);
    panel.dataset.loading = "false";
    const list = panel.querySelector("[data-audit-list]");
    if (!result.ok || result.data?.ok === false) {
      list.textContent = panel.dataset.error;
      return;
    }
    render(panel, result.data.events, page > 1);
    panel.dataset.page = String(page);
    panel.querySelector("[data-audit-more]").hidden = page * pageSize >= result.data.total;
    const exportLink = panel.querySelector("[data-audit-export]");
    const exportQuery = new URLSearchParams({ campaign_id: campaignId });
    if (filter) exportQuery.set("event_type", filter);
    exportLink.href = `/campaigns/audit/export?${exportQuery}`;
  }

  document.addEventListener("click", (event) => {
    const refresh = event.target.closest("[data-audit-refresh]");
    if (refresh) load(refresh.closest("[data-audit-panel]"), 1);
    const more = event.target.closest("[data-audit-more]");
    if (more) {
      const panel = more.closest("[data-audit-panel]");
      load(panel, Number(panel.dataset.page || 1) + 1);
    }
  });


  document.addEventListener("inside:modal-open", (event) => {
    const panel = event.detail?.modal?.querySelector("[data-audit-panel]");
    if (panel && !panel.dataset.page) load(panel, 1);
  });
})();
