# AGENTS.md — Gravewright

Instructions for agents and contributors working in this repository. Gravewright
is a modular virtual tabletop: the server owns data, permissions and persistence;
the browser presents the tabletop and its tools. Complete the user's request
while preserving campaigns, compatibility and existing work.

## 1. Permanent project decisions

- **The installation is portable.** Data, state, logs, tools, environments and
  caches default to locations inside the folder where the VTT was extracted.
  Never redirect these defaults to AppData, HOME, XDG or macOS Library folders.
- **The core is independent of RPG systems.** Character sheets, rules, items,
  powers, system-specific initiative and catalogs belong to their system package.
  The core provides generic capabilities and contracts.
- **Each new RPG system is one installable system package.** Keep its sheets,
  items, rules, automation, translations and assets together. Do not introduce
  a separately installed Server Rules companion under Modules.
- **Respect the requested released host version.** Use its existing public APIs.
  Do not require a newer VTT or publish a VTT release as a workaround for a
  system-package task unless the owner explicitly requests that host upgrade.
- **Use the existing modals.** Do not introduce the HTML `<dialog>` element,
  browser alerts or native confirmations as substitutes for application modals.
- **Preserve data and earlier changes.** Do not overwrite pending work or publish
  private files alongside application code.
- **Distribute only authorized content.** Permission to implement sheet and item
  structures does not authorize shipping books, catalogs or rulebook text.
- Technical convenience does not override these decisions. A product change
  requires an explicit instruction from the owner, including existing conversation
  context. Do not ask again when that instruction has already been given.

## 2. Before editing

Read the request and earlier decisions. Inspect `git status --short`, identify
the owning domain and use `rg` to find existing implementations and tests.
Verify files and commands in the current checkout before citing or running them.

| Document | Subject |
| --- | --- |
| `CONTRIBUTING.md` and `CONTRIBUTING.pt-BR.md` | Conventions, contributions and licensing |
| `docs/en/architecture.md` and `docs/en/code-map.md` | Domain boundaries and operation flows |
| `docs/en/development.md` | Development workflow and generated contracts |
| `docs/en/testing.md` | Test suites, isolation and side effects |
| `docs/en/api.md` and `docs/en/modules.md` | Public API, SDK and independent packages |
| `docs/en/frontend.md` | JavaScript, rendering and asset preparation |
| `docs/en/configuration.md` and `docs/en/deployment.md` | Configuration, security and recovery |
| `windows-runner.md`, `linux-runner.md` and `macos-runner.md` under `docs/en/` | Native installers and execution |
| `.github/workflows/` | Checks actually performed by CI |

Guides have Portuguese counterparts under `docs/pt-BR/`. Read the documents
relevant to the task; do not invent tools, commands, files or project goals.

## 3. Responsibility map

| Location | Responsibility |
| --- | --- |
| `config/` | Django/ASGI, environment, HTTP security and execution profiles |
| `gravewright/<domain>/` | Domain models, services, validation, views and tests |
| `gravewright/realtime/` | WebSocket transport, subscriptions and notifications |
| `gravewright/web/` and `gravewright/table/` | Interface, navigation, windows and modals |
| `gravewright/maps/` | Tabletop, maps, geometry and rendering |
| `gravewright/modules/` | SDK, installation, permissions and module lifecycle |
| `api/` | Public Python interface, distinct from HTTP `/api/` routes |
| `scripts/` and root installers | Bootstrap, Runner, tools and packaging |
| `tests/` | JavaScript, browser and native acceptance scenarios |
| `extensions/` | Extension locations; operator installations are not core source |
| `data/` | Private data and local state; never bundle it in a release |

Domain services own rules, authorization and persistence. Views, consumers and
the interface call those services. Modules use the public API/SDK rather than
bypassing contracts with direct ORM writes or private host imports.

## 4. Installation-local storage contract

The installation root contains `manage.py`, `pyproject.toml`, the installers and
`.env`. Resolve relative paths against that root, regardless of the directory
from which someone launched the installer.

