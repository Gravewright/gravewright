# Semântica de geometria

Walls lógicas expõem um objeto fechado `behavior` com `movement`, `vision` e `light`, cada um aceitando somente `block` ou `pass`. Valores ausentes usam `block`, preservando walls legadas. Doors abertas passam em todos os canais.

O core — nunca código de package — executa colisão de movimento e filtros de LOS e iluminação. Window, bars e invisible barrier usam movement `block` com vision/light `pass`. Como não existe propagação de efeitos baseada em geometria, `effects` é rejeitado em vez de publicado como metadata ignorada.

`presentation` aceita `normal`, `window`, `bars`, `invisible` ou `secret`. Players não recebem invisible barriers. Secret não descoberto é projetado como wall comum sem metadata de discovery; GM recebe a apresentação semântica. Mudanças emitem o sinal agregado `scene.geometry.changed` e consumers fazem nova leitura autorizada.
