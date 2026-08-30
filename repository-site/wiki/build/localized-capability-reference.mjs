import { capabilityDescriptions as enDescriptions } from "../locales/en.capabilities.mjs";
import { referenceText as enText } from "../locales/en.reference.mjs";
import { capabilityDescriptions as esDescriptions } from "../locales/es.capabilities.mjs";
import { capabilityDescriptionCorrections as esDescriptionCorrections } from "../locales/es.capability-review.mjs";
import { referenceText as esText } from "../locales/es.reference.mjs";
import { resolveCapabilityRegistry } from "./capability-registry.mjs";

const registry = resolveCapabilityRegistry().registry;
const allCapabilities = Object.entries(registry.capabilities);

const groups = [
  ["sdk-capabilities-atores-itens", ["actors.", "items."]],
  ["sdk-capabilities-assets-ui", ["assets.", "ui."]],
  ["sdk-capabilities-eventos", ["bus.", "events.", "commands."]],
  ["sdk-capabilities-jogo", ["chat.", "cards.", "combat.", "dice.", "rolls."]],
  ["sdk-capabilities-conteudo", ["content.", "journals.", "handouts.", "pdf."]],
  ["sdk-capabilities-cena", ["scene.", "tokens."]],
  ["sdk-capabilities-regras", ["rules.", "sheets.", "settings", "storage.", "locales", "permissions."]],
  ["sdk-capabilities-automacao", ["packages.", "campaign.members.", "users.", "automation.", "interactions.", "audio.", "sounds.", "navigation.", "input.", "workflows.", "gameplay.", "timelines."]],
];

const localeData = {
  en: { descriptions: enDescriptions, text: enText },
  es: { descriptions: { ...esDescriptions, ...esDescriptionCorrections }, text: esText },
};

function authorityLevel(name) {
  if (name === "storage.sqlite") return "STORAGE";
  if (/^(bus\.|events\.|commands\.)/.test(name)) return "EVENT";
  if (/^(assets\.ui|ui\.|sheets\.|scene\.overlays)/.test(name)) return "UI";
  if (/\.(write|manage|move)$/.test(name) || ["rules.actions", "handouts.present"].includes(name)) return /^(scene\.|combat\.|cards\.)/.test(name) ? "ADMIN-LIKE" : "WRITE";
  if (/\.read$/.test(name) || ["content.index", "content.references", "permissions.inspect"].includes(name)) return "READ";
  return "UI";
}

function guidance(name, text) {
  if (name === "actors.write") return text.guidance.actorsWrite;
  if (name === "scene.geometry.write") return text.guidance.geometryWrite;
  if (name.endsWith(".read") || name === "content.index" || name === "content.references" || name === "permissions.inspect") return text.guidance.read;
  if (/\.(write|manage|move)$/.test(name) || name === "rules.actions") return text.guidance.write;
  if (name.startsWith("assets.")) return text.guidance.asset;
  if ((registry.capabilities[name].methods || []).length === 0) return text.guidance.manifest;
  return text.guidance.runtime;
}

function permission(name, text) {
  if (/^(actors|items)\.read/.test(name)) return text.permission.actorRead;
  if (/^(actors|items)\.(write|data\.write)/.test(name)) return text.permission.actorWrite;
  if (name === "tokens.read") return text.permission.tokenRead;
  if (/^tokens\.(move|manage)/.test(name)) return text.permission.tokenWrite;
  if (/^scene\..*\.write|^scene\.effects\.write|^scene\.fog\.write|^scene\.images\.write/.test(name)) return text.permission.sceneWrite;
  if (/^scene\..*\.read|^scene\.read/.test(name)) return text.permission.sceneRead;
  if (/^combat\.manage|^cards\.manage/.test(name)) return text.permission.manage;
  if (/^(journals|pdf|chat|content|assets\.library)/.test(name)) return text.permission.content;
  if (name === "permissions.inspect") return text.permission.inspect;
  if (name === "settings") return text.permission.settings;
  if (name === "storage.sqlite") return text.permission.storage;
  return text.permission.default;
}

