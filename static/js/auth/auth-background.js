(() => {
    const canvas = document.getElementById("auth-background");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function hex(n) {
        return "#" + n.toString(16).padStart(6, "0");
    }

    const C = {
        background:  hex(0x090b0c),
        boardOuter:  hex(0x101416),
        boardInner:  hex(0x14191c),
        grid:        hex(0x20272b),
        wall:        hex(0x4a555d),
        wallStrong:  hex(0x66737d),
        tokenNeutral: hex(0x7f8a91),
        tokenPlayer: hex(0xb99a5d),
        tokenEnemy:  hex(0xb66150),
        tokenStroke: hex(0xe7e3db),
    };

    const EPSILON = 0.0001;
    const LIGHT_RADIUS = 300;

    const state = {
        width:   window.innerWidth,
        height:  window.innerHeight,
        mouseX:  window.innerWidth  * 0.5,
        mouseY:  window.innerHeight * 0.5,
        smoothX: window.innerWidth  * 0.5,
        smoothY: window.innerHeight * 0.5,
    };

    const roomRects = [];

    const TOKEN_DEFS = [
        { x: 150,  y: 520, color: "tokenPlayer"  },
        { x: 240,  y: 430, color: "tokenNeutral" },
        { x: 390,  y: 370, color: "tokenEnemy"   },
        { x: 520,  y: 500, color: "tokenNeutral" },
        { x: 710,  y: 280, color: "tokenPlayer"  },
        { x: 880,  y: 520, color: "tokenEnemy"   },
        { x: 1020, y: 330, color: "tokenNeutral" },
        { x: 1180, y: 470, color: "tokenPlayer"  },
    ];

    
    const darkCanvas = document.createElement("canvas");
    const darkCtx = darkCanvas.getContext("2d");

    

    function buildWalls() {
        const w = state.width;
        const h = state.height;
        roomRects.length = 0;
        roomRects.push({ x: 170,       y: 140,       w: 250, h: 150 });
        roomRects.push({ x: w - 460,   y: 130,       w: 260, h: 160 });
        roomRects.push({ x: 230,       y: h - 330,   w: 310, h: 150 });
        roomRects.push({ x: w - 530,   y: h - 360,   w: 350, h: 180 });
        roomRects.push({ x: w * 0.46,  y: 250,       w: 190, h: 170 });
    }

    function rectSegments(x, y, w, h) {
        return [
            { a: { x,     y     }, b: { x: x + w, y       } },
            { a: { x: x + w, y }, b: { x: x + w, y: y + h } },
            { a: { x: x + w, y: y + h }, b: { x, y: y + h } },
            { a: { x, y: y + h }, b: { x, y               } },
        ];
    }

    function getSegments() {
        const w = state.width;
        const h = state.height;
        const segs = [...rectSegments(84, 84, w - 168, h - 168)];
        for (const r of roomRects) segs.push(...rectSegments(r.x, r.y, r.w, r.h));
        return segs;
    }

    

    function intersectRay(px, py, dx, dy, ax, ay, bx, by) {
        const sx = bx - ax;
        const sy = by - ay;
        const denom = dx * sy - dy * sx;
        if (Math.abs(denom) < 1e-7) return null;
        const t = ((ax - px) * sy - (ay - py) * sx) / denom;
        const u = ((ax - px) * dy - (ay - py) * dx) / denom;
        if (t >= 0 && u >= 0 && u <= 1) return { x: px + dx * t, y: py + dy * t, t };
        return null;
    }

    function visibilityPolygon(px, py) {
        const segs = getSegments();
        const angles = [];
        for (const s of segs) {
            for (const p of [s.a, s.b]) {
                const a = Math.atan2(p.y - py, p.x - px);
                angles.push(a - EPSILON, a, a + EPSILON);
            }
        }
        const pts = [];
        for (const angle of angles) {
            const dx = Math.cos(angle);
            const dy = Math.sin(angle);
            let best = null;
            for (const s of segs) {
                const hit = intersectRay(px, py, dx, dy, s.a.x, s.a.y, s.b.x, s.b.y);
                if (hit && (!best || hit.t < best.t)) best = hit;
            }
            if (!best) continue;
            const dist = Math.hypot(best.x - px, best.y - py);
            pts.push(dist <= LIGHT_RADIUS + 2
                ? { x: best.x, y: best.y, angle }
                : { x: px + dx * LIGHT_RADIUS, y: py + dy * LIGHT_RADIUS, angle });
        }
        pts.sort((a, b) => a.angle - b.angle);
        return pts;
    }

    

    function drawBoard() {
        const w = state.width;
        const h = state.height;
        const spacing = 56;

        ctx.fillStyle = C.background;
        ctx.fillRect(0, 0, w, h);

        ctx.fillStyle = C.boardOuter;
        ctx.fillRect(60, 60, w - 120, h - 120);

        ctx.fillStyle = C.boardInner;
        ctx.fillRect(84, 84, w - 168, h - 168);

        ctx.strokeStyle = C.grid;
        ctx.globalAlpha = 0.6;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 84; x <= w - 84; x += spacing) { ctx.moveTo(x, 84); ctx.lineTo(x, h - 84); }
        for (let y = 84; y <= h - 84; y += spacing) { ctx.moveTo(84, y); ctx.lineTo(w - 84, y); }
        ctx.stroke();
        ctx.globalAlpha = 1;

        ctx.lineWidth = 5;
        for (const r of roomRects) {
            ctx.strokeStyle = C.wall;
            ctx.globalAlpha = 0.95;
            ctx.strokeRect(r.x, r.y, r.w, r.h);

            ctx.strokeStyle = C.wallStrong;
            ctx.globalAlpha = 0.55;
            ctx.lineWidth = 2;
            ctx.strokeRect(r.x + 3, r.y + 3, r.w - 6, r.h - 6);
            ctx.lineWidth = 5;
        }
        ctx.globalAlpha = 1;
    }

    function drawToken(tx, ty, color, outerAlpha) {
        ctx.beginPath();
        ctx.arc(tx, ty, 20, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = outerAlpha * 0.85;
        ctx.fill();
        ctx.strokeStyle = C.tokenStroke;
        ctx.lineWidth = 2;
        ctx.globalAlpha = outerAlpha * 0.80;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(tx, ty, 13, 0, Math.PI * 2);
        ctx.strokeStyle = C.tokenStroke;
        ctx.lineWidth = 1;
        ctx.globalAlpha = outerAlpha * 0.18;
        ctx.stroke();

        ctx.globalAlpha = 1;
    }

    function drawTokens(px, py) {
        for (const t of TOKEN_DEFS) {
            const dist = Math.hypot(t.x - px, t.y - py);
            drawToken(t.x, t.y, C[t.color], dist < LIGHT_RADIUS * 0.9 ? 0.70 : 0.25);
        }
    }

    function drawPointerToken(px, py) {
        ctx.beginPath();
        ctx.arc(px, py, 18, 0, Math.PI * 2);
        ctx.fillStyle = C.tokenPlayer;
        ctx.globalAlpha = 0.96;
        ctx.fill();
        ctx.strokeStyle = C.tokenStroke;
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.9;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(px, py, 10, 0, Math.PI * 2);
        ctx.strokeStyle = C.tokenStroke;
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.22;
        ctx.stroke();

        ctx.globalAlpha = 1;
    }

    function drawLighting(poly, px, py) {
        const w = state.width;
        const h = state.height;

        
        if (darkCanvas.width !== w) darkCanvas.width = w;
        if (darkCanvas.height !== h) darkCanvas.height = h;

        darkCtx.clearRect(0, 0, w, h);
        darkCtx.fillStyle = "rgba(0,0,0,0.74)";
        darkCtx.fillRect(0, 0, w, h);

        if (poly.length > 1) {
            darkCtx.globalCompositeOperation = "destination-out";
            darkCtx.beginPath();
            darkCtx.moveTo(poly[0].x, poly[0].y);
            for (let i = 1; i < poly.length; i++) darkCtx.lineTo(poly[i].x, poly[i].y);
            darkCtx.closePath();
            darkCtx.fillStyle = "#fff";
            darkCtx.fill();
            darkCtx.globalCompositeOperation = "source-over";
        }

        ctx.drawImage(darkCanvas, 0, 0);

        
        if (poly.length > 1) {
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(poly[0].x, poly[0].y);
            for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i].x, poly[i].y);
            ctx.closePath();
            ctx.clip();

            ctx.globalCompositeOperation = "screen";

            const g1 = ctx.createRadialGradient(px, py, 0, px, py, 360);
            g1.addColorStop(0,    "rgba(255,244,214,0.22)");
            g1.addColorStop(0.45, "rgba(230,197,123,0.10)");
            g1.addColorStop(1,    "rgba(230,197,123,0.00)");
            ctx.fillStyle = g1;
            ctx.fillRect(0, 0, w, h);

            const g2 = ctx.createRadialGradient(px, py, 0, px, py, 130);
            g2.addColorStop(0,    "rgba(255,247,224,0.30)");
            g2.addColorStop(0.45, "rgba(243,214,144,0.14)");
            g2.addColorStop(1,    "rgba(243,214,144,0.00)");
            ctx.fillStyle = g2;
            ctx.fillRect(0, 0, w, h);

            ctx.restore();
        }
    }

    

    function frame() {
        state.smoothX += (state.mouseX - state.smoothX) * 0.22;
        state.smoothY += (state.mouseY - state.smoothY) * 0.22;

        const px = state.smoothX;
        const py = state.smoothY;

        drawBoard();
        drawTokens(px, py);
        drawLighting(visibilityPolygon(px, py), px, py);
        drawPointerToken(px, py);

        requestAnimationFrame(frame);
    }

    function resize() {
        state.width  = window.innerWidth;
        state.height = window.innerHeight;
        canvas.width  = state.width;
        canvas.height = state.height;
        buildWalls();
    }

    window.addEventListener("pointermove", (e) => {
        state.mouseX = e.clientX;
        state.mouseY = e.clientY;
    });

    window.addEventListener("resize", resize);

    resize();
    requestAnimationFrame(frame);
})();
