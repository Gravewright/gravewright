# Spatial Sounds persistentes

Los paquetes pueden usar `scene.spatialSounds.read` y `scene.spatialSounds.write`
para administrar los mismos emisores persistentes de Escena usados por las
herramientas nativas de Sonido de Gravewright. Esta autoridad de configuración es
independiente de `audio.playback`.

`sdk.scene.spatialSounds.create(sceneId, input)` recibe un `soundId` nativo,
`position` en coordenadas del mundo, `radius` acotado (mayor que 0 y como máximo
100000), gain entre 0 y 1, falloff `linear` o `smooth`, flags de loop/activación,
audience y el control semántico `constrainedByWalls`. No acepta URLs, rutas del
sistema, objetos de audio del navegador ni handles del renderer.

`list`/`get` devuelven configuración filtrada por audiencia. `update` y `delete`
usan `expectedVersion`; las mutaciones stale fallan atómicamente. La proyección
acústica de Walls y Doors permanece en el core y no revela geometría oculta. Borrar
la Escena elimina los emisores mediante el ciclo de vida nativo; descargar el
paquete no borra los datos de campaña.

