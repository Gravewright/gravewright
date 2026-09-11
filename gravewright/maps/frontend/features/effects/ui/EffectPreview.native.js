import { text as gwText } from '../../../shared/config/i18n/text.js';
import { renderingPreferences } from '../../../shared/rendering/render-profile.js';
import { effectQuality } from '../../../shared/rendering/effect-quality.js';
import { PREAMBLE, USER_PREFIX, USER_SUFFIX } from '../../scene-layers/lib/shader-language.js';
import { shaderPresets } from '../../scene-layers/lib/shader-presets.js';
import { PARTICLE_DEFAULTS, PARTICLE_KINDS, particlesOf } from '../model/particle-profiles.js';
import { defaults } from '../model/effects.js';
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "div", "attrs": { "class": "effect-preview", "role": "img" }, "bind": { "aria-label": "(gwText('Preview: {0}', label))" }, "events": [], "children": [{ "tag": "div", "attrs": { "ref": "host", "class": "effect-preview__surface" }, "bind": {}, "events": [], "children": [{ "tag": "canvas", "attrs": { "ref": "canvas" }, "bind": {}, "events": [], "children": [] }] }, { "tag": "span", "attrs": { "class": "effect-preview__label" }, "bind": {}, "events": [], "children": [{ "value": "(failed ? gwText('Preview unavailable') : label)" }] }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const host = ref(), canvas = ref();
    const failed = ref(false);
    let gl = null, ctx = null;
    let program = null, buffer = null, white = null;
    let observer, frame = 0, closed = false, started = 0;
    let stopProfile;
    let animate;
    function compile(type, source) { const shader = gl.createShader(type); gl.shaderSource(shader, source); gl.compileShader(shader); if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        gl.deleteShader(shader);
        throw new Error('Shader preview compilation failed');
    } return shader; }
    function render() {
        if (!canvas.value || !host.value || closed)
            return;
        animate = undefined;
        failed.value = false;
        if (program) {
            gl.deleteProgram(program);
            program = null;
        }
        const width = host.value.clientWidth, height = host.value.clientHeight;
        if (!width || !height)
            return;
        const ratio = Math.min(devicePixelRatio, 2);
        canvas.value.width = Math.round(width * ratio);
        canvas.value.height = Math.round(height * ratio);
        try {
            if (props.kind === 'shader') {
                if (!gl)
                    throw new Error('WebGL unavailable');
                const preset = { ...defaults(), ...shaderPresets.find(p => p.id === props.choice) };
                const vertex = compile(gl.VERTEX_SHADER, '#version 300 es\nin vec2 position;out vec2 vTextureCoord;void main(){vTextureCoord=(position+1.0)*0.5;gl_Position=vec4(position.x,-position.y,0.0,1.0);}');
                let fragment;
                try {
                    fragment = compile(gl.FRAGMENT_SHADER, PREAMBLE + USER_PREFIX + preset.source + USER_SUFFIX);
                }
                catch (error) {
                    gl.deleteShader(vertex);
                    throw error;
                }
                program = gl.createProgram();
                gl.attachShader(program, vertex);
                gl.attachShader(program, fragment);
                gl.linkProgram(program);
                gl.deleteShader(vertex);
                gl.deleteShader(fragment);
                if (!gl.getProgramParameter(program, gl.LINK_STATUS))
                    throw new Error('Shader preview linking failed');
                gl.useProgram(program);
                gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
                const position = gl.getAttribLocation(program, 'position');
                gl.enableVertexAttribArray(position);
                gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
                gl.viewport(0, 0, canvas.value.width, canvas.value.height);
                const loc = (name) => gl.getUniformLocation(program, name);
                const worldHeight = 610, worldWidth = worldHeight * width / height;
                const values = { gwUQuality: (effectQuality(renderingPreferences.current().name).shaderDetail - 1) / 4, gwUIntensity: preset.intensity, gwUOpacity: preset.opacity, gwUScale: preset.scale, gwUSpeed: preset.speed, gwUAspect: worldWidth / worldHeight, gwURadius: preset.radius > 0 ? 500 : 0, gwURotation: preset.rotation * Math.PI / 180 };
                for (const [name, value] of Object.entries(values))
                    gl.uniform1f(loc(name), value);
                gl.uniform2f(loc('gwUResolution'), worldWidth, worldHeight);
                gl.uniform2f(loc('gwUScreen'), worldWidth, worldHeight);
                gl.uniform2f(loc('gwUOrigin'), worldWidth / 2, worldHeight / 2);
                gl.uniform2f(loc('gwUFrameOrigin'), 0, 0);
                gl.uniform3f(loc('gwUCamera'), 0, 0, 1);
                const color = parseInt(preset.color.slice(1), 16);
                gl.uniform3f(loc('gwUColor'), (color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255);
                gl.activeTexture(gl.TEXTURE0);
                gl.bindTexture(gl.TEXTURE_2D, white);
                gl.uniform1i(loc('gwUTexture'), 0);
                gl.uniform1i(loc('gwULightBuffer'), 0);
                const timeUniform = loc('gwUTime');
                animate = time => { gl.uniform1f(timeUniform, time); gl.drawArrays(gl.TRIANGLES, 0, 6); };
            }
            else {
                if (!ctx)
                    throw new Error('Canvas unavailable');
                const settings = PARTICLE_DEFAULTS[props.choice], spec = PARTICLE_KINDS[props.choice];
                if (!settings || !spec)
                    return;
                const emitter = { ...defaults(), ...settings, id: 'preview', kind: props.choice, x: width / 2, y: spec.orbit ? height / 2 : (spec.rise ?? 0) > 0 ? height * .85 : height * .15 };
                const cell = Math.min(height * .7 / (Math.max(1, Math.abs(spec.rise ?? 0), spec.gravity ?? 0) * settings.scale), width / (settings.scale * 3));
                const dot = document.createElement('canvas');
                dot.width = dot.height = 64;
                const dc = dot.getContext('2d');
                const gradient = dc.createRadialGradient(32, 32, 0, 32, 32, 32);
                gradient.addColorStop(0, settings.color);
                gradient.addColorStop(.35, `${settings.color}bf`);
                gradient.addColorStop(1, `${settings.color}00`);
                dc.fillStyle = gradient;
                dc.fillRect(0, 0, 64, 64);
                animate = time => { ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, width, height); for (const p of particlesOf(emitter, time * 1000, cell)) {
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rotation);
                    ctx.globalAlpha = p.alpha;
                    ctx.globalCompositeOperation = p.blend === 'add' ? 'lighter' : p.blend === 'screen' ? 'screen' : 'source-over';
                    ctx.drawImage(dot, -p.size * p.aspect, -p.size, p.size * 2 * p.aspect, p.size * 2);
                    ctx.restore();
                } };
            }
            started = performance.now();
            animate?.(0);
        }
        catch {
            failed.value = true;
        }
    }
    watch(() => props.choice, render);
    onMounted(() => {
        if (props.kind === 'shader') {
            gl = canvas.value.getContext('webgl2', { alpha: true, premultipliedAlpha: true });
            if (gl) {
                buffer = gl.createBuffer();
                gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
                gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW);
                white = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, white);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
            }
        }
        else
            ctx = canvas.value.getContext('2d');
        render();
        observer = new ResizeObserver(render);
        observer.observe(host.value);
        let last = 0;
        const tick = () => { if (closed)
            return; const fps = effectQuality(renderingPreferences.current().name).fps; if (!fps) {
            animate?.(0);
            return;
        } const now = performance.now(); if (now - last >= 1000 / fps) {
            last = now;
            animate?.((now - started) / 1000);
        } frame = requestAnimationFrame(tick); };
        stopProfile = renderingPreferences.subscribe(() => { cancelAnimationFrame(frame); render(); tick(); });
    });
    onBeforeUnmount(() => { closed = true; stopProfile?.(); cancelAnimationFrame(frame); observer?.disconnect(); animate = undefined; if (gl) {
        gl.deleteProgram(program);
        gl.deleteBuffer(buffer);
        gl.deleteTexture(white);
        gl.getExtension('WEBGL_lose_context')?.loseContext();
    } gl = null; ctx = null; });
    return { gwText, renderingPreferences, effectQuality, PREAMBLE, USER_PREFIX, USER_SUFFIX, shaderPresets, PARTICLE_DEFAULTS, PARTICLE_KINDS, particlesOf, defaults, host, canvas, failed, gl, ctx, program, buffer, white, observer, frame, closed, started, stopProfile, animate, compile, render, emit: options.emit };
});
