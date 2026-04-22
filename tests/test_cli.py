import argparse

import pytest

from kartli.cli import (
    _build_parser,
    _parse_coord_label,
    _parse_coord_list,
    _parse_coord_list_with_label,
    _parse_scale,
    _parse_size,
)

# --- _parse_coord_label ---


def test_parse_coord_label_with_label():
    lat, lon, label = _parse_coord_label("46.948,7.447,Bern")
    assert lat == 46.948
    assert lon == 7.447
    assert label == "Bern"


def test_parse_coord_label_without_label():
    lat, lon, label = _parse_coord_label("46.948,7.447")
    assert lat == 46.948
    assert lon == 7.447
    assert label == ""


def test_parse_coord_label_label_with_commas():
    lat, lon, label = _parse_coord_label("46.948,7.447,City of Bern, Switzerland")
    assert lat == 46.948
    assert label == "City of Bern, Switzerland"


def test_parse_coord_label_invalid_single_value():
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid coordinate"):
        _parse_coord_label("invalid")


def test_parse_coord_label_invalid_not_a_number():
    with pytest.raises(ValueError):
        _parse_coord_label("abc,def")


# --- _parse_size ---


def test_parse_size():
    w, h = _parse_size("1024x768")
    assert w == 1024
    assert h == 768


def test_parse_size_case_insensitive():
    w, h = _parse_size("800X600")
    assert w == 800
    assert h == 600


def test_parse_size_invalid():
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid size"):
        _parse_size("invalid")


def test_parse_size_too_many_parts():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_size("800x600x400")


# --- _parse_coord_list ---


def test_parse_coord_list():
    coords = _parse_coord_list("46.948,7.447;47.0,8.0;46.5,7.5")
    assert len(coords) == 3
    assert coords[0] == (46.948, 7.447)
    assert coords[1] == (47.0, 8.0)


def test_parse_coord_list_with_spaces():
    coords = _parse_coord_list("46.948,7.447 ; 47.0,8.0")
    assert len(coords) == 2


def test_parse_coord_list_single():
    coords = _parse_coord_list("46.948,7.447")
    assert len(coords) == 1


# --- _parse_coord_list_with_label ---


def test_parse_coord_list_with_label_no_label():
    coords, label = _parse_coord_list_with_label("46.948,7.447;47.0,8.0")
    assert len(coords) == 2
    assert label == ""


def test_parse_coord_list_with_label_simple():
    coords, label = _parse_coord_list_with_label("46.948,7.447;47.0,8.0|Route A")
    assert len(coords) == 2
    assert label == "Route A"


def test_parse_coord_list_with_label_strips_whitespace():
    _, label = _parse_coord_list_with_label("46.948,7.447;47.0,8.0|  Route A  ")
    assert label == "Route A"


def test_parse_coord_list_with_label_handles_umlauts():
    _, label = _parse_coord_list_with_label(
        "46.948,7.447;47.0,8.0|Schiessstand Süd"
    )
    assert label == "Schiessstand Süd"


def test_parse_coord_list_with_label_pipe_in_label_kept():
    """`split('|', 1)` splits on the first pipe, so pipes inside the
    label are preserved."""
    _, label = _parse_coord_list_with_label(
        "46.948,7.447;47.0,8.0|A|B"
    )
    assert label == "A|B"


# --- _parse_scale ---


def test_parse_scale_with_colon():
    assert _parse_scale("1:25000") == 25000


def test_parse_scale_without_colon():
    assert _parse_scale("25000") == 25000


def test_parse_scale_with_apostrophes():
    assert _parse_scale("1:25'000") == 25000


def test_parse_scale_with_commas():
    assert _parse_scale("1:25,000") == 25000


# --- Parser structure ---


def test_parser_zoom_and_scale_mutually_exclusive():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["render", "--zoom", "15", "--scale", "1:25000"])


def test_parser_accepts_all_tile_sources():
    parser = _build_parser()
    for source in ["swisstopo", "swisstopo-satellite", "osm", "esri-satellite"]:
        args = parser.parse_args([
            "render", "--tiles", source, "--center", "46.948,7.447"
        ])
        assert args.tiles == source


def test_parser_no_scalebar_flag():
    parser = _build_parser()
    args = parser.parse_args(["render", "--no-scalebar", "--center", "46.948,7.447"])
    assert args.no_scalebar is True


def test_parser_lv95_flag():
    parser = _build_parser()
    args = parser.parse_args([
        "render", "--lv95", "--center", "2600072,1199545"
    ])
    assert args.lv95 is True


def test_parser_lv95_default_false():
    parser = _build_parser()
    args = parser.parse_args(["render", "--center", "46.948,7.447"])
    assert args.lv95 is False


def test_parser_defaults():
    parser = _build_parser()
    args = parser.parse_args(["render", "--center", "46.948,7.447"])
    assert args.size == "800x600"
    assert args.output == "map.png"
    assert args.tiles is None
    assert args.zoom is None
    assert args.scale is None
    assert args.no_scalebar is False
    assert args.label_font_size == 13


def test_parser_label_font_size():
    parser = _build_parser()
    args = parser.parse_args([
        "render", "--label-font-size", "20", "--center", "46.948,7.447"
    ])
    assert args.label_font_size == 20
