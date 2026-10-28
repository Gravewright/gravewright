# Public API reference

[Documentation index](../README.md) · [Português](../pt-BR/api.md) · [Module guide](modules.md)

Gravewright has three related interfaces. They use the same native permission checks, but have different version markers, signatures, and result shapes:

| Interface | Entry point | Current marker | Intended caller |
| --- | --- | --- | --- |
| Python | `from api import actors, ...` | `api.API_VERSION == "1.0"` | Trusted server integrations with initialized Django |
| Browser domain API | `window.gravewright`, or a module context's `api` | `api.version == "1.2.0"` | Native frontend code and browser extensions |
| Original module operations | Mount block's `host.call(name, payload, options)` | SDK `1.0.0` | Installed, active browser modules |

The Python facade re-exports selected service functions; it does not discover plugins or register Django applications. The browser APIs send authenticated requests to those services. The SDK registry is narrower and has explicit JSON input/output schemas. Do not interchange `api.actors.update(...)` and `host.call("actor.update", ...)` payloads without checking their respective contracts. The project does not currently ship an npm SDK, OpenAPI specification, or automatic compatibility release checker. Treat the version markers as descriptions of this checkout, not a promise covering undocumented internals. See [licensing](../../LICENSING.md) for extension licensing.

## Browser domain API

The base template loads [`frontend-api.js`](../../gravewright/modules/static/gravewright_modules/frontend-api.js). Once loaded, use the table-bound API on a game page, or explicitly select a table on other pages:

```javascript
const table = gravewright.forTable("<campaign-uuid>");
const actors = await table.actors.list();
const result = await table.dice.roll("1d20+3", { label: "Check" });
```

Replace the UUID with a campaign the authenticated user belongs to. Dice rolls publish a chat message; `dice.roll` is not a read-only calculator. A module should use its supplied `api` instead of obtaining a fresh global handle, so its requests remain tied to activation and mounting.

`forTable(tableId, {sceneId})` fixes a scene. A conflicting `sceneId`/`mapId` in later payloads fails with `stale_context`. An unbound scene on the current game page can default to the selected map; integrations requiring stable scene identity should bind it explicitly. Global account/campaign/admin/module adapters work without selecting a table, while table operations require a table context.

### Methods and payloads

The authoritative method-to-command mapping is [`contracts/frontend.json`](../../gravewright/modules/contracts/frontend.json); [`domain-api.js`](../../gravewright/modules/static/gravewright_modules/domain-api.js) supplies convenience methods. Payload validation and permission projection belong to the native service for each domain. This contract is a method registry, not a full payload schema. Representative payloads and result assertions live in [frontend API tests](../../gravewright/table/tests/test_frontend_api.py), [table domain tests](../../gravewright/table/tests/test_modules.py), and each app's tests.

Every domain below has `state(payload = {}, options)` and the listed command methods, normally `(payload = {}, options)`:

| Domain | Command methods |
| --- | --- |
| `actors` | `create`, `update`, `delete`, `setPermissions`, `saveSheet`, `createFolder`, `updateFolder`, `deleteFolder`, `deleteAsset` |
| `tokens` | `place`, `move`, `remove`, `duplicate`, `setHidden`, `setVision`, `configure`, `addCondition`, `removeCondition` |
| `maps` | `update`, `move`, `delete`, `activate`, `navigate`, `updateObjects`, `createFolder`, `updateFolder`, `deleteFolder`, `exportUniversalVtt` |
| `journals` | `resources`, `resolve`, `create`, `update`, `delete`, `move`, `setAccess`, `present`, `createFolder`, `updateFolder`, `moveFolder`, `deleteFolder`, `setStatus`, `setObjective`, `assignCharacters`, `createBoardQuest`, `addQuest`, `removeQuest`, `pinQuest`, `reorderQuests`, `roll`, `reset`, `setPrerequisites`, `restoreRevision`, `restoreDeleted`, `purgeDeleted` |
| `items` | `create`, `update`, `delete`, `duplicate`, `setPermissions`, `createFolder`, `updateFolder`, `deleteFolder` |
| `combat` | `add`, `remove`, `configure`, `setInitiative`, `rollInitiative`, `toggle`, `moveUp`, `moveDown`, `setTurn`, `nextRound`, `previousRound`, `start`, `stop`, `nextTurn`, `previousTurn` |
| `clocks` | `create`, `update`, `advance`, `reset`, `delete` |
| `clues` | `create`, `update`, `advance`, `reset`, `reveal`, `hide`, `delete` |
| `mindmaps` | `read`, `resources`, `resolve`, `create`, `update`, `node`, `delete` |
| `cards` | `define`, `instantiate`, `create`, `draw`, `shuffle`, `reset`, `deleteDeck`, `discard`, `return`, `give`, `place`, `take`, `flip`, `move` |
| `audio` | `updateTrack`, `deleteTrack`, `createPlaylist`, `updatePlaylist`, `deletePlaylist`, `createSpatialSound`, `updateSpatialSound`, `deleteSpatialSound`, `play`, `pause`, `stop`, `seek`, `setVolume`, `startScore`, `pauseScore`, `resumeScore`, `stopScore`, `nextScore`, `previousScore` |
| `compendiums` | `create`, `configure`, `read`, `delete`, `add`, `remove`, `import`, `setPermissions` |
| `mapBuilder` | `read`, `save`, `generate`, `update`, `sync`, `adopt` |
| `blueprints` | `save`, `templates`, `readTemplate`, `saveTemplate`, `deleteTemplate`, `test`, `testDraft`, `control` |
| `library` | `createFolder`, `updateFolder`, `deleteFolder`, `move`, `delete` |
| `ownership` | `read`, `update`; `state`/`read` require `{kind, id}` |
| `system` | `call(operation, data, options)`; `state` describes the campaign system's operations |

Additional forms:

