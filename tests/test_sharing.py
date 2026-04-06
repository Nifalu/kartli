import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from kartli.models import Area, Coord, Line, MapObjects, Marker
from kartli.sharing import (
    ShareResult,
    _color_to_kml,
    build_map_url,
    objects_to_kml,
    share,
)

_KML_NS = "http://www.opengis.net/kml/2.2"


# --- _color_to_kml ---


def test_color_red():
    assert _color_to_kml("red") == "ff0000ff"


def test_color_blue():
    assert _color_to_kml("blue") == "ffff0000"


def test_color_with_opacity():
    result = _color_to_kml("red", opacity=0.5)
    assert result.startswith("7f")  # ~127 in hex


def test_color_hex():
    assert _color_to_kml("#ff0000") == "ff0000ff"


def test_color_hex_no_hash():
    assert _color_to_kml("00ff00") == "ff00ff00"


# --- objects_to_kml ---


def test_kml_empty_objects():
    kml = objects_to_kml(MapObjects())
    assert '<?xml version="1.0"' in kml
    root = ET.fromstring(kml)
    doc = root.find(f"{{{_KML_NS}}}Document")
    assert doc is not None
    placemarks = doc.findall(f"{{{_KML_NS}}}Placemark")
    assert len(placemarks) == 0


def test_kml_marker():
    objects = MapObjects(
        markers=[Marker(coord=(46.9472, 7.4443), label="Bern")]
    )
    kml = objects_to_kml(objects)
    root = ET.fromstring(kml)
    doc = root.find(f"{{{_KML_NS}}}Document")
    pm = doc.find(f"{{{_KML_NS}}}Placemark")
    assert pm is not None
    name = pm.find(f"{{{_KML_NS}}}name")
    assert name.text == "Bern"
    point = pm.find(f"{{{_KML_NS}}}Point")
    coords = point.find(f"{{{_KML_NS}}}coordinates")
    assert "7.4443,46.9472,0" in coords.text


def test_kml_area_closes_ring():
    objects = MapObjects(
        areas=[
            Area(coords=[(46.0, 7.0), (46.1, 7.1), (46.0, 7.1)])
        ]
    )
    kml = objects_to_kml(objects)
    root = ET.fromstring(kml)
    doc = root.find(f"{{{_KML_NS}}}Document")
    pm = doc.find(f"{{{_KML_NS}}}Placemark")
    polygon = pm.find(f".//{{{_KML_NS}}}LinearRing/{{{_KML_NS}}}coordinates")
    coord_lines = polygon.text.strip().split("\n")
    # Should close ring: first coord repeated at end
    assert coord_lines[0] == coord_lines[-1]


def test_kml_line():
    objects = MapObjects(
        lines=[
            Line(coords=[(46.0, 7.0), (46.1, 7.1)], label="Route")
        ]
    )
    kml = objects_to_kml(objects)
    root = ET.fromstring(kml)
    doc = root.find(f"{{{_KML_NS}}}Document")
    pm = doc.find(f"{{{_KML_NS}}}Placemark")
    name = pm.find(f"{{{_KML_NS}}}name")
    assert name.text == "Route"
    ls = pm.find(f"{{{_KML_NS}}}LineString")
    assert ls is not None


def test_kml_all_object_types():
    objects = MapObjects(
        markers=[Marker(coord=(46.9, 7.4))],
        areas=[Area(coords=[(46.0, 7.0), (46.1, 7.1), (46.0, 7.1)])],
        lines=[Line(coords=[(46.0, 7.0), (46.1, 7.1)])],
    )
    kml = objects_to_kml(objects)
    root = ET.fromstring(kml)
    doc = root.find(f"{{{_KML_NS}}}Document")
    placemarks = doc.findall(f"{{{_KML_NS}}}Placemark")
    assert len(placemarks) == 3


def test_kml_marker_no_label():
    objects = MapObjects(markers=[Marker(coord=(46.9, 7.4))])
    kml = objects_to_kml(objects)
    root = ET.fromstring(kml)
    doc = root.find(f"{{{_KML_NS}}}Document")
    pm = doc.find(f"{{{_KML_NS}}}Placemark")
    name = pm.find(f"{{{_KML_NS}}}name")
    assert name is None


# --- build_map_url ---


def test_build_map_url():
    url = build_map_url("abc123", Coord(lat=46.9472, lon=7.4443), zoom=13)
    assert "map.geo.admin.ch" in url
    assert "layers=KML|" in url
    assert "abc123" in url
    assert "center=" in url
    assert "z=13" in url


# --- share (mocked) ---


def test_share_calls_upload_and_returns_result():
    mock_response = {
        "id": "test-kml-id",
        "admin_id": "test-admin-id",
        "links": {"kml": "https://public.geo.admin.ch/api/kml/files/test-kml-id"},
    }
    objects = MapObjects(markers=[Marker(coord=(46.9, 7.4), label="Test")])

    with patch("kartli.sharing.upload_kml", return_value=mock_response) as mock_upload:
        result = share(objects, Coord(lat=46.9, lon=7.4), zoom=13)

    mock_upload.assert_called_once()
    assert isinstance(result, ShareResult)
    assert result.kml_id == "test-kml-id"
    assert result.admin_id == "test-admin-id"
    assert "map.geo.admin.ch" in result.url
    assert "test-kml-id" in result.url


# --- CLI --share flag ---


def test_parser_share_flag():
    from kartli.cli import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["render", "--share", "--center", "46.948,7.447"])
    assert args.share is True


def test_share_rejects_non_swiss_coords():
    from kartli.map import Map
    m = Map()
    m.marker(52.52, 13.405, label="Berlin")  # outside Switzerland
    with pytest.raises(
        ValueError, match="only compatible with coordinates inside Switzerland",
    ):
        m.share_online()


def test_share_rejects_mixed_coords():
    from kartli.map import Map
    m = Map()
    m.marker(46.9472, 7.4443, label="Bern")  # Swiss
    m.marker(48.8566, 2.3522, label="Paris")  # non-Swiss
    with pytest.raises(ValueError, match="1 coordinate"):
        m.share_online()


def test_parser_share_default_false():
    from kartli.cli import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["render", "--center", "46.948,7.447"])
    assert args.share is False
