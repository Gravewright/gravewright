import { ModuleError } from './lifetime.js';

// Translator's host adapter. Catalogs belong to the registering module and
// disappear with its lifetime; modules cannot replace the host or another module.
const catalogs = new Map();
const placeholder = /\{([A-Za-z_][A-Za-z0-9_.]*|\d+)\}/g;
const localePattern = /^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/;
let initialText, initialLanguage = { id: 'en', messages: {} };
function language() {
  const config = typeof document !== 'undefined' && document.getElementById('gravewright-language');
  if (config && config.textContent !== initialText) {
    initialText = config.textContent;
    initialLanguage = JSON.parse(initialText);
  }
  const current = typeof window !== 'undefined' && window.gravewrightLocale;
  return current ? { id: current.id, messages: current.messages?.text ?? current.messages ?? {} } : initialLanguage;
}
function format(value, params) {
  return value.replace(placeholder, (match, key) => params && Object.hasOwn(params, key) ? String(params[key]) : match);
}
function names(value) { return [...value.matchAll(placeholder)].map(m => m[1]).sort().join('|'); }
function catalogChanged(namespace) {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('gravewright:i18n-catalog', {detail:{namespace}}));
}

export function createTranslator(namespace = 'gravewright', life) {
  const check = () => life?.check();
  const own = () => [...catalogs.get(namespace)?.values() ?? []];
  function lookup(key) {
    const { id, messages } = language();
    const available = own().reverse();
    for (const locale of [...new Set([id, id.split('-')[0], 'en'])]) {
      for (const catalog of available) if (Object.hasOwn(catalog[locale] ?? {}, key)) return catalog[locale][key];
    }
    if (namespace === 'gravewright') {
      if (Object.hasOwn(messages, key)) return messages[key];
      if (Object.hasOwn(messages, key.trim())) return key.replace(key.trim(), () => messages[key.trim()]);
    }
    return undefined;
  }
  return Object.freeze({
    get locale() { check(); return language().id; },
    t(key, params = {}) {
      check();
      if (typeof key !== 'string') throw new ModuleError('invalid_data');
      return format(lookup(key) ?? key, params);
    },
    has(key) { check(); return lookup(key) !== undefined; },
    number(value, options = {}) { check(); return new Intl.NumberFormat(language().id, options).format(value); },
    register(value) {
      check();
      if (!value || typeof value !== 'object' || Array.isArray(value) || !value.en) throw new ModuleError('invalid_data');
      const copy = Object.create(null);
      let count = 0;
      for (const [locale, messages] of Object.entries(value)) {
        if (!localePattern.test(locale) || !messages || typeof messages !== 'object' || Array.isArray(messages)) throw new ModuleError('invalid_data');
        copy[locale] = Object.create(null);
        for (const [key, text] of Object.entries(messages)) {
          if (++count > 15000 || !key.trim() || key.length > 12000 || typeof text !== 'string' || !text.trim() || text.length > 12000
              || typeof value.en[key] !== 'string' || names(text) !== names(value.en[key])) throw new ModuleError('invalid_data');
          copy[locale][key] = text;
        }
      }
      const token = {};
      if (!catalogs.has(namespace)) catalogs.set(namespace, new Map());
      catalogs.get(namespace).set(token, copy);
      catalogChanged(namespace);
      const dispose = () => {
        if (!catalogs.get(namespace)?.delete(token)) return;
        if (!catalogs.get(namespace)?.size) catalogs.delete(namespace);
        catalogChanged(namespace);
      };
      life?.onDispose(dispose);
      return dispose;
    },
    onChange(handler) {
      check();
      if (typeof handler !== 'function') throw new ModuleError('invalid_data');
      const callback = () => { if (!life?.signal.aborted) handler(language().id); };
      const catalogCallback = event => { if (event.detail?.namespace === namespace) callback(); };
      window.addEventListener('gravewright:locale', callback);
      window.addEventListener('gravewright:i18n-catalog', catalogCallback);
      const dispose = () => {
        window.removeEventListener('gravewright:locale', callback);
        window.removeEventListener('gravewright:i18n-catalog', catalogCallback);
      };
      life?.onDispose(dispose);
      return dispose;
    },
  });
}
