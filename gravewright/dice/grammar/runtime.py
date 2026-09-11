"""Bounded execution with immutable historical facts and ordered modifiers."""

import math
import operator
import secrets
from collections import deque

from .errors import RollError

COMPARE = {
    "=": operator.eq,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}
ARITHMETIC = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}
FUDGE = (-1, -1, 0, 0, 1, 1)


def secure_sample():
    return secrets.randbelow(2**53) / 2**53


def finite(value):
    if not math.isfinite(value):
        raise RollError("Standard dice expression produced a non-finite value")
    return value


class Executor:
    def __init__(self, random_source=None):
        self.random = random_source if random_source is not None else secure_sample
        self.next_id = 1
        self.facts_used = 0
        self.rolls = []
        self.traces = []

    def execute(self, node):
        value = self.expression(node)
        return {
            "schema": "gravewright-dice-result",
            "version": 1,
            "value": {
                "kind": "boolean" if type(value) is bool else "number",
                "value": value,
            },
            "rolls": self.rolls,
            "traces": self.traces,
        }

    def expression(self, node):
        kind = node["kind"]
        if kind == "number":
            return node["value"]
        if kind == "dice":
            roll = self.dice(node)
            return finite(
                sum(
                    f["face"]
                    for f in roll["facts"]
                    if roll["selection"][f["id"]] == "active"
                )
            )
        if kind == "unary":
            value = self.expression(node["operand"])
            return finite(-value if node["operator"] == "-" else value)
        if kind == "binary":
            left = self.expression(node["left"])
            right = self.expression(node["right"])
            if node["operator"] == "/" and right == 0:
                raise RollError("Division by zero in standard dice expression")
            return finite(ARITHMETIC[node["operator"]](left, right))
        if kind == "call":
            values = [self.expression(child) for child in node["arguments"]]
            name = node["name"]
            if name == "clamp":
                if values[1] > values[2]:
                    raise RollError("Clamp minimum cannot be greater than maximum")
                result = min(max(values[0], values[1]), values[2])
            elif name in ("min", "max"):
                result = (min if name == "min" else max)(values)
            elif name == "round":
                # JavaScript Math.round ties toward +infinity, unlike Python round.
                value = values[0]
                lower = math.floor(value)
                result = lower + (value - lower >= 0.5)
            else:
                result = {"floor": math.floor, "ceil": math.ceil, "abs": abs}[name](
                    values[0]
                )
            return finite(float(result))
        if kind == "comparison":
            compare = COMPARE[node["operator"]]
            if node["left"]["kind"] == "dice":
                roll = self.dice(node["left"])
                threshold = self.expression(node["right"])
                matched, unmatched = [], []
                for fact in roll["facts"]:
                    if roll["selection"][fact["id"]] == "active":
                        (
                            matched if compare(fact["face"], threshold) else unmatched
                        ).append(fact["id"])
                self.traces.append(
                    {
                        "kind": "pool-comparison",
                        "operator": node["operator"],
                        "threshold": threshold,
                        "matched": matched,
                        "unmatched": unmatched,
                    }
                )
                return len(matched)
            left = self.expression(node["left"])
            right = self.expression(node["right"])
            result = compare(left, right)
            self.traces.append(
                {
                    "kind": "scalar-comparison",
                    "operator": node["operator"],
                    "left": left,
                    "right": right,
                    "result": result,
                }
            )
            return result
        raise RollError("Unknown expression node")

    def fact(self, node, die_index, cause):
        if self.facts_used >= 512:
            raise RollError("Expression exceeds the limit of 512 dice facts")
        sample = self.random()
        if (
            type(sample) not in (int, float)
            or not math.isfinite(sample)
            or not 0 <= sample < 1
        ):
            raise RollError("Random source must return a finite value in [0, 1)")
        sides = 6 if node["fudge"] else node["sides"]
        face_index = math.floor(sample * sides)
        fact = {
            "id": f"roll-{self.next_id}",
            "dieId": f"dF-{die_index + 1}"
            if node["fudge"]
            else f"notation-{die_index + 1}",
            "dieIndex": die_index,
            "faceIndex": face_index,
            "face": FUDGE[face_index] if node["fudge"] else face_index + 1,
            "cause": cause,
            "entropy": {"kind": "normalized-sample", "value": sample},
        }
        self.next_id += 1
        self.facts_used += 1
        return fact

    def dice(self, node):
        if self.facts_used + node["count"] > 512:
            raise RollError("Expression exceeds the limit of 512 dice facts")
        facts = [self.fact(node, i, {"kind": "initial"}) for i in range(node["count"])]
        selection = {f["id"]: "active" for f in facts}
        generated = 0
        for operation in node["modifiers"]:
            active = [f for f in facts if selection[f["id"]] == "active"]
            if operation["category"] == "selection":
                # Stable ties follow the generation order, also for highest first.
                ranked = sorted(
                    active,
                    key=lambda f: (
                        f["face"] if operation["direction"] == "lowest" else -f["face"]
                    ),
                )
                affected = (
                    ranked[operation["count"] :]
                    if operation["kind"] == "keep"
                    else ranked[: operation["count"]]
                )
                selection.update((f["id"], "discarded") for f in affected)
                continue
            condition = operation["condition"]
            matches = lambda face, condition=condition: COMPARE[condition["operator"]](
                face, condition["value"]
            )
            queue = deque(f for f in active if matches(f["face"]))
            while queue:
                parent = queue.popleft()
                if generated >= 256:
                    raise RollError(
                        "Dice term exceeds the limit of 256 generated results"
                    )
                fact = self.fact(
                    node,
                    parent["dieIndex"],
                    {"kind": operation["kind"], "parentId": parent["id"]},
                )
                generated += 1
                facts.append(fact)
                selection[fact["id"]] = "active"
                if operation["kind"] == "reroll":
                    selection[parent["id"]] = "replaced"
                if operation["mode"] == "recursive" and matches(fact["face"]):
                    queue.append(fact)
        initial = {
            "kind": "standard-pool",
            "count": node["count"],
            "sides": node["sides"],
        }
        if node["fudge"]:
            initial = {
                "kind": "definition",
                "definition": {
                    "dice": [
                        {
                            "id": f"dF-{i + 1}",
                            "faces": [{"value": face, "weight": 1} for face in FUDGE],
                        }
                        for i in range(node["count"])
                    ]
                },
            }
        roll = {
            "sourceSpan": node["span"],
            "plan": {"initial": initial, "operations": node["modifiers"]},
            "facts": facts,
            "selection": selection,
        }
        self.rolls.append(roll)
        return roll
