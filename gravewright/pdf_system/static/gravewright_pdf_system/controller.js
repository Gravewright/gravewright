// gravewright/pdf_system/frontend/pdf-geometry.js
function fieldBounds(viewport, rect, offsetTop = 0) {
  const [x1, y1] = viewport.convertToViewportPoint(rect[0], rect[1]);
  const [x2, y2] = viewport.convertToViewportPoint(rect[2], rect[3]);
  return {
    left: Math.min(x1, x2),
    top: Math.min(y1, y2) + offsetTop,
    width: Math.abs(x2 - x1),
    height: Math.abs(y2 - y1),
    hidden: false
  };
}

// ../../pdf_system/frontend/text.js
function text(value, ...args) {
  const i18n = typeof window !== "undefined" && window.gravewright?.i18n;
  return i18n ? i18n.t(value, args) : value.replace(/\{(\d+)\}/g, (match, i) => args[Number(i)] === void 0 ? match : String(args[Number(i)]));
}

// ../../pdf_system/frontend/pdfjs-loader.js
var cached;
function loadPdfjs(url) {
  if (!cached) {
    cached = import(
      /* @vite-ignore */
      url("vendor/pdf.mjs")
    ).then((lib) => {
      lib.GlobalWorkerOptions.workerSrc = url("vendor/pdf.worker.mjs");
      return lib;
    }).catch((error) => {
      cached = void 0;
      throw error;
    });
  }
  return cached;
}

// ../../pdf_system/frontend/mapping.js
var BAR_SLOTS = [
  { key: "bar1Value", label: text("Bar 1 \xB7 Current"), path: "sheet.bars.bar_1.value" },
  { key: "bar1Max", label: text("Bar 1 \xB7 Maximum"), path: "sheet.bars.bar_1.max" },
  { key: "bar2Value", label: text("Bar 2 \xB7 Current"), path: "sheet.bars.bar_2.value" },
  { key: "bar2Max", label: text("Bar 2 \xB7 Maximum"), path: "sheet.bars.bar_2.max" },
  { key: "initiative", label: text("Initiative"), path: "sheet.init" },
  { key: "defense", label: text("Defense"), path: "sheet.ac" }
];
function safeSegment(name) {
  return (name || "").replace(/[^A-Za-z0-9_-]/g, "_").replace(/^_+|_+$/g, "") || "campo";
}
function autoMapFields(fieldNames, canonicalFields, fieldType, barChoices) {
  const fields = /* @__PURE__ */ Object.create(null);
  const forBar = /* @__PURE__ */ new Map();
  for (const slot of BAR_SLOTS) {
    const chosen = barChoices[slot.key];
    if (chosen)
      forBar.set(chosen, slot.path);
  }
  const used = /* @__PURE__ */ new Set();
  for (const name of fieldNames) {
    const barPath = forBar.get(name);
    const known = canonicalFields && Object.hasOwn(canonicalFields, name) ? canonicalFields[name] : void 0;
    if (known) {
      fields[name] = barPath ? { path: barPath, type: "number" } : known;
      continue;
    }
    let segment = safeSegment(name);
    const base = segment;
    let suffix = 2;
    while (used.has(segment))
      segment = `${base}_${suffix++}`;
    used.add(segment);
    fields[name] = barPath ? { path: barPath, type: "number" } : { path: `sheet.fields.${segment}`, type: fieldType(name) === "Btn" ? "boolean" : "string" };
  }
  return fields;
}
function readCanonical(actor, path) {
  if (path === "core.name")
    return actor.name;
  if (!path.startsWith("sheet.") || path.split(".").some((key) => ["__proto__", "prototype", "constructor"].includes(key)))
    return;
  const rest = path.slice("sheet.".length);
  return rest.split(".").reduce((cursor, key) => cursor && typeof cursor === "object" ? cursor[key] : void 0, actor.data);
}
function writeCanonical(actor, path, value) {
  if (path === "core.name") {
    actor.name = String(value ?? "");
    return;
  }
  if (!path.startsWith("sheet.") || path.split(".").some((key) => ["__proto__", "prototype", "constructor"].includes(key)))
    return;
  const rest = path.slice("sheet.".length);
  const keys = rest.split(".");
  const last = keys.pop();
  if (!last)
    return;
  let cursor = actor.data;
  for (const key of keys) {
    if (!cursor[key] || typeof cursor[key] !== "object")
      cursor[key] = {};
    cursor = cursor[key];
  }
  cursor[last] = value;
}

// ../../pdf_system/frontend/manual-fields.js
var MANUAL_FIELD_TYPES = Object.freeze(["text", "number", "checkbox", "multiline"]);
var MAX_MANUAL_FIELDS = 256;
var MIN_MANUAL_SIZE = 1e-3;
var UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
var TEMPLATE_PATTERN = /^[A-Za-z0-9_-]{1,120}$/;
var FIELD_KEYS = /* @__PURE__ */ new Set(["id", "source", "page", "type", "name", "x", "y", "width", "height"]);
var finite = (value) => typeof value === "number" && Number.isFinite(value);
function sourceKey(source) {
  if (source && typeof source === "object") {
    if (typeof source.kind !== "string" || typeof source.id !== "string")
      return "";
    return sourceKey(`${source.kind}:${source.id}`);
  }
  if (typeof source !== "string")
    return "";
  if (source.startsWith("asset:") && UUID_PATTERN.test(source.slice(6).toLowerCase()))
    return `asset:${source.slice(6).toLowerCase()}`;
  if (source.startsWith("template:") && TEMPLATE_PATTERN.test(source.slice(9)))
    return source;
  return "";
}
function manualFieldKey(fieldOrId) {
  const id = typeof fieldOrId === "string" ? fieldOrId : fieldOrId?.id;
  if (typeof id !== "string" || !UUID_PATTERN.test(id))
    return "";
  return `manual_${id.replaceAll("-", "")}`;
}
function validManualField(field) {
  if (!field || typeof field !== "object" || Array.isArray(field) || Object.keys(field).some((key) => !FIELD_KEYS.has(key)) || !manualFieldKey(field) || !field.source || sourceKey(field.source) !== field.source || !Number.isInteger(field.page) || field.page < 1 || field.page > 1e5 || !MANUAL_FIELD_TYPES.includes(field.type) || typeof field.name !== "string" || !field.name.trim() || field.name.length > 120)
    return false;
  const { x, y, width, height } = field;
  return [x, y, width, height].every(finite) && x >= 0 && y >= 0 && width >= MIN_MANUAL_SIZE && height >= MIN_MANUAL_SIZE && x <= 1 && y <= 1 && width <= 1 && height <= 1 && x + width <= 1 && y + height <= 1;
}
function manualFieldsForSource(pdf, source) {
  const key = sourceKey(source);
  if (!key || !Array.isArray(pdf?.manualFields))
    return [];
  return pdf.manualFields.filter((field) => validManualField(field) && field.source === key);
}
function manualFieldSpec(field) {
  const key = manualFieldKey(field);
  if (!key || !MANUAL_FIELD_TYPES.includes(field.type))
    return null;
  return {
    path: `sheet.fields.${key}`,
    type: field.type === "checkbox" ? "boolean" : field.type === "number" ? "number" : "string"
  };
}
function manualFieldBounds(field, viewport, offsetTop = 0) {
  return {
    left: field.x * viewport.width,
    top: field.y * viewport.height + offsetTop,
    width: field.width * viewport.width,
    height: field.height * viewport.height,
    hidden: false
  };
}

// ../../pdf_system/sheet-shape.js
function pdfCharacterDefaults() {
  return {
    pdf: { template: "generic", page: 1, zoom: 1, spread: false, asset: "", textColor: "#111111" },
    fields: {},
    ac: 0,
    init: 0,
    bio: "",
    history: "",
    notes: "",
    token: { size: 1, bars: { bar1Value: "", bar1Max: "", bar2Value: "", bar2Max: "", initiative: "", defense: "" }, display: { name: true, bar_1: true, bar_2: true } },
    bars: { bar_1: { value: 0, max: 0 }, bar_2: { value: 0, max: 0 } }
  };
}
function normalizePdfCharacterData(value) {
  const defaults = pdfCharacterDefaults();
  const merge = (base, source) => Object.fromEntries(Object.entries(base).map(([key, fallback]) => {
    const incoming = source[key];
    return [key, fallback && typeof fallback === "object" && !Array.isArray(fallback) && incoming && typeof incoming === "object" && !Array.isArray(incoming) ? merge(fallback, incoming) : incoming ?? fallback];
  }).concat(Object.entries(source).filter(([key]) => !(key in base))));
  return merge(defaults, value);
}

