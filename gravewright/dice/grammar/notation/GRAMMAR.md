# Gravewright dice notation — initial grammar

[English](GRAMMAR.md) · [Português](GRAMMAR.pt-BR.md)

The parser produces syntax only. It does not roll dice, evaluate an outcome,
access the SDK, or compile expressions into `RollDefinition` objects.

## Implemented subset

```ebnf
expression       = comparison ;
comparison       = additive, [ expression-comparison, additive ] ;
expression-comparison = "==" | "!=" | ">" | ">=" | "<" | "<=" ;
additive         = multiplicative, { ("+" | "-"), multiplicative } ;
multiplicative   = unary, { ("*" | "/"), unary } ;
unary            = ( "+" | "-" ), unary | primary ;
primary          = number | dice-expression | function-call |
                   "(", expression, ")" ;
function-call    = identifier, "(", [ expression, { ",", expression } ], ")" ;
identifier       = ( letter | "_" ), { letter | digit | "_" } ;
dice-expression  = [ positive-integer ], "d", ( positive-integer | "F" | "f" ),
                   { dice-modifier } ;
dice-modifier    = explode-modifier | reroll-modifier |
                   keep-modifier | drop-modifier ;
explode-modifier = "!", [ "o" ], [ explode-condition ] ;
reroll-modifier  = ( "r" | "rr" ), ( number | comparison-condition ) ;
keep-modifier    = ( "kh" | "kl" ), [ positive-integer ] ;
drop-modifier    = ( "dh" | "dl" ), [ positive-integer ] ;
comparison-condition = ( "=" | "!=" | ">" | ">=" | "<" | "<=" ), number ;
explode-condition = ( "=" | ">" | ">=" | "<" | "<=" ), number ;
number           = digit+, [ ".", digit+ ] | ".", digit+ ;
positive-integer = digit+ ;
```

Whitespace is ignored between tokens. The canonical and only accepted dice
marker is lowercase `d`. Dice counts and sides must be positive safe integers;
`d20` means `1d20`. Decimal ordinary numbers are accepted, but decimal dice
counts or sides are syntax errors. Modifiers must be lexically attached to the
dice term: `4d6kh3` is valid and `4d6 kh3` is invalid. Whitespace inside a
modifier is not accepted.

Modifier order is preserved exactly. Counts omitted from `kh`, `kl`, `dh`, or
`dl` default to one. `!` is recursive explode and defaults to equality with the
maximum face; `!o` explodes once. Both accept attached conditions. `r` rerolls
once and `rr` rerolls recursively; both require either an implicit equality
value (`r1`) or an explicit comparison (`r<=2`).

After a dice term, an attached `!` always begins an explode modifier. Therefore
`1d6!=5` means recursive explode when the face equals 5; it is not the 
not-equal comparison expression `1d6 != 5`. This lexical attachment rule avoids
contextual reinterpretation. A not-equal explode condition has no notation in
this grammar version; the runtime condition type remains capable of expressing it.

Whitespace is specifically significant at the explode/comparison boundary:

- `1d6!=5` is an attached explode modifier with equality condition 5;
- `1d6 != 5` is a pool comparison using expression inequality;
- `2d6!>=5` is conditional recursive explode, not success counting;
- `2d6! >= 5` is default recursive explode followed by pool success counting.

Expression equality uses `==`. A single `=` remains reserved for modifier
conditions. Comparisons are non-associative, so `1 < 2 < 3` is invalid.

## Precedence (highest to lowest)

1. Parenthesized expressions.
2. Dice terms and their postfix modifiers (`!`, `kh`, `kl`, `dh`, `dl`, `r`).
3. Unary `+` and `-`.
4. Multiplication and division, left-associative.
5. Addition and subtraction, left-associative.
6. Comparisons, non-associative.

All six levels are implemented. Function calls behave as primary expressions. A modifier condition such as the `>=5` in
`1d6!>=5` belongs to the explode modifier; a comparison in `8d10 >= 8` is a
separate comparison-expression node.

## Python validation and execution boundary

Python validates types and resource bounds on the notation tree before rolling.
The executor evaluates this tree depth-first and left-to-right. Compact dice
plans retain the original serialized structure, including initial `count` and
`sides` and ordered operations. A dice term's standard scalar value is the sum
of faces whose final selection state is `active`.

A comparison whose left AST node is directly a dice term compiles to numeric
pool success counting over active facts. Its threshold must be deterministic
numeric arithmetic without dice. Other comparisons compile to scalar boolean
comparisons. Parentheses are not preserved as AST nodes, so `(8d10) >= 8` has
the same pool semantics as `8d10 >= 8`.

## Standard numeric functions

The parser accepts call syntax without knowing the function table. The compiler
recognizes only lowercase `floor`, `ceil`, `round`, `abs`, `min`, `max`, and
`clamp`. Unary functions require one argument, `min` and `max` require two or
more, and `clamp` requires exactly three. All arguments and return values are
numeric. Arguments execute depth-first and left-to-right. Unknown or uppercase
names are compilation errors; there is no runtime-mutable function registry.

## VTT Fudge extension

`dF` (also `df`) uses a balanced six-face custom die: −1, −1, 0, 0, +1, +1. It supports the same modifiers; its maximum face for default explosion is +1.
