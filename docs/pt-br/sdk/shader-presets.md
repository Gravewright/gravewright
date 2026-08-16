# Presets semânticos de shader

`scene.shaders.read` descobre o registry server-owned e lê instances aplicadas.
`scene.shaders.write` aplica e gerencia presets sem conceder authority trusted de
GLSL raw usada pelo editor interno.

```js
const presets = await sdk.scene.shaders.presets();
const schema = await sdk.scene.shaders.getPreset("vortex-1");
let instance = await sdk.scene.shaders.apply(sceneId, {
  presetId: schema.id, schemaVersion: schema.schemaVersion,
  parameters: { intensity: 0.5, speed: 1.5 }
});
instance = await sdk.scene.shaders.update(instance.id,
  { intensity: 0.7 }, { expectedVersion: instance.version });
instance = await sdk.scene.shaders.enable(instance.id, false,
  { expectedVersion: instance.version });
const atuais = await sdk.scene.shaders.list(sceneId);
await sdk.scene.shaders.remove(instance.id);
```

Preset, schema version ou parâmetro desconhecido é rejeitado. Valores obedecem
tipo e range; uniforms arbitrários nunca são aceitos. Mutations são authority do
GM e updates CAS retornam `STALE_VERSION` sem mutation parcial.
`scene.shaders.changed` é emitido depois do commit e exige re-read autorizado.
Source, programa compilado, uniform handle e GPU object não entram no contrato.
