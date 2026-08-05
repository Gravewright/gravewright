"""Declarative formula DSL for the Gravewright SDK (§9.1) — no JS / no ``eval``.

Supports::

    paths   @core.name  @sheet.hp.value  @sheet.attributes.str.score
    vars    input.amount  helper args
    math    + - * /  (unary -)
    funcs   floor ceil round abs min max clamp  if(cond, a, b)
    compare == != < <= > >=   logic && ||
    dice    1d20, die(8), successes(5, 6, 6), under(2, 20, 10), fate(), draw(52)
    helpers abilityMod(@sheet.attributes.str.score)   (from formulas.gw.json)

Evaluation is a hand-written tokenizer + recursive-descent parser, so a system
author can never run arbitrary code. Dice are rolled as they are evaluated and
collected into ``groups`` matching the chat ROLL message format.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable

MAX_EXPRESSION_LEN = 200
MAX_DICE_COUNT = 100
MAX_DICE_SIDES = 1000
MAX_HELPER_DEPTH = 16

_TWO_CHAR_OPS = {"==", "!=", "<=", ">=", "&&", "||"}
_ONE_CHAR_OPS = {"+", "-", "*", "/", "<", ">", "(", ")", ","}


class FormulaError(Exception):
    pass


@dataclass
class _Tok:
    kind: str                                                                  
    value: object = None


@dataclass
class FormulaResult:
    total: float
    groups: list[dict] = field(default_factory=list)                                   

    @property
    def int_total(self) -> int:
        return int(self.total)

    @property
    def dice_subtotal(self) -> int:
        return sum(int(group["subtotal"]) for group in self.groups)

    @property
    def modifier(self) -> int:
        return self.int_total - self.dice_subtotal


def _tokenize(text: str) -> list[_Tok]:
    tokens: list[_Tok] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and text[i + 1].isdigit()):
            j = i
            is_int = True
            while j < n and text[j].isdigit():
                j += 1
            if j < n and text[j] == ".":
                is_int = False
                j += 1
                while j < n and text[j].isdigit():
                    j += 1
                                                                           
                                                                                     
            if is_int and j < n and text[j] == "d" and j + 1 < n and text[j + 1].isdigit():
                count = int(text[i:j])
                k = j + 1
                while k < n and text[k].isdigit():
                    k += 1
                sides = int(text[j + 1 : k])
                keep = ""
                if text.startswith("kh1", k) or text.startswith("kl1", k):
                    keep = text[k : k + 3]
                    k += 3
                tokens.append(_Tok("DICE", (count, sides, keep)))
                i = k
                continue
            tokens.append(_Tok("NUM", float(text[i:j])))
            i = j
            continue
        if ch == "@":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "_."):
                j += 1
            tokens.append(_Tok("PATH", text[i + 1 : j]))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_."):
                j += 1
            tokens.append(_Tok("IDENT", text[i:j]))
            i = j
            continue
        two = text[i : i + 2]
        if two in _TWO_CHAR_OPS:
            tokens.append(_Tok("OP", two))
            i += 2
            continue
        if ch in _ONE_CHAR_OPS:
            if ch == "(":
                tokens.append(_Tok("LPAREN"))
            elif ch == ")":
                tokens.append(_Tok("RPAREN"))
            elif ch == ",":
                tokens.append(_Tok("COMMA"))
            else:
                tokens.append(_Tok("OP", ch))
            i += 1
            continue
        raise FormulaError(f"unexpected character {ch!r}")
    tokens.append(_Tok("EOF"))
    return tokens


def _as_number(value: object) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _resolve_path(root: dict, dotted: str) -> object:
    cursor: object = root
    for segment in dotted.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


class _Evaluator:
    def __init__(
        self,
        tokens: list[_Tok],
        *,
        context: dict,
        scope: dict,
        helpers: dict,
        roller: Callable[[int, int], list[int]],
        groups: list[dict],
        depth: int,
    ) -> None:
        self.tokens = tokens
        self.pos = 0
        self.context = context
        self.scope = scope
        self.helpers = helpers
        self.roller = roller
        self.groups = groups
        self.depth = depth

    def _peek(self) -> _Tok:
        return self.tokens[self.pos]

    def _next(self) -> _Tok:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, kind: str) -> _Tok:
        tok = self._next()
        if tok.kind != kind:
            raise FormulaError(f"expected {kind}, got {tok.kind}")
        return tok

    def parse(self) -> float:
        value = self._or_expr()
        if self._peek().kind != "EOF":
            raise FormulaError("trailing tokens")
        return value

    def _or_expr(self) -> float:
        value = self._and_expr()
        while self._peek().kind == "OP" and self._peek().value == "||":
            self._next()
            rhs = self._and_expr()
            value = 1.0 if (value != 0 or rhs != 0) else 0.0
        return value

    def _and_expr(self) -> float:
        value = self._cmp_expr()
        while self._peek().kind == "OP" and self._peek().value == "&&":
            self._next()
            rhs = self._cmp_expr()
            value = 1.0 if (value != 0 and rhs != 0) else 0.0
        return value

    def _cmp_expr(self) -> float:
        value = self._add_expr()
        tok = self._peek()
        if tok.kind == "OP" and tok.value in {"==", "!=", "<", "<=", ">", ">="}:
            self._next()
            rhs = self._add_expr()
            op = tok.value
            result = {
                "==": value == rhs,
                "!=": value != rhs,
                "<": value < rhs,
                "<=": value <= rhs,
                ">": value > rhs,
                ">=": value >= rhs,
            }[op]
            return 1.0 if result else 0.0
        return value

    def _add_expr(self) -> float:
        value = self._mul_expr()
        while self._peek().kind == "OP" and self._peek().value in {"+", "-"}:
            op = self._next().value
            rhs = self._mul_expr()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _mul_expr(self) -> float:
        value = self._unary()
        while self._peek().kind == "OP" and self._peek().value in {"*", "/"}:
            op = self._next().value
            rhs = self._unary()
            if op == "*":
                value *= rhs
            else:
                if rhs == 0:
                    raise FormulaError("division by zero")
                value /= rhs
        return value

    def _unary(self) -> float:
        if self._peek().kind == "OP" and self._peek().value == "-":
            self._next()
            return -self._unary()
        return self._primary()

    def _primary(self) -> float:
        tok = self._next()
        if tok.kind == "NUM":
            return float(tok.value)
        if tok.kind == "DICE":
            keep = tok.value[2] if len(tok.value) > 2 else ""
            return self._roll(tok.value[0], tok.value[1], keep)
        if tok.kind == "PATH":
            return _as_number(_resolve_path(self.context, tok.value))
        if tok.kind == "LPAREN":
            value = self._or_expr()
            self._expect("RPAREN")
            return value
        if tok.kind == "IDENT":
            if self._peek().kind == "LPAREN":
                return self._call(tok.value)
            return _as_number(_resolve_path(self.scope, tok.value))
        raise FormulaError(f"unexpected token {tok.kind}")

    def _args(self) -> list[float]:
        self._expect("LPAREN")
        args: list[float] = []
        if self._peek().kind != "RPAREN":
            args.append(self._or_expr())
            while self._peek().kind == "COMMA":
                self._next()
                args.append(self._or_expr())
        self._expect("RPAREN")
        return args

    def _call(self, name: str) -> float:
        args = self._args()
        if name == "explode":
            return self._explode(args)
        if name == "die":
            return self._dynamic_dice(args)
        if name == "successes":
            return self._count_successes(args, under=False)
        if name == "under":
            return self._count_successes(args, under=True)
        if name == "fate":
            return self._fate(args)
        if name == "draw":
            return self._draw(args)
        builtin = _BUILTINS.get(name)
        if builtin is not None:
            return builtin(args)
        helper = self.helpers.get(name)
        if helper is not None:
            return self._call_helper(name, helper, args)
        raise FormulaError(f"unknown function {name!r}")

    def _roll_values(self, count: int, sides: int) -> list[int]:
        if count < 1 or count > MAX_DICE_COUNT or sides < 2 or sides > MAX_DICE_SIDES:
            raise FormulaError("dice out of bounds")
        results = [int(value) for value in self.roller(count, sides)]
        if len(results) != count or any(value < 1 or value > sides for value in results):
            raise FormulaError("roller returned an invalid result")
        return results

    def _dynamic_dice(self, args: list[float]) -> float:
        if len(args) not in {1, 2}:
            raise FormulaError("die expects sides or count and sides")
        count, sides = (1, int(args[0])) if len(args) == 1 else (int(args[0]), int(args[1]))
        results = self._roll_values(count, sides)
        subtotal = sum(results)
        self.groups.append(
            {"notation": f"{count}d{sides}", "results": results, "subtotal": subtotal}
        )
        return float(subtotal)

    def _count_successes(self, args: list[float], *, under: bool) -> float:
        if len(args) != 3:
            raise FormulaError("success count expects count, sides and target")
        count, sides, target = (int(value) for value in args)
        if target < 1 or target > sides:
            raise FormulaError("dice target out of bounds")
        results = self._roll_values(count, sides)
        hits = sum(value <= target if under else value >= target for value in results)
        operator = "<=" if under else ">="
        self.groups.append(
            {
                "notation": f"{count}d{sides}{operator}{target}",
                "results": results,
                "subtotal": hits,
            }
        )
        return float(hits)

    def _fate(self, args: list[float]) -> float:
        if args:
            raise FormulaError("fate expects no arguments")
        raw = self._roll_values(4, 3)
        results = [value - 2 for value in raw]
        subtotal = sum(results)
        self.groups.append({"notation": "4dF", "results": results, "subtotal": subtotal})
        return float(subtotal)

    def _draw(self, args: list[float]) -> float:
        if len(args) != 1:
            raise FormulaError("draw expects a deck size")
        cards = int(args[0])
        result = self._roll_values(1, cards)
        self.groups.append({"notation": f"draw({cards})", "results": result, "subtotal": result[0]})
        return float(result[0])

    def _explode(self, args: list[float]) -> float:
        if len(args) != 2:
            raise FormulaError("explode expects sides and threshold")
        sides, threshold = int(args[0]), int(args[1])
        if sides < 2 or sides > MAX_DICE_SIDES or threshold < 1 or threshold > sides:
            raise FormulaError("exploding dice out of bounds")
        results: list[int] = []
        while len(results) < MAX_DICE_COUNT:
            value = self._roll_values(1, sides)[0]
            results.append(value)
            if value < threshold:
                break
        subtotal = sum(results)
        self.groups.append(
            {
                "notation": f"1d{sides}!>={threshold}",
                "results": results,
                "subtotal": subtotal,
            }
        )
        return float(subtotal)

    def _call_helper(self, name: str, helper: dict, args: list[float]) -> float:
        if self.depth >= MAX_HELPER_DEPTH:
            raise FormulaError("helper recursion too deep")
        arg_names = helper.get("args") or []
        expression = helper.get("expression")
        if not isinstance(expression, str):
            raise FormulaError(f"helper {name!r} has no expression")
        helper_scope = {arg_names[i]: args[i] for i in range(min(len(arg_names), len(args)))}
        sub = _Evaluator(
            _tokenize(expression),
            context=self.context,
            scope=helper_scope,
            helpers=self.helpers,
            roller=self.roller,
            groups=self.groups,
            depth=self.depth + 1,
        )
        return sub.parse()

    def _roll(self, count: int, sides: int, keep: str = "") -> float:
        if count < 1 or count > MAX_DICE_COUNT or sides < 1 or sides > MAX_DICE_SIDES:
            raise FormulaError("dice out of bounds")
        if keep not in {"", "kh1", "kl1"}:
            raise FormulaError("unsupported dice keep notation")
        results = self._roll_values(count, sides)
        if keep == "kh1":
            subtotal = max(results) if results else 0
        elif keep == "kl1":
            subtotal = min(results) if results else 0
        else:
            subtotal = sum(results)
        self.groups.append(
            {"notation": f"{count}d{sides}{keep}", "results": list(results), "subtotal": subtotal}
        )
        return float(subtotal)


def _default_roller(count: int, sides: int) -> list[int]:
    return [random.randint(1, sides) for _ in range(count)]


_BUILTINS: dict[str, Callable[[list[float]], float]] = {
    "floor": lambda a: float(math.floor(a[0])),
    "ceil": lambda a: float(math.ceil(a[0])),
    "round": lambda a: float(round(a[0])),
    "abs": lambda a: float(abs(a[0])),
    "min": lambda a: float(min(a)) if a else 0.0,
    "max": lambda a: float(max(a)) if a else 0.0,
    "clamp": lambda a: float(min(max(a[0], a[1]), a[2])),
    "if": lambda a: a[1] if a[0] != 0 else a[2],
}


def evaluate(
    expression: str,
    *,
    context: dict | None = None,
    scope: dict | None = None,
    helpers: dict | None = None,
    roller: Callable[[int, int], list[int]] | None = None,
) -> FormulaResult:
    if not isinstance(expression, str):
        raise FormulaError("expression must be a string")
    if len(expression) > MAX_EXPRESSION_LEN:
        raise FormulaError("expression too long")
    groups: list[dict] = []
    evaluator = _Evaluator(
        _tokenize(expression),
        context=context or {},
        scope=scope or {},
        helpers=helpers or {},
        roller=roller or _default_roller,
        groups=groups,
        depth=0,
    )
    total = evaluator.parse()
    return FormulaResult(total=total, groups=groups)
