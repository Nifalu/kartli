import argparse

import pytest

from kartli.cli import _parse_coord_label, _parse_size


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


def test_parse_coord_label_invalid():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_coord_label("invalid")


def test_parse_size():
    w, h = _parse_size("1024x768")
    assert w == 1024
    assert h == 768


def test_parse_size_invalid():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_size("invalid")
