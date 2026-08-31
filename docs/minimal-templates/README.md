# Minimal module templates

These templates contain only the files required by the current Gravewright architecture.

| Kind | Template | Purpose |
| --- | --- | --- |
| `server` | [`server/`](server/) | Required transport and composition contract |
| `room` | [`room/`](room/) | Complete campaign interface |
| `ruleset` | [`ruleset/`](ruleset/) | Game rules and resolution |
| `addon` | [`addon/`](addon/) | Optional extension |
| `system` | [`system/`](system/) | Backend service |

The only runtime cardinality rule is exactly one active server. Every other kind
is optional and may have multiple active implementations. Every kind publishes
`read`, `write`, and `stat`.

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
