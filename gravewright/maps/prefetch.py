"""Bounded speculation ordered by spatial benefit and real encoded tile cost."""

import math

from .models import Tile

MAX_BYTES = 64 * 1024 * 1024


def candidates(scene_id, region, utility, policy):
    cx = (region["firstColumn"] + region["lastColumn"]) / 2
    cy = (region["firstRow"] + region["lastRow"]) / 2
    tiles = Tile.objects.filter(
        scene_id=scene_id,
        lod=region["lod"],
        x__gte=region["firstColumn"],
        x__lte=region["lastColumn"],
        y__gte=region["firstRow"],
        y__lte=region["lastRow"],
    ).only("pk", "x", "y", "byte_size", "file")
    values = []
    for tile in tiles.iterator(chunk_size=256):
        size = tile.byte_size
        if not size:
            try:
                size = tile.file.size
            except FileNotFoundError:
                continue
            Tile.objects.filter(pk=tile.pk, byte_size=0).update(byte_size=size)
        distance = math.hypot(tile.x - cx, tile.y - cy)
        value = {
            "x": tile.x,
            "y": tile.y,
            "byte_size": size,
            "distance": distance,
            "priority_per_byte": utility / (1 + distance) / max(1, size),
        }
        values.append(value)
        # The active viewport is bounded, but converting coarse hints can span a
        # long thin image. Retain bounded top candidates while scanning metadata.
        if len(values) > 256:
            values.sort(
                key=lambda r: (
                    -r["priority_per_byte"]
                    if policy == "utility_per_byte"
                    else r["distance"]
                )
            )
            del values[128:]
    values.sort(
        key=lambda r: (
            -r["priority_per_byte"] if policy == "utility_per_byte" else r["distance"],
            r["y"],
            r["x"],
        )
    )
    result = []
    used = 0
    for row in values:
        if used + row["byte_size"] > MAX_BYTES:
            continue
        result.append(row)
        used += row["byte_size"]
        if len(result) == 128:
            break
    return result
