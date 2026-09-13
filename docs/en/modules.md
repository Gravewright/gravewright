# Writing and operating modules

[Documentation index](../README.md) · [Português](../pt-BR/modules.md) · [API reference](api.md)

Gravewright installs signed ZIP packages containing browser JavaScript, assets, and a JSON manifest. A server owner installs releases; a campaign GM chooses exact releases and interface replacements for a table. Installation never imports package Python or starts package executables.

Third-party module licensing is described in the [licensing policy](../../LICENSING.md). The manifest records the module author's chosen license; installation does not change it.

## Trust and installation boundaries

Installed modules execute as ES modules in the application's main browser page. There is no iframe sandbox, Shadow DOM, or capability-based JavaScript isolation. Modules can interact with the page and browser environment. A signature authenticates the configured publisher and archive bytes; it does not prove that code is safe. Configure signing keys for publishers whose code you are prepared to run in users' sessions.

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

The system ID and title come from the package's `id` and `name`. Each package declares one system; it cannot replace `gravewright-pdf-system`. Declare at least one actor type; item types are optional. Type IDs must be unique within each list, start with a lowercase letter, and contain only lowercase letters, digits, underscores or hyphens (80 characters maximum). Each list supports up to 64 entries with labels of 1–120 characters.

After a signed installation, the system appears in Systems, `/api/rulesets`, and the campaign form. The catalog uses the newest compatible, non-revoked installed version per package, ordered by numeric version. Ordinary modules without `system` remain available under Installed modules. Existing campaigns can retain an unavailable system when editing their details, but it cannot be selected for a new campaign.

Selecting a system supplies document types; the GM still activates its JavaScript and sheet replacements under Settings → Extensions. Tables use the document types of that exact activated release, or the latest installed version if none is activated. Actor data keeps the existing native document structure; module-specific data uses the supported module storage and document APIs. Installing a new version does not automatically change a table's activated release.

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

Installation checks the archive digest, manifest identity and SDK range, entry-file presence, filenames, entry types, and extracted bytes. Limits are 64 MiB compressed, 256 MiB expanded, 4,096 entries, and 64 active modules per table. Paths cannot traverse directories or contain backslashes, percent escapes, URL punctuation, or NUL. Symlinks, encrypted entries, case-insensitive duplicate paths, disallowed extensions, and recognized native executable headers are rejected. Supported file extensions are listed in `ModulePackages.install`; license texts should use `.txt` or `.md` because extensionless files are not accepted.

Installed archives live under `MEDIA_ROOT/modules/archives/`; extracted packages live under `MEDIA_ROOT/modules/packages/<id>/<version>/<digest>/`. The database stores manifests and signed records. A release ID/version cannot be replaced with different bytes. Activation and authenticated asset access recheck stored content; do not edit extracted files to develop an update. Publish a new version instead.

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

A manifest may declare `locales`, mapping locale IDs to `{ "name": "Português (Brasil)", "path": "locales/pt-BR.json" }`. Catalog files are nonempty JSON objects mapping original UI strings to translations, preserving `{name}`-style placeholders. English is built into the host and cannot be overridden; a package cannot combine `system` and `locales`. Python is not loaded from marketplace packages.

Language packages appear in Installed modules. An owner uses `POST /api/module-packages/activation` with `{ "id": "gravewright.translator", "version": "0.1.0", "enabled": true }` to activate one installation-wide language package. Activation verifies the installed signed archive. Campaign module configuration rejects language packages and the table extension list omits them.

After activation, each authenticated user can choose a language in internal account Settings. The choice is stored in `UserPreference.locale`; a signed cookie supports the anonymous login screen. A different signed-in account does not inherit the previous account's cookie preference. Disabling/revoking the package restores English on the next page load and removes the selector. Reload existing pages after changing global activation.

The host translates application dictionaries and literal template text. Reactive template labels are translated before Datastar processes them to avoid conflicting DOM observers. Browser-created controls use the static catalog; user-authored names, chat and editable content are excluded. This does not translate PDFs, rule content or arbitrary third-party interfaces.

The Translator Django app is maintained at <https://github.com/Gravewright/translator>. Its build command creates the portable signed release input; the Django authoring app is not needed after marketplace installation. See its `VALIDATION.md` for offline/online browser coverage. The host changes in this development checkout are required by the Translator v0.1.0 preview.

### Package library and installation browser

Inside now has separate **Systems** and **Modules** libraries, with a tile/list view preference, search and pagination. **Install system** or **Install module** opens the configured catalog in a dialog filtered to that category. The native PDF system remains visible without remote configuration. Installed libraries never require a catalog fetch; catalog diagnostics appear when opening the installation browser. The old `section=marketplace` link resolves to Modules for compatibility.

New signed catalog records should include `"type": "system"` or `"type": "module"`. This field participates in the signature and must match the ZIP manifest (`system` means the manifest declares `system`). Invalid values and mismatches are rejected. Legacy records without a type remain valid and default to modules when not yet installed; installed manifests determine their actual category. Publishers of system packages must include the signed type for correct discovery before installation.

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