| Content | Default location inside the installation |
| --- | --- |
| Configuration and private secret | `.env` |
| SQLite database | `data/gravewright.sqlite3` |
| Media and installed packages | `data/media/` |
| Runner compendiums and collected assets | `data/compendiums/` and `data/staticfiles/` |
| Runner logs and locks | `data/logs/` and `data/runner.lock` |
| Official Marketplace public keys | `data/marketplace/` |
| Launcher recovery copies | `data/.runner-launchers/` |
| Updater transactions, releases and backups | `data/updates/` |
| Managed tools, environments, caches and temporary files | `data/runner/` |

Two extracted installations must operate independently for the same OS user.
Do not read, import or share a global `active.json` to select the active release.
A legacy path generated automatically in the user's OS profile is not an explicit
operator request to store installation data there.

Configure child-process caches and temporary directories before starting tools.
Account for `tempfile`, uv/Python, npm, Cargo/Rust and native helper programs.
Do not register managed Python globally or make permanent PATH changes. Helpers
must not create caches outside the installation as an incidental side effect.

If the installation directory is not writable, report the failing path. Never
silently fall back to global storage. Existing overrides explicitly supplied for
isolated tests or operator configuration retain their documented semantics.
Do not introduce them as defaults or use them to bypass this contract.

Updates protect `.env`, `data/`, environments, caches and local extensions.
Immutable launchers survive source replacement while remaining inside the
installation. Staged preparation must generate launchers targeting the final
installation. Do not remove another installation's files to repair a failure.

Storage changes require coverage of two installations, stale global state,
spaces/Unicode, offline reuse, permission failures and recovery. Validate Windows,
Linux and macOS through their corresponding native scenarios.

## 5. Security and data consistency

- Validate payloads, types, limits and resource ownership on the server. Hiding
  a browser control does not establish an authorization boundary.
- Preserve campaign, session and role isolation. Streamers remain read-only;
  the server must filter hidden data before delivery.
- Follow the domain's transactions, receipts and revisions. Allocate a new UUID
  for each logical operation and reuse it only to retry that same operation.
- Refresh state after a version conflict. Do not force a write by silently
  replacing its expected revision.
- Notify after commit and preserve clients' ability to resynchronize.
- Treat files, ZIPs, PDFs, images and parameters as untrusted input. Bound size
  and complexity, reject path traversal and validate destinations.
- Verify absolute paths and containment before recursively deleting or moving
  trees. Preserve transactions and backups when recovery fails.
- File, network, disk and configuration errors need useful diagnostics. Do not
  return success or continue with partial data to conceal a failure.

## 6. Modules, contracts and licensing

System-specific capabilities stay entirely in their package: services, assets,
styles, translations, settings and automation. A package requirement can justify
a generic host contract with validation, permissions and tests. It does not
justify system-name conditionals inside the core.

Preserve manifest and SDK compatibility. To change the browser contract, edit
`gravewright/modules/contracts/frontend.json` and regenerate its counterpart
with `scripts/generate_frontend_api.py`. Do not edit only `frontend-contract.js`.

Respect content boundaries, licenses, notices and authorized branding. Do not
include rulebook PDFs, authorization emails, proprietary catalogs or private
material in fixtures, public documentation or release archives. Preserve third-party
headers and notices, and update the applicable licensing records.

## 7. Interface, languages and performance

Keep the existing stack: Django/Jinja2/Datastar on the host, native JavaScript
modules in the browser and PixiJS where the tabletop uses it. Do not replace
frameworks or introduce Vue to solve a localized change.

Use existing colors, tokens, typography and interaction patterns. Modals must
support focus, keyboard navigation, closing, scrolling and smaller viewports.
Visually inspect layout changes using synthetic data, long content and empty
states. Do not present buttons for functionality with no implemented action.

