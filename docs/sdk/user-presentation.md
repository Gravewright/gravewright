# User presentation

User presentation is the small, server-authoritative visual projection that packages may use to represent a participant consistently. SDK 1 exposes only a canonical lowercase `#rrggbb` color and the participant's already-visible user ID. It does not expose core settings, arbitrary preferences, profile data, email, locale, permissions, or authentication metadata.

Packages must declare `users.presentation.read`. Capability grant and user authority are separate checks: `list()` contains only members of the active campaign, and `get(userId)` succeeds only for a member visible in that campaign. An inaccessible campaign is rejected; an unknown or out-of-campaign target is indistinguishable from a missing resource.

```js
const participants = await sdk.users.presentation.list();
const presentation = await sdk.users.presentation.get(userId);

const dispose = sdk.events.on("user.presentation.changed", async event => {
  const current = await sdk.users.presentation.get(event.resourceId);
  updateParticipantColor(current.userId, current.color);
});
```

The event follows the normal SDK event lifecycle and is delivered only through campaign rooms. Its bounded event shape identifies the changed participant through `resourceId`; consumers re-read the authoritative projection. Dispose the subscription during package teardown.

A 3D dice addon, for example, can take the author user ID from an authorized roll DTO, call `presentation.get(authorUserId)`, and render that color. This does not require access to core settings and does not broaden roll visibility.
