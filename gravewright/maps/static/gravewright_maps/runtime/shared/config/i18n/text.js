// shared/config/i18n/text.js
var listeners = /* @__PURE__ */ new Set();
function onTextChange(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
function notifyTextChange() {
  for (const listener of listeners)
    listener();
}
var currentLocale = () => "en";
var formats = /* @__PURE__ */ new Map();
function formatNumber(value) {
  const locale = currentLocale();
  let format = formats.get(locale);
  if (!format) {
    format = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
    formats.set(locale, format);
  }
  return format.format(value);
}
var resolve = (source) => source;
function registerTextResolver(resolver, locale = () => "en") {
  resolve = resolver;
  currentLocale = locale;
  notifyTextChange();
  return () => {
    if (resolve === resolver) {
      resolve = (source) => source;
      currentLocale = () => "en";
      notifyTextChange();
    }
  };
}
function text(source, ...values) {
  return resolve(source).replace(/\{(\d+)\}/g, (match, index) => Number(index) < values.length ? String(values[Number(index)]) : match);
}
if (typeof window !== "undefined") {
  const apply = (detail) => registerTextResolver((source) => {
    const messages = detail.messages?.text ?? detail.messages ?? {};
    if (typeof messages[source] === "string") return messages[source];
    const translated = messages[source.trim()];
    return typeof translated === "string" ? source.replace(source.trim(), () => translated) : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
  else {
    const config = document.getElementById("gravewright-language");
    if (config) apply(JSON.parse(config.textContent));
  }
}
export {
  formatNumber,
  notifyTextChange,
  onTextChange,
  registerTextResolver,
  text
};
