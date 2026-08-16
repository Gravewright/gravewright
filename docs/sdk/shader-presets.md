# Semantic shader presets

`scene.shaders.read` discovers the server-owned registry and reads applied
instances. `scene.shaders.write` applies and manages presets without granting
the trusted raw-GLSL authority used by the internal editor.

```js
const presets = await sdk.scene.shaders.presets();
const schema = await sdk.scene.shaders.getPreset("vortex-1");
let instance = await sdk.scene.shaders.apply(sceneId, {
  presetId: schema.id,
  schemaVersion: schema.schemaVersion,
  parameters: { intensity: 0.5, speed: 1.5 }
});
instance = await sdk.scene.shaders.update(instance.id,
  { intensity: 0.7 }, { expectedVersion: instance.version });
instance = await sdk.scene.shaders.enable(instance.id, false,
  { expectedVersion: instance.version });
const current = await sdk.scene.shaders.list(sceneId);
await sdk.scene.shaders.remove(instance.id);
```

Unknown presets, schema versions and parameters are rejected. Values must match
their declared type and range; arbitrary uniforms are never accepted. Mutations
are GM-authoritative and compare-and-swap updates return `STALE_VERSION` without
partial mutation. `scene.shaders.changed` is a small post-commit event followed
by an authorized re-read. No source, compiled program, uniform handle or GPU
object appears in the public registry, DTO or event.
