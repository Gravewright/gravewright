# Authoritative Rolls

Gravewright rolls are evaluated on the server. A package sends a formula or an
action intent; the engine evaluates dice, builds roll groups, renders the chat
card, broadcasts it, and returns the same authoritative result to the caller.

Use this guide for any ruleset style. The formula engine is system-neutral: step
dice, advantage/disadvantage, success pools, variable dice, Fate dice, card
draws, and helper formulas all use the same path.

## Formula Syntax

| Feature | Syntax | Notes |
|---|---|---|
| Arithmetic | `+ - * /`, parentheses, unary `-` | Standard precedence. |
| Comparison and logic | `== != < <= > >=`, `&&`, `||` | Returns `1` or `0`. |
| Actor paths | `@core.name`, `@sheet.strength`, `@sheet.rank` | `@sheet` is the actor sheet/system data supplied to rules. Missing paths are `0`. |
| Input scope | `input.amount` | Used by declarative actions with runtime inputs. |
| Dice notation | `1d20`, `2d6`, `2d20kh1`, `2d20kl1` | `kh1` keeps the highest die; `kl1` keeps the lowest. |
| Dynamic dice | `die(sides)`, `die(count, sides)` | Sides and count may come from `@paths`. |
| Exploding die | `explode(sides, threshold)` | Rolls `1d{sides}` until a result is below `threshold`. |
| Success pool | `successes(count, sides, target)` | Counts dice at or above target. |
| Roll under | `under(count, sides, target)` | Counts dice at or below target. |
| Fate dice | `fate()` | Rolls four Fate/Fudge dice, returned as `4dF`. |
| Card draw | `draw(n)` | Draws one card index from a deck size. |
| Builtins | `floor`, `ceil`, `round`, `abs`, `min`, `max`, `clamp`, `if` | `if(cond, a, b)` returns `a` when `cond != 0`. |
| Helpers | `abilityMod(@sheet.str.score)` | Helpers are declared in `rules/formulas.gw.json`. |

## Safety Limits

Formulas are parsed by a dedicated evaluator. They do not execute JavaScript,
Python, SQL, or package code.

Limits enforced by the engine:

| Limit | Value |
|---|---:|
| Maximum expression length | `200` characters |
| Maximum dice count per group | `100` |
| Maximum dice sides | `1000` |
| Maximum helper recursion depth | `16` |

Invalid formulas, unsafe dice counts, out-of-range sides, bad helper definitions,
and division by zero fail server-side.

## Common System Patterns

| Pattern | Formula |
|---|---|
| Step die with explosion | `explode(@sheet.traitDie, @sheet.traitDie)` |
| Advantage | `2d20kh1` or `max(1d20, 1d20)` |
| Disadvantage | `2d20kl1` or `min(1d20, 1d20)` |
| Success pool | `successes(@sheet.pool, 10, 8)` |
| Roll-under pool | `under(@sheet.pool, 20, @sheet.target)` |
| Variable stat die | `die(@sheet.attributeDie)` |
| Multiple variable dice | `die(@sheet.count, @sheet.sides)` |
| Fate roll with modifier | `fate() + @sheet.approach` |
| Clamped resource check | `clamp(1d20 + @sheet.bonus, 1, 30)` |

Each dice expression contributes one entry to `groups`, for example:

```json
{
  "notation": "2d20kh1",
  "results": [4, 17],
  "subtotal": 17
}
```

## Runtime API

### `sdk.dice.roll({ formula, label?, actorId? })`

Requires `dice.roll`.

Posts to `POST /game/actor/roll`. Use it when the package already knows the
formula and only needs an authoritative roll and chat card.

```js
await sdk.dice.roll({
  actorId: ctx.actor.id,
  label: "Strength",
  formula: "explode(die(@sheet.strengthDie), @sheet.strengthDie)"
});
```

### `sdk.rolls.intent({ actorId, actionId, inputs?, rollOptions?, target? })`

Requires `rolls.intent`.

Posts to `POST /game/actor/action`. Use it for declarative Sheet IR actions,
targets, damage application, initiative, or any action that should stay defined
in `rules/actions.gw.json`.

```js
await sdk.rolls.intent({
  actorId: ctx.actor.id,
  actionId: "attack.primary",
  inputs: { calledShot: false },
  rollOptions: { visibility: "public" },
  target: { actorId: targetActorId, tokenId: targetTokenId }
});
```

Both methods return the server response:

```json
{
  "actor_id": "actor-id",
  "type": "roll",
  "label": "Strength",
  "expression": "1d20 + @sheet.bonus",
  "groups": [],
  "modifier": 0,
  "total": 12,
  "visibility": "public",
  "metadata": { "rendered": {} },
  "applied": []
}
```

## HTML Sheets

Template-only HTML sheets can roll without a controller:

```html
<button
  type="button"
  data-roll="2d20kh1 + @sheet.attackBonus"
  data-roll-label="Attack">
  Attack
</button>
```

The package must declare `dice.roll`. The runtime reads the actor id from the
mounted sheet context and calls `sdk.dice.roll` through the same capability gate.

Use a controller when the formula is chosen dynamically:

```js
sdk.sheets.registerController("character", {
  async onAction(action, ctx) {
    if (action.name !== "roll-attribute") return;
    await sdk.dice.roll({
      actorId: ctx.actor.id,
      label: action.element.dataset.label,
      formula: action.element.dataset.formula
    });
  }
});
```

Prefer Sheet IR actions and `sdk.rolls.intent` when the roll also applies damage,
updates state, targets an actor/token, or participates in initiative.
