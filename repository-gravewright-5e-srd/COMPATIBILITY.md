# Compatibility

## Gravewright compatibility

This package targets:

```text
Gravewright core: 3.0.0-alpha
SDK: 1
```

Manifest compatibility:

```json
{
  "minimum": "1.0.0-rc.1",
  "verified": "1.0.0",
  "maximum": "1.x"
}
```

The manifest compatibility window targets the SDK API line, not the core
marketing version. Alpha 3.0.0 continues to provide SDK 1.

## Package kind

```json
{
  "kind": "ruleset",
  "activation": {
    "scope": "campaign",
    "mode": "exclusive"
  }
}
```

A campaign should normally activate only one ruleset.

## SDK capabilities

The package declares:

```text
actors.register
items.register
sheets.declarative
sheets.runtime
rules.declarative
content.packs
tokens.mappings
dice.roll
chat.cards
rolls.intent
locales
assets.ui
assets.styles
assets.scripts
combat.config
```

## Package path

Expected local path:

```text
data/packages/rulesets/dnd5e
```

## Compatibility scope

This package is intended as a 5e/SRD-compatible framework. It does not guarantee
feature parity with every official or third-party 5e product.

## Breaking changes

Breaking changes should be documented in `CHANGELOG.md`.

Examples of breaking changes:

- actor schema field removal or rename;
- item schema field removal or rename;
- content pack ID rename;
- actor/item type ID rename;
- package ID rename;
- capability removal;
- sheet path rename;
- rule formula ID rename.
