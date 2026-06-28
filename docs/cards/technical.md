# Cards Technical Notes

Cards live under `app/engine/decks/`.

The implementation follows Gravewright's existing persistence conventions:

- IDs are `uuid4().hex` strings stored as `String(64)`.
- JSON payloads are stored in `Text` columns with explicit encode/decode in repositories.
- Card state changes are server-side only; clients request operations.
- Hidden card responses redact card definition IDs, names, front asset IDs, tags, and metadata.

Main backend entry points:

- `app.engine.decks.cards`: pure domain enums, helpers, draw/move/redaction logic.
- `app.engine.decks.card_service`: permission-aware application service.
- `app.persistence.repositories.card_repository`: SQLAlchemy Core repository.
- `app.actions.game.manage_cards`: protected Litestar HTTP handlers.

HTTP endpoints:

- `GET /game/cards/state/{campaign_id}`
- `POST /game/cards/assets/upload`
- `POST /game/cards/decks`
- `POST /game/cards/decks/instantiate`
- `POST /game/cards/decks/shuffle`
- `POST /game/cards/decks/reset`
- `POST /game/cards/draw`
- `POST /game/cards/reveal`
- `POST /game/cards/discard`
- `POST /game/cards/play-to-scene`
- `POST /game/cards/scene-placement/update`
- `POST /game/cards/scene-placement/discard`

Clients should listen for `cards.state.updated` and refetch state. The event intentionally
does not include card payloads, so private card data cannot leak through a room broadcast.

`GET /game/cards/state/{campaign_id}` includes `scene_placements` for cards the viewer is
allowed to know exist. Card front/name/metadata visibility still comes from the redacted
`cards` array.

Card image upload reuses Gravewright's journal asset storage with card-specific purposes
(`card_front`, `card_back`). Only GM/assistant GM users can upload card assets for a
campaign.
