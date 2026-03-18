import pytest

from kartli.models import Coord
from kartli.tiles.esri import EsriSatelliteTiles
from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles

# --- OSM ---


def test_osm_tile_url():
    t = OsmTiles()
    url = t.tile_url(15, 100, 200)
    assert url == "https://tile.openstreetmap.org/15/100/200.png"


def test_osm_properties():
    t = OsmTiles()
    assert t.tile_size == 256
    assert t.max_zoom == 19
    assert t.min_zoom == 0
    assert t.name == "OpenStreetMap"


def test_osm_no_bounds_validation():
    t = OsmTiles()
    # Should not raise for any valid coords
    t.validate_coords([Coord(0, 0), Coord(89, 179)])


# --- Swisstopo ---


def test_swisstopo_tile_url():
    t = SwisstopoTiles()
    url = t.tile_url(15, 100, 200)
    assert "wmts.geo.admin.ch" in url
    assert "/3857/" in url
    assert "/15/100/200.jpeg" in url


def test_swisstopo_properties():
    t = SwisstopoTiles()
    assert t.tile_size == 256
    assert t.max_zoom == 18
    assert t.name == "Swisstopo"


def test_swisstopo_custom_layer():
    t = SwisstopoTiles(layer="ch.swisstopo.swissimage")
    url = t.tile_url(10, 50, 50)
    assert "ch.swisstopo.swissimage" in url


def test_swisstopo_cache_prefix_unique_per_layer():
    t1 = SwisstopoTiles()
    t2 = SwisstopoTiles(layer="ch.swisstopo.swissimage")
    assert t1.cache_prefix != t2.cache_prefix


def test_swisstopo_validate_swiss_coords():
    t = SwisstopoTiles()
    # Should not raise
    t.validate_coords([Coord(46.948, 7.447), Coord(47.3, 8.5)])


def test_swisstopo_validate_rejects_paris():
    t = SwisstopoTiles()
    with pytest.raises(ValueError, match="Out of bounds"):
        t.validate_coords([Coord(48.85, 2.35)])


def test_swisstopo_validate_rejects_mixed():
    t = SwisstopoTiles()
    with pytest.raises(ValueError, match="Out of bounds"):
        # One Swiss, one not
        t.validate_coords([Coord(46.948, 7.447), Coord(52.52, 13.405)])


def test_swisstopo_validate_rejects_lat_out_of_range():
    t = SwisstopoTiles()
    with pytest.raises(ValueError, match="Out of bounds"):
        t.validate_coords([Coord(44.0, 7.5)])  # South of Switzerland


def test_swisstopo_validate_rejects_lon_out_of_range():
    t = SwisstopoTiles()
    with pytest.raises(ValueError, match="Out of bounds"):
        t.validate_coords([Coord(46.948, 12.0)])  # East of Switzerland


# --- ESRI ---


def test_esri_tile_url():
    t = EsriSatelliteTiles()
    url = t.tile_url(15, 100, 200)
    assert "arcgisonline.com" in url
    assert "/15/200/100" in url  # Note: ESRI uses z/y/x


def test_esri_properties():
    t = EsriSatelliteTiles()
    assert t.tile_size == 256
    assert t.max_zoom == 19
    assert t.name == "ESRI Satellite"
    assert t.cache_prefix == "esri_satellite"


def test_esri_no_bounds_validation():
    t = EsriSatelliteTiles()
    t.validate_coords([Coord(0, 0), Coord(-33, 151)])


# --- Common interface ---


def test_all_sources_have_headers():
    for source in [OsmTiles(), SwisstopoTiles(), EsriSatelliteTiles()]:
        headers = source.headers
        assert "User-Agent" in headers
        assert "kartli" in headers["User-Agent"]
