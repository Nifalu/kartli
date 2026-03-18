
from kartli.models import BBox, Coord
from kartli.rendering.projection import (
    STANDARD_SCALES,
    WebMercatorProjection,
    auto_zoom,
    ground_resolution,
    map_scale,
    snap_to_standard_scale,
    zoom_for_scale,
)

# --- Coord <-> Pixel roundtrip ---


def test_roundtrip_bern():
    proj = WebMercatorProjection()
    original = Coord(lat=46.948, lon=7.447)
    px, py = proj.coord_to_pixel(original, zoom=15, tile_size=256)
    result = proj.pixel_to_coord(px, py, zoom=15, tile_size=256)
    assert abs(result.lat - original.lat) < 1e-6
    assert abs(result.lon - original.lon) < 1e-6


def test_roundtrip_equator():
    proj = WebMercatorProjection()
    original = Coord(lat=0, lon=0)
    px, py = proj.coord_to_pixel(original, zoom=10, tile_size=256)
    result = proj.pixel_to_coord(px, py, zoom=10, tile_size=256)
    assert abs(result.lat) < 1e-6
    assert abs(result.lon) < 1e-6


def test_roundtrip_negative_coords():
    proj = WebMercatorProjection()
    original = Coord(lat=-33.86, lon=-151.21)  # Sydney-ish (southern/western)
    px, py = proj.coord_to_pixel(original, zoom=12, tile_size=256)
    result = proj.pixel_to_coord(px, py, zoom=12, tile_size=256)
    assert abs(result.lat - original.lat) < 1e-6
    assert abs(result.lon - original.lon) < 1e-6


# --- Coord to tile ---


def test_coord_to_tile_returns_ints():
    proj = WebMercatorProjection()
    tx, ty = proj.coord_to_tile(Coord(lat=46.948, lon=7.447), zoom=15)
    assert isinstance(tx, int)
    assert isinstance(ty, int)


def test_coord_to_tile_within_bounds():
    proj = WebMercatorProjection()
    for z in [0, 5, 10, 18]:
        tx, ty = proj.coord_to_tile(Coord(lat=46.948, lon=7.447), zoom=z)
        assert 0 <= tx < 2**z
        assert 0 <= ty < 2**z


def test_coord_to_tile_zoom_zero():
    proj = WebMercatorProjection()
    tx, ty = proj.coord_to_tile(Coord(lat=46.948, lon=7.447), zoom=0)
    assert tx == 0
    assert ty == 0


def test_coord_to_tile_clamped():
    proj = WebMercatorProjection()
    # Edge of the world
    tx, ty = proj.coord_to_tile(Coord(lat=85, lon=179.99), zoom=5)
    assert tx < 2**5
    assert ty < 2**5


# --- Auto zoom ---


def test_auto_zoom_tight_bbox():
    bbox = BBox(min_lat=46.94, min_lon=7.44, max_lat=46.95, max_lon=7.45)
    zoom = auto_zoom(bbox, 800, 600)
    assert 13 <= zoom <= 17


def test_auto_zoom_wide_bbox():
    bbox = BBox(min_lat=45, min_lon=5, max_lat=48, max_lon=11)
    zoom = auto_zoom(bbox, 800, 600)
    assert 5 <= zoom <= 9


def test_auto_zoom_single_point():
    bbox = BBox(min_lat=46.948, min_lon=7.447, max_lat=46.948, max_lon=7.447)
    zoom = auto_zoom(bbox, 800, 600)
    # Single point — should zoom in to max
    assert zoom == 18


def test_auto_zoom_whole_world():
    bbox = BBox(min_lat=-60, min_lon=-170, max_lat=60, max_lon=170)
    zoom = auto_zoom(bbox, 800, 600)
    assert zoom <= 3


def test_auto_zoom_larger_canvas_allows_higher_zoom():
    bbox = BBox(min_lat=46.9, min_lon=7.4, max_lat=47.0, max_lon=7.5)
    z_small = auto_zoom(bbox, 400, 300)
    z_large = auto_zoom(bbox, 1600, 1200)
    assert z_large >= z_small


# --- Ground resolution / map scale ---


def test_ground_resolution_decreases_with_zoom():
    res_z10 = ground_resolution(46.948, zoom=10)
    res_z15 = ground_resolution(46.948, zoom=15)
    assert res_z10 > res_z15


def test_ground_resolution_higher_at_equator():
    # At the equator, each pixel covers more ground
    res_equator = ground_resolution(0, zoom=10)
    res_swiss = ground_resolution(46.948, zoom=10)
    assert res_equator > res_swiss


def test_map_scale_reasonable():
    # At zoom 15 in Switzerland, scale should be roughly 1:10k-1:50k
    s = map_scale(46.948, zoom=15)
    assert 5_000 < s < 100_000


def test_zoom_for_scale_25k():
    z = zoom_for_scale(25_000, lat=46.948)
    # Verify it produces something reasonable
    s = map_scale(46.948, z)
    # Should be within a factor of 2 of the requested scale
    assert 12_500 < s < 50_000


def test_zoom_for_scale_roundtrip():
    for target in [10_000, 25_000, 50_000, 100_000]:
        z = zoom_for_scale(target, lat=46.948)
        actual = map_scale(46.948, z)
        # Discrete zoom levels mean we can't be exact, but should be close
        ratio = actual / target
        assert 0.4 < ratio < 2.5


def test_snap_to_standard_scale():
    result = snap_to_standard_scale(46.948, zoom=15)
    assert result in STANDARD_SCALES
