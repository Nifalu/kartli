from __future__ import annotations

from kartli.tiles.base import TileSource


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