// ../../pdf_system/frontend/field-actions.js
function actionsForSource(pdf, source) {
  const key = sourceKey(source), result = /* @__PURE__ */ Object.create(null);
  const actions = Array.isArray(pdf?.fieldActions) ? pdf.fieldActions : [];
  for (const action of actions) {
    if (action?.source === key && typeof action.field === "string" && action.roll)
      result[action.field] = action.roll;
  }
  return result;
}
function numericFieldValue(value) {
  if (value === "" || value === void 0 || value === null) return 0;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "string") {
    const text2 = value.trim();
    if (!text2) return 0;
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text2))
      throw new Error("This field needs a numeric value.");
    value = Number(text2);
  }
  if (typeof value !== "number" || !Number.isFinite(value) || Math.abs(value) > 1e6)
    throw new Error("This field needs a numeric value.");
  return value;
}
function storedValue(spec, value) {
  if (spec.type === "number") return numericFieldValue(value);
  if (spec.type === "boolean") return Boolean(value);
  return String(value ?? "");
}
function fieldActionCandidate(actor, source, name, config, fields, originals) {
  const spec = fields[name], original = originals[name];
  if (!spec || !original || !config || typeof config !== "object" || typeof config.bar !== "string" || typeof config.formula !== "string" || typeof config.label !== "string")
    throw new Error("Invalid PDF field action.");
  const slot = BAR_SLOTS.find((slot2) => slot2.key === config.bar);
  if (config.bar && !slot) throw new Error("Invalid token mapping.");
  if (slot && (original.type === "boolean" || spec.multiline))
    throw new Error("Checkbox and multiline fields cannot be linked to a token bar.");
  const candidate = structuredClone(actor);
  const bars = candidate.data.token.bars;
  const current = readCanonical(actor, spec.path);
  for (const previous of BAR_SLOTS) {
    if (bars[previous.key] === name) {
      writeCanonical(candidate, original.path, storedValue(original, current));
      bars[previous.key] = "";
    }
  }
  if (slot) {
    const displaced = bars[slot.key];
    if (displaced && fields[displaced] && originals[displaced])
      writeCanonical(
        candidate,
        originals[displaced].path,
        storedValue(originals[displaced], readCanonical(actor, fields[displaced].path))
      );
    bars[slot.key] = name;
    writeCanonical(candidate, slot.path, numericFieldValue(current));
  }
  const key = sourceKey(source);
  const actions = (candidate.data.pdf.fieldActions || []).filter((action) => action.source !== key || action.field !== name);
  if (config.formula.trim()) actions.push({
    source: key,
    field: name,
    roll: { formula: config.formula.trim(), label: config.label.trim() }
  });
  candidate.data.pdf.fieldActions = actions;
  return candidate;
}

// ../../pdf_system/frontend/formulas.js
var fail = (message) => {
  throw new Error(message);
};
var finite2 = (value) => {
  if (!Number.isFinite(value)) fail("Could not calculate this PDF field. Check its formula and numeric values.");
  return value;
};
var numeric = (value) => {
  if (value === void 0 || value === null || value === "") return 0;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "string") {
    value = value.trim();
    if (!value) return 0;
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)) fail("This field needs a numeric value.");
    value = Number(value);
  }
  if (typeof value !== "number" || !Number.isFinite(value) || Math.abs(value) > 1e6)
    fail("This field needs a numeric value.");
  return value === 0 ? 0 : value;
};
function decimal(value) {
  const text2 = String(numeric(value));
  if (!text2.includes("e")) return text2;
  const [mantissa, exponent] = text2.split("e");
  const sign = mantissa.startsWith("-") ? "-" : "";
  const unsigned = mantissa.replace("-", ""), digits = unsigned.replace(".", "");
  const point = unsigned.split(".")[0].length + Number(exponent);
  return point <= 0 ? sign + "0." + "0".repeat(-point) + digits : sign + digits.slice(0, point) + (point < digits.length ? "." + digits.slice(point) : "0".repeat(point - digits.length));
}
function fieldReference(field) {
  if (typeof field !== "string" || !field.trim() || field.includes("\0")) fail("Invalid PDF field reference.");
  return "@{" + field.replaceAll("\\", "\\\\").replaceAll("}", "\\}") + "}";
}
function parts(formula, allowValue = true) {
  if (typeof formula !== "string" || !formula.trim() || formula.length > 512)
    fail("Use a PDF field formula with 1 to 512 characters.");
  const result = [];
  let offset = 0;
  while (offset < formula.length) {
    const start = formula.indexOf("@", offset);
    if (start < 0) {
      result.push(formula.slice(offset));
      break;
    }
    result.push(formula.slice(offset, start));
    const value = /^@value(?![A-Za-z0-9_.])/.exec(formula.slice(start));
    if (value) {
      if (!allowValue) fail("Calculated fields must reference other fields instead of @value.");
      result.push({ field: null });
      offset = start + value[0].length;
      continue;
    }
    if (!formula.startsWith("@{", start)) fail("Use @value or @{field} to reference PDF fields.");
    offset = start + 2;
    let name = "";
    while (offset < formula.length && formula[offset] !== "}") {
      let character = formula[offset++];
      if (character === "\\") {
        character = formula[offset++];
        if (character !== "\\" && character !== "}") fail("Invalid PDF field reference.");
      }
      name += character;
    }
    if (offset >= formula.length || !name.trim() || name.includes("\0")) fail("Invalid PDF field reference.");
    result.push({ field: name });
    offset += 1;
  }
  return result;
}
function fieldReferences(formula, { allowValue = true } = {}) {
  return [...new Set(parts(formula, allowValue).filter((part) => typeof part !== "string" && part.field !== null).map((part) => part.field))];
}
function expandFieldFormula(formula, resolve, { value, allowValue = true, maxLength = 512 } = {}) {
  const expression = parts(formula, allowValue).map((part) => typeof part === "string" ? part : `(${decimal(part.field === null ? value : resolve(part.field))})`).join("").trim();
  if (expression.length > maxLength) fail("The resolved roll formula is too long.");
  return expression;
}
function calculationPlan(formula) {
  const tokens = [];
  for (const part of parts(formula, false)) {
    if (typeof part !== "string") {
      tokens.push({ kind: "reference", field: part.field });
      continue;
    }
    let text2 = part;
    while (text2) {
      const whitespace = /^[\s\uFEFF]+/.exec(text2);
      if (whitespace) {
        text2 = text2.slice(whitespace[0].length);
        continue;
      }
      const number = /^(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)/.exec(text2);
      const identifier = /^[A-Za-z_][A-Za-z0-9_]*/.exec(text2);
      const operator = /^(?:>=|<=|==|!=|[+*/<>()!,\-])/.exec(text2);
      if (number) {
        tokens.push({ kind: "number", value: finite2(Number(number[0])) });
        text2 = text2.slice(number[0].length);
      } else if (identifier) {
        tokens.push({ kind: "identifier", name: identifier[0] });
        text2 = text2.slice(identifier[0].length);
      } else if (operator) {
        tokens.push({ kind: operator[0] });
        text2 = text2.slice(operator[0].length);
      } else fail("Invalid PDF field formula.");
    }
  }
  let position = 0, nesting = 0;
  const peek = () => tokens[position]?.kind;
  const consume = (kind) => peek() === kind ? tokens[position++] : null;
  const required = (kind) => consume(kind) || fail("Invalid PDF field formula.");
  const nested = (read) => {
    if (++nesting > 32) fail("Invalid PDF field formula.");
    try {
      return read();
    } finally {
      nesting--;
    }
  };
  function primary() {
    const number = consume("number") || consume("reference");
    if (number) return number;
    if (consume("(")) {
      const node = nested(comparison);
      required(")");
      return node;
    }
    const identifier = consume("identifier");
    if (!identifier) fail("Invalid PDF field formula.");
    if (/^d(?:[0-9]|[Ff])/.test(identifier.name)) fail("Calculated fields cannot roll dice.");
    required("(");
    const args = [];
    if (!consume(")")) {
      do {
        args.push(nested(comparison));
      } while (consume(","));
      required(")");
    }
    return { kind: "call", name: identifier.name, args };
  }
  function unary() {
    const operator = consume("+") || consume("-");
    return operator ? { kind: "unary", operator: operator.kind, operand: nested(unary) } : primary();
  }
  function binary(read, choices) {
    let left = read();
    while (choices.includes(peek())) {
      const operator = tokens[position++].kind;
      left = { kind: "binary", operator, left, right: read() };
    }
    return left;
  }
  const multiplicative = () => binary(unary, ["*", "/"]);
  const additive = () => binary(multiplicative, ["+", "-"]);
  function comparison() {
    const left = additive();
    if (![">=", "<=", "==", "!=", ">", "<"].includes(peek())) return left;
    const operator = tokens[position++].kind;
    return { kind: "comparison", operator, left, right: additive() };
  }
  const root = comparison();
  if (position !== tokens.length) fail("Invalid PDF field formula.");
  let nodes = 0;
  function check(node, depth = 1) {
    if (++nodes > 1e3 || depth > 128) fail("Invalid PDF field formula.");
    const children = node.args || (node.operand ? [node.operand] : node.left ? [node.left, node.right] : []);
    if (children.some((child) => check(child, depth + 1) !== "number")) fail("Invalid PDF field formula.");
    if (node.kind === "call") {
      const ranges = { floor: [1, 1], ceil: [1, 1], round: [1, 1], abs: [1, 1], min: [2, 100], max: [2, 100], clamp: [3, 3] };
      const range = Object.hasOwn(ranges, node.name) && ranges[node.name];
      if (!range || children.length < range[0] || children.length > range[1]) fail("Invalid PDF field formula.");
    }
    return node.kind === "comparison" ? "boolean" : "number";
  }
  check(root);
  return root;
}
function calculateFormula(formula, resolve) {
  const root = calculationPlan(formula);
  function execute(node) {
    if (node.kind === "reference") return numeric(resolve(node.field));
    if (node.kind === "number") return node.value;
    if (node.kind === "unary") return finite2((node.operator === "-" ? -1 : 1) * execute(node.operand));
    if (node.kind === "call") {
      const args = node.args.map(execute);
      if (node.name === "clamp") {
        if (args[1] > args[2]) fail("Could not calculate this PDF field. Check its formula and numeric values.");
        return finite2(Math.min(Math.max(args[0], args[1]), args[2]));
      }
      return finite2(Math[node.name](...args));
    }
    const left = execute(node.left), right = execute(node.right);
    if (node.kind === "comparison") return { ">=": left >= right, "<=": left <= right, "==": left === right, "!=": left !== right, ">": left > right, "<": left < right }[node.operator];
    if (node.operator === "/" && right === 0) fail("Could not calculate this PDF field. Check its formula and numeric values.");
    return finite2(node.operator === "+" ? left + right : node.operator === "-" ? left - right : node.operator === "*" ? left * right : left / right);
  }
  return numeric(execute(root));
}
var validPath = (path) => typeof path === "string" && (BAR_SLOTS.some((slot) => slot.path === path) || /^sheet\.fields\.[A-Za-z0-9_-]{1,512}$/.test(path) && !["__proto__", "prototype", "constructor"].includes(path.slice(13)));
function captureFieldBindings(source, originals, fieldIndex) {
  const key = sourceKey(source), result = [];
  if (!key) return result;
  for (const [field, spec] of Object.entries(originals)) {
    if (!validPath(spec.path) || !["string", "number", "boolean"].includes(spec.type) || field.length > 512 || !field.trim()) continue;
    const info = fieldIndex?.get(field);
    result.push({
      source: key,
      field,
      path: spec.path,
      type: spec.type,
      name: String(info?.manual?.name || spec.label || field).slice(0, 512),
      readOnly: !!info?.readOnly
    });
  }
  return result;
}
function bindingsForSource(pdf, source) {
  const key = sourceKey(source), result = /* @__PURE__ */ Object.create(null);
  for (const binding of pdf?.fieldBindings || []) {
    if (binding.source === key && validPath(binding.path)) result[binding.field] = binding;
  }
  for (const field of manualFieldsForSource(pdf, key)) {
    const name = manualFieldKey(field), spec = manualFieldSpec(field);
    result[name] = {
      source: key,
      field: name,
      ...spec,
      name: field.name,
      readOnly: false,
      multiline: field.type === "multiline",
      manual: true
    };
  }
  return result;
}
function bindingPath(data, binding) {
  const matches = BAR_SLOTS.filter((slot) => data.token?.bars?.[slot.key] === binding.field);
  return matches.length ? (binding.manual ? matches[0] : matches.at(-1)).path : binding.path;
}
function recalculateFields(actor, source, { previous } = {}) {
  const key = sourceKey(source), pdf = actor.data.pdf;
  const definitions = (pdf.calculatedFields || []).filter((entry) => entry.source === key);
  const bindings = bindingsForSource(pdf, key), targets = new Map(definitions.map((entry) => [entry.field, entry]));
  const fields = new Set(targets.keys()), errors = [], paths = /* @__PURE__ */ new Map(), order = [];
  const visiting = /* @__PURE__ */ new Set(), visited = /* @__PURE__ */ new Set();
  let changed2 = false;
  try {
    let visit = function(field) {
      if (visiting.has(field)) fail("Calculated PDF fields cannot contain circular references.");
      if (visited.has(field)) return;
      visiting.add(field);
      calculationPlan(targets.get(field).formula);
      for (const reference of fieldReferences(targets.get(field).formula, { allowValue: false })) {
        if (!bindings[reference]) fail("A referenced PDF field is not available.");
        const dependency = paths.get(bindingPath(actor.data, bindings[reference]));
        if (dependency) visit(dependency);
      }
      visiting.delete(field);
      visited.add(field);
      order.push(targets.get(field));
    };
    for (const field of fields) {
      const binding = bindings[field];
      if (!binding) fail("A calculated PDF field is not available.");
      if (binding.type === "boolean" || binding.multiline || binding.readOnly) fail("This PDF field cannot be calculated.");
      const path = bindingPath(actor.data, binding);
      if (paths.has(path)) fail("Calculated PDF fields must use different value addresses.");
      paths.set(path, field);
    }
    for (const field of fields) visit(field);
  } catch (error) {
    return { changed: changed2, errors: [{ field: "", message: error.message }], fields };
  }
  for (const entry of order) {
    const binding = bindings[entry.field], path = bindingPath(actor.data, binding);
    const type = BAR_SLOTS.some((slot) => slot.path === path) ? "number" : binding.type;
    let value;
    try {
      value = calculateFormula(entry.formula, (field) => readCanonical(actor, bindingPath(actor.data, bindings[field])));
      if (type === "string") value = decimal(value);
    } catch (error) {
      errors.push({ field: entry.field, message: error.message });
      if (!previous) continue;
      const old = bindingsForSource(previous.data.pdf, key)[entry.field] || binding;
      value = readCanonical(previous, bindingPath(previous.data, old));
      try {
        value = type === "string" ? String(value ?? "0") : numeric(value);
      } catch {
        value = 0;
      }
    }
    if (readCanonical(actor, path) !== value) {
      writeCanonical(actor, path, value);
      changed2 = true;
    }
  }
  return { changed: changed2, errors, fields };
}

