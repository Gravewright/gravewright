# Semantic presentations

`sdk.ui.presentations` descreve projeções temporárias sem conceder DOM, CSS, canvas ou renderer. Difere de UI slots, applications e Directed Interactions, que persistem respostas autoritativas.

Os modes limitados são `world-anchor`, `screen-overlay`, `title-card`, `countdown` e `fade`. Conteúdo aceita texto, progresso, AssetReference autorizado e buttons de registered actions; HTML/CSS/script/URL arbitrários são rejeitados.

`show/get/list/update/close` usa handles server-owned, audience autorizada, CAS, expiry server-derived, close idempotente e reconstrução após reload. Anchors invisíveis falham fechados. Presentation não concede navigation de Scene.
