# Persistent Spatial Sounds

Packages may use `scene.spatialSounds.read` and `scene.spatialSounds.write` to manage
the same persistent Scene emitters used by Gravewright's native Sound tools. This is
configuration authority, separate from `audio.playback`.

`sdk.scene.spatialSounds.create(sceneId, input)` accepts a native `soundId`, a
world-space `position`, bounded `radius` (greater than 0 and at most 100000), gain
from 0 through 1, `linear` or `smooth` falloff, loop/enabled flags, audience, and
the semantic `constrainedByWalls` switch. It never accepts URLs, filesystem paths,
browser audio objects, or renderer handles.

Use `list`/`get` to read audience-filtered configuration. Use `update` and `delete`
with `expectedVersion`; stale mutations fail atomically. Wall and Door acoustic
projection remains core-owned and does not expose hidden geometry. Scene deletion
removes emitters through the native lifecycle, while package unload does not delete
campaign-owned Scene data.

