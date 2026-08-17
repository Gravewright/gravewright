(() => {

























    const MAX_ACTIVE = 8;




    const BLEND_MODES = new Set(["normal", "add", "multiply", "screen"]);

    function blendMode(value) {
        const mode = String(value || "normal").toLowerCase();
        return BLEND_MODES.has(mode) ? mode : "normal";
    }




    const PREAMBLE = `#version 300 es
precision highp float;

in vec2 vTextureCoord;
out vec4 finalColor;



uniform sampler2D gwUTexture;

uniform float gwUTime;
uniform float gwUIntensity;
uniform float gwUOpacity;
uniform float gwUScale;
uniform float gwUSpeed;
uniform vec3 gwUColor;


uniform vec2 gwUResolution;
uniform float gwUAspect;



uniform vec2 gwUOrigin;
uniform float gwURadius;
uniform float gwURotation;


uniform vec3 gwUCamera;



uniform sampler2D gwULightBuffer;


uniform vec2 gwUScreen;










uniform vec2 gwUFrameOrigin;


vec2 gwScreen(vec2 uv) {
    return uv * gwUResolution + gwUFrameOrigin;
}


vec2 gwScreenUV(vec2 uv) {
    return gwScreen(uv) / max(gwUScreen, vec2(1.0));
}



vec4 gwLight(vec2 uv) {
    return texture(gwULightBuffer, gwScreenUV(uv));
}



vec2 gwWorld(vec2 uv) {
    return (gwScreen(uv) - gwUCamera.xy) / max(gwUCamera.z, 0.0001);
}


vec2 gwRotated(vec2 uv) {
    vec2 d = gwWorld(uv) - gwUOrigin;
    float c = cos(gwURotation);
    float s = sin(gwURotation);
    return gwUOrigin + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
}










float gwFeature() {
    float base = gwURadius > 0.0 ? gwURadius * 0.6 : 420.0;
    return max(base * gwUScale, 1.0);
}



vec2 gwPattern(vec2 uv) {


    return (gwRotated(uv) - gwUOrigin) / gwFeature();
}
`;
    const MESH_VERTEX = `#version 300 es
precision highp float;
in vec2 aPosition;
in vec2 aUV;
out vec2 vTextureCoord;
uniform mat3 uProjectionMatrix;
uniform mat3 uWorldTransformMatrix;
uniform mat3 uTransformMatrix;
void main() {
    vTextureCoord = aUV;
    gl_Position = vec4((uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix * vec3(aPosition, 1.0)).xy, 0.0, 1.0);
}`;


    const USER_PREFIX = `#define uTexture gwUTexture
#define uTime gwUTime
#define uIntensity gwUIntensity
#define uOpacity gwUOpacity
#define uScale gwUScale
#define uSpeed gwUSpeed
#define uColor gwUColor
#define uResolution gwUResolution
#define uAspect gwUAspect
#define uOrigin gwUOrigin
#define uRadius gwURadius
#define uRotation gwURotation
#define uCamera gwUCamera
#define uLightBuffer gwULightBuffer
#define uScreen gwUScreen
#define uFrameOrigin gwUFrameOrigin
#define main gwUserMain
`;
    const USER_SUFFIX = "\n#undef main\nvoid main() { gwUserMain(); finalColor *= gwUOpacity; }\n";
    const PREAMBLE_LINES = PREAMBLE.split("\n").length - 1 + 1;








    const bank = new Map();
    const lastGood = new Map();
    const stage = new Map();
    const broken = new Map();









    const FADE_FROM = 0.85;

    function rangeFill(centreX, centreY, radius) {
        return new PIXI.FillGradient({
            type: "radial",




            textureSpace: "global",
            start: { x: centreX, y: centreY }, innerRadius: 0,
            end: { x: centreX, y: centreY }, outerRadius: radius,
            colorStops: [
                { offset: 0, color: "rgba(255,255,255,1)" },
                { offset: FADE_FROM, color: "rgba(255,255,255,1)" },
                { offset: 1, color: "rgba(255,255,255,0)" },
            ],
        });
    }



    let dark = null;
    function darkPixel() {
        if (dark) return dark;
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 1;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, 1, 1);
        dark = PIXI.Texture.from(canvas);
        return dark;
    }

    function rgb(hex) {
        const parsed = parseInt(String(hex || "").replace("#", ""), 16);
        const value = Number.isFinite(parsed) ? parsed : 0x8fb6ff;
        return [((value >> 16) & 0xff) / 255, ((value >> 8) & 0xff) / 255, (value & 0xff) / 255];
    }




    function compileProblem(gl, fragment) {
        if (!gl) return null;
        const handle = gl.createShader(gl.FRAGMENT_SHADER);
        if (!handle) return null;
        gl.shaderSource(handle, fragment);
        gl.compileShader(handle);
        const ok = gl.getShaderParameter(handle, gl.COMPILE_STATUS);
        const log = ok ? null : (gl.getShaderInfoLog(handle) || "erro de compilacao");
        gl.deleteShader(handle);
        if (ok) return null;

        return log.replace(/ERROR:\s*(\d+):(\d+)/g, (_all, col, line) =>
            `ERRO: linha ${Math.max(1, Number(line) - PREAMBLE_LINES)}, coluna ${col}`);
    }

    function build(gl, source) {
        const compileStarted = performance.now();
        const fragment = PREAMBLE + USER_PREFIX + source + USER_SUFFIX;
        const problem = compileProblem(gl, fragment);
        if (problem) {
            performance.measure?.("shader_pipeline_compile_ms", { start: compileStarted, end: performance.now() });
            return { shader: null, error: problem };
        }
        try {
            const uniforms = new PIXI.UniformGroup({
                gwUTime: { value: 0, type: "f32" },
                gwUIntensity: { value: 0.6, type: "f32" },
                gwUOpacity: { value: 1, type: "f32" },
                gwUScale: { value: 1, type: "f32" },
                gwUSpeed: { value: 1, type: "f32" },
                gwUColor: { value: [0.56, 0.71, 1], type: "vec3<f32>" },
                gwUResolution: { value: [1, 1], type: "vec2<f32>" },
                gwUAspect: { value: 1, type: "f32" },
                gwUOrigin: { value: [0, 0], type: "vec2<f32>" },
                gwURadius: { value: 0, type: "f32" },
                gwURotation: { value: 0, type: "f32" },
                gwUCamera: { value: [0, 0, 1], type: "vec3<f32>" },
                gwUScreen: { value: [1, 1], type: "vec2<f32>" },
                gwUFrameOrigin: { value: [0, 0], type: "vec2<f32>" },
            });
            const shaderProgram = new PIXI.Shader({
                glProgram: PIXI.GlProgram.from({ vertex: MESH_VERTEX, fragment }),



                resources: {
                    shaderUniforms: uniforms,
                    gwUTexture: PIXI.Texture.WHITE.source,
                    gwULightBuffer: darkPixel().source,
                },
            });
            performance.measure?.("shader_pipeline_compile_ms", { start: compileStarted, end: performance.now() });
            return { shader: shaderProgram, uniforms, error: null };
        } catch (error) {
            performance.measure?.("shader_pipeline_compile_ms", { start: compileStarted, end: performance.now() });
            return { shader: null, error: String(error?.message || error) };
        }
    }

    function semanticPresetSource(value) {
        const match = /^gravewright-preset:\/\/([^/]+)\/v(\d+)$/.exec(String(value || ""));
        if (!match || match[2] !== "1") return String(value || "");
        const preset = (window.GravewrightShaderPresets || []).find(candidate => candidate.id === match[1]);
        return String(preset?.source || "");
    }

    function programFor(gl, shader) {
        const switchStarted = performance.now();
        const source = semanticPresetSource(shader.source);


        const key = `${shader.id}\u0000${source}`;

        if (bank.has(key)) {
            const cached = bank.get(key);
            return cached.error ? (lastGood.get(shader.id) || cached) : cached;
        }
        const built = build(gl, source);
        if (shader.transient) performance.measure?.("preset_preview_switch_ms", {
            start: switchStarted, end: performance.now(),
        });
        bank.set(key, built);
        if (built.error && broken.get(shader.id) !== built.error) {
            broken.set(shader.id, built.error);


            document.dispatchEvent(new CustomEvent("vtt:shader-error", {
                detail: { shaderId: shader.id, name: shader.name || "", error: built.error },
            }));
        }
        if (!built.error) {
            broken.delete(shader.id);
            lastGood.set(shader.id, built);
        }
        if (bank.size > 24) {
            const oldest = bank.keys().next().value;
            try { bank.get(oldest)?.shader?.destroy?.(); } catch (_err) {                    }
            bank.delete(oldest);
        }
        return built.error ? (lastGood.get(shader.id) || built) : built;
    }

    function meshFor(board, id, shaderProgram) {
        const existing = stage.get(id);
        if (existing) {
            existing.mesh.shader = shaderProgram;
            return existing;
        }
        const geometry = new PIXI.MeshGeometry({
            positions: new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]),
            uvs: new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]),
            indices: new Uint32Array([0, 1, 2, 0, 2, 3]),
        });
        const mesh = new PIXI.Mesh({ geometry, shader: shaderProgram });
        mesh.eventMode = "none";
        const mask = new PIXI.Graphics();
        const entry = { mesh, mask, stamp: "" };
        stage.set(id, entry);
        board.effectsLayer.addChild(mask, mesh);
        return entry;
    }

    function drop(id) {
        const entry = stage.get(id);
        if (!entry) return;
        entry.mesh.mask = null;
        entry.mesh.destroy({ children: true });
        entry.mask.destroy();
        stage.delete(id);
    }






    function traceShape(target, polygon, centreX, centreY, radius) {
        if (polygon && polygon.length >= 3) {



            const pontos = [];
            polygon.forEach((point) => pontos.push(point.sx, point.sy));
            return target.poly(pontos);
        }
        return target.circle(centreX, centreY, radius);
    }

    function paintMask(entry, polygon, centreX, centreY, radius, stamp) {
        if (entry.stamp === stamp) return;
        entry.stamp = stamp;
        entry.mask.clear();
        traceShape(entry.mask, polygon, centreX, centreY, radius)
            .fill(rangeFill(centreX, centreY, radius));
    }









    function render(board, shaders, now, cssW, cssH, camera, lightTexture) {
        const layer = board?.effectsLayer;
        if (!layer) return 0;
        const zoom = camera?.zoom || 1;
        const offsetX = camera?.offsetX || 0;
        const offsetY = camera?.offsetY || 0;
        const active = (shaders || []).filter((shader) => {
            const radius = Number(shader.radiusWorld || 0) * zoom;
            if (radius <= 0) return true;
            const x = Number(shader.x || 0) * zoom + offsetX;
            const y = Number(shader.y || 0) * zoom + offsetY;
            return x + radius >= 0 && y + radius >= 0 && x - radius <= cssW && y - radius <= cssH;
        }).slice(0, MAX_ACTIVE);
        const alive = new Set(active.map((shader) => shader.id));

        [...stage.keys()].forEach((id) => { if (!alive.has(id)) drop(id); });
        if (!active.length) return 0;

        const gl = board?.app?.renderer?.gl || null;
        let drawn = 0;

        active.forEach((shader) => {
            const program = programFor(gl, shader);
            if (!program.shader) { drop(shader.id); return; }

            const entry = meshFor(board, shader.id, program.shader);
            const { mesh, mask } = entry;
            const radius = Number(shader.radiusWorld || 0) * zoom;
            const centreX = Number(shader.x || 0) * zoom + offsetX;
            const centreY = Number(shader.y || 0) * zoom + offsetY;




            const left = radius > 0 ? centreX - radius : 0;
            const top = radius > 0 ? centreY - radius : 0;
            const width = radius > 0 ? radius * 2 : cssW;
            const height = radius > 0 ? radius * 2 : cssH;

            mesh.position.set(left, top);
            mesh.width = Math.max(1, width);
            mesh.height = Math.max(1, height);
            mesh.blendMode = blendMode(shader.blend_mode);
            mesh.visible = true;
            if (radius > 0) {
                mask.visible = true;
                mesh.mask = mask;

                const screened = (shader.occlusion || []).map((point) => ({
                    sx: point.x * zoom + offsetX, sy: point.y * zoom + offsetY,
                }));


                const forma = `${shader.occlusionStamp || ""}:${Math.round(centreX)}:${Math.round(centreY)}:${Math.round(radius)}`;
                paintMask(entry, screened, centreX, centreY, radius, forma);
            } else {



                mask.visible = false;
                mask.clear();
                mesh.mask = null;
                entry.stamp = "";

            }

            const u = program.uniforms.uniforms;


            u.gwUTime = (now % 3600000) / 1000;
            u.gwUIntensity = Number(shader.intensity ?? 0.6);
            u.gwUOpacity = Math.max(0, Math.min(1, Number(shader.opacity ?? 1)));
            u.gwUScale = Number(shader.scale ?? 1);
            u.gwUSpeed = Number(shader.speed ?? 1);
            u.gwUColor = rgb(shader.color);
            u.gwUResolution = [width, height];
            u.gwUAspect = height ? width / height : 1;
            u.gwUOrigin = [Number(shader.x || 0), Number(shader.y || 0)];
            u.gwURadius = Number(shader.radiusWorld || 0);
            u.gwURotation = (Number(shader.rotation || 0) * Math.PI) / 180;




            u.gwUCamera = [offsetX, offsetY, zoom];
            u.gwUScreen = [cssW, cssH];
            u.gwUFrameOrigin = [left, top];



            program.shader.resources.gwULightBuffer = (lightTexture || darkPixel()).source;
            drawn += 1;
        });
        return drawn;
    }

    function requiresContinuousFrames(shaders) {
        return (shaders || []).slice(0, MAX_ACTIVE)
            .some((shader) => Number(shader.speed ?? 1) !== 0);
    }

    function requestNextFrame(shaders, drawn, requestRender) {
        if (drawn > 0 && requiresContinuousFrames(shaders)) requestRender?.();
    }

    function clear() {
        [...stage.keys()].forEach(drop);
    }

    function invalidate(shaderId) {
        const id = String(shaderId || "");
        if (!id) return;
        drop(id);
        const prefix = `${id}\u0000`;
        [...bank.keys()].forEach((key) => {
            if (!key.startsWith(prefix)) return;
            try { bank.get(key)?.shader?.destroy?.(); } catch (_err) {                    }
            bank.delete(key);
        });
        broken.delete(id);
        lastGood.delete(id);
    }

    window.GravewrightShaderEffects = {
        render,
        requiresContinuousFrames,
        requestNextFrame,
        clear,
        invalidate,
        errorFor: (shaderId) => broken.get(shaderId) || null,
        PREAMBLE,
        MAX_ACTIVE,
        BLEND_MODES: [...BLEND_MODES],
    };
})();
