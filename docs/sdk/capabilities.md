# Capabilities

A package declares the capabilities it needs. The engine validates them against
the allow-list (rejecting unknown and forbidden ones), and the browser SDK gates
each method on the relevant capability.

## Allowed capabilities

```
actors.register      items.register

sheets.declarative   sheets.hooks        sheets.components
rules.declarative    rules.extends
dice.roll            rolls.intent
combat.config        combat.hooks
tokens.mappings      tokens.extends
scene.tools          scene.overlays
chat.cards
content.packs
settings
locales

assets.ui    assets.styles   assets.scripts
assets.pack  assets.images   assets.audio   assets.maps   assets.icons

hooks.client
commands.register
```

## Forbidden capabilities (always rejected)

```
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

There is no backend plugin execution in SDK v1.

## Enforcement

If a package calls an SDK method without the required capability, the runtime
throws a clear error, e.g.:

```
Package "x" attempted to use sdk.chat.send but does not declare capability "chat.cards".
```
