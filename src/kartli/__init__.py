"""kartli: Generate static map images with Swisstopo and OpenStreetMap tiles."""

from kartli.cache import DiskCache, NoCache, TileCache
from kartli.coordinates import lv95_to_wgs84, wgs84_to_lv95
from kartli.map import Map
from kartli.models import Area, Coord, CoordinateError, Line, Marker
from kartli.rendering.overlays import Overlay
from kartli.rendering.projection import Projection, WebMercatorProjection
from kartli.sharing import ShareResult, generate_qr, objects_to_kml
from kartli.tiles.base import TileSource
from kartli.tiles.esri import EsriSatelliteTiles
from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles

__all__ = [
    "Area",
    "Coord",
    "CoordinateError",
    "DiskCache",
    "EsriSatelliteTiles",
    "Line",
    "Map",
    "Marker",
    "NoCache",
    "OsmTiles",
    "Overlay",
    "Projection",
    "ShareResult",
    "SwisstopoTiles",
    "TileCache",
    "TileSource",
    "WebMercatorProjection",
    "generate_qr",
    "lv95_to_wgs84",
    "objects_to_kml",
    "wgs84_to_lv95",
]
