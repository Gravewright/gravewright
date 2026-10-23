# Universal VTT import and export

[Documentation](../README.md) · [Português](../pt-BR/universal-vtt.md) · [Map Builder](map-builder.md)

Use Universal VTT to bring a finished map, its grid, walls, doors and lights into
Gravewright, or to download an interchange copy of a native scene. Only a campaign
GM can import or export. Imported scenes start **visible only to the GM** and do
not replace the scene currently broadcast to players.

## Choose the import path

The Builder offers two different import actions:

| What you have | Action | Result |
| --- | --- | --- |
| A `.uvtt`, `.dd2vtt` or `.df2vtt` file containing an image and map data | **Import Universal VTT** in Builder | A new linked native scene and editable Builder project with compatible walls, doors and lights |
| The same file, when only a game scene is needed | **New scene → Import Universal VTT** | A native scene; use **Edit with MapBuilder** later to create its source |
| A PNG, JPEG, WebP or TIFF image | **Import ready-made map** | A background in the current Builder project; add walls, objects, lights and behaviors over it |

For an image, choose **Library → Import → Import ready-made map**, or the same
action in **Settings** or **Saved projects**. Upload an image (up to 25 MB) or
choose an existing campaign image, set the width and height in cells and the cell
size, then choose **Use map image**. The image fills the map beneath its layers.
Project changes save automatically; **Generate scene** or **Update scene** applies
them to the game. See [Import a finished map](map-builder.md#import-a-finished-map)
for replacement, removal and Undo/Redo.

A Universal VTT import cannot reconstruct the source map's brush strokes,
individual assets or Builder layers from its flattened background. Importing from
Builder saves the current draft first, creates a separate linked project and
loads it in the editor. Compatible collision geometry and lights remain editable;
the flattened background remains one image. Both paths keep the new scene GM-only.

## Import a Universal VTT scene

1. In **Scenes**, choose **New scene → Import Universal VTT**. To import into a
   scene folder, start the new-scene action from that folder. The same importer
   is available under **Saved projects → Import Universal VTT** in the Builder.
2. Select the **Universal VTT file** and check **Scene name**. Selecting a file
   fills an empty name from its filename; you can change it. Names must contain
   1–120 characters. The dialog has no grid or lighting controls: those values
   come from the file.
3. Choose **Import scene** and wait for the result. The import dialog cannot
   close while this request is running.
4. Read the warnings, then choose **Close**. Warnings describe the scene already
   created; there is no approval or preview step before creation.
5. Inspect the scene in **Scenes**. Check grid alignment, wall openings, door
   states and lighting with the native scene tools before activating it for
   players.

The destination folder comes from the action that opened the importer; there is
no folder picker inside the dialog. The folder must belong to this campaign.
The background is stored as scene tiles, while walls, doors and lights remain
editable native objects. Import from the scene directory creates no Builder
project; import from Builder creates and loads one. Neither path overwrites an
existing scene or Builder draft. **Update scene** applies Builder edits to the
same linked scene. Import warnings report objects that must remain native.

### Read the import warnings

Warnings indicate an imported approximation, rather than a failed import:

| Warning concerns | What to check |
| --- | --- |
| Portals imported as doors | Every portal becomes a door. Check intended windows, movement and sight behavior, and whether each opening should start open or closed. |
| Ambient color | Colored ambient light becomes an approximation using scene darkness. |
| Baked lighting | Lights start disabled because the file says the image already contains lighting. Check before enabling them to avoid lighting the artwork twice. |
| Light range or intensity | Ranges above 200 cells and intensities above 1 are clamped to those maxima. |
| Zero-range lights | These start disabled. Set an appropriate native radius before enabling them. |
| Per-light shadows | Per-light shadow settings have no direct equivalent. |
| Degenerate wall segments | Extremely short segments were ignored; inspect the surrounding wall. |

### Recover from an import error

If validation fails, read the message, correct the name or source file and choose
**Import scene** again. Invalid files, unsupported images or excessive geometry
do not leave a partially created scene. If the file contains lights and the
installation reports **Dynamic lighting is disabled**, the operator must enable
that feature or provide a file without lights.

If the connection fails, the server may already have completed the import. Keep
the same dialog open, leave the file and name unchanged and choose **Import
scene** again: the dialog reuses the operation's request UUID and the server
returns the original result instead of creating another scene. There is no
separate Retry button or automatic retry.

Changing either field or reopening the dialog starts a new operation. After
closing the dialog or reloading the page following an uncertain result, check
**Scenes** before importing again, to avoid creating a second scene.

## Export the current scene

If you are working in the Builder, first finish **Generate scene** or **Update
scene**. Automatic saving stores the project; exporting reads the native scene
already applied to the game, including its subsequent native edits. A saved
project or an unpublished draft is not the export source.

1. Right-click the scene in **Scenes** and choose **Export Universal VTT**.
2. Choose **Prepare export** and wait for preparation to finish.
3. Review the warnings, then choose **Download Universal VTT** to save a `.uvtt`
   file.

The prepared download is a snapshot. If the scene changes after preparation,
close and reopen the exporter to prepare a new copy. You can close the export
dialog while preparation is pending. Export does not modify the scene, project,
receipts or stored artwork.

### What the download keeps

| Content | Exported representation |
| --- | --- |
| Map background and visible scene images | One embedded PNG; individual image objects and materials become pixels |
| Dynamic floors and walls | Flattened with their current material, mask, opacity, rotation and layer erasure |
| Door artwork | Current appearance, including the open quarter-turn around an explicit start, center or end anchor |
| Grid and origin | Cell size and coordinate alignment; fractional pixel cell sizes are rounded and the raster resampled, with a warning |
| Walls and doors | Wall segments and portals reflecting current open/closed state |
| Enabled native lights | Position, color, intensity and range; cones, animation, elevation and unlimited ranges are approximated |

GM-only image artwork is omitted. Locks, secret-door presentation, height ranges
and separate movement, vision, light and sound barrier channels are not
preserved. A secret door's geometry can still be present: check the file before
sharing it with players.

Blueprints, variables, timers, presence regions, tokens, cards, markers, journal
permissions, particles, shaders, fog, drawings and audio are not transferred.
Disabled lights are omitted. The file does not restore a Builder project or
campaign state, and another application's interpretation may differ. Keep the
original project and use the installation's backup process for recovery.

If preparation fails, read the error before trying again. Missing or unreadable
background tiles and exceeded composition limits prevent a complete export;
the dialog does not offer a partial download.

## Format and coordinate contract

The accepted container is JSON with numeric `format: 0.2` or `format: 0.3`; the
three supported filename extensions use this contract. Export uses `0.2`.
These are interchange versions, independent of the Gravewright application version.
Import requires an
embedded, single-frame PNG or WebP image encoded as raw base64, not a data URL,
file path or remote URL. Image metadata is removed; EXIF orientation is not
applied to map coordinates.

| Input field | Interpretation |
| --- | --- |
| `resolution.map_size` | Positive width (`x`) and height (`y`) in cells |
| `resolution.pixels_per_grid` | Integral numeric pixels per cell (`70` and `70.0` are equivalent) |
| `resolution.map_origin` | Origin offset in cells; fractional values retain grid alignment |
| `line_of_sight`, `objects_line_of_sight` | Polylines split into consecutive native wall segments |
| `portals[].bounds` | Two endpoints defining the native door; collinear walls are cut around its opening |
| `portals[].closed` | Required boolean: `true` means closed, `false` means open |
| `lights[]` | Cell-based position and range, intensity, color and shadow setting |
| `environment` | Baked-lighting flag and ambient color |

Image dimensions must equal the rounded products of `map_size` and
`pixels_per_grid`. For example, a 20 × 15-cell map at 70 pixels per cell needs a
1400 × 1050-pixel image. Object positions become
`(point - map_origin) × pixels_per_grid`. Portal bounds determine door geometry;
portal `position`, `rotation` and `freestanding` do not add separate native
placement or behavior.
Portal cutting uses a separate bounded geometry adapter and tolerates producer
rounding up to 0.05 pixels when matching a collinear wall. It retains the original
door coordinates; walls beyond that tolerance are unaffected. Optional software and
creator labels are bounded metadata; they never become paths or executable data.

Colors accept six-digit `RRGGBB` or eight-digit `AARRGGBB`, optionally prefixed
with `#`. Light alpha multiplies the clamped intensity. For example, color
`80ff0000` and intensity `1` produce a red light with intensity approximately
`0.502`. Imported range becomes the dim radius, with a zero bright radius.

## Limits and authorization

These limits apply in addition to installation configuration:

| Resource | Limit |
| --- | --- |
| JSON upload/download | 64 MiB |
| Embedded compressed image | 48 MiB |
| Raster area | 16,777,216 pixels, or the lower configured map/Pillow limit |
| Native objects, including wall segments after portal cuts | 5,000 |
| Line-of-sight vertices | 20,000 |
| Wall/portal intersection checks | 2,000,000 |
| Floor composition groups during export | 32 |
| Cumulative export composition work | 134,217,728 pixels |
| Pixels per grid cell | Integer from 1 to 10,000 |
| Input light range / intensity | Finite, nonnegative, at most 1,000,000; clamped to native 200 cells / 1 |

Configured upload bytes, image dimensions and tile-count limits may be lower.
Duplicate JSON keys, invalid numbers or base64, unsupported or animated images,
inconsistent dimensions and excessive geometry are rejected. Uploaded filenames
never become server paths. Artwork used during export must belong to the
campaign; generated masks must also belong to that exact scene.

Players and streamers cannot import or export. Import rechecks GM membership and
folder ownership before committing, records a request receipt and removes newly
stored tiles if the operation fails. The same request UUID with the same file,
name and folder replays the original result; a changed payload with that UUID is
rejected as a conflict. Import through the public interface never activates the
new scene for players.

## HTTP contract and implementation checks

- `POST /api/containers/{campaign}/universal-vtt/import`: multipart `file`,
  `name`, `request_id`, optional `folderId` and optional string
  `builderEditable: "true" | "false"` (default false); returns
  `{scene, warnings, builderEditable}` and `project` when editable. The mode is
  included in the receipt fingerprint; scene/project/file creation rolls back together.
- `GET /api/maps/{scene}/universal-vtt`: returns
  `{filename, document, warnings}`. `document` is the downloadable UVTT JSON.

The service is [universal_vtt.py](../../gravewright/maps/universal_vtt.py), with
GM-only [HTTP views](../../gravewright/maps/universal_vtt_views.py) and the
[import/export dialog](../../gravewright/maps/static/gravewright_maps/universal-vtt.js).
[Focused tests](../../gravewright/maps/tests/test_universal_vtt.py) cover geometry,
grid/ARGB conversion, current artwork, receipts, rollback, isolation and limits.
The [browser scenario](../../tests/e2e/map_builder_universal_vtt.py) covers the
public modals, a lost-response retry, downloads, round trips and role boundaries.
Use the isolated environments described in [Testing](testing.md).
The shared [scene adapter](../../gravewright/maps/builder_import.py) is also used
by **Edit with MapBuilder**. Its [integration tests](../../gravewright/maps/tests/test_builder_import.py)
cover scene identity, native edits, cloning and rollback; [validation tests](../../gravewright/maps/tests/test_builder_import_validation.py)
cover exact bounds, image scale, native-only properties and bounded query work.
