import { marked } from "marked";

export function renderMarkdown(markdown) {
  const alerts = marked.parse(markdown, { gfm: true }).replace(
    /<blockquote>\s*<p>\[!(WARNING|NOTE|TIP|IMPORTANT)\]\s*/gi,
    (_match, type) => `<blockquote class="wiki-alert wiki-alert--${type.toLowerCase()}"><p>`,
  );
  const seen = new Map();
  return alerts.replace(/<(h[23])>([\s\S]*?)<\/h[23]>/gi, (_match, tag, inner) => {
    const text = inner.replace(/<[^>]+>/g, "");
    const base = text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "section";
    const count = seen.get(base) || 0;
    seen.set(base, count + 1);
    return `<${tag} id="${count ? `${base}-${count + 1}` : base}">${inner}</${tag}>`;
  });
}

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const guideHref = (slug, locale) => `${slug}.html${locale === "en" ? "" : `?lang=${locale}`}`;

function renderTree(guides, current, locale) {
  const groups = new Map();
  for (const guide of guides) {
    if (!groups.has(guide.section)) groups.set(guide.section, []);
    groups.get(guide.section).push(guide);
  }
  return [...groups].map(([section, entries]) => `<section class="wiki-tree-section"><strong>${escapeHtml(section)}</strong>${entries.map((entry) => `<a data-search-item data-search-text="${escapeHtml(`${entry.title} ${entry.summary} ${(entry.headings || []).join(" ")} ${(entry.keywords || []).join(" ")}`.toLowerCase())}" href="${guideHref(entry.slug, locale)}"${entry.slug === current.slug ? ' class="is-active" aria-current="page"' : ""}>${escapeHtml(entry.title)}</a>`).join("")}</section>`).join("");
}

function renderNeighbors(guides, current, ui, locale) {
  const index = guides.findIndex((entry) => entry.slug === current.slug);
  const previous = guides[index - 1];
  const next = guides[index + 1];
  return `${previous ? `<a href="${guideHref(previous.slug, locale)}"><small>${escapeHtml(ui.previous)}</small><strong>${escapeHtml(previous.title)}</strong></a>` : "<span></span>"}${next ? `<a href="${guideHref(next.slug, locale)}"><small>${escapeHtml(ui.next)}</small><strong>${escapeHtml(next.title)}</strong></a>` : ""}`;
}

function renderToc(html) {
  return [...html.matchAll(/<h2 id="([^"]+)">([\s\S]*?)<\/h2>/gi)].map((match) => `<a href="#${escapeHtml(match[1])}" data-level="2">${escapeHtml(match[2].replace(/<[^>]+>/g, ""))}</a>`).join("");
}

export function renderPageShell(guide, payload) {
  const { locale, ui, guides } = payload;
  return `<!doctype html><html lang="${escapeHtml(ui.htmlLang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${escapeHtml(guide.summary)}"><meta name="theme-color" content="#0b0d10"><title>${escapeHtml(guide.title)} | Gravewright Wiki</title><link rel="stylesheet" href="../../styles.css"><link rel="stylesheet" href="../wiki.css"><script src="../page.js" defer></script></head><body class="wiki-page" data-guide-slug="${escapeHtml(guide.slug)}" data-default-locale="${locale}"><a class="skip-link" href="#wiki-article" data-i18n="skip">${escapeHtml(ui.skip)}</a><header class="site-header is-scrolled wiki-header"><div class="shell header-inner"><a class="brand" href="../../index.html"><span class="brand-icon"><img src="../../assets/icon.svg" alt="" width="34" height="34"></span><span>Gravewright <small>Wiki</small></span></a><div class="wiki-header-actions"><label class="wiki-language"><span data-i18n="language">${escapeHtml(ui.language)}</span><select data-language-select><option value="en" selected>English</option><option value="pt-br">Português</option><option value="es">Español</option></select></label><button class="wiki-icon-button wiki-mobile-nav" type="button" data-sidebar-toggle data-i18n-aria="openNavigation" aria-label="${escapeHtml(ui.openNavigation)}">☰</button><a class="nav-button" href="https://github.com/Gravewright/gravewright" data-i18n="github">${escapeHtml(ui.github)}</a></div></div></header><main class="wiki-shell"><aside class="wiki-sidebar" data-sidebar><div class="wiki-search-wrap"><label for="wiki-search" data-i18n="searchLabel">${escapeHtml(ui.searchLabel)}</label><div class="wiki-search-box"><span>⌕</span><input id="wiki-search" type="search" data-search placeholder="${escapeHtml(ui.searchPlaceholder)}"></div><p class="wiki-search-empty" data-search-empty hidden>${escapeHtml(ui.searchEmpty)}</p></div><nav class="wiki-tree" data-wiki-tree>${renderTree(guides, guide, locale)}</nav><footer class="wiki-sidebar-footer"><a href="../../index.html" data-i18n="home">${escapeHtml(ui.home)}</a><a href="https://github.com/Gravewright/gravewright/issues" data-i18n="report">${escapeHtml(ui.report)}</a></footer></aside><section class="wiki-main"><div class="wiki-breadcrumbs" data-breadcrumbs><span>${escapeHtml(ui.wiki)}</span><span>${escapeHtml(guide.section)}</span><span>${escapeHtml(guide.title)}</span></div><article class="wiki-article" id="wiki-article">${guide.html}</article><nav class="wiki-page-nav" data-page-nav>${renderNeighbors(guides, guide, ui, locale)}</nav></section><aside class="wiki-toc"><strong data-i18n="onThisPage">${escapeHtml(ui.onThisPage)}</strong><nav data-toc>${renderToc(guide.html)}</nav></aside></main><div class="wiki-overlay" data-overlay hidden></div></body></html>`;
}
