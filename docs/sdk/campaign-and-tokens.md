# Campaign roster and token control

Two reads exist so a package can *address* the right person: who is at this table,
and who drives this token.

## `sdk.campaign.members()`

Returns the campaign roster — the same membership the native table already shows the
caller.

```js
const roster = await sdk.campaign.members();
// [{ userId, role, name }, ...]
const players = roster.filter((member) => member.role === "player");
```

Each entry carries a user id, the member's role in this campaign, and a display
name. That is all: no email, no account metadata, no credentials.

The roster is membership, **not presence**. It says who belongs to the campaign, not
who is currently connected; there is no online status here and no presence feed
behind it. Read it again when you need current membership — a member who was removed
is gone from the next authoritative read.

The call is campaign-scoped and answers only for a caller who is themselves a member.
There is no cross-campaign directory and no global user enumeration.

Requires `campaign.members.read`.

## `TokenDTO.controllers`

Every token you can read carries the users who may control it.

```js
const token = await sdk.tokens.get(tokenId, { sceneId });
// token.controllers -> ["gm-user-id", "player-user-id"]
```

These are the canonical control relationships, derived from the same authority that
decides whether a move is allowed. A token owned by two players lists both, plus the
GM; the list is never collapsed to a single "primary" user, because a package should
choose its own recipient policy rather than inherit ours.

**The projection is filtered.** Seeing a token on the board is not authority to learn
who drives it: controllers are returned only for tokens the caller could control
themselves. A player sees controllers on their own token and an empty list on
another player's, which is what keeps a shared board from becoming a roster
side-channel. A hidden token is absent entirely, controllers included.

## Addressing, not delegation

A controller id is a targeting reference. It confers nothing.

Knowing that a user controls a token does not let a package move that token, respond
as that user, or execute anything on their behalf. Every subsequent operation still
derives its principal from the authenticated session.

## Typical flow

Reacting to someone entering a region, and asking *that* person to decide:

```js
sdk.events.on("zone.entered", async (event) => {
  const zone = await sdk.scene.zones.get(event.zone_id);
  if (zone?.type !== "my-package.restricted") return;

  const token = await sdk.tokens.get(event.token_id, { sceneId: event.scene_id });
  const roster = await sdk.campaign.members();
  const players = new Set(roster.filter((m) => m.role === "player").map((m) => m.userId));
  const recipient = (token?.controllers || []).find((userId) => players.has(userId));
  if (!recipient) return;

  await sdk.interactions.request({
    recipients: [recipient],
    title: "Restricted area",
    text: "You have crossed the line. Continue?",
    responseSchema: { type: "boolean" },
    deadline: Math.floor(Date.now() / 1000) + 300,
  });
});
```

The zone event supplies a token id; the token resolves the person; the roster tells
you which of them is a player rather than the GM. The decision then belongs to the
authenticated recipient alone.

## Common errors

| Code | Cause |
|---|---|
| `CAPABILITY_REQUIRED` | `campaign.members.read` was not declared. |
| `PERMISSION_DENIED` | The caller is not a member of the requested campaign. |

## What these APIs do not expose

No presence, no account identity beyond a display name, no cross-campaign lookup, and
no controller information for tokens the caller could not control.
