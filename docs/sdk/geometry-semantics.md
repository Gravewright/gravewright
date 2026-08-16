# Geometry semantics

Logical walls expose a closed `behavior` object with `movement`, `vision` and `light`, each accepting only `block` or `pass`. Missing values default to `block`, preserving legacy wall behavior. Open doors pass every channel.

The core—not package code—executes movement collision, LOS and lighting filtering. Window, bars and invisible barriers use movement `block` with vision/light `pass`. Gravewright has no geometry-based effect propagation; `effects` is rejected rather than published as ignored metadata.

`presentation` accepts `normal`, `window`, `bars`, `invisible` or `secret`. Players do not receive invisible barriers. An undiscovered secret projects as an ordinary wall without discovery metadata; the GM receives its semantic presentation. Changes emit the aggregate `scene.geometry.changed` signal and consumers perform an authorized re-read.
