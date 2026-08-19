# Semantic presentations

`sdk.ui.presentations` describes temporary user-facing projections without granting DOM, CSS, canvas, or renderer access. It differs from UI slots (stable embedded areas), applications (package windows), and Directed Interactions (persistent authoritative answers).

The bounded modes are `world-anchor`, `screen-overlay`, `title-card`, `countdown`, and `fade`. Content is plain text, numeric progress, authorized asset references, and buttons backed only by registered actions. Raw HTML, CSS, URLs, scripts, and inline handlers are rejected.

`show/get/list/update/close` operate on server-owned handles. Remote audiences require GM authority, updates use `expectedVersion`, expiry is server-derived, close is idempotent, and active recipient projections reconstruct after reload. World anchors accept visible Tokens or scene world objects; inaccessible/deleted anchors fail closed. Presentations never change scene navigation authority.
