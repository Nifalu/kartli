from kartli.models import Area, Coord, Line, MapObjects, Marker
from kartli.rendering.layout import (
    _marker_extent,
    compute_label_extents,
)

# --- _marker_extent ---


def test_marker_extent_no_label_is_just_radius():
    ext = _marker_extent(Marker(coord=(46.9, 7.4), size=8), font_size=13)
    assert ext.dx_min == -8
    assert ext.dx_max == 8
    assert ext.dy_min == -8
    assert ext.dy_max == 8


def test_marker_extent_with_label_extends_right():
    ext = _marker_extent(
        Marker(coord=(46.9, 7.4), size=8, label="Hello"), font_size=13
    )
    # Label starts at +12 (r + 4) and extends further right by text width.
    assert ext.dx_max > 12
    assert ext.dx_min == -8


def test_marker_extent_larger_font_extends_further():
    small = _marker_extent(
        Marker(coord=(46.9, 7.4), label="Bundeshaus"), font_size=13
    )
    large = _marker_extent(
        Marker(coord=(46.9, 7.4), label="Bundeshaus"), font_size=30
    )
    assert large.dx_max > small.dx_max
    assert large.dy_max > small.dy_max


# --- compute_label_extents across MapObjects ---


def test_compute_label_extents_collects_markers():
    objs = MapObjects()
    objs.markers = [
        Marker(coord=(46.9, 7.4), label="A"),
        Marker(coord=(47.0, 7.5), label="B"),
    ]
    extents = compute_label_extents(objs, font_size=13)
    assert len(extents) == 2


def test_compute_label_extents_skips_unlabeled_areas_and_lines():
    objs = MapObjects()
    objs.areas = [
        Area(coords=[(46.9, 7.4), (46.95, 7.4), (46.95, 7.45)])  # no label
    ]
    objs.lines = [Line(coords=[(46.9, 7.4), (46.95, 7.45)])]  # no label
    extents = compute_label_extents(objs, font_size=13)
    assert extents == []


def test_compute_label_extents_includes_labeled_area():
    objs = MapObjects()
    objs.areas = [
        Area(
            coords=[(46.9, 7.4), (46.95, 7.4), (46.95, 7.45)],
            label="Area label",
        )
    ]
    extents = compute_label_extents(objs, font_size=13)
    assert len(extents) == 1
    ext = extents[0]
    assert ext.dx_max > 0
    assert ext.dy_max > 0


def test_compute_label_extents_includes_labeled_line():
    objs = MapObjects()
    objs.lines = [
        Line(coords=[(46.9, 7.4), (46.95, 7.45)], label="Route")
    ]
    extents = compute_label_extents(objs, font_size=13)
    assert len(extents) == 1


# --- End-to-end: label size drives auto-zoom ---


def test_large_font_zooms_out_more_than_small():
    """A long label with a huge font should force a lower zoom than the
    same label with a small font, so the label stays on the canvas."""
    from kartli.map import Map

    def zoom_for_font(font_size: int) -> int:
        m = Map(width=400, height=300, label_font_size=font_size)
        m.marker(46.9, 7.4, label="Bundeshausplatz in Bern")
        m.marker(46.95, 7.45, label="Zytglogge am Kramgasse")
        projection = m._resolve_tile_source().projection
        _, zoom = m._resolve_center_zoom(projection)
        return zoom

    small_zoom = zoom_for_font(10)
    large_zoom = zoom_for_font(40)
    assert large_zoom < small_zoom


def test_default_font_matches_previous_behavior_qualitatively():
    """Sanity check: a plain labeled marker still picks a reasonable zoom."""
    from kartli.map import Map

    m = Map(width=800, height=600)
    m.marker(46.9, 7.4, label="A")
    m.marker(47.0, 7.5, label="B")
    projection = m._resolve_tile_source().projection
    _, zoom = m._resolve_center_zoom(projection)
    assert 1 <= zoom <= 18


# --- auto_center shifts toward label-heavy side ---


def test_auto_center_shifts_right_for_right_extending_labels():
    """Two markers with long labels: center should shift right compared to
    the plain coord-bbox center so labels have room on the right edge."""
    from kartli.map import Map

    def center_for(labels: list[str]) -> Coord:
        m = Map(width=400, height=300, label_font_size=20)
        m.marker(46.9, 7.4, label=labels[0])
        m.marker(46.9, 7.5, label=labels[1])
        projection = m._resolve_tile_source().projection
        c, _ = m._resolve_center_zoom(projection)
        return c

    plain = center_for(["", ""])
    labeled = center_for(["Really Long Label A", "Really Long Label B"])
    # Labels extend right (eastward), so the adjusted center should be
    # at a higher longitude than the coord-bbox center.
    assert labeled.lon > plain.lon
