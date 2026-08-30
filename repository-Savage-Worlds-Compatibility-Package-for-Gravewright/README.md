<img src="assets/SW_LOGO_FP_2018.png" alt="Savage Worlds" width="300">

Official logo source: [SW_LOGO_FP_2018.png](https://peginc.com/wp-content/uploads/2019/01/SW_LOGO_FP_2018.png)

# Savage Worlds Compatibility Package for Gravewright

An SDK 1 ruleset package providing editable actor and item sheets, exploding-die rolls, combat automation, localized chat cards, Bennie notifications, and card-based initiative for Gravewright.

Package version: **1.1.0**

> This game references the Savage Worlds game system, available from Pinnacle Entertainment Group at www.peginc.com. Savage Worlds and all associated logos and trademarks are copyrights of Pinnacle Entertainment Group. Used with permission. Pinnacle makes no representation or warranty as to the quality, viability, or suitability for purpose of this product.

This free package provides technical compatibility only. It is not sold or paywalled and does not distribute rulebook text, PDFs, compendia, setting material, or other Pinnacle game content. Users provide their own game data and rules references.

Português do Brasil: [README.pt-BR.md](README.pt-BR.md)

## Features

- Wild Card, Extra, Vehicle, and Group actor sheets.
- Skill, Weapon, Armor, Shield, Gear, Edge, Hindrance, and Power items. Dropped items become independent editable copies on the actor.
- Acing trait and damage dice, Wild Die support, unskilled rolls, situational modifiers, multi-action penalties, range modifiers, and raise damage.
- Automatic Parry, Toughness, load limit, encumbrance, and wound/fatigue penalties.
- Conditions synchronized with the effect system and applied to derived values and matching roll intents.
- Roll cards translated in each viewer's selected language, with formulas and individual dice kept in an expandable details section.
- Localized toast feedback when Bennies are gained or spent.
- Action Card initiative using an instantiated campaign deck: initial shuffle, reveal one card per combatant in chat, order by rank and suit, and reshuffle only after a round in which a Joker was dealt.

## Action Card initiative

Create or instantiate a standard playing-card deck in Gravewright's Cards panel. In an active encounter, the GM can press **Deal Action Cards** in the combat toolbar. The package uses the first deck with enough cards, or resets the first available deck when required.

Card names are interpreted in English or Portuguese. Jokers appear first as the tracker's default order but may act at any time; the remaining cards run from Ace through Two, with ties resolved by Spades, Hearts, Diamonds, and Clubs. The deck is shuffled initially and then only after a round in which a Joker was dealt. Deck authors may avoid name parsing by placing numeric `initiative` (and optional `suitRank`) values in card metadata.

## Package layout

```text
assets/       Ruleset CSS and image assets
scripts/      Ruleset browser controllers and automations
sheets/       HTML actor sheets
layouts/      Declarative sheets and item layouts
schemas/      Actor and item data schemas
rules/        Formulas, derived data, actions, conditions, validation, combat
mappings/     Chat, toast, and token presentation
locales/      English and Brazilian Portuguese catalogs
```

Savage Worlds-specific CSS and JavaScript live inside this package. Changes to Gravewright core are limited to system-neutral SDK/rendering contracts.

## Install and validate

From the Gravewright repository:

```bash
grave package validate data/packages/rulesets/savage-worlds
grave package install data/packages/rulesets/savage-worlds --yes --enable
```

Activate `savage-worlds` as the campaign's exclusive ruleset. After updating package files, reinstall or restart the development server if its package cache is enabled.

## License

The original code and declarative compatibility data in this package are licensed under the [Apache License 2.0](LICENSE). That license does not apply to the Savage Worlds name, trademarks, or supplied logo. See [NOTICE](NOTICE) for the permission notice and distribution boundary.
