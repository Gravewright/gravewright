# Writing and operating modules

[Documentation index](../README.md) · [Português](../pt-BR/modules.md) · [API reference](api.md)

Gravewright installs signed ZIP packages containing browser JavaScript or trusted Django apps, assets, and a JSON manifest. A server owner installs releases; a campaign GM chooses browser modules and interface replacements for a table. Django apps are activated separately for the whole server.

Third-party module licensing is described in the [licensing policy](../../LICENSING.md). The manifest records the module author's chosen license; installation does not change it.

## Host compatibility

VTT **0.2.1** is the first public release with the `system.combat` provider
contract, installed `content.compendiums`, native `api.ui.openModal`, and the
asynchronous sheet-save closing lifecycle documented below. These are additive
host features; the SDK contract version remains **1.0.0**. An SDK version range
alone does not distinguish VTT 0.2.0 from 0.2.1: packages using these features
must document VTT 0.2.1 as their minimum and check optional browser APIs before
calling them. VTT 0.2.0 already introduced private `context.i18n` catalogs;
0.2.1 also resolves translated document-type labels in native directories.

Game rules, choices, sheet layouts and game translation catalogs belong to the
installed system or its trusted companion app. The core validates descriptors,
authorization and storage without interpreting a game's rules. See the
[0.2.1 release notes](../releases/0.2.1.md) for installation and upgrade steps.

## Trust and installation boundaries

Browser modules execute as ES modules in the application's main browser page. There is no iframe sandbox, Shadow DOM, or capability-based JavaScript isolation. Modules can interact with the page and browser environment. A signature authenticates the configured publisher and archive bytes; it does not prove that code is safe. Configure signing keys for publishers whose code you are prepared to run in users' sessions.

The supported host interfaces enforce the authenticated user's campaign membership, native resource permissions, module activation revision, and mount lease. Those checks remain on the server. Modules receive no Python execution, SQL interface, or server-side service loader through this mechanism. Integrations installed separately as Django/Python code are trusted server code; see the [Python API](api.md#python-interface).

Implementation entry points:

| File | Responsibility |
| --- | --- |
| [`packages.py`](../../gravewright/modules/packages.py) | Signatures, archive validation, immutable installation, activation revisions, JSON storage |
| [`models.py`](../../gravewright/modules/models.py) | Installed releases, table activation, stored values, mount leases |
| [`views.py`](../../gravewright/modules/views.py) | Owner/GM routes, downloads, leases, assets, schema-checked calls |
| [`frontend.py`](../../gravewright/modules/frontend.py) | Shared browser domain API and authenticated dispatch |
| [`module-runtime.js`](../../gravewright/modules/static/gravewright_modules/module-runtime.js) | Import, start/register/stop, mounting, replacement, disposal |
| [`browser-bridge.js`](../../gravewright/modules/static/gravewright_modules/browser-bridge.js) | Package assets, storage, leased operations and domain API |
| [`workspace.js`](../../gravewright/modules/static/gravewright_modules/workspace.js) | Attach extension surfaces to the live table and reconcile activation |

## Minimal browser package

Create this directory outside the source tree, or in an ignored development directory:

```text
example.actor-counter/
├── manifest.json
├── main.js
├── styles.css
└── LICENSE.txt
```

`manifest.json`:

```json
{
  "id": "example.actor-counter",
  "name": "Actor counter",
  "version": "1.0.0",
  "sdk": { "requires": ">=1.0.0 <2.0.0", "tested": "1.0.0" },
  "entry": "main.js",
  "description": "Shows the number of actors visible to the current user.",
  "author": "Your name",
  "license": "GPL-3.0-only"
}
```

Choose your actual license and include its text in `LICENSE.txt`. An extension's license need not match this illustrative value; see the licensing policy. The manifest schema rejects unknown keys and requires every field shown. IDs must contain at least one dot or hyphen, begin with a lowercase letter, and use lowercase letters/digits in their components. Versions use three numeric components, without prerelease/build suffixes. SDK ranges support whitespace-separated comparisons such as `>=1.0.0 <2.0.0`; `^`, `~`, wildcards, and `||` are not supported. The package loader currently checks SDK **1.0.0**; the separate domain API reports **1.1.0**.

`main.js`:

```javascript
export default {
  start({ styles }) {
    styles.use("styles.css");
  },

  register({ register }) {
    register("actor.directory", async ({ root, api, signal }) => {
      const label = root.ownerDocument.createElement("p");
      label.className = "example-actor-counter";
      root.append(label);

      const render = actors => {
        if (!signal.aborted) label.textContent = `Visible actors: ${actors.length}`;
      };

      render(await api.actors.list());
      api.events.on("actors.changed", snapshot => render(snapshot.actors));
    });
  },

  stop() {
    // The host disposes styles, roots, subscriptions, and scoped API handles.
  }
};
```

