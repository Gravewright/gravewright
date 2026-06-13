# Changelog

All notable changes to Gravewright should be documented here.

The project is currently in Alpha. Breaking changes may occur before 1.0, especially around database schema, storage layout, system manifests, module manifests, realtime events, and public extension APIs.

## Unreleased

### Added

- Documented locale-agnostic system sheet labels.
- Documented supported system combat hooks and slots.
- Documented the public boundary between supported system APIs and private renderer internals.

### Changed

- System-owned UI text is now the preferred path for sheet and combat labels.
- The engine keeps English fallback labels, but active systems may provide their own labels and combat UI text.
- D&D 5e system assets now define their own labels, locales, and combat UI text instead of relying on engine-hardcoded strings.
- Public API documentation now clarifies that documented APIs are the only stable extension contract during Alpha.

### Breaking Changes

- Existing Alpha systems may need updates to provide labels, locale keys, combat UI text, or compatible sheet/combat configuration.
- Hardcoded engine UI strings should no longer be treated as a stable extension surface.
- Undocumented sheet globals, combat globals, renderer internals, DOM structure, and fallback behavior remain private implementation details.
- Full combat renderer replacement is not part of the stable public API during Alpha.

### Known Issues

- Alpha releases do not guarantee an upgrade path for existing tables.