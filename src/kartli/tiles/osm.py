from __future__ import annotations

from kartli.tiles.base import TileSource


class OsmTiles(TileSource):
    """OpenStreetMap tile source."""

    @property
    def name(self) -> str:
        return "OpenStreetMap"

    @property
    def tile_size(self) -> int:
        return 256

    @property
    def max_zoom(self) -> int:
        return 19

    def tile_url(self, z: int, x: int, y: int) -> str:
        return f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": "kartli/0.1 (Python; https://github.com/kartli)"
        }