function errors(name, text) {
  const items = [text.errors.capability];
  if (/read|write|manage|move|present|inspect|actions/.test(name)) items.push(text.errors.permission);
  if (/write|manage|move|settings|storage|actions|geometry|fog|images/.test(name)) items.push(text.errors.validation);
  if (/actors|items|tokens|scene|combat|journals|cards/.test(name)) items.push(text.errors.missing);
  if (/write|manage|move/.test(name)) items.push(text.errors.stale);
  if (name === "storage.sqlite") items.push(text.errors.storage);
  return items.map((item) => `- ${item}`).join("\n");
}

function visibility(name, text) {
  if (/^(actors|items|tokens|scene|chat|journals|content|pdf|cards|assets\.library)/.test(name)) return text.visibility.resource;
  if (/^(bus|events)\./.test(name)) return text.visibility.event;
  if (/\.write|\.manage|\.move|rules\.actions/.test(name)) return text.visibility.write;
  return text.visibility.default;
}

function lifecycle(name, text) {
  if (["bus.subscribe", "events.subscribe", "settings"].includes(name)) return text.lifecycle.subscription;
  if (["commands.register", "bus.provide", "sheets.controller", "sheets.runtime", "ui.slots", "ui.applications", "combat.runtime"].includes(name)) return text.lifecycle.registration;
  if (["assets.scripts", "assets.styles"].includes(name)) return text.lifecycle.assets;
  if (name === "storage.sqlite") return text.lifecycle.storage;
  return text.lifecycle.default;
}

const relations = {
  actors: ["actors.read", "actors.write", "actors.data.write", "permissions.inspect", "tokens.mappings"],
  items: ["items.read", "items.write", "items.data.write", "permissions.inspect"],
  tokens: ["tokens.read", "tokens.move", "tokens.manage", "actors.read", "scene.read"],
  scene: ["scene.read", "scene.geometry.read", "scene.geometry.write", "scene.effects.read", "scene.effects.write", "scene.fog.read", "scene.fog.write", "scene.images.read", "scene.images.write"],
  combat: ["combat.config", "combat.read", "combat.manage", "combat.runtime", "cards.read", "cards.manage", "events.subscribe"],
  cards: ["cards.read", "cards.manage", "combat.manage", "events.subscribe"],
  sheets: ["sheets.declarative", "sheets.html", "sheets.controller", "sheets.runtime", "actors.data.write", "items.data.write"],
  storage: ["settings", "storage.sqlite"],
  settings: ["storage.sqlite", "events.subscribe"],
  bus: ["bus.publish", "bus.subscribe", "bus.provide", "bus.request"],
};

function relatedCapabilities(name) {
  const domain = name.split(".")[0];
  return [...new Set((relations[domain] || allCapabilities.map(([item]) => item).filter((item) => item.startsWith(`${domain}.`))).filter((item) => item !== name))];
}

function pageFor(name) {
  const group = groups.find(([_slug, prefixes]) => prefixes.some((prefix) => name === prefix || name.startsWith(prefix)));
  return group ? `${group[0]}.html#${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` : "sdk-capabilities-runtime.html";
}

function example(name, methods, text) {
  const declaration = `\`\`\`json\n"capabilities": ["${name}"]\n\`\`\``;
  if (!methods.length) return `${declaration}\n\n${text.manifestExample(name)}`;
  const examples = {
    "actors.read": "const actors = await sdk.actors.list();\nconst actor = await sdk.actors.get(actorId);",
    "actors.write": "const actor = await sdk.actors.create({ name: \"Aria\", type: \"character\" });\nawait sdk.actors.update(actor.id, { name: \"Aria Winds\" });",
    "actors.data.write": "await sdk.actors.patchData(actorId, { hp: { value: 8 } });",
    "tokens.move": "await sdk.tokens.move(tokenId, { x: 12, y: 8 });",
    "dice.roll": "await sdk.dice.roll({ formula: \"1d20+3\", label: \"Perception\" });",
    "bus.subscribe": "const off = sdk.bus.subscribe(\"my-package.event\", handler);\n// teardown: off();",
    "bus.publish": "sdk.bus.publish(\"my-package.event\", { version: 1, resourceId });",
    settings: "const value = sdk.settings.get(\"my-setting\");\nconst off = sdk.settings.onChange(\"my-setting\", handler);",
    "storage.sqlite": "await sdk.storage.sqlite.execute(\"campaign\", \"saveState\", params);\nconst rows = await sdk.storage.sqlite.query(\"campaign\", \"getState\", params);",
    "scene.geometry.write": "await sdk.scene.geometry.createWall(sceneId, wallInput);\nawait sdk.scene.geometry.setDoorState(sceneId, wallId, \"open\");",
  };
  const code = examples[name] || methods.map((method) => `await sdk.${method}(/* ${text.parameterPlaceholder} */);`).join("\n");
  return `${declaration}\n\n\`\`\`js\n${code}\n\`\`\``;
}

