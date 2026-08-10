# Dice tray, rolls, and naming

The dice tray builds a notation string and sends it to the chat as `/roll` or
`/gmroll`. It never rolls anything itself: the chat is where a roll is evaluated,
persisted, and turned into a card, so there is one result format and one history
instead of two.

## Notation

The tray speaks the evaluator's notation, not Foundry's:

| Intent | Notation | Notes |
| --- | --- | --- |
| Dice | `2d6`, `1d20`, `1d%`, `1dF` | `d%` is percentile, `dF` is Fudge (−1..1). |
| Drop lowest / highest | `2d20L1`, `6d6L1H2` | `Ln`/`Hn` **drop** n dice. `L` is written before `H`. |
| Explode | `1d6!`, `1d12!` | Open-ended: see below. |
| Modifier | `2d6+3`, `1d8-1` | |
| Best of | `max(1d8!,1d6!)` | Used by the Savage Worlds bonus die. |

`kh`/`kl` are another system's notation and are rejected by the evaluator.

## Exploding dice are open-ended

`!` keeps rolling while the die lands on its maximum. A d12 that rolls 12 rolls
again, and again, for as long as it keeps rolling 12; every die in the chain is
shown in the roll card.

Two rules bound it:

- Dropping resolves **before** any explosion. In `4d6L1!` the lowest of the four
  opening dice is dropped, and the dice that explosion adds are never candidates
  for dropping — otherwise `L`/`H` would change meaning mid-roll.
- Dice with no meaningful maximum do not explode: `dF` (which runs −1..1) and
  `d1` (which would never stop). A ceiling per roll keeps a pathological
  expression from hanging the request.

The SDK formula function `explode(sides, threshold)` documented in
`../sdk/rolls.md` is a different engine used by system formulas. It chains the
same way; the two agree.

> Before v3.0.1-alpha, `!` added a single extra die per maximum and never
> re-examined it, so chains stopped at two dice and open-ended totals were
> systematically low.

## Naming a roll

The name field in the tray is optional and never blocks a roll. It labels the
roll for everyone at the table:

- it appears in the **roll toast** (`{author} — {label}: {total}`);
- it appears in the **chat message**, above the notation, live and after a reload.

The name travels as a message label after `#`, which the evaluator's notation
never uses:

```text
/roll 2d6+1 # Sword damage
/gmroll 1d20 # Stealth
```

Anything after `#` is the label (48 characters, trimmed); everything before it is
the expression. A `#` with nothing after it is not a label. Typing the command by
hand in the chat works exactly the same way, and a secret roll keeps its name.

The label is stored as the message's `content`, which is the same field the page
rehydrates the chat history from — so a named roll is still named after a reload.

## The tray history

Every successful roll is remembered per table, in the browser
(`localStorage`, key `gravewright.dice.history.v1.<campaign_id>`):

- up to 30 entries, most recent first;
- an entry keeps the name it was given, and clicking it restores both the
  expression and the name;
- the same expression with different names are separate entries — `2d6` and
  `2d6` named "Damage" are different shortcuts;
- each entry can be removed individually.

Because it lives in the browser, the history is per browser and per table, and it
is **not** part of a campaign backup. Histories written by older versions are
read as unnamed entries.
