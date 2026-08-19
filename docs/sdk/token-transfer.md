# Token transfer

Token transfer moves a token from one scene to another while preserving the thing
that matters: it is still the same token, owned by the same people, with the same
identity everything else already references.

## Transfer is not navigation

Moving a token and moving a viewpoint are separate acts, and the SDK keeps them
separate on purpose.

- `sdk.tokens.transfer` / `sdk.tokens.transferMany` move a token between scenes.
- `sdk.navigation.scene.go` changes which scene a user is looking at.

A transfer on its own moves nobody's view. A GM may relocate a party's tokens while
players continue to look at what they were looking at, and a player may follow the
action without their token going anywhere. If you want both, do both — the transfer
accepts an optional `navigateAudience` for exactly that, and it is still audited as
a navigation of its own.

## Single and group transfer

```js
// One token.
await sdk.tokens.transfer(tokenId, { sceneId: innerVaultId, x: 12, y: 8 });

// The whole party, atomically.
await sdk.tokens.transferMany([
  { tokenId: tokenA, sceneId: innerVaultId, x: 12, y: 8 },
  { tokenId: tokenB, sceneId: innerVaultId, x: 13, y: 8 },
]);
```

`transferMany` is all-or-nothing. If any token in the batch fails — a stale
`expectedVersion`, a token the caller may not control, a destination they may not
see — nothing moves. A party cannot be split by a partial failure, which is the
whole reason the batch operation exists.

## Identity, ownership and coordinates

The token keeps its id, its actor link, its ownership and its overrides. Destination
coordinates are grid coordinates in the destination scene; elevation carries over
unless you set it. Source and destination must differ, and both must belong to the
caller's campaign.

## Zone membership

Zone membership is recalculated by core at both ends of the move: the token leaves
the zones it occupied in the source scene and enters the zones that contain its
destination point. Packages listening for `zone.entered` and `zone.left` receive the
resulting events; nothing needs to poll geometry.

## Authority

The caller must be able to control the token, under the same rule that governs
moving it normally, and must be able to see the destination scene. A player cannot
transfer another player's token, and a destination scene hidden from the caller is
not a legal destination — a hidden scene never becomes discoverable by attempting a
transfer into it.

Navigating other users remains a separate authority: a player can navigate only
themselves.

## Lifecycle

Transfers are persisted immediately. A player who reloads finds their token in the
destination scene; a client that was disconnected during the move reconciles on
reconnect from server state rather than replaying the event.

## Common errors

| Code | Cause |
|---|---|
| `VALIDATION_FAILED` | Same source and destination, non-finite coordinates, or a batch outside its bounds. |
| `NOT_FOUND` | Unknown token or scene, a token the caller cannot control, or a destination they cannot see. |
| `STALE_VERSION` | `expectedVersion` no longer matches for at least one token in the batch. |

## What this API does not expose

No cross-campaign movement, no way to move a token the caller could not move
directly, and no implicit navigation of users who were not addressed.
