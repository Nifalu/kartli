from __future__ import annotations

from pathlib import Path

from PIL import Image

from kartli.cache import DiskCache, TileCache
from kartli.models import Area, Coord, Line, MapObjects, Marker
from kartli.rendering.overlays import ScaleBarOverlay, build_overlays
from kartli.rendering.projection import (
    Projection,
    auto_zoom,
    zoom_for_scale,
)
from kartli.rendering.stitcher import stitch_tiles
from kartli.tiles.base import TileSource
from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles

_SWISS_LAT = (45.8, 47.9)
_SWISS_LON = (5.9, 10.5)


def _is_swiss(coord: Coord) -> bool:
    in_lat = _SWISS_LAT[0] <= coord.lat <= _SWISS_LAT[1]
    in_lon = _SWISS_LON[0] <= coord.lon <= _SWISS_LON[1]
    return in_lat and in_lon


class Map:
    def __init__(
        self,
        tile_source: TileSource | None = None,
        width: int = 800,
        height: int = 600,
        cache: TileCache | None = None,
        show_scalebar: bool = True,
    ):
        self._tile_source = tile_source
        self._width = width
        self._height = height
        self._cache = cache or DiskCache()
        self._objects = MapObjects()
        self._center: Coord | None = None
        self._zoom: int | None = None
        self._scale: int | None = None
        self._show_scalebar = show_scalebar

    def add_marker(self, marker: Marker) -> None:
        self._objects.markers.append(marker)

    def add_area(self, area: Area) -> None:
        self._objects.areas.append(area)

    def add_line(self, line: Line) -> None:
        self._objects.lines.append(line)

    def set_center(self, lat: float, lon: float, zoom: int | None = None) -> None:
        self._center = Coord(lat=lat, lon=lon)
        if zoom is not None:
            self._zoom = zoom

    def set_zoom(self, zoom: int) -> None:
        self._zoom = zoom

    def set_scale(self, scale: int) -> None:
        """Set zoom via map scale denominator, e.g. 25000 for 1:25'000."""
        self._scale = scale

    def _resolve_tile_source(self) -> TileSource:
        if self._tile_source is not None:
            return self._tile_source
        coords = self._objects.all_coords()
        if coords and all(_is_swiss(c) for c in coords):
            return SwisstopoTiles()
        return OsmTiles()

    def _resolve_center_zoom(
        self, projection: Projection
    ) -> tuple[Coord, int]:
        center = self._center
        zoom = self._zoom

        bbox = self._objects.bbox()
        if center is None:
            if bbox is not None:
                center = bbox.center
            else:
                msg = "No center set and no objects to auto-compute center from"
                raise ValueError(msg)

        if zoom is None and self._scale is not None:
            zoom = zoom_for_scale(self._scale, center.lat)

        if zoom is None:
            if bbox is not None:
                zoom = auto_zoom(bbox, self._width, self._height)
            else:
                zoom = 15

        return center, zoom

    def render(self, output: str | Path | None = None) -> Image.Image:
        """Render the map and optionally save to a file. Returns the PIL Image."""
        source = self._resolve_tile_source()
        projection = source.projection
        center, zoom = self._resolve_center_zoom(projection)
        tile_size = source.tile_size

        zoom = max(source.min_zoom, min(zoom, source.max_zoom))

        image, origin_x, origin_y = stitch_tiles(
            source=source,
            center=center,
            zoom=zoom,
            width=self._width,
            height=self._height,
            cache=self._cache,
            projection=projection,
        )

        overlays = build_overlays(
            self._objects.markers,
            self._objects.areas,
            self._objects.lines,
        )
        for overlay in overlays:
            overlay.draw(image, origin_x, origin_y, zoom, tile_size, projection)

        if self._show_scalebar:
            scale_bar = ScaleBarOverlay()
            scale_bar.draw(image, origin_x, origin_y, zoom, tile_size, projection)

        rgb_image = image.convert("RGB")

        if output is not None:
            rgb_image.save(str(output), "PNG")

        return rgb_image
