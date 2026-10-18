/** Optional authored barriers use the tabletop's native defaults and units. */
export const wallPropertyFields = Object.freeze(['presentation', 'behavior', 'vertical', 'discovered']);

export function wallProperties(wall) {
    return {
        presentation: wall.presentation ?? 'normal',
        behavior: Object.fromEntries(['movement', 'vision', 'light', 'sound'].map(key => [key, wall.behavior?.[key] ?? 'block'])),
        vertical: { bottom: wall.vertical?.bottom ?? null, top: wall.vertical?.top ?? null },
        discovered: wall.discovered ?? false,
    };
}

export function copyWallProperties(wall) {
    return Object.fromEntries(wallPropertyFields.filter(key => Object.hasOwn(wall, key)).map(key => [key, structuredClone(wall[key])]));
}

export function wallPropertiesKey(wall) { return JSON.stringify(wallProperties(wall)); }

export function nativeWallProperties(wall) {
    const { presentation, behavior, vertical, discovered } = wallProperties(wall);
    return {
        presentation, discovered,
        ...Object.fromEntries(Object.entries(behavior).map(([key, value]) => [key + '_behavior', value])),
        vertical_bottom: vertical.bottom, vertical_top: vertical.top,
        blocks_light: Number(behavior.light === 'block'), blocks_sight: Number(behavior.vision === 'block'),
    };
}
