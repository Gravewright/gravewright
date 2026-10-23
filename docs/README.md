# Documentation

[English](README.md) · [Português (Brasil)](README.pt-BR.md) · [Project home](../README.md)

English is the primary documentation. Each guide has a corresponding Portuguese version; source identifiers, API names and commands remain unchanged. Guides describe the implementation in this checkout, including its current limits. Design-direction documents identify proposed capabilities separately.

| Guide | What it explains |
| --- | --- |
| [Windows runner](en/windows-runner.md) | Double-click installation, local execution, icon shortcut and personal data |
| [Linux runner](en/linux-runner.md) | Distribution detection, private tools, local execution and unattended checks |
| [macOS runner](en/macos-runner.md) | Intel/Apple Silicon installation, Finder launcher, private tools and local execution |
| [Getting started](en/getting-started.md) | Dependencies, configuration, migrations and first login |
| [User guide](en/user-guide.md) | Campaigns, scenes, sheets, journals and table workflows |
| [Campaign management](en/campaign-management.md) | Prepare campaign documents and assets in the GM workspace before entering the tabletop |
| [Map Builder](en/map-builder.md) | First project, Tiles/Painting, finished-map backgrounds, layers, saving, Smart Objects and scene updates |
| [Universal VTT importer/exporter](en/universal-vtt.md) | Import workflows, native maps/walls/doors/lights, warnings and error recovery |
| [Smart Objects direction](en/smart-objects-direction.md) | Proposed node editor, element capabilities, references and delivery order |
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

Current release: [Gravewright 0.3.1 — Alpha](releases/0.3.1.md), with consistent forms, Map Builder object menus and interactive models, dice and quest actions, and synchronization of game edits. The release notes cover installation and upgrading from 0.3.0, with no additional database migrations. [0.3.0 notes](releases/0.3.0.md) describe the original Map Builder, Smart Objects, Universal VTT support and their migrations; [0.2.3 notes](releases/0.2.3.md) retain the earlier release history.
