# Public API reference

[Documentation index](../README.md) · [Português](../pt-BR/api.md) · [Module guide](modules.md)

Gravewright has three related interfaces. They use the same native permission checks, but have different version markers, signatures, and result shapes:

| Interface | Entry point | Current marker | Intended caller |
| --- | --- | --- | --- |
| Python | `from api import actors, ...` | `api.API_VERSION == "1.0"` | Trusted server integrations with initialized Django |
| Browser domain API | `window.gravewright`, or a module context's `api` | `api.version == "1.1.0"` | Native frontend code and browser extensions |
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
| `maps` | `update`, `move`, `delete`, `activate`, `updateObjects`, `createFolder`, `updateFolder`, `deleteFolder` |
| `journals` | `create`, `update`, `delete`, `move`, `setAccess`, `present`, `createFolder`, `updateFolder`, `moveFolder`, `deleteFolder`, `setStatus`, `addQuest`, `removeQuest`, `pinQuest`, `reorderQuests`, `roll`, `reset` |
| `items` | `create`, `update`, `delete`, `duplicate`, `setPermissions`, `createFolder`, `updateFolder`, `deleteFolder` |
| `combat` | `add`, `remove`, `configure`, `setInitiative`, `rollInitiative`, `toggle`, `moveUp`, `moveDown`, `setTurn`, `nextRound`, `previousRound`, `start`, `stop`, `nextTurn`, `previousTurn` |
| `cards` | `define`, `instantiate`, `create`, `draw`, `shuffle`, `reset`, `deleteDeck`, `discard`, `return`, `give`, `place`, `take`, `flip`, `move` |
| `audio` | `updateTrack`, `deleteTrack`, `createPlaylist`, `updatePlaylist`, `deletePlaylist`, `createSpatialSound`, `updateSpatialSound`, `deleteSpatialSound`, `play`, `pause`, `stop`, `seek`, `setVolume`, `startScore`, `pauseScore`, `resumeScore`, `stopScore`, `nextScore`, `previousScore` |
| `compendiums` | `create`, `configure`, `read`, `delete`, `add`, `remove`, `import`, `setPermissions` |

Additional forms:

| Method | Behavior |
| --- | --- |
| `actors/tokens/maps/journals/items.list(payload, options)` | Return the collection from the authorized `state` response |
| `actors/tokens/maps/journals/items.get(id, payload, options)` | Find an item in that projected collection, or `not_found` |
| `actors.update(id, changes, options)` | Convenience overload; reads current version if `changes.version` is absent |
| `actors.sheet(id, payload, options)` | Read a sheet; supports token context in payload |
| `maps.layers(payload, options)` | Read authorized scene layers |
| `chat.history(payload, options)` | Read visible messages |
| `chat.send(payload, options)` | Send `{text, sceneId?}` through native chat processing |
| `chat.remove(id, options)` / `chat.clear(options)` | Delete one/all visible-domain messages under native moderation rules |
| `dice.roll(expression, payload, options)` | Roll and publish; payload supports `repeat`, `label`, `visibility`, scene context |
| `table.search(query, options)` | Search resources visible to the current user |
| `table.lobby(options)` / `table.updateLobby(payload, options)` | Read/change native lobby state |

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

`options.signal` cancels pending work. A disposed context produces `stale_context`; explicit cancellation produces `cancelled` in scoped module operations. Error handling should inspect `error.code`, not translated text. Global HTTP adapters can additionally expose transport/authentication errors from the underlying endpoint.

### Account, campaign, owner and module adapters

These are available on the global `gravewright` object, not on the module's domain-only `api`:

| Adapter | Methods |
| --- | --- |
| `accounts` | `status`, `session`, `login`, `register`, `setup`, `logout`, `update` |
| `campaigns` | `list`, `create`, `update(id, payload)`, `join(code)`, `remove(id, code)`, `invite(id, payload)`, `rulesets` |
| `administration` | `status`, `diagnostics`, `settings`, `updateSettings(section, payload)` |
| `modules` | `list`, `catalog`, `status`, `install(payload)`, `state(tableId)`, `configure(tableId, payload)` |

Owner-only operations and campaign management remain checked on the server. These methods use session cookies and acquire a CSRF token before writes. They do not provide an API-key authentication scheme. Account/admin payloads are defined by the corresponding app views and tests; never place credentials in module source.

### Domain events

Subscribe using `api.events.on(name, handler)`, which returns an unsubscribe function. Event subscriptions are disposed with their API lifetime. Supported names:

```text
actors.changed       tokens.changed       maps.changed
maps.layersChanged   journals.changed     items.changed
combat.changed       cards.changed        audio.changed
compendiums.changed  chat.changed         chat.message
table.presence       table.lobbyChanged
```

Collection change subscriptions perform an authorized HTTP read initially, on matching socket invalidations, and on reconnect. Concurrent invalidations are coalesced; they do not carry every intermediate mutation. Actor/token/map/journal callbacks receive the projected state plus table/scene identity; item/combat/card/audio/compendium callbacks receive `{module, state, tableId, sceneId?}`. `chat.changed`, `chat.message`, presence, and lobby callbacks forward matching socket payloads rather than automatically reading an initial snapshot. Read their initial state separately as needed.

