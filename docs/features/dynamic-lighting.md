# Dynamic lighting, walls, and doors

The lighting layer gives GMs dedicated wall and door tools. Wall clicks chain
segments; door clicks create a single segment. Drawing uses free coordinates,
without grid or angle snapping. Select a segment and press Delete to remove it. Closed doors block
vision; open doors do not.

Walls are persisted per scene and broadcast through `scene.walls.updated`.
Members may read the geometry required for local line-of-sight rendering, while
only the campaign GM may create, delete, or toggle it. The client computes a
visibility polygon from the controlled token without evaluating package code.

Set `DYNAMIC_LIGHTING_ENABLED=false` and restart for rollback. The schema may
remain in place; the UI and HTTP endpoints become unavailable.

## Scene shaders

GMs can place fragment-shader effects at a clicked world position. The effect
origin remains anchored to that point while the camera pans or zooms. Shader
snippets implement `void main()` and assign `finalColor`; the runtime supplies
the documented Gravewright coordinates, time, colour, intensity, scale, speed,
rotation, and origin helpers around the snippet.

The editor provides opacity and compositing modes such as normal, multiply,
darken, screen, and intense light. Compositing is applied by the renderer, so it
works consistently across valid shader snippets rather than requiring each
snippet to implement blending itself.

The built-in library contains 50 localized presets across fire, electricity,
fog, runes, portals, weather, energy, shadows, and environmental effects.
Selecting a preset updates the active editor immediately.

## Particles

Scene particles support multiple emitter and motion styles. The editor exposes
particle type, count/rate, lifetime, speed, direction, spread, gravity, scale,
rotation, colour, opacity, and related appearance controls. Saved changes are
applied to the live scene without requiring a page reload.

## Layer visibility

Effects, walls, and lighting are three separate visibility toggles in the layer
HUD, persisted per table in the browser. Hiding lighting darkens nothing and
leaves particles and shaders on screen; hiding effects removes particles and
shaders without touching vision. Doors can only be picked where they are
actually visible, so a door hidden behind a wall the current view cannot see is
not a click target.

## Streamer composition sandbox

A streamer view can compose lighting, walls, particles, and shaders as if it were
a GM, but every edit stays in that browser: the mutations are applied to the
local scene state and never reach the server, the table, or the database. It is
a staging surface for framing a shot, not a second GM seat — reloading the
streamer view discards everything it composed.

The streamer view also sees the scene lit as the table's audience view, not
through a single token's vision.
