# Compendiums / content libraries

## Architectural diagnosis

### Foundry reference

Foundry models one pack as a `CompendiumCollection` identified by the providing
package plus pack name. Its metadata declares package type/name, label, document
type, system, ownership and lock state. Documents use UUIDs of the form
`Compendium.<pack>.<DocumentName>.<id>`; embedded UUID segments preserve links.

The client initially owns metadata and a lightweight index. `getIndex(fields)`
requests only missing fields and caches the resulting index; `getDocument(id)`
loads a complete document on demand and evicts loaded instances after a TTL.
The global `DocumentIndex` indexes world collections and compendium indexes in
word trees. Directory search, type filters and a result limit operate on these
indexes rather than full documents.

World documents and pack documents share document classes, sheets and drag data,
but have different collections and persistence targets. `toCompendium` strips or
normalizes world-only data; `fromCompendium` prepares a campaign-owned copy.
Canonical UUIDs resolve links independently of display names. Import may retain
IDs to preserve a graph. Folders and Adventure documents support graph-shaped
bulk import/export.

The server remains authoritative for CRUD. World packs can be configured;
system/module packs are normally locked to avoid package updates overwriting
local edits. Ownership gates visibility, while lock/package provenance gates
writes. Pack metadata is supplied by world/system/module manifests. Package and
core migrations prepare stored documents when schemas or generations change.
Assets remain paths/UUID references and therefore require the providing package
to remain available unless copied during an export/import workflow.

Useful product behavior to retain: typed libraries, canonical identities, small
indexes, lazy documents, shared renderers, drag-copy semantics, explicit
read-only state, package provenance, folders, and server-side authorization.

Behavior not copied: a mutable package pack as campaign state, client-side
permission as authority, implicit global access to package files, Foundry's
document-class globals, or a storage/backend contract exposed to packages.

### Gravewright before this change

SDK 1 already had the right primitive: `provides.contentPacks`, the
`content.packs` capability, package activation/dependency validation, safe
package paths, localized labels, a read-only JSON source, campaign copy-based
imports, drag sources, Actor/Item/Journal services, and import audit rows.
Per-pack `none/read/owner` access is applied by the game endpoints and the UI
reuses Actor/Item sheets for read-only previews.

The important gaps were: every read decoded and returned the complete pack;
there was no pagination or pack-local search; index and document payload were
the same object; identity was the loose `(package, pack, id)` triple with no
portable reference string; manifest pack types encoded ruleset concepts such as
`spell`; and package authors could not declare a custom document kind without a
core change. Import adapters currently exist only for Actor, Item and Journal.
The existing import audit is pack-level, so it cannot yet drive per-document
update/conflict UX.

## Native Gravewright model

The public identity is:

`gwpack://<package-id>/<pack-id>/<document-id>`

A pack declaration retains all SDK 1 fields and optionally adds:

```json
{
  "id": "lore",
  "type": "document_pack",
  "documentType": "ruleset.clue",
  "path": "content/lore.index.json",
  "formatVersion": 2,
  "indexFields": ["name", "type", "image", "tags"]
}
```

Format 1 remains an `{ "entries": [...] }` file. Format 2 is an
`{ "index": [...] }` file; an index row may contain
`"document": "content/lore/<id>.json"`. Paths are resolved by the existing
safe package-path boundary. A ruleset-defined `documentType` is namespaced data,
not a new core class or capability.

Read flow:

1. Resolve installed, enabled and campaign-active package.
2. Apply per-pack access on the server.
3. Read the index, project the declared lightweight fields, search, then page
   (default 50, hard maximum 200).
4. Attach `document_type` and canonical `ref` to each result.
5. Only `get_entry`, preview, drop resolution or import loads the referenced
   document JSON.
6. Cache parsed JSON by path and modification time in a bounded LRU; a package
   update changes mtime and invalidates the entry without package hooks.

Import is copy semantics. The source document is immutable package content; the
destination is validated and created through its existing campaign service.
Local edits therefore never mutate the library. Actor/Item/Journal adapters are
kept, and future Scene/Card/Deck/Asset adapters must use their public services
rather than branching into persistence internals.

## Compatibility and remaining work

### VTT component coverage

| Component | Library document | Campaign materialization | Drag target |
|---|---:|---:|---|
| Actor / sheet | `actor_pack` | Actor Core + Sheet Data | Actor directory/folder |
| Item | `item_pack` (`spell_pack` legacy) | Item Core + Sheet Data | Item directory/folder |
| Journal / handout | `journal_pack` | Journal document | Journal directory/folder |
| Scene | `scene_pack` | Scene metadata | Scene directory/group |
| Deck / cards | `deck_pack` / `card_pack` | Assets + deck definition + instance | Deck panel |
| Package assets | `provides.assets` | Existing asset-package importer | Asset library workflow |
| Ruleset-defined document | `document_pack` + namespaced `documentType` | Requires an explicit public adapter | Adapter-defined |

Tokens, card instances, hands/piles, combat state, chat messages, fog, active
effects in progress, scene navigation and current audio playback are deliberately
not importable top-level compendium documents. They are mutable runtime state or
embedded state. A Scene or Actor pack may eventually carry validated embedded
templates for some of them, but importing them independently would violate
ownership and reference integrity.

Roll-table, macro and playlist pack names remain reserved in the manifest. They
do not claim campaign materialization until Gravewright has corresponding public
document services; accepting a declaration is not treated as adapter coverage.

There is no SDK version bump and no migration for the index/lazy-read change.
All existing manifests and inline packs remain valid. The new metadata is
additive. Existing `actor_pack`, `item_pack`, `spell_pack`, `journal_pack`, table
and condition names remain accepted; neutral core types and namespaced custom
document types are now accepted as well.

Before synchronization can be promised, add per-document provenance containing
source ref, source content hash/version, destination document identity, imported
snapshot hash and timestamp. A sync operation must compare source, imported
snapshot and local state (three-way), never overwrite local edits silently.
Also pending are adapter registration for Scene/Card/Deck/Asset/Table, graph
import with reference rewriting, asset bundling policy, database/FTS indexes for
catalogues too large for an in-process JSON index, and locale selection from the
request rather than the current English fallback.
