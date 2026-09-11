"""Core-owned closed geometry behavior; no package code runs in this path."""

from __future__ import annotations

from math import inf, isfinite


def channel_blocks(wall: dict, channel: str) -> bool:
    if channel not in {"movement", "vision", "light", "sound"}:
        raise ValueError("unsupported geometry channel")
    if wall.get("kind") == "door" and wall.get("door_state") == "open":
        return False
    return wall.get(f"{channel}_behavior", "block") == "block"


def segments_cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]) -> bool:
    def orientation(p, q, r):
        value = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        return 0 if abs(value) < 1e-9 else (1 if value > 0 else -1)
    return orientation(a, b, c) != orientation(a, b, d) and orientation(c, d, a) != orientation(c, d, b)


def vertical_bounds(wall: dict) -> tuple[float, float]:
    """Return the extruded wall interval; NULL legacy bounds are unbounded."""
    bottom = wall.get("vertical_bottom")
    top = wall.get("vertical_top")
    return (-inf if bottom is None else float(bottom), inf if top is None else float(top))


def height_blocked(wall: dict, elevation: float) -> bool:
    bottom, top = vertical_bounds(wall)
    return bottom <= elevation <= top


def _intersection_t(a, b, c, d) -> float | None:
    rx, ry = b[0]-a[0], b[1]-a[1]
    sx, sy = d[0]-c[0], d[1]-c[1]
    denominator = rx*sy-ry*sx
    if abs(denominator) < 1e-9: return None
    qx, qy = c[0]-a[0], c[1]-a[1]
    t=(qx*sy-qy*sx)/denominator; u=(qx*ry-qy*rx)/denominator
    return t if 0 <= t <= 1 and 0 <= u <= 1 else None


def ray_crosses_wall(*, wall: dict, channel: str, origin: tuple[float,float,float], target: tuple[float,float,float]) -> bool:
    if not channel_blocks(wall, channel): return False
    t=_intersection_t(origin, target, (float(wall["x1"]),float(wall["y1"])), (float(wall["x2"]),float(wall["y2"])))
    if t is None: return False
    z=origin[2]+(target[2]-origin[2])*t
    return height_blocked(wall,z)


def movement_crosses_wall(*, walls: list[dict], origin: tuple[float, float], target: tuple[float, float], elevation: float = 0.0) -> bool:
    if not isfinite(float(elevation)): raise ValueError("invalid elevation")
    return any(ray_crosses_wall(wall=wall,channel="movement",origin=(*origin,float(elevation)),target=(*target,float(elevation))) for wall in walls)


def line_of_sight_blocked(*, walls: list[dict], origin: tuple[float,float,float], target: tuple[float,float,float], channel: str = "vision") -> bool:
    if channel not in {"vision","light"} or not all(isfinite(float(value)) for value in (*origin,*target)): raise ValueError("invalid semantic ray")
    return any(ray_crosses_wall(wall=wall,channel=channel,origin=origin,target=target) for wall in walls)


def sound_attenuation(*, walls: list[dict], origin: tuple[float,float,float], target: tuple[float,float,float]) -> float:
    """Return only a safe acoustic scalar; callers never need hidden geometry."""
    if not all(isfinite(float(value)) for value in (*origin,*target)): raise ValueError("invalid acoustic ray")
    gain = 1.0
    for wall in walls:
        if wall.get("kind") == "door" and wall.get("door_state") == "open": continue
        t=_intersection_t(origin,target,(float(wall["x1"]),float(wall["y1"])),(float(wall["x2"]),float(wall["y2"])))
        if t is None: continue
        z=origin[2]+(target[2]-origin[2])*t
        if not height_blocked(wall,z): continue
        behavior=wall.get("sound_behavior","block")
        gain *= 1.0 if behavior=="pass" else 0.45 if behavior=="attenuate" else 0.0
        if gain <= 0.0025: return 0.0
    return max(0.0,min(1.0,gain))
