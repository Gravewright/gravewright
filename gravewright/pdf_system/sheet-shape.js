/**
 * What a PDF character sheet is made of. This lived in the core's actor domain, which meant every
 * ruleset inherited PDF's fields; it belongs here, with the module that gives the data meaning.
 */
export function pdfCharacterDefaults() {
    return {
        pdf: { template: "generic", page: 1, zoom: 1, spread: false, asset: "", textColor: "#111111" },
        fields: {}, ac: 0, init: 0, bio: "", history: "", notes: "",
        token: { size: 1, bars: { bar1Value: "", bar1Max: "", bar2Value: "", bar2Max: "", initiative: "", defense: "" }, display: { name: true, bar_1: true, bar_2: true } },
        bars: { bar_1: { value: 0, max: 0 }, bar_2: { value: 0, max: 0 } },
    };
}
/** Fills in whatever a stored sheet is missing, without discarding anything it already carries. */
export function normalizePdfCharacterData(value) {
    const defaults = pdfCharacterDefaults();
    const merge = (base, source) => Object.fromEntries(Object.entries(base).map(([key, fallback]) => {
        const incoming = source[key];
        return [key, fallback && typeof fallback === "object" && !Array.isArray(fallback) && incoming && typeof incoming === "object" && !Array.isArray(incoming) ? merge(fallback, incoming) : incoming ?? fallback];
    }).concat(Object.entries(source).filter(([key]) => !(key in base))));
    return merge(defaults, value);
}
