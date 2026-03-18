from __future__ import annotations

from typing import TYPE_CHECKING

from kartli.tiles.base import TileSource

if TYPE_CHECKING:
    from kartli.models import Coord

_SWISS_LAT = (45.8, 47.9)
_SWISS_LON = (5.9, 10.5)


class SwisstopoTiles(TileSource):
    """Swisstopo WMTS tile source (Web Mercator / EPSG:3857)."""

    def __init__(
        self,
        layer: str = "ch.swisstopo.pixelkarte-farbe",
    ):
        self._layer = layer

    @property
    def name(self) -> str:
        return "Swisstopo"

    @property
    def tile_size(self) -> int:
        return 256

    @property
    def max_zoom(self) -> int:
        return 18

    def tile_url(self, z: int, x: int, y: int) -> str:
        return (
            f"https://wmts.geo.admin.ch/1.0.0/{self._layer}"
            f"/default/current/3857/{z}/{x}/{y}.jpeg"
        )

    @property
    def cache_prefix(self) -> str:
        return f"swisstopo_{self._layer.replace('.', '_')}"

    def validate_coords(self, coords: list[Coord]) -> None:
        out_of_bounds = []
        for c in coords:
            if not (_SWISS_LAT[0] <= c.lat <= _SWISS_LAT[1]):
                out_of_bounds.append(c)
            elif not (_SWISS_LON[0] <= c.lon <= _SWISS_LON[1]):
                out_of_bounds.append(c)
        if out_of_bounds:
            pts = ", ".join(f"({c.lat}, {c.lon})" for c in out_of_bounds)
            msg = (
                f"Swisstopo tiles only cover Switzerland "
                f"(lat {_SWISS_LAT[0]}-{_SWISS_LAT[1]}, "
                f"lon {_SWISS_LON[0]}-{_SWISS_LON[1]}). "
                f"Out of bounds: {pts}"
            )
            raise ValueError(msg)