Subscriptions use the current page's socket event source. A `forTable` handle on `/inside`, or one targeting another table, can make HTTP requests but does not create a socket for that table. Do not assume it receives ongoing changes. Callbacks should be synchronous; start async work explicitly with error handling. The older mount-level `events` interface has different names and delivery caveats documented in the [module guide](modules.md#assets-persistence-and-events).

## Original schema-checked operations

Use the mount's `host.call` for the following names. Input/output/event/context schemas are linked from [`contracts/registry.json`](../../gravewright/modules/contracts/registry.json); lifecycle/storage semantics are in [`contracts/api.json`](../../gravewright/modules/contracts/api.json).

| Operation | Scope | Purpose |
| --- | --- | --- |
| `actor.list`, `actor.read` | Table | Read visible actor summaries/documents |
| `actor.create`, `actor.update`, `actor.delete` | Table | Create, patch supplied fields, or logically delete with revision checks |
| `actor.data.read`, `actor.data.update` | Table | Read/replace the full system data object |
| `token.read`, `token.move` | Scene | Read a token or move its center in scene pixels |
| `token.data.read`, `token.data.update` | Scene | Read/replace linked actor data or unlinked token snapshot data |
| `asset.list`, `asset.upload`, `asset.download` | Table | List/upload/download current-system PDF templates |
| `actor.image.upload` | Table | Upload an actor portrait/token image with native validation |
| `locale.apply` | Local | Apply a client language catalog for the mount lifetime |

```javascript
const actor = await host.call("actor.read", { id: actorId });
const data = await host.call("actor.data.read", { id: actorId });
// Check the operation's schema for revision and replacement fields before writing.
```

Scene operations require a mounted scene; a scene ID in an arbitrary payload cannot create that authority. `actor.data.update` and `token.data.update` replace whole data objects, including nested arrays/objects; `null` is a value, not a delete instruction. `actor.update` changes only supplied patch fields. Use the exact schema for each revision field; SDK revisions are not interchangeable with domain API entity versions.

Binary uploads take a real `File`/`Blob` in `payload.file`, use authenticated multipart transport, and derive metadata on the server. PDF template upload is GM-only and limited to 10 MiB. Downloads return `{blob, name, contentType, size}`. `options.onProgress` reports completion for this fetch-based SDK transport, not streaming progress. `options.signal` is supported; cancellation cannot undo a committed mutation.

| Public module error | Interpretation |
| --- | --- |
| `not_found` | Resource missing or unavailable to this context |
| `permission_denied` | Authenticated user cannot perform the action |
| `invalid_data` | Payload/schema/path/value validation failed |
| `conflict` | Entity, storage, activation revision or registration conflict |
| `unavailable` | Unknown/unsupported operation, incompatible SDK, or service failure |
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
| `api.actors` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `sheet(campaign_id, user_id, actor_id, token_id=None)` |
| `api.tokens` | `state(campaign_id, user_id, map_id)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.maps` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)`, `layer_state(campaign_id, user_id, scene_id)` |
| `api.journals` | `state(campaign_id, user_id)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.items`, `api.combat`, `api.cards`, `api.audio`, `api.compendiums` | `state(campaign_id, user_id, scene_id=None)`, `command(campaign_id, user_id, action, data, request_id)` |
| `api.resources` | `state(campaign_id, user_id, name, scene_id=None, preview_token_id=None)`, `command(campaign_id, user_id, name, action, data, request_id)` |
| `api.chat` | `history(campaign_id, user_id, map_id=None)`, `send(campaign_id, user_id, text, request_id, map_id=None)`, `remove(campaign_id, user_id, message_id=None)` |
| `api.dice` | `evaluate(expression, repeat=1, *, random_source=None)`, `roll(campaign_id, user_id, expression, request_id, *, repeat=1, label="", visibility="public", map_id=None)` |
| `api.table` | `search(campaign_id, user_id, query)`, `lobby(campaign_id, user_id)`, `update_lobby(campaign_id, user_id, payload)` |
| `api.events` | `Change`, `resource_changed` |
| `api.errors` | `AuthError`, `JournalError`, `MapError`, `RollError` |

Use positional arguments as illustrated where facade parameter names vary. `resources` selects the native `items`, `combat`, `cards`, `audio`, or `compendiums` domain by name. `dice.evaluate` computes locally; `dice.roll` stores/publishes a table roll. Python exceptions preserve their original service types/codes rather than the browser's seven-code normalization.

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

The host browser domain endpoint is `POST /api/tables/<table_id>/api`; installed modules use `POST /api/tables/<table_id>/modules/<module_id>/api`. Both receive `{domain, method, payload, requestId?}` and return `{value}`. Module calls also carry `mountId`, `moduleSetRevision`, and optional `sceneId`; the bridge acquires a lease before calling. The older schema API uses the same module prefix with `/call` and a `{name, payload, ...context}` envelope. These URLs describe the implementation for maintainers; module code should use its provided APIs.

After changing the domain method registry, run:

```sh
uv run --locked python scripts/generate_frontend_api.py
uv run --locked python manage.py test gravewright.table.tests.test_frontend_api gravewright.table.tests.test_public_api gravewright.modules
node --test tests/modules/*.test.mjs
```

`frontend-contract.js` is generated from `frontend.json`; update the source registry first. Keep native frontend calls, module-scoped calls, and public Python calls consistent in authorization, payload semantics and post-commit behavior. For new original SDK operations, update the schemas, registry, supported operation constants, dispatcher, and tests together; the repository has no general-purpose generator for all of those files.