| Method | Behavior |
| --- | --- |
| `actors/tokens/maps/journals/items/clocks/clues/mindmaps.list(payload, options)` | Return the collection from the authorized `state` response |
| `actors/tokens/maps/journals/items/clocks/clues/mindmaps.get(id, payload, options)` | Find an item in that projected collection, or `not_found` |
| `actors.update(id, changes, options)` | Convenience overload; reads current version if `changes.version` is absent |
| `actors.sheet(id, payload, options)` | Read a sheet; supports token context in payload |
| `maps.layers(payload, options)` | Read authorized scene layers |
| `chat.history(payload, options)` | Read visible messages |
| `chat.send(payload, options)` | Send `{text, sceneId?}` through native chat processing |
| `chat.remove(id, options)` / `chat.clear(options)` | Delete one/all visible-domain messages under native moderation rules |
| `compendiums.read({packId, id}, options)` | Read one entry using current table access; retain its compendium document/envelope |
| `compendiums.read({packId, ids}, options)` | Read 1–100 unique IDs and return `{entries: [...]}` in requested order; missing entries fail the whole batch |
| `dice.roll(expression, payload, options)` | Roll and publish; payload supports `repeat`, `label`, `visibility`, scene context |
| `table.search(query, options)` | Search documents with at least read access. Options accept `kind` (`actor`, `item`, `journal`, `quest`, `quest_board`, `scene`, `compendium`) and `recent` (up to 12 `{id, type}` references with an empty query). Results include authorized `snippet`, `kind`, and `actions`; recent references are revalidated on every request. |
| `table.lobby(options)` / `table.updateLobby(payload, options)` | Read/change native lobby state |

`combat.stop` ends the encounter and clears its participants, initiative, turn and round history. Actors and scene tokens are preserved; add participants again before starting another encounter.

The six combat transition helpers (`nextTurn`, `previousTurn`, `nextRound`, `previousRound`, `start`, `stop`) also fetch the current version if omitted. Explicit versions make concurrent editing intentional:

```javascript
const current = await table.actors.get("<actor-uuid>");
const requestId = crypto.randomUUID();
await table.actors.update(current.id, {
  name: "Renamed actor",
  version: current.version
}, { requestId });
```

Mutation methods send a generated UUID `requestId` unless supplied. Commands using native receipts deduplicate retries with the same ID; reuse it only when retrying the same logical command, and generate a new ID for a new change. A stale entity `version`/`expectedVersion` can still produce `conflict`. Do not assume every endpoint is idempotent: lobby updates and chat moderation, for example, have different service signatures.

`options.signal` cancels pending work. A disposed context produces `stale_context`; explicit cancellation produces `cancelled` in scoped module operations. Error handling should inspect `error.code`, not translated text. Authorized native service failures can additionally provide a display message in `error.message`; render it as plain text through Translator. Global HTTP adapters can additionally expose transport/authentication errors from the underlying endpoint.

### Capability discovery and extended domains

`api.capabilities()` returns an independent copy of the local browser contract,
including domain methods, reads, binary transports and long-running operations.
Its `global` section lists page-only account/campaign/owner adapters; those are
not granted to a leased module handle. It performs no request and grants no permissions. Python `api.capabilities()`
returns `{pythonVersion, browser}` without database access. Runtime system
operations are discovered separately through `await api.system.state()`.

The new domains retain the native campaign boundary, GM checks, operation UUIDs
and expected revisions. Their payloads use these public names:

| Operation | Payload |
| --- | --- |
| `mapBuilder.state` / `read` | `{}` / `{projectId}` |
| `mapBuilder.save` | `{projectId, expectedVersion, document, folderId?}`; use a new project UUID and `expectedVersion: 0` when creating |
| `mapBuilder.generate` | `{projectId, expectedVersion}`; creates a private scene |
| `mapBuilder.update` / `sync` | `{projectId, expectedVersion, expectedSceneVersion}` |
| `mapBuilder.adopt` | `{sceneId, expectedSceneVersion}` |
| `blueprints.state` | `{sceneId}`; authorized automation network |
| `blueprints.save` | `{sceneId, elementId, expectedVersion, expectedProjectVersion, blueprint}` |
| `blueprints.templates` / `readTemplate` | `{}` / `{templateId}` |
| `blueprints.saveTemplate` / `deleteTemplate` | `{templateId, expectedVersion, name, description, definition}` / `{templateId, expectedVersion}` |
| `blueprints.test` | `{sceneId, elementId, expectedVersion, event, tokenId?, blueprint?}` |
| `blueprints.testDraft` | `{document, elementId, event, actorId?, projectId?}`; an authorized linked project supplies the original scene scope for clock, clue and mind-map bindings in the temporary rehearsal |
| `blueprints.control` | `{sceneId, elementId, expectedVersion, action, value?}` |
| `maps.exportUniversalVtt` | `{sceneId}`; native interchange JSON |
| `maps.navigate` | `{mapId}`; explicit `mapId: null` resumes following the broadcast in an unbound context |
| `maps.activate` | `{mapId, playerIds?}`; GM-only. Omit `playerIds` to activate for everyone and clear individual destinations. A nonempty unique array of campaign player user IDs changes only those players' destinations. GM map state includes `players: [{id, name, color, sceneId}]`; other roles never receive this roster. |
| `library.createFolder` | `{name}`; returns `{ok, id}` |
| `library.updateFolder` / `deleteFolder` | `{folderId, name}` / `{folderId}` |
| `library.move` / `delete` | `{assetId, folderId}` / `{assetId}`; native snake_case aliases remain accepted |
| `ownership.read` / `state` | `{kind, id}`; GM-only revision, levels, grants and current members |
| `ownership.update` | `{kind, id, version, permissions, reset?}`; preserves the native bulk-folder/page rules |

Ownership kinds are `actors`, `items`, `journals`, `scenes`, `cards`,
`compendiums`, `tokens`, `pages`, and the four `actor-folders`, `item-folders`,
`journal-folders`, `scene-folders` groups. A page ID is `journalUUID:sectionId`;
bulk folder revisions are opaque strings. No new-domain method silently replaces
a supplied revision. Builder updates also verify their generated scene against
an authoritative mounted scene. Rehearsals retain native rollback semantics.

