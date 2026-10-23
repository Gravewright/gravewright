# Testing

[Documentation](../README.md) · [Português](../pt-BR/testing.md)

Run commands from the source root after `uv sync --locked`. The repository uses Django/unittest for Python, Node's built-in runner for JavaScript and standalone Playwright scripts for browser flows. There is no root `npm test` or configured pytest runner.

### Known Windows limitations

- Windows limits paths to 260 characters. Map Builder scenarios install a fixture
  module under their output directory; a long `--output` path, such as one nested
  in the user's temporary folder, makes that installation fail with "Invalid
  module archive". Use the default output under `data/` or another short path.
- `tests/e2e/escape_windows.py` does not start its own server. It needs
  `ownership_server.py` on `127.0.0.1:30002` and `data/permissions-review-seed.json`
  from that fixture.

## Controlled local environment

Tests load the project's `.env` unless a process variable overrides it. For local HTTP browser tests, use a shell with these settings rather than inheriting a production HTTPS origin or external Redis:

```bash
export DJANGO_DEBUG=true
export DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost,[::1],testserver'
export GRAVEWRIGHT_PUBLIC_ORIGIN=''
export DJANGO_SECURE_COOKIES=false
export GRAVEWRIGHT_REDIS_URL=''
export TRUSTED_PROXIES=''
export GRAVEWRIGHT_MARKETPLACE_URL=''
export GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=''
export GRAVEWRIGHT_RELEASES_REPOSITORY=''
```

These are shell-local settings, not changes to `.env`. Browser fixtures normally override the database and media with temporary directories. Tests may override individual settings as part of a scenario.

## Python

```bash
uv run --locked python manage.py check
uv run --locked python manage.py makemigrations --check --dry-run
uv run --locked python manage.py test config gravewright --noinput
```

The runner uses the explicit file-backed `data/test-gravewright.sqlite3` database to exercise SQLite locking. `--noinput` authorizes replacing that test database if it already exists. Do not point it at valuable data or run parallel suites against the same path. Changing `GRAVEWRIGHT_DATABASE` does not change this explicit test database name. Media-writing tests generally create temporary storage; use a disposable `GRAVEWRIGHT_MEDIA_ROOT` for an extra boundary when running the full suite.

Focused examples:

```bash
uv run --locked python manage.py test config gravewright.accounts gravewright.realtime --noinput
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.modules --noinput
uv run --locked python manage.py test gravewright.dice --noinput
```

Release checks for marketplace Django apps and managed updates also include:

```bash
uv run --locked python tests/e2e/django_marketplace.py
uv run --locked python tests/e2e/automatic_updates.py --runner
```

These use isolated data and exercise dependency preparation, Django routes,
migration failure recovery, preservation across core upgrades and `.old` rollback.

## JavaScript

Use a current Node.js release with native ES modules and `node:test`; these commands were checked with Node 24. No root package installation is needed for these tests.

```bash
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

For all colocated JavaScript tests as well, this Python launcher avoids shell-specific recursive globs:

```bash
uv run --locked python - <<'PY'
from pathlib import Path
import subprocess
files = sorted(str(p) for base in ('gravewright', 'tests')
               for p in Path(base).rglob('*')
               if p.name.endswith(('.test.js', '.test.mjs')))
