"""Derived wall-art mesh, mirrored by the builder's wall-joins.js."""

import math

from .services import MapError

EPSILON = 1e-7
BIN_SIZE = 8
MAX_WORK = 8_388_608


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _add(a, b, scale=1):
    return a[0] + b[0] * scale, a[1] + b[1] * scale


def _sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def _first(wall):
    return wall["x1"], wall["y1"]


def _last(wall):
    return wall["x2"], wall["y2"]


def _same(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= EPSILON


def _quant(value):
    return math.floor(value / EPSILON + .5)


def _frames(doc):
    result, groups = {}, {}
    for wall in doc["walls"]:
        a, b = _first(wall), _last(wall)
        size = math.hypot(b[0] - a[0], b[1] - a[1])
        if size <= EPSILON:
            continue
        authored = (b[0] - a[0]) / size, (b[1] - a[1]) / size
        result[wall["id"]] = {"origin": a, "direction": authored, "phase": 0, "polygons": []}
        sign = -1 if authored[0] < -EPSILON or abs(authored[0]) <= EPSILON and authored[1] < 0 else 1
        direction = authored[0] * sign, authored[1] * sign
        key = (wall.get("layerId"), wall.get("assetId"), wall["thickness"],
               _quant(direction[0]), _quant(direction[1]), _quant(_cross(direction, a)))
        groups.setdefault(key, []).append({"wall": wall, "a": a, "b": b, "direction": direction,
            "from": min(_dot(a, direction), _dot(b, direction)), "to": max(_dot(a, direction), _dot(b, direction))})
    for values in groups.values():
        values.sort(key=lambda value: (value["from"], value["to"]))
        component, end = [], -math.inf

        def flush():
            if len(component) < 2:
                return
            head = component[0]
            origin = head["a"] if _dot(head["a"], head["direction"]) <= _dot(head["b"], head["direction"]) else head["b"]
            for entry in component:
                result[entry["wall"]["id"]].update(origin=origin, direction=head["direction"])

        for entry in values:
            if entry["from"] > end + EPSILON:
                flush()
                component, end = [], -math.inf
            component.append(entry)
            end = max(end, entry["to"])
        flush()
    return result


def wall_join_geometry(doc, solid_spans):
    """Map source IDs to local artwork polygons; never change native segments."""
    result, spans, nodes, bins = _frames(doc), [], {}, {}
    work = 0

    def spend():
        nonlocal work
        work += 1
        if work > MAX_WORK:
            raise MapError("The map produces too many wall segments.")

    def blocked(wall, point):
        if not _same(point, _first(wall)) and not _same(point, _last(wall)):
            return True
        for door in doc.get("doors", []):
            spend()
            a, b = _first(door), _last(door)
            line = _sub(b, a)
            size = math.hypot(*line)
            if not size:
                continue
            source = _sub(_last(wall), _first(wall))
            source_size = math.hypot(*source)
            source_unit = source[0] / source_size, source[1] / source_size
            if (abs(_cross(_sub(a, _first(wall)), source_unit)) > EPSILON
                    or abs(_cross(_sub(b, _first(wall)), source_unit)) > EPSILON):
                continue
            unit, offset = (line[0] / size, line[1] / size), _sub(point, a)
            position = _dot(offset, unit)
            if abs(_cross(offset, unit)) <= EPSILON and -EPSILON <= position <= size + EPSILON:
                return True
        return False

    def node(point, wall):
        layer = wall.get("layerId")
        key = layer, _quant(point[0]), _quant(point[1])
        if key not in nodes:
            value = {"point": point, "rays": []}
            nodes[key] = value
            bin_key = layer, math.floor(point[0] / BIN_SIZE), math.floor(point[1] / BIN_SIZE)
            bins.setdefault(bin_key, []).append(value)
        return nodes[key]

    occupied = {}
    for span in solid_spans:
        spend()
        wall = span["wall"]
        if wall["id"] not in result:
            continue
        a, b = _first(span), _last(span)
        size = math.hypot(b[0] - a[0], b[1] - a[1])
        if size <= EPSILON:
            continue
        frame = result[wall["id"]]
        start, end = _dot(_sub(a, frame["origin"]), frame["direction"]), _dot(_sub(b, frame["origin"]), frame["direction"])
        low, high = min(start, end), max(start, end)
        key = (wall.get("layerId"), wall.get("assetId"), wall["thickness"], frame["origin"], frame["direction"])
        known, remaining, cursor = occupied.get(key, []), [], low
        for left, right in known:
            spend()
            if right <= cursor or left >= high:
                continue
            if left > cursor + EPSILON:
                remaining.append((cursor, min(left, high)))
            cursor = max(cursor, right)
        if cursor < high - EPSILON:
            remaining.append((cursor, high))
        merged = []
        for left, right in sorted([*known, (low, high)]):
            if merged and left <= merged[-1][1] + EPSILON:
                merged[-1] = merged[-1][0], max(merged[-1][1], right)
            else:
                merged.append((left, right))
        occupied[key] = merged
        hard_a, hard_b = blocked(wall, a), blocked(wall, b)

        def hard(point):
            return hard_a if _same(point, a) else hard_b if _same(point, b) else False

        for left, right in remaining:
            p = _add(frame["origin"], frame["direction"], left if start <= end else right)
            q = _add(frame["origin"], frame["direction"], right if start <= end else left)
            spans.append({"wall": wall, "a": p, "b": q, "size": right - left,
                "start": None if hard(p) else node(p, wall), "end": None if hard(q) else node(q, wall)})
    pieces = []
    for span in spans:
        a, b, size = span["a"], span["b"], span["size"]
        direction = (b[0] - a[0]) / size, (b[1] - a[1]) / size
        splits = [(0, a, span["start"]), (size, b, span["end"])]
        for y in range(math.floor(min(a[1], b[1]) / BIN_SIZE), math.floor(max(a[1], b[1]) / BIN_SIZE) + 1):
            for x in range(math.floor(min(a[0], b[0]) / BIN_SIZE), math.floor(max(a[0], b[0]) / BIN_SIZE) + 1):
                spend()
                for value in bins.get((span["wall"].get("layerId"), x, y), []):
                    spend()
                    offset = _sub(value["point"], a)
                    position = _dot(offset, direction)
                    if EPSILON < position < size - EPSILON and abs(_cross(offset, direction)) <= EPSILON:
                        splits.append((position, value["point"], value))
        splits.sort(key=lambda value: value[0])
        for left, right in zip(splits, splits[1:]):
            if right[0] - left[0] <= EPSILON:
                continue
            half = span["wall"]["thickness"] / 2
            normal = -direction[1] * half, direction[0] * half
            piece = {"wall": span["wall"], "al": _add(left[1], normal), "ar": _add(left[1], normal, -1),
                "bl": _add(right[1], normal), "br": _add(right[1], normal, -1)}
            pieces.append(piece)
            if left[2] is not None:
                left[2]["rays"].append({"piece": piece, "start": True, "direction": direction, "half": half})
            if right[2] is not None:
                right[2]["rays"].append({"piece": piece, "start": False, "direction": (-direction[0], -direction[1]), "half": half})
    polygons = {key: [] for key in result}

    def put(wall, points):
        area = sum(_cross(a, b) for a, b in zip(points, points[1:] + points[:1]))
        if abs(area) > EPSILON * EPSILON:
            polygons[wall["id"]].append(points if area > 0 else list(reversed(points)))

    def corner(ray, side, point):
        key = ("al" if side == "left" else "ar") if ray["start"] else ("br" if side == "left" else "bl")
        ray["piece"][key] = ray[side] = point

    for value in nodes.values():
        rays = sorted(value["rays"], key=lambda ray: math.atan2(ray["direction"][1], ray["direction"][0]))
        if len(rays) < 2:
            continue
        point = value["point"]
        for a, b in zip(rays, rays[1:] + rays[:1]):
            spend()
            da, db = a["direction"], b["direction"]
            pa, pb = _add(point, (-da[1], da[0]), a["half"]), _add(point, (db[1], -db[0]), b["half"])
            denominator, joint = _cross(da, db), None
            if abs(denominator) > EPSILON:
                candidate = _add(pa, da, _cross(_sub(pb, pa), db) / denominator)
                if math.hypot(*_sub(candidate, point)) <= 4 * max(a["half"], b["half"]):
                    joint = candidate
            elif _dot(da, db) < 0 and _same(pa, pb):
                joint = pa
            if joint is not None:
                corner(a, "left", joint)
                corner(b, "right", joint)
            else:
                corner(a, "left", pa)
                corner(b, "right", pb)
                low, high = 0, 1
                for ray in (a, b):
                    normal = -ray["direction"][1], ray["direction"][0]
                    start, delta = _dot(_sub(pa, point), normal), _dot(_sub(pb, pa), normal)
                    if abs(delta) <= EPSILON:
                        continue
                    one, two = (-ray["half"] - start) / delta, (ray["half"] - start) / delta
                    low, high = max(low, min(one, two)), min(high, max(one, two))
                middle = _add(pa, _sub(pb, pa), max(0, min(1, (low + high) / 2)))
                put(a["piece"]["wall"], [point, pa, middle])
                put(b["piece"]["wall"], [point, middle, pb])
        for ray in rays:
            put(ray["piece"]["wall"], [point, ray["left"], ray["right"]])
    for piece in pieces:
        put(piece["wall"], [piece["al"], piece["bl"], piece["br"], piece["ar"]])
    for key, values in polygons.items():
        frame = result[key]
        normal = -frame["direction"][1], frame["direction"][0]
        frame["polygons"] = [[(_dot(_sub(p, frame["origin"]), frame["direction"]),
                                _dot(_sub(p, frame["origin"]), normal)) for p in points] for points in values]
    return result
