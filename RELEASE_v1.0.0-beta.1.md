# Gravewright v1.0.0-beta.1

Released 2026-08-13.

Gravewright Beta 1 closes the Alpha line with the SDK 1 compatibility baseline stable and the
current tabletop, campaign, package, PDF, large-map, and renderer work integrated
into one release.

## Highlights

- GM-guided predictive tile prefetch and adaptive raster granularity.
- Dense shared-asset renderer validated on an RTX 4060 at approximately 7,500
  simultaneously visible synthetic dragons in the 60 Hz presentation band and
  approximately 10,000 in the 30 Hz band. The isolated callback-budget crossing
  occurred between 11,000 and 11,500 visible instances. These are stress-test
  figures, not realistic campaign token recommendations.
- Expanded SDK 1 with authorized actors, items, tokens, scenes, effects, combat,
  cards, journals, handouts, fog, scene images, events, PDF viewing, and complete
  PDF annotation CRUD. ID-addressed writes are bound to the authorized campaign.
- Campaign export/import and complete state snapshot support.
- Savage Worlds action-card initiative with deck selection, card artwork,
  authoritative ordering, round-only redeals, and Joker reshuffling.
- Three additive migrations: virtual raster v2, adaptive raster policy, and PDF
  annotations.

## Versions

- Product version: `1.0.0-beta.1`
- Python package version: `1.0.0b1`
- Public extension line: `SDK 1`
- Savage Worlds package: `1.1`

The exhaustive list of additions, changes, fixes, benchmarks, and migrations is
in [CHANGELOG.md](CHANGELOG.md).

Benchmark methodology, workload boundaries, and raw-result links are documented
in [docs/performance.md](docs/performance.md).