subprocess.run(['node', '--test', *files], check=True)
PY
```

Coverage includes module lifetimes and contracts, shader parsing, board input, tile scheduling, visibility, walls, selection, token routes and PDF field mapping. Pure geometry/model tests do not replace checking the actual GPU-rendered board.

Module tests cover multipart card-image uploads from lifecycle contexts,
activation leases, native permissions and cancelled operations. The Django
`gravewright.modules.test_card_assets` suite also verifies image validation,
asset reuse, table isolation and failed-upload cleanup.

## Browser scenarios

`uv run --locked python tests/e2e/door_rotation_anchor.py` checks door pivot
selection, rotation, Undo, opening/closing artwork, the shared wall editor and
saved settings in English, Portuguese and Spanish at desktop and mobile widths.
It uses an isolated campaign and accepts `--output` and `--browser-executable`.

The [campaign management scenario](../../tests/e2e/campaign_management.py) uses
disposable campaign data to exercise native PDF sheets, diary and quest editors,
co-GM access, denied requests and GM revocation. It checks that management opens
no game WebSocket or table presence, comparing before/after snapshots of broadcast,
private scene navigation and presence. It also checks English, Portuguese and
Spanish at mobile widths, then opens the real table to verify shared documents,
player filtering and audio playback in two clients. This describes the scenario's
coverage, not the result of a particular run.

```bash
uv run --locked python tests/e2e/campaign_management.py --output data/cm-check --browser-executable "<existingChromium>"
```

Replace `<existingChromium>` with an existing Chromium executable. Choose a new
or empty output directory for each run; fixtures, logs, state comparisons and
screenshots stay in that installation-local directory.

The [campaign preparation scenario](../../tests/e2e/campaign_preparation.py)
uses the same disposable fixture to exercise the dashboard, the reference picker
without a table connection, the session planner, the timeline and calendar, quest
columns with prerequisites, connections, the player preview and restoring a
journal from the trash, and checks phone-width layouts. Run it with the same
`--output` and `--browser-executable` options as the scenario above.

`tests/e2e/campaign_preparation_regressions.py` checks session draft preservation,
editing during an in-flight save, asynchronous reference-picker errors and retry,
stale comparisons during concurrent GM edits, private revision permissions and
atomic rejection of a historical revision restore whose physical file is missing.
It also checks the exact native error in English and its Portuguese/Spanish
translations at 320px. Use a separate fresh output directory:
`uv run --locked python tests/e2e/campaign_preparation_regressions.py --output data/prep-regressions --browser-executable "<existingChromium>"`.

`gravewright.administration.test_preparation_archives` covers preparation and
history round trips, retained files, each GM's snapshot dashboard, old-archive
compatibility, typed reference remapping, chronology and rejection of malformed
metadata, conflicting asset owners and quest cycles.

The [progress-clock scenario](../../tests/e2e/clocks.py) uses isolated campaign
fixtures to check shared clocks in management and the real table, realtime
updates, player and streamer permissions, private and scene-scoped filtering,
concurrent revisions, persistence and pinned display. It also checks English,
Portuguese and Spanish at 320px and preserves management's broadcast, navigation
and presence boundaries. Run it with
`uv run --locked python tests/e2e/clocks.py --output data/clocks-check --browser-executable "<existingChromium>"`,
using a fresh output directory. This describes coverage rather than a particular
run's result.

`tests/e2e/map_builder_clocks.py` checks native clock nodes, typed Amount wires,
execution continuations, save/reload, and nonmutating server rehearsal with
clock/receipt/media snapshots. It exercises player-triggered GM bindings,
private-clock filtering, realtime pinned HUD changes and live node editing for
advance, reduce, set and reset, plus English, Portuguese and Spanish at desktop
and 320px. Use a fresh directory, for example
`uv run --locked python tests/e2e/map_builder_clocks.py --output data/mbclocks-check --browser-executable "<existingChromium>"`.

`tests/e2e/clues.py` covers one-step and progressive discoveries through the native
campaign manager, table and MapBuilder editor. It checks undiscovered-record and
GM-note filtering in player JSON, events and DOM; reveal/hide, permissions,
revisions, receipt retries, persistence, scene scope, pinned displays and a
nonmutating server rehearsal. Native clue nodes exercise typed numeric inputs,
execution continuations and live advance/reduce/set/reset/reveal/hide actions.
English, Portuguese and Spanish are checked with long authored content at 320px
and desktop widths. Run with a fresh installation-local output directory:
`uv run --locked python tests/e2e/clues.py --output data/clues-check --browser-executable "<existingChromium>"`.

[`tests/e2e/progress_hud.py`](../../tests/e2e/progress_hud.py) checks transparent
clock/clue cards and empty segments, minimal pinned displays, direct left/right
progress controls, permissions and independent local positioning with multiple
real clients. Double-clicking a name opens the native editor for GMs and a
read-only description for players/streamers. Long and empty descriptions and
revoked access during pending reads exercise modal lifetime and privacy. It
compares requests, socket frames and persisted campaign state to verify moving
an indicator does not publish a campaign change, then checks saved positions
after reload and English/Portuguese/Spanish layouts at 320px. Use a fresh output:
`uv run --locked python tests/e2e/progress_hud.py --output data/progress-hud-check --browser-executable "<existingChromium>"`.
This describes the scenario's coverage, not the outcome of a particular run.

Journal reference validation and portable identity remapping use the owning
domain suites and the shared resource registry:

```bash
uv run --locked python manage.py test gravewright.journals gravewright.table.tests.test_journal_resource_api gravewright.administration.test_journal_resource_archives --noinput
node --test tests/modules/journal-resource-links.test.mjs tests/modules/mindmaps-ui.test.mjs
uv run --locked python tests/e2e/journal_resource_links.py --output data/journal-links-check --browser-executable "<existingChromium>"
```

The browser scenario inserts typed references with **@** in the native journal editor,
reopens saved links, exercises table and management access, checks hidden-target
preservation and permission changes during pending reads, and reviews translated
desktop/320px layouts with synthetic resources. Use fresh local output and
independent fixture databases. These commands describe coverage, not a completed
release validation. It also checks cancellation, email boundaries, slash blocks,
replacement of the captured trigger range and translated empty-editor hints.

The [journal chapter scenario](../../tests/e2e/journal_chapters.py) exercises
empty chapters, nested hierarchies, moving pages, renaming and reparenting,
deletion without page loss, older category groups and retained resource links.
It checks native campaign management and table clients, player filtering and
owner saves that preserve omitted private structure, then inspects English,
Portuguese and Spanish at desktop and 320px, including eight nested levels. Use a fresh isolated output:
`uv run --locked python tests/e2e/journal_chapters.py --output data/journal-chapters-check --browser-executable "<existingChromium>"`.
This describes scenario coverage, not the result of a particular run.

Mind-map graph, access, redacted-link, resource projection, archive and Blueprint
checks use the owning suites:

```bash
uv run --locked python manage.py test gravewright.table.tests.test_mindmaps gravewright.table.tests.test_resource_links gravewright.table.tests.test_mindmap_review gravewright.administration.test_mindmap_archives gravewright.maps.tests.test_blueprint_mindmaps --noinput
node --test tests/modules/mindmap-model.test.mjs tests/modules/mindmaps-ui.test.mjs
uv run --locked python tests/e2e/map_builder_mindmaps.py --output data/mindmaps-builder-check --browser-executable "<existingChromium>"
```

The isolated Builder scenario authors both mind-map nodes, saves/reopens their
bindings, checks rehearsal rollback and committed completion, and verifies that
open requests reach only authorized recipients. Responsive translated editors
use synthetic topics. These commands describe coverage rather than a release
validation result; keep each run's fixtures and output separate.

[`tests/e2e/mindmaps.py`](../../tests/e2e/mindmaps.py) exercises the native manager
and tabletop with a GM, selected player editor, ordinary reader and streamer.
It covers graph authoring, real pointer/keyboard input, local undo/redo, saving,
concurrent revisions and preserved drafts. Live link revocation must redact
identities without losing unrelated edits, including newly linked unsaved
resources. Native close/confirmation modals retain focus and drafts on cancel.
English, Portuguese and Spanish layouts are checked at 320px with authored text
preserved. Run in a new installation-local output directory:
`uv run --locked python tests/e2e/mindmaps.py --output data/mindmaps-check --browser-executable "<existingChromium>"`.
The independent `test_mindmap_review` suite checks that sheet text cannot expose
another actor's private asset metadata and that denied scene access does not
prevent discovery of other authorized campaign resources.

```bash
uv run --locked playwright install chromium
uv run --locked python tests/e2e/authentication.py
uv run --locked python tests/e2e/realtime.py
uv run --locked python tests/e2e/frontend_api.py
uv run --locked python tests/e2e/https.py
uv run --locked python tests/e2e/runner.py
uv run --locked python tests/web/window_i18n_browser.py
uv run --locked python tests/web/form_controls_browser.py
```

The standalone window test serves only static host files and checks native
controls in English, Portuguese and Spanish, including listener disposal and
preservation of authored content. It does not load a campaign or database.

The standalone form-control test exercises the shared theme, keyboard file
selection, checkbox/range behavior, validation, disabled/read-only fields and
320px layouts. It also checks that mapped PDF fields retain their authored
dimensions inside table windows. It serves static files with synthetic controls
and writes screenshots to `test-results/form-controls/` without a database.

`uv run --locked python tests/e2e/board_scene_refresh.py` exercises same-scene
updates with real WebGL, synthetic artwork and delayed tile responses. It checks
camera and artwork continuity, replacement retries, superseded requests, grid
changes and scene switches without loading campaign data. Diagnostics default to
a unique directory under `data/runner/`; `--workdir`, `--browser-executable` and
`--node` select an isolated output and existing runtimes.

`uv run --locked python tests/e2e/scene_layer_continuity.py` checks native floor
surfaces and grouped paint/erasers through region entry/exit, lights, darkness,
delayed material changes, removal and scene/role changes. It samples actual GPU
pixels between frames and serves only synthetic assets, with the same local
output and runtime options as the board refresh scenario.

`uv run --locked python tests/e2e/token_teleport_presentation.py` verifies that
teleport destroys and recreates only the token's rendered object at its destination,
while ordinary motion still interpolates. Its synthetic WebGL cases cover
duplicate updates, selection and sheet identity, delayed/superseded artwork,
disposal, and unchanged camera/floor resources. It uses the same local output and
runtime options as the other standalone rendering scenarios.

`uv run --locked python tests/e2e/token_saving.py` opens the native board with
synthetic actors in a disposable campaign and controls token replies to check
silent fast/slow acknowledgements, no-op movements, undo, group moves, conflicts,
newer snapshots, teleport and disposal. It records token reads, layer refreshes
and status DOM mutations; successful movement must reuse its acknowledgement,
while failed movement must resynchronize. `--output` and `--browser-executable`
select isolated results and an existing browser. `--baseline-dir` can serve
previously saved token assets for comparison without changing application files.

`uv run --locked python tests/e2e/mapbuilder_ingame_performance.py` generates a
representative MapBuilder scene and drives real token movements through the
native WebSocket transport with two browser clients. It measures acknowledgement
and authoritative presentation times, sequential movement throughput, frame gaps,
GPU resource activity and wire traffic, including region sprite changes and
teleport. Screenshots are outside timed intervals. It uses disposable campaign
data and accepts `--output` and `--browser-executable`. Optional `--baseline-dir`
and `--backend-source` load saved public assets and server source only in the
isolated fixture for before/after comparisons. The Django
`gravewright.realtime.tests.test_token_refresh_cost` suite checks notification
cost, actor projection stability, independent audio updates and live revocation.

On Linux, Playwright may need system browser libraries; `uv run --locked playwright install --with-deps chromium` also installs those and can require administrator privileges. Scenarios launch their own servers on temporary ports and seed synthetic data. Most use development settings and write diagnostics under `test-results/`; the HTTPS and runner scenarios use dedicated settings described below. Run scenarios sequentially: several share `test-results/migration-closure/`.

`tests/e2e/compendium_server.py --fixture <new-empty-directory>` starts a
disposable localhost fixture with a synthetic browser system, language catalogs
and compendiums. Repeat `--archive <system.zip>` to review local browser systems;
no operator data is reused. Run `tests/e2e/compendium_layout.py --seed
<fixture>/seed.json [--browser-executable <chromium>]` to check desktop, 390px and
320px layouts, en/pt-BR/es collation, accent-insensitive search, type/pack filters,
previews and native keyboard focus, independent imports, failed-import retry,
permissions, read-only access and first-pack creation. Results go to
`test-results/compendiums/` by default. On a separate fresh fixture,
`tests/e2e/item_directory_layout.py --seed <fixture>/seed.json --output
<results-directory> [--browser-executable <chromium>]` checks the native item
directory's density, item/folder/type ordering, search, keyboard menus,
duplication, moving and read-only controls. Stop each owned server afterward.

`tests/e2e/actor_form_layout.py --seed <fixture>/seed.json --output <results-directory>`
uses the same disposable fixture to verify actor/folder modal layouts at desktop,
390px and 320px, focus trapping/restoration, Escape/cancel, pending saves and
failure/retry with real persistence. It also accepts `--browser-executable`.

| Change | Relevant scenarios |
| --- | --- |
| Accounts and campaigns | `authentication.py`, `inside.py`, `campaign_controls.py` |
| VTT update alerts | `update_notification.py`; Django tests in `gravewright.administration.test_update_notifications` |
| Update progress and restart reconnection | `update_progress.py` (isolated, simulated updates; never replaces application files) |
| Installed release name and notes | `release_presentation.py`; Django tests in `gravewright.administration.test_release_presentation` |
| Realtime and permissions | `realtime.py`, `lighting_realtime.py`, `map_prefetch.py` |
| HTTPS, WSS and proxy trust | `https.py`; Django tests in `config` and `gravewright.realtime` |
| Local Windows runner | `runner.py`; Django tests in `config.test_runner` and `config.test_frontend_preparation`; Windows CMD runner workflow |
| Board, tokens and PDF sheets | `maps.py`, `tokens_pdf.py`, `token_routes.py`, `mixed_selection.py` |
| Map Builder | `map_builder.py`, `map_builder_studio.py`, `map_builder_expansion.py`; Django `gravewright.maps.tests.test_builder_projects`, `test_builder_expansion`, `test_builder_update`, `test_builder_render_expansion`, `test_builder_door_art` and `gravewright.administration.test_builder_archives` |
| Effects and rendering | `effects.py`, `effect_editor.py`, `effect_pixels.py`, `light_rendering.py` |
| Journals and dice | `journals.py`, `journal_types.py`, `dice.py`, `dice_validation.py` |
| SDK and table modules | `frontend_api.py`, `table_modules.py`, `management.py`, `marketplace.py`, `modal_flush.py` |
| Audio and chat | `audio_lifecycle.py`, `chat_controls.py` |

The Map Builder expansion scenario creates its own synthetic campaign, database
and media under a fresh installation-local output directory and stops its server
on exit:

```sh
uv run --locked python tests/e2e/map_builder_expansion.py
```

Optional `--output <new-empty-directory>` and `--browser-executable <chromium>`
select diagnostics and an existing browser. It checks saved layers and library
metadata, brushes/snapping, group transforms, native decorations/lights, safe
scene updates with manual content, revision conflicts and responsive localized
Studio layouts. `--large-only` measures selection and group movement of 1,000
synthetic floor objects, reporting observed times without a timing threshold.
Geometry model tests run directly with
`node --test gravewright/maps/static/gravewright_maps/builder/model.test.mjs`.

`uv run --locked python tests/e2e/map_builder_wall_art.py` checks wall artwork
with a synthetic transparent strip. It compares browser and generated-raster
pixels, grid-edge snapping, moving and undo, free diagonals, door cutouts and
saved fractional coordinates. It accepts the same output/browser options above;
Django `gravewright.maps.tests.test_builder_wall_art` covers raster edge cases.

`uv run --locked python tests/e2e/map_builder_collections.py` checks project-local
collection imports, edits, cancellation, removal and filtering, including families
with members in different collections. It also drives a wall/object group against
a fractional map boundary and reviews English, Portuguese and Spanish layouts at
320/390 px. The Studio and expansion scenarios use the current import modal,
one-cell floor tiles and visible auxiliary panels, including **Projects → New project**.

`uv run --locked python tests/e2e/map_builder_asset_removal.py` checks the asset
editor's campaign-wide removal button, confirmation/cancellation, failed and
lost acknowledgements, retained unsaved work and undo, project revision conflicts,
dependent scene/project cleanup, and localized desktop/mobile modals. It uses
the same isolated output and browser options.

`uv run --locked python tests/e2e/map_builder_scene_directory.py` checks the
red MapBuilder scene icon and context-menu project edit action, normal scene navigation
and broadcast preservation, keyboard access and localized narrow layouts. It
uses the same isolated output/browser options. Django
`gravewright.maps.tests.test_builder_scene_directory` covers campaign and role
isolation, current project links and bounded directory queries.

`uv run --locked python tests/e2e/map_builder_player_broadcast.py` keeps a player
connected while the GM generates a private MapBuilder scene, then uses the
directory's **Activate for players** action without a separate visibility edit.
It checks live delivery and reloading through rendered floor/art pixels, public
tiles and assets, and exclusion of GM artwork, blueprints and source projects.
It uses the same isolated output/browser options. Django
`gravewright.maps.tests.test_builder_player_activation` covers activation
revisions, retries, rollback, streamer reads and authorization boundaries.

`uv run --locked python tests/e2e/map_builder_native_effects.py` checks the VTT's
native light/particle/shader presets in the builder, editable settings, visible
animated preview pixels, saved/reopened documents, localized desktop/mobile
catalogs, native GM/player scene rendering, update ownership/live toggles and
renderer disposal. Server coverage is in
`gravewright.maps.tests.test_builder_effects`; browser options and fixture
isolation are the same as the other builder scenarios.

`uv run --locked python tests/e2e/pixi_board_lifetime.py` bundles the local
renderer sources and checks actual GPU pixels while token art is immediately
released and reacquired, and while another board is closed. It verifies circular
masks, resizing and independent disposal without Django or campaign data. Use
`--workdir <output-directory>`, `--node <node-executable>` and
`--browser-executable <chromium>` to select local tools and diagnostics; frontend
build dependencies must already be installed. The asset-reference unit tests also
exercise this race through Pixi's real loader.

`uv run --locked python tests/e2e/map_builder_render_lifetime.py` exercises
reciprocal presence-area teleports with shared token artwork, dynamic vision,
masked lights, particles and shaders in live GM/player clients. It checks
browser exceptions and continued GPU animation after repeated teleports,
hide/show updates, native behavior testing and resizing. It uses the builder's
isolated fixture and the same `--output`/`--browser-executable` options.

`uv run --locked python tests/e2e/map_builder_torches.py` exercises a composed
torch from builder configuration to real table interaction. It checks native
component windows, independent flame/mechanism state, group transforms, copies,
layers and deletion/undo, Blueprint door/flame actions, localized narrow layouts,
player keyboard/pointer controls, authoritative native image transforms and
streamer refusal. It uses synthetic artwork and the shared disposable campaign,
database, media, port and output isolation. Domain coverage is in
`gravewright.maps.tests.test_torches`; pure builder and native image model tests
cover ownership, affine transforms, missing references and duplicated IDs.

`uv run --locked python tests/e2e/map_builder_interactions.py` authors dice
requests, journal opening and quest status changes through the real node editor,
then exercises them as players in a disposable campaign. It checks one-player
and all-player delivery, authoritative dice results, previews and localized
desktop/mobile layouts. Use `--output` and `--browser-executable` for isolated
diagnostics and an existing browser. Domain coverage is in
`gravewright.maps.tests.test_blueprint_interactions`.

`uv run --locked python tests/e2e/map_builder_ingame_sync.py` edits generated
objects through the game, reopens the linked Builder and updates the same scene.
It checks imported geometry/artwork/light settings, deletion, independent local
drafts, conflicts, Undo, manual content and preserved live state, including a
Portuguese mobile viewport. It uses the disposable Builder fixture and accepts
`--output` and `--browser-executable`. Django coverage is in
`gravewright.maps.tests.test_builder_sync`; merge and history cases run with
`node --test gravewright/maps/static/gravewright_maps/builder/scene-sync-model.test.mjs`.

`uv run --locked python tests/e2e/map_builder_object_menu.py` checks mouse and
keyboard object menus, property section modals, region map picking and the 14
configurable models in an isolated Builder campaign. It verifies cancel,
replacement, media omissions, Undo/Redo, simulation and saved generation, then
measures native active/inactive artwork pixels and actual sound playback.
Layouts cover English, Portuguese and Spanish at desktop, 390px and 320px widths,
including the touch-accessible Object options action. Use `--output` and
`--browser-executable` for isolated results and an existing browser.

`uv run --locked python tests/web/automation_roll_browser.py` checks the native
roll modal and realtime transport with synthetic socket replies: explicit submit,
stable retry identity/scene, busy/error/success states, keyboard focus, localization,
long content and disposal. `tests/web/interactive_object_catalog_browser.py`
checks preset configuration, journal/player selection, optional sound and image,
replacement confirmation, empty catalogs and English/Portuguese/Spanish layouts
down to 320px. Both serve
static host assets with synthetic data and accept the same output/browser options;
they do not access campaign data.

`uv run --locked python tests/e2e/map_builder_composite_conditions.py` constructs
All/Any through the actual Blueprint editor, checks pure simulation, saved typed
wires, localized desktop/mobile layouts, then tests a real three-torch passage
as a player and switches its rule to Any through a linked scene update. It uses
synthetic art and the isolated builder fixture. Server tests are in
`gravewright.maps.tests.test_blueprint_logic`; pure model tests cover truth tables,
nested gates, eager evaluation, missing references and version/type/cycle limits.

`uv run --locked python tests/e2e/map_builder_variables_signals.py` authors typed
element/scene variables and named receiving graphs through the actual editor.
It checks private simulation, retyping and undo, targeted and scene-wide signal
delivery from real player interactions, operation receipts, reconnects, linked
updates, private audience projections and the GM variable inspector/reset.
English, Portuguese and Spanish layouts use synthetic artwork and the shared
isolated campaign, database, media, port and browser setup. Domain coverage is
in `gravewright.maps.tests.test_blueprint_variables`; pure Blueprint model tests
cover falsy values, initial snapshots, typed ports, malformed memory, signal
bounds and version compatibility. Archive and native duplication tests cover
preserved progress and independent copied element memory.

`uv run --locked python tests/e2e/map_builder_choices.py` authors Switch and
weighted Random through the real editor, with typed Value wiring, case/branch
controls, duplicate-value recovery, Undo/Redo, Cancel and local simulation.
It checks localized desktop/mobile layouts without intersecting choice cards
and the isolated scene's player actions, server-selected branches, command
receipts, privacy, linked updates and scheduled interactions. Domain tests in
`gravewright.maps.tests.test_blueprint_choices` cover strict typed cases and
weights, default/disconnected outputs, one draw on reconvergence, private
retry-stable draws including rollback, permissions, GM traces, Delay
continuations, Timer fresh reads, legacy/private draw ordinals, batch/path
presence events, actor and recursive-folder deletion, and authored values
during archive rewriting. Pure tests in
`builder/blueprint-choices.test.mjs` cover dynamic stable ports, falsy/Unicode
values, immutable snapshots, invalid definitions and samplers, weighted interval
boundaries, unreachable/convergent choices, Delay order and gate composition.

`uv run --locked python tests/e2e/map_builder_capabilities.py` exercises the real
editor's groups, typed resource references, transforms, interaction/region
actions and Event context, using synthetic assets and isolated campaign,
database, media, port and browser state. It checks authoring, temporary simulation,
localized layouts, saved source and play-time native effects/permissions.
`gravewright.maps.tests.test_blueprint_capabilities` covers typed ordered groups,
light/sound references, missing and incompatible targets, native transforms and
torch components, interaction gates, original trigger identity through signals
and timed work, atomic rollback/retries, scene updates and archive/copy remapping.
`gravewright.maps.tests.test_region_filters` covers AND/OR predicates, hidden and
disposition changes, identity ownership, quiet configuration baselines, runtime
region enablement, command-local presence suppression, current-row synchronization
and preserved/remapped filters across updates and archives.
`builder/blueprint-capabilities.test.mjs` checks typed set wiring, bounded groups
and actions, context defaults/types, lazy simulation, source copying, stale-target
preservation and execution-only bridging on deletion. Region model tests share
the native filter helper and verify matching, normalization and legacy omissions;
native lever interaction tests cover disabled player controls, stale keyboard
targets, occlusion and GM override. Run the actual scene/browser scenarios as well
to verify geometry, permissions and filtered occupancy visually.

The reusable-model, network and dynamic-world scenarios are
`tests/e2e/map_builder_templates.py`, `map_builder_network.py` and
`map_builder_world.py`. They use the same isolated output/browser options and
synthetic data. Template checks cover typed rebinding, parameter limits,
independent copies and the real editor's Apply/Undo/Redo/Cancel. Network checks
exercise existing-owner editing and filtered relationships; world checks cover
promoted artwork, material/visibility changes, presentation audiences, camera
preferences and same-scene token transport. Run them as browser scenarios;
pure simulation does not verify delivery or native rendering.

Focused server suites are `gravewright.maps.tests.test_blueprint_templates`,
`test_blueprint_network`, `test_builder_dynamic`, `test_blueprint_world`, `test_surface_archives` and
`gravewright.realtime.tests.test_automation_presentations`. They cover resource
ownership, payload-bound receipts, revision conflicts, atomic source/native
saves, rollback, archive remapping, generated-mask ownership, aggregate surface
budgets, durable arrival gates and recipient checks.
Pure JavaScript coverage lives beside the Builder models in
`blueprint-templates.test.mjs`, `network-model.test.mjs`,
`blueprint-presentation.test.mjs`, `dynamic-surfaces.test.mjs`, and beside the
native image helpers. Rebuild the native board when changing those helpers.

Real-engine rehearsal and live controls have separate server coverage in
`gravewright.maps.tests.test_blueprint_testing` and
`gravewright.maps.tests.test_scene_controls`. Run these with the disposable
database/media configuration described above. Rehearsal checks unsaved source
binding, authenticated token context, metadata-only dynamic surfaces, exact
chosen events, signals, time warnings, deterministic retries and complete
rollback of data, receipts, files and after-commit deliveries. Live-control checks
cover GM/player/streamer isolation, revisions, payload-bound receipts,
state-versus-interaction semantics, torch children, region baselines, material
restore and preservation of authored projects through a linked update.

`uv run --locked python tests/e2e/map_builder_playtest.py` exercises the public
Builder and native rehearsal APIs and their actual controls with synthetic data.
It compares campaign/database/media snapshots and observes a connected player
for accidental presentation delivery. JavaScript checks live in
`builder/playtest-model.test.mjs`, `builder/run-format.test.mjs` (trace and change
summaries shared with the automation log) and `scene-controls.test.mjs`. Server rehearsal
does not advance a scheduler: verify real Delay/Timer expiry with their separate
scenarios below.

`uv run --locked python tests/e2e/map_builder_universal_vtt.py` exercises the
native import chooser, warnings, lost-acknowledgement retry, export cancellation,
download and round-trip geometry/lights. It checks GM/player/streamer boundaries
and English, Portuguese and Spanish import/export layouts at 1440px and 390px,
using a generated image and a disposable campaign.

`uv run --locked python tests/e2e/map_builder_region_filters.py` checks actor
catalog failure/retry, legacy omission when opening and clearing filters,
save/Undo/Redo, inert missing token IDs and native Cancel/Save. Its isolated
Builder/native forms use long authored names in English, Portuguese and Spanish
at 1440px and 390px, checking control reachability, text size, overflow and
configuration without synthetic automation events.

`uv run --locked python tests/e2e/map_builder_persistent_gates.py` authors
Counter, Once and Cooldown through the actual Blueprint editor, checks their
temporary simulation memory and localized desktop/mobile layouts, then exercises
player interactions, operation receipts, reconnects, linked updates, private
projections and the GM node-memory reset. It uses synthetic artwork and the
shared isolated campaign/database/media/browser fixture. Domain coverage in
`gravewright.maps.tests.test_blueprint_controls` checks persistent progress,
atomic rollback, reconciliation, cloning/archives and server-clock cooldowns.
Pure coverage in `builder/blueprint-controls.test.mjs` verifies threshold
branches, saturation, first use, exact cooldown deadlines, blocked attempts,
event isolation, reconvergence, immutable inputs and strict memory/time bounds.
These scenarios validate event-driven cooldowns; persistent waiting has its own
coverage below.

`uv run --locked python tests/e2e/map_builder_delay.py` authors Delay through the
actual Blueprint editor and checks suspension-only simulation, saved typed
connections and English/Portuguese/Spanish desktop/mobile layouts. In a real
scene it exercises delayed door actions, the GM Waiting view and cancellation,
pause/resume, disconnected browsers and recovery after restarting the ASGI
server. The shared fixture isolates campaign, database, media, ports and output;
it does not touch an operator's queue. Pure tests in
`builder/blueprint-delay.test.mjs` cover whole-event suspension, Sequence/fanout
order, reconvergence, lazy inputs, control memory, named events, immutability,
duration bounds and version compatibility.
`gravewright.maps.tests.test_blueprint_delays` covers private checkpoints,
ordered resume, preserved event snapshots and current control memory, receipts,
segment rollback, actor/scene permissions, semantic-edit cancellation, private
projections, queue/archive/copy boundaries, serial waits, competing SQLite workers
and budgets across waits.
`gravewright.maps.tests.test_delay_worker` checks automatic host lifecycle,
browser-independent passes, safe shutdown, disabled workers, error reporting and
connection cleanup, plus suspension during managed updater maintenance.

`uv run --locked python tests/e2e/map_builder_timer.py` authors named Timer
start/stop/restart actions and their signal receivers through the real editor,
checks immediate Next execution and simulation without countdowns, and inspects
English/Portuguese/Spanish desktop/mobile layouts. Its isolated real scene
exercises player actions and receipt retries, private projections, stop/restart
and stale GM controls, preserved linked updates, fresh expiry variable reads,
pause/resume, closed browsers and ASGI restart recovery. No operator data or
queue is reused. Domain tests in
`gravewright.maps.tests.test_blueprint_timers` cover typed validation, named
identity/deadline/actor preservation, ordered start/stop/restart, GM restart
authority, receipts, rollback, shared Delay capacity, inherited timed/element
budgets, cancellation, archive/copy boundaries and racing workers. Pure tests in
`builder/blueprint-timer.test.mjs` cover strict action/duration/name/version
validation, immediate continuation, separate expiry receivers, Delay ordering,
unreached/reconvergent nodes and immutable authored/preview data.

`uv run --locked python tests/e2e/map_builder_library_controls.py` checks library
toolbar stability across materials, lights and particle/shader catalogs, long
collection filters, search and collapse, with empty and synthetic media. It also
checks compact checkbox alignment and pointer/Space activation in settings,
layers and selected light, torch and region properties in English, Portuguese
and Spanish at desktop and mobile sizes. It uses the isolated builder fixture.

`uv run --locked python tests/e2e/map_builder_regions.py` exercises named
rectangles, the door pressure-plate preset and the real Blueprint editor,
localized narrow layouts, two player-owned tokens, first-arrival/last-departure,
private native occupancy, scene update/reload and the native GM region editor.
It uses the same disposable campaign, database, media, port and browser setup.
Domain tests are in `gravewright.maps.tests.test_regions`; builder and native
region model tests cover geometry, typed references and copy/layer behavior.

`uv run --locked python tests/e2e/map_builder_native_editors.py` exercises the
same light, particle, shader and wall/door editing windows used by the game.
It checks private drafts, cancel/Escape, one undo step per save, full GLSL,
the preset library and nested prompt helper, barrier channels/elevation,
window dragging, keyboard focus and presets, save/reopen and native generation/update.
It also opens those windows at the actual game table to check their normal host.
Live scenes remain unchanged until
an explicit generation/update action. English/Portuguese desktop and Portuguese/Spanish
390px layouts check focus, localized controls and reachable save actions.
It uses the same isolated campaign and output/browser options.

`uv run --locked python tests/e2e/map_builder_native_effects_occlusion.py`
compares actual preview pixels across solid walls and closed/open doors. It also
checks invalid GLSL and missing-preset diagnostics, recovery, custom shaders that
ignore the intensity uniform, and renderer disposal while the document is hidden.

`uv run --locked python tests/e2e/map_builder_refinements.py` checks round brush
footprints and cursors, size shortcuts, area erasure, bucket seeds, material
sampling and keyboard cancellation of polygons. It exercises layer selection,
transfer, isolation, creation while isolated, locks and safe merges, including
undo, reopening and native scene updates that preserve identities and live light
state. English, Portuguese and Spanish layouts cover desktop and mobile,
including scrolled layer actions and active-layer status clipping. The pure geometry
and layer operations are covered by the builder's colocated `node:test` suites.

`uv run --locked python tests/e2e/map_builder_custom_layers.py` checks the single
empty, renameable starting layer, removing the final empty layer, explicit layer
creation, mixed object types, expandable contents and selection guards. It
exercises duplication with a one-cell offset, new identities and remapped Smart
Object references, real drag reordering, undo, the visible collection filter,
save/reopen and generation. Layout checks cover English, Portuguese and Spanish,
including narrow mobile viewports. Server coverage in
`gravewright.maps.tests.test_builder_layers` checks layerless save/reopen,
background-only generation, updates that preserve manual scene objects, orphan
rejection for all seven object types and compatibility with existing sources.

`uv run --locked python tests/e2e/map_builder_clean_layout.py` checks the enlarged
canvas, drawing controls in the existing panel's Tools tab and unique control
identities. It exercises the header map-name field, Enter/blur commits, Escape
cancellation, undo/redo and saving the currently entered name. It also checks
library categories selecting drawing tools and localized desktop/mobile layouts
while retaining project and native object data.

`uv run --locked python tests/e2e/map_builder_header_tools.py` checks the header's
Select/Paint/Erase shortcuts, Shift and box selection, group movement and undo.
It verifies Paint restoring the floor brush without changing its material,
actual brush footprints, size synchronization with Tools and bracket shortcuts,
fractional geometry without snapping, and whole-object erasure. Intercepted
saving and Preview check disabled editing controls. English, Portuguese and
Spanish layouts exercise the controls at desktop and mobile widths.

`uv run --locked python tests/e2e/map_builder_editor_panels.py` checks all six
editor panels, linked tab/panel semantics, arrow-key navigation, focus restoration
and independent scroll positions without changing the saved document or revision.
It exercises empty states, real selection property edits and undo, Tiles/Painting
brush controls and Shift-drag previews, native effect filters and disabled editing
in Preview. Synthetic long map, image and layer names cover English/Portuguese
desktop and Portuguese/Spanish 390px and 320px layouts. It uses the same disposable
fixture and output/browser options as the other builder scenarios.

`uv run --locked python tests/e2e/map_builder_tiles_only.py` retains the Tiles
regression despite its historical filename. It checks unchanged default Tiles
sources, preserves stored legacy geometry, color/opacity and native objects,
and generates their expected pixels before explicitly selecting Tiles for new
edits. New Tiles gestures retain snapped cells and continuous shapes when
snapping is disabled. It covers floor tools, layers and localized desktop/mobile
layouts with the usual isolated campaign/output/browser options.
`gravewright.maps.tests.test_builder_paint_modes` retains server coverage for
reading and rendering previously saved paint metadata.

`uv run --locked python tests/e2e/map_builder_terrain_paint.py` exercises the
header's Tiles/Painting selector and circular terrain brush with asymmetric
synthetic floor patterns. An independent radial/layer-compositing oracle checks
soft edges, hardness, stationary intensity buildup, material mixing and soft
erasure, including protected layers and paint added after an eraser. Real
gestures exercise one-step undo, Escape cancellation, locks, fractional
positions and the unchanged Tiles no-op optimization.
Shift-drag checks the live brush footprint and size without changing source
or revision, in Painting and snapped/free Tiles. It compares the terrain
region of the actual editor SVG against generated and updated scene tiles,
checks save/reopen source parity, and preserves native wall/door/light data,
live door state and manual scene walls. Focused English/Portuguese/Spanish
desktop/mobile captures inspect the actual mode and brush controls. It uses the
same disposable fixture and output/browser options as the other builder tests.
Kernel, source limits and rasterization have focused coverage in
`gravewright.maps.tests.test_builder_terrain_brush`,
`builder/terrain-brush.test.mjs` and `builder/terrain-painter.test.mjs`.

`uv run --locked python tests/e2e/map_builder_floor_repaint.py` checks repeated
floor painting with snapping on and off. It verifies unchanged source rows,
IDs, order, saved revision and undo history, family variants, union coverage,
and replacement without hidden backing floors. Holes, other layers, saved
projects, previews and generated pixels retain their expected coverage. Model,
painter and geometry unit tests also cover atomic rejection at geometry limits.

`uv run --locked python tests/e2e/map_builder_smart_walls.py` checks wall artwork
and editable nodes using a padded asymmetric synthetic strip. It compares a
continuous wall with collinear segments and reversed endpoints, probes L/T
junctions and door openings, and compares Preview coverage with generated tiles.
Real gestures exercise shared-node moves, snapping, layer locks, unchanged doors,
midpoint splits, corner drags, extension onto another wall and one-step undo.
Keyboard focus, Escape cancellation and a zoomed mobile touch drag are included,
along with save/reopen and generation. Use the same isolated output and browser
options as the other Map Builder scenarios. Focused JavaScript coverage is in
`builder/wall-edit.test.mjs` and `builder/wall-joins.test.mjs` beside their sources.

`uv run --locked python tests/e2e/map_builder_free_paint.py` checks unsnapped
fractional brush strokes, smooth circles, rectangles and polygons, continuous
area erasure, exact-shape fill, hover guides and contour/hole transforms. It
compares actual editor SVG coverage against generated scene tiles, including
save/reopen and the switch back to legacy snapped cells. Server validation,
even-odd masks, alpha, texture phase and resource limits are covered by
`gravewright.maps.tests.test_builder_free_paint`.

`uv run --locked python tests/e2e/map_builder_asset_types.py` checks exact library
categories after typed imports, automatic saving, reload and a new browser tab.
It verifies Paint and Material filtering, moving an existing asset to another
type, and classifying a previously untyped campaign image through Material
without rewriting campaign resources. All artwork and state are disposable.

`uv run --locked python tests/e2e/map_builder_autosave.py` exercises automatic
project persistence without clicking Save: typing, drawing, Undo/Redo, delayed
acknowledgements during a stroke, lost-response receipt retries, reload with an
uncertain committed write and newer undone draft, failed initial load/retry,
revision conflicts with copy/reload recovery and navigation flush. Smart Object checks
cover automatic graph application, invalid fields, localized desktop/mobile
status, live source/native configuration and stale-revision protection without
gameplay execution. It uses disposable state and generated artwork. The older
manual Smart Object Save/Cancel scenarios describe the previous modal flow;
use this scenario for the automatic persistence contract.

`uv run --locked python tests/e2e/map_builder_lifecycle_events.py` authors
`onDestroy` through the actual editor, checks capability-specific region and
signal ports, localized desktop/mobile layouts and predicted removal under
complete rollback. Real player token crossings verify per-token area events and
first/last occupancy changes. Native removal checks permissions, pause behavior,
failed-chain rollback, cross-element signal effects and idempotent receipts;
the authored project stays intact. All database, media and output are isolated.

`tests/e2e/map_builder_events.py` predates the simplified starting-event contract.
Use the focused scenario below for the current interaction workflow.

`uv run --locked python tests/e2e/map_builder_event_origins.py` checks base-event
ports with no comparisons or state filters, visible cable origins at two zoom
levels, English/Portuguese/Spanish layouts and a real game-scene double-click with
**Select** on the **Game** layer. It authors the complete `onInteract` sequence
with Check state, Change state and Change sprite; checks autosave, undo/redo,
reloading, server rehearsal and native interaction; and verifies that empty or
image-only sequences do not toggle implicitly. It also checks that loading drops
removed event graphs without removing elements or assets. The fixture isolates
campaign, database, media, port and output with synthetic artwork. Server tests
in `gravewright.maps.tests.test_blueprint_state_sprite` exercise explicit state
and image actions, snapshot-based conditions and retry receipts.

The current server event contract is covered by `test_blueprint_events`,
`test_blueprint_base_events` and `test_blueprint_references`. Their fixtures use
starting events and explicit state/condition nodes; cross-element execution uses
named signals. Coverage includes discarded retired graphs, active-graph UUID and
type validation, lock permissions, bounded chains, full rollback and retry
receipts. `test_blueprint_testing` also verifies that a GM can rehearse a paused
scene without changing its stored pause flag: normal actions, destruction and
unexpected failures leave gameplay paused and produce no committed effects.

`uv run --locked python tests/e2e/map_builder_object_areas.py` checks object,
torch and Empty Object area-event ports, local simulation, rolled-back rehearsal,
authorized player token crossings and private occupancy. It inspects rotated
bounds and full pass-through movements, with desktop and localized narrow layouts.
Server suites `test_object_areas` and `test_object_area_integration` cover
per-token events, explicit actions, pause, blocked moves, geometry edits, scene
updates, imports, occupancy counts, listener limits and atomic rollback.

`uv run --locked python tests/e2e/map_builder_target_connections.py` checks wiring
an Empty Object's area action to other objects through **Target**, dragging in
either direction at different zoom levels, compatible producer selection,
keyboard and cancellation, autosave, server rehearsal and committed token entry.

`uv run --locked python tests/e2e/map_builder_area_live_sync.py` checks an Empty
Object explicitly interacting with a lever that owns state, image and light
actions. A player drags a token in, out and back in; pushed states, interaction
controls, rendered image pixels and light state update on both live GM and player
boards without reloading. The fixture also distinguishes project autosave from
applying a new exit graph with **Update scene**. `test_blueprint_interact_action`
covers native and authored targets, typed groups, torch components, lock rules,
bounded chains, rollback, retries, rehearsal and delayed token context.

The finite Smart Object combination matrix is checked at three layers:

- `tests/fixtures/map_builder_connections.json` defines 28 value producers and
  38 consumer variants, including nodes without a Target input. Both
  `gravewright.maps.tests.test_blueprint_connection_matrix` and
  `builder/blueprint-connection-matrix.test.mjs` check all 1,064 pairs against
  the same expected types. They also require every registered value port to
  appear in the fixture. Rejected connections preserve the graph; accepted
  connections survive full validation and reject a second incoming value wire.
- `gravewright.maps.tests.test_blueprint_action_matrix` checks 362 action,
  target-kind and reference/group cases, including all writable states,
  native versus authored interaction, lights, sounds, missing/foreign references
  and mixed groups. It asserts effects and separate applied, missing and
  unsupported target identities. `test_blueprint_event_matrix` checks 387
  owner/event/state, control, permission, pause, audience, timer/delay and
  two-token presence cases. Events only start flows; state changes do not
  implicitly run another object's interaction graph.
- `uv run --locked python tests/e2e/map_builder_combination_matrix.py` exercises
  131 real browser cases: typed references/groups in both wiring directions,
  forward/reverse node creation, Boolean/number/text adapters, logic composition,
  event capabilities, unavailable resources, cancellation, atomic undo, autosave,
  reload and same-scene update. A server rehearsal identifies an existing
  unsupported target by name. It uses synthetic assets and the shared isolated
  campaign, database, media, port, output and browser fixture.

These matrices cover the enumerated contracts, not every possible authored
graph. Run the existing behavior suites above as well for longer execution
chains and live GM/player synchronization.

`uv run --locked python tests/e2e/map_builder_sprite_targets.py` checks the full
node catalog on doors, levers, torches, Empty Objects and regions. It authors an
Empty Object's area entry/exit directly into **Change sprite** with an ordinary
image connected to **Target**, without a target interaction graph. Real player
token movement checks the received image and rendered pixels in both GM and
player browsers, plus autosave/reload, reference remapping, same-scene updates,
native move/resize and restoration. Manual native geometry retains the update
conflict guard. It uses the shared disposable fixture and synthetic artwork.
`gravewright.maps.tests.test_blueprint_sprite_targets` covers typed references
and groups, every owner kind and visual mode, private base-image restoration,
native edits, resource deletion, archive remapping/validation, rollback and
receipt retries. `builder/blueprint-sprite-targets.test.mjs` checks the shared
catalog and image-resource contracts; the connection matrix includes sprite's
typed Target input.

`uv run --locked python tests/e2e/map_builder_gm_layers.py` verifies that Empty
Objects are editable only on GM, public images can move to GM and return through
their context menus, and hidden controllers still trigger area actions from real
player token drags. It checks ordinary images, levers, torches and live sprite
overrides on both boards, private payloads, generation, source updates and reload.
`gravewright.maps.tests.test_empty_gm_layer` checks native routing, legacy read
privacy, player command rejection, linked update compatibility and unchanged
manual-geometry conflict protection. Image-layer and interaction model tests
check workspace selection, mixed selections and stale keyboard controls.

`uv run --locked python tests/e2e/map_builder_element_names.py` checks all eight
element name fields, automatic saving, reopening, Undo/Redo, duplication and
reference labels. It creates Empty Objects and regions directly from the library
tool strip, checks keyboard access and localized desktop/390/320 px layouts, and
generates/updates the linked scene without replacing identities or target UUIDs.
`gravewright.maps.tests.test_builder_element_names` covers validation, Unicode,
unnamed legacy rows, native edits, dynamic surfaces and atomic failed writes.

`uv run --locked python tests/e2e/map_builder_event_latency.py` measures real
token-area entry/exit and direct interaction against a scene with 52 synthetic
images in GM/player clients. It records mouse release or interaction through the
first matching rendered WebGL pixel, socket acknowledgements/projections and
image fetch/decode/upload counts. Screenshot polling is outside the timed
interval. Compare runs on the same host and fixture; timings are observations,
not pass/fail thresholds. The scenario also checks faint GM-only Empty markers,
art and drawings across tabs, GM-only editing and player payload privacy. Use
the usual fresh `--output` and `--browser-executable` options. Image-art model
tests cover reuse, bounded eviction, failures, stale results and disposal;
`gravewright.realtime.tests.test_scene_update_priority` covers real socket
delivery before blocked audio, post-commit ordering and live authorization.

`gravewright.maps.tests.test_blueprint_performance` measures real domain commands
with synthetic data. It checks bounded inventory queries, projected token paths,
state/image/light effects, fresh asset metadata and ownership on the next command,
cleanup after errors and one history notification after commit. To record SQL
counts and timings, set `GRAVEWRIGHT_EVENT_BENCHMARK_OUTPUT` to an explicit JSON
file under an installation-local test directory and run that suite with the
disposable test database/media configuration above. Normal tests run one sample;
benchmark mode runs five eight-object chains and three sixteen-area entries.
Each sample uses a new receipt UUID and rolls back afterward; effect assertions
run outside the timed interval. The interval includes authorization, receipts,
SQL and synchronous serialization, excluding the outer transaction's disk flush,
network delivery and browser rendering. On the measured synthetic fixture, SQL
counts changed from 101 to 42 for the chain and from 286 to 174 for area entry.
Timings depend on the host and are not pass/fail thresholds.

`uv run --locked python tests/e2e/map_builder_blueprints.py` checks the door's
Smart object modal, draft cancellation, connections, local simulation, undo,
saved projects and localized mobile layouts. It also opens GM and player clients
to verify native state, active artwork, light and audio synchronization, retries,
locked-door permissions, the GM Automation window, scene updates and image cleanup. It uses the same
isolated output/browser options. Python validation and compatibility checks are
in `test_blueprints`, `test_blueprint_data_nodes`, `test_automation_runs`, `test_blueprint_references`, `test_builder_blueprints` and `test_blueprint_compatibility`
under `gravewright.maps.tests`; editor graph tests run with
`node --test gravewright/maps/static/gravewright_maps/builder/blueprint-model.test.mjs`.
`uv run --locked python tests/e2e/map_builder_levers.py` checks enabling lever
behavior, its two-state editor and object images, references and simulation,
saved/reopened projects, localized desktop/mobile layouts, generation and an
actual player double-click unlocking a door. It checks active-image projection
and the private Automation log using isolated state and synthetic assets.
`gravewright.maps.tests.test_levers` covers native interaction, retries, bounded
chains and rollback, roles, updates, image deletion and campaign archives.
`tests/e2e/map_builder_blueprint_assets.py` focuses on state-only image type
guards, saved volume precision and native copying without a base door image.
`tests/e2e/map_builder_instance_nodes.py` checks two real door-instance nodes,
their labeled verb ports, separate state appearance, native state and draft isolation, unchanged
legacy saves, explicit conversion after editing, and localized keyboard/mobile
layouts. It uses the same isolated output and browser options.

`tests/e2e/map_builder_drag_connections.py` exercises real mouse and touch cable
dragging, the node chooser at the drop point, direct input connections, multiple
branches, typed value wires, cancellation and cycle rejection. It checks saved/reloaded connections,
placement with zoom and panning, and localized mobile layouts. It uses the
same isolated output and browser options.

Some scenarios accept `--original /path/to/reference` for optional pixel comparisons against another checkout's `dist/frontend`. That checkout is not needed for ordinary smoke tests. `reference_tokens.cjs` is an auxiliary comparison tool, not part of the root Node unit command.

[`tests/e2e/https.py`](../../tests/e2e/https.py) runs the installed Daphne with direct TLS and behind a temporary TLS proxy. It checks browser account setup, Secure `__Host-` cookies, HSTS, CSRF rejection, authenticated WSS join/chat and page reload. Raw TLS handshakes check rejection of missing, foreign, HTTP and wrong-port WebSocket origins. The scenario generates temporary certificates and uses isolated database/media paths, production security settings, a test-only static handler and an in-memory channel layer. It needs the locked Python dependencies and Playwright Chromium above; no external Redis or Nginx is required. It leaves the system certificate store and application data untouched and writes diagnostics to `test-results/https/`. This tests the application transport contract; verify your deployed Nginx configuration and certificate separately using the [deployment guide](deployment.md).

`tests/e2e/realtime_processes.py` specifically starts a temporary `redis:7-alpine` Docker container and two ASGI processes. It requires Docker access and network/image availability; it cleans up its own container. It is separate from the default Django/Node suites.

## Windows runner validation

[`tests/e2e/runner.py`](../../tests/e2e/runner.py) starts the actual Python runner with temporary personal data and no Redis. It checks first-time setup, collected static assets, HTTP security, authenticated messages between two WebSocket sessions, occupied-port rejection and restart persistence of the configuration, session, campaign, chat and media. It checks that the project `.env` is preserved across restarts and existing development data remain unchanged. The scenario needs the development dependencies and Playwright Chromium above; ordinary runner startup does not.

[`config/test_frontend_preparation.py`](../../config/test_frontend_preparation.py) covers dependency reuse/installation, source and output changes, missing packages or a broken esbuild executable, failed-build retries, corrupt state and concurrent preparation. It also checks the batch `--plan`/`--record` handoff, incomplete dependencies and invalid manifests without running npm installation/build in those helper modes. These controlled subprocess tests belong to the normal Django suite and do not replace an actual npm build. Run the focused suite with `uv run --locked python manage.py test config.test_frontend_preparation --noinput`.

The [Windows workflow](../../.github/workflows/windows-runner.yml) uses CMD to run [`tests/windows/runner.py`](../../tests/windows/runner.py). On any operating system, its source check verifies that obsolete launcher scripts and references are absent:

```sh
python tests/windows/runner.py --source-check
```

On Windows, run the complete native scenario from the source root:

```bat
python tests\windows\runner.py
```

The scenario creates a temporary checkout with spaces, punctuation and Unicode in its path and runs the actual BAT without a data-directory override. Managed uv, Python, Node/npm, caches and temporary files stay under the project's `data/runner/`; state and logs stay under `data/`. A fake legacy AppData profile contains another installation's active pointer, and snapshots verify it remains unchanged. Repeated offline installation also ignores compatible external PATH tools. The test reads the icon shortcut through Windows COM, checks that an invalid port fails without pausing, and verifies creation and reuse of `.env`, preservation of `.venv`, Python/npm locks, saved configuration and user/machine/parent-process `PATH`. Generated frontend outputs are prepared only in the disposable checkout.

The same scenario runs the frontend preparation unit tests and the real Python server scenario in Chromium. `--skip-browser` omits installation of the browser-test dependencies and the browser scenario while keeping the batch checks. Diagnostics are saved under `test-results/windows-runner/`. The temporary source, environment and campaign data are cleaned up when the scenario finishes.

Use `"Install Windows.bat" --check --no-pause --data-dir "<temporary-data-directory>"` for a manual batch preparation check that exits without serving requests. This still installs missing dependencies, builds assets when needed and applies migrations. Workflow presence does not mean its jobs have already passed for a release; `--source-check` alone does not validate native batch execution.

Before publishing a Windows build, run that workflow and check a normal double-click launch, automatic browser opening, Ctrl+C and closing the console on a Windows computer. The [runner guide](windows-runner.md) describes diagnostic mode with an isolated data directory. Tests run on Linux or another operating system verify the Python runtime there, not native Windows CMD or shortcut behavior.

When reporting results, name the commands, versions and failures. A browser scenario that could not launch is not a passing test.
