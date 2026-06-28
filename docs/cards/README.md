# Cards and Deck Piles

Gravewright includes a generic, server-authoritative cards subsystem for campaign decks,
draw piles, discard piles, player hands, scene card placements, reveal/discard actions,
and persisted card events.

Current backend support includes:

- GM-created deck definitions from structured card metadata.
- GM card image uploads for card fronts and backs.
- Deck instances with default draw, discard, revealed, and removed piles.
- Player hands as private owner-only piles.
- Server-side shuffle, draw, reveal, discard, and reset.
- Playing cards to scenes, updating scene placement, flipping scene cards, and discarding
  scene cards back to the deck discard pile.
- Rich persisted chat messages for cards drawn revealed to chat.
- Per-viewer redaction for hidden card fronts and metadata.
- Realtime `cards.state.updated` notifications for clients to refresh state.

Visual scene manipulation UI and package-provided deck import are planned follow-up layers
on top of this backend foundation.
