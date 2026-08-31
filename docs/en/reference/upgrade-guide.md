# Upgrade guide

## Marketplace registry-only dependency policy

Marketplace releases with Node dependencies must include `package-lock.json`.
Dependency specs must resolve through the approved npm registry; filesystem,
workspace, URL, Git and shorthand repository specs are rejected. Lock entries
must use the approved registry and include integrity metadata.

Remove project `.npmrc` files from release ZIPs. Installation uses a temporary,
credential-free npm configuration with scripts, audit, funding and workspaces
disabled.

## Capability naming

Use a stable name plus a SemVer protocol value:

```ts
provides: { "gravewright.storage": "1.0.0" }
requires: { "gravewright.storage": "^1.0.0" }
```

Do not encode `/v1` in the capability name.