Rendering and tiling run outside an enclosing transport transaction; each owning
service retains its own commit and cleanup boundary. Generation, scene updates,
UVTT export and rehearsals default to no client deadline. `options.timeoutMs`
can set an explicit deadline; `null` disables it. Builder collections use the
existing map invalidations. Clocks and clues have the collection events described
below.

### Progress clocks

The `clocks` domain serves the same persistent records in the table and campaign
manager. `state({sceneId})` returns campaign clocks plus clocks in that authorized
scene, filtered by current membership. The native page adapter uses the existing
GET resource-state route so read-only stream sessions can view public clocks.

Create accepts `{name, description?, segments?, value?, color?, visibility?, playersCanEdit?,
pinned?, scopeSceneId?}`. Defaults are 4 segments, value 0, `#c9a44c`, `gm`,
false, false and campaign scope. Segments are integers 2–24; progress is 0–segments;
there are at most 128 clocks per campaign. Update accepts those configuration
fields plus the existing `id` and `version`. `advance({id, version, delta})`
accepts an integer delta from -24 to 24 and clamps progress to its valid range.
Reset and delete accept `{id, version}`. Only GMs configure, reset or delete;
players advance only public clocks with `playersCanEdit: true`. Streamers remain
read-only. Returned clocks expose `canEdit`, `canConfigure` and their saved
scope as `sceneId`.

`description` is optional authored text, defaults to `""`, and must be a string
of at most 4,000 characters. Only GM configuration writes can change it. Omitted
updates preserve it; readers receive it only when the clock is visible to them.
The field is additive and introduces no new browser method or SDK version.

`scopeSceneId: null` persists campaign scope; a scene UUID persists scene scope.
The request's `sceneId`/`mapId` is the viewing context and never relocates a clock.
A scene-bound handle rejects a different non-null `scopeSceneId`. Existing-clock
writes require the saved version; conflicts require reviewing fresh state.
The `clocks.changed` event uses the resource-state envelope below. See the
[clock guide](clocks.md) for visibility, pinning and synchronization.

### Clue discoveries

The `clues` domain shares persistent discoveries between the table and campaign
manager. `state({sceneId})` returns campaign clues and clues in that authorized
scene. Players and streamers receive only clues with `visibility: "players"`
and `value === segments`; undiscovered clues have no public record, title,
content, ID or placeholder. `gmNotes` is absent from every public projection,
including completed clues. All direct mutations require current GM authority.

Create accepts `{name, content?, gmNotes?, segments?, value?, color?, visibility?,
pinned?, scopeSceneId?}`. Defaults are empty content and notes, 4 steps, value 0,
`#c9a44c`, `players`, false and campaign scope. Names have at most 120 characters;
content and GM notes each have at most 4000. Steps are integers 1–24; value is
0–segments. A single step supports immediate discovery. Each campaign can hold
at most 128 clues, independently of clocks.

Update accepts those fields plus `{id, version}`. `advance({id, version, delta})`
accepts integer -24–24 and clamps progress. `reset({id, version})` clears progress
and preserves visibility; `hide({id, version})` selects GM visibility and preserves
progress; `reveal({id, version})` completes discovery and selects player visibility.
Delete accepts `{id, version}`. Revisions and retry UUIDs follow native receipts;
a former GM cannot replay a private receipt after losing authority.

`scopeSceneId` controls saved scope; `sceneId`/`mapId` supplies viewing context,
as for clocks. Native reads use the streamer-compatible GET resource route.
`clues.changed` subscriptions reread projected state using the resource envelope
below. The MapBuilder `clueControl` node delegates only its authored effect and
does not grant players direct clue writes. Rehearsals roll back its changes and
notifications. See [clues](clues.md) for usage and node actions.

### Collaborative mind maps and typed resource links

The `mindmaps` domain reads shared campaign graphs through each member's current
permissions. It has no implicit current-scene default: `state({})` lists every
accessible map; `state({sceneId})` selects campaign maps plus maps in that scene.
An explicitly scene-bound module retains its authoritative scene context.

| Method | Payload and result |
| --- | --- |
| `state` / `read` | `{sceneId?}` / `{id, sceneId?}`; the collection envelope / one projected map |
| `resources` | `{query?, kinds?, limit?, sceneId?}`; `{kinds:[{id,label}], resources:[...], truncated}` |
| `resolve` | `{reference}`; one live authorized display row or `null` for missing/denied targets |
| `create` | `{name, visibility?, editorIds?, scopeSceneId?, document?}`; GM-only, defaults to private campaign scope |
| `update` | `{id, version, name?, document?, visibility?, editorIds?, scopeSceneId?}` |
| `node` | `{id, version, nodeId, patch}`; update a topic's supplied fields |
| `delete` | `{id, version}`; GM-only |

`visibility` is `gm` or `players`. `editorIds` contains current campaign player
UUIDs; selected editors can read/edit even a private map. All GMs can edit, and
public visibility grants other participants reading only. Players can change
`name`, `document` and topic fields; configuring scope/access remains GM-only.
Streamers cannot write. Writes return `{id, version, mindmap}` (delete returns
`{id}`), use a dedicated retry receipt and require the saved version for existing
maps. Conflicts require reviewing current state, without replacing the draft's
expected version silently. `mindmaps.changed` uses the resource-state envelope.

A document is `{nodes, edges}`. Topics have UUID `id`, optional `parentId`,
`label`, `notes`, hex `color`, `x`, `y`, `collapsed`, `completed`, and `links`.
Parent links form an acyclic forest. Additional edges are
`{id, from, to, label?}` between existing topics. Topic patches accept these topic
fields except `id`. Limits are 64 maps per campaign, 500 topics/1,000 edges per
map, 16 links per topic/2,048 overall, and 1 MiB per document. Labels have 240
characters, notes 8,000, and coordinates are bounded to ±100,000.

Canonical resource references are exactly `{kind, id, pageId?}`. The
[resource registry](../../gravewright/table/resource_links.py) defines 37 types,
including native numeric IDs, installed compendium entries (`packId/entryId`),
journal pages (`id: journalId` plus `pageId`) and drawings (`sceneId/drawingId`).
Discover kind IDs through `resources`, rather than inferring them from labels.
Search accepts up to 120 characters; `limit` defaults to 80 and is bounded to
1–200. Labels come from current native projections. Authored labels stay literal;
optional `labelKey`/`descriptionKey` identify generated text for Translator.

