# Global search and command palette

The MVP indexes campaign actors, items, journals, scenes, and active-system
compendium packs. The portable SQL candidate search is bounded and does not
require FTS. `COMMAND_PALETTE_ENABLED=false` hides the UI and endpoint while all
existing panels remain available.

Each result has `id`, `type`, `title`, `subtitle`, `icon`, `snippet`, and a
non-destructive `target`. Folder names become subtitles. Existing resource
types act as tags until first-class tags exist. Journal text may contribute a
short snippet; raw documents and permission metadata are never returned.

The service first verifies campaign membership, then applies the existing actor,
item, journal, and scene authorization rules. Private results are filtered on
the server, never only in JavaScript. Compendiums are restricted to the GM
because the current content browser is GM-only.

The HTTP contract is `GET /game/search?campaign_id=<id>&q=<query>&limit=<n>`.
Queries shorter than two characters return an empty list; input is capped at
100 characters and output at 20 results. The reference objective is p95 below
150 ms for 5,000 resources on local SQLite. FTS may replace candidate matching
later without changing the response contract.
