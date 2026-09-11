/** English source text works independently of Vue, the DOM, and optional language packs. */
const listeners = new Set();
export function onTextChange(listener) { listeners.add(listener); return () => { listeners.delete(listener); }; }
export function notifyTextChange() { for (const listener of listeners)
    listener(); }
let currentLocale = () => 'en';
const formats = new Map();
export function formatNumber(value) { const locale = currentLocale(); let format = formats.get(locale); if (!format) {
    format = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
    formats.set(locale, format);
} return format.format(value); }
let resolve = source => source;
export function registerTextResolver(resolver, locale = () => 'en') {
    resolve = resolver;
    currentLocale = locale;
    notifyTextChange();
    return () => { if (resolve === resolver) {
        resolve = source => source;
        currentLocale = () => 'en';
        notifyTextChange();
    } };
}
export function text(source, ...values) {
    return resolve(source).replace(/\{(\d+)\}/g, (match, index) => Number(index) < values.length ? String(values[Number(index)]) : match);
}

if (typeof window !== 'undefined') {
    const apply = detail => registerTextResolver(source => {
        const translated = detail.messages?.text?.[source];
        return typeof translated === 'string' ? translated : source;
    }, () => detail.id || 'en');
    window.addEventListener('gravewright:locale', event => apply(event.detail));
    if (window.gravewrightLocale) apply(window.gravewrightLocale);
}