Missing and denied links are both projected as `{unavailable:true, key}` without
hidden kind/ID/name/URL. Return that opaque placeholder unchanged when editing
other content, or omit it to remove the link. It cannot authorize a new hidden
reference. Reopening resolves permissions again; naming a target or sharing a
map does not grant target access. See [Mind maps](mindmaps.md) for resource types,
collaboration, MapBuilder nodes and typed archive remapping.

### Journal resource links

`api.journals.resources({query?, kinds?, limit?, sceneId?}, options)` searches the
same typed campaign catalog used by mind maps. `api.journals.resolve({reference},
options)` returns `{resource: row | null}` after checking current target access.
Both are read methods, available to authorized players and streamers. Unbound
reads do not inherit the table's broadcast scene; an explicitly mounted scene
remains authoritative.

Rich text retains `gw-journal-doc-v1`, version 1. A reference is an inline atom:

```json
{"type":"gwResourceLink","attrs":{"reference":{"kind":"journal-page","id":"<journalUUID>","pageId":"page_main"}}}
```

Stored references contain only `kind`, `id` and optional `pageId`. Recipient
projections add current display metadata and an opaque `key`; an inaccessible
target becomes `{unavailable:true,key}` without its identity or title. Return
that placeholder unchanged to preserve it during an authorized edit. It is
bound to the source journal and cannot create a new private connection. A
journal accepts up to 512 reference atoms; normal document size and depth limits
also apply. Saving uses the existing journal version and operation UUID.

Native reads use `GET /api/containers/{campaign}/journals/resources` with query
parameters `query`, `kinds` (JSON array), `limit` and optional `sceneId`, and
`GET /api/containers/{campaign}/journals/resolve?reference=<JSON>`. Responses are
private and not cached. Python packages use
`api.journals.resources(campaign_id, user_id, *, query='', kinds=None, limit=80,
scene_id=None)` and `api.journals.resolve(campaign_id, user_id, reference)`.
Resource lookup never changes table presence or navigation. See
[Journals and references](journals.md) for editing, access and portable copies.

### Diary chapters and pages

Diary updates use the existing journal command, expected version and operation
UUID. The `data` payload can include independent chapters, including empty ones:

```json
{
  "chapters": [
    {"id":"chapter_main", "name":"Chapter one", "parentId":null, "sortOrder":10},
    {"id":"chapter_child", "name":"A subchapter", "parentId":"chapter_main", "sortOrder":10}
  ],
  "sections": [
    {"id":"page_main", "title":"A page", "kind":"text", "chapterId":"chapter_child"},
    {"id":"page_loose", "title":"An ungrouped page", "kind":"text", "chapterId":null}
  ]
}
```

Each page belongs to zero or one chapter. Each chapter has zero or one parent
and can contain zero to many pages and subchapters. IDs are local to the journal;
copying a campaign preserves them and does not treat them as resource UUIDs.
Chapter IDs are unique, 1–40 ASCII letters/digits/underscores/hyphens; names are
1–80 characters. The server allows up to 128 chapters, eight hierarchy levels
and the existing 64 pages. Missing parents, cycles and dangling page assignments
are rejected before saving. Chapter sorting uses `sortOrder` within each parent.

Authorized diary projections expose `chapters` alongside `sections`. Private
pages remain filtered, together with chapter branches containing only unreadable
pages. Ancestors of readable pages and genuinely empty branches remain visible.
Page-scoped presentations contain only their page's chapter path. Updates preserve
server-owned hidden pages and the chapter structure those pages require.

Legacy `sections[].category` names receive stable chapter IDs on normalization;
`category` remains a compatibility name mirror. An explicit `chapterId: null`
removes a page's assignment. Older updates omitting `chapters` retain existing
chapters, including empty ones. History and campaign archives retain the tree.

### System-owned operations and the PDF System

The host routes `api.system.call(name, data, options)` only to the current
campaign system's registered provider. Changing an operation name or a payload
cannot select another system. Trusted server packages register callbacks from
`AppConfig.ready()` with `api.systems.register_api(system_id, operations)`, where
each entry declares `{effect: "read" | "write", handler, description?}`. Registration
does not query the database. Handlers receive
`(campaign_id, user_id, payload, request_id, scene_id)` and own resource validation,
transactions, revisions, retry receipts and notifications. The host rechecks
membership, bounds JSON, prevents mounted-scene retargeting and makes every
streamer write fail before invoking the handler.

The bundled PDF provider exposes the following names through that generic API:

| Operation | Data and behavior |
| --- | --- |
| `pdf.read` | `{actorId, tokenId?}`; authorized native sheet plus active `source` |
| `pdf.configure` | `{actorId, tokenId?, source, version, sheetVersion, changes}`; GM-only partial layout configuration |
| `pdf.exportMapping` | `{actorId, tokenId?, source?}`; GM-only portable bundle without PDFs or character values |
| `pdf.applyMapping` | `{actorId, tokenId?, source, version, sheetVersion, bundle}`; GM-only application to an actor or independent token |
| `pdf.diagnostics` | `{actorId, tokenId?, source?, document?}`; saved metadata/calculation diagnostics without writes |
| `preparation.diagnostics` | `{}`; GM-only saved-sheet problems for the preparation dashboard, without reading PDF bytes |
| `pdf.roll` | `{actorId, tokenId?, field, source?, visibility?, sceneId?}`; authorized saved action through native dice/chat receipts |
| `pdf.templates.list` / `read` / `export` | `{}` / `{id}` / `{id}`; GM-only campaign library |
| `pdf.templates.create` / `update` | `{name, bundle}` / `{id, revision, name, bundle}` |
| `pdf.templates.delete` / `import` | `{id, revision}` / `{name, bundle}`; import accepts original JSON text or an existing object |
| `pdf.templates.apply` | `{id, revision, targets:[{actorId, version, sheetVersion, source}]}`; atomic batch, up to 100 actors |

