"""Bounded PDF field references interpreted by the existing native dice grammar."""

import math
import re
from decimal import Decimal
from uuid import UUID

from gravewright.dice.engine import RollError
from gravewright.dice.grammar.compiler import children, compile_expression
from gravewright.dice.grammar.parser import Parser
from gravewright.dice.grammar.runtime import Executor
from gravewright.maps.services import MapError

MAX_FORMULA_LENGTH = 512
NUMERIC = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")
VALUE = re.compile(r"@value(?![A-Za-z0-9_.])")


def source_identity(value):
    if isinstance(value, str):
        if value.startswith("asset:"):
            try:
                return "asset:" + str(UUID(value[6:]))
            except ValueError:
                pass
        elif re.fullmatch(r"template:[A-Za-z0-9_-]{1,120}", value):
            return value
    raise MapError("Invalid PDF field source.")


def formula_parts(formula, *, allow_value=True):
    """Split references without treating field names as paths or executable text."""
    if not isinstance(formula, str) or not formula.strip() or len(formula) > MAX_FORMULA_LENGTH:
        raise MapError("Use a PDF field formula with 1 to 512 characters.")
    parts = []
    offset = 0
    while offset < len(formula):
        start = formula.find("@", offset)
        if start < 0:
            parts.append(formula[offset:])
            break
        parts.append(formula[offset:start])
        value = VALUE.match(formula, start)
        if value:
            if not allow_value:
                raise MapError("Calculated fields must reference other fields instead of @value.")
            parts.append((None,))
            offset = value.end()
            continue
        if not formula.startswith("@{", start):
            raise MapError("Use @value or @{field} to reference PDF fields.")
        offset = start + 2
        name = []
        while offset < len(formula) and formula[offset] != "}":
            char = formula[offset]
            if char == "\\":
                offset += 1
                if offset >= len(formula) or formula[offset] not in ("\\", "}"):
                    raise MapError("Invalid PDF field reference.")
                char = formula[offset]
            name.append(char)
            offset += 1
        if offset >= len(formula):
            raise MapError("Invalid PDF field reference.")
        field = "".join(name)
        if not field.strip() or "\x00" in field or len(field) > 512:
            raise MapError("Invalid PDF field reference.")
        parts.append((field,))
        offset += 1
    return parts


def field_references(formula, *, allow_value=True):
    return list(dict.fromkeys(part[0] for part in formula_parts(formula, allow_value=allow_value)
                              if isinstance(part, tuple) and part[0] is not None))


def numeric_value(value):
    """Match browser numeric coercion without accepting notation or executable input."""
    if value is None or value == "":
        return 0
    if type(value) is bool:
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        if not NUMERIC.fullmatch(text):
            raise MapError("This field needs a numeric value.")
        value = float(text)
    if type(value) not in (int, float) or abs(value) > 1_000_000 or not math.isfinite(value):
        raise MapError("This field needs a numeric value.")
    return value


def number_text(value):
    value = numeric_value(value)
    if value == 0:
        return "0"
    text = format(Decimal(str(value)), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def expand_formula(formula, resolve, *, value=None, allow_value=True, max_length=512):
    pieces = []
    for part in formula_parts(formula, allow_value=allow_value):
        if isinstance(part, str):
            pieces.append(part)
        else:
            pieces.append("(" + number_text(value if part[0] is None else resolve(part[0])) + ")")
    expression = "".join(pieces).strip()
    if len(expression) > max_length:
        raise MapError("The resolved roll formula is too long.")
    return expression


def compile_formula(formula, *, dice=True, allow_value=True):
    """Validate native syntax and complexity without evaluating or consuming RNG."""
    expression = expand_formula(formula, lambda name: 1, value=1, allow_value=allow_value)
    try:
        plan = compile_expression(Parser(expression).parse())
    except RollError:
        raise MapError("Invalid PDF field formula.") from None
    if not dice:
        stack = [plan]
        while stack:
            node = stack.pop()
            if node["kind"] == "dice":
                raise MapError("Calculated fields cannot roll dice.")
            stack.extend(children(node))
    return plan


def calculate_formula(formula, resolve):
    """Evaluate a deterministic expression with the native numeric semantics."""
    compile_formula(formula, dice=False, allow_value=False)
    # A tiny decimal may expand to 326 characters. The authored formula remains
    # bounded; native compilation independently bounds nodes and nesting.
    expression = expand_formula(formula, resolve, allow_value=False, max_length=65536)
    try:
        plan = compile_expression(Parser(expression).parse())
        result = Executor().execute(plan)["value"]["value"]
        return numeric_value(result)
    except (RollError, ArithmeticError):
        raise MapError("Could not calculate this PDF field. Check its formula and numeric values.") from None
