(function (global) {
    "use strict";

    const SUPPORTED_FACES = Object.freeze(new Set([4, 6, 8, 10, 12, 20, 100]));
    const FALLBACK_COLOR = "#6d7280";
    const MAX_DICE = 50;

    function normalizeColor(value) {
        const color = String(value || "").trim().toLowerCase();
        return /^#[0-9a-f]{6}$/.test(color) ? color : FALLBACK_COLOR;
    }

    function rgb(color) {
        const value = normalizeColor(color).slice(1);
        return [0, 2, 4].map(index => parseInt(value.slice(index, index + 2), 16));
    }

    function relativeLuminance(color) {
        const channels = rgb(color).map(value => {
            const channel = value / 255;
            return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    }

    function contrastRatio(first, second) {
        const light = Math.max(relativeLuminance(first), relativeLuminance(second));
        const dark = Math.min(relativeLuminance(first), relativeLuminance(second));
        return (light + 0.05) / (dark + 0.05);
    }

    function rgbToHsl(color) {
        const [red, green, blue] = rgb(color).map(value => value / 255);
        const max = Math.max(red, green, blue);
        const min = Math.min(red, green, blue);
        const lightness = (max + min) / 2;
        const delta = max - min;
        if (!delta) return [0, 0, lightness];
        const saturation = delta / (1 - Math.abs(2 * lightness - 1));
        const hue = max === red ? 60 * (((green - blue) / delta) % 6)
            : max === green ? 60 * (((blue - red) / delta) + 2)
                : 60 * (((red - green) / delta) + 4);
        return [(hue + 360) % 360, saturation, lightness];
    }

    function hslToHex(hue, saturation, lightness) {
        const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
        const x = chroma * (1 - Math.abs(((hue / 60) % 2) - 1));
        const match = lightness - chroma / 2;
        const [red, green, blue] = hue < 60 ? [chroma, x, 0] : hue < 120 ? [x, chroma, 0]
            : hue < 180 ? [0, chroma, x] : hue < 240 ? [0, x, chroma]
                : hue < 300 ? [x, 0, chroma] : [chroma, 0, x];
        return `#${[red, green, blue].map(value => Math.round((value + match) * 255).toString(16).padStart(2, "0")).join("")}`;
    }

    function numeralColor(baseColor) {
        const base = normalizeColor(baseColor);
        const [hue, saturation] = rgbToHsl(base);
        const complementaryHue = (hue + 180) % 360;
        const candidates = [
            hslToHex(complementaryHue, Math.max(0.45, saturation), 0.92),
            hslToHex(complementaryHue, Math.max(0.5, saturation), 0.12),
            "#ffffff",
            "#000000",
        ];
        return candidates.reduce((best, candidate) => contrastRatio(base, candidate) > contrastRatio(base, best) ? candidate : best);
    }

    function visualDice(groups) {
        const dice = [];
        for (const group of Array.isArray(groups) ? groups : []) {
            const faces = Number(group && group.faces);
            if (!SUPPORTED_FACES.has(faces) || !Array.isArray(group.results)) continue;
            for (const raw of group.results) {
                const result = Number(raw);
                if (!Number.isInteger(result) || result < 1 || result > faces) continue;
                if (faces === 100) {
                    const percentile = result === 100 ? 0 : result;
                    dice.push({faces: 10, result: Math.floor(percentile / 10) * 10, percentile: "tens"});
                    dice.push({faces: 10, result: percentile % 10, percentile: "ones"});
                } else {
                    dice.push({faces, result, percentile: null});
                }
                if (dice.length >= MAX_DICE) return dice;
            }
        }
        return dice;
    }

    function finalOrientation(faces, result) {
        const safeFaces = Number(faces) || 6;
        const safeResult = Number(result) || 1;
        const phase = ((safeResult - 1) / safeFaces) * Math.PI * 2;
        return Object.freeze({x: -0.52, y: phase, z: phase * 0.37});
    }

    const api = Object.freeze({
        SUPPORTED_FACES, FALLBACK_COLOR, MAX_DICE, normalizeColor, relativeLuminance,
        contrastRatio, numeralColor, visualDice, finalOrientation,
    });
    global.Gravewright3DDiceCore = api;
    if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
