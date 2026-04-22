from kartli.models import Marker
from kartli.rendering.placement import (
    LabelDirection,
    label_anchor,
    place_marker_labels,
)
from kartli.rendering.projection import WebMercatorProjection

# --- label_anchor produces distinct positions per direction ---


def test_label_anchor_east_matches_legacy_position():
    """E preserves the historical label position so unconflicted maps
    render the same as before placement was introduced."""
    x, y = label_anchor(LabelDirection.E, cx=100, cy=100, r=8, tw=50, th=13)
    assert (x, y) == (100 + 8 + 4, 100 - 8)


def test_label_anchor_all_directions_unique():
    anchors = {
        d: label_anchor(d, cx=100, cy=100, r=8, tw=50, th=13)
        for d in LabelDirection
    }
    assert len(set(anchors.values())) == len(LabelDirection)


def test_label_anchor_west_is_left_of_marker():
    x, _ = label_anchor(LabelDirection.W, cx=100, cy=100, r=8, tw=50, th=13)
    assert x < 100


def test_label_anchor_south_is_below_marker():
    _, y = label_anchor(LabelDirection.S, cx=100, cy=100, r=8, tw=50, th=13)
    assert y > 100


# --- Greedy placement ---


def _projection():
    return WebMercatorProjection()


def test_single_marker_picks_east():
    """One marker with no neighbors — default E wins since nothing collides."""
    markers = [Marker(coord=(46.9, 7.4), label="Only")]
    result = place_marker_labels(
        markers, font_size=13, zoom=15, tile_size=256, projection=_projection()
    )
    assert result == {0: LabelDirection.E}


def test_unlabeled_markers_are_skipped():
    markers = [
        Marker(coord=(46.9, 7.4), label=""),
        Marker(coord=(46.95, 7.45), label="Has label"),
    ]
    result = place_marker_labels(
        markers, font_size=13, zoom=15, tile_size=256, projection=_projection()
    )
    assert 0 not in result
    assert 1 in result


def test_two_overlapping_markers_pick_different_directions():
    """Two markers at the same coord: the second label can't use E without
    overlapping the first label, so it falls back to another direction."""
    markers = [
        Marker(coord=(46.9, 7.4), label="First"),
        Marker(coord=(46.9, 7.4), label="Second"),
    ]
    result = place_marker_labels(
        markers, font_size=13, zoom=15, tile_size=256, projection=_projection()
    )
    assert result[0] == LabelDirection.E
    assert result[1] != LabelDirection.E


def test_horizontal_row_of_close_markers_spreads_labels():
    """Five markers in a tight horizontal row — labels should not all stack
    at E (which would completely overlap each other)."""
    markers = [
        Marker(coord=(46.9, 7.40 + i * 0.0001), label=f"Box {i+1}")
        for i in range(5)
    ]
    result = place_marker_labels(
        markers, font_size=13, zoom=18, tile_size=256, projection=_projection()
    )
    # At least some labels must use directions other than E
    directions = set(result.values())
    assert len(directions) > 1


def test_far_apart_markers_all_use_east():
    """When markers are far apart, every label gets its preferred E slot."""
    markers = [
        Marker(coord=(46.0, 7.0), label="A"),
        Marker(coord=(47.5, 9.5), label="B"),
    ]
    result = place_marker_labels(
        markers, font_size=13, zoom=8, tile_size=256, projection=_projection()
    )
    assert result == {0: LabelDirection.E, 1: LabelDirection.E}


def test_placement_is_deterministic():
    markers = [
        Marker(coord=(46.9, 7.40 + i * 0.0001), label=f"Box {i+1}")
        for i in range(5)
    ]
    r1 = place_marker_labels(
        markers, font_size=13, zoom=18, tile_size=256, projection=_projection()
    )
    r2 = place_marker_labels(
        markers, font_size=13, zoom=18, tile_size=256, projection=_projection()
    )
    assert r1 == r2
