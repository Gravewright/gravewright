# Manifest

`manifest.json` é a fronteira estática de segurança e composição. O kernel o valida antes de importar o código.

O schema legível por ferramentas está em
[`docs/schema/manifest-v1.json`](../../schema/manifest-v1.json). A validação de
runtime continua sendo a autoridade para regras semânticas, como faixas SemVer.

```json
{
  "name": "dice-roller",
  "kind": "addon",
  "provider": "community",
  "version": "1.0.0",
  "entry": "./index.ts",
  "types": "./types.ts",
  "dependencies": {},
  "exports": { "get": ["read", "write", "stat", "roll"] }
}
```

Ele também pode declarar `routes`, `middleware`, `slots`, `dependencies` concretas,
capabilities `requires`/`provides` e campos de release. Uma room também declara
`room_protocol: "gravewright.room/v1"` e seus `exposes.slots` canônicos. Paths de
entry e types permanecem dentro do módulo.

```bash
grave module build modules/dice-roller
grave module build modules/dice-roller --check
```

O manifest não é uma sandbox: o código instalado ainda executa com as permissões do processo host.

## Manifest com composição e release

```json
{
  "name": "character-sheet",
  "kind": "system",
  "provider": "community",
  "version": "2.1.0",
  "entry": "./index.js",
  "types": "./types.d.ts",
  "dependencies": { "campaign-api": "^1.0.0" },
  "routes": { "/characters": "characters" },
  "middleware": { "/characters": ["authenticate"] },
  "slots": { "room.sidebar": ["sidebarPanel"] },
  "exports": { "get": ["read", "write", "stat", "characters", "authenticate", "sidebarPanel"] },
  "download_url": "https://example.org/releases/character-sheet-2.1.0.zip",
  "download_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

A release é rejeitada se o hash divergir, nome/versão do ZIP não coincidirem ou a entry escapar do pacote.