Fixed design-token dimensions use plain pixel values. Reuse existing tokens and
add a new one when a value is shared across components. Padding, margins and
gaps use the `--space-*` scale; corners use `--radius-*`. Host interface text
must remain at least 12px, including relative sizes and font shorthands.
Component-specific widths and heights may use literal pixels. Keep responsive
geometry as CSS expressions and preserve authored document and scene text sizes.

`en` is the default language; preserve explicit user choices. Integrate translations
through the official mechanism and the owning package, considering `en`, `pt-BR`
and `es` where available. Do not translate authored content or legal notices whose
wording must remain exact. Keep English and Portuguese documentation aligned.

Dispose of listeners, timers, subscriptions, render objects and asynchronous work
when components or modules close. Avoid expensive per-frame work, repeated queries
and rendering invisible resources. Measure before and after changes to expensive
operations; do not invent performance results.

## 8. Validation proportional to the change

Use the actual project tools: Django/unittest, `node:test`, Playwright and native
scripts. There is no root `npm test` or configured pytest runner. Select tests
for the changed behavior; do not write tests that merely repeat code or documentation.

```sh
uv run --locked python manage.py check
uv run --locked python manage.py test <changed-domains-or-modules> --noinput
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

Read `docs/en/testing.md`: Django uses an explicitly configured test database;
changing only `GRAVEWRIGHT_DATABASE` does not necessarily change that test database.
Use disposable copies and isolated databases, media, modules and state. Do not
edit the real `.env` to facilitate testing or run parallel suites against the same
data, ports or result directories.

Installers, Runner and updater changes need native execution beyond unit tests.
Consult `tests/windows/runner.py`, `tests/posix/smoke.py` and
`tests/e2e/automatic_updates.py`. `--skip-browser` and `--source-check` do not
validate the stages they omit.

Run focused checks during implementation. After they pass, repeat or broaden them
when new changes, failures or unresolved concerns justify it. Fix the cause of
regressions rather than removing assertions or weakening scenarios. Report the
commands run, results and actual limitations.

## 9. Concurrent work and continuity

Preserve earlier changes and distinguish them from your own. Do not use
`reset --hard`, `clean`, indiscriminate stashing or file replacement to obtain a
clean tree. Use a separate checkout when it protects concurrent work.

Delegate non-overlapping files or responsibilities. Agree on ownership of shared
files and reread them before editing. Use independent fixtures, databases, ports
and outputs. Do not publish code that another agent is still modifying.

Record lasting decisions here or in the owning domain's documentation and keep
them consistent with the implementation. Do not rely solely on conversation
memory. When resuming interrupted work, inspect processes, results and previous
changes before repeating commands or rebuilding artifacts.

## 10. Git and publication

Do not commit `.env`, databases, media, installed packages, private keys, logs,
test results or operator files. Do not change the meaning of a published migration.
Use English for identifiers, code comments and API documentation, following
repository conventions. Keep this `AGENTS.md` in English.

Read release versions from current manifests; do not hardcode release numbers
in this guide. Keep `pyproject.toml`, `uv.lock`, frontend manifests and release
notes consistent when changing versions. Document the resulting behavior for
readers who have not seen the conversation.

Build the public ZIP with `scripts/build_release.py`. Review file selection,
exclusions, script permissions, integrity and checksum. Tag, commit, notes and
assets must represent the same verified result. Reissues need backups and
protection against concurrent changes. Users already on the same version need
manual installation instructions because the updater compares versions.

Complete publications already authorized in the conversation within that scope.
Do not request another confirmation for routine technical decisions. Do not send
external messages or expand publication to another repository without authorization.

## 11. Completion criteria

Confirm that the request is implemented in the appropriate layer, the relevant
checks passed and existing data and changes are preserved. Review the diff,
documentation and generated contracts before finishing.

Report the outcome directly in the user's language: what changed, how it was
validated and which action the user needs to take. Distinguish completion,
pending work and actual blockers. Do not claim publication, successful CI or
visual correctness without verification. Continue authorized work until the
requested result is delivered.
