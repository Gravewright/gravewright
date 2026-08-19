(() => {
    function createMeasureGeometry(deps) {
        const {
            defaultGridSize,
            sceneDataFor,
            stateFor,
            screenFromWorld,
            screenToWorldXY,
            measureStoreFor,
        } = deps;

        function worldToScreenXY(point, state) {
            return {
                x: screenFromWorld(point.worldX, state.offsetX, state.zoom),
                y: screenFromWorld(point.worldY, state.offsetY, state.zoom),
            };
        }

        function worldPathFor(points, state) {
            if (!Array.isArray(points) || !points.length) return "";
            return points.map((point, index) => {
                const screen = worldToScreenXY(point, state);
                return `${index === 0 ? "M" : "L"} ${screen.x} ${screen.y}`;
            }).join(" ");
        }

        function clampMeasureWorld(point, scene) {
            return {
                worldX: Math.max(0, Math.min(scene.width, point.worldX)),
                worldY: Math.max(0, Math.min(scene.height, point.worldY)),
            };
        }

        function snapWorldToCellCenter(point, scene) {
            const s = scene.scaledTileSize || defaultGridSize;
            return clampMeasureWorld({
                worldX: (Math.floor(point.worldX / s) + 0.5) * s,
                worldY: (Math.floor(point.worldY / s) + 0.5) * s,
            }, scene);
        }

        function measurePointFromEvent(canvas, event) {
            const scene = sceneDataFor(canvas);
            if (!scene) return null;
            const state = stateFor(canvas);
            return snapWorldToCellCenter(
                screenToWorldXY(event.clientX, event.clientY, state),
                scene,
            );
        }

        function measureStartPointFromEvent(canvas, event) {
            return measurePointFromEvent(canvas, event);
        }

        function rawMeasurePointFromEvent(canvas, event) {
            const scene = sceneDataFor(canvas);
            if (!scene) return null;
            const state = stateFor(canvas);
            return clampMeasureWorld(
                screenToWorldXY(event.clientX, event.clientY, state),
                scene,
            );
        }

        function cellsBetween(a, b, scene) {
            const s = scene.scaledTileSize || defaultGridSize;
            const dx = (b.worldX - a.worldX) / s;
            const dy = (b.worldY - a.worldY) / s;
            return Math.sqrt(dx * dx + dy * dy);
        }

        function formatCells(value) {
            const rounded = Math.round(value * 10) / 10;
            return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)} cel`;
        }

        function measureLabelFor(measure, scene) {
            const s = scene.scaledTileSize || defaultGridSize;
            if (measure.shape === "square") {
                const cols = Math.abs(
                    Math.floor(measure.end.worldX / s) - Math.floor(measure.start.worldX / s),
                ) + 1;
                const rows = Math.abs(
                    Math.floor(measure.end.worldY / s) - Math.floor(measure.start.worldY / s),
                ) + 1;
                return `${formatCells(cols)} x ${formatCells(rows)}`;
            }
            if (measure.shape === "line") {
                const cols = Math.abs(
                    Math.floor(measure.end.worldX / s) - Math.floor(measure.start.worldX / s),
                );
                const rows = Math.abs(
                    Math.floor(measure.end.worldY / s) - Math.floor(measure.start.worldY / s),
                );
                return formatCells(Math.max(cols, rows) + 1);
            }
            return formatCells(cellsBetween(measure.start, measure.end, scene));
        }

        function gridCellsForMeasure(measure, scene) {
            if (!measure?.start || !measure?.end || !scene) return [];
            const size = scene.scaledTileSize || defaultGridSize;
            const bounds = measureBounds(measure);
            const minCol = Math.max(0, Math.floor(bounds.minX / size) - 1);
            const maxCol = Math.min(Math.ceil(scene.width / size) - 1, Math.floor(bounds.maxX / size) + 1);
            const minRow = Math.max(0, Math.floor(bounds.minY / size) - 1);
            const maxRow = Math.min(Math.ceil(scene.height / size) - 1, Math.floor(bounds.maxY / size) + 1);
            const cells = [];
            const originCol = Math.floor(measure.start.worldX / size);
            const originRow = Math.floor(measure.start.worldY / size);
            for (let row = minRow; row <= maxRow; row += 1) {
                for (let col = minCol; col <= maxCol; col += 1) {
                    const center = {
                        worldX: (col + 0.5) * size,
                        worldY: (row + 0.5) * size,
                    };
                    const covered = measure.shape === "line"
                        ? measureContainsPoint(measure, center, size * 0.45)
                        : measureContainsPoint(measure, center, 0.0001);
                    if (covered || (col === originCol && row === originRow)) {
                        cells.push({ col, row, worldX: col * size, worldY: row * size, size });
                    }
                }
            }
            return cells;
        }

        function areaMarkerTextAnchor(measure) {
            if (measure.shape === "circle") return { ...measure.start };
            return {
                worldX: (measure.start.worldX + measure.end.worldX) / 2,
                worldY: (measure.start.worldY + measure.end.worldY) / 2,
            };
        }

        function normalizedRotation(measure) {
            const value = Number(measure?.rotation || 0);
            return Number.isFinite(value) ? value : 0;
        }

        function rotationPivot(measure) {
            return { ...measure.start };
        }

        function rotatePoint(point, pivot, degrees) {
            if (!degrees) return { ...point };
            const radians = degrees * Math.PI / 180;
            const cos = Math.cos(radians);
            const sin = Math.sin(radians);
            const dx = point.worldX - pivot.worldX;
            const dy = point.worldY - pivot.worldY;
            return {
                worldX: pivot.worldX + dx * cos - dy * sin,
                worldY: pivot.worldY + dx * sin + dy * cos,
            };
        }

        function unrotatePoint(point, measure) {
            return rotatePoint(point, rotationPivot(measure), -normalizedRotation(measure));
        }

        function distancePointToSegment(px, py, ax, ay, bx, by) {
            const dx = bx - ax;
            const dy = by - ay;
            const lenSq = dx * dx + dy * dy;
            if (lenSq === 0) return Math.sqrt((px - ax) ** 2 + (py - ay) ** 2);
            const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
            const x = ax + t * dx;
            const y = ay + t * dy;
            return Math.sqrt((px - x) ** 2 + (py - y) ** 2);
        }

        function isPointInCone(point, measure) {
            const dx = measure.end.worldX - measure.start.worldX;
            const dy = measure.end.worldY - measure.start.worldY;
            const radius = Math.sqrt(dx * dx + dy * dy);
            if (radius <= 0) return false;
            const px = point.worldX - measure.start.worldX;
            const py = point.worldY - measure.start.worldY;
            const dist = Math.sqrt(px * px + py * py);
            if (dist > radius) return false;
            const coneAngle = Math.atan2(dy, dx);
            const pointAngle = Math.atan2(py, px);
            const delta = Math.atan2(Math.sin(pointAngle - coneAngle), Math.cos(pointAngle - coneAngle));
            return Math.abs(delta) <= Math.PI / 6;
        }

        function measureKind(measure) {
            if (measure.kind === "freehand") return "freehand";
            if (measure.kind === "text") return "text";
            return "shape";
        }

        function textBounds(measure) {
            const pos = measure.position || { worldX: 0, worldY: 0 };
            const fontSize = measure.fontSize || 28;
            const width = Math.max(fontSize, (String(measure.text || "").length || 1) * fontSize * 0.6);
            const height = fontSize * 1.2;
            return {
                minX: pos.worldX,
                maxX: pos.worldX + width,
                minY: pos.worldY,
                maxY: pos.worldY + height,
            };
        }

        function measureContainsPoint(measure, point, toleranceWorld) {
            if (measure.kind === "freehand") {
                const points = measure.points || [];
                for (let i = 1; i < points.length; i += 1) {
                    if (distancePointToSegment(
                        point.worldX,
                        point.worldY,
                        points[i - 1].worldX,
                        points[i - 1].worldY,
                        points[i].worldX,
                        points[i].worldY,
                    ) <= toleranceWorld) return true;
                }
                return false;
            }

            if (measure.kind === "text") {
                const b = textBounds(measure);
                return point.worldX >= b.minX - toleranceWorld && point.worldX <= b.maxX + toleranceWorld
                    && point.worldY >= b.minY - toleranceWorld && point.worldY <= b.maxY + toleranceWorld;
            }

            const localPoint = unrotatePoint(point, measure);

            if (measure.shape === "line") {
                return distancePointToSegment(
                    localPoint.worldX,
                    localPoint.worldY,
                    measure.start.worldX,
                    measure.start.worldY,
                    measure.end.worldX,
                    measure.end.worldY,
                ) <= toleranceWorld;
            }

            if (measure.shape === "circle") {
                const radius = Math.sqrt((measure.end.worldX - measure.start.worldX) ** 2 + (measure.end.worldY - measure.start.worldY) ** 2);
                const dist = Math.sqrt((localPoint.worldX - measure.start.worldX) ** 2 + (localPoint.worldY - measure.start.worldY) ** 2);
                return dist <= radius + toleranceWorld;
            }

            if (measure.shape === "square") {
                const minX = Math.min(measure.start.worldX, measure.end.worldX) - toleranceWorld;
                const maxX = Math.max(measure.start.worldX, measure.end.worldX) + toleranceWorld;
                const minY = Math.min(measure.start.worldY, measure.end.worldY) - toleranceWorld;
                const maxY = Math.max(measure.start.worldY, measure.end.worldY) + toleranceWorld;
                return localPoint.worldX >= minX && localPoint.worldX <= maxX && localPoint.worldY >= minY && localPoint.worldY <= maxY;
            }

            if (measure.shape === "cone") return isPointInCone(localPoint, measure);
            return false;
        }

        function measureAtPoint(canvas, event, allowedKinds = null, predicate = null) {
            const scene = sceneDataFor(canvas);
            if (!scene) return null;
            const point = rawMeasurePointFromEvent(canvas, event);
            if (!point) return null;
            const toleranceWorld = 10 / stateFor(canvas).zoom;
            const store = measureStoreFor(canvas);
            for (let i = store.length - 1; i >= 0; i -= 1) {
                const measure = store[i];
                if (allowedKinds && !allowedKinds.has(measureKind(measure))) continue;
                if (predicate && !predicate(measure)) continue;
                if (measureContainsPoint(measure, point, toleranceWorld)) return measure;
            }
            return null;
        }

        function measureBounds(measure) {
            if (measure.kind === "freehand") {
                const xs = (measure.points || []).map((p) => p.worldX);
                const ys = (measure.points || []).map((p) => p.worldY);
                return {
                    minX: Math.min(...xs),
                    maxX: Math.max(...xs),
                    minY: Math.min(...ys),
                    maxY: Math.max(...ys),
                };
            }
            if (measure.kind === "text") {
                return {
                    minX: measure.position.worldX,
                    maxX: measure.position.worldX,
                    minY: measure.position.worldY,
                    maxY: measure.position.worldY,
                };
            }
            if (measure.shape === "circle") {
                const radius = Math.hypot(
                    measure.end.worldX - measure.start.worldX,
                    measure.end.worldY - measure.start.worldY,
                );
                return {
                    minX: measure.start.worldX - radius,
                    maxX: measure.start.worldX + radius,
                    minY: measure.start.worldY - radius,
                    maxY: measure.start.worldY + radius,
                };
            }
            if (measure.shape === "cone") {
                const radius = Math.hypot(
                    measure.end.worldX - measure.start.worldX,
                    measure.end.worldY - measure.start.worldY,
                );
                const direction = Math.atan2(
                    measure.end.worldY - measure.start.worldY,
                    measure.end.worldX - measure.start.worldX,
                ) + normalizedRotation(measure) * Math.PI / 180;
                const halfAngle = Math.PI / 6;
                const signedAngleDelta = (angle, reference) =>
                    Math.atan2(Math.sin(angle - reference), Math.cos(angle - reference));
                const angles = [direction - halfAngle, direction + halfAngle];
                [0, Math.PI / 2, Math.PI, Math.PI * 1.5].forEach((angle) => {
                    if (Math.abs(signedAngleDelta(angle, direction)) <= halfAngle) angles.push(angle);
                });
                const points = [measure.start, ...angles.map((angle) => ({
                    worldX: measure.start.worldX + Math.cos(angle) * radius,
                    worldY: measure.start.worldY + Math.sin(angle) * radius,
                }))];
                return {
                    minX: Math.min(...points.map((point) => point.worldX)),
                    maxX: Math.max(...points.map((point) => point.worldX)),
                    minY: Math.min(...points.map((point) => point.worldY)),
                    maxY: Math.max(...points.map((point) => point.worldY)),
                };
            }
            const minX = Math.min(measure.start.worldX, measure.end.worldX);
            const maxX = Math.max(measure.start.worldX, measure.end.worldX);
            const minY = Math.min(measure.start.worldY, measure.end.worldY);
            const maxY = Math.max(measure.start.worldY, measure.end.worldY);
            if (!normalizedRotation(measure)) return { minX, maxX, minY, maxY };
            const pivot = rotationPivot(measure);
            const points = [
                { worldX: minX, worldY: minY }, { worldX: maxX, worldY: minY },
                { worldX: maxX, worldY: maxY }, { worldX: minX, worldY: maxY },
            ].map((point) => rotatePoint(point, pivot, normalizedRotation(measure)));
            return {
                minX: Math.min(...points.map((point) => point.worldX)),
                maxX: Math.max(...points.map((point) => point.worldX)),
                minY: Math.min(...points.map((point) => point.worldY)),
                maxY: Math.max(...points.map((point) => point.worldY)),
            };
        }

        function clampMeasureDelta(measure, dx, dy, scene) {
            const b = measureBounds(measure);
            return {
                dx: Math.max(-b.minX, Math.min(scene.width - b.maxX, dx)),
                dy: Math.max(-b.minY, Math.min(scene.height - b.maxY, dy)),
            };
        }

        function translatedMeasure(measure, dx, dy) {
            if (measure.kind === "freehand") {
                return {
                    ...measure,
                    points: (measure.points || []).map((p) => ({
                        worldX: p.worldX + dx,
                        worldY: p.worldY + dy,
                    })),
                };
            }
            if (measure.kind === "text") {
                return {
                    ...measure,
                    position: {
                        worldX: measure.position.worldX + dx,
                        worldY: measure.position.worldY + dy,
                    },
                };
            }
            return {
                ...measure,
                start: {
                    worldX: measure.start.worldX + dx,
                    worldY: measure.start.worldY + dy,
                },
                end: {
                    worldX: measure.end.worldX + dx,
                    worldY: measure.end.worldY + dy,
                },
            };
        }

        return {
            areaMarkerTextAnchor,
            cellsBetween,
            clampMeasureDelta,
            clampMeasureWorld,
            distancePointToSegment,
            formatCells,
            gridCellsForMeasure,
            isPointInCone,
            measureAtPoint,
            measureBounds,
            measureContainsPoint,
            measureKind,
            measureLabelFor,
            measurePointFromEvent,
            measureStartPointFromEvent,
            normalizedRotation,
            rawMeasurePointFromEvent,
            rotatePoint,
            rotationPivot,
            snapWorldToCellCenter,
            textBounds,
            translatedMeasure,
            worldPathFor,
            worldToScreenXY,
        };
    }

    window.GravewrightMapMeasureGeometry = { createMeasureGeometry };
})();
