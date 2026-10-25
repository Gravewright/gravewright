# Documentation

[English](README.md) · [Português (Brasil)](README.pt-BR.md) · [Project home](../README.md)

English is the primary documentation. Each guide has a corresponding Portuguese version; source identifiers, API names and commands remain unchanged. Guides describe the implementation in this checkout, including its current limits. Design-direction documents identify proposed capabilities separately.

| Guide | What it explains |
| --- | --- |
| [Windows runner](en/windows-runner.md) | Double-click installation, local execution, icon shortcut and personal data |
| [Linux runner](en/linux-runner.md) | Distribution detection, private tools, local execution and unattended checks |
| [macOS runner](en/macos-runner.md) | Intel/Apple Silicon installation, Finder launcher, private tools and local execution |
| [Getting started](en/getting-started.md) | Dependencies, configuration, migrations and first login |
| [Upgrade and recovery](en/upgrading.md) | Preparing for 0.3.3, required migrations, dependency updates and recovery from a backup |
| [User guide](en/user-guide.md) | Campaigns, scenes, sheets, journals and table workflows |
| [Journals and references](en/journals.md) | Insert links to campaign resources in rich text, open native tools and preserve private targets during edits and campaign copies |
| [Campaign management](en/campaign-management.md) | GM workspace, personal dashboard, session planner, timeline, quest columns, connections, player preview and history/trash |
| [PDF System](en/pdf-system.md) | Manual fields for non-editable PDFs, token bars, saved dice rolls, calculations, reusable mappings, export and diagnostics |
| [Progress clocks](en/clocks.md) | Shared progress, audience controls, scene scope and pinned clocks on the table and in campaign management |
| [Clues](en/clues.md) | Progressive discoveries, private GM notes, player revelation and MapBuilder mechanisms |
| [Mind maps](en/mindmaps.md) | Collaborative topic graphs, permission-filtered links to 37 native resource types and MapBuilder actions |
| [Map Builder](en/map-builder.md) | First project, Tiles/Painting, finished-map backgrounds, layers, saving, Smart Objects and scene updates |
| [Universal VTT importer/exporter](en/universal-vtt.md) | Import workflows, native maps/walls/doors/lights, warnings and error recovery |
| [Smart Objects direction](en/smart-objects-direction.md) | Delivered node-editor stages, element capabilities, references and proposed extensions |
| [Architecture](en/architecture.md) | Request flow, persistence, authorization and realtime |
| [Code map](en/code-map.md) | What each domain does and where to make changes |
| [Development](en/development.md) | Contributor workflow, source conventions and contracts |
| [API](en/api.md) | Python facade, browser API and transport boundaries |
| [Modules](en/modules.md) | Package manifests, trust, lifecycle and extension examples |
| [Ethical module porting](en/ethical-module-porting.md) | Licenses, content rights and mapping features to native domains |
| [Frontend](en/frontend.md) | Jinja2, Datastar, JavaScript, rendering and vendor assets |
| [Configuration](en/configuration.md) | Environment variables, defaults and persisted preferences |
| [Testing](en/testing.md) | Django, Node.js and browser regression checks |
| [Deployment](en/deployment.md) | ASGI, Redis, private storage, backups and release limits |

Project policies: [contributing](../CONTRIBUTING.md), [security](../SECURITY.md), [licensing](../LICENSING.md), [module permission](../LICENSE-EXCEPTION), [third-party notices](../THIRD_PARTY_NOTICES.md).

For the dice implementation, see the existing [grammar architecture](../gravewright/dice/grammar/ARCHITECTURE.md) and [notation reference](../gravewright/dice/grammar/notation/GRAMMAR.md). Machine-readable module contracts live in [contracts/](../gravewright/modules/contracts/); the [transport note](../gravewright/modules/contracts/transport.md) accompanies them.

Current project version: [Gravewright 0.3.3 — Alpha](releases/0.3.3.md). The release notes cover individual scene audiences, blank maps, shared cursors and shortcuts, token presentation, Builder productivity and Smart Object shader controls, with three new database migrations relative to 0.3.2. See [upgrade and recovery](en/upgrading.md) before updating an existing installation.

Historical notes remain unchanged: [0.3.2](releases/0.3.2.md) covers campaign preparation, journal history/trash, clocks, clues, mind maps and PDF mapping; [0.3.1](releases/0.3.1.md) covers forms, object models and scene synchronization; [0.3.0](releases/0.3.0.md) covers the original Map Builder and Universal VTT support; [0.2.3](releases/0.2.3.md) retains the earlier release history. Historical numbering and migration statements describe those releases, not the current version.
