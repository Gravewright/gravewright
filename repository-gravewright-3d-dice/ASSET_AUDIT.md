# Asset audit

| Family | Source | Decision |
|---|---|---|
| Geometry and physical-shape data | Dice So Nice `DiceModels.js`, AGPL-3.0 | Included |
| Resin PBR roughness map | Dice So Nice `roughnessMap_resin.webp`, distributed with AGPL source | Included |
| Other upstream textures/themes | Mixed credits; unnecessary for fixed appearance | Excluded |
| Upstream sounds | Includes separately sourced effects | Excluded |
| Dice So Nice upstream fonts | Not required | Excluded |
| Inter 4.1 variable webfont | Official rsms/inter release, SIL OFL-1.1 | Included unchanged for fixed dice numerals |
| Upstream GLB/Blend models | Not required for base dice | Excluded |
| Upstream icons/UI | Foundry-specific | Excluded |
| Top-down wooden tray | Gravewright project asset | Included unchanged |
| Mint resin surface experiment | Created for Gravewright | Retained in source tree but not used by the package |

Only upstream engine data covered by the upstream AGPL distribution is imported. Optional or ambiguous asset families are excluded.
