# Semantic presentations

`sdk.ui.presentations` describe proyecciones temporales sin conceder DOM, CSS, canvas o renderer. Es distinta de UI slots, applications y Directed Interactions.

Los modos limitados son `world-anchor`, `screen-overlay`, `title-card`, `countdown` y `fade`. El contenido admite texto, progreso, AssetReference autorizado y botones de registered actions; HTML, CSS, scripts y URLs arbitrarios se rechazan.

`show/get/list/update/close` usa handles server-owned, audience autorizada, CAS, expiry del servidor, cierre idempotente y reconstrucción tras reload. Los anchors invisibles fallan de forma cerrada. Presentation no concede navegación de Scene.