// ../../pdf_system/frontend/layout-history.js
var LISTS = ["manualFields", "fieldActions", "calculatedFields", "fieldBindings"];
function captureLayout(actor, source) {
  const key = sourceKey(source);
  const snapshot = { source: key, bars: structuredClone(actor.data.token.bars) };
  for (const list of LISTS) snapshot[list] = structuredClone((actor.data.pdf[list] || []).filter((row) => row.source === key));
  return snapshot;
}
function restoreLayout(actor, snapshot) {
  for (const list of LISTS)
    actor.data.pdf[list] = [...(actor.data.pdf[list] || []).filter((row) => row.source !== snapshot.source), ...structuredClone(snapshot[list])];
  actor.data.token.bars = structuredClone(snapshot.bars);
}
function copyLayout(actor, source, ids, fields) {
  const key = sourceKey(source), selected = new Set(ids);
  const definitions = (actor.data.pdf.manualFields || []).filter((field) => field.source === key && selected.has(field.id));
  if (!definitions.length) return null;
  const keys = new Set(definitions.map(manualFieldKey));
  const values = /* @__PURE__ */ Object.create(null);
  for (const field of definitions) values[manualFieldKey(field)] = readCanonical(actor, fields[manualFieldKey(field)]?.path || `sheet.fields.${manualFieldKey(field)}`);
  return {
    version: 1,
    source: key,
    fields: structuredClone(definitions),
    values,
    actions: structuredClone((actor.data.pdf.fieldActions || []).filter((row) => row.source === key && keys.has(row.field))),
    calculations: structuredClone((actor.data.pdf.calculatedFields || []).filter((row) => row.source === key && keys.has(row.field)))
  };
}
function remapFormula(formula, keys) {
  let result = formula;
  for (const key of fieldReferences(formula))
    if (keys.has(key)) result = result.split(fieldReference(key)).join(fieldReference(keys.get(key)));
  return result;
}
function pasteLayout(actor, source, clipboard, { page, pageCount, dx = 0.02, dy = 0.02, uuid = () => crypto.randomUUID() }) {
  const key = sourceKey(source);
  if (!clipboard || clipboard.version !== 1 || clipboard.source !== key || !Array.isArray(clipboard.fields) || !clipboard.fields.length || !clipboard.fields.every(validManualField) || ![dx, dy].every(Number.isFinite)) throw new Error("Copy fields from this PDF before pasting.");
  const all = actor.data.pdf.manualFields || [];
  if (all.length + clipboard.fields.length > MAX_MANUAL_FIELDS) throw new Error("Use at most 256 manual PDF fields.");
  const candidate = structuredClone(actor), keys = /* @__PURE__ */ new Map();
  const firstPage = Math.min(...clipboard.fields.map((field) => field.page));
  const minX = Math.min(...clipboard.fields.map((field) => field.x)), minY = Math.min(...clipboard.fields.map((field) => field.y));
  const maxX = Math.max(...clipboard.fields.map((field) => field.x + field.width)), maxY = Math.max(...clipboard.fields.map((field) => field.y + field.height));
  dx = Math.max(-minX, Math.min(1 - maxX, dx));
  dy = Math.max(-minY, Math.min(1 - maxY, dy));
  const definitions = clipboard.fields.map((field) => {
    const next = {
      ...field,
      id: uuid(),
      source: key,
      page: page + field.page - firstPage,
      x: Math.max(0, Math.min(1 - field.width, field.x + dx)),
      y: Math.max(0, Math.min(1 - field.height, field.y + dy))
    };
    if (!validManualField(next) || next.page > pageCount) throw new Error("Choose a PDF page that can contain the copied fields.");
    keys.set(manualFieldKey(field), manualFieldKey(next));
    return next;
  });
  candidate.data.pdf.manualFields = [...all, ...definitions];
  for (const field of definitions) {
    const oldKey = [...keys].find(([, next]) => next === manualFieldKey(field))[0];
    const value = clipboard.values[oldKey];
    if (value !== void 0) candidate.data.fields[manualFieldKey(field)] = field.type === "text" || field.type === "multiline" ? String(value) : value;
  }
  for (const [list, rows] of [["fieldActions", clipboard.actions], ["calculatedFields", clipboard.calculations]]) {
    const copies = (rows || []).map((row) => ({
      ...row,
      source: key,
      field: keys.get(row.field),
      ...list === "fieldActions" ? { roll: { ...row.roll, formula: remapFormula(row.roll.formula, keys) } } : { formula: remapFormula(row.formula, keys) }
    }));
    if (copies.length) candidate.data.pdf[list] = [...candidate.data.pdf[list] || [], ...copies];
  }
  return { candidate, ids: definitions.map((field) => field.id) };
}

