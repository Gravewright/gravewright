# Browser API modules

Default folder for module sources written against the public extension
interface in `api/` and the browser contracts in
`gravewright/modules/contracts/`. Configured by `GRAVEWRIGHT_API_MODULES_ROOT`
in `.env` and exposed to tooling as the Django setting of the same name.

This folder holds authoring sources and build inputs only. The host installs
modules from signed marketplace archives into `MEDIA_ROOT/modules`, and never
imports Python or executes binaries from a package. Nothing placed here is
loaded automatically; a module becomes available after it is packaged, signed
and installed through the marketplace.

Folder contents are ignored by git, so third-party modules stay outside this
repository's history. Keep each module in its own subdirectory.

See `docs/en/modules.md` and `docs/en/api.md`.
