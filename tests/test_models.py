from kartli.models import Area, BBox, Coord, Line, MapObjects, Marker


def test_coord_from_tuple():
    m = Marker(coord=(46.9, 7.4), label="A")
    assert isinstance(m.coord, Coord)
    assert m.coord.lat == 46.9
    assert m.coord.lon == 7.4


def test_coord_iter():
    c = Coord(lat=1.0, lon=2.0)
    assert list(c) == [1.0, 2.0]


def test_area_normalizes_coords():
    a = Area(coords=[(1, 2), (3, 4), (5, 6)])
    assert all(isinstance(c, Coord) for c in a.coords)


def test_line_normalizes_coords():
    ln = Line(coords=[(1, 2), (3, 4)])
    assert all(isinstance(c, Coord) for c in ln.coords)


def test_area_default_stroke():
    a = Area(coords=[(1, 2), (3, 4), (5, 6)], fill_color="blue")
    assert a.stroke_color == "blue"


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
