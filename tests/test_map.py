import pytest

from kartli.map import Map, _is_swiss
from kartli.models import Area, Coord, CoordinateError, Line, Marker
from kartli.rendering.overlays import (
    AreaOverlay,
    LineOverlay,
    MarkerOverlay,
    build_overlays,
)
from kartli.tiles.esri import EsriSatelliteTiles
from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles

# --- Swiss detection ---


def test_is_swiss_bern():
    assert _is_swiss(Coord(46.948, 7.447))


def test_is_swiss_zurich():
    assert _is_swiss(Coord(47.37, 8.54))


def test_is_not_swiss_berlin():
    assert not _is_swiss(Coord(52.52, 13.405))


def test_is_not_swiss_paris():
    assert not _is_swiss(Coord(48.85, 2.35))


# --- Tile source auto-detection ---


def test_auto_detect_swiss_coords():
    m = Map()
    m.add_marker(Marker(coord=(46.948, 7.447)))
    source = m._resolve_tile_source()
    assert isinstance(source, SwisstopoTiles)


def test_auto_detect_non_swiss_coords():
    m = Map()
    m.add_marker(Marker(coord=(52.52, 13.405)))
    source = m._resolve_tile_source()
    assert isinstance(source, OsmTiles)


def test_auto_detect_mixed_coords_uses_osm():
    m = Map()
    m.add_marker(Marker(coord=(46.948, 7.447)))
    m.add_marker(Marker(coord=(52.52, 13.405)))
    source = m._resolve_tile_source()
    assert isinstance(source, OsmTiles)


def test_explicit_tile_source_overrides_auto():
    m = Map(tile_source=OsmTiles())
    m.add_marker(Marker(coord=(46.948, 7.447)))  # Swiss coords
    source = m._resolve_tile_source()
    assert isinstance(source, OsmTiles)


def test_explicit_esri_source():
    m = Map(tile_source=EsriSatelliteTiles())
    source = m._resolve_tile_source()
    assert isinstance(source, EsriSatelliteTiles)


# --- Center and zoom ---


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


def test_set_zoom_separately():
    m = Map()
    m.set_center(46.948, 7.447)
    m.set_zoom(12)
    proj = OsmTiles().projection
    _, zoom = m._resolve_center_zoom(proj)
    assert zoom == 12


def test_auto_center_from_markers():
    m = Map()
    m.add_marker(Marker(coord=(46.0, 7.0)))
    m.add_marker(Marker(coord=(47.0, 8.0)))
    proj = OsmTiles().projection
    center, _ = m._resolve_center_zoom(proj)
    assert abs(center.lat - 46.5) < 0.01
    assert abs(center.lon - 7.5) < 0.01


def test_auto_zoom_from_markers():
    m = Map()
    m.add_marker(Marker(coord=(46.0, 7.0)))
    m.add_marker(Marker(coord=(47.0, 8.0)))
    proj = OsmTiles().projection
    _, zoom = m._resolve_center_zoom(proj)
    assert isinstance(zoom, int)
    assert zoom > 0


def test_set_scale():
    m = Map()
    m.set_center(46.948, 7.447)
    m.set_scale(25_000)
    proj = OsmTiles().projection
    _, zoom = m._resolve_center_zoom(proj)
    assert isinstance(zoom, int)
    assert zoom > 0


# --- Builder pattern ---


def test_fluent_chaining():
    m = (
        Map(width=400, height=300)
        .marker(46.948, 7.447, label="Bern")
        .area([(46.9, 7.4), (46.95, 7.4), (46.95, 7.45)])
        .line([(46.9, 7.4), (46.95, 7.45)])
        .set_center(46.948, 7.447, zoom=15)
    )
    assert isinstance(m, Map)
    assert len(m._objects.markers) == 1
    assert len(m._objects.areas) == 1
    assert len(m._objects.lines) == 1


def test_convenience_marker():
    m = Map()
    m.marker(46.948, 7.447, label="Test", color="blue", size=12)
    marker = m._objects.markers[0]
    assert marker.coord == Coord(46.948, 7.447)
    assert marker.label == "Test"
    assert marker.color == "blue"
    assert marker.size == 12


def test_convenience_area():
    m = Map()
    m.area([(46.9, 7.4), (46.95, 7.4), (46.95, 7.45)], label="Zone", color="green")
    area = m._objects.areas[0]
    assert area.label == "Zone"
    assert area.color == "green"
    assert len(area.coords) == 3


def test_convenience_line():
    m = Map()
    m.line(
        [(46.9, 7.4), (46.95, 7.45)],
        label="Route",
        label_position=0.3,
        color="green",
    )
    line = m._objects.lines[0]
    assert line.label == "Route"
    assert line.label_position == 0.3
    assert line.color == "green"


# --- Validation at render time ---


def test_invalid_coords_in_marker_raises():
    with pytest.raises(CoordinateError):
        Map().marker(999, 0)


def test_swisstopo_rejects_non_swiss_at_render():
    m = Map(tile_source=SwisstopoTiles())
    m.marker(48.85, 2.35, label="Paris")
    with pytest.raises(ValueError, match="Out of bounds"):
        m.render()


# --- Scalebar toggle ---


def test_scalebar_default_on():
    m = Map()
    assert m._show_scalebar is True


def test_scalebar_disabled():
    m = Map(show_scalebar=False)
    assert m._show_scalebar is False


# --- Label font size ---


def test_label_font_size_default():
    m = Map()
    assert m._label_font_size == 13


def test_label_font_size_custom():
    m = Map(label_font_size=20)
    assert m._label_font_size == 20


def test_build_overlays_propagates_font_size():
    marker = Marker(coord=(46.948, 7.447), label="m")
    area = Area(coords=[(46.9, 7.4), (46.95, 7.4), (46.95, 7.45)], label="a")
    line = Line(coords=[(46.9, 7.4), (46.95, 7.45)], label="l")

    overlays = build_overlays([marker], [area], [line], label_font_size=18)

    by_type = {type(o): o for o in overlays}
    assert by_type[MarkerOverlay].label_font_size == 18
    assert by_type[AreaOverlay].label_font_size == 18
    assert by_type[LineOverlay].label_font_size == 18


def test_build_overlays_default_font_size():
    marker = Marker(coord=(46.948, 7.447), label="m")
    overlays = build_overlays([marker], [], [])
    assert overlays[0].label_font_size == 13