// ../../pdf_system/frontend/layout-editor.js
var finite3 = (value) => typeof value === "number" && Number.isFinite(value);
var clamp = (value, lower, upper) => Math.max(lower, Math.min(upper, value));
var valid = (field) => field && typeof field.id === "string" && [field.x, field.y, field.width, field.height].every(finite3) && field.x >= 0 && field.y >= 0 && field.width >= 1e-3 && field.height >= 1e-3 && field.x + field.width <= 1 && field.y + field.height <= 1;
var nearest = (value, step) => finite3(step) && step > 0 ? Math.round(value / step) * step : value;
function groups(fields) {
  const pages = /* @__PURE__ */ new Map(), seen = /* @__PURE__ */ new Set();
  for (const field of fields || []) {
    if (!valid(field) || seen.has(field.id)) continue;
    seen.add(field.id);
    const key = JSON.stringify([field.source || "", field.page || 1]);
    if (!pages.has(key)) pages.set(key, []);
    pages.get(key).push(field);
  }
  return [...pages.values()];
}
function changed(field, changes) {
  return Object.keys(changes).some((key) => Math.abs(field[key] - changes[key]) > 1e-12) ? { id: field.id, changes } : null;
}
function layoutBounds(fields) {
  const rows = (fields || []).filter(valid);
  if (!rows.length) return null;
  const x = Math.min(...rows.map((field) => field.x));
  const y = Math.min(...rows.map((field) => field.y));
  return {
    x,
    y,
    width: Math.max(...rows.map((field) => field.x + field.width)) - x,
    height: Math.max(...rows.map((field) => field.y + field.height)) - y
  };
}
function moveLayoutFields(fields, dx, dy, grid = {}) {
  if (!finite3(dx) || !finite3(dy)) return [];
  return groups(fields).flatMap((rows) => {
    const bounds = layoutBounds(rows);
    const x = clamp(nearest(bounds.x + dx, grid.x), 0, 1 - bounds.width);
    const y = clamp(nearest(bounds.y + dy, grid.y), 0, 1 - bounds.height);
    return rows.map((field) => changed(field, {
      x: clamp(field.x + x - bounds.x, 0, 1 - field.width),
      y: clamp(field.y + y - bounds.y, 0, 1 - field.height)
    })).filter(Boolean);
  });
}
function alignLayoutFields(fields, alignment) {
  if (!["left", "right", "top", "bottom", "center-x", "center-y"].includes(alignment)) return [];
  return groups(fields).flatMap((rows) => {
    if (rows.length < 2) return [];
    const bounds = layoutBounds(rows);
    return rows.map((field) => {
      const changes = alignment === "left" ? { x: bounds.x } : alignment === "right" ? { x: bounds.x + bounds.width - field.width } : alignment === "top" ? { y: bounds.y } : alignment === "bottom" ? { y: bounds.y + bounds.height - field.height } : alignment === "center-x" ? { x: bounds.x + (bounds.width - field.width) / 2 } : { y: bounds.y + (bounds.height - field.height) / 2 };
      if (changes.x !== void 0) changes.x = clamp(changes.x, 0, 1 - field.width);
      if (changes.y !== void 0) changes.y = clamp(changes.y, 0, 1 - field.height);
      return changed(field, changes);
    }).filter(Boolean);
  });
}
function distributeLayoutFields(fields, axis) {
  if (!["horizontal", "vertical"].includes(axis)) return [];
  const coordinate = axis === "horizontal" ? "x" : "y";
  const size = axis === "horizontal" ? "width" : "height";
  return groups(fields).flatMap((rows) => {
    if (rows.length < 3) return [];
    const ordered = [...rows].sort((a, b) => a[coordinate] - b[coordinate] || a.id.localeCompare(b.id));
    const first = ordered[0][coordinate];
    const last = ordered.at(-1)[coordinate] + ordered.at(-1)[size];
    const gap = (last - first - ordered.reduce((sum, field) => sum + field[size], 0)) / (ordered.length - 1);
    if (gap < -1e-12) return [];
    let cursor = first;
    const updates = /* @__PURE__ */ new Map();
    for (const field of ordered) {
      const update = changed(field, { [coordinate]: clamp(cursor, 0, 1 - field[size]) });
      if (update) updates.set(field.id, update);
      cursor += field[size] + Math.max(0, gap);
    }
    return rows.map((field) => updates.get(field.id)).filter(Boolean);
  });
}
function snapLayoutRect(rect, grid = {}) {
  if (!rect || ![rect.x, rect.y, rect.width, rect.height].every(finite3) || rect.width < 0 || rect.height < 0) return null;
  const x = clamp(nearest(rect.x, grid.x), 0, 0.999);
  const y = clamp(nearest(rect.y, grid.y), 0, 0.999);
  const right = clamp(nearest(rect.x + rect.width, grid.x), x + 1e-3, 1);
  const bottom = clamp(nearest(rect.y + rect.height, grid.y), y + 1e-3, 1);
  return { x, y, width: right - x, height: bottom - y };
}

// ../../pdf_system/frontend/raster-pdf.js
var encode = (value) => new TextEncoder().encode(value);
function rasterPdf(pages) {
  if (!Array.isArray(pages) || !pages.length || pages.length > 100)
    throw new Error("Export between 1 and 100 PDF pages.");
  const chunks = [], offsets = [0];
  let length = 0;
  const append = (value) => {
    const bytes = typeof value === "string" ? encode(value) : value;
    length += bytes.byteLength;
    if (length > 1e8) throw new Error("The filled PDF is too large to export.");
    chunks.push(bytes);
  };
  const object = (id, body) => {
    offsets[id] = length;
    append(`${id} 0 obj
`);
    for (const part of body) append(part);
    append("\nendobj\n");
  };
  append("%PDF-1.4\n");
  append(new Uint8Array([37, 226, 227, 207, 211, 10]));
  object(1, ["<< /Type /Catalog /Pages 2 0 R >>"]);
  object(2, [`<< /Type /Pages /Count ${pages.length} /Kids [${pages.map((_, i) => `${3 + 3 * i} 0 R`).join(" ")}] >>`]);
  pages.forEach((page, i) => {
    const { width, height, pixelWidth, pixelHeight, jpeg } = page;
    if (![width, height, pixelWidth, pixelHeight].every((n) => Number.isFinite(n) && n > 0 && n <= 32768) || !Number.isInteger(pixelWidth) || !Number.isInteger(pixelHeight) || !(jpeg instanceof Uint8Array) || jpeg.length < 4 || jpeg[0] !== 255 || jpeg[1] !== 216)
      throw new Error("Could not encode a filled PDF page.");
    const id = 3 + 3 * i;
    object(id, [`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /XObject << /PageImage ${id + 1} 0 R >> >> /Contents ${id + 2} 0 R >>`]);
    object(id + 1, [`<< /Type /XObject /Subtype /Image /Width ${pixelWidth} /Height ${pixelHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>
stream
`, jpeg, "\nendstream"]);
    const commands = `q
${width} 0 0 ${height} 0 0 cm
/PageImage Do
Q
`;
    object(id + 2, [`<< /Length ${encode(commands).length} >>
stream
${commands}endstream`]);
  });
  const start = length;
  append(`xref
0 ${offsets.length}
0000000000 65535 f\r
`);
  for (const offset of offsets.slice(1)) append(`${String(offset).padStart(10, "0")} 00000 n\r
`);
  append(`trailer
<< /Size ${offsets.length} /Root 1 0 R >>
startxref
${start}
%%EOF
`);
  const result = new Uint8Array(length);
  let cursor = 0;
  for (const chunk of chunks) {
    result.set(chunk, cursor);
    cursor += chunk.length;
  }
  return result;
}

// ../../pdf_system/frontend/diagnostics.js
function mappingDiagnostics(view) {
  const source = sourceKey(view.currentSource), pdf = view.actor?.data.pdf;
  if (!pdf || !source) return [];
  const issues = [], names = new Set(Object.keys(view.fields)), bindings = bindingsForSource(pdf, source);
  const issue = (code, field, message, params = {}) => issues.push({ code, field, message, params });
  const actual = view.sourceDocument;
  const expected = (pdf.sourceMetadata || []).find((row) => row.source === source);
  if (actual && expected) {
    if (expected.pageCount !== actual.pageCount)
      issue("page-count", "", "The PDF page count differs from the saved mapping. Check the field positions.");
    const changed2 = (expected.pages || []).some((page) => {
      const current = actual.pages.find((row) => row.page === page.page);
      return current && (Math.abs(current.width - page.width) > 0.5 || Math.abs(current.height - page.height) > 0.5 || current.rotation !== page.rotation);
    });
    if (changed2) issue("page-geometry", "", "PDF page sizes or rotations differ from the saved mapping. Check the field positions.");
    else if (expected.fingerprint && actual.fingerprint && expected.fingerprint !== actual.fingerprint)
      issue("document-changed", "", "This PDF differs from the document used to create the mapping.");
  }
  for (const field of (pdf.manualFields || []).filter((row) => row.source === source)) {
    if (!validManualField(field)) issue("field-bounds", "", "A mapped field has invalid page bounds: {0}.", [field.name || field.id]);
    else if (actual && field.page > actual.pageCount)
      issue("field-page", `manual_${field.id.replaceAll("-", "")}`, "A mapped field refers to a missing PDF page: {0}.", [field.name]);
  }
  for (const [kind, rows] of [["roll", pdf.fieldActions || []], ["calculation", pdf.calculatedFields || []]]) {
    for (const row of rows.filter((row2) => row2.source === source)) {
      if (!names.has(row.field)) issue("orphan-action", row.field, "An action has no matching PDF field: {0}.", [bindings[row.field]?.name || row.field]);
      const formula = kind === "roll" ? row.roll.formula : row.formula;
      try {
        for (const reference of fieldReferences(formula, { allowValue: kind === "roll" }))
          if (!names.has(reference)) issue("missing-reference", row.field, "A formula references a field that is no longer on this PDF: {0}.", [bindings[reference]?.name || reference]);
        if (kind === "roll") expandFieldFormula(formula, (reference) => {
          if (!bindings[reference]) throw Error("A referenced PDF field is not available.");
          return readCanonical(view.actor, bindingPath(view.actor.data, bindings[reference]));
        }, { value: view.fields[row.field] ? readCanonical(view.actor, view.fields[row.field].path) : "" });
      } catch (error) {
        issue("formula-value", row.field, error.message);
      }
    }
  }
  for (const error of view.calculationErrors || []) issue("calculation-value", error.field, error.message);
  return issues;
}

