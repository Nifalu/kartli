from kartli.models import Coord
from kartli.sharing import build_map_url

# --- Coord.from_lv95 ---


def test_coord_from_lv95():
    c = Coord.from_lv95(2600072.37, 1199544.65)
    assert 45.8 < c.lat < 47.9
    assert 5.9 < c.lon < 10.5


def test_coord_from_lv95_preserves_originals():
    c = Coord.from_lv95(2600072.37, 1199544.65)
    assert c.lv95_east == 2600072.37
    assert c.lv95_north == 1199544.65


def test_coord_from_lv95_equality_ignores_lv95_fields():
    c1 = Coord.from_lv95(2600072.37, 1199544.65)
    c2 = Coord(lat=c1.lat, lon=c1.lon)
    assert c1 == c2


def test_coord_default_lv95_fields_are_none():
    c = Coord(lat=46.9, lon=7.4)
    assert c.lv95_east is None
    assert c.lv95_north is None


# --- build_map_url uses stored LV95 directly ---


def test_build_map_url_uses_stored_lv95():
    """When a Coord has stored LV95 values, build_map_url should use them
    directly instead of converting from WGS84."""
    c = Coord.from_lv95(2600072.37, 1199544.65)
    url = build_map_url("test-id", c, zoom=10)
    assert "center=2600072.37,1199544.65" in url


def test_build_map_url_converts_when_no_lv95():
    """When a Coord has no stored LV95, build_map_url should convert."""
    c = Coord(lat=46.95, lon=7.44)
    url = build_map_url("test-id", c, zoom=10)
    assert "center=" in url
    # Should NOT contain the WGS84 values as-is
    assert "46.95" not in url
