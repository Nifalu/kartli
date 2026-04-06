"""Coordinate transformations between WGS84 and Swiss LV95 (EPSG:2056)."""

from __future__ import annotations

from pyproj import Transformer

_LV95_TO_WGS84 = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
_WGS84_TO_LV95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)


def lv95_to_wgs84(east: float, north: float) -> tuple[float, float]:
    """Convert Swiss LV95 (E, N) to WGS84 (lat, lon).

    Returns (lat, lon) in degrees.
    """
    lon, lat = _LV95_TO_WGS84.transform(east, north)
    return lat, lon


def wgs84_to_lv95(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 (lat, lon) to Swiss LV95 (E, N).

    Returns (easting, northing).
    """
    east, north = _WGS84_TO_LV95.transform(lon, lat)
    return east, north
