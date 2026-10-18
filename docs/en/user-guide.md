# Using Gravewright

[Documentation](../README.md) · [Português](../pt-BR/user-guide.md)

## Accounts and campaigns

Create the first VTT owner at `/setup`, then sign in at `/login`. Other users register at `/register`. The owner manages the host and creates campaigns from `/inside`. A campaign is also called a `container` in HTTP routes and a `table` in browser/realtime interfaces.

The native ruleset is **Gravewright PDF System**, with `character` actors. Invite players using a campaign join code; the campaign GM configures expiration and maximum uses and can revoke codes. Successful first-time joins increment the usage count automatically. Membership gives a player access to a campaign, while document and scene permissions determine what they can actually see or change. A streamer link provides a restricted read-only view and is not a player account.

In **Systems** and **Modules**, **Install** lists the newest compatible, non-revoked version of each package. Search, categories and pagination operate on that selection.

## VTT update alerts

The installation owner has a bell next to their name in the library header. A gold marker appears when a newer verified VTT release is available. Open it to compare installed and available versions; **View update** opens Administration directly on the Updates tab. Installation still requires the owner's explicit action there.

Discovery runs without blocking the library. The visible page refreshes the indicator every five minutes, reusing the host's 24-hour release cache. **Check for updates** in Administration performs an explicit fresh check and updates the bell immediately. Player accounts do not receive host administration alerts.

The Updates tab highlights the full installed release name and loads its bundled notes immediately, including offline. It has no release-channel selector. When a newer version is available, its name and notes appear with the installation controls. Notes support readable headings, lists, code and safe links; Portuguese notes are selected when available for a Portuguese interface.

## Prepare the table

1. Create a campaign and open its table.
2. Create/import a map scene and configure its grid and initial view. **Activate for players** makes that scene player-visible and broadcasts it. Opening a scene privately does not share it.
3. Create actors, attach PDF sheets when needed, and place their tokens in the scene. Actor data and placed token state are related but distinct; a token represents an actor on a particular map.
4. Prepare journals, handouts and resources, granting access intentionally. Check with a separate player session before sharing.
5. Invite players, use the lobby/readiness controls where enabled, and broadcast the intended scene.

Board tools include selection, movement, drawing, measurement, walls, fog, lighting, map pings and effects. Permissions and the active tool determine available actions. The GM can prepare hidden material without broadcasting it. Rendering depends on browser WebGL capability and the scene's complexity.

### Enter Map Builder

For the campaign GM, **New scene** opens a choice between **Upload map** and
**Map Builder**. Upload keeps the existing image-import workflow. Map Builder
opens its own full-page workspace in the same tab, carrying the selected scene
folder. **Back to game** returns to the campaign's selected scene; entering the
builder leaves the players' broadcast unchanged.

The Studio has a left tool rail, contextual brush options above the map and a
horizontal **Library** below it. The header holds the save status button,
**Preview** and scene generation; zoom controls and dimensions in cells sit at the bottom
of the canvas. The library provides search, **Import** and type categories;
its arrow collapses the cards while keeping the toolbar accessible. On entry,
**Floor** is highlighted and shows available campaign images across all types;
clicking a category filters them independently of the selected drawing tool.
**Layers**, at the upper right of the map, opens an auxiliary panel for **Layers**,
**Selection**, **Settings**, **Projects** and **Review**. Closing it leaves the
library accessible. This panel starts closed and opens only when requested;
selecting or painting objects does not open it. **Components** remains planned.

**Import** opens a modal to choose your images and their type: **Floor**, **Wall**,
**Door** or **Object**. Optionally choose an existing asset family or enter a new
family name to group variations of the same type. Choose a family in the library
or the top material selector to paint with all its images; individual images
remain selectable. Double-click an image card to edit its type or family; an
image already used on the map keeps its type.

