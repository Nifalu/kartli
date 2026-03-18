from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles


def test_osm_tile_url():
    t = OsmTiles()
    url = t.tile_url(15, 100, 200)
    assert url == "https://tile.openstreetmap.org/15/100/200.png"
    assert t.tile_size == 256
    assert t.max_zoom == 19


def test_swisstopo_tile_url():
    t = SwisstopoTiles()
    url = t.tile_url(15, 100, 200)
    assert "wmts.geo.admin.ch" in url
    assert "/3857/" in url
    assert "/15/100/200.jpeg" in url
    assert t.tile_size == 256
    assert t.max_zoom == 18


def test_swisstopo_custom_layer():
    t = SwisstopoTiles(layer="ch.swisstopo.swissimage")
    url = t.tile_url(10, 50, 50)
    assert "ch.swisstopo.swissimage" in url
