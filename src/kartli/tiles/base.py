from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from kartli.rendering.projection import Projection, WebMercatorProjection

if TYPE_CHECKING:
    from kartli.models import Coord


class TileSource(ABC):
    """Abstract base class for map tile providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the tile source."""
        ...

    @property
    @abstractmethod
    def tile_size(self) -> int:
        """Size of each tile in pixels (typically 256)."""
        ...

    @property
    @abstractmethod
    def max_zoom(self) -> int:
        """Maximum zoom level supported."""
        ...

    @property
    def min_zoom(self) -> int:
        """Minimum zoom level supported."""
        return 0

    @property
    def projection(self) -> Projection:
        """Projection used by this tile source."""
        return WebMercatorProjection()

    @abstractmethod
    def tile_url(self, z: int, x: int, y: int) -> str:
        """Return the URL for the tile at the given z/x/y coordinates."""
        ...

    @property
    def headers(self) -> dict[str, str]:
        """HTTP headers to include with tile requests."""
        return {
            "User-Agent": "kartli/0.1 (Python; https://github.com/kartli)"
        }

    @property
    def cache_prefix(self) -> str:
        """Prefix for cache directory, defaults to source name."""
        return self.name.lower().replace(" ", "_")

    def validate_coords(self, coords: list[Coord]) -> None:  # noqa: B027
        """Check that coordinates are within this source's coverage.

        Override in subclasses with geographic bounds. Default: no-op.
        """
