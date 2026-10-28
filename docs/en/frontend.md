# Frontend architecture

[Documentation index](../README.md) · [Português](../pt-BR/frontend.md) · [API reference](api.md)

The application renders Jinja2 HTML on the server, uses Datastar for reactive signals and fragment updates, and runs JavaScript controllers for interactive workspaces. The game board uses PixiJS and a separate source/build pipeline. There is no single application-wide SPA build step.

## Follow a page from its template

[`base.html`](../../gravewright/web/jinja2/gravewright_web/base.html) loads the shared stylesheet, vendored Datastar, and `gravewright_modules/frontend-api.js`, which creates `window.gravewright`. The `/inside` workspace and game table extend that shell. [`table/page.html`](../../gravewright/table/jinja2/gravewright_table/page.html) composes feature templates and loads table, map, journal, actor, dice and module controllers.

Useful areas to inspect:

| Location | Purpose |
| --- | --- |
| `gravewright/web/jinja2/` | Shared shell, Inside pages and reusable HTML |
| `gravewright/accounts/jinja2/` | Authentication and initial account setup templates |
| `gravewright/web/static/gravewright_web/css/` | Design tokens, base styles and component classes |
| `gravewright/web/static/gravewright_web/inside/` | Inside account/campaign/admin controllers and styles |
| `gravewright/web/static/gravewright_web/windows.js` | Movable/resizable window behavior |
| `gravewright/table/static/gravewright_table/realtime.js` | Socket connection, subscriptions, authenticated fragments and event dispatch |
| `gravewright/modules/static/gravewright_modules/` | Public browser API, signed-module runtime, transport and lifecycle |
| `gravewright/maps/frontend/` | Editable board, wall, token, lighting, selection and tool sources |
| `gravewright/maps/static/gravewright_maps/workspace.js` | Native map workspace integration |
| `gravewright/pdf_system/frontend/` | Editable PDF mapping/controller sources |
| App-specific `jinja2/`, `static/`, and `messages.json` | Domain UI, styling and text catalogs |

Templates carry IDs and `data-*` attributes that native controllers and extension surfaces depend on. Changing one may affect the corresponding controller, Datastar signals, and module attachment. Check all three before renaming selectors or replacing an entire panel.

`modules/static/gravewright_modules/domain-api.js` exposes the generated domain
contract to pages and leased modules. `file-api.js` keeps file bytes in multipart
requests and returns authenticated blobs; `global-api.js` owns account, campaign,
administration and package adapters on the page lifetime. These adapters preserve
caller cancellation and native permission checks. See the [extended public API](api.md)
for MapBuilder, blueprints, ownership, library files and system-owned operations.

### Manual PDF fields

For the complete player/GM workflow, see the [PDF System guide](pdf-system.md).
This section identifies the implementation and its validation boundaries.

In a Gravewright PDF System character sheet, the GM can open a PDF and choose
**Map fields**. Select text, number, checkbox or multiline text, then drag a
rectangle over its area on the page. **Add field** creates a rectangle with the
keyboard. Select a rectangle to rename it, change its percentage bounds, drag it
or resize its lower-right corner. Arrow keys move the selected rectangle one
display pixel (Shift: ten); Delete removes it and Escape cancels a gesture.
**Finish mapping** returns to filling the sheet. Changes save automatically.

Mappings belong to that actor or independent token copy, PDF source and page.
They stay aligned through zoom and spread changes and coexist with native PDF
form widgets. Authorized players can fill the fields; only the GM can change
their definitions. The overlay leaves the original PDF file unchanged, including
when downloading it. Deleting a rectangle retains its stored value. Number and
single-line text fields can also be chosen for token bars.

`pdf_system/frontend/manual-fields.js` owns stable identities and normalized
display-page geometry; `frontend/controller.js` combines manual definitions with
native widgets. `static/gravewright_pdf_system/manual-editor.js` owns gestures,
selection and disposal. `pdf_system/manual_fields.py` validates at most 256
definitions across sources, page bounds, names, types and values, and enforces
GM-only layout changes through the normal sheet-save service. Omitted layouts
are preserved for older clients. The generated controller follows the existing
map asset build pipeline.

The GM can double-click a native or manually mapped field, or focus it and press
F2, to open **Field actions** in the existing application modal. Choose a token
value, enter a roll formula and label, or use one of six presets: d20, highest or
lowest of two d20s, 2d6, exploding d6 and 4dF. `@value` references that field's
current numeric value; an empty value is zero and checkboxes use zero or one.
Formulas without `@value` also work on text fields. Clear the formula to remove
the roll action. Assigning or removing a token-bar binding preserves the field's
current value. Saving validates the complete candidate before updating the
displayed sheet; Cancel and Escape discard the draft.

Saved roll actions appear as buttons above the PDF for authorized editors.
Players can also double-click a configured field; Alt+Enter rolls a focused
field. The GM's double-click continues to open configuration, where **Roll saved
action** executes the saved formula without applying the draft. Rolls use the
native [dice notation](../../gravewright/dice/grammar/notation/GRAMMAR.md),
publish to chat in the current scene context and retain normal request receipts
and reconnect retries. Configuring an action consumes no randomness.

`pdf.fieldActions` is optional and holds up to 256 source/field-bound roll
definitions with a 512-character formula and a 48-character label. The server
compiles formulas using the dice parser and compiler, preserving omitted actions
and rejecting changes by non-GMs. `frontend/field-actions.js` builds isolated save
candidates, preserves canonical bar values and expands the bounded numeric
`@value` reference. `static/gravewright_pdf_system/field-actions-editor.js` owns
the modal's draft and disposal.

**Reference field** inserts `@{field-key}` into a roll or calculated formula.
The picker shows readable names; manual keys remain stable when fields are
renamed, and native PDF references retain their exact form-field name. Braces
and backslashes in native names are escaped by the picker. Reference values are
numeric and limited to the existing ±1,000,000 range. **Calculated value
formula** accepts deterministic arithmetic, comparisons and the native numeric
functions, with references to other fields. Clear it to return to ordinary
editing. Calculated controls are read-only and update in dependency order.
The server recomputes results on every sheet save, rejects circular references
including aliases through token bars, and retains the previous canonical result
when an input is temporarily nonnumeric or a calculation cannot execute.

`pdf.fieldBindings` records validated original field addresses for references;
bar overrides resolve against the current token mapping. Only the GM can change
bindings or `pdf.calculatedFields`. The server's `formulas.py` and
`calculated_fields.py` own validation and authoritative calculation;
`frontend/formulas.js` mirrors the deterministic subset for immediate feedback.
Archived field values and bindings remain available after removing a rectangle;
diagnostics identify references whose visible field has disappeared.

While mapping, Shift/Ctrl-click or drag a selection rectangle to select multiple
fields on a page. The layout toolbar supports copying, pasting, duplication,
six alignments, horizontal/vertical distribution and optional snapping to a
five-point grid. Ctrl+C/V/D and Ctrl+Z/Shift+Z provide the same operations. The
toolbar is inside **Layout tools**, initially collapsed in narrow sheet windows
and expandable by keyboard or touch. Each gesture is one history step, limited
to 50 steps in the active PDF. Undo restores
definitions while retaining current character values; switching documents clears
the history. Copies receive new UUIDs and remap formulas inside the selection.
`frontend/layout-editor.js` owns geometry and `layout-history.js` owns definition
snapshots and clipboard identities.

**Mapping library** opens campaign templates for GMs. Save or replace the current
mapping, apply a template to the current sheet or selected actors, and import or
export versioned JSON. Templates contain rectangles, actions, calculations,
bindings and optional document geometry, without PDFs, character values, names
or media. Existing values are retained by field identity and canonical bars;
templates do not merge unrelated fields by their visible labels. Independent
token snapshots retain their own layouts unless explicitly applying a template
to that open snapshot. Batch application validates all actor revisions before
committing any changes. Stable manual IDs already used by another PDF in the
same sheet cause a validation error rather than reassigning that PDF's fields.

`MappingTemplate` and its initial migration belong to `pdf_system`. The
`/api/containers/<id>/pdf-mappings` routes enforce GM and campaign boundaries,
revision checks and operation receipts. Limits are 128 templates per campaign,
100 actors per batch and 1 MB per JSON import, in addition to sheet limits.
Campaign archives include the templates and validate their portable bundles on
restore. Template changes require a new application to update a character.

**Filled PDF** downloads a separate flattened copy of every PDF page with the
current field values, including repeated native widgets across pages. It renders
through the bundled PDF.js at 144 dpi and writes
JPEG page images in a minimal PDF container, preserving Unicode text as rendered
by the browser. The original remains available separately. The copy contains no
editable widgets or executable PDF content. Export rejects text that cannot fit
its rectangle, excessive page/image complexity or a result over 100 MB, and
downloads only after every page succeeds. It supports at most 100 pages,
16 million pixels per page and 128 million pixels per operation. Closing or
switching documents cancels the work. The container follows the image-XObject
and byte-offset structure of [ISO 32000-1](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf).

