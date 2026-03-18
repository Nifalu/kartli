from __future__ import annotations

from kartli.tiles.base import TileSource


class EsriSatelliteTiles(TileSource):
    """ESRI World Imagery satellite tile source."""

    @property
    def name(self) -> str:
        return "ESRI Satellite"

    @property
    def tile_size(self) -> int:
        return 256

    @property
    def max_zoom(self) -> int:
        return 19

    def tile_url(self, z: int, x: int, y: int) -> str:
        return (
            "https://server.arcgisonline.com/ArcGIS/rest/services"
            f"/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        )

    @property
    def cache_prefix(self) -> str:
        return "esri_satellite"
