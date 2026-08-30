import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { buildCapabilityReference } from "../wiki/build/capability-reference.mjs";
import { buildLocalizedCapabilityReference } from "../wiki/build/localized-capability-reference.mjs";
import { renderMarkdown, renderPageShell } from "../wiki/build/render.mjs";
import { DEFAULT_LOCALE, localeCatalogs, SUPPORTED_LOCALES } from "../wiki/i18n/index.mjs";

const siteRoot = path.resolve(import.meta.dirname, "..");
const wikiRoot = path.join(siteRoot, "wiki");
const pagesDir = path.join(wikiRoot, "pages");
const translationsDir = path.join(wikiRoot, "translations");
const dataDir = path.join(wikiRoot, "data");
const translationReviewsPath = path.join(wikiRoot, "locales", "translation-reviews.json");
const capabilityReference = buildCapabilityReference();
const referenceGuides = [capabilityReference.intentGuide, ...capabilityReference.guides];
const referencesByLocale = {
  "pt-br": referenceGuides,
  en: (() => { const value = buildLocalizedCapabilityReference("en"); return [value.intentGuide, ...value.guides]; })(),
  es: (() => { const value = buildLocalizedCapabilityReference("es"); return [value.intentGuide, ...value.guides]; })(),
};

fs.mkdirSync(pagesDir, { recursive: true });
fs.mkdirSync(translationsDir, { recursive: true });
fs.mkdirSync(dataDir, { recursive: true });

const hashGuide = (guide) => `sha256:${createHash("sha256").update(JSON.stringify({
  section: guide.section,
  title: guide.title,
  summary: guide.summary,
  body: guide.body,
})).digest("hex")}`;

function decodeHtmlEntities(value) {
  return value
    .replace(/&#(\d+);/g, (_match, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_match, code) => String.fromCodePoint(Number.parseInt(code, 16)))
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&");
}

function serializeGuide(guide, sourceHash) {
  const html = renderMarkdown(guide.body);
  const headings = [...html.matchAll(/<h[23] id="[^"]+">([\s\S]*?)<\/h[23]>/gi)].map((match) => decodeHtmlEntities(match[1].replace(/<[^>]+>/g, "")));
  const keywords = [...new Set(`${guide.title} ${guide.summary} ${headings.join(" ")}`.toLowerCase().match(/[\p{L}\p{N}_.:-]{3,}/gu) || [])];
  return { slug: guide.slug, section: guide.section, title: guide.title, summary: guide.summary, headings, keywords, sourceHash, html };
}

const defaultGuides = [...localeCatalogs[DEFAULT_LOCALE].guides, ...referencesByLocale[DEFAULT_LOCALE]];
const sourceGuides = [...localeCatalogs["pt-br"].guides, ...referencesByLocale["pt-br"]];
const sourceHashes = new Map(sourceGuides.map((guide) => [guide.slug, hashGuide(guide)]));
const translationReviews = JSON.parse(fs.readFileSync(translationReviewsPath, "utf8"));
const freshness = { policy: "zero-stale", locales: {} };
for (const locale of SUPPORTED_LOCALES) {
  const catalog = localeCatalogs[locale];
  const localizedBySlug = new Map([...catalog.guides, ...referencesByLocale[locale]].map((guide) => [guide.slug, guide]));
  const guides = defaultGuides.map((guide) => localizedBySlug.get(guide.slug) || guide).map((guide) => serializeGuide(guide, sourceHashes.get(guide.slug)));
  freshness.locales[locale] = guides.map((guide) => {
    const reviewedSourceHash = locale === "pt-br" ? guide.sourceHash : translationReviews.locales?.[locale]?.[guide.slug] || null;
    const status = reviewedSourceHash === guide.sourceHash ? "current" : "stale";
    return { slug: guide.slug, sourceHash: guide.sourceHash, reviewedSourceHash, reviewed: status === "current", status };
  });
  const payload = { locale, ui: catalog.ui, guides };
  const assignment = `window.GravewrightWikiLocales=window.GravewrightWikiLocales||{};window.GravewrightWikiLocales[${JSON.stringify(locale)}]=${JSON.stringify(payload)};\n`;
  fs.writeFileSync(path.join(translationsDir, `${locale}.js`), assignment, "utf8");
}

for (const legacy of ["pt-br", "en", "es"]) fs.rmSync(path.join(wikiRoot, legacy), { recursive: true, force: true });
for (const file of fs.readdirSync(pagesDir)) if (file.endsWith(".html")) fs.rmSync(path.join(pagesDir, file));
fs.writeFileSync(path.join(dataDir, "translation-freshness.json"), `${JSON.stringify(freshness, null, 2)}\n`, "utf8");
for (const locale of SUPPORTED_LOCALES) {
  const entries = freshness.locales[locale];
  const stale = entries.filter((entry) => entry.status === "stale").length;
  console.log(`${locale.toUpperCase()}: ${entries.length - stale} current, ${stale} stale`);
}

const defaultPayload = { locale: DEFAULT_LOCALE, ui: localeCatalogs[DEFAULT_LOCALE].ui, guides: defaultGuides.map((guide) => serializeGuide(guide, sourceHashes.get(guide.slug))) };
for (const guide of defaultPayload.guides) fs.writeFileSync(path.join(pagesDir, `${guide.slug}.html`), renderPageShell(guide, defaultPayload), "utf8");

fs.writeFileSync(path.join(wikiRoot, "index.html"), '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url=pages/inicio.html"><title>Gravewright Wiki</title></head><body><p><a href="pages/inicio.html">Open Gravewright Wiki</a></p></body></html>', "utf8");
console.log(`Generated ${defaultGuides.length} single-URL pages; default=${DEFAULT_LOCALE}; locales=${SUPPORTED_LOCALES.join(",")}; capabilities=${capabilityReference.capabilityCount}.`);
