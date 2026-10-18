# Universal VTT interchange

[Documentation](../README.md) · [Português](../pt-BR/universal-vtt.md) · [Map Builder](map-builder.md)

The GM can import a `.uvtt`, `.dd2vtt` or `.df2vtt` file as a new native scene,
or export an existing scene. These extensions use the same JSON container.
Gravewright supports version `0.2` with an embedded PNG or WebP image.
[Arkenforge's format description](https://arkenforge.com/universal-vtt-files/)
documents the common fields and their cell-based coordinates.

## Import

Choose **New scene → Import Universal VTT**, select the file and provide a scene
name. The same import action is available in the Builder's **Saved projects** panel.
Import creates a **GM-only scene** in Scenes, without activating it for players.
Review the returned warnings, then adjust the native scene before broadcasting.
The uploaded filename never becomes a server path.

The background is a single image. Import does not create a Map Builder project
or recover its individual tiles, brush strokes, layers or assets. Walls, doors
and lights are separate native scene objects that the GM can edit normally.

| Input | Native result |
| --- | --- |
| Resolution and image | Tiled background and scene grid |
| `map_origin` | Coordinate offset; fractional origins retain grid alignment |
| `line_of_sight`, `objects_line_of_sight` | Wall segments |
| Portal bounds | Doors; collinear walls are cut at their openings |
| Lights | Native color, radius, intensity and position |

Positions become `(point - map_origin) × pixels_per_grid`. Image dimensions must
match the rounded declared cell dimensions. Image metadata is stripped, and
EXIF orientation is not applied to map coordinates.

Portal semantics vary between consumers. Gravewright treats `closed: true` as a
closed door and `closed: false` as an open door, and always reports a warning.
The [Foundry importer source](https://github.com/moo-man/FVTT-DD-Import/blob/master/ddimport.js)
instead assumes the latter describes a window. Check these openings manually
after interchange, especially their movement and sight behavior.

Eight-digit colors use `AARRGGBB`; six-digit RGB colors are accepted too. Color
alpha scales native light intensity. Colored ambient light is approximated by
scene darkness; per-light shadow settings have no direct equivalent. Lights
from an image marked as containing baked lighting start disabled, and zero-range
lights also start disabled. The result lists these approximations explicitly.
External light ranges above 200 cells and intensities above 1 are clamped to
those native maxima, with warnings, rather than rejecting the whole map.

## Export

Right-click a scene in **Scenes** and choose **Export Universal VTT**. Prepare
the export, review its warnings and choose **Download Universal VTT**.

Export reads the current native scene, including its latest raster and visible
image placements. Dynamic surfaces retain their active material, mask, opacity,
rotation and layer erasure when flattened. Hidden GM image artwork is omitted.
The exporter reads no unsaved or unpublished Builder draft and changes no scene
state, project, receipt or stored file.

The download contains one PNG background, grid information, wall segments,
portals reflecting current open/closed state and enabled native lights. Locks,
secret-door presentation, height ranges and independent barrier channels do not
survive this representation. A fractional pixel grid is resampled to an integer
pixel grid and reported in the warnings.

Blueprints, variables, timers, presence regions, tokens, cards, permissions,
particles, shaders, fog, drawings and audio are excluded. Individual images and
dynamic materials become pixels in the exported background. Lighting cones,
animations, elevation and unlimited ranges are approximated. Review the warning
list before downloading; the file is an interchange copy, not a campaign backup.

## Limits and authorization

These interchange limits apply in addition to installation configuration:

| Resource | Limit |
| --- | --- |
| JSON upload/download | 64 MiB |
| Embedded compressed image | 48 MiB |
| Raster area | 16,777,216 pixels, or the lower configured map/Pillow limit |
| Native objects after portal cuts | 5,000 |
| Line-of-sight vertices | 20,000 |
| Wall/portal intersection checks | 2,000,000 |
| Floor composition groups | 32 |
| Cumulative composition work | 134,217,728 pixels |
| Pixels per grid cell | Integer from 1 to 10,000 |
| Input light range / intensity | Finite, nonnegative, at most 1,000,000; clamped to native 200 cells / 1 |

Configured upload bytes, image dimensions and tile-count limits may be lower.
Malformed numbers, duplicate JSON keys, invalid base64, unsupported image types,
animation, inconsistent image dimensions and excessive geometry are rejected
before scene publication. Native artwork must belong to the campaign; generated
masks must also belong to that exact scene.

Only a GM can import or export. Import rechecks membership and folder ownership
before committing, records a request receipt and removes newly stored tiles if
the operation fails. Retrying the same operation with the same request UUID
returns its original scene; changing the payload requires a new UUID.

## HTTP contract and checks

- `POST /api/containers/{campaign}/universal-vtt/import`: multipart `file`,
  `name`, `request_id` and optional `folderId`; returns
  `{scene, warnings, builderEditable: false}`.
- `GET /api/maps/{scene}/universal-vtt`: returns
  `{filename, document, warnings}`. `document` is the downloadable UVTT JSON.

The service is `gravewright/maps/universal_vtt.py`. Focused tests are in
`gravewright/maps/tests/test_universal_vtt.py`; they cover origin/grid and ARGB
conversion, portal openings, raster round trips, active dynamic materials and
erasers, GM isolation, receipts, rollback cleanup and resource limits. Run them
with the isolated test environment described in [Testing](testing.md).
