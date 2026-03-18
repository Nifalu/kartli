from __future__ import annotations

import io

import httpx
from PIL import Image

from kartli.cache import DiskCache, TileCache
from kartli.models import Coord
from kartli.rendering.projection import Projection
from kartli.tiles.base import TileSource


def fetch_tile(
    source: TileSource,
    z: int,
    x: int,
    y: int,
    cache: TileCache,
    client: httpx.Client,
) -> Image.Image:
    """Fetch a single tile, using cache if available."""
    key = TileCache.tile_key(source.cache_prefix, z, x, y)
    data = cache.get(key)
    if data is None:
        url = source.tile_url(z, x, y)
        resp = client.get(url, headers=source.headers)
        if resp.status_code != 200:
            msg = f"Failed to fetch tile: {url} (HTTP {resp.status_code})"
            raise RuntimeError(msg)
        data = resp.content
        cache.put(key, data)
    return Image.open(io.BytesIO(data)).convert("RGBA")


def stitch_tiles(
    source: TileSource,
    center: Coord,
    zoom: int,
    width: int,
    height: int,
    cache: TileCache | None = None,
    projection: Projection | None = None,
) -> tuple[Image.Image, float, float]:
    """Fetch and stitch tiles into a single image.

    Returns (image, origin_px_x, origin_px_y) where origin is the absolute
    pixel coordinate of the top-left corner of the returned image.
    """
    if cache is None:
        cache = DiskCache()
    if projection is None:
        projection = source.projection

    tile_size = source.tile_size
    center_px, center_py = projection.coord_to_pixel(center, zoom, tile_size)

    origin_x = center_px - width / 2
    origin_y = center_py - height / 2

    tile_x_min = int(origin_x // tile_size)
    tile_x_max = int((origin_x + width) // tile_size)
    tile_y_min = int(origin_y // tile_size)
    tile_y_max = int((origin_y + height) // tile_size)

    n = 2**zoom

    canvas = Image.new("RGBA", (width, height), (240, 240, 240, 255))

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for tx in range(tile_x_min, tile_x_max + 1):
            for ty in range(tile_y_min, tile_y_max + 1):
                if ty < 0 or ty >= n:
                    continue
                actual_tx = tx % n

                tile_img = fetch_tile(source, zoom, actual_tx, ty, cache, client)
                if tile_img.size != (tile_size, tile_size):
                    tile_img = tile_img.resize(
                        (tile_size, tile_size), Image.Resampling.LANCZOS
                    )

                paste_x = int(tx * tile_size - origin_x)
                paste_y = int(ty * tile_size - origin_y)

                canvas.paste(tile_img, (paste_x, paste_y), tile_img)

    return canvas, origin_x, origin_y
