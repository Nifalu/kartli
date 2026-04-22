from __future__ import annotations

import math
from abc import ABC, abstractmethod

from kartli.models import Coord


class Projection(ABC):
    """Abstract base for map projections (coord <-> pixel math)."""

    @abstractmethod
    def coord_to_pixel(
        self, coord: Coord, zoom: int, tile_size: int
    ) -> tuple[float, float]:
        """Convert a geographic coordinate to absolute pixel position."""
        ...

    @abstractmethod
    def pixel_to_coord(
        self, px: float, py: float, zoom: int, tile_size: int
    ) -> Coord:
        """Convert absolute pixel position to geographic coordinate."""
        ...

    @abstractmethod
    def coord_to_tile(
        self, coord: Coord, zoom: int
    ) -> tuple[int, int]:
        """Convert a geographic coordinate to tile x, y indices."""
        ...


class WebMercatorProjection(Projection):
    """Web Mercator (EPSG:3857) projection used by OSM and most tile servers."""

    def coord_to_pixel(
        self, coord: Coord, zoom: int, tile_size: int
    ) -> tuple[float, float]:
        n = 2**zoom
        px = (coord.lon + 180.0) / 360.0 * n * tile_size
        lat_rad = math.radians(coord.lat)
        py = (
            (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
            / 2.0
            * n
            * tile_size
        )
        return px, py

    def pixel_to_coord(
        self, px: float, py: float, zoom: int, tile_size: int
    ) -> Coord:
        n = 2**zoom
        lon = px / (n * tile_size) * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * py / (n * tile_size))))
        lat = math.degrees(lat_rad)
        return Coord(lat=lat, lon=lon)

    def coord_to_tile(
        self, coord: Coord, zoom: int
    ) -> tuple[int, int]:
        n = 2**zoom
        x = int((coord.lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(coord.lat)
        y = int(
            (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
            / 2.0
            * n
        )
        x = max(0, min(x, n - 1))
        y = max(0, min(y, n - 1))
        return x, y


_EARTH_CIRCUMFERENCE_M = 40_075_016.686

# Standard map scale denominators used by Swisstopo and common cartography
STANDARD_SCALES = [
    5_000,
    10_000,
    25_000,
    50_000,
    100_000,
    200_000,
    500_000,
    1_000_000,
]


def ground_resolution(lat: float, zoom: int, tile_size: int = 256) -> float:
    """Meters per pixel at a given latitude and zoom level."""
    return (
        _EARTH_CIRCUMFERENCE_M * math.cos(math.radians(lat)) / (2**zoom * tile_size)
    )


def map_scale(lat: float, zoom: int, tile_size: int = 256, dpi: int = 96) -> float:
    """Approximate map scale denominator (e.g. 25000 for 1:25'000)."""
    meters_per_pixel = ground_resolution(lat, zoom, tile_size)
    meters_per_inch = 0.0254
    return meters_per_pixel * dpi / meters_per_inch


def zoom_for_scale(
    scale: int, lat: float, tile_size: int = 256, dpi: int = 96
) -> int:
    """Find the zoom level closest to the requested map scale denominator."""
    best_zoom = 1
    best_diff = float("inf")
    for z in range(0, 21):
        s = map_scale(lat, z, tile_size, dpi)
        diff = abs(s - scale)
        if diff < best_diff:
            best_diff = diff
            best_zoom = z
    return best_zoom


def snap_to_standard_scale(
    lat: float, zoom: int, tile_size: int = 256, dpi: int = 96
) -> int:
    """Return the standard scale denominator closest to the current zoom."""
    current = map_scale(lat, zoom, tile_size, dpi)
    best = STANDARD_SCALES[0]
    best_diff = abs(current - best)
    for s in STANDARD_SCALES[1:]:
        diff = abs(current - s)
        if diff < best_diff:
            best_diff = diff
            best = s
    return best


def _pixel_bounds(
    bbox: "BBox",  # noqa: UP037, F821
    label_extents: "list[AnchoredExtent] | None",  # noqa: UP037, F821
    zoom: int,
    tile_size: int,
    projection: Projection,
) -> tuple[float, float, float, float]:
    """Pixel bounding rectangle (min_x, max_x, min_y, max_y) covering the
    coord bbox plus each label extent at the given zoom."""
    tl = projection.coord_to_pixel(
        Coord(lat=bbox.max_lat, lon=bbox.min_lon), zoom, tile_size
    )
    br = projection.coord_to_pixel(
        Coord(lat=bbox.min_lat, lon=bbox.max_lon), zoom, tile_size
    )
    min_x, max_x = min(tl[0], br[0]), max(tl[0], br[0])
    min_y, max_y = min(tl[1], br[1]), max(tl[1], br[1])

    for ext in label_extents or []:
        px, py = projection.coord_to_pixel(ext.coord, zoom, tile_size)
        min_x = min(min_x, px + ext.dx_min)
        max_x = max(max_x, px + ext.dx_max)
        min_y = min(min_y, py + ext.dy_min)
        max_y = max(max_y, py + ext.dy_max)

    return min_x, max_x, min_y, max_y


def auto_zoom(
    bbox: "BBox",  # noqa: UP037, F821
    width: int,
    height: int,
    tile_size: int = 256,
    projection: Projection | None = None,
    label_extents: "list[AnchoredExtent] | None" = None,  # noqa: UP037, F821
) -> int:
    """Compute the best zoom to fit a bounding box in the given dimensions.

    When `label_extents` is provided, the chosen zoom also keeps each
    label's pixel footprint inside the canvas, so wider labels force a
    lower zoom instead of being clipped at the edges.
    """
    if projection is None:
        projection = WebMercatorProjection()

    for zoom in range(18, 0, -1):
        min_x, max_x, min_y, max_y = _pixel_bounds(
            bbox, label_extents, zoom, tile_size, projection
        )
        dx = max_x - min_x
        dy = max_y - min_y
        padding = 0.8
        if dx <= width * padding and dy <= height * padding:
            return zoom
    return 1


def auto_center(
    bbox: "BBox",  # noqa: UP037, F821
    zoom: int,
    tile_size: int = 256,
    projection: Projection | None = None,
    label_extents: "list[AnchoredExtent] | None" = None,  # noqa: UP037, F821
) -> Coord:
    """Center coord that balances the coord bbox and any label extents.

    Falls back to the coord bbox center when no label extents are given,
    so it matches the pre-label behavior."""
    if projection is None:
        projection = WebMercatorProjection()
    if not label_extents:
        return bbox.center

    min_x, max_x, min_y, max_y = _pixel_bounds(
        bbox, label_extents, zoom, tile_size, projection
    )
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    return projection.pixel_to_coord(cx, cy, zoom, tile_size)