`styles.css`:

```css
.gw-module-root[data-module-id="example.actor-counter"] .example-actor-counter {
  margin: 0.5rem;
  font-weight: 600;
}
```

Create the ZIP with files at its root, not under an extra package directory:

```sh
cd example.actor-counter
python -m zipfile -c ../actor-counter-1.0.0.zip manifest.json main.js styles.css LICENSE.txt
```

This produces a package ready for signing. There is no unsigned package upload endpoint or file-watching module development server in this repository. The [module tests](../../gravewright/modules/tests.py) and [browser integration fixture](../../tests/e2e/frontend_api.py) show isolated signing/install fixtures for development.

## Declaring an installed system

A package can also provide a campaign system by adding `system` to its manifest:

```json
"system": {
  "actorTypes": [
    { "id": "character", "label": "Character" },
    { "id": "npc", "label": "Non-player character" }
  ],
  "itemTypes": [{ "id": "gear", "label": "Gear" }]
}
```

Optionally declare initiative for the native combat manager:

```json
"combat": { "formula": "1d20 + @combat.initiative", "manualInput": "number" }
```

This object belongs inside `system`. The formula accepts up to 120 characters
using the native dice grammar. `@field.path` references read finite numeric
values from the actor sheet or independent token snapshot; missing fields are
zero, while nonnumeric values are rejected. The system sheet must persist its
calculated modifiers. Combat uses the table's selected installed release.
`showRoll` optionally hides native initiative roll controls when `false`.
`manualInput` accepts `number` or `text` and applies if scene configuration
disables the formula. A manifest cannot supply executable JavaScript or Python.
For live system rules, see [system combat providers](#system-combat-providers).

The system ID and title come from the package's `id` and `name`. Each package declares one system; it cannot replace an identity registered by a bundled provider. Declare at least one actor type; item types are optional. Type IDs must be unique within each list, start with a lowercase letter, and contain only lowercase letters, digits, underscores or hyphens (80 characters maximum). Each list supports up to 64 entries with labels of 1–120 characters.

Type descriptors optionally accept `labelKey` (a translation key up to 120
characters) and `icon` (an icon name up to 80 characters). Actor and item directories
resolve `labelKey` in the package's own catalog registered with
`context.i18n.register`, falling back to `label`. Available item icons include
`Backpack`, `Sword`, `ShieldCheck`, `Scroll`, `Sparkle` and `User`; unavailable
names use the default icon. For example, `{"id":"component","label":"Component",
"labelKey":"types.component","icon":"Backpack"}`. The host keeps no game-type
label or icon mappings. `i18n.onChange` consumers also update when their namespace
catalog is registered or disposed.

After a signed installation, the system appears in Systems, `/api/rulesets`, and the campaign form. The catalog uses the newest compatible, non-revoked installed version per package, ordered by numeric version. Ordinary modules without `system` remain available under Installed modules. Existing campaigns can retain an unavailable system when editing their details, but it cannot be selected for a new campaign.

Saving a campaign with an installed system selects its document types and activates its browser package. The existing exact release is retained when already active; switching systems removes the previous system package while preserving unrelated modules and replacement preferences. Tables use the document types of that exact activated release, or the latest installed version if none is activated. Actor data keeps the existing native document structure; module-specific data uses the supported module storage and document APIs. Installing a new version does not automatically change a table's activated release.

## System combat providers

The core never selects a named game-rule profile. A trusted server extension
registers callbacks for its own system ID from `AppConfig.ready()`:

```python
from api.combat import register_provider

register_provider('publisher.starship',
                  prepare_initiative=prepare_initiative,
                  advance_effects=advance_effects)
```

`prepare_initiative(formula, data, *, conditions=())` receives isolated copies
and returns `(formula, data)`. The native dice parser evaluates the returned
formula and validates numeric results; it does not know the system's modifiers.
`advance_effects(data, event)` mutates a bounded sheet copy and returns `True`
when it needs persistence. The system owns field names, equipment activation,
resource rules, conditions and effect clocks. Without a provider, sheet effects
are left untouched. Registration for another system never affects the selected
system; duplicate conflicting registrations fail startup.

The event contains `phase` (`start`/`end`), `roundBoundary`, `isCurrent`,
`periodic`, `actorType`, event-source `tokenId`/`actorId`/`conditions`, and
`ownerTokenId`/`ownerActorId` for the supplied document. Linked tokens share one
actor document; independent tokens receive their own snapshot. `documentKey`
is an opaque tuple identifying that document; `clockKeys` is a set shared across
one command's phases for system-owned clock deduplication. Skipped turns have
`periodic=False`; backward navigation never dispatches these callbacks.

The host retains membership, ownership, encounter boundaries, transactions,
JSON limits, revisions, retry receipts and publication. A callback failure rolls
back the command. Callbacks must avoid external side effects: the transaction
cannot undo them. These are trusted Python extensions enabled by the host owner
through the existing Django package mechanism, never imports requested by a
browser manifest. A system may distribute its browser UI and server rules as
separate packages. Add `"requiresProvider": true` inside `system.combat` when
its rules require that backend: combat actions fail clearly if it is missing,
instead of silently using incomplete rules. No game-specific fallback is built
into the VTT.

## Signed catalog and activation

The marketplace uses the publisher catalog configured by the host owner; there is no built-in public feed. Installed modules load from `/api/module-packages` independently of the remote catalog and its configuration. Refreshing the marketplace discards previous remote results before loading the current catalog, and re-reads installed packages after signed revocations or installation.

The owner-only `GET /api/marketplace/status` checks local configuration without contacting the publisher or writing package files. It returns HTTP 200 with `catalogConfigured`, `trustedKeysConfigured`, `ready`, `sdk`, and `errors` (an array of `{field, code}`, where `field` is `catalog` or `keys`). The booleans indicate valid local configuration, not publisher availability. `ready` is true only when the HTTPS URL is valid and the trust store contains at least one valid key. Configuration failures return HTTP 503 from catalog and installation requests with `{ "error": "<code>" }`:

| Code | Owner action |
| --- | --- |
| `marketplace_catalog_missing` | Set the publisher's HTTPS JSON catalog URL. |
| `marketplace_catalog_invalid` | Correct the URL; credentials, invalid ports and fragments are rejected. |
| `marketplace_keys_missing` | Set the trusted public keys file path. |
| `marketplace_keys_unreadable` | Check that the file exists and the server can read it. |
| `marketplace_keys_invalid` | Correct its JSON object, key IDs or base64 Ed25519 public keys. |
| `marketplace_keys_empty` | Add at least one trusted publisher key. |

Restart the host after changing environment settings; edits to the configured keys file are read on the next request. Publisher/network failure remains `unavailable` (503), invalid catalog/package data is `invalid_data` (400), and untrusted or invalid signatures remain `permission_denied` (403). Failed trust configuration never disables signature verification.

Set `GRAVEWRIGHT_MARKETPLACE_URL` to an HTTPS JSON catalog, and `GRAVEWRIGHT_MARKETPLACE_KEYS_FILE` to a JSON file containing `{ "key-id": "base64-encoded-32-byte-Ed25519-public-key" }`. Keep private signing keys outside distributed packages and public catalogs. The catalog is an array of records:

```json
[
  {
    "id": "example.actor-counter",
    "version": "1.0.0",
    "sdk": ">=1.0.0 <2.0.0",
    "download": "https://your-publisher.example/actor-counter-1.0.0.zip",
    "sha256": "<64 lowercase hexadecimal characters>",
    "keyId": "publisher-key",
    "signature": "<base64 Ed25519 signature>"
  }
]
```

Replace the placeholders with real values. The signature covers every field except `signature`, including optional `status`, serialized with sorted keys, compact separators, ASCII escaping, and no NaN. All record values must be ASCII strings. An equivalent signer in initialized Django code is:

```python
import base64
import hashlib
from gravewright.modules.packages import canonical

# archive: the final ZIP bytes; private_key: publisher's Ed25519PrivateKey.
# record: the record above without its signature field.
record["sha256"] = hashlib.sha256(archive).hexdigest()
record["signature"] = base64.b64encode(private_key.sign(canonical(record))).decode("ascii")
```

Publish the archive and catalog over HTTPS, configure the public key, then use the owner's Marketplace screen to install the release. A GM activates it under the table's Settings → Extensions. The HTTP installation route takes only `id` and `version`, looks up the configured catalog, and verifies the selected archive. It does not accept an arbitrary archive URL from the request.

As a fully local alternative, the owner can use **Install from ZIP** in the same modal. This flow does not contact the marketplace or require a catalog or publisher keys: the local upload is the owner's explicit trust decision. The ZIP still undergoes the same manifest, compatibility, path, file-type, quota, and executable-content validation. In Systems it must declare `system`; in Modules it must not. Because module JavaScript runs on the application origin, install only trusted files.

Installation checks the archive digest, manifest identity and SDK range, entry-file presence, filenames, entry types, and extracted bytes. Limits are 64 MiB compressed, 256 MiB expanded, 4,096 entries, and 64 active modules per table. Paths cannot traverse directories or contain backslashes, percent escapes, URL punctuation, or NUL. Symlinks, encrypted entries, case-insensitive duplicate paths, disallowed extensions, and recognized native executable headers are rejected. Supported file extensions are listed in `ModulePackages.install`; license texts should use `.txt` or `.md` because extensionless files are not accepted.

By default, installed archives live under `MEDIA_ROOT/modules/archives/`; extracted packages live under `MEDIA_ROOT/modules/packages/<id>/<version>/<digest>/`. Set, for example, `GRAVEWRIGHT_MODULES_ROOT=/srv/gravewright/modules` in `.env` to choose another folder; relative paths start at the source root and changing it requires a host restart. The database stores manifests and the trusted origin of each installation. A release ID/version cannot be replaced with different bytes. Activation and authenticated asset access recheck stored content; do not edit extracted files to develop an update. Publish a new version instead.

Activation uses `{modules, replacements, expectedRevision}`. `modules` maps IDs to exact versions, `replacements` maps surface names to module IDs, and `expectedRevision` must equal the last read `moduleSetRevision` (`"0"` initially). A stale revision produces `conflict`. Successful changes issue a fresh revision and notify table clients. Clients also poll and reconcile on reconnect, so activation does not depend solely on socket delivery.

A signed catalog record with `status: "revoked"` revokes an installed release when that catalog is fetched, removes it from affected tables, clears its replacement preferences, and changes their revisions. This is catalog-fetch-driven revocation, not an always-connected publisher push. Rolling back to another installed version changes code selection; stored module data is not reverted.

## Lifecycle and mounting

Every entry exports one default object with `start`, `register`, and `stop` functions. The runtime rejects the obsolete `execute` member.

1. The runtime invalidates old handles before reconciling a new activation revision.
2. It imports each selected package, calls and awaits `start(moduleContext)`, then calls `register(registrationContext)` once.
3. `register` must be synchronous. It declares mount callbacks; an async mount callback is allowed. Duplicate registrations for a domain produce `conflict`; unknown domains and registrations after `register` returns produce `invalid_data`.
4. Each matching visible surface receives a separate mount root, frozen context, abort signal, API, assets/styles/storage, and `onDispose` callback registry. Scene surfaces also receive scene identifiers; `scene.overlay` has viewport coordinate conversion helpers.
5. Detaching a surface, leaving a table, changing scene/replacement/module revision, or revoking access invalidates the corresponding lifetimes. Cleanup aborts the signal first, runs registered cleanup callbacks in reverse order, and bounds each async cleanup to five seconds. `stop` runs after module disposal, including when `start` fails after the module was registered internally for cleanup.

The module-level `start` context supplies `api`, `assets`, `styles`, `storage`, `signal`, and `onDispose`; it has no surface root or scene identity. Mount blocks additionally supply `root`, `context`, `host`, `events`, and optionally `viewport`. Registration receives `register` and an API whose `ui.register` forwards to that same synchronous registration phase. Use the provided `register` when declaring module surfaces.

Do not retain a mount's API for a later mount. Disposal rejects pending/scoped work with `stale_context`. Add listeners with `{ signal }`, and register timer, observer, or external-resource cleanup through `onDispose`. Client cancellation cannot undo a write already committed by the server. An error in module start/registration tears down the activation and restores native UI; an individual mount failure is reported and a failed selected replacement restores its native surface.

## Available surfaces

The [registry and context schemas](../../gravewright/modules/contracts/registry.json) define the accepted names and context shapes:

| Surface | Purpose / additional context |
| --- | --- |
| `actor.directory` | Actor list |
| `actor.sheet` | Actor sheet; `actorId` |
| `token.sheet` | Token sheet; actor/token and scene context |
| `item.directory` | Item list |
| `item.sheet` | Item sheet; `itemId` |
| `journal.sheet` | Journal document; `journalId` |
| `scene.directory` | Map/scene list |
| `scene.controls` | Controls for the current scene |
| `scene.overlay` | Overlay clipped to the current scene viewport |
| `chat.log` | Chat area |
| `combat.tracker` | Combat for the current scene |
| `preferences` | Table preferences |
| `table.interface` | Table workspace |

`augment` is the default and keeps native content. `replace` hides native content while the selected module mounts. One replacement candidate is selected automatically; competing candidates need an explicit table preference. Additional augmentations still mount. CSS is shared with the page, so namespace selectors. Scene overlay roots do not intercept input by default; opt in only for your interactive elements.

Coordinates are logical scene pixels, origin at top left, positive x right and y down. Token coordinates refer to the center. `viewport.sceneToViewport({x,y})` and `viewport.viewportToScene({x,y})` convert to/from CSS viewport pixels independently of device pixel ratio. Use the mounted scene identity rather than a globally selected map.

The global `gravewright.ui` also exposes `app.shell` and `inside.content`; these are host-page surfaces, not accepted domains in the signed module runtime. See [frontend architecture](frontend.md).

## Assets, persistence, and events

Use `assets.url(path)`, `assets.text(path)`, `assets.json(path)`, or `assets.bytes(path)` with package-relative paths. `styles.use(path)` attaches a stylesheet and returns a disposer; it is also removed automatically on context disposal. These helpers do not provide arbitrary network access as part of the supported SDK.

| Store | Scope | Write policy |
| --- | --- | --- |
| `storage.local` | Browser origin + module ID; not separated by table/user | Browser-local JSON, 256 KiB per value |
| `storage.user` | Module + table + authenticated user | That user's persistent JSON |
| `storage.table` | Module + table | Members read; GM writes |

Persistent values have a 256 KiB limit and each persistent namespace a 4 MiB limit. Keys are at most 240 characters. `get` returns `{value, revision}` or `null`; `list(prefix)` returns key/revision pairs. To create a value use `expectedRevision: null`; update/delete with the exact revision returned by `get` or `set`:

```javascript
const previous = await storage.user.get("panel-settings");
const saved = await storage.user.set("panel-settings", { collapsed: true }, {
  expectedRevision: previous?.revision ?? null
});
await storage.user.delete("panel-settings", { expectedRevision: saved.revision });
```

On `conflict`, read again and decide how to merge. Do not repeatedly overwrite another client's update. These values outlive deactivation and code upgrades; version and migrate your own JSON data explicitly. Local browser storage is unsuitable for private user data on a shared browser because its module namespace is shared across accounts.

Prefer `api.events.on("actors.changed", handler)` and the other domain events for current authorized snapshots. The older mount-level `events.on` exposes `actor.created`, `actor.updated`, `actor.deleted`, and `scene.viewport.changed`. In the current workspace bridge the actor events are inferred from successive visible actor lists: initial/repeated snapshots and changes of visibility can appear as creates, updates, or deletes. They are refresh hints, not a mutation audit. Re-read after reconnect and do not use these notifications as exactly-once side effects. Unsubscribe explicitly using the returned disposer or let mount disposal unsubscribe.

## Verification

From the repository root:

```sh
uv run --locked python manage.py test gravewright.modules gravewright.table.tests.test_frontend_api gravewright.table.tests.test_public_api
node --test tests/modules/*.test.mjs
uv run --locked python tests/e2e/frontend_api.py
uv run --locked python tests/e2e/table_modules.py
```

Browser tests require the development dependencies and installed Playwright browser; see [testing](testing.md). Exercise activation/deactivation, a failed mount, scene changes, membership loss, reconnect, stale storage revisions, and the GM/player views of any new operation. Existing schema files and tests are concrete contract references; this checkout does not include a TypeScript SDK package or an automated major-version compatibility release checker.

### Installation-wide language packages

A manifest may declare `locales`, mapping locale IDs to `{ "name": "Português (Brasil)", "path": "locales/pt-BR.json" }`. Catalog files are nonempty JSON objects mapping original UI strings to translations, preserving `{name}`-style placeholders. English is built into the host and cannot be overridden; a package cannot combine `system` and `locales`. Language packages cannot contain Python.

Language packages appear in Installed modules. An owner uses `POST /api/module-packages/activation` with `{ "id": "gravewright.translator", "version": "0.1.0", "enabled": true }` to activate one installation-wide language package. Activation verifies the installed signed archive. Campaign module configuration rejects language packages and the table extension list omits them.

After activation, each authenticated user can choose a language in internal account Settings. The choice is stored in `UserPreference.locale`; a signed cookie supports the anonymous login screen. A different signed-in account does not inherit the previous account's cookie preference. Disabling/revoking the package restores English on the next page load and removes the selector. Reload existing pages after changing global activation.

The host translates application dictionaries and literal template text. Reactive template labels are translated before Datastar processes them to avoid conflicting DOM observers. Browser-created controls use the static catalog; user-authored names, chat and editable content are excluded. This does not translate PDFs, rule content or arbitrary third-party interfaces.

The Translator Django app is maintained at <https://github.com/Gravewright/translator>. Its build command creates the portable signed release input; the Django authoring app is not needed after marketplace installation. See its `VALIDATION.md` for offline/online browser coverage. The host changes in this development checkout are required by the Translator v0.1.0 preview.

### Package library and installation browser

Inside now has separate **Systems** and **Modules** libraries, with a tile/list view preference, search and pagination. **Install system** or **Install module** opens the configured catalog in a dialog filtered to that category. The native PDF system remains visible without remote configuration. Installed libraries never require a catalog fetch; catalog diagnostics appear when opening the installation browser. The old `section=marketplace` link resolves to Modules for compatibility.

New signed catalog records should include `"type": "system"`, `"type": "module"`, or `"type": "django"`. Django records require an explicit type and a `django` manifest block. This field participates in the signature and must match the ZIP manifest (`system` means the manifest declares `system`). Invalid values and mismatches are rejected. Legacy records without a type remain valid and default to modules when not yet installed; installed manifests determine their actual category. Publishers of system packages must include the signed type for correct discovery before installation.

Catalog records may also declare `tags`: up to 24 unique, trimmed, nonempty Unicode strings of at most 64 characters. They participate in the canonical signature and form creator-defined categories in the installation modal. Categories are scoped to the selected package type. Missing tags remain valid and packages still appear under All packages.

The installation modal receives NDJSON progress from `POST /api/marketplace/install` when `Accept: application/x-ndjson` is sent. Events have `stage` values `catalog`, `download` (actual `received` bytes and nullable `total`), `verify`, `complete` (manifest), or `error` (code). Completion is emitted only after archive verification, extraction and database installation. Without a known Content-Length, download progress is indeterminate with a byte count. The ordinary JSON endpoint remains compatible. Disconnecting a browser does not roll back an installation already running; refresh the installed library to check its result.

### Optional per-user customization

An active browser module may export `customize(context)` alongside its required
lifecycle methods. The table extension list displays **Customize** immediately
before Deactivate (or on its own for players). The callback receives the same
module-scoped assets, storage and lifetime as `start`; no new permissions are
granted. Use `storage.user` for personal choices, and close dialogs and dispose
resources on `onDispose`. The host only supplies the button; the module owns its
UI, assets and validation. Modules without this optional callback are unchanged.

### Explicitly installed Django apps

The marketplace also accepts signed catalog records with `"type": "django"`.
These appear in **Modules** with a **Django · Server** badge. A local Django ZIP
can be installed through **Install from ZIP** in the same library. Installation
only validates and extracts the archive; use its activation button to execute
the trusted server code and restart the host. This requires the managed Runner
or `main.py`, plus `uv`. There is no manual `.env` change for marketplace apps.

Use the normal manifest identity, SDK, description, author and license fields,
omit `entry`, `system` and `locales`, and add:

```json
"django": {
  "apps": ["my_extension.apps.MyExtensionConfig"],
  "requirements": ["some-library==1.2.3"]
}
```

The ZIP must contain `my_extension/__init__.py` and the app's Python sources,
migrations, templates and static assets. `requirements` is optional and accepts
exact `name==version` pins from the configured Python package index, without
URLs, local paths, extras or installer flags. Dependency resolution cannot
replace the core versions locked by Gravewright. Apps must use distinct import
names and Django labels. An AppConfig may define `gravewright_urlconf`; each
app is responsible for authentication, CSRF and resource permissions on its routes.

Activation prepares a separate Python environment, checks Django, backs up the
database and files, applies migrations, collects static files and restarts.
Failures restore the previous environment, package selection and data. Only
one server operation may run at a time. Enabled selections live in
`MEDIA_ROOT/modules/server-apps.json` (or the configured modules directory),
survive core updates, and have their dependency pins reapplied during updates.
Deactivation restarts the host without the app; it does not reverse migrations
or delete the app's data. Revoked releases cannot be newly activated; an already
running app must be deactivated by the owner. Python sources are not served by
the browser-package asset endpoint or offered as table-level modules.

The following remains an alternative for operator-managed source checkouts:

A host operator may install a trusted Python app in the server's environment and
set `GRAVEWRIGHT_SERVER_APPS` to its import path (comma-separated for multiple
apps). An AppConfig may expose `gravewright_urlconf` to append its URL patterns.
These apps run as trusted server code and must enforce authentication, CSRF and
native domain permissions. This setting is never populated from browser package
manifests. Environment rebuilds require reinstalling these separately managed
Python dependencies. An invalid app import prevents startup rather than silently
disabling its server functionality.

Native item rows expose `application/x-gravewright-item` drag data containing
`{id, tableId}`. Resolve the ID through the authenticated item API before copying
it into a sheet; do not treat data supplied by a drag payload as authoritative.

Actor and token sheet replacements own the **complete window body**. The host
provides only the movable title bar, detach/minimize/close controls, permissions
and document identity. PDF, Token and Notes tabs belong exclusively to the
bundled PDF system module; other systems never load its controller, templates or
styles. The bundled module registers its descriptor, sheet provider and data
validator through its AppConfig. Legacy PDF campaigns keep their existing ID
and stored data, with no conversion required.

Signed system packages can register different sheets for declared actor types:

```js
register("actor.sheet", {
  mode: "replace",
  types: ["hero"],
  mount({ root, context, api, signal }) {
    // Render the entire sheet, including any navigation your system needs.
    // context includes actorId, actorType, systemId and canEdit.
    // Use api.actors.sheet(...) and api.actors.saveSheet(...) for document data.
  }
});
```

Omitting `types` applies the registration to all actor types. Disjoint type lists
allow multiple registrations on the same surface. An explicit table replacement
wins; otherwise the campaign's system sheet takes precedence over competing
add-ons. A token uses the system's actor sheet with `tokenId` and `sceneId` in its
context unless that package registers a matching `token.sheet` replacement.
Actor and snapshot-token data for external systems retain their own JSON shape;
the host enforces size, JSON safety, ownership and revision checks without
injecting PDF fields. Optional `token` and `bars` presentation hints still work;
missing hints use neutral scene defaults without changing stored sheet data.

Before closing, the window emits `gravewright:sheet-flush`; a mounted extension
can call `event.detail.waitUntil(promise)` synchronously to await pending writes.
A rejection keeps the window open and displays the error. Bind listeners on
`root.closest('.gw-window')` using the mount abort signal. Custom sheets own
flush/refresh behavior when switching their internal tabs. The PDF provider
continues emitting `gravewright:sheet-flush` and `gravewright:sheet-refresh` when
switching its own tabs.

Item sheet replacements retain the native title bar and also emit
`gravewright:sheet-flush` before closing. Bind the listener on
`root.closest('.item-sheet')` and call `event.detail.waitUntil(promise)` to
await writes, including when the user presses ESC. Rejection keeps the item
open. Losing read access forces immediate closure without waiting for writes.

For separately maintained source checkouts, set `GRAVEWRIGHT_SERVER_APP_PATHS`
to their package root directories (`:` separated on Linux/macOS, `;` on Windows).
Relative paths resolve against the VTT checkout. These explicitly trusted paths
survive virtual-environment synchronization; app dependencies still require
installation. The Python packages remain outside the VTT repository.

The checkout ships a default folder for these apps: `extensions/django`, set by
`GRAVEWRIGHT_DJANGO_MODULES_ROOT`. It is appended to `sys.path` when it exists,
so a package placed directly in it only needs its import path in
`GRAVEWRIGHT_SERVER_APPS`; explicit `GRAVEWRIGHT_SERVER_APP_PATHS` entries
precede it. Browser module sources have a matching default folder,
`extensions/api` (`GRAVEWRIGHT_API_MODULES_ROOT`), which is documentation and
authoring space only — installed signed packages still live under
`MEDIA_ROOT/modules`. A configured folder that does not exist prevents startup;
deleting the shipped defaults without configuring them is supported. Git ignores
the contents of both folders, so extensions stay out of this repository.

[Ethical module porting](ethical-module-porting.md)

## Compendiums supplied by a system package

A browser system may declare up to 16 JSON collections in its manifest:

```json
"content": {"compendiums": ["compendiums/entities.json", "compendiums/gear.json"]}
```

Paths must be relative package paths ending in `.json`. Absolute paths, traversal,
URLs and symlinks outside the approved package are rejected. Each collection is
limited to 8 MiB, 64 packs and 20,000 entries in total. An entry is limited to
256 KiB; JSON nesting is limited to 24 levels. Collections contain declarative
JSON, and each entry's `data` belongs to its provider. The core does not execute
expressions or fetch external assets from those fields:

```json
{
  "name": "Example equipment",
  "packs": [{
    "id": "gear", "label": "Equipment", "type": "item_pack",
    "entries": [{
      "id": "survey-kit", "name": "Survey kit", "type": "gear",
      "systemId": "author.example-system",
      "data": {"revision": "original", "description": "Plain text"}
    }]
  }]
}
```

Supported pack kinds are `actor_pack`, `item_pack` and `spell_pack`. Every entry
must use the provider's own `systemId` and a type registered in its
`system.actorTypes` or `system.itemTypes`. Pack IDs must be unique within the
collection; entry IDs must be unique within their pack. IDs accept ASCII
letters, digits, dots, underscores, colons and hyphens, up to 120 characters,
and must start with a letter or digit. Names and labels are limited to 120
characters. Keep IDs and relative paths stable across updates so permissions
and entry references remain stable.

Installation validates the declarations and files. The native compendium UI
exposes them only in campaigns using that system's exact active, pinned,
approved and non-revoked package version. Every read checks installed bytes
against the approved archive; changing a file does not authorize new content.
Collections do not declare campaign IDs. The host binds access internally.
Packs are private to the GM by default. Existing compendium read grants and
role defaults control player visibility; importing documents remains a GM
action. The host treats `data` as opaque JSON and retains the provider's fields;
it does not interpret revisions or game rules. Update the VTT
base to a version supporting `content.compendiums` before installing a package
that uses this optional declaration.

Declared collection JSON files are not served by generic package asset URLs.
Read and import their entries through the table-scoped compendium API, which
checks the active system and the user's current read grants.

Use `api.compendiums.state()` to discover visible pack and entry IDs.
`api.compendiums.read({packId, id})` still returns one entry;
`api.compendiums.read({packId, ids: [id1, id2]})` returns `{entries: [...]}`
containing the same documents in requested order. A batch accepts 1–100 unique
IDs; do not combine `id` with `ids`. Invalid or duplicate IDs produce
`invalid_data`. A missing entry fails the entire batch with `not_found`,
without partial results. Native packs retain full source documents; packs
created in a table retain their individual `kind`, `data` and `version` envelope.

Every read rechecks table membership and current grants, plus the active
version and integrity of installed collections. Reads create no mutation
receipts and publish no `compendiums.changed` event. Reusing a request ID does
not retain access after revocation. A read-only role may read under a valid
grant and still cannot import documents.

The root index contains only pack metadata and each entry's `id`, `name`,
`kind`, `type` and `version`. It does not include document bodies or archives.
`type` is the provider's registered document type, not a host rules category;
`spell_pack` is a compatibility pack kind that routes to item documents without
adding spell rules. Full documents are loaded through authorized individual or
batch reads. Installed collections share the same bounded, verified content
cache regardless of provider or document type; permissions, package selection
and revocation are checked on each request and are never cached with content.
Legacy actor imports without a type use the system's declared actor default,
the same contract as actor creation, instead of a built-in actor type.

## Module modal windows

Use `api.ui.openModal(element, {nested = true, canClose = () => true})` for
module windows. It mounts the shared Gravewright modal component synchronously
and returns the same element, with `close()`, `suspend()` and `resume()` methods.
Pass a `section`, `div` or `form` created in the host document. Native HTML
`dialog` elements and elements from another document are rejected. The host adds
`table-modal-window`, traps focus, makes the background inert, restores focus
on close, and handles Escape. Modules provide their content, accessible name,
translated labels and close button; a modal does not automatically gain a
movable title bar.

```js
mount({root, api, signal}) {
  const doc = root.ownerDocument;
  const panel = doc.createElement('section');
  panel.setAttribute('aria-label', 'Details'); // Use your translated label.
  const close = doc.createElement('button');
  close.type = 'button';
  close.textContent = 'Close'; // Use your translated label.
  panel.append(close);
  const modal = api.ui.openModal(panel);
  close.addEventListener('click', () => modal.close(), {signal});
}
```

`nested: true` keeps an existing modal underneath the new one; closing the child
restores the parent. Set `nested: false` to request closing the previous modal.
`canClose` is a synchronous guard for Escape; explicit `close()` calls remain
under the module's control. `close()` emits `gravewright:sheet-flush`, so attach
a listener to the returned element and call `event.detail.waitUntil(promise)`
during the event to await pending writes. A rejected write keeps the modal open.
`suspend()` temporarily hides the modal for interactions such as picking on
the map; `resume()` restores it.

The API is bound to the activation or surface lifetime. Disposal forces the
modal closed, even when a save is pending, and releases its focus and background
state. Normal close releases the lifetime cleanup immediately. Opening a modal
after disposal throws `stale_context`; opening an already mounted element
throws `conflict`. This helper is available to `start`, `customize`, registration
and surface callbacks. `api.ui.register` retains its existing registration-phase
behavior.
