from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


FOG_SUBCELLS_PER_TILE = 4


class FogMode(StrEnum):
    REVEAL = "reveal"
    HIDE = "hide"


class FogShape(StrEnum):
    CIRCLE = "circle"
    SQUARE = "square"
    POLYGON = "polygon"


class FogInitialState(StrEnum):
    HIDE_ALL = "hide_all"
    REVEAL_ALL = "reveal_all"


@dataclass(frozen=True)
class FogCircleGeom:
    center_x_cells: float
    center_y_cells: float
    radius_cells: float


@dataclass(frozen=True)
class FogSquareGeom:
    center_x_cells: float
    center_y_cells: float
    size_cells: float


@dataclass(frozen=True)
class FogPolygonGeom:
    points_cells: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class FogOp:
    mode: FogMode
    shape: FogShape
    geom: FogCircleGeom | FogSquareGeom | FogPolygonGeom
