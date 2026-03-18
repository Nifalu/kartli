from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TileCache(ABC):
    """Abstract base for tile caching strategies."""

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        """Return cached tile bytes, or None if not cached."""
        ...

    @abstractmethod
    def put(self, key: str, data: bytes) -> None:
        """Store tile bytes under the given key."""
        ...

    @staticmethod
    def tile_key(prefix: str, z: int, x: int, y: int) -> str:
        return f"{prefix}/{z}/{x}/{y}"


class DiskCache(TileCache):
    """Simple file-system tile cache."""

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".cache" / "kartli"
        self._base_dir = base_dir

    def _path_for(self, key: str) -> Path:
        return self._base_dir / key

    def get(self, key: str) -> bytes | None:
        path = self._path_for(key)
        if path.is_file():
            return path.read_bytes()
        return None

    def put(self, key: str, data: bytes) -> None:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class NoCache(TileCache):
    """Cache that never stores anything — useful for testing."""

    def get(self, key: str) -> bytes | None:
        return None

    def put(self, key: str, data: bytes) -> None:
        pass
