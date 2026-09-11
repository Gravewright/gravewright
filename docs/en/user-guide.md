# Using Gravewright

[Documentation](../README.md) · [Português](../pt-BR/user-guide.md)

## Accounts and campaigns

Create the first VTT owner at `/setup`, then sign in at `/login`. Other users register at `/register`. The owner manages the host and creates campaigns from `/inside`. A campaign is also called a `container` in HTTP routes and a `table` in browser/realtime interfaces.

The native ruleset is **Gravewright PDF System**, with `character` actors. Invite players using a campaign join code; the campaign GM configures expiration and maximum uses and can revoke codes. Successful first-time joins increment the usage count automatically. Membership gives a player access to a campaign, while document and scene permissions determine what they can actually see or change. A streamer link provides a restricted read-only view and is not a player account.

## Prepare the table

1. Create a campaign and open its table.
2. Create/import a map scene and configure its grid, initial view and visibility. A scene must be player-visible and actively broadcast before players can access it.
3. Create actors, attach PDF sheets when needed, and place their tokens in the scene. Actor data and placed token state are related but distinct; a token represents an actor on a particular map.
4. Prepare journals, handouts and resources, granting access intentionally. Check with a separate player session before sharing.
5. Invite players, use the lobby/readiness controls where enabled, and broadcast the intended scene.

Board tools include selection, movement, drawing, measurement, walls, fog, lighting, map pings and effects. Permissions and the active tool determine available actions. The GM can prepare hidden material without broadcasting it. Rendering depends on browser WebGL capability and the scene's complexity.

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
- Online marketplace and core release discovery require operator configuration. Core update discovery does not install an update automatically.

For development or integrations, continue with the [API](api.md) and [module](modules.md) guides.
