"""Greedy 8-position label placement for markers.

For each labeled marker we try 8 candidate directions around the dot
(E, NE, SE, N, S, W, NW, SW) and pick the first one whose pixel
rectangle doesn't collide with an already-placed label, a marker dot,
or (optionally) the canvas edge. Falls back to E if every position
collides.

Collision checks use world-pixel AABBs (pre-origin subtraction) since
the origin offset is the same for every overlay.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from kartli.models import Marker
from kartli.rendering.overlays import _get_font
from kartli.rendering.projection import Projection


class LabelDirection(IntEnum):
    E = 0
    NE = 1
    SE = 2
    N = 3
    S = 4
    W = 5
    NW = 6
    SW = 7


# Order in which the solver tries positions. E first preserves the legacy
# "up-and-right of the dot" look when nothing collides.
_PRIORITY: tuple[LabelDirection, ...] = (
    LabelDirection.E,
    LabelDirection.NE,
    LabelDirection.SE,
    LabelDirection.N,
    LabelDirection.S,
    LabelDirection.W,
    LabelDirection.NW,
    LabelDirection.SW,
)

_COLLISION_PAD = 2


@dataclass(frozen=True)
class _Box:
    x0: int
    y0: int
    x1: int
    y1: int


def _overlaps(a: _Box, b: _Box, pad: int = _COLLISION_PAD) -> bool:
    return not (
        a.x1 + pad <= b.x0
        or a.x0 >= b.x1 + pad
        or a.y1 + pad <= b.y0
        or a.y0 >= b.y1 + pad
    )


def _text_size(text: str, font_size: int) -> tuple[int, int]:
    font = _get_font(font_size)
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top


def label_anchor(
    direction: LabelDirection,
    cx: int,
    cy: int,
    r: int,
    tw: int,
    th: int,
    pad: int = 4,
) -> tuple[int, int]:
    """Top-left pixel where PIL should draw the label text."""
    d = int((r + pad) * 0.707)
    if direction is LabelDirection.E:
        return cx + r + pad, cy - r
    if direction is LabelDirection.NE:
        return cx + d, cy - d - th
    if direction is LabelDirection.SE:
        return cx + d, cy + d
    if direction is LabelDirection.N:
        return cx - tw // 2, cy - r - pad - th
    if direction is LabelDirection.S:
        return cx - tw // 2, cy + r + pad
    if direction is LabelDirection.W:
        return cx - r - pad - tw, cy - r
    if direction is LabelDirection.NW:
        return cx - d - tw, cy - d - th
    if direction is LabelDirection.SW:
        return cx - d - tw, cy + d
    msg = f"unknown direction: {direction}"
    raise ValueError(msg)


def _label_box(
    direction: LabelDirection,
    cx: int,
    cy: int,
    r: int,
    tw: int,
    th: int,
) -> _Box:
    x, y = label_anchor(direction, cx, cy, r, tw, th)
    return _Box(x, y, x + tw, y + th)


def place_marker_labels(
    markers: list[Marker],
    font_size: int,
    zoom: int,
    tile_size: int,
    projection: Projection,
) -> dict[int, LabelDirection]:
    """Return {marker_index: chosen_direction} for labeled markers.

    Unlabeled markers are omitted. When every candidate position
    collides, falls back to E (so the legacy behavior still wins when
    there are no conflicts anyway)."""
    dots: list[_Box] = []
    centers: list[tuple[int, int, int]] = []  # (cx, cy, r)
    for m in markers:
        px, py = projection.coord_to_pixel(m.coord, zoom, tile_size)
        cx, cy = int(px), int(py)
        r = m.size
        dots.append(_Box(cx - r, cy - r, cx + r, cy + r))
        centers.append((cx, cy, r))

    placed_labels: list[_Box] = []
    result: dict[int, LabelDirection] = {}

    for i, m in enumerate(markers):
        if not m.label:
            continue
        cx, cy, r = centers[i]
        tw, th = _text_size(m.label, font_size)

        chosen: LabelDirection | None = None
        for direction in _PRIORITY:
            box = _label_box(direction, cx, cy, r, tw, th)
            collides = any(_overlaps(box, d) for j, d in enumerate(dots) if j != i)
            if not collides:
                collides = any(_overlaps(box, p) for p in placed_labels)
            if not collides:
                chosen = direction
                placed_labels.append(box)
                break

        if chosen is None:
            chosen = LabelDirection.E
            placed_labels.append(_label_box(chosen, cx, cy, r, tw, th))

        result[i] = chosen

    return result
