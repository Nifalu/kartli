"""Pixel-space extents of labeled overlays, used to pick a zoom that keeps
labels visible inside the canvas instead of clipped at the edges.

Each extent is anchored to a geographic coord with signed pixel offsets
(dx_min, dx_max, dy_min, dy_max). At a given zoom, the anchor projects to
some (px, py), and the extent covers pixels
(px + dx_min .. px + dx_max, py + dy_min .. py + dy_max).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from kartli.models import Area, Coord, Line, MapObjects, Marker
from kartli.rendering.overlays import _get_font


@dataclass(frozen=True)
class AnchoredExtent:
    coord: Coord
    dx_min: int
    dx_max: int
    dy_min: int
    dy_max: int


def _text_size(text: str, font_size: int) -> tuple[int, int]:
    font = _get_font(font_size)
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top


def _centroid(coords: list[Coord]) -> Coord:
    lat = sum(c.lat for c in coords) / len(coords)
    lon = sum(c.lon for c in coords) / len(coords)
    return Coord(lat=lat, lon=lon)


def _polyline_point_at(coords: list[Coord], t: float) -> Coord:
    """Interpolate at fraction t along a polyline, measuring distance in
    degrees of lat/lon. Approximate (doesn't account for projection), but
    good enough to anchor a label for auto-zoom padding."""
    if len(coords) == 1:
        return coords[0]
    segs: list[float] = []
    total = 0.0
    for i in range(len(coords) - 1):
        d = math.hypot(
            coords[i + 1].lon - coords[i].lon,
            coords[i + 1].lat - coords[i].lat,
        )
        segs.append(d)
        total += d
    if total == 0:
        return coords[0]
    target = t * total
    acc = 0.0
    for i, d in enumerate(segs):
        if acc + d >= target or i == len(segs) - 1:
            frac = (target - acc) / d if d > 0 else 0.0
            return Coord(
                lat=coords[i].lat + (coords[i + 1].lat - coords[i].lat) * frac,
                lon=coords[i].lon + (coords[i + 1].lon - coords[i].lon) * frac,
            )
        acc += d
    return coords[-1]


def _marker_extent(m: Marker, font_size: int) -> AnchoredExtent:
    r = m.size
    dx_min, dx_max = -r, r
    dy_min, dy_max = -r, r
    if m.label:
        tw, th = _text_size(m.label, font_size)
        # overlays.py draws the label at (cx + r + 4, cy - r): extends right
        # by tw, and downward from cy - r by th.
        dx_max = max(dx_max, r + 4 + tw)
        dy_max = max(dy_max, -r + th)
    return AnchoredExtent(m.coord, dx_min, dx_max, dy_min, dy_max)


def _area_label_extent(a: Area, font_size: int) -> AnchoredExtent | None:
    if not a.label or not a.coords:
        return None
    tw, th = _text_size(a.label, font_size)
    # overlays.py draws the label at pixel centroid with top-left at (cx, cy).
    # The pixel centroid and the lat/lon centroid only coincide for small
    # areas, but it's accurate enough for auto-zoom padding.
    return AnchoredExtent(_centroid(a.coords), 0, tw, 0, th)


def _line_label_extent(ln: Line, font_size: int) -> AnchoredExtent | None:
    if not ln.label or len(ln.coords) < 2:
        return None
    tw, th = _text_size(ln.label, font_size)
    # Line labels are rotated to follow the line, so use a conservative
    # symmetric extent (max dimension in every direction).
    r = max(tw, th) // 2
    return AnchoredExtent(
        _polyline_point_at(ln.coords, ln.label_position), -r, r, -r, r
    )


def compute_label_extents(
    objects: MapObjects, font_size: int
) -> list[AnchoredExtent]:
    """Collect pixel extents for every marker and every labeled area/line.
    Unlabeled areas/lines already contribute their coords to the coord bbox
    and don't need entries here."""
    extents: list[AnchoredExtent] = []
    for m in objects.markers:
        extents.append(_marker_extent(m, font_size))
    for a in objects.areas:
        ext = _area_label_extent(a, font_size)
        if ext is not None:
            extents.append(ext)
    for ln in objects.lines:
        ext = _line_label_extent(ln, font_size)
        if ext is not None:
            extents.append(ext)
    return extents
