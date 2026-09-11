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

## Native state and realtime

Native UI code calls the shared domain API where implemented and still has dedicated HTTP/socket adapters for specialized flows such as uploads, board subscriptions and rendered fragments. The public browser API does not replace every native transport.

The realtime controller connects the current table's authenticated WebSocket, tracks subscriptions and reconnect state, and dispatches `gravewright:*` browser events. The server sends user-authorized projections and rendered HTML; private actor data, chat audiences and scene visibility are enforced before delivery. Insert user-provided text with `textContent`. Existing HTML fragment insertion is for HTML rendered by the trusted server templates, not arbitrary module or chat text.

`gravewright:api-event` is the internal adapter event consumed by the domain API; `api.changed` notifications trigger fresh authorized reads. Public integrations should use `api.events.on(...)` as documented in [API events](api.md#domain-events), rather than copying the native socket command protocol. Subscriptions are not a durable change stream: reconnect and reread current state. Creating `gravewright.forTable(...)` alone does not open a socket.

## Sources and generated assets

Most app-specific JavaScript files under `static/` are directly served source. Some files there are committed build outputs. In particular, [`maps/scripts/build.cjs`](../../gravewright/maps/scripts/build.cjs) bundles the following:

| Editable entry/source | Generated destination |
| --- | --- |
| `maps/frontend/widgets/game-board/ui/board.js` | `maps/static/gravewright_maps/vendor/` board bundle/chunks |
| `maps/frontend/shared/rendering/render-profile.js` | `maps/static/gravewright_maps/render-profile.js` |
| `maps/frontend/native/tools.js` | `maps/static/gravewright_maps/tools.js` |
| `maps/frontend/native/table-modules.js` | `table/static/gravewright_table/media-workspace.js` |
| `maps/frontend/features/walls/{ui,model}/walls.js` | `maps/static/gravewright_maps/walls/` |
| Scene-layer sources and lighting profiles | `maps/static/gravewright_maps/sources/` |
| `maps/frontend/calibration.js`, `directory.js` | Corresponding map static model/controller files |
| `maps/frontend/shared/lib/dom/tree-drag.js` | `actors/static/gravewright_actors/tree-drag.js` |
| `maps/frontend/features/tokens/ui/controller.js` | `tokens/static/gravewright_tokens/controller.js` |
| `pdf_system/frontend/controller.js` | `pdf_system/static/gravewright_pdf_system/controller.js` |

Paths in this table are relative to `gravewright/`. Edit the source and rebuild these destinations. Do not make one-off fixes in minified board chunks or vendored libraries.

From the repository root:

```sh
npm ci --include=dev --prefix gravewright/maps/frontend
npm run build --prefix gravewright/maps/frontend
npm test --prefix gravewright/maps/frontend
```

The build uses the locked PixiJS and esbuild dependencies in [`maps/frontend/package-lock.json`](../../gravewright/maps/frontend/package-lock.json), targets ES2022, and keeps `/static/*` imports external. A shared render-profile module stays external so all features use the same runtime profile. The build also collects package license/notice files and writes `vendor/packages.json`; retain those outputs when redistributing built assets. It explicitly rejects including Vue packages.

### Windows runner preparation

The [Gravewright Runner](windows-runner.md) detects and reuses compatible installed Node.js/npm, or downloads its verified fallback when necessary. Its CMD batch file calls [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) in `--plan` mode to check package versions, fingerprints and a real esbuild operation. A matching healthy dependency installation can be reused even on first launch. The batch file itself executes `npm ci --include=dev --include=optional` when dependencies need installation, and the existing `npm run build` for the first preparation or an invalidated build. It then calls the helper in `--record` mode to verify and save the completed output state. esbuild is required during preparation even though Python development dependencies are omitted from normal runner installation.

The plan returns exit code `0` for current assets, `10` for npm installation plus build, or `11` for build only. The batch launcher handles these decisions explicitly. Both helper modes accept `--node`, `--npm-cli` and `--state-dir`; the helper's default mode remains available to perform complete preparation in developer scripts and regression tests.

The npm project remains `gravewright/maps/frontend`; its ignored `node_modules/` is installed there and generated static assets are written to the destinations above. These outputs are committed application assets, so a source change followed by runner preparation can produce a version-control diff. Review and include the appropriate generated outputs and notices when contributing frontend changes.

Preparation state lives outside the checkout under `%LOCALAPPDATA%\Gravewright\runner\frontend\<source-location-hash>\state.json`. Dependency checks include the package files and selected Node/npm versions. Build checks include editable sources, the build script and hashes of generated outputs. The batch file requests an output manifest, including vendor notices, from `build.cjs` through its optional `GRAVEWRIGHT_BUILD_MANIFEST` process variable. A later launch skips a valid unchanged build; changed inputs or missing/modified outputs cause preparation again. A failed build stops launcher startup instead of serving an unverified frontend. `collectstatic` then copies the prepared public assets to the runner's personal static directory.

The module domain-method registry has its own generation command:

```sh
uv run --locked python scripts/generate_frontend_api.py
```

This generates only `modules/static/gravewright_modules/frontend-contract.js` from `contracts/frontend.json`. The original SDK's `generated.js` and JSON schemas are separate artifacts; this script does not regenerate them. `collectstatic` gathers deployable assets but does not run either JavaScript build.

## Board layers and resource lifetimes

The `maps/frontend/` tree separates entity models, feature models/UI, shared utilities, and the game-board widget. The board widget coordinates rendering, input, tile scheduling/cache/prefetch, native layers, vision polygons, lighting and shaders. Feature code contains walls, tokens, drawings, measurements, effects, and selection. Algorithm tests live beside the relevant models and are bundled by `maps/scripts/test_models.cjs` for Node's test runner.

Use one consistent coordinate system across controllers and renderer calls: logical scene pixels, top-left origin, token centers as anchors. Camera pan/zoom converts scene positions into CSS viewport coordinates; device pixel ratio affects rendering resolution. Mixing these units causes selection, token and lighting misalignment. The extension overlay API exposes explicit conversion helpers instead of exposing the PixiJS renderer.

Async work belongs to a page, board, module activation, or individual mount. [`Lifetime`](../../gravewright/modules/static/gravewright_modules/lifetime.js) cancels API calls and disposes subscriptions; map source code has its own shared lifecycle helpers. Add/remove listeners and observers with their owner. Release rendering resources and pending work during board teardown or scene changes. A listener or cached API handle that outlives its owner can update the next scene with old data.

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
