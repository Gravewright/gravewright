/** Exact authored cell-space extent; containing grid cells retain integer indexes. */
export function documentBounds(document) {
    const geometry = document.sceneGeometry, cell = document.cellSize;
    if (document.schemaVersion === 3 && geometry && Number.isFinite(cell) && cell > 0
        && ['width', 'height'].every(key => Number.isInteger(geometry[key]) && geometry[key] > 0)
        && Math.ceil(geometry.width / cell) === document.columns && Math.ceil(geometry.height / cell) === document.rows)
        return { width: geometry.width / cell, height: geometry.height / cell };
    return { width: document.columns, height: document.rows };
}
