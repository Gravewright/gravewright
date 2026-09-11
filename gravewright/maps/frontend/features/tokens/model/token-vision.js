/** Persist cells for compatibility; display distances using the scene's scale. */
export function distancePerCell(value) {
    return Number.isFinite(value) && value > 0 ? value : 1;
}
export function selectedVision(tokens, selectedIds, cell, origin = { x: 0, y: 0 }) {
    return tokens.filter(token => selectedIds.includes(token.id) && token.visionEnabled !== false).map(token => ({
        x: origin.x + (token.gridX + token.cells / 2) * cell,
        y: origin.y + (token.gridY + (token.heightCells ?? token.cells) / 2) * cell,
        radius: (token.visionRange ?? 0) * cell,
        elevation: token.elevation ?? 0,
    }));
}
