# Show to Players

The action lives on a journal, standalone item, or library image. It opens a
transient recipient dialog where the GM chooses all players or specific
members. Submitting immediately opens the content for those recipients.

The contextual action does **not** create a permission grant. Ordinary `can_view`,
ownership, and edit authorization remain unchanged before and after presentation.

## Security model

- Only the campaign GM can initiate a presentation.
- The resource and every selected recipient must belong to the same campaign.
- The server issues a distinct HMAC ticket for each recipient.
- Tickets are bound to the authenticated user, one resource, and a 90-second
  validity window.
- Presentation rendering is always read-only and still filters GM-only journal
  content according to the recipient's campaign role.
- The detailed realtime event is delivered directly without a room ID, so its
  ticket and resource type never enter the room replay log.
- Knowing a resource ID or another user's ticket does not bypass normal routes.

`TARGETED_HANDOUTS_ENABLED=false` hides the action and makes presentation routes
return 404 after restart.

## HTTP endpoints

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `POST /game/handouts/present` | GM | Validate the audience and send personal presentation tickets. |
| `GET /game/handouts/presentation/{ticket}` | Ticket recipient | Render the requested journal, item, or image read-only. |

Successful presentations are recorded as `handout.presented` without persisting
the ticket or changing resource permissions.
