# Audio Assets and Native Sounds

The SDK keeps four separate concepts: an Asset stores canonical bytes, a Sound is
reusable semantic content, a Spatial Sound places that content persistently in a
Scene, and an Audio Playback is runtime state.

`sdk.assets.ingest(file)` accepts user-selected, signature-validated audio files and
returns an Asset whose `kind` is `audio`. `sdk.assets.list({ kind: "audio" })` reads
authorized campaign Assets. No storage path is exposed.

Packages use `sounds.read` and `sounds.write` for `sdk.sounds.list`, `get`, `create`,
`update`, and `delete`. Creation accepts a `library-asset` or a declared
`package-asset` reference. Package audio is copied through the canonical safe
ingestion pipeline before the native Sound is created. Updates and deletion use
`expectedVersion`; deletion retains the native dependency policy for Playlists,
Soundscapes, and Spatial Sounds.


A delete that a Playlist, Soundscape, or Spatial Sound still depends on fails with
`RESOURCE_IN_USE` and reports `details.dependencyCount`, exactly as the native Sound
library does; nothing is partially removed. A stale `expectedVersion` fails with
`STALE_VERSION`. `audio.playback` never grants authority over the Sound library:
playing audio and editing reusable content are separate capabilities.
