"""Validate types and complexity before consuming any randomness."""

from .errors import RollError

FUNCTIONS = {
    "floor": (1, 1),
    "ceil": (1, 1),
    "round": (1, 1),
    "abs": (1, 1),
    "min": (2, 100),
    "max": (2, 100),
    "clamp": (3, 3),
}


def children(node):
    if node["kind"] == "unary":
        return [node["operand"]]
    if node["kind"] in ("binary", "comparison"):
        return [node["left"], node["right"]]
    return node.get("arguments", [])


def compile_expression(root):
    stack = [(root, 1)]
    nodes = initial = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > 1000 or depth > 128 or len(node.get("arguments", [])) > 100:
            raise RollError("Expression compilation limit exceeded")
        if node["kind"] == "dice":
            initial += node["count"]
            if node["count"] > 99 or node["sides"] > 1000 or initial > 256:
                raise RollError(
                    "Limit: 99 dice per term, 1,000 faces, and 256 dice per expression."
                )
        stack.extend((child, depth + 1) for child in children(node))

    def check(node):
        kind = node["kind"]
        parts = [check(child) for child in children(node)]
        if any(value_kind != "number" for value_kind, _ in parts):
            raise RollError("This operation requires a numeric expression")
        terms = sum(count for _, count in parts)
        if kind == "dice":
            terms = 1
        if kind == "call":
            limits = FUNCTIONS.get(node["name"])
            if limits is None:
                raise RollError("Unknown standard function: " + node["name"])
            if not limits[0] <= len(parts) <= limits[1]:
                raise RollError("Invalid argument count for " + node["name"])
        if kind == "comparison":
            if node["left"]["kind"] == "dice":
                if parts[1][1]:
                    raise RollError("Pool comparison threshold cannot contain dice")
            else:
                return "boolean", terms
        return "number", terms

    _, terms = check(root)
    if terms > 32:
        raise RollError("Expression exceeds the limit of 32 dice terms")
    return root
