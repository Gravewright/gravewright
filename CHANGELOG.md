# Changelog

All notable changes will be documented here. Gravewright remains pre-1.0; no
1.0 release or API freeze is declared by this file.

The target of this preparation cycle is `0.9.0` pre-freeze. Version numbers are
not changed by the preparation itself; release versioning happens separately.

## Unreleased

- Harden marketplace npm dependency installation to registry-only packages.
- Normalize IPv4-mapped IPv6 addresses before network policy checks.
- Bound server route and middleware bridges across repeated lifecycle cycles.
- Add kernel state-machine and capability-resolution coverage.
- Document manifest schema v1, compatibility policy, API status and upgrade notes.
- Align `DynamicContext` diagnostics with the typed `Context` contract.
- Formalize module ownership, surface minimization and framework/transport non-goals.