The **PDF mapping diagnostics** button checks missing fields or references,
calculation errors, absent pages and differences from saved document size,
rotation or fingerprint. `pdf.sourceMetadata` keeps the expected document
descriptor when applying a template; opening a PDF does not silently replace it.
Diagnostics use authored labels as text and provide navigation to fields that
are still present. Export and diagnosis never modify the original PDF.

`node --test gravewright/pdf_system/frontend/*.test.js` covers the field model;
`manage.py test gravewright.pdf_system.test_manual_fields` covers persistence and
authorization. The isolated browser scenario
`tests/e2e/pdf_manual_fields.py` exercises drawing, filling, navigation, native
widgets, token copies, roles and Translator in English, Portuguese and Spanish.
`manage.py test gravewright.pdf_system.test_field_actions` and
`tests/e2e/pdf_field_actions.py` cover roll configuration, bar-value preservation,
chat delivery, cancelled/invalid drafts, permissions and responsive translated
modals.
`manage.py test gravewright.pdf_system` also covers templates, calculations,
metadata and campaign archive round trips. `tests/e2e/pdf_workbench.py` exercises
the combined workflow and parses/renders the generated PDF with PDF.js.

### Map Builder workspace

`GET /game/<campaign_id>/map-builder` renders
[`maps/builder.html`](../../gravewright/maps/jinja2/gravewright_maps/builder.html)
through `maps/builder.py`. It checks current GM membership and validates the
optional `folder` query against that campaign. The new-scene chooser performs
normal same-tab navigation; the builder uses the base shell with its own
`static/gravewright_maps/builder/` controllers, without mounting table runtime,
scene subscriptions or the table workspace. Native effects use the dedicated
preview described below.

The table's scene directory reads the optional `builderProjectId` from the GM
projection of `maps.services.state()`. It is resolved in one campaign-scoped ID
query from the project's current scene link; non-GM projections do not include
it. Linked scenes keep the same compact row and map icon, colored with `--danger`,
and add **Edit with MapBuilder** beside the normal edit action in the context
menu. Shift+F10 or the context-menu key opens the menu from a focused scene.
Menus render in the directory's document, including detached windows; the edit
action opens the editor in the main game tab. The project endpoint
rechecks GM membership and campaign ownership on load.

`native-effects.js` is a builder adapter to the same light, particle and shader
catalogs as the tabletop. Its small eager `builder-catalog.js` bundle supplies
presets without starting WebGL; `builder-native.js` loads lazily for visible
sources. The editable entries are `frontend/native/builder-catalog.js` and
`frontend/native/builder-preview.js`. The latter reuses `PixiBoardRenderer` and
`SceneLayers` on a transparent overlay synchronized to the SVG camera and wall
geometry. Hidden/empty layers, page hiding and disposal release rendering and
animation resources. Native effects remain separate from the generated raster.

`frontend/native/builder-editors.js` hosts the same `LightEditor` and
`EffectEditor` widgets used by the game against a detached builder draft. Its
`builder-editor-model.js` adapter maps the builder's light radius names and
resolves compact preset references for GLSL editing without expanding an
unchanged source. Transactional widget footers are enabled only in this host;
the game's existing autosave behavior remains available to its normal host.
Draft validation and preview never call scene commands. Saving returns one
candidate to `workspace.js`, which checks editability and commits one project
history step. Cancel/close disposes preview timers, shader validation and any
nested prompt, preserving the project and live scene.

`static/gravewright_maps/wall-editor.js` and the `wall_editor.html` template
share the wall configuration window with the table's wall controller.
Its builder host writes optional native presentation, channel, elevation and
discovery settings to the source wall/door. Door and lever Smart Object behavior
windows remain separate from physical wall configuration.

`builder/torch-model.js` binds a decoration to native light/effect source rows.
Mechanism state and flame illumination are independent; preview projects the
mechanism's quarter turn and gates enabled components without rewriting source
coordinates. `model.js` expands composed selections once for transforms and
duplication, while `object-removal.js` reconciles ownership and Blueprint light
references atomically. Component editor buttons reuse `builder-editors.js` and
retain the selected parent. On the table, `lever-controls.js` hosts both lever
and torch interactions, and `image-components.js` projects linked render nodes
through image/selection previews without recreating GPU resources. The domain's
`torches.py` validates scene-local ownership, applies authoritative transforms
and flame gating, and keeps native group operations within map transactions.

Entry is read-only. The Studio's `workspace.js` composes the editor controllers,
navigation and drawing gestures. Its directly served sibling modules own these
boundaries:

| Module under `static/gravewright_maps/builder/` | Responsibility |
| --- | --- |
| `project-persistence.js` | Draft recovery/storage, HTTP/CSRF, receipt identities and the save queue |
| `workspace-library.js` | Campaign asset catalog, brush choices and material controls |
| `workspace-import.js` | Asset import/edit modals and their listener lifetime |
| `inspector-controller.js` | Shared selection fields, section modals and region/torch configuration |
| `object-menu.js` | Object context menu, keyboard navigation and model submenu |
| `interactive-presets.js` | Configurable generic object Blueprints and their catalog modal |
| `shader-control.js` | Typed shader property controls shared by Blueprint editing, simulation and logs |
| `layer-controller.js` | Layer controls, contents, selection and drag listeners |
| `productivity.js`, `productivity-model.js` | Grouping, atomic arrangement, campaign object bundles, area guides and object strokes |
| `player-test.js`, `player-test-model.js` | Detached player rehearsal, area crossings and rollback-only behavior requests |
| `canvas-renderer.js` | SVG artwork, selection overlays and disposable terrain/wall caches |

Controllers receive explicit state and callbacks rather than importing the
workspace or sharing globals. Persistence tests import its public factory;
they do not extract function text from `workspace.js`. A disposed save owner
cannot write a late acknowledgement over a recovered draft.
`model.js` owns cell-space geometry and undo history, and `viewport.js` owns the
independent SVG camera. Camera listeners, pointer capture,
requests and resize observation end on `pagehide`; history restoration remounts
the editor. `builder_services.py` owns campaign-scoped project revisions, retry
receipts, validation, scene generation and updates. See [Map Builder](map-builder.md) for
the source schema, native geometry and raster boundaries.

`newDocument()` creates one empty, generically named layer with a fresh UUID;
the controller localizes its initial **Layer 1** name. It creates no layers by
object type. Schema-3 normalization preserves authored layers, including an
empty layer list after removing the final empty layer. The server accepts that
list only with no objects, and empty-map generation renders just the background.
Version-1/2 upgrades retain their existing Base-layer conversion.

All element kinds accept an authored `name` of up to 120 characters. Optional
names stay omitted on unnamed legacy rows; regions and shaders retain their
required names. The inspector supplies the existing Empty Object label for
older unnamed controllers. `element_names.py` validates type, whitespace,
length and NUL at the server boundary. Native edits, scene generation and linked
updates preserve labels without replacing UUIDs or Blueprint targets. Static
floor artwork remains baked; a dynamic surface carries its source name on the
native image. The Selection inspector owns one name field per selected element,
and layers, behavior catalogs and light/door choices prefer authored labels.

The library's persistent tool strip exposes its additional controls through
`data-builder-dock-tool`; existing panel tool selectors remain distinct. Tool
changes flush the focused property before returning focus to the canvas. The
strip scrolls independently on narrow screens and keeps a stable layout when
the native light/effect library replaces the asset cards.

The header mode selector honors optional `editingMode: "tiles" | "paint"`;
omission defaults to Tiles without changing the source. Tiles and terrain
Painting share layers, native objects, camera and project history. Existing
`floor.paint` color/opacity still renders independently through SVG and the
raster, multiplying shape coverage, texture alpha and opacity. Selecting the
new terrain brush does not reinterpret those earlier styles or convert existing
geometry. Floors retain their layer and transform contracts.
SVG and Pillow use different antialiasing at coincident contour/cut boundaries;
pixel comparisons keep interiors exact and isolate that subpixel boundary band.

`floor-painter.js` owns transient floor gestures and commits one complete edit.
`model.js` supplies swept brush footprints, family-aware flood fill, material
sampling and atomic floor subtraction. `floor-geometry.js` supplies continuous
contours and excluded cuts when snapping is disabled, along with shape-aware hit
testing and source/raster budgets. The server validates the same optional floor
shape contract and rasterizes its union-minus-cuts mask with bounded antialiasing.
Preview fragments retain stable UUIDs;
no-op strokes do not consume undo steps. `layer-model.js` counts layer contents
and moves or merges them while preserving object identities and paint order.
Layer duplication reuses atomic object duplication with an exact one-cell
offset on both axes, new IDs and remapped internal Smart Object references.
Bounds, global door overlap and project limits can reject the entire copy.
Isolation is an editor filter; project visibility and native generation retain
their existing semantics. Drawing controls belong to the auxiliary panel's
**Tools** tab, leaving the canvas space available when the panel is closed.

