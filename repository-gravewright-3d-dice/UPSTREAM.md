# Upstream

- Project: Dice So Nice
- Repository: https://gitlab.com/riccisi/foundryvtt-dice-so-nice
- Version: 6.2.9
- Commit: `e427713c9db42b3bc629af9d6c6eeba95ab0026e`
- License: GNU AGPL-3.0
- Authors declared upstream: Simone, JDW
- Port date: 2026-08-25

## Reused upstream engine

`src/upstream/DiceModels.js` preserves render geometries, cannon-es convex shapes, face values and rotation combinations.

## Gravewright boundary

- Foundry rolls → public `ChatMessageDTO.groups` adapter.
- Foundry hooks → public `chat.created` subscription.
- Foundry settings → `UserPresentationDTO`.
- Foundry canvas → addon-owned `board.overlay` slot.
- Foundry module URLs → Gravewright package assets.
- Foundry lifecycle → SDK mount/unmount callbacks.

Foundry UI, customization, themes, tours, settings, flags, SFX, persistent dice, manual interaction and special effects are excluded.
