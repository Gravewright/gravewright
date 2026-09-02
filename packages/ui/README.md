# @gravewright/ui

The interface language of Gravewright: one set of tokens, one set of BEM
blocks, one set of Vue primitives. Every surface — the setup screen, the table,
the gates, and every module that mounts into a room slot — draws from here.

```ts
// once, in the application entry point
import "@gravewright/ui/styles";
```

```vue
<script setup lang="ts">
import { GwButton, GwField, GwModal } from "@gravewright/ui";
</script>
```

## The scale is Fibonacci

Every dimensional value — spacing, padding, margin, gap, sizes, radii, type —
resolves to a step of the Fibonacci sequence in pixels, or to a sum of
non-consecutive steps:

```
--fib-1 … --fib-15  →  1 2 3 5 8 13 21 34 55 89 144 233 377 610 987
```

Zeckendorf's theorem says every positive integer is the sum of a unique set of
non-consecutive Fibonacci numbers. A value that does not land on a step is
therefore not an arbitrary literal: it is written as that sum, in `calc()`,
behind a named token. `--step-16` is `13 + 3`; `--nav-width` is
`233 + 55 + 8 + 3 + 1`. The scale stays honest and the geometry stays exact.

**Rules for new CSS**

1. Reach for a bare `--fib-*` step first.
2. If the geometry needs an in-between value, reach for the named `--step-*`
   / `--size-*` / `--text-*` composite in `styles/tokens.css`.
3. Two spacing families exist and must never be mixed in one rule: `--step-N`
   is exactly N pixels (ours); `--space-N` is the reference interface's scale
   of fours (`--space-4` is 16px), kept because the ported legacy stylesheets
   speak it.
4. Never write a raw pixel literal for a dimension. If a value is missing, add
   it to `tokens.css` as a Fibonacci sum, with the arithmetic in a comment.

Colours, shadow geometry and easing curves are not dimensions and stay literal.

## Naming is BEM

`block__element--modifier`, one block per file under `styles/blocks/`.

- A block never styles another block's elements. If a block needs to look
  different in a context, it gets a modifier (`gw-badge--plain`), not a
  descendant selector.
- A modifier never changes what a thing *is*, only how it reads.
- Blocks carry no layout of their own beyond their internal geometry: where a
  block sits is the parent's business.

The room-slot names the kernel mounts into — `gw-main`, `gw-grid`,
`gw-sidebar`, `gw-chat`, `gw-toolbar`, `gw-overlay` — are **not** blocks. They
are protocol identifiers, and no block in this package claims those names.

## The blocks

| Block | What it is |
| --- | --- |
| `gw-mark` | The house glyph: brand, nav bullet, empty-state marker. |
| `gw-button` | Every control that is pressed. One `--primary` per view. |
| `gw-field` / `gw-switch` | A label, its control, and its help. |
| `gw-form` / `gw-filters` | How fields sit together. |
| `gw-notice` | An alert as a left rule, never a tinted box. |
| `gw-badge` | A fact about a thing, in micro caps. Never pressed. |
| `gw-empty` | The dashed field a view stands in before it has anything. |
| `gw-modal` | A dialog over a blurred board. |
| `gw-shell` / `gw-nav` / `gw-panel` | The setup screen. |
| `gw-card` / `gw-row` / `gw-facts` | Every box on every tab. |
| `gw-campaign` | A table on the shelf, with its drawn cover plate. |
| `gw-gate` | The standalone screens: joining a table, unlocking setup. |
| `gw-stage` | The table itself, and what stands on it when it is empty. |
| `gw-window` | A floating panel over the board. |
| `gw-dock` / `gw-tool-dock` | The panel toggles and the tool rail. |
| `gw-layer-hud` | Which plane of the table you are editing. |
| `gw-tray` | Who is here, and how loud. |

## The active layer paints the table

Setting `data-table-layer` on `<body>` re-bases `--layer-accent-rgb`, and with
it `--border-accent` and `--border-accent-strong`. The docks, the panels and
the windows then say, through their border, which plane is being edited —
without a label, and without any rule having to know about layers.

```
game gold · gm red · composition blue · effects green · walls violet · lighting yellow
```

## Responsive

One breakpoint matters: `980px`, where the nav stops being a rail and becomes a
footer. Below `900px` card shelves drop to a single column; below `640px` the
page gutter tightens. `prefers-reduced-motion` collapses every transition at the
token level.
