"""Bounded, deterministic terrain dab masks shared with terrain-brush.js."""

from collections import OrderedDict
import math

from PIL import Image

from .services import MapError

MAX_DABS = 2048
MAX_DOCUMENT_DABS = 8192
MAX_DAB_PIXELS = 67_108_864
MAX_RADIUS = 10000


def clean_floor_brush(raw):
    if (not isinstance(raw, dict) or set(raw) != {"operation", "points", "radius", "hardness"}
            or raw["operation"] not in ("paint", "erase")):
        raise MapError("Invalid floor brush.")

    def number(value, minimum, maximum, positive=False):
        if (type(value) not in (int, float) or not minimum <= value <= maximum
                or positive and value == 0 or not math.isfinite(value)):
            raise MapError("Invalid floor brush.")
        return value

    if not isinstance(raw["points"], list) or not raw["points"]:
        raise MapError("Invalid floor brush.")
    if len(raw["points"]) > MAX_DABS:
        raise MapError("The map has too many terrain brush dabs.")
    if not isinstance(raw["radius"], list) or len(raw["radius"]) != 2:
        raise MapError("Invalid floor brush.")
    points = []
    for point in raw["points"]:
        if not isinstance(point, list) or len(point) != 3:
            raise MapError("Invalid floor brush.")
        points.append([number(value, 0, 1) for value in point])
    return {"operation": raw["operation"], "points": points,
            "radius": [number(value, 0, MAX_RADIUS, positive=True) for value in raw["radius"]],
            "hardness": number(raw["hardness"], 0, 1)}


def terrain_brush_cost(row, cell):
    """Mirror clipped integer pixel boxes, before any mask allocation."""
    left, top = math.floor(row["x"] * cell), math.floor(row["y"] * cell)
    right, bottom = math.ceil((row["x"] + row["width"]) * cell), math.ceil((row["y"] + row["height"]) * cell)
    rx, ry = row["brush"]["radius"][0] * row["width"] * cell, row["brush"]["radius"][1] * row["height"] * cell
    pixels = 0
    for u, v, alpha in row["brush"]["points"]:
        if not alpha:
            continue
        cx, cy = (row["x"] + u * row["width"]) * cell, (row["y"] + v * row["height"]) * cell
        pixels += max(0, min(right, math.ceil(cx + rx)) - max(left, math.floor(cx - rx))) * max(
            0, min(bottom, math.ceil(cy + ry)) - max(top, math.floor(cy - ry)))
        if pixels > MAX_DAB_PIXELS:
            break
    return len(row["brush"]["points"]), pixels


def terrain_brush_mask(row, cell, left, top, size):
    """Compose quantized source-over dabs at pixel centers, independent of FPS."""
    brush = row["brush"]
    if len(brush["points"]) > MAX_DABS or terrain_brush_cost(row, cell)[1] > MAX_DAB_PIXELS:
        raise MapError("The map terrain brushes are too complex.")
    width, height = size
    output = bytearray(width * height)
    rx, ry = brush["radius"][0] * row["width"] * cell, brush["radius"][1] * row["height"] * cell
    if rx == 0 or ry == 0:
        return Image.new("L", size)
    hardness = brush["hardness"]
    # Spatially resampled dabs often share a subpixel center. Keep only small
    # kernels, with a hard 1 MiB cache rather than one bitmap per saved point.
    cache, cached_bytes = OrderedDict(), 0
    for u, v, intensity in brush["points"]:
        if intensity == 0:
            continue
        cx, cy = (row["x"] + u * row["width"]) * cell - left, (row["y"] + v * row["height"]) * cell - top
        x0, y0 = max(0, math.floor(cx - rx)), max(0, math.floor(cy - ry))
        x1, y1 = min(width, math.ceil(cx + rx)), min(height, math.ceil(cy + ry))
        if x1 <= x0 or y1 <= y0:
            continue
        w, h = x1 - x0, y1 - y0
        key = (w, h, cx - x0, cy - y0, intensity)
        kernel = cache.get(key)
        if kernel is None:
            kernel = bytearray(w * h)
            normalized_x = [(x + x0 + .5 - cx) / rx for x in range(w)]
            squared_x = [value * value for value in normalized_x]
            for y in range(h):
                normalized_y = (y + y0 + .5 - cy) / ry
                squared_y = normalized_y * normalized_y
                offset = y * w
                for x, squared in enumerate(squared_x):
                    distance = math.sqrt(squared + squared_y)
                    if distance >= 1:
                        continue
                    falloff = 1 if distance <= hardness else (1 - distance) / (1 - hardness)
                    kernel[offset + x] = min(255, math.floor(255 * intensity * falloff + .5))
            if len(kernel) <= 1_048_576:
                while cache and (len(cache) >= 8 or cached_bytes + len(kernel) > 1_048_576):
                    _, removed = cache.popitem(last=False)
                    cached_bytes -= len(removed)
                cache[key] = kernel
                cached_bytes += len(kernel)
        else:
            cache.move_to_end(key)
        for y in range(h):
            source, target = y * w, (y + y0) * width + x0
            for x in range(w):
                alpha = kernel[source + x]
                if alpha:
                    previous = output[target + x]
                    output[target + x] = (alpha * 255 + previous * (255 - alpha) + 127) // 255
    return Image.frombytes("L", size, bytes(output))
