import pytest

from kartli.models import Area, BBox, Coord, CoordinateError, Line, MapObjects, Marker

# --- Coord validation ---


def test_coord_valid():
    c = Coord(lat=46.948, lon=7.447)
    assert c.lat == 46.948
    assert c.lon == 7.447


def test_coord_boundary_values():
    assert Coord(lat=90, lon=180)
    assert Coord(lat=-90, lon=-180)
    assert Coord(lat=0, lon=0)


def test_coord_invalid_lat_too_high():
    with pytest.raises(CoordinateError, match="latitude"):
        Coord(lat=91, lon=0)


def test_coord_invalid_lat_too_low():
    with pytest.raises(CoordinateError, match="latitude"):
        Coord(lat=-91, lon=0)


def test_coord_invalid_lon_too_high():
    with pytest.raises(CoordinateError, match="longitude"):
        Coord(lat=0, lon=181)


def test_coord_invalid_lon_too_low():
    with pytest.raises(CoordinateError, match="longitude"):
        Coord(lat=0, lon=-181)


def test_coord_invalid_propagates_through_marker():
    with pytest.raises(CoordinateError):
        Marker(coord=(999, 0))


def test_coord_invalid_propagates_through_area():
    with pytest.raises(CoordinateError):
        Area(coords=[(0, 0), (999, 0), (0, 1)])


def test_coord_invalid_propagates_through_line():
    with pytest.raises(CoordinateError):
        Line(coords=[(0, 0), (0, 999)])


def test_coord_iter():
    c = Coord(lat=1.0, lon=2.0)
    assert list(c) == [1.0, 2.0]


def test_coord_frozen():
    c = Coord(lat=1.0, lon=2.0)
    with pytest.raises(AttributeError):
        c.lat = 5.0


# --- Marker ---


def test_marker_from_tuple():
    m = Marker(coord=(46.9, 7.4), label="A")
    assert isinstance(m.coord, Coord)
    assert m.coord.lat == 46.9
    assert m.coord.lon == 7.4


def test_marker_from_coord():
    c = Coord(lat=46.9, lon=7.4)
    m = Marker(coord=c, label="A")
    assert m.coord is c


def test_marker_defaults():
    m = Marker(coord=(0, 0))
    assert m.label == ""
    assert m.color == "red"
    assert m.size == 8


# --- Area ---


def test_area_normalizes_coords():
    a = Area(coords=[(1, 2), (3, 4), (5, 6)])
    assert all(isinstance(c, Coord) for c in a.coords)
    assert len(a.coords) == 3


def test_area_defaults():
    a = Area(coords=[(1, 2), (3, 4), (5, 6)])
    assert a.color == "red"
    assert a.opacity == 0.3
    assert a.stroke_width == 2
    assert a.label == ""


def test_area_custom_color():
    a = Area(coords=[(1, 2), (3, 4), (5, 6)], color="blue")
    assert a.color == "blue"


# --- Line ---


def test_line_normalizes_coords():
    ln = Line(coords=[(1, 2), (3, 4)])
    assert all(isinstance(c, Coord) for c in ln.coords)


def test_line_defaults():
    ln = Line(coords=[(1, 2), (3, 4)])
    assert ln.color == "blue"
    assert ln.width == 3
    assert ln.label == ""
    assert ln.label_position == 0.5


def test_line_label_position_clamped_high():
    ln = Line(coords=[(1, 2), (3, 4)], label_position=2.0)
    assert ln.label_position == 1.0


def test_line_label_position_clamped_low():
    ln = Line(coords=[(1, 2), (3, 4)], label_position=-1.0)
    assert ln.label_position == 0.0


# --- BBox ---


def test_bbox_from_coords():
    coords = [Coord(1, 10), Coord(3, 20), Coord(2, 15)]
    bbox = BBox.from_coords(coords)
    assert bbox.min_lat == 1
    assert bbox.max_lat == 3
    assert bbox.min_lon == 10
    assert bbox.max_lon == 20


def test_bbox_center():
    bbox = BBox(min_lat=0, min_lon=0, max_lat=10, max_lon=20)
    c = bbox.center
    assert c.lat == 5
    assert c.lon == 10


def test_bbox_single_point():
    coords = [Coord(5, 10)]
    bbox = BBox.from_coords(coords)
    assert bbox.min_lat == bbox.max_lat == 5
    assert bbox.min_lon == bbox.max_lon == 10
    assert bbox.center == Coord(5, 10)


# --- MapObjects ---


def test_map_objects_all_coords():
    objs = MapObjects()
    objs.markers.append(Marker(coord=(1, 2)))
    objs.areas.append(Area(coords=[(3, 4), (5, 6), (7, 8)]))
    objs.lines.append(Line(coords=[(9, 10), (11, 12)]))
    coords = objs.all_coords()
    assert len(coords) == 6


def test_map_objects_bbox_empty():
    objs = MapObjects()
    assert objs.bbox() is None


def test_map_objects_bbox_single_marker():
    objs = MapObjects()
    objs.markers.append(Marker(coord=(46.948, 7.447)))
    bbox = objs.bbox()
    assert bbox is not None
    assert bbox.min_lat == bbox.max_lat == 46.948
