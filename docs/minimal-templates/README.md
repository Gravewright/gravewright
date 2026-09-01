# Minimal module templates

These templates contain only the files required by the current Gravewright architecture.

| Kind | Template | Purpose |
| --- | --- | --- |
| `server` | [`server/`](server/) | Required transport and composition contract |
| `room` | [`room/`](room/) | Complete campaign interface |
| `ruleset` | [`ruleset/`](ruleset/) | Game rules and resolution |
| `chat` | [`chat/`](chat/) | Interoperable messages |
| `dice-engine` | [`dice-engine/`](dice-engine/) | Dice expression engine |
| `assets` | [`assets/`](assets/) | Asset persistence and resolution |
| `storage` | [`storage/`](storage/) | Structured persistence |
| `addon` | [`addon/`](addon/) | Optional extension |
| `backend` | [`backend/`](backend/) | Backend service |

`server` requires exactly one active implementation. `room`, `ruleset`, `chat`,
`dice-engine`, `assets`, and `storage` accept at most one; `backend` and `addon`
accept many. Administrative `read`, `write`, and `stat` hooks are optional.

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