function section(name, raw, descriptions, text) {
  const methods = raw.methods || [];
  const advice = guidance(name, text);
  const surfaces = (raw.surfaces || []).map((item) => `\`${item}\``).join(", ") || "-";
  const methodList = methods.length ? methods.map((method) => `- \`sdk.${method}\``).join("\n") : text.noMethods;
  const related = relatedCapabilities(name).map((item) => `[\`${item}\`](${pageFor(item)})`).join(", ") || text.none;
  return `## \`${name}\`\n\n**Authority level:** \`${authorityLevel(name)}\` · **Status:** \`${raw.status}\` · **Surfaces:** ${surfaces}\n\n### ${text.headings.authorizes}\n\n${descriptions[name] || raw.description}\n\n### ${text.headings.when}\n\n${advice.use}\n\n### ${text.headings.limits}\n\n${advice.limit}\n\n> [!IMPORTANT]\n> ${text.important}\n\n### ${text.headings.methods}\n\n${methodList}\n\n### ${text.headings.permissions}\n\n${permission(name, text)}\n\n### ${text.headings.example}\n\n${example(name, methods, text)}\n\n### ${text.headings.errors}\n\n${errors(name, text)}\n\n### ${text.headings.security}\n\n${visibility(name, text)}\n\n### ${text.headings.lifecycle}\n\n${lifecycle(name, text)}\n\n### ${text.headings.related}\n\n${related}\n\n> [!WARNING]\n> **${text.warning}** ${advice.avoid}\n`;
}

function list(items) {
  return items.map((item) => `- ${item}`).join("\n");
}

export function buildLocalizedCapabilityReference(locale) {
  const { descriptions, text } = localeData[locale] || {};
  if (!text) throw new Error(`Unsupported localized capability reference: ${locale}`);
  const guides = groups.map(([slug, prefixes]) => {
    const entries = allCapabilities.filter(([name]) => prefixes.some((prefix) => name === prefix || name.startsWith(prefix)));
    const title = text.groups[slug];
    return { slug, section: text.section, title, summary: text.groupSummary(entries.length), body: `# ${title}\n\n${text.groupIntro(entries.length)}\n\n${entries.map(([name, raw]) => section(name, raw, descriptions, text)).join("\n")}` };
  });
  const cap = (name) => `[\`${name}\`](${pageFor(name)})`;
  const items = text.intent.items(cap);
  const intentGuide = {
    slug: "sdk-mapa-de-poder", section: text.section, title: text.intent.title, summary: text.intent.summary,
    body: `# ${text.intent.title}\n\n${text.intent.intro}\n\n## ${text.intent.tokens}\n\n${list(items.tokens)}\n\n## ${text.intent.scene}\n\n${list(items.scene)}\n\n> [!IMPORTANT]\n> ${text.intent.geometryNote}\n\n## ${text.intent.combat}\n\n${list(items.combat)}\n\n## ${text.intent.content}\n\n${list(items.content)}\n\n## ${text.intent.persistence}\n\n${list(items.persistence)}\n\n## ${text.intent.minimization}\n\n${text.intent.finalRule}`,
  };
  return { intentGuide, guides, capabilityCount: allCapabilities.length };
}