The **Panels** launcher opens the drawer's six linked tabs in a three-column
grid. Each tab retains its own scroll position; the heading and tabs stay visible
above the scrolling content. Arrow keys, Home and End navigate the tabs, while
closing the drawer returns focus to its opener. Active brush settings precede
the compact tool palette, and detailed brush help is a separate disclosure.
Panel navigation and scrolling do not change the saved project or its history.

Tiles repainting compares the topmost floor material before replacing coverage.
An unchanged cell or completely matching free stroke retains its source rows
without rerolling eligible family variants or adding history. Coverage accounts
for the union of several floors and their cuts; another material above them
blocks a match. Snapped gestures filter matching cells independently. Mixed free
gestures replace their complete footprint, keeping geometry outside it. Coverage
proofs have a bounded geometry work budget and reject atomically when it is
exceeded. Terrain Painting uses its own radial brush representation rather than
the earlier flat `floor.paint` opacity composition.

### Map Builder terrain painting

`terrain-painter.js` owns a transient circular gesture, distance-spaced dabs and
50 ms stationary accumulation. It commits one `floor.brush` row per completed
gesture and clears its timer on cancel, completion and disposal. The workspace
owns pointer capture, shared brush size, mode controls, history and rendering;
switching tools or modes cancels an active stroke. Tiles continues using
`floor-painter.js` and its existing no-op and replacement semantics.

`terrain-brush.js` and `maps/terrain_brush.py` evaluate the same radial kernel at
absolute raster pixel centers. Hardness defines an inner plateau with linear
falloff to the radius; dab alpha accumulates with bounded integer source-over
rounding. The source stores local normalized points, horizontal/vertical radii,
hardness and paint/erase operation in the floor box. Texture sampling retains
the existing map-space phase and rotation, while the brush supplies coverage.

An erase row applies destination-out only to earlier floors on its own layer.
SVG nests the accumulated layer under its mask; Pillow keeps a separate RGBA
surface for that layer. Later paint is outside the earlier eraser's scope.
Merging an upper layer with erasers into a lower layer containing floors is
refused, retaining that isolation.
`terrain-render.js` caches disposable alpha-mask images by source signature and
releases them on pruning/disposal; they are not campaign image assets. Limits
bound dabs per stroke/document and the actual per-dab pixel work before raster
allocation, and reject an oversized operation atomically.

