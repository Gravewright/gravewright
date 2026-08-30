(() => {
  const DEFAULT_LOCALE = document.body.dataset.defaultLocale || "en";
  const SUPPORTED_LOCALES = ["en", "pt-br", "es"];
  const slug = document.body.dataset.guideSlug || "inicio";
  const select = document.querySelector("[data-language-select]");
  const article = document.querySelector("#wiki-article");
  const tree = document.querySelector("[data-wiki-tree]");
  const loaded = new Map();

  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const hrefFor = (guideSlug, locale) => `${guideSlug}.html${locale === DEFAULT_LOCALE ? "" : `?lang=${locale}`}`;

  function requestedLocale() {
    const queryLocale = new URLSearchParams(location.search).get("lang");
    if (SUPPORTED_LOCALES.includes(queryLocale)) return queryLocale;
    const savedLocale = localStorage.getItem("gravewright.wiki.locale");
    if (SUPPORTED_LOCALES.includes(savedLocale)) return savedLocale;
    const browserLocale = navigator.language?.toLowerCase();
    if (browserLocale?.startsWith("pt")) return "pt-br";
    if (browserLocale?.startsWith("es")) return "es";
    return DEFAULT_LOCALE;
  }

  function localeUrl(locale) {
    const url = new URL(location.href);
    if (locale === DEFAULT_LOCALE) url.searchParams.delete("lang");
    else url.searchParams.set("lang", locale);
    return url;
  }

  function loadLocale(locale) {
    if (loaded.has(locale)) return loaded.get(locale);
    const existing = window.GravewrightWikiLocales?.[locale];
    if (existing) return Promise.resolve(existing);
    const promise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `../translations/${locale}.js`;
      script.onload = () => resolve(window.GravewrightWikiLocales?.[locale]);
      script.onerror = () => reject(new Error(`Unable to load locale: ${locale}`));
      document.head.append(script);
    });
    loaded.set(locale, promise);
    return promise;
  }

  function renderToc() {
    const toc = document.querySelector("[data-toc]");
    if (!toc) return;
    toc.innerHTML = [...article.querySelectorAll("h2")].map((heading) => `<a href="#${heading.id}" data-level="2">${escape(heading.textContent)}</a>`).join("");
  }

  function render(catalog, locale) {
    const guide = catalog.guides.find((entry) => entry.slug === slug) || catalog.guides[0];
    const index = catalog.guides.findIndex((entry) => entry.slug === guide.slug);
    const previous = catalog.guides[index - 1];
    const next = catalog.guides[index + 1];
    document.documentElement.lang = catalog.ui.htmlLang;
    document.title = `${guide.title} | Gravewright Wiki`;
    document.querySelector('meta[name="description"]')?.setAttribute("content", guide.summary);
    document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = catalog.ui[node.dataset.i18n] || ""; });
    document.querySelectorAll("[data-i18n-aria]").forEach((node) => node.setAttribute("aria-label", catalog.ui[node.dataset.i18nAria] || ""));
    document.querySelector("[data-search]").placeholder = catalog.ui.searchPlaceholder;
    document.querySelector("[data-search-empty]").textContent = catalog.ui.searchEmpty;
    document.querySelector("[data-breadcrumbs]").innerHTML = `<span>${escape(catalog.ui.wiki)}</span><span>${escape(guide.section)}</span><span>${escape(guide.title)}</span>`;
    article.innerHTML = guide.html;

    const groups = new Map();
    for (const entry of catalog.guides) {
      if (!groups.has(entry.section)) groups.set(entry.section, []);
      groups.get(entry.section).push(entry);
    }
    tree.innerHTML = [...groups].map(([section, entries]) => `<section class="wiki-tree-section"><strong>${escape(section)}</strong>${entries.map((entry) => `<a data-search-item data-search-text="${escape(`${entry.title} ${entry.summary} ${(entry.headings || []).join(" ")} ${(entry.keywords || []).join(" ")}`.toLowerCase())}" href="${hrefFor(entry.slug, locale)}"${entry.slug === slug ? ' class="is-active" aria-current="page"' : ""}>${escape(entry.title)}</a>`).join("")}</section>`).join("");
    document.querySelector("[data-page-nav]").innerHTML = `${previous ? `<a href="${hrefFor(previous.slug, locale)}"><small>${escape(catalog.ui.previous)}</small><strong>${escape(previous.title)}</strong></a>` : "<span></span>"}${next ? `<a href="${hrefFor(next.slug, locale)}"><small>${escape(catalog.ui.next)}</small><strong>${escape(next.title)}</strong></a>` : ""}`;
    select.value = locale;
    renderToc();
  }

  async function changeLocale(locale, { updateUrl = true } = {}) {
    localStorage.setItem("gravewright.wiki.locale", locale);
    if (locale === DEFAULT_LOCALE) {
      if (updateUrl) location.assign(localeUrl(locale));
      return;
    }
    try {
      const catalog = await loadLocale(locale);
      if (!catalog) throw new Error(`Locale payload is empty: ${locale}`);
      render(catalog, locale);
      if (updateUrl) history.replaceState(null, "", localeUrl(locale));
    } catch (error) {
      console.error(error);
      select.value = DEFAULT_LOCALE;
    }
  }

  select?.addEventListener("change", () => changeLocale(select.value));

  const sidebar = document.querySelector("[data-sidebar]");
  const overlay = document.querySelector("[data-overlay]");
  const close = () => { sidebar?.classList.remove("is-open"); if (overlay) overlay.hidden = true; };
  document.querySelector("[data-sidebar-toggle]")?.addEventListener("click", () => { sidebar?.classList.toggle("is-open"); if (overlay) overlay.hidden = !sidebar?.classList.contains("is-open"); });
  overlay?.addEventListener("click", close);
  document.querySelector("[data-search]")?.addEventListener("input", (event) => {
    const query = event.target.value.trim().toLocaleLowerCase();
    let visible = 0;
    document.querySelectorAll("[data-search-item]").forEach((link) => { link.hidden = Boolean(query) && !link.dataset.searchText.includes(query); if (!link.hidden) visible += 1; });
    document.querySelectorAll(".wiki-tree-section").forEach((section) => { section.hidden = !section.querySelector("[data-search-item]:not([hidden])"); });
    document.querySelector("[data-search-empty]").hidden = visible > 0;
  });

  const initialLocale = requestedLocale();
  select.value = initialLocale;
  if (initialLocale !== DEFAULT_LOCALE) changeLocale(initialLocale, { updateUrl: true });
})();
