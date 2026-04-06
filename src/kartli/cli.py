from __future__ import annotations

import argparse
import sys
from functools import partial
from pathlib import Path

from kartli.map import Map
from kartli.models import Area, Coord, Line, Marker
from kartli.sharing import generate_qr
from kartli.tiles.esri import EsriSatelliteTiles
from kartli.tiles.osm import OsmTiles
from kartli.tiles.swisstopo import SwisstopoTiles


def _parse_coord_label(value: str) -> tuple[float, float, str]:
    """Parse 'lat,lon[,label]' into (lat, lon, label)."""
    parts = value.split(",", 2)
    if len(parts) < 2:
        msg = f"Invalid coordinate format: {value!r} (expected lat,lon[,label])"
        raise argparse.ArgumentTypeError(msg)
    lat, lon = float(parts[0]), float(parts[1])
    label = parts[2] if len(parts) > 2 else ""
    return lat, lon, label


def _parse_size(value: str) -> tuple[int, int]:
    """Parse 'WxH' into (width, height)."""
    parts = value.lower().split("x")
    if len(parts) != 2:
        msg = f"Invalid size format: {value!r} (expected WxH)"
        raise argparse.ArgumentTypeError(msg)
    return int(parts[0]), int(parts[1])


def _parse_coord_list(value: str) -> list[tuple[float, float]]:
    """Parse semicolon-separated coord pairs."""
    coords = []
    for part in value.split(";"):
        lat, lon, _ = _parse_coord_label(part.strip())
        coords.append((lat, lon))
    return coords


_TILE_SOURCES = {
    "swisstopo": SwisstopoTiles,
    "swisstopo-satellite": lambda: SwisstopoTiles(layer="ch.swisstopo.swissimage"),
    "osm": OsmTiles,
    "esri-satellite": EsriSatelliteTiles,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kartli",
        description="Generate static map images",
    )
    sub = parser.add_subparsers(dest="command")
    render = sub.add_parser("render", help="Render a map image")
    render.add_argument("--center", type=str, help="Center as lat,lon")

    zoom_group = render.add_mutually_exclusive_group()
    zoom_group.add_argument("--zoom", type=int, help="Zoom level")
    zoom_group.add_argument(
        "--scale", type=str, metavar="SCALE",
        help="Map scale, e.g. 1:25000 or 25000",
    )

    render.add_argument(
        "--marker", action="append", default=[],
        metavar="LAT,LON[,LABEL]", help="Add a marker",
    )
    render.add_argument(
        "--area", action="append", default=[],
        metavar="LAT1,LON1;LAT2,LON2;...", help="Add a polygon area",
    )
    render.add_argument(
        "--line", action="append", default=[],
        metavar="LAT1,LON1;LAT2,LON2;...", help="Add a line",
    )
    render.add_argument(
        "--size", type=str, default="800x600", help="Image size WxH",
    )
    render.add_argument(
        "--tiles", choices=list(_TILE_SOURCES), default=None,
        help="Tile source (default: auto-detect)",
    )
    render.add_argument(
        "--lv95", action="store_true",
        help="Interpret coordinates as LV95 East,North (EPSG:2056) "
        "instead of WGS84 lat,lon",
    )
    render.add_argument(
        "--no-scalebar", action="store_true",
        help="Disable the scale bar overlay",
    )
    render.add_argument(
        "--share", action="store_true",
        help="Upload drawing to swisstopo and generate a shareable URL, "
        "QR code ({output}_qr.png), and URL file ({output}_url.txt)",
    )
    render.add_argument(
        "--output", "-o", type=str, default="map.png", help="Output file",
    )
    return parser


def _parse_scale(value: str) -> int:
    """Parse '1:25000' or '25000' into the denominator integer."""
    cleaned = value.replace("'", "").replace(",", "").replace(" ", "")
    if ":" in cleaned:
        cleaned = cleaned.split(":")[1]
    return int(cleaned)


def _make_coord(a: float, b: float, *, lv95: bool) -> Coord:
    if lv95:
        return Coord.from_lv95(a, b)
    return Coord(lat=a, lon=b)


def _handle_share(m: Map, output: str) -> None:
    try:
        result = m.share_online()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    out = Path(output)
    url_path = out.with_name(f"{out.stem}_url.txt")
    qr_path = out.with_name(f"{out.stem}_qr.png")
    url_path.write_text(result.url + "\n")
    generate_qr(result.url, qr_path)
    print(f"URL saved to {url_path}")  # noqa: T201
    print(f"QR code saved to {qr_path}")  # noqa: T201
    print(f"Open in browser: {result.url}")  # noqa: T201


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "render":
        parser.print_help()
        sys.exit(1)

    factory = _TILE_SOURCES.get(args.tiles) if args.tiles else None
    tile_source = factory() if factory else None

    width, height = _parse_size(args.size)
    m = Map(
        tile_source=tile_source,
        width=width,
        height=height,
        show_scalebar=not args.no_scalebar,
    )

    coord = partial(_make_coord, lv95=args.lv95)

    for s in args.marker:
        a, b, label = _parse_coord_label(s)
        m.add_marker(Marker(coord=coord(a, b), label=label))
    for s in args.area:
        raw = _parse_coord_list(s)
        m.add_area(Area(coords=[coord(a, b) for a, b in raw]))
    for s in args.line:
        raw = _parse_coord_list(s)
        m.add_line(Line(coords=[coord(a, b) for a, b in raw]))

    if args.center:
        parts = args.center.split(",")
        m.set_center(coord(float(parts[0]), float(parts[1])))
    if args.zoom:
        m.set_zoom(args.zoom)
    elif args.scale:
        m.set_scale(_parse_scale(args.scale))

    m.render(args.output)
    print(f"Map saved to {args.output}")  # noqa: T201

    if args.share:
        _handle_share(m, args.output)


if __name__ == "__main__":
    main()
