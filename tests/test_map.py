import pytest

from kartli.map import Map, _is_swiss
from kartli.models import Coord, Marker
from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles


def test_is_swiss():
    assert _is_swiss(Coord(46.948, 7.447))
    assert not _is_swiss(Coord(52.52, 13.405))  # Berlin


def test_auto_detect_swiss():
    m = Map()
    m.add_marker(Marker(coord=(46.948, 7.447)))
    source = m._resolve_tile_source()
    assert isinstance(source, SwisstopoTiles)


def test_auto_detect_osm():
    m = Map()
    m.add_marker(Marker(coord=(52.52, 13.405)))
    source = m._resolve_tile_source()
    assert isinstance(source, OsmTiles)


def test_explicit_tile_source():
    m = Map(tile_source=OsmTiles())
    m.add_marker(Marker(coord=(46.948, 7.447)))
    source = m._resolve_tile_source()
    assert isinstance(source, OsmTiles)


def test_no_center_no_objects_raises():
    m = Map()
    with pytest.raises(ValueError, match="No center"):
        m.render()


def test_set_center_and_zoom():
    m = Map()
    m.set_center(46.948, 7.447, zoom=15)
    proj = OsmTiles().projection
    center, zoom = m._resolve_center_zoom(proj)
    assert center.lat == 46.948
    assert zoom == 15
