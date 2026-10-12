/** Resolve labels before interpolating document values. */
export function text(value, ...args) {
    const i18n = typeof window !== 'undefined' && window.gravewright?.i18n;
    return i18n ? i18n.t(value, args) : value.replace(/\{(\d+)\}/g, (match, i) => args[Number(i)] === undefined ? match : String(args[Number(i)]));
}
