"""Recursive descent parser preserving the original lexical attachment rules."""

import math
import re

from .errors import RollError

NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
COMPARISONS = (">=", "<=", "==", "!=", ">", "<")
SAFE_INTEGER = 2**53 - 1


class Parser:
    def __init__(self, source):
        self.source = source
        self.position = 0
        self.nesting = 0

    def error(self, message):
        raise RollError(f"{message} at position {self.position}")

    def peek(self):
        return self.source[self.position : self.position + 1]

    def whitespace(self):
        while self.peek() and (self.peek().isspace() or self.peek() == "\ufeff"):
            self.position += 1

    def consume(self, value):
        if self.source.startswith(value, self.position):
            self.position += len(value)
            return True
        return False

    def operator(self, choices, whitespace=False):
        if whitespace:
            self.whitespace()
        for candidate in choices:
            if self.consume(candidate):
                return candidate
        return None

    def node(self, kind, start, **values):
        return {"kind": kind, "span": {"start": start, "end": self.position}, **values}

    def nested(self, parse):
        if self.nesting >= 32:
            self.error("Maximum syntactic nesting exceeded")
        self.nesting += 1
        try:
            return parse()
        finally:
            self.nesting -= 1

    def parse(self):
        self.whitespace()
        if not self.peek():
            self.error("Expression cannot be empty")
        result = self.comparison()
        self.whitespace()
        if self.peek():
            self.error("Unexpected token")
        return result

    def comparison(self):
        left = self.additive()
        operator = self.operator(COMPARISONS, True)
        if operator is None:
            return left
        right = self.additive()
        if any(self.source.startswith(op, self.position) for op in COMPARISONS):
            self.error("Chained comparisons are not supported")
        return {
            "kind": "comparison",
            "operator": operator,
            "left": left,
            "right": right,
            "span": {"start": left["span"]["start"], "end": right["span"]["end"]},
        }

    def binary(self, operand, operators):
        left = operand()
        while (operator := self.operator(operators, True)) is not None:
            right = operand()
            left = {
                "kind": "binary",
                "operator": operator,
                "left": left,
                "right": right,
                "span": {"start": left["span"]["start"], "end": right["span"]["end"]},
            }
        return left

    def additive(self):
        return self.binary(self.multiplicative, ("+", "-"))

    def multiplicative(self):
        return self.binary(self.unary, ("*", "/"))

    def unary(self):
        self.whitespace()
        start = self.position
        if self.peek() in ("+", "-"):
            operator = self.peek()
            self.position += 1
            return self.node(
                "unary", start, operator=operator, operand=self.nested(self.unary)
            )
        return self.primary()

    def primary(self):
        self.whitespace()
        start = self.position
        if self.consume("("):
            result = self.nested(self.comparison)
            self.whitespace()
            if not self.consume(")"):
                self.error("Unclosed parenthesized expression")
            return {**result, "span": {"start": start, "end": self.position}}
        next_character = self.source[self.position + 1 : self.position + 2]
        if self.peek() == "d" and next_character and next_character in "0123456789Ff":
            self.position += 1
            return self.die(1, start)
        if IDENTIFIER.match(self.source, self.position):
            return self.call()
        value, integer = self.number()
        self.whitespace()
        if self.consume("d"):
            if not integer:
                self.error("Dice count must be an integer")
            return self.die(value, start)
        return self.node("number", start, value=value)

    def call(self):
        start = self.position
        name = IDENTIFIER.match(self.source, self.position)[0]
        self.position += len(name)
        self.whitespace()
        if not self.consume("("):
            self.error("Function name must be followed by '('")
        arguments = []
        self.whitespace()
        if not self.consume(")"):
            while True:
                arguments.append(self.nested(self.comparison))
                self.whitespace()
                if self.consume(")"):
                    break
                if not self.consume(","):
                    self.error("Expected ',' or ')' after function argument")
                self.whitespace()
                if self.peek() == ")":
                    self.error("Trailing comma is not supported")
        return self.node("call", start, name=name, arguments=arguments)

    def number(self, immediate=False):
        if not immediate:
            self.whitespace()
        match = NUMBER.match(self.source, self.position)
        if match is None:
            if immediate:
                return None
            self.error("Expected a number or die expression")
        value = float(match[0])
        if not math.isfinite(value):
            self.error("Number literal must be finite")
        self.position = match.end()
        return value, "." not in match[0]

    def positive_integer(self, value):
        if not value.is_integer() or not 0 < value <= SAFE_INTEGER:
            self.error("Expected a positive safe integer")
        return int(value)

    def die(self, count, start):
        count = self.positive_integer(float(count))
        self.whitespace()
        fudge = self.peek() in ("F", "f")
        if fudge:
            self.position += 1
            sides = 3
        else:
            value, integer = self.number()
            if not integer:
                self.error("Dice sides must be a positive safe integer")
            sides = self.positive_integer(value)
        modifiers = []
        while True:
            if self.consume("!"):
                mode = "once" if self.consume("o") else "recursive"
                condition = self.condition(False)
                modifiers.append(
                    {
                        "category": "generation",
                        "kind": "explode",
                        "mode": mode,
                        "condition": condition
                        or {"operator": "=", "value": 1 if fudge else sides},
                    }
                )
            elif (pair := self.operator(("kh", "kl", "dh", "dl"))) is not None:
                match = re.match(r"[0-9]+", self.source[self.position :])
                amount = 1
                if match:
                    self.position += len(match[0])
                    amount = self.positive_integer(float(match[0]))
                if self.peek() in (".", "-"):
                    self.error("Selection count must be a positive integer")
                modifiers.append(
                    {
                        "category": "selection",
                        "kind": "keep" if pair[0] == "k" else "drop",
                        "direction": "highest" if pair[1] == "h" else "lowest",
                        "count": amount,
                    }
                )
            elif self.consume("r"):
                mode = "recursive" if self.consume("r") else "once"
                condition = self.condition(True, True)
                if condition is None:
                    self.error("Reroll modifier requires a condition")
                modifiers.append(
                    {
                        "category": "generation",
                        "kind": "reroll",
                        "mode": mode,
                        "condition": condition,
                    }
                )
            else:
                break
        return self.node(
            "dice", start, count=count, sides=sides, fudge=fudge, modifiers=modifiers
        )

    def condition(self, allow_not_equal, implicit=False):
        choices = (
            (">=", "<=", "!=", "=", ">", "<")
            if allow_not_equal
            else (">=", "<=", "=", ">", "<")
        )
        operator = self.operator(choices)
        if operator is None and not implicit:
            return None
        number = self.number(immediate=True)
        if number is None:
            if operator:
                self.error("Comparison condition requires a value")
            return None
        return {"operator": operator or "=", "value": number[0]}
