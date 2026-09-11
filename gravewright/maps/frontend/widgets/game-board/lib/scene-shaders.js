import { Container, GlProgram, Graphics, Mesh, MeshGeometry, Shader, Texture, UniformGroup } from "pixi.js";
import { PREAMBLE, MESH_VERTEX, USER_PREFIX, USER_SUFFIX } from "../../../features/scene-layers/lib/shader-language.js";
import { shaderPresets } from "../../../features/scene-layers/lib/shader-presets.js";
import { effectQuality } from "../../../shared/rendering/effect-quality.js";
import { visibilityPolygon } from "../model/visibility-polygon.js";
export function mountShaders(layer, state, cell, sceneWidth, sceneHeight, lightMap, ambient, profile, register) {
    const quality = effectQuality(profile);
    const owned = [];
    for (const record of state.shaders.filter(s => s.enabled)) {
        const group = new Container();
        layer.addChild(group);
        register?.(`shader:${record.id}`, group);
        const preset = /^gravewright-preset:\/\/([^/]+)\/v1$/.exec(record.source);
        const source = preset ? shaderPresets.find(p => p.id === preset[1])?.source : record.source;
        if (!source)
            continue;
        const radius = record.radius * cell, width = radius > 0 ? radius * 2 : sceneWidth, height = radius > 0 ? radius * 2 : sceneHeight;
        const x = radius > 0 ? record.x - radius : 0, y = radius > 0 ? record.y - radius : 0;
        if (!quality.shaders) {
            const shape = new Graphics();
            if (radius > 0)
                shape.poly(visibilityPolygon(record, radius, state.walls).flatMap(p => [p.x, p.y]));
            else
                shape.rect(0, 0, sceneWidth, sceneHeight);
            shape.fill({ color: record.color, alpha: .12 * (record.opacity ?? 1) });
            group.addChild(shape);
            continue;
        }
        const color = Number.parseInt(record.color.replace('#', ''), 16);
        const uniforms = new UniformGroup({
            gwUQuality: { value: (quality.shaderDetail - 1) / 4, type: "f32" }, gwULightResponse: { value: record.light_response ?? 0, type: "f32" }, gwUAmbient: { value: ambient, type: "f32" },
            gwUTime: { value: 0, type: "f32" }, gwUIntensity: { value: record.intensity, type: "f32" },
            gwUOpacity: { value: record.opacity ?? 1, type: "f32" }, gwUScale: { value: record.scale ?? 1, type: "f32" }, gwUSpeed: { value: record.speed, type: "f32" },
            gwUColor: { value: [(color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255], type: "vec3<f32>" },
            gwUResolution: { value: [width, height], type: "vec2<f32>" }, gwUAspect: { value: width / height, type: "f32" },
            gwUOrigin: { value: [record.x, record.y], type: "vec2<f32>" }, gwURadius: { value: radius, type: "f32" }, gwURotation: { value: (record.rotation ?? 0) * Math.PI / 180, type: "f32" },
            gwUCamera: { value: [0, 0, 1], type: "vec3<f32>" }, gwUScreen: { value: [sceneWidth, sceneHeight], type: "vec2<f32>" }, gwUFrameOrigin: { value: [x, y], type: "vec2<f32>" },
        });
        const shader = new Shader({ glProgram: GlProgram.from({ vertex: MESH_VERTEX, fragment: PREAMBLE + USER_PREFIX + source + USER_SUFFIX }), resources: { shaderUniforms: uniforms, gwUTexture: Texture.WHITE.source, gwULightBuffer: lightMap.source } });
        const geometry = new MeshGeometry({ positions: new Float32Array([0, 0, width, 0, width, height, 0, height]), uvs: new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), indices: new Uint32Array([0, 1, 2, 0, 2, 3]) });
        const mesh = new Mesh({ geometry, shader });
        mesh.position.set(x, y);
        const blend = record.blend_mode;
        if (blend === "add" || blend === "multiply" || blend === "screen")
            mesh.blendMode = blend;
        if (radius > 0) {
            const polygon = visibilityPolygon(record, radius, state.walls);
            const mask = new Graphics().poly(polygon.flatMap(p => [p.x, p.y])).fill("white");
            group.addChild(mask);
            mesh.mask = mask;
        }
        group.addChild(mesh);
        owned.push({ shader, geometry, tick: time => { uniforms.uniforms.gwUTime = time; } });
    }
    return { tick(time) { for (const item of owned)
            item.tick(time); }, dispose() { for (const item of owned) {
            item.shader.destroy();
            item.geometry.destroy();
        } owned.length = 0; } };
}