`changes` accepts source-free `manualFields`, `fieldActions`, `fieldBindings`,
`calculatedFields`, token `bindings` and expected `document` metadata. Omitted
sections and current values are preserved. Native calculated-field validation
and cycle protection still apply. Snapshot operations retain the snapshot's
name, permissions and values. JSON imports retain their 1 MB file limit and
reject duplicate keys/nonfinite numbers when supplied as original text.

```javascript
const capabilities = await api.system.state();
const sheet = await api.system.call('pdf.read', { actorId });
const bundle = await api.system.call('pdf.exportMapping', { actorId, source: sheet.source });
const template = await api.system.call('pdf.templates.create', {
  name: 'Reusable mapping', bundle,
}, { requestId: crypto.randomUUID() });
```

PDF.js document inspection, flattened PDF rendering, selection and undo history
remain browser work. Server diagnostics inspect saved bindings/calculations and
an optional caller-observed page descriptor; they do not claim to parse PDF bytes.
See [PDF System](pdf-system.md) for the mapping, calculation and export workflow.

### Binary domain methods

Binary methods accept a real `File`/`Blob` as `payload.file`, use CSRF-protected
multipart transport and retain module activation/lease identity. Downloads return
`{blob, name, contentType, size}`. No file is encoded into the JSON command body.

| Method | Additional payload |
| --- | --- |
| `maps.upload` | `{name, settings?, activate?}` |
| `maps.importUniversalVtt` | `{name, folderId?, builderEditable?}`; use `options.requestId` for native import retries |
| `library.upload` | `{purpose?, folderId?}`; native image/audio/PDF library uploader |
| `library.download` | `{id, kind?: "image" | "audio" | "pdf"}` |
| `actors.uploadAsset` / `downloadAsset` | `{folderId?}` / `{id}`; current system's native asset provider and authorized download |
| `actors.uploadImage` | `{id, kind: "portrait" | "token"}` |
| `audio.upload` | `{name?, purpose?, folderId?}` |
| `cards.uploadAsset` | `{purpose: "card_front" | "card_back"}` |
| `journals.uploadAsset` / `downloadAsset` | `{journalId}` / `{id}` |

Native format, size and complexity limits still apply. Uploads create new files
and have no retry receipt except UVTT import. Persist returned IDs before starting
another import. `onProgress` reports completed bytes, and `signal` cancels work;
disposing a context prevents later progress callbacks. File operations default
to no deadline, with optional `timeoutMs`. Cross-campaign asset IDs are rejected
even when the user belongs to both campaigns. Server file handlers recheck native
ownership and page visibility; a route or client handle grants no access itself.

### Account, campaign, owner and module adapters

These are available on the global `gravewright` object, not on the module's domain-only `api`:

| Adapter | Methods |
| --- | --- |
| `accounts` | `status`, `session`, `login(payload)`, `register(payload)`, `setup(payload)`, `logout`, `update(payload)`, `home(kind)`, `privacy` |
| `campaigns` | `list`, `management(id)`, `create(payload)`, `update(id, payload)`, `join(code)`, `remove(id, code)`, `invite(id, payload)`, `removalCode(id, payload)`, `invitationStatus(id)`, `revokeInvitation(id)`, `banMember(id, payload)`, `onboarding(id)`, `configureOnboarding(id, payload)`, `claimCharacter(id)`, `streamerLink(id)`, `revokeStreamer(id)`, `rulesets`, `preparation(id)`, `prepare(id, action, payload, requestId)`, `references(id, type, documentId)`, `viewAs(id, userId)`, `journalHistory(id, journalId)`, `journalRevision(id, revisionId)`, `journalTrash(id)` |
| `administration` | `status`, `diagnostics`, `settings`, `updateSettings(section, payload)`, `snapshots(id)`, `createSnapshot(id, payload)`, `snapshotAction(id, snapshotId, action, payload)`, `previewSnapshot(id, snapshotId)`, `restoreSnapshot(id, snapshotId, payload)`, `deleteSnapshot(id, snapshotId, payload)`, `clonePreview(id, payload)`, `clone(id, payload)`, `exportCampaign(id)`, `importCampaign(file, payload)` |
| `administration.updates` | `check`, `notification`, `channel(payload)`, `apply(payload)` |
| `modules` | `list`, `catalog`, `catalogLatest`, `status`, `install(payload)`, `state(tableId)`, `configure(tableId, payload)`, `activation(payload)`, `update(payload)`, `removalPreview(payload)`, `remove(payload)`, `defaultMarketplace`, `configureDefaultMarketplace`, `acknowledge(tableId, payload)`, `localInstallationInfo`, `installLocal(file, payload)` |

Every method accepts an optional final `options` argument with `signal` and `timeoutMs`; file transfers also accept `onProgress`. Signatures and native payload field names are documented in [`global-api.js`](../../gravewright/modules/static/gravewright_modules/global-api.js). Snapshot actions preserve caller-supplied `{confirm}` values, and package removal preserves `confirmedTables`; the adapters do not synthesize approvals. Export returns `{blob, name, contentType, size}`. Campaign import takes a ZIP `File`/`Blob` and optional `{title}`; local package installation takes a ZIP and `{kind: "module" | "system"}`. There is no native snapshot-download endpoint. Creating the API handle performs no administrative action.

`campaigns.management(id, options)` reads the GM-only campaign overview without loading the tabletop or joining its presence. The [management workspace](campaign-management.md) uses the same native document services and current campaign-local GM checks.

