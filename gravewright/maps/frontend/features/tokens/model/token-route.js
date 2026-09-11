import { distancePerCell } from './token-vision.js';
/** Measure the displayed anchor's actual path, including diagonals and return trips. */
export function routeMeasurements(route, measureValue) {
    const scale = distancePerCell(measureValue);
    const segments = route.slice(1).map((step, index) => {
        const from = route[index][0], to = step[0];
        return {
            distance: Math.hypot(to.gridX - from.gridX, to.gridY - from.gridY) * scale,
            x: (from.gridX + from.cells / 2 + to.gridX + to.cells / 2) / 2,
            y: (from.gridY + (from.heightCells ?? from.cells) / 2 + to.gridY + (to.heightCells ?? to.cells) / 2) / 2,
        };
    });
    return { segments, total: segments.reduce((sum, segment) => sum + segment.distance, 0) };
}
export const ROUTE_CELLS_PER_SECOND = 4;
export const MAX_ROUTE_POINTS = 64;
export function routeLengths(route) {
    return route.slice(1).map((step, index) => Math.max(0, ...step.map((token, i) => {
        const previous = route[index][i];
        return Math.hypot(token.gridX - previous.gridX, token.gridY - previous.gridY);
    })));
}
/** Constant spatial speed with exact corners, rather than a straight tween to the last click. */
export function routePosition(route, lengths, distance) {
    let segment = 0, remaining = Math.max(0, distance);
    while (segment < lengths.length && remaining >= lengths[segment]) {
        remaining -= lengths[segment];
        segment++;
    }
    if (segment >= lengths.length)
        return { tokens: route.at(-1) ?? [], passed: lengths.length, done: true };
    const from = route[segment], to = route[segment + 1], t = lengths[segment] > 0 ? remaining / lengths[segment] : 1;
    return { tokens: to.map((token, i) => ({ ...token, gridX: from[i].gridX + (token.gridX - from[i].gridX) * t, gridY: from[i].gridY + (token.gridY - from[i].gridY) * t })), passed: segment, done: false };
}
