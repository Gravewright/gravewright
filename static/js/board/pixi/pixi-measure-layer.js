(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    function screenPoint(point, camera) {
        return {
            x: point.worldX * camera.zoom + camera.offsetX,
            y: point.worldY * camera.zoom + camera.offsetY,
        };
    }

    function rotate(point, pivot, degrees) {
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

    function rgba(value, fallback, colorParser) {
        const raw = String(value || "").trim();
        if (!raw || raw === "none" || raw === "transparent") return { color: fallback, alpha: 0 };
        const match = /^rgba?\(([^)]+)\)$/i.exec(raw);
        if (match) {
            const [r, g, b, a = 1] = match[1].split(",").map((part) => Number(part.trim()));
            return {
                color: ((Math.max(0, Math.min(255, r)) << 16)
                    | (Math.max(0, Math.min(255, g)) << 8)
                    | Math.max(0, Math.min(255, b))),
                alpha: Math.max(0, Math.min(1, Number.isFinite(a) ? a : 1)),
            };
        }
        return { color: colorParser(raw), alpha: 1 };
    }

    function measureStyle(renderer, item) {
        const style = item.style || {};
        const stroke = rgba(style.stroke || "#f2c679", 0xf2c679, (value) => renderer._color(value));
        const fill = rgba(style.fill || "rgba(192,154,90,0.16)", stroke.color, (value) => renderer._color(value));
        const layerAlpha = (item.gmLayer ? 0.5 : 1) * (item.preview ? 0.9 : 1);
        return {
            stroke: { color: stroke.color, alpha: stroke.alpha * layerAlpha, width: Number(style.strokeWidth) || 2 },
            fill: { color: fill.color, alpha: fill.alpha * layerAlpha },
        };
    }

    function dashedLine(gfx, from, to, stroke, dash = 6, gap = 5) {
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const length = Math.hypot(dx, dy);
        if (!length) return;
        const ux = dx / length;
        const uy = dy / length;
        for (let cursor = 0; cursor < length; cursor += dash + gap) {
            const end = Math.min(length, cursor + dash);
            gfx.moveTo(from.x + ux * cursor, from.y + uy * cursor)
                .lineTo(from.x + ux * end, from.y + uy * end)
                .stroke(stroke);
        }
    }

    function labelNode(board, index) {
        let node = board.measureLabels[index];
        if (node) return node;
        node = {
            container: new PIXI.Container(),
            background: new PIXI.Graphics(),
            text: new PIXI.Text({
                text: "",
                style: {
                    fontFamily: "sans-serif",
                    fontSize: 12,
                    fontWeight: "700",
                    fill: 0xf4efe4,
                    align: "center",
                    lineHeight: 15,
                    stroke: { color: 0x000000, width: 3, alpha: 0.72 },
                },
            }),
        };
        node.text.anchor.set(0.5);
        node.text.resolution = window.devicePixelRatio || 1;
        node.text.roundPixels = true;
        node.container.addChild(node.background, node.text);
        board.measureLabelLayer.addChild(node.container);
        board.measureLabels.push(node);
        return node;
    }

    function drawLabel(board, index, x, y, content, variant = "measure", options = {}) {
        const node = labelNode(board, index);
        node.container.visible = true;
        node.container.position.set(Math.round(x), Math.round(y));
        node.text.text = String(content || "");
        node.text.style.fontSize = options.fontSize || (variant === "marker" ? 13 : 12);
        node.text.style.fontWeight = variant === "marker" ? "800" : "700";
        node.text.style.fill = options.color ? new PIXI.Color(options.color).toNumber() : 0xf4efe4;
        node.background.clear();
        if (variant === "plain") return node;
        const paddingX = variant === "marker" ? 11 : 7;
        const paddingY = variant === "marker" ? 7 : 5;
        const width = Math.max(variant === "marker" ? 90 : 44, node.text.width + paddingX * 2);
        const height = Math.max(22, node.text.height + paddingY * 2);
        if (variant === "marker") {
            node.background.roundRect(-width / 2, -height / 2, width, height, 6)
                .fill({ color: 0x0f766e, alpha: 0.94 })
                .stroke({ color: 0x99f6e4, alpha: 0.86, width: 1 });
        } else {
            node.background.roundRect(-width / 2, -height / 2, width, height, 5)
                .fill({ color: 0x080a0b, alpha: 0.9 })
                .stroke({ color: 0xf2c679, alpha: 0.36, width: 1 });
        }
        return node;
    }

    Object.assign(proto, {
        _renderMeasurements(board) {
            const gfx = board.measureGfx;
            if (!gfx || !board.measureLabelLayer) return;
            gfx.clear();
            let labelIndex = 0;
            const camera = this.camera;
            const scene = this.scene;
            const items = board.measureSnapshot?.items || [];

            items.forEach((item) => {
                const style = measureStyle(this, item);
                if (item.kind === "freehand") {
                    const points = (item.points || []).map((point) => screenPoint(point, camera));
                    if (points.length >= 2) {
                        gfx.moveTo(points[0].x, points[0].y);
                        points.slice(1).forEach((point) => gfx.lineTo(point.x, point.y));
                        gfx.stroke(style.stroke);
                    }
                    return;
                }
                if (item.kind === "text") {
                    const pos = screenPoint(item.position, camera);
                    drawLabel(board, labelIndex++, pos.x, pos.y, item.text, "plain", {
                        color: item.style?.fill || "#f8fafc",
                        fontSize: Math.max(6, (item.fontSize || 28) * camera.zoom),
                    });
                    return;
                }

                const start = screenPoint(item.start, camera);
                const rotatedEndWorld = rotate(item.end, item.start, Number(item.rotation) || 0);
                const end = screenPoint(rotatedEndWorld, camera);
                const cells = item.cells || [];
                if (item.shape === "line" || item.shape === "square") {
                    cells.forEach((cell) => {
                        const topLeft = screenPoint(cell, camera);
                        const size = cell.size * camera.zoom;
                        gfx.rect(topLeft.x, topLeft.y, size, size).fill(style.fill).stroke(style.stroke);
                    });
                }

                if (item.shape === "circle") {
                    const radius = Math.hypot(end.x - start.x, end.y - start.y);
                    gfx.circle(start.x, start.y, radius).fill(style.fill).stroke(style.stroke);
                    dashedLine(gfx, start, end, { ...style.stroke, width: Math.max(1, style.stroke.width * 0.8) });
                } else if (item.shape === "square") {
                    const corners = [
                        { worldX: Math.min(item.start.worldX, item.end.worldX) - (scene?.scaledTileSize || 70) / 2, worldY: Math.min(item.start.worldY, item.end.worldY) - (scene?.scaledTileSize || 70) / 2 },
                        { worldX: Math.max(item.start.worldX, item.end.worldX) + (scene?.scaledTileSize || 70) / 2, worldY: Math.min(item.start.worldY, item.end.worldY) - (scene?.scaledTileSize || 70) / 2 },
                        { worldX: Math.max(item.start.worldX, item.end.worldX) + (scene?.scaledTileSize || 70) / 2, worldY: Math.max(item.start.worldY, item.end.worldY) + (scene?.scaledTileSize || 70) / 2 },
                        { worldX: Math.min(item.start.worldX, item.end.worldX) - (scene?.scaledTileSize || 70) / 2, worldY: Math.max(item.start.worldY, item.end.worldY) + (scene?.scaledTileSize || 70) / 2 },
                    ].map((point) => screenPoint(rotate(point, item.start, Number(item.rotation) || 0), camera));
                    gfx.poly(corners.flatMap((point) => [point.x, point.y])).stroke(style.stroke);
                } else if (item.shape === "cone") {
                    const angle = Math.atan2(end.y - start.y, end.x - start.x);
                    const radius = Math.hypot(end.x - start.x, end.y - start.y);
                    const points = [start];
                    for (let step = 0; step <= 24; step += 1) {
                        const theta = angle - Math.PI / 6 + (Math.PI / 3) * (step / 24);
                        points.push({ x: start.x + Math.cos(theta) * radius, y: start.y + Math.sin(theta) * radius });
                    }
                    gfx.poly(points.flatMap((point) => [point.x, point.y])).fill(style.fill).stroke(style.stroke);
                    dashedLine(gfx, start, end, { ...style.stroke, width: Math.max(1, style.stroke.width * 0.8) });
                }

                let labelX = (start.x + end.x) / 2;
                let labelY = (start.y + end.y) / 2 - 14;
                if (item.shape === "circle" || item.shape === "cone") {
                    labelX = end.x;
                    labelY = end.y - 16;
                }
                drawLabel(board, labelIndex++, labelX, labelY, item.label, "measure");
                if (item.markerText) {
                    const anchor = screenPoint(item.markerTextAnchor, camera);
                    drawLabel(board, labelIndex++, anchor.x, anchor.y, item.markerText, "marker");
                }
            });

            for (let index = labelIndex; index < board.measureLabels.length; index += 1) {
                board.measureLabels[index].container.visible = false;
            }
            board.measureLayer.visible = items.length > 0;
        },
    });
})();
