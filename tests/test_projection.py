from kartli.models import BBox, Coord
from kartli.rendering.projection import WebMercatorProjection, auto_zoom


def test_roundtrip():
    proj = WebMercatorProjection()
    original = Coord(lat=46.948, lon=7.447)
    zoom = 15
    tile_size = 256
    px, py = proj.coord_to_pixel(original, zoom, tile_size)
    result = proj.pixel_to_coord(px, py, zoom, tile_size)
    assert abs(result.lat - original.lat) < 1e-6
    assert abs(result.lon - original.lon) < 1e-6


def test_coord_to_tile():
    proj = WebMercatorProjection()
    coord = Coord(lat=46.948, lon=7.447)
    tx, ty = proj.coord_to_tile(coord, 15)
    assert isinstance(tx, int)
    assert isinstance(ty, int)
    assert 0 <= tx < 2**15
    assert 0 <= ty < 2**15


def test_auto_zoom_tight_bbox():
    bbox = BBox(min_lat=46.94, min_lon=7.44, max_lat=46.95, max_lon=7.45)
    zoom = auto_zoom(bbox, 800, 600)
    assert 13 <= zoom <= 17


def test_auto_zoom_wide_bbox():
    bbox = BBox(min_lat=45, min_lon=5, max_lat=48, max_lon=11)
    zoom = auto_zoom(bbox, 800, 600)
    assert 5 <= zoom <= 9
