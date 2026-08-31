# CLI reference

Run locally with `npm run grave -- <command>` or as `grave <command>` when the
binary is installed.

## `grave run`

Plans, activates, composes, and starts the project.

```bash
grave run [--diagnostic] [--diagnostic-file <path>]
```

`--diagnostic` writes semantic audit actions. The status means whether the
software action completed, not whether a game check succeeded.

## `grave new`

```bash
grave new <server|room|ruleset|addon|backend> [name] [--example-complete]
```

Creates a disabled module scaffold. The complete variant also includes an
example README, test, and diagnostic event.

## `grave doctor`

```bash
grave doctor [--json]
```

Validates project state, manifests, dependencies, capabilities, room contracts,
and the exactly-one-server rule. `--json` is intended for automation.

## `grave module build`

```bash
grave module build [path] [--check]
```

Generates static artifacts from the module definition. `--check` performs no
update and exits unsuccessfully when generated files are stale.

## `grave help`

```bash
grave help [command]
grave <command> --help
```

Shows the global help or command-specific syntax.