With **Floor**, choose **Shape** in the contextual toolbar: drag freely with the
brush, drag a rectangle between corners, or drag a circle from its center to set
the radius. For a polygon, click at least three vertices and press **Enter** or
double-click to finish; **Escape** cancels it. A floor family chooses an image at
random for each cell, keeping those choices through preview, undo/redo, saving and scene
generation. Each completed stroke or shape is one undo step. Draw walls and
doors between two endpoints. Doors work independently
and replace collinear wall spans when drawn over them. Select objects to move
or edit them in **Selection**; undo/redo tracks edits. Click the header's save
status button or press **Ctrl+S**, then use **Layers → Projects** to reopen saved work,
including after restarting the VTT. Named project layers organize objects with
saved visibility and locks; the active layer receives new objects. The contextual
toolbar configures materials, brushes, grid snapping and floor/object rotation.
Shift-click and rectangle selection build a group for moving, duplicating,
rotating or changing layers. **Object** and **Light** in the rail place decorative
images and native lights. **Review** shows a project summary and scene generation.

**Preview** hides editing guides and pauses painting; pan and zoom remain
available. It temporarily shows all layers and restores their previous visibility
when editing resumes. **Layers** controls visibility only in the editor, so
hidden layers still appear in the generated scene.

**Generate scene** saves the source, builds the tiled map and native walls and
doors, then opens the new GM-only scene. A doorway can replace part of a wall:
opening the native door releases movement and vision through that gap. Door
images follow the live door state. The players' broadcast stays unchanged; use
**Activate for players** in the scene's context menu when ready to share it.
Each new generation creates a separate scene. **Layers → Review → Update scene** replaces the map
and the project's generated resources in its linked scene, retaining manually
placed tokens and content, scene settings and live door state. Conflicting edits
stop the update; scenes with manual content keep their dimensions and cell size.
See the [Map Builder guide](map-builder.md) for workflow, limits and the delivery plan.

## During a game

| Area | Purpose |
| --- | --- |
| Actors and tokens | Character data, PDF field mapping, placed tokens, movement and visual state |
| Chat and dice | Shared messages, supported private/GM projections, rolls and presets |
| Journals | Diaries, quests, quest boards, weighted roll tables and attached images/PDFs |
| Audio | Uploaded tracks, playlists, synchronized playback and positional sound controls |
| Cards | Deck assets, drawing, hands and table card state |
| Combat | Encounter turns, initiative and effects |
| Compendiums | Reusable content packs, access controls and imports |
| Modules | Optional browser extensions and replacement/overlay surfaces |

Use the [dice notation reference](../../gravewright/dice/grammar/notation/GRAMMAR.md) for supported expressions. Journal rich text is stored as structured documents; access to GM sections and handouts is filtered by the server. An export or screenshot may have a different audience from the live table, so select what you share deliberately.

Browser audio may require a user interaction before playback. If the table stops updating, check connection status and reconnect; refreshing a page reloads authorized state. Module activation changes may require clients to load the new module set before issuing extension calls.

## Preserve content

Campaign export/import, cloning and snapshots are available according to host feature settings and permissions. Exports are designed for portable content and can omit private history or reset ownership; they are not full instance backups. Before restoring a snapshot or replacing campaign contents, use the recovery procedures in [deployment](deployment.md).

Maps, music, PDFs and other uploads retain their own licenses and ownership. The project license does not authorize redistribution of game books or media you do not own. Modules may use different licenses; see [licensing](../../LICENSING.md).

## Current limits

- The application locale preference currently supports `en`; Portuguese project documentation is available, but a Portuguese UI is not implemented by these documentation changes.
- The native PDF ruleset does not provide item types; the generic item backend should not be read as a complete native item editor/catalog.
- The provided extension loader runs JavaScript in the main page. Install code you trust; signatures do not provide isolation.
- Online marketplace discovery requires a catalog and trusted publisher keys. Managed hosts install core updates from Administration after the owner requests them. Django packages in Modules activate for the entire server and restart it automatically; browser modules remain table-specific.

For development or integrations, continue with the [API](api.md) and [module](modules.md) guides.
