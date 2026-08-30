import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";

import { buildLocalizedCapabilityReference } from "../wiki/build/localized-capability-reference.mjs";
import { guides as englishGuides } from "../wiki/locales/en.guides.mjs";
import { forbiddenEnglishSdkTerms } from "../wiki/locales/en.guide-review.mjs";
import { guides as spanishGuides } from "../wiki/locales/es.guides.mjs";
import { forbiddenSpanishSdkTerms } from "../wiki/locales/es.guide-review.mjs";
import { resolveCapabilityRegistry } from "../wiki/build/capability-registry.mjs";

const root = resolve(import.meta.dirname, "..");
const ignoredDirectories = new Set([".git", "node_modules", "gravewright-core"]);

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) return [];
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [path];
  });
}

const htmlFiles = walk(root).filter((path) => extname(path) === ".html");
const failures = [];
const idsByFile = new Map();

for (const file of htmlFiles) {
  const html = readFileSync(file, "utf8");
  idsByFile.set(file, [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]));
}

for (const file of htmlFiles) {
  const html = readFileSync(file, "utf8");
  if (html.includes('<article class="wiki-article" id="wiki-article"></article>')) {
    failures.push(`${relative(root, file)}: article is empty instead of server-rendered`);
  }
  if (html.includes("translations/en.js") || html.includes("translations/pt-br.js") || html.includes("translations/es.js")) {
    failures.push(`${relative(root, file)}: locale bundles must be loaded on demand`);
  }
  if (html.includes("raw.githubusercontent.com/Gravewright/gravewright/main/icon.svg")) {
    failures.push(`${relative(root, file)}: logo must use the local versioned asset`);
  }
  const ids = idsByFile.get(file);
  const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
  if (duplicateIds.length) {
    failures.push(`${relative(root, file)}: duplicate IDs: ${[...new Set(duplicateIds)].join(", ")}`);
  }

  for (const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    const reference = match[1];
    if (/^(?:https?:|mailto:|data:)/.test(reference)) continue;
    const [targetReference, fragment] = reference.split("#", 2);
    const target = targetReference ? resolve(dirname(file), targetReference.split("?", 1)[0]) : file;
    if (!existsSync(target)) {
      failures.push(`${relative(root, file)}: missing local reference ${reference}`);
    } else if (fragment && extname(target) === ".html" && !idsByFile.get(target)?.includes(decodeURIComponent(fragment))) {
      failures.push(`${relative(root, file)}: missing anchor ${reference}`);
    }
  }
}

const englishReference = buildLocalizedCapabilityReference("en");
const spanishReference = buildLocalizedCapabilityReference("es");
const registryCapabilityCount = Object.keys(resolveCapabilityRegistry().registry.capabilities).length;
const referenceLeaks = {
  en: ["Ler paredes", "Criar/alterar geometria", "Somente exibir", "Pesquisar conteúdo", "Se você", "Esta página documenta", "O que autoriza", "Quando usar"],
  es: ["Ler paredes", "Criar/alterar geometria", "Somente exibir", "Pesquisar conteúdo", "Se você", "O que autoriza", "Quando usar"],
};
for (const [locale, reference] of [["en", englishReference], ["es", spanishReference]]) {
  const guides = [reference.intentGuide, ...reference.guides];
  if (reference.capabilityCount !== registryCapabilityCount) failures.push(`${locale}: documented ${reference.capabilityCount} of ${registryCapabilityCount} registry capabilities`);
  for (const guide of guides) {
    for (const phrase of referenceLeaks[locale]) {
      if (guide.body.includes(phrase)) failures.push(`${locale}/${guide.slug}: untranslated phrase: ${phrase}`);
    }
  }
}

const pageScript = readFileSync(join(root, "wiki", "page.js"), "utf8");
if (!pageScript.includes('url.searchParams.set("lang", locale)')) failures.push("wiki/page.js: locale selection is not propagated through ?lang=");
if (!pageScript.includes("../translations/${locale}.js")) failures.push("wiki/page.js: alternate locales are not loaded on demand");

const freshnessPath = join(root, "wiki", "data", "translation-freshness.json");
if (!existsSync(freshnessPath)) failures.push("wiki/data/translation-freshness.json: missing translation freshness report");
else {
  const freshness = JSON.parse(readFileSync(freshnessPath, "utf8"));
  for (const locale of ["en", "pt-br", "es"]) {
    const entries = freshness.locales?.[locale] || [];
    if (!entries.length) failures.push(`${locale}: no translation freshness entries`);
    const stale = entries.filter((entry) => entry.status !== "current" || entry.sourceHash !== entry.reviewedSourceHash);
    if (stale.length) failures.push(`${locale}: stale translations: ${stale.map((entry) => entry.slug).join(", ")}`);
    if (entries.some((entry) => !entry.sourceHash?.startsWith("sha256:") || !entry.reviewedSourceHash?.startsWith("sha256:"))) failures.push(`${locale}: invalid translation review hashes`);
  }
}

for (const guide of englishGuides) {
  const content = `${guide.section}\n${guide.title}\n${guide.summary}\n${guide.body}`;
  for (const term of forbiddenEnglishSdkTerms) {
    if (content.includes(term)) failures.push(`en/${guide.slug}: unreviewed technical translation: ${term}`);
  }
}

for (const guide of spanishGuides) {
  const content = `${guide.section}\n${guide.title}\n${guide.summary}\n${guide.body}`;
  for (const term of forbiddenSpanishSdkTerms) {
    if (content.includes(term)) failures.push(`es/${guide.slug}: unreviewed technical translation: ${term}`);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Validated ${htmlFiles.length} HTML files: local references and IDs are valid.`);
