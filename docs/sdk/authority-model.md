# Authority model

Every SDK call follows the same path. Understanding it once explains most of the
behaviour you will meet, including the refusals.

```
package intent
  → declared capability
  → authenticated principal
  → that principal's current authority
  → core mutation
  → projection filtered for the reader
```

A package expresses an intent. The capability it declared decides whether that kind
of intent is available to it at all. The session decides *who* is asking. The
campaign's permissions decide whether that person may do it. Core performs the
change. What comes back is filtered for whoever is reading.

## A capability is permission to ask, not authority to act

Declaring `tokens.transfer` does not let a package move any token; it lets the
package ask, on behalf of a user who could already move that token. A capability
never raises a player to a GM, and a package running in a player's browser has
exactly that player's authority.

This is why two users running the same package see different results from the same
call, and why a package cannot escalate by declaring more capabilities.

## Identity comes from the session

Every operation derives its principal from the authenticated session. A package
cannot act as another user, and knowing a user's id changes nothing — ids appear in
DTOs so a package can *address* someone, never so it can *become* them.

Concretely: a package may learn from `TokenDTO.controllers` who drives a token, and
still cannot move that token. It may address a directed interaction to that user, and
still cannot answer it for them.

## Visibility is a projection, not a filter you apply

Core decides what a reader may see before it returns anything. Hidden resources are
absent rather than marked hidden, so a package cannot infer their existence from the
response. A token you may not inspect returns no controllers; a scene you may not see
is not a valid destination; a private submission is simply not in the payload.

The practical consequence: never treat an empty result as proof that something does
not exist. It means *you* cannot see it.

## Campaign isolation

Every call is scoped to one campaign. A package activated in campaign A cannot read
or write campaign B, even for a user who belongs to both, and no API enumerates
resources across campaigns.

## Concurrency

Mutations that can conflict accept `expectedVersion` and fail with `STALE_VERSION`
when the resource has moved on. Nothing is partially applied: a rejected mutation
leaves the resource exactly as it was. Re-read, decide again, retry.

## What a package can never do

- act as another user, or answer a decision addressed to them;
- bypass campaign permissions by declaring a capability;
- read a hidden resource because it declared a capability that covers its type;
- reach another campaign;
- reach the database, the filesystem, the renderer, or a private route;
- assert that something happened at a time core did not agree to.

If you find an operation you believe should be possible and is refused, it is worth
checking whether the acting *user* could perform it directly. That is almost always
the answer.
