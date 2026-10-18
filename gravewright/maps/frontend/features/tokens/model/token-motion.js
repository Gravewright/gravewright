export const TOKEN_SETTLE_MS = 120;
/** A teleport replaces this placement rather than moving it through intervening cells. */
export function tokenTeleported(from, to) {
    return (from.teleportVersion ?? 0) !== (to.teleportVersion ?? 0);
}
/** Deceleration without overshoot; new network targets start at the displayed position. */
export function interpolateTokens(from, to, progress) {
    const starts = new Map(from.map(token => [token.id, token]));
    const t = 1 - Math.pow(1 - Math.max(0, Math.min(1, progress)), 3);
    return to.map(token => {
        const start = starts.get(token.id);
        if (!start || t === 1 || tokenTeleported(start, token))
            return token;
        return { ...token, gridX: start.gridX + (token.gridX - start.gridX) * t, gridY: start.gridY + (token.gridY - start.gridY) * t };
    });
}