// ../../pdf_system/frontend/controller.js
function pdfController(host, options) {
  const props = options.props;
  const box = (initial) => {
    let value = initial;
    return {
      get value() {
        return value;
      },
      set value(next) {
        value = next;
        options.repaint();
      }
    };
  };
  const derive = (read) => ({
    get value() {
      return read();
    }
  }), reactive = (v) => v, nextTick = async () => {
    options.repaint();
    await new Promise(requestAnimationFrame);
  };
  const actor = box(null);
  const mapping = box(null);
  const campaignAssets = box([]);
  const loading = box(true);
  const error = box("");
  const saveError = box("");
  const actionError = box("");
  let disposed = false, sourceGeneration = 0, renderGeneration = 0;
  const sourceAbort = new AbortController();
  const activeTab = box("ficha");
  const pageLabel = box("-");
  const statusText = box("");
  const viewerMissing = box(false);
  const fields = reactive(/* @__PURE__ */ Object.create(null));
  const positions = reactive(/* @__PURE__ */ Object.create(null));
  const openFieldNames = box([]);
  const pickerOpen = box(false);
  const pageHost = box();
  const isGm = derive(() => props.block.context.role === "gm");
  const canEditNow = derive(() => actor.value?.canEdit === true);
  const currentSource = box(null);
  const mappingEditing = box(false), rendering = box(false), configuring = box(false), rolling = box(false);
  const exporting = box(false);
  const pageFrames = [], renderTasks = /* @__PURE__ */ new Set();
  const undoLayouts = [], redoLayouts = [];
  let sourceDocument = null, calculationErrors = [];
  let nativeFieldNames = [];
  let viewerDoc;
  let loadingTask;
  let exportAbort;
  function releasePdf() {
    for (const task2 of renderTasks) task2.cancel();
    renderTasks.clear();
    pageFrames.length = 0;
    const task = loadingTask;
    loadingTask = void 0;
    viewerDoc = void 0;
    if (task)
      void task.destroy().catch(() => {
      });
  }
  const fieldIndex = /* @__PURE__ */ new Map();
  let saveTimer;
  let saving = false;
  let saveQueued = false;
  function fieldValue(pdfField) {
    const spec = fields[pdfField];
    if (!spec || !actor.value)
      return "";
    const value = readCanonical(actor.value, spec.path);
    if (spec.type === "boolean")
      return Boolean(value);
    if (spec.type === "number")
      return typeof value === "number" ? value : "";
    return typeof value === "string" ? value : "";
  }
  function onFieldInput(pdfField, event) {
    const spec = fields[pdfField];
    if (!spec || spec.calculated || !actor.value || !canEditNow.value)
      return;
    const target = event.target;
    const raw = spec.type === "boolean" ? target.checked : spec.type === "number" ? target.value === "" ? 0 : Number(target.value) : target.value;
    if (spec.manualId && spec.type === "number") {
      const message = text("Use a number between -1000000 and 1000000.");
      if (target.validity?.badInput || !Number.isFinite(raw) || Math.abs(raw) > 1e6) {
        target.setCustomValidity(message);
        target.setAttribute("aria-invalid", "true");
        statusText.value = message;
        return;
      }
      target.setCustomValidity("");
      target.removeAttribute("aria-invalid");
      if (statusText.value === message) statusText.value = "";
    }
    writeCanonical(actor.value, spec.path, raw);
    recalculate();
    scheduleSave();
  }
  function scheduleSave() {
    if (!canEditNow.value || disposed)
      return;
    saveQueued = true;
    if (saveTimer)
      clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      saveTimer = void 0;
      void save();
    }, 400);
  }
  async function save() {
    if (!actor.value || !canEditNow.value)
      return;
    if (saving) {
      saveQueued = true;
      return;
    }
    saving = true;
    saveQueued = false;
    try {
      recalculate();
      const snapshot = JSON.parse(JSON.stringify(actor.value));
      if (props.tokenId)
        snapshot.data.token.name = snapshot.name;
      const result = await options.save(snapshot);
      actor.value.sheetVersion = result.sheetVersion;
      actor.value.version = result.version;
      saveError.value = "";
    } catch (reason) {
      saveError.value = reason.code === "conflict" ? "This sheet was changed in another window. Your changes remain here. Copy anything you want to preserve before reloading." : "Could not save. Your changes remain here; try again.";
      saveQueued = false;
    } finally {
      saving = false;
      if (saveQueued) {
        if (disposed)
          void save();
        else
          scheduleSave();
      }
      options.repaint();
    }
  }
  async function flush() {
    clearTimeout(saveTimer);
    while (saving || saveQueued) {
      clearTimeout(saveTimer);
      if (saving) await new Promise((resolve) => setTimeout(resolve, 20));
      else await save();
    }
    if (saveError.value) throw new Error(saveError.value);
  }
  async function fetchPdfBytes(kind, id) {
    if (kind === "template")
      return new Uint8Array(await props.block.assets.bytes("assets/blank-a4.pdf"));
    const file = await props.block.host.call("asset.download", { id }, { signal: sourceAbort.signal });
    return new Uint8Array(await file.blob.arrayBuffer());
  }
  function resolveSource() {
    if (!actor.value)
      return null;
    const assetId = actor.value.data.pdf.asset;
    if (assetId)
      return { kind: "asset", id: assetId };
    const templateId = actor.value.data.pdf.template || Object.keys(mapping.value?.templates ?? {})[0] || "";
    if (!templateId || !mapping.value?.templates[templateId])
      return null;
    return { kind: "template", id: templateId };
  }
  async function indexFields(doc) {
    const indexed = /* @__PURE__ */ new Map();
    indexed.documentPages = [];
    for (let number = 1; number <= doc.numPages; number += 1) {
      const page = await doc.getPage(number);
      const viewport = page.getViewport({ scale: 1 });
      if (indexed.documentPages.length < 1024 && viewport.width <= 32768 && viewport.height <= 32768)
        indexed.documentPages.push({ page: number, width: viewport.width, height: viewport.height, rotation: viewport.rotation });
      const annotations = await page.getAnnotations({ intent: "display" });
      for (const annotation of annotations) {
        if (!annotation.fieldName || annotation.subtype !== "Widget")
          continue;
        if (!indexed.has(annotation.fieldName)) {
          indexed.set(annotation.fieldName, {
            page: number,
            rect: annotation.rect,
            fieldType: annotation.fieldType ?? "Tx",
            readOnly: Boolean(annotation.readOnly)
          });
        }
      }
    }
    return indexed;
  }
  function fieldTypeOf(name) {
    return fieldIndex.get(name)?.fieldType ?? "Tx";
  }
  function computeFields(source, templateFields) {
    if (!actor.value)
      return;
    const barChoices = actor.value.data.token.bars;
    Object.keys(fields).forEach((key) => delete fields[key]);
    for (const [key, info] of fieldIndex) if (info.manual) fieldIndex.delete(key);
    let next;
    if (!nativeFieldNames.length && templateFields && viewerMissing.value) {
      next = templateFields;
    } else {
      next = autoMapFields(nativeFieldNames, mapping.value?.templates.generic?.fields, fieldTypeOf, barChoices);
    }
    Object.assign(fields, next);
    const manual = manualFieldsForSource(actor.value.data.pdf, source);
    for (const field of manual) {
      const key = manualFieldKey(field);
      const slot = ["text", "number"].includes(field.type) && BAR_SLOTS.find((slot2) => barChoices[slot2.key] === key);
      fields[key] = {
        ...slot ? { path: slot.path, type: "number" } : manualFieldSpec(field),
        label: field.name,
        manualId: field.id,
        multiline: field.type === "multiline"
      };
      fieldIndex.set(key, {
        page: field.page,
        manual: field,
        readOnly: false,
        fieldType: field.type === "checkbox" ? "Btn" : "Tx"
      });
    }
    openFieldNames.value = [...nativeFieldNames, ...manual.map(manualFieldKey)];
    for (const entry of actor.value.data.pdf.calculatedFields || [])
      if (entry.source === sourceKey(source) && fields[entry.field]) fields[entry.field].calculated = true;
    recalculate();
    for (const name of Object.keys(positions)) if (!Object.hasOwn(fields, name)) delete positions[name];
  }
  function positionFields(viewport, pageNumber, offsetTop, visiblePages) {
    for (const name of Object.keys(fields)) {
      const info = fieldIndex.get(name);
      if (!info || !visiblePages.has(info.page)) {
        positions[name] = {
          left: 0,
          top: 0,
          width: 0,
          height: 0,
          hidden: true
        };
        continue;
      }
      if (info.page !== pageNumber)
        continue;
      positions[name] = info.manual ? manualFieldBounds(info.manual, viewport, offsetTop) : fieldBounds(viewport, info.rect, offsetTop);
    }
  }
  async function render() {
    if (!viewerDoc || !pageHost.value || !actor.value) return;
    const generation = ++renderGeneration;
    for (const task of renderTasks) task.cancel();
    renderTasks.clear();
    pageFrames.length = 0;
    rendering.value = true;
    try {
      await renderPages(generation);
    } catch {
      if (!disposed && generation === renderGeneration)
        statusText.value = text("Could not render the page.");
    } finally {
      if (!disposed && generation === renderGeneration) rendering.value = false;
    }
  }
  async function renderPages(generation) {
    if (!viewerDoc || !pageHost.value || !actor.value)
      return;
    const doc = viewerDoc;
    pageHost.value.replaceChildren();
    const first = Math.max(1, Math.min(doc.numPages, actor.value.data.pdf.page));
    actor.value.data.pdf.page = first;
    const last = actor.value.data.pdf.spread ? Math.min(first + 1, viewerDoc.numPages) : first;
    const visible = /* @__PURE__ */ new Set();
    for (let number = first; number <= last; number += 1)
      visible.add(number);
    for (const name of Object.keys(fields))
      if (!visible.has(fieldIndex.get(name)?.page ?? -1))
        positions[name] = {
          left: 0,
          top: 0,
          width: 0,
          height: 0,
          hidden: true
        };
    let offsetTop = 0;
    for (let number = first; number <= last; number += 1) {
      const page = await doc.getPage(number);
      if (disposed || generation !== renderGeneration)
        return;
      const viewport = page.getViewport({ scale: actor.value.data.pdf.zoom });
      const canvas = pageHost.value.ownerDocument.createElement("canvas");
      canvas.className = "pdf-sheet__canvas";
      canvas.dataset.pdfPage = number;
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      pageHost.value.append(canvas);
      try {
        const task = page.render({
          canvas,
          viewport,
          transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0]
        });
        renderTasks.add(task);
        try {
          await task.promise;
        } finally {
          renderTasks.delete(task);
        }
      } catch (reason) {
        if (disposed || generation !== renderGeneration)
          return;
        statusText.value = text("Could not render the page.");
        return;
      }
      if (disposed || generation !== renderGeneration)
        return;
      positionFields(viewport, number, offsetTop, visible);
      pageFrames.push({ page: number, viewport, top: offsetTop });
      offsetTop += viewport.height;
    }
    pageLabel.value = `${actor.value.data.pdf.page} / ${viewerDoc.numPages}`;
  }
  async function openSource() {
    const generation = ++sourceGeneration;
    ++renderGeneration;
    const source = resolveSource();
    undoLayouts.length = redoLayouts.length = 0;
    exportAbort?.abort();
    sourceDocument = null;
    mappingEditing.value = false;
    currentSource.value = source;
    viewerMissing.value = false;
    statusText.value = "";
    openFieldNames.value = [];
    nativeFieldNames = [];
    releasePdf();
    Object.keys(fields).forEach((key) => delete fields[key]);
    if (!source)
      return;
    const templateFields = source.kind === "template" ? mapping.value?.templates[source.id]?.fields : void 0;
    try {
      const lib = await loadPdfjs(props.block.assets.url);
      const bytes = await fetchPdfBytes(source.kind, source.id);
      if (disposed || generation !== sourceGeneration)
        return;
      const task = lib.getDocument({ data: bytes, isEvalSupported: false });
      loadingTask = task;
      const doc = await task.promise;
      if (disposed || generation !== sourceGeneration) {
        await task.destroy();
        return;
      }
      viewerDoc = doc;
      const indexed = await indexFields(viewerDoc);
      if (disposed || generation !== sourceGeneration)
        return;
      fieldIndex.clear();
      for (const [key, value] of indexed) fieldIndex.set(key, value);
      nativeFieldNames = [...indexed.keys()];
      sourceDocument = {
        source: sourceKey(source),
        pageCount: doc.numPages,
        fingerprint: String(doc.fingerprints?.[0] || "").slice(0, 128),
        pages: indexed.documentPages
      };
      computeFields(source, templateFields);
      if (captureReferenceData()) scheduleSave();
      await nextTick();
      await render();
    } catch (reason) {
      if (disposed || generation !== sourceGeneration)
        return;
      viewerMissing.value = true;
      statusText.value = reason instanceof Error ? reason.message : text("Could not open the PDF.");
      fieldIndex.clear();
      computeFields(source, templateFields);
    }
  }
  function canMap() {
    return isGm.value && canEditNow.value && !disposed && !viewerMissing.value && !rendering.value && Boolean(viewerDoc) && pageFrames.length > 0;
  }
  function updatePositions() {
    if (!currentSource.value || !actor.value) return;
    computeFields(currentSource.value, currentSource.value.kind === "template" ? mapping.value?.templates[currentSource.value.id]?.fields : void 0);
    const visible = new Set(pageFrames.map((frame) => frame.page));
    for (const frame of pageFrames) positionFields(frame.viewport, frame.page, frame.top, visible);
    options.repaint();
  }
  function recalculate() {
    if (!actor.value || !currentSource.value) return;
    const result = recalculateFields(actor.value, currentSource.value);
    calculationErrors = result.errors;
    return result;
  }
  function captureReferenceData() {
    if (!actor.value || !isGm.value || !currentSource.value) return false;
    const pdf = actor.value.data.pdf, key = sourceKey(currentSource.value);
    let changed2 = false;
    const rows = new Map((pdf.fieldBindings || []).filter((row) => row.source === key).map((row) => [row.field, row]));
    for (const row of captureFieldBindings(currentSource.value, originalFields(), fieldIndex)) rows.set(row.field, row);
    const next = [...(pdf.fieldBindings || []).filter((row) => row.source !== key), ...rows.values()];
    if (next.length <= 1024 && JSON.stringify(next) !== JSON.stringify(pdf.fieldBindings || [])) {
      pdf.fieldBindings = next;
      changed2 = true;
    }
    if (sourceDocument && !(pdf.sourceMetadata || []).some((row) => row.source === key) && (pdf.sourceMetadata || []).length < 64) {
      pdf.sourceMetadata = [...pdf.sourceMetadata || [], structuredClone(sourceDocument)];
      changed2 = true;
    }
    return changed2;
  }
  function layoutChanged(before) {
    captureReferenceData();
    const after = captureLayout(actor.value, currentSource.value);
    if (JSON.stringify(before) !== JSON.stringify(after)) {
      undoLayouts.push(before);
      if (undoLayouts.length > 50) undoLayouts.shift();
      redoLayouts.length = 0;
    }
    updatePositions();
    scheduleSave();
  }
  function addManualField(type, name, page, rectangle) {
    if (!canMap() || !mappingEditing.value || !pageFrames.some((frame) => frame.page === page)) return false;
    const definitions = actor.value.data.pdf.manualFields || [];
    if (definitions.length >= MAX_MANUAL_FIELDS) {
      statusText.value = text("Use at most 256 manual PDF fields.");
      return false;
    }
    const labels = { text: "Text field", number: "Number field", checkbox: "Checkbox", multiline: "Multiline text" };
    if (!Object.hasOwn(labels, type)) return false;
    const field = {
      ...rectangle,
      id: crypto.randomUUID(),
      source: sourceKey(currentSource.value),
      page,
      type,
      name: typeof name === "string" && name.trim() ? name.trim() : text(labels[type])
    };
    if (!validManualField(field)) return false;
    const before = captureLayout(actor.value, currentSource.value);
    actor.value.data.pdf.manualFields = [...definitions, field];
    layoutChanged(before);
    return field.id;
  }
  function updateManualField(id, patch) {
    if (!canMap() || !mappingEditing.value || !patch || typeof patch !== "object" || Object.keys(patch).some((key) => !["name", "x", "y", "width", "height"].includes(key))) return false;
    const field = manualFieldsForSource(actor.value.data.pdf, currentSource.value).find((field2) => field2.id === id);
    if (!field) return false;
    const next = { ...field, ...patch };
    if (typeof next.name === "string") next.name = next.name.trim();
    if (!validManualField(next)) return false;
    const before = captureLayout(actor.value, currentSource.value);
    actor.value.data.pdf.manualFields = actor.value.data.pdf.manualFields.map((field2) => field2.id === id ? next : field2);
    layoutChanged(before);
    return true;
  }
  function removeManualField(id) {
    if (!canMap() || !mappingEditing.value) return false;
    const field = manualFieldsForSource(actor.value.data.pdf, currentSource.value).find((field2) => field2.id === id);
    if (!field) return false;
    const before = captureLayout(actor.value, currentSource.value);
    archiveManualValue(actor.value, field);
    actor.value.data.pdf.manualFields = actor.value.data.pdf.manualFields.filter((field2) => field2.id !== id);
    if (actor.value.data.pdf.fieldActions) {
      const source = sourceKey(currentSource.value), key = manualFieldKey(field);
      actor.value.data.pdf.fieldActions = actor.value.data.pdf.fieldActions.filter((action) => action.source !== source || action.field !== key);
    }
    if (actor.value.data.pdf.calculatedFields)
      actor.value.data.pdf.calculatedFields = actor.value.data.pdf.calculatedFields.filter((row) => row.source !== sourceKey(currentSource.value) || row.field !== manualFieldKey(field));
    for (const [slot, key] of Object.entries(actor.value.data.token.bars)) {
      if (key === manualFieldKey(field)) actor.value.data.token.bars[slot] = "";
    }
    layoutChanged(before);
    return true;
  }
  function editManualFields(edits) {
    if (!canMap() || !mappingEditing.value || !Array.isArray(edits) || !edits.length || edits.length > 256) return false;
    const source = sourceKey(currentSource.value), before = captureLayout(actor.value, source);
    const candidate = structuredClone(actor.value), seen = /* @__PURE__ */ new Set();
    for (const edit of edits) {
      if (!edit || seen.has(edit.id)) return false;
      seen.add(edit.id);
      const field = candidate.data.pdf.manualFields.find((row) => row.source === source && row.id === edit.id);
      if (!field) return false;
      if (edit.remove === true) {
        archiveManualValue(candidate, field);
        const key = manualFieldKey(field);
        candidate.data.pdf.manualFields = candidate.data.pdf.manualFields.filter((row) => row.id !== field.id);
        for (const list of ["fieldActions", "calculatedFields"])
          if (candidate.data.pdf[list]) candidate.data.pdf[list] = candidate.data.pdf[list].filter((row) => row.source !== source || row.field !== key);
        for (const slot of BAR_SLOTS) if (candidate.data.token.bars[slot.key] === key) candidate.data.token.bars[slot.key] = "";
      } else {
        if (!edit.changes || Object.keys(edit.changes).some((key) => !["x", "y", "width", "height", "name"].includes(key))) return false;
        const next = { ...field, ...edit.changes };
        if (typeof next.name === "string") next.name = next.name.trim();
        if (!validManualField(next)) return false;
        Object.assign(field, next);
      }
    }
    actor.value.data = candidate.data;
    layoutChanged(before);
    return true;
  }
  function archiveManualValue(candidate, field) {
    const key = manualFieldKey(field), current = fieldValue(key);
    const value = field.type === "number" && current === "" ? 0 : current;
    candidate.data.fields[key] = field.type === "text" || field.type === "multiline" ? String(value ?? "") : value;
  }
  function pasteManualFields(clipboard, offset = {}) {
    if (!canMap() || !mappingEditing.value) return false;
    const before = captureLayout(actor.value, currentSource.value);
    const { candidate, ids } = pasteLayout(
      actor.value,
      currentSource.value,
      clipboard,
      { ...offset, page: actor.value.data.pdf.page, pageCount: viewerDoc.numPages }
    );
    actor.value.data = candidate.data;
    layoutChanged(before);
    return ids;
  }
  function moveLayoutHistory(from, to) {
    if (!canMap() || !mappingEditing.value || !from.length) return false;
    to.push(captureLayout(actor.value, currentSource.value));
    restoreLayout(actor.value, from.pop());
    updatePositions();
    scheduleSave();
    return true;
  }
  function canConfigureFieldActions() {
    return isGm.value && canEditNow.value && !disposed && !rendering.value && !configuring.value && Boolean(currentSource.value) && sourceKey(resolveSource()) === sourceKey(currentSource.value);
  }
  function originalFields() {
    const originals = autoMapFields(nativeFieldNames, mapping.value?.templates.generic?.fields, fieldTypeOf, {});
    for (const field of manualFieldsForSource(actor.value.data.pdf, currentSource.value))
      originals[manualFieldKey(field)] = manualFieldSpec(field);
    if (viewerMissing.value && currentSource.value?.kind === "template")
      Object.assign(originals, mapping.value?.templates[currentSource.value.id]?.fields);
    return originals;
  }
  async function configureFieldAction(name, config) {
    if (!canConfigureFieldActions() || !Object.hasOwn(fields, name))
      throw new Error("Only the GM can configure PDF field actions.");
    const source = sourceKey(currentSource.value);
    configuring.value = true;
    try {
      await flush();
      if (disposed || sourceKey(currentSource.value) !== source || !Object.hasOwn(fields, name))
        throw new Error("This field is no longer available. Reopen the character sheet.");
      captureReferenceData();
      const candidate = fieldActionCandidate(actor.value, currentSource.value, name, config, fields, originalFields());
      if (config.calculation !== void 0 && typeof config.calculation !== "string") throw new Error("Invalid calculated PDF field.");
      if (config.calculation !== void 0) {
        const calculations = (candidate.data.pdf.calculatedFields || []).filter((row) => row.source !== source || row.field !== name);
        if (config.calculation.trim()) calculations.push({ source, field: name, formula: config.calculation.trim() });
        if (candidate.data.pdf.calculatedFields || config.calculation.trim()) candidate.data.pdf.calculatedFields = calculations;
      }
      recalculateFields(candidate, currentSource.value, { previous: actor.value });
      if (config.bar && fieldIndex.get(name)?.readOnly)
        throw new Error("This field cannot be linked to a token bar.");
      if (props.tokenId) candidate.data.token.name = candidate.name;
      saving = true;
      const result = await options.save(candidate);
      if (!disposed) {
        undoLayouts.length = redoLayouts.length = 0;
        actor.value.name = candidate.name;
        actor.value.data = candidate.data;
        actor.value.sheetVersion = result.sheetVersion;
        actor.value.version = result.version;
        saveError.value = "";
        updatePositions();
      }
      return true;
    } catch (failure) {
      if (!disposed && failure.code === "conflict")
        saveError.value = "This sheet was changed in another window. Your changes remain here. Copy anything you want to preserve before reloading.";
      throw failure;
    } finally {
      saving = false;
      configuring.value = false;
      if (saveQueued && !disposed) scheduleSave();
    }
  }
  async function rollField(name) {
    if (disposed || !canEditNow.value || rolling.value || !Object.hasOwn(fields, name)) return false;
    const source = sourceKey(currentSource.value);
    rolling.value = true;
    actionError.value = "";
    try {
      await flush();
      if (disposed) return false;
      if (sourceKey(currentSource.value) !== source)
        throw new Error("This field is no longer available. Reopen the character sheet.");
      const action = actionsForSource(actor.value.data.pdf, currentSource.value)[name];
      if (!action) return false;
      const bindings = bindingsForSource(actor.value.data.pdf, currentSource.value);
      const expression = expandFieldFormula(action.formula, (reference) => {
        if (!bindings[reference]) throw new Error("A referenced PDF field is not available.");
        return readCanonical(actor.value, bindingPath(actor.value.data, bindings[reference]));
      }, { value: fieldValue(name) });
      const label = action.label || Array.from(fields[name]?.label || name).slice(0, 48).join("");
      await options.roll({ expression, label, visibility: "public" }, { requestId: crypto.randomUUID() });
      if (!disposed) statusText.value = text("Roll sent to chat.");
      return true;
    } catch (failure) {
      if (!disposed) actionError.value = text(failure.message || "Could not roll this field. Try again.");
      throw failure;
    } finally {
      rolling.value = false;
    }
  }
  async function remapFields() {
    if (!actor.value || !currentSource.value)
      return;
    computeFields(currentSource.value, currentSource.value.kind === "template" ? mapping.value?.templates[currentSource.value.id]?.fields : void 0);
    await nextTick();
    await render();
  }
  function onBarChoice(slot, event) {
    if (!actor.value || !canEditNow.value)
      return;
    actor.value.data.token.bars[slot] = event.target.value || void 0;
    undoLayouts.length = redoLayouts.length = 0;
    scheduleSave();
    void remapFields();
  }
  async function chooseSource(kind, id) {
    if (!actor.value)
      return;
    pickerOpen.value = false;
    if (currentSource.value?.kind === kind && currentSource.value.id === id)
      return;
    actor.value.data.pdf.asset = kind === "asset" ? id : "";
    actor.value.data.pdf.template = kind === "template" ? id : "";
    actor.value.data.pdf.page = 1;
    await save();
    await openSource();
  }
  async function nextPage() {
    if (!actor.value || !viewerDoc)
      return;
    const step = actor.value.data.pdf.spread ? 2 : 1;
    actor.value.data.pdf.page = Math.min(viewerDoc.numPages, actor.value.data.pdf.page + step);
    scheduleSave();
    await render();
  }
  async function prevPage() {
    if (!actor.value || !viewerDoc)
      return;
    const step = actor.value.data.pdf.spread ? 2 : 1;
    actor.value.data.pdf.page = Math.max(1, actor.value.data.pdf.page - step);
    scheduleSave();
    await render();
  }
  async function zoomBy(factor) {
    if (!actor.value)
      return;
    actor.value.data.pdf.zoom = Math.max(0.1, Math.min(8, actor.value.data.pdf.zoom * factor));
    scheduleSave();
    await render();
  }
  async function fitPage() {
    if (!actor.value || !viewerDoc || !pageHost.value)
      return;
    const page = await viewerDoc.getPage(actor.value.data.pdf.page);
    const unscaled = page.getViewport({ scale: 1 });
    const available = pageHost.value.parentElement?.clientHeight || unscaled.height;
    actor.value.data.pdf.zoom = Math.max(0.1, Math.min(8, available / unscaled.height));
    scheduleSave();
    await render();
  }
  async function toggleSpread() {
    if (!actor.value)
      return;
    actor.value.data.pdf.spread = !actor.value.data.pdf.spread;
    scheduleSave();
    await render();
  }
  async function download() {
    if (!currentSource.value)
      return;
    const bytes = await fetchPdfBytes(currentSource.value.kind, currentSource.value.id);
    const url = URL.createObjectURL(new Blob([new Uint8Array(bytes).buffer], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${actor.value?.name || "sheet"}.pdf`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1e3);
  }
  function exportMappingBundle() {
    if (!canConfigureFieldActions()) throw new Error("Only the GM can manage PDF mappings.");
    captureReferenceData();
    const source = sourceKey(currentSource.value), pdf = actor.value.data.pdf;
    const bundle = { format: "gravewright.pdf-mapping", version: 1, bindings: {} };
    for (const list of ["manualFields", "fieldActions", "calculatedFields", "fieldBindings"])
      bundle[list] = (pdf[list] || []).filter((row) => row.source === source).map((row) => {
        const { source: ignored, ...definition } = structuredClone(row);
        return definition;
      });
    for (const slot of BAR_SLOTS) {
      const name = actor.value.data.token.bars[slot.key];
      bundle.bindings[slot.key] = name && fields[name] ? name : "";
    }
    const document2 = (pdf.sourceMetadata || []).find((row) => row.source === source) || sourceDocument;
    if (document2) {
      const { source: ignored, ...metadata } = structuredClone(document2);
      bundle.document = metadata;
    }
    return bundle;
  }
  async function applyMappingBundle(bundle) {
    if (!canConfigureFieldActions()) throw new Error("Only the GM can manage PDF mappings.");
    if (!bundle || bundle.format !== "gravewright.pdf-mapping" || bundle.version !== 1)
      throw new Error("Unsupported PDF mapping format or version.");
    const source = sourceKey(currentSource.value);
    configuring.value = true;
    try {
      await flush();
      if (source !== sourceKey(currentSource.value) || disposed) throw new Error("The PDF source changed. Reload the character sheet.");
      const candidate = structuredClone(actor.value), pdf = candidate.data.pdf;
      for (const list of ["manualFields", "fieldActions", "calculatedFields", "fieldBindings"]) {
        if (bundle[list] !== void 0 && !Array.isArray(bundle[list])) throw new Error("Invalid PDF mapping definitions.");
        const incoming = (bundle[list] || []).map((row) => ({ ...structuredClone(row), source }));
        if (list === "manualFields") {
          const occupied = new Set((pdf.manualFields || []).filter((row) => row.source !== source).map((row) => row.id));
          if (incoming.some((row) => occupied.has(row.id))) throw new Error("This mapping's field identifiers are already used by another PDF.");
        }
        pdf[list] = [...(pdf[list] || []).filter((row) => row.source !== source), ...incoming];
      }
      candidate.data.token.bars = Object.fromEntries(BAR_SLOTS.map((slot) => [slot.key, bundle.bindings?.[slot.key] || ""]));
      if (bundle.document) pdf.sourceMetadata = [
        ...(pdf.sourceMetadata || []).filter((row) => row.source !== source),
        { ...structuredClone(bundle.document), source, fingerprint: bundle.document.fingerprint || "", pages: bundle.document.pages || [] }
      ];
      recalculateFields(candidate, currentSource.value, { previous: actor.value });
      if (props.tokenId) candidate.data.token.name = candidate.name;
      saving = true;
      const result = await options.save(candidate);
      if (!disposed) {
        actor.value.data = candidate.data;
        actor.value.version = result.version;
        actor.value.sheetVersion = result.sheetVersion;
        undoLayouts.length = redoLayouts.length = 0;
        saveError.value = "";
        updatePositions();
      }
      return true;
    } catch (failure) {
      if (!disposed && failure.code === "conflict") saveError.value = "This sheet was changed in another window. Your changes remain here. Copy anything you want to preserve before reloading.";
      throw failure;
    } finally {
      saving = false;
      configuring.value = false;
      if (saveQueued && !disposed) scheduleSave();
    }
  }
  async function downloadFilled() {
    if (!actor.value || !viewerDoc || disposed || exporting.value) return false;
    exporting.value = true;
    exportAbort?.abort();
    exportAbort = new AbortController();
    const source = sourceKey(currentSource.value), doc = viewerDoc, signal = exportAbort.signal;
    try {
      await flush();
      recalculate();
      const [{ filledPdf }, lib] = await Promise.all([
        import("/static/gravewright_pdf_system/filled-pdf.js"),
        loadPdfjs(props.block.assets.url)
      ]);
      if (disposed || source !== sourceKey(currentSource.value)) return false;
      const snapshotFields = structuredClone(fields), snapshotIndex = new Map(fieldIndex);
      const values = Object.fromEntries(Object.keys(snapshotFields).map((name) => [name, fieldValue(name)]));
      const bytes = await filledPdf({
        doc,
        lib,
        fields: snapshotFields,
        fieldIndex: snapshotIndex,
        value: (name) => values[name],
        color: actor.value.data.pdf.textColor,
        document: pageHost.value.ownerDocument,
        signal,
        onProgress: (page, total) => {
          statusText.value = text("Preparing PDF page {0} of {1}\u2026", page, total);
        }
      });
      signal.throwIfAborted();
      const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
      const link = pageHost.value.ownerDocument.createElement("a");
      link.href = url;
      link.download = `${actor.value.name || "sheet"}-filled.pdf`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1e3);
      statusText.value = text("Filled PDF downloaded.");
      return true;
    } catch (failure) {
      if (signal.aborted || disposed) return false;
      actionError.value = text(failure.message || "Could not export the filled PDF.");
      throw failure;
    } finally {
      exporting.value = false;
    }
  }
  async function load() {
    try {
      const [value, config, catalog] = await Promise.all([
        options.read(),
        props.block.assets.json("assets/pdf-fields.gw.json"),
        props.block.host.call("asset.list", {})
      ]);
      if (disposed)
        return;
      actor.value = { ...value, data: normalizePdfCharacterData(value.data) };
      mapping.value = config;
      campaignAssets.value = catalog.items;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
    await nextTick();
    await openSource();
  }
  async function uploadPdf(event) {
    const input = event.target;
    const file = input.files?.[0];
    input.value = "";
    if (!file || !isGm.value)
      return;
    try {
      const body = await props.block.host.call("asset.upload", { file });
      if (disposed)
        return;
      campaignAssets.value = [...campaignAssets.value, body];
      await chooseSource("asset", body.id);
    } catch (cause) {
      saveError.value = text(cause.message || "Could not upload the PDF.");
    }
  }
  function leaving(event) {
    if (saving || saveQueued || saveError.value) {
      event.preventDefault();
    }
  }
  function noteDocument(value) {
    return typeof value === "object" ? value : void 0;
  }
  function setNote(key, value) {
    if (actor.value && canEditNow.value) {
      actor.value.data[key] = value;
      scheduleSave();
    }
  }
  async function uploadImage(kind, event) {
    const input = event.target, file = input.files?.[0];
    input.value = "";
    if (!file || !actor.value || !canEditNow.value)
      return;
    try {
      if (props.tokenId) {
        saveError.value = text("Change the image through the original actor\u2019s sheet.");
        return;
      }
      const result = await props.block.host.call("actor.image.upload", {
        id: props.actorId,
        kind,
        file
      });
      if (!disposed && actor.value)
        actor.value[kind === "token" ? "tokenUrl" : "portraitUrl"] = result.url;
    } catch {
      if (!disposed)
        saveError.value = text("Could not upload the image.");
    }
  }
  pageHost.value = host;
  window.addEventListener("beforeunload", leaving);
  void load();
  return {
    get view() {
      return {
        actor: actor.value,
        loading: loading.value,
        error: error.value,
        saveError: saveError.value,
        actionError: actionError.value,
        fields,
        positions,
        pageLabel: pageLabel.value,
        statusText: statusText.value,
        viewerMissing: viewerMissing.value,
        currentSource: currentSource.value,
        openFieldNames: openFieldNames.value,
        pickerOpen: pickerOpen.value,
        mapping: mapping.value,
        campaignAssets: campaignAssets.value,
        canEdit: canEditNow.value,
        pages: viewerDoc?.numPages ?? 0,
        fieldIndex,
        mappingEditing: mappingEditing.value,
        canMap: canMap(),
        canConfigureFieldActions: canConfigureFieldActions(),
        fieldActions: actor.value ? actionsForSource(actor.value.data.pdf, currentSource.value) : /* @__PURE__ */ Object.create(null),
        rolling: rolling.value,
        exporting: exporting.value,
        sourceDocument,
        calculationErrors,
        referenceFields: actor.value ? Object.values(bindingsForSource(actor.value.data.pdf, currentSource.value)) : [],
        calculatedFields: Object.fromEntries((actor.value?.data.pdf.calculatedFields || []).filter((row) => row.source === sourceKey(currentSource.value)).map((row) => [row.field, row.formula])),
        canUndoManualLayout: !!undoLayouts.length,
        canRedoManualLayout: !!redoLayouts.length,
        manualFields: actor.value ? manualFieldsForSource(actor.value.data.pdf, currentSource.value) : [],
        nativeFieldCount: nativeFieldNames.length,
        pageFrames,
        saving,
        pending: saveQueued
      };
    },
    value: fieldValue,
    call(name, ...args) {
      const methods = {
        flush,
        async refreshActor() {
          const previousLayout = actor.value && currentSource.value ? JSON.stringify(captureLayout(actor.value, currentSource.value)) : "";
          const value = await options.read();
          if (!disposed) {
            actor.value = { ...value, data: normalizePdfCharacterData(value.data) };
            const source = resolveSource();
            if (source?.kind !== currentSource.value?.kind || source?.id !== currentSource.value?.id) await openSource();
            else {
              if (previousLayout !== JSON.stringify(captureLayout(actor.value, currentSource.value))) undoLayouts.length = redoLayouts.length = 0;
              updatePositions();
            }
          }
        },
        toggleMapping() {
          if (canMap()) mappingEditing.value = !mappingEditing.value;
        },
        addManualField,
        updateManualField,
        removeManualField,
        editManualFields,
        copyManualFields: (ids) => copyLayout(actor.value, currentSource.value, ids, fields),
        pasteManualFields,
        undoManualLayout: () => moveLayoutHistory(undoLayouts, redoLayouts),
        redoManualLayout: () => moveLayoutHistory(redoLayouts, undoLayouts),
        configureFieldAction,
        rollField,
        exportMappingBundle,
        applyMappingBundle,
        save,
        prevPage,
        nextPage,
        zoomBy,
        fitPage,
        toggleSpread,
        download,
        downloadFilled,
        async showField(name2) {
          const info = fieldIndex.get(name2);
          if (!info || !actor.value) return false;
          actor.value.data.pdf.page = info.page;
          await render();
          return true;
        },
        chooseSource,
        onFieldInput,
        onBarChoice,
        uploadPdf,
        uploadImage,
        setNote,
        scheduleSave,
        togglePicker: () => pickerOpen.value = !pickerOpen.value
      };
      const result = methods[name](...args);
      options.repaint();
      if (result?.finally)
        result.then(options.repaint, options.repaint);
      return result;
    },
    destroy() {
      disposed = true;
      ++sourceGeneration;
      ++renderGeneration;
      sourceAbort.abort();
      exportAbort?.abort();
      window.removeEventListener("beforeunload", leaving);
      clearTimeout(saveTimer);
      if (saveQueued)
        void save();
      saveQueued = false;
      releasePdf();
    }
  };
}
export {
  alignLayoutFields,
  distributeLayoutFields,
  fieldBounds,
  fieldReference,
  layoutBounds,
  mappingDiagnostics,
  moveLayoutFields,
  pdfController,
  rasterPdf,
  snapLayoutRect
};