The [Dungeondraft TerrainBrush reference](https://megasploot.github.io/DungeondraftModdingAPI/reference/TerrainBrush/)
and [Terrain reference](https://megasploot.github.io/DungeondraftModdingAPI/reference/Terrain/)
informed the separation between brush size/intensity and the terrain surface.
Gravewright implements and persists its own radial brush contract.

Shift and a left-button drag resize the floor brush using horizontal screen
distance (40 pixels per cell). The anchored live guide follows Tiles snapping
or the continuous terrain radius. Completion updates only editor preferences;
Escape restores the previous size without a source/history write.

`builder/region-model.js` authors named rectangles in cells and the explicit
door pressure-plate preset. Regions share selection, layers, duplication and
project undo, but are absent from the raster and player preview. `regions.py`
derives private occupancy from validated token commands in their transaction;
`zones.py` establishes a silent baseline for authored edits. The native
`features/regions` modal displays GM state/count and edits zone settings.

`blueprint-editor.js` edits a door, lever, torch or region's private draft through the shared `mountModal`
helper; `blueprint-model.js` validates connections and simulates the selected
event locally. The editor is native DOM/SVG without a graph library: nodes stay
focusable elements on a translated and scaled plane, and native scrolling caused
by focus is folded into that camera. Its own undo history covers only the open
draft and ends with the modal. Saving applies one undo operation to the project. Generated doors
keep the native `door_state`, while lever images keep `lever.state`;
`blueprint_runtime.py` executes effects inside the
existing map command transaction and receipt, which also records a GM-only
run for `automation-log.js`, the table's Automation window. Lights and sounds use their current
domains and realtime transport. Audience projections include only the active
appearance, keeping graphs and inactive images private to the GM.

`blueprint-templates.js` captures campaign-owned reusable snapshots, replacing
only typed resource fields with bindings and exposing allowlisted scalar
parameters. Applying a resolved copy is one draft undo operation; it creates
no live dependency on the template. `scene-network.js` derives relationships
from these same element-owned graphs, renders at most 40 cards per page and
opens their existing editor. `blueprint_network.py` saves native rules with
object/project revisions and a payload-bound receipt, atomically translating
owned references back to the Builder source. The overview never executes rules.

`builder_dynamic.py` promotes explicitly marked floors/walls to masked native
image planes, leaving ordinary maps baked. Ordered paint/erase groups preserve
floor alpha; `surface-material.js` samples replacement materials in the original
texture frame and `surface-group.js` composes them on invalidation, outside the
frame loop. Generated images belong to their scene and stay outside the asset
library. Visibility and material actions mutate runtime state without creating
files. Limits bound promoted surfaces, generated pixels, bytes and cache work.
Preparation serializes dynamic/base raster work and releases each PNG buffer
after storing an operation-owned artifact, before opening the write transaction.
Repeated wall-material actions share a bounded request-local crop cache.
Archive import validates the new surface metadata, aggregate buffer budgets and
scene ownership of generated artwork/masks. Asset delivery enforces that ownership
again for non-GM viewers; the renderer budgets all group buffers before allocation.

`blueprint_world.py` validates presentation audiences and same-scene transport
inside the existing command transaction. Recipient-filtered
`automation.presentation` events are sent after commit and rechecked at delivery.
`automation-presentation.js` displays authored text with `textContent`, opens the
native journal window and deduplicates recent event IDs. Camera focus applies
only to the viewed scene and requires a per-profile/device preference, off by
default. Teleport uses the original authenticated trigger token, validates a
free whole-token footprint inside the destination region and queues arrival
presence after the current object cache is persisted. A durable arrival gate
prevents return loops until the token leaves the region; scene navigation and
party membership are unchanged.

Uploaded **Object** artwork can become a Smart Object directly: choose **Edit
nodes** in its context menu or **Smart object** in its Behavior properties. A
left-button double-click also opens the editor with either Selection or Objects
active, without placing another object. Dragging still uses the active tool.
The first opening creates
a blank Blueprint with inherited artwork; it preserves the object's identity,
image, layer and geometry. Author states and nodes freely, then use the existing
autosave and scene generation workflow. Reopening an existing Smart Object keeps
its authored behavior. Ready-made models remain optional.

The **Interactive object catalog** in Builder selection, **Ready-made models**
in the object context menu and the node editor's **Object catalog** share 14
editable generic lever Blueprints. Models cover switches, chests, secret
passages, books, altars, warning traps, bells, pressure plates, dice requests,
quest activation/completion, entrance signs, timed switches and door buttons.
The configuration modal offers optional sound/volume and active-state artwork;
unchecked options produce no sound node or image override. State artwork comes
only from Object assets and restores the original artwork while inactive.
Applying a model keeps object identity and geometry; replacing authored behavior
requires confirmation in the application modal and can be undone. The trap warns
on entry while armed; it does not apply system-specific damage. The inspector's
Behavior choices open the same configuration modal. Property section modals
reuse the inspector controls and save through its existing commits and history.

Blueprint V2 `requestRoll` stores a validated dice `expression` (up to 512
characters), `label` (up to 48), `visibility` (`public` or `gm`) and `audience`.
Audience controls offer the triggering user, all players, one player or chosen
users. One player persists as the compatible `users` scope with one UUID.
Authorized recipients receive a native modal and explicitly choose **Roll**;
the normal server dice service validates and posts the result to chat. The event
UUID identifies the same logical roll per user across retries and tabs, and the
originating scene stays fixed. Streamers cannot receive roll requests.
The action continues immediately: it does not branch on a roll result.

**Open journal** uses the existing `showHandout` contract for diaries, quests and
quest boards, without granting reading access. `setQuestStatus` stores a quest
`journalId` and one of `draft`, `available`, `active`, `completed`, `failed` or
`archived`. The server validates campaign/type and applies the fixed GM-authored
action through the journal service within the map transaction; players do not
gain journal edit permission. Rehearsals report quest changes and roll prompts
without persisting journals or delivering player windows. Templates, delayed
references and archives preserve these bindings and authored roll labels.

Blueprint V2 `all`/`any` are pure Boolean values with inputs `a`–`d` and `result`.
Connected inputs evaluate in fixed order without short circuit; fewer than two
returns False. Shared nodes are memoized only within the current event. Both
Python and JavaScript enforce Boolean wires, one source per input and graph
cycle/size limits. The palette groups the nodes under Logic, and the card shows
connected-input count; simulation and the GM log display evaluated results.

Blueprint V2 `elementGroup` is a pure typed ordered set: `name` (1–80 characters),
`memberType` (`element`, `light`, `sound`) and 1–32 unique UUID `targetIds`.
Its `targets` output becomes `elementset`, `lightset` or `soundset`.
`lightReference.targetId` outputs `light: light`; `soundReference.trackId` outputs
`sound: sound`. Legacy `reference` retains its `door: element` output ID and also
addresses ordinary live images, whose state is null. Baked walls/floors remain
outside this contract. `acceptsDataType(port, type)` handles `acceptedTypes` on
Target ports: element actions accept an element/set, light and sound actions
their corresponding resource/set, transforms an element/light or either set.
Get property remains single-element. A connected Target overrides the legacy
resource binding or Self; stale UUIDs stay connected and are skipped/logged,
never silently redirected. Group order is explicit and each expanded action
counts against the existing action budget.

`move` stores finite `dx`/`dy` offsets in cells, each bounded by ±1,000; `rotate`
stores finite relative `degrees` bounded by ±36,000. `blueprint_actions.py` uses
native image, door, light and region validators inside the command transaction.
Rotation uses each target's own center, and presence rectangles require multiples
of 90 degrees. Linked torch components follow the image. Authorized transforms
acknowledge owned geometry without changing the source; scene update reapplies
authored transforms, preserving conflict protection for unrelated manual edits.
`setInteraction.enabled` and `setRegion.enabled` are strict Booleans. The former
gates direct player requests and pointer/keyboard/torch-flame controls while GMs
retain manual override; it does not gate authored automation. The public native
projection carries `interactionEnabled`; omitted authored flags retain the enabled
default. Runtime interaction flags survive update while their authored defaults
are unchanged; an explicit authored change wins. Runtime region enabled state
is preserved while source enabled/layer settings stay unchanged; authored changes
win and quietly baseline occupancy. Native copies and campaign archives retain
configuration; UUID remapping touches typed references/group members, not authored
scalar strings. Deleting a legacy resource action bridges only execution edges;
data wires never become execution wires, and stale new refs/groups remain inert.

Archive import uses `remap_omitted_bindings` for new sound references/sound-group
members and presence-filter actor/token IDs when their records are omitted.
A model/UUID lookup allocates one fresh inert UUID per missing identity and reuses
it in project documents, native data and generation manifests. Imported links
remain inert until replacement resources are chosen; names, event/group labels and authored scalar
text are preserved, including text that happens to resemble a UUID.

`eventContext.property` selects a readonly typed `value`. Text properties are
`event`, `sourceId`, `userId`, `userName`, `tokenId`, `actorId` and `presence`;
`count` is an integer from 0 to 1,000,000, `hasToken` is Boolean, and `state`/
`previous` carry State. `blueprint_context.py` builds original trigger metadata
from authenticated users and validated region/token objects. Signals and durable
jobs preserve it. Event/state/previous are always set by the evaluator for the
current graph snapshot; Delay keeps its saved snapshot, while Timer takes fresh
event state with the original trigger metadata. Missing token/actor IDs are empty,
count defaults to zero and hasToken derives from token presence. Arbitrary
payload/role fields are rejected. The optional `context.eventContext` simulation
fixture is private preview data and cannot write server identity or trigger effects.

Presence filters live in optional source `region.filters` and native
`zone.region.filters`: `tokenIds`/`actorIds` (up to 64 unique UUIDs each),
`dispositions` (`friendly`, `neutral`, `hostile`, `unknown`) and `visibility`
(`any`, `visible`, `hidden`). Lists are OR and criteria are AND; empty lists do
not restrict. Hidden state is the token flag, independent of ownership or vision.
The pure shared `static/gravewright_maps/region-filters.js` is re-exported by the
Builder and native region models. `normalizeRegionFilters` fills editor defaults
without mutating source; omitted filters remain omitted in legacy documents.
Server `regions.py` validates identity ownership and computes occupancy/events
from accepted token commands. Configuration or runtime region enable/transform
changes quietly baseline occupancy, suppressing synthetic presence events.
Disabling presence does not cancel unrelated named signals or scheduled work.
Objects can opt into a circular activation area in the Builder's Behavior
properties. `decoration.presenceRadius` is a radius in cells (0.05–200), converted
to native image `presenceRadius` in pixels. The circle follows the object's
center independently of artwork size and rotation. A selected object's circle
and drag handle are editor guides; the radius is private to GMs and is never
baked into the map image. Wire `presence:enter` or `presence:exit` to run effects
on committed token crossings without clicking. Omitting the radius retains the
existing oriented artwork box; changing the area quietly rebaselines occupancy.
The native editor uses the current scene token catalog and a cancellable GM
actor-catalog request, discarding late work on close. Filter configuration and
occupant identities remain private.

Blueprint V2 also implements `getVariable`, `setVariable`, `compareValue` and
`emitEvent`. Variable nodes store `scope` (`element`/`scene`), `name`, `valueType`
(`boolean`/`number`/`text`) and a typed `default` or `value`; comparisons store
`valueType`, `operator` and `expected`. `dataInputs`/`dataOutputs` derive the Value
port type from the node. Retyping removes incompatible wires in one undo step.
`signal:<name>` graph keys are named receiving events; emitters queue them for
Self, an Element Target or listeners in the same scene. Signals carry no payload.
Graphs remain version 2, without top-level variable declarations or runtime memory.

`blueprint_variables.py` validates names, types, definitions and private stores:
64 entries per scope, ASCII names up to 64 characters beginning with a letter,
finite numbers bounded by ±1,000,000, text up to 256 characters and 16 receiving
graphs per blueprint. Element stores use `SceneObject.data.automationVariables`;
scene stores use `Scene.settings.automationVariables`, both `{name: {type, value}}`.
Type conflicts reject a command rather than coercing saved values. Each event
reads one initial snapshot; queued assignments are visible to the next event,
including signal receivers. Failures roll back memory and other effects together.

`simulateGraph` accepts an optional sixth argument
`{variables: {element: {...}, scene: {...}}}`. It validates private preview memory
and returns assignments/emissions as actions without writing it or executing
receivers. The modal's Simulation variables controls configure only this preview.
The GM-only automation response includes `variables`, and its Variables view can
send `automation/reset-variable` through the normal command service with scope,
name, optional `elementId` and the displayed `{type, value}` as `expected`.
Reset compares that entry, removes only it and triggers no graph; conflicts need
a refresh. Standard scene, player and streamer projections omit private stores.
Linked updates and campaign archives preserve runtime memory, while native
element duplication clears its own store without clearing shared scene memory.

Blueprint V2 `switch` and `random` are execution controls with dynamic ports,
without per-node `automationMemory`. Switch stores `valueType`, typed fallback
`value` and one to four exact `{id, value}` cases. Case IDs are unique members of
`case1`–`case4`, and case values are unique within the selected Boolean/number/text
type; Boolean permits at most two. Scalar limits match variables. Value input
type derives from `valueType`. Strict equality selects one configured case ID or
`default`, using the fallback only when Value is disconnected. Connected reads
use the event snapshot. Retyping resets values, prunes incompatible Value wires
and discarded cases in one undo step; removing one case preserves all surviving
IDs and their wires.

Random stores two to four `weights`: integers from 0 to 1,000 with positive sum.
Its ports are `branch1` through the configured count. The draw covers the total
weight of all configured outputs, including disconnected ones. A zero weight
cannot win; a disconnected selected branch ends the path without another draw.
`executionOutputs(node)` returns dynamic descriptors and `nodeOutputs(node)`
derives their IDs. Choice nodes execute once per graph traversal, and the result
`decisions` records selected port strings alongside existing Boolean decisions.
The GM log records Switch's input type/value/output and Random's output,
selected weight and total. Audience projections do not expose private choices.

The runtime derives each draw using an HMAC under the installation's private
server key over request UUID, root-event ordinal, chain draw ordinal, element, event and node ID,
then uses an isolated generator for the configured weight total. It does not
consume or reset process-global RNG state. A receipt retry does not execute
again; retrying a rolled-back logical command uses the same draw identity.
Delay continuations preserve selected outputs and the visited-node set; both
Delay and Timer carry the private `budget.randomRoot` and `budget.randomDraws`
ordinals across segments; legacy jobs default both to zero. Token movement and
actor/folder deletion keep the original command context, distinguishing separate
presence-event roots without resetting their sequence on nested calls.
Invalid private state is rejected,
and ordinary permissions, transaction rollback and chain limits still apply.
Authored Switch fallback/case values survive project generation, native copying
and archive reference rewriting as content, including UUID-like text.

Local `simulateGraph` accepts `context.randomDraw(nodeId, total)`, returning an
integer in `[0, total)`, or uses `Math.random` for this preview. Only reached
Random nodes sample; validation rejects out-of-range/coerced samples. Preview
choices do not consume the server's draw sequence, write runtime memory, execute
signal receivers or resume scheduled work.

Blueprint V2 `counter`, `once` and `cooldown` are execution controls with one
Input and `true`/`false` branches; they have no value ports. Counter's integer
`target` is 1–1,000,000; count increments before comparison and saturates at
1,000,000. Once stores only `true` after its first visit. Cooldown's finite
`seconds` is 0.1–86,400; an allowed visit stores integer UTC milliseconds
`now + ceil(seconds * 1000)`, and a blocked visit keeps its deadline. The runtime
supplies server time, while pure evaluation defaults to zero. Elapsing time
alone never starts an event; scheduled continuation uses the separate Delay node.

`blueprint_memory.py` validates and reconciles the private
`SceneObject.data.automationMemory` store, shaped
`{event: {nodeId: {type, value}}}` with at most 128 rows. Memory is distinct from
typed variables and belongs to one element. Removing an event/node or changing
its type prunes progress; parameter, layout and connection edits preserve it.
An edited cooldown duration takes effect at its next allowed activation, keeping
the current deadline. Progress participates in the command transaction and
receipt, so failures roll it back and retries do not repeat it. Linked updates
and campaign archives preserve it; native copies clear it. Audience projections
omit the store for every role outside the GM-only automation response.

`validateBlueprintMemory` and `reconcileBlueprintMemory` mirror those rules in
the pure model. `simulateGraph` additionally accepts `{memory, now}` in its sixth
argument, clones/reconciles that memory and returns `memory` and branch
`decisions` for control graphs. The modal's Persistent node preview inputs supply temporary
starting values for each simulation. The automation response's `memory.elements`
feeds the GM's Node memory view; `automation/reset-memory` takes `elementId`,
`event`, `nodeId` and the displayed `{type, value}` as `expected`. Reset compares
and removes that row without emitting events, with a refresh required on conflict.

Blueprint V2 `delay` is an execution control with Input and Next, finite
`seconds` from 0.1 to 86,400 and no value ports or `automationMemory` entry.
`simulateGraph` returns `delay: {nodeId, seconds}` at the first reached wait and
stops the entire remaining event traversal, including later Sequence branches.
Its trace includes the Delay and its actions include only preceding effects;
the browser neither schedules work nor simulates a continuation.

The server stores a private `AutomationDelay` checkpoint in the transaction that
commits the preceding effects. Its DFS pending stack, visited execution nodes,
memoized pure values and original event snapshots survive restarts, keeping
Sequence order and preventing replay at convergent nodes. State, previous state,
reference states and typed variables retain their original event snapshot even
when first read after a wait; control-node memory is read live on resume. Claim,
effects, completion and the continuation receipt commit atomically. Chain budgets
span every segment: 32 element operations, 256 scene-signal deliveries, four
operations per element, 1,024
actions and 32 timed resumptions. Delay and Timer share 64 pending jobs per scene
and 256 per campaign.
Resuming a continuation does not consume a new element-operation slot.

`blueprint_delays.py` validates semantic identity and referenced targets/resources,
rechecks current membership/access without promoting the original role, and records
cancellation/failure. Missing element targets used by the continuation cancel it;
missing light, sound or image bindings anywhere in the owning blueprint also
cancel it, even when used only before suspension. Blueprint behavior changes
cancel pending work;
x/y card movement does not. Scene pause preserves overdue work until resume. A server
background worker processes due rows independently of HTTP/browser activity;
no transaction remains open while waiting. Continuations are omitted from
campaign content archives and copies, and from audience projections.
The queue retains at most 50 finished rows per scene for private diagnostics.

The GM-only automation response's `delays` list feeds the Waiting view. A
normal `automation/cancel-delay` command sends `delayId` and displayed
`expectedDueAt`, compares that pending row and cancels without changing game
state or firing a graph. A conflict requires refresh.

Blueprint V2 `timer` is an execution control with Input/Next, no value ports and
no `automationMemory` entry. Its exact authored fields are `name` and `action`
(`start`, `stop` or `restart`), with finite `seconds` from 0.1 to 86,400 required
only for start/restart and absent for stop. Names use the signal/variable ASCII
format and are case-sensitive. `simulateGraph` queues a cloned timer action and
immediately follows Next; it never advances a countdown or runs its receiver.
Timers reached before a Delay remain queued, while those after it await the
server continuation. The modal hides duration for Stop and warns when the owning
blueprint has no `signal:name` receiving graph, without rejecting that draft.

`AutomationDelay` also stores timer jobs with `kind="timer"` and `name`. A
database constraint allows one pending timer per element/name; distinct nodes
and graphs on that element control the same named job. `control_timer` applies
actions in authored order within the command transaction. Start keeps an
existing row's identity, deadline, actor and budget; Stop cancels it without
emitting; Restart creates a replacement under the current event's actor and
budget. Each action continues the graph immediately. Capacity or later-action
failure rolls back timer operations with the other effects.

The same durable worker delivers expiry as a fresh `signal:name` on the owner,
reading current state, references and variables instead of a saved event
snapshot. A missing receiver completes without effects. Actor/access checks,
semantic-edit/resource cancellation, pause/resume, private projections and
archive/copy exclusion follow Delay's policy. Expiry effects, completion and
receipt commit atomically, retaining chain budgets across worker runs. Timer
expiry consumes an element operation; resuming a Delay checkpoint does not.
Both consume the shared 32 timed-resumption budget, and per-element limits bound
graphs that rearm timers. There is no repeating/global timer mode.

The GM `delays` projection marks timers with `kind: "timer"` and `name`. Waiting
renders named expiry rows and adds Stop timer and Restart timer controls. Stop
uses `automation/cancel-delay`; `automation/restart-timer` takes `delayId` and
`expectedDueAt`, checks the displayed pending row and creates a replacement due
after its stored duration. This GM restart preserves the original actor, role
ceiling and chain budget. Both controls require refresh on stale work and emit
no immediate gameplay event.

Lever decorations share the adapter registry and typed element references.
`features/images/ui/lever-controls.js` handles native double-click interaction
before mixed selection, with role/tool/layer checks, a pending-command guard
and listener disposal. Geometry/configuration edits do not run their graphs.

`floor-painter.js` coordinates freehand brush, rectangle, circle and polygon
gestures without registering events. It captures the document and brush options
at the start, then retains each cell's image and object ID across previews.
`model.js` enumerates the shape's cells and applies floor replacement atomically;
`workspace.js` handles input and commits each completed gesture once to undo
history. Cancellation or an object-limit failure preserves the source document.

The Studio has a full-width canvas and a horizontal asset library below it.
The existing auxiliary drawer's **Tools** tab contains the tool buttons, material,
brush settings, active layer and snap toggle. These controls retain their
existing `data-builder-*` hooks and listeners without duplicated DOM controls.
The header contains the quick map-name input, Select/Paint/Erase shortcuts and
a brush-size input, then undo/redo before the save status button, preview and
scene generation. The quick controls use their own hooks and share the existing
tool and brush state with Tools. Paint restores the freehand floor brush and
paint operation and selects the Floor library category; Erase retains whole-object
erasure. The size mirrors Tools and is enabled for the freehand floor brush,
including floor area erasure. It retains the snapped 1–20 and unsnapped
0.05–20-cell limits and bracket shortcuts. Selection retains Shift-click and box
selection. Preview and pending
requests disable these editing controls. The quick name mirrors Settings: Enter
or blur commits one history operation, Escape cancels the draft, and Ctrl+S
commits the current name before saving. History shortcuts remain Ctrl+Z,
Ctrl+Shift+Z and Ctrl+Y.
The library keeps search, import, collection and type filters accessible when its cards
are collapsed. Its initial Floor highlight shows all available campaign images;
choosing a Floor, Wall, Door or Object category also activates its drawing tool.
Choosing a native light/effect preset activates its placement tool. The material
selector in Tools follows the active brush and includes individual images, asset families
and its default appearance. Family cards also appear in the library. Import uses
the standard application modal to choose files, image type and an optional family;
double-clicking an image card opens its type and family editor. Lights
show placement instructions without becoming an image asset classification.
Panels, at the upper right of the canvas, opens the same auxiliary drawer with
tools, layers, selection, settings, projects and review. The drawer starts closed; selection and
painting do not open it. Closing that drawer leaves the library accessible.
Existing property and setup forms remain in these panels, and hidden legacy DOM
hooks preserve controller compatibility. Object properties stay in Selection;
this layout adds no properties modal. Components remains planned. Review shows
a summary, generation and the linked-scene update action. View controls and
dimensions in cells sit at the bottom of the canvas. Drawer,
library and view state belong to the editor rather than the project document;
they must not change the generated scene. Named project layers
are different: their order, names, visibility and locks are persisted in schema 3,
along with floor orientation, decorations, lights and project-local asset metadata.
Layer handles support drag reordering alongside the arrow controls. Expandable
contents lists select individual objects without changing the canvas layout.
The optional asset `family` field stays in schema 3; its members share one image
type. Floor painting saves a concrete `assetId` for each 1 × 1 cell, so preview,
undo/redo, reopening and generation preserve the chosen family variations.
Visibility and locking control hit testing and edits, but generation includes
every project layer. `model.js` applies group moves, duplication and rotation
atomically, retaining exact quarter turns and legacy door endpoints. Preview
disables editing, hides editing guides and
temporarily shows every layer, restoring previous visibility on exit. It does
not change the camera or the source document; save and generation remain available.
Rasterization contains floors and wall strips; native images, lights and door art
remain live objects. The layer order preserves the existing raster passes: all
floors precede all wall strips. Native objects retain their VTT rendering
contracts. Generation records resource ownership on the project. Updating
the linked scene replaces only those resources and its tiles, preserving manual
content and live door state. Project/scene revisions and original object data are
checked again in the write transaction; conflicting VTT edits stop the update.
The table reloads a history-cached document on `pageshow.persisted` because
its game renderer and module lifetimes have already been disposed.

### Map Builder wall networks

`builder/wall-edit.js` owns atomic node moves, splitting, extension and endpoint
connection on schema-three wall center lines. Shared nodes are derived from
coincident endpoints in one editable layer, regardless of material or thickness.
Adding or extending a wall onto an editable edge splits that edge to form a T
node. Doors remain independent source objects. Failed bounds, minimum-length or
resource checks leave the document and allocated fragment IDs unchanged.

`builder/wall-controls.js` owns pointer and keyboard gestures for the selected
wall. The workspace commits each finished operation once; cancellation restores
the pre-gesture document. SVG endpoint, midpoint and extension controls retain
their screen size as the camera zooms. Their focus targets are restored after
rendering; Preview, busy state and layer permissions disable editing. Armed
extension uses a separate preview marker and returns focus to the viewport.

`builder/wall-joins.js` and `maps/wall_joins.py` derive the matching artwork mesh
after door intervals are removed. Corners use a miter limited to four times the
larger half-thickness, with a bevel fallback. Compatible contiguous collinear
runs share a canonical frame; isolated walls keep their authored frame. Compatible
legacy collinear spans are deduplicated for rendering. A wall's polygons form one
coverage mask, preserving artwork alpha without applying it twice at its own
joins. Layers remain separate, and door openings are never bridged by a join.
The mesh is presentation data: source coordinates, IDs and native collision
center lines retain their existing persistence contract.

## Shared dimensions and design tokens

[`tokens.css`](../../gravewright/web/static/gravewright_web/css/tokens.css) defines the shared visual values. Fixed dimensional tokens use plain `px` values. Reuse existing tokens when they fit the component, and introduce a new shared value only when it is needed across components. The Fibonacci scale and its audit script have been retired; core CSS uses the spacing, radius and typography rules below instead of `--fib-*` or `--step-*`.

Use `--space-*` for padding, margins and gaps, including their shorthand, logical and row/column forms. When migrating a fixed length, choose the nearest value in this scale; on a tie, choose the smaller value. Preserve the sign of negative margins. The token suffix counts four-pixel steps, with separate names for zero, one and two pixels:

| Token | Value |
| --- | --- |
| `--space-0` | `0` |
| `--space-px` | `1px` |
| `--space-half` | `2px` |
| `--space-1` | `4px` |
| `--space-2` | `8px` |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-5` | `20px` |
| `--space-6` | `24px` |
| `--space-7` | `28px` |
| `--space-8` | `32px` |
| `--space-10` | `40px` |
| `--space-12` | `48px` |
| `--space-14` | `56px` |
| `--space-16` | `64px` |

The former `--space-9` value of 34px is replaced by `--space-8` at 32px. Border radii use these shared names:

| Token | Value |
| --- | --- |
| `--radius-sm` | `4px` |
| `--radius-md` | `8px` |
| `--radius-lg` | `12px` |
| `--radius-xl` | `16px` |
| `--radius-pill` | `999px` |
| `--radius-circle` | `50%` |

Host interface CSS must render text at **12px or larger**. Check effective sizes from inherited styles, relative units and font shorthands as well as explicit `font-size`. The existing `--text-3xs`, `--text-2xs` and `--text-xs` names remain available at 12px. Authored text in PDFs and drawings, and scene labels scaled by the camera, retain their authored sizes.

Widths, heights and other component geometry keep their required dimensions. A value specific to one component may use a local `px` literal; reserve shared `--size-*` tokens for values reused across components. Responsive geometry can still use relative units and layout expressions such as `calc()` and `clamp()` where needed.

### Form controls

The shared `base.css` supplies dark, low-specificity defaults for native fields and buttons,
file chooser buttons, checkboxes, sliders and color swatches, including forms
mounted after page load. Use `gw-field` for a label, control and help text;
checkboxes, radios, ranges and colors retain their own geometry rather than
inheriting text-field dimensions. Native invalid fields and `aria-invalid="true"`
use the field error treatment. Associate hints and errors with `aria-describedby`.

Single-choice selects inherit their chevron from the base styles. Override their
surface with `background-color`, since the `background` shorthand removes that
image, and reserve end padding for the chevron. Multiple/visible-list selects do
not use a chevron. Custom upload surfaces must keep the real file input reachable
by keyboard, show its focus, and prevent window dragging from the upload target.
Check empty, selected, disabled and error states at narrow viewport widths with
synthetic data; operating-system file selection remains the native file picker.

## Native state and realtime

Native UI code calls the shared domain API where implemented and still has dedicated HTTP/socket adapters for specialized flows such as uploads, board subscriptions and rendered fragments. The public browser API does not replace every native transport.

The realtime controller connects the current table's authenticated WebSocket, tracks subscriptions and reconnect state, and dispatches `gravewright:*` browser events. The server sends user-authorized projections and rendered HTML; private actor data, chat audiences and scene visibility are enforced before delivery. Insert user-provided text with `textContent`. Existing HTML fragment insertion is for HTML rendered by the trusted server templates, not arbitrary module or chat text.

`gravewright:api-event` is the internal adapter event consumed by the domain API; `api.changed` notifications trigger fresh authorized reads. Public integrations should use `api.events.on(...)` as documented in [API events](api.md#domain-events), rather than copying the native socket command protocol. Subscriptions are not a durable change stream: reconnect and reread current state. Creating `gravewright.forTable(...)` alone does not open a socket.

The native item and compendium directories sort copies of visible entries by
their displayed names using the active locale; stored document order and IDs
stay unchanged. Compendium packs, filters and previews use compact rows and
content-sized default windows, with internal scrolling for long content. Manual
window layouts retain the shared drag, resize, minimize and reset controls. GMs
can create the first compendium from the empty directory; read access does not
expose import or permission controls. System-owned item editors remain in their
packages and use the existing host contracts. Repeated item projections preserve
open action menus and focus; document or permission changes invalidate them.

## Sources and generated assets

Most app-specific JavaScript files under `static/` are directly served source. Some files there are committed build outputs. In particular, [`maps/scripts/build.cjs`](../../gravewright/maps/scripts/build.cjs) bundles the following:

| Editable entry/source | Generated destination |
| --- | --- |
| `maps/frontend/widgets/game-board/ui/board.js` | `maps/static/gravewright_maps/vendor/board.js` and named `runtime/` modules |
| `maps/frontend/shared/rendering/render-profile.js` | `maps/static/gravewright_maps/render-profile.js` |
| `maps/frontend/native/tools.js` | `maps/static/gravewright_maps/tools.js` |
| `maps/frontend/native/builder-catalog.js`, `builder-preview.js` | `maps/static/gravewright_maps/builder-catalog.js`, `builder-native.js` |
| `maps/frontend/native/builder-editors.js` | `maps/static/gravewright_maps/builder-editors.js` |
| `maps/frontend/native/table-modules.js` | `table/static/gravewright_table/media-workspace.js` |
| `maps/frontend/features/walls/{ui,model}/walls.js` | `maps/static/gravewright_maps/walls/` |
| Scene-layer sources and lighting profiles | `maps/static/gravewright_maps/sources/` |
| `maps/frontend/calibration.js`, `directory.js` | Corresponding map static model/controller files |
| `maps/frontend/shared/lib/dom/tree-drag.js` | `actors/static/gravewright_actors/tree-drag.js` |
| `maps/frontend/features/tokens/ui/controller.js` | `tokens/static/gravewright_tokens/controller.js` |
| `pdf_system/frontend/controller.js` | `pdf_system/static/gravewright_pdf_system/controller.js` |

Paths in this table are relative to `gravewright/`. Edit the source and rebuild these destinations. Do not make one-off fixes in minified board chunks or vendored libraries.

Tools, the board, Builder catalogs, editors and preview retain their public
entry URLs while importing named ES modules from `gravewright_maps/runtime/`,
following the source's feature paths. Shared modules have one browser identity;
PixiJS and its unsafe-eval adapter are emitted once as `vendor/pixi.js`. Preview
and editor imports stay lazy, and the visibility worker keeps its relative
resource URL plus the existing public worker entry. The Runner manifest includes
every emitted module and license notice. Ship the complete generated graph.
This layout uses more small requests while avoiding repeated bundled copies;
artifact sizes alone do not establish a browser performance improvement.

From the repository root:

```sh
npm ci --include=dev --prefix gravewright/maps/frontend
npm run build --prefix gravewright/maps/frontend
npm test --prefix gravewright/maps/frontend
```

The build uses the locked PixiJS and esbuild dependencies in [`maps/frontend/package-lock.json`](../../gravewright/maps/frontend/package-lock.json), targets ES2022, and keeps `/static/*` imports external. A shared render-profile module stays external so all features use the same runtime profile. The build also collects package license/notice files and writes `vendor/packages.json`; retain those outputs when redistributing built assets. It explicitly rejects including Vue packages.

### Windows runner preparation

The [Gravewright Runner](windows-runner.md) reuses verified Node.js/npm inside data/runner, or downloads its managed copy into that installation when necessary. Its CMD batch file calls [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) in `--plan` mode to check package versions, fingerprints and a real esbuild operation. A matching healthy dependency installation can be reused even on first launch. The batch file itself executes `npm ci --include=dev --include=optional` when dependencies need installation, and the existing `npm run build` for the first preparation or an invalidated build. It then calls the helper in `--record` mode to verify and save the completed output state. esbuild is required during preparation even though Python development dependencies are omitted from normal runner installation.

The plan returns exit code `0` for current assets, `10` for npm installation plus build, or `11` for build only. The batch launcher handles these decisions explicitly. Both helper modes accept `--node`, `--npm-cli` and `--state-dir`; the helper's default mode remains available to perform complete preparation in developer scripts and regression tests.

The npm project remains `gravewright/maps/frontend`; its ignored `node_modules/` is installed there and generated static assets are written to the destinations above. These outputs are committed application assets, so a source change followed by runner preparation can produce a version-control diff. Review and include the appropriate generated outputs and notices when contributing frontend changes.

Preparation state stays inside the extracted project under `data/runner/frontend/<source-location-hash>/state.json`. Managed tools and npm/uv caches are also local to this installation. Dependency checks include the package files and selected Node/npm versions. Build checks include editable sources, the build script and hashes of generated outputs. The batch file requests an output manifest, including vendor notices, from `build.cjs` through its optional `GRAVEWRIGHT_BUILD_MANIFEST` process variable. A later launch skips a valid unchanged build; changed inputs or missing/modified outputs cause preparation again. A failed build stops launcher startup instead of serving an unverified frontend. `collectstatic` then copies the prepared public assets to the project-local data/staticfiles directory.

The module domain-method registry has its own generation command:

```sh
uv run --locked python scripts/generate_frontend_api.py
```

This generates only `modules/static/gravewright_modules/frontend-contract.js` from `contracts/frontend.json`. The original SDK's `generated.js` and JSON schemas are separate artifacts; this script does not regenerate them. `collectstatic` gathers deployable assets but does not run either JavaScript build.

## Board layers and resource lifetimes

`pixi-application.js` initializes the real board or builder-preview WebGL context directly. Shared empty/white textures use initialized, premultiplied pixels. After context restoration, the board rebuilds pooled text textures and schedules a repaint without waiting for user input. The build retains explicit compatibility adjustments for Pixi context detection and restored texture bindings; it fails if upstream source no longer matches those adjustments.

The standalone `tests/web/firefox_webgl_browser.py` scenario serves built assets and synthetic graphics without campaign data. It checks warning-free startup, transparency and opaque pixels, then deliberately loses/restores the GPU context and compares the complete rendered image. It requires Playwright Firefox.

The **New scene** chooser includes **Empty map**. Its form asks for the scene
name, background color and width and height in pixels. It also offers the same
creation settings as an uploaded map: grid size, scale, distance per cell, unit,
grid visibility/color/opacity, folder and player/GM visibility. The current
folder is preselected; it can be changed or cleared. Both paths use the shared
scene-settings validation. Activation after creation remains optional.
When activation is unchecked, the creator previews the new scene while players
stay on the existing active scene. The server creates
ordinary lossless map tiles within the configured image and tile-count limits,
so existing rendering, permissions, tools and campaign archives continue to work.

The GM scene directory shows player dots in each player's saved identification
color and a **GM** badge on the scene currently being viewed. Dot tooltips identify
players, including offline members whose destinations persist. The context menu's
**Activate for selected players** opens a checkbox list for one or more players;
**Activate for players** still activates for everyone and clears individual
destinations. Changing identification color refreshes the dots without reloading.
The **GM** badge also identifies a private preview; there is no additional
**Preparing** label. Scene pointers show other participants as translucent colored
dots with their names, using each sender's saved ping color. The user's own mouse
keeps its native cursor. Remote motion is interpolated in scene coordinates and
projected through the viewer's camera, preserving screen size through pan/zoom.
Positions are transient, sampled at most ten times per second, and discarded
when users leave, disconnect or change scene. A stationary pointer remains visible
across delayed updates; silence alone is not a departure. Scene tool overlays
publish positions just like the rendering surface, excluding interface controls.
Switching browser windows or tabs pauses publication while preserving the last
shared position. Only actual scene departures, disconnects and explicit hide
packets remove it; losing window focus is not a departure.
Preferences → Mouse pointers has independent controls for viewing participants'
pointers and sharing one's own. Both default to enabled, persist per profile on
the current device and synchronize across tabs. Hiding received pointers keeps
their last positions available for immediate redisplay without rendering them.
Disabling sharing immediately hides that user's pointer remotely and stops
publication; it does not affect map pings or other participants' settings.

The same house menu has a **Keyboard shortcuts** topic for the table's executable
dock tools and windows, including campaign search. `table/shortcuts.js` derives
the defaults from the rendered dock, records combinations in focused fields,
updates accessible shortcuts/tooltips and dispatches the existing buttons.
Mappings persist per profile/device under `gravewright.shortcuts.<profile>` and
synchronize across tabs. Each layer has its own tool scope; window bindings
conflict across all layers. Existing default precedence is preserved. Users can
unassign actions or restore all defaults. Escape cancels recording; text editing,
composition, modal keyboard navigation and reserved browser/editing combinations
retain their native behavior. Tool-specific gestures are not remapped here.

These table additions use the installed Translator's English source-key contract:
Jinja `tr(...)`, the native `gwText(...)` adapter and `createTranslator().t(...)`
for browser-owned controls. Reviewed pt-BR/es host supplements cover new keys
without changing installed signed language archives. Without an active language
package, the host falls back to English and preserves the saved locale choice.
Player names, scene names and authored measurement titles are marked
`translate="no"`; key combinations and action IDs also remain unchanged.
The integration scenario `tests/e2e/table_translator.py` accepts an explicit
`GRAVEWRIGHT_TRANSLATOR_CATALOG_ROOT` containing real `en.json`, `pt-BR.json` and
`es.json` catalogs. It installs a disposable package and checks the new table
controls, uploaded Smart Objects, circular areas, authored values and fallback.
Only authorized viewers of the same scene receive positions. Streamers receive
pointers without sending them, and the GM layer does not publish mouse movement.

The table dock provides drawing through Mini Paint (`Draw`, shortcut `B`).
Rectangles and ellipses belong to that editor; there is no separate Shapes tool
or `T` shortcut. Existing shared area markers remain visible, and their stored
data and public APIs remain compatible. `Measure` continues to provide local
scene measurements. Enable **Title** to edit a measurement label directly on the
map, above its dimensions. Each title follows its measurement through movement
and zoom and stays visible when the tool closes. Titles share the same local
lifetime as measurements; they are not broadcast or saved to the campaign.

The `maps/frontend/` tree separates entity models, feature models/UI, shared utilities, and the game-board widget. The board widget coordinates rendering, input, tile scheduling/cache/prefetch, native layers, vision polygons, lighting and shaders. Feature code contains walls, tokens, drawings, measurements, effects, and selection. Algorithm tests live beside the relevant models and are bundled by `maps/scripts/test_models.cjs` for Node's test runner.

Use one consistent coordinate system across controllers and renderer calls: logical scene pixels, top-left origin, token centers as anchors. Camera pan/zoom converts scene positions into CSS viewport coordinates; device pixel ratio affects rendering resolution. Mixing these units causes selection, token and lighting misalignment. The extension overlay API exposes explicit conversion helpers instead of exposing the PixiJS renderer.

Async work belongs to a page, board, module activation, or individual mount. [`Lifetime`](../../gravewright/modules/static/gravewright_modules/lifetime.js) cancels API calls and disposes subscriptions; map source code has its own shared lifecycle helpers. Add/remove listeners and observers with their owner. Release rendering resources and pending work during board teardown or scene changes. A listener or cached API handle that outlives its owner can update the next scene with old data.

Updates to the current scene preserve camera pan/zoom, token art and mounted
layers, including revisions caused by teleport automation. Only a scene change
resets the camera. Raster revisions refresh existing tile keys by URL and keep
the previous decoded tiles visible until replacements are ready; superseded
requests cannot paint an older revision. A failed replacement retains its current
art while the bounded retry runs. Region occupancy and geometry refresh their own
overlay, keeping unrelated floor, light and shader resources mounted.

Token names, fallback initials and condition badges rasterize at a density matched
to the camera zoom and renderer resolution. Power-of-two density bands, capped at
eight, keep enlarged text sharp without regenerating textures during panning or
within the same zoom band. External labels use centered sans-serif text with a
thin outline and extra line spacing for conditions below the name.
The browser scenario `tests/e2e/token_text_resolution.py`
checks zoom, normal/dense displays, label updates and renderer disposal.

**Configure token** lets the GM choose each bar's color and audience: everyone,
owner and GM, or GM only. The server omits restricted bars from each recipient's
token state. Existing sheet display flags remain the defaults until overridden.
These settings belong to the scene token, survive duplication and do not change
the system sheet schema. Bars keep their 5px gap above/below the token; the name
and condition badges leave room for them. No numerical bar labels are added.
The name can appear always, only on selection, only on hover, or on selection/hover
(the compatibility default). A per-token switch controls the combat turn indicator:
a static green outline for the current turn and a muted dashed outline for the next.
`tests/e2e/token_appearance.py` checks native saves, recipient filtering, colors,
turn indicators and the editor at desktop/mobile widths.

Token acknowledgements and realtime snapshots can carry native
`teleports: [{id, version}]` metadata, filtered against the recipient's visible
tokens and their exact revisions. The token workspace remembers each accepted
teleport revision across normal reads. It bypasses movement interpolation and
recreates only that token's Pixi object at its destination; repeated delivery
keeps the same replacement. Logical identity, selection and sheet data remain
unchanged, and older asynchronous art loads cannot restore an earlier object.

Successful token commands apply the authorized token snapshot in their
acknowledgement. They do not issue another token GET or request scene layers;
committed scene changes arrive through the existing realtime subscription.
Failures and version conflicts still reload authoritative state. A movement
with no displacement and no traversed path does not save or enter the busy
state. Paths that leave and return to the same position remain real operations
so region entry/exit automation is preserved.

The token workspace saves silently, including when a confirmation takes longer.
Pending commands keep the interaction guard for concurrent edits. Errors and
route instructions remain immediate; there is no saving notice or notice timer.
Unchanged status text is not rewritten on every paint.

Local token previews reuse the static scene key and image reconciliation while
their immutable scene inputs remain the same. They do not walk all native image
transforms or reconstruct the component-origin index on every frame. A new image
snapshot still reconciles its transforms and artwork; changed walls, effects,
scene identity and role still invalidate their owning resources.

Movement notifications refresh scene layers and tokens without rebuilding the
unchanged actor directory or combat panel. Actor/combat edits and other token
commands retain the relevant notifications. Paired layer/token notifications
deliver spatial audio once through the token refresh; independent layer edits
still refresh audio. Live authorization and extension change hooks remain in place.

Same-scene teleport advances token revisions, not scene metadata or raster
revisions. Its layer/token notifications carry region and appearance changes
without requesting a new scene manifest or changing existing tile URLs. Repeated
portals therefore retain the decoded floors and raster textures already loaded.

### Native image updates

`SceneImageArt` reconciles ordinary image textures independently of the static
scene key. A source change keeps the sprite and its previous art until the new
texture is decoded; late results cannot overwrite newer state or a closed scene.
Current art survives same-scene light/geometry rebuilds. Composed surfaces and
grouped floors use a separate cache with the same lifecycle. Unchanged composites
rebind synchronously during effect rebuilds; material replacement retains current
art until decoding completes. Changed masks, geometry, group membership or
visibility revoke obsolete coverage immediately. Composition closes all input
bitmaps, including failed and cancelled loads, and publishes no partial floor.
Each art cache retains at most eight idle textures and 16 MiB of idle decoded
RGBA data, evicting the least recently used entries. Scene/role changes and disposal abort
pending loads and release textures/bitmaps. Only art in the authorized projection
is requested; inactive appearances are not prefetched.

Token-art references wait for a pending unload of the same URL before loading
again. Pixi's loader can otherwise return its old cached texture while unloading
is about to destroy it. Independent URLs remain concurrent. Dispose applications
with explicit `removeView: true, releaseGlobalResources: false` options: boolean
`true` also releases process-wide pools still used by other boards and previews.
Scene-owned textures and renderer resources still end with their owner.

GM-private images and Empty Object markers remain visible at 55% opacity in all
workspaces, with selection and interaction restricted to GM. Private drawings
multiply their authored opacity by the same factor. Server projections still
exclude private elements from player/streamer clients.

Realtime delivery sends committed `maps.layers` and `tokens.state` before their
dependent audio/combat refreshes. Every delivery retains its own authorization
check. Token-triggered changes may share the same scene revision; never discard
snapshots solely because that revision is equal.

### Lighting and vision work

`SceneLayers` calculates light occlusion once for each static scene key and
reuses those polygons for masks, the light atlas and the GM darkness veil.
`createVisibilityContext` shares wall indices and keeps at most eight filtered
subsets for finite ranges or elevation. Preserve the original ray arithmetic
and wall membership: changing a BVH can change rounding at coincident endpoints.

Torch and pulse frames update additive Pixi sprites over immutable falloff
textures. Shaders receive a GPU render texture; only particles that respond to
light request CPU samples, capped at eight samples per second. Profiles keep
their existing animation rates. A scene owns the texture pool and releases it
after shader bindings, the atlas and sprite layers.

Vision changes coalesce once per animation frame. Scenes with at least 128 wall
segments use the same-origin module worker emitted as `vendor/visibility-worker.js`;
smaller scenes and unavailable workers use the same geometry synchronously.
The worker keeps one active job and the latest pending snapshot, transferring
coordinate buffers. Native observers carry a `sourceId` so movement can retain
the last completed view while the next calculation runs. Selection, range,
elevation, cone and preview changes revoke that view immediately; wall and scene
changes terminate the old worker. Never reuse visibility across those boundaries
or quantize the configured vision range or token positions.
Pending movement retains the existing veil texture until a result arrives;
unrestricted GM vision reuses its static veil without repainting on token moves.

Compare full frames and completed worker jobs when profiling. Queuing work is
not completion, and headless software WebGL results do not establish hardware
GPU performance. Rebuild both board and worker entries together with the normal
asset build.

## Extending the interface

The host's [`SurfaceRegistry`](../../gravewright/modules/static/gravewright_modules/surface-registry.js) accepts `gravewright.ui.register(domain, declaration)` and returns an unregister function. It supports registered table surfaces plus `app.shell` and `inside.content`. A mount receives `{root, context, api, signal, onDispose}`. It gets a fresh lifetime and a dedicated root; failed mounts are cleaned up, and replaced native elements have their previous visibility restored. This global registry permits one replacement per domain.

Installed signed packages use `ModuleRuntime` instead. Its registrations are synchronous during module activation, its calls carry module identity/lease/revision, and competing replacements are chosen using table preferences. Use the module's `register` callback for installed packages; global UI registration is for host-page integrations and has different ownership/selection rules. Full examples and supported names are in [modules](modules.md).

## Frontend verification

Run the checks affected by the source you changed:

```sh
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
npm test --prefix gravewright/maps/frontend
uv run --locked python tests/e2e/frontend_api.py
```

For rendering or interaction changes, use relevant scenarios under `tests/e2e/`, including `mixed_selection.py`, `token_routes.py`, `light_rendering.py`, `effect_geometry.py`, `effect_pixels.py`, `map_prefetch.py` and `realtime.py`. The browser harness and dependencies are explained in [testing](testing.md). Test player and GM sessions where behavior is permission-dependent, and check disposal/reconnect when adding subscriptions. Keep labels and message catalogs aligned with the application's supported languages.

Scene selection follows the active workspace: Game selects game tokens and cards; Walls selects walls; Lighting selects lights; Effects selects effects; Sound selects sound sources; Images selects public images. GM selects private tokens, private images and regions. Drawing and measurement editing use their own tools. Click, marquee, context menus and Select All share this scope; changing workspaces cancels pending selection gestures.

The menubar uses F1–F8 in visual order: Game, GM, Images, Sound, Effects, Walls, Lighting and Edit Scene. These global bindings are listed in shortcut settings and can be reassigned. F5 selects Effects instead of reloading while the table accepts shortcuts; Ctrl+R remains available to reload. Hidden or unavailable actions do not run, and typing or modal focus does not switch layers.

The bottom dock separates current-layer tools from labeled Chat, Actors and Combat buttons. The Panels disclosure groups scene and content directories, search, settings and campaign tools. It retains the original controls and keyboard mappings: shortcuts work with the disclosure closed, while unavailable controls remain unavailable. Escape returns focus to the disclosure button; outside clicks and focus leaving the disclosure close it. Narrow screens use two rows and a scrollable panel list.

The chat titlebar groups chat-specific actions separately from the shared Reset layout, Minimize/Restore and Close controls. Its own minimize button participates in the shared window contract, preventing a duplicate control. The chat header stays below the menubar on narrow screens; detached chat retains Clear history for the GM and Close.

The table's Extensions panel lists ordinary installed modules, but only the
active version of the campaign's selected system. Other installed systems remain
available in the global Systems and Marketplace catalogs.

Inside includes a Theme section for owners and players, with Classic, Ocean,
Forest and Amethyst palettes. Shared interface colors apply immediately, including
on the table. The choice is local to the browser (`gravewright.interface-theme`),
not campaign data. Missing or invalid choices use Classic; unavailable browser
storage leaves the current selection usable and displays a saving warning.

Creating a subfolder in Scenes, Actors, Journals or Items expands its parent after
the server confirms creation. The expanded state uses the directory's existing
browser preference so the new folder remains visible after a reload. Failed
creation does not change the parent's expanded state.
