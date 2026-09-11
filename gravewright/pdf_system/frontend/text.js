/** English labels retained from the original PDF module. */
export function text(value, ...args) { return value.replace(/\{(\d+)\}/g, (_, i) => String(args[Number(i)] ?? '')); }
