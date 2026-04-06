from __future__ import annotations

from dataclasses import dataclass, field


class CoordinateError(ValueError):
    """Raised when coordinates are invalid."""


@dataclass(frozen=True)
class Coord:
    lat: float
    lon: float
    lv95_east: float | None = field(default=None, repr=False, compare=False)
    lv95_north: float | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if not -90 <= self.lat <= 90:
            msg = f"Invalid latitude {self.lat}: must be between -90 and 90"
            raise CoordinateError(msg)
        if not -180 <= self.lon <= 180:
            msg = f"Invalid longitude {self.lon}: must be between -180 and 180"
            raise CoordinateError(msg)

    def __iter__(self):
        yield self.lat
        yield self.lon

    @classmethod
    def from_lv95(cls, east: float, north: float) -> Coord:
        """Create a Coord from Swiss LV95 (EPSG:2056) easting/northing.

        The original LV95 values are preserved on the returned Coord
        to avoid precision loss in roundtrip conversions.
        """
        from kartli.coordinates import lv95_to_wgs84

        lat, lon = lv95_to_wgs84(east, north)
        return cls(lat=lat, lon=lon, lv95_east=east, lv95_north=north)


@dataclass
class Marker:
    coord: tuple[float, float] | Coord
    label: str = ""
    color: str = "red"
    size: int = 8

    def __post_init__(self):
        if not isinstance(self.coord, Coord):
            self.coord = Coord(*self.coord)


@dataclass
class Area:
    coords: list[tuple[float, float] | Coord]
    label: str = ""
    color: str = "red"
    opacity: float = 0.3
    stroke_width: int = 2

    def __post_init__(self):
        self.coords = [
            c if isinstance(c, Coord) else Coord(*c) for c in self.coords
        ]


@dataclass
class Line:
    coords: list[tuple[float, float] | Coord]
    color: str = "blue"
    width: int = 3
    label: str = ""
    label_position: float = 0.5
    """Position of the label along the line, from 0.0 (start) to 1.0 (end)."""

    def __post_init__(self):
        self.coords = [
            c if isinstance(c, Coord) else Coord(*c) for c in self.coords
        ]
        self.label_position = max(0.0, min(1.0, self.label_position))


@dataclass
class BBox:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    @classmethod
    def from_coords(cls, coords: list[Coord]) -> BBox:
        lats = [c.lat for c in coords]
        lons = [c.lon for c in coords]
        return cls(
            min_lat=min(lats),
            min_lon=min(lons),
            max_lat=max(lats),
            max_lon=max(lons),
        )

    @property
    def center(self) -> Coord:
        return Coord(
            lat=(self.min_lat + self.max_lat) / 2,
            lon=(self.min_lon + self.max_lon) / 2,
        )


@dataclass
class MapObjects:
    markers: list[Marker] = field(default_factory=list)
    areas: list[Area] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)

    def all_coords(self) -> list[Coord]:
        coords: list[Coord] = []
        for m in self.markers:
            coords.append(m.coord)
        for a in self.areas:
            coords.extend(a.coords)
        for ln in self.lines:
            coords.extend(ln.coords)
        return coords

    def bbox(self) -> BBox | None:
        coords = self.all_coords()
        if not coords:
            return None
        return BBox.from_coords(coords)
