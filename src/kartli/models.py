from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Coord:
    lat: float
    lon: float

    def __iter__(self):
        yield self.lat
        yield self.lon


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
    fill_color: str = "red"
    stroke_color: str = ""
    opacity: float = 0.3
    stroke_width: int = 2

    def __post_init__(self):
        self.coords = [
            c if isinstance(c, Coord) else Coord(*c) for c in self.coords
        ]
        if not self.stroke_color:
            self.stroke_color = self.fill_color


@dataclass
class Line:
    coords: list[tuple[float, float] | Coord]
    color: str = "blue"
    width: int = 3

    def __post_init__(self):
        self.coords = [
            c if isinstance(c, Coord) else Coord(*c) for c in self.coords
        ]


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
