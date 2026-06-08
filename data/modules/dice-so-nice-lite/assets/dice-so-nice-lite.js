(function () {
    "use strict";

    const MODULE_ID = "dice-so-nice-lite";
    const DEFAULT_COLOR = "#7c5cff";
    const vertexShaderSource = `
        attribute vec3 aPosition;
        attribute vec3 aNormal;
        uniform mat4 uMatrix;
        uniform mat4 uNormalMatrix;
        varying vec3 vNormal;
        void main() {
            gl_Position = uMatrix * vec4(aPosition, 1.0);
            vNormal = mat3(uNormalMatrix) * aNormal;
        }
    `;
    const fragmentShaderSource = `
        precision mediump float;
        uniform vec3 uColor;
        varying vec3 vNormal;
        void main() {
            vec3 n = normalize(vNormal);
            vec3 light = normalize(vec3(0.45, 0.75, 0.8));
            float diffuse = max(dot(n, light), 0.0);
            float rim = pow(1.0 - max(dot(n, vec3(0.0, 0.0, 1.0)), 0.0), 2.0);
            vec3 color = uColor * (0.32 + diffuse * 0.72) + vec3(0.95, 0.9, 1.0) * rim * 0.18;
            gl_FragColor = vec4(color, 1.0);
        }
    `;

    function normalizeColor(value) {
        const raw = String(value || "").trim();
        return /^#[0-9a-fA-F]{6}$/.test(raw) ? raw.toLowerCase() : DEFAULT_COLOR;
    }

    function hexToRgb(color) {
        const value = normalizeColor(color).slice(1);
        return [
            parseInt(value.slice(0, 2), 16) / 255,
            parseInt(value.slice(2, 4), 16) / 255,
            parseInt(value.slice(4, 6), 16) / 255,
        ];
    }

    function compileShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            throw new Error(gl.getShaderInfoLog(shader) || "Shader compile failed");
        }
        return shader;
    }

    function createProgram(gl) {
        const program = gl.createProgram();
        gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, vertexShaderSource));
        gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource));
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            throw new Error(gl.getProgramInfoLog(program) || "Program link failed");
        }
        return program;
    }

    function icosahedron() {
        const t = (1 + Math.sqrt(5)) / 2;
        const source = [
            [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
            [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
            [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
        ].map((v) => {
            const l = Math.hypot(v[0], v[1], v[2]);
            return [v[0] / l, v[1] / l, v[2] / l];
        });
        const faces = [
            [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
            [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
            [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
            [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
        ];
        const positions = [];
        const normals = [];
        faces.forEach((face) => {
            const a = source[face[0]];
            const b = source[face[1]];
            const c = source[face[2]];
            const n = faceNormal(a, b, c);
            [a, b, c].forEach((v) => {
                positions.push(v[0], v[1], v[2]);
                normals.push(n[0], n[1], n[2]);
            });
        });
        return { positions: new Float32Array(positions), normals: new Float32Array(normals), count: positions.length / 3 };
    }

    function faceNormal(a, b, c) {
        const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
        const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
        const nx = uy * vz - uz * vy;
        const ny = uz * vx - ux * vz;
        const nz = ux * vy - uy * vx;
        const l = Math.hypot(nx, ny, nz) || 1;
        return [nx / l, ny / l, nz / l];
    }

    function multiply(a, b) {
        const out = new Float32Array(16);
        for (let r = 0; r < 4; r += 1) {
            for (let c = 0; c < 4; c += 1) {
                out[c * 4 + r] = a[0 * 4 + r] * b[c * 4 + 0]
                    + a[1 * 4 + r] * b[c * 4 + 1]
                    + a[2 * 4 + r] * b[c * 4 + 2]
                    + a[3 * 4 + r] * b[c * 4 + 3];
            }
        }
        return out;
    }

    function perspective(fov, aspect, near, far) {
        const f = 1 / Math.tan(fov / 2);
        const out = new Float32Array(16);
        out[0] = f / aspect;
        out[5] = f;
        out[10] = (far + near) / (near - far);
        out[11] = -1;
        out[14] = (2 * far * near) / (near - far);
        return out;
    }

    function translation(x, y, z) {
        const out = identity();
        out[12] = x;
        out[13] = y;
        out[14] = z;
        return out;
    }

    function rotationX(rad) {
        const out = identity();
        const c = Math.cos(rad), s = Math.sin(rad);
        out[5] = c;
        out[6] = s;
        out[9] = -s;
        out[10] = c;
        return out;
    }

    function rotationY(rad) {
        const out = identity();
        const c = Math.cos(rad), s = Math.sin(rad);
        out[0] = c;
        out[2] = -s;
        out[8] = s;
        out[10] = c;
        return out;
    }

    function identity() {
        const out = new Float32Array(16);
        out[0] = 1;
        out[5] = 1;
        out[10] = 1;
        out[15] = 1;
        return out;
    }

    function createRenderer(canvas) {
        const gl = canvas.getContext("webgl", { alpha: true, antialias: true });
        if (!gl) return null;
        const program = createProgram(gl);
        const mesh = icosahedron();
        const position = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, position);
        gl.bufferData(gl.ARRAY_BUFFER, mesh.positions, gl.STATIC_DRAW);
        const normal = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, normal);
        gl.bufferData(gl.ARRAY_BUFFER, mesh.normals, gl.STATIC_DRAW);
        const loc = {
            position: gl.getAttribLocation(program, "aPosition"),
            normal: gl.getAttribLocation(program, "aNormal"),
            matrix: gl.getUniformLocation(program, "uMatrix"),
            normalMatrix: gl.getUniformLocation(program, "uNormalMatrix"),
            color: gl.getUniformLocation(program, "uColor"),
        };

        function draw(time, color) {
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const w = Math.max(1, Math.floor(rect.width * dpr));
            const h = Math.max(1, Math.floor(rect.height * dpr));
            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
            }
            gl.viewport(0, 0, w, h);
            gl.clearColor(0, 0, 0, 0);
            gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
            gl.enable(gl.DEPTH_TEST);
            gl.useProgram(program);

            gl.bindBuffer(gl.ARRAY_BUFFER, position);
            gl.enableVertexAttribArray(loc.position);
            gl.vertexAttribPointer(loc.position, 3, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ARRAY_BUFFER, normal);
            gl.enableVertexAttribArray(loc.normal);
            gl.vertexAttribPointer(loc.normal, 3, gl.FLOAT, false, 0, 0);

            const model = multiply(rotationY(time * 2.7), rotationX(time * 1.9));
            const view = translation(0, 0, -3.15);
            const proj = perspective(Math.PI / 4, w / h, 0.1, 20);
            const matrix = multiply(proj, multiply(view, model));
            gl.uniformMatrix4fv(loc.matrix, false, matrix);
            gl.uniformMatrix4fv(loc.normalMatrix, false, model);
            gl.uniform3fv(loc.color, hexToRgb(color));
            gl.drawArrays(gl.TRIANGLES, 0, mesh.count);
        }

        return { draw };
    }

    function buildUi(api) {
        if (document.querySelector("[data-gw-dsn]")) return null;
        let color = normalizeColor(api.settings.get("dice.color", DEFAULT_COLOR));

        const controls = document.createElement("div");
        controls.className = "gw-dsn";
        controls.dataset.gwDsn = "true";

        const roll = document.createElement("button");
        roll.className = "gw-dsn__roll";
        roll.type = "button";
        roll.textContent = "d20";
        roll.title = "Roll d20";

        const picker = document.createElement("input");
        picker.className = "gw-dsn__color";
        picker.type = "color";
        picker.value = color;
        picker.title = "Die color";
        controls.append(roll, picker);

        const stage = document.createElement("div");
        stage.className = "gw-dsn-stage";
        stage.hidden = true;

        const canvas = document.createElement("canvas");
        canvas.className = "gw-dsn-stage__canvas";
        const result = document.createElement("div");
        result.className = "gw-dsn-stage__result";
        result.textContent = "";
        stage.append(canvas, result);
        document.body.append(stage, controls);

        const renderer = createRenderer(canvas);
        let raf = 0;
        let rolling = false;

        function renderLoop(start, duration) {
            const now = performance.now();
            const elapsed = now - start;
            renderer?.draw(now / 1000, color);
            if (elapsed < duration) {
                raf = requestAnimationFrame(() => renderLoop(start, duration));
            } else {
                rolling = false;
                window.setTimeout(() => { stage.hidden = true; }, 1200);
            }
        }

        roll.addEventListener("click", () => {
            if (rolling) return;
            rolling = true;
            stage.hidden = false;
            result.textContent = String(1 + Math.floor(Math.random() * 20));
            cancelAnimationFrame(raf);
            renderLoop(performance.now(), 1700);
        });

        picker.addEventListener("input", () => {
            color = normalizeColor(picker.value);
            if (!stage.hidden) renderer?.draw(performance.now() / 1000, color);
        });

        picker.addEventListener("change", () => {
            color = normalizeColor(picker.value);
            void api.settings.set("dice.color", color).catch(() => {});
        });

        return { controls, stage };
    }

    window.Gravewright.modules.register({
        id: MODULE_ID,
        init(api) {
            buildUi(api);
        },
    });
})();
