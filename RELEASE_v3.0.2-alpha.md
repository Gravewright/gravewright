# Gravewright v3.0.2-alpha

Released 2026-08-11.

This is a focused shader lifecycle hotfix for the Alpha 3 line. It contains no
database migration and does not change the public SDK or shader ABI.

## Fixed

- Temporal scene shaders continue animating when the camera, tokens, and board
  are otherwise idle. Frames are requested through Gravewright's existing
  deduplicated on-demand scheduler only while an active shader has non-zero
  speed.
- Saving edited GLSL replaces the active compiled runtime immediately. Old mesh
  and program resources are invalidated and disposed on source changes, remote
  refreshes, deletion, scene clearing, failed-save rollback, and invalid-source
  recovery.
- Uniform-only edits remain lightweight and do not force GLSL recompilation.

## Validation

- The shader lifecycle JavaScript harness passes, including continuous-frame,
  static-idle, repeated-edit, disposal, deletion, and invalid-source recovery
  cases.
- Release artifacts are produced from `grave.spec` for Windows x64.

## Version

- Core version: `3.0.2-alpha`
- Python package version: `3.0.2a0`
