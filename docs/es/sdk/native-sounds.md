# Assets de audio y Sounds nativos

El SDK mantiene cuatro conceptos separados: Asset almacena bytes canónicos, Sound
es contenido semántico reutilizable, Spatial Sound coloca ese contenido de forma
persistente en una Escena y Audio Playback representa estado de ejecución.

`sdk.assets.ingest(file)` acepta archivos de audio seleccionados por el usuario y
validados por firma, devolviendo un Asset con `kind: "audio"`.
`sdk.assets.list({ kind: "audio" })` lee Assets autorizados de campaña sin exponer
rutas de almacenamiento.

Los paquetes usan `sounds.read` y `sounds.write` para `sdk.sounds.list`, `get`,
`create`, `update` y `delete`. La creación acepta referencias `library-asset` o
`package-asset` declaradas. El audio del paquete pasa por la ingestión segura
canónica antes de crear el Sound nativo. Actualización y borrado usan
`expectedVersion` y conservan la política nativa de dependencias.


Borrar un Sound del que todavía dependen una Playlist, un Soundscape o un Sonido
espacial falla con `RESOURCE_IN_USE` e informa `details.dependencyCount`, igual que
la biblioteca nativa de Sounds; nada se elimina parcialmente. Un `expectedVersion`
obsoleto falla con `STALE_VERSION`. `audio.playback` nunca otorga autoridad sobre la
biblioteca de Sounds: reproducir audio y editar contenido reutilizable son
capabilities separadas.
