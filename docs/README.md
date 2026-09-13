# Documentation

[English](README.md) · [Português (Brasil)](README.pt-BR.md) · [Project home](../README.md)

English is the primary documentation. Each guide has a corresponding Portuguese version; source identifiers, API names and commands remain unchanged. This documentation describes the implementation in this checkout, including its current limits.

| Guide | What it explains |
| --- | --- |
| [Windows runner](en/windows-runner.md) | Double-click installation, local execution, icon shortcut and personal data |
| [Getting started](en/getting-started.md) | Dependencies, configuration, migrations and first login |
| [User guide](en/user-guide.md) | Campaigns, scenes, sheets, journals and table workflows |
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
