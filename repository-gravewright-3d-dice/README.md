# Gravewright 3D Dice

Gravewright adaptation of [Dice So Nice](https://gitlab.com/riccisi/foundryvtt-dice-so-nice), using its mature dice geometry, physical shapes and face-rotation data behind a small Gravewright SDK 1 adapter.

This project is not affiliated with or endorsed by the upstream maintainers.

The Gravewright server remains authoritative. The adapter consumes authorized `chat.created` resources through `sdk.chat.get`, converts public `RollGroupDTO` values, reads author colors through `sdk.users.presentation.get`, and mounts only in the public `board.overlay` slot.

Customization from Dice So Nice is intentionally not ported. There is no theme, skin, material, texture, font, preset, SFX or appearance-editor UI. User color is automatic; the bundled Inter numeral font and all other appearance defaults are fixed by this addon.

The existing Gravewright top-down wooden and leather dice tray is preserved. No upstream tray or Foundry UI asset is included.

This adapted addon is GNU AGPL-3.0. See `UPSTREAM.md`, `ASSET_AUDIT.md`, and `THIRD_PARTY_NOTICES.md`.
