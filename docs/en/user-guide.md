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

As the campaign GM, open **New scene**. Choose the workflow that matches your source:

| Source and goal | Action | Result |
| --- | --- | --- |
| An image you want to use directly as a scene | **Upload map** | A native scene with its configured grid and visibility |
| A map you want to build or keep editing as a project | **Map Builder** | An editable project; generating a scene is a separate action |
| A finished image you want to add walls, objects or behaviors over | **Map Builder → Library → Import → Import ready-made map** | A project background with editable elements above it |
| A `.uvtt`, `.dd2vtt` or `.df2vtt` file | **Import Universal VTT** | A new GM-only native scene with supported walls, doors and lights |

Importing an image does not detect walls or reconstruct its original layers.
Universal VTT imports do not create Builder projects. The
[importer/exporter guide](universal-vtt.md) explains supported fields and warnings.

For a first Builder project:

1. Choose **New scene → Map Builder** and name the project in the header.
   Entering the Builder preserves the players' current scene.
2. Use **Panels → Settings** for map dimensions and cell size. The header chooses
   **Tiles** or **Painting**; **Panels → Tools** holds the active brush options.
3. Import your own images through **Library → Import**, or choose a ready-made
   map background. Set the grid dimensions to match the image.
4. Paint floors and add walls, doors, objects, lights or effects. **Panels → Layers**
   controls the active layer, visibility, locks and contents. Select an element
   and use **Panels → Selection** for its properties.
5. Wait for the header to report that the project is saved. Edits save
   automatically; the status button and **Ctrl+S** synchronize immediately.
   Reopen saved work through **Panels → Projects**.
6. Use **Preview** to inspect the map. Use **Test behavior** for an available
   Smart Object graph; rehearsal reports predictions without committing gameplay
   effects. See the [Map Builder guide](map-builder.md) for supported objects.
7. Choose **Generate scene** to create a private native scene. After linking,
   the header action becomes **Update scene** to apply later project edits to
   that same scene. A revision conflict stops the update for explicit recovery.
8. In **Scenes**, use **Activate for players** when the scene is ready to share.

These actions have different effects:

| Action | What it changes |
| --- | --- |
| Automatic saving / **Ctrl+S** | The editable project |
| **Generate scene** / **Update scene** | Native scene artwork and generated resources |
| **Activate for players** | Scene visibility and the players' broadcast |

If saving fails, keep the tab open and use the recovery controls. **Reload saved
project** adopts the server version; **Save a copy** preserves the local document
under a new project identity. A browser draft is recovery storage, not a backup.
The [Map Builder guide](map-builder.md) covers drawing modes, asset removal,
layer operations, Smart Objects, shortcuts, limits and troubleshooting.

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

- Host catalogs include English, Portuguese (Brazil) and Spanish. English is the default when no preference is saved. Changing the interface language does not translate authored names, text or assets; installed systems provide their own translations.
- The native PDF ruleset does not provide item types; the generic item backend should not be read as a complete native item editor/catalog.
- The provided extension loader runs JavaScript in the main page. Install code you trust; signatures do not provide isolation.
- Online marketplace discovery requires a catalog and trusted publisher keys. Managed hosts install core updates from Administration after the owner requests them. Django packages in Modules activate for the entire server and restart it automatically; browser modules remain table-specific.

For development or integrations, continue with the [API](api.md) and [module](modules.md) guides.
