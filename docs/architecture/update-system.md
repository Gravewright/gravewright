# Update system

Gravewright uses the existing package distribution pipeline for package updates. It does not
grant packages an updater capability and it never executes package-provided commands.

## Product releases

The owner-only administration surface queries published releases from the official repository.
It selects the installed release channel (`stable`, `beta`, or `alpha`), ignores drafts and
branches, and only exposes a platform artifact whose GitHub release metadata includes a SHA-256
digest. The current version remains the configured/packaged Gravewright version.

The application deliberately does not overwrite its own running executable. For the current
Win64 ZIP distribution the UI links the exact digest-bearing release artifact and tells the
operator to create a verified backup first. Source and container installations remain managed by
their deployment mechanism. An in-process `git pull` is never an update strategy.

## Package releases

`MarketplaceService` fetches curated publisher manifests through the shared remote URL policy,
validates SDK 1 and compatibility, and caches results atomically. `MarketplaceInstaller` downloads
only ZIP distributions with an approved SHA-256, stages and validates the archive, checks its
identity and dependency/conflict graph, runs the package doctor, and publishes it with rollback.

An update must be newer than the installed version. A globally enabled or campaign-active package
must be deactivated and disabled before replacement, preventing a campaign runtime from observing
half of an update. Package-managed storage and settings live outside the package code directory and
are therefore preserved.

`grave package update ID` retains its compatibility behavior of refreshing metadata from disk.
`grave package update ID --remote` uses the same Marketplace installer as the owner UI.

## Recovery and migrations

Package directory promotion keeps the prior tree until the database record is committed and
restores it on failure. Core operators use `grave backup --include-assets --include-packages
--verify` before installing a product release. Database migrations remain part of normal
Gravewright startup; no updater-specific database schema is introduced.
