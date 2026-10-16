import { createVisibilityContext } from './visibility-polygon.js';
import { visionPolygons } from './visibility-jobs.js';

let walls = [], context;
self.onmessage = ({ data }) => {
    if (data.type === 'walls') {
        walls = data.walls;
        context = createVisibilityContext(walls);
    } else if (data.type === 'vision') {
        try {
            const polygons = visionPolygons(data.sources, data.radius, walls, context);
            self.postMessage({ id: data.id, polygons }, polygons.map(points => points.buffer));
        } catch {
            self.postMessage({ id: data.id, error: true });
        }
    }
};
