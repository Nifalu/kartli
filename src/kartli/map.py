from __future__ import annotations

from pathlib import Path

from PIL import Image

from kartli.cache import DiskCache, TileCache
from kartli.models import Area, Coord, Line, MapObjects, Marker
from kartli.rendering.layout import compute_label_extents
from kartli.rendering.overlays import ScaleBarOverlay, build_overlays
from kartli.rendering.placement import place_marker_labels
from kartli.rendering.projection import (
    Projection,
    auto_center,
    auto_zoom,
    zoom_for_scale,
)
from kartli.rendering.stitcher import stitch_tiles
from kartli.sharing import ShareResult, share
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
        label_font_size: int = 13,
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
        self._label_font_size = label_font_size

    # -- Object model methods (accept pre-built dataclasses) --

    def add_marker(self, marker: Marker) -> Map:
        """Add a pre-built Marker object."""
        self._objects.markers.append(marker)
        return self

    def add_area(self, area: Area) -> Map:
        """Add a pre-built Area object."""
        self._objects.areas.append(area)
        return self

    def add_line(self, line: Line) -> Map:
        """Add a pre-built Line object."""
        self._objects.lines.append(line)
        return self

    # -- Convenience constructors (build objects inline) --

    def marker(
        self,
        lat: float,
        lon: float,
        *,
        label: str = "",
        color: str = "red",
        size: int = 8,
    ) -> Map:
        """Add a marker at the given coordinates."""
        self._objects.markers.append(
            Marker(coord=(lat, lon), label=label, color=color, size=size)
        )
        return self

    def area(
        self,
        coords: list[tuple[float, float]],
        *,
        label: str = "",
        color: str = "red",
        opacity: float = 0.3,
        stroke_width: int = 2,
    ) -> Map:
        """Add a polygon area from a list of (lat, lon) tuples."""
        self._objects.areas.append(
            Area(
                coords=coords,
                label=label,
                color=color,
                opacity=opacity,
                stroke_width=stroke_width,
            )
        )
        return self

    def line(
        self,
        coords: list[tuple[float, float]],
        *,
        color: str = "blue",
        width: int = 3,
        label: str = "",
        label_position: float = 0.5,
    ) -> Map:
        """Add a line from a list of (lat, lon) tuples."""
        self._objects.lines.append(
            Line(
                coords=coords,
                color=color,
                width=width,
                label=label,
                label_position=label_position,
            )
        )
        return self

    # -- Configuration --

    def set_center(
        self,
        lat_or_coord: float | Coord,
        lon: float | None = None,
        zoom: int | None = None,
    ) -> Map:
        """Set the map center. Accepts (lat, lon) or a Coord object."""
        if isinstance(lat_or_coord, Coord):
            self._center = lat_or_coord
        else:
            if lon is None:
                msg = "lon is required when passing lat as a float"
                raise TypeError(msg)
            self._center = Coord(lat=lat_or_coord, lon=lon)
        if zoom is not None:
            self._zoom = zoom
        return self

    def set_zoom(self, zoom: int) -> Map:
        """Set the zoom level explicitly."""
        self._zoom = zoom
        return self

    def set_scale(self, scale: int) -> Map:
        """Set zoom via map scale denominator, e.g. 25000 for 1:25'000."""
        self._scale = scale
        return self

    def share_online(self) -> ShareResult:
        """Upload map objects as KML to swisstopo and return a shareable URL.

        Resolves center and zoom the same way render() does, then uploads
        all markers, areas, and lines as a KML drawing.

        Raises ValueError if any coordinates are outside Switzerland,
        since the swisstopo viewer only covers Swiss territory.
        """
        coords = self._objects.all_coords()
        non_swiss = [c for c in coords if not _is_swiss(c)]
        if non_swiss:
            msg = (
                "--share is only compatible with coordinates inside Switzerland. "
                f"Found {len(non_swiss)} coordinate(s) outside Swiss bounds "
                f"(lat {_SWISS_LAT[0]}-{_SWISS_LAT[1]}, "
                f"lon {_SWISS_LON[0]}-{_SWISS_LON[1]})."
            )
            raise ValueError(msg)

        source = self._resolve_tile_source()
        projection = source.projection
        center, zoom = self._resolve_center_zoom(projection)
        return share(self._objects, center, zoom)

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
        label_extents = (
            compute_label_extents(self._objects, self._label_font_size)
            if bbox is not None
            else []
        )

        if zoom is None and self._scale is not None:
            lat_anchor = center or (bbox.center if bbox else None)
            if lat_anchor is None:
                msg = "No center set and no objects to anchor scale from"
                raise ValueError(msg)
            zoom = zoom_for_scale(self._scale, lat_anchor.lat)

        if zoom is None:
            if bbox is not None:
                zoom = auto_zoom(
                    bbox,
                    self._width,
                    self._height,
                    projection=projection,
                    label_extents=label_extents,
                )
            else:
                zoom = 15

        if center is None:
            if bbox is not None:
                center = auto_center(
                    bbox,
                    zoom,
                    projection=projection,
                    label_extents=label_extents,
                )
            else:
                msg = "No center set and no objects to auto-compute center from"
                raise ValueError(msg)

        return center, zoom

    def render(self, output: str | Path | None = None) -> Image.Image:
        """Render the map and optionally save to a file. Returns the PIL Image."""
        source = self._resolve_tile_source()

        coords = self._objects.all_coords()
        if coords:
            source.validate_coords(coords)

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

        marker_placements = place_marker_labels(
            self._objects.markers,
            font_size=self._label_font_size,
            zoom=zoom,
            tile_size=tile_size,
            projection=projection,
        )

        overlays = build_overlays(
            self._objects.markers,
            self._objects.areas,
            self._objects.lines,
            label_font_size=self._label_font_size,
            marker_placements=marker_placements,
        )
        for overlay in overlays:
            overlay.draw(image, origin_x, origin_y, zoom, tile_size, projection)

        if self._show_scalebar:
            scale_bar = ScaleBarOverlay()
            scale_bar.draw(image, origin_x, origin_y, zoom, tile_size, projection)

        rgb_image = image.convert("RGB")

        if output is not None:
            out_path = Path(output)
            fmt = out_path.suffix.lower()
            if fmt == ".pdf":
                rgb_image.save(str(out_path), "PDF", resolution=150)
            else:
                rgb_image.save(str(out_path), "PNG")

        return rgb_image