The [preparation tools](campaign-management.md#preparation-tools) use further GM-only methods. `preparation(id)` reads session plans, timeline events, the caller's dashboard, pending work and system sheet diagnostics. `prepare(id, action, payload, requestId)` runs one command: `session-create`, `session-update`, `session-finish`, `session-reopen`, `session-delete`, `event-create`, `event-update`, `event-delete` or `board-update`. A retry of the same command reuses its request UUID. Updates and deletes send the record's current `revision`; a stale revision is rejected with HTTP 409. `references(id, type, documentId)` lists a character, item, journal or scene's links and usages. `viewAs(id, userId)` returns the native journal, actor, item and scene projections that one player receives. `journalHistory(id, journalId)`, `journalRevision(id, revisionId)` and `journalTrash(id)` read journal versions, a line comparison with the current version, and deleted journals. Failed preparation requests return the reason in the JSON `error` field.

Preparation command payloads use these native fields. Create returns `{id,
revision}`; dashboard changes return `{revision}`. Fields omitted during an update
retain their current values.

| Action | Payload |
| --- | --- |
| `session-create` / `session-update` | `{title, scheduledFor?, steps?, checklist?, notes?}`; update also requires `{id, revision}` |
| `session-finish` | `{id, revision, summary, pending?}`; pending uses checklist entries |
| `session-reopen` / `session-delete` | `{id, revision}` |
| `event-create` / `event-update` | `{title, worldDate?, position?, date?, upcoming?, description?, links?}`; update also requires `{id, revision}` |
| `event-delete` | `{id, revision}` |
| `board-update` | `{revision, pins?, widgets?}`; edits only the caller's dashboard |

A step is `{id, kind, refId, label, done}`; `kind` is `actor`, `item`, `journal`,
`scene`, `encounter`, `track`, `playlist` or `note` (notes have `refId: null`). A
checklist entry is `{id, text, done}`. Event links and dashboard pins use
`{type, id}` for the same resource kinds except `note`. Dates use `YYYY-MM-DD`
or `null`; in-world dates remain text. Widget IDs are `pins`, `session`, `pending`,
`diagnostics`, `events`, in the desired order, without duplicates. The service
validates campaign ownership and [preparation limits](campaign-management.md).

Journal history writes use the table-bound `journals` API and its operation UUIDs:

| Method | Payload |
| --- | --- |
| `setPrerequisites` | `{journal_id, version, prerequisites: [questId, ...]}`; GM-only, same-campaign quests, rejects cycles |
| `restoreRevision` | `{journal_id, revision_id, version}`; `version` must be the `current.version` returned by the displayed comparison |
| `restoreDeleted` / `purgeDeleted` | `{revision_id}`; the ID of the deleted entry, rather than its former journal UUID |

Restores revalidate default access, quest prerequisites and physical attachments.
Failure leaves the current journal/trash unchanged. After a conflict, obtain a new
comparison before submitting another restore; replacing its expected version
without reviewing it would discard another GM's edits. History/trash reads and
writes recheck current campaign GM membership, including receipt retries.

Owner-only operations and campaign management remain checked on the server. These methods use session cookies and acquire a CSRF token before writes. They do not provide an API-key authentication scheme. Account/admin payloads are defined by the corresponding app views and tests; never place credentials in module source.

The Inside header uses owner-only `POST /api/admin/updates/notification` with an empty JSON body and the normal CSRF token. Its compact response includes `status`, `available`, installed/available versions and labels, `channel`, `checkedAt` and the internal Updates URL. It reuses the 24-hour discovery cache; concurrent stale checks return `checking` while one request refreshes metadata. It does not start installation or expose release artifacts or internal errors.

Owner-only `GET /api/marketplace?latest=1` returns one compatible, non-revoked release per package ID, selecting the highest numeric `X.Y.Z` version after validating the full signed catalog and applying its revocations. Systems and Modules use this selection for installation. Without `latest=1`, the endpoint continues returning all compatible non-revoked releases; exact-version installation remains available.

`GET /api/admin/status` includes `updates.installedRelease` with `version`, full `name`, `notes`, canonical GitHub `url` and `source` (`bundled`, `published` or `metadata`). Explicit update-check responses include the same presentation. Bundled notes are available without discovery or network access and are not stored in the update cache. Notes are bounded to 128 KiB of UTF-8; numeric update versions and comparison rules remain independent of the display name.

### Domain events

Subscribe using `api.events.on(name, handler)`, which returns an unsubscribe function. Event subscriptions are disposed with their API lifetime. Supported names:

```text
actors.changed       tokens.changed       maps.changed
maps.layersChanged   journals.changed     items.changed
combat.changed       cards.changed        audio.changed
compendiums.changed  chat.changed         chat.message
table.presence       table.lobbyChanged   clocks.changed   clues.changed
mindmaps.changed
```

Collection change subscriptions perform an authorized HTTP read initially, on matching socket invalidations, and on reconnect. Concurrent invalidations are coalesced; they do not carry every intermediate mutation. Actor/token/map/journal callbacks receive the projected state plus table/scene identity; item/combat/card/audio/compendium/clock/clue/mindmap callbacks receive `{module, state, tableId, sceneId?}`. `chat.changed`, `chat.message`, presence, and lobby callbacks forward matching socket payloads rather than automatically reading an initial snapshot. Read their initial state separately as needed.

Subscriptions use the current page's socket event source. A `forTable` handle on `/inside`, or one targeting another table, can make HTTP requests but does not create a socket for that table. Do not assume it receives ongoing changes. Callbacks should be synchronous; start async work explicitly with error handling. The older mount-level `events` interface has different names and delivery caveats documented in the [module guide](modules.md#assets-persistence-and-events).

## Original schema-checked operations

Use the mount's or lifecycle/customization context's `host.call` for the following names. Input/output/event/context schemas are linked from [`contracts/registry.json`](../../gravewright/modules/contracts/registry.json); lifecycle/storage semantics are in [`contracts/api.json`](../../gravewright/modules/contracts/api.json).

| Operation | Scope | Purpose |
| --- | --- | --- |
| `actor.list`, `actor.read` | Table | Read visible actor summaries/documents |
| `actor.create`, `actor.update`, `actor.delete` | Table | Create, patch supplied fields, or logically delete with revision checks |
| `actor.data.read`, `actor.data.update` | Table | Read/replace the full system data object |
| `token.read`, `token.move` | Scene | Read a token or move its center in scene pixels |
| `token.data.read`, `token.data.update` | Scene | Read/replace linked actor data or unlinked token snapshot data |
| `asset.list`, `asset.upload`, `asset.download` | Table | List/upload/download current-system PDF templates |
| `actor.image.upload` | Table | Upload an actor portrait/token image with native validation |
| `card.asset.upload` | Table | Upload a reusable card front/back image; GM only |
| `locale.apply` | Local | Apply a client language catalog for the mount lifetime |

```javascript
const actor = await host.call("actor.read", { id: actorId });
const data = await host.call("actor.data.read", { id: actorId });
// Check the operation's schema for revision and replacement fields before writing.
```

Scene operations require a mounted scene; a scene ID in an arbitrary payload cannot create that authority. `actor.data.update` and `token.data.update` replace whole data objects, including nested arrays/objects; `null` is a value, not a delete instruction. `actor.update` changes only supplied patch fields. Use the exact schema for each revision field; SDK revisions are not interchangeable with domain API entity versions.

Binary uploads take a real `File`/`Blob` in `payload.file`, use authenticated multipart transport, and derive metadata on the server. PDF template upload is GM-only and limited to 10 MiB. Downloads return `{blob, name, contentType, size}`. `options.onProgress` reports completion for this fetch-based SDK transport, not streaming progress. `options.signal` is supported; cancellation cannot undo a committed mutation.

`card.asset.upload` is an additive SDK 1.0 operation available in Gravewright 0.2.3 and later. It accepts `purpose: "card_front" | "card_back"` and a `File`/`Blob`, validates PNG/JPEG/WebP up to 10 MiB and 16 megapixels through the native card uploader, and returns `{assetId}`. The asset belongs to the authenticated GM and current table. Reuse it in `api.cards.define` as `front_asset_id` or `default_back_asset_id`; deck instances reference the same stored image. Uploads create new assets and have no retry receipt: persist returned IDs before starting another import. No database migration or SDK major-version change is required.

```javascript
const { assetId } = await context.host.call("card.asset.upload", {
  file: new File([await context.assets.bytes("cards/front.png")], "front.png", { type: "image/png" }),
  purpose: "card_front",
});
const definition = await context.api.cards.define({
  name: "My deck", cards: [{ name: "One", front_asset_id: assetId }],
});
await context.api.cards.instantiate({ deck_definition_id: definition.deck.id });
```

| Public module error | Interpretation |
| --- | --- |
| `not_found` | Resource missing or unavailable to this context |
| `permission_denied` | Authenticated user cannot perform the action |
| `invalid_data` | Payload/schema/path/value validation failed |
| `conflict` | Entity, storage, activation revision or registration conflict |
| `unavailable` | Unknown/unsupported operation, incompatible SDK, or service failure (HTTP 503), including a required system provider that is not enabled |
| `cancelled` | Caller cancelled live work |
| `stale_context` | Mount/scene/activation context is no longer valid |

## Python interface

Initialize Django before importing domain facades. `manage.py shell`, Django views, and app startup already do this. In standalone scripts, set `DJANGO_SETTINGS_MODULE=config.settings` and call `django.setup()` first. Do not run database queries during module import or `AppConfig.ready()`.

`Context(campaign_id, user_id)` normalizes UUIDs and is immutable; constructing it does not authorize an action. `Context.from_request(request, campaign_id)` checks authentication and membership. Service calls continue to recheck current permissions. Use authenticated identity, not a client-supplied user ID.

```python
from uuid import uuid4
from api import Context, actors

# Inside an authenticated Django view; campaign_id comes from the route.
context = Context.from_request(request, campaign_id)
visible = actors.state(context.campaign_id, context.user_id)
created = actors.command(
    context.campaign_id,
    context.user_id,
    "actor.create",
    {"name": "Example actor"},
    uuid4(),
)
```

Public imports and signatures, with `campaign_id`/`user_id` denoting identifiers even where the implementation's parameter names are shorter:

| Import | Callable signatures |
| --- | --- |
| `api` | `API_VERSION == "1.0"`, `capabilities()`; the Python marker is independent of browser API `1.2.0` and SDK `1.0.0`. [Catalog implementation](../../api/__init__.py) |
| `api.campaigns` | `management(campaign_id, user_id)`; [GM-only campaign overview](../../gravewright/campaigns/management.py) and [management guide](campaign-management.md) |
| `api.actors` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `sheet(campaign_id, user_id, actor_id, token_id=None)` |
| `api.tokens` | `state(campaign_id, user_id, map_id)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.maps` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `layer_state(campaign_id, user_id, scene_id)` |
| `api.map_builder` | Editable project catalog, revisions, generation, scene updates and adoption; [public exports](../../api/map_builder.py), [project signatures](../../gravewright/maps/builder_services.py), [adoption signature](../../gravewright/maps/builder_import.py) |
| `api.map_blueprints` | Campaign templates, scene networks, controls and rehearsals; [public exports and owning signature references](../../api/map_blueprints.py) |
| `api.universal_vtt` | Native map import/export; [public exports](../../api/universal_vtt.py) and [call signatures](../../gravewright/maps/universal_vtt.py) |
| `api.pdf_system` | Sheets, mapping configuration, diagnostics, saved rolls and mapping templates; [public exports](../../api/pdf_system.py) and [call signatures](../../gravewright/pdf_system/public.py) |
| `api.systems` | `capabilities(campaign_id, user_id)`, `call(campaign_id, user_id, operation, payload, request_id=None, *, scene_id=None)`, `register_api(system_id, operations)`; [provider contract](../../gravewright/campaigns/system_api.py) |
| `api.library` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, payload, request_id)`; [native library service](../../gravewright/maps/library_services.py) |
| `api.ownership` | `state(campaign_id, user_id, kind, resource_id)`, `command(campaign_id, user_id, kind, resource_id, payload, request_id)`; [GM document, folder and page service](../../gravewright/table/permission_services.py) |
| `api.journals` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `resources(campaign_id, user_id, **search)`, `resolve(campaign_id, user_id, reference)` |
| `api.clocks` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)`; actions `create`, `update`, `advance`, `reset`, `delete` |
| `api.clues` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)`; actions `create`, `update`, `advance`, `reset`, `reveal`, `hide`, `delete` |
| `api.mindmaps` | `state(campaign_id, user_id, scene_id=None)`, `read(campaign_id, user_id, mindmap_id, scene_id=None)`, `resources(campaign_id, user_id, *, query='', kinds=None, limit=80, scene_id=None)`, `resolve(campaign_id, user_id, reference)`, `command(campaign_id, user_id, action, data, request_id)`; actions `create`, `update`, `node`, `delete` |
| `api.items`, `api.combat`, `api.cards`, `api.audio`, `api.compendiums` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.combat.register_provider` | Trusted system callback registration from `AppConfig.ready()`; see [system combat providers](modules.md#system-combat-providers) |
| `api.resources` | `state(campaign_id, user_id, name, scene_id=None, preview_token_id=None)`, `command(campaign_id, user_id, name, action, data, request_id)` |
| `api.chat` | `history(campaign_id, user_id, map_id=None)`, `send(campaign_id, user_id, text, request_id, map_id=None)`, `remove(campaign_id, user_id, message_id=None)` |
| `api.dice` | `evaluate(expression, repeat=1, *, random_source=None)`, `roll(campaign_id, user_id, expression, request_id, *, repeat=1, label="", visibility="public", map_id=None)` |
| `api.table` | `search(campaign_id, user_id, query)`, `lobby(campaign_id, user_id)`, `update_lobby(campaign_id, user_id, payload)` |
| `api.events` | `Change`, `resource_changed` |
| `api.errors` | `AuthError`, `JournalError`, `MapError`, `RollError` |

Use positional arguments as illustrated where facade parameter names vary. `resources` selects the native `items`, `combat`, `cards`, `audio`, `compendiums`, `clocks`, `clues`, or `mindmaps` domain by name. `dice.evaluate` computes locally; `dice.roll` stores/publishes a table roll. Python exceptions preserve their original service types/codes rather than the browser's seven-code normalization.

### Transactions and server hooks

Public command wrappers retain native transactions, permission checks, version checks, deduplication receipts where implemented, and notifications after commit. An enclosing transaction rollback produces neither the committed write nor its queued notifications. Direct ORM writes bypass this command behavior and should not be used as an equivalent mutation API.

Connect trusted server hooks to the Django signal:

```python
from api.events import resource_changed

def observe_change(sender, change, **kwargs):
    # sender is the resource name; change contains identifiers, not a snapshot.
    print(change.resource, change.action, change.request_id)

resource_changed.connect(
    observe_change,
    dispatch_uid="example.observe-change",
    weak=False,
)
```

Register receivers once in your explicitly installed app's `AppConfig.ready()`. `Change` contains `campaign_id`, `user_id`, `resource`, `action`, and `request_id`. The signal is sent after commit through `send_robust`; receiver failures are logged and do not roll back committed commands. It runs inside the serving process and is not a durable queue or a replayable audit log. Keep handlers short; do not forward identifiers or subsequently loaded private data to unfiltered browser audiences. The native chat and dice publishing paths have their own audience-aware notifications and are not a promise that every write emits `resource_changed`.

## Transport and maintenance

The host browser domain endpoint is `POST /api/tables/<table_id>/api`; installed modules use `POST /api/tables/<table_id>/modules/<module_id>/api`. Both receive `{domain, method, payload, requestId?}` and return `{value}`. Module calls also carry `mountId`, `moduleSetRevision`, and optional `sceneId`; the bridge acquires a lease before calling. Binary domain methods use the respective `/files` suffix, with JSON metadata in multipart `metadata` and the file in `file`; download calls return bytes. The older schema API uses the same module prefix with `/call` and a `{name, payload, ...context}` envelope. These URLs describe the implementation for maintainers; module code should use its provided APIs.

After changing the domain method registry, run:

```sh
uv run --locked python scripts/generate_frontend_api.py
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.table.tests.test_public_api gravewright.modules
node --test tests/modules/*.test.mjs
```

`frontend-contract.js` is generated from `frontend.json`; update the source registry first. Keep native frontend calls, module-scoped calls, and public Python calls consistent in authorization, payload semantics and post-commit behavior. For new original SDK operations, update the schemas, registry, supported operation constants, dispatcher, and tests together; the repository has no general-purpose generator for all of those files.

## Module translations (Translator)

Modules receive `context.i18n` and `context.api.i18n`. Register catalogs in the
activation's `start(context)`, then translate through the API supplied to a surface:

```javascript
export default {
  start({ i18n }) {
    i18n.register({
      en: { 'sheet.title': 'Character sheet', 'sheet.greeting': 'Welcome, {name}' },
      'pt-BR': { 'sheet.title': 'Ficha de personagem', 'sheet.greeting': 'Boas-vindas, {name}' },
      es: { 'sheet.title': 'Ficha de personaje', 'sheet.greeting': 'Bienvenido, {name}' },
    });
  },
  register({ register }) {
    register('actor.directory', async ({ root, api }) => {
      root.setAttribute('translate', 'no');
      root.textContent = api.i18n.t('sheet.greeting', { name: 'Arin' });
    });
  },
};
```

Catalogs can also be loaded with `await context.assets.json('locales/messages.json')`.
`locale` follows the user's interface language. Lookup falls back from the exact
locale to its base language, then English, then the source key. `t(key, params)`
substitutes named or numbered placeholders as plain text. Use `textContent` for
rendering. `has(key)` checks coverage; `number(value, options)` uses
`Intl.NumberFormat`; `onChange(handler)` returns an unsubscribe function for locale
events and registration/removal of catalogs in that namespace. Changing the interface language currently reloads the page, preserving the
table URL.

Catalogs are isolated by module ID and shared across that module's contexts on the
page. `register` returns a disposer and also removes its catalog when its owning
context is disposed. Partial translations require an English fallback for each key
and matching placeholders. Register during activation so surface mounts can reuse
the catalog. No HTTP permission or external translation service is needed. Without
Translator/language packs, the interface uses English. The native
`gravewright.i18n` adapter resolves host catalogs; installed modules use their
supplied context.
