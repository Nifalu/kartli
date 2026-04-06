"""Share map drawings via swisstopo's KML service and generate QR codes."""

from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import httpx
import segno

from kartli.models import Coord, MapObjects

_KML_NS = "http://www.opengis.net/kml/2.2"
_SWISSTOPO_KML_API = "https://public.geo.admin.ch/api/kml/admin"
_KML_MIME = "application/vnd.google-earth.kml+xml"

# Named color map -> KML AABBGGRR format
_COLOR_MAP = {
    "red": "ff0000ff",
    "blue": "ffff0000",
    "green": "ff00ff00",
    "yellow": "ff00ffff",
    "orange": "ff0080ff",
    "purple": "ffff00ff",
    "black": "ff000000",
    "white": "ffffffff",
}


@dataclass
class ShareResult:
    """Result of uploading a KML drawing to swisstopo."""

    url: str
    kml_id: str
    admin_id: str
    kml_file_url: str


def _color_to_kml(color: str, opacity: float = 1.0) -> str:
    """Convert a named color or hex color to KML AABBGGRR format."""
    alpha = format(int(opacity * 255), "02x")
    if color in _COLOR_MAP:
        base = _COLOR_MAP[color]
        return alpha + base[2:]  # replace alpha
    # Try to parse hex (#RRGGBB or RRGGBB)
    color = color.lstrip("#")
    if len(color) == 6:
        r, g, b = color[0:2], color[2:4], color[4:6]
        return f"{alpha}{b}{g}{r}"
    return f"{alpha}0000ff"  # fallback to red


def _coord_to_kml_str(coord: Coord) -> str:
    """Convert a Coord to KML coordinate string (lon,lat,0)."""
    return f"{coord.lon},{coord.lat},0"


def objects_to_kml(objects: MapObjects) -> str:
    """Convert MapObjects (markers, areas, lines) to a KML XML string."""
    kml = ET.Element("kml", xmlns=_KML_NS)
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = "kartli drawing"

    for marker in objects.markers:
        pm = ET.SubElement(doc, "Placemark")
        if marker.label:
            ET.SubElement(pm, "name").text = marker.label
        style = ET.SubElement(pm, "Style")
        icon_style = ET.SubElement(style, "IconStyle")
        ET.SubElement(icon_style, "color").text = _color_to_kml(marker.color)
        ET.SubElement(icon_style, "scale").text = str(max(0.5, marker.size / 8))
        point = ET.SubElement(pm, "Point")
        ET.SubElement(point, "coordinates").text = _coord_to_kml_str(marker.coord)

    for area in objects.areas:
        pm = ET.SubElement(doc, "Placemark")
        if area.label:
            ET.SubElement(pm, "name").text = area.label
        style = ET.SubElement(pm, "Style")
        line_style = ET.SubElement(style, "LineStyle")
        ET.SubElement(line_style, "color").text = _color_to_kml(area.color)
        ET.SubElement(line_style, "width").text = str(area.stroke_width)
        poly_style = ET.SubElement(style, "PolyStyle")
        ET.SubElement(poly_style, "color").text = _color_to_kml(
            area.color, area.opacity
        )
        polygon = ET.SubElement(pm, "Polygon")
        outer = ET.SubElement(polygon, "outerBoundaryIs")
        ring = ET.SubElement(outer, "LinearRing")
        coords = [_coord_to_kml_str(c) for c in area.coords]
        # Close the ring if not already closed
        if area.coords and area.coords[0] != area.coords[-1]:
            coords.append(_coord_to_kml_str(area.coords[0]))
        ET.SubElement(ring, "coordinates").text = "\n".join(coords)

    for line in objects.lines:
        pm = ET.SubElement(doc, "Placemark")
        if line.label:
            ET.SubElement(pm, "name").text = line.label
        style = ET.SubElement(pm, "Style")
        line_style = ET.SubElement(style, "LineStyle")
        ET.SubElement(line_style, "color").text = _color_to_kml(line.color)
        ET.SubElement(line_style, "width").text = str(line.width)
        ls = ET.SubElement(pm, "LineString")
        coords = [_coord_to_kml_str(c) for c in line.coords]
        ET.SubElement(ls, "coordinates").text = "\n".join(coords)

    ET.indent(kml)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        kml, encoding="unicode"
    )


def upload_kml(kml_content: str) -> dict:
    """Upload a KML string to swisstopo's service-kml API.

    Returns the JSON response containing id, admin_id, and links.
    """
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as f:
        f.write(kml_content.encode("utf-8"))
        kml_path = Path(f.name)

    try:
        with kml_path.open("rb") as f:
            response = httpx.post(
                _SWISSTOPO_KML_API,
                headers={"Origin": "https://map.geo.admin.ch"},
                files={"kml": ("drawing.kml", f, _KML_MIME)},
                data={"author": "kartli", "author_version": "0.1.0"},
                timeout=30,
            )
        response.raise_for_status()
    finally:
        kml_path.unlink(missing_ok=True)

    return response.json()


def build_map_url(kml_id: str, center: Coord, zoom: int) -> str:
    """Build a map.geo.admin.ch URL that displays the uploaded KML."""
    from kartli.coordinates import wgs84_to_lv95

    kml_file_url = f"https://public.geo.admin.ch/api/kml/files/{kml_id}"
    if center.lv95_east is not None and center.lv95_north is not None:
        easting, northing = center.lv95_east, center.lv95_north
    else:
        easting, northing = wgs84_to_lv95(center.lat, center.lon)
    return (
        f"https://map.geo.admin.ch/#/map"
        f"?lang=en"
        f"&center={easting:.2f},{northing:.2f}"
        f"&z={zoom}"
        f"&layers=KML|{kml_file_url}"
    )


def share(objects: MapObjects, center: Coord, zoom: int) -> ShareResult:
    """Upload map objects as KML to swisstopo and return a shareable URL.

    Args:
        objects: The map objects (markers, areas, lines) to share.
        center: The map center coordinate.
        zoom: The map zoom level.

    Returns:
        ShareResult with the URL, KML ID, admin ID, and KML file URL.
    """
    kml = objects_to_kml(objects)
    result = upload_kml(kml)
    kml_id = result["id"]
    url = build_map_url(kml_id, center, zoom)
    return ShareResult(
        url=url,
        kml_id=kml_id,
        admin_id=result["admin_id"],
        kml_file_url=result["links"]["kml"],
    )


def generate_qr(url: str, output: str | Path) -> None:
    """Generate a QR code PNG for the given URL."""
    qr = segno.make(url)
    qr.save(str(output), scale=8, border=2)
