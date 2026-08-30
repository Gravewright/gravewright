# Minimal module templates

These templates contain only the files required by the current Gravewright architecture.

| Kind | Template | Purpose |
| --- | --- | --- |
| `server` | [`server/`](server/) | Required transport and composition contract |
| `campaign` | [`campaign/`](campaign/) | Campaign data and operations |
| `room` | [`room/`](room/) | Shared table or room behavior |
| `marketplace` | [`marketplace/`](marketplace/) | Module and recipe discovery |
| `ruleset` | [`ruleset/`](ruleset/) | Game rules and resolution |
| `addon` | [`addon/`](addon/) | Optional cross-cutting capability |
| `asset` | [`asset/`](asset/) | Asset storage, indexing, or delivery |
| `ui` | [`ui/`](ui/) | User interface capability |
| `system` | [`system/`](system/) | Game-system integration |

Only `server` has required exports. Every other template deliberately returns an empty object with a placeholder comment; add only the capabilities your module actually publishes.

Prefer generating a fresh template with the CLI because it follows the installed SDK version:

```bash
grave new addon my-module
grave new server my-server
```

After copying or editing a template:

```bash
grave module build modules/my-module
npm run types:sync
npm run typecheck
grave doctor
```

See the [English guide](../en/creating-a-module.md) or [guia em português](../pt-br/criando-um-modulo.md).
